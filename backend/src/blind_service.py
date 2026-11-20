"""盲测服务：封卷冻结、盲码读数、按等级KDE计分、漏判/误报统计。

与日常化验表完全解耦，仅在封卷时读取当前参考样编号与密度做快照；
计分只认快照，不重新查 fuel_samples，保证重试结果一致。"""
import json
import numpy as np
from fastapi import HTTPException
from sqlalchemy import select
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KernelDensity
from .database import Session
from .models import FuelSample,Tank
from .constants import GRADES
from .blind_models import BlindSession,BlindSample,BlindReading,BlindScore,now_iso
from .transfer_service import obj,get,audit

OPEN='open';SEALED='sealed';SCORING='scoring';REVEALED='revealed'

# ---------- 视图：揭榜前对所有人屏蔽封存字段（人工判定/考样密度/成绩） ----------
def reading_view(x):
    return None if x is None else obj(x)
def sample_view(s,x,role,revealed):
    reading=s.scalar(select(BlindReading).where(BlindReading.sample_id==x.id))
    base={'id':x.id,'session_id':x.session_id,'blind_code':x.blind_code,'grade':x.grade,
          'reading':reading_view(reading)}
    if revealed:
        base.update({'density_15':float(x.density_15),'human_verdict':x.human_verdict,
                     'human_basis':x.human_basis})
        score=s.scalar(select(BlindScore).where(BlindScore.sample_id==x.id))
        base['score']=None if score is None else obj(score)
    else:
        base.update({'density_15':None,'human_verdict':None,'human_basis':None,'score':None})
    return base
def session_view(s,x,u=None):
    role=u['role']if u else 'viewer'
    revealed=x.state==REVEALED
    samples=[sample_view(s,z,role,revealed)for z in s.scalars(
        select(BlindSample).where(BlindSample.session_id==x.id).order_by(BlindSample.blind_code))]
    out=obj(x)
    if not revealed:
        # 参考快照只回传每级条数，编号与密度范围封存到揭榜
        snap=out.get('reference_snapshot')
        out['reference_snapshot']=None if snap is None else {g:{'reference_count':len(v['reference_codes'])}for g,v in snap.items()}
        out['summary_snapshot']=None
    out['samples']=samples
    return out

# ---------- 开场 ----------
def create_session(s,d,u):
    if s.scalar(select(BlindSession.id).where(BlindSession.code==d.code)):
        raise HTTPException(409,'盲测场次编号已存在')
    x=BlindSession(code=d.code,title=d.title,state=OPEN,score_error='')
    s.add(x);s.flush();audit(s,u,'blind_session_opened',f'{x.code}:{x.title}')
    return x
def add_sample(s,session_id,d,u):
    sess=get(s,BlindSession,session_id,True)
    if sess.state!=OPEN:raise HTTPException(409,'场次已封卷，不能再增减考样')
    if s.scalar(select(BlindSample.id).where(BlindSample.session_id==session_id,BlindSample.blind_code==d.blind_code)):
        raise HTTPException(409,'该盲码已在本场使用')
    x=BlindSample(session_id=session_id,**d.model_dump())
    s.add(x);s.flush();audit(s,u,'blind_sample_sealed_in',f'{sess.code}:{x.blind_code}:{x.grade}')
    return x

# ---------- 封卷：冻结人工判定与参考样范围 ----------
def seal(s,session_id,u):
    sess=get(s,BlindSession,session_id,True)
    if sess.state!=OPEN:raise HTTPException(409,'只有开场中的场次可以收卷封卷')
    samples=s.scalars(select(BlindSample).where(BlindSample.session_id==session_id)).all()
    if not samples:raise HTTPException(409,'场次还没有考样，不能封卷')
    snapshot={}
    for grade in sorted({z.grade for z in samples}):
        refs=s.scalars(select(FuelSample).join(Tank,FuelSample.tank_id==Tank.id)
                       .where(FuelSample.reference==True,Tank.grade==grade)
                       .order_by(FuelSample.id)).all()
        if len(refs)<20:raise HTTPException(409,f'{grade} 等级参考样不足20条，无法封卷计分')
        snapshot[grade]={'reference_codes':[z.code for z in refs],
                         'reference_values':[float(z.density_15)for z in refs]}
    sess.reference_snapshot=json.loads(json.dumps(snapshot))
    sess.state=SEALED;sess.sealed_at=now_iso();sess.sealed_by=u['email'];sess.score_error=''
    audit(s,u,'blind_session_sealed',f'{sess.code}:考样{len(samples)}个/参考{sum(len(v["reference_codes"])for v in snapshot.values())}条')
    return sess

# ---------- 化验员凭盲码录读数；收卷与补录并发 ----------
def submit_reading(s,session_id,d,u):
    sess=get(s,BlindSession,session_id,True)  # 锁场次行，串行化封卷与录入
    if sess.state==REVEALED:raise HTTPException(409,'场次已揭榜，读数通道关闭')
    sample=s.scalar(select(BlindSample).where(BlindSample.session_id==session_id,
                     BlindSample.blind_code==d.blind_code).with_for_update())
    if not sample:raise HTTPException(404,'盲码不属于本场次，请核对盲码单')
    reading=s.scalar(select(BlindReading).where(BlindReading.sample_id==sample.id).with_for_update())
    late=sess.state!=OPEN  # 封卷/计分中受理一律为补录
    if reading is None:
        reading=BlindReading(sample_id=sample.id,density_read=d.density_read,
                             chemist=u['email'],accepted_at=now_iso(),late=late,attempts=1)
        s.add(reading)
    else:
        if reading.late and not late:
            raise HTTPException(409,'该读数已按补录受理，不能回退为收卷前读数')
        reading.density_read=d.density_read;reading.chemist=u['email']
        reading.accepted_at=now_iso();reading.late=late;reading.attempts+=1
    s.flush()
    audit(s,u,'blind_reading_late'if late else'blind_reading_accepted',
          f'{sess.code}:{sample.blind_code}:{reading.density_read}')
    return reading

# ---------- 等级 KDE：只用封卷快照，考样不参与拟合 ----------
def fit_grade(snapshot_grade):
    values=np.array([[v]for v in snapshot_grade['reference_values']],dtype=float)
    if len(values)<20:raise ValueError('参考样不足20条')
    scaler=StandardScaler();z=scaler.fit_transform(values)
    if float(scaler.var_[0])<1e-8:raise ValueError('参考密度没有足够变化')
    model=KernelDensity(kernel='gaussian',bandwidth=.3).fit(z)
    threshold=float(np.quantile(model.score_samples(z),.05))
    return model,scaler,threshold
def judge_grade(model,scaler,threshold,grade,density):
    score=float(model.score_samples(scaler.transform([[float(density)]]))[0])
    spec=GRADES[grade]
    in_spec=spec['density_min']<=float(density)<=spec['density_max']
    return score,threshold,(score>=threshold and in_spec)

def _outcome(algo_ok,human):
    algo='normal'if algo_ok else'anomaly'
    if human=='anomaly'and algo=='normal':outcome='miss'          # 漏判：人工说异常，算法放行
    elif human=='normal'and algo=='anomaly':outcome='false_alarm' # 误报：人工说正常，算法判异
    else:outcome='correct'
    return algo,outcome

# ---------- 计分：断点续算、重试不重复出成绩 ----------
def run_scoring(session_id,u):
    # 短事务抢锁并置 scoring；正在计分的场次拒绝并发重入
    with Session.begin() as s:
        sess=get(s,BlindSession,session_id,True)
        if sess.state not in (SEALED,SCORING):
            raise HTTPException(409,'只有已封卷场次可以计分')
        if sess.state==SCORING and sess.score_error=='':
            raise HTTPException(409,'计分正在进行中，请勿重复触发')
        sess.state=SCORING;sess.score_error='';s.flush()
    try:
        with Session() as s:
            sess=s.get(BlindSession,session_id)
            snapshot=sess.reference_snapshot
            samples=s.scalars(select(BlindSample).where(BlindSample.session_id==session_id)
                              .order_by(BlindSample.id)).all()
        fitted={}
        for grade in sorted({z.grade for z in samples}):
            model,scaler,threshold=fit_grade(snapshot[grade])
            fitted[grade]=(model,scaler,threshold)
        for sample in samples:
            with Session.begin() as s:
                # 已有成绩直接跳过：中断恢复与重试都不会重复出成绩
                if s.scalar(select(BlindScore.id).where(BlindScore.sample_id==sample.id)):
                    continue
                z=s.get(BlindSample,sample.id)
                reading=s.scalar(select(BlindReading).where(BlindReading.sample_id==z.id))
                if reading is None:
                    s.add(BlindScore(sample_id=z.id,session_id=session_id,grade=z.grade,
                                     used_density=None,kde_score=None,kde_threshold=None,
                                     algo_verdict=None,human_verdict=z.human_verdict,
                                     outcome='missing',evidence={'reason':'缺交：收卷前无受理读数'},
                                     scored_at=now_iso()))
                    s.flush();continue
                if reading.late:
                    s.add(BlindScore(sample_id=z.id,session_id=session_id,grade=z.grade,
                                     used_density=reading.density_read,kde_score=None,kde_threshold=None,
                                     algo_verdict=None,human_verdict=z.human_verdict,
                                     outcome='late',evidence={'reason':'补录：封卷后受理，不计分'},
                                     scored_at=now_iso()))
                    s.flush();continue
                model,scaler,threshold=fitted[z.grade]
                score,thr,algo_ok=judge_grade(model,scaler,threshold,z.grade,reading.density_read)
                algo,outcome=_outcome(algo_ok,z.human_verdict)
                s.add(BlindScore(sample_id=z.id,session_id=session_id,grade=z.grade,
                                 used_density=reading.density_read,kde_score=score,kde_threshold=thr,
                                 algo_verdict=algo,human_verdict=z.human_verdict,outcome=outcome,
                                 evidence={'reference_count':len(snapshot[z.grade]['reference_codes']),
                                           'threshold_quantile':.05,'bandwidth':.3,'kernel':'gaussian',
                                           'spec':GRADES[z.grade],
                                           'fit_scope':'封卷快照参考样，考样不参与拟合'},
                                 scored_at=now_iso()))
                s.flush()
        with Session.begin() as s:
            sess=get(s,BlindSession,session_id,True)
            sess.state=SEALED  # 计分完成回到已封卷，等待主管揭榜
            sess.score_error='';sess.last_scored_sample_id=samples[-1].id
            audit(s,u,'blind_scoring_done',f'{sess.code}:{len(samples)}个考样')
    except Exception as e:
        with Session.begin() as s:
            sess=get(s,BlindSession,session_id,True)
            sess.state=SEALED;sess.score_error=f'{type(e).__name__}: {e}'
            audit(s,u,'blind_scoring_failed',f'{sess.code}:{sess.score_error}')
        raise HTTPException(500,f'计分中断，已保留进度，可重试续算：{e}')

# ---------- 揭榜 ----------
def reveal(s,session_id,u):
    sess=get(s,BlindSession,session_id,True)
    if sess.state not in (SEALED,SCORING):raise HTTPException(409,'场次未封卷，不能揭榜')
    if sess.state==SCORING:raise HTTPException(409,'计分尚未完成，不能揭榜')
    samples=s.scalars(select(BlindSample).where(BlindSample.session_id==session_id)).all()
    scores=s.scalars(select(BlindScore).where(BlindScore.session_id==session_id)).all()
    if len(scores)<len(samples):raise HTTPException(409,'仍有考样未出成绩，不能揭榜')
    def bucket(rows):
        # 只有收卷前已受理、实际计分的读数进入率分母；缺交/补录单列
        b={'total':len(rows),'scored':0,'miss':0,'false_alarm':0,'correct':0,'missing':0,'late':0,
           'human_anomaly':0,'human_normal':0,'algo_pass_on_anomaly':0,'algo_flag_on_normal':0}
        for sc in rows:
            b[sc.outcome]+=1
            if sc.outcome in('correct','miss','false_alarm'):
                b['scored']+=1
                if sc.human_verdict=='anomaly':b['human_anomaly']+=1
                else:b['human_normal']+=1
            if sc.outcome=='miss':b['algo_pass_on_anomaly']+=1
            if sc.outcome=='false_alarm':b['algo_flag_on_normal']+=1
        b['miss_rate']=(b['miss']/b['human_anomaly'])if b['human_anomaly']else None
        b['false_alarm_rate']=(b['false_alarm']/b['human_normal'])if b['human_normal']else None
        return b
    by_grade={g:bucket([sc for sc in scores if sc.grade==g])for g in sorted({z.grade for z in samples})}
    summary={'overall':bucket(scores),'by_grade':by_grade,
             'note':'漏判率=漏判/人工异常数；误报率=误报/人工正常数；缺交、补录单列不计分母'}
    sess.summary_snapshot=summary;sess.state=REVEALED
    sess.revealed_at=now_iso();sess.revealed_by=u['email']
    audit(s,u,'blind_session_revealed',
          f"{sess.code}:漏判{summary['overall']['miss']}/误报{summary['overall']['false_alarm']}/缺交{summary['overall']['missing']}/补录{summary['overall']['late']}")
    return sess

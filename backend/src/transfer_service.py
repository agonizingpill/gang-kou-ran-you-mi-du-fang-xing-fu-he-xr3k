from datetime import datetime,timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from .models import Tank,FuelSample,Transfer,Audit
from .density_model import within_spec

def obj(x):return {c.name:float(getattr(x,c.name))if isinstance(getattr(x,c.name),Decimal)else getattr(x,c.name)for c in x.__table__.columns}
def get(s,model,id,lock=False):
    q=select(model).where(model.id==id)
    if lock:q=q.with_for_update().execution_options(populate_existing=True)
    x=s.scalar(q)
    if not x:raise HTTPException(404,'记录不存在')
    return x
def audit(s,u,action,detail):s.add(Audit(actor=u['email'],action=action,detail=str(detail),at=datetime.now(timezone.utc).isoformat()))
def sample_view(s,x):return {**obj(x),'tank_code':s.get(Tank,x.tank_id).code,'grade':s.get(Tank,x.tank_id).grade}
def transfer_view(s,x):
    sample=s.get(FuelSample,x.sample_id);tank=s.get(Tank,sample.tank_id)
    return {**obj(x),'sample_code':sample.code,'tank_code':tank.code,'tank_liters':float(tank.liters)}
def eligible(s,x):
    if x.reference:raise HTTPException(409,'参考样不能用于实船调拨')
    if x.status not in ['qualified','retested']:raise HTTPException(409,'油样未合格或异常尚未通过复检，不能申请调拨')
    t=get(s,Tank,x.tank_id)
    density=x.retest_density if x.retest_density is not None else x.density_15
    if not within_spec(t.grade,density,x.viscosity,x.sulfur):raise HTTPException(409,'复检或原样仍超出本等级密度/黏度/硫规格')
    return t,density

def retest(s,x,d,u):
    if x.reference or x.status not in ['anomaly','rejected','retested']:raise HTTPException(409,'仅异常待复检或未通过样可复检')
    if s.scalar(select(Transfer.id).where(Transfer.sample_id==x.id).limit(1)):raise HTTPException(409,'油样已被调拨引用，化验快照冻结')
    t=get(s,Tank,x.tank_id);x.retest_density=d.density;x.retest_note=d.note
    x.status='retested'if within_spec(t.grade,d.density,x.viscosity,x.sulfur)else'rejected';audit(s,u,'sample_retested',f'{x.code}:{x.status}');return sample_view(s,x)
def request_transfer(s,x,d,u):
    t,density=eligible(s,x)
    if t.status!='active':raise HTTPException(409,'储罐处于暂停调拨状态')
    if d.liters>t.liters:raise HTTPException(409,'申请调拨量超过罐内可用量，未扣减')
    tr=Transfer(**d.model_dump(),status='requested',grade_snapshot=t.grade,density_snapshot=density,viscosity_snapshot=x.viscosity,sulfur_snapshot=x.sulfur,released_by='');s.add(tr);s.flush();audit(s,u,'transfer_requested',tr.code);return transfer_view(s,tr)
def release(s,tr,u):
    if tr.status!='requested':raise HTTPException(409,'调拨单已放行，不能重复扣减')
    x=get(s,FuelSample,tr.sample_id);t=get(s,Tank,x.tank_id,True)
    if t.status!='active':raise HTTPException(409,'储罐暂停中，不能放行')
    if not within_spec(tr.grade_snapshot,tr.density_snapshot,tr.viscosity_snapshot,tr.sulfur_snapshot):raise HTTPException(409,'调拨化验快照不满足等级规格')
    if tr.liters>t.liters:raise HTTPException(409,'罐内可用量不足，调拨未扣减')
    from .harbor_service import occupy_for_release
    occupy_for_release(s,tr,u)
    t.liters-=tr.liters;tr.status='released';tr.released_by=u['email'];audit(s,u,'transfer_released',f'{tr.code}:{tr.liters}L');s.flush();return transfer_view(s,tr)

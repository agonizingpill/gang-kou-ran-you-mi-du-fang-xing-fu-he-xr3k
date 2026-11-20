import random,json
from sqlalchemy import select,func
from src.database import Base,engine,Session
from src.models import User,Tank,FuelSample,Transfer
from src.receipt_models import TankCapacity,TankReceipt,LoadingReconciliation
from src.harbor_models import FuelLine,LinePermit,Berth,VesselWindow,RetainedSample,RetestOrder
from src.blind_models import BlindSession,BlindSample,BlindReading,BlindScore
from src.security import password_hash

def seed():
    Base.metadata.create_all(engine)
    with Session.begin() as s:
        for role in ['admin','chemist','viewer']:
            if not s.scalar(select(User).where(User.email==role+'@chenggang.local')):s.add(User(email=role+'@chenggang.local',password=password_hash('Harbor2026!'),role=role))
        for code,grade,liters in [('TK-06','VLSFO',50000),('TK-08','VLSFO',20000),('TK-M01','MGO',35000)]:
            if not s.scalar(select(Tank).where(Tank.code==code)):s.add(Tank(code=code,grade=grade,liters=liters,status='active'))
        s.flush();tanks={x.code:x for x in s.scalars(select(Tank))};rng=random.Random(42)
        for grade,tank,mu,sigma,visc,sulfur in [('VLSFO','TK-06',975,8,130,.35),('MGO','TK-M01',850,6,4,.06)]:
            for i in range(60):
                code=f'REF-{grade}-{i:03}'
                if not s.scalar(select(FuelSample).where(FuelSample.code==code)):s.add(FuelSample(code=code,tank_id=tanks[tank].id,density_15=round(rng.gauss(mu,sigma),3),viscosity=visc,sulfur=sulfur,status='qualified',reference=True,evidence='seed42固定等级合格参考样',retest_note=''))
        for code,tank,density,visc,sulfur in [('FS-20261117-01','TK-06',980,130,.35),('FS-OFF','TK-06',1035,130,.35),('FS-MGO-01','TK-M01',852,4,.06)]:
            if not s.scalar(select(FuelSample).where(FuelSample.code==code)):s.add(FuelSample(code=code,tank_id=tanks[tank].id,density_15=density,viscosity=visc,sulfur=sulfur,status='received',reference=False,evidence='',retest_note=''))
        for code,grade in [('FL-V01','VLSFO'),('FL-M01','MGO')]:
            if not s.scalar(select(FuelLine).where(FuelLine.code==code)):s.add(FuelLine(code=code,allowed_grade=grade,capacity_lpm=1000,min_flush_liters=200,state='idle'))
        for code,draft in [('BT-01',10),('BT-02',8)]:
            if not s.scalar(select(Berth).where(Berth.code==code)):s.add(Berth(code=code,max_draft=draft,active=True))
        s.flush()
        for code,cap,density in [('TK-06',100000,975),('TK-08',60000,978),('TK-M01',70000,850)]:
            tank=tanks[code]
            if not s.scalar(select(TankCapacity.id).where(TankCapacity.tank_id==tank.id)):
                s.add(TankCapacity(tank_id=tank.id,capacity_liters=cap,density_15=density,baseline_note='演示初始计量基准，按储罐台账与等级密度建立'))
        if not s.scalar(select(TankReceipt.id).where(TankReceipt.code=='RC-DEMO-17')):
            s.add(TankReceipt(tank_id=tanks['TK-06'].id,code='RC-DEMO-17',grade='VLSFO',liters=5000,density_15=985,viscosity=130,sulfur=.35,state='planned'))
        # 盲测演示场次：开场中，6 个考样；人工判定与参考范围封存在字段里，页面揭榜前不回传
        if not s.scalar(select(BlindSession.id).where(BlindSession.code=='BLIND-2026A')):
            bs=BlindSession(code='BLIND-2026A',title='2026秋季密度比对盲测（KDE漏判/误报）',state='open',score_error='')
            s.add(bs);s.flush()
            demo_samples=[('BC-A01','VLSFO',978.0,'normal','落在VLSFO参考分布主体内'),
                          ('BC-A02','VLSFO',1005.0,'normal','接近内控上限但参考分布支持'),
                          ('BC-A03','VLSFO',1035.0,'anomaly','明显高于参考分布且超内控规格'),
                          ('BC-A04','VLSFO',952.0,'anomaly','低于参考分布主体，人工判异待查'),
                          ('BC-M01','MGO',852.0,'normal','落在MGO参考分布主体内'),
                          ('BC-M02','MGO',898.0,'anomaly','超出MGO密度内控上限')]
            for blind_code,grade,density,verdict,basis in demo_samples:
                s.add(BlindSample(session_id=bs.id,blind_code=blind_code,grade=grade,
                                  density_15=density,human_verdict=verdict,human_basis=basis))
    with Session() as s:print(json.dumps({k:s.scalar(select(func.count()).select_from(v))for k,v in [('users',User),('tanks',Tank),('samples',FuelSample),('transfers',Transfer),('tank_capacities',TankCapacity),('receipts',TankReceipt),('reconciliations',LoadingReconciliation),('fuel_lines',FuelLine),('line_permits',LinePermit),('berths',Berth),('vessel_windows',VesselWindow),('retained_samples',RetainedSample),('retest_orders',RetestOrder),('blind_sessions',BlindSession),('blind_samples',BlindSample),('blind_readings',BlindReading),('blind_scores',BlindScore)]}))
if __name__=='__main__':seed()

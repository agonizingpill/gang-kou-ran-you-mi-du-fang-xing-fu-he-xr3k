from decimal import Decimal
from datetime import datetime,timezone
from fastapi import HTTPException
from sqlalchemy import select
from .models import Tank,Transfer
from .receipt_models import TankCapacity,TankReceipt,LoadingReconciliation
from .transfer_service import obj,get,audit,transfer_view
from .density_model import within_spec
from .constants import GRADES

def now():return datetime.now(timezone.utc).isoformat()
def capacity_view(s,x):return {**obj(x),'tank_code':s.get(Tank,x.tank_id).code}
def receipt_view(s,x):return {**obj(x),'tank_code':s.get(Tank,x.tank_id).code}
def recon_view(s,x):return {**obj(x),'transfer_code':s.get(Transfer,x.transfer_id).code}
def capacity(s,data,u):
    tank=get(s,Tank,data.tank_id,True)
    if s.scalar(select(TankCapacity.id).where(TankCapacity.tank_id==tank.id)):raise HTTPException(409,'储罐已建罐容与密度基准，不可覆盖历史计量')
    if data.capacity_liters<tank.liters:raise HTTPException(409,'罐容不能小于当前存油量')
    spec=GRADES[tank.grade]
    if not spec['density_min']<=data.density_15<=spec['density_max']:raise HTTPException(409,'初始存油密度不在储罐等级范围内')
    x=TankCapacity(**data.model_dump());s.add(x);s.flush();audit(s,u,'capacity_registered',tank.code);return capacity_view(s,x)
def verify(s,x):
    tank=get(s,Tank,x.tank_id)
    if x.grade!=tank.grade:raise HTTPException(409,'到港油品等级与接收储罐不一致')
    if not within_spec(x.grade,x.density_15,x.viscosity,x.sulfur):raise HTTPException(409,'到港密度、黏度或硫含量超出本等级规格')
    return tank
def inspect(s,id,u):
    x=get(s,TankReceipt,id,True)
    if x.state!='planned':raise HTTPException(409,'仅计划收油单可化验核对，已核对或已入罐不可重复')
    verify(s,x);x.state='inspected';x.inspection_snapshot={**obj(x),'inspection_snapshot':None,'receipt_snapshot':None,'checked_by':u['email'],'at':now()}
    audit(s,u,'receipt_inspected',x.code);return receipt_view(s,x)
def receive(s,id,u):
    x=get(s,TankReceipt,id,True)
    if x.state!='inspected':raise HTTPException(409,'收油须先化验核对且不得重复入罐')
    t=get(s,Tank,x.tank_id,True);verify(s,x)
    if t.status!='active':raise HTTPException(409,'储罐暂停，禁止到港油入罐')
    c=s.scalar(select(TankCapacity).where(TankCapacity.tank_id==t.id).with_for_update())
    if not c:raise HTTPException(409,'主管须先建立罐容及存油密度基准')
    before=t.liters;after=before+x.liters
    if after>c.capacity_liters:raise HTTPException(409,'到港入量超过储罐剩余罐容，未改变存量')
    old_density=c.density_15;weighted=((before*old_density+x.liters*x.density_15)/after).quantize(Decimal('.001'))
    t.liters=after;c.density_15=weighted;x.state='received';x.received_by=u['email']
    x.receipt_snapshot={'code':x.code,'tank_code':t.code,'grade':t.grade,'before_liters':float(before),'receipt_liters':float(x.liters),'after_liters':float(after),'capacity_liters':float(c.capacity_liters),'before_density_15':float(old_density),'arrival_density_15':float(x.density_15),'weighted_density_15':float(weighted),'received_by':u['email'],'at':now(),'density_formula':'(before_liters * before_density + receipt_liters * arrival_density) / after_liters'}
    audit(s,u,'receipt_received',x.code+' / '+str(x.liters)+'L');return receipt_view(s,x)
def reconciliation(s,data,u):
    tr=get(s,Transfer,data.transfer_id,True)
    if tr.status!='released':raise HTTPException(409,'只有已放行调拨单可以做实船计量对账')
    if s.scalar(select(LoadingReconciliation.id).where(LoadingReconciliation.transfer_id==tr.id)):raise HTTPException(409,'该调拨已有对账，不能重复登记交接计量')
    meter=data.meter_after-data.meter_before
    if meter<=0:raise HTTPException(409,'表底必须递增，表后读数不能小于或等于表前')
    meter_pct=(meter-tr.liters)/tr.liters*100;vessel_pct=(data.vessel_received_liters-tr.liters)/tr.liters*100
    state='variance' if max(abs(meter_pct),abs(vessel_pct))>1 else 'matched'
    x=LoadingReconciliation(**data.model_dump(),meter_liters=meter,meter_variance_pct=meter_pct.quantize(Decimal('.0001')),vessel_variance_pct=vessel_pct.quantize(Decimal('.0001')),tolerance_pct=1,investigation='',state=state,transfer_snapshot=transfer_view(s,tr));s.add(x);s.flush();audit(s,u,'loading_reconciled',tr.code+' / '+state);return recon_view(s,x)
def investigate(s,id,data,u):
    x=get(s,LoadingReconciliation,id,True)
    if x.state=='closed':raise HTTPException(409,'主管已结案，不可覆盖调查依据')
    x.investigation=data.investigation;audit(s,u,'loading_investigated',str(x.transfer_id));return recon_view(s,x)
def close(s,id,u):
    x=get(s,LoadingReconciliation,id,True)
    if x.state=='closed':raise HTTPException(409,'对账已结案，不可重复签结')
    if x.state=='variance' and len(x.investigation.strip())<8:raise HTTPException(409,'表计或船收偏差超过1%，须补调查依据再由主管结案')
    from .harbor_service import complete_resources
    complete_resources(s,x.transfer_id,u,'调拨计量对账主管结案，完成管线与泊位交接')
    x.state='closed';x.closed_by=u['email'];x.closure_snapshot={**obj(x),'closure_snapshot':None,'at':now()}
    audit(s,u,'loading_closed',str(x.transfer_id));return recon_view(s,x)

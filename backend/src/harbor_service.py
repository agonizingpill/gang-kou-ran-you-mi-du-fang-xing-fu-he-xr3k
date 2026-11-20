from datetime import datetime,timezone,date,timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from .models import Transfer
from .harbor_models import FuelLine,LinePermit,Berth,VesselWindow,RetainedSample,RetestOrder
from .transfer_service import obj,get,audit,transfer_view
from .constants import GRADES

def stamp(x):return (x.replace(tzinfo=ZoneInfo('Asia/Shanghai'))if x.tzinfo is None else x).astimezone(timezone.utc)
def now():return datetime.now(timezone.utc).isoformat()
def permit_view(s,x):return {**obj(x),'transfer_code':get(s,Transfer,x.transfer_id).code,'line_code':get(s,FuelLine,x.line_id).code}
def window_view(s,x):return {**obj(x),'transfer_code':get(s,Transfer,x.transfer_id).code,'berth_code':get(s,Berth,x.berth_id).code}
def retained_view(s,x):return {**obj(x),'transfer_code':get(s,Transfer,x.transfer_id).code,'expired':date.fromisoformat(x.storage_until)<datetime.now(timezone.utc).date()}
def order_view(s,x):return {**obj(x),'seal_code':get(s,RetainedSample,x.retained_id).seal_code}
def requested(s,id):
    tr=get(s,Transfer,id,True)
    if tr.status!='requested':raise HTTPException(409,'仅待放行调拨可配置管线或受油窗口，已放行历史不改')
    return tr
def create_permit(s,p,u):
    tr=requested(s,p.transfer_id);get(s,FuelLine,p.line_id)
    if s.scalar(select(LinePermit.id).where(LinePermit.transfer_id==tr.id)):raise HTTPException(409,'调拨已有管线许可单，请修订原计划')
    x=LinePermit(**p.model_dump(),state='planned');s.add(x);s.flush();audit(s,u,'permit_planned',tr.code);return permit_view(s,x)
def revise_permit(s,id,p,u):
    candidate=get(s,LinePermit,id);requested(s,candidate.transfer_id);x=get(s,LinePermit,id,True)
    if x.state!='planned':raise HTTPException(409,'许可已批准，不可修改清线证据')
    get(s,FuelLine,p.line_id)
    for k,v in p.model_dump().items():setattr(x,k,v)
    return permit_view(s,x)
def check_line(s,tr,x,line):
    if line.allowed_grade!=tr.grade_snapshot or x.clean_grade!=tr.grade_snapshot:raise HTTPException(409,'管线允许等级或清线等级与调拨油品不符')
    if x.flush_liters<line.min_flush_liters:raise HTTPException(409,'清线量不足管线最低冲洗量，不能许可')
    if line.state!='idle':raise HTTPException(409,'管线正在占用，不能许可或放行第二单')
def approve_permit(s,id,u):
    candidate=get(s,LinePermit,id);tr=requested(s,candidate.transfer_id);x=get(s,LinePermit,id,True);line=get(s,FuelLine,x.line_id,True)
    if x.state!='planned':raise HTTPException(409,'仅计划许可可批准，不可重复')
    check_line(s,tr,x,line);x.state='permitted';x.approved_by=u['email'];audit(s,u,'line_permitted',tr.code);return permit_view(s,x)
def overlap(s,berth,start,end,exclude=None):
    for x in s.scalars(select(VesselWindow).where(VesselWindow.berth_id==berth.id,VesselWindow.state.in_(['confirmed','in_use','completed'])).execution_options(populate_existing=True)):
        if x.id!=exclude and datetime.fromisoformat(x.starts_at)<end and datetime.fromisoformat(x.ends_at)>start:raise HTTPException(409,'同泊位受油时间与已确认预约重叠')
def window_values(s,tr,p):
    berth=get(s,Berth,p.berth_id,True);start,end=stamp(p.starts_at),stamp(p.ends_at)
    if end<=start:raise HTTPException(409,'受油结束时间须晚于开始')
    if not berth.active:raise HTTPException(409,'泊位已停用')
    if p.draft>berth.max_draft:raise HTTPException(409,'船舶吃水超过泊位上限')
    return berth,start,end
def create_window(s,p,u):
    tr=requested(s,p.transfer_id)
    if s.scalar(select(VesselWindow.id).where(VesselWindow.transfer_id==tr.id)):raise HTTPException(409,'调拨已有受油窗口，不能重复预约')
    berth,start,end=window_values(s,tr,p);x=VesselWindow(transfer_id=tr.id,berth_id=berth.id,starts_at=start.isoformat(),ends_at=end.isoformat(),draft=p.draft,state='planned');s.add(x);s.flush();audit(s,u,'window_planned',tr.code);return window_view(s,x)
def confirm_window(s,id,u):
    candidate=get(s,VesselWindow,id);tr=requested(s,candidate.transfer_id);berth=get(s,Berth,candidate.berth_id,True);x=get(s,VesselWindow,id,True)
    if x.state!='planned':raise HTTPException(409,'只可确认计划受油窗口，不能重复')
    if not berth.active or x.draft>berth.max_draft:raise HTTPException(409,'泊位状态或吃水条件不满足')
    if datetime.fromisoformat(x.ends_at)<=datetime.now(timezone.utc):raise HTTPException(409,'受油预约已过期，不能确认')
    overlap(s,berth,datetime.fromisoformat(x.starts_at),datetime.fromisoformat(x.ends_at),x.id);x.state='confirmed';x.confirmed_by=u['email'];audit(s,u,'window_confirmed',tr.code);return window_view(s,x)
def occupy_for_release(s,tr,u):
    x=s.scalar(select(LinePermit).where(LinePermit.transfer_id==tr.id).with_for_update().execution_options(populate_existing=True))
    if not x or x.state!='permitted':raise HTTPException(409,'新放行须有主管批准的清线管线许可')
    line=get(s,FuelLine,x.line_id,True);check_line(s,tr,x,line)
    w=s.scalar(select(VesselWindow).where(VesselWindow.transfer_id==tr.id).with_for_update().execution_options(populate_existing=True))
    if not w or w.state!='confirmed':raise HTTPException(409,'新放行须有主管确认的船舶受油窗口')
    berth=get(s,Berth,w.berth_id,True)
    if not berth.active or w.draft>berth.max_draft or datetime.fromisoformat(w.ends_at)<=datetime.now(timezone.utc):raise HTTPException(409,'受油泊位/吃水或预约有效期不满足')
    minutes=Decimal(str((datetime.fromisoformat(w.ends_at)-datetime.fromisoformat(w.starts_at)).total_seconds()/60))
    if tr.liters>minutes*line.capacity_lpm:raise HTTPException(409,'受油窗口不足以按管线额定流量完成调拨')
    x.state='in_use';line.state='busy';w.state='in_use'
    x.release_snapshot={**permit_view(s,x),'release_snapshot':None,'line_grade':line.allowed_grade,'capacity_lpm':float(line.capacity_lpm),'min_flush_liters':float(line.min_flush_liters),'at':now()}
    w.release_snapshot={**window_view(s,w),'release_snapshot':None,'max_draft':float(berth.max_draft),'vessel':tr.vessel,'at':now()};audit(s,u,'harbor_occupied',tr.code)
def complete_resources(s,transfer_id,u,note,strict=False):
    # Existing released records without V3 permits require no retroactive mutation.
    x=s.scalar(select(LinePermit).where(LinePermit.transfer_id==transfer_id).with_for_update().execution_options(populate_existing=True))
    if not x:
        if strict:raise HTTPException(409,'该历史调拨无V3占线许可，无需重复释放')
        return
    if x.state!='in_use':
        if strict:raise HTTPException(409,'管线未占用或已释放，不能重复完工')
        return
    line=get(s,FuelLine,x.line_id,True);w=s.scalar(select(VesselWindow).where(VesselWindow.transfer_id==transfer_id).with_for_update().execution_options(populate_existing=True))
    x.state='completed';x.completion_note=note;line.state='idle'
    if w and w.state=='in_use':w.state='completed'
    audit(s,u,'harbor_completed',str(transfer_id)+' / '+note)
def complete_permit(s,id,p,u):
    candidate=get(s,LinePermit,id);get(s,Transfer,candidate.transfer_id,True)
    complete_resources(s,candidate.transfer_id,u,p.completion_note,True);return permit_view(s,get(s,LinePermit,id))
def create_retained(s,p,u):
    tr=get(s,Transfer,p.transfer_id,True)
    if tr.status!='released':raise HTTPException(409,'仅已放行调拨可封存留样')
    if s.scalar(select(RetainedSample.id).where(RetainedSample.transfer_id==tr.id)):raise HTTPException(409,'该调拨已有封存留样，不可重复')
    today=datetime.now(timezone.utc).date()
    if p.storage_until<today+timedelta(days=90):raise HTTPException(409,'留样保管期须从登记日起至少90天')
    x=RetainedSample(transfer_id=tr.id,seal_code=p.seal_code,retained_ml=p.retained_ml,storage_until=p.storage_until.isoformat(),state='sealed',transfer_snapshot=transfer_view(s,tr));s.add(x);s.flush();audit(s,u,'retained_sealed',x.seal_code);return retained_view(s,x)
def commission(s,p,u):
    retained=get(s,RetainedSample,p.retained_id,True)
    if retained.state!='sealed' or date.fromisoformat(retained.storage_until)<datetime.now(timezone.utc).date():raise HTTPException(409,'留样已过保管期或未封存，不能委托复检')
    if s.scalar(select(RetestOrder.id).where(RetestOrder.retained_id==retained.id,RetestOrder.state!='closed')):raise HTTPException(409,'同封样已有未结案复检委托，不可重复')
    x=RetestOrder(**p.model_dump(),state='commissioned',commissioned_by=u['email']);s.add(x);s.flush();audit(s,u,'retest_commissioned',retained.seal_code);return order_view(s,x)
def record_result(s,id,p,u):
    x=get(s,RetestOrder,id,True)
    if x.state!='commissioned':raise HTTPException(409,'只可给已委托未报告检验登记结果，不可覆盖')
    retained=get(s,RetainedSample,x.retained_id);spec=GRADES[retained.transfer_snapshot['grade_snapshot']]
    x.result_density=p.result_density;x.result_note=p.result_note;x.out_of_spec=not spec['density_min']<=p.result_density<=spec['density_max'];x.state='reported';audit(s,u,'retest_reported',str(id));return order_view(s,x)
def close_order(s,id,p,u):
    x=get(s,RetestOrder,id,True)
    if x.state!='reported':raise HTTPException(409,'复检须先报告，且不可重复结案')
    if x.out_of_spec and len(p.closure_note.strip())<8:raise HTTPException(409,'委托复检密度超等级规格，主管结案须填写处置依据')
    x.closure_note=p.closure_note;x.state='closed';x.result_snapshot={**obj(x),'result_snapshot':None,'closed_by':u['email'],'at':now()};audit(s,u,'retest_closed',str(id));return order_view(s,x)

from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import Session
from .security import current,allow
from .transfer_service import obj,audit
from .harbor_models import FuelLine,LinePermit,Berth,VesselWindow,RetainedSample,RetestOrder
from .harbor_schemas import LineInput,PermitInput,PermitValues,Completion,BerthInput,WindowInput,RetainedInput,RetestInput,RetestResult,RetestClose
from . import harbor_service as svc
router=APIRouter()
@router.get('/fuel-lines')
def lines(u=Depends(current)):
    with Session()as s:return [obj(x)for x in s.scalars(select(FuelLine).order_by(FuelLine.id))]
@router.post('/fuel-lines')
def line(p:LineInput,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:
        x=FuelLine(**p.model_dump(),state='idle');s.add(x);s.flush();audit(s,u,'line_registered',x.code);return obj(x)
@router.get('/line-permits')
def permits(u=Depends(current)):
    with Session()as s:return [svc.permit_view(s,x)for x in s.scalars(select(LinePermit).order_by(LinePermit.id.desc()))]
@router.post('/line-permits')
def permit(p:PermitInput,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin()as s:return svc.create_permit(s,p,u)
@router.patch('/line-permits/{id}')
def revise(id:int,p:PermitValues,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin()as s:return svc.revise_permit(s,id,p,u)
@router.post('/line-permits/{id}/approve')
def approve(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:return svc.approve_permit(s,id,u)
@router.post('/line-permits/{id}/complete')
def complete(id:int,p:Completion,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:return svc.complete_permit(s,id,p,u)
@router.get('/berths')
def berths(u=Depends(current)):
    with Session()as s:return [obj(x)for x in s.scalars(select(Berth).order_by(Berth.id))]
@router.post('/berths')
def berth(p:BerthInput,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:
        x=Berth(**p.model_dump(),active=True);s.add(x);s.flush();audit(s,u,'berth_registered',x.code);return obj(x)
@router.get('/vessel-windows')
def windows(u=Depends(current)):
    with Session()as s:return [svc.window_view(s,x)for x in s.scalars(select(VesselWindow).order_by(VesselWindow.id.desc()))]
@router.post('/vessel-windows')
def window(p:WindowInput,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin()as s:return svc.create_window(s,p,u)
@router.post('/vessel-windows/{id}/confirm')
def confirm(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:return svc.confirm_window(s,id,u)
@router.get('/retained-samples')
def retained(u=Depends(current)):
    with Session()as s:return [svc.retained_view(s,x)for x in s.scalars(select(RetainedSample).order_by(RetainedSample.id.desc()))]
@router.post('/retained-samples')
def retain(p:RetainedInput,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin()as s:return svc.create_retained(s,p,u)
@router.get('/retest-orders')
def orders(u=Depends(current)):
    with Session()as s:return [svc.order_view(s,x)for x in s.scalars(select(RetestOrder).order_by(RetestOrder.id.desc()))]
@router.post('/retest-orders')
def commission(p:RetestInput,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:return svc.commission(s,p,u)
@router.post('/retest-orders/{id}/result')
def result(id:int,p:RetestResult,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin()as s:return svc.record_result(s,id,p,u)
@router.post('/retest-orders/{id}/close')
def close(id:int,p:RetestClose,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:return svc.close_order(s,id,p,u)

from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from .database import Session
from .security import current,allow
from .receipt_models import TankCapacity,TankReceipt,LoadingReconciliation
from .receipt_schemas import CapacityIn,ReceiptIn,ReceiptValues,ReconciliationIn,Investigation
from .transfer_service import audit,get
from . import receipt_service as svc
router=APIRouter()
@router.get('/tank-capacities')
def capacities(u=Depends(current)):
    with Session() as s:return [svc.capacity_view(s,x)for x in s.scalars(select(TankCapacity).order_by(TankCapacity.id))]
@router.post('/tank-capacities')
def baseline(p:CapacityIn,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return svc.capacity(s,p,u)
@router.get('/tank-receipts')
def receipts(u=Depends(current)):
    with Session() as s:return [svc.receipt_view(s,x)for x in s.scalars(select(TankReceipt).order_by(TankReceipt.id.desc()))]
@router.post('/tank-receipts')
def create(p:ReceiptIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:
        from .models import Tank
        get(s,Tank,p.tank_id);x=TankReceipt(**p.model_dump(),state='planned');s.add(x);s.flush();audit(s,u,'receipt_planned',x.code);return svc.receipt_view(s,x)
@router.patch('/tank-receipts/{id}')
def revise(id:int,p:ReceiptValues,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:
        x=get(s,TankReceipt,id,True)
        if x.state!='planned':raise HTTPException(409,'化验已确认或已入罐，收油测值不可改写')
        for k,v in p.model_dump().items():setattr(x,k,v)
        audit(s,u,'receipt_revised',x.code);return svc.receipt_view(s,x)
@router.post('/tank-receipts/{id}/inspect')
def inspect(id:int,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:return svc.inspect(s,id,u)
@router.post('/tank-receipts/{id}/receive')
def receive(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return svc.receive(s,id,u)
@router.get('/loading-reconciliations')
def reconciliations(u=Depends(current)):
    with Session() as s:return [svc.recon_view(s,x)for x in s.scalars(select(LoadingReconciliation).order_by(LoadingReconciliation.id.desc()))]
@router.post('/loading-reconciliations')
def reconcile(p:ReconciliationIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:return svc.reconciliation(s,p,u)
@router.patch('/loading-reconciliations/{id}/investigation')
def investigate(id:int,p:Investigation,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:return svc.investigate(s,id,p,u)
@router.post('/loading-reconciliations/{id}/close')
def close(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return svc.close(s,id,u)

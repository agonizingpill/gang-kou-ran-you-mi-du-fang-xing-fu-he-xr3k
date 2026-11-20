from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import Session
from .security import current,allow
from .transfer_service import get,audit
from .blind_models import BlindSession,BlindSample
from .blind_schemas import SessionIn,SampleIn,ReadingIn
from . import blind_service as svc
router=APIRouter()

@router.get('/blind/sessions')
def sessions(u=Depends(current)):
    with Session()as s:
        return [svc.session_view(s,x,u)for x in s.scalars(select(BlindSession).order_by(BlindSession.id.desc()))]
@router.post('/blind/sessions')
def create_session(d:SessionIn,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:
        x=svc.create_session(s,d,u);return svc.session_view(s,x,u)
@router.get('/blind/sessions/{id}')
def one_session(id:int,u=Depends(current)):
    with Session()as s:return svc.session_view(s,get(s,BlindSession,id),u)
@router.post('/blind/sessions/{id}/samples')
def add_sample(id:int,d:SampleIn,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:
        x=svc.add_sample(s,id,d,u);return svc.session_view(s,get(s,BlindSession,id),u)
@router.post('/blind/sessions/{id}/seal')
def seal(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:
        svc.seal(s,id,u);return svc.session_view(s,get(s,BlindSession,id),u)
@router.post('/blind/sessions/{id}/readings')
def reading(id:int,d:ReadingIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin()as s:
        r=svc.submit_reading(s,id,d,u)
        return {'id':r.id,'blind_code':d.blind_code,'density_read':float(r.density_read),
                'late':r.late,'accepted_at':r.accepted_at,'attempts':r.attempts}
@router.post('/blind/sessions/{id}/score')
def score(id:int,u=Depends(current)):
    allow(u,'admin')
    svc.run_scoring(id,u)
    with Session()as s:return svc.session_view(s,get(s,BlindSession,id),u)
@router.post('/blind/sessions/{id}/reveal')
def reveal(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin()as s:
        svc.reveal(s,id,u);return svc.session_view(s,get(s,BlindSession,id),u)

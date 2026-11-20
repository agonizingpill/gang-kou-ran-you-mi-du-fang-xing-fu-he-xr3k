import os,hmac,logging
from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select,text
from sqlalchemy.exc import IntegrityError
from redis import Redis
from .database import Base,engine,Session
from .models import User,Tank,FuelSample,Transfer,Audit
from .schemas import Login,TankIn,TankState,SampleIn,RetestIn,TransferIn
from .security import current,allow,password_hash,token_for
from .transfer_service import obj,get,audit,sample_view,transfer_view,retest,request_transfer,release
from .constants import GRADES
from .middlewares import RequestTrace,Recovery
from scripts.seed_demo import seed
logging.basicConfig(level=logging.INFO)
r=Redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    if os.getenv('SEED_DEMO','true')=='true':
        try:seed()
        except Exception:logging.exception('seed failed')
    yield
app=FastAPI(title='澄港 · 油样放行簿',lifespan=lifespan);app.add_middleware(RequestTrace);app.add_middleware(Recovery)
from .receipt_routes import router as receipt_router
app.include_router(receipt_router)
from .harbor_routes import router as harbor_router
app.include_router(harbor_router)
@app.exception_handler(IntegrityError)
async def duplicate(request,e):return JSONResponse({'detail':'编号已存在或关联记录不合法'},status_code=409)
@app.get('/health')
def health():
    with Session() as s:s.execute(text('SELECT 1'))
    return {'status':'ok','redis':r.ping()}
@app.post('/auth/login')
def login(d:Login):
    with Session() as s:
        u=s.scalar(select(User).where(User.email==d.email))
        if not u or not hmac.compare_digest(u.password,password_hash(d.password)):raise HTTPException(401,'账号或密码不正确')
        return {'token':token_for(u),'role':u.role,'email':u.email}
@app.get('/tanks')
def tanks(u=Depends(current)):
    with Session() as s:return [obj(x)for x in s.scalars(select(Tank).order_by(Tank.id))]
@app.post('/tanks')
def add_tank(d:TankIn,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:
        t=Tank(**d.model_dump(),status='active');s.add(t);s.flush();audit(s,u,'tank_registered',t.code);return obj(t)
@app.patch('/tanks/{id}/status')
def tank_status(id:int,d:TankState,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:
        t=get(s,Tank,id,True);t.status=d.status;audit(s,u,'tank_state',f'{t.code}:{t.status}');return obj(t)
@app.get('/grades')
def grades(u=Depends(current)):return GRADES
@app.get('/samples')
def samples(u=Depends(current)):
    with Session() as s:return [sample_view(s,x)for x in s.scalars(select(FuelSample).where(FuelSample.reference==False).order_by(FuelSample.id.desc()))]
@app.post('/samples')
def add_sample(d:SampleIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:
        get(s,Tank,d.tank_id);x=FuelSample(**d.model_dump(),status='received',reference=False,evidence='',retest_note='');s.add(x);s.flush();audit(s,u,'sample_received',x.code);return sample_view(s,x)
@app.post('/samples/{id}/compare')
def compare_sample(id:int,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:
        x=get(s,FuelSample,id,True)
        if x.reference or x.status not in ['received','failed']:raise HTTPException(409,'该样品已比对或不可重新计算')
        x.status='queued';audit(s,u,'sample_compared',x.code)
    r.rpush('density-check',id);return {'status':'queued'}
@app.put('/samples/{id}/retest')
def retest_sample(id:int,d:RetestIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:return retest(s,get(s,FuelSample,id,True),d,u)
@app.get('/transfers')
def transfers(u=Depends(current)):
    with Session() as s:return [transfer_view(s,x)for x in s.scalars(select(Transfer).order_by(Transfer.id.desc()))]
@app.post('/transfers')
def new_transfer(d:TransferIn,u=Depends(current)):
    allow(u,'admin','chemist')
    with Session.begin() as s:return request_transfer(s,get(s,FuelSample,d.sample_id,True),d,u)
@app.post('/transfers/{id}/release')
def release_transfer(id:int,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return release(s,get(s,Transfer,id,True),u)
@app.get('/audit')
def audit_logs(u=Depends(current)):
    with Session() as s:return [obj(x)for x in s.scalars(select(Audit).order_by(Audit.id.desc()).limit(35))]

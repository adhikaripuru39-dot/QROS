"""Database-backed pipeline APIs. No endpoint opens a broker connection."""
from datetime import datetime,timezone
from pathlib import Path
import json,uuid
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from sqlalchemy import select
from qros.audit.log import record
from qros.db.models import BackgroundJob,OrderLedger,Strategy,SystemState
from qros.research.registry import registry_dicts
from qros.services.readiness import readiness
from .deps import get_db,get_app_settings,require_owner

router=APIRouter(prefix='/api')

@router.get('/system/readiness')
def get_readiness(db=Depends(get_db),settings=Depends(get_app_settings),_=Depends(require_owner)):
    return readiness(db,settings)

@router.get('/execution/orders')
def get_orders(limit:int=Query(100,ge=1,le=1000),db=Depends(get_db),_=Depends(require_owner)):
    return [{'client_order_id':r.client_order_id,'strategy_id':r.strategy_id,'symbol':r.symbol,'mode':r.mode,'status':r.status,'decision':r.decision,'result':r.result,'created_at':r.created_at.isoformat()} for r in db.execute(select(OrderLedger).order_by(OrderLedger.created_at.desc()).limit(limit)).scalars()]

@router.get('/data/datasets')
def datasets(settings=Depends(get_app_settings),_=Depends(require_owner)):
    root=settings.data_dir/'history';result=[]
    for path in sorted(root.glob('*/manifest.json'),reverse=True)[:500]:
        try:
            raw=json.loads(path.read_text(encoding='utf-8'));result.append(raw)
        except (OSError,ValueError):continue
    return result

@router.get('/research/hypotheses')
def hypotheses(_=Depends(require_owner)):
    return registry_dicts()

@router.get('/research/jobs')
def jobs(limit:int=Query(100,ge=1,le=500),db=Depends(get_db),_=Depends(require_owner)):
    return [{'id':r.id,'kind':r.kind,'status':r.status,'payload':r.payload,'result':r.result,'error':r.error,'created_at':r.created_at.isoformat()} for r in db.execute(select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(limit)).scalars()]

class ResearchJobIn(BaseModel):
    symbol:str=Field(pattern=r'^[A-Za-z0-9_.-]{3,32}$')
    timeframe:str=Field(default='M15',pattern=r'^(M1|M5|M15|H1|H4|D1)$')
    days:int=Field(default=180,ge=1,le=3650)
    finalize_oos:bool=False
    dataset_version:str|None=None
    candidate_ids:list[str]|None=None

@router.post('/research/jobs',status_code=202)
def start_job(body:ResearchJobIn,db=Depends(get_db),actor=Depends(require_owner)):
    if body.finalize_oos:
        raise HTTPException(422,'OOS consumption requires a frozen, eligible validation cohort; use the research worker finalize command after review')
    job=BackgroundJob(id=uuid.uuid4().hex,kind='research',status='queued',payload=body.model_dump(),result={})
    db.add(job);record(db,actor,'research.job.queued',{'job_id':job.id,'payload':job.payload})
    return {'id':job.id,'status':job.status,'note':'Persisted. The independent research worker will process this job.'}

class RegisterStrategy(BaseModel):
    hypothesis_id:str
    symbol:str=Field(pattern=r'^[A-Za-z0-9_.-]{3,32}$')
    timeframe_seconds:int=Field(default=900,ge=60,le=86400)

@router.post('/strategies/register',status_code=201)
def register_strategy(body:RegisterStrategy,db=Depends(get_db),actor=Depends(require_owner)):
    registry={s['id']:s for s in registry_dicts()}
    if body.hypothesis_id not in registry:raise HTTPException(422,'Unknown hypothesis')
    sid=f'{body.hypothesis_id}_{body.symbol}_{body.timeframe_seconds}'
    if db.get(Strategy,sid):raise HTTPException(409,'Strategy already registered')
    spec=registry[body.hypothesis_id]
    row=Strategy(id=sid,hypothesis_id=body.hypothesis_id,family=spec['family'],name=f"{spec['family']} / {body.symbol}",status='IDEA',spec={'hypothesis':spec,'runtime':{'symbol':body.symbol,'timeframe_seconds':body.timeframe_seconds,'stop_atr_multiple':2,'target_atr_multiple':3}})
    db.add(row);record(db,actor,'strategy.registered',{'strategy_id':sid})
    return {'id':sid,'status':'IDEA'}


@router.get('/system/news')
def get_news(db=Depends(get_db),settings=Depends(get_app_settings),_=Depends(require_owner)):
    from qros.services.news_status import news_status
    return news_status(db,settings)

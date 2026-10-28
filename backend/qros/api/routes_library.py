"""Research library and immutable weekly review snapshots; no execution actions."""
from datetime import date, datetime, timezone
from typing import Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from qros.db.models import Strategy, SystemState, BackgroundJob
from qros.research.library import library
from qros.reporting.weekly import weekly_report
from qros.audit.log import record
from qros.services import settings_store as st
from .deps import get_db, require_owner

router = APIRouter(prefix='/api/library')
TF = {'M15':900,'H1':3600,'H4':14400,'D1':86400}

def strategy(db, sid):
    row = db.get(Strategy,sid)
    if row is None: raise HTTPException(404,'Strategy not found')
    return row

class RuntimeIn(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)
    symbol: str = Field(pattern=r'^[A-Za-z0-9_.-]{3,32}$')
    timeframe: Literal['M15','H1','H4','D1'] = 'H1'
    atr_period: int = Field(default=14,ge=5,le=50)
    stop_atr_multiple: float = Field(default=2,ge=.5,le=10)
    target_atr_multiple: float = Field(default=3,ge=.5,le=10)

def runtime(db, body):
    if body.symbol not in {i.symbol for i in st.instruments(db)}:
        raise HTTPException(422,'Select an instrument configured on this broker')
    return {'symbol':body.symbol,'timeframe_seconds':TF[body.timeframe],
            'atr_period':body.atr_period,'stop_atr_multiple':body.stop_atr_multiple,
            'target_atr_multiple':body.target_atr_multiple}

@router.get('')
def get_library(_=Depends(require_owner)):
    return library()

class CreateIn(RuntimeIn):
    hypothesis_id: str

@router.post('/versions',status_code=201)
def create(body:CreateIn,db=Depends(get_db),actor=Depends(require_owner)):
    templates={s['id']:s for s in library()}
    if body.hypothesis_id not in templates: raise HTTPException(422,'Unknown library template')
    spec=templates[body.hypothesis_id]
    sid='lib_'+uuid.uuid4().hex
    row=Strategy(id=sid,hypothesis_id=body.hypothesis_id,family=spec['family'],
        name=f"{spec['title']} / {body.symbol}",status='IDEA',spec={
            'library_version':1,'revision':1,'hypothesis':spec,'runtime':runtime(db,body)})
    db.add(row);record(db,actor,'library.version.created',{'strategy_id':sid,'hypothesis':body.hypothesis_id})
    return {'id':sid,'status':'IDEA','spec':row.spec}

class ForkIn(RuntimeIn):
    reason: str = Field(min_length=10,max_length=2000)

@router.post('/versions/{sid}/fork',status_code=201)
def fork(sid:str,body:ForkIn,db=Depends(get_db),actor=Depends(require_owner)):
    parent=strategy(db,sid)
    if parent.hypothesis_id not in {s['id'] for s in library()}: raise HTTPException(422,'Choose a library strategy')
    child_id='lib_'+uuid.uuid4().hex
    spec={'library_version':1,'revision':parent.spec.get('revision',1)+1,'parent_id':sid,
        'change_reason':body.reason,'hypothesis':parent.spec['hypothesis'],'runtime':runtime(db,body)}
    db.add(Strategy(id=child_id,hypothesis_id=parent.hypothesis_id,family=parent.family,
        name=f"{parent.family} / {body.symbol} / v{spec['revision']}",status='IDEA',spec=spec))
    record(db,actor,'library.version.forked',{'parent_id':sid,'strategy_id':child_id,'reason':body.reason,'runtime':spec['runtime']})
    return {'id':child_id,'status':'IDEA','spec':spec}

@router.post('/versions/{sid}/research',status_code=202)
def queue(sid:str,db=Depends(get_db),actor=Depends(require_owner)):
    row=strategy(db,sid)
    if not row.spec.get('library_version'):raise HTTPException(422,'Choose a library version')
    cfg=row.spec['runtime'];tf={v:k for k,v in TF.items()}[cfg['timeframe_seconds']]
    payload={'strategy_id':sid,'symbol':cfg['symbol'],'timeframe':tf,'days':180,
             'candidate_ids':[row.hypothesis_id],'runtime_spec':cfg,'finalize_oos':False}
    job=BackgroundJob(id=uuid.uuid4().hex,kind='research',status='queued',payload=payload,result={})
    db.add(job);record(db,actor,'library.research.queued',{'strategy_id':sid,'job_id':job.id})
    return {'id':job.id,'status':'queued'}

@router.get('/versions/{sid}/weekly')
def weekly(sid:str,week_start:date,mode:Literal['paper','demo','live']='paper',
           db=Depends(get_db),_=Depends(require_owner)):
    try:return weekly_report(db,strategy(db,sid),week_start,mode)
    except ValueError as exc:raise HTTPException(422,str(exc))

class ReviewIn(BaseModel):
    week_start: date
    mode: Literal['paper','demo','live'] = 'paper'
    notes: str = Field(min_length=10,max_length=10000)
    decision: Literal['hold','collect_more_data','research_change','retire_candidate']
    next_hypothesis: str = Field(default='',max_length=3000)
    snapshot_hash: str = Field(pattern=r'^[a-f0-9]{64}$')

@router.post('/versions/{sid}/reviews',status_code=201)
def review(sid:str,body:ReviewIn,db=Depends(get_db),actor=Depends(require_owner)):
    try:snapshot=weekly_report(db,strategy(db,sid),body.week_start,body.mode)
    except ValueError as exc:raise HTTPException(422,str(exc))
    if snapshot['snapshot_hash']!=body.snapshot_hash:raise HTTPException(409,'Observations changed; refresh the report before saving')
    key='weekly_review:'+uuid.uuid4().hex
    data={'id':key,'strategy_id':sid,**body.model_dump(mode='json'),'snapshot':snapshot,
          'saved_at':datetime.now(timezone.utc).isoformat(),'actor':actor}
    db.add(SystemState(key=key,data=data))
    record(db,actor,'strategy.weekly_review.saved',{'review_id':key,'strategy_id':sid,'snapshot_hash':body.snapshot_hash,'decision':body.decision})
    return data

@router.get('/reviews')
def reviews(db=Depends(get_db),_=Depends(require_owner)):
    return [r.data for r in db.execute(select(SystemState).where(SystemState.key.like('weekly_review:%')).order_by(SystemState.updated_at.desc()).limit(200)).scalars()]

"""Idempotently introduce five research baselines; never activate execution."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from qros.config.settings import Settings
from qros.db.session import session_factory,session_scope
from qros.db.models import Strategy,BackgroundJob
from qros.research.library import library
from qros.audit.log import record

s=Settings()
with session_scope(session_factory(s.database_url)) as db:
    for template in library():
        symbol=template['suggested_symbols'][0]
        tf=template['default_timeframe'];seconds={'M15':900,'H1':3600}[tf]
        runtime={'symbol':symbol,'timeframe_seconds':seconds,**template['default_runtime']}
        sid=f"lib_v1_{template['id']}_{symbol}_{seconds}"
        if db.get(Strategy,sid) is None:
            db.add(Strategy(id=sid,hypothesis_id=template['id'],family=template['family'],
                name=f"{template['title']} / {symbol}",status='IDEA',spec={
                    'library_version':1,'revision':1,'hypothesis':template,'runtime':runtime}))
            record(db,'commissioning','library.version.created',{'strategy_id':sid,'hypothesis':template['id']})
        jid='baseline_'+sid
        if db.get(BackgroundJob,jid) is None:
            payload={'strategy_id':sid,'symbol':symbol,'timeframe':tf,'days':180,
                'candidate_ids':[template['id']],'runtime_spec':runtime,'finalize_oos':False}
            db.add(BackgroundJob(id=jid,kind='research',status='queued',payload=payload,result={}))
            record(db,'commissioning','library.research.queued',{'job_id':jid,'strategy_id':sid})
        print(sid,'IDEA / exploratory baseline queued or already recorded')

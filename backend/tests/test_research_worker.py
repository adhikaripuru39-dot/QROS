"""Archive/job fixtures only; never connects to a terminal or creates live data."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
import pandas as pd
import pytest
from sqlalchemy import select
from qros.config.settings import Settings
from qros.data.history import DatasetManifest
from qros.db.models import BackgroundJob,EvidenceReport,Experiment,Strategy,Trade,ServiceHeartbeat
from qros.db.session import session_scope
from qros.services.research_worker import ResearchWorker


@pytest.fixture
def worker(factory,tmp_path):
    root=tmp_path/'data';version='isolated_fixture'
    directory=root/'history'/version;directory.mkdir(parents=True)
    rows=[]
    for i in range(400):
        op=1.1+i*.00001;close=op+(.00005 if i%7<4 else -.00004)
        rows.append({'time':1700000000+i*900,'open':op,'high':max(op,close)+.00002,'low':min(op,close)-.00002,'close':close,'tick_volume':10,'spread':2,'real_volume':0})
    path=directory/'bars.parquet';pd.DataFrame(rows).to_parquet(path,index=False)
    manifest=DatasetManifest(version,'EURUSD','M15','2023-11-14T00:00:00+00:00','2023-11-20T00:00:00+00:00',datetime.now(timezone.utc).isoformat(),.00001,'bid',hashlib.sha256(path.read_bytes()).hexdigest(),400,None,None,{'provider':'isolated fixture'},{'invalid_rows':0,'duplicate_times':0,'out_of_range':0,'monotonic':True,'coverage_proven':False},timestamp_metadata={'historical_timestamp_verified':False})
    (directory/'manifest.json').write_text(json.dumps(asdict(manifest)),encoding='utf-8')
    readiness=tmp_path/'readiness';readiness.mkdir()
    specs={'observed_utc':datetime.now(timezone.utc).isoformat(),'leverage':100,'symbols':{'EURUSD':{'trade_contract_size':100000.,'trade_tick_size':.00001,'trade_tick_value_loss':1.,'volume_min':.01,'volume_max':50.,'volume_step':.01}}}
    (readiness/'broker_specs.json').write_text(json.dumps(specs),encoding='utf-8')
    settings=Settings(_env_file=None,data_dir=root,broker_adapter='none')
    return ResearchWorker(settings,factory,max_bars=400),manifest,path


def queue(worker,job_id='job',**changes):
    payload={'symbol':'EURUSD','timeframe':'M15','days':180,'candidate_ids':['momentum','time_drift'],'finalize_oos':False,**changes}
    with session_scope(worker.factory) as db:
        db.add(BackgroundJob(id=job_id,kind='research',status='queued',payload=payload,result={}))


def test_real_archive_runner_persists_truthful_failed_eligibility_without_promotion(worker):
    w,manifest,_=worker;queue(w)
    assert w.run_once()
    with session_scope(w.factory) as db:
        job=db.get(BackgroundJob,'job')
        assert job.status=='completed' and job.result['dataset_hash']==manifest.file_sha256
        assert job.result['rows']==400 and job.result['disabled_candidates']==['time_drift']
        assert not job.result['eligible'] and not job.result['oos_evaluated']
        report=db.execute(select(EvidenceReport)).scalar_one()
        assert not report.passed and report.content['provenance']['execution_costs_verified'] is False
        assert report.content['provenance']['timeframe_seconds'] is None
        assert report.content['binding']['source_dataset_hash']==manifest.file_sha256
        assert db.execute(select(Experiment)).scalar_one().kind=='backtest'
        assert db.execute(select(Strategy)).scalar_one().status=='IDEA'
        assert not list(db.execute(select(Trade)).scalars())
        heartbeat=db.get(ServiceHeartbeat,'research_worker')
        assert heartbeat and not heartbeat.broker_connected and heartbeat.broker_detail['read_only']


def test_corrupt_archive_fails_job_without_results(worker):
    w,_,path=worker;queue(w)
    path.write_bytes(b'corrupted fixture')
    w.run_once()
    with session_scope(w.factory) as db:
        job=db.get(BackgroundJob,'job')
        assert job.status=='failed' and 'hash mismatch' in job.error
        assert not list(db.execute(select(Experiment)).scalars())


def test_explicit_dataset_mismatch_never_silently_substitutes(worker):
    w,manifest,_=worker;queue(w,symbol='GBPUSD',dataset_version=manifest.version)
    w.run_once()
    with session_scope(w.factory) as db:
        job=db.get(BackgroundJob,'job')
        assert job.status=='failed' and 'does not match' in job.error


def test_worker_refuses_queued_oos_finalization(worker):
    w,_,_=worker;queue(w,finalize_oos=True)
    w.run_once()
    with session_scope(w.factory) as db:
        assert db.get(BackgroundJob,'job').status=='failed'
    assert not (w.settings.data_dir/'research_results'/'holdout_escrow.sqlite').exists()


def test_transactional_claim_and_interrupted_job_recovery(worker):
    w,_,_=worker;queue(w)
    other=ResearchWorker(w.settings,w.factory,max_bars=400)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda service:service.claim(),[w,other]))
    assert sum(x is not None for x in results)==1
    # Simulated locked restart after both claim attempts have stopped.
    w.recover_abandoned()
    with session_scope(w.factory) as db:
        job=db.get(BackgroundJob,'job')
        assert job.status=='failed' and 'not automatically retried' in job.error
    assert w.claim() is None


def test_library_job_binds_reports_and_exit_parameters_to_exact_version(worker):
    from qros.services.evidence import canonical_hash
    w,_,_=worker
    cfg={'symbol':'EURUSD','timeframe_seconds':900,'atr_period':20,'stop_atr_multiple':4.,'target_atr_multiple':6.}
    with session_scope(w.factory) as db:
        db.add(Strategy(id='lib_fixture',hypothesis_id='momentum',family='Trend',name='Fixture',status='IDEA',
            spec={'library_version':1,'runtime':cfg}))
    queue(w,strategy_id='lib_fixture',runtime_spec=cfg,candidate_ids=['momentum'])
    w.run_once()
    with session_scope(w.factory) as db:
        job=db.get(BackgroundJob,'job');assert job.status=='completed',job.error
        report=db.execute(select(EvidenceReport)).scalar_one()
        assert report.strategy_id=='lib_fixture' and report.content['runtime_spec_hash']==canonical_hash(cfg)
        assert db.execute(select(Experiment)).scalar_one().config['runtime_spec']==cfg
        assert db.get(Strategy,'lib_fixture').status=='IDEA'


def test_library_job_refuses_runtime_tampering_before_archive_use(worker):
    w,_,_=worker
    cfg={'symbol':'EURUSD','timeframe_seconds':900,'stop_atr_multiple':2.,'target_atr_multiple':3.}
    with session_scope(w.factory) as db:
        db.add(Strategy(id='lib_fixture',hypothesis_id='momentum',family='Trend',name='Fixture',status='IDEA',
            spec={'library_version':1,'runtime':cfg}))
    queue(w,strategy_id='lib_fixture',runtime_spec={**cfg,'target_atr_multiple':8.},candidate_ids=['momentum'])
    w.run_once()
    with session_scope(w.factory) as db:
        job=db.get(BackgroundJob,'job')
        assert job.status=='failed' and 'binding mismatch' in job.error
        assert not list(db.execute(select(Experiment)).scalars())

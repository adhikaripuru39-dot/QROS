"""Isolated worker tests; no MetaTrader5 module or real terminal is used."""
from datetime import datetime,timezone,timedelta
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from sqlalchemy import event
from qros.broker.base import AccountInfo,ConnectionStatus
from qros.config.settings import Settings
from qros.db.models import ServiceHeartbeat,SystemState,Setting
from qros.db.session import session_scope
from qros.services.data_worker import DataWorker
from qros.services.process_lock import ProcessLock

NOW=datetime(2026,10,23,17,tzinfo=timezone.utc)
ACCOUNT=AccountInfo('fixture','fixture-server',True,'USD',10000,10000,0,10000,100,True)


class FixtureAdapter:
    allow_orders=False
    def __init__(self,*,connects=True,advances=True,offset=10800,assert_no_tx=lambda:None):
        self.clock_verified=False;self._utc_offset_seconds=None;self._clock_samples=[]
        self._mt5=SimpleNamespace();self.connects=connects;self.advances=advances;self.offset=offset
        self.disconnected=False;self.assert_no_tx=assert_no_tx;self.quote_calls=0
    def connect(self):
        self.assert_no_tx();return ConnectionStatus(self.connects)
    def quote(self,symbol):
        self.assert_no_tx();self.quote_calls+=1
        if self.advances:
            self._clock_samples.append((symbol,self.offset,NOW))
            self._utc_offset_seconds=self.offset
            self.clock_verified=len(self._clock_samples)>=3 and len({x[0] for x in self._clock_samples})>=2
    def account_info(self):self.assert_no_tx();return ACCOUNT
    def disconnect(self):self.assert_no_tx();self.disconnected=True
    def send_market_order(self,*_):raise AssertionError('Data worker must never submit orders')


class FixtureStore:
    def __init__(self,path,assert_no_tx=lambda:None):self.root=path;self.calls=[];self.assert_no_tx=assert_no_tx
    def ingest_ticks(self,mt5,symbol,start,end,**kwargs):
        self.assert_no_tx();self.calls.append((symbol,start,end,kwargs))
        return {'version':'fixture-tick-'+symbol,'file_sha256':'a'*64,'quality':{'rows':2,'timestamp_verified':False,'coverage_proven':False}}


@pytest.fixture
def setup_worker(factory,tmp_path):
    settings=Settings(_env_file=None,data_dir=tmp_path/'data',broker_adapter='mt5',mt5_password='fixture-private-password',api_token='fixture-private-api-token')
    sessions=set()
    def remember(session,_):sessions.add(session)
    event.listen(factory,'after_transaction_create',remember)
    def assert_no_tx():assert not any(session.in_transaction() for session in sessions)
    made=[];sync_calls=[];tickstore=FixtureStore(settings.data_dir/'history',assert_no_tx)
    def adapter_factory():
        adapter=FixtureAdapter(assert_no_tx=assert_no_tx);made.append(adapter);return adapter
    def syncer(mt5,root,symbols,start,end,timeframes,**kwargs):
        assert_no_tx();sync_calls.append((symbols,start,end,timeframes,kwargs))
        return {'datasets':[{'symbol':s,'timeframe':tf,'version':'fixture-'+s+tf,'quality':{'timestamp_verified':False}}
                             for s in symbols for tf in timeframes],'errors':[],'report_path':'fixture-sync-report'}
    worker=DataWorker(settings,factory,adapter_factory=adapter_factory,syncer=syncer,clock=lambda:NOW,
        sleeper=lambda _:None,history_store=tickstore,calibration_attempts=3)
    return worker,made,sync_calls,tickstore


def test_continuous_cycle_recalibrates_each_time_preserves_archives_and_correct_windows(setup_worker):
    worker,made,sync_calls,ticks=setup_worker
    first=worker.run_once();first_bytes=Path(first['report_path']).read_bytes()
    second=worker.run_once()
    assert first['status']==second['status']=='completed'
    assert len(made)==2 and made[0] is not made[1] and all(a.disconnected for a in made)
    assert len(sync_calls)==2 and len(first['datasets'])==42 and len(first['ticks'])==7
    symbols,start,end,timeframes,kwargs=sync_calls[0]
    assert len(symbols)==7 and len(timeframes)==6 and end-start==timedelta(days=7)
    assert kwargs['request_axis_offset_seconds']==10800 and kwargs['include_ticks'] is False
    assert kwargs['timestamp_metadata']['historical_offset_schedule']==[]
    assert not kwargs['timestamp_metadata']['historical_timestamp_verified']
    assert all(end-start==timedelta(minutes=15) for _,start,end,_ in ticks.calls)
    assert first['report_path']!=second['report_path'] and Path(first['report_path']).read_bytes()==first_bytes
    with session_scope(worker.factory) as db:
        state=db.get(SystemState,'data_sync');heartbeat=db.get(ServiceHeartbeat,'data_worker')
        assert state.data['job_id']==second['job_id']
        assert heartbeat.broker_detail['read_only'] and not heartbeat.broker_connected
        assert heartbeat.broker_detail['fresh_current_clock_verified']
        assert heartbeat.last_error is None


def test_auth_failure_records_failed_cycle_without_sync_or_fake_clock(setup_worker):
    worker,made,sync_calls,ticks=setup_worker
    bad=FixtureAdapter(connects=False);worker.adapter_factory=lambda:bad
    result=worker.run_once()
    assert result['status']=='failed' and not sync_calls and not ticks.calls and bad.disconnected
    assert 'current_clock_calibration' not in result
    assert 'AUTHORIZATION_FAILED' in result['errors'][0]['error']
    with session_scope(worker.factory) as db:
        assert db.get(ServiceHeartbeat,'data_worker').last_error
        assert not db.get(ServiceHeartbeat,'data_worker').broker_detail['fresh_current_clock_verified']


def test_stale_quotes_never_reuse_previously_observed_offset(setup_worker):
    worker,made,sync_calls,ticks=setup_worker
    assert worker.run_once()['status']=='completed'
    worker.adapter_factory=lambda:FixtureAdapter(advances=False)
    result=worker.run_once()
    assert result['status']=='failed' and len(sync_calls)==1
    assert worker.current_offset is None and not worker.fresh_clock_verified
    assert 'NOT_FRESHLY_VERIFIED' in result['errors'][0]['error']


def test_fresh_dst_change_updates_selection_only_not_historical_mapping(setup_worker):
    worker,_,sync_calls,_=setup_worker
    assert worker.run_once()['current_clock_calibration']['request_axis_offset_seconds']==10800
    worker.adapter_factory=lambda:FixtureAdapter(offset=7200)
    report=worker.run_once()
    assert report['current_clock_calibration']['request_axis_offset_seconds']==7200
    assert sync_calls[-1][-1]['request_axis_offset_seconds']==7200
    assert not report['historical_timestamps_verified']


def test_disabled_symbols_excluded_and_order_capable_adapter_refused(setup_worker):
    worker,_,calls,_=setup_worker
    worker._symbols()
    with session_scope(worker.factory) as db:
        row=db.get(Setting,'instruments');data=dict(row.value)
        data['items']=[{**i,'enabled':i['symbol'] in {'EURUSD','GBPUSD'}} for i in data['items']];row.value=data
    assert worker.run_once()['configured_enabled_symbols']==['EURUSD','GBPUSD']
    capable=FixtureAdapter();capable.allow_orders=True;worker.adapter_factory=lambda:capable
    report=worker.run_once()
    assert report['status']=='failed' and len(calls)==1
    assert 'READ_ONLY_ADAPTER_REQUIRED' in report['errors'][0]['error']


def test_partial_capture_and_secrets_redacted_in_immutable_failure(setup_worker):
    worker,_,_,_=setup_worker
    def broken(*args,**kwargs):raise RuntimeError('fixture-private-password fixture-private-api-token')
    worker.syncer=broken
    result=worker.run_once()
    raw=Path(result['report_path']).read_text()
    assert result['status']=='failed' and '[redacted]' in raw
    assert 'fixture-private-password' not in raw and 'fixture-private-api-token' not in raw


def test_partial_source_capture_is_not_reported_as_completed(setup_worker):
    worker,_,_,_=setup_worker
    worker.syncer=lambda *args,**kwargs:{'datasets':[{'symbol':'EURUSD','version':'fixture'}],
        'errors':[{'symbol':'GBPUSD','error':'fixture source unavailable'}]}
    result=worker.run_once()
    assert result['status']=='partial' and result['errors'] and result['datasets']
    with session_scope(worker.factory) as db:
        assert db.get(ServiceHeartbeat,'data_worker').last_error=='SOURCE_CAPTURE_ERRORS_REVIEW_IMMUTABLE_REPORT'


def test_factory_reusing_previously_verified_adapter_is_rejected(setup_worker):
    worker,_,calls,_=setup_worker
    stale=FixtureAdapter();stale.clock_verified=True;stale._utc_offset_seconds=10800
    worker.adapter_factory=lambda:stale
    result=worker.run_once()
    assert result['status']=='failed' and not calls and stale.quote_calls==0
    assert 'FRESH_ADAPTER_CALIBRATION_REQUIRED' in result['errors'][0]['error']


def test_worker_lock_excludes_second_process(tmp_path):
    path=tmp_path/'data_worker.lock'
    with ProcessLock(path):
        with pytest.raises(RuntimeError):
            with ProcessLock(path):pass
    with ProcessLock(path):pass

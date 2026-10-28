"""Independent read-only MT5 archive worker with fresh per-cycle clock calibration.

No execution service, order request, or broker order method is used. Current clock
calibration selects raw request windows; historical UTC/DST remains unverified.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time
import uuid

from qros.audit.log import record
from qros.broker.mt5_adapter import MT5Adapter
from qros.config.settings import get_settings
from qros.data.history import HistoryStore,TIMEFRAMES
from qros.data.sync import sync_history
from qros.db.models import ServiceHeartbeat,SystemState
from qros.db.session import session_factory,session_scope
from qros.services.process_lock import ProcessLock
from qros.services import settings_store as st


def utcnow():return datetime.now(timezone.utc)


class DataSyncError(RuntimeError):pass


class DataWorker:
    def __init__(self,settings,factory=None,*,adapter_factory=None,syncer=sync_history,
                 clock=utcnow,sleeper=time.sleep,history_store=None,lookback_days=7,
                 tick_minutes=15,calibration_attempts=16,calibration_sleep=.5):
        if min(lookback_days,tick_minutes,calibration_attempts)<=0 or calibration_sleep<0:
            raise ValueError('Positive archive windows and calibration attempts required')
        self.settings=settings;self.factory=factory or session_factory(settings.database_url)
        self.clock=clock;self.sleeper=sleeper;self.syncer=syncer
        self.adapter_factory=adapter_factory or self._new_adapter
        self.store=history_store or HistoryStore(settings.data_dir/'history')
        self.lookback_days=lookback_days;self.tick_minutes=tick_minutes
        self.calibration_attempts=calibration_attempts;self.calibration_sleep=calibration_sleep
        self.started_at=clock();self.phase='starting';self.current_job=None;self.connected=False
        self.last_status=None;self.last_error=None;self.next_run_utc=None;self.current_offset=None
        self.fresh_clock_verified=False

    def _new_adapter(self):
        return MT5Adapter(path=self.settings.mt5_path,login=self.settings.mt5_login,
            password=self.settings.mt5_password.get_secret_value() if self.settings.mt5_password else None,
            server=self.settings.mt5_server,allow_orders=False)

    def _safe(self,value):
        message=str(value)
        for secret in (self.settings.mt5_password,self.settings.api_token):
            if secret and secret.get_secret_value():message=message.replace(secret.get_secret_value(),'[redacted]')
        if self.settings.mt5_login is not None:message=message.replace(str(self.settings.mt5_login),'[account]')
        return message[:1200]

    def heartbeat(self):
        now=self.clock()
        with session_scope(self.factory) as db:
            row=db.get(ServiceHeartbeat,'data_worker')
            if row is None:
                row=ServiceHeartbeat(service='data_worker',pid=os.getpid(),started_at=self.started_at,
                    last_beat=now,broker_adapter='mt5_read_only',broker_connected=False,broker_detail={})
                db.add(row)
            row.pid=os.getpid();row.started_at=self.started_at;row.last_beat=now
            row.broker_connected=self.connected;row.last_error=self.last_error
            row.broker_detail={'read_only':True,'orders_allowed':False,'phase':self.phase,
                'job_id':self.current_job,'last_status':self.last_status,'next_run_utc':self.next_run_utc,
                'fresh_current_clock_verified':self.fresh_clock_verified,
                'current_request_offset_seconds':self.current_offset,'historical_timestamps_verified':False,
                'lookback_days':self.lookback_days,'tick_lookback_minutes':self.tick_minutes}

    def _symbols(self):
        # This transaction is closed before terminal connection or any broker I/O.
        with session_scope(self.factory) as db:
            st.seed_if_empty(db,self.settings.config_dir)
            return tuple(i.symbol for i in st.instruments(db) if i.enabled)

    def _calibrate(self,adapter,symbols):
        if getattr(adapter,'allow_orders',None) is not False:
            raise DataSyncError('READ_ONLY_ADAPTER_REQUIRED')
        # The factory must create a fresh adapter each cycle. Reject any stale
        # verification rather than reusing an offset across a DST transition.
        if adapter.clock_verified:raise DataSyncError('FRESH_ADAPTER_CALIBRATION_REQUIRED')
        for attempt in range(self.calibration_attempts):
            for symbol in symbols:adapter.quote(symbol)
            samples=getattr(adapter,'_clock_samples',[])
            offset=getattr(adapter,'_utc_offset_seconds',None)
            now=self.clock()
            matching=[s for s in samples if len(s)==3 and s[1]==offset and
                      0<=(now-st.as_utc(s[2])).total_seconds()<=30]
            if (adapter.clock_verified and isinstance(offset,(int,float)) and math.isfinite(offset) and
                abs(offset)<=14*3600 and len(matching)>=3 and len({s[0] for s in matching})>=2):
                self.fresh_clock_verified=True;self.current_offset=offset
                return {'verified_at_utc':now.isoformat(),'request_axis_offset_seconds':offset,
                    'samples':[{'symbol':symbol,'offset_seconds':candidate,'observed_utc':stamp.isoformat()}
                               for symbol,candidate,stamp in matching],
                    'calibration':'advancing broker quotes with matching local elapsed cadence across multiple symbols',
                    'historical_offset_schedule_verified':False}
            if attempt+1<self.calibration_attempts:self.sleeper(self.calibration_sleep)
        raise DataSyncError('CURRENT_BROKER_CLOCK_NOT_FRESHLY_VERIFIED')

    def _persist_report(self,report):
        directory=self.settings.data_dir/'data_sync_reports';directory.mkdir(parents=True,exist_ok=True)
        path=directory/(report['job_id']+'.json')
        # Reports are immutable snapshots; SystemState is just the latest pointer.
        serialized=json.dumps(report,indent=2,allow_nan=False)
        with path.open('x',encoding='utf-8') as handle:handle.write(serialized)
        summary={**report,'report_path':str(path.resolve()),
                 'report_sha256':hashlib.sha256(serialized.encode()).hexdigest()}
        now=self.clock()
        with session_scope(self.factory) as db:
            state=db.get(SystemState,'data_sync')
            if state is None:db.add(SystemState(key='data_sync',data=summary,updated_at=now))
            else:state.data=summary;state.updated_at=now
            record(db,'data_worker','data.sync.'+report['status'],{
                'job_id':report['job_id'],'report_path':str(path.resolve()),
                'datasets':len(report['datasets']),'ticks':len(report['ticks']),
                'errors':len(report['errors']),'read_only':True})
        return summary

    def run_once(self):
        self.current_job=uuid.uuid4().hex;self.phase='preparing';self.connected=False
        self.current_offset=None;self.fresh_clock_verified=False;self.last_error=None
        report={'schema':1,'job_id':self.current_job,'started_utc':self.clock().isoformat(),
            'status':'running','read_only':True,'orders_submitted':0,'historical_timestamps_verified':False,
            'lookback_days':self.lookback_days,'tick_lookback_minutes':self.tick_minutes,
            'datasets':[],'ticks':[],'errors':[]}
        adapter=None
        try:
            symbols=self._symbols();report['configured_enabled_symbols']=list(symbols)
            if not symbols:raise DataSyncError('NO_ENABLED_CONFIGURED_SYMBOLS')
            if self.settings.broker_adapter!='mt5':raise DataSyncError('MT5_DATA_SOURCE_NOT_CONFIGURED')
            adapter=self.adapter_factory()
            if getattr(adapter,'allow_orders',None) is not False:raise DataSyncError('READ_ONLY_ADAPTER_REQUIRED')
            self.phase='connecting';self.heartbeat()
            status=adapter.connect()
            self.connected=bool(status.connected)
            if not self.connected:raise DataSyncError('MT5_CONNECTION_OR_AUTHORIZATION_FAILED')
            account=adapter.account_info()
            if account is None:raise DataSyncError('BROKER_ACCOUNT_UNAVAILABLE')
            account_scope=hashlib.sha256((account.server+'|'+account.login).encode()).hexdigest()
            report.update(source_server=account.server,account_is_demo=account.is_demo,account_scope=account_scope)
            self.phase='calibrating';self.heartbeat()
            calibration=self._calibrate(adapter,symbols);report['current_clock_calibration']=calibration
            metadata={'raw_timestamps_preserved':True,'historical_offset_schedule':[],
                'historical_timestamp_verified':False,'current_clock_calibration':calibration,
                'raw_timestamp_semantics':'broker-reported epoch; historical UTC/DST mapping unverified',
                'request_offset_purpose':'current API request selection only; never historical normalization'}
            self.phase='syncing';self.heartbeat();end=self.clock()
            captured=self.syncer(adapter._mt5,self.store.root,symbols,end-timedelta(days=self.lookback_days),end,
                tuple(TIMEFRAMES),include_ticks=False,timestamp_metadata=metadata,
                request_axis_offset_seconds=self.current_offset)
            report['datasets']=captured.get('datasets',[])
            report['errors']=[self._safe(item) for item in captured.get('errors',[])]
            report['bar_sync_report_path']=captured.get('report_path')
            # Tick lookback is independent of the seven-day bar window.
            for symbol in symbols:
                end=self.clock()+timedelta(seconds=self.current_offset)
                try:
                    tick=self.store.ingest_ticks(adapter._mt5,symbol,end-timedelta(minutes=self.tick_minutes),end,
                        timestamp_metadata=metadata,request_axis_offset_seconds=self.current_offset)
                    report['ticks'].append({'symbol':symbol,'version':tick['version'],
                        'file_sha256':tick['file_sha256'],'quality':tick['quality']})
                except Exception as exc:report['errors'].append({'symbol':symbol,'phase':'ticks','error':self._safe(type(exc).__name__+': '+str(exc))})
            observed=adapter.account_info()
            if observed is None or (observed.server,observed.login)!=(account.server,account.login):
                raise DataSyncError('SOURCE_ACCOUNT_CHANGED_DURING_CAPTURE_REQUIRES_REVIEW')
            report['source_connected_during_sync']=True
            if report['errors']:
                report['status']='partial' if report['datasets'] or report['ticks'] else 'failed'
                self.last_error='SOURCE_CAPTURE_ERRORS_REVIEW_IMMUTABLE_REPORT'
            else:report['status']='completed'
        except Exception as exc:
            report['status']='failed';self.last_error=self._safe(type(exc).__name__+': '+str(exc))
            report['errors'].append({'phase':self.phase,'error':self.last_error})
        finally:
            if adapter is not None:
                try:adapter.disconnect()
                except Exception as exc:
                    report['errors'].append({'phase':'disconnect','error':self._safe(type(exc).__name__)})
                    self.last_error='SOURCE_DISCONNECT_FAILED'
                    if report['status']=='completed':report['status']='partial'
            self.connected=False;self.phase='waiting';self.last_status=report['status']
            report['finished_utc']=self.clock().isoformat()
            report=self._persist_report(report)
            self.current_job=None;self.heartbeat()
        return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once',action='store_true')
    parser.add_argument('--interval-seconds',type=float,default=3600)
    parser.add_argument('--lookback-days',type=float,default=7)
    parser.add_argument('--tick-minutes',type=float,default=15)
    args=parser.parse_args()
    if min(args.interval_seconds,args.lookback_days,args.tick_minutes)<=0:parser.error('Positive intervals/windows required')
    settings=get_settings();worker=DataWorker(settings,lookback_days=args.lookback_days,tick_minutes=args.tick_minutes)
    stop=threading.Event()
    with ProcessLock(settings.data_dir.parent/'data_worker.lock'):
        worker.heartbeat()
        def pulse():
            while not stop.wait(10):
                try:worker.heartbeat()
                except Exception:pass
        thread=threading.Thread(target=pulse,daemon=True);thread.start()
        try:
            while True:
                result=worker.run_once()
                print(json.dumps({'status':result['status'],'report_path':result['report_path'],
                    'datasets':len(result['datasets']),'ticks':len(result['ticks']),'errors':len(result['errors'])}),flush=True)
                if args.once:return 0 if result['status']=='completed' else 1
                # Auth/calibration/capture failures back off; no hot retry loop.
                worker.next_run_utc=(worker.clock()+timedelta(seconds=args.interval_seconds)).isoformat()
                worker.heartbeat();stop.wait(args.interval_seconds)
        except KeyboardInterrupt:return 0
        finally:stop.set();thread.join(timeout=11)


if __name__=='__main__':raise SystemExit(main())

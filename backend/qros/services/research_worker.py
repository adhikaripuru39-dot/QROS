"""Independent read-only research worker; never submits broker orders.

Queue claims are transactional. A running job left by a crashed worker becomes
failed at the next locked startup; it is not silently retried across OOS.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time
import uuid
from sqlalchemy import select, text
from qros.audit.log import record
from qros.backtest import Bar, BacktestConfig
from qros.config.settings import Settings, get_settings
from qros.data.history import HistoryStore, TIMEFRAMES
from qros.db.models import BackgroundJob, EvidenceReport, Experiment, ServiceHeartbeat, Setting, Strategy
from qros.db.session import session_factory, session_scope
from qros.research.registry import registry_dicts
from qros.research.runner import run_research
from qros.services.evidence import canonical_hash
from qros.services.process_lock import ProcessLock
from qros.services import settings_store as st


def utcnow(): return datetime.now(timezone.utc)


class ResearchWorker:
    def __init__(self,settings:Settings,factory=None,*,runner=run_research,max_bars=2000):
        if not 100<=max_bars<=5000: raise ValueError('Pilot window must contain 100..5000 bars')
        self.settings=settings
        self.factory=factory or session_factory(settings.database_url)
        self.runner=runner;self.max_bars=max_bars
        self.store=HistoryStore(settings.data_dir/'history')
        self.started_at=utcnow();self.current_job=None

    def heartbeat(self,error=None):
        now=utcnow()
        with session_scope(self.factory) as db:
            row=db.get(ServiceHeartbeat,'research_worker')
            if row is None:
                row=ServiceHeartbeat(service='research_worker',pid=os.getpid(),started_at=self.started_at,last_beat=now,broker_adapter='research',broker_connected=False,broker_detail={})
                db.add(row)
            row.pid=os.getpid();row.started_at=self.started_at;row.last_beat=now
            row.broker_detail={'job_id':self.current_job,'read_only':True,'max_bars':self.max_bars}
            row.last_error=error

    def recover_abandoned(self):
        """Call only after acquiring the OS worker lock."""
        with session_scope(self.factory) as db:
            st.seed_if_empty(db,self.settings.config_dir)
            for row in db.execute(select(BackgroundJob).where(BackgroundJob.kind=='research',BackgroundJob.status=='running')).scalars():
                row.status='failed';row.error='WORKER_RESTART: interrupted job is not automatically retried; review any consumed holdout'
                row.updated_at=utcnow()
                record(db,'research_worker','research.job.interrupted',{'job_id':row.id})

    def claim(self):
        with session_scope(self.factory) as db:
            if db.bind.dialect.name=='sqlite': db.execute(text('BEGIN IMMEDIATE'))
            row=db.execute(select(BackgroundJob).where(BackgroundJob.kind=='research',BackgroundJob.status=='queued').order_by(BackgroundJob.created_at,BackgroundJob.id).limit(1).with_for_update(skip_locked=True)).scalar_one_or_none()
            if row is None:return None
            row.status='running';row.updated_at=utcnow();row.error=None
            record(db,'research_worker','research.job.claimed',{'job_id':row.id})
            return row.id,dict(row.payload)

    def _find_dataset(self,payload):
        requested=payload.get('dataset_version')
        if requested:
            frame,manifest=self.store.load(requested)
            if manifest.symbol!=payload['symbol'] or manifest.timeframe!=payload['timeframe']:
                raise ValueError('Requested dataset symbol/timeframe does not match job')
            return frame,manifest
        candidates=[]
        for path in self.store.root.glob('*/manifest.json'):
            try:
                raw=json.loads(path.read_text(encoding='utf-8'))
                if raw.get('symbol')==payload['symbol'] and raw.get('timeframe')==payload['timeframe'] and (path.parent/'bars.parquet').is_file():
                    candidates.append((int(raw.get('rows',0)),raw.get('collected_utc',''),raw['version']))
            except (OSError,ValueError,KeyError):continue
        if not candidates:
            self._sync_missing(payload)
            return self._find_dataset({**payload,'dataset_version':self._newest_version(payload)})
        return self.store.load(max(candidates)[2])

    def _newest_version(self,payload):
        found=[]
        for path in self.store.root.glob('*/manifest.json'):
            raw=json.loads(path.read_text(encoding='utf-8'))
            if raw.get('symbol')==payload['symbol'] and raw.get('timeframe')==payload['timeframe'] and 'file_sha256' in raw:
                found.append((raw.get('collected_utc',''),raw['version']))
        if not found:raise RuntimeError('Read-only history sync produced no matching archive')
        return max(found)[1]

    def _sync_missing(self,payload):
        if self.settings.broker_adapter!='mt5':raise RuntimeError('No archived dataset; read-only MT5 history sync is not configured')
        import MetaTrader5 as mt5
        from qros.data.sync import sync_history
        initialized=mt5.initialize(path=self.settings.mt5_path) if self.settings.mt5_path else mt5.initialize()
        if not initialized:raise RuntimeError('Read-only MT5 connection failed')
        try:
            end=utcnow();start=end-timedelta(days=payload.get('days',180))
            result=sync_history(mt5,self.store.root,[payload['symbol']],start,end,[payload['timeframe']])
            if result['errors']:raise RuntimeError('Read-only history sync failed: '+str(result['errors']))
        finally:mt5.shutdown()

    def _specs(self,symbol):
        candidates=[self.settings.data_dir.parent/'readiness'/'broker_specs.json',self.settings.data_dir.parent.parent/'var'/'readiness'/'broker_specs.json']
        for path in dict.fromkeys(candidates):
            if path.is_file():
                raw=json.loads(path.read_text(encoding='utf-8'))
                spec=raw.get('symbols',{}).get(symbol)
                if spec:
                    return raw,spec,hashlib.sha256(path.read_bytes()).hexdigest()
        raise RuntimeError('Captured broker contract specifications unavailable for '+symbol)

    def process(self,job_id,payload):
        if payload.get('finalize_oos'):raise ValueError('Queued worker jobs preserve OOS; finalization requires a separately frozen reviewed cohort')
        symbol=payload['symbol'];timeframe=payload.get('timeframe','M15')
        if timeframe not in TIMEFRAMES:raise ValueError('Unsupported timeframe')
        payload={**payload,'timeframe':timeframe}
        pinned_id=payload.get('strategy_id')
        pinned_runtime=None
        if pinned_id:
            with session_scope(self.factory) as db:
                pinned=db.get(Strategy,pinned_id)
                if pinned is None or not pinned.spec.get('library_version'):raise ValueError('Unknown library version')
                pinned_runtime=dict(pinned.spec['runtime'])
                if (pinned_runtime!=payload.get('runtime_spec') or pinned_runtime['symbol']!=symbol
                        or pinned_runtime['timeframe_seconds']!=TIMEFRAMES[timeframe]
                        or payload.get('candidate_ids')!=[pinned.hypothesis_id]):
                    raise ValueError('Queued strategy/runtime binding mismatch')
        frame,manifest=self._find_dataset(payload)
        if manifest.price_basis!='bid':raise ValueError('Backtest requires explicitly observed bid OHLC basis')
        for name in ('invalid_rows','duplicate_times','out_of_range'):
            if manifest.quality.get(name,0):raise ValueError('Source quality failure: '+name)
        if manifest.quality.get('monotonic') is False:raise ValueError('Source timestamps are not monotonic')
        source_rows=len(frame)
        if source_rows==0:raise ValueError('Historical archive is empty')
        # Select on reported-axis relative distance, not falsely claimed UTC.
        latest=float(frame.time.iloc[-1]);days=int(payload.get('days',180))
        if not 1<=days<=3650:raise ValueError('Invalid lookback days')
        frame=frame[frame.time>=latest-days*86400].tail(self.max_bars).copy()
        timestamp_verified=manifest.timestamp_metadata.get('historical_timestamp_verified') is True and 'time_utc' in frame.columns
        seconds=TIMEFRAMES[timeframe]
        times=frame.time_utc if timestamp_verified else frame.time
        bars=[Bar(int(epoch),float(row.open),float(row.high),float(row.low),float(row.close),float(row.spread)*manifest.point) for epoch,row in zip(times,frame.itertuples())]
        raw_specs,spec,spec_hash=self._specs(symbol)
        def positive(key):
            result=float(spec[key])
            if not math.isfinite(result) or result<=0:raise ValueError('Invalid captured broker specification: '+key)
            return result
        unit=positive('trade_contract_size');tick_size=positive('trade_tick_size');tick_value=positive('trade_tick_value_loss')
        conversion=tick_value/(tick_size*unit)
        with session_scope(self.factory) as db:
            st.seed_if_empty(db,self.settings.config_dir)
            firm=st.active_firm(db);limits=st.internal_limits(db)
            preference=db.get(Setting,'research_profile');profile=preference.value.get('profile','B') if preference else 'B'
        leverage=float(raw_specs.get('leverage',0))
        if not math.isfinite(leverage) or leverage<=0:raise ValueError('Observed leverage unavailable')
        cfg=BacktestConfig(initial_cash=firm.initial_balance,contract_size=unit,leverage=leverage,
            commission_per_lot_side=firm.commission_per_lot_round_turn/2,
            slippage=limits.slippage_buffer_points*manifest.point,swap_per_lot_day=0,
            quote_to_account=conversion,min_lot=positive('volume_min'),lot_step=positive('volume_step'),max_lot=positive('volume_max'))
        ids=payload.get('candidate_ids') or ['momentum','mean_reversion','squeeze','failed_breakout','regime_trend','ensemble']
        disabled=[]
        if not timestamp_verified:
            disabled=[sid for sid in ids if sid in {'session_open','time_drift','multi_timeframe'}]
            ids=[sid for sid in ids if sid not in disabled]
        if not ids:raise ValueError('All requested hypotheses require verified historical UTC mapping')
        provenance={'dataset_version':manifest.version,'source':manifest.source,'timestamp_metadata':manifest.timestamp_metadata,
            'historical_timestamps_verified':timestamp_verified,'timeframe':timeframe,
            'timeframe_seconds':seconds if timestamp_verified else None,'reported_bar_interval_seconds':seconds,
            'source_rows':source_rows,'selected_rows':len(bars),'pilot_max_bars':self.max_bars,
            'selected_reported_start':int(frame.time.iloc[0]),'selected_reported_end':int(frame.time.iloc[-1]),
            'disabled_time_sensitive_candidates':disabled,'broker_specs_snapshot_hash':spec_hash,
            'broker_specs_observed_utc':raw_specs.get('observed_utc'),'broker_specs_verified':False,
            'coverage_verified':manifest.quality.get('coverage_proven') is True and timestamp_verified,
            'execution_costs_verified':False,'runtime_equivalence_verified':False,'independent_trade_assumption_reviewed':False,
            'commission_assumption':'Active firm configured commission; historical schedule not verified',
            'swap_assumption':'Zero financing in pilot; unverified, blocks eligibility',
            'conversion_assumption':'Constant captured tick_value_loss / (tick_size * contract_size); time-varying conversion unverified',
            'spread_assumption':manifest.spread_semantics,
            'runtime_spec':{'symbol':symbol,'timeframe_seconds':seconds,'stop_atr_multiple':2,'target_atr_multiple':3,'volume_policy':'fixed broker min lot in research; runtime sizing equivalence unverified'}}
        if pinned_runtime is not None:provenance['runtime_spec']=pinned_runtime
        report=self.runner(bars,manifest.file_sha256,self.settings.data_dir/'research_results',config=cfg,provenance=provenance,finalize_oos=False,candidate_ids=ids,profile=profile)
        registry={row['id']:row for row in registry_dicts()}
        experiment_ids=[];report_ids=[]
        with session_scope(self.factory) as db:
            for candidate in report['candidates']:
                hypothesis=candidate['strategy_id'];sid=pinned_id or f'{hypothesis}_{symbol}_{seconds}'
                strategy=db.get(Strategy,sid)
                if strategy is None:
                    spec_entry=registry[hypothesis]
                    strategy=Strategy(id=sid,hypothesis_id=hypothesis,family=spec_entry['family'],name=f"{spec_entry['family']} / {symbol}",status='IDEA',spec={'hypothesis':spec_entry,'runtime':{'symbol':symbol,'timeframe_seconds':seconds,'stop_atr_multiple':2,'target_atr_multiple':3}})
                    db.add(strategy)
                rid=uuid.uuid4().hex;eid=uuid.uuid4().hex
                content=dict(report)
                passed=report.get('eligible') is True and report.get('selected_candidate')==hypothesis
                db.add(EvidenceReport(id=rid,strategy_id=sid,kind='validation',passed=passed,dataset_hash=manifest.file_sha256,code_hash=report['binding']['code_hash'],config_hash=report['binding']['config_hash'],report_hash=canonical_hash(content),content=content))
                db.add(Experiment(id=eid,hypothesis_id=hypothesis,kind='backtest',status='completed',code_version=report['binding']['code_hash'],dataset_version=manifest.file_sha256,config={**asdict(cfg),'strategy_id':sid,'runtime_spec':provenance['runtime_spec']},seed=1729,results={'candidate':candidate,'binding':report['binding'],'validation_report_id':rid,'source_dataset_version':manifest.version},progress=1.,finished_at=utcnow()))
                if passed:
                    db.add(Experiment(id=uuid.uuid4().hex,hypothesis_id=hypothesis,kind='oos',status='completed',code_version=report['binding']['code_hash'],dataset_version=manifest.file_sha256,config=asdict(cfg),seed=1729,results=content,progress=1.,finished_at=utcnow()))
                experiment_ids.append(eid);report_ids.append(rid)
            record(db,'research_worker','research.report.persisted',{'job_id':job_id,'dataset_version':manifest.version,'eligible':report['eligible'],'experiments':experiment_ids})
        return {'report_path':report.get('report_path'),'report_hash':report.get('report_hash'),'dataset_version':manifest.version,'dataset_hash':manifest.file_sha256,'rows':len(bars),'source_rows':source_rows,'eligible':report['eligible'],'oos_evaluated':report.get('oos',{}).get('evaluated',False),'candidates':[{'strategy_id':r['strategy_id'],'development':r['development'],'validation':r['validation']} for r in report['candidates']],'preflight_failures':report.get('preflight_failures',[]),'disabled_candidates':disabled,'experiment_ids':experiment_ids,'evidence_report_ids':report_ids}

    def run_once(self):
        claimed=self.claim()
        if claimed is None:self.heartbeat();return False
        job_id,payload=claimed;self.current_job=job_id;self.heartbeat()
        try:
            result=self.process(job_id,payload)
            with session_scope(self.factory) as db:
                row=db.get(BackgroundJob,job_id);row.status='completed';row.result=result;row.updated_at=utcnow()
            self.heartbeat()
        except Exception as exc:
            message=f'{type(exc).__name__}: {exc}'
            with session_scope(self.factory) as db:
                row=db.get(BackgroundJob,job_id);row.status='failed';row.error=message;row.updated_at=utcnow()
                record(db,'research_worker','research.job.failed',{'job_id':job_id,'error':message})
            self.heartbeat(message)
        finally:self.current_job=None
        return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once',action='store_true');parser.add_argument('--interval-seconds',type=float,default=3)
    parser.add_argument('--max-bars',type=int,default=2000)
    args=parser.parse_args()
    if args.interval_seconds<=0:parser.error('Positive polling interval required')
    settings=get_settings();worker=ResearchWorker(settings,max_bars=args.max_bars)
    stop=threading.Event()
    with ProcessLock(settings.data_dir.parent/'research_worker.lock'):
        worker.recover_abandoned();worker.heartbeat()
        def pulse():
            while not stop.wait(5):
                try:worker.heartbeat()
                except Exception:pass
        thread=threading.Thread(target=pulse,daemon=True);thread.start()
        try:
            while True:
                worked=worker.run_once()
                if args.once:return 0
                if not worked:stop.wait(args.interval_seconds)
        finally:stop.set();thread.join(timeout=6)


if __name__=='__main__':raise SystemExit(main())

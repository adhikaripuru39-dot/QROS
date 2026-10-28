"""Execution service — runs as an independent process (never inside the web API).

    python -m qros.services.executor

Responsibilities (Phase 1):
* Broker connection management with exponential back-off reconnect.
* Heartbeat + truthful connection status.
* Account/position snapshots (broker-observed, timestamped).
* Daily-reset anchors, high-water marks, and risk-engine evaluation.
* Authoritative processing of dashboard commands (start/pause/stop/kill/mode).
* Automatic HALT when any firm or internal drawdown limit is reached.
* Restart recovery: persisted control state; RUNNING resumes as PAUSED_ENTRIES
  unless QROS_RESUME_ON_RESTART=true.

Includes completed-bar signals, durable entry pipeline, broker-deal reconciliation,
explicit paper venue, and managed-only risk halt handling. All evidence/owner/host gates apply.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import math
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from qros.audit.log import record
from qros.broker.base import BrokerAdapter, BrokerPosition, make_adapter, client_tag
from qros.config.schemas import InstrumentConfig, RunState, TradingMode
from qros.config.settings import Settings, get_settings
from qros.db.models import (AccountSnapshot, ControlCommand, ControlState, PositionSnapshot,
                            RiskDay, RiskStateRow, ServiceHeartbeat, Setting, Strategy)
from qros.db.session import session_factory, session_scope
from qros.risk.calendar import last_reset, next_reset, trading_day
from qros.risk.drawdown import AccountState, evaluate
from qros.risk.exposure import ExposureLeg, currency_exposure
from qros.risk.gate import ALLOWED_STATUS_BY_MODE
from qros.risk.sizing import ContractSpec
from qros.services import settings_store as st
from qros.services.settings_store import as_utc

log = logging.getLogger("qros.executor")

COMMAND_TTL_SECONDS = 120
SNAPSHOT_PERSIST_SECONDS = 15
LIVE_CONFIRM_PHRASE = "ENABLE LIVE TRADING"
RESUME_PHRASE = "RESUME"
KILL_RELEASE_PHRASE = "RELEASE KILL SWITCH"
DAILY_HALT_CODES = {"INTERNAL_DAILY_STOP", "FIRM_DAILY_LOSS_BREACHED"}
PERMANENT_HALT_CODES = {"FIRM_MAX_LOSS_BREACHED"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def spec_from_config(i: InstrumentConfig) -> ContractSpec:
    return ContractSpec(symbol=i.symbol, tick_size=i.tick_size, tick_value_per_lot=i.tick_value_per_lot,
                        point=i.point, volume_min=i.volume_min, volume_max=i.volume_max,
                        volume_step=i.volume_step, min_stop_points=i.min_stop_points)


def position_risk_to_stop(p: BrokerPosition, spec: Optional[ContractSpec]) -> Optional[float]:
    """Remaining loss (account ccy) if the broker-side stop is hit from the current price."""
    if p.sl is None or spec is None:
        return None
    dist = (p.price_current - p.sl) if p.side == "buy" else (p.sl - p.price_current)
    return max(0.0, dist) / spec.tick_size * spec.tick_value_per_lot * p.volume


class Executor:
    def __init__(self, settings: Settings, adapter: BrokerAdapter, factory: sessionmaker[Session],
                 clock: Callable[[], datetime] = utcnow, service: str = "executor"):
        self.settings, self.adapter, self.factory, self.clock = settings, adapter, factory, clock
        self.service = service
        self.connected = False
        self.conn_detail: dict = {}
        self.last_error: Optional[str] = None
        self._next_connect_at: Optional[datetime] = None
        self._backoff = 1.0
        self._last_persist: Optional[datetime] = None
        self.started_at = clock()
        self.snapshot: Optional[dict] = None
        self.market_source = adapter
        self._signals = None
        self._last_degradation_at = None

    # ------------------------------------------------------------------ startup
    def startup(self) -> None:
        with session_scope(self.factory) as s:
            st.seed_if_empty(s, self.settings.config_dir)
            from qros.db.models import SystemState
            pending=s.get(SystemState,'demo_forward_arm')
            if pending and pending.data.get('pending'):
                pending.data={**pending.data,'pending':False,'cancelled':'executor_restart_requires_owner_rearm'}
                pending.updated_at=self.clock()
                record(s,self.service,'demo.arm.cancelled_on_restart',{})
            cs = s.get(ControlState, 1)
            if cs.run_state == RunState.RUNNING.value:
                cs.run_state = RunState.PAUSED_ENTRIES.value
                cs.halt_reason = "SERVICE_RESTARTED: new entries paused until owner resumes"
                cs.updated_at = self.clock()
                record(s, self.service, "executor.recovery.paused_entries", {})
            record(s, self.service, "executor.start",
                   {"pid": os.getpid(), "adapter": self.adapter.name,
                    "live_trading_enabled_on_host": self.settings.live_trading_enabled,
                    "restored_state": {"mode": cs.trading_mode, "run_state": cs.run_state,
                                       "kill_switch": cs.kill_switch}})

    # --------------------------------------------------------------------- loop
    def tick(self) -> None:
        now = self.clock()
        self._ensure_connection(now)
        with session_scope(self.factory) as state_db:
            state=state_db.get(ControlState,1)
            desired=state.trading_mode if state else "off"
            if desired=="paper" and self.adapter.name!="paper" and self.connected:
                try:self._activate_paper(state_db)
                except Exception as exc:self.last_error="PAPER_SETUP_FAILED:"+str(exc);self.connected=False
            elif desired!="paper" and self.adapter.name=="paper":
                self.adapter.disconnect();self.adapter=self.market_source;self.connected=False
            self._refresh_market(state_db,now)
        self.snapshot = self._take_snapshot(now) if self.connected else None
        with session_scope(self.factory) as s:
            if self.snapshot is not None:
                self._persist_snapshot(s, self.snapshot, now)
                self._update_risk(s, self.snapshot, now)
            self._process_commands(s, now)
            self._enforce_limits(s, now)
            if self.snapshot is not None:
                from qros.services.reconciliation import reconcile
                reconcile(s,self.adapter,now,self._state(s).trading_mode)
                if self._last_degradation_at is None or (now-self._last_degradation_at).total_seconds()>=15:
                    from qros.services.degradation_service import evaluate_degradation
                    evaluate_degradation(s,self.settings,now)
                    self._last_degradation_at=now
            self._heartbeat(s, now)
            self._activate_pending_demo(s, now)
        self._flatten_managed_after_halt(now)
        self._protect_before_news(now)
        self._evaluate_signals(now)

    def run_forever(self) -> None:
        from qros.services.process_lock import ProcessLock
        import hashlib,tempfile
        identity=hashlib.sha256(str(self.settings.mt5_path or self.settings.database_url).encode()).hexdigest()[:20]
        lease=ProcessLock(Path(tempfile.gettempdir())/'qros-locks'/('executor-'+identity+'.lock')).acquire()
        self.startup()
        log.info("executor started adapter=%s", self.adapter.name)
        try:
            while True:
                t0 = time.monotonic()
                try:
                    self.tick()
                except Exception as e:  # keep the service alive; record the failure
                    self.last_error = f"{type(e).__name__}: {e}"
                    log.exception("tick failed")
                time.sleep(max(0.1, self.settings.executor_interval_seconds - (time.monotonic() - t0)))
        except KeyboardInterrupt:
            log.info("executor stopping")
        finally:
            self.adapter.disconnect()
            lease.release()

    def _activate_paper(self,db):
        if any(v is None for v in (self.settings.paper_initial_balance,self.settings.paper_commission_per_lot_round_turn,self.settings.paper_swap_per_lot_day)):
            raise ValueError("PAPER_ASSUMPTIONS_REQUIRED")
        from qros.signals.paper import PaperBroker,PaperAssumptions,PaperMarketAdapter
        specs={};margins={}
        for item in st.instruments(db):
            if not item.enabled:continue
            spec=self.market_source.contract_spec(item.symbol);quote=self.market_source.quote(item.symbol)
            if spec is None or quote is None:raise ValueError("PAPER_CONTRACT_OR_QUOTE_UNKNOWN:"+item.symbol)
            margin=self.market_source.margin_required(item.symbol,'buy',1.,quote.ask)
            if margin is None:raise ValueError("PAPER_MARGIN_UNKNOWN:"+item.symbol)
            specs[item.symbol]=spec;margins[item.symbol]=margin
        firm=st.active_firm(db)
        costs=PaperAssumptions(self.settings.paper_initial_balance,firm.currency,self.settings.paper_commission_per_lot_round_turn/2,self.settings.paper_slippage_points,self.settings.paper_swap_per_lot_day,self.settings.paper_swap_per_lot_day)
        self.settings.data_dir.mkdir(parents=True,exist_ok=True)
        paper=PaperBroker(self.settings.data_dir/'paper_account.sqlite',specs,margins,costs,clock=self.clock)
        self.adapter=PaperMarketAdapter(self.market_source,paper)
        status=self.adapter.connect();self.connected=status.connected;self.conn_detail=status.detail;self.last_error=status.error
        if not status.connected:raise ValueError(status.error)

    def _refresh_market(self,db,now):
        from qros.services.execution import set_state
        quotes={}
        if self.connected:
            for item in st.instruments(db):
                if not item.enabled:continue
                try:
                    quote=self.adapter.quote(item.symbol)
                    if quote:quotes[item.symbol]={"bid":quote.bid,"ask":quote.ask,"observed_quote_time":quote.time.isoformat(),"stale":not 0 <= (now-quote.time).total_seconds() <= self.settings.stale_after_seconds}
                except Exception as exc:quotes[item.symbol]={"error":str(exc)}
            status=self.adapter.ping()
            self.conn_detail=status.detail
            self.connected=status.connected
        set_state(db,'market_observations',{'quotes':quotes,'source':self.adapter.name,'observed_at':now.isoformat()},now)

    def _flatten_managed_after_halt(self,now):
        if self.settings.halt_action!='flatten_managed':return
        from qros.db.models import OrderLedger
        from qros.services.execution import account_key,set_state
        with session_scope(self.factory) as db:
            ctrl=self._state(db)
            if ctrl.run_state!='halted' or self.snapshot is None:return
            if self.adapter.name!='paper' and not self.settings.order_execution_enabled:
                set_state(db,'risk_flatten',{'status':'blocked','reason':'HOST_ORDER_EXECUTION_DISABLED'},now);return
            key=account_key(self.snapshot['account'],ctrl.trading_mode)
            rows=list(db.execute(select(OrderLedger).where(OrderLedger.account_key==key,OrderLedger.status=='verified')).scalars())
            tags={client_tag(row.client_order_id) for row in rows}
            positions=self.adapter.positions()
            if positions is None:return
            managed=[p for p in positions if p.comment in tags]
        results=[]
        orders=self.adapter.pending_orders() or []
        managed_orders=[o for o in orders if getattr(o,'comment',None) in tags]
        for order in managed_orders:
            r=self.adapter.cancel_order(order.ticket)
            results.append({'order_ticket':order.ticket,'ok':r.ok,'message':r.message})
        for position in managed:
            result=self.adapter.close_position(position.ticket)
            results.append({'ticket':position.ticket,'ok':result.ok,'verified':result.verified,'message':result.message})
        with session_scope(self.factory) as db:
            if results:
                set_state(db,'risk_flatten',{'status':'attempted','results':results},now)
                record(db,'executor','risk.flatten_managed',{'results':results})

    def _protect_before_news(self,now):
        if not self.connected or self.snapshot is None:return
        from qros.db.models import OrderLedger
        from qros.risk.news import configured_news
        from qros.services.execution import account_key,set_state
        with session_scope(self.factory) as db:
            ctrl=self._state(db);firm=st.active_firm(db)
            flatten_pos=bool(getattr(firm.news,'flatten_before_news',False))
            cancel_ord=bool(getattr(firm.news,'cancel_pending_before_news',False))
            if not (flatten_pos or cancel_ord):return
            if self.adapter.name!='paper' and not self.settings.order_execution_enabled:return
            key=account_key(self.snapshot['account'],ctrl.trading_mode)
            rows=list(db.execute(select(OrderLedger).where(OrderLedger.account_key==key,OrderLedger.status=='verified')).scalars())
            tags={client_tag(row.client_order_id) for row in rows}
            inst_map={i.symbol:i for i in st.instruments(db)}
            news_source=getattr(self.adapter,'source',self.adapter)
            news_conn=news_source.ping()
            news_acct=news_source.account_info() if ctrl.trading_mode=='paper' else self.snapshot['account']
            blackout_syms=set()
            for sym,ic in inst_map.items():
                if not ic.enabled:continue
                cov,blk,_=configured_news(self.settings,firm,now,{ic.base,ic.quote},
                    expected_server=news_acct.server if news_acct else None,
                    expected_offset=news_conn.detail.get('observed_server_utc_offset_seconds'))
                if blk or not cov:blackout_syms.add(sym)
        if not blackout_syms:return
        results=[]
        if cancel_ord:
            for o in (self.adapter.pending_orders() or []):
                if getattr(o,'comment',None) in tags and getattr(o,'symbol',None) in blackout_syms:
                    r=self.adapter.cancel_order(o.ticket)
                    results.append({'order_ticket':o.ticket,'symbol':o.symbol,'ok':r.ok,'message':r.message})
        if flatten_pos:
            for p in (self.adapter.positions() or []):
                if p.comment in tags and p.symbol in blackout_syms:
                    r=self.adapter.close_position(p.ticket)
                    results.append({'ticket':p.ticket,'symbol':p.symbol,'ok':r.ok,'verified':r.verified,'message':r.message})
        if results:
            with session_scope(self.factory) as db:
                set_state(db,'news_flatten',{'status':'attempted','results':results},now)
                record(db,'executor','news.flatten_managed',{'results':results})

    def _evaluate_signals(self,now):
        if not self.connected or self.snapshot is None:return
        from qros.services.evidence import strategy_eligibility
        from qros.services.execution import execute_intent,set_state
        from qros.signals.engine import SignalEngine,StrategyRuntime,Bar
        candidates=[]
        with session_scope(self.factory) as db:
            ctrl=self._state(db)
            if ctrl.run_state!='running' or ctrl.kill_switch:return
            limits=st.internal_limits(db);firm=st.active_firm(db)
            base_eq = min(self.snapshot['account'].balance, self.snapshot['account'].equity)
            hwm = max(firm.initial_balance, self.snapshot['account'].balance, self.snapshot['account'].equity, getattr(self, '_hwm_equity', firm.initial_balance))
            self._hwm_equity = hwm
            dd_pct = (hwm - self.snapshot['account'].equity) / hwm * 100.0 if hwm > 0 else 0.0
            risk_factor = 1.0 if dd_pct <= 0.75 else (0.60 if dd_pct <= 1.50 else (0.30 if dd_pct <= 2.25 else 0.0))
            dynamic_risk = base_eq * (limits.risk_per_trade_pct * risk_factor / 100.0)
            if dynamic_risk <= 0:
                return
            for sid in ctrl.active_strategy_ids or []:
                strategy=db.get(Strategy,sid)
                if strategy is None or strategy_eligibility(db,strategy,ctrl.trading_mode):continue
                cfg=strategy.spec.get('runtime',{})
                if cfg.get('symbol') is None:continue
                runtime=StrategyRuntime(strategy.id,strategy.hypothesis_id,cfg['symbol'],strategy.status,int(cfg.get('timeframe_seconds',900)),dynamic_risk,True,TradingMode(ctrl.trading_mode),atr_period=int(cfg.get('atr_period',14)),stop_atr_multiple=float(cfg.get('stop_atr_multiple',2)),target_atr_multiple=float(cfg.get('target_atr_multiple',3)),commission_round_turn_per_lot=firm.commission_per_lot_round_turn,adverse_slippage_points=limits.slippage_buffer_points)
                candidates.append(runtime)
        busy_symbols={pos.symbol for pos in (self.snapshot.get('positions') or [])}
        priority={'failed_breakout':0,'trend_pullback':1,'momentum':2,'mean_reversion':3,'squeeze':4}
        candidates.sort(key=lambda r:(priority.get(r.hypothesis_id,9),r.strategy_id))
        engine=SignalEngine(max_quote_age_seconds=self.settings.stale_after_seconds)
        for runtime in candidates:
            quote=self.adapter.quote(runtime.symbol);spec=self.adapter.contract_spec(runtime.symbol)
            if quote is None or spec is None:continue
            frames={}
            for tf in {runtime.timeframe_seconds,14400}:
                raw=self.adapter.completed_bars(runtime.symbol,tf,512)
                if raw is not None:frames[tf]=[Bar(datetime.fromtimestamp(r['time'],timezone.utc),r['open'],r['high'],r['low'],r['close'],r.get('tick_volume',0)) for r in raw]
            signal=engine.evaluate(runtime,frames,quote,now,spec)
            if signal.intent:
                if runtime.symbol in busy_symbols:
                    result={'status':'rejected','reasons':['OPEN_POSITION_ON_INSTRUMENT']}
                else:
                    result=execute_intent(self.factory,self.adapter,self.settings,signal.intent,signal.client_order_id,now)
                    if result.get('status') in ('verified','submitting','unknown'):
                        busy_symbols.add(runtime.symbol)
            else:result={'status':'no_order','reason':signal.reason}
            with session_scope(self.factory) as db:
                set_state(db,'signal:'+runtime.strategy_id,result,now)
                from qros.services.signal_log import record_signal
                record_signal(db,runtime,signal,result,now)

    # --------------------------------------------------------------- connection
    def _ensure_connection(self, now: datetime) -> None:
        if self.connected:
            st_ = self.adapter.ping()
            if st_.connected:
                self.conn_detail = st_.detail
                return
            self.connected, self.last_error = False, st_.error
            self._next_connect_at = now
            log.warning("broker connection lost: %s", st_.error)
        if self._next_connect_at is not None and now < self._next_connect_at:
            return
        st_ = self.adapter.connect()
        self.connected, self.conn_detail = st_.connected, st_.detail
        if st_.connected:
            self._backoff = 1.0
            self.last_error = None
        else:
            self.last_error = st_.error
            self._backoff = min(self._backoff * 2, 60.0)
            self._next_connect_at = now + timedelta(seconds=self._backoff)

    def _take_snapshot(self, now: datetime) -> Optional[dict]:
        acct = self.adapter.account_info()
        positions = self.adapter.positions()
        orders = self.adapter.pending_orders()
        if acct is None or positions is None or orders is None or not all(math.isfinite(v) for v in (acct.balance,acct.equity,acct.margin,acct.free_margin)):
            self.last_error = "snapshot incomplete: account/positions/orders query failed"
            return None
        return {"account": acct, "positions": positions, "orders": orders, "observed_at": now}

    # ---------------------------------------------------------------- persist
    def _spec(self, s: Session, symbol: str) -> Optional[ContractSpec]:
        spec = self.adapter.contract_spec(symbol)
        if spec is not None:
            return spec
        return None

    def _persist_snapshot(self, s: Session, snap: dict, now: datetime) -> None:
        a = snap["account"]
        if self._last_persist is None or (now - self._last_persist).total_seconds() >= SNAPSHOT_PERSIST_SECONDS:
            s.add(AccountSnapshot(observed_at=now, source=self.adapter.name, login=a.login, server=a.server,
                                  is_demo=a.is_demo, currency=a.currency, balance=a.balance, equity=a.equity,
                                  margin=a.margin, free_margin=a.free_margin, leverage=a.leverage))
            self._last_persist = now
        s.execute(delete(PositionSnapshot))
        for p in snap["positions"]:
            s.add(PositionSnapshot(ticket=p.ticket, observed_at=now, symbol=p.symbol, side=p.side,
                                   volume=p.volume, price_open=p.price_open, sl=p.sl, tp=p.tp,
                                   profit=p.profit, magic=p.magic, comment=p.comment,
                                   risk_to_stop=position_risk_to_stop(p, self._spec(s, p.symbol))))

    # -------------------------------------------------------------------- risk
    def _update_risk(self, s: Session, snap: dict, now: datetime) -> None:
        a = snap["account"]
        firm = st.active_firm(s)
        limits = st.internal_limits(s)
        day = trading_day(now, firm.daily_reset).isoformat()
        from qros.services.risk_identity import risk_day_scope
        scope=risk_day_scope(firm.id,a,self._state(s).trading_mode)
        prev = s.get(RiskStateRow, 1)
        same_account=prev is not None and prev.firm_id==firm.id and prev.data.get('risk_scope_key')==scope
        # Owner-entered anchors (e.g. HWM shown on the firm's dashboard) for periods the
        # executor did not observe. Only ever make limits stricter (max()).
        overrides = s.get(Setting, "account_anchors")
        ov = overrides.value if overrides else {}

        rd = s.execute(select(RiskDay).where(RiskDay.firm_id == scope, RiskDay.trading_day == day)
                       ).scalar_one_or_none()
        if rd is None:
            rd = self._create_risk_day(s, firm, day, a, prev if same_account else None, now, scope)

        hwm_eq = max(x for x in [firm.initial_balance, a.equity, a.balance,
                                 prev.hwm_equity if same_account else 0.0,
                                 ov.get("hwm_equity") or 0.0])
        hwm_eod = max(x for x in [firm.initial_balance,
                                  prev.hwm_eod_balance if same_account else 0.0,
                                  ov.get("hwm_eod_balance") or 0.0])
        if same_account and prev.trading_day != day:
            # Day rolled over: finalize previous day's end-of-day balance.
            last_bal = (prev.data or {}).get("balance")
            old = s.execute(select(RiskDay).where(RiskDay.firm_id == scope,
                                                  RiskDay.trading_day == prev.trading_day)).scalar_one_or_none()
            if old is not None and last_bal is not None and old.eod_balance is None:
                old.eod_balance = float(last_bal)
            if last_bal is not None:
                hwm_eod = max(hwm_eod, float(last_bal))

        acct = AccountState(balance=a.balance, equity=a.equity, initial_balance=firm.initial_balance,
                            sod_balance=rd.sod_balance, sod_equity=rd.sod_equity,
                            hwm_equity=hwm_eq, hwm_eod_balance=hwm_eod)
        dd = evaluate(firm, limits, acct)

        pos_rows = s.execute(select(PositionSnapshot)).scalars().all()
        legs, open_risk, unprotected = [], 0.0, []
        inst_map = {i.symbol: i for i in st.instruments(s)}
        for p in pos_rows:
            if p.risk_to_stop is None:
                unprotected.append(p.ticket)
            else:
                open_risk += p.risk_to_stop
            ic = inst_map.get(p.symbol)
            if ic is not None:
                legs.append(ExposureLeg(p.symbol, ic.base, ic.quote, p.side, p.risk_to_stop or 0.0))

        from qros.services.execution import account_key
        data = {**dd.to_dict(), "balance": a.balance, "equity": a.equity,
                "account_key":account_key(a,self._state(s).trading_mode),"risk_scope_key":scope,"source":self.adapter.name,"currency":a.currency,
                "initial_balance": firm.initial_balance, "sod_balance": rd.sod_balance,
                "sod_equity": rd.sod_equity, "anchor_method": rd.anchor_method,
                "open_risk": open_risk, "unprotected_tickets": unprotected,
                "currency_exposure": currency_exposure(legs),
                "next_reset_utc": next_reset(now, firm.daily_reset).isoformat(),
                "limits_version": st.version_of(s, "internal_limits"),
                "firm_version": st.version_of(s, "firm_profiles")}
        if prev is None:
            prev = RiskStateRow(id=1, computed_at=now, firm_id=firm.id, trading_day=day, data=data,
                                hwm_equity=hwm_eq, hwm_eod_balance=hwm_eod)
            s.add(prev)
        else:
            prev.computed_at, prev.firm_id, prev.trading_day = now, firm.id, day
            prev.data, prev.hwm_equity, prev.hwm_eod_balance = data, hwm_eq, hwm_eod

    def _create_risk_day(self, s: Session, firm, day: str, a, prev: Optional[RiskStateRow],
                         now: datetime, scope: str | None = None) -> RiskDay:
        max_gap = 3 * self.settings.executor_interval_seconds + 5
        if (prev is not None and prev.firm_id == firm.id and prev.trading_day != day
                and (now - as_utc(prev.computed_at)).total_seconds() <= max_gap):
            sod_b, sod_e, method = a.balance, a.equity, "observed_at_reset"
        else:
            realized = self.adapter.realized_pnl_since(last_reset(now, firm.daily_reset))
            if realized is not None:
                sod_b = a.balance - realized
                sod_e = max(sod_b, a.equity)  # floating P/L at reset unknown → conservative
                method = "reconstructed_from_deals"
            else:
                sod_b = sod_e = max(a.balance, a.equity)
                method = "conservative_estimate"
        rd = RiskDay(firm_id=scope or firm.id, trading_day=day, sod_balance=sod_b, sod_equity=sod_e,
                     anchor_method=method)
        s.add(rd)
        s.flush()
        record(s, self.service, "risk.day_anchor",
               {"firm": firm.id, "day": day, "sod_balance": sod_b, "sod_equity": sod_e, "method": method})
        return rd

    def _enforce_limits(self, s: Session, now: datetime) -> None:
        cs = s.get(ControlState, 1)
        rs = s.get(RiskStateRow, 1)
        if rs is None:return
        reasons=list(rs.data.get('halt_reasons',[]))
        if rs.data.get('unprotected_tickets'):reasons.append('UNPROTECTED_OPEN_POSITION')
        firm=st.active_firm(s);hours=st.trading_hours(s)
        from qros.risk.calendar import minutes_to_weekend_close,is_weekend_market_closed,in_trading_hours
        if not firm.weekend_allowed and (is_weekend_market_closed(now) or minutes_to_weekend_close(now)<=hours.flat_before_weekend_minutes):reasons.append('WEEKEND_FLATTEN_WINDOW')
        if not firm.overnight_allowed and not in_trading_hours(now,hours):reasons.append('OUTSIDE_APPROVED_HOLDING_SESSION')
        if not reasons:return
        if cs.run_state in (RunState.RUNNING.value, RunState.PAUSED_ENTRIES.value):
            cs.run_state = RunState.HALTED.value
            cs.halt_reason = json.dumps({"codes": reasons, "trading_day": rs.trading_day,
                                         "at": now.isoformat()})
            cs.updated_at = now
            record(s, self.service, "risk.halt", {"reasons": reasons, "trading_day": rs.trading_day})
            log.warning("TRADING HALTED: %s", reasons)

    # ---------------------------------------------------------------- heartbeat
    def _heartbeat(self, s: Session, now: datetime) -> None:
        hb = s.get(ServiceHeartbeat, self.service)
        if hb is None:
            hb = ServiceHeartbeat(service=self.service, pid=os.getpid(), started_at=self.started_at,
                                  last_beat=now, broker_adapter=self.adapter.name)
            s.add(hb)
        hb.pid, hb.started_at, hb.last_beat = os.getpid(), self.started_at, now
        hb.broker_adapter, hb.broker_connected = self.adapter.name, self.connected
        detail = dict(self.conn_detail or {})
        detail["live_trading_enabled_on_host"] = self.settings.live_trading_enabled
        detail["snapshot_ok"] = self.snapshot is not None
        if self.snapshot is not None:
            a = self.snapshot["account"]
            detail.update(login=a.login, server=a.server, is_demo=a.is_demo,
                          broker_trade_allowed=a.trade_allowed,
                          pending_orders=len(self.snapshot["orders"]))
        hb.broker_detail = detail
        hb.last_error = self.last_error

    # ----------------------------------------------------------------- commands
    def _process_commands(self, s: Session, now: datetime) -> None:
        cmds = s.execute(select(ControlCommand).where(ControlCommand.status == "pending")
                         .order_by(ControlCommand.id)).scalars().all()
        for c in cmds:
            age = (now - as_utc(c.created_at)).total_seconds()
            if age > COMMAND_TTL_SECONDS and c.command != "kill":
                status, result = "rejected", {"reasons": ["COMMAND_EXPIRED"], "age_s": round(age)}
            else:
                handler = getattr(self, f"_cmd_{c.command}", None)
                if handler is None:
                    status, result = "rejected", {"reasons": [f"UNKNOWN_COMMAND:{c.command}"]}
                else:
                    try:
                        if c.command!='arm_demo':
                            from qros.db.models import SystemState
                            arm=s.get(SystemState,'demo_forward_arm')
                            if arm and arm.data.get('pending'):
                                arm.data={**arm.data,'pending':False,'cancelled':'owner_command:'+c.command};arm.updated_at=now
                                record(s,self.service,'demo.arm.cancelled',{'command':c.command})
                        status, result = handler(s, c.payload or {}, now)
                    except Exception as e:
                        status, result = "failed", {"reasons": [f"EXCEPTION:{type(e).__name__}: {e}"]}
            c.status, c.result, c.processed_at = status, result, now
            record(s, self.service, f"command.{c.command}.{status}",
                   {"command_id": c.id, "actor": c.actor, "payload": c.payload, "result": result})

    def _state(self, s: Session) -> ControlState:
        return s.get(ControlState, 1)

    def _set(self, cs: ControlState, now: datetime, **kw) -> None:
        for k, v in kw.items():
            setattr(cs, k, v)
        cs.updated_at = now

    def _reject(self, *reasons: str) -> tuple[str, dict]:
        return "rejected", {"reasons": list(reasons)}

    def _account(self):
        return self.snapshot["account"] if self.snapshot else None

    def _cmd_start(self, s: Session, p: dict, now: datetime):
        cs = self._state(s)
        mode = TradingMode(cs.trading_mode)
        reasons = []
        if cs.kill_switch:
            reasons.append("KILL_SWITCH_ACTIVE")
        if mode == TradingMode.OFF:
            reasons.append("TRADING_MODE_OFF")
        if mode == TradingMode.PAPER and any(v is None for v in (self.settings.paper_initial_balance,self.settings.paper_commission_per_lot_round_turn,self.settings.paper_swap_per_lot_day)):
            reasons.append("PAPER_ASSUMPTIONS_REQUIRED")
        if mode in (TradingMode.DEMO, TradingMode.LIVE):
            if not self.connected or self.snapshot is None:
                reasons.append("BROKER_DISCONNECTED")
            else:
                reasons += self._account_mode_mismatch(mode)
        if mode == TradingMode.LIVE and not self.settings.live_trading_enabled:
            reasons.append("LIVE_TRADING_NOT_ENABLED_ON_HOST")
        rs = s.get(RiskStateRow, 1)
        if rs is None or self.snapshot is None:
            reasons.append("RISK_STATE_UNKNOWN")
        elif rs.data.get("halt_required"):
            reasons += rs.data.get("halt_reasons", [])
        if not cs.active_strategy_ids:reasons.append("NO_ACTIVE_APPROVED_STRATEGY")
        from qros.services.evidence import strategy_eligibility
        for sid in cs.active_strategy_ids or []:
            strategy=s.get(Strategy,sid)
            if strategy is None:reasons.append("UNKNOWN_STRATEGY:"+sid)
            else:reasons.extend(strategy_eligibility(s,strategy,mode.value))
            if strategy is not None and strategy.status=='DEMO_TESTING':
                from qros.services.demo_testing import grant_errors
                reasons.extend(grant_errors(s,strategy,mode.value,now,self._account(),self.settings))
        if mode in (TradingMode.DEMO,TradingMode.LIVE):
            if st.active_firm(s).is_example:reasons.append("EXAMPLE_FIRM_PROFILE")
            if not self.settings.order_execution_enabled:reasons.append("HOST_ORDER_EXECUTION_DISABLED")
        if mode==TradingMode.PAPER and self.adapter.name!='paper':reasons.append("MODE_SWITCH_PENDING_OBSERVATION")
        if rs is not None and rs.data.get('source')!=self.adapter.name:reasons.append("RISK_SOURCE_MISMATCH")
        if mode in (TradingMode.DEMO,TradingMode.LIVE) and rs is not None and rs.data.get('anchor_method')!='observed_at_reset':reasons.append("FIRM_RESET_ANCHOR_NOT_VERIFIED")
        if cs.run_state == RunState.RUNNING.value:
            reasons.append("ALREADY_RUNNING")
        if cs.run_state == RunState.HALTED.value:
            if p.get("confirm") != RESUME_PHRASE:
                reasons.append("RESUME_CONFIRMATION_REQUIRED")
            try:
                h = json.loads(cs.halt_reason or "{}")
            except json.JSONDecodeError:
                h = {}
            codes = set(h.get("codes", []))
            if codes & PERMANENT_HALT_CODES:
                reasons.append("PERMANENT_HALT_ACCOUNT_LIMIT_BREACHED")
            if codes & DAILY_HALT_CODES and rs is not None and h.get("trading_day") == rs.trading_day:
                reasons.append("DAILY_HALT_PERSISTS_UNTIL_NEXT_RESET")
        if reasons:
            return self._reject(*reasons)
        self._set(cs, now, run_state=RunState.RUNNING.value, halt_reason=None)
        return "done", {"run_state": cs.run_state, "note": "Selected strategies remain subject to every evidence, market, reconciliation and risk gate"}

    def _cmd_arm_demo(self,s,p,now):
        from qros.db.models import SystemState
        from qros.services.demo_testing import grant_errors
        from qros.services.execution import set_state,account_key
        cs=self._state(s);account=self._account();errors=[];expiry=[]
        if (cs.trading_mode!='demo' or cs.run_state not in ('stopped','paused_entries') or
                cs.kill_switch or account is None or not cs.active_strategy_ids):
            return self._reject('DEMO_ARM_REQUIRES_STOPPED_OR_PAUSED_DEMO_WITH_SELECTED_EXPERIMENTS')
        if not self.settings.order_execution_enabled:errors.append('HOST_ORDER_EXECUTION_DISABLED')
        for sid in cs.active_strategy_ids:
            strategy=s.get(Strategy,sid)
            if strategy is None or strategy.status!='DEMO_TESTING':errors.append('DEMO_ARM_ONLY_FOR_DEMO_TESTING');continue
            errors.extend(grant_errors(s,strategy,'demo',now,account,self.settings))
            grant=s.get(SystemState,'demo_test_grant:'+sid)
            if grant:expiry.append(grant.data.get('expires_at',''))
        if errors:return self._reject(*errors)
        set_state(s,'demo_forward_arm',{'pending':True,'account_key':account_key(account,'demo'),
            'strategy_ids':list(cs.active_strategy_ids),'expires_at':min(expiry),'armed_at':now.isoformat()},now)
        self._set(cs,now,run_state='paused_entries',halt_reason='DEMO_ARM_WAITING_FOR_READINESS')
        return 'done',{'armed':True,'expires_at':min(expiry),'effect':'Start once all observed demo readiness checks pass; manual commands or executor restart cancel this arm'}

    def _activate_pending_demo(self,s,now):
        from qros.db.models import SystemState
        from qros.services.execution import account_key
        from qros.services.readiness import readiness
        row=s.get(SystemState,'demo_forward_arm')
        if row is None or not row.data.get('pending'):return
        cs=self._state(s);g=row.data;account=self._account()
        valid=(cs.trading_mode=='demo' and cs.run_state=='paused_entries' and not cs.kill_switch and
            account is not None and account.is_demo is True and account_key(account,'demo')==g['account_key'] and
            list(cs.active_strategy_ids)==g['strategy_ids'] and now<datetime.fromisoformat(g['expires_at']))
        if not valid:
            row.data={**g,'pending':False,'cancelled':'state_account_selection_or_expiry_changed'}
            row.updated_at=now;record(s,self.service,'demo.arm.cancelled',{})
        elif readiness(s,self.settings,now)['ready_for_demo']:
            status,result=self._cmd_start(s,{},now)
            if status=='done':
                row.data={**g,'pending':False,'started_at':now.isoformat()};row.updated_at=now
                record(s,self.service,'demo.arm.started',result)

    def _cmd_pause_entries(self, s: Session, p: dict, now: datetime):
        cs = self._state(s)
        if cs.run_state != RunState.RUNNING.value:
            return self._reject(f"NOT_RUNNING:{cs.run_state}")
        self._set(cs, now, run_state=RunState.PAUSED_ENTRIES.value)
        return "done", {"run_state": cs.run_state,
                        "effect": "no new entries; open positions and broker-side stops unchanged"}

    def _cmd_stop(self, s: Session, p: dict, now: datetime):
        cs = self._state(s)
        if cs.run_state == RunState.HALTED.value:
            return self._reject("HALTED_USE_RESUME_OR_RELEASE")
        self._set(cs, now, run_state=RunState.STOPPED.value)
        return "done", {"run_state": cs.run_state,
                        "effect": "strategy evaluation stopped; open positions NOT closed; "
                                  "broker-side stops remain"}

    def _cmd_kill(self, s: Session, p: dict, now: datetime):
        """Kill-switch policy:
        1. Engage kill flag + HALTED immediately (blocks all new orders in the gate).
        2. Cancel ALL pending orders on the account.
        3. Attempt to close ALL open positions at market.
        4. Report every per-ticket failure. Kill flag stays engaged regardless.
        """
        if p.get('confirm')!='KILL':return self._reject('CONFIRMATION_REQUIRED')
        cs = self._state(s)
        self._set(cs, now, kill_switch=True, run_state=RunState.HALTED.value,
                  halt_reason=json.dumps({"codes": ["KILL_SWITCH"], "at": now.isoformat()}))
        s.flush()
        record(s,self.service,'kill.engaged',{'durable_before_broker_actions':True})
        s.commit()
        result: dict[str, Any] = {"kill_switch": True, "cancelled": [], "closed": [], "failures": []}
        if not self.connected:
            result["failures"].append({"ticket": None, "error": "BROKER_DISCONNECTED: could not cancel "
                                       "orders or close positions; broker-side stops remain in place"})
            return "failed", result
        orders = self.adapter.pending_orders()
        positions = self.adapter.positions()
        if orders is None or positions is None:
            result["failures"].append({"ticket": None, "error": "could not query orders/positions"})
        for o in orders or []:
            r = self.adapter.cancel_order(o.ticket)
            (result["cancelled"] if r.ok else result["failures"]).append(
                {"ticket": o.ticket, "message": r.message, "retcode": r.retcode})
        for pos in positions or []:
            r = self.adapter.close_position(pos.ticket)
            (result["closed"] if r.ok else result["failures"]).append(
                {"ticket": pos.ticket, "symbol": pos.symbol, "message": r.message, "retcode": r.retcode})
        return ("failed" if result["failures"] else "done"), result

    def _cmd_release_kill(self, s: Session, p: dict, now: datetime):
        cs = self._state(s)
        if not cs.kill_switch:
            return self._reject("KILL_SWITCH_NOT_ENGAGED")
        if p.get("confirm") != KILL_RELEASE_PHRASE:
            return self._reject("CONFIRMATION_REQUIRED")
        self._set(cs, now, kill_switch=False, run_state=RunState.STOPPED.value, halt_reason=None)
        return "done", {"kill_switch": False, "run_state": cs.run_state}

    def _account_mode_mismatch(self, mode: TradingMode) -> list[str]:
        a = self._account()
        if a is None:
            return ["ACCOUNT_UNKNOWN"]
        if mode == TradingMode.DEMO and a.is_demo is not True:
            return ["DEMO_MODE_REQUIRES_DEMO_ACCOUNT"]
        if mode == TradingMode.LIVE and a.is_demo is not False:
            return ["LIVE_MODE_REQUIRES_REAL_ACCOUNT"]
        return []

    def _cmd_set_mode(self, s: Session, p: dict, now: datetime):
        cs = self._state(s)
        try:
            mode = TradingMode(p.get("mode"))
        except ValueError:
            return self._reject("INVALID_MODE")
        if mode == TradingMode.OFF:
            new_run = cs.run_state if cs.run_state == RunState.HALTED.value else RunState.STOPPED.value
            self._set(cs, now, trading_mode=mode.value, run_state=new_run, active_strategy_ids=[])
            return "done", {"trading_mode": mode.value, "run_state": new_run}
        reasons = []
        if cs.run_state != RunState.STOPPED.value:
            reasons.append(f"STOP_TRADING_FIRST:{cs.run_state}")
        if cs.kill_switch:
            reasons.append("KILL_SWITCH_ACTIVE")
        if mode == TradingMode.PAPER and any(v is None for v in (self.settings.paper_initial_balance,self.settings.paper_commission_per_lot_round_turn,self.settings.paper_swap_per_lot_day)):
            reasons.append("PAPER_ASSUMPTIONS_REQUIRED")
        if mode in (TradingMode.DEMO, TradingMode.LIVE):
            if not self.connected or self.snapshot is None:
                reasons.append("BROKER_DISCONNECTED")
            else:
                reasons += self._account_mode_mismatch(mode)
        if mode == TradingMode.LIVE:
            if not self.settings.live_trading_enabled:
                reasons.append("LIVE_TRADING_NOT_ENABLED_ON_HOST")
            if p.get("confirm") != LIVE_CONFIRM_PHRASE:
                reasons.append("LIVE_CONFIRMATION_PHRASE_REQUIRED")
            n = s.execute(select(Strategy).where(Strategy.status.in_(["LIVE_APPROVED", "ACTIVE"]))).first()
            if n is None:
                reasons.append("NO_LIVE_APPROVED_STRATEGY")
        if reasons:
            return self._reject(*reasons)
        # Strategies must be re-selected for the new mode.
        self._set(cs, now, trading_mode=mode.value, active_strategy_ids=[])
        return "done", {"trading_mode": mode.value}

    def _cmd_set_active_strategies(self, s: Session, p: dict, now: datetime):
        cs = self._state(s)
        ids = p.get("strategy_ids") or []
        mode = TradingMode(cs.trading_mode)
        reasons = []
        if cs.run_state == RunState.RUNNING.value:
            reasons.append("PAUSE_OR_STOP_FIRST")
        if mode == TradingMode.OFF and ids:
            reasons.append("SET_TRADING_MODE_FIRST")
        for sid in ids:
            row = s.get(Strategy, sid)
            if row is None:
                reasons.append(f"UNKNOWN_STRATEGY:{sid}")
            elif row.status not in ALLOWED_STATUS_BY_MODE[mode]:
                reasons.append(f"STRATEGY_{sid}_STATUS_{row.status}_NOT_ALLOWED_IN_{mode.value.upper()}")
        if reasons:
            return self._reject(*reasons)
        self._set(cs, now, active_strategy_ids=list(ids))
        return "done", {"active_strategy_ids": ids}


def _configure_logging() -> None:
    class JsonFmt(logging.Formatter):
        def format(self, r: logging.LogRecord) -> str:
            d = {"ts": datetime.now(timezone.utc).isoformat(), "level": r.levelname, "logger": r.name,
                 "msg": r.getMessage()}
            if r.exc_info:
                d["exc"] = self.formatException(r.exc_info)
            return json.dumps(d)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFmt())
    logging.basicConfig(level=logging.INFO, handlers=[h])


def main(argv: Optional[list[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="QROS-PROP execution service")
    ap.add_argument("--once", action="store_true", help="run a single tick and exit")
    args = ap.parse_args(argv)
    _configure_logging()
    settings = get_settings()
    ex = Executor(settings, make_adapter(settings), session_factory(settings.database_url))
    if args.once:
        from qros.services.process_lock import ProcessLock
        import hashlib,tempfile
        key=hashlib.sha256(str(settings.mt5_path or settings.database_url).encode()).hexdigest()[:20]
        with ProcessLock(Path(tempfile.gettempdir())/'qros-locks'/('executor-'+key+'.lock')):
            try:
                ex.startup();ex.tick()
                print(json.dumps({"connected": ex.connected, "error": ex.last_error}))
            finally:ex.adapter.disconnect()
        return
    ex.run_forever()


if __name__ == "__main__":
    main()


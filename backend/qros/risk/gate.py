"""Pre-trade risk gate.

Every order intent must pass ``check_order``. All checks are evaluated (not
short-circuited) so the full list of reasons is reported. The gate is
deliberately conservative: when information is missing it rejects.

This module must not import strategy, signal, or broker code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from datetime import datetime
from typing import Optional

from qros.config.schemas import FirmProfile, InternalLimits, RunState, TradingMode

from .drawdown import AccountState, evaluate
from .exposure import ExposureLeg, max_directional_risk
from .sizing import ContractSpec, loss_per_lot

# Lifecycle statuses permitted to trade in each mode (see qros.governance).
ALLOWED_STATUS_BY_MODE: dict[TradingMode, set[str]] = {
    TradingMode.OFF: set(),
    TradingMode.PAPER: {"PAPER_TRADING", "DEMO_APPROVED", "LIVE_APPROVED", "ACTIVE"},
    TradingMode.DEMO: {"DEMO_TESTING", "DEMO_APPROVED", "LIVE_APPROVED", "ACTIVE"},
    TradingMode.LIVE: {"LIVE_APPROVED", "ACTIVE"},
}

EPS = 1e-9


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str                 # "buy" | "sell"
    entry_price: float
    stop_price: Optional[float]
    volume: float
    strategy_id: str
    strategy_status: str
    take_profit: Optional[float] = None


@dataclass(frozen=True)
class OpenPosition:
    symbol: str
    base: str
    quote: str
    side: str
    volume: float
    # Remaining loss to stop in account currency. None => no protective stop (unbounded).
    risk_to_stop: Optional[float]


@dataclass(frozen=True)
class InstrumentState:
    spec: ContractSpec
    base: str
    quote: str
    enabled: bool
    max_spread_points: float
    bid: Optional[float]
    ask: Optional[float]
    quote_time: Optional[datetime]


@dataclass(frozen=True)
class GateContext:
    firm: FirmProfile
    limits: InternalLimits
    account: AccountState
    instrument: InstrumentState
    positions: list[OpenPosition]
    now: datetime
    trading_mode: TradingMode
    run_state: RunState
    kill_switch: bool
    broker_connected: bool
    live_trading_enabled: bool
    trades_today: int
    session_realized_pnl: float
    in_trading_hours: bool
    in_news_blackout: bool
    minutes_to_weekend_close: float
    flat_before_weekend_minutes: int
    free_margin: Optional[float] = None
    margin_required: Optional[float] = None


@dataclass
class GateDecision:
    approved: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def check_order(o: OrderIntent, c: GateContext) -> GateDecision:
    # Invalid numeric state must fail closed before divisions, round() or comparisons.
    numeric = {"entry": o.entry_price, "volume": o.volume, "session_realized_pnl":c.session_realized_pnl, "max_spread_points":c.instrument.max_spread_points, "trades_today":c.trades_today, "minutes_to_weekend_close":c.minutes_to_weekend_close,
               **{f"account.{k}": v for k,v in vars(c.account).items()},
               **{f"contract.{k}": v for k,v in vars(c.instrument.spec).items() if k != "symbol"}}
    for key,value in (("stop",o.stop_price),("bid",c.instrument.bid),("ask",c.instrument.ask),("take_profit",o.take_profit),("free_margin",c.free_margin),("margin_required",c.margin_required)):
        if value is not None:numeric[key]=value
    for i,p in enumerate(c.positions):
        numeric[f"position.{i}.volume"]=p.volume
        if p.risk_to_stop is not None:numeric[f"position.{i}.risk"]=p.risk_to_stop
    bad=[key for key,value in numeric.items() if not isinstance(value,(int,float)) or not math.isfinite(value)]
    if bad:return GateDecision(False,["NONFINITE_OR_INVALID_DATA:"+",".join(bad)])
    if min(c.instrument.spec.tick_size,c.instrument.spec.tick_value_per_lot,c.instrument.spec.point,c.instrument.spec.volume_step,c.account.initial_balance)<=0:
        return GateDecision(False,["INVALID_CONTRACT_OR_ACCOUNT"])
    if c.now.tzinfo is None or (c.instrument.quote_time is not None and c.instrument.quote_time.tzinfo is None):
        return GateDecision(False,["NAIVE_TIMESTAMP"])
    if not math.isclose(c.account.initial_balance,c.firm.initial_balance,rel_tol=1e-10):return GateDecision(False,["ACCOUNT_FIRM_INITIAL_MISMATCH"])
    R: list[str] = []
    W: list[str] = []
    m: dict = {}
    init = c.account.initial_balance
    spec = c.instrument.spec

    # --- operational state -------------------------------------------------
    if c.kill_switch:
        R.append("KILL_SWITCH_ACTIVE")
    if c.run_state != RunState.RUNNING:
        R.append(f"RUN_STATE_{c.run_state.value.upper()}")
    if c.trading_mode == TradingMode.OFF:
        R.append("TRADING_MODE_OFF")
    if c.trading_mode == TradingMode.LIVE and not c.live_trading_enabled:
        R.append("LIVE_TRADING_NOT_ENABLED_ON_HOST")
    if c.trading_mode in (TradingMode.DEMO, TradingMode.LIVE) and not c.broker_connected:
        R.append("BROKER_DISCONNECTED")
    if not c.firm.automated_trading_allowed:
        R.append("FIRM_DISALLOWS_AUTOMATED_TRADING")

    # --- strategy governance -----------------------------------------------
    if o.strategy_status not in ALLOWED_STATUS_BY_MODE[c.trading_mode]:
        R.append(f"STRATEGY_STATUS_{o.strategy_status}_NOT_ALLOWED_IN_{c.trading_mode.value.upper()}")

    # --- instrument / market data -----------------------------------------
    inst = c.instrument
    if o.symbol != spec.symbol:
        R.append("SYMBOL_SPEC_MISMATCH")
    if not inst.enabled:
        R.append("INSTRUMENT_DISABLED")
    spread = None
    if inst.bid is None or inst.ask is None or inst.quote_time is None:
        R.append("NO_QUOTE")
    else:
        age = (c.now - inst.quote_time).total_seconds()
        m["quote_age_s"] = age
        if age > c.limits.max_stale_quote_seconds or age < -5:
            R.append("STALE_QUOTE")
        spread = inst.ask - inst.bid
        if spread < 0:
            R.append("CROSSED_QUOTE")
        spread_pts = spread / spec.point
        m["spread_points"] = spread_pts
        if spread_pts > inst.max_spread_points:
            R.append("SPREAD_TOO_WIDE")

    if o.entry_price <= 0 or (o.stop_price is not None and o.stop_price <= 0):
        R.append("NONPOSITIVE_ORDER_PRICE")
    if c.instrument.bid is not None and c.instrument.ask is not None and min(c.instrument.bid,c.instrument.ask)<=0:
        R.append("NONPOSITIVE_QUOTE")
    if any(p.volume<=0 or (p.risk_to_stop is not None and p.risk_to_stop<0) for p in c.positions):
        R.append("INVALID_OPEN_RISK")
    # --- order geometry ------------------------------------------------------
    if o.side not in ("buy", "sell"):
        R.append("INVALID_SIDE")
    if o.stop_price is None:
        R.append("NO_STOP_LOSS")
    else:
        if o.side == "buy" and o.stop_price >= o.entry_price:
            R.append("STOP_WRONG_SIDE")
        if o.side == "sell" and o.stop_price <= o.entry_price:
            R.append("STOP_WRONG_SIDE")
        dist_pts = abs(o.entry_price - o.stop_price) / spec.point
        m["stop_points"] = dist_pts
        if dist_pts < spec.min_stop_points:
            R.append("STOP_BELOW_BROKER_MINIMUM")
    if o.take_profit is not None:
        if (o.side == "buy" and o.take_profit <= o.entry_price) or \
           (o.side == "sell" and o.take_profit >= o.entry_price):
            R.append("TAKE_PROFIT_WRONG_SIDE")

    # --- volume ----------------------------------------------------------------
    if o.volume < spec.volume_min - EPS or o.volume > spec.volume_max + EPS:
        R.append("VOLUME_OUTSIDE_BROKER_LIMITS")
    steps = o.volume / spec.volume_step
    if abs(steps - round(steps)) > 1e-6:
        R.append("VOLUME_NOT_ON_STEP")
    if c.firm.max_lots_per_order is not None and o.volume > c.firm.max_lots_per_order + EPS:
        R.append("FIRM_MAX_LOTS_PER_ORDER")
    total_lots = sum(p.volume for p in c.positions) + o.volume
    if c.firm.max_total_lots is not None and total_lots > c.firm.max_total_lots + EPS:
        R.append("FIRM_MAX_TOTAL_LOTS")

    # --- positions / frequency --------------------------------------------------
    if any(p.symbol == o.symbol for p in c.positions):
        R.append("OPEN_POSITION_ON_INSTRUMENT")
    if len(c.positions) >= c.limits.max_open_positions:
        R.append("MAX_OPEN_POSITIONS")
    if c.trades_today >= c.limits.max_trades_per_day:
        R.append("MAX_TRADES_PER_DAY")
    if -c.session_realized_pnl >= c.limits.max_session_loss_pct / 100.0 * init:
        R.append("MAX_SESSION_LOSS")

    # --- calendar --------------------------------------------------------------
    if not c.in_trading_hours:
        R.append("OUTSIDE_TRADING_HOURS")
    if c.firm.news.enabled and c.in_news_blackout:
        R.append("NEWS_BLACKOUT")
    if not c.firm.weekend_allowed and c.minutes_to_weekend_close <= c.flat_before_weekend_minutes:
        R.append("TOO_CLOSE_TO_WEEKEND_CLOSE")

    # --- risk amounts ------------------------------------------------------------
    unprotected = [p.symbol for p in c.positions if p.risk_to_stop is None]
    if unprotected:
        R.append("UNPROTECTED_OPEN_POSITION:" + ",".join(unprotected))
    open_risk = sum(p.risk_to_stop or 0.0 for p in c.positions)

    new_risk = None
    if o.stop_price is not None and spread is not None:
        new_risk = o.volume * loss_per_lot(spec, o.entry_price, o.stop_price, spread,
                                           c.limits.slippage_buffer_points,
                                           c.firm.commission_per_lot_round_turn)
        m["new_trade_risk"] = new_risk
        m["open_risk"] = open_risk
        sizing_equity = min(c.account.balance, c.account.equity)
        per_trade_cap = c.limits.risk_per_trade_pct / 100.0 * sizing_equity
        m["per_trade_cap"] = per_trade_cap
        if new_risk > per_trade_cap * 1.0001:
            R.append("RISK_PER_TRADE_EXCEEDED")
        sym_risk = sum(p.risk_to_stop or 0.0 for p in c.positions if p.symbol == o.symbol) + new_risk
        if sym_risk > c.limits.max_risk_per_instrument_pct / 100.0 * init + EPS:
            R.append("MAX_RISK_PER_INSTRUMENT")
        if open_risk + new_risk > c.limits.max_total_open_risk_pct / 100.0 * init + EPS:
            R.append("MAX_TOTAL_OPEN_RISK")
        legs = [ExposureLeg(p.symbol, p.base, p.quote, p.side, p.risk_to_stop or 0.0) for p in c.positions]
        legs.append(ExposureLeg(o.symbol, inst.base, inst.quote, o.side, new_risk))
        ccy, ccy_risk = max_directional_risk(legs)
        m["max_currency"] = ccy
        m["max_currency_risk"] = ccy_risk
        if ccy_risk > c.limits.max_currency_risk_pct / 100.0 * init + EPS:
            R.append(f"MAX_CURRENCY_RISK:{ccy}")

    # --- drawdown: worst case if every stop is hit -----------------------------------
    dd = evaluate(c.firm, c.limits, c.account)
    m["effective_floor"] = dd.effective_floor
    if dd.halt_required:
        R.extend(dd.halt_reasons)
    if dd.internal_daily_warning and not dd.internal_daily_stop:
        W.append("INTERNAL_DAILY_WARNING")
    if new_risk is not None:
        worst = dd.internal_measured - open_risk - new_risk
        m["worst_case_equity"] = worst
        if worst <= dd.effective_floor:
            R.append("WORST_CASE_BREACHES_DRAWDOWN_FLOOR")

    if c.free_margin is not None and c.free_margin<0:R.append("NEGATIVE_FREE_MARGIN")
    if c.margin_required is not None and c.margin_required<0:R.append("INVALID_MARGIN_REQUIREMENT")
    # --- margin ------------------------------------------------------------------
    if c.trading_mode in (TradingMode.DEMO, TradingMode.LIVE):
        if c.free_margin is None or c.margin_required is None:
            R.append("MARGIN_UNKNOWN")
        else:
            remaining = c.free_margin - c.margin_required
            if remaining < c.limits.min_free_margin_pct / 100.0 * c.account.equity:
                R.append("INSUFFICIENT_FREE_MARGIN")

    return GateDecision(approved=not R, reasons=R, warnings=W, metrics=m)

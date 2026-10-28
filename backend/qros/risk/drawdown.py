"""Prop-firm drawdown rule evaluation.

Pure functions, no I/O, no imports from strategy/broker code.

Conventions
-----------
* Firm floors are computed exactly as the configured firm rule describes.
* Internal floors are QROS self-imposed and always at least as strict as the
  firm floors (we take the max).
* Internal checks measure ``min(balance, equity)`` — i.e. floating profit is
  never credited but floating loss always is. This is deliberately conservative.
* All internal percentages are expressed as % of the initial balance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

from qros.config.schemas import (AmountBasis, DailyLossAnchor, DrawdownType, FirmProfile,
                                 InternalLimits, Measure)


@dataclass(frozen=True)
class AccountState:
    balance: float
    equity: float
    initial_balance: float
    sod_balance: float           # balance at the firm's daily reset
    sod_equity: float            # equity at the firm's daily reset
    hwm_equity: float            # highest equity ever observed (intraday trailing)
    hwm_eod_balance: float       # highest end-of-day balance (EOD trailing)


@dataclass(frozen=True)
class DrawdownStatus:
    # firm daily
    daily_anchor: float
    daily_limit_amount: float
    daily_floor: float
    daily_measured: float
    daily_used: float
    daily_used_pct_of_limit: float
    firm_daily_breached: bool
    # firm total
    total_base: float
    total_limit_amount: float
    total_floor: float
    total_measured: float
    total_used: float
    total_used_pct_of_limit: float
    firm_total_breached: bool
    # internal
    internal_measured: float
    internal_daily_warning_floor: float
    internal_daily_stop_floor: float
    internal_total_stop_floor: float
    internal_daily_warning: bool
    internal_daily_stop: bool
    internal_total_stop: bool
    effective_floor: float          # tightest of all stop floors
    remaining_to_effective_floor: float

    @property
    def halt_required(self) -> bool:
        return (self.firm_daily_breached or self.firm_total_breached
                or self.internal_daily_stop or self.internal_total_stop)

    @property
    def halt_reasons(self) -> list[str]:
        r = []
        if self.firm_daily_breached:
            r.append("FIRM_DAILY_LOSS_BREACHED")
        if self.firm_total_breached:
            r.append("FIRM_MAX_LOSS_BREACHED")
        if self.internal_daily_stop:
            r.append("INTERNAL_DAILY_STOP")
        if self.internal_total_stop:
            r.append("INTERNAL_TOTAL_STOP")
        return r

    def to_dict(self) -> dict:
        d = asdict(self)
        d["halt_required"] = self.halt_required
        d["halt_reasons"] = self.halt_reasons
        return d


def _measure(m: Measure, a: AccountState) -> float:
    return a.equity if m == Measure.EQUITY else a.balance


def daily_anchor(firm: FirmProfile, a: AccountState) -> float:
    anc = firm.daily_loss.anchor
    if anc == DailyLossAnchor.START_OF_DAY_BALANCE:
        return a.sod_balance
    if anc == DailyLossAnchor.START_OF_DAY_EQUITY:
        return a.sod_equity
    return max(a.sod_balance, a.sod_equity)


def daily_floor(firm: FirmProfile, a: AccountState) -> tuple[float, float, float]:
    """Return (anchor, limit_amount, floor)."""
    anchor = daily_anchor(firm, a)
    basis = a.initial_balance if firm.daily_loss.amount_basis == AmountBasis.INITIAL_BALANCE else anchor
    amount = firm.daily_loss.pct / 100.0 * basis
    return anchor, amount, anchor - amount


def total_floor(firm: FirmProfile, a: AccountState) -> tuple[float, float, float]:
    """Return (base, limit_amount, floor)."""
    amount = firm.max_loss.pct / 100.0 * a.initial_balance
    dt = firm.max_loss.drawdown_type
    if dt == DrawdownType.STATIC:
        base = a.initial_balance
    elif dt == DrawdownType.TRAILING_EOD:
        base = max(a.initial_balance, a.hwm_eod_balance)
    else:
        base = max(a.initial_balance, a.hwm_equity)
    floor = base - amount
    if dt != DrawdownType.STATIC and firm.max_loss.trail_lock_at_initial:
        floor = min(floor, a.initial_balance)
    return base, amount, floor


def evaluate(firm: FirmProfile, limits: InternalLimits, a: AccountState) -> DrawdownStatus:
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vars(a).values()):
        raise ValueError("account state must contain only finite numbers")
    if a.initial_balance <= 0:
        raise ValueError("initial_balance must be positive")
    init = a.initial_balance

    anchor, d_amount, d_floor = daily_floor(firm, a)
    d_meas = _measure(firm.daily_loss.measure, a)
    d_used = max(0.0, anchor - d_meas)

    t_base, t_amount, t_floor = total_floor(firm, a)
    t_meas = _measure(firm.max_loss.measure, a)
    t_used = max(0.0, t_base - t_meas) if firm.max_loss.drawdown_type != DrawdownType.STATIC \
        else max(0.0, init - t_meas)

    i_meas = min(a.balance, a.equity)
    i_anchor = max(a.sod_balance, a.sod_equity)  # internal is always max-anchored
    i_warn = max(d_floor, i_anchor - limits.daily_warning_pct / 100.0 * init)
    i_dstop = max(d_floor, i_anchor - limits.daily_stop_pct / 100.0 * init)
    i_tstop = t_floor + (firm.max_loss.pct - limits.total_stop_pct) / 100.0 * init
    i_tstop = max(i_tstop, t_floor)

    eff = max(d_floor, t_floor, i_dstop, i_tstop)

    return DrawdownStatus(
        daily_anchor=anchor, daily_limit_amount=d_amount, daily_floor=d_floor,
        daily_measured=d_meas, daily_used=d_used,
        daily_used_pct_of_limit=100.0 * d_used / d_amount if d_amount else 0.0,
        firm_daily_breached=d_meas <= d_floor,
        total_base=t_base, total_limit_amount=t_amount, total_floor=t_floor,
        total_measured=t_meas, total_used=t_used,
        total_used_pct_of_limit=100.0 * t_used / t_amount if t_amount else 0.0,
        firm_total_breached=t_meas <= t_floor,
        internal_measured=i_meas,
        internal_daily_warning_floor=i_warn, internal_daily_stop_floor=i_dstop,
        internal_total_stop_floor=i_tstop,
        internal_daily_warning=i_meas <= i_warn,
        internal_daily_stop=i_meas <= i_dstop,
        internal_total_stop=i_meas <= i_tstop,
        effective_floor=eff,
        remaining_to_effective_floor=i_meas - eff,
    )

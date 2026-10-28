"""Position sizing from stop distance and contract specifications.

Volumes are always rounded DOWN to the volume step. If the resulting volume is
below the broker minimum the trade is rejected (never rounded up into more risk).
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from decimal import ROUND_DOWN, Decimal
from typing import Optional


@dataclass(frozen=True)
class ContractSpec:
    symbol: str
    tick_size: float
    tick_value_per_lot: float  # account-currency value of one tick move for 1.0 lot
    point: float
    volume_min: float
    volume_max: float
    volume_step: float
    min_stop_points: float = 0.0


@dataclass(frozen=True)
class SizingResult:
    volume: float
    loss_per_lot: float
    risk_at_volume: float
    rejected: bool
    reason: Optional[str] = None


def loss_per_lot(spec: ContractSpec, entry: float, stop: float, spread: float = 0.0,
                 slippage_points: float = 0.0, commission_per_lot: float = 0.0) -> float:
    """Conservative worst-case loss for 1.0 lot if the stop is hit.

    Adds the current spread (exit on the other side of the book) and a slippage
    buffer to the raw stop distance, plus the round-turn commission.
    """
    dist = abs(entry - stop) + max(spread, 0.0) + max(slippage_points, 0.0) * spec.point
    ticks = dist / spec.tick_size
    return ticks * spec.tick_value_per_lot + max(commission_per_lot, 0.0)


def floor_to_step(volume: float, step: float) -> float:
    v, s = Decimal(str(volume)), Decimal(str(step))
    return float((v / s).to_integral_value(rounding=ROUND_DOWN) * s)


def size_position(spec: ContractSpec, risk_amount: float, entry: float, stop: float,
                  spread: float = 0.0, slippage_points: float = 0.0,
                  commission_per_lot: float = 0.0,
                  max_lots_override: Optional[float] = None) -> SizingResult:
    values=[risk_amount,entry,stop,spread,slippage_points,commission_per_lot]+[v for k,v in vars(spec).items() if k!='symbol']
    if max_lots_override is not None:values.append(max_lots_override)
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):return SizingResult(0.,0.,0.,True,"nonfinite sizing input")
    if min(spec.tick_size,spec.tick_value_per_lot,spec.point,spec.volume_step,spec.volume_min,spec.volume_max)<=0 or spec.volume_min>spec.volume_max:return SizingResult(0.,0.,0.,True,"invalid contract specification")
    if min(spread,slippage_points,commission_per_lot)<0:return SizingResult(0.,0.,0.,True,"negative cost input")
    if risk_amount <= 0:
        return SizingResult(0.0, 0.0, 0.0, True, "risk_amount must be positive")
    if entry <= 0 or stop <= 0 or entry == stop:
        return SizingResult(0.0, 0.0, 0.0, True, "invalid entry/stop")
    dist_points = abs(entry - stop) / spec.point
    if dist_points < spec.min_stop_points:
        return SizingResult(0.0, 0.0, 0.0, True,
                            f"stop distance {dist_points:.1f}pt below broker minimum {spec.min_stop_points}pt")
    lpl = loss_per_lot(spec, entry, stop, spread, slippage_points, commission_per_lot)
    raw = risk_amount / lpl
    cap = spec.volume_max if max_lots_override is None else min(spec.volume_max, max_lots_override)
    vol = floor_to_step(min(raw, cap), spec.volume_step)
    if vol < spec.volume_min:
        return SizingResult(0.0, lpl, 0.0, True,
                            f"computed volume {raw:.4f} below broker minimum {spec.volume_min}")
    return SizingResult(vol, lpl, vol * lpl, False, None)

"""Performance statistics on closed trades. Pure functions.

Returns ``None`` for any metric that is undefined for the given sample rather
than inventing a value (e.g. profit factor with no losing trades).
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from scipy.stats import norm


@dataclass(frozen=True)
class ClosedTrade:
    symbol: str
    strategy_id: str
    exit_time: datetime
    pnl: float                       # net of commission & swap
    slippage_points: Optional[float] = None


def wilson_interval(wins: int, n: int, conf: float = 0.95) -> Optional[tuple[float, float]]:
    if n <= 0:
        return None
    z = norm.ppf(1 - (1 - conf) / 2)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def max_drawdown(pnls: list[float], start_equity: float = 0.0) -> float:
    peak, eq, mdd = start_equity, start_equity, 0.0
    for x in pnls:
        eq += x
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    return mdd


def max_consecutive_losses(pnls: list[float]) -> int:
    best = cur = 0
    for x in pnls:
        cur = cur + 1 if x < 0 else 0
        best = max(best, cur)
    return best


def summarize(trades: Iterable[ClosedTrade]) -> dict:
    ts = sorted(trades, key=lambda t: t.exit_time)
    n = len(ts)
    if n == 0:
        return {"available": False, "n": 0}
    pnls = [t.pnl for t in ts]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    ci = wilson_interval(len(wins), n)
    gross_win, gross_loss = sum(wins), -sum(losses)
    by_symbol: dict[str, list[float]] = defaultdict(list)
    by_strategy: dict[str, list[float]] = defaultdict(list)
    for t in ts:
        by_symbol[t.symbol].append(t.pnl)
        by_strategy[t.strategy_id].append(t.pnl)
    slips = [t.slippage_points for t in ts if t.slippage_points is not None]

    def grp(d: dict[str, list[float]]) -> list[dict]:
        return [{"key": k, "n": len(v), "net": sum(v),
                 "win_rate": sum(1 for x in v if x > 0) / len(v)} for k, v in sorted(d.items())]

    return {
        "available": True,
        "n": n,
        "net_pnl": sum(pnls),
        "win_rate": len(wins) / n,
        "win_rate_ci95": list(ci) if ci else None,
        "avg_win": (gross_win / len(wins)) if wins else None,
        "avg_loss": (-gross_loss / len(losses)) if losses else None,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
        "expectancy": sum(pnls) / n,
        "max_drawdown": max_drawdown(pnls),
        "max_consecutive_losses": max_consecutive_losses(pnls),
        "by_symbol": grp(by_symbol),
        "by_strategy": grp(by_strategy),
        "avg_slippage_points": (sum(slips) / len(slips)) if slips else None,
        "small_sample_warning": n < 30,
    }

"""Currency-decomposed exposure for correlation-aware limits.

Each position's stop-risk is attributed to its two legs: a BUY of EURUSD is
long EUR (+R) and short USD (-R). For each currency we take the larger of the
gross long-risk and gross short-risk (no netting credit across pairs), which is
conservative: long EURUSD + long GBPUSD => USD short-risk = 2R.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class ExposureLeg:
    symbol: str
    base: str
    quote: str
    side: str  # "buy" | "sell"
    risk: float


def currency_exposure(legs: list[ExposureLeg]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(lambda: {"long": 0.0, "short": 0.0})
    for l in legs:
        sgn = 1 if l.side == "buy" else -1
        for ccy, s in ((l.base, sgn), (l.quote, -sgn)):
            out[ccy]["long" if s > 0 else "short"] += l.risk
    return {k: {**v, "max_directional": max(v["long"], v["short"])} for k, v in out.items()}


def max_directional_risk(legs: list[ExposureLeg]) -> tuple[str | None, float]:
    exp = currency_exposure(legs)
    if not exp:
        return None, 0.0
    ccy = max(exp, key=lambda c: exp[c]["max_directional"])
    return ccy, exp[ccy]["max_directional"]

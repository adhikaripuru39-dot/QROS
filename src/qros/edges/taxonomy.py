"""Part 10: Edge Discovery — classification taxonomy and verification metrics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EdgeCategory(str, Enum):
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    EXECUTION = "execution"
    STAT_ARB = "stat_arb"
    UNCLASSIFIED = "unclassified"


@dataclass(frozen=True)
class EdgeSpec:
    """An edge category from the Part 10 ch.1 taxonomy."""

    category: EdgeCategory
    driver: str
    decay_half_life: str
    verification_metric: str


EDGE_TAXONOMY: tuple[EdgeSpec, ...] = (
    EdgeSpec(
        category=EdgeCategory.STRUCTURAL,
        driver="Regulatory mandates, exchange rule mechanics, ETF basket creation/redemption bounds.",
        decay_half_life="Multi-year / Long-term persistence",
        verification_metric="Cointegration test (Engle-Granger) with p-value < 0.001.",
    ),
    EdgeSpec(
        category=EdgeCategory.BEHAVIORAL,
        driver="Persistent human cognitive biases (loss aversion, overreaction, disposition effect).",
        decay_half_life="Months to years (decays slowly as algorithmic share grows)",
        verification_metric="Cross-sectional momentum t-stat > 3.5 across 20-year sample.",
    ),
    EdgeSpec(
        category=EdgeCategory.EXECUTION,
        driver="Co-location speed, queue priority positioning, low-latency market maker inventory management.",
        decay_half_life="Sub-second to milliseconds (decays as market hardware improves)",
        verification_metric="Execution fill rate advantage over public NBBO.",
    ),
    EdgeSpec(
        category=EdgeCategory.STAT_ARB,
        driver="Mean-reversion of cointegrated asset pairs or cross-sectional factor spreads.",
        decay_half_life="Weeks to months",
        verification_metric="Half-life of mean reversion (Ornstein-Uhlenbeck tau < 5 days).",
    ),
)


@dataclass
class EdgeClassification:
    category: EdgeCategory
    confidence: str
    verification_tests: dict[str, float]


def classify_edge(
    cointegration_p: float | None = None,
    momentum_t: float | None = None,
    ou_half_life: float | None = None,
    latency_advantage: bool = False,
) -> EdgeClassification:
    """Classify an edge per the Part 10 taxonomy verification metrics.

    Handbook thresholds:
    - Structural: Engle-Granger p < 0.001
    - Behavioral: cross-sectional momentum t-stat > 3.5
    - Stat-arb: OU half-life < 5 days
    - Execution: latency advantage present

    Returns the first matching category (priority: STRUCTURAL → STAT_ARB → BEHAVIORAL → EXECUTION).
    """
    from qros.governance.policy import DEFAULT_POLICY

    tests: dict[str, float] = {}
    if cointegration_p is not None:
        tests["cointegration_p"] = cointegration_p
        if cointegration_p < DEFAULT_POLICY.cointegration_p_max:
            return EdgeClassification(EdgeCategory.STRUCTURAL, "high", tests)

    if ou_half_life is not None:
        tests["ou_half_life_days"] = ou_half_life
        if ou_half_life < DEFAULT_POLICY.ou_half_life_days_max:
            return EdgeClassification(EdgeCategory.STAT_ARB, "high", tests)

    if momentum_t is not None:
        tests["momentum_t_stat"] = momentum_t
        if momentum_t > DEFAULT_POLICY.behavioral_t_min:
            return EdgeClassification(EdgeCategory.BEHAVIORAL, "high", tests)

    if latency_advantage:
        tests["latency_advantage"] = 1.0
        return EdgeClassification(EdgeCategory.EXECUTION, "medium", tests)

    return EdgeClassification(EdgeCategory.UNCLASSIFIED, "low", tests)
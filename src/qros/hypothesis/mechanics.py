"""Part 6: Hypothesis Generation Framework — the institutional anomaly mechanics catalog.

The handbook heading and Master table claim "15 Core Institutional Anomaly
Mechanics", but the Part 6 docx verbatim documents only 6. We implement the 6
verbatim, scaffold the remaining 9 slots (MECH-07..15) for registration, and
raise on an attempt to exceed 15. No invented mechanics. ADR-003.
"""

from __future__ import annotations

from dataclasses import dataclass


class MechanismSlotOverflow(ValueError):
    """Raised when registering a mechanism past the 15-slot catalog."""


@dataclass(frozen=True)
class AnomalyMechanism:
    id: str
    name: str
    root_cause: str
    decay_condition: str
    measure: str
    falsification_test: str


MECHANISM_CATALOG_MAX = 15

# The six mechanisms documented verbatim in QROS_Part6_Hypothesis_Generation.docx.
_DOCUMENTED_MECHANISMS: tuple[AnomalyMechanism, ...] = (
    AnomalyMechanism(
        id="MECH-01",
        name="Microstructure Liquidity Imbalance",
        root_cause="Market makers adjust quotes based on inventory imbalance and toxic order flow.",
        decay_condition="When market maker competition increases or spread tightens to minimum tick.",
        measure="Order Flow Imbalance (OFI), L2 Quote Size Ratio.",
        falsification_test="t-test on 1-sec mid-price return following extreme OFI.",
    ),
    AnomalyMechanism(
        id="MECH-02",
        name="Dealer Gamma Pinning (GEX)",
        root_cause="Options market makers delta-hedge long/short gamma positions near large open interest strikes.",
        decay_condition="At option expiration or when spot price breaks far outside gamma cluster bounds.",
        measure="Aggregated Net GEX by strike dollar value.",
        falsification_test="Variance ratio test of spot returns near zero-gamma vs high-gamma strikes.",
    ),
    AnomalyMechanism(
        id="MECH-03",
        name="ETF Creation/Redemption Flow",
        root_cause="Authorized Participants (APs) arbitrage between ETF market price and underlying basket NAV.",
        decay_condition="When AP arbitrage latency drops or creation/redemption fees decrease.",
        measure="ETF NAV Premium/Discount spread and daily basket creation volume.",
        falsification_test="Regression of 30-min basket return on AP flow trigger.",
    ),
    AnomalyMechanism(
        id="MECH-04",
        name="End-of-Month Index Rebalancing",
        root_cause="Institutional passive funds trade at market close to match benchmark weight shifts.",
        decay_condition="When hedge funds front-run rebalance announcements fully.",
        measure="Projected rebalance dollar flow derived from constituent weight changes.",
        falsification_test="Cross-sectional return anomaly on rebalance date close.",
    ),
    AnomalyMechanism(
        id="MECH-05",
        name="Volatility Risk Premium (VRP)",
        root_cause="Investors pay a premium for index put options as tail risk insurance.",
        decay_condition="During sustained low-volatility regimes or sudden volatility explosions.",
        measure="Difference between implied volatility (VIX) and realized volatility (Garman-Klass).",
        falsification_test="Long variance swap / delta-hedged short straddle return t-stat.",
    ),
    AnomalyMechanism(
        id="MECH-06",
        name="Cross-Asset Interest Rate Spillover",
        root_cause="Global FX and equity flows react to sovereign yield curve shifts with time delay.",
        decay_condition="When high-frequency algos co-locate cross-venue execution.",
        measure="Yield spread change (10Y US - 10Y Bund) vs FX spot return lead-lag.",
        falsification_test="Granger Causality test of rate changes on FX return.",
    ),
)

# MECH-07..15 = empty slots awaiting documented mechanism registration.
MECHANISM_CATALOG: dict[str, AnomalyMechanism] = {m.id: m for m in _DOCUMENTED_MECHANISMS}
MECHANISM_IDS: frozenset[str] = frozenset(MECHANISM_CATALOG.keys())


def add_mechanism(spec: AnomalyMechanism) -> None:
    """Register a mechanism into the catalog (slots MECH-07..MECH-15)."""
    if spec.id in MECHANISM_CATALOG:
        raise ValueError(f"Mechanism {spec.id} already registered.")
    index = int(spec.id.split("-")[1])
    if not (7 <= index <= MECHANISM_CATALOG_MAX):
        # first 6 are reserved to the documented mechanisms; only 07..15 are addable
        raise MechanismSlotOverflow(
            f"Unregistered catalog slots are MECH-07..{MECHANISM_CATALOG_MAX}; got {spec.id}."
        )
    MECHANISM_CATALOG[spec.id] = spec


def documented_mechanisms() -> tuple[AnomalyMechanism, ...]:
    """The mechanics verbatim from the handbook."""
    return _DOCUMENTED_MECHANISMS
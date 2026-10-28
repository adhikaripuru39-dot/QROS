"""Strategy lifecycle governance.

IDEA → RESEARCH → BACKTESTED → VALIDATED → PAPER_TRADING → DEMO_APPROVED →
LIVE_APPROVED → ACTIVE → SUSPENDED / RETIRED

Rules enforced here (and tested):
* Only listed transitions are allowed.
* Each forward transition declares the evidence keys it requires; the caller
  must supply them (e.g. experiment IDs). Evidence *content* is checked by the
  validation module in Phase 3 — this module only enforces presence.
* Transitions into DEMO_APPROVED, LIVE_APPROVED and ACTIVE require a human
  actor (``actor_kind == "owner"``). The research scheduler ("system") can
  never approve deployment.
* Anyone (system or owner) may SUSPEND; only the owner may RETIRE or reinstate.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StrategyStatus(str, Enum):
    IDEA = "IDEA"
    DEMO_TESTING = "DEMO_TESTING"
    RESEARCH = "RESEARCH"
    BACKTESTED = "BACKTESTED"
    VALIDATED = "VALIDATED"
    PAPER_TRADING = "PAPER_TRADING"
    DEMO_APPROVED = "DEMO_APPROVED"
    LIVE_APPROVED = "LIVE_APPROVED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


S = StrategyStatus


@dataclass(frozen=True)
class TransitionRule:
    target: StrategyStatus
    criteria: str
    required_evidence: tuple[str, ...] = ()
    owner_only: bool = False


TRANSITIONS: dict[StrategyStatus, list[TransitionRule]] = {
    S.IDEA: [
        TransitionRule(S.DEMO_TESTING, "Owner-authorized unvalidated broker demo experiment, account/runtime/code bound and expiring; no live eligibility.", ("demo_test_grant",), owner_only=True),
        TransitionRule(S.RESEARCH, "Hypothesis fully specified: rationale, entry/exit/stop, "
                       "falsifiable predictions, failure conditions.", ("hypothesis_id",)),
        TransitionRule(S.RETIRED, "Abandoned before research.", owner_only=True),
    ],
    S.RESEARCH: [
        TransitionRule(S.BACKTESTED, "Execution-realistic backtest on DEVELOPMENT split completed "
                       "and registered.", ("experiment_id", "dataset_version")),
        TransitionRule(S.RETIRED, "Rejected during research (reason recorded).", ("rejection_reason",)),
    ],
    S.BACKTESTED: [
        TransitionRule(S.VALIDATED, "Passed pre-registered validation gates on VALIDATION split and "
                       "walk-forward; single untouched OOS evaluation passed.",
                       ("validation_report_id", "oos_experiment_id")),
        TransitionRule(S.RETIRED, "Failed validation (reason recorded).", ("rejection_reason",)),
    ],
    S.VALIDATED: [
        TransitionRule(S.PAPER_TRADING, "Owner enabled forward paper trading.", owner_only=True),
        TransitionRule(S.RETIRED, "Retired.", ("rejection_reason",), owner_only=True),
    ],
    S.PAPER_TRADING: [
        TransitionRule(S.DEMO_APPROVED, "Forward paper results consistent with validation "
                       "expectations over the pre-registered minimum trade count.",
                       ("paper_report_id",), owner_only=True),
        TransitionRule(S.SUSPENDED, "Degradation or anomaly.", ("reason",)),
    ],
    S.DEMO_APPROVED: [
        TransitionRule(S.LIVE_APPROVED, "Demo execution quality (slippage, fills, reconciliation) "
                       "acceptable; owner signs off.", ("demo_report_id",), owner_only=True),
        TransitionRule(S.SUSPENDED, "Degradation or anomaly.", ("reason",)),
    ],
    S.LIVE_APPROVED: [
        TransitionRule(S.ACTIVE, "Owner activated for live trading.", owner_only=True),
        TransitionRule(S.SUSPENDED, "Suspended before activation.", ("reason",)),
    ],
    S.ACTIVE: [
        TransitionRule(S.SUSPENDED, "Degradation, distribution shift, risk event or owner decision.",
                       ("reason",)),
    ],
    S.SUSPENDED: [
        TransitionRule(S.PAPER_TRADING, "Owner reinstated to paper after review.", ("review_note",),
                       owner_only=True),
        TransitionRule(S.RETIRED, "Retired after suspension.", ("reason",), owner_only=True),
    ],
    S.DEMO_TESTING: [
        TransitionRule(S.SUSPENDED, "Demo experiment stopped or review required.", ("reason",)),
        TransitionRule(S.RETIRED, "Demo experiment retired.", ("reason",), owner_only=True),
    ],
    S.RETIRED: [],
}


class TransitionError(ValueError):
    pass


def allowed_targets(current: StrategyStatus) -> list[TransitionRule]:
    return TRANSITIONS[current]


def check_transition(current: StrategyStatus, target: StrategyStatus, actor_kind: str,
                     evidence: dict[str, str]) -> TransitionRule:
    if actor_kind not in ("owner", "system"):
        raise TransitionError("actor_kind must be 'owner' or 'system'")
    rule = next((r for r in TRANSITIONS[current] if r.target == target), None)
    if rule is None:
        raise TransitionError(f"transition {current.value} -> {target.value} is not permitted")
    if rule.owner_only and actor_kind != "owner":
        raise TransitionError(f"transition to {target.value} requires owner authorisation")
    missing = [k for k in rule.required_evidence if not str(evidence.get(k, "")).strip()]
    if missing:
        raise TransitionError(f"missing required evidence: {', '.join(missing)}")
    return rule

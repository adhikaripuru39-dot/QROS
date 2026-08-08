"""Part 7: The 15-Stage Institutional Research Workflow (gatekeeper-controlled)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class CriterionSpec:
    """An exit-criterion test read from the run context."""

    id: str
    field: str  # key in the run context dict
    operator: Literal["<", "<=", ">", ">=", "==", "!="]
    target: float | bool
    label: str


@dataclass(frozen=True)
class StageDef:
    number: int
    name: str
    outputs: tuple[str, ...]
    exit_criteria: tuple[CriterionSpec, ...]
    approvers: tuple[str, ...]


def _c(
    cid: str,
    field: str,
    op: Literal["<", "<=", ">", ">=", "==", "!="],
    target: float | bool,
    label: str,
) -> CriterionSpec:
    return CriterionSpec(id=cid, field=field, operator=op, target=target, label=label)


# Part 7 ch.1 — exact handbook stage data.
STAGES: list[StageDef] = [
    StageDef(
        number=1, name="Idea Generation",
        outputs=("idea_note", "mechanism_description"),
        exit_criteria=(_c("review_seq", "qr_team_review", "==", True, "Peer Review Approval by QR Team"),),
        approvers=("QUANT_RESEARCHER",),
    ),
    StageDef(
        number=2, name="Literature Review",
        outputs=("annotated_bibliography", "academic_matrix"),
        exit_criteria=(_c("novel_edge", "edge_novelty_verified", "==", True, "Novel edge vs published papers"),),
        approvers=("QUANT_RESEARCHER",),
    ),
    StageDef(
        number=3, name="Theory Formation",
        outputs=("mechanism_spec",),
        exit_criteria=(_c("head_approval", "head_of_research_mechanism_approved", "==", True, "Head of Research Mechanism Approval"),),
        approvers=("HEAD_OF_RESEARCH",),
    ),
    StageDef(
        number=4, name="Hypothesis Creation",
        outputs=("hyp_doc_locked",),
        exit_criteria=(
            _c("lock_ok", "hyp_sha256_locked", "==", True, "SHA-256 Lock & Registration"),
            _c("registered", "hyp_registered", "==", True, "Registered in Registry"),
        ),
        approvers=("HEAD_OF_RESEARCH", "LEAD_STATISTICIAN"),
    ),
    StageDef(
        number=5, name="Data Collection",
        outputs=("data_request", "schema_spec"),
        exit_criteria=(_c("lineage_pass", "data_engineer_lineage_audit", "==", True, "Data Engineer Data Lineage Audit"),),
        approvers=("DATA_ENGINEER",),
    ),
    StageDef(
        number=6, name="Data Cleaning",
        outputs=("cleansed_snapshot", "quality_metrics"),
        exit_criteria=(
            _c("no_bad_tick", "zero_bad_ticks", "==", True, "Zero Bad Tick"),
            _c("time_audit", "timestamp_audit_pass", "==", True, "Timestamp Audit Pass"),
        ),
        approvers=("DATA_ENGINEER",),
    ),
    StageDef(
        number=7, name="Feature Engineering",
        outputs=("feature_frame", "stationarity_metrics"),
        exit_criteria=(_c("adf_p", "max_adf_p", "<", 0.05, "ADF Test p-value < 0.05 on all features"),),
        approvers=("LEAD_STATISTICIAN",),
    ),
    StageDef(
        number=8, name="Exploratory Analysis",
        outputs=("eda_notebook", "correlation_matrix"),
        exit_criteria=(_c("vif", "max_vif", "<", 10.0, "Multicollinearity Check (VIF < 10.0)"),),
        approvers=("LEAD_STATISTICIAN",),
    ),
    StageDef(
        number=9, name="Statistical Testing",
        outputs=("in_sample_report",),
        exit_criteria=(
            _c("tstat", "t_statistic", ">", 3.0, "t-statistic > 3.0"),
            _c("pval", "p_value", "<", 0.001, "p-value < 0.001"),
        ),
        approvers=("HEAD_OF_RESEARCH", "LEAD_STATISTICIAN"),
    ),
    StageDef(
        number=10, name="Robustness Testing",
        outputs=("param_sensitivity", "stress_suite"),
        exit_criteria=(_c("robust", "max_degradation_ratio", "<", 0.50, "Stable across +/-50% parameter shift"),),
        approvers=("LEAD_STATISTICIAN",),
    ),
    StageDef(
        number=11, name="Walk Forward Validation",
        outputs=("walk_forward_matrix",),
        exit_criteria=(
            _c("oos_sr", "oos_sharpe", ">", 2.0, "OOS Sharpe Ratio > 2.0"),
            _c("max_dd", "max_drawdown", "<", 0.15, "Max Drawdown < 15%"),
        ),
        approvers=("HEAD_OF_RESEARCH",),
    ),
    StageDef(
        number=12, name="Replication",
        outputs=("replication_result",),
        exit_criteria=(_c("corr2", "corr_with_secondary", ">", 0.999, "Secondary QR Code Match (>99.9% correlation)"),),
        approvers=("LEAD_STATISTICIAN",),
    ),
    StageDef(
        number=13, name="Documentation",
        outputs=("monograph", "code_manual"),
        exit_criteria=(_c("peer", "peer_review_signoff", "==", True, "Peer Review Sign-off by Research Division"),),
        approvers=("HEAD_OF_RESEARCH",),
    ),
    StageDef(
        number=14, name="Research Approval",
        outputs=("ic_presentation",),
        exit_criteria=(_c("ic", "ic_signoff", "==", True, "Formal IC Sign-Off (Head of Research + Risk)"),),
        approvers=("INVESTMENT_COMMITTEE",),
    ),
    StageDef(
        number=15, name="Model Development",
        outputs=("prod_architecture_spec",),
        exit_criteria=(_c("handoff", "handoff_approved", "==", True, "Hand-off to Quant Development Division"),),
        approvers=("QUANT_DEV",),
    ),
]


def get_stage(n: int) -> StageDef:
    for s in STAGES:
        if s.number == n:
            return s
    raise KeyError(f"No such stage: {n}")


def all_stages() -> tuple[StageDef, ...]:
    return tuple(STAGES)
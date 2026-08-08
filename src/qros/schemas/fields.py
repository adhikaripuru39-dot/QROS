"""Authoritative field-ID tables from the QROS Master Handbook.

- HYP_FIELDS : 22 fields of the Hypothesis Document (Part 5)
- EXP_FIELDS : 17 fields of the Experiment Record (Part 9)

These are the authority tables; registries validate against them verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldDef:
    """A required field of an institutional document."""

    id: str
    name: str
    spec: str


# Part 5: Research Hypothesis Management — 22-field Hypothesis Document.
HYP_FIELDS: tuple[FieldDef, ...] = (
    FieldDef("HYP-01", "Hypothesis ID", "Globally unique identifier (e.g., HYP-EQUITY-MICROSTRUCTURE-2026-0042)."),
    FieldDef("HYP-02", "Research Question", "Precise scientific question (e.g., Does high L2 order book imbalance predict 5-minute forward returns?)."),
    FieldDef("HYP-03", "Market Logic", "Microstructural mechanism or market mechanics driving the phenomenon."),
    FieldDef("HYP-04", "Economic Theory", "Underlying economic equilibrium or risk compensation theory."),
    FieldDef("HYP-05", "Behavioral Theory", "Cognitive bias, loss aversion, or institutional constraint causing market mispricing."),
    FieldDef("HYP-06", "Expected Edge", "Quantified expected edge capacity, direction, and decay half-life."),
    FieldDef("HYP-07", "Market Conditions", "Specific market regimes (e.g., High Volatility, Elevated Spread) where edge manifests."),
    FieldDef("HYP-08", "Assumptions", "Core assumptions regarding liquidity, execution costs, and market impact."),
    FieldDef("HYP-09", "Independent Variables", "Primary predictive features (e.g., Order Flow Imbalance, VPIN)."),
    FieldDef("HYP-10", "Dependent Variables", "Target return metric (e.g., 5-minute mid-price forward return)."),
    FieldDef("HYP-11", "Control Variables", "Confounding market factors held constant (e.g., Sector Return, Market Beta)."),
    FieldDef("HYP-12", "Expected Direction", "Theoretical sign of the relationship (Positive / Negative correlation)."),
    FieldDef("HYP-13", "Supporting Literature", "Academic papers or empirical industry research validating the mechanism."),
    FieldDef("HYP-14", "Contradicting Literature", "Academic arguments against the persistence of the anomaly."),
    FieldDef("HYP-15", "Alternative Explanations", "Competing hypotheses (e.g., risk premium vs behavioral mispricing vs noise)."),
    FieldDef("HYP-16", "Data Requirements", "Required dataset snapshot versions, depth levels, and sample frequency."),
    FieldDef("HYP-17", "Testing Requirements", "Statistical tests (e.g., t-stat, Deflated Sharpe Ratio, Walk-Forward CV)."),
    FieldDef("HYP-18", "Acceptance Criteria", "Strict thresholds (e.g., OOS Sharpe Ratio > 2.0, t-stat > 3.0, DSR p-value < 0.01)."),
    FieldDef("HYP-19", "Rejection Criteria", "Conditions triggering immediate hypothesis rejection (e.g., t-stat < 2.0)."),
    FieldDef("HYP-20", "Confidence Level", "Required statistical significance level (e.g., 99.5% confidence)."),
    FieldDef("HYP-21", "Replication Requirements", "Independent replication by a secondary Quant Researcher."),
    FieldDef("HYP-22", "Retirement Criteria", "Performance decay triggers for retiring a live production alpha factor."),
)

# Part 9: Experiment Tracking System — 17-field Experiment Record.
EXP_FIELDS: tuple[FieldDef, ...] = (
    FieldDef("EXP-01", "Experiment ID", "Globally unique hash (e.g., EXP-20260806-991A04)."),
    FieldDef("EXP-02", "Date & Timestamp", "ISO 8601 UTC execution timestamp."),
    FieldDef("EXP-03", "Researcher Name", "Quant researcher ID and division email tag."),
    FieldDef("EXP-04", "Dataset Version Hash", "SHA-256 hash of exact dataset snapshot used."),
    FieldDef("EXP-05", "Code Version / Git Commit", "Full 40-character git commit hash of code repository."),
    FieldDef("EXP-06", "Feature Version", "Feature store version string (e.g., feat_v2.4.1)."),
    FieldDef("EXP-07", "Hypothesis ID", "Foreign key linking to registered HYP document."),
    FieldDef("EXP-08", "Objective", "Primary optimization/validation target (e.g., Maximizing DSR)."),
    FieldDef("EXP-09", "Hyperparameter Map", "Complete JSON dictionary of all hyperparameters."),
    FieldDef("EXP-10", "Statistical Test Output", "Recorded t-stat, p-value, DSR score, and Sharpe Ratio."),
    FieldDef("EXP-11", "Key Metrics", "In-Sample & Out-of-Sample Sharpe, Max DD, Turnover %."),
    FieldDef("EXP-12", "Conclusions", "Structured text summary of empirical findings."),
    FieldDef("EXP-13", "Limitations", "Identified edge constraints (e.g., high execution sensitivity)."),
    FieldDef("EXP-14", "Next Actions", "Action items (e.g., promote to Walk-Forward CV or Reject)."),
    FieldDef("EXP-15", "Approval Status", "Workflow state (PENDING_REVIEW, APPROVED, REJECTED)."),
    FieldDef("EXP-16", "Peer Review Notes", "Audit comments from Lead Statistician / Peer QR."),
    FieldDef("EXP-17", "Replication Status", "Verification indicator from independent replication run."),
)

HYP_ALL_IDS: frozenset[str] = frozenset(f.id for f in HYP_FIELDS)
EXP_ALL_IDS: frozenset[str] = frozenset(f.id for f in EXP_FIELDS)
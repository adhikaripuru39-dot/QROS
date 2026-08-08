"""QROS institutional roles and responsibilities (Part 1 ch.1.3, Part 7 approvers)."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """Institutional roles with sign-off authority per Part 1 ch.1.3."""

    DATA_ENGINEER = "DATA_ENGINEER"
    QUANT_RESEARCHER = "QUANT_RESEARCHER"
    STATISTICAL_RESEARCHER = "STATISTICAL_RESEARCHER"
    DATA_GOVERNANCE_OFFICER = "DATA_GOVERNANCE_OFFICER"
    HEAD_OF_RESEARCH = "HEAD_OF_RESEARCH"
    LEAD_STATISTICIAN = "LEAD_STATISTICIAN"
    INVESTMENT_COMMITTEE = "INVESTMENT_COMMITTEE"
    QUANT_DEV = "QUANT_DEV"


# Responsibilities per Part 1 ch.1.3 Institutional Roles & Responsibilities Matrix.
ROLE_MATRIX: dict[Role, tuple[str, ...]] = {
    Role.DATA_ENGINEER: (
        "Feed handlers, hardware PTP capture, exchange binary protocol decoding (SBE, ITCH, FIX), data lake storage.",
        "Low-latency ingestion daemons, Parquet/KDB+ data streams.",
    ),
    Role.QUANT_RESEARCHER: (
        "Validation specifications, microstructural feature requirements, domain cleaning rules, bias audit specs.",
        "Data Quality Requirements, Alpha Feature Specs.",
    ),
    Role.STATISTICAL_RESEARCHER: (
        "Statistical anomaly detection algorithms, stationarity verification, noise and outlier modeling.",
        "Outlier Filters, Robustness Metrics.",
    ),
    Role.DATA_GOVERNANCE_OFFICER: (
        "Vendor SLA compliance, data licensing audit, point-in-time metadata validation, regulatory compliance.",
        "Data Catalog Sign-Off, Compliance Audits.",
    ),
    Role.HEAD_OF_RESEARCH: (
        "Research leadership, hypothesis and theory approval, pipeline gate sign-off, IC presentation ownership.",
        "Stage 3/4/9/11/13 sign-off authority.",
    ),
    Role.LEAD_STATISTICIAN: (
        "Statistical rigor, DSR/FDR/FWER enforcement, stationarity and multicollinearity audit.",
        "Stage 4/7/8/9/10/12 statistical sign-off.",
    ),
    Role.INVESTMENT_COMMITTEE: (
        "Final research approval for capital allocation; risk sign-off.",
        "Stage 14 formal IC sign-off.",
    ),
    Role.QUANT_DEV: (
        "Production model engineering and hand-off from research.",
        "Stage 15 hand-off acceptance.",
    ),
}
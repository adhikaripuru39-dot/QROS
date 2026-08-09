"""Tests for the governance core (policy, roles, constitution, decision log)."""

from __future__ import annotations

import pytest

from qros.governance.constitution import VERSION, registered_amendments
from qros.governance.decision_log import Decision, export_markdown, load, record_decision
from qros.governance.policy import DEFAULT_POLICY
from qros.governance.roles import ROLE_MATRIX, Role


def test_policy_literals_match_handbook():
    p = DEFAULT_POLICY
    assert p.adf_p_max == 0.05
    assert p.vif_max == 10.0
    assert p.corr_max == 0.85
    assert p.dsr_p_max == 0.01
    assert p.fdr_q_max == 0.05
    assert p.holm_alpha == 0.01
    assert p.cpcv_min_paths == 16
    assert p.pbo_max == 0.10
    assert p.permutation_n == 10_000
    assert p.stage9_t_min == 3.0
    assert p.stage9_p_max == 0.001
    assert p.stage10_param_shift == 0.50
    assert p.stage11_oos_sharpe_min == 2.0
    assert p.stage11_maxdd_max == 0.15
    assert p.stage12_corr_min == 0.999
    assert p.cointegration_p_max == 0.001
    assert p.behavioral_t_min == 3.5
    assert p.ou_half_life_days_max == 5.0
    assert p.mad_z_threshold == 8.0
    assert p.missing_alert_ratio == 0.0005


def test_eight_roles_matrix():
    assert len(ROLE_MATRIX) == 8
    names = {r.value for r in ROLE_MATRIX}
    assert "DATA_ENGINEER" in names
    assert "INVESTMENT_COMMITTEE" in names


def test_constitution_version_and_ratification():
    assert "1.0" in VERSION
    amendments = registered_amendments()
    assert any(a["id"] == "AMEND-001" and a["status"] == "RATIFIED" for a in amendments)


def test_decision_log_add_and_export(tmp_path):
    path = tmp_path / "decisions.json"
    record_decision(path, Decision("ADR-TEST-01", "2026-08-08", "title", "ctx", "decision"))
    assert len(load(path)) == 1
    md = tmp_path / "decisions.md"
    export_markdown(md, load(path))
    assert md.exists() and "ADR-TEST-01" in md.read_text(encoding="utf-8")


def test_policy_render_summary_shape():
    from qros.governance.policy import render_summary

    summary = render_summary(DEFAULT_POLICY)
    assert summary["dsr_p_max"] == 0.01
    assert isinstance(summary, dict)
"""Tests for edges package (Part 10) — including the mandatory 5-diagnostic audit contract."""

from __future__ import annotations

import numpy as np
import pytest

from qros.edges.audit import REQUIRED_DIAGNOSTICS, audit_false_edge
from qros.edges.taxonomy import EDGE_TAXONOMY, EdgeCategory, classify_edge

REQUIRED_SET = set(REQUIRED_DIAGNOSTICS)


def test_taxonomy_has_four_categories():
    assert len(EDGE_TAXONOMY) == 4
    cats = {e.category for e in EDGE_TAXONOMY}
    assert cats == {EdgeCategory.STRUCTURAL, EdgeCategory.BEHAVIORAL, EdgeCategory.EXECUTION, EdgeCategory.STAT_ARB}


def test_classify_structural():
    result = classify_edge(cointegration_p=0.0005)
    assert result.category == EdgeCategory.STRUCTURAL


def test_classify_stat_arb():
    result = classify_edge(ou_half_life=2.5)
    assert result.category == EdgeCategory.STAT_ARB


def test_classify_behavioral():
    result = classify_edge(momentum_t=4.0)
    assert result.category == EdgeCategory.BEHAVIORAL


def test_classify_unclassified():
    result = classify_edge(momentum_t=1.0)
    assert result.category == EdgeCategory.UNCLASSIFIED


def test_all_five_mandatory_diagnostics_always_present():
    """Audit always returns all five required diagnostics, even with no evidence."""
    r = np.random.default_rng(0).normal(0.001, 0.01, 300)
    audit = audit_false_edge(r, n_trials=5)  # no optional evidence supplied
    diag = {c.diagnostic: c for c in audit.checks}
    assert REQUIRED_SET.issubset(diag.keys())
    # every mandatory diagnostic must exist exactly once
    assert len(audit.mandatory_checks()) == len(REQUIRED_DIAGNOSTICS)
    # with no evidence the audit fails closed
    assert audit.overall_pass is False


def test_missing_execution_and_capacity_evidence_fails_closed():
    """Missing execution/capacity evidence is reported and blocks the audit."""
    r = np.random.default_rng(0).normal(0.001, 0.01, 300)
    audit = audit_false_edge(r, n_trials=5, perturbed_returns=r * 0.98)  # good curve evidence only
    diag = {c.diagnostic: c for c in audit.checks}
    assert "insufficient evidence" in diag["execution_mirage"].reason
    assert "insufficient evidence" in diag["capacity_bottleneck"].reason
    assert diag["execution_mirage"].passed is False
    assert diag["capacity_bottleneck"].passed is False
    assert audit.overall_pass is False


def test_fully_evidenced_audit_passes_only_when_all_five_pass():
    """A fully evidenced edge passes only when every mandatory diagnostic passes.

    We construct one series where all five diagnostics pass, then re-run with a
    single capacity failure and confirm the audit no longer passes.
    """
    rng = np.random.default_rng(11)
    # Two-regime series: strong +ve edge in first half, weaker second half.
    r = np.concatenate([rng.normal(0.006, 0.01, 150), rng.normal(0.001, 0.01, 150)])
    perturbed = r * 0.98  # low perturbation degradation -> curve_fitting passes

    def _audit(capacity_pnl):
        return audit_false_edge(
            r,
            n_trials=2,
            perturbed_returns=perturbed,
            execution_slippage_bps=1.0,
            tiny_size_pnl=1000.0,
            institutional_size_pnl=capacity_pnl,
        )

    good = _audit(capacity_pnl=60_000.0)  # ratio 60 > 0.5 -> passes
    diag_good = {c.diagnostic: c for c in good.checks}
    for d in REQUIRED_DIAGNOSTICS:
        assert diag_good[d].passed is True, f"unexpectedly failed: {d} -> {diag_good[d].reason}"
    assert good.overall_pass is True

    # Capacity fails (ratio ~0.04 < 0.5) -> overall must NOT pass
    bad = _audit(capacity_pnl=40.0)
    diag_bad = {c.diagnostic: c for c in bad.checks}
    assert diag_bad["capacity_bottleneck"].passed is False
    assert bad.overall_pass is False


def test_curve_fitting_contract_not_weakened():
    """Part of the contract: a destroyed edge must be flagged by curve_fitting.

    This is a contract test — it must never be weakened to hide the diagnostic;
    it also ensures the (previously only-partial) audit still reports all five.
    """
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.01, 300)
    perturbed = r * 0.2  # 80% perturbation destroys the edge
    audit = audit_false_edge(r, n_trials=5, perturbed_returns=perturbed)
    diag = {c.diagnostic: c for c in audit.checks}
    assert diag["curve_fitting"].passed is False
    # all five mandatory diagnostics must be present even here
    assert REQUIRED_SET.issubset(diag.keys())
    assert audit.overall_pass is False


def test_false_edge_structural_pass():
    """The optional sixth diagnostic (structural cointegration) is supplementary."""
    rng = np.random.default_rng(3)
    y = np.cumsum(rng.normal(0, 1, 300))
    x = y + rng.normal(0, 0.2, 300)
    audit = audit_false_edge(rng.normal(0.0005, 0.01, 300), n_trials=2, cointegration_pair=(y, x))
    diag = {c.diagnostic: c for c in audit.checks}
    assert diag["structural_cointegration"].passed is True
    # supplementary diagnostic does not replace the five mandatory ones
    assert REQUIRED_SET.issubset(diag.keys())
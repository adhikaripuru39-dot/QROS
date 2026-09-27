"""End-to-end integration tests for QROS statistical evaluation pipeline."""

import numpy as np
import pytest
from qros.pipeline.evaluation import evaluate_statistical_profile
from qros.schemas.validation_profile import get_default_profile
from qros.tracking.lineage import capture_lineage


def test_full_pipeline_promising_candidate():
    np.random.seed(42)
    # Generate 500 synthetic trade returns with strong positive mean
    gross_returns = np.random.normal(loc=0.003, scale=0.015, size=500)

    profile = get_default_profile("CLASS-II")

    # Evaluate
    result = evaluate_statistical_profile(
        returns_net=gross_returns,
        validation_profile=profile,
        hypothesis_id="QROS-HYP-000001",
        trial_count_k=5,
        observation_count_t=20000,
        calendar_span_years=3.5,
        n_bootstrap_resamples=1000,
        random_seed=42,
    )

    assert result.sample_size_n == 500
    assert result.passed_sample_power is True
    assert result.profit_factor_net > 1.35
    assert result.annualized_sharpe_net > 1.40
    assert result.passed_bootstrap_ci is True
    assert result.overall_gate_pass is True
    assert len(result.failure_reasons) == 0


def test_full_pipeline_failing_candidate():
    np.random.seed(42)
    # Generate noisy / slightly negative trade returns
    gross_returns = np.random.normal(loc=-0.0005, scale=0.015, size=200)

    profile = get_default_profile("CLASS-II")

    result = evaluate_statistical_profile(
        returns_net=gross_returns,
        validation_profile=profile,
        hypothesis_id="QROS-HYP-000002",
        trial_count_k=100,
        observation_count_t=5000,
        calendar_span_years=1.0,
        n_bootstrap_resamples=500,
        random_seed=42,
    )

    assert result.passed_sample_power is False  # N=200 < 400
    assert result.passed_profit_factor is False
    assert result.passed_sharpe is False
    assert result.passed_bootstrap_ci is False
    assert result.overall_gate_pass is False
    assert len(result.failure_reasons) > 0


def test_lineage_capture():
    lineage = capture_lineage(
        dataset_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        random_seed=42,
        validation_profile_name="INTRADAY-MOM_DEFAULT",
    )
    assert len(lineage.dataset_sha256) == 64
    assert lineage.random_seed == 42
    assert lineage.python_version is not None
    assert "INTRADAY-MOM" in lineage.validation_profile_name

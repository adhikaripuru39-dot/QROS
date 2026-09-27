"""Validation Profile differentiation tests across Research Classes I through V.

Demonstrates that identical synthetic return profiles receive distinct evaluation outcomes
calibrated to their declared Validation Regime.
"""

import numpy as np
import pytest
from qros.pipeline.costs import CostModelConfig, TransactionCostModel
from qros.pipeline.evaluation import evaluate_statistical_profile
from qros.schemas.validation_profile import get_default_profile


def test_class_hurdle_differentiation():
    """Verify that sample size N=250 and Sharpe=1.35 fails Class I/II but passes Class III."""
    np.random.seed(42)
    # Generate 250 discrete trades with positive Sharpe and PF > 1.30
    returns = np.random.normal(loc=0.0035, scale=0.02, size=250)

    profile_class1 = get_default_profile("CLASS-I")  # N >= 1000, SR >= 1.80
    profile_class2 = get_default_profile("CLASS-II")  # N >= 400, SR >= 1.40
    profile_class3 = get_default_profile("CLASS-III")  # N >= 150, SR >= 1.20

    # Evaluate against Class I
    res1 = evaluate_statistical_profile(
        returns_net=returns,
        validation_profile=profile_class1,
        hypothesis_id="QROS-HYP-000101",
        trial_count_k=2,
        observation_count_t=60000,
        calendar_span_years=3.0,
        n_bootstrap_resamples=500,
        random_seed=42,
    )
    assert res1.passed_sample_power is False  # N=250 < 1000
    assert res1.overall_gate_pass is False
    assert any("N=250 < 1000" in f for f in res1.failure_reasons)

    # Evaluate against Class II
    res2 = evaluate_statistical_profile(
        returns_net=returns,
        validation_profile=profile_class2,
        hypothesis_id="QROS-HYP-000102",
        trial_count_k=2,
        observation_count_t=20000,
        calendar_span_years=3.5,
        n_bootstrap_resamples=500,
        random_seed=42,
    )
    assert res2.passed_sample_power is False  # N=250 < 400
    assert res2.overall_gate_pass is False
    assert any("N=250 < 400" in f for f in res2.failure_reasons)

    # Evaluate against Class III (Swing / StatArb: N >= 150, SR >= 1.20, PF >= 1.30)
    res3 = evaluate_statistical_profile(
        returns_net=returns,
        validation_profile=profile_class3,
        hypothesis_id="QROS-HYP-000103",
        trial_count_k=2,
        observation_count_t=6000,
        calendar_span_years=5.5,
        n_bootstrap_resamples=500,
        random_seed=42,
    )
    assert res3.passed_sample_power is True  # N=250 >= 150
    assert res3.passed_sharpe is True  # SR >= 1.20
    assert res3.overall_gate_pass is True
    assert len(res3.failure_reasons) == 0


def test_friction_stress_multipliers_by_class():
    """Verify that Class I microstructure regime applies higher friction stress than Class III/IV."""
    base_config = CostModelConfig(
        base_spread_pts=20.0,
        base_slippage_pts=10.0,
    )

    profile_class1 = get_default_profile("CLASS-I")  # 3.0x spread, 4.0x slippage, 500ms latency
    profile_class3 = get_default_profile("CLASS-III")  # 1.5x spread, 2.0x slippage, 0ms latency
    profile_class4 = get_default_profile("CLASS-IV")  # 1.5x spread, 1.5x slippage, 0ms latency

    cost_m1 = TransactionCostModel(base_config=base_config, profile=profile_class1)
    cost_m3 = TransactionCostModel(base_config=base_config, profile=profile_class3)
    cost_m4 = TransactionCostModel(base_config=base_config, profile=profile_class4)

    pts1 = cost_m1.calculate_total_friction_pts(is_stress_test=True)
    pts3 = cost_m3.calculate_total_friction_pts(is_stress_test=True)
    pts4 = cost_m4.calculate_total_friction_pts(is_stress_test=True)

    # Class 1: 20*3 + 10*4 + 7.5 = 107.5 pts
    # Class 3: 20*1.5 + 10*2 = 50.0 pts
    # Class 4: 20*1.5 + 10*1.5 = 45.0 pts
    assert pts1 > pts3 > pts4
    assert pts1 == 107.5
    assert pts3 == 50.0
    assert pts4 == 45.0

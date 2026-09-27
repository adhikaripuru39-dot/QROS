"""Unit tests for transaction cost and friction models."""

import numpy as np
import pytest
from qros.pipeline.costs import CostModelConfig, TransactionCostModel
from qros.schemas.validation_profile import get_default_profile


def test_nominal_friction():
    config = CostModelConfig(
        base_spread_pts=20.0, base_slippage_pts=8.0, point_value_multiplier=0.0001
    )
    model = TransactionCostModel(base_config=config)

    total_pts = model.calculate_total_friction_pts(is_stress_test=False)
    assert total_pts == 28.0  # 20 + 8

    gross_rets = np.array([0.01, 0.02, -0.005])
    net_rets = model.apply_friction_to_returns(gross_rets)
    # Deduction: 28 * 0.0001 = 0.0028
    assert pytest.approx(net_rets[0], abs=1e-6) == 0.01 - 0.0028


def test_stress_test_friction_multipliers():
    # Class I has 3.0x spread, 4.0x slippage, 500ms latency delay
    profile = get_default_profile("CLASS-I")
    config = CostModelConfig(base_spread_pts=10.0, base_slippage_pts=5.0)
    model = TransactionCostModel(base_config=config, profile=profile)

    stress_pts = model.calculate_total_friction_pts(is_stress_test=True)
    # spread: 10 * 3.0 = 30
    # slippage: 5 * 4.0 = 20
    # latency penalty: (500/100) * 1.5 = 7.5
    # total: 30 + 20 + 7.5 = 57.5
    assert stress_pts == 57.5

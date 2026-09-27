"""Unit tests for statistical moments, Profit Factor, Sharpe, Sortino, VaR/CVaR, and Neff."""

import numpy as np
import pytest
from qros.stats.moments import (
    calculate_effective_sample_size,
    calculate_moments,
    calculate_profit_factor,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_t_stat,
    calculate_var_cvar,
)


def test_moments_normal_distribution():
    np.random.seed(42)
    sample = np.random.normal(loc=0.001, scale=0.02, size=10000)
    moments = calculate_moments(sample)

    assert pytest.approx(moments["mean"], abs=0.001) == 0.001
    assert pytest.approx(moments["std"], abs=0.001) == 0.02
    assert abs(moments["skewness"]) < 0.1
    assert abs(moments["excess_kurtosis"]) < 0.15


def test_profit_factor():
    returns = np.array([10.0, 20.0, -5.0, -15.0, 30.0])
    # Pos: 10 + 20 + 30 = 60, Neg: |-5 - 15| = 20 -> PF = 60/20 = 3.0
    pf = calculate_profit_factor(returns)
    assert pf == 3.0

    all_pos = np.array([1.0, 2.0, 3.0])
    assert calculate_profit_factor(all_pos) == float("inf")


def test_sharpe_and_sortino():
    np.random.seed(42)
    returns = np.random.normal(loc=0.001, scale=0.01, size=500)
    sr = calculate_sharpe_ratio(returns, annualization_factor=252.0)
    sortino = calculate_sortino_ratio(returns, annualization_factor=252.0)

    assert sr > 0.0
    assert sortino > 0.0


def test_var_cvar():
    np.random.seed(42)
    # Standard normal returns
    returns = np.random.normal(loc=0.0, scale=1.0, size=10000)
    var_99, cvar_99 = calculate_var_cvar(returns, alpha=0.01)

    # For standard normal, 99% 1-tailed quantile is ~2.326, CVaR is ~2.665
    assert 2.1 < var_99 < 2.5
    assert cvar_99 > var_99


def test_effective_sample_size():
    # Independent series: Neff should be close to N
    np.random.seed(42)
    indep_returns = np.random.randn(500)
    neff_indep = calculate_effective_sample_size(indep_returns)
    assert 400 <= neff_indep <= 500

    # Highly autocorrelated AR(1) series: Neff should be significantly smaller than N
    ar_returns = np.zeros(500)
    for t in range(1, 500):
        ar_returns[t] = 0.8 * ar_returns[t - 1] + np.random.randn()

    neff_ar = calculate_effective_sample_size(ar_returns)
    assert neff_ar < 200


def test_t_stat():
    np.random.seed(42)
    pos_returns = np.random.normal(loc=0.05, scale=0.1, size=200)
    t_stat, p_val = calculate_t_stat(pos_returns)
    assert t_stat > 3.0
    assert p_val < 0.01

"""Unit tests for Stationary Block Bootstrap resampling and Sharpe CI."""

import numpy as np
import pytest
from qros.stats.bootstrap import (
    StationaryBlockBootstrap,
    bootstrap_sharpe_ci,
)


def test_stationary_bootstrap_resample_properties():
    data = np.arange(100)
    boot = StationaryBlockBootstrap(expected_block_length=10.0, random_seed=42)
    resamples = boot.generate_resamples(data, n_resamples=500)

    assert resamples.shape == (500, 100)
    # Check that indices are strictly within 0 to 99
    assert np.all((resamples >= 0) & (resamples < 100))
    # Mean of resamples should be close to mean of data
    assert abs(np.mean(resamples) - np.mean(data)) < 2.0


def test_bootstrap_sharpe_positive_ci():
    np.random.seed(42)
    # Strong positive signal
    returns = np.random.normal(loc=0.002, scale=0.01, size=500)
    ci_res = bootstrap_sharpe_ci(
        returns, n_resamples=1000, expected_block_length=10.0, random_seed=42
    )

    assert ci_res.n_resamples == 1000
    assert ci_res.mean_sharpe > 0.0
    assert ci_res.ci_lower_95 > 0.0
    assert ci_res.ci_upper_95 > ci_res.ci_lower_95
    assert ci_res.ci_strictly_positive is True


def test_bootstrap_sharpe_non_positive_ci():
    np.random.seed(42)
    # Zero/noisy signal
    returns = np.random.normal(loc=0.0, scale=0.01, size=500)
    ci_res = bootstrap_sharpe_ci(
        returns, n_resamples=1000, expected_block_length=10.0, random_seed=42
    )

    assert ci_res.ci_lower_95 <= 0.0
    assert ci_res.ci_strictly_positive is False

"""Unit tests for Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR)."""

import numpy as np
import pytest
from qros.stats.dsr import (
    calculate_dsr,
    calculate_psr,
    calculate_sharpe_std_error,
    compute_expected_max_sharpe,
)


def test_expected_max_sharpe():
    # K=1 trial -> expected max is 0
    assert compute_expected_max_sharpe(1) == 0.0

    # K=10, 100, 1000 trials -> expected max increases monotonically
    em_10 = compute_expected_max_sharpe(10)
    em_100 = compute_expected_max_sharpe(100)
    em_1000 = compute_expected_max_sharpe(1000)

    assert 0.0 < em_10 < em_100 < em_1000
    assert 1.0 < em_100 < 2.5


def test_dsr_single_vs_multiple_trials():
    # High periodic Sharpe (0.15), sample length T = 1000
    # For single trial K=1: DSR should be very high (~1.0)
    res_k1 = calculate_dsr(
        observed_sharpe=0.15,
        trial_count_k=1,
        sample_length_t=1000,
        skewness=0.0,
        kurtosis=3.0,
    )
    assert res_k1.dsr_score > 0.99
    assert res_k1.is_statistically_significant is True

    # For K=5000 trials: DSR score should be deflated substantially
    res_k5000 = calculate_dsr(
        observed_sharpe=0.15,
        trial_count_k=5000,
        sample_length_t=1000,
        skewness=0.0,
        kurtosis=3.0,
    )
    assert res_k5000.dsr_score < res_k1.dsr_score


def test_dsr_skewness_kurtosis_impact():
    # When observed Sharpe exceeds benchmark, negative skew and heavy kurtosis
    # increase standard error, which deflates DSR score (reduces significance confidence)
    res_normal = calculate_dsr(
        observed_sharpe=2.5,
        trial_count_k=50,
        sample_length_t=500,
        skewness=0.0,
        kurtosis=3.0,
    )

    res_heavy_tail = calculate_dsr(
        observed_sharpe=2.5,
        trial_count_k=50,
        sample_length_t=500,
        skewness=-1.5,
        kurtosis=10.0,
    )

    # Standard error for heavy tail must be larger
    se_norm = calculate_sharpe_std_error(2.5, 500, skewness=0.0, kurtosis=3.0)
    se_tail = calculate_sharpe_std_error(2.5, 500, skewness=-1.5, kurtosis=10.0)
    assert se_tail > se_norm
    assert res_heavy_tail.dsr_score < res_normal.dsr_score


def test_psr_benchmark():
    # Test PSR against non-zero benchmark
    psr_val = calculate_psr(
        observed_sharpe=0.10,
        benchmark_sharpe=0.05,
        sample_length_t=500,
        skewness=0.0,
        kurtosis=3.0,
    )
    assert psr_val > 0.50

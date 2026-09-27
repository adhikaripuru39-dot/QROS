"""Independent mathematical benchmarking suite for QROS statistical engine.

Validates that mathematical routines strictly match closed-form analytical solutions
and extreme value theory benchmarks from literature.
"""

import numpy as np
import pytest
from scipy import stats
from qros.stats.bootstrap import StationaryBlockBootstrap, bootstrap_sharpe_ci
from qros.stats.dsr import (
    calculate_dsr,
    calculate_psr,
    calculate_sharpe_std_error,
    compute_expected_max_sharpe,
)
from qros.stats.moments import (
    calculate_effective_sample_size,
    calculate_moments,
    calculate_var_cvar,
)
from qros.stats.multiple_testing import benjamini_hochberg, bonferroni_correction
from qros.testing.synthetic_data import (
    generate_autocorrelated_series,
    generate_fat_tailed_returns,
)


def test_extreme_value_sharpe_analytical():
    """Verify expected maximum Sharpe ratio SR*(K, V) against closed-form EVT values."""
    # Under standard normal variance V = 1.0
    v = 1.0

    # Exact closed-form formula values:
    # K=1 -> 0.0
    # K=10 -> 1.5746
    # K=100 -> 2.5306
    # K=1000 -> 3.2551
    # K=10000 -> 3.8607
    sr_1 = compute_expected_max_sharpe(1, var_sharpe=v)
    sr_10 = compute_expected_max_sharpe(10, var_sharpe=v)
    sr_100 = compute_expected_max_sharpe(100, var_sharpe=v)
    sr_1000 = compute_expected_max_sharpe(1000, var_sharpe=v)
    sr_10000 = compute_expected_max_sharpe(10000, var_sharpe=v)

    assert sr_1 == 0.0
    assert pytest.approx(sr_10, abs=0.001) == 1.5746
    assert pytest.approx(sr_100, abs=0.001) == 2.5306
    assert pytest.approx(sr_1000, abs=0.001) == 3.2551
    assert pytest.approx(sr_10000, abs=0.001) == 3.8607


def test_psr_against_scipy_normal_cdf():
    """Verify PSR score matches independent closed-form Gaussian integral."""
    obs_sr = 0.12
    bmk_sr = 0.0
    t = 250
    skew = -0.5
    kurt = 4.5  # Pearson kurtosis

    # Independent manual calculation of standard error:
    # sigma_SR = sqrt((1 - skew*SR + ((kurt - 1)/4)*SR^2) / (T - 1))
    var_term = 1.0 - skew * obs_sr + ((kurt - 1.0) / 4.0) * (obs_sr**2)
    expected_se = np.sqrt(var_term / (t - 1.0))
    expected_z = (obs_sr - bmk_sr) / expected_se
    expected_psr = float(stats.norm.cdf(expected_z))

    qros_se = calculate_sharpe_std_error(obs_sr, t, skewness=skew, kurtosis=kurt)
    qros_psr = calculate_psr(obs_sr, bmk_sr, t, skewness=skew, kurtosis=kurt)

    assert pytest.approx(qros_se, rel=1e-7) == expected_se
    assert pytest.approx(qros_psr, rel=1e-7) == expected_psr


def test_stationary_bootstrap_geometric_distribution():
    """Verify that StationaryBlockBootstrap block lengths follow theoretical geometric properties."""
    expected_block_len = 10.0
    p = 1.0 / expected_block_len
    boot = StationaryBlockBootstrap(
        expected_block_length=expected_block_len, random_seed=42
    )

    # Generate a large single trajectory of indices
    n = 50000
    indices = boot.resample_indices(n)

    # Count consecutive continuous segments (blocks)
    block_lengths = []
    current_len = 1
    for i in range(1, n):
        if indices[i] == (indices[i - 1] + 1) % n:
            current_len += 1
        else:
            block_lengths.append(current_len)
            current_len = 1
    block_lengths.append(current_len)

    # Theoretical Geometric distribution moments:
    # Mean = 1 / p = 10.0
    # Variance = (1 - p) / p^2 = 0.9 / 0.01 = 90.0
    mean_emp = float(np.mean(block_lengths))
    var_emp = float(np.var(block_lengths))

    assert pytest.approx(mean_emp, rel=0.10) == expected_block_len
    assert pytest.approx(var_emp, rel=0.20) == (1.0 - p) / (p**2)


def test_effective_sample_size_ar1_analytical():
    """Verify calculated N_eff against theoretical formula N * (1 - phi) / (1 + phi)."""
    for phi in [0.3, 0.6, 0.75]:
        series, info = generate_autocorrelated_series(
            n_samples=5000, ar_phi=phi, sigma_eps=0.01, random_seed=42
        )
        theoretical_neff = info["theoretical_neff"]
        qros_neff = calculate_effective_sample_size(series, max_lags=30)

        # Empirical estimate on 5000 samples should be within 15% of theoretical
        assert pytest.approx(qros_neff, rel=0.15) == theoretical_neff


def test_var_cvar_analytical_normal():
    """Verify VaR and CVaR against analytical standard normal formulas."""
    np.random.seed(42)
    # Standard normal returns: mu = 0, sigma = 1
    samples = np.random.normal(loc=0.0, scale=1.0, size=50000)
    var_99, cvar_99 = calculate_var_cvar(samples, alpha=0.01)

    # Analytical 99% 1-tailed:
    # VaR_99 = -Phi^{-1}(0.01) = 2.326348
    # CVaR_99 = phi(2.326348) / 0.01 = 2.6652
    expected_var = float(stats.norm.ppf(0.99))
    expected_cvar = float(stats.norm.pdf(stats.norm.ppf(0.99)) / 0.01)

    assert pytest.approx(var_99, abs=0.08) == expected_var
    assert pytest.approx(cvar_99, abs=0.08) == expected_cvar


def test_fat_tailed_kurtosis_student_t():
    """Verify kurtosis calculation against Student-t theoretical excess kurtosis 6 / (nu - 4)."""
    # df = 6 -> Excess Kurtosis = 6 / (6 - 4) = 3.0
    returns, info = generate_fat_tailed_returns(
        n_samples=100000, df_degrees=6.0, loc=0.0, scale=1.0, random_seed=42
    )
    moments = calculate_moments(returns)

    assert pytest.approx(moments["excess_kurtosis"], rel=0.20) == 3.0
    assert pytest.approx(moments["skewness"], abs=0.1) == 0.0


def test_benjamini_hochberg_known_table():
    """Verify Benjamini-Hochberg against textbook reference step-up vector."""
    # Textbook example with 8 hypotheses and FDR q = 0.10
    raw_p = [0.002, 0.008, 0.015, 0.025, 0.040, 0.080, 0.120, 0.200]
    # m = 8, q = 0.10
    # Thresholds: (i/8)*0.10 -> [0.0125, 0.025, 0.0375, 0.050, 0.0625, 0.075, 0.0875, 0.100]
    # p[0]=0.002 <= 0.0125 (sig)
    # p[1]=0.008 <= 0.025 (sig)
    # p[2]=0.015 <= 0.0375 (sig)
    # p[3]=0.025 <= 0.050 (sig)
    # p[4]=0.040 <= 0.0625 (sig)
    # p[5]=0.080 > 0.075 (fail)
    # Largest k with p_(k) <= (k/m)*q is k=5 (p=0.040). So first 5 are rejected.
    sig, q_vals = benjamini_hochberg(raw_p, fdr_q=0.10)

    assert list(sig) == [True, True, True, True, True, False, False, False]

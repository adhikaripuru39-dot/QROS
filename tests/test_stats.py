"""Tests for the stats package (Part 8)."""

from __future__ import annotations

import numpy as np
import pytest

from qros.stats.bootstrap import permutation_test, stationary_bootstrap
from qros.stats.cpcv import combinatorial_purged_cv, split_leaves
from qros.stats.multiple_testing import benjamini_hochberg, holm_bonferroni
from qros.stats.sharpe import deflated_sharpe_ratio, expected_max_sr, sharpe_ratio
from qros.stats.timeseries import engle_granger_p, ornstein_uhlenbeck_half_life


def test_dsr_accepts_strong_edge_few_trials():
    rng = np.random.default_rng(7)
    r = rng.normal(0.004, 0.01, 300)
    d = deflated_sharpe_ratio(r, n_trials=2)
    assert d.rejected is False  # p < 0.01


def test_dsr_rejects_with_massive_trial_count():
    rng = np.random.default_rng(7)
    r = rng.normal(0.003, 0.01, 300)
    d_small = deflated_sharpe_ratio(r, n_trials=2)
    d_many = deflated_sharpe_ratio(r, n_trials=100_000)
    assert d_many.p_value > d_small.p_value
    assert d_many.rejected is True


def test_dsr_policy_threshold():
    from qros.governance.policy import DEFAULT_POLICY

    assert DEFAULT_POLICY.dsr_p_max == 0.01


def test_fdr_bh_controls():
    p = np.array([0.001, 0.02, 0.04, 0.2, 0.5])
    reject, q = benjamini_hochberg(p, q=0.05)
    assert bool(reject[0]) is True
    assert bool(reject[-1]) is False
    assert q == 0.05


def test_holm_bonferroni_gate():
    p = np.array([0.001, 0.01, 0.05])
    reject, alpha = holm_bonferroni(p)
    assert bool(reject[0]) is True  # 0.001 <= 0.01/3 -> reject
    assert alpha == 0.01


def test_cpcv_paths_and_purge():
    rng = np.random.default_rng(0)
    r = rng.normal(0, 1, 400)
    cp = combinatorial_purged_cv(r, n_splits=8, k_test=2)
    assert cp.paths >= 16  # C(8,2)=28
    assert 0.0 <= cp.pbo <= 1.0


def test_cpcv_split_leaves_disjoint_pairs():
    pairs = split_leaves(T=400, n_splits=8, k_test=2)
    for train, test in pairs:
        assert set(train).isdisjoint(set(test))


def test_stationary_bootstrap_reproducible():
    rng = np.random.default_rng(5)
    x = np.arange(100.0)
    a = stationary_bootstrap(x, size=200, mean_block=10, rng=np.random.default_rng(3))
    b = stationary_bootstrap(x, size=200, mean_block=10, rng=np.random.default_rng(3))
    assert np.allclose(a, b)


def test_permutation_noise_high_p():
    from qros.stats.bootstrap import permutation_test

    rng = np.random.default_rng(1)
    x = rng.normal(0, 1, 60)
    y = rng.normal(0, 1, 60)
    res = permutation_test(x, y, lambda a, b: float(np.mean(a) - np.mean(b)), n_perm=300)
    assert res["p_value"] > 0.01  # pure noise: no significant difference


def test_expected_max_sr_grows_with_trials():
    e3 = expected_max_sr(3, 200)
    e1000 = expected_max_sr(1000, 200)
    assert e1000 > e3


def test_sharpe_ratio_positive():
    r = np.full(100, 0.01)
    assert sharpe_ratio(r) > 0


def test_cointegrated_pair_low_p():
    rng = np.random.default_rng(3)
    y = np.cumsum(rng.normal(0, 1, 300))
    x = y + rng.normal(0, 0.2, 300)
    p = engle_granger_p(y, x)
    assert p < 0.05


def test_ou_half_life_mean_reverting():
    rng = np.random.default_rng(2)
    x = np.empty(300)
    x[0] = 0
    for i in range(1, 300):
        x[i] = 0.7 * x[i - 1] + rng.normal(0, 1)
    tau = ornstein_uhlenbeck_half_life(x)
    assert 0 < tau < 10
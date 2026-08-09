"""Tests for features package (Part 4)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qros.features.transforms import (
    fraction_diff_ffd,
    garman_klass_vol,
    log_return,
    order_book_imbalance,
    percentile_rank,
    rolling_zscore,
    vpin,
)
from qros.features.validate import (
    adf_pvalue,
    detect_multicollinearity,
    test_stationarity as _test_stationarity,
    validate_feature_frame,
    vif_table,
)


def test_log_return_formula():
    px = np.array([100.0, 110.0, 121.0])
    lr = log_return(px)
    assert np.isnan(lr[0])
    assert lr[1] == pytest.approx(np.log(110.0 / 100.0))
    assert lr[2] == pytest.approx(np.log(121.0 / 110.0))


def test_fraction_diff_identity_and_first_diff():
    x = np.array([1.0, 2.0, 4.0, 8.0, 16.0])
    assert np.allclose(fraction_diff_ffd(x, 0.0), x)  # d=0 -> identity
    d1 = fraction_diff_ffd(x, 1.0)
    assert d1[0] == pytest.approx(1.0)
    assert d1[1] == pytest.approx(1.0)  # 2-1


def test_rolling_zscore_is_backward_only():
    x = np.array([1.0, 2.0, 3.0, 4.0, 100.0])
    z = rolling_zscore(x, window=3)
    # The last value's z uses only the trailing window (no future values).
    assert np.isfinite(z[-1])
    window = x[-3:]
    expected = (x[-1] - np.mean(window)) / np.std(window, ddof=1)  # rolling std uses ddof=1
    assert z[-1] == pytest.approx(expected)


def test_order_book_imbalance_range():
    bid = np.array([100, 200, 300])
    ask = np.array([100, 100, 300])
    obi = order_book_imbalance(bid, ask)
    assert np.all(obi >= -1.0) and np.all(obi <= 1.0)
    assert obi[0] == 0.0
    assert obi[1] == pytest.approx((200 - 100) / 300)


def test_garman_klass_matches_formula():
    o = np.array([100.0, 101.0])
    h = np.array([102.0, 103.0])
    l = np.array([99.0, 100.0])
    c = np.array([101.5, 102.5])
    gk = garman_klass_vol(o, h, l, c)
    expected = 0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2
    assert gk[1] == pytest.approx(expected[1])


def test_vpin_in_unit_interval():
    rng = np.random.default_rng(0)
    buy = np.abs(rng.normal(size=200))
    sell = np.abs(rng.normal(size=200))
    vp = vpin(buy, sell, 20, 5000.0)
    assert np.all(vp >= 0.0) and np.all(vp <= 1.0)


def test_percentile_rank_uniform():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    pr = percentile_rank(x)
    assert pr[-1] == pytest.approx(1.0)


def test_adf_random_walk_vs_stationary():
    rng = np.random.default_rng(0)
    rw = np.cumsum(rng.normal(0, 1, 400))  # non-stationary
    sta = rng.normal(0, 1, 400)  # IID stationary
    assert adf_pvalue(rw) >= 0.05
    assert adf_pvalue(sta) < 0.05


def test_vif_high_multicollinearity():
    rng = np.random.default_rng(1)
    a = rng.normal(0, 1, 200)
    df = pd.DataFrame({"a": a, "b": 100 * a + rng.normal(0, 0.01, 200)})
    vif = vif_table(df)
    assert vif["b"] > 10.0
    assert "b" in detect_multicollinearity(df)


def test_stationarity_of_iid_make_returns(make_returns):
    r = make_returns(n=400, seed=0)
    res = _test_stationarity(r)
    assert res.passed is True


def test_missing_stationarity_on_short():
    assert np.isnan(adf_pvalue([1.0, 2.0]))


def test_validate_feature_frame_batch(make_returns):
    rng = np.random.default_rng(2)
    a = make_returns(n=400, seed=3)
    b = 50 * a + rng.normal(0, 0.01, 400)  # highly collinear with a
    c = np.cumsum(a)  # non-stationary random walk
    df = pd.DataFrame({"a": a, "b": b, "c": c})
    report = validate_feature_frame(df)
    assert report.all_stationary() is False  # c (random walk) is non-stationary
    assert len(report.correlation_pairs) >= 1  # a/b highly correlated
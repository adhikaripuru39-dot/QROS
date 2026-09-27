"""Unit tests for dataset validation and SHA-256 hashing."""

import numpy as np
import pandas as pd
import pytest
from qros.data.validation import validate_ohlcv_dataframe, compute_dataset_hash


@pytest.fixture
def valid_ohlcv_df():
    dates = pd.date_range("2023-01-01", periods=100, freq="1h", tz="UTC")
    np.random.seed(42)
    close = 1800.0 + np.cumsum(np.random.randn(100) * 2.0)
    open_p = close + np.random.randn(100) * 0.5
    high = np.maximum(open_p, close) + np.abs(np.random.randn(100) * 0.8)
    low = np.minimum(open_p, close) - np.abs(np.random.randn(100) * 0.8)
    volume = np.random.randint(100, 1000, size=100)

    df = pd.DataFrame(
        {
            "Open": open_p,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=dates,
    )
    return df


def test_valid_ohlcv(valid_ohlcv_df):
    clean_df, report = validate_ohlcv_dataframe(valid_ohlcv_df)
    assert report.is_valid is True
    assert report.total_bars == 100
    assert len(report.detected_issues) == 0
    assert len(report.dataset_sha256) == 64  # SHA-256 hex string length
    assert "open" in clean_df.columns
    assert "close" in clean_df.columns


def test_invalid_ohlcv_high_low_violation(valid_ohlcv_df):
    corrupted_df = valid_ohlcv_df.copy()
    # Force high to be lower than low on a bar
    corrupted_df.loc[corrupted_df.index[10], "High"] = 1000.0

    clean_df, report = validate_ohlcv_dataframe(corrupted_df)
    assert report.is_valid is False
    assert any("High < max" in issue for issue in report.detected_issues)


def test_nan_values_detection(valid_ohlcv_df):
    corrupted_df = valid_ohlcv_df.copy()
    corrupted_df.loc[corrupted_df.index[5], "Close"] = np.nan

    clean_df, report = validate_ohlcv_dataframe(corrupted_df)
    assert report.is_valid is False
    assert any("NaN/null" in issue for issue in report.detected_issues)


def test_non_utc_index_normalization(valid_ohlcv_df):
    tz_naive_df = valid_ohlcv_df.copy()
    tz_naive_df.index = tz_naive_df.index.tz_localize(None)

    clean_df, report = validate_ohlcv_dataframe(tz_naive_df)
    assert report.is_valid is True
    assert clean_df.index.tz is not None
    assert str(clean_df.index.tz) == "UTC"


def test_hash_determinism(valid_ohlcv_df):
    hash1 = compute_dataset_hash(valid_ohlcv_df)
    hash2 = compute_dataset_hash(valid_ohlcv_df.copy())
    assert hash1 == hash2

    # Modified data must yield different hash
    mod_df = valid_ohlcv_df.copy()
    mod_df.iloc[0, 0] += 0.001
    hash3 = compute_dataset_hash(mod_df)
    assert hash1 != hash3

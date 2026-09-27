"""Unit tests for purging overlapping labels and autocorrelation embargoing."""

import pandas as pd
import pytest
from qros.data.purging import (
    compute_embargo_cutoff,
    purge_overlapping_labels,
    purged_train_test_split,
)


def test_purge_overlapping_labels():
    start_times = pd.Series(
        [
            pd.Timestamp("2023-01-01 10:00", tz="UTC"),
            pd.Timestamp("2023-01-01 11:30", tz="UTC"),
            pd.Timestamp("2023-01-01 14:00", tz="UTC"),
        ]
    )
    end_times = pd.Series(
        [
            pd.Timestamp("2023-01-01 10:30", tz="UTC"),
            pd.Timestamp("2023-01-01 12:30", tz="UTC"),  # Overlaps test window (11:00-13:00)
            pd.Timestamp("2023-01-01 15:00", tz="UTC"),
        ]
    )

    test_start = pd.Timestamp("2023-01-01 11:00", tz="UTC")
    test_end = pd.Timestamp("2023-01-01 13:00", tz="UTC")

    keep_mask = purge_overlapping_labels(start_times, end_times, test_start, test_end)
    assert keep_mask.iloc[0] == True
    assert keep_mask.iloc[1] == False  # Purged
    assert keep_mask.iloc[2] == True


def test_compute_embargo_cutoff():
    idx = pd.date_range("2023-01-01 00:00", periods=50, freq="1h", tz="UTC")
    test_end = idx[20]

    cutoff = compute_embargo_cutoff(test_end, idx, embargo_bars=5)
    # The 5th bar after idx[20] is idx[25]
    assert cutoff == idx[25]


def test_purged_train_test_split():
    idx = pd.date_range("2023-01-01", periods=100, freq="1D", tz="UTC")
    df = pd.DataFrame({"val": range(100)}, index=idx)

    train_df, test_df = purged_train_test_split(
        df,
        test_start_pct=0.60,
        test_end_pct=0.80,
        holding_bars=2,
        embargo_bars=3,
    )

    assert len(test_df) == 20  # indices 60 to 79
    # Pre-test train: 0 to 57 (60 - 2 = 58 items)
    # Post-test train: 83 to 99 (80 + 3 = 83, so 17 items)
    assert len(train_df) == 58 + 17

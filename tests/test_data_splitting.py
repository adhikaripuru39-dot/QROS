"""Unit tests for 4-tier chronological splitting and protected OOS vault."""

import numpy as np
import pandas as pd
import pytest
from qros.data.splitting import (
    DataSplitter,
    ProtectedOOSViolationError,
)


@pytest.fixture
def sample_dataset():
    dates = pd.date_range("2020-01-01", periods=1000, freq="1h", tz="UTC")
    df = pd.DataFrame({"close": np.linspace(100, 200, 1000)}, index=dates)
    return df


def test_default_4_tier_split(sample_dataset):
    splitter = DataSplitter(eda_pct=0.20, train_pct=0.40, val_pct=0.20, oos_pct=0.20)
    split_ds = splitter.split(sample_dataset, lock_oos=True)

    assert len(split_ds.eda) == 200
    assert len(split_ds.train) == 400
    assert len(split_ds.validation) == 200
    assert split_ds.is_oos_locked is True

    # Attempting to read OOS partition when locked must raise ProtectedOOSViolationError
    with pytest.raises(ProtectedOOSViolationError):
        _ = split_ds.oos

    # Unlocking with valid token
    split_ds.unlock_oos("GOVERNANCE-GATE-11-AUTH")
    assert split_ds.is_oos_locked is False
    assert len(split_ds.oos) == 200


def test_custom_allocation_split(sample_dataset):
    splitter = DataSplitter(eda_pct=0.10, train_pct=0.60, val_pct=0.15, oos_pct=0.15)
    split_ds = splitter.split(sample_dataset, lock_oos=False)

    assert len(split_ds.eda) == 100
    assert len(split_ds.train) == 600
    assert len(split_ds.validation) == 150
    assert len(split_ds.oos) == 150


def test_invalid_split_percentages():
    with pytest.raises(ValueError, match="must sum to 1.0"):
        DataSplitter(eda_pct=0.30, train_pct=0.40, val_pct=0.20, oos_pct=0.20)

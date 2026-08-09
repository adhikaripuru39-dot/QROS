"""Shared deterministic fixtures for the QROS offline test suite."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from qros.data.engineering import DatasetMetadata
from qros.data.snapshot import SnapshotRegistry
from qros.schemas.fields import EXP_FIELDS, HYP_FIELDS


@pytest.fixture
def make_ohlc():
    def _make(n: int = 200, seed: int = 42) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        px = 100 + np.cumsum(rng.normal(0, 0.5, n))
        return pd.DataFrame(
            {
                "symbol": "TEST",
                "event_timestamp": pd.date_range("2026-01-01", periods=n, freq="h"),
                "open": px + 0.1,
                "high": px + 1.0,
                "low": px - 1.0,
                "close": px,
                "volume": rng.integers(100, 1000, n),
            }
        )

    return _make


@pytest.fixture
def make_returns():
    def _make(n: int = 300, seed: int = 0, drift: float = 0.0, vol: float = 1.0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        return rng.normal(drift, vol, n)

    return _make


@pytest.fixture
def plant_spike(make_ohlc):
    """Return a clean OHLC frame with a planted closing spike at an index."""

    def _plant(index: int = 150, magnitude: float = 40.0) -> pd.DataFrame:
        df = make_ohlc()
        df.loc[index, "close"] += magnitude
        return df

    return _plant


@pytest.fixture
def plant_duplicate(make_ohlc):
    """A clean OHLC frame with a planted duplicate row."""

    def _plant() -> pd.DataFrame:
        df = make_ohlc()
        return pd.concat([df, df.iloc[[30]]], ignore_index=True)

    return _plant


@pytest.fixture
def make_hyp_spec():
    """A valid 22-field HYP field dict (HYP-01..HYP-22)."""

    def _make(hyp_id: str = "HYP-EQUITY-MICROSTRUCTURE-2026-0042") -> dict[str, str]:
        fields = {f.id: f"value for {f.name}" for f in HYP_FIELDS}
        fields["HYP-01"] = hyp_id
        return fields

    return _make


@pytest.fixture
def make_exp_spec():
    """A valid 17-field EXP record data dict."""

    def _make(hyp_id: str = "HYP-EQUITY-2026-0001") -> dict:
        return {
            "timestamp": "2026-08-08T10:00:00Z",
            "researcher": "qr-1",
            "dataset_hash": "a" * 64,
            "code_commit": "b" * 40,
            "feature_version": "feat_v1.0",
            "hypothesis_id": hyp_id,
            "objective": "Maximize DSR",
            "hyperparameters": {"window": 10},
            "test_output": {"t_stat": 4.2, "p_value": 0.0002},
            "metrics": {"is_sharpe": 3.1, "oos_sharpe": 2.4, "max_drawdown": 0.08, "turnover_pct": 11.0},
            "conclusions": "statistically verified",
            "limitations": "none documented",
            "next_actions": "promote to walk-forward",
        }

    return _make


@pytest.fixture
def make_snapshot_registry(tmp_path: Path):
    """A fresh SnapshotRegistry rooted at tmp_path."""

    def _make() -> SnapshotRegistry:
        reg = SnapshotRegistry(tmp_path / "snapshots")
        meta = DatasetMetadata(git_commit="a" * 40, etl_version="etl_v1", schema_version="sch_v1", ingested_at="2026-08-08")
        df = pd.DataFrame({"close": [1.0, 2.0, 3.0], "volume": [10, 20, 30]})
        reg.register(df, "snapshot_v1", meta)
        return reg

    return _make
"""Tests for data/engineering.py and data/snapshot.py (Part 3)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qros.data.engineering import TIERS, Tier, DatasetMetadata, partition_path
from qros.data.snapshot import SnapshotLockedError, SnapshotRegistry, _canonical_bytes


def test_partition_path_convention():
    path = partition_path(Tier.WARM, "us_equities", "trade_ticks", 2026, 8, 6, "AAPL")
    assert path == (
        "s3://qros-data-lake/tier=warm/asset_class=us_equities/data_type=trade_ticks/"
        "year=2026/month=08/day=06/AAPL.parquet"
    )


def test_three_tiers_present():
    assert {t.tier for t in TIERS} == {Tier.HOT, Tier.WARM, Tier.COLD}


def test_snapshot_sha256_roundtrip(make_snapshot_registry):
    reg = make_snapshot_registry()
    snap = reg.get("snapshot_v1")
    assert len(snap.sha256) == 64
    assert reg.verify("snapshot_v1") is True
    assert reg.all_frozen() is True


def test_register_then_tamper_detected(make_snapshot_registry):
    reg = make_snapshot_registry()
    # overwrite the artifact file -> canonical hash changes
    artifact = reg.root / "artifacts" / "snapshot_v1" / "data.canon"
    artifact.write_bytes(b"corrupted-tamper")
    assert reg.verify("snapshot_v1") is False
    with pytest.raises(SnapshotLockedError):
        reg.get("snapshot_v1")


def test_register_idempotent_and_frozen_copy(make_snapshot_registry):
    reg = make_snapshot_registry()
    df = pd.DataFrame({"close": [1.0, 2.0, 3.0], "volume": [10, 20, 30]})
    meta = DatasetMetadata("a" * 40, "etl_v1", "sch_v1", "2026-08-08")
    reg.register(df, "snapshot_v1", meta)  # same hash -> idempotent, no error
    out = reg.get("snapshot_v1")
    out.content.loc[0, "close"] = 999.0  # mutating the returned copy must not affect registry
    assert reg.get("snapshot_v1").content.loc[0, "close"] == 1.0


def test_canonical_bytes_deterministic():
    df = pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})
    assert _canonical_bytes(df) == _canonical_bytes(df)
    assert _canonical_bytes(df) != _canonical_bytes(df + 1)
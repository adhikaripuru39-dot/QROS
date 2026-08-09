"""Tests for data/quality.py (Part 2 + Part 1 checklists)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from qros.data.quality import (
    BIAS_KEYS,
    bias_audit,
    check_bar_bounds,
    check_pit_ordering,
    check_quote_sanity,
    detect_duplicates,
    detect_outliers_mad,
    detect_spikes,
    normalize_timestamps_utc,
    reconcile_vendors,
    run_quality_suite,
)


def test_spike_detected(make_ohlc):
    df = make_ohlc()
    df.loc[150, "close"] += 60.0
    mask = detect_spikes(df["close"])
    assert bool(mask.iloc[150]) is True


def test_mad_outlier_flagged(make_ohlc):
    df = make_ohlc()
    df.loc[80, "close"] = float(df["close"].median() + 50.0)  # far outside MAD threshold
    mask = detect_outliers_mad(df["close"], window=30)
    assert bool(mask.iloc[80]) is True


def test_duplicate_detected(plant_duplicate):
    df = plant_duplicate()
    dups = detect_duplicates(df)
    assert dups.sum() == 1


def test_bar_bounds_violation(make_ohlc):
    df = make_ohlc()
    df.loc[20, "low"] = df.loc[20, "close"] + 5.0  # low > close -> invalid
    mask = check_bar_bounds(df["open"], df["high"], df["low"], df["close"])
    assert bool(mask.iloc[20]) is False


def test_pit_ordering():
    event = pd.Series([pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-02")])
    knowledge = pd.Series([pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-03")])
    ok = check_pit_ordering(event, knowledge)
    assert bool(ok.all())
    bad = check_pit_ordering(knowledge, event)  # knowledge before event
    assert bool(bad.any())


def test_quote_sanity():
    bid = pd.Series([100.0, 100.0])
    ask = pd.Series([100.2, 500.0])  # second spread huge
    ok = check_quote_sanity(bid, ask)
    assert bool(ok.iloc[0]) is True
    assert bool(ok.iloc[1]) is False


def test_utc_timezone_normalization():
    ser = pd.Series(pd.date_range("2026-01-01", periods=3, tz="America/New_York"))
    idx = normalize_timestamps_utc(ser)
    assert all(t.tzinfo is not None and str(t.tzinfo) == "UTC" for t in idx)


def test_vendor_reconciliation_flags_discrepancy():
    primary = pd.Series([100.0, 100.0, 100.0])
    secondary = pd.Series([100.0, 100.02, 99.0])  # 2bp and 1% differences
    flags = reconcile_vendors(primary, secondary)
    assert bool(flags.iloc[1]) is True or bool(flags.iloc[2]) is True


def test_bias_audit_eight_keys():
    status = bias_audit(
        {k: False for k in BIAS_KEYS}
    )
    assert set(status.keys()) == set(BIAS_KEYS)
    assert len(status) == 8


def test_quality_suite_reports_anomalies(plant_spike):
    df = plant_spike()
    report = run_quality_suite(df)
    assert report.flagged_rows > 0
    assert report.checks["no_spikes"] is False
    assert report.checks["no_duplicates"] is True
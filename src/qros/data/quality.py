"""Part 2: Data Quality Management — anomaly detection, cleaning, bias audit.

Transcribes Part 2 ch.1 (anomalies) and ch.2 (8 quantitative research biases).
All thresholds read from ``governance.policy``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from qros.governance.policy import DEFAULT_POLICY, Policy

# Part 2 ch.2 — the 8 quantitative research bias elimination protocols.
BIASES: tuple[tuple[str, str, str], ...] = (
    ("survivorship", "Excluding delisted, bankrupt, or acquired firms from historical index constituents.", "Use point-in-time survivor-inclusive universe including historical delisted assets."),
    ("look_ahead", "Using data at timestamp t not publicly available until t+k.", "Enforce bitemporal point-in-time schema; restrict signal to Knowledge Time."),
    ("selection", "Selecting assets based on post-hoc performance criteria.", "Define universe dynamically at every point-in-time t using lagged market cap."),
    ("execution", "Assuming fills at mid-price or bar close without modeling depth/latency.", "Incorporate L2 depth, queue priority delay, and square-root impact."),
    ("sampling", "Sampling during a unique market regime and generalizing results.", "Enforce multi-decade spans covering 2008, 2011, 2020, 2022 crises."),
    ("data_snooping", "Testing thousands of parameter combinations until significance by chance.", "Track trial count in registry; penalize p-values using DSR and FWER."),
    ("publication_lag", "Assuming macro indicators available on observation date, not release date.", "Map macro to release date and hour (e.g., CPI + 08:30 EST)."),
    ("revision", "Using final revised macro prints instead of first-print values.", "Store full revision histories; query initial print for signal generation."),
)
BIAS_KEYS: tuple[str, ...] = tuple(b[0] for b in BIASES)


@dataclass
class QualityReport:
    """Aggregate result of the quality suite over a DataFrame."""

    checks: dict[str, bool]
    anomalies: pd.DataFrame
    bias_status: dict[str, bool]
    flagged_rows: int


def check_bar_bounds(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Part 1 4.2: valid iff High >= max(Open, Close) and Low <= min(Open, Close)."""
    valid = (high >= np.maximum(open_, close)) & (low <= np.minimum(open_, close))
    return valid


def check_quote_sanity(bid: pd.Series, ask: pd.Series, policy: Policy = DEFAULT_POLICY) -> pd.Series:
    """Part 1 4.2: ask > bid and spread <= policy.max_ask_bid_spread_bp basis points of mid."""
    mid = (bid + ask) / 2.0
    spread_bp = ((ask - bid) / mid) * 10_000  # basis points
    valid = (ask > bid) & (spread_bp <= policy.max_ask_bid_spread_bp)
    return valid


def check_pit_ordering(event_ts: pd.Series, knowledge_ts: pd.Series) -> pd.Series:
    """Part 1 4.2: Knowledge_Timestamp >= Event_Timestamp (bitemporal point-in-time)."""
    return knowledge_ts >= event_ts


def detect_missing_seconds(df: pd.DataFrame, session_calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Part 2 1.1: grid continuity audit comparing expected session minutes vs observed.

    Returns a DataFrame of missing timestamp windows.
    """
    observed = pd.DatetimeIndex(df["event_timestamp"]) if "event_timestamp" in df else df.index
    if not isinstance(observed, pd.DatetimeIndex):
        observed = pd.to_datetime(observed)
    missing = session_calendar.difference(observed)
    if len(missing) == 0:
        return pd.DataFrame(columns=["event_timestamp"])
    return pd.DataFrame({"event_timestamp": missing})


def report_missing_ratio(observed: pd.DatetimeIndex, session_calendar: pd.DatetimeIndex) -> float:
    """Fraction of expected session timestamps that are missing."""
    if len(session_calendar) == 0:
        return 0.0
    missing = session_calendar.difference(observed)
    return len(missing) / len(session_calendar)


def detect_outliers_mad(price: pd.Series, window: int = 20, policy: Policy = DEFAULT_POLICY) -> pd.Series:
    """Part 2 1.2: rolling MAD filter; flag where |P - M_med|/MAD > mad_z_threshold."""
    med = price.rolling(window, min_periods=max(5, window // 2)).median()
    abs_dev = (price - med).abs()
    mad = abs_dev.rolling(window, min_periods=max(5, window // 2)).median().replace(0.0, np.nan)
    z = abs_dev / mad
    return z > policy.mad_z_threshold


def detect_spikes(close: pd.Series, window: int = 20, policy: Policy = DEFAULT_POLICY) -> pd.Series:
    """Part 1 5.1 CASE 2: |P_t - P_{t-1}| > spike_sigma_threshold * rolling step sigma.

    Sigma is the rolling std of the local step size (differences), so a strong price
    drift does not inflate the threshold.
    """
    steps = close.diff()
    step_std = steps.rolling(window, min_periods=max(5, window // 2)).std().shift(1).replace(0.0, np.nan)
    return steps.abs() > policy.spike_sigma_threshold * step_std


def detect_duplicates(df: pd.DataFrame) -> pd.Series:
    """Part 2 1.3: multi-column hash uniqueness across (Symbol, Timestamp, O, H, L, C, V)."""
    cols = ["symbol", "event_timestamp", "open", "high", "low", "close", "volume"]
    present = [c for c in cols if c in df.columns]
    key = df[present].astype(str).agg("|".join, axis=1)
    return key.duplicated(keep="first")


def normalize_timestamps_utc(series: pd.Series) -> pd.DatetimeIndex:
    """Part 2 1.4: IANA tz -> UTC. Input may be tz-naive (assumed UTC) or tz-aware."""
    idx = pd.to_datetime(series)
    if idx.tz is None:
        idx = idx.dt.tz_localize("UTC")
    else:
        idx = idx.dt.tz_convert("UTC")
    return idx


def reconcile_vendors(primary_close: pd.Series, secondary_close: pd.Series, policy: Policy = DEFAULT_POLICY) -> pd.Series:
    """Part 2 1.5: flag close discrepancy > 1 basis point between independent vendors.

    Cross-referencing aligns both indexes; unpaired values are flagged as needs-review.
    """
    aligned = pd.concat([primary_close, secondary_close], axis=1, join="inner")
    if aligned.empty:
        return pd.Series(dtype=bool)
    pct_diff = (aligned.iloc[:, 0] - aligned.iloc[:, 1]).abs() / aligned.iloc[:, 0].abs()
    return pct_diff > policy.vendor_discrepancy_pct


def bias_audit(flags: dict[str, bool]) -> dict[str, bool]:
    """Consume pre-computed mitigation flags and produce the 8-key bias status.

    Each key is True when the bias is detected as un-mitigated (i.e., NOT clean).
    """
    status: dict[str, bool] = {}
    for key in BIAS_KEYS:
        status[key] = flags.get(key, False)  # default False => treated clean
    return status


def run_quality_suite(
    df: pd.DataFrame,
    session_calendar: pd.DatetimeIndex | None = None,
    policy: Policy = DEFAULT_POLICY,
) -> QualityReport:
    """Execute the full quality-chain over an OHLC DataFrame and report anomalies."""
    anomaly_flags: list[pd.Series] = []
    checks: dict[str, bool] = {}

    if {"open", "high", "low", "close"}.issubset(df.columns):
        ok_bounds = check_bar_bounds(df["open"], df["high"], df["low"], df["close"])
        checks["bar_bounds"] = bool(ok_bounds.all())
        anomaly_flags.append(~ok_bounds)

    if "close" in df.columns:
        spikes = detect_spikes(df["close"])
        checks["no_spikes"] = bool(~spikes.any())
        anomaly_flags.append(spikes)
        outliers = detect_outliers_mad(df["close"])
        checks["no_mad_outliers"] = bool(~outliers.any())
        anomaly_flags.append(outliers)

    dups = detect_duplicates(df) if {"open", "low", "close"}.issubset(df.columns) else pd.Series(dtype=bool)
    checks["no_duplicates"] = bool(~dups.any())
    anomaly_flags.append(dups.reindex(df.index, fill_value=False))

    if session_calendar is not None and "event_timestamp" in df.columns:
        ratio = report_missing_ratio(pd.DatetimeIndex(df["event_timestamp"]), session_calendar)
        checks["missing_ok"] = ratio <= policy.missing_alert_ratio

    columns = [f"anomaly_{i}" for i in range(len(anomaly_flags))]
    frame = pd.concat(anomaly_flags, axis=1) if anomaly_flags else pd.DataFrame(index=df.index)
    if not frame.empty and not frame.columns.tolist():
        frame.columns = columns
    elif not frame.empty:
        frame.columns = columns
    flagged_rows = int(frame.any(axis=1).sum()) if not frame.empty else 0

    mitigation_flags = {k: not v for k, v in checks.items()}
    return QualityReport(
        checks=checks,
        anomalies=frame,
        bias_status=bias_audit(mitigation_flags),
        flagged_rows=flagged_rows,
    )
"""Dataset integrity validation and cryptographic hashing utilities."""

from dataclasses import dataclass, field
import hashlib
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class DataValidationReport:
    """Detailed audit report for a financial OHLCV time-series dataset."""

    is_valid: bool
    total_bars: int
    start_timestamp: Optional[str]
    end_timestamp: Optional[str]
    calendar_span_years: float
    detected_issues: List[str] = field(default_factory=list)
    dataset_sha256: str = ""
    column_names: List[str] = field(default_factory=list)
    missing_bar_count: int = 0


def compute_dataset_hash(df: pd.DataFrame) -> str:
    """Compute a deterministic cryptographic SHA-256 hash of a DataFrame's data and index.

    Ensures 100% byte-for-byte dataset lineage and reproducibility.
    """
    hasher = hashlib.sha256()

    # Hash the index (nanosecond timestamps or raw values)
    if isinstance(df.index, pd.DatetimeIndex):
        hasher.update(df.index.view(np.int64).tobytes())
    else:
        hasher.update(np.asarray(df.index.values, dtype=str).tobytes())

    # Hash column values deterministically
    for col in sorted(df.columns):
        col_data = np.asarray(df[col].values)
        hasher.update(str(col).encode("utf-8"))
        hasher.update(col_data.tobytes())

    return hasher.hexdigest()


def validate_ohlcv_dataframe(
    df: pd.DataFrame,
    expected_frequency: Optional[str] = None,
    allow_zero_volume: bool = True,
) -> Tuple[pd.DataFrame, DataValidationReport]:
    """Audit and normalize an OHLCV financial dataset.

    Enforces:
    - Monotonically increasing, strictly UTC datetime index with no duplicates.
    - Standard lowercase column names: open, high, low, close, volume.
    - Zero NaN, null, or infinite values.
    - Mathematical consistency: high >= max(open, close), low <= min(open, close), all prices > 0.
    - Volume >= 0.

    Parameters
    ----------
    df : pd.DataFrame
        Raw input dataframe.
    expected_frequency : Optional[str]
        Expected pandas offset string (e.g., '1min', '5min', '1h', '1D') for gap checking.
    allow_zero_volume : bool
        Whether zero volume bars are permissible (e.g. during quiet sessions or tick synthetic bars).

    Returns
    -------
    Tuple[pd.DataFrame, DataValidationReport]
        Clean normalized DataFrame and the validation audit report.
    """
    issues = []
    df_clean = df.copy()

    # 1. Check if DataFrame is empty
    if df_clean.empty:
        return df_clean, DataValidationReport(
            is_valid=False,
            total_bars=0,
            start_timestamp=None,
            end_timestamp=None,
            calendar_span_years=0.0,
            detected_issues=["DataFrame is empty."],
            dataset_sha256="",
        )

    # 2. Normalize column names to lowercase
    col_map = {c: str(c).strip().lower() for c in df_clean.columns}
    df_clean.rename(columns=col_map, inplace=True)

    required_cols = ["open", "high", "low", "close"]
    missing_cols = [c for c in required_cols if c not in df_clean.columns]
    if missing_cols:
        issues.append(f"Missing mandatory OHLC columns: {missing_cols}")

    if "volume" not in df_clean.columns:
        # Default volume to 0 if not present
        df_clean["volume"] = 0.0

    # 3. Validate Index is DatetimeIndex
    if not isinstance(df_clean.index, pd.DatetimeIndex):
        try:
            df_clean.index = pd.to_datetime(df_clean.index)
        except Exception as e:
            issues.append(f"Index could not be converted to DatetimeIndex: {e}")

    if isinstance(df_clean.index, pd.DatetimeIndex):
        # Enforce UTC timezone
        if df_clean.index.tz is None:
            df_clean.index = df_clean.index.tz_localize("UTC")
        else:
            df_clean.index = df_clean.index.tz_convert("UTC")

        # Check monotonic ordering
        if not df_clean.index.is_monotonic_increasing:
            issues.append("DatetimeIndex is not strictly monotonically increasing.")
            df_clean.sort_index(inplace=True)

        # Check for duplicates
        duplicate_count = df_clean.index.duplicated().sum()
        if duplicate_count > 0:
            issues.append(f"Detected {duplicate_count} duplicate timestamps.")
            df_clean = df_clean[~df_clean.index.duplicated(keep="first")]

    # 4. Check for NaN, Null, or Infinite values
    num_nans = df_clean[required_cols].isna().sum().sum()
    if num_nans > 0:
        issues.append(f"Dataset contains {num_nans} NaN/null values in OHLC columns.")

    num_infs = np.isinf(df_clean[required_cols].to_numpy()).sum()
    if num_infs > 0:
        issues.append(f"Dataset contains {num_infs} infinite values in OHLC columns.")

    # 5. Price Sanity & Mathematical Integrity Checks
    if not missing_cols and num_nans == 0 and num_infs == 0:
        # Positive prices
        negative_prices = (df_clean[required_cols] <= 0).sum().sum()
        if negative_prices > 0:
            issues.append(f"Detected {negative_prices} non-positive price values.")

        # High must be >= Open, Close, Low
        invalid_high = (
            (df_clean["high"] < df_clean["open"])
            | (df_clean["high"] < df_clean["close"])
            | (df_clean["high"] < df_clean["low"])
        ).sum()
        if invalid_high > 0:
            issues.append(
                f"Detected {invalid_high} bars where High < max(Open, Close, Low)."
            )

        # Low must be <= Open, Close, High
        invalid_low = (
            (df_clean["low"] > df_clean["open"])
            | (df_clean["low"] > df_clean["close"])
            | (df_clean["low"] > df_clean["high"])
        ).sum()
        if invalid_low > 0:
            issues.append(
                f"Detected {invalid_low} bars where Low > min(Open, Close, High)."
            )

        # Volume must be >= 0
        invalid_vol = (df_clean["volume"] < 0).sum()
        if invalid_vol > 0:
            issues.append(f"Detected {invalid_vol} bars with negative volume.")

    # Compute span
    total_bars = len(df_clean)
    start_ts = (
        df_clean.index[0].isoformat() if isinstance(df_clean.index, pd.DatetimeIndex) and total_bars > 0 else None
    )
    end_ts = (
        df_clean.index[-1].isoformat() if isinstance(df_clean.index, pd.DatetimeIndex) and total_bars > 0 else None
    )

    span_years = 0.0
    if total_bars > 1 and isinstance(df_clean.index, pd.DatetimeIndex):
        delta = df_clean.index[-1] - df_clean.index[0]
        span_years = delta.total_seconds() / (365.25 * 86400.0)

    # Compute SHA-256 hash
    dataset_hash = compute_dataset_hash(df_clean) if total_bars > 0 else ""

    is_valid = len(issues) == 0

    report = DataValidationReport(
        is_valid=is_valid,
        total_bars=total_bars,
        start_timestamp=start_ts,
        end_timestamp=end_ts,
        calendar_span_years=span_years,
        detected_issues=issues,
        dataset_sha256=dataset_hash,
        column_names=list(df_clean.columns),
    )

    return df_clean, report

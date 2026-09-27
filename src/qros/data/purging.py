"""Trade purging and autocorrelation embargoing utilities for cross-validation and split isolation."""

from typing import Generator, List, Optional, Tuple
import numpy as np
import pandas as pd


def purge_overlapping_labels(
    event_start_times: pd.Series,
    event_end_times: pd.Series,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
) -> pd.Series:
    """Identify and flag boolean mask of training events that temporally overlap with a test evaluation window.

    Prevents label leakage (López de Prado) where training observations use future information
    from open positions that span across split boundaries.

    Parameters
    ----------
    event_start_times : pd.Series
        Timestamps when trade events begin.
    event_end_times : pd.Series
        Timestamps when trade events terminate.
    test_start : pd.Timestamp
        Start timestamp of the test evaluation partition.
    test_end : pd.Timestamp
        End timestamp of the test evaluation partition.

    Returns
    -------
    pd.Series
        Boolean mask: True = KEEP (no overlap), False = PURGE (overlaps with test).
    """
    # Overlap condition:
    # Event starts within test: (start >= test_start) & (start <= test_end)
    # Event ends within test: (end >= test_start) & (end <= test_end)
    # Event wraps around test: (start <= test_start) & (end >= test_end)
    overlap = (
        ((event_start_times >= test_start) & (event_start_times <= test_end))
        | ((event_end_times >= test_start) & (event_end_times <= test_end))
        | ((event_start_times <= test_start) & (event_end_times >= test_end))
    )
    return ~overlap


def compute_embargo_cutoff(
    test_end: pd.Timestamp,
    index: pd.DatetimeIndex,
    embargo_bars: int,
) -> pd.Timestamp:
    """Calculate the post-test embargo cutoff timestamp.

    Samples between test_end and the embargo cutoff are excluded from downstream training
    to prevent autoregressive feature/return leakage.

    Parameters
    ----------
    test_end : pd.Timestamp
        End timestamp of the test partition.
    index : pd.DatetimeIndex
        Complete dataset datetime index.
    embargo_bars : int
        Number of bars to embargo.

    Returns
    -------
    pd.Timestamp
        The timestamp after which training samples may safely be included.
    """
    if embargo_bars <= 0:
        return test_end

    post_test_locs = np.where(index > test_end)[0]
    if len(post_test_locs) == 0:
        return test_end

    cutoff_idx = min(post_test_locs[0] + embargo_bars - 1, len(index) - 1)
    return index[cutoff_idx]


def purged_train_test_split(
    df: pd.DataFrame,
    test_start_pct: float,
    test_end_pct: float,
    holding_bars: int = 1,
    embargo_bars: int = 10,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Execute a purged and embargoed single Train/Test chronological split.

    Parameters
    ----------
    df : pd.DataFrame
        Input time-series DataFrame with DatetimeIndex.
    test_start_pct : float
        Percentage into dataset where test begins (e.g., 0.70).
    test_end_pct : float
        Percentage into dataset where test ends (e.g., 0.90).
    holding_bars : int
        Max holding horizon in bars for trade purge estimation.
    embargo_bars : int
        Number of bars to embargo after test partition.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        Purged & embargoed training set, and test set.
    """
    n = len(df)
    test_start_idx = int(n * test_start_pct)
    test_end_idx = int(n * test_end_pct)

    test_df = df.iloc[test_start_idx:test_end_idx].copy()
    test_start_time = df.index[test_start_idx]
    test_end_time = df.index[test_end_idx - 1]

    # Purging pre-test training data: must end before test_start_time
    pre_test_end_idx = max(0, test_start_idx - holding_bars)
    pre_test_train = df.iloc[:pre_test_end_idx]

    # Embargoing post-test training data
    post_test_start_idx = min(n, test_end_idx + embargo_bars)
    post_test_train = df.iloc[post_test_start_idx:]

    train_df = pd.concat([pre_test_train, post_test_train])
    return train_df, test_df

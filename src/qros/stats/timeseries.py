"""Part 10 verification metrics: cointegration, mean-reversion half-life, Hurst."""

from __future__ import annotations

import numpy as np

from qros.features.validate import adf_pvalue


def engle_granger_p(y: np.ndarray, x: np.ndarray) -> float:
    """Engle-Granger cointegration: ADF p-value of the OLS residual of y on x.

    Structural-edge verification requires this p < 0.001 (Part 10 ch.1).
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    mask = np.isfinite(y) & np.isfinite(x)
    y, x = y[mask], x[mask]
    if len(y) < 4:
        return float("nan")
    X = np.column_stack([np.ones(len(x)), x])
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return float("nan")
    resid = y - X @ beta
    return adf_pvalue(resid)


def ornstein_uhlenbeck_half_life(series: np.ndarray, dt: float = 1.0) -> float:
    """OU mean-reversion half-life tau = -ln(2)/k (days), k from OLS on y_t on y_{t-1}.

    Stat-arb gate requires tau < 5 days (Part 10 ch.1).
    """
    x = np.asarray(series, dtype=float)
    mask = np.isfinite(x)
    x = x[mask]
    if len(x) < 3:
        return float("nan")
    yt = x[1:]
    yt1 = x[:-1]
    # OLS: y_t = a + b * y_{t-1}; speed of mean reversion k = -ln(b)/dt
    b = np.polyfit(yt1, yt, 1)[0]
    if not (0 < b < 1):
        return float("inf") if b >= 1 else 0.0
    k = -np.log(b) / dt  # mean-reversion speed (per dt unit)
    tau = np.log(2.0) / k  # half-life = ln(2)/k
    return float(tau)


def hurst_exponent(x: np.ndarray, max_lag: int = 20) -> float:
    """Hurst exponent of a series (R/S method approximation)."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return float("nan")
    lags = range(2, min(max_lag, len(x) // 2))
    rs = []
    lag_vals = []
    for lag in lags:
        subs = np.array([x[i : i + lag] for i in range(0, len(x) - lag, lag)])
        if len(subs) < 2:
            continue
        mean_adj = subs - subs.mean(axis=1, keepdims=True)
        cumdev = np.cumsum(mean_adj, axis=1)
        r = np.max(cumdev, axis=1) - np.min(cumdev, axis=1)
        s = subs.std(axis=1, ddof=1)
        rs_vals = r / np.where(s == 0, np.nan, s)
        rs_vals = rs_vals[np.isfinite(rs_vals)]
        if len(rs_vals) == 0:
            continue
        rs.append(np.mean(rs_vals))
        lag_vals.append(lag)
    if len(lag_vals) < 2:
        return float("nan")
    slope = np.polyfit(np.log(lag_vals), np.log(rs), 1)[0]
    return float(slope)
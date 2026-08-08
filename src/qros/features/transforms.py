"""Part 4 ch.1-2: Mathematical feature transforms.

All scaling is backward-looking only — no global/full-sample fitting (Part 4 ch.1
[ZERO LOOK-AHEAD SCALING]). Formulas transcribed from the handbook tables.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def log_return(px: np.ndarray) -> np.ndarray:
    """r_t = ln(P_t / P_{t-1}); first element is NaN (no prior)."""
    px = np.asarray(px, dtype=float)
    out = np.full_like(px, np.nan)
    out[1:] = np.log(px[1:] / px[:-1])
    return out


def fraction_diff_ffd(x: np.ndarray, d: float) -> np.ndarray:
    """Fractional differentiation (Marcos Lopez de Prado), d in [0,1].

    Weight w0 = 1; w_k = -w_{k-1} * (d - k + 1) / k. Series min-computable
    from the backward window. d=0 -> identity; d=1 -> first difference.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return x.copy()
    if not (0.0 <= d <= 1.0):
        raise ValueError(f"fractional differentiation d must be in [0,1], got {d}")
    if d == 0.0:
        return x.copy()
    weights = [1.0]
    for k in range(1, n):
        weights.append(-weights[-1] * (d - k + 1.0) / k)
    weights = np.array(weights)
    out = np.full(n, np.nan)
    for t in range(n):
        w = weights[: t + 1]
        out[t] = float(np.dot(x[: t + 1][::-1], w))
    return out


def rolling_zscore(x: np.ndarray, window: int) -> np.ndarray:
    """Backward-looking rolling z-score: z_t = (x_t - mu_w) / sigma_w.

    Uses only the trailing ``window`` observations ending at t (never the future).
    """
    s = pd.Series(np.asarray(x, dtype=float))
    mu = s.rolling(window, min_periods=2).mean()
    sd = s.rolling(window, min_periods=2).std()
    return ((s - mu) / sd).to_numpy()


def percentile_rank(x: np.ndarray) -> np.ndarray:
    """Map features to uniform U(0,1) via the empirical (expanding) CDF."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    out = np.full(n, np.nan)
    for t in range(n):
        out[t] = (x[: t + 1] <= x[t]).sum() / (t + 1.0)
    return out


def order_book_imbalance(bid_size: np.ndarray, ask_size: np.ndarray) -> np.ndarray:
    """OBI = (Vbid,1 - Vask,1) / (Vbid,1 + Vask,1). Result in [-1, 1]."""
    bid = np.asarray(bid_size, dtype=float)
    ask = np.asarray(ask_size, dtype=float)
    denom = bid + ask
    out = np.zeros_like(denom)
    np.divide(bid - ask, denom, out=out, where=denom != 0)
    return out


def vwap(price: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """VWAP_t = sum(P_i * V_i) / sum(V_i) (cumulative)."""
    px = np.asarray(price, dtype=float)
    vol = np.asarray(volume, dtype=float)
    pv = px * vol
    cum_pv = np.cumsum(pv)
    cum_v = np.cumsum(vol)
    out = np.zeros_like(px)
    np.divide(cum_pv, cum_v, out=out, where=cum_v != 0)
    return out


def garman_klass_vol(open_: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """sigma_GK^2 = 0.5*(ln(H/L))^2 - (2*ln2 - 1)*(ln(C/O))^2."""
    o = np.asarray(open_, dtype=float)
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    c = np.asarray(close, dtype=float)
    term1 = 0.5 * np.log(h / l) ** 2
    term2 = (2.0 * np.log(2.0) - 1.0) * np.log(c / o) ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        var = term1 - term2
    return np.where(np.isfinite(var), var, np.nan)


def vpin(buy_volume: np.ndarray, sell_volume: np.ndarray, n_bars: int, bar_volume: float) -> np.ndarray:
    """VPIN = sum(|V_B - V_S|) / (n_bars * V_bar) over rolling buckets."""
    b = np.asarray(buy_volume, dtype=float)
    s = np.asarray(sell_volume, dtype=float)
    abs_diff = np.abs(b - s)
    if n_bars <= 1:
        return abs_diff / bar_volume
    roll = pd.Series(abs_diff).rolling(n_bars, min_periods=1).sum().to_numpy()
    return roll / (n_bars * bar_volume)


def relative_momentum(asset_ret: np.ndarray, benchmark_ret: np.ndarray, window: int) -> np.ndarray:
    """Cross-asset relative momentum: sum of asset - benchmark over window."""
    a = pd.Series(np.asarray(asset_ret, dtype=float))
    b = pd.Series(np.asarray(benchmark_ret, dtype=float))
    rel = (a - b).rolling(window, min_periods=1).sum().to_numpy()
    return rel


def gamma_exposure(gamma: np.ndarray, open_interest: np.ndarray, price: np.ndarray) -> np.ndarray:
    """GEX = sum(Gamma_i * OpenInterest_i * S^2 * 0.01)."""
    g = np.asarray(gamma, dtype=float)
    oi = np.asarray(open_interest, dtype=float)
    s = np.asarray(price, dtype=float)
    return g * oi * s**2 * 0.01
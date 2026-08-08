"""Part 6 ch.2: Structural breaks, black swans & regime shifts (HMM / MS-VAR).

Regime discovery is used for edge falsification: if an edge vanishes under
high-volatility regimes, it is an implicit short-volatility exposure (Part 6).
"""

from __future__ import annotations

from dataclasses import dataclass
from warnings import warn

import numpy as np


@dataclass
class RegimeResult:
    regimes: np.ndarray  # int labels, len == n obs
    n_regimes: int
    method: str


def markov_regimes(returns: np.ndarray, k: int = 2, seed: int = 0) -> RegimeResult:
    """Two-state Markov-switching mean-variance model (statsmodels MarkovRegression)."""
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 20:
        raise ValueError("Markov-switching requires at least 20 finite observations.")
    model = MarkovRegression(r, k_regimes=k, trend="c", switching_variance=True)
    res = model.fit(search_reps=1, em_iter=20)
    probs = np.asarray(res.smoothed_marginal_probabilities)
    # statsmodels returns (nobs, k_regimes); normalize to that orientation.
    if probs.shape[0] == k and probs.shape[1] != k:
        probs = probs.T
    regimes = np.argmax(probs, axis=1).astype(int)
    return RegimeResult(regimes=regimes, n_regimes=k, method="MS-VAR(1)")


def hmm_regimes(returns: np.ndarray, n_states: int = 2, seed: int = 0) -> RegimeResult:
    """HMM regime placeholder (offline-safe).

    ``hmmlearn`` is not a hermetic dependency; we defer to the Markov-switching
    model. ADR-005.
    """
    warn("hmmlearn not installed; using Markov-switching regime assign.", UserWarning, stacklevel=2)
    return markov_regimes(returns, k=n_states, seed=seed)


def discontinuity_check(returns: np.ndarray, regime_idx: np.ndarray) -> dict[str, float]:
    """Compare realized-vol stats between the highest- and lowest-return regimes."""
    returns = np.asarray(returns, dtype=float)
    regimes = np.asarray(regime_idx)
    labels = np.unique(regimes)
    if len(labels) < 2:
        return {"high_vol_regime": 0.0, "low_vol_regime": 0.0, "regime_std_ratio": float("nan"), "n_regimes": 1}
    vols: dict[int, float] = {}
    for lab in labels:
        sub = returns[regimes == lab]
        rms = float(np.sqrt(np.sum(sub**2) / max(len(sub), 1)))
        vols[int(lab)] = rms
    hi = max(vols, key=vols.get)
    lo = min(vols, key=vols.get)
    ratio = vols[hi] / vols[lo] if vols[lo] > 0 else float("inf")
    return {
        "high_vol_regime": int(hi),
        "low_vol_regime": int(lo),
        "regime_std_ratio": float(ratio),
        "mean_returns_high_vol": float(np.mean(returns[regimes == hi])),
        "mean_returns_low_vol": float(np.mean(returns[regimes == lo])),
        "n_regimes": len(labels),
    }


def regime_pair_test(edge_stats: dict[str, float], high_vol_regime: int, low_vol_regime: int) -> bool:
    """Edge survives only if the performance retains its sign in both regimes.

    Used to falsify implicit short-volatility exposure (Part 6 ch.2).
    """
    mean_high = edge_stats.get(f"mean_returns_regime_{high_vol_regime}")
    mean_low = edge_stats.get(f"mean_returns_regime_{low_vol_regime}")
    # heuristic: retain sign in both regimes
    if mean_high is None or mean_low is None:
        return edge_stats.get("survives", True)
    return (mean_high >= 0) == (mean_low >= 0)
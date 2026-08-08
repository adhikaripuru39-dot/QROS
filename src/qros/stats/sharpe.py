"""Part 8 ch.1: Sharpe ratio and the Deflated Sharpe Ratio (Bailey & Lopez de Prado).

DSR = P(SR > SR0 | N_trials, skew, kurt). Acceptance threshold: DSR p < 0.01.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from scipy import stats

from qros.governance.policy import DEFAULT_POLICY, Policy


def sharpe_ratio(r: np.ndarray, rf: float = 0.0, periods_per_year: int = 252) -> float:
    """Annualized Sharpe ratio of a return series."""
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return float("nan")
    excess = r - rf / periods_per_year
    sd = np.std(excess, ddof=1)
    if sd == 0:
        return 0.0
    return float(np.mean(excess) / sd * np.sqrt(periods_per_year))


def skew(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 3:
        return 0.0
    return float(stats.skew(r))


def kurtosis(r: np.ndarray) -> float:
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 4:
        return 3.0
    return float(stats.kurtosis(r, fisher=False))  # Pearson kurtosis


@dataclass
class DSRResult:
    sr: float
    dsr_prob: float
    p_value: float
    rejected: bool
    n_trials: int


def _sr_nonannualized(r: np.ndarray) -> float:
    """Per-period (non-annualized) Sharpe: mean/std. DSR uses this scale."""
    if len(r) < 2:
        return float("nan")
    sd = float(np.std(r, ddof=1))
    if sd == 0:
        return 0.0
    return float(np.mean(r) / sd)


def deflated_sharpe_ratio(
    returns: np.ndarray,
    n_trials: int,
    sr0: float = 0.0,
    seed: int = 0,
    policy: Policy = DEFAULT_POLICY,
) -> DSRResult:
    """Compute the Deflated Sharpe Ratio (Bailey & Lopez de Prado).

    sigma  = sqrt(1 - skew*sr + (kurt-1)/4*sr^2)
    d      = (sr_hat - sr0) * sqrt(N-1) / sigma
    DSR    = Phi(d); p = 1 - Phi(d)
    Reject the finding (i.e. the edge is *not* deflated-sound)
    when p >= policy.dsr_p_max.

    Both ``sr_hat`` and ``sr0`` are non-annualized per-period Sharpe values,
    consistent with the expected-max-SR null used for trial deflation.
    """
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 2:
        return DSRResult(float("nan"), float("nan"), float("nan"), True, n_trials)

    sr_hat = _sr_nonannualized(r)
    if not np.isfinite(sr_hat):
        return DSRResult(float("nan"), float("nan"), float("nan"), True, n_trials)

    # Trial-count deflation: with more trials the expected maximum SR under the
    # null rises, so a higher bar is required for the edge to survive.
    if n_trials > 1 and sr0 == 0.0:
        sr0 = expected_max_sr(n_trials, n)

    gamma3 = skew(r)
    gamma4 = kurtosis(r)
    sigma = np.sqrt(
        max(1.0 - gamma3 * sr_hat + (gamma4 - 1.0) / 4.0 * sr_hat**2, 1e-12)
    )
    d = (sr_hat - sr0) * np.sqrt(max(n - 1, 0)) / sigma
    dsr_prob = float(stats.norm.cdf(d))
    p_value = float(1.0 - dsr_prob)
    accepted = p_value < policy.dsr_p_max
    return DSRResult(sr=sr_hat, dsr_prob=dsr_prob, p_value=p_value, rejected=not accepted, n_trials=n_trials)


def expected_max_sr(n_trials: int, n_obs: int) -> float:
    """E[max SR over N_trials] under the null (Bailey & Lopez de Prado approximation)."""
    if n_trials <= 1:
        return 0.0
    euler = 0.5772156649015328606
    z = (1 - euler) * stats.norm.ppf(1 - 1.0 / n_trials) + euler * stats.norm.ppf(
        1 - 1.0 / (n_trials * np.e)
    )
    return z / np.sqrt(max(n_obs, 1) - 1)
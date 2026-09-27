"""Statistical moments, risk metrics, and performance calculations."""

from typing import Dict, Tuple
import numpy as np
from scipy import stats


def calculate_moments(returns: np.ndarray) -> Dict[str, float]:
    """Calculate sample mean, standard deviation, skewness, and excess kurtosis.

    Parameters
    ----------
    returns : np.ndarray
        1D array of return observations.

    Returns
    -------
    Dict[str, float]
        Dictionary with mean, std, skewness, excess_kurtosis.
    """
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n < 3:
        return {
            "mean": 0.0,
            "std": 0.0,
            "skewness": 0.0,
            "excess_kurtosis": 0.0,
        }

    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1))
    if std_val == 0.0:
        return {
            "mean": mean_val,
            "std": 0.0,
            "skewness": 0.0,
            "excess_kurtosis": 0.0,
        }

    skew_val = float(stats.skew(arr, bias=False))
    kurt_val = float(stats.kurtosis(arr, bias=False))  # Fisher's excess kurtosis (normal=0)

    return {
        "mean": mean_val,
        "std": std_val,
        "skewness": skew_val,
        "excess_kurtosis": kurt_val,
    }


def calculate_profit_factor(returns: np.ndarray) -> float:
    """Calculate Net Profit Factor: Sum of positive returns / Absolute sum of negative returns."""
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    pos_sum = np.sum(arr[arr > 0])
    neg_sum = np.abs(np.sum(arr[arr < 0]))

    if neg_sum == 0:
        return float("inf") if pos_sum > 0 else 1.0
    return float(pos_sum / neg_sum)


def calculate_sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    annualization_factor: float = 252.0,
) -> float:
    """Calculate annualized Sharpe Ratio.

    Parameters
    ----------
    returns : np.ndarray
        Discrete return series.
    risk_free_rate : float
        Periodic risk-free benchmark return (default: 0.0).
    annualization_factor : float
        Number of periods in a trading year (252 for daily, 252*24 for hourly, etc.).
    """
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return 0.0

    excess_returns = arr - risk_free_rate
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns, ddof=1)

    if std_excess == 0.0:
        return 0.0

    return float((mean_excess / std_excess) * np.sqrt(annualization_factor))


def calculate_sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    annualization_factor: float = 252.0,
) -> float:
    """Calculate annualized Sortino Ratio (penalizing only downside variance)."""
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return 0.0

    excess_returns = arr - risk_free_rate
    mean_excess = np.mean(excess_returns)
    downside = excess_returns[excess_returns < 0]

    if len(downside) == 0:
        return float("inf") if mean_excess > 0 else 0.0

    downside_std = np.sqrt(np.mean(downside**2))
    if downside_std == 0.0:
        return 0.0

    return float((mean_excess / downside_std) * np.sqrt(annualization_factor))


def calculate_var_cvar(
    returns: np.ndarray, alpha: float = 0.01
) -> Tuple[float, float]:
    """Calculate Historical Value at Risk (VaR) and Conditional VaR (Expected Shortfall).

    Parameters
    ----------
    returns : np.ndarray
        Return series.
    alpha : float
        Tail significance quantile (e.g. 0.01 for 99% VaR, 0.05 for 95% VaR).

    Returns
    -------
    Tuple[float, float]
        (Historical VaR, Conditional VaR / Expected Shortfall) as positive loss magnitudes.
    """
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return 0.0, 0.0

    # Sort ascending
    sorted_returns = np.sort(arr)
    var_idx = int(np.floor(alpha * len(sorted_returns)))
    var_idx = max(0, min(var_idx, len(sorted_returns) - 1))

    var_val = -sorted_returns[var_idx]
    tail_losses = sorted_returns[: var_idx + 1]
    cvar_val = -float(np.mean(tail_losses)) if len(tail_losses) > 0 else var_val

    return float(max(0.0, var_val)), float(max(0.0, cvar_val))


def calculate_effective_sample_size(
    returns: np.ndarray, max_lags: int = 20
) -> float:
    """Calculate effective sample size N_eff adjusting for autocorrelation in returns/trades.

    Formula: N_eff = N / (1 + 2 * sum_{k=1}^{max_lags} rho(k))
    """
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n <= 2:
        return float(n)

    arr_centered = arr - np.mean(arr)
    var_0 = np.dot(arr_centered, arr_centered)
    if var_0 == 0.0:
        return float(n)

    acf_sum = 0.0
    actual_lags = min(max_lags, n // 2)
    for lag in range(1, actual_lags + 1):
        c_k = np.dot(arr_centered[:-lag], arr_centered[lag:])
        rho_k = c_k / var_0
        if rho_k > 0:
            acf_sum += rho_k
        else:
            break  # Truncate at first non-positive autocorrelation per Geyer / initial positive sequence

    denominator = 1.0 + 2.0 * acf_sum
    return float(max(1.0, n / denominator))


def calculate_t_stat(returns: np.ndarray) -> Tuple[float, float]:
    """Calculate Student's t-statistic and 2-tailed p-value testing H_0: mean_return == 0."""
    arr = np.asarray(returns, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return 0.0, 1.0

    res = stats.ttest_1samp(arr, popmean=0.0)
    t_stat = float(res.statistic) if not np.isnan(res.statistic) else 0.0
    p_val = float(res.pvalue) if not np.isnan(res.pvalue) else 1.0
    return t_stat, p_val

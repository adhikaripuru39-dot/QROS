"""Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR) implementation.

References
----------
Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting
for Selection Bias, Backtest Overfitting and Non-Normality. Journal of Portfolio
Management, 40(5), 94-107.
"""

from typing import List, Optional, Tuple
import numpy as np
from scipy import stats
from qros.schemas.results import DSRResult

EULER_MASCHERONI = 0.57721566490153286060


def compute_expected_max_sharpe(
    trial_count_k: int, var_sharpe: float = 0.5
) -> float:
    """Calculate the expected maximum Sharpe Ratio among K independent/identically distributed trials.

    Parameters
    ----------
    trial_count_k : int
        Number of tested strategies / parameter combinations (K >= 1).
    var_sharpe : float
        Variance of the Sharpe Ratio distribution across trials (default: 0.5).

    Returns
    -------
    float
        Expected maximum Sharpe Ratio (SR*).
    """
    if trial_count_k <= 1:
        return 0.0

    k = float(trial_count_k)
    z1 = stats.norm.ppf(1.0 - 1.0 / k)
    z2 = stats.norm.ppf(1.0 - 1.0 / (k * np.e))

    expected_max = np.sqrt(var_sharpe) * (
        (1.0 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2
    )
    return float(max(0.0, expected_max))


def calculate_sharpe_std_error(
    observed_sharpe: float,
    sample_length_t: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,  # Pearson kurtosis (normal=3.0)
) -> float:
    """Calculate the asymptotic standard error of the Sharpe Ratio adjusting for non-normality.

    Formula
    -------
    sigma_SR = sqrt((1 - skew*SR + ((kurt - 1)/4)*SR^2) / (T - 1))

    Note: kurtosis argument is Pearson kurtosis (normal distribution = 3.0).
    """
    if sample_length_t <= 1:
        return 1.0

    sr = observed_sharpe
    t = float(sample_length_t)
    var_term = 1.0 - skewness * sr + ((kurtosis - 1.0) / 4.0) * (sr**2)

    # Protect against negative variance terms due to numerical edge cases
    var_term = max(1e-8, var_term)
    std_error = np.sqrt(var_term / (t - 1.0))
    return float(std_error)


def calculate_psr(
    observed_sharpe: float,
    benchmark_sharpe: float,
    sample_length_t: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """Calculate the Probabilistic Sharpe Ratio (PSR).

    PSR = Phi((observed_sr - benchmark_sr) / sigma_SR)
    """
    std_error = calculate_sharpe_std_error(
        observed_sharpe, sample_length_t, skewness, kurtosis
    )
    if std_error <= 0.0:
        return 1.0 if observed_sharpe >= benchmark_sharpe else 0.0

    z_stat = (observed_sharpe - benchmark_sharpe) / std_error
    return float(stats.norm.cdf(z_stat))


def calculate_dsr(
    observed_sharpe: float,
    trial_count_k: int,
    sample_length_t: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    var_sharpe: float = 0.5,
    dsr_hurdle: float = 0.95,
) -> DSRResult:
    """Calculate the Deflated Sharpe Ratio (DSR) per Bailey & López de Prado (2014).

    Corrects the observed Sharpe Ratio for:
    1. Selection bias & multiple testing across K trial variations.
    2. Non-normality (skewness and fat-tailed excess kurtosis).
    3. Sample length inflation (T observations).

    Parameters
    ----------
    observed_sharpe : float
        The non-annualized or periodic Sharpe ratio of the candidate strategy.
    trial_count_k : int
        Total number of trials / variations evaluated (K >= 1).
    sample_length_t : int
        Number of discrete observations (sample length T).
    skewness : float
        Sample skewness of return series.
    kurtosis : float
        Pearson kurtosis of return series (normal = 3.0). If excess kurtosis is passed, add 3.0.
    var_sharpe : float
        Variance of the Sharpe Ratio distribution across trials.
    dsr_hurdle : float
        Institutional acceptance hurdle (default: 0.95).

    Returns
    -------
    DSRResult
        Detailed DSR evaluation container.
    """
    sr_star = compute_expected_max_sharpe(trial_count_k, var_sharpe=var_sharpe)
    dsr_score = calculate_psr(
        observed_sharpe=observed_sharpe,
        benchmark_sharpe=sr_star,
        sample_length_t=sample_length_t,
        skewness=skewness,
        kurtosis=kurtosis,
    )

    is_significant = bool(dsr_score >= dsr_hurdle)

    return DSRResult(
        observed_sharpe=float(observed_sharpe),
        benchmark_sharpe=float(sr_star),
        dsr_score=float(dsr_score),
        trial_count_k=int(trial_count_k),
        sample_length_t=int(sample_length_t),
        skewness=float(skewness),
        kurtosis=float(kurtosis),
        is_statistically_significant=is_significant,
    )

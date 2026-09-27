"""Standardized statistical evaluation pipeline executing full validation battery."""

from typing import Dict, List, Optional
import numpy as np
from qros.schemas.hypothesis import HypothesisRecord
from qros.schemas.results import StatisticalResult
from qros.schemas.validation_profile import ValidationProfile
from qros.stats.bootstrap import bootstrap_sharpe_ci
from qros.stats.dsr import calculate_dsr
from qros.stats.moments import (
    calculate_effective_sample_size,
    calculate_moments,
    calculate_profit_factor,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_t_stat,
    calculate_var_cvar,
)
from qros.tracking.ledger import GlobalTrialLedger


def evaluate_statistical_profile(
    returns_net: np.ndarray,
    validation_profile: ValidationProfile,
    hypothesis_id: str = "QROS-HYP-000000",
    trial_count_k: int = 1,
    observation_count_t: Optional[int] = None,
    calendar_span_years: Optional[float] = None,
    n_bootstrap_resamples: int = 2000,
    random_seed: int = 42,
) -> StatisticalResult:
    r"""Execute the full QROS statistical validation battery on a net return series.

    Evaluates:
    1. Sample power & observations ($N \ge N_{\text{min}}$, $T \ge T_{\text{min}}$, Span $\ge \text{Span}_{\text{min}}$).
    2. Effective sample size ($N_{\text{eff}}$) with serial autocorrelation adjustment.
    3. Net Profit Factor ($\text{PF} \ge \text{PF}_{\text{target}}$).
    4. Net Annualized Sharpe Ratio ($\text{SR} \ge \text{SR}_{\text{target}}$).
    5. Deflated Sharpe Ratio ($\text{DSR} \ge \text{DSR}_{\text{hurdle}}$) adjusting for global trial count $K$.
    6. Non-parametric Stationary Block Bootstrap 95% Confidence Interval ($CI_{95\%}^{\text{lower}} > 0.0$).
    7. Higher moments (skewness, kurtosis) and tail risk (99% VaR and CVaR).

    Parameters
    ----------
    returns_net : np.ndarray
        Array of net returns after all transaction friction deductions.
    validation_profile : ValidationProfile
        Declared validation regime and parameter thresholds.
    hypothesis_id : str
        Hypothesis identifier.
    trial_count_k : int
        Total cumulative trial count $K$ for DSR calculation.
    observation_count_t : Optional[int]
        Total underlying bar observations (default: len(returns_net)).
    calendar_span_years : Optional[float]
        Data span in years (default: profile.min_calendar_span_years).
    n_bootstrap_resamples : int
        Number of bootstrap replications.
    random_seed : int
        Deterministic random seed.

    Returns
    -------
    StatisticalResult
        Comprehensive result container with individual gate pass/fail flags and failure reasons.
    """
    arr = np.asarray(returns_net, dtype=np.float64)
    arr = arr[~np.isnan(arr)]
    n_samples = len(arr)

    obs_t = observation_count_t if observation_count_t is not None else max(n_samples, validation_profile.min_observations)
    span_yrs = calendar_span_years if calendar_span_years is not None else validation_profile.min_calendar_span_years

    # 1. Moments & Core Performance
    moments = calculate_moments(arr)
    pf_net = calculate_profit_factor(arr)
    sharpe_net = calculate_sharpe_ratio(arr)
    sortino_net = calculate_sortino_ratio(arr)
    var_99, cvar_99 = calculate_var_cvar(arr, alpha=0.01)
    t_stat, p_val = calculate_t_stat(arr)
    n_eff = calculate_effective_sample_size(arr)

    # 2. Deflated Sharpe Ratio (DSR)
    # Pearson kurtosis = excess_kurtosis + 3.0
    pearson_kurt = moments["excess_kurtosis"] + 3.0

    dsr_res = calculate_dsr(
        observed_sharpe=sharpe_net,
        trial_count_k=max(1, trial_count_k),
        sample_length_t=max(10, obs_t),
        skewness=moments["skewness"],
        kurtosis=pearson_kurt,
        dsr_hurdle=validation_profile.dsr_hurdle,
    )

    # 3. Stationary Block Bootstrap 95% Confidence Interval
    boot_res = bootstrap_sharpe_ci(
        returns=arr,
        n_resamples=n_bootstrap_resamples,
        expected_block_length=float(validation_profile.embargo_bars),
        random_seed=random_seed,
    )

    # 4. Gate Evaluations
    failures: List[str] = []

    # Sample power gate
    pass_n = n_samples >= validation_profile.min_trades
    if not pass_n:
        failures.append(
            f"Insufficient discrete trades: N={n_samples} < {validation_profile.min_trades}"
        )

    pass_neff = n_eff >= validation_profile.min_effective_trades
    if not pass_neff:
        failures.append(
            f"Insufficient effective trades: N_eff={n_eff:.1f} < {validation_profile.min_effective_trades}"
        )

    pass_t = obs_t >= validation_profile.min_observations
    if not pass_t:
        failures.append(
            f"Insufficient observations: T={obs_t} < {validation_profile.min_observations}"
        )

    pass_span = span_yrs >= validation_profile.min_calendar_span_years
    if not pass_span:
        failures.append(
            f"Insufficient calendar span: Span={span_yrs:.1f}y < {validation_profile.min_calendar_span_years}y"
        )

    passed_sample_power = pass_n and pass_neff and pass_t and pass_span

    # Profit Factor Gate
    passed_profit_factor = pf_net >= validation_profile.target_profit_factor
    if not passed_profit_factor:
        failures.append(
            f"Net Profit Factor failed: PF={pf_net:.2f} < {validation_profile.target_profit_factor:.2f}"
        )

    # Sharpe Gate
    passed_sharpe = sharpe_net >= validation_profile.target_sharpe
    if not passed_sharpe:
        failures.append(
            f"Net Sharpe failed: SR={sharpe_net:.2f} < {validation_profile.target_sharpe:.2f}"
        )

    # DSR Gate
    passed_dsr = dsr_res.is_statistically_significant
    if not passed_dsr:
        failures.append(
            f"DSR score failed: DSR={dsr_res.dsr_score:.3f} < {validation_profile.dsr_hurdle:.3f} (K={trial_count_k})"
        )

    # Bootstrap CI Gate
    passed_bootstrap_ci = boot_res.ci_strictly_positive
    if not passed_bootstrap_ci:
        failures.append(
            f"Bootstrap 95% CI lower bound is non-positive: CI_lower={boot_res.ci_lower_95:.3f} <= 0.0"
        )

    overall_pass = (
        passed_sample_power
        and passed_profit_factor
        and passed_sharpe
        and passed_dsr
        and passed_bootstrap_ci
    )

    return StatisticalResult(
        hypothesis_id=hypothesis_id,
        sample_size_n=n_samples,
        effective_sample_size_neff=n_eff,
        observation_count_t=obs_t,
        calendar_span_years=span_yrs,
        mean_return_net=moments["mean"],
        std_return_net=moments["std"],
        skewness=moments["skewness"],
        excess_kurtosis=moments["excess_kurtosis"],
        profit_factor_net=pf_net,
        annualized_sharpe_net=sharpe_net,
        annualized_sortino_net=sortino_net,
        historical_var_99=var_99,
        expected_shortfall_cvar_99=cvar_99,
        t_statistic=t_stat,
        p_value=p_val,
        dsr_result=dsr_res,
        bootstrap_result=boot_res,
        passed_sample_power=passed_sample_power,
        passed_profit_factor=passed_profit_factor,
        passed_sharpe=passed_sharpe,
        passed_dsr=passed_dsr,
        passed_bootstrap_ci=passed_bootstrap_ci,
        overall_gate_pass=overall_pass,
        failure_reasons=failures,
    )

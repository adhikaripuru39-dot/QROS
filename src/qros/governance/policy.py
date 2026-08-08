"""QROS governance policy — single source of truth for every institutional threshold.

All thresholds in this module are transcribed from the QROS Master Handbook
Parts 1-10. Tests assert against these values rather than re-literal thresholds.

References:
- Part 1 Data Collection Framework (checklists, case thresholds)
- Part 2 Data Quality Management (MAD Z, discrepancy, spread caps)
- Part 4 Feature Engineering (ADF, VIF, correlation)
- Part 7 Research Pipeline (stage gate thresholds)
- Part 8 Statistical Methodology (DSR, FDR, FWER, CPCV)
- Part 10 Edge Discovery (cointegration, momentum t, OU half-life, capacity)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Policy:
    # ---------- Part 1 / Part 2 : data quality ----------
    # Part 2 1.1 : alert if missing-bar fraction exceeds 0.05% of daily universe
    missing_alert_ratio: float = 0.0005
    # Part 2 1.2 : rolling MAD filter |P - M_med|/MAD > 8.0 flags bad tick
    mad_z_threshold: float = 8.0
    # Part 1 5.1 : |P_t - P_{t-1}| > 10 * sigma flagged as spike candidate
    spike_sigma_threshold: float = 10.0
    # Part 2 1.5 : flag close discrepancy exceeding 1 basis point (0.01%)
    vendor_discrepancy_pct: float = 0.0001
    # Part 1 4.2 : bid-ask spread must be <= 500 basis points of mid-price
    max_ask_bid_spread_bp: float = 500.0

    # ---------- Part 4 : feature gates ----------
    # Part 4 ch.3 : ADF p-value < 0.05 required for all feature series
    adf_p_max: float = 0.05
    # Part 4 ch.3 : eliminate features with variance inflation factor > 10.0
    vif_max: float = 10.0
    # Part 4 ch.3 : drop features with |correlation| > 0.85
    corr_max: float = 0.85

    # ---------- Part 8 : statistical methodology ----------
    # Part 8 ch.1 : DSR p-value < 0.01 required for backtest acceptance
    dsr_p_max: float = 0.01
    # Part 8 ch.1 : FDR-BH target false discovery rate q* <= 0.05
    fdr_q_max: float = 0.05
    # Part 8 ch.1 : FWER-Holm alpha = 0.01
    holm_alpha: float = 0.01
    # Part 8 ch.1 : CPCV embargo = 1% of total sample
    cpcv_embargo_pct: float = 0.01
    # Part 8 ch.1 : CPCV requires number of paths >= 16
    cpcv_min_paths: int = 16
    # Part 8 ch.1 : probability of backtest overfitting < 0.10
    pbo_max: float = 0.10
    # Part 8 ch.2 : permutation null constructed over 10,000 shuffles
    permutation_n: int = 10_000

    # ---------- Part 7 : stage gate thresholds ----------
    # Stage 9 Statistical Testing
    stage9_t_min: float = 3.0
    stage9_p_max: float = 0.001
    # Stage 10 Robustness Testing : stable within +/-50% parameter shift
    stage10_param_shift: float = 0.50
    # Stage 11 Walk-Forward Validation
    stage11_oos_sharpe_min: float = 2.0
    stage11_maxdd_max: float = 0.15
    # Stage 12 Replication : secondary engine code match > 99.9%
    stage12_corr_min: float = 0.999

    # ---------- Part 10 : edge discovery ----------
    # Cointegration (Engle-Granger) p < 0.001 for structural edges
    cointegration_p_max: float = 0.001
    # Behavioral edge: cross-sectional momentum t-stat > 3.5
    behavioral_t_min: float = 3.5
    # Stat-arb: Ornstein-Uhlenbeck mean-reversion half-life < 5 days
    ou_half_life_days_max: float = 5.0
    # Curve-fitting check: perturbation window of +/-10%
    perturbation_window: float = 0.10
    # Capacity bottleneck: edge only for trivial (<$10k) trades
    tiny_size_usd: float = 10_000.0
    institutional_size_usd: float = 50_000_000.0


DEFAULT_POLICY = Policy()


def render_summary(policy: Policy = DEFAULT_POLICY) -> dict[str, float]:
    """Flatten the policy into a JSON-serializable dict for reporting."""
    return asdict(policy)
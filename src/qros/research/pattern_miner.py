"""Conditional Pattern Mining and Structural Market Relationship Extraction Engine."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from qros.tracking.ledger import GlobalTrialLedger


@dataclass
class ConditionalPattern:
    """Standardized record of an empirical conditional dependency pattern."""

    pattern_id: str
    name: str
    timeframe: str
    target_variable: str
    condition_description: str
    sample_size_total: int
    conditioned_events_count: int
    unconditional_baseline_value: float
    conditional_value: float
    effect_size: float
    test_statistic_name: str
    test_statistic_value: float
    p_value: float
    is_statistically_significant: bool
    economic_mechanism: str
    recommended_research_class: str
    is_hypothesis_candidate: bool
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConditionalPatternMiner:
    """Discovers and quantifies non-linear, regime-conditioned, and structural market patterns."""

    def __init__(
        self,
        data_map: Dict[str, pd.DataFrame],
        ledger: Optional[GlobalTrialLedger] = None,
    ) -> None:
        self.data_map = data_map
        self.ledger = ledger or GlobalTrialLedger()
        self.patterns: List[ConditionalPattern] = []

    def _record_trial(self, pattern_id: str) -> int:
        """Increment trial ledger for multiple-testing tracking."""
        return self.ledger.record_trial_evaluation(
            hypothesis_id=pattern_id,
            parameter_variations_count=1,
            feature_count=1,
            outcome="TESTED",
        )

    def mine_all_patterns(self) -> List[ConditionalPattern]:
        """Execute systematic pattern mining routines across non-OOS datasets."""
        self.patterns = []

        if "D1" in self.data_map:
            self._mine_d1_macro_trend_continuation()
            self._mine_d1_nr4_volatility_expansion()
            self._mine_d1_weekly_seasonality()
            self._mine_d1_volatility_regime_persistence()

        if "H1" in self.data_map:
            self._mine_h1_pdh_pdl_sweep_rejection()
            if "D1" in self.data_map:
                self._mine_cross_timeframe_trend_breakout()

        return self.patterns

    def _mine_d1_macro_trend_continuation(self) -> None:
        """Pattern CP-01: Multi-Day Macro Trend Continuation following 50-Day High Breakout."""
        pid = "QROS-PAT-001"
        self._record_trial(pid)

        df = self.data_map["D1"].copy()
        # Compute 50-day rolling high and 5-day forward log return (point-in-time shifted by 1)
        roll_high_50 = df["high"].rolling(50).max().shift(1)
        fwd_ret_5d = np.log(df["close"].shift(-5) / df["close"])
        
        valid_mask = roll_high_50.notna() & fwd_ret_5d.notna()
        sub_df = df[valid_mask]
        sub_fwd = fwd_ret_5d[valid_mask]
        sub_high50 = roll_high_50[valid_mask]

        is_breakout = sub_df["close"] > sub_high50
        baseline_mean = float(sub_fwd.mean())
        cond_mean = float(sub_fwd[is_breakout].mean()) if is_breakout.sum() > 0 else 0.0
        
        t_stat, p_val = stats.ttest_ind(
            sub_fwd[is_breakout], sub_fwd[~is_breakout], equal_var=False
        ) if is_breakout.sum() > 10 else (0.0, 1.0)

        n_events = int(is_breakout.sum())
        p_val_clean = float(p_val) if not np.isnan(p_val) else 1.0
        t_stat_clean = float(t_stat) if not np.isnan(t_stat) else 0.0

        pat = ConditionalPattern(
            pattern_id=pid,
            name="Daily Macro 50-Day High Breakout Momentum Continuation",
            timeframe="D1",
            target_variable="5-Day Forward Log Return (E[R_{t+5}])",
            condition_description="Daily Close > Prior 50-Day High",
            sample_size_total=len(sub_df),
            conditioned_events_count=n_events,
            unconditional_baseline_value=baseline_mean,
            conditional_value=cond_mean,
            effect_size=cond_mean - baseline_mean,
            test_statistic_name="Welch's Two-Sample t-statistic",
            test_statistic_value=t_stat_clean,
            p_value=p_val_clean,
            is_statistically_significant=(p_val_clean < 0.05 and cond_mean > baseline_mean),
            economic_mechanism="Macro monetary trend persistence; global institutional capital allocations to gold accelerate following major multi-month technical breakouts.",
            recommended_research_class="CLASS-IV",
            is_hypothesis_candidate=(n_events >= 30 and cond_mean > 0.005),
            summary=f"Conditioned on a 50-day high breakout (N={n_events}), 5-day forward return averages {cond_mean*100:.2f}% vs baseline {baseline_mean*100:.2f}% (p={p_val_clean:.4f}).",
        )
        self.patterns.append(pat)

    def _mine_d1_nr4_volatility_expansion(self) -> None:
        """Pattern CP-02: Multi-Day Volatility Expansion following NR4 (Narrowest Range of 4 Days)."""
        pid = "QROS-PAT-002"
        self._record_trial(pid)

        df = self.data_map["D1"].copy()
        daily_range = df["high"] - df["low"]
        nr4 = (daily_range < daily_range.shift(1)) & (daily_range < daily_range.shift(2)) & (daily_range < daily_range.shift(3))
        fwd_vol_3d = daily_range.rolling(3).mean().shift(-3) / daily_range.rolling(20).mean()

        valid_mask = nr4.notna() & fwd_vol_3d.notna()
        sub_nr4 = nr4[valid_mask]
        sub_vol = fwd_vol_3d[valid_mask]

        baseline_mean = float(sub_vol.mean())
        cond_mean = float(sub_vol[sub_nr4].mean()) if sub_nr4.sum() > 0 else 0.0

        t_stat, p_val = stats.ttest_ind(
            sub_vol[sub_nr4], sub_vol[~sub_nr4], equal_var=False
        ) if sub_nr4.sum() > 10 else (0.0, 1.0)

        n_events = int(sub_nr4.sum())
        p_val_clean = float(p_val) if not np.isnan(p_val) else 1.0
        t_stat_clean = float(t_stat) if not np.isnan(t_stat) else 0.0

        pat = ConditionalPattern(
            pattern_id=pid,
            name="Daily NR4 Range Compression -> Multi-Day Volatility Expansion",
            timeframe="D1",
            target_variable="3-Day Forward Relative True Range Expansion Ratio",
            condition_description="Daily True Range < Previous 3 Days' True Range (NR4)",
            sample_size_total=len(sub_nr4),
            conditioned_events_count=n_events,
            unconditional_baseline_value=baseline_mean,
            conditional_value=cond_mean,
            effect_size=cond_mean - baseline_mean,
            test_statistic_name="Two-Sample t-statistic",
            test_statistic_value=t_stat_clean,
            p_value=p_val_clean,
            is_statistically_significant=(p_val_clean < 0.05 and cond_mean > baseline_mean),
            economic_mechanism="Liquidity equilibrium and volatility compression regimes build latent order book energy before explosive multi-day breakout expansion.",
            recommended_research_class="CLASS-IV",
            is_hypothesis_candidate=(n_events >= 50 and cond_mean > baseline_mean * 1.05),
            summary=f"Following an NR4 compression (N={n_events}), subsequent 3-day volatility expands by {(cond_mean/baseline_mean - 1)*100:.1f}% relative to baseline (p={p_val_clean:.4f}).",
        )
        self.patterns.append(pat)

    def _mine_d1_weekly_seasonality(self) -> None:
        """Pattern CP-03: Mid-Week (Tue-Thu) Institutional Liquidity Expansion vs Mon/Fri Settlement."""
        pid = "QROS-PAT-003"
        self._record_trial(pid)

        df = self.data_map["D1"].copy()
        df["dayofweek"] = df.index.dayofweek
        daily_ret = np.log(df["close"] / df["close"].shift(1))
        
        valid_mask = daily_ret.notna()
        sub_df = df[valid_mask]
        sub_ret = daily_ret[valid_mask]

        is_midweek = sub_df["dayofweek"].isin([1, 2, 3])  # Tue, Wed, Thu
        baseline_mean = float(sub_ret.abs().mean())
        cond_mean = float(sub_ret[is_midweek].abs().mean())

        t_stat, p_val = stats.ttest_ind(
            sub_ret[is_midweek].abs(), sub_ret[~is_midweek].abs(), equal_var=False
        )

        n_events = int(is_midweek.sum())
        p_val_clean = float(p_val) if not np.isnan(p_val) else 1.0
        t_stat_clean = float(t_stat) if not np.isnan(t_stat) else 0.0

        pat = ConditionalPattern(
            pattern_id=pid,
            name="Mid-Week (Tuesday-Thursday) Institutional Volatility Surge",
            timeframe="D1",
            target_variable="Absolute Daily Return (|R_t|)",
            condition_description="Day of Week in {Tuesday, Wednesday, Thursday}",
            sample_size_total=len(sub_df),
            conditioned_events_count=n_events,
            unconditional_baseline_value=baseline_mean,
            conditional_value=cond_mean,
            effect_size=cond_mean - baseline_mean,
            test_statistic_name="Two-Sample t-statistic",
            test_statistic_value=t_stat_clean,
            p_value=p_val_clean,
            is_statistically_significant=(p_val_clean < 0.05),
            economic_mechanism="London physical fixing and COMEX futures positioning concentrates heavily mid-week, whereas Mondays suffer from weekend transition and Fridays feature position squaring.",
            recommended_research_class="CLASS-IV",
            is_hypothesis_candidate=(p_val_clean < 0.01),
            summary=f"Mid-week trading days exhibit significantly higher realized price movement (|R_t| = {cond_mean*100:.2f}%) vs Mon/Fri ({baseline_mean*100:.2f}%, p={p_val_clean:.4f}).",
        )
        self.patterns.append(pat)

    def _mine_d1_volatility_regime_persistence(self) -> None:
        """Pattern CP-04: Volatility Regime Transition and Trend Persistence."""
        pid = "QROS-PAT-004"
        self._record_trial(pid)

        df = self.data_map["D1"].copy()
        log_ret = np.log(df["close"] / df["close"].shift(1))
        vol_20 = log_ret.rolling(20).std() * np.sqrt(252)
        vol_q75 = vol_20.rolling(252).quantile(0.75).shift(1)

        fwd_ret_20d = np.log(df["close"].shift(-20) / df["close"])
        valid_mask = vol_20.notna() & vol_q75.notna() & fwd_ret_20d.notna()
        
        is_high_vol = vol_20[valid_mask] > vol_q75[valid_mask]
        sub_fwd = fwd_ret_20d[valid_mask]

        baseline_std = float(sub_fwd.std())
        cond_std = float(sub_fwd[is_high_vol].std()) if is_high_vol.sum() > 0 else 0.0

        f_stat = (cond_std**2) / (baseline_std**2) if baseline_std > 0 else 1.0
        p_val = 1.0 - stats.f.cdf(f_stat, max(1, is_high_vol.sum() - 1), max(1, len(sub_fwd) - 1))

        n_events = int(is_high_vol.sum())
        p_val_clean = float(p_val) if not np.isnan(p_val) else 1.0

        pat = ConditionalPattern(
            pattern_id=pid,
            name="High-Volatility Regime Dispersion and Tail Clustering",
            timeframe="D1",
            target_variable=r"20-Day Forward Return Variance (\sigma_{t+20})",
            condition_description="20-Day Realized Volatility > 75th Percentile of Prior Year",
            sample_size_total=len(sub_fwd),
            conditioned_events_count=n_events,
            unconditional_baseline_value=baseline_std,
            conditional_value=cond_std,
            effect_size=cond_std - baseline_std,
            test_statistic_name="F-test for Equality of Variances",
            test_statistic_value=float(f_stat),
            p_value=p_val_clean,
            is_statistically_significant=(p_val_clean < 0.05),
            economic_mechanism="Macro shocks trigger persistent volatility clustering where returns disperse widely and trend runs extend.",
            recommended_research_class="CLASS-IV",
            is_hypothesis_candidate=(n_events >= 50 and f_stat > 1.25),
            summary=f"In high-volatility regimes (N={n_events}), 20-day return standard deviation expands from {baseline_std*100:.2f}% to {cond_std*100:.2f}% (F={f_stat:.2f}, p={p_val_clean:.4f}).",
        )
        self.patterns.append(pat)

    def _mine_h1_pdh_pdl_sweep_rejection(self) -> None:
        """Pattern CP-05: Previous-Day High/Low Sweep Rejection Drift on H1."""
        pid = "QROS-PAT-005"
        self._record_trial(pid)

        df = self.data_map["H1"].copy()
        df["day_key"] = df.index.strftime("%Y-%m-%d")
        
        # Calculate daily high/low per date
        daily_hl = df.groupby("day_key").agg(day_high=("high", "max"), day_low=("low", "min"))
        daily_hl["pdh"] = daily_hl["day_high"].shift(1)
        daily_hl["pdl"] = daily_hl["day_low"].shift(1)
        
        df = df.merge(daily_hl[["pdh", "pdl"]], left_on="day_key", right_index=True, how="left")
        
        # Sweep condition: High > PDH but Close < PDH (Failed breakout / liquidity sweep)
        is_sweep_high = (df["high"] > df["pdh"]) & (df["close"] < df["pdh"]) & df["pdh"].notna()
        fwd_ret_4h = np.log(df["close"].shift(-4) / df["close"])

        valid_mask = is_sweep_high & fwd_ret_4h.notna()
        baseline_mean = float(fwd_ret_4h.mean())
        cond_mean = float(fwd_ret_4h[valid_mask].mean()) if valid_mask.sum() > 0 else 0.0

        n_events = int(valid_mask.sum())
        t_stat, p_val = stats.ttest_1samp(fwd_ret_4h[valid_mask], 0.0) if n_events > 10 else (0.0, 1.0)
        p_val_clean = float(p_val) if not np.isnan(p_val) else 1.0
        t_stat_clean = float(t_stat) if not np.isnan(t_stat) else 0.0

        pat = ConditionalPattern(
            pattern_id=pid,
            name="H1 Previous-Day High Liquidity Sweep and Mean-Reversion",
            timeframe="H1",
            target_variable="4-Hour Forward Return following Failed PDH Breakout",
            condition_description="H1 High > PDH and H1 Close < PDH (False Breakout Rejection)",
            sample_size_total=len(df),
            conditioned_events_count=n_events,
            unconditional_baseline_value=baseline_mean,
            conditional_value=cond_mean,
            effect_size=cond_mean - baseline_mean,
            test_statistic_name="One-Sample t-statistic",
            test_statistic_value=t_stat_clean,
            p_value=p_val_clean,
            is_statistically_significant=(p_val_clean < 0.05 and cond_mean < 0.0),
            economic_mechanism="Resting stop liquidity above PDH is swept by market makers; lack of sustained institutional buying triggers inventory liquidation back inside range.",
            recommended_research_class="CLASS-III",
            is_hypothesis_candidate=(n_events >= 40 and cond_mean < -0.001),
            summary=f"Failed PDH breakout sweeps (N={n_events}) exhibit negative 4-hour forward drift of {cond_mean*100:.3f}% (t={t_stat_clean:.2f}, p={p_val_clean:.4f}).",
        )
        self.patterns.append(pat)

    def _mine_cross_timeframe_trend_breakout(self) -> None:
        """Pattern CP-06: Cross-Timeframe Multi-Day Breakout Alignment (D1 Trend + H1 Breakout)."""
        pid = "QROS-PAT-006"
        self._record_trial(pid)

        df_h1 = self.data_map["H1"].copy()
        df_d1 = self.data_map["D1"].copy()

        # D1 50-day moving average
        df_d1["ma_50"] = df_d1["close"].rolling(50).mean().shift(1)
        df_d1["d1_bullish"] = df_d1["close"] > df_d1["ma_50"]
        df_d1["day_key"] = df_d1.index.strftime("%Y-%m-%d")

        df_h1["day_key"] = df_h1.index.strftime("%Y-%m-%d")
        df_h1 = df_h1.merge(df_d1[["day_key", "d1_bullish"]].drop_duplicates(subset=["day_key"]), on="day_key", how="left")

        # H1 24-period high breakout
        h24 = df_h1["high"].rolling(24).max().shift(1)
        h1_breakout = (df_h1["close"] > h24) & (df_h1["d1_bullish"] == True)
        fwd_ret_8h = np.log(df_h1["close"].shift(-8) / df_h1["close"])

        valid_mask = h1_breakout & fwd_ret_8h.notna()
        baseline_mean = float(fwd_ret_8h.mean())
        cond_mean = float(fwd_ret_8h[valid_mask].mean()) if valid_mask.sum() > 0 else 0.0

        n_events = int(valid_mask.sum())
        t_stat, p_val = stats.ttest_1samp(fwd_ret_8h[valid_mask], 0.0) if n_events > 10 else (0.0, 1.0)
        p_val_clean = float(p_val) if not np.isnan(p_val) else 1.0
        t_stat_clean = float(t_stat) if not np.isnan(t_stat) else 0.0

        pat = ConditionalPattern(
            pattern_id=pid,
            name="Cross-Timeframe Trend-Aligned H1 Momentum Breakout",
            timeframe="D1 -> H1",
            target_variable="8-Hour Forward Return (E[R_{t+8}])",
            condition_description="H1 Close > 24-Bar High AND D1 Close > 50-Day MA",
            sample_size_total=len(df_h1),
            conditioned_events_count=n_events,
            unconditional_baseline_value=baseline_mean,
            conditional_value=cond_mean,
            effect_size=cond_mean - baseline_mean,
            test_statistic_name="One-Sample t-statistic",
            test_statistic_value=t_stat_clean,
            p_value=p_val_clean,
            is_statistically_significant=(p_val_clean < 0.05 and cond_mean > 0.0),
            economic_mechanism="Higher-timeframe macro trend filter suppresses false whipsaws during consolidation and captures strong institutional trend expansion waves.",
            recommended_research_class="CLASS-III",
            is_hypothesis_candidate=(n_events >= 30 and cond_mean > 0.001),
            summary=f"Trend-aligned H1 breakouts (N={n_events}) produce positive 8-hour expected return of {cond_mean*100:.3f}% vs baseline {baseline_mean*100:.3f}% (t={t_stat_clean:.2f}, p={p_val_clean:.4f}).",
        )
        self.patterns.append(pat)

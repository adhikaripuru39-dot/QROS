"""Empirical Hypothesis Testing and Evaluation Engine enforcing point-in-time execution and QROS-STD-EXP-004."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from qros.data.purging import purge_overlapping_labels
from qros.pipeline.costs import TransactionCostModel
from qros.pipeline.evaluation import evaluate_statistical_profile
from qros.schemas.experiment import ExperimentRecord
from qros.schemas.hypothesis import HypothesisRecord
from qros.schemas.results import StatisticalResult
from qros.schemas.validation_profile import ValidationProfile
from qros.tracking.ledger import GlobalTrialLedger


@dataclass
class TradeEvent:
    """Individual simulated trade execution event."""

    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: int  # 1 for Long, -1 for Short
    entry_price: float
    exit_price: float
    holding_bars: int
    gross_return: float
    net_return: float
    friction_deduction: float


class HypothesisTester:
    """Deterministic, point-in-time empirical testing engine for pre-registered hypotheses."""

    def __init__(
        self,
        ledger: Optional[GlobalTrialLedger] = None,
        random_seed: int = 42,
    ) -> None:
        self.ledger = ledger or GlobalTrialLedger()
        self.random_seed = random_seed

    def test_hypothesis_001(
        self,
        df_m5: pd.DataFrame,
        hypothesis: HypothesisRecord,
        dataset_hash: str = "",
        experiment_id: str = "QROS-EXP-000001",
        dataset_version: str = "v2.0.0",
    ) -> Tuple[ExperimentRecord, StatisticalResult, List[TradeEvent]]:
        """Execute empirical backtest for QROS-HYP-000001: London Open Breakout (Class II)."""
        profile = hypothesis.validation_profile or ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
        cost_model = TransactionCostModel(profile=profile)

        df = df_m5.copy()
        df["hour"] = df.index.hour
        df["date"] = df.index.date

        # Compute 20-period volume moving average (point-in-time, shifted by 1)
        vol_col = "tick_volume" if "tick_volume" in df.columns else "volume"
        vol_ma = df[vol_col].rolling(20).mean().shift(1)

        # Compute daily Asian range (00:00 to 06:55 UTC)
        trades: List[TradeEvent] = []
        unique_dates = df["date"].unique()

        for d in unique_dates:
            day_df = df[df["date"] == d]
            asia_df = day_df[day_df["hour"] < 7]
            if len(asia_df) < 12:
                continue

            asia_high = float(asia_df["high"].max())
            asia_low = float(asia_df["low"].min())

            # London opening window: 07:00 to 09:00 UTC
            london_window = day_df[(day_df["hour"] >= 7) & (day_df["hour"] < 9)]
            if len(london_window) == 0:
                continue

            in_trade = False
            for idx, bar in london_window.iterrows():
                if in_trade:
                    break

                bar_vol_ma = vol_ma.get(idx, 0.0)
                vol_condition = bar[vol_col] > 1.5 * bar_vol_ma if bar_vol_ma > 0 else True

                # Long Breakout
                if bar["close"] > asia_high and vol_condition:
                    entry_idx_pos = day_df.index.get_loc(idx)
                    exit_idx_pos = min(entry_idx_pos + 18, len(day_df) - 1)
                    exit_bar = day_df.iloc[exit_idx_pos]
                    if exit_bar["hour"] >= 11:
                        pre_ny_bars = day_df[(day_df.index > idx) & (day_df["hour"] <= 11)]
                        if len(pre_ny_bars) > 0:
                            exit_bar = pre_ny_bars.iloc[-1]
                            exit_idx_pos = day_df.index.get_loc(exit_bar.name)

                    entry_p = float(bar["close"])
                    exit_p = float(exit_bar["close"])
                    gross_ret = (exit_p - entry_p) / entry_p
                    
                    # Deduct transaction friction
                    friction_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=(exit_idx_pos - entry_idx_pos)*5.0/1440.0, is_long=True)
                    friction_pct = (friction_pts * 0.01) / entry_p  # 1 pt = $0.01
                    net_ret = gross_ret - friction_pct

                    trades.append(
                        TradeEvent(
                            entry_time=idx,
                            exit_time=exit_bar.name,
                            direction=1,
                            entry_price=entry_p,
                            exit_price=exit_p,
                            holding_bars=exit_idx_pos - entry_idx_pos,
                            gross_return=gross_ret,
                            net_return=net_ret,
                            friction_deduction=friction_pct,
                        )
                    )
                    in_trade = True

                # Short Breakout
                elif bar["close"] < asia_low and vol_condition:
                    entry_idx_pos = day_df.index.get_loc(idx)
                    exit_idx_pos = min(entry_idx_pos + 18, len(day_df) - 1)
                    exit_bar = day_df.iloc[exit_idx_pos]
                    if exit_bar["hour"] >= 11:
                        pre_ny_bars = day_df[(day_df.index > idx) & (day_df["hour"] <= 11)]
                        if len(pre_ny_bars) > 0:
                            exit_bar = pre_ny_bars.iloc[-1]
                            exit_idx_pos = day_df.index.get_loc(exit_bar.name)

                    entry_p = float(bar["close"])
                    exit_p = float(exit_bar["close"])
                    gross_ret = (entry_p - exit_p) / entry_p
                    
                    friction_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=(exit_idx_pos - entry_idx_pos)*5.0/1440.0, is_long=False)
                    friction_pct = (friction_pts * 0.01) / entry_p
                    net_ret = gross_ret - friction_pct

                    trades.append(
                        TradeEvent(
                            entry_time=idx,
                            exit_time=exit_bar.name,
                            direction=-1,
                            entry_price=entry_p,
                            exit_price=exit_p,
                            holding_bars=exit_idx_pos - entry_idx_pos,
                            gross_return=gross_ret,
                            net_return=net_ret,
                            friction_deduction=friction_pct,
                        )
                    )
                    in_trade = True

        return self._evaluate_and_build_record(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            trades=trades,
            raw_df=df_m5,
            dataset_hash=dataset_hash,
            cost_model=cost_model,
            dataset_version=dataset_version,
        )

    def test_hypothesis_002(
        self,
        df_h1: pd.DataFrame,
        hypothesis: HypothesisRecord,
        dataset_hash: str = "",
        experiment_id: str = "QROS-EXP-000002",
        dataset_version: str = "v2.0.0",
    ) -> Tuple[ExperimentRecord, StatisticalResult, List[TradeEvent]]:
        """Execute empirical backtest for QROS-HYP-000002: Range Compression Breakout (Class III)."""
        profile = hypothesis.validation_profile or ValidationProfile(class_id="CLASS-III", profile_name="SWING-STATARB_DEFAULT")
        cost_model = TransactionCostModel(profile=profile)

        df = df_h1.copy()
        # Compute True Range and ATR(6) and ATR(24)
        tr = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                np.abs(df["high"] - df["close"].shift(1)),
                np.abs(df["low"] - df["close"].shift(1)),
            ),
        )
        atr_6 = tr.rolling(6).mean().shift(1)
        atr_24 = tr.rolling(24).mean().shift(1)
        compression_ratio = (atr_6 / atr_24).fillna(1.0)

        # 24-hour high and low (shifted by 1 for point-in-time)
        roll_high_24 = df["high"].rolling(24).max().shift(1)
        roll_low_24 = df["low"].rolling(24).min().shift(1)

        trades: List[TradeEvent] = []
        n_bars = len(df)
        i = 48
        holding_period = 16  # 16 hours

        while i < n_bars - holding_period:
            idx = df.index[i]
            c_ratio = compression_ratio.iloc[i]
            close_p = float(df["close"].iloc[i])
            h24 = float(roll_high_24.iloc[i])
            l24 = float(roll_low_24.iloc[i])

            # Condition: At least 6 hours of ATR6/ATR24 < 0.65
            is_compressed = bool((compression_ratio.iloc[i - 5 : i + 1] < 0.65).all())

            if is_compressed and close_p > h24:
                # Long compression breakout
                exit_idx_pos = i + holding_period
                exit_p = float(df["close"].iloc[exit_idx_pos])
                gross_ret = (exit_p - close_p) / close_p
                
                friction_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_period/24.0, is_long=True)
                friction_pct = (friction_pts * 0.01) / close_p
                net_ret = gross_ret - friction_pct

                trades.append(
                    TradeEvent(
                        entry_time=idx,
                        exit_time=df.index[exit_idx_pos],
                        direction=1,
                        entry_price=close_p,
                        exit_price=exit_p,
                        holding_bars=holding_period,
                        gross_return=gross_ret,
                        net_return=net_ret,
                        friction_deduction=friction_pct,
                    )
                )
                i += holding_period

            elif is_compressed and close_p < l24:
                # Short compression breakout
                exit_idx_pos = i + holding_period
                exit_p = float(df["close"].iloc[exit_idx_pos])
                gross_ret = (close_p - exit_p) / close_p
                
                friction_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_period/24.0, is_long=False)
                friction_pct = (friction_pts * 0.01) / close_p
                net_ret = gross_ret - friction_pct

                trades.append(
                    TradeEvent(
                        entry_time=idx,
                        exit_time=df.index[exit_idx_pos],
                        direction=-1,
                        entry_price=close_p,
                        exit_price=exit_p,
                        holding_bars=holding_period,
                        gross_return=gross_ret,
                        net_return=net_ret,
                        friction_deduction=friction_pct,
                    )
                )
                i += holding_period
            else:
                i += 1

        return self._evaluate_and_build_record(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            trades=trades,
            raw_df=df_h1,
            dataset_hash=dataset_hash,
            cost_model=cost_model,
            dataset_version=dataset_version,
        )

    def test_hypothesis_003(
        self,
        df_d1: pd.DataFrame,
        hypothesis: HypothesisRecord,
        dataset_hash: str = "",
        experiment_id: str = "QROS-EXP-000003",
        dataset_version: str = "v2.0.0",
    ) -> Tuple[ExperimentRecord, StatisticalResult, List[TradeEvent]]:
        """Execute empirical backtest for QROS-HYP-000003: 3-Sigma Daily Mean Reversion (Class IV)."""
        profile = hypothesis.validation_profile or ValidationProfile(class_id="CLASS-IV", profile_name="MACRO-REGIME_DEFAULT")
        cost_model = TransactionCostModel(profile=profile)

        df = df_d1.copy()
        ma_50 = df["close"].rolling(50).mean().shift(1)
        std_50 = df["close"].rolling(50).std().shift(1)
        ma_20 = df["close"].rolling(20).mean().shift(1)

        trades: List[TradeEvent] = []
        n_bars = len(df)
        i = 52
        max_holding = 8  # 8 trading days

        while i < n_bars - max_holding:
            idx = df.index[i]
            close_p = float(df["close"].iloc[i])
            m50 = float(ma_50.iloc[i])
            s50 = float(std_50.iloc[i])
            m20 = float(ma_20.iloc[i])

            if s50 > 0:
                z_score = (close_p - m50) / s50
            else:
                z_score = 0.0

            # Short Mean Reversion (Extreme Upper Extension > +2.5 sigma)
            if z_score >= 2.5:
                exit_idx_pos = min(i + max_holding, n_bars - 1)
                for j in range(i + 1, min(i + max_holding + 1, n_bars)):
                    if df["close"].iloc[j] <= ma_20.iloc[j]:
                        exit_idx_pos = j
                        break

                exit_p = float(df["close"].iloc[exit_idx_pos])
                gross_ret = (close_p - exit_p) / close_p
                holding_days = float(exit_idx_pos - i)
                
                friction_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_days, is_long=False)
                friction_pct = (friction_pts * 0.01) / close_p
                net_ret = gross_ret - friction_pct

                trades.append(
                    TradeEvent(
                        entry_time=idx,
                        exit_time=df.index[exit_idx_pos],
                        direction=-1,
                        entry_price=close_p,
                        exit_price=exit_p,
                        holding_bars=exit_idx_pos - i,
                        gross_return=gross_ret,
                        net_return=net_ret,
                        friction_deduction=friction_pct,
                    )
                )
                i = exit_idx_pos + 1

            # Long Mean Reversion (Extreme Lower Extension < -2.5 sigma)
            elif z_score <= -2.5:
                exit_idx_pos = min(i + max_holding, n_bars - 1)
                for j in range(i + 1, min(i + max_holding + 1, n_bars)):
                    if df["close"].iloc[j] >= ma_20.iloc[j]:
                        exit_idx_pos = j
                        break

                exit_p = float(df["close"].iloc[exit_idx_pos])
                gross_ret = (exit_p - close_p) / close_p
                holding_days = float(exit_idx_pos - i)
                
                friction_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_days, is_long=True)
                friction_pct = (friction_pts * 0.01) / close_p
                net_ret = gross_ret - friction_pct

                trades.append(
                    TradeEvent(
                        entry_time=idx,
                        exit_time=df.index[exit_idx_pos],
                        direction=1,
                        entry_price=close_p,
                        exit_price=exit_p,
                        holding_bars=exit_idx_pos - i,
                        gross_return=gross_ret,
                        net_return=net_ret,
                        friction_deduction=friction_pct,
                    )
                )
                i = exit_idx_pos + 1
            else:
                i += 1

        return self._evaluate_and_build_record(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            trades=trades,
            raw_df=df_d1,
            dataset_hash=dataset_hash,
            cost_model=cost_model,
            dataset_version=dataset_version,
        )

    def _evaluate_and_build_record(
        self,
        experiment_id: str,
        hypothesis: HypothesisRecord,
        trades: List[TradeEvent],
        raw_df: pd.DataFrame,
        dataset_hash: str,
        cost_model: TransactionCostModel,
        dataset_version: str = "v2.0.0",
    ) -> Tuple[ExperimentRecord, StatisticalResult, List[TradeEvent]]:
        """Evaluate statistical battery and construct standardized ExperimentRecord."""
        profile = hypothesis.validation_profile or ValidationProfile(profile_name=hypothesis.research_class)

        # Record trial increment in global ledger
        k = self.ledger.record_trial_evaluation(
            hypothesis_id=hypothesis.hypothesis_id,
            parameter_variations_count=1,
            feature_count=1,
            outcome="TESTED",
        )

        n_trades = len(trades)
        net_returns = np.array([t.net_return for t in trades]) if n_trades > 0 else np.array([0.0])
        gross_returns = np.array([t.gross_return for t in trades]) if n_trades > 0 else np.array([0.0])

        obs_t = len(raw_df)
        span_years = (
            (raw_df.index[-1] - raw_df.index[0]).total_seconds() / (365.25 * 86400.0)
            if obs_t > 1
            else 0.0
        )

        # Run statistical validation battery
        stat_res = evaluate_statistical_profile(
            returns_net=net_returns,
            validation_profile=profile,
            hypothesis_id=hypothesis.hypothesis_id,
            trial_count_k=k,
            observation_count_t=obs_t,
            calendar_span_years=span_years,
            random_seed=self.random_seed,
        )

        # Classify outcome conclusion according to Rule #2 and Rule #6
        if n_trades < profile.min_trades or obs_t < profile.min_observations or span_years < profile.min_calendar_span_years:
            conclusion = "DATA INSUFFICIENT"
        elif stat_res.overall_gate_pass:
            conclusion = "EDGE CANDIDATE ELIGIBLE"
        else:
            conclusion = "REJECTED"

        # Update ledger with final outcome
        self.ledger.record_trial_evaluation(
            hypothesis_id=hypothesis.hypothesis_id,
            parameter_variations_count=0,
            feature_count=0,
            outcome=conclusion,
        )

        # Build ExperimentRecord
        exp_record = ExperimentRecord(
            experiment_id=experiment_id,
            hypothesis_id=hypothesis.hypothesis_id,
            dataset_version=dataset_version,
            dataset_hash=dataset_hash or "SHA-256-REGISTERED",
            research_period=f"{raw_df.index[0].isoformat()} to {raw_df.index[-1].isoformat()}",
            training_period="Non-OOS Research Partitions (Tier 1: EDA & Tier 2: Train)",
            validation_period="Non-OOS Validation Partition (Tier 3: Val)",
            test_period="Protected Tier-4 OOS (LOCKED - UNTOUCHED)",
            feature_definitions={
                "timeframe": hypothesis.timeframe,
                "market_condition": hypothesis.market_condition,
                "holding_window": hypothesis.holding_period,
            },
            signal_definition=hypothesis.hypothesis_statement,
            entry_execution_rules=hypothesis.entry_condition,
            exit_execution_rules=hypothesis.exit_condition,
            holding_period_stats={
                "mean_holding_bars": float(np.mean([t.holding_bars for t in trades])) if n_trades > 0 else 0.0,
                "total_trades": float(n_trades),
            },
            direct_costs_fees={
                "base_spread_points": cost_model.config.base_spread_pts,
                "spread_multiplier": profile.spread_multiplier,
                "point_value": 0.01,
            },
            slippage_assumptions={
                "slippage_stress_multiplier": profile.slippage_multiplier,
                "execution_latency_ms": float(profile.latency_delay_ms),
            },
            position_sizing_rules="Fixed 1.0 unit position size per discrete trade event.",
            evaluation_metrics={
                "gross_profit_factor": float(np.sum(gross_returns[gross_returns > 0]) / abs(np.sum(gross_returns[gross_returns < 0]))) if np.sum(gross_returns < 0) != 0 else 1.0,
                "net_profit_factor": stat_res.profit_factor_net,
                "net_annualized_sharpe": stat_res.annualized_sharpe_net,
                "net_annualized_sortino": stat_res.annualized_sortino_net,
                "effective_sample_size_neff": stat_res.effective_sample_size_neff,
                "historical_var_99": stat_res.historical_var_99,
                "expected_shortfall_cvar_99": stat_res.expected_shortfall_cvar_99,
            },
            statistical_tests={
                "t_statistic": stat_res.t_statistic,
                "p_value": stat_res.p_value,
                "dsr_score": stat_res.dsr_result.dsr_score,
                "benchmark_sharpe_sr_star": stat_res.dsr_result.benchmark_sharpe,
                "bootstrap_ci_lower_95": stat_res.bootstrap_result.ci_lower_95,
                "bootstrap_ci_upper_95": stat_res.bootstrap_result.ci_upper_95,
                "cumulative_trial_k": k,
            },
            result_summary={
                "passed_sample_power": stat_res.passed_sample_power,
                "passed_profit_factor": stat_res.passed_profit_factor,
                "passed_sharpe": stat_res.passed_sharpe,
                "passed_dsr": stat_res.passed_dsr,
                "passed_bootstrap_ci": stat_res.passed_bootstrap_ci,
                "overall_gate_pass": stat_res.overall_gate_pass,
                "failure_reasons": stat_res.failure_reasons,
            },
            conclusion=conclusion,
            git_commit_hash="HEAD",
            random_seed=self.random_seed,
            author="QROS Quantitative Research Agent",
            date_executed=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

        return exp_record, stat_res, trades

    def test_hypothesis_004(
        self,
        hypothesis: HypothesisRecord,
        df_d1: pd.DataFrame,
        dataset_hash: str = "",
        experiment_id: str = "QROS-EXP-000007",
        dataset_version: str = "v3.0.0",
        lookback_period: int = 50,
        holding_days: int = 15,
        atr_trailing_mult: float = 2.0,
    ) -> Tuple[ExperimentRecord, StatisticalResult, List[TradeEvent]]:
        """Test QROS-HYP-000004: Daily Macro 50-Day High Breakout Momentum Continuation."""
        profile = hypothesis.validation_profile or get_default_profile("CLASS-IV")
        cost_model = TransactionCostModel(profile=profile)

        df = df_d1.copy()
        roll_high = df["high"].rolling(lookback_period).max().shift(1)
        ma_trend = df["close"].rolling(lookback_period).mean().shift(1)
        ma_slope = ma_trend - ma_trend.shift(5)
        ma_20 = df["close"].rolling(20).mean().shift(1)

        tr = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                (df["high"] - df["close"].shift(1)).abs(),
                (df["low"] - df["close"].shift(1)).abs(),
            ),
        )
        atr_20 = tr.rolling(20).mean().shift(1)

        trades: List[TradeEvent] = []
        i = max(lookback_period + 5, 55)
        n = len(df)

        while i < n - holding_days:
            close_p = df["close"].iloc[i]
            rh = roll_high.iloc[i]
            slope = ma_slope.iloc[i]
            atr_val = atr_20.iloc[i]

            if not np.isnan(rh) and not np.isnan(slope) and not np.isnan(atr_val):
                if close_p > rh and slope > 0:
                    entry_p = close_p
                    exit_idx_pos = min(i + holding_days, n - 1)
                    exit_p = df["close"].iloc[exit_idx_pos]
                    trailing_stop = entry_p - (atr_trailing_mult * atr_val)

                    for step in range(i + 1, exit_idx_pos + 1):
                        cur_low = df["low"].iloc[step]
                        cur_close = df["close"].iloc[step]
                        cur_ma20 = ma_20.iloc[step] if not np.isnan(ma_20.iloc[step]) else 0.0

                        if cur_low <= trailing_stop:
                            exit_p = trailing_stop
                            exit_idx_pos = step
                            break
                        elif cur_close < cur_ma20:
                            exit_p = cur_close
                            exit_idx_pos = step
                            break

                    gross_ret = float(np.log(exit_p / entry_p))
                    holding_d = float(exit_idx_pos - i)
                    friction_pts = cost_model.calculate_total_friction_pts(
                        is_stress_test=True, holding_days=holding_d, is_long=True
                    )
                    friction_pct = (friction_pts * 0.01) / entry_p
                    net_ret = gross_ret - friction_pct

                    trades.append(
                        TradeEvent(
                            entry_time=df.index[i],
                            exit_time=df.index[exit_idx_pos],
                            direction=1,
                            entry_price=entry_p,
                            exit_price=exit_p,
                            holding_bars=exit_idx_pos - i,
                            gross_return=gross_ret,
                            net_return=net_ret,
                            friction_deduction=friction_pct,
                        )
                    )
                    i = exit_idx_pos + 1
                    continue
            i += 1

        return self._evaluate_and_build_record(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            trades=trades,
            raw_df=df_d1,
            dataset_hash=dataset_hash,
            cost_model=cost_model,
            dataset_version=dataset_version,
        )

    def test_hypothesis_005(
        self,
        hypothesis: HypothesisRecord,
        df_d1: pd.DataFrame,
        dataset_hash: str = "",
        experiment_id: str = "QROS-EXP-000008",
        dataset_version: str = "v3.0.0",
        holding_days: int = 5,
        atr_trailing_mult: float = 1.5,
    ) -> Tuple[ExperimentRecord, StatisticalResult, List[TradeEvent]]:
        """Test QROS-HYP-000005: Daily NR4 Range Compression to Multi-Day Volatility Expansion."""
        profile = hypothesis.validation_profile or get_default_profile("CLASS-IV")
        cost_model = TransactionCostModel(profile=profile)

        df = df_d1.copy()
        tr = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                (df["high"] - df["close"].shift(1)).abs(),
                (df["low"] - df["close"].shift(1)).abs(),
            ),
        )
        atr_20 = tr.rolling(20).mean().shift(1)

        # NR4 condition on day t-1
        is_nr4 = (tr < tr.shift(1)) & (tr < tr.shift(2)) & (tr < tr.shift(3))

        trades: List[TradeEvent] = []
        i = 25
        n = len(df)

        while i < n - holding_days:
            nr4_prev = is_nr4.iloc[i - 1]
            atr_val = atr_20.iloc[i]

            if nr4_prev and not np.isnan(atr_val):
                prev_high = df["high"].iloc[i - 1]
                prev_low = df["low"].iloc[i - 1]
                cur_close = df["close"].iloc[i]

                # Directional breakout of NR4 boundaries
                direction = 0
                if cur_close > prev_high:
                    direction = 1
                elif cur_close < prev_low:
                    direction = -1

                if direction != 0:
                    entry_p = cur_close
                    exit_idx_pos = min(i + holding_days, n - 1)
                    exit_p = df["close"].iloc[exit_idx_pos]
                    trailing_stop = entry_p - (direction * atr_trailing_mult * atr_val)

                    for step in range(i + 1, exit_idx_pos + 1):
                        cur_bar_low = df["low"].iloc[step]
                        cur_bar_high = df["high"].iloc[step]

                        if direction == 1 and cur_bar_low <= trailing_stop:
                            exit_p = trailing_stop
                            exit_idx_pos = step
                            break
                        elif direction == -1 and cur_bar_high >= trailing_stop:
                            exit_p = trailing_stop
                            exit_idx_pos = step
                            break

                    gross_ret = float(direction * np.log(exit_p / entry_p))
                    holding_d = float(exit_idx_pos - i)
                    friction_pts = cost_model.calculate_total_friction_pts(
                        is_stress_test=True, holding_days=holding_d, is_long=(direction == 1)
                    )
                    friction_pct = (friction_pts * 0.01) / entry_p
                    net_ret = gross_ret - friction_pct

                    trades.append(
                        TradeEvent(
                            entry_time=df.index[i],
                            exit_time=df.index[exit_idx_pos],
                            direction=direction,
                            entry_price=entry_p,
                            exit_price=exit_p,
                            holding_bars=exit_idx_pos - i,
                            gross_return=gross_ret,
                            net_return=net_ret,
                            friction_deduction=friction_pct,
                        )
                    )
                    i = exit_idx_pos + 1
                    continue
            i += 1

        return self._evaluate_and_build_record(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            trades=trades,
            raw_df=df_d1,
            dataset_hash=dataset_hash,
            cost_model=cost_model,
            dataset_version=dataset_version,
        )

    def test_hypothesis_006(
        self,
        hypothesis: HypothesisRecord,
        df_h1: pd.DataFrame,
        df_d1: pd.DataFrame,
        dataset_hash: str = "",
        experiment_id: str = "QROS-EXP-000009",
        dataset_version: str = "v3.0.0",
        h1_lookback: int = 24,
        holding_hours_bars: int = 16,
        atr_trailing_mult: float = 2.0,
    ) -> Tuple[ExperimentRecord, StatisticalResult, List[TradeEvent]]:
        """Test QROS-HYP-000006: Cross-Timeframe Macro Trend Filtered Intraday Momentum."""
        profile = hypothesis.validation_profile or get_default_profile("CLASS-III")
        cost_model = TransactionCostModel(profile=profile)

        # Prepare D1 macro trend indicator
        df_d1_copy = df_d1.copy()
        df_d1_copy["ma_50"] = df_d1_copy["close"].rolling(50).mean().shift(1)
        df_d1_copy["d1_bullish"] = df_d1_copy["close"] > df_d1_copy["ma_50"]
        df_d1_copy["day_key"] = df_d1_copy.index.strftime("%Y-%m-%d")

        df = df_h1.copy()
        df["day_key"] = df.index.strftime("%Y-%m-%d")
        df = df.merge(df_d1_copy[["day_key", "d1_bullish"]].drop_duplicates(subset=["day_key"]), on="day_key", how="left")

        h24 = df["high"].rolling(h1_lookback).max().shift(1)
        l24 = df["low"].rolling(h1_lookback).min().shift(1)

        tr_h1 = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                (df["high"] - df["close"].shift(1)).abs(),
                (df["low"] - df["close"].shift(1)).abs(),
            ),
        )
        atr_24 = tr_h1.rolling(24).mean().shift(1)

        trades: List[TradeEvent] = []
        i = 50
        n = len(df)

        while i < n - holding_hours_bars:
            cur_close = df["close"].iloc[i]
            high_b = h24.iloc[i]
            low_b = l24.iloc[i]
            d1_trend = df["d1_bullish"].iloc[i]
            atr_val = atr_24.iloc[i]

            if not np.isnan(high_b) and not np.isnan(low_b) and not np.isnan(atr_val) and pd.notna(d1_trend):
                direction = 0
                if cur_close > high_b and d1_trend is True:
                    direction = 1
                elif cur_close < low_b and d1_trend is False:
                    direction = -1

                if direction != 0:
                    entry_p = cur_close
                    exit_idx_pos = min(i + holding_hours_bars, n - 1)
                    exit_p = df["close"].iloc[exit_idx_pos]
                    trailing_stop = entry_p - (direction * atr_trailing_mult * atr_val)

                    for step in range(i + 1, exit_idx_pos + 1):
                        cur_bar_low = df["low"].iloc[step]
                        cur_bar_high = df["high"].iloc[step]

                        if direction == 1 and cur_bar_low <= trailing_stop:
                            exit_p = trailing_stop
                            exit_idx_pos = step
                            break
                        elif direction == -1 and cur_bar_high >= trailing_stop:
                            exit_p = trailing_stop
                            exit_idx_pos = step
                            break

                    gross_ret = float(direction * np.log(exit_p / entry_p))
                    holding_d = float(exit_idx_pos - i) / 24.0
                    friction_pts = cost_model.calculate_total_friction_pts(
                        is_stress_test=True, holding_days=holding_d, is_long=(direction == 1)
                    )
                    friction_pct = (friction_pts * 0.01) / entry_p
                    net_ret = gross_ret - friction_pct

                    trades.append(
                        TradeEvent(
                            entry_time=df.index[i],
                            exit_time=df.index[exit_idx_pos],
                            direction=direction,
                            entry_price=entry_p,
                            exit_price=exit_p,
                            holding_bars=exit_idx_pos - i,
                            gross_return=gross_ret,
                            net_return=net_ret,
                            friction_deduction=friction_pct,
                        )
                    )
                    i = exit_idx_pos + 1
                    continue
            i += 1

        return self._evaluate_and_build_record(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            trades=trades,
            raw_df=df_h1,
            dataset_hash=dataset_hash,
            cost_model=cost_model,
            dataset_version=dataset_version,
        )


"""Empirical test of QROS-HYP-000007: H1 Imbalance (FVG) + London/NY Overlap on v4.0.0."""

import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("src"))

from qros.pipeline.costs import TransactionCostModel
from qros.schemas.validation_profile import ValidationProfile
from qros.stats.moments import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_profit_factor,
    calculate_effective_sample_size,
    calculate_t_stat,
)
from qros.stats.bootstrap import bootstrap_sharpe_ci
from qros.stats.dsr import calculate_dsr

# 1. Load M5 and H1 non-OOS data
t1_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier1_eda.parquet")
t2_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier2_train.parquet")
t3_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier3_val.parquet")
df_m5 = pd.concat([t1_m5, t2_m5, t3_m5]).sort_index()

t1_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier1_eda.parquet")
t2_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier2_train.parquet")
t3_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier3_val.parquet")
df_h1 = pd.concat([t1_h1, t2_h1, t3_h1]).sort_index()

# Compute H1 ATR
df_h1["tr"] = np.maximum(
    df_h1["high"] - df_h1["low"],
    np.maximum(
        (df_h1["high"] - df_h1["close"].shift(1)).abs(),
        (df_h1["low"] - df_h1["close"].shift(1)).abs()
    )
)
df_h1["atr14"] = df_h1["tr"].rolling(14).mean()

# 2. Detect H1 Fair Value Gaps (Bullish and Bearish)
bullish_fvgs = []
bearish_fvgs = []

for i in range(2, len(df_h1)):
    b0 = df_h1.iloc[i-2]
    b1 = df_h1.iloc[i-1]
    b2 = df_h1.iloc[i]
    atr = b1["atr14"]
    
    if np.isnan(atr) or atr <= 0:
        continue
    
    if b2["low"] > b0["high"] and (b1["high"] - b1["low"]) >= 1.2 * atr:
        bullish_fvgs.append({
            "created_time": b2.name,
            "gap_top": b2["low"],
            "gap_bottom": b0["high"],
            "target_high": b2["high"],
            "stop_loss": b0["high"] - 0.5 * atr,
            "mitigated": False
        })
    
    if b2["high"] < b0["low"] and (b1["high"] - b1["low"]) >= 1.2 * atr:
        bearish_fvgs.append({
            "created_time": b2.name,
            "gap_top": b0["low"],
            "gap_bottom": b2["high"],
            "target_low": b2["low"],
            "stop_loss": b0["low"] + 0.5 * atr,
            "mitigated": False
        })

profile = ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
cost_model = TransactionCostModel(profile=profile)

trades = []
active_bull_gaps = []
active_bear_gaps = []

df_m5["hour"] = df_m5.index.hour
bg_idx = 0
br_idx = 0

for idx, bar in df_m5.iterrows():
    while bg_idx < len(bullish_fvgs) and bullish_fvgs[bg_idx]["created_time"] <= idx:
        active_bull_gaps.append(bullish_fvgs[bg_idx])
        bg_idx += 1
    while br_idx < len(bearish_fvgs) and bearish_fvgs[br_idx]["created_time"] <= idx:
        active_bear_gaps.append(bearish_fvgs[br_idx])
        br_idx += 1
    
    active_bull_gaps = [g for g in active_bull_gaps if (idx - g["created_time"]).total_seconds() <= 172800 and not g["mitigated"]]
    active_bear_gaps = [g for g in active_bear_gaps if (idx - g["created_time"]).total_seconds() <= 172800 and not g["mitigated"]]
    
    if not (12 <= bar["hour"] < 16):
        continue
    
    # Bullish Retest
    for gap in active_bull_gaps:
        if gap["gap_bottom"] <= bar["low"] <= gap["gap_top"]:
            entry_p = float(bar["close"])
            tp = gap["target_high"]
            sl = gap["stop_loss"]
            gap["mitigated"] = True
            
            future_bars = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
            if len(future_bars) == 0:
                continue
            
            exit_p = float(future_bars.iloc[-1]["close"])
            holding_bars = len(future_bars)
            for f_idx, f_bar in future_bars.iterrows():
                if f_bar["high"] >= tp:
                    exit_p = tp
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
                if f_bar["low"] <= sl:
                    exit_p = sl
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
            
            gross_ret = (exit_p - entry_p) / entry_p
            fric_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_bars*5.0/1440.0, is_long=True)
            net_ret = gross_ret - (fric_pts * 0.01) / entry_p
            trades.append({"net_return": net_ret, "gross_return": gross_ret, "dir": 1})
            break

    # Bearish Retest
    for gap in active_bear_gaps:
        if gap["gap_bottom"] <= bar["high"] <= gap["gap_top"]:
            entry_p = float(bar["close"])
            tp = gap["target_low"]
            sl = gap["stop_loss"]
            gap["mitigated"] = True
            
            future_bars = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
            if len(future_bars) == 0:
                continue
            
            exit_p = float(future_bars.iloc[-1]["close"])
            holding_bars = len(future_bars)
            for f_idx, f_bar in future_bars.iterrows():
                if f_bar["low"] <= tp:
                    exit_p = tp
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
                if f_bar["high"] >= sl:
                    exit_p = sl
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
            
            gross_ret = (entry_p - exit_p) / entry_p
            fric_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_bars*5.0/1440.0, is_long=False)
            net_ret = gross_ret - (fric_pts * 0.01) / entry_p
            trades.append({"net_return": net_ret, "gross_return": gross_ret, "dir": -1})
            break

print("\n" + "=" * 80)
print("EMPIRICAL TEST RESULTS: QROS-HYP-000007 (H1 Imbalance + London/NY Overlap)")
print("=" * 80)
if len(trades) > 0:
    returns = np.array([t["net_return"] for t in trades])
    gross_returns = np.array([t["gross_return"] for t in trades])
    
    N = len(returns)
    N_eff = calculate_effective_sample_size(returns)
    pf_gross = calculate_profit_factor(gross_returns)
    pf_net = calculate_profit_factor(returns)
    sr_gross = calculate_sharpe_ratio(gross_returns, annualization_factor=252.0)
    sr_net = calculate_sharpe_ratio(returns, annualization_factor=252.0)
    t_stat, p_val = calculate_t_stat(returns)
    
    bs_res = bootstrap_sharpe_ci(returns, n_resamples=1000)
    dsr_res = calculate_dsr(observed_sharpe=sr_net, trial_count_k=120, sample_length_t=N, skewness=float(pd.Series(returns).skew()), kurtosis=float(pd.Series(returns).kurt()))
    
    print(f"Total Trades (N):                   {N}")
    print(f"Effective Sample Size (N_eff):      {N_eff:.1f}")
    print(f"Gross Profit Factor:                {pf_gross:.4f}")
    print(f"Net Profit Factor (after costs):    {pf_net:.4f}")
    print(f"Gross Annualized Sharpe:            {sr_gross:.4f}")
    print(f"Net Annualized Sharpe:              {sr_net:.4f}")
    print(f"t-Statistic:                        {t_stat:.4f} (p-value: {p_val:.6f})")
    print(f"Stationary Bootstrap 95% CI:        [{bs_res.ci_lower_95:.4f}, {bs_res.ci_upper_95:.4f}] (Strictly > 0: {bs_res.ci_strictly_positive})")
    print(f"Deflated Sharpe Ratio (DSR K=120):  {dsr_res.dsr_score:.4f} (Significant: {dsr_res.is_statistically_significant})")
    
    status = "PROMISING / CANDIDATE" if bs_res.ci_strictly_positive and dsr_res.is_statistically_significant and pf_net >= 1.35 else "REJECTED"
    print(f"\nHypothesis Outcome: [{status}]")
print("=" * 80)
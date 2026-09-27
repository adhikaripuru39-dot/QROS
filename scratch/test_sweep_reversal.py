"""Empirical test of QROS-HYP-000009: Trend-Filtered Asian Liquidity Sweep Reversal on v4.0.0."""

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

# 1. Load M5, H1, and D1 non-OOS data
t1_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier1_eda.parquet")
t2_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier2_train.parquet")
t3_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier3_val.parquet")
df_m5 = pd.concat([t1_m5, t2_m5, t3_m5]).sort_index()

t1_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier1_eda.parquet")
t2_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier2_train.parquet")
t3_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier3_val.parquet")
df_h1 = pd.concat([t1_h1, t2_h1, t3_h1]).sort_index()

# 2. Compute H1 Trend Filter (50 EMA) & H1 ATR
df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()
df_h1["tr"] = np.maximum(
    df_h1["high"] - df_h1["low"],
    np.maximum(
        (df_h1["high"] - df_h1["close"].shift(1)).abs(),
        (df_h1["low"] - df_h1["close"].shift(1)).abs()
    )
)
df_h1["atr14"] = df_h1["tr"].rolling(14).mean()

# Merge H1 trend & ATR to M5 point-in-time (as-of prior completed H1 bar)
df_h1_shifted = df_h1[["ema50", "atr14", "close"]].shift(1)
df_m5 = pd.merge_asof(df_m5, df_h1_shifted, left_index=True, right_index=True, direction="backward", suffixes=("", "_h1"))

# 3. Simulate Asian Sweep Reversal Strategy
profile = ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
cost_model = TransactionCostModel(profile=profile)

df_m5["hour"] = df_m5.index.hour
df_m5["date"] = df_m5.index.date
unique_dates = df_m5["date"].unique()

trades = []

for d in unique_dates:
    day_df = df_m5[df_m5["date"] == d]
    asia = day_df[day_df["hour"] < 7]
    if len(asia) < 12:
        continue
    
    asia_high = float(asia["high"].max())
    asia_low = float(asia["low"].min())
    asia_mid = (asia_high + asia_low) / 2.0
    
    # London session window: 07:00 to 11:00 UTC
    london = day_df[(day_df["hour"] >= 7) & (day_df["hour"] < 11)]
    if len(london) == 0:
        continue
    
    in_trade = False
    for idx, bar in london.iterrows():
        if in_trade:
            break
        
        h1_ema = bar.get("ema50", np.nan)
        h1_close = bar.get("close_h1", np.nan)
        h1_atr = bar.get("atr14", 3.0)
        
        if np.isnan(h1_ema) or np.isnan(h1_atr) or h1_atr <= 0:
            continue
        
        is_bullish_trend = h1_close > h1_ema
        is_bearish_trend = h1_close < h1_ema
        
        # Setup A: Bearish Trend + High Sweep Reversal (Short Setup)
        # Price swept above Asia High, but current bar closed back below Asia High
        if is_bearish_trend and bar["high"] > asia_high and bar["close"] < asia_high:
            entry_p = float(bar["close"])
            sweep_high = float(bar["high"])
            sl = sweep_high + 0.3 * h1_atr
            tp = asia_mid
            
            # Simulate forward trajectory
            future_bars = day_df[day_df.index > idx]
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
            in_trade = True
            break
        
        # Setup B: Bullish Trend + Low Sweep Reversal (Long Setup)
        # Price swept below Asia Low, but current bar closed back above Asia Low
        if is_bullish_trend and bar["low"] < asia_low and bar["close"] > asia_low:
            entry_p = float(bar["close"])
            sweep_low = float(bar["low"])
            sl = sweep_low - 0.3 * h1_atr
            tp = asia_mid
            
            future_bars = day_df[day_df.index > idx]
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
            in_trade = True
            break

print("=" * 80)
print("EMPIRICAL TEST RESULTS: QROS-HYP-000009 (Trend-Filtered Asian Sweep Reversal)")
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
    dsr_res = calculate_dsr(observed_sharpe=sr_net, trial_count_k=121, sample_length_t=N, skewness=float(pd.Series(returns).skew()), kurtosis=float(pd.Series(returns).kurt()))
    
    print(f"Total Trades (N):                   {N}")
    print(f"Effective Sample Size (N_eff):      {N_eff:.1f}")
    print(f"Gross Profit Factor:                {pf_gross:.4f}")
    print(f"Net Profit Factor (after costs):    {pf_net:.4f}")
    print(f"Gross Annualized Sharpe:            {sr_gross:.4f}")
    print(f"Net Annualized Sharpe:              {sr_net:.4f}")
    print(f"t-Statistic:                        {t_stat:.4f} (p-value: {p_val:.6f})")
    print(f"Stationary Bootstrap 95% CI:        [{bs_res.ci_lower_95:.4f}, {bs_res.ci_upper_95:.4f}] (Strictly > 0: {bs_res.ci_strictly_positive})")
    print(f"Deflated Sharpe Ratio (DSR K=121):  {dsr_res.dsr_score:.4f} (Significant: {dsr_res.is_statistically_significant})")
    
    status = "PROMISING / CANDIDATE" if bs_res.ci_strictly_positive and dsr_res.is_statistically_significant and pf_net >= 1.35 else "REJECTED"
    print(f"\nHypothesis Outcome: [{status}]")
else:
    print("Zero trades executed.")
print("=" * 80)
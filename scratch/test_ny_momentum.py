"""Empirical test of QROS-HYP-000008: New York Volatility Expansion & Momentum on v4.0.0."""

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

df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()
df_h1_shifted = df_h1[["ema50", "close"]].shift(1)
df_m5 = pd.merge_asof(df_m5, df_h1_shifted, left_index=True, right_index=True, direction="backward", suffixes=("", "_h1"))

profile = ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
cost_model = TransactionCostModel(profile=profile)

df_m5["hour"] = df_m5.index.hour
df_m5["minute"] = df_m5.index.minute
df_m5["date"] = df_m5.index.date
df_m5["vol_ma20"] = df_m5["tick_volume"].rolling(20).mean().shift(1)

unique_dates = df_m5["date"].unique()
trades = []

for d in unique_dates:
    day_df = df_m5[df_m5["date"] == d]
    
    # Define NY Opening Range (13:30 to 14:00 UTC)
    ny_open_bars = day_df[(day_df["hour"] == 13) & (day_df["minute"] >= 30)]
    if len(ny_open_bars) < 5:
        continue
    
    ny_high = float(ny_open_bars["high"].max())
    ny_low = float(ny_open_bars["low"].min())
    ny_range = ny_high - ny_low
    
    # Look for breakout between 14:00 and 15:30 UTC
    breakout_window = day_df[((day_df["hour"] == 14) | ((day_df["hour"] == 15) & (day_df["minute"] <= 30)))]
    if len(breakout_window) == 0:
        continue
    
    in_trade = False
    for idx, bar in breakout_window.iterrows():
        if in_trade:
            break
        
        h1_ema = bar.get("ema50", np.nan)
        h1_close = bar.get("close_h1", np.nan)
        vol_ma = bar.get("vol_ma20", 0)
        
        if np.isnan(h1_ema) or bar["tick_volume"] < 1.3 * vol_ma:
            continue
        
        # Bullish Breakout
        if bar["close"] > ny_high and h1_close > h1_ema:
            entry_p = float(bar["close"])
            sl = ny_low
            tp = entry_p + 1.5 * ny_range
            
            future = day_df[day_df.index > idx]
            if len(future) == 0:
                continue
            
            exit_p = float(future.iloc[-1]["close"])
            holding_bars = len(future)
            for f_idx, f_bar in future.iterrows():
                if f_bar["high"] >= tp:
                    exit_p = tp
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
                if f_bar["low"] <= sl:
                    exit_p = sl
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
                if f_bar["hour"] >= 18:
                    exit_p = float(f_bar["close"])
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
            
            gross_ret = (exit_p - entry_p) / entry_p
            fric_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_bars*5.0/1440.0, is_long=True)
            net_ret = gross_ret - (fric_pts * 0.01) / entry_p
            trades.append({"net_return": net_ret, "gross_return": gross_ret, "dir": 1})
            in_trade = True
            break
        
        # Bearish Breakout
        if bar["close"] < ny_low and h1_close < h1_ema:
            entry_p = float(bar["close"])
            sl = ny_high
            tp = entry_p - 1.5 * ny_range
            
            future = day_df[day_df.index > idx]
            if len(future) == 0:
                continue
            
            exit_p = float(future.iloc[-1]["close"])
            holding_bars = len(future)
            for f_idx, f_bar in future.iterrows():
                if f_bar["low"] <= tp:
                    exit_p = tp
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
                if f_bar["high"] >= sl:
                    exit_p = sl
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
                if f_bar["hour"] >= 18:
                    exit_p = float(f_bar["close"])
                    holding_bars = int((f_idx - idx).total_seconds() // 300)
                    break
            
            gross_ret = (entry_p - exit_p) / entry_p
            fric_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_bars*5.0/1440.0, is_long=False)
            net_ret = gross_ret - (fric_pts * 0.01) / entry_p
            trades.append({"net_return": net_ret, "gross_return": gross_ret, "dir": -1})
            in_trade = True
            break

print("\n" + "=" * 80)
print("EMPIRICAL TEST RESULTS: QROS-HYP-000008 (New York Volatility Expansion & Momentum)")
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
    dsr_res = calculate_dsr(observed_sharpe=sr_net, trial_count_k=122, sample_length_t=N, skewness=float(pd.Series(returns).skew()), kurtosis=float(pd.Series(returns).kurt()))
    
    print(f"Total Trades (N):                   {N}")
    print(f"Effective Sample Size (N_eff):      {N_eff:.1f}")
    print(f"Gross Profit Factor:                {pf_gross:.4f}")
    print(f"Net Profit Factor (after costs):    {pf_net:.4f}")
    print(f"Gross Annualized Sharpe:            {sr_gross:.4f}")
    print(f"Net Annualized Sharpe:              {sr_net:.4f}")
    print(f"t-Statistic:                        {t_stat:.4f} (p-value: {p_val:.6f})")
    print(f"Stationary Bootstrap 95% CI:        [{bs_res.ci_lower_95:.4f}, {bs_res.ci_upper_95:.4f}] (Strictly > 0: {bs_res.ci_strictly_positive})")
    print(f"Deflated Sharpe Ratio (DSR K=122):  {dsr_res.dsr_score:.4f} (Significant: {dsr_res.is_statistically_significant})")
    
    status = "PROMISING / CANDIDATE" if bs_res.ci_strictly_positive and dsr_res.is_statistically_significant and pf_net >= 1.35 else "REJECTED"
    print(f"\nHypothesis Outcome: [{status}]")
else:
    print("Zero trades executed.")
print("=" * 80)
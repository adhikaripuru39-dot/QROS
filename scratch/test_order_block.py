"""Empirical test of H1 Institutional Order Block Mitigation on v4.0.0."""

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

# 1. Load M5, H1 non-OOS data
t1_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier1_eda.parquet")
t2_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier2_train.parquet")
t3_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier3_val.parquet")
df_m5 = pd.concat([t1_m5, t2_m5, t3_m5]).sort_index()

t1_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier1_eda.parquet")
t2_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier2_train.parquet")
t3_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier3_val.parquet")
df_h1 = pd.concat([t1_h1, t2_h1, t3_h1]).sort_index()

df_h1["tr"] = np.maximum(
    df_h1["high"] - df_h1["low"],
    np.maximum((df_h1["high"] - df_h1["close"].shift(1)).abs(), (df_h1["low"] - df_h1["close"].shift(1)).abs())
)
df_h1["atr14"] = df_h1["tr"].rolling(14).mean()
df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()

# 2. Detect H1 Order Blocks
bullish_obs = []
bearish_obs = []

for i in range(2, len(df_h1)):
    b_prev = df_h1.iloc[i-1]
    b_curr = df_h1.iloc[i]
    atr = b_curr["atr14"]
    if np.isnan(atr) or atr <= 0:
        continue
    
    # Bullish OB: Bearish candle followed by strong bullish impulse
    if b_prev["close"] < b_prev["open"] and (b_curr["close"] - b_curr["open"]) >= 1.0 * atr and b_curr["close"] > b_curr["ema50"]:
        bullish_obs.append({
            "created_time": b_curr.name,
            "ob_top": b_prev["high"],
            "ob_bottom": b_prev["low"],
            "target": b_curr["high"],
            "sl": b_prev["low"] - 0.3 * atr,
            "mitigated": False
        })
    
    # Bearish OB: Bullish candle followed by strong bearish impulse
    if b_prev["close"] > b_prev["open"] and (b_prev["open"] - b_curr["close"]) >= 1.0 * atr and b_curr["close"] < b_curr["ema50"]:
        bearish_obs.append({
            "created_time": b_curr.name,
            "ob_top": b_prev["high"],
            "ob_bottom": b_prev["low"],
            "target": b_curr["low"],
            "sl": b_prev["high"] + 0.3 * atr,
            "mitigated": False
        })

print(f"Detected {len(bullish_obs)} Bullish H1 Order Blocks and {len(bearish_obs)} Bearish H1 Order Blocks.")

profile = ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
cost_model = TransactionCostModel(profile=profile)

df_m5["hour"] = df_m5.index.hour
trades = []
active_bull_obs = []
active_bear_obs = []

b_idx = 0
r_idx = 0

for idx, bar in df_m5.iterrows():
    while b_idx < len(bullish_obs) and bullish_obs[b_idx]["created_time"] <= idx:
        active_bull_obs.append(bullish_obs[b_idx])
        b_idx += 1
    while r_idx < len(bearish_obs) and bearish_obs[r_idx]["created_time"] <= idx:
        active_bear_obs.append(bearish_obs[r_idx])
        r_idx += 1
    
    active_bull_obs = [ob for ob in active_bull_obs if (idx - ob["created_time"]).total_seconds() <= 172800 and not ob["mitigated"]]
    active_bear_obs = [ob for ob in active_bear_obs if (idx - ob["created_time"]).total_seconds() <= 172800 and not ob["mitigated"]]
    
    # Restrict to liquid hours: 12:00 to 18:00 UTC
    if not (12 <= bar["hour"] < 18):
        continue
    
    # Bullish OB Retest
    for ob in active_bull_obs:
        if ob["ob_bottom"] <= bar["low"] <= ob["ob_top"]:
            entry_p = float(bar["close"])
            tp = ob["target"]
            sl = ob["sl"]
            ob["mitigated"] = True
            
            future = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
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
            
            gross_ret = (exit_p - entry_p) / entry_p
            fric_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_bars*5.0/1440.0, is_long=True)
            net_ret = gross_ret - (fric_pts * 0.01) / entry_p
            trades.append({"net_return": net_ret, "gross_return": gross_ret, "dir": 1})
            break

    # Bearish OB Retest
    for ob in active_bear_obs:
        if ob["ob_bottom"] <= bar["high"] <= ob["ob_top"]:
            entry_p = float(bar["close"])
            tp = ob["target"]
            sl = ob["sl"]
            ob["mitigated"] = True
            
            future = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
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
            
            gross_ret = (entry_p - exit_p) / entry_p
            fric_pts = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=holding_bars*5.0/1440.0, is_long=False)
            net_ret = gross_ret - (fric_pts * 0.01) / entry_p
            trades.append({"net_return": net_ret, "gross_return": gross_ret, "dir": -1})
            break

print("\n" + "=" * 80)
print("EMPIRICAL TEST RESULTS: QROS-HYP-000010 (H1 Order Block Mitigation during NY Overlap)")
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
    dsr_res = calculate_dsr(observed_sharpe=sr_net, trial_count_k=124, sample_length_t=N, skewness=float(pd.Series(returns).skew()), kurtosis=float(pd.Series(returns).kurt()))
    
    print(f"Total Trades (N):                   {N}")
    print(f"Effective Sample Size (N_eff):      {N_eff:.1f}")
    print(f"Gross Profit Factor:                {pf_gross:.4f}")
    print(f"Net Profit Factor (after costs):    {pf_net:.4f}")
    print(f"Gross Annualized Sharpe:            {sr_gross:.4f}")
    print(f"Net Annualized Sharpe:              {sr_net:.4f}")
    print(f"t-Statistic:                        {t_stat:.4f} (p-value: {p_val:.6f})")
    print(f"Stationary Bootstrap 95% CI:        [{bs_res.ci_lower_95:.4f}, {bs_res.ci_upper_95:.4f}] (Strictly > 0: {bs_res.ci_strictly_positive})")
    print(f"Deflated Sharpe Ratio (DSR K=124):  {dsr_res.dsr_score:.4f} (Significant: {dsr_res.is_statistically_significant})")
    
    status = "PROMISING / CANDIDATE" if bs_res.ci_strictly_positive and dsr_res.is_statistically_significant and pf_net >= 1.35 and N >= 100 else "REJECTED"
    print(f"\nHypothesis Outcome: [{status}]")
else:
    print("Zero trades executed.")
print("=" * 80)
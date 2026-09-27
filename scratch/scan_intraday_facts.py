"""Scan empirical stylized facts and patterns on v4.0.0 M5 and H1 non-OOS data."""

import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("src"))

# Load non-OOS M5
t1 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier1_eda.parquet")
t2 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier2_train.parquet")
t3 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier3_val.parquet")
df_m5 = pd.concat([t1, t2, t3]).sort_index()

# 1. Session Volatility & Drift Analysis
df_m5["hour"] = df_m5.index.hour
df_m5["ret"] = df_m5["close"].pct_change()
df_m5["range"] = df_m5["high"] - df_m5["low"]

hourly_stats = df_m5.groupby("hour").agg(
    mean_ret=("ret", "mean"),
    volatility=("ret", "std"),
    mean_range=("range", "mean"),
    mean_ticks=("tick_volume", "mean"),
    mean_spread=("spread_pts", "mean")
)

print("=" * 80)
print("XAUUSD 6-YEAR INTRADAY SESSION CHARACTERIZATION (M5 NON-OOS DATA)")
print("=" * 80)
print(hourly_stats.to_string())

# 2. Asian Range Sweep & Mean Reversion vs Continuation
df_m5["date"] = df_m5.index.date
dates = df_m5["date"].unique()

sweep_fakeout_count = 0
sweep_continuation_count = 0
total_sweeps = 0

for d in dates:
    day_df = df_m5[df_m5["date"] == d]
    asia = day_df[day_df["hour"] < 7]
    if len(asia) < 12:
        continue
    
    asia_high = asia["high"].max()
    asia_low = asia["low"].min()
    
    # Check London session (07:00 to 12:00 UTC)
    london = day_df[(day_df["hour"] >= 7) & (day_df["hour"] < 12)]
    if len(london) == 0:
        continue
    
    # High sweep
    swept_high = (london["high"] > asia_high).any()
    swept_low = (london["low"] < asia_low).any()
    
    if swept_high and not swept_low:
        total_sweeps += 1
        # Check if London closed below Asia High (Fakeout) or above (Continuation)
        london_close = london.iloc[-1]["close"]
        if london_close < asia_high:
            sweep_fakeout_count += 1
        else:
            sweep_continuation_count += 1
    elif swept_low and not swept_high:
        total_sweeps += 1
        london_close = london.iloc[-1]["close"]
        if london_close > asia_low:
            sweep_fakeout_count += 1
        else:
            sweep_continuation_count += 1

print("\n" + "-" * 80)
print("ASIAN RANGE BREAKOUT VS LIQUIDITY SWEEP (FAKEOUT) ANALYSIS")
print("-" * 80)
print(f"Total Isolated Asian Boundary Sweeps: {total_sweeps}")
print(f"Fakeouts / Mean Reversion back inside range: {sweep_fakeout_count} ({sweep_fakeout_count/total_sweeps*100:.1f}%)")
print(f"True Directional Continuations: {sweep_continuation_count} ({sweep_continuation_count/total_sweeps*100:.1f}%)")
print("=" * 80)
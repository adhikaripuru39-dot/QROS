"""Backtest and inspect market behavior starting from 2026-08-25 15:45:00 UTC."""

import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("src"))

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

print("=" * 85)
print("  QROS FOCUSED BACKTEST: FROM 2026-08-25 15:45:00 UTC TO PRESENT  ")
print("=" * 85)

# Check if MT5 is available to pull the absolute newest bars up to this second
bars_from_mt5 = False
df_recent = None

if MT5_AVAILABLE and mt5.initialize():
    print("[OK] Connected to local MT5 terminal to pull latest live bars.")
    # Fetch last 500 M5 bars
    rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M5, 0, 500)
    if rates is not None and len(rates) > 0:
        df_recent = pd.DataFrame(rates)
        df_recent["time"] = pd.to_datetime(df_recent["time"], unit="s", utc=True)
        df_recent = df_recent.set_index("time").sort_index()
        bars_from_mt5 = True
        print(f"Pulled {len(df_recent)} M5 bars from MT5 ({df_recent.index[0]} to {df_recent.index[-1]}).")

if not bars_from_mt5:
    # Load from parquet files
    t4_m5 = pd.read_parquet("data/vault/xauusd/qros-data-xauusd-m5-v4.0.0_tier4_oos.parquet")
    df_recent = t4_m5

# Filter strictly >= 2026-08-25 15:45:00 UTC
start_ts = pd.to_datetime("2026-08-25 15:45:00+00:00")
df_target = df_recent[df_recent.index >= start_ts]

print(f"\nBars available from {start_ts}: {len(df_target)} bars.")
if len(df_target) > 0:
    print(f"Start Bar: {df_target.index[0]} | Close: {df_target.iloc[0]['close']}")
    print(f"End Bar:   {df_target.index[-1]} | Close: {df_target.iloc[-1]['close']}")
    print("\nRecent Price Action Summary:")
    print(df_target[["open", "high", "low", "close"]].tail(10))
else:
    print("No bars found in current local dataset past 2026-08-25 15:45. Let's inspect the latest parquet boundary.")
    print(f"Parquet Max Timestamp: {df_recent.index[-1]}")
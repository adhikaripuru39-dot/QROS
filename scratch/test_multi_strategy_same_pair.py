"""Empirical test of Joint Multi-Strategy Ensemble on XAUUSD (EDGE-000001 + EDGE-000002)."""

import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("src"))

from qros.pipeline.costs import TransactionCostModel
from qros.schemas.validation_profile import ValidationProfile
from qros.stats.moments import calculate_sharpe_ratio, calculate_profit_factor

# 1. Load full M5 and H1 data
t1_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier1_eda.parquet")
t2_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier2_train.parquet")
t3_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier3_val.parquet")
t4_m5 = pd.read_parquet("data/vault/xauusd/qros-data-xauusd-m5-v4.0.0_tier4_oos.parquet")
df_m5 = pd.concat([t1_m5, t2_m5, t3_m5, t4_m5]).sort_index()

t1_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier1_eda.parquet")
t2_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier2_train.parquet")
t3_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier3_val.parquet")
t4_h1 = pd.read_parquet("data/vault/xauusd/qros-data-xauusd-h1-v4.0.0_tier4_oos.parquet")
df_h1 = pd.concat([t1_h1, t2_h1, t3_h1, t4_h1]).sort_index()

df_h1["tr"] = np.maximum(
    df_h1["high"] - df_h1["low"],
    np.maximum((df_h1["high"] - df_h1["close"].shift(1)).abs(), (df_h1["low"] - df_h1["close"].shift(1)).abs())
)
df_h1["atr14"] = df_h1["tr"].rolling(14).mean()
df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()

# Detect FVGs & OBs
bull_gaps, bear_gaps = [], []
bull_obs, bear_obs = [], []

for i in range(2, len(df_h1)):
    b0, b1, b2 = df_h1.iloc[i-2], df_h1.iloc[i-1], df_h1.iloc[i]
    atr = b1["atr14"]
    if np.isnan(atr) or atr <= 0: continue
    # FVG
    if b2["low"] > b0["high"] and (b1["high"] - b1["low"]) >= 1.2 * atr:
        bull_gaps.append({"created": b2.name, "bot": b0["high"], "top": b2["low"], "tgt": b2["high"], "sl": b0["high"] - 0.5 * atr, "mit": False})
    if b2["high"] < b0["low"] and (b1["high"] - b1["low"]) >= 1.2 * atr:
        bear_gaps.append({"created": b2.name, "bot": b2["high"], "top": b0["low"], "tgt": b2["low"], "sl": b0["low"] + 0.5 * atr, "mit": False})
    # Order Block
    if b1["close"] < b1["open"] and (b2["close"] - b2["open"]) >= 1.0 * atr and b2["close"] > b2["ema50"]:
        bull_obs.append({"created": b2.name, "bot": b1["low"], "top": b1["high"], "tgt": b2["high"], "sl": b1["low"] - 0.3 * atr, "mit": False})
    if b1["close"] > b1["open"] and (b1["open"] - b2["close"]) >= 1.0 * atr and b2["close"] < b2["ema50"]:
        bear_obs.append({"created": b2.name, "bot": b1["low"], "top": b1["high"], "tgt": b2["low"], "sl": b1["high"] + 0.3 * atr, "mit": False})

profile = ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
cost_model = TransactionCostModel(profile=profile)
df_m5["hour"] = df_m5.index.hour

trades_s1 = []
trades_s2 = []

# Simulate S1 (FVG) & S2 (OB)
act_bg, act_br = [], []
act_bo, act_ro = [], []
bg_i, br_i, bo_i, ro_i = 0, 0, 0, 0

for idx, bar in df_m5.iterrows():
    while bg_i < len(bull_gaps) and bull_gaps[bg_i]["created"] <= idx: act_bg.append(bull_gaps[bg_i]); bg_i += 1
    while br_i < len(bear_gaps) and bear_gaps[br_i]["created"] <= idx: act_br.append(bear_gaps[br_i]); br_i += 1
    while bo_i < len(bull_obs) and bull_obs[bo_i]["created"] <= idx: act_bo.append(bull_obs[bo_i]); bo_i += 1
    while ro_i < len(bear_obs) and bear_obs[ro_i]["created"] <= idx: act_ro.append(bear_obs[ro_i]); ro_i += 1
    
    act_bg = [g for g in act_bg if (idx - g["created"]).total_seconds() <= 172800 and not g["mit"]]
    act_br = [g for g in act_br if (idx - g["created"]).total_seconds() <= 172800 and not g["mit"]]
    act_bo = [o for o in act_bo if (idx - o["created"]).total_seconds() <= 172800 and not o["mit"]]
    act_ro = [o for o in act_ro if (idx - o["created"]).total_seconds() <= 172800 and not o["mit"]]
    
    # S1: FVG (12:00 to 16:00 UTC)
    if 12 <= bar["hour"] < 16:
        for g in act_bg:
            if g["bot"] <= bar["low"] <= g["top"]:
                ep, tp, sl, g["mit"] = float(bar["close"]), g["tgt"], g["sl"], True
                fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
                if len(fut) == 0: continue
                xp, hb = float(fut.iloc[-1]["close"]), len(fut)
                for fi, fb in fut.iterrows():
                    if fb["high"] >= tp: xp, hb = tp, int((fi - idx).total_seconds() // 300); break
                    if fb["low"] <= sl: xp, hb = sl, int((fi - idx).total_seconds() // 300); break
                fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=hb*5.0/1440.0, is_long=True)
                trades_s1.append({"time": idx, "net_return": ((xp - ep)/ep - (fric*0.01)/ep)})
                break
    
    # S2: OB (12:00 to 18:00 UTC)
    if 12 <= bar["hour"] < 18:
        for o in act_bo:
            if o["bot"] <= bar["low"] <= o["top"]:
                ep, tp, sl, o["mit"] = float(bar["close"]), o["tgt"], o["sl"], True
                fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
                if len(fut) == 0: continue
                xp, hb = float(fut.iloc[-1]["close"]), len(fut)
                for fi, fb in fut.iterrows():
                    if fb["high"] >= tp: xp, hb = tp, int((fi - idx).total_seconds() // 300); break
                    if fb["low"] <= sl: xp, hb = sl, int((fi - idx).total_seconds() // 300); break
                fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=hb*5.0/1440.0, is_long=True)
                trades_s2.append({"time": idx, "net_return": ((xp - ep)/ep - (fric*0.01)/ep)})
                break

# Build combined timeline
df_s1 = pd.DataFrame(trades_s1).set_index("time").rename(columns={"net_return": "ret_s1"})
df_s2 = pd.DataFrame(trades_s2).set_index("time").rename(columns={"net_return": "ret_s2"})
combined = pd.merge(df_s1, df_s2, left_index=True, right_index=True, how="outer").fillna(0.0)

# 50/50 Combined Portfolio
combined["ret_portfolio"] = 0.5 * combined["ret_s1"] + 0.5 * combined["ret_s2"]

equity_s1 = np.cumprod(1.0 + combined["ret_s1"].values)
equity_s2 = np.cumprod(1.0 + combined["ret_s2"].values)
equity_port = np.cumprod(1.0 + combined["ret_portfolio"].values)

dd_port = (equity_port - np.maximum.accumulate(equity_port)) / np.maximum.accumulate(equity_port)
max_dd_port = np.min(dd_port) * 100.0

sr_s1 = calculate_sharpe_ratio(combined["ret_s1"].values, annualization_factor=252.0)
sr_s2 = calculate_sharpe_ratio(combined["ret_s2"].values, annualization_factor=252.0)
sr_port = calculate_sharpe_ratio(combined["ret_portfolio"].values, annualization_factor=252.0)

print("=" * 80)
print("MULTI-STRATEGY ENSEMBLE PERFORMANCE ON XAUUSD (6.15 YEARS)")
print("=" * 80)
print(f"Strategy 1 (FVG Imbalance):    Total Return: +{(equity_s1[-1]-1)*100:.2f}% | Net Sharpe: {sr_s1:.4f}")
print(f"Strategy 2 (Order Block):      Total Return: +{(equity_s2[-1]-1)*100:.2f}% | Net Sharpe: {sr_s2:.4f}")
print("-" * 80)
print(f"COMBINED 50/50 PORTFOLIO:      Total Return: +{(equity_port[-1]-1)*100:.2f}% | Net Sharpe: {sr_port:.4f}")
print(f"Maximum Portfolio Drawdown:    {max_dd_port:.2f}%")
print("=" * 80)
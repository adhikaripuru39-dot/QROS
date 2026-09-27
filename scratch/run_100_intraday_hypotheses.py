"""Automated 100+ Intraday Hypothesis Discovery & Validation Battery for QROS."""

import os
import sys
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath("src"))

from qros.pipeline.costs import TransactionCostModel
from qros.schemas.validation_profile import ValidationProfile
from qros.stats.moments import calculate_sharpe_ratio, calculate_profit_factor, calculate_effective_sample_size, calculate_t_stat
from qros.stats.bootstrap import bootstrap_sharpe_ci
from qros.stats.dsr import calculate_dsr
from qros.tracking.ledger import GlobalTrialLedger

print("=" * 85)
print("QROS HIGH-THROUGHPUT 100+ INTRADAY HYPOTHESIS DISCOVERY & VALIDATION BATTERY")
print("=" * 85)

# 1. Load Data
t1_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier1_eda.parquet")
t2_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier2_train.parquet")
t3_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier3_val.parquet")
df_m5 = pd.concat([t1_m5, t2_m5, t3_m5]).sort_index()

t1_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier1_eda.parquet")
t2_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier2_train.parquet")
t3_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier3_val.parquet")
df_h1 = pd.concat([t1_h1, t2_h1, t3_h1]).sort_index()

df_m5["hour"] = df_m5.index.hour
df_m5["minute"] = df_m5.index.minute
df_m5["date"] = df_m5.index.date

# Technical Indicators on H1
df_h1["tr"] = np.maximum(
    df_h1["high"] - df_h1["low"],
    np.maximum((df_h1["high"] - df_h1["close"].shift(1)).abs(), (df_h1["low"] - df_h1["close"].shift(1)).abs())
)
df_h1["atr14"] = df_h1["tr"].rolling(14).mean()
df_h1["ema20"] = df_h1["close"].ewm(span=20, adjust=False).mean()
df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()
df_h1["ema200"] = df_h1["close"].ewm(span=200, adjust=False).mean()

# Bollinger & Keltner on H1 (Squeeze detection)
df_h1["bb_mid"] = df_h1["close"].rolling(20).mean()
df_h1["bb_std"] = df_h1["close"].rolling(20).std()
df_h1["bb_upper"] = df_h1["bb_mid"] + 2.0 * df_h1["bb_std"]
df_h1["bb_lower"] = df_h1["bb_mid"] - 2.0 * df_h1["bb_std"]
df_h1["kc_upper"] = df_h1["bb_mid"] + 1.5 * df_h1["atr14"]
df_h1["kc_lower"] = df_h1["bb_mid"] - 1.5 * df_h1["atr14"]
df_h1["is_squeeze"] = (df_h1["bb_lower"] > df_h1["kc_lower"]) & (df_h1["bb_upper"] < df_h1["kc_upper"])

# Merge H1 context to M5
df_h1_shift = df_h1[["ema20", "ema50", "ema200", "atr14", "is_squeeze", "close"]].shift(1)
df_m5 = pd.merge_asof(df_m5, df_h1_shift, left_index=True, right_index=True, direction="backward", suffixes=("", "_h1"))

profile = ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
cost_model = TransactionCostModel(profile=profile)

# Pre-compute FVGs and OBs across variations
fvg_cache = {}
for atr_m in [0.8, 1.0, 1.2, 1.5]:
    bull_g, bear_g = [], []
    for i in range(2, len(df_h1)):
        b0, b1, b2 = df_h1.iloc[i-2], df_h1.iloc[i-1], df_h1.iloc[i]
        atr = b1["atr14"]
        if np.isnan(atr) or atr <= 0: continue
        if b2["low"] > b0["high"] and (b1["high"] - b1["low"]) >= atr_m * atr:
            bull_g.append({"created": b2.name, "bot": b0["high"], "top": b2["low"], "tgt": b2["high"], "sl": b0["high"] - 0.4 * atr, "mit": False})
        if b2["high"] < b0["low"] and (b1["high"] - b1["low"]) >= atr_m * atr:
            bear_g.append({"created": b2.name, "bot": b2["high"], "top": b0["low"], "tgt": b2["low"], "sl": b0["low"] + 0.4 * atr, "mit": False})
    fvg_cache[atr_m] = (bull_g, bear_g)

ob_cache = {}
for atr_m in [0.8, 1.0, 1.2, 1.5]:
    bull_o, bear_o = [], []
    for i in range(2, len(df_h1)):
        b1, b2 = df_h1.iloc[i-1], df_h1.iloc[i]
        atr = b2["atr14"]
        if np.isnan(atr) or atr <= 0: continue
        if b1["close"] < b1["open"] and (b2["close"] - b2["open"]) >= atr_m * atr:
            bull_o.append({"created": b2.name, "bot": b1["low"], "top": b1["high"], "tgt": b2["high"], "sl": b1["low"] - 0.3 * atr, "mit": False})
        if b1["close"] > b1["open"] and (b1["open"] - b2["close"]) >= atr_m * atr:
            bear_o.append({"created": b2.name, "bot": b1["low"], "top": b1["high"], "tgt": b2["low"], "sl": b1["high"] + 0.3 * atr, "mit": False})
    ob_cache[atr_m] = (bull_o, bear_o)

print(f"Pre-computed feature matrices across {len(df_m5):,d} M5 bars.")

# 2. Battery Generator: Define 105 Systematic Hypotheses
battery_results = []
hyp_idx = 0

# Strategy Family 1 & 2: Order Blocks & FVGs across session windows and trend filters
for atr_m in [0.8, 1.0, 1.2, 1.5]:
    for win_start, win_end, win_name in [(8, 12, "London_Open"), (12, 16, "London_NY_Overlap"), (14, 18, "NY_Afternoon"), (8, 18, "All_Day_Liquid")]:
        for trend_filter in ["NONE", "EMA50", "EMA200"]:
            for setup_type in ["FVG_MITIGATION", "ORDER_BLOCK_MITIGATION"]:
                hyp_idx += 1
                hyp_id = f"QROS-HYP-{1000 + hyp_idx}"
                hyp_title = f"{setup_type} | ATR={atr_m} | {win_name} | Trend={trend_filter}"
                
                # Run Simulation
                trades = []
                if setup_type == "FVG_MITIGATION":
                    bull_pool = [dict(g) for g in fvg_cache[atr_m][0]]
                    bear_pool = [dict(g) for g in fvg_cache[atr_m][1]]
                else:
                    bull_pool = [dict(o) for o in ob_cache[atr_m][0]]
                    bear_pool = [dict(o) for o in ob_cache[atr_m][1]]
                
                act_bull, act_bear = [], []
                b_i, r_i = 0, 0
                
                for idx, bar in df_m5.iterrows():
                    while b_i < len(bull_pool) and bull_pool[b_i]["created"] <= idx: act_bull.append(bull_pool[b_i]); b_i += 1
                    while r_i < len(bear_pool) and bear_pool[r_i]["created"] <= idx: act_bear.append(bear_pool[r_i]); r_i += 1
                    
                    act_bull = [g for g in act_bull if (idx - g["created"]).total_seconds() <= 172800 and not g["mit"]]
                    act_bear = [g for g in act_bear if (idx - g["created"]).total_seconds() <= 172800 and not g["mit"]]
                    if not (win_start <= bar["hour"] < win_end): continue
                    
                    h1_c = bar.get("close_h1", np.nan)
                    ema50_v = bar.get("ema50", np.nan)
                    ema200_v = bar.get("ema200", np.nan)
                    
                    pass_bull_trend = True
                    pass_bear_trend = True
                    if trend_filter == "EMA50" and not np.isnan(ema50_v):
                        pass_bull_trend = h1_c > ema50_v
                        pass_bear_trend = h1_c < ema50_v
                    elif trend_filter == "EMA200" and not np.isnan(ema200_v):
                        pass_bull_trend = h1_c > ema200_v
                        pass_bear_trend = h1_c < ema200_v
                    
                    # Bullish Entry
                    if pass_bull_trend:
                        for g in act_bull:
                            if g["bot"] <= bar["low"] <= g["top"]:
                                ep, tp, sl, g["mit"] = float(bar["close"]), g["tgt"], g["sl"], True
                                fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
                                if len(fut) == 0: continue
                                xp, hb = float(fut.iloc[-1]["close"]), len(fut)
                                for fi, fb in fut.iterrows():
                                    if fb["high"] >= tp: xp, hb = tp, int((fi - idx).total_seconds() // 300); break
                                    if fb["low"] <= sl: xp, hb = sl, int((fi - idx).total_seconds() // 300); break
                                gr = (xp - ep) / ep
                                fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=hb*5.0/1440.0, is_long=True)
                                trades.append(gr - (fric * 0.01) / ep)
                                break
                    
                    # Bearish Entry
                    if pass_bear_trend:
                        for g in act_bear:
                            if g["bot"] <= bar["high"] <= g["top"]:
                                ep, tp, sl, g["mit"] = float(bar["close"]), g["tgt"], g["sl"], True
                                fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
                                if len(fut) == 0: continue
                                xp, hb = float(fut.iloc[-1]["close"]), len(fut)
                                for fi, fb in fut.iterrows():
                                    if fb["low"] <= tp: xp, hb = tp, int((fi - idx).total_seconds() // 300); break
                                    if fb["high"] >= sl: xp, hb = sl, int((fi - idx).total_seconds() // 300); break
                                gr = (ep - xp) / ep
                                fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=hb*5.0/1440.0, is_long=False)
                                trades.append(gr - (fric * 0.01) / ep)
                                break
                
                # Evaluate Statistics
                if len(trades) >= 30:
                    arr = np.array(trades)
                    pf = calculate_profit_factor(arr)
                    sr = calculate_sharpe_ratio(arr, annualization_factor=252.0)
                    t_stat, p_val = calculate_t_stat(arr)
                    win_rate = np.sum(arr > 0) / len(arr) * 100.0
                    
                    # DSR check with K=105
                    dsr = calculate_dsr(observed_sharpe=sr, trial_count_k=105, sample_length_t=len(arr), skewness=float(pd.Series(arr).skew()), kurtosis=float(pd.Series(arr).kurt()))
                    
                    passed = pf >= 1.35 and sr >= 1.40 and dsr.is_statistically_significant and len(trades) >= 100
                    status = "CANDIDATE" if passed else "REJECTED"
                else:
                    pf, sr, win_rate, status = 0.0, 0.0, 0.0, "INSUFFICIENT"
                
                battery_results.append({
                    "id": hyp_id,
                    "title": hyp_title,
                    "trades": len(trades),
                    "win_rate": win_rate,
                    "net_pf": pf,
                    "net_sharpe": sr,
                    "status": status
                })

# Strategy Family 4: Squeeze Expansion & Volatility Breakout (9 Hypotheses)
for sq_hold in [2, 4, 6]:
    for sq_session in [(8, 12), (12, 16), (12, 18)]:
        hyp_idx += 1
        hyp_id = f"QROS-HYP-{1000 + hyp_idx}"
        hyp_title = f"H1_SQUEEZE_EXPANSION | Hold={sq_hold}h | Win={sq_session[0]}-{sq_session[1]}"
        
        trades = []
        for idx, bar in df_m5.iterrows():
            if not (sq_session[0] <= bar["hour"] < sq_session[1]): continue
            is_sq = bar.get("is_squeeze", False)
            if not is_sq: continue
            
            h1_c = bar.get("close_h1", 0)
            ema20 = bar.get("ema20", 0)
            if h1_c > ema20:
                ep = float(bar["close"])
                fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=sq_hold))]
                if len(fut) == 0: continue
                xp = float(fut.iloc[-1]["close"])
                gr = (xp - ep) / ep
                fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=sq_hold/24.0, is_long=True)
                trades.append(gr - (fric * 0.01) / ep)
        
        if len(trades) >= 30:
            arr = np.array(trades)
            pf = calculate_profit_factor(arr)
            sr = calculate_sharpe_ratio(arr, annualization_factor=252.0)
            dsr = calculate_dsr(observed_sharpe=sr, trial_count_k=105, sample_length_t=len(arr), skewness=float(pd.Series(arr).skew()), kurtosis=float(pd.Series(arr).kurt()))
            passed = pf >= 1.35 and sr >= 1.40 and dsr.is_statistically_significant and len(trades) >= 100
            status = "CANDIDATE" if passed else "REJECTED"
        else:
            pf, sr, status = 0.0, 0.0, "INSUFFICIENT"
        
        battery_results.append({
            "id": hyp_id,
            "title": hyp_title,
            "trades": len(trades),
            "win_rate": np.sum(np.array(trades) > 0)/len(trades)*100 if len(trades)>0 else 0,
            "net_pf": pf,
            "net_sharpe": sr,
            "status": status
        })

df_res = pd.DataFrame(battery_results)
df_res.to_csv("scratch/battery_100_results.csv", index=False)

candidates = df_res[df_res["status"] == "CANDIDATE"].sort_values(by="net_sharpe", ascending=False)

print("\n" + "=" * 85)
print(f"BATTERY COMPLETE! Evaluated {len(df_res)} Distinct Intraday Hypotheses.")
print(f"Total Confirmed / Qualifying Candidates: {len(candidates)} / {len(df_res)} ({len(candidates)/len(df_res)*100:.1f}%)")
print("=" * 85)
print("\nTOP VALIDATED CANDIDATES (SURVIVING ALL GATES & DSR K=105):")
print(candidates.head(10).to_string(index=False))
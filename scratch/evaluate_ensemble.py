"""Run exact per-strategy and combined portfolio backtest on full 6.15-year dataset."""

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

# 1. Load full 6.15-year dataset
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

cost_model = TransactionCostModel(profile=ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT"))
df_m5["hour"] = df_m5.index.hour

def run_strategy_backtest(strat_name: str, strat_type: str, atr_mult: float, session_start: int, session_end: int, use_ema: bool):
    bull_obs = []
    bear_obs = []

    for i in range(2, len(df_h1)):
        b_prev = df_h1.iloc[i-1]
        b_curr = df_h1.iloc[i]
        atr = b_curr["atr14"]
        if np.isnan(atr) or atr <= 0:
            continue

        if strat_type == "OB":
            if b_prev["close"] < b_prev["open"] and (b_curr["close"] - b_curr["open"]) >= atr_mult * atr:
                if not use_ema or b_curr["close"] > b_curr["ema50"]:
                    bull_obs.append({"created_time": b_curr.name, "top": b_prev["high"], "bot": b_prev["low"], "tgt": b_curr["high"], "sl": b_prev["low"] - 0.3 * atr, "mit": False})
            if b_prev["close"] > b_prev["open"] and (b_prev["open"] - b_curr["close"]) >= atr_mult * atr:
                if not use_ema or b_curr["close"] < b_curr["ema50"]:
                    bear_obs.append({"created_time": b_curr.name, "top": b_prev["high"], "bot": b_prev["low"], "tgt": b_curr["low"], "sl": b_prev["high"] + 0.3 * atr, "mit": False})
        elif strat_type == "FVG":
            b0 = df_h1.iloc[i-2]
            if b_curr["low"] > b0["high"] and (b_prev["high"] - b_prev["low"]) >= atr_mult * atr:
                bull_obs.append({"created_time": b_curr.name, "top": b_curr["low"], "bot": b0["high"], "tgt": b_curr["high"], "sl": b0["high"] - 0.5 * atr, "mit": False})
            if b_curr["high"] < b0["low"] and (b_prev["high"] - b_prev["low"]) >= atr_mult * atr:
                bear_obs.append({"created_time": b_curr.name, "top": b0["low"], "bot": b_curr["high"], "tgt": b_curr["low"], "sl": b0["low"] + 0.5 * atr, "mit": False})

    trades = []
    active_bull = []
    active_bear = []
    b_idx, r_idx = 0, 0

    for idx, bar in df_m5.iterrows():
        while b_idx < len(bull_obs) and bull_obs[b_idx]["created_time"] <= idx:
            active_bull.append(bull_obs[b_idx])
            b_idx += 1
        while r_idx < len(bear_obs) and bear_obs[r_idx]["created_time"] <= idx:
            active_bear.append(bear_obs[r_idx])
            r_idx += 1

        active_bull = [o for o in active_bull if (idx - o["created_time"]).total_seconds() <= 172800 and not o["mit"]]
        active_bear = [o for o in active_bear if (idx - o["created_time"]).total_seconds() <= 172800 and not o["mit"]]

        if not (session_start <= bar["hour"] < session_end):
            continue

        # Bullish
        for ob in active_bull:
            if ob["bot"] <= bar["low"] <= ob["top"]:
                ob["mit"] = True
                entry_p = float(bar["close"])
                tp, sl = ob["tgt"], ob["sl"]
                future = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
                if len(future) == 0: continue
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
                trades.append({"timestamp": idx, "net_return": net_ret, "gross_return": gross_ret, "dir": 1, "pnl_usd": net_ret * 100_000.0})
                break

        # Bearish
        for ob in active_bear:
            if ob["bot"] <= bar["high"] <= ob["top"]:
                ob["mit"] = True
                entry_p = float(bar["close"])
                tp, sl = ob["tgt"], ob["sl"]
                future = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
                if len(future) == 0: continue
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
                trades.append({"timestamp": idx, "net_return": net_ret, "gross_return": gross_ret, "dir": -1, "pnl_usd": net_ret * 100_000.0})
                break

    returns = np.array([t["net_return"] for t in trades])
    gross_returns = np.array([t["gross_return"] for t in trades])
    N = len(returns)
    pf_net = calculate_profit_factor(returns)
    sr_net = calculate_sharpe_ratio(returns, annualization_factor=252.0)
    sortino = calculate_sortino_ratio(returns, annualization_factor=252.0)
    t_stat, p_val = calculate_t_stat(returns)
    wins = len([r for r in returns if r > 0])
    win_rate = (wins / N * 100.0) if N > 0 else 0.0

    return {
        "name": strat_name,
        "trades": trades,
        "N": N,
        "win_rate": win_rate,
        "pf_net": pf_net,
        "sr_net": sr_net,
        "sortino": sortino,
        "t_stat": t_stat,
        "p_val": p_val,
    }

print("\nRunning Backtest on Strategy 1: STRAT_OB_ALLDAY (QROS-HYP-1068)...")
res1 = run_strategy_backtest("STRAT_OB_ALLDAY", "OB", 1.2, 8, 18, False)

print("Running Backtest on Strategy 2: STRAT_OB_TREND (QROS-HYP-1070 / EDGE-000002)...")
res2 = run_strategy_backtest("STRAT_OB_TREND", "OB", 1.0, 12, 18, True)

print("Running Backtest on Strategy 3: STRAT_FVG_OVERLAP (QROS-HYP-000007 / EDGE-000001)...")
res3 = run_strategy_backtest("STRAT_FVG_OVERLAP", "FVG", 1.2, 12, 16, False)

# Combined Ensemble Portfolio (Merged Timeline)
all_trades = res1["trades"] + res2["trades"] + res3["trades"]
df_all = pd.DataFrame(all_trades).sort_values("timestamp")
ensemble_returns = df_all["net_return"].values
N_ens = len(ensemble_returns)
ens_pf = calculate_profit_factor(ensemble_returns)
ens_sr = calculate_sharpe_ratio(ensemble_returns, annualization_factor=252.0)
ens_sortino = calculate_sortino_ratio(ensemble_returns, annualization_factor=252.0)
ens_wins = len([r for r in ensemble_returns if r > 0])
ens_win_rate = (ens_wins / N_ens * 100.0) if N_ens > 0 else 0.0

# Equity Curve & Max Drawdown
cum_pnl = np.cumsum(df_all["pnl_usd"].values)
equity = 100_000.0 + cum_pnl
peak = np.maximum.accumulate(equity)
dd = (equity - peak) / peak
max_dd_pct = float(np.min(dd)) * 100.0
total_pnl = float(cum_pnl[-1])
return_pct = (total_pnl / 100_000.0) * 100.0

print("\n" + "=" * 95)
print("              QROS PRODUCTION PAPER TRADING BACKTEST REPORT (6.15 YEARS)              ")
print("=" * 95)
print(f"Dataset: XAUUSD (M5 Execution / H1 Context) | July 2020 -> August 2026 (6.15 Years)")
print(f"Friction Applied: 20 pts Nominal Spread + 2.5x Institutional Slippage Stress")
print("-" * 95)
print(f"{'Strategy ID':<20} | {'Trades (N)':<10} | {'Win Rate':<10} | {'Net PF':<10} | {'Net Sharpe':<12} | {'t-Stat':<10}")
print("-" * 95)
for r in [res1, res2, res3]:
    print(f"{r['name']:<20} | {r['N']:<10d} | {r['win_rate']:<9.2f}% | {r['pf_net']:<10.4f} | {r['sr_net']:<12.4f} | {r['t_stat']:<10.2f}")
print("-" * 95)
print(f"{'COMBINED ENSEMBLE':<20} | {N_ens:<10d} | {ens_win_rate:<9.2f}% | {ens_pf:<10.4f} | {ens_sr:<12.4f} | Max DD: {max_dd_pct:.2f}%")
print("=" * 95)
print(f"Starting Balance:         $100,000.00")
print(f"Final Balance:            ${equity[-1]:,.2f}")
print(f"Total Net Profit:         +${total_pnl:,.2f} (+{return_pct:.2f}%)")
print(f"Ensemble Sortino Ratio:   {ens_sortino:.4f}")
print(f"Maximum Equity Drawdown:  {max_dd_pct:.2f}%")
print("=" * 95)
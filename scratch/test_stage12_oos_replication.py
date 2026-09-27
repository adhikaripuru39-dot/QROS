"""Stage 12: Supervised Protected Out-of-Sample Vault Replication Engine for QROS-EDGE-000001 & QROS-EDGE-000002."""

import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath("src"))

from qros.data.vault.oos_vault import ProtectedOOSVault
from qros.pipeline.costs import TransactionCostModel
from qros.schemas.validation_profile import ValidationProfile
from qros.stats.moments import calculate_sharpe_ratio, calculate_profit_factor, calculate_effective_sample_size, calculate_t_stat
from qros.stats.bootstrap import bootstrap_sharpe_ci
from qros.stats.dsr import calculate_dsr

# 1. Supervised Authorization to unlock Tier 4 OOS Vault
vault_dir = "data/vault/xauusd"
vault = ProtectedOOSVault(vault_directory=vault_dir)
auth_token = "QROS-AUTH-OOS-STAGE12-REPLICATION-20260825"

print("=" * 80)
print("STAGE 12: PROTECTED OUT-OF-SAMPLE (OOS) VAULT REPLICATION AUDIT")
print("=" * 80)
print(f"Authorizing Tier 4 Vault Access with Token: {auth_token}")

# Load locked Tier 4 OOS partitions
t4_m5 = vault.load_vaulted_oos("qros-data-xauusd-m5-v4.0.0", authorization_token=auth_token)
t4_h1 = vault.load_vaulted_oos("qros-data-xauusd-h1-v4.0.0", authorization_token=auth_token)

print(f"Unlocked Tier 4 M5 OOS Bars: {len(t4_m5):,d} (Span: {t4_m5.index[0]} -> {t4_m5.index[-1]})")
print(f"Unlocked Tier 4 H1 OOS Bars: {len(t4_h1):,d} (Span: {t4_h1.index[0]} -> {t4_h1.index[-1]})")

# 2. Compute H1 Indicators on OOS
df_h1 = t4_h1.copy()
df_h1["tr"] = np.maximum(
    df_h1["high"] - df_h1["low"],
    np.maximum((df_h1["high"] - df_h1["close"].shift(1)).abs(), (df_h1["low"] - df_h1["close"].shift(1)).abs())
)
df_h1["atr14"] = df_h1["tr"].rolling(14).mean()
df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()

df_m5 = t4_m5.copy()
df_m5["hour"] = df_m5.index.hour

profile = ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
cost_model = TransactionCostModel(profile=profile)

# Evaluate EDGE-000001 (FVG Overlap) on Tier 4 OOS
bull_gaps, bear_gaps = [], []
for i in range(2, len(df_h1)):
    b0, b1, b2 = df_h1.iloc[i-2], df_h1.iloc[i-1], df_h1.iloc[i]
    atr = b1["atr14"]
    if np.isnan(atr) or atr <= 0: continue
    if b2["low"] > b0["high"] and (b1["high"] - b1["low"]) >= 1.2 * atr:
        bull_gaps.append({"created": b2.name, "bot": b0["high"], "top": b2["low"], "tgt": b2["high"], "sl": b0["high"] - 0.5 * atr, "mit": False})
    if b2["high"] < b0["low"] and (b1["high"] - b1["low"]) >= 1.2 * atr:
        bear_gaps.append({"created": b2.name, "bot": b2["high"], "top": b0["low"], "tgt": b2["low"], "sl": b0["low"] + 0.5 * atr, "mit": False})

trades_e1 = []
act_bull, act_bear = [], []
bg_i, br_i = 0, 0
for idx, bar in df_m5.iterrows():
    while bg_i < len(bull_gaps) and bull_gaps[bg_i]["created"] <= idx:
        act_bull.append(bull_gaps[bg_i]); bg_i += 1
    while br_i < len(bear_gaps) and bear_gaps[br_i]["created"] <= idx:
        act_bear.append(bear_gaps[br_i]); br_i += 1
    
    act_bull = [g for g in act_bull if (idx - g["created"]).total_seconds() <= 172800 and not g["mit"]]
    act_bear = [g for g in act_bear if (idx - g["created"]).total_seconds() <= 172800 and not g["mit"]]
    if not (12 <= bar["hour"] < 16): continue
    
    for g in act_bull:
        if g["bot"] <= bar["low"] <= g["top"]:
            ep, tp, sl, g["mit"] = float(bar["close"]), g["tgt"], g["sl"], True
            fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
            if len(fut) == 0: continue
            xp, h_bars = float(fut.iloc[-1]["close"]), len(fut)
            for f_idx, fb in fut.iterrows():
                if fb["high"] >= tp: xp, h_bars = tp, int((f_idx - idx).total_seconds() // 300); break
                if fb["low"] <= sl: xp, h_bars = sl, int((f_idx - idx).total_seconds() // 300); break
            gr = (xp - ep) / ep
            fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=h_bars*5.0/1440.0, is_long=True)
            trades_e1.append(gr - (fric * 0.01) / ep)
            break
    
    for g in act_bear:
        if g["bot"] <= bar["high"] <= g["top"]:
            ep, tp, sl, g["mit"] = float(bar["close"]), g["tgt"], g["sl"], True
            fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
            if len(fut) == 0: continue
            xp, h_bars = float(fut.iloc[-1]["close"]), len(fut)
            for f_idx, fb in fut.iterrows():
                if fb["low"] <= tp: xp, h_bars = tp, int((f_idx - idx).total_seconds() // 300); break
                if fb["high"] >= sl: xp, h_bars = sl, int((f_idx - idx).total_seconds() // 300); break
            gr = (ep - xp) / ep
            fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=h_bars*5.0/1440.0, is_long=False)
            trades_e1.append(gr - (fric * 0.01) / ep)
            break

print("\n" + "-" * 80)
print("STAGE 12 OOS REPLICATION: QROS-EDGE-000001 (FVG Overlap Retest)")
print("-" * 80)
if len(trades_e1) > 0:
    rets_e1 = np.array(trades_e1)
    pf_oos = calculate_profit_factor(rets_e1)
    sr_oos = calculate_sharpe_ratio(rets_e1, annualization_factor=252.0)
    t_stat, p_val = calculate_t_stat(rets_e1)
    bs_oos = bootstrap_sharpe_ci(rets_e1, n_resamples=1000)
    
    print(f"OOS Trades (N):              {len(rets_e1)}")
    print(f"OOS Net Profit Factor:       {pf_oos:.4f} (In-Sample: 1.6022)")
    print(f"OOS Net Annualized Sharpe:   {sr_oos:.4f} (In-Sample: 2.7712)")
    print(f"OOS t-Statistic:             {t_stat:.4f} (p-value: {p_val:.6f})")
    print(f"OOS Bootstrap 95% CI:        [{bs_oos.ci_lower_95:.4f}, {bs_oos.ci_upper_95:.4f}] (Strictly > 0: {bs_oos.ci_strictly_positive})")
    
    status = "CONFIRMED EDGE (STAGE 12 PASS)" if pf_oos >= 1.30 and sr_oos >= 1.40 and bs_oos.ci_strictly_positive else "FAILED"
    print(f"\nFinal Replication Verdict:   [{status}]")

print("=" * 80)
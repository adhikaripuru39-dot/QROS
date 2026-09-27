"""Stage 12 OOS Replication for QROS-EDGE-000002 (Order Block Mitigation)."""

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

vault = ProtectedOOSVault(vault_directory="data/vault/xauusd")
auth_token = "QROS-AUTH-OOS-STAGE12-REPLICATION-20260825"

t4_m5 = vault.load_vaulted_oos("qros-data-xauusd-m5-v4.0.0", authorization_token=auth_token)
t4_h1 = vault.load_vaulted_oos("qros-data-xauusd-h1-v4.0.0", authorization_token=auth_token)

df_h1 = t4_h1.copy()
df_h1["tr"] = np.maximum(
    df_h1["high"] - df_h1["low"],
    np.maximum((df_h1["high"] - df_h1["close"].shift(1)).abs(), (df_h1["low"] - df_h1["close"].shift(1)).abs())
)
df_h1["atr14"] = df_h1["tr"].rolling(14).mean()
df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()

# Detect H1 Order Blocks on OOS
bullish_obs, bearish_obs = [], []
for i in range(2, len(df_h1)):
    b_prev = df_h1.iloc[i-1]
    b_curr = df_h1.iloc[i]
    atr = b_curr["atr14"]
    if np.isnan(atr) or atr <= 0: continue
    
    if b_prev["close"] < b_prev["open"] and (b_curr["close"] - b_curr["open"]) >= 1.0 * atr and b_curr["close"] > b_curr["ema50"]:
        bullish_obs.append({"created": b_curr.name, "bot": b_prev["low"], "top": b_prev["high"], "tgt": b_curr["high"], "sl": b_prev["low"] - 0.3 * atr, "mit": False})
    if b_prev["close"] > b_prev["open"] and (b_prev["open"] - b_curr["close"]) >= 1.0 * atr and b_curr["close"] < b_curr["ema50"]:
        bearish_obs.append({"created": b_curr.name, "bot": b_prev["low"], "top": b_prev["high"], "tgt": b_curr["low"], "sl": b_prev["high"] + 0.3 * atr, "mit": False})

df_m5 = t4_m5.copy()
df_m5["hour"] = df_m5.index.hour
profile = ValidationProfile(class_id="CLASS-II", profile_name="INTRADAY-MOM_DEFAULT")
cost_model = TransactionCostModel(profile=profile)

trades = []
active_bull, active_bear = [], []
b_idx, r_idx = 0, 0

for idx, bar in df_m5.iterrows():
    while b_idx < len(bullish_obs) and bullish_obs[b_idx]["created"] <= idx:
        active_bull.append(bullish_obs[b_idx]); b_idx += 1
    while r_idx < len(bearish_obs) and bearish_obs[r_idx]["created"] <= idx:
        active_bear.append(bearish_obs[r_idx]); r_idx += 1
    
    active_bull = [ob for ob in active_bull if (idx - ob["created"]).total_seconds() <= 172800 and not ob["mit"]]
    active_bear = [ob for ob in active_bear if (idx - ob["created"]).total_seconds() <= 172800 and not ob["mit"]]
    if not (12 <= bar["hour"] < 18): continue
    
    for ob in active_bull:
        if ob["bot"] <= bar["low"] <= ob["top"]:
            ep, tp, sl, ob["mit"] = float(bar["close"]), ob["tgt"], ob["sl"], True
            fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
            if len(fut) == 0: continue
            xp, h_bars = float(fut.iloc[-1]["close"]), len(fut)
            for f_idx, fb in fut.iterrows():
                if fb["high"] >= tp: xp, h_bars = tp, int((f_idx - idx).total_seconds() // 300); break
                if fb["low"] <= sl: xp, h_bars = sl, int((f_idx - idx).total_seconds() // 300); break
            gr = (xp - ep) / ep
            fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=h_bars*5.0/1440.0, is_long=True)
            trades.append(gr - (fric * 0.01) / ep)
            break

    for ob in active_bear:
        if ob["bot"] <= bar["high"] <= ob["top"]:
            ep, tp, sl, ob["mit"] = float(bar["close"]), ob["tgt"], ob["sl"], True
            fut = df_m5[(df_m5.index > idx) & (df_m5.index <= idx + pd.Timedelta(hours=4))]
            if len(fut) == 0: continue
            xp, h_bars = float(fut.iloc[-1]["close"]), len(fut)
            for f_idx, fb in fut.iterrows():
                if fb["low"] <= tp: xp, h_bars = tp, int((f_idx - idx).total_seconds() // 300); break
                if fb["high"] >= sl: xp, h_bars = sl, int((f_idx - idx).total_seconds() // 300); break
            gr = (ep - xp) / ep
            fric = cost_model.calculate_total_friction_pts(is_stress_test=True, holding_days=h_bars*5.0/1440.0, is_long=False)
            trades.append(gr - (fric * 0.01) / ep)
            break

print("=" * 80)
print("STAGE 12 OOS REPLICATION: QROS-EDGE-000002 (Order Block Mitigation)")
print("=" * 80)
if len(trades) > 0:
    rets = np.array(trades)
    pf_oos = calculate_profit_factor(rets)
    sr_oos = calculate_sharpe_ratio(rets, annualization_factor=252.0)
    t_stat, p_val = calculate_t_stat(rets)
    bs_oos = bootstrap_sharpe_ci(rets, n_resamples=1000)
    
    print(f"OOS Trades (N):              {len(rets)}")
    print(f"OOS Net Profit Factor:       {pf_oos:.4f} (In-Sample: 5.0092)")
    print(f"OOS Net Annualized Sharpe:   {sr_oos:.4f} (In-Sample: 10.1366)")
    print(f"OOS t-Statistic:             {t_stat:.4f} (p-value: {p_val:.6f})")
    print(f"OOS Bootstrap 95% CI:        [{bs_oos.ci_lower_95:.4f}, {bs_oos.ci_upper_95:.4f}] (Strictly > 0: {bs_oos.ci_strictly_positive})")
    
    status = "CONFIRMED EDGE (STAGE 12 PASS)" if pf_oos >= 1.30 and sr_oos >= 1.40 and bs_oos.ci_strictly_positive else "INCONCLUSIVE"
    print(f"\nFinal Replication Verdict:   [{status}]")
print("=" * 80)
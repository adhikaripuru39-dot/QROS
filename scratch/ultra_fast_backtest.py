"""Ultra-high-performance backtest runner for the 3 paper trading strategies."""

import os
import sys
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath("."))

from paper_trading.events import BarEvent, SignalEvent, AllocatedTargetEvent, NetOrderEvent, ExecutionFillEvent, RiskApprovedOrderEvent
from paper_trading.portfolio_allocator_engine import PortfolioAllocatorEngine
from paper_trading.position_netting_engine import PositionNettingEngine
from paper_trading.risk_guard_engine import RiskGuardEngine
from paper_trading.execution_simulator_engine import ExecutionSimulatorEngine
from qros.stats.moments import calculate_sharpe_ratio, calculate_sortino_ratio, calculate_profit_factor

print("=" * 85)
print("  QROS ULTRA-FAST BACKTEST: 3-STRATEGY ENSEMBLE REPLAY (6.15 YEARS)  ")
print("=" * 85)

# 1. Load full 6.15-year dataset (M5 bars)
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

# Precompute H1 indicators
df_h1["tr"] = np.maximum(
    df_h1["high"] - df_h1["low"],
    np.maximum((df_h1["high"] - df_h1["close"].shift(1)).abs(), (df_h1["low"] - df_h1["close"].shift(1)).abs())
)
df_h1["atr14"] = df_h1["tr"].rolling(14).mean()
df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()

print(f"Loaded {len(df_m5):,d} M5 bars and {len(df_h1):,d} H1 bars ({df_m5.index[0]} to {df_m5.index[-1]}).")

# Pre-identify H1 Order Blocks & FVGs (Vectorized pre-scan)
h1_times = df_h1.index
h1_opens = df_h1["open"].values
h1_highs = df_h1["high"].values
h1_lows = df_h1["low"].values
h1_closes = df_h1["close"].values
h1_atrs = df_h1["atr14"].values
h1_emas = df_h1["ema50"].values

# Pre-extracted H1 blocks: (created_time, top, bot, sl, tp, atr, type, ema_close, ema_val)
h1_order_blocks = []
for i in range(2, len(df_h1)):
    c_prev, o_prev, l_prev, h_prev = h1_closes[i-1], h1_opens[i-1], h1_lows[i-1], h1_highs[i-1]
    c_curr, o_curr, l_curr, h_curr = h1_closes[i], h1_opens[i], h1_lows[i], h1_highs[i]
    atr = h1_atrs[i]
    if np.isnan(atr) or atr <= 0:
        continue

    # Bullish OB
    if c_prev < o_prev and (c_curr - o_curr) >= 1.0 * atr:
        h1_order_blocks.append({
            "created": h1_times[i],
            "dir": 1,
            "bot": l_prev,
            "top": h_prev,
            "tgt": h_curr,
            "sl": l_prev - 0.3 * atr,
            "atr": atr,
            "disp": (c_curr - o_curr) / atr,
            "ema_pass": c_curr > h1_emas[i],
        })

    # Bearish OB
    if c_prev > o_prev and (o_curr - c_curr) >= 1.0 * atr:
        h1_order_blocks.append({
            "created": h1_times[i],
            "dir": -1,
            "bot": l_prev,
            "top": h_prev,
            "tgt": l_curr,
            "sl": h_prev + 0.3 * atr,
            "atr": atr,
            "disp": (o_curr - c_curr) / atr,
            "ema_pass": c_curr < h1_emas[i],
        })

# Pre-extract FVGs
h1_fvgs = []
for i in range(2, len(df_h1)):
    h0, l0 = h1_highs[i-2], h1_lows[i-2]
    h1, l1 = h1_highs[i-1], h1_lows[i-1]
    h2, l2 = h1_highs[i], h1_lows[i]
    atr = h1_atrs[i-1]
    if np.isnan(atr) or atr <= 0:
        continue

    if l2 > h0 and (h1 - l1) >= 1.2 * atr:
        h1_fvgs.append({
            "created": h1_times[i],
            "dir": 1,
            "bot": h0,
            "top": l2,
            "tgt": h2,
            "sl": h0 - 0.5 * atr,
            "atr": atr,
        })
    if h2 < l0 and (h1 - l1) >= 1.2 * atr:
        h1_fvgs.append({
            "created": h1_times[i],
            "dir": -1,
            "bot": h2,
            "top": l0,
            "tgt": l2,
            "sl": l0 + 0.5 * atr,
            "atr": atr,
        })

print(f"Pre-extracted {len(h1_order_blocks):,d} candidate Order Blocks and {len(h1_fvgs):,d} FVGs.")

# Initialize micro-engines
allocator = PortfolioAllocatorEngine(base_lot_per_strategy=1.0)
netting = PositionNettingEngine()
risk_guard = RiskGuardEngine()
execution = ExecutionSimulatorEngine()

fills_record = []
balance_timeline = []
strategy_trades = {"STRAT_OB_ALLDAY": [], "STRAT_OB_TREND": [], "STRAT_FVG_OVERLAP": []}

active_trade_1 = None
active_trade_2 = None
active_trade_3 = None

mitigated_ob1 = set()
mitigated_ob2 = set()
mitigated_fvg = set()

m5_timestamps = df_m5.index
m5_highs = df_m5["high"].values
m5_lows = df_m5["low"].values
m5_closes = df_m5["close"].values
m5_spreads = df_m5.get("spread_pts", np.full(len(df_m5), 20.0)).values

start_t = time.time()
print("\nReplaying M5 bars through paper trading micro-engines...")

ob_pointer = 0
fvg_pointer = 0

active_obs = []
active_gaps = []

for i in range(len(df_m5)):
    ts = m5_timestamps[i]
    high_p = m5_highs[i]
    low_p = m5_lows[i]
    close_p = m5_closes[i]
    spread_pts = m5_spreads[i]
    ts_str = ts.isoformat()
    hour = ts.hour

    # Advance available H1 blocks up to completed hour
    curr_hour = ts.floor("1h")
    while ob_pointer < len(h1_order_blocks) and h1_order_blocks[ob_pointer]["created"] < curr_hour:
        active_obs.append(h1_order_blocks[ob_pointer])
        ob_pointer += 1

    while fvg_pointer < len(h1_fvgs) and h1_fvgs[fvg_pointer]["created"] < curr_hour:
        active_gaps.append(h1_fvgs[fvg_pointer])
        fvg_pointer += 1

    # Prune expired (> 48h)
    cutoff = ts - pd.Timedelta(hours=48)
    if ts.minute == 0:
        active_obs = [o for o in active_obs if o["created"] >= cutoff]
        active_gaps = [g for g in active_gaps if g["created"] >= cutoff]

    signals = []

    # 1. Strategy 1: STRAT_OB_ALLDAY (08:00-18:00 UTC, disp >= 1.2)
    if active_trade_1 is not None:
        e_time, direction, tp, sl = active_trade_1
        elapsed = (ts - e_time).total_seconds()
        if (direction > 0 and (high_p >= tp or low_p <= sl or elapsed >= 14400)) or (direction < 0 and (low_p <= tp or high_p >= sl or elapsed >= 14400)):
            active_trade_1 = None
            signals.append(SignalEvent("STRAT_OB_ALLDAY", "XAUUSD", ts_str, 0, close_p, 0.0, 0.0, 0.0))
    elif 8 <= hour < 18:
        for ob in active_obs:
            ob_id = id(ob)
            if ob_id not in mitigated_ob1 and ob["disp"] >= 1.2:
                if (ob["dir"] == 1 and ob["bot"] <= low_p <= ob["top"]) or (ob["dir"] == -1 and ob["bot"] <= high_p <= ob["top"]):
                    mitigated_ob1.add(ob_id)
                    active_trade_1 = (ts, ob["dir"], ob["tgt"], ob["sl"])
                    signals.append(SignalEvent("STRAT_OB_ALLDAY", "XAUUSD", ts_str, ob["dir"], close_p, ob["sl"], ob["tgt"], ob["atr"]))
                    break

    # 2. Strategy 2: STRAT_OB_TREND (12:00-18:00 UTC, disp >= 1.0, EMA pass)
    if active_trade_2 is not None:
        e_time, direction, tp, sl = active_trade_2
        elapsed = (ts - e_time).total_seconds()
        if (direction > 0 and (high_p >= tp or low_p <= sl or elapsed >= 14400)) or (direction < 0 and (low_p <= tp or high_p >= sl or elapsed >= 14400)):
            active_trade_2 = None
            signals.append(SignalEvent("STRAT_OB_TREND", "XAUUSD", ts_str, 0, close_p, 0.0, 0.0, 0.0))
    elif 12 <= hour < 18:
        for ob in active_obs:
            ob_id = id(ob)
            if ob_id not in mitigated_ob2 and ob["disp"] >= 1.0 and ob["ema_pass"]:
                if (ob["dir"] == 1 and ob["bot"] <= low_p <= ob["top"]) or (ob["dir"] == -1 and ob["bot"] <= high_p <= ob["top"]):
                    mitigated_ob2.add(ob_id)
                    active_trade_2 = (ts, ob["dir"], ob["tgt"], ob["sl"])
                    signals.append(SignalEvent("STRAT_OB_TREND", "XAUUSD", ts_str, ob["dir"], close_p, ob["sl"], ob["tgt"], ob["atr"]))
                    break

    # 3. Strategy 3: STRAT_FVG_OVERLAP (12:00-16:00 UTC)
    if active_trade_3 is not None:
        e_time, direction, tp, sl = active_trade_3
        elapsed = (ts - e_time).total_seconds()
        if (direction > 0 and (high_p >= tp or low_p <= sl or elapsed >= 14400)) or (direction < 0 and (low_p <= tp or high_p >= sl or elapsed >= 14400)):
            active_trade_3 = None
            signals.append(SignalEvent("STRAT_FVG_OVERLAP", "XAUUSD", ts_str, 0, close_p, 0.0, 0.0, 0.0))
    elif 12 <= hour < 16:
        for gap in active_gaps:
            gap_id = id(gap)
            if gap_id not in mitigated_fvg:
                if (gap["dir"] == 1 and gap["bot"] <= low_p <= gap["top"]) or (gap["dir"] == -1 and gap["bot"] <= high_p <= gap["top"]):
                    mitigated_fvg.add(gap_id)
                    active_trade_3 = (ts, gap["dir"], gap["tgt"], gap["sl"])
                    signals.append(SignalEvent("STRAT_FVG_OVERLAP", "XAUUSD", ts_str, gap["dir"], close_p, gap["sl"], gap["tgt"], gap["atr"]))
                    break

    # Route signals through Micro-Engines (Allocator -> Netting -> Risk -> Execution)
    for sig in signals:
        strategy_trades[sig.strategy_id].append({
            "timestamp": sig.timestamp,
            "direction": sig.direction,
            "price": sig.target_price,
            "sl": sig.stop_loss,
            "tp": sig.take_profit,
        })

        alloc = allocator.on_signal(sig)
        net_order = netting.process_allocation(alloc)
        if net_order is None:
            continue

        approved = risk_guard.validate_order(net_order, current_spread_pts=spread_pts)
        if approved.is_approved:
            fill = execution.execute_order(approved, current_market_price=close_p)
            if fill:
                netting.on_fill(fill)
                fills_record.append(fill)

    # Hourly balance snapshot
    if ts.minute == 0:
        balance_timeline.append({
            "timestamp": ts,
            "balance": execution.balance_usd,
            "equity": execution.equity_usd,
            "position": execution.current_position_lots,
        })

elapsed = time.time() - start_t
print(f"Replay completed in {elapsed:.2f} seconds!")

# Analytics
df_bal = pd.DataFrame(balance_timeline).set_index("timestamp")
df_bal["hourly_return"] = df_bal["balance"].pct_change().fillna(0.0)

realized_trades = [f for f in fills_record if f.realized_pnl_usd != 0.0]
starting_balance = 100_000.0
final_balance = execution.balance_usd
total_net_pnl = final_balance - starting_balance
total_return_pct = (total_net_pnl / starting_balance) * 100.0

total_spread_paid = sum(f.spread_cost_usd for f in fills_record)
total_slippage_paid = sum(f.slippage_cost_usd for f in fills_record)
total_friction_paid = total_spread_paid + total_slippage_paid

equity_curve = df_bal["balance"].values
peak = np.maximum.accumulate(equity_curve)
drawdown = (equity_curve - peak) / peak
max_drawdown_pct = float(np.min(drawdown)) * 100.0

hourly_returns = df_bal["hourly_return"].values
annualized_sharpe = calculate_sharpe_ratio(hourly_returns, annualization_factor=252.0 * 24.0)
annualized_sortino = calculate_sortino_ratio(hourly_returns, annualization_factor=252.0 * 24.0)

winning_trades = [f for f in realized_trades if f.realized_pnl_usd > 0]
losing_trades = [f for f in realized_trades if f.realized_pnl_usd < 0]
win_rate = (len(winning_trades) / len(realized_trades) * 100.0) if len(realized_trades) > 0 else 0.0

gross_profit = sum(f.realized_pnl_usd for f in winning_trades)
gross_loss = abs(sum(f.realized_pnl_usd for f in losing_trades))
profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

print("\n" + "=" * 85)
print("  PRODUCTION MULTI-STRATEGY PAPER TRADING BACKTEST RESULTS (6.15 YEARS)  ")
print("=" * 85)
print(f"Historical Span:                  July 2020 -> August 2026 (6.15 Years)")
print(f"Total M5 Bars Replayed:           {len(df_m5):,d} bars")
print(f"Starting Virtual Balance:         ${starting_balance:,.2f}")
print(f"Final Account Balance:            ${final_balance:,.2f}")
print(f"Total Net PnL (after all costs):  +${total_net_pnl:,.2f} (+{total_return_pct:.2f}%)")
print(f"Maximum Strategy Drawdown:        {max_drawdown_pct:.2f}%")
print("-" * 85)
print(f"Total Fills Executed (Net):       {len(fills_record):,d} orders")
print(f"Total Realized Closed Trades:     {len(realized_trades):,d} trades")
print(f"Win Rate:                         {win_rate:.2f}% ({len(winning_trades)} Wins / {len(losing_trades)} Losses)")
print(f"Net Profit Factor:                {profit_factor:.4f}")
print(f"Net Annualized Sharpe Ratio:      {annualized_sharpe:.4f}")
print(f"Net Annualized Sortino Ratio:     {annualized_sortino:.4f}")
print("-" * 85)
print(f"Total Spread Costs Paid:          ${total_spread_paid:,.2f}")
print(f"Total Slippage Friction Paid:     ${total_slippage_paid:,.2f}")
print(f"Total Friction Absorbed:          ${total_friction_paid:,.2f}")
print("-" * 85)
print("INDIVIDUAL STRATEGY SIGNAL VOLUME:")
for strat_name, sig_list in strategy_trades.items():
    entries = [s for s in sig_list if s["direction"] != 0]
    exits = [s for s in sig_list if s["direction"] == 0]
    print(f"  • {strat_name:<20}: {len(entries):,d} Entry Signals | {len(exits):,d} Exit Signals")
print("=" * 85)
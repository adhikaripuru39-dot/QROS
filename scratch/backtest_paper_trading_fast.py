"""High-Performance Backtest of the 3 Paper Trading Strategies on 6.15-Year Data."""

import os
import sys
import pandas as pd
import numpy as np
import time

sys.path.insert(0, os.path.abspath("."))

from paper_trading.orchestrator import PaperTradingOrchestrator
from paper_trading.events import BarEvent, SignalEvent, ExecutionFillEvent
from qros.stats.moments import calculate_sharpe_ratio, calculate_sortino_ratio, calculate_profit_factor, calculate_effective_sample_size, calculate_t_stat

print("=" * 85)
print("  QROS FAST BACKTEST: 3-STRATEGY ENSEMBLE REPLAY (6.15 YEARS)  ")
print("=" * 85)

# 1. Load full 6.15-year dataset (M5 bars)
t1_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier1_eda.parquet")
t2_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier2_train.parquet")
t3_m5 = pd.read_parquet("data/processed/xauusd/xauusd_m5_v4.0.0_tier3_val.parquet")
t4_m5 = pd.read_parquet("data/vault/xauusd/qros-data-xauusd-m5-v4.0.0_tier4_oos.parquet")
df_m5 = pd.concat([t1_m5, t2_m5, t3_m5, t4_m5]).sort_index()

# Precompute H1 bars once for instantaneous indicator lookup
t1_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier1_eda.parquet")
t2_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier2_train.parquet")
t3_h1 = pd.read_parquet("data/processed/xauusd/xauusd_h1_v4.0.0_tier3_val.parquet")
t4_h1 = pd.read_parquet("data/vault/xauusd/qros-data-xauusd-h1-v4.0.0_tier4_oos.parquet")
df_h1_full = pd.concat([t1_h1, t2_h1, t3_h1, t4_h1]).sort_index()

df_h1_full["tr"] = np.maximum(
    df_h1_full["high"] - df_h1_full["low"],
    np.maximum((df_h1_full["high"] - df_h1_full["close"].shift(1)).abs(), (df_h1_full["low"] - df_h1_full["close"].shift(1)).abs())
)
df_h1_full["atr14"] = df_h1_full["tr"].rolling(14).mean()
df_h1_full["ema50"] = df_h1_full["close"].ewm(span=50, adjust=False).mean()

print(f"Loaded {len(df_m5):,d} M5 bars and {len(df_h1_full):,d} H1 bars ({df_m5.index[0]} to {df_m5.index[-1]}).")

# 2. Run simulation through paper_trading orchestrator
orchestrator = PaperTradingOrchestrator(symbol="XAUUSD")

fills_record = []
balance_timeline = []
strategy_trades = {"STRAT_OB_ALLDAY": [], "STRAT_OB_TREND": [], "STRAT_FVG_OVERLAP": []}

start_t = time.time()
print("\nReplaying M5 bars through paper trading micro-engines...")

last_h1_time = None
current_h1_df = pd.DataFrame()
h1_times = df_h1_full.index

for idx, row in df_m5.iterrows():
    ts_str = idx.isoformat()
    open_p = float(row["open"])
    high_p = float(row["high"])
    low_p = float(row["low"])
    close_p = float(row["close"])
    volume = float(row.get("tick_volume", row.get("volume", 100.0)))
    spread_pts = float(row.get("spread_pts", 20.0))

    bar = orchestrator.market_data.process_m5_bar(ts_str, open_p, high_p, low_p, close_p, volume, spread_pts)

    # Point-in-time H1 slice: only bars up to the last completed H1 hour
    current_hour_floor = idx.floor("1h")
    if current_hour_floor != last_h1_time:
        last_h1_time = current_hour_floor
        # Cut H1 dataframe up to completed hour strictly point-in-time
        current_h1_df = df_h1_full[df_h1_full.index < current_hour_floor]

    if len(current_h1_df) < 3:
        continue

    sig1 = orchestrator.strat_ob_allday.evaluate_bar(bar, current_h1_df)
    sig2 = orchestrator.strat_ob_trend.evaluate_bar(bar, current_h1_df)
    sig3 = orchestrator.strat_fvg.evaluate_bar(bar, current_h1_df)

    for sig in [sig1, sig2, sig3]:
        if sig is None:
            continue

        strategy_trades[sig.strategy_id].append({
            "timestamp": sig.timestamp,
            "direction": sig.direction,
            "price": sig.target_price,
            "sl": sig.stop_loss,
            "tp": sig.take_profit,
        })

        alloc = orchestrator.allocator.on_signal(sig)
        net_order = orchestrator.netting.process_allocation(alloc)
        if net_order is None:
            continue

        approved = orchestrator.risk_guard.validate_order(net_order, current_spread_pts=bar.spread_pts)
        if approved.is_approved:
            fill = orchestrator.execution.execute_order(approved, current_market_price=bar.close)
            if fill:
                orchestrator.netting.on_fill(fill)
                fills_record.append(fill)

    # Hourly snapshot
    if idx.minute == 0:
        balance_timeline.append({
            "timestamp": idx,
            "balance": orchestrator.execution.balance_usd,
            "equity": orchestrator.execution.equity_usd,
            "position": orchestrator.execution.current_position_lots,
        })

elapsed = time.time() - start_t
print(f"Replay completed in {elapsed:.2f} seconds.")

# 3. Analytics
df_bal = pd.DataFrame(balance_timeline).set_index("timestamp")
df_bal["hourly_return"] = df_bal["balance"].pct_change().fillna(0.0)

realized_trades = [f for f in fills_record if f.realized_pnl_usd != 0.0]
starting_balance = 100_000.0
final_balance = orchestrator.execution.balance_usd
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
print(f"Starting Virtual Balance:         ${starting_balance:,.2f}")
print(f"Final Account Balance:            ${final_balance:,.2f}")
print(f"Total Net PnL (after all costs):  +${total_net_pnl:,.2f} (+{total_return_pct:.2f}%)")
print(f"Maximum Strategy Drawdown:        {max_drawdown_pct:.2f}%")
print("-" * 85)
print(f"Total Fills Executed (Net):       {len(fills_record):,d} orders")
print(f"Total Realized Roundtrips:        {len(realized_trades):,d} closed trades")
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
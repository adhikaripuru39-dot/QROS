"""Production 24/7 Live Streamer for QROS Paper Trading with MT5 Live Order Routing."""

import os
import sys
import time
from datetime import datetime, timezone

# Ensure project root is in path
sys.path.insert(0, os.path.abspath("."))

from paper_trading.orchestrator import PaperTradingOrchestrator

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False


def run_live_paper_trading(
    symbol: str = "XAUUSD",
    poll_interval_sec: float = 2.0,
    enable_live_mt5_orders: bool = False,
    risk_pct_per_trade: float = 0.02,  # 2.0% equity risk per trade
):
    """Continuously streams live M5 bars from MT5 into the QROS micro-engine orchestrator with live order routing."""
    print("=" * 80)
    print("  QROS MULTI-STRATEGY MT5 LIVE ORDER ROUTING ENGINE (VPS PRODUCTION)  ")
    print("=" * 80)

    if not MT5_AVAILABLE:
        print("[ERROR] 'MetaTrader5' Python package not installed. Run: pip install MetaTrader5")
        return

    if not mt5.initialize():
        print(f"[ERROR] MT5 Initialization failed: {mt5.last_error()}")
        print("Ensure MT5 terminal is open and logged into your Demo/Paper account.")
        return

    account_info = mt5.account_info()
    if enable_live_mt5_orders:
        if os.getenv("QROS_ENABLE_LIVE_MT5_ORDERS") != "YES":
            print("[SAFE STOP] Physical MT5 routing requires QROS_ENABLE_LIVE_MT5_ORDERS=YES.")
            mt5.shutdown()
            return
        demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
        if account_info is None or (demo_mode is not None and account_info.trade_mode != demo_mode):
            print("[SAFE STOP] Physical routing is limited to a confirmed demo account.")
            mt5.shutdown()
            return
    if account_info is not None:
        print(f"[OK] Connected to MT5 Account: {account_info.login} ({account_info.server})")
        print(f"[OK] Balance: ${account_info.balance:,.2f} | Leverage: 1:{account_info.leverage}")
        print(f"[OK] Dynamic Sizing: {risk_pct_per_trade * 100:.1f}% Equity Risk Per Trade")
        print(f"[OK] Live Order Routing: {'ENABLED (Physical Orders Sent to MT5)' if enable_live_mt5_orders else 'SIMULATION ONLY'}")
    else:
        print("[WARN] Connected to terminal, but account details unavailable.")

    # Initialize micro-engine orchestrator with MT5 live order routing & 2% dynamic risk
    orchestrator = PaperTradingOrchestrator(
        symbol=symbol,
        enable_mt5_live_routing=enable_live_mt5_orders,
        risk_pct_per_trade=risk_pct_per_trade,
    )

    # Warm up rolling market data engine with existing MT5 history (e.g. last 600 bars = 50 hours)
    print(f"[INIT] Warming up historical M5 buffer for {symbol}...")
    warmup_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 1, 600)
    if warmup_rates is not None and len(warmup_rates) > 0:
        for b in warmup_rates:
            orchestrator.market_data.process_m5_bar(
                timestamp=datetime.fromtimestamp(b["time"], tz=timezone.utc).isoformat(),
                open_p=float(b["open"]),
                high_p=float(b["high"]),
                low_p=float(b["low"]),
                close_p=float(b["close"]),
                volume=float(b["tick_volume"]),
                spread_pts=float(b["spread"]),
            )
        df_h1_warmup = orchestrator.market_data.get_h1_dataframe()
        print(f"[OK] Warmed up with {len(warmup_rates)} M5 bars ({len(df_h1_warmup)} H1 bars constructed).")
        # Pre-populate active order blocks and fair value gaps from warmup history
        orchestrator.strat_ob_allday.update_order_blocks(df_h1_warmup)
        orchestrator.strat_ob_trend.update_order_blocks(df_h1_warmup)
        orchestrator.strat_fvg.update_fvgs(df_h1_warmup)
        print(f"[OK] Active Order Blocks ready: Bull={len(orchestrator.strat_ob_allday.active_bull_obs)}, Bear={len(orchestrator.strat_ob_allday.active_bear_obs)}")
    else:
        print("[WARN] Could not pre-fetch historical M5 bars for warmup.")

    last_processed_bar_time = None
    heartbeat_counter = 0

    print(f"[OK] Micro-engine pipeline initialized for {symbol}. Monitoring M5 bars...\n")

    while True:
        try:
            # Fetch the most recently closed M5 bar (index 1 is closed, index 0 is currently forming)
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 1, 1)
            
            if rates is not None and len(rates) > 0:
                latest_bar = rates[0]
                bar_time = datetime.fromtimestamp(latest_bar["time"], tz=timezone.utc).isoformat()

                if bar_time != last_processed_bar_time:
                    last_processed_bar_time = bar_time

                    open_p = float(latest_bar["open"])
                    high_p = float(latest_bar["high"])
                    low_p = float(latest_bar["low"])
                    close_p = float(latest_bar["close"])
                    volume = float(latest_bar["tick_volume"])
                    spread_pts = float(latest_bar["spread"])

                    # Route bar through the 7 single-responsibility micro-engines
                    orchestrator.on_m5_bar(
                        timestamp=bar_time,
                        open_p=open_p,
                        high_p=high_p,
                        low_p=low_p,
                        close_p=close_p,
                        volume=volume,
                        spread_pts=spread_pts,
                    )

                    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}] "
                          f"M5 CLOSED: {bar_time} | O: {open_p:.2f} H: {high_p:.2f} L: {low_p:.2f} C: {close_p:.2f} "
                          f"| Spread: {spread_pts:.0f} pts | Balance: ${orchestrator.execution.balance_usd:,.2f} "
                          f"| Net Position: {orchestrator.execution.current_position_lots:+.2f} lots")

            # Heartbeat print every 60 seconds
            heartbeat_counter += 1
            if heartbeat_counter >= int(60 / poll_interval_sec):
                heartbeat_counter = 0
                tick = mt5.symbol_info_tick(symbol)
                bid = tick.bid if tick else 0.0
                ask = tick.ask if tick else 0.0
                print(f"[HEARTBEAT] Engine Active | Current Bid: {bid:.2f} Ask: {ask:.2f} | Open Lots: {orchestrator.execution.current_position_lots:+.2f}")

            time.sleep(poll_interval_sec)

        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Paper trading daemon gracefully stopped by user.")
            mt5.shutdown()
            break
        except Exception as e:
            print(f"[EXCEPTION] Loop error: {e}. Auto-recovering in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    run_live_paper_trading(symbol="XAUUSD", enable_live_mt5_orders=False)

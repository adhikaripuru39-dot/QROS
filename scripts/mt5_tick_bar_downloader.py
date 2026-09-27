"""Pipeline to download up to 7 years of Tick Data (Bid, Ask, Last, Volume, Flags) 
and Multi-Timeframe OHLC Bars (M1, M5, H1, D1) directly from MetaTrader 5 terminal."""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 package is required. Install via: pip install MetaTrader5")
    sys.exit(1)


def connect_mt5(terminal_path: Optional[str] = None) -> bool:
    """Connect to MetaTrader 5 terminal."""
    init_kwargs = {}
    if terminal_path:
        init_kwargs["path"] = terminal_path

    if not mt5.initialize(**init_kwargs):
        print(f"[ERROR] Failed to initialize MT5: {mt5.last_error()}")
        return False

    terminal_info = mt5.terminal_info()
    account_info = mt5.account_info()
    print("=== MetaTrader 5 Connected ===")
    if terminal_info:
        print(f"Company/Broker : {terminal_info.company}")
        print(f"Terminal Name  : {terminal_info.name} (Build {terminal_info.build})")
        print(f"Data Path      : {terminal_info.data_path}")
    if account_info:
        print(f"Account Login  : {account_info.login} ({account_info.currency})")
        print(f"Server         : {account_info.server}")
    print("================================")
    return True


def download_ticks_7years(
    symbol: str = "XAUUSD",
    years: int = 7,
    output_dir: str = "data/raw/ticks",
    chunk_days: int = 30,
) -> None:
    """Download up to 7 years of tick data (Bid, Ask, Last, Volume, Flags) using sliding windows."""
    print(f"\n[INFO] Starting {years}-Year Tick Ingestion for {symbol}...")
    if not mt5.symbol_select(symbol, True):
        print(f"[ERROR] Symbol {symbol} not found or cannot be selected.")
        return

    sym_dir = os.path.join(output_dir, symbol.lower())
    os.makedirs(sym_dir, exist_ok=True)

    dt_end = datetime.now()
    dt_start = dt_end - timedelta(days=years * 365)

    current_start = dt_start
    total_ticks = 0

    print(f"[INFO] Fetching ticks from {dt_start.strftime('%Y-%m-%d')} to {dt_end.strftime('%Y-%m-%d')} in {chunk_days}-day batches...")

    while current_start < dt_end:
        current_end = min(current_start + timedelta(days=chunk_days), dt_end)
        
        # copy_ticks_range extracts: time, bid, ask, last, volume, time_msc, flags, volume_real
        ticks = mt5.copy_ticks_range(symbol, current_start, current_end, mt5.COPY_TICKS_ALL)
        
        if ticks is not None and len(ticks) > 0:
            df_chunk = pd.DataFrame(ticks)
            # Use microsecond/millisecond resolution timestamp
            df_chunk["timestamp"] = pd.to_datetime(df_chunk["time_msc"], unit="ms", utc=True)
            df_chunk.set_index("timestamp", inplace=True)
            df_chunk.drop(columns=["time", "time_msc"], inplace=True, errors="ignore")
            
            chunk_file = os.path.join(
                sym_dir, 
                f"{symbol.lower()}_ticks_{current_start.strftime('%Y%m%d')}_{current_end.strftime('%Y%m%d')}.parquet"
            )
            df_chunk.to_parquet(chunk_file, compression="snappy")
            total_ticks += len(df_chunk)
            print(f"  -> Saved {len(df_chunk):>8} ticks for {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')} | Cumulative: {total_ticks:,}")
        
        current_start = current_end

    print(f"[SUCCESS] Downloaded a total of {total_ticks:,} ticks for {symbol}.")


def download_bars_7years(
    symbol: str = "XAUUSD",
    timeframes: Optional[List[str]] = None,
    years: int = 7,
    output_dir: str = "data/raw/bars",
) -> None:
    """Download OHLC bar data (Open, High, Low, Close, Tick Volume, Spread, Real Volume) for 7 years."""
    if timeframes is None:
        timeframes = ["M1", "M5", "M15", "H1", "D1"]

    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
    }

    sym_dir = os.path.join(output_dir, symbol.lower())
    os.makedirs(sym_dir, exist_ok=True)

    dt_end = datetime.now()
    dt_start = dt_end - timedelta(days=years * 365)

    for tf in timeframes:
        tf_enum = tf_map.get(tf.upper())
        if tf_enum is None:
            print(f"[WARN] Unknown timeframe {tf}. Skipping.")
            continue

        print(f"\n[INFO] Downloading {symbol} {tf} Bars ({dt_start.strftime('%Y-%m-%d')} to {dt_end.strftime('%Y-%m-%d')})...")
        rates = mt5.copy_rates_range(symbol, tf_enum, dt_start, dt_end)

        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
            df.set_index("timestamp", inplace=True)
            df.drop(columns=["time"], inplace=True, errors="ignore")
            df.rename(columns={"spread": "spread_pts"}, inplace=True)

            parquet_path = os.path.join(sym_dir, f"{symbol.lower()}_{tf.lower()}_7y.parquet")
            csv_path = os.path.join(sym_dir, f"{symbol.lower()}_{tf.lower()}_7y.csv")

            df.to_parquet(parquet_path, compression="snappy")
            df.to_csv(csv_path)

            print(f"[SUCCESS] {symbol} {tf}: {len(df):,} bars saved to:")
            print(f"  - Parquet: {parquet_path}")
            print(f"  - CSV:     {csv_path}")
            print(f"  - Date Range: {df.index[0]} to {df.index[-1]}")
        else:
            print(f"[WARN] No bar data returned for {symbol} {tf}. Broker error: {mt5.last_error()}")


def main():
    symbol = "XAUUSD"
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ticks_dir = os.path.join(base_dir, "data", "raw", "ticks")
    bars_dir = os.path.join(base_dir, "data", "raw", "bars")

    if not connect_mt5():
        return

    try:
        # 1. Download multi-timeframe OHLC bars (M1, M5, M15, H1, D1) for 7 years
        download_bars_7years(symbol=symbol, timeframes=["M1", "M5", "M15", "H1", "D1"], years=7, output_dir=bars_dir)

        # 2. Download Tick data with Bid, Ask, Last, Volume, Flags for 7 years (chunked)
        download_ticks_7years(symbol=symbol, years=7, output_dir=ticks_dir, chunk_days=30)

    finally:
        mt5.shutdown()
        print("\n=== MT5 Ingestion Session Completed ===")


if __name__ == "__main__":
    main()

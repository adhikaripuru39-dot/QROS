"""MetaTrader 5 institutional broker feed ingestion adapter."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
import pandas as pd
from qros.data.adapters.base import BaseIngestionAdapter


class MT5IngestionAdapter(BaseIngestionAdapter):
    """Ingests historical market rates directly from MetaTrader 5 terminal."""

    TIMEFRAME_MAP = {
        "M1": 1,  # mt5.TIMEFRAME_M1
        "M5": 5,  # mt5.TIMEFRAME_M5
        "M15": 15,  # mt5.TIMEFRAME_M15
        "M30": 30,  # mt5.TIMEFRAME_M30
        "H1": 16385,  # mt5.TIMEFRAME_H1
        "H4": 16388,  # mt5.TIMEFRAME_H4
        "D1": 16408,  # mt5.TIMEFRAME_D1
        "W1": 32769,  # mt5.TIMEFRAME_W1
    }

    def __init__(self, terminal_path: Optional[str] = None) -> None:
        self.terminal_path = terminal_path or r"C:\Program Files\MetaTrader 5\terminal64.exe"
        self._mt5 = None

    def _get_mt5(self):
        if self._mt5 is None:
            import MetaTrader5 as mt5

            self._mt5 = mt5
        return self._mt5

    def is_available(self) -> bool:
        """Check if MT5 terminal can be initialized."""
        try:
            mt5 = self._get_mt5()
            res = mt5.initialize(path=self.terminal_path)
            if res:
                mt5.shutdown()
                return True
            return False
        except Exception:
            return False

    def fetch_data(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "M5",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count: Optional[int] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch historical bars from MT5."""
        mt5 = self._get_mt5()
        if not mt5.initialize(path=self.terminal_path):
            err = mt5.last_error()
            raise ConnectionError(f"Failed to initialize MetaTrader 5 terminal: {err}")

        try:
            tf_upper = timeframe.upper().strip()
            if tf_upper not in self.TIMEFRAME_MAP:
                raise ValueError(
                    f"Unsupported timeframe '{timeframe}'. Must be one of {list(self.TIMEFRAME_MAP.keys())}"
                )
            tf_enum = self.TIMEFRAME_MAP[tf_upper]

            # Ensure symbol is selected
            mt5.symbol_select(symbol, True)
            sym_info = mt5.symbol_info(symbol)
            if sym_info is None:
                raise ValueError(f"Symbol '{symbol}' not found in MetaTrader 5 symbols.")

            df_list = []
            if start_date and end_date:
                dt_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                dt_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                dt_start_naive = dt_start.replace(tzinfo=None)
                dt_end_naive = dt_end.replace(tzinfo=None)
                rates = mt5.copy_rates_range(symbol, tf_enum, dt_start_naive, dt_end_naive)
                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
                    df_list.append(df)
            else:
                target_count = count if (count is not None and count > 0) else 10000
                chunk_size = 9000
                dt_cursor = datetime.now()
                remaining = target_count

                while remaining > 0:
                    fetch_size = min(chunk_size, remaining)
                    rates = mt5.copy_rates_from(symbol, tf_enum, dt_cursor, fetch_size)
                    
                    if rates is None or len(rates) == 0:
                        break  # Broker limit reached or no more data

                    df_chunk = pd.DataFrame(rates)
                    df_chunk["timestamp"] = pd.to_datetime(df_chunk["time"], unit="s", utc=True)
                    df_list.append(df_chunk)

                    # Update cursor to the oldest timestamp in this chunk
                    oldest_dt = df_chunk["timestamp"].min().replace(tzinfo=None)
                    if dt_cursor <= oldest_dt:
                        break  # Stuck or reached broker data boundary, cannot paginate further backwards
                    
                    dt_cursor = oldest_dt
                    remaining -= len(df_chunk)

            if not df_list:
                err = mt5.last_error()
                raise RuntimeError(
                    f"No rates returned for {symbol} ({timeframe}). MT5 error: {err}"
                )

            # Combine, deduplicate at boundaries, and sort chronologically
            df = pd.concat(df_list, ignore_index=True)
            df.drop_duplicates(subset=["time"], inplace=True)
            df.sort_values("time", inplace=True)
            df.set_index("timestamp", inplace=True)
            df.drop(columns=["time"], inplace=True, errors="ignore")

            # Standardize columns
            col_rename = {
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "tick_volume": "tick_volume",
                "spread": "spread_pts",
                "real_volume": "real_volume",
            }
            df.rename(columns=col_rename, inplace=True)

            term_info = mt5.terminal_info()
            metadata = {
                "source": "MetaTrader5",
                "symbol": symbol,
                "timeframe": timeframe,
                "broker": term_info.company if term_info else "Unknown",
                "terminal_build": term_info.build if term_info else 0,
                "digits": sym_info.digits,
                "point_size": sym_info.point,
                "total_bars_fetched": len(df),
                "acquisition_time_utc": datetime.now(timezone.utc).isoformat(),
            }

            return df, metadata

        finally:
            mt5.shutdown()

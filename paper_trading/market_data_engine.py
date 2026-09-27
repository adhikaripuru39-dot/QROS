"""MarketDataEngine: Single Responsibility = Ingest & Resample Market Bars."""

from collections import deque
from typing import List, Optional
import pandas as pd
import numpy as np
from paper_trading.events import BarEvent


class MarketDataEngine:
    """Maintains rolling historical bar buffers and emits point-in-time BarEvents."""

    def __init__(self, symbol: str = "XAUUSD", max_buffer_bars: int = 1500) -> None:
        self.symbol = symbol
        self.m5_history: deque = deque(maxlen=max_buffer_bars)

    def process_m5_bar(
        self,
        timestamp: str,
        open_p: float,
        high_p: float,
        low_p: float,
        close_p: float,
        volume: float,
        spread_pts: float = 20.0,
    ) -> BarEvent:
        bar = BarEvent(
            symbol=self.symbol,
            timeframe="M5",
            timestamp=timestamp,
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=volume,
            spread_pts=spread_pts,
        )
        self.m5_history.append(bar)
        return bar

    def get_h1_dataframe(self) -> pd.DataFrame:
        """Resample rolling M5 buffer into H1 OHLCV DataFrame with ATR and EMA."""
        if len(self.m5_history) == 0:
            return pd.DataFrame()

        records = [
            {
                "timestamp": pd.to_datetime(b.timestamp),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in self.m5_history
        ]
        df = pd.DataFrame(records).set_index("timestamp").sort_index()
        df_h1 = df.resample("1h").agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
            bar_count=("open", "count"),
        ).dropna(subset=["open"])

        # Exclude incomplete currently-forming hour (must have 12 closed M5 bars unless it is historical boundary)
        if len(df_h1) > 0:
            if df_h1.iloc[-1]["bar_count"] < 12 and len(df_h1) > 1:
                df_h1 = df_h1.iloc[:-1]
            df_h1 = df_h1.drop(columns=["bar_count"])

        if len(df_h1) > 0:
            df_h1["tr"] = np.maximum(
                df_h1["high"] - df_h1["low"],
                np.maximum(
                    (df_h1["high"] - df_h1["close"].shift(1)).abs(),
                    (df_h1["low"] - df_h1["close"].shift(1)).abs(),
                ),
            )
            df_h1["atr14"] = df_h1["tr"].rolling(14).mean()
            df_h1["ema50"] = df_h1["close"].ewm(span=50, adjust=False).mean()

        return df_h1

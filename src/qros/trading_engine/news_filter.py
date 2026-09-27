"""MT5 Economic News Scraping and Filtering for Backtesting & Live Trading."""

import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Optional

class MT5NewsFilter:
    """
    Scrapes economic news (from MT5 or CSV fallback) and ensures trades
    are not opened within restricted time windows (e.g. 5 mins before/after High Impact news).
    """

    def __init__(self,
                 csv_fallback_path: Optional[str] = None,
                 mins_before_block: int = 5,
                 mins_after_block: int = 5,
                 impact_levels_to_block: list = [3]): # MT5: 0=holiday, 1=low, 2=medium, 3=high
        """
        Parameters:
        - csv_fallback_path: Path to a CSV calendar for backtesting if MT5 historical news is absent.
        - mins_before_block: Minutes before news event to block trading.
        - mins_after_block: Minutes after news event to block trading.
        - impact_levels_to_block: List of news impacts to block. Default [3] (High impact).
        """
        self.mins_before_block = timedelta(minutes=mins_before_block)
        self.mins_after_block = timedelta(minutes=mins_after_block)
        self.impact_levels_to_block = impact_levels_to_block

        self.news_df = self._load_news_data(csv_fallback_path)

    def _load_news_data(self, csv_path: Optional[str]) -> pd.DataFrame:
        """
        Loads news from MT5. If running in an environment where MT5 isn't available
        (or for deep historical backtests), falls back to CSV.
        """
        df = pd.DataFrame()
        mt5_success = False

        try:
            import MetaTrader5 as mt5
            # Assuming mt5 is already initialized by the caller or adapter
            if mt5.initialize():
                # Attempt to get news. MT5 terminal might not store deep history.
                news = mt5.news_get()
                if news is not None and len(news) > 0:
                    df = pd.DataFrame(news)
                    df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
                    # For mt5 news, we might not always have strict 'impact' fields directly in news_get() in all builds,
                    # but if we do or if it's integrated via an EA calendar, we map it.
                    # Note: standard MT5 `news_get` might just return generic news. Economic calendar is `mt5.calendar_get()`.
                    mt5_success = True
        except ImportError:
            pass

        if not mt5_success and csv_path and os.path.exists(csv_path):
            # Fallback to CSV (e.g. ForexFactory scraped data)
            df = pd.read_csv(csv_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            if 'impact' not in df.columns:
                df['impact'] = 3 # Assume all in CSV are high if not specified
        elif not mt5_success:
            # Create an empty dataframe with correct schema
            df = pd.DataFrame(columns=['timestamp', 'impact', 'currency'])

        if not df.empty:
            # Filter only impacts we care about
            if 'impact' in df.columns:
                df = df[df['impact'].isin(self.impact_levels_to_block)]
            df = df.sort_values(by='timestamp').reset_index(drop=True)

        return df

    def is_trading_allowed(self, current_time: pd.Timestamp, symbol: str = "XAUUSD") -> bool:
        """
        Checks if the current time is outside the restricted window of any high-impact news.

        Parameters:
        - current_time: pd.Timestamp (timezone aware, matching news df)
        - symbol: The asset being traded. Used to filter news by relevant currency (e.g., USD for XAUUSD).
        """
        if self.news_df.empty:
            return True # No news data means no restrictions

        # Naive implementation: for backtesting performance, we should ideally vectorize this.
        # But for an event-driven check:

        # Optionally filter by currency if that column exists
        relevant_news = self.news_df
        if 'currency' in relevant_news.columns:
            # Example: for XAUUSD, care about USD news.
            # In a real setup, parse the symbol to base/quote.
            if "USD" in symbol:
                relevant_news = relevant_news[relevant_news['currency'] == 'USD']

        # Check if current_time falls within [news_time - mins_before, news_time + mins_after]
        # using bisect or simple mask (optimized for sequential event-driven processing)

        # Get news around the current time
        window_start = current_time - self.mins_after_block
        window_end = current_time + self.mins_before_block

        # If there is any news timestamp between window_start and window_end, trading is blocked
        mask = (relevant_news['timestamp'] >= window_start) & (relevant_news['timestamp'] <= window_end)
        if mask.any():
            return False # Blocked by news

        return True

    def get_news_block_intervals(self) -> list:
        """
        Returns a list of (start_block, end_block) tuples for vectorised masking.
        """
        intervals = []
        for _, row in self.news_df.iterrows():
            start = row['timestamp'] - self.mins_before_block
            end = row['timestamp'] + self.mins_after_block
            intervals.append((start, end))
        return intervals

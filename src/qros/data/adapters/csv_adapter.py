"""Standard CSV and Parquet file ingestion adapter."""

from datetime import datetime, timezone
import os
from typing import Any, Dict, Optional, Tuple
import pandas as pd
from qros.data.adapters.base import BaseIngestionAdapter


class CSVIngestionAdapter(BaseIngestionAdapter):
    """Ingests, parses, and standardizes historical data from local CSV or Parquet files."""

    def __init__(self, data_directory: Optional[str] = None) -> None:
        self.data_directory = data_directory or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data")
        )

    def fetch_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count: Optional[int] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Look for local file matching symbol and timeframe and load it."""
        # Check for parquet first, then csv
        expected_filename_base = f"{symbol.lower()}_{timeframe.lower()}"
        file_candidates = [
            os.path.join(self.data_directory, "raw", symbol.lower(), f"{expected_filename_base}.parquet"),
            os.path.join(self.data_directory, "raw", symbol.lower(), f"{expected_filename_base}.csv"),
            os.path.join(self.data_directory, "processed", symbol.lower(), f"{expected_filename_base}.parquet"),
            os.path.join(self.data_directory, "processed", symbol.lower(), f"{expected_filename_base}.csv"),
        ]

        found_path = None
        for path in file_candidates:
            if os.path.exists(path):
                found_path = path
                break

        if not found_path:
            raise FileNotFoundError(
                f"No local data file found for {symbol} ({timeframe}) in {self.data_directory}. "
                f"Looked for: {file_candidates}"
            )

        return self.load_file(found_path, symbol=symbol, timeframe=timeframe)

    def load_file(
        self,
        filepath: str,
        symbol: str = "UNKNOWN",
        timeframe: str = "UNKNOWN",
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Load and normalize a CSV or Parquet file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        if filepath.endswith(".parquet"):
            df = pd.read_parquet(filepath)
        else:
            # Auto-detect separator
            df = pd.read_csv(filepath)

        # Normalize columns to lowercase
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Identify timestamp column
        ts_candidates = ["timestamp", "time", "date", "datetime", "gmt time", "dtedate"]
        ts_col = next((c for c in ts_candidates if c in df.columns), None)

        if ts_col:
            df["timestamp"] = pd.to_datetime(df[ts_col], utc=True)
            df.set_index("timestamp", inplace=True)
            if ts_col != "timestamp":
                df.drop(columns=[ts_col], inplace=True, errors="ignore")
        elif not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True)

        if "spread_pts" not in df.columns:
            if "spread" in df.columns:
                df.rename(columns={"spread": "spread_pts"}, inplace=True)
            else:
                df["spread_pts"] = 20.0  # Default nominal spread

        if "tick_volume" not in df.columns:
            if "volume" in df.columns:
                df.rename(columns={"volume": "tick_volume"}, inplace=True)
            else:
                df["tick_volume"] = 100

        metadata = {
            "source": "LocalFile",
            "file_path": os.path.abspath(filepath),
            "symbol": symbol,
            "timeframe": timeframe,
            "total_rows_read": len(df),
            "file_size_bytes": os.path.getsize(filepath),
            "acquisition_time_utc": datetime.now(timezone.utc).isoformat(),
        }

        return df, metadata

"""Abstract Base Class for QROS Data Ingestion Adapters."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
import pandas as pd


class BaseIngestionAdapter(ABC):
    """Base interface for all market data ingestion sources."""

    @abstractmethod
    def fetch_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        count: Optional[int] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch raw market observations and source metadata.

        Parameters
        ----------
        symbol : str
            Target asset symbol (e.g. 'XAUUSD').
        timeframe : str
            Bar interval (e.g. 'M1', 'M5', 'H1', 'D1').
        start_date : Optional[str]
            Start date string (ISO format).
        end_date : Optional[str]
            End date string (ISO format).
        count : Optional[int]
            Max bar count to fetch if start/end dates are not provided.

        Returns
        -------
        Tuple[pd.DataFrame, Dict[str, Any]]
            Raw DataFrame and source provenance dictionary.
        """
        pass

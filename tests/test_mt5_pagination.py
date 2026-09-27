import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pandas as pd
from qros.data.adapters.mt5_adapter import MT5IngestionAdapter

class TestMT5Pagination(unittest.TestCase):
    @patch("qros.data.adapters.mt5_adapter.MT5IngestionAdapter._get_mt5")
    def test_fetch_data_pagination(self, mock_get_mt5):
        mock_mt5 = MagicMock()
        mock_get_mt5.return_value = mock_mt5
        
        mock_mt5.initialize.return_value = True
        mock_mt5.symbol_info.return_value = MagicMock(digits=5, point=0.01)
        mock_mt5.terminal_info.return_value = MagicMock(company="Test", build=123)
        
        # Simulate returning 3 chunks of data (9000, 9000, 2000) for a target of 20000
        def side_effect(symbol, timeframe, dt, count):
            base_time = int(datetime(2023, 1, 1).timestamp())
            if count == 9000:
                if dt.year >= 2026:
                    rates = [{"time": base_time + i * 3600, "open": 1, "high": 2, "low": 0, "close": 1, "tick_volume": 10, "spread": 2, "real_volume": 0} for i in range(9000, 18000)]
                else:
                    rates = [{"time": base_time + i * 3600, "open": 1, "high": 2, "low": 0, "close": 1, "tick_volume": 10, "spread": 2, "real_volume": 0} for i in range(0, 9000)]
            else:
                rates = [{"time": base_time - i * 3600, "open": 1, "high": 2, "low": 0, "close": 1, "tick_volume": 10, "spread": 2, "real_volume": 0} for i in range(2000, 0, -1)]
            return tuple(rates)

        mock_mt5.copy_rates_from.side_effect = side_effect
        
        adapter = MT5IngestionAdapter()
        df, meta = adapter.fetch_data("XAUUSD", "H1", count=20000)
        
        self.assertEqual(len(df), 20000)
        self.assertEqual(meta["total_bars_fetched"], 20000)
        self.assertEqual(mock_mt5.copy_rates_from.call_count, 3)

if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import pandas as pd

from utils.market_api import StockDataFetcher

class TestStockDataFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = StockDataFetcher()
        self.test_symbol = "AAPL"
        self.start_date = "2026-08-01"
        self.end_date = "2026-09-01"
        self.sample_data = pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0],
                "High": [101.0, 102.0, 103.0],
                "Low": [99.0, 100.0, 101.0],
                "Close": [100.5, 101.5, 102.5],
                "Volume": [1000, 1100, 1200],
            },
            index=pd.date_range(self.start_date, periods=3, freq="D"),
        )
        
    @patch("utils.market_api.yf.Ticker")
    def test_fetch_stock_data(self, ticker):
        ticker.return_value.history.return_value = self.sample_data
        df = self.fetcher.fetch_stock_data(self.test_symbol, self.start_date, self.end_date)
        
        # Check if data is not empty
        self.assertFalse(df.empty)
        
        # Check if required columns exist
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            self.assertIn(col, df.columns)
            
    @patch("utils.market_api.yf.Ticker")
    def test_get_stock_info(self, ticker):
        ticker.return_value.info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
        }
        info = self.fetcher.get_stock_info(self.test_symbol)
        
        # Check if basic info is present
        self.assertIsNotNone(info['name'])
        self.assertIsNotNone(info['sector'])
        
    @patch("utils.market_api.yf.Ticker")
    def test_fallback_when_yfinance_returns_no_rows(self, ticker):
        ticker.return_value.history.return_value = pd.DataFrame()
        with patch.object(self.fetcher, "_fetch_chart_data", return_value=self.sample_data) as fallback:
            df = self.fetcher.fetch_stock_data(self.test_symbol, self.start_date, self.end_date)

        fallback.assert_called_once_with(self.test_symbol, self.start_date, self.end_date)
        self.assertEqual(len(df), 3)

    @patch("utils.market_api.yf.Ticker")
    def test_invalid_symbol(self, ticker):
        ticker.return_value.history.return_value = pd.DataFrame()
        with patch.object(self.fetcher, "_fetch_chart_data", side_effect=ValueError("provider error")):
            with self.assertRaises(ValueError):
                self.fetcher.fetch_stock_data(
                    "INVALID_SYMBOL",
                    self.start_date,
                    self.end_date,
                )

if __name__ == '__main__':
    unittest.main()
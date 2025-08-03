import unittest
from utils.market_api import StockDataFetcher
from datetime import datetime, timedelta

class TestStockDataFetcher(unittest.TestCase):
    def setUp(self):
        self.fetcher = StockDataFetcher()
        self.test_symbol = "AAPL"
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
    def test_fetch_stock_data(self):
        df = self.fetcher.fetch_stock_data(
            self.test_symbol,
            self.start_date,
            self.end_date
        )
        
        # Check if data is not empty
        self.assertFalse(df.empty)
        
        # Check if required columns exist
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            self.assertIn(col, df.columns)
            
    def test_get_stock_info(self):
        info = self.fetcher.get_stock_info(self.test_symbol)
        
        # Check if basic info is present
        self.assertIsNotNone(info['name'])
        self.assertIsNotNone(info['sector'])
        
    def test_invalid_symbol(self):
        with self.assertRaises(Exception):
            self.fetcher.fetch_stock_data(
                "INVALID_SYMBOL",
                self.start_date,
                self.end_date
            )

if __name__ == '__main__':
    unittest.main()
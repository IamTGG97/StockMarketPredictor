import yfinance as yf
import pandas as pd
import logging
from datetime import datetime

class StockDataFetcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def fetch_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch stock data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                self.logger.error(f"No data found for {symbol}")
                raise ValueError(f"No data available for {symbol}")
                
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching {symbol}: {str(e)}")
            raise

    def get_stock_info(self, symbol: str) -> dict:
        """Get basic information about a stock"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'currency': info.get('currency', 'USD'),
                'market_cap': info.get('marketCap', None),
                'country': info.get('country', '')
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching info for {symbol}: {str(e)}")
            raise
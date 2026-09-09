import json
import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Stock symbol cannot be empty")

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)

            if not df.empty:
                return df

            self.logger.warning("yfinance returned no rows for %s; trying Yahoo chart API", symbol)
            return self._fetch_chart_data(symbol, start_date, end_date)
            
        except Exception as e:
            self.logger.warning("yfinance failed for %s: %s; trying Yahoo chart API", symbol, e)
            try:
                return self._fetch_chart_data(symbol, start_date, end_date)
            except Exception:
                self.logger.error("No data found for %s", symbol)
                raise ValueError(f"No data available for {symbol}") from e

    def _fetch_chart_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        query = urlencode({
            "period1": int(start.timestamp()),
            "period2": int(end.timestamp()),
            "interval": "1d",
            "events": "history",
        })
        request = Request(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}",
            headers={"User-Agent": "StockMarketPredictor/1.0"},
        )
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)

        result = payload.get("chart", {}).get("result")
        if not result:
            raise ValueError(f"No data available for {symbol}")
        chart = result[0]
        quote = chart.get("indicators", {}).get("quote", [{}])[0]
        timestamps = chart.get("timestamp", [])
        frame = pd.DataFrame(quote, index=pd.to_datetime(timestamps, unit="s", utc=True))
        frame.index.name = "Date"
        frame = frame.dropna(subset=["close"])
        frame = frame.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        if frame.empty:
            raise ValueError(f"No data available for {symbol}")
        return frame

    def fetch_stock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Backward-compatible name used by the original project tests."""
        return self.fetch_data(symbol, start_date, end_date)

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
            self.logger.warning("Stock metadata unavailable for %s: %s", symbol, e)
            return {
                'name': symbol.upper(),
                'sector': '',
                'industry': '',
                'currency': 'USD',
                'market_cap': None,
                'country': ''
            }
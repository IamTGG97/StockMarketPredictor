import unittest

import pandas as pd

from utils.data_processor import forecast_prices, prepare_price_data


class TestDataProcessor(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2026-08-03", periods=5, freq="D")
        self.data = pd.DataFrame({"Close": [100, 101, 102, 103, 104]}, index=dates)

    def test_prepare_price_data_normalizes_dates_and_prices(self):
        prices = prepare_price_data(self.data)

        self.assertEqual(list(prices.columns), ["Date", "Close"])
        self.assertEqual(len(prices), 5)
        self.assertEqual(prices.iloc[-1]["Close"], 104)

    def test_prepare_price_data_rejects_missing_close_column(self):
        with self.assertRaises(ValueError):
            prepare_price_data(pd.DataFrame({"Open": [1]}))

    def test_forecast_prices_returns_requested_trading_days(self):
        result = forecast_prices(self.data, days=3)

        self.assertEqual(result["last_close"], 104.0)
        self.assertEqual(len(result["forecast"]), 3)
        self.assertEqual(result["forecast"][0]["price"], 105.0)
        self.assertTrue(all(point["date"] for point in result["forecast"]))

    def test_forecast_prices_rejects_invalid_horizon(self):
        with self.assertRaises(ValueError):
            forecast_prices(self.data, days=0)


if __name__ == "__main__":
    unittest.main()
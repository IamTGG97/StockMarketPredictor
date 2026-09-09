import unittest
from unittest.mock import patch

import pandas as pd

from app import app


class TestApplication(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_homepage_renders(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Stock Market Predictor", response.data)

    def test_stock_data_requires_parameters(self):
        response = self.client.get("/api/stock_data")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "Missing required parameters")

    @patch("app.fetcher.get_stock_info", return_value={"name": "Apple Inc."})
    @patch("app.fetcher.fetch_data")
    def test_stock_data_returns_history_and_prediction(self, fetch_data, get_stock_info):
        fetch_data.return_value = pd.DataFrame(
            {"Close": [100.0, 101.0, 102.0]},
            index=pd.date_range("2026-08-03", periods=3, freq="D"),
        )
        response = self.client.get(
            "/api/stock_data?symbol=AAPL&start_date=2026-08-01&end_date=2026-09-01"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["data"]), 3)
        self.assertEqual(payload["prediction"]["last_close"], 102.0)
        self.assertEqual(payload["info"]["name"], "Apple Inc.")
        get_stock_info.assert_called_once_with("AAPL")


if __name__ == "__main__":
    unittest.main()
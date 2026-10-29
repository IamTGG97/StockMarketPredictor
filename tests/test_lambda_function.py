import os
import unittest
from unittest.mock import Mock, patch

import pandas as pd

from lambda_function import lambda_handler, sqs_worker_handler


class TestLambdaFunction(unittest.TestCase):
    @patch.dict(os.environ, {"S3_BUCKET_NAME": "test-bucket"}, clear=False)
    @patch("lambda_function.S3DataStore")
    @patch("lambda_function.StockDataFetcher")
    def test_handler_fetches_and_stores_requested_history(self, fetcher_factory, store_factory):
        fetcher = fetcher_factory.return_value
        fetcher.fetch_data.return_value = pd.DataFrame(
            {"Close": [100.0, 101.0]},
            index=pd.date_range("2026-09-01", periods=2),
        )
        store = store_factory.return_value
        store.save_market_data.return_value = {
            "raw": "raw/AAPL/2026-09-08.json",
            "processed": "processed/AAPL/2026-09-08.csv",
        }

        result = lambda_handler(
            {"symbol": "aapl", "start_date": "2026-09-01", "end_date": "2026-09-08"},
            None,
        )

        fetcher.fetch_data.assert_called_once_with("aapl", "2026-09-01", "2026-09-08")
        store.save_market_data.assert_called_once_with("aapl", fetcher.fetch_data.return_value)
        self.assertEqual(result["symbol"], "AAPL")
        self.assertEqual(result["storage"]["raw"], "raw/AAPL/2026-09-08.json")

    @patch.dict(os.environ, {}, clear=True)
    def test_handler_requires_symbol_and_bucket(self):
        with self.assertRaises(ValueError):
            lambda_handler({}, None)

    @patch.dict(os.environ, {"S3_BUCKET_NAME": "test-bucket"}, clear=True)
    def test_handler_requires_bucket_configuration(self):
        with self.assertRaises(RuntimeError):
            with patch.dict(os.environ, {}, clear=True):
                lambda_handler({"symbol": "AAPL"}, None)

    @patch("lambda_function.lambda_handler")
    def test_sqs_worker_passes_single_message_to_existing_handler(self, handler):
        event = {
            "Records": [
                {
                    "body": '{"symbol":"AAPL","start_date":"2026-09-01","end_date":"2026-09-30"}'
                }
            ]
        }

        sqs_worker_handler(event, None)

        handler.assert_called_once_with(
            {
                "symbol": "AAPL",
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
            },
            None,
        )

    def test_sqs_worker_requires_single_record(self):
        with self.assertRaisesRegex(ValueError, "batch size of one"):
            sqs_worker_handler({"Records": []}, None)


if __name__ == "__main__":
    unittest.main()
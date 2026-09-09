import unittest
from datetime import date
from unittest.mock import Mock, patch

import pandas as pd

from utils.storage import S3DataStore


class TestS3DataStore(unittest.TestCase):
    @patch("utils.storage.boto3.client")
    def test_save_market_data_uploads_raw_and_processed_objects(self, client_factory):
        client = Mock()
        client_factory.return_value = client
        store = S3DataStore("test-bucket")
        data = pd.DataFrame({"Close": [100.0, 101.0]}, index=pd.date_range("2026-09-01", periods=2))

        keys = store.save_market_data("aapl", data, captured_on=date(2026, 9, 8))

        self.assertEqual(keys, {
            "raw": "raw/AAPL/2026-09-08.json",
            "processed": "processed/AAPL/2026-09-08.csv",
        })
        self.assertEqual(client.put_object.call_count, 2)
        client.put_object.assert_any_call(
            Bucket="test-bucket",
            Key="raw/AAPL/2026-09-08.json",
            Body=unittest.mock.ANY,
            ContentType="application/json",
        )
        client.put_object.assert_any_call(
            Bucket="test-bucket",
            Key="processed/AAPL/2026-09-08.csv",
            Body=unittest.mock.ANY,
            ContentType="text/csv",
        )

    @patch("utils.storage.boto3.client")
    def test_save_market_data_rejects_empty_data(self, client_factory):
        store = S3DataStore("test-bucket")

        with self.assertRaises(ValueError):
            store.save_market_data("AAPL", pd.DataFrame())


if __name__ == "__main__":
    unittest.main()
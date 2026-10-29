import json
import os
import unittest
from unittest.mock import Mock, patch

import pandas as pd

from lambda_dispatcher import lambda_handler
from utils.sp500_symbols import get_sp500_symbols


class TestLambdaDispatcher(unittest.TestCase):
    @patch.dict(os.environ, {"SQS_QUEUE_URL": "https://sqs.example/queue"}, clear=False)
    @patch("lambda_dispatcher.get_sp500_symbols")
    @patch("lambda_dispatcher.boto3.client")
    def test_handler_batches_symbols_into_sqs_messages(
        self, client_factory, symbols_factory
    ):
        symbols_factory.return_value = [f"STOCK{i}" for i in range(25)]
        sqs = client_factory.return_value
        sqs.send_message_batch.return_value = {"Successful": []}

        result = lambda_handler(
            {"start_date": "2026-09-01", "end_date": "2026-09-30"},
            None,
        )

        self.assertEqual(result, {"queued_symbols": 25})
        self.assertEqual(sqs.send_message_batch.call_count, 3)
        entries = [
            entry
            for call in sqs.send_message_batch.call_args_list
            for entry in call.kwargs["Entries"]
        ]
        self.assertEqual(len(entries), 25)
        self.assertTrue(
            all(
                len(call.kwargs["Entries"]) <= 10
                for call in sqs.send_message_batch.call_args_list
            )
        )
        self.assertEqual(
            json.loads(entries[0]["MessageBody"]),
            {
                "symbol": "STOCK0",
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
            },
        )

    @patch.dict(os.environ, {"SQS_QUEUE_URL": "https://sqs.example/queue"}, clear=False)
    @patch("lambda_dispatcher.get_sp500_symbols", return_value=["AAPL"])
    @patch("lambda_dispatcher.boto3.client")
    def test_handler_reports_partial_sqs_batch_failure(self, client_factory, _):
        client_factory.return_value.send_message_batch.return_value = {
            "Failed": [{"Id": "0", "Message": "Rejected"}]
        }

        with self.assertRaisesRegex(RuntimeError, "batch IDs: 0"):
            lambda_handler(
                {"start_date": "2026-09-01", "end_date": "2026-09-30"},
                None,
            )

    @patch.dict(os.environ, {"SQS_QUEUE_URL": "https://sqs.example/queue"}, clear=False)
    def test_handler_rejects_reversed_dates(self):
        with self.assertRaisesRegex(ValueError, "start_date"):
            lambda_handler(
                {"start_date": "2026-09-30", "end_date": "2026-09-01"},
                None,
            )

    @patch.dict(os.environ, {"SQS_QUEUE_URL": "https://sqs.example/queue"}, clear=False)
    @patch("lambda_dispatcher.get_sp500_symbols", return_value=[])
    @patch("lambda_dispatcher.boto3.client")
    def test_handler_rejects_empty_constituent_list(self, client_factory, _):
        with self.assertRaisesRegex(RuntimeError, "returned no symbols"):
            lambda_handler({}, None)
        client_factory.assert_not_called()


class TestSP500Symbols(unittest.TestCase):
    @patch("utils.sp500_symbols.urlopen")
    @patch("utils.sp500_symbols.pd.read_html")
    def test_symbols_are_normalized_and_deduplicated(self, read_html, urlopen):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b"table"
        urlopen.return_value = response
        read_html.return_value = [
            pd.DataFrame({"Symbol": ["BRK.B", "AAPL", "AAPL", None, "  MSFT  "]})
        ]

        self.assertEqual(get_sp500_symbols(), ["BRK-B", "AAPL", "MSFT"])

    @patch("utils.sp500_symbols.urlopen")
    @patch("utils.sp500_symbols.pd.read_html", return_value=[])
    def test_missing_constituent_table_is_reported(self, _, urlopen):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b"page"
        urlopen.return_value = response

        with self.assertRaisesRegex(RuntimeError, "table was not found"):
            get_sp500_symbols()


if __name__ == "__main__":
    unittest.main()

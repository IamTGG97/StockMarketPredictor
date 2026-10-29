from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any

import boto3

from utils.sp500_symbols import get_sp500_symbols


def lambda_handler(event: dict[str, Any] | None, _context: Any) -> dict[str, int]:
    """Queue one S&P 500 market-data job per symbol."""
    event = event or {}
    queue_url = os.getenv("SQS_QUEUE_URL")
    if not queue_url:
        raise RuntimeError("SQS_QUEUE_URL is not configured")

    end_date = date.fromisoformat(event.get("end_date", date.today().isoformat()))
    start_date = date.fromisoformat(
        event.get("start_date", (end_date - timedelta(days=30)).isoformat())
    )
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    symbols = get_sp500_symbols()
    if not symbols:
        raise RuntimeError("The S&P 500 constituent source returned no symbols")
    sqs = boto3.client("sqs")
    queued_count = 0

    for offset in range(0, len(symbols), 10):
        batch = symbols[offset : offset + 10]
        response = sqs.send_message_batch(
            QueueUrl=queue_url,
            Entries=[
                {
                    "Id": str(index),
                    "MessageBody": json.dumps(
                        {
                            "symbol": symbol,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat(),
                        }
                    ),
                }
                for index, symbol in enumerate(batch)
            ],
        )
        failures = response.get("Failed", [])
        if failures:
            failed_ids = ", ".join(item["Id"] for item in failures)
            raise RuntimeError(f"SQS rejected messages with batch IDs: {failed_ids}")
        queued_count += len(batch)

    return {"queued_symbols": queued_count}

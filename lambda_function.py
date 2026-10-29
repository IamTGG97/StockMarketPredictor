from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any

from utils.market_api import StockDataFetcher
from utils.storage import S3DataStore


def _event_value(event: dict[str, Any], name: str) -> str | None:
    detail = event.get("detail", {}) if isinstance(event, dict) else {}
    value = event.get(name) if isinstance(event, dict) else None
    return value or detail.get(name) or os.getenv(name.upper())


def lambda_handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    """Fetch a stock history and persist it to S3 for a scheduled invocation."""
    event = event or {}
    symbol = _event_value(event, "symbol")
    end_date = _event_value(event, "end_date") or date.today().isoformat()
    start_date = _event_value(event, "start_date")
    if not start_date:
        start_date = (date.fromisoformat(end_date) - timedelta(days=30)).isoformat()

    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not symbol:
        raise ValueError("A stock symbol is required")
    if not bucket_name:
        raise RuntimeError("S3_BUCKET_NAME is not configured")

    fetcher = StockDataFetcher()
    data = fetcher.fetch_data(symbol, start_date, end_date)
    storage = S3DataStore(
        bucket_name,
        region_name=os.getenv("AWS_REGION", "us-east-2"),
    )
    objects = storage.save_market_data(symbol, data)

    return {
        "symbol": symbol.strip().upper(),
        "start_date": start_date,
        "end_date": end_date,
        "storage": objects,
    }


def sqs_worker_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Process one SQS message; configure the event source batch size as one."""
    records = event.get("Records", [])
    if len(records) != 1:
        raise ValueError("The SQS worker requires an event batch size of one")

    payload = json.loads(records[0]["body"])
    if not isinstance(payload, dict):
        raise ValueError("The SQS message body must contain a JSON object")
    return lambda_handler(payload, context)
from __future__ import annotations

import json
from datetime import date

import boto3
import pandas as pd


class S3DataStore:
    """Store raw market responses and processed price data in one S3 bucket."""

    def __init__(self, bucket_name: str, region_name: str = "us-east-2"):
        if not bucket_name.strip():
            raise ValueError("S3 bucket name cannot be empty")
        self.bucket_name = bucket_name
        self.client = boto3.client("s3", region_name=region_name)

    def save_market_data(self, symbol: str, data: pd.DataFrame, captured_on: date | None = None) -> dict[str, str]:
        """Upload raw and processed forms of a market data frame and return their keys."""
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Stock symbol cannot be empty")
        if data.empty:
            raise ValueError("Cannot store an empty market data frame")

        captured_on = captured_on or date.today()
        date_key = captured_on.isoformat()
        raw_key = f"raw/{symbol}/{date_key}.json"
        processed_key = f"processed/{symbol}/{date_key}.csv"

        raw_payload = data.reset_index().to_json(orient="records", date_format="iso")
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=raw_key,
            Body=raw_payload.encode("utf-8"),
            ContentType="application/json",
        )
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=processed_key,
            Body=data.to_csv().encode("utf-8"),
            ContentType="text/csv",
        )
        return {"raw": raw_key, "processed": processed_key}
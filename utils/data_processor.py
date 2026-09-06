from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd


def prepare_price_data(data: pd.DataFrame) -> pd.DataFrame:
	"""Normalize provider output to the columns needed by the application."""
	if data.empty or "Close" not in data.columns:
		raise ValueError("Historical data must include a Close column")

	prices = data.copy()
	prices.index = pd.to_datetime(prices.index).tz_localize(None)
	prices = prices.reset_index().rename(columns={prices.index.name or "index": "Date"})
	prices["Close"] = pd.to_numeric(prices["Close"], errors="coerce")
	prices = prices.dropna(subset=["Close"])
	if prices.empty:
		raise ValueError("Historical data contains no valid closing prices")
	return prices[["Date", "Close"]]


def forecast_prices(data: pd.DataFrame, days: int = 5) -> dict:
	"""Forecast the next trading days with a transparent linear trend baseline."""
	if days < 1 or days > 30:
		raise ValueError("Forecast days must be between 1 and 30")

	prices = prepare_price_data(data)
	values = prices["Close"].to_numpy(dtype=float)
	window = min(len(values), 30)
	x = np.arange(window, dtype=float)
	slope, intercept = np.polyfit(x, values[-window:], 1)

	last_date = prices["Date"].iloc[-1]
	forecast = []
	date = last_date
	for offset in range(1, days + 1):
		date += timedelta(days=1)
		while date.weekday() >= 5:
			date += timedelta(days=1)
		forecast.append({
			"date": date.strftime("%Y-%m-%d"),
			"price": round(float(intercept + slope * (window - 1 + offset)), 2),
		})

	return {
		"method": "linear trend baseline",
		"last_close": round(float(values[-1]), 2),
		"trend_slope": round(float(slope), 4),
		"forecast": forecast,
	}

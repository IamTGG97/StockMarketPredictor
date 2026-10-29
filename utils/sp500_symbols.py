from __future__ import annotations

from io import BytesIO
from urllib.request import Request, urlopen

import pandas as pd


SP500_CONSTITUENTS_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def get_sp500_symbols() -> list[str]:
    request = Request(
        SP500_CONSTITUENTS_URL,
        headers={"User-Agent": "StockMarketPredictor/1.0"},
    )
    with urlopen(request, timeout=15) as response:
        tables = pd.read_html(BytesIO(response.read()), match="Symbol")

    for table in tables:
        if "Symbol" not in table.columns:
            continue

        symbols = (
            table["Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .str.replace(".", "-", regex=False)
        )
        result = list(dict.fromkeys(symbol for symbol in symbols if symbol))
        if result:
            return result

    raise RuntimeError("The S&P 500 constituent table was not found or was empty")

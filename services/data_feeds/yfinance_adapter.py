"""yfinance integration placeholder."""
from __future__ import annotations

from typing import Optional

import yfinance as yf


def fetch_history(symbol: str, period: str = "1mo", interval: str = "1d") -> Optional[object]:
    """Fetch historical data via yfinance."""
    ticker = yf.Ticker(symbol)
    return ticker.history(period=period, interval=interval)

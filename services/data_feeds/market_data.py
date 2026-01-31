"""Market data aggregation service."""
from __future__ import annotations

from typing import Optional

import pandas as pd
from loguru import logger


class MarketDataFeed:
    """Aggregates historical and real-time market data."""

    def __init__(self, config: dict) -> None:
        self.config = config

    async def connect(self) -> None:
        logger.info("Market data feed connected (stub)")

    async def disconnect(self) -> None:
        logger.info("Market data feed disconnected (stub)")

    async def get_bars(self, symbol: str, timeframe: str, limit: int = 50) -> Optional[pd.DataFrame]:
        _ = (symbol, timeframe, limit)
        return pd.DataFrame()

    async def get_current_price(self, symbol: str) -> Optional[float]:
        _ = symbol
        return None

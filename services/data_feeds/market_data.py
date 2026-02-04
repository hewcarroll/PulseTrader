"""Market data aggregation service."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Tuple

import pandas as pd
from loguru import logger


class MarketDataFeed:
    """Aggregates historical and real-time market data."""

    def __init__(self, config: dict, alpaca_client) -> None:
        """
        Initialize MarketDataFeed with AlpacaClient.
        
        Args:
            config: Configuration dictionary
            alpaca_client: AlpacaClient instance for market data retrieval
        """
        self.config = config
        self.alpaca_client = alpaca_client
        
        # Price cache with TTL (time-to-live)
        self.price_cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_ttl = 5  # seconds

    async def connect(self) -> None:
        """Initialize market data feed."""
        logger.info("Market data feed connected")

    async def disconnect(self) -> None:
        """Cleanup market data feed."""
        logger.info("Market data feed disconnected")

    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 50
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve historical bars from Alpaca.
        
        Args:
            symbol: Symbol to retrieve bars for (e.g., "AAPL" or "BTC/USD")
            timeframe: Timeframe string (e.g., "1Min", "5Min", "15Min", "1Hour", "1Day")
            limit: Maximum number of bars to retrieve (default: 50)
            
        Returns:
            pandas DataFrame with OHLCV data, or None if no data available
        """
        try:
            bars = self.alpaca_client.get_bars(symbol, timeframe, limit)
            if bars is not None and not bars.empty:
                return bars
            logger.warning(f"No bar data for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            return None

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price (latest trade or quote midpoint).
        
        Args:
            symbol: Symbol to get price for (e.g., "AAPL" or "BTC/USD")
            
        Returns:
            Current price as float, or None if no price data available
        """
        # Check cache first
        if symbol in self.price_cache:
            price, timestamp = self.price_cache[symbol]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return price
        
        try:
            # Try latest trade first
            trade = self.alpaca_client.get_latest_trade(symbol)
            if trade:
                price = float(trade["price"])
                self.price_cache[symbol] = (price, datetime.now())
                return price
            
            # Fall back to quote midpoint
            quote = self.alpaca_client.get_latest_quote(symbol)
            if quote:
                price = (float(quote["ask_price"]) + float(quote["bid_price"])) / 2
                self.price_cache[symbol] = (price, datetime.now())
                return price
            
            logger.warning(f"No price data for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None

    async def get_previous_close(self, symbol: str) -> Optional[float]:
        """
        Get previous day's closing price.
        
        Args:
            symbol: Symbol to get previous close for (e.g., "AAPL" or "BTC/USD")
            
        Returns:
            Previous day's closing price as float, or None if not available
        """
        try:
            # Get 2 days of daily bars
            bars = self.alpaca_client.get_bars(symbol, "1Day", limit=2)
            if bars is not None and len(bars) >= 2:
                return float(bars.iloc[-2]["close"])
            logger.warning(f"No previous close for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Failed to get previous close for {symbol}: {e}")
            return None

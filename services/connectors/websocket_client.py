"""WebSocket client for real-time market data streaming from Alpaca."""
from __future__ import annotations

import os
from typing import Dict, List, Callable, Any
from loguru import logger

from alpaca.data.live import StockDataStream, CryptoDataStream


class WebSocketClient:
    """WebSocket client for real-time market data streaming."""

    def __init__(self, config: Dict) -> None:
        """
        Initialize WebSocket client with Alpaca credentials.
        
        Args:
            config: Configuration dictionary (not used for credentials, kept for consistency)
        """
        self.config = config
        
        # Load credentials from environment
        self.api_key = os.getenv("ALPACA_PAPER_API_KEY")
        self.api_secret = os.getenv("ALPACA_PAPER_API_SECRET")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing Alpaca API credentials for WebSocket")
        
        # Initialize data streams
        self.stock_stream = StockDataStream(self.api_key, self.api_secret)
        self.crypto_stream = CryptoDataStream(self.api_key, self.api_secret)
        
        # Setup callback registries
        self.callbacks: Dict[str, List[Callable]] = {
            "trade": [],
            "quote": [],
            "bar": []
        }
        
        logger.info("WebSocketClient initialized")

    async def connect(self) -> None:
        """
        Establish WebSocket connections.
        
        Note: Alpaca streams connect automatically when subscriptions are made.
        This method is provided for interface consistency.
        """
        try:
            logger.info("WebSocket client ready for subscriptions")
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket client: {e}")
            raise

    async def disconnect(self) -> None:
        """
        Close WebSocket connections gracefully.
        
        Closes both stock and crypto data streams.
        """
        try:
            await self.stock_stream.close()
            await self.crypto_stream.close()
            logger.info("WebSocket connections closed")
        except Exception as e:
            logger.error(f"Error closing WebSocket connections: {e}")

    def subscribe_trades(self, symbols: List[str], callback: Callable) -> None:
        """
        Subscribe to trade updates for specified symbols.
        
        Args:
            symbols: List of symbols to subscribe to (e.g., ["AAPL", "BTC/USD"])
            callback: Async callback function to invoke on trade updates
        """
        self.callbacks["trade"].append(callback)
        
        # Separate crypto and stock symbols
        crypto_symbols = [s for s in symbols if "/" in s]
        stock_symbols = [s for s in symbols if "/" not in s]
        
        # Subscribe to crypto trades
        if crypto_symbols:
            self.crypto_stream.subscribe_trades(self._trade_handler, *crypto_symbols)
            logger.info(f"Subscribed to crypto trades: {crypto_symbols}")
        
        # Subscribe to stock trades
        if stock_symbols:
            self.stock_stream.subscribe_trades(self._trade_handler, *stock_symbols)
            logger.info(f"Subscribed to stock trades: {stock_symbols}")

    def subscribe_quotes(self, symbols: List[str], callback: Callable) -> None:
        """
        Subscribe to quote updates for specified symbols.
        
        Args:
            symbols: List of symbols to subscribe to (e.g., ["AAPL", "BTC/USD"])
            callback: Async callback function to invoke on quote updates
        """
        self.callbacks["quote"].append(callback)
        
        # Separate crypto and stock symbols
        crypto_symbols = [s for s in symbols if "/" in s]
        stock_symbols = [s for s in symbols if "/" not in s]
        
        # Subscribe to crypto quotes
        if crypto_symbols:
            self.crypto_stream.subscribe_quotes(self._quote_handler, *crypto_symbols)
            logger.info(f"Subscribed to crypto quotes: {crypto_symbols}")
        
        # Subscribe to stock quotes
        if stock_symbols:
            self.stock_stream.subscribe_quotes(self._quote_handler, *stock_symbols)
            logger.info(f"Subscribed to stock quotes: {stock_symbols}")

    async def _trade_handler(self, trade: Any) -> None:
        """
        Handle incoming trade updates from Alpaca streams.
        
        Parses trade data and forwards to registered callbacks.
        
        Args:
            trade: Trade object from Alpaca stream
        """
        try:
            # Parse trade data
            trade_data = {
                "symbol": trade.symbol,
                "price": float(trade.price),
                "size": int(trade.size),
                "timestamp": trade.timestamp
            }
            
            # Invoke all registered trade callbacks
            for callback in self.callbacks["trade"]:
                try:
                    await callback(trade_data)
                except Exception as e:
                    logger.error(f"Error in trade callback for {trade.symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling trade update: {e}")

    async def _quote_handler(self, quote: Any) -> None:
        """
        Handle incoming quote updates from Alpaca streams.
        
        Parses quote data and forwards to registered callbacks.
        
        Args:
            quote: Quote object from Alpaca stream
        """
        try:
            # Parse quote data
            quote_data = {
                "symbol": quote.symbol,
                "bid_price": float(quote.bid_price),
                "ask_price": float(quote.ask_price),
                "bid_size": int(quote.bid_size),
                "ask_size": int(quote.ask_size),
                "timestamp": quote.timestamp
            }
            
            # Invoke all registered quote callbacks
            for callback in self.callbacks["quote"]:
                try:
                    await callback(quote_data)
                except Exception as e:
                    logger.error(f"Error in quote callback for {quote.symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling quote update: {e}")

    def run(self) -> None:
        """
        Start the WebSocket streams.
        
        This method starts both stock and crypto streams. It should be called
        after subscriptions are set up. The streams will run until disconnect()
        is called or an error occurs.
        """
        try:
            logger.info("Starting WebSocket streams...")
            # Note: In practice, these would be run in separate tasks/threads
            # The actual implementation depends on how the orchestrator manages async tasks
            self.stock_stream.run()
            self.crypto_stream.run()
        except Exception as e:
            logger.error(f"Error running WebSocket streams: {e}")
            raise

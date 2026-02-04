"""Alpaca API client for paper trading integration."""
from __future__ import annotations

import os
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from loguru import logger
import pandas as pd

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest, StockLatestTradeRequest, CryptoLatestTradeRequest, StockLatestQuoteRequest, CryptoLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, GetOrdersRequest, ClosePositionRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.common.exceptions import APIError


class RetryStrategy:
    """Exponential backoff retry strategy for API calls."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        """
        Initialize retry strategy.
        
        Args:
            max_attempts: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic using exponential backoff.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: The last exception if all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Don't retry on authentication errors
                if isinstance(e, APIError) and e.status_code == 401:
                    logger.error(f"Authentication error, not retrying: {e}")
                    raise
                
                # Don't retry on validation errors (4xx except 429)
                if isinstance(e, APIError) and 400 <= e.status_code < 500 and e.status_code != 429:
                    logger.error(f"Client error (status {e.status_code}), not retrying: {e}")
                    raise
                
                # If this was the last attempt, raise the exception
                if attempt == self.max_attempts - 1:
                    logger.error(f"All {self.max_attempts} retry attempts failed")
                    raise
                
                # Calculate delay with exponential backoff
                delay = self.base_delay * (2 ** attempt)
                
                # For rate limit errors, use the retry-after header if available
                if isinstance(e, APIError) and e.status_code == 429:
                    # Alpaca typically uses 60 second rate limit windows
                    delay = 60
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{self.max_attempts}). "
                        f"Waiting {delay}s before retry..."
                    )
                else:
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                
                time.sleep(delay)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception


class AlpacaClient:
    """Alpaca API client wrapper for PulseTrader integration."""

    def __init__(self, config: Dict) -> None:
        """
        Initialize AlpacaClient with authentication and API clients.
        
        Args:
            config: Configuration dictionary
            
        Raises:
            ValueError: If required API credentials are missing
        """
        self.config = config
        
        # Load credentials from environment variables
        self.api_key = os.getenv("ALPACA_PAPER_API_KEY")
        self.api_secret = os.getenv("ALPACA_PAPER_API_SECRET")
        self.mode = os.getenv("ALPACA_MODE", "paper")
        
        # Validate credentials
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Missing Alpaca API credentials. Please set ALPACA_PAPER_API_KEY "
                "and ALPACA_PAPER_API_SECRET environment variables."
            )
        
        # Determine if paper mode
        self.is_paper = self.mode.lower() == "paper"
        
        # Initialize retry strategy
        self.retry_strategy = RetryStrategy(max_attempts=3, base_delay=1.0)
        
        # Initialize TradingClient
        try:
            self.trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                paper=self.is_paper
            )
            logger.info(f"TradingClient initialized in {'paper' if self.is_paper else 'live'} mode")
        except Exception as e:
            logger.error(f"Failed to initialize TradingClient: {e}")
            raise
        
        # Initialize StockHistoricalDataClient
        try:
            self.stock_data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret
            )
            logger.info("StockHistoricalDataClient initialized")
        except Exception as e:
            logger.error(f"Failed to initialize StockHistoricalDataClient: {e}")
            raise
        
        # Initialize CryptoHistoricalDataClient
        try:
            self.crypto_data_client = CryptoHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret
            )
            logger.info("CryptoHistoricalDataClient initialized")
        except Exception as e:
            logger.error(f"Failed to initialize CryptoHistoricalDataClient: {e}")
            raise

    def get_account(self) -> Dict:
        """
        Retrieve account information including equity, cash, and buying power.
        
        Returns:
            Dictionary containing account data with keys:
                - account_id: Account identifier
                - equity: Total account equity
                - cash: Available cash
                - buying_power: Available buying power
                - portfolio_value: Total portfolio value
                - pattern_day_trader: PDT status
                - trading_blocked: Trading blocked status
                - account_blocked: Account blocked status
                - currency: Account currency
                
        Raises:
            APIError: If API request fails
        """
        try:
            account = self.trading_client.get_account()
            
            # Convert Alpaca Account object to PulseTrader dictionary
            account_data = {
                "account_id": str(account.id),
                "equity": float(account.equity),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "account_blocked": account.account_blocked,
                "currency": account.currency
            }
            
            logger.debug(f"Account retrieved: equity=${account_data['equity']:.2f}")
            return account_data
            
        except APIError as e:
            logger.error(f"API error retrieving account: {e}")
            self._handle_api_error(e, "get_account")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving account: {e}")
            raise

    def get_positions(self) -> List[Dict]:
        """
        Retrieve all open positions.
        
        Returns:
            List of dictionaries, each containing position data with keys:
                - symbol: Position symbol
                - qty: Position quantity (positive for long, negative for short)
                - side: Position side ("long" or "short")
                - market_value: Current market value
                - cost_basis: Total cost basis
                - unrealized_pl: Unrealized profit/loss
                - unrealized_plpc: Unrealized P/L percentage
                - current_price: Current market price
                - avg_entry_price: Average entry price
                - asset_class: Asset class ("us_equity" or "crypto")
                
        Raises:
            APIError: If API request fails
        """
        try:
            positions = self.trading_client.get_all_positions()
            
            # Convert Alpaca Position objects to PulseTrader dictionaries
            positions_data = []
            for position in positions:
                position_dict = {
                    "symbol": position.symbol,
                    "qty": int(position.qty),
                    "side": position.side,
                    "market_value": float(position.market_value),
                    "cost_basis": float(position.cost_basis),
                    "unrealized_pl": float(position.unrealized_pl),
                    "unrealized_plpc": float(position.unrealized_plpc),
                    "current_price": float(position.current_price),
                    "avg_entry_price": float(position.avg_entry_price),
                    "asset_class": position.asset_class
                }
                positions_data.append(position_dict)
            
            logger.debug(f"Retrieved {len(positions_data)} positions")
            return positions_data
            
        except APIError as e:
            logger.error(f"API error retrieving positions: {e}")
            self._handle_api_error(e, "get_positions")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving positions: {e}")
            raise

    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Retrieve a specific position by symbol.
        
        Args:
            symbol: The symbol to retrieve position for
            
        Returns:
            Dictionary containing position data (same format as get_positions),
            or None if position doesn't exist
            
        Raises:
            APIError: If API request fails (except for 404 not found)
        """
        try:
            position = self.trading_client.get_open_position(symbol)
            
            # Convert Alpaca Position object to PulseTrader dictionary
            position_dict = {
                "symbol": position.symbol,
                "qty": int(position.qty),
                "side": position.side,
                "market_value": float(position.market_value),
                "cost_basis": float(position.cost_basis),
                "unrealized_pl": float(position.unrealized_pl),
                "unrealized_plpc": float(position.unrealized_plpc),
                "current_price": float(position.current_price),
                "avg_entry_price": float(position.avg_entry_price),
                "asset_class": position.asset_class
            }
            
            logger.debug(f"Position retrieved for {symbol}: {position_dict['qty']} @ ${position_dict['avg_entry_price']:.2f}")
            return position_dict
            
        except APIError as e:
            # 404 means no position exists, which is not an error
            if e.status_code == 404:
                logger.debug(f"No position found for {symbol}")
                return None
            
            logger.error(f"API error retrieving position for {symbol}: {e}")
            self._handle_api_error(e, f"get_position({symbol})")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving position for {symbol}: {e}")
            raise

    def _handle_api_error(self, error: APIError, operation: str) -> None:
        """
        Centralized error handling for API errors with detailed logging and categorization.
        
        This method categorizes API errors and logs appropriate messages based on the error type.
        It handles:
        - Rate limit errors (429): Logs warning about rate limiting
        - Authentication errors (401): Logs critical error about invalid credentials
        - Forbidden errors (403): Logs error about insufficient permissions
        - Not found errors (404): Logs debug message (often expected)
        - Validation errors (422): Logs error about invalid request parameters
        - Server errors (5xx): Logs error about Alpaca service issues
        - Network errors: Logs error about connectivity issues
        
        Args:
            error: The APIError exception from Alpaca SDK
            operation: Description of the operation that failed (for logging context)
        """
        status_code = getattr(error, 'status_code', None)
        
        if status_code == 429:
            # Rate limit error - should be handled by retry logic
            logger.warning(
                f"Rate limit exceeded for {operation}. "
                f"The request will be retried with exponential backoff. "
                f"Consider reducing request frequency."
            )
        elif status_code == 401:
            # Authentication error - critical, cannot retry
            logger.critical(
                f"Authentication failed for {operation}. "
                f"Please verify ALPACA_PAPER_API_KEY and ALPACA_PAPER_API_SECRET "
                f"environment variables are set correctly. Error: {error}"
            )
        elif status_code == 403:
            # Forbidden - insufficient permissions
            logger.error(
                f"Forbidden: {operation}. "
                f"The API key does not have permission to perform this operation. "
                f"Error: {error}"
            )
        elif status_code == 404:
            # Not found - often expected (e.g., no position exists)
            logger.debug(
                f"Resource not found for {operation}. "
                f"This may be expected behavior. Error: {error}"
            )
        elif status_code == 422:
            # Validation error - invalid request parameters
            logger.error(
                f"Validation error for {operation}. "
                f"Request parameters are invalid or violate business rules. "
                f"Error: {error}"
            )
        elif status_code and 500 <= status_code < 600:
            # Server error - Alpaca service issue
            logger.error(
                f"Alpaca server error for {operation} (status {status_code}). "
                f"This is a temporary issue with Alpaca's service. "
                f"The request will be retried. Error: {error}"
            )
        else:
            # Generic API error or network error
            if status_code:
                logger.error(
                    f"API error in {operation}: Status {status_code} - {error}"
                )
            else:
                # Network error (no status code)
                logger.error(
                    f"Network error in {operation}. "
                    f"Check internet connectivity and Alpaca service status. "
                    f"Error: {error}"
                )

    def _parse_timeframe(self, timeframe: str) -> TimeFrame:
        """
        Parse timeframe string to Alpaca TimeFrame object.
        
        Args:
            timeframe: Timeframe string (e.g., "1Min", "5Min", "1Hour", "1Day")
            
        Returns:
            Alpaca TimeFrame object
            
        Raises:
            ValueError: If timeframe format is invalid
        """
        timeframe_map = {
            "1Min": TimeFrame(1, TimeFrameUnit.Minute),
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
            "1Day": TimeFrame(1, TimeFrameUnit.Day),
        }
        
        if timeframe not in timeframe_map:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. "
                f"Supported timeframes: {', '.join(timeframe_map.keys())}"
            )
        
        return timeframe_map[timeframe]

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 50,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve historical bar data for stocks or crypto.
        
        Args:
            symbol: Symbol to retrieve bars for (e.g., "AAPL" or "BTC/USD")
            timeframe: Timeframe string (e.g., "1Min", "5Min", "15Min", "1Hour", "1Day")
            limit: Maximum number of bars to retrieve (default: 50)
            start: Start datetime for bars (optional)
            end: End datetime for bars (optional)
            
        Returns:
            pandas DataFrame with columns: open, high, low, close, volume, trade_count, vwap
            or None if no data available
            
        Raises:
            ValueError: If timeframe is invalid
            APIError: If API request fails
        """
        try:
            # Parse timeframe
            tf = self._parse_timeframe(timeframe)
            
            # Determine if crypto or stock based on symbol format
            is_crypto = "/" in symbol
            
            if is_crypto:
                # Use crypto data client
                request = CryptoBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=tf,
                    limit=limit,
                    start=start,
                    end=end
                )
                bars = self.crypto_data_client.get_crypto_bars(request)
            else:
                # Use stock data client
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=tf,
                    limit=limit,
                    start=start,
                    end=end
                )
                bars = self.stock_data_client.get_stock_bars(request)
            
            # Convert to DataFrame
            if bars and symbol in bars:
                df = bars.df
                
                # If multi-index (symbol, timestamp), reset to single index
                if isinstance(df.index, pd.MultiIndex):
                    df = df.reset_index(level=0, drop=True)
                
                logger.debug(f"Retrieved {len(df)} bars for {symbol} at {timeframe}")
                return df
            else:
                logger.warning(f"No bar data available for {symbol}")
                return None
                
        except ValueError as e:
            logger.error(f"Invalid timeframe for get_bars({symbol}): {e}")
            raise
        except APIError as e:
            logger.error(f"API error retrieving bars for {symbol}: {e}")
            self._handle_api_error(e, f"get_bars({symbol})")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving bars for {symbol}: {e}")
            raise

    def get_latest_trade(self, symbol: str) -> Optional[Dict]:
        """
        Retrieve the latest trade for a symbol.
        
        Args:
            symbol: Symbol to retrieve trade for (e.g., "AAPL" or "BTC/USD")
            
        Returns:
            Dictionary containing trade data with keys:
                - symbol: Trade symbol
                - price: Trade price
                - size: Trade size
                - timestamp: Trade timestamp
            or None if no trade data available
            
        Raises:
            APIError: If API request fails
        """
        try:
            # Determine if crypto or stock
            is_crypto = "/" in symbol
            
            if is_crypto:
                request = CryptoLatestTradeRequest(symbol_or_symbols=symbol)
                trades = self.crypto_data_client.get_crypto_latest_trade(request)
                
                if symbol in trades:
                    trade = trades[symbol]
                    trade_data = {
                        "symbol": symbol,
                        "price": float(trade.price),
                        "size": float(trade.size),
                        "timestamp": trade.timestamp
                    }
                    logger.debug(f"Latest trade for {symbol}: ${trade_data['price']:.2f}")
                    return trade_data
            else:
                request = StockLatestTradeRequest(symbol_or_symbols=symbol)
                trades = self.stock_data_client.get_stock_latest_trade(request)
                
                if symbol in trades:
                    trade = trades[symbol]
                    trade_data = {
                        "symbol": symbol,
                        "price": float(trade.price),
                        "size": int(trade.size),
                        "timestamp": trade.timestamp
                    }
                    logger.debug(f"Latest trade for {symbol}: ${trade_data['price']:.2f}")
                    return trade_data
            
            logger.warning(f"No trade data available for {symbol}")
            return None
            
        except APIError as e:
            logger.error(f"API error retrieving latest trade for {symbol}: {e}")
            self._handle_api_error(e, f"get_latest_trade({symbol})")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving latest trade for {symbol}: {e}")
            raise

    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """
        Retrieve the latest quote for a symbol.
        
        Args:
            symbol: Symbol to retrieve quote for (e.g., "AAPL" or "BTC/USD")
            
        Returns:
            Dictionary containing quote data with keys:
                - symbol: Quote symbol
                - bid_price: Bid price
                - ask_price: Ask price
                - bid_size: Bid size
                - ask_size: Ask size
                - timestamp: Quote timestamp
            or None if no quote data available
            
        Raises:
            APIError: If API request fails
        """
        try:
            # Determine if crypto or stock
            is_crypto = "/" in symbol
            
            if is_crypto:
                request = CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
                quotes = self.crypto_data_client.get_crypto_latest_quote(request)
                
                if symbol in quotes:
                    quote = quotes[symbol]
                    quote_data = {
                        "symbol": symbol,
                        "bid_price": float(quote.bid_price),
                        "ask_price": float(quote.ask_price),
                        "bid_size": float(quote.bid_size),
                        "ask_size": float(quote.ask_size),
                        "timestamp": quote.timestamp
                    }
                    logger.debug(
                        f"Latest quote for {symbol}: "
                        f"bid=${quote_data['bid_price']:.2f} ask=${quote_data['ask_price']:.2f}"
                    )
                    return quote_data
            else:
                request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                quotes = self.stock_data_client.get_stock_latest_quote(request)
                
                if symbol in quotes:
                    quote = quotes[symbol]
                    quote_data = {
                        "symbol": symbol,
                        "bid_price": float(quote.bid_price),
                        "ask_price": float(quote.ask_price),
                        "bid_size": int(quote.bid_size),
                        "ask_size": int(quote.ask_size),
                        "timestamp": quote.timestamp
                    }
                    logger.debug(
                        f"Latest quote for {symbol}: "
                        f"bid=${quote_data['bid_price']:.2f} ask=${quote_data['ask_price']:.2f}"
                    )
                    return quote_data
            
            logger.warning(f"No quote data available for {symbol}")
            return None
            
        except APIError as e:
            logger.error(f"API error retrieving latest quote for {symbol}: {e}")
            self._handle_api_error(e, f"get_latest_quote({symbol})")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving latest quote for {symbol}: {e}")
            raise

    def get_previous_close(self, symbol: str) -> Optional[float]:
        """
        Retrieve the previous trading day's closing price.
        
        Args:
            symbol: Symbol to retrieve previous close for (e.g., "AAPL" or "BTC/USD")
            
        Returns:
            Previous day's closing price as float, or None if not available
            
        Raises:
            APIError: If API request fails
        """
        try:
            # Get 2 days of daily bars to ensure we have previous close
            bars_df = self.get_bars(symbol, "1Day", limit=2)
            
            if bars_df is not None and len(bars_df) >= 2:
                # Get the second-to-last bar's close price (previous day)
                previous_close = float(bars_df.iloc[-2]["close"])
                logger.debug(f"Previous close for {symbol}: ${previous_close:.2f}")
                return previous_close
            elif bars_df is not None and len(bars_df) == 1:
                # Only one bar available, use it as previous close
                previous_close = float(bars_df.iloc[0]["close"])
                logger.debug(f"Previous close for {symbol} (single bar): ${previous_close:.2f}")
                return previous_close
            else:
                logger.warning(f"No previous close data available for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving previous close for {symbol}: {e}")
            raise

    def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: int,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Submit an order to Alpaca.
        
        Args:
            symbol: Symbol to trade (e.g., "AAPL" or "BTC/USD")
            side: Order side ("buy" or "sell")
            order_type: Order type ("market", "limit", or "stop")
            qty: Order quantity (number of shares/units)
            limit_price: Limit price for limit orders (optional)
            stop_price: Stop price for stop orders (optional)
            client_order_id: Client-generated order ID for idempotency (optional)
            
        Returns:
            Dictionary containing order details with keys:
                - id: Alpaca order ID
                - client_order_id: Client order ID
                - symbol: Order symbol
                - side: Order side
                - order_type: Order type
                - qty: Order quantity
                - filled_qty: Filled quantity
                - status: Order status
                - submitted_at: Submission timestamp
                - filled_at: Fill timestamp (if filled)
                - filled_avg_price: Average fill price (if filled)
                - limit_price: Limit price (if limit order)
                - stop_price: Stop price (if stop order)
            or None if submission fails
            
        Raises:
            ValueError: If order parameters are invalid
            APIError: If API request fails
        """
        try:
            # Validate parameters
            if side not in ["buy", "sell"]:
                raise ValueError(f"Invalid order side: {side}. Must be 'buy' or 'sell'")
            
            if order_type not in ["market", "limit", "stop"]:
                raise ValueError(f"Invalid order type: {order_type}. Must be 'market', 'limit', or 'stop'")
            
            if qty <= 0:
                raise ValueError(f"Invalid quantity: {qty}. Must be positive")
            
            if order_type == "limit" and limit_price is None:
                raise ValueError("Limit price is required for limit orders")
            
            if order_type == "stop" and stop_price is None:
                raise ValueError("Stop price is required for stop orders")
            
            # Convert side to Alpaca enum
            order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
            
            # Create order request based on order type
            if order_type == "market":
                order_request = MarketOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                    client_order_id=client_order_id
                )
            elif order_type == "limit":
                order_request = LimitOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price,
                    client_order_id=client_order_id
                )
            else:  # stop order
                order_request = StopOrderRequest(
                    symbol=symbol,
                    qty=qty,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                    stop_price=stop_price,
                    client_order_id=client_order_id
                )
            
            # Submit order
            order = self.trading_client.submit_order(order_request)
            
            # Convert Alpaca Order object to PulseTrader dictionary
            order_dict = {
                "id": str(order.id),
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "qty": int(order.qty),
                "filled_qty": int(order.filled_qty) if order.filled_qty else 0,
                "status": order.status.value,
                "submitted_at": order.submitted_at,
                "filled_at": order.filled_at,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None
            }
            
            logger.info(
                f"Order submitted: {side} {qty} {symbol} @ {order_type} "
                f"(ID: {order_dict['id']}, Status: {order_dict['status']})"
            )
            return order_dict
            
        except ValueError as e:
            logger.error(f"Invalid order parameters: {e}")
            raise
        except APIError as e:
            logger.error(f"API error submitting order for {symbol}: {e}")
            self._handle_api_error(e, f"submit_order({symbol})")
            return None
        except Exception as e:
            logger.error(f"Unexpected error submitting order for {symbol}: {e}")
            raise

    def get_order(self, order_id: str) -> Optional[Dict]:
        """
        Retrieve order details by order ID.
        
        Args:
            order_id: Alpaca order ID
            
        Returns:
            Dictionary containing order details (same format as submit_order),
            or None if order doesn't exist
            
        Raises:
            APIError: If API request fails (except for 404 not found)
        """
        try:
            order = self.trading_client.get_order_by_id(order_id)
            
            # Convert Alpaca Order object to PulseTrader dictionary
            order_dict = {
                "id": str(order.id),
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "qty": int(order.qty),
                "filled_qty": int(order.filled_qty) if order.filled_qty else 0,
                "status": order.status.value,
                "submitted_at": order.submitted_at,
                "filled_at": order.filled_at,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None
            }
            
            logger.debug(f"Order retrieved: {order_id} - Status: {order_dict['status']}")
            return order_dict
            
        except APIError as e:
            # 404 means order doesn't exist, which is not an error
            if e.status_code == 404:
                logger.debug(f"No order found with ID: {order_id}")
                return None
            
            logger.error(f"API error retrieving order {order_id}: {e}")
            self._handle_api_error(e, f"get_order({order_id})")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving order {order_id}: {e}")
            raise

    def get_orders(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Retrieve orders with optional status filter.
        
        Args:
            status: Filter by order status (optional). Valid values:
                    "open", "closed", "all". Default is "open"
            limit: Maximum number of orders to retrieve (default: 100)
            
        Returns:
            List of dictionaries, each containing order details
            (same format as submit_order)
            
        Raises:
            ValueError: If status is invalid
            APIError: If API request fails
        """
        try:
            # Validate and convert status
            if status is None:
                query_status = QueryOrderStatus.OPEN
            elif status == "open":
                query_status = QueryOrderStatus.OPEN
            elif status == "closed":
                query_status = QueryOrderStatus.CLOSED
            elif status == "all":
                query_status = QueryOrderStatus.ALL
            else:
                raise ValueError(
                    f"Invalid status: {status}. Must be 'open', 'closed', or 'all'"
                )
            
            # Create request
            request = GetOrdersRequest(
                status=query_status,
                limit=limit
            )
            
            # Get orders
            orders = self.trading_client.get_orders(request)
            
            # Convert Alpaca Order objects to PulseTrader dictionaries
            orders_data = []
            for order in orders:
                order_dict = {
                    "id": str(order.id),
                    "client_order_id": order.client_order_id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "order_type": order.order_type.value,
                    "qty": int(order.qty),
                    "filled_qty": int(order.filled_qty) if order.filled_qty else 0,
                    "status": order.status.value,
                    "submitted_at": order.submitted_at,
                    "filled_at": order.filled_at,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                    "limit_price": float(order.limit_price) if order.limit_price else None,
                    "stop_price": float(order.stop_price) if order.stop_price else None
                }
                orders_data.append(order_dict)
            
            logger.debug(f"Retrieved {len(orders_data)} orders with status: {status or 'open'}")
            return orders_data
            
        except ValueError as e:
            logger.error(f"Invalid status parameter: {e}")
            raise
        except APIError as e:
            logger.error(f"API error retrieving orders: {e}")
            self._handle_api_error(e, "get_orders")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving orders: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Alpaca order ID to cancel
            
        Returns:
            True if order was successfully canceled, False otherwise
            
        Raises:
            APIError: If API request fails
        """
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"Order canceled: {order_id}")
            return True
            
        except APIError as e:
            # 404 means order doesn't exist or already canceled
            if e.status_code == 404:
                logger.warning(f"Cannot cancel order {order_id}: not found or already canceled")
                return False
            
            # 422 means order is not cancelable (already filled, etc.)
            if e.status_code == 422:
                logger.warning(f"Cannot cancel order {order_id}: order is not cancelable")
                return False
            
            logger.error(f"API error canceling order {order_id}: {e}")
            self._handle_api_error(e, f"cancel_order({order_id})")
            raise
        except Exception as e:
            logger.error(f"Unexpected error canceling order {order_id}: {e}")
            raise

    def close_position(self, symbol: str) -> Optional[Dict]:
        """
        Close a position by submitting a market order for the full quantity.
        
        Args:
            symbol: Symbol of the position to close
            
        Returns:
            Dictionary containing the close order details (same format as submit_order),
            or None if position doesn't exist or close fails
            
        Raises:
            APIError: If API request fails
        """
        try:
            # Use Alpaca's close position endpoint
            order = self.trading_client.close_position(symbol)
            
            # Convert Alpaca Order object to PulseTrader dictionary
            order_dict = {
                "id": str(order.id),
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "qty": int(order.qty),
                "filled_qty": int(order.filled_qty) if order.filled_qty else 0,
                "status": order.status.value,
                "submitted_at": order.submitted_at,
                "filled_at": order.filled_at,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None
            }
            
            logger.info(f"Position closed: {symbol} (Order ID: {order_dict['id']})")
            return order_dict
            
        except APIError as e:
            # 404 means no position exists
            if e.status_code == 404:
                logger.warning(f"Cannot close position for {symbol}: no position found")
                return None
            
            logger.error(f"API error closing position for {symbol}: {e}")
            self._handle_api_error(e, f"close_position({symbol})")
            return None
        except Exception as e:
            logger.error(f"Unexpected error closing position for {symbol}: {e}")
            raise

    def close_all_positions(self) -> List[Dict]:
        """
        Close all open positions.
        
        Returns:
            List of dictionaries, each containing close order details
            (same format as submit_order)
            
        Raises:
            APIError: If API request fails
        """
        try:
            # Use Alpaca's close all positions endpoint
            orders = self.trading_client.close_all_positions(cancel_orders=True)
            
            # Convert Alpaca Order objects to PulseTrader dictionaries
            orders_data = []
            for order in orders:
                order_dict = {
                    "id": str(order.id),
                    "client_order_id": order.client_order_id,
                    "symbol": order.symbol,
                    "side": order.side.value,
                    "order_type": order.order_type.value,
                    "qty": int(order.qty),
                    "filled_qty": int(order.filled_qty) if order.filled_qty else 0,
                    "status": order.status.value,
                    "submitted_at": order.submitted_at,
                    "filled_at": order.filled_at,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                    "limit_price": float(order.limit_price) if order.limit_price else None,
                    "stop_price": float(order.stop_price) if order.stop_price else None
                }
                orders_data.append(order_dict)
            
            logger.info(f"All positions closed: {len(orders_data)} orders submitted")
            return orders_data
            
        except APIError as e:
            logger.error(f"API error closing all positions: {e}")
            self._handle_api_error(e, "close_all_positions")
            raise
        except Exception as e:
            logger.error(f"Unexpected error closing all positions: {e}")
            raise



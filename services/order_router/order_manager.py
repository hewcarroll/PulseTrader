"""Order lifecycle management."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from loguru import logger


class OrderManager:
    """Order manager with real Alpaca execution."""

    def __init__(
        self,
        config: Dict,
        alpaca_client,
        account_manager,
        market_data,
        risk_manager
    ) -> None:
        """
        Initialize OrderManager with dependencies.
        
        Args:
            config: Configuration dictionary
            alpaca_client: AlpacaClient instance for order execution
            account_manager: AccountManager instance for account data
            market_data: MarketDataFeed instance for price data
            risk_manager: RiskManager instance for trade validation
        """
        self.config = config
        self.alpaca_client = alpaca_client
        self.account_manager = account_manager
        self.market_data = market_data
        self.risk_manager = risk_manager
        
        # Order cache for quick lookup
        self.order_cache: Dict[str, Dict] = {}

    async def get_account_equity(self) -> float:
        """
        Get current account equity.
        
        Returns:
            Current equity as float
        """
        return await self.account_manager.get_equity()

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Symbol to get price for
            
        Returns:
            Current price as float, or None if not available
        """
        return await self.market_data.get_current_price(symbol)

    async def get_previous_close(self, symbol: str) -> Optional[float]:
        """
        Get previous close for a symbol.
        
        Args:
            symbol: Symbol to get previous close for
            
        Returns:
            Previous close as float, or None if not available
        """
        return await self.market_data.get_previous_close(symbol)

    async def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: int,
        strategy: str,
        limit_price: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Submit an order with risk validation.
        
        Args:
            symbol: Symbol to trade
            side: Order side ("buy" or "sell")
            order_type: Order type ("market", "limit", or "stop")
            qty: Order quantity
            strategy: Strategy name for tracking
            limit_price: Limit price for limit orders (optional)
            
        Returns:
            Order dictionary if successful, None if rejected or failed
        """
        # Get current equity for risk validation
        equity = await self.get_account_equity()
        
        # Get current price for trade value calculation
        current_price = await self.get_current_price(symbol)
        
        if current_price is None:
            logger.error(f"Cannot submit order for {symbol}: no price data available")
            return None
        
        # Calculate trade value
        trade_value = qty * current_price
        
        # Determine asset type
        asset_type = self._get_asset_type(symbol)
        
        # Get current position counts by type
        positions = await self.account_manager.get_positions()
        position_counts = self._count_positions_by_type(positions)
        
        # Validate trade with risk manager
        is_valid, reasons = self.risk_manager.validate_trade(
            equity=equity,
            proposed_trade_value=trade_value,
            asset_type=asset_type,
            current_positions=position_counts
        )
        
        if not is_valid:
            # Log order rejection with detailed reasons
            logger.warning(
                f"Order REJECTED for {symbol}: {side.upper()} {qty} shares @ {order_type.upper()} "
                f"(Strategy: {strategy}, Reasons: {', '.join(reasons)})"
            )
            return None
        
        # Generate client order ID for idempotency
        client_order_id = self._generate_client_order_id(symbol, strategy)
        
        # Log order submission attempt with full details
        logger.info(
            f"Submitting order: {side.upper()} {qty} {symbol} @ {order_type.upper()} "
            f"(Strategy: {strategy}, Trade Value: ${trade_value:.2f}, "
            f"Current Price: ${current_price:.2f}"
            f"{f', Limit Price: ${limit_price:.2f}' if limit_price else ''})"
        )
        
        # Submit order via AlpacaClient
        try:
            order = self.alpaca_client.submit_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=qty,
                limit_price=limit_price,
                client_order_id=client_order_id
            )
            
            if order:
                # Cache the order
                self.order_cache[order["id"]] = order
                
                # Log successful submission with order details
                logger.info(
                    f"Order SUBMITTED successfully: {side.upper()} {qty} {symbol} @ {order_type.upper()} "
                    f"(Order ID: {order['id']}, Client ID: {client_order_id}, "
                    f"Status: {order['status']}, Strategy: {strategy})"
                )
                
                # Check if order is already filled and log fill details
                if order['status'] in ['filled', 'partially_filled']:
                    self._log_order_fill(order)
                
                return order
            else:
                logger.error(
                    f"Order submission FAILED for {symbol}: No order returned from API "
                    f"({side.upper()} {qty} @ {order_type.upper()}, Strategy: {strategy})"
                )
                return None
                
        except Exception as e:
            logger.error(
                f"Error submitting order for {symbol}: {e} "
                f"({side.upper()} {qty} @ {order_type.upper()}, Strategy: {strategy})"
            )
            return None

    async def submit_dividend_order(
        self, symbol: str, qty: int, order_type: str, force_fill_time: str
    ) -> Optional[Dict]:
        """
        Submit a dividend allocation order.
        
        Args:
            symbol: Symbol to trade
            qty: Order quantity
            order_type: Order type
            force_fill_time: Force fill time (not used in current implementation)
            
        Returns:
            Order dictionary if successful, None otherwise
        """
        return await self.submit_order(
            symbol=symbol,
            side="buy",
            order_type=order_type,
            qty=qty,
            strategy="dividend_allocation",
        )

    async def close_position(self, symbol: str) -> Optional[Dict]:
        """
        Close a specific position.
        
        Args:
            symbol: Symbol of position to close
            
        Returns:
            Order dictionary if successful, None otherwise
        """
        # Get the position
        position = await self.account_manager.get_position(symbol)
        
        if not position:
            logger.warning(f"No position to close for {symbol}")
            return None
        
        # Calculate order parameters
        qty = abs(int(position["qty"]))
        side = "sell" if float(position["qty"]) > 0 else "buy"
        unrealized_pl = float(position.get("unrealized_pl", 0))
        current_price = float(position.get("current_price", 0))
        
        logger.info(
            f"Closing position: {side.upper()} {qty} {symbol} @ MARKET "
            f"(Current Price: ${current_price:.2f}, Unrealized P/L: ${unrealized_pl:.2f})"
        )
        
        # Submit market order to close position
        return await self.submit_order(
            symbol=symbol,
            side=side,
            order_type="market",
            qty=qty,
            strategy="position_close"
        )

    async def close_losing_positions(self) -> None:
        """Close positions with unrealized losses."""
        try:
            positions = await self.account_manager.get_positions()
            
            losing_positions = []
            for position in positions:
                unrealized_pl = float(position.get("unrealized_pl", 0))
                
                if unrealized_pl < 0:
                    losing_positions.append(position)
            
            if losing_positions:
                logger.info(f"Found {len(losing_positions)} losing positions to close")
                
                for position in losing_positions:
                    symbol = position["symbol"]
                    unrealized_pl = float(position.get("unrealized_pl", 0))
                    logger.info(
                        f"Closing losing position: {symbol} "
                        f"(Unrealized P/L: ${unrealized_pl:.2f})"
                    )
                    await self.close_position(symbol)
            else:
                logger.info("No losing positions found to close")
                    
        except Exception as e:
            logger.error(f"Error closing losing positions: {e}")

    async def tighten_all_stops(self) -> None:
        """Tighten stop losses for all positions (stub for future implementation)."""
        logger.info("Tightening all stops (not yet implemented)")

    async def close_all_positions(self) -> None:
        """Close all open positions."""
        try:
            logger.info("Closing all open positions...")
            results = self.alpaca_client.close_all_positions()
            
            # Log details about each close order
            for order in results:
                symbol = order.get("symbol", "UNKNOWN")
                side = order.get("side", "UNKNOWN")
                qty = order.get("qty", 0)
                order_id = order.get("id", "UNKNOWN")
                logger.info(
                    f"Position close order submitted: {side.upper()} {qty} {symbol} "
                    f"(Order ID: {order_id})"
                )
            
            logger.info(f"All positions closed: {len(results)} close orders submitted")
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")

    def _get_asset_type(self, symbol: str) -> str:
        """
        Determine asset type from symbol.
        
        Args:
            symbol: Symbol to classify
            
        Returns:
            Asset type: "crypto", "etf", or "stock"
        """
        # Crypto symbols contain "/"
        if "/" in symbol:
            return "crypto"
        
        # Known leveraged ETFs
        leveraged_etfs = [
            "TQQQ", "SQQQ", "SPXL", "SPXS", "SOXL", "SOXS",
            "UDOW", "SDOW", "TNA", "TZA", "UPRO", "SPXU"
        ]
        
        if symbol in leveraged_etfs:
            return "etf"
        
        # Default to stock
        return "stock"

    def _count_positions_by_type(self, positions: list) -> Dict[str, int]:
        """
        Count positions by asset type.
        
        Args:
            positions: List of position dictionaries
            
        Returns:
            Dictionary with counts by asset type
        """
        counts = {"crypto": 0, "etf": 0, "stock": 0}
        
        for position in positions:
            asset_type = self._get_asset_type(position["symbol"])
            counts[asset_type] += 1
        
        return counts

    def _generate_client_order_id(self, symbol: str, strategy: str) -> str:
        """
        Generate unique client order ID for idempotency.
        
        Args:
            symbol: Order symbol
            strategy: Strategy name
            
        Returns:
            Unique client order ID
        """
        # Get prefix from config or use default
        prefix = self.config.get("execution", {}).get("client_order_id", {}).get("prefix", "pt01")
        
        # Generate timestamp in milliseconds
        timestamp = int(datetime.now().timestamp() * 1000)
        
        # Format: prefix_strategy_symbol_timestamp
        return f"{prefix}_{strategy}_{symbol}_{timestamp}"

    def _log_order_fill(self, order: Dict) -> None:
        """
        Log order fill details with price and quantity information.
        
        Args:
            order: Order dictionary containing fill information
        """
        symbol = order.get("symbol", "UNKNOWN")
        side = order.get("side", "UNKNOWN")
        status = order.get("status", "UNKNOWN")
        filled_qty = order.get("filled_qty", 0)
        total_qty = order.get("qty", 0)
        filled_avg_price = order.get("filled_avg_price")
        order_id = order.get("id", "UNKNOWN")
        
        if status == "filled":
            # Fully filled order
            logger.info(
                f"Order FILLED: {side.upper()} {filled_qty} {symbol} @ ${filled_avg_price:.2f} "
                f"(Order ID: {order_id}, Total Value: ${filled_qty * filled_avg_price:.2f})"
            )
        elif status == "partially_filled":
            # Partially filled order
            remaining_qty = total_qty - filled_qty
            logger.info(
                f"Order PARTIALLY FILLED: {side.upper()} {filled_qty}/{total_qty} {symbol} @ ${filled_avg_price:.2f} "
                f"(Order ID: {order_id}, Remaining: {remaining_qty}, "
                f"Filled Value: ${filled_qty * filled_avg_price:.2f})"
            )

    async def get_order_status(self, order_id: str) -> Optional[Dict]:
        """
        Get current order status and log fill information if order is filled.
        
        Args:
            order_id: Alpaca order ID
            
        Returns:
            Order dictionary with current status, or None if not found
        """
        try:
            order = self.alpaca_client.get_order(order_id)
            
            if order:
                # Update cache
                self.order_cache[order_id] = order
                
                # Log fill information if order is filled or partially filled
                if order['status'] in ['filled', 'partially_filled']:
                    self._log_order_fill(order)
                
                return order
            else:
                logger.warning(f"Order not found: {order_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving order status for {order_id}: {e}")
            return None

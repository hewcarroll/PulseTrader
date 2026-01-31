"""Order lifecycle management."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from loguru import logger


class OrderManager:
    """Basic order manager placeholder."""

    def __init__(self, config: Dict) -> None:
        self.config = config

    async def get_account_equity(self) -> float:
        return 0.0

    async def get_current_price(self, symbol: str) -> Optional[float]:
        return None

    async def get_previous_close(self, symbol: str) -> Optional[float]:
        return None

    async def submit_order(
        self, symbol: str, side: str, order_type: str, qty: int, strategy: str
    ) -> Optional[Dict]:
        logger.info(f"Submitting order: {side} {qty} {symbol} ({order_type})")
        return {
            "id": f"order_{symbol}_{datetime.now().timestamp()}",
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "order_type": order_type,
            "submitted_at": datetime.now().isoformat(),
            "status": "submitted",
        }

    async def submit_dividend_order(
        self, symbol: str, qty: int, order_type: str, force_fill_time: str
    ) -> Optional[Dict]:
        return await self.submit_order(
            symbol=symbol,
            side="buy",
            order_type=order_type,
            qty=qty,
            strategy="dividend_allocation",
        )

    async def close_losing_positions(self) -> None:
        logger.info("Closing losing positions (stub)")

    async def tighten_all_stops(self) -> None:
        logger.info("Tightening all stops (stub)")

    async def close_all_positions(self) -> None:
        logger.info("Closing all positions (stub)")

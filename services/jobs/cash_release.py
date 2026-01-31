"""Cash release handler."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict

from loguru import logger


class CashReleaseJob:
    """Handle cash release requests."""

    def __init__(self, config: Dict, order_manager) -> None:
        self.config = config
        self.order_manager = order_manager

    async def execute(self, amount: Decimal) -> None:
        logger.info(f"Cash release requested: ${amount:,.2f} (stub)")

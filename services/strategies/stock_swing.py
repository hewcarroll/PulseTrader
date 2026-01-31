"""Stock swing strategy (PDT-aware)."""
from __future__ import annotations

from typing import Dict

from loguru import logger

from services.strategies.base_strategy import BaseStrategy


class StockSwingStrategy(BaseStrategy):
    """Placeholder stock swing strategy."""

    def __init__(self, config: Dict, risk_manager, order_manager, market_data) -> None:
        super().__init__(config, risk_manager, order_manager, market_data)
        self.min_equity_required = config.get("min_equity_required", 25000)
        logger.info("Stock Swing Strategy initialized")

    async def evaluate(self) -> None:
        return None

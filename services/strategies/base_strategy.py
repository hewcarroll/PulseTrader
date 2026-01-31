"""Base strategy implementation."""
from __future__ import annotations

from typing import Dict


class BaseStrategy:
    """Abstract strategy base class."""

    def __init__(self, config: Dict, risk_manager, order_manager, market_data) -> None:
        self.config = config
        self.risk_manager = risk_manager
        self.order_manager = order_manager
        self.market_data = market_data
        self.is_running = False
        self.new_entries_disabled = False

    async def start(self) -> None:
        self.is_running = True

    async def stop(self) -> None:
        self.is_running = False

    def disable_new_entries(self) -> None:
        self.new_entries_disabled = True

    async def evaluate(self) -> None:
        raise NotImplementedError

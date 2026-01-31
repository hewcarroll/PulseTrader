"""Daily report generation job."""
from __future__ import annotations

from typing import Dict

from loguru import logger


class DailyReportJob:
    """Generate daily performance reports."""

    def __init__(self, config: Dict, account_manager, performance_analyzer) -> None:
        self.config = config
        self.account_manager = account_manager
        self.performance_analyzer = performance_analyzer

    async def schedule(self) -> None:
        logger.info("Daily report job scheduled (stub)")

    async def execute(self) -> None:
        logger.info("Daily report generation started (stub)")

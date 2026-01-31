"""End-of-day analysis job."""
from __future__ import annotations

from typing import Dict

from loguru import logger


class EODAnalysisJob:
    """Run end-of-day analysis and strategy tuning."""

    def __init__(self, config: Dict, performance_analyzer, strategies: Dict) -> None:
        self.config = config
        self.performance_analyzer = performance_analyzer
        self.strategies = strategies

    async def schedule(self) -> None:
        logger.info("EOD analysis job scheduled (stub)")

    async def execute(self) -> None:
        logger.info("EOD analysis running (stub)")

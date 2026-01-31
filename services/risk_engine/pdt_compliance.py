"""
PDT (Pattern Day Trading) Compliance Module
Enforces PDT rules and manages pre/post PDT behavior.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from loguru import logger


class PDTComplianceManager:
    """
    Manages Pattern Day Trading compliance.
    """

    PDT_THRESHOLD = Decimal("25000.00")
    MAX_DAY_TRADES = 3
    ROLLING_WINDOW_DAYS = 5

    def __init__(self, config: Dict) -> None:
        self.config = config
        self.pdt_config = config.get("pdt", {})
        self.enabled = self.pdt_config.get("enabled", True)

        self.day_trades: List[Dict] = []
        self.stock_entry_times: Dict[str, datetime] = {}

        logger.info("PDT Compliance Manager initialized")

    def is_pdt_unlocked(self, equity: float) -> bool:
        return Decimal(str(equity)) >= self.PDT_THRESHOLD

    def get_remaining_day_trades(self, equity: float) -> int:
        if self.is_pdt_unlocked(equity):
            return 999

        self._clean_old_day_trades()
        used = len(self.day_trades)
        remaining = max(0, self.MAX_DAY_TRADES - used)
        return remaining

    def _clean_old_day_trades(self) -> None:
        cutoff_date = date.today() - timedelta(days=self.ROLLING_WINDOW_DAYS)

        self.day_trades = [
            day_trade
            for day_trade in self.day_trades
            if datetime.fromisoformat(day_trade["date"]).date() > cutoff_date
        ]

    def record_day_trade(self, symbol: str, entry_time: datetime, exit_time: datetime) -> None:
        if entry_time.date() == exit_time.date():
            day_trade = {
                "symbol": symbol,
                "date": entry_time.date().isoformat(),
                "entry_time": entry_time.isoformat(),
                "exit_time": exit_time.isoformat(),
            }

            self.day_trades.append(day_trade)
            logger.warning(
                f"Day trade recorded: {symbol} on {entry_time.date()} "
                f"({len(self.day_trades)}/{self.MAX_DAY_TRADES})"
            )

    def can_day_trade(self, equity: float, symbol: str) -> Tuple[bool, str]:
        if not self.enabled:
            return True, "PDT compliance disabled"

        if self.is_pdt_unlocked(equity):
            return True, "PDT unlocked"

        remaining = self.get_remaining_day_trades(equity)

        if remaining <= 0:
            reason = (
                "No day trades remaining in 5-day window "
                f"(used {self.MAX_DAY_TRADES}/{self.MAX_DAY_TRADES})"
            )
            logger.error(f"PDT VIOLATION PREVENTED: {reason}")
            return False, reason

        if remaining == 1:
            logger.warning("WARNING: Last day trade available before PDT restriction")

        return True, f"{remaining} day trades remaining"

    def can_close_position_today(
        self, equity: float, symbol: str, entry_time: datetime
    ) -> Tuple[bool, str]:
        if not self.enabled:
            return True, "PDT compliance disabled"

        if self.is_pdt_unlocked(equity):
            return True, "PDT unlocked"

        if entry_time.date() == date.today():
            return self.can_day_trade(equity, symbol)

        return True, "Not a day trade"

    def is_stock_trading_allowed(self, equity: float) -> Tuple[bool, str]:
        pre_pdt_config = self.pdt_config.get("pre_pdt", {})

        if self.is_pdt_unlocked(equity):
            return True, "PDT unlocked - stock trading enabled"

        if pre_pdt_config.get("disable_stock_trading", True):
            reason = "Stock trading disabled until equity >= $25k (PDT optimization)"
            return False, reason

        return True, "Stock trading allowed with restrictions"

    def record_stock_entry(self, symbol: str) -> None:
        self.stock_entry_times[symbol] = datetime.now()
        logger.debug(f"Stock entry recorded: {symbol} at {datetime.now()}")

    def remove_stock_entry(self, symbol: str) -> None:
        if symbol in self.stock_entry_times:
            del self.stock_entry_times[symbol]
            logger.debug(f"Stock entry removed: {symbol}")

    def get_minimum_hold_time(self, equity: float) -> timedelta:
        if self.is_pdt_unlocked(equity):
            post_pdt_config = self.pdt_config.get("post_pdt", {})
            if post_pdt_config.get("remove_hold_restrictions", False):
                return timedelta(seconds=0)
            return timedelta(days=1)

        pre_pdt_config = self.pdt_config.get("pre_pdt", {})
        min_hold_days = pre_pdt_config.get("min_stock_hold_days", 1)
        return timedelta(days=min_hold_days)

    def can_exit_stock_position(self, equity: float, symbol: str) -> Tuple[bool, str]:
        if symbol not in self.stock_entry_times:
            return True, "No entry time on record"

        entry_time = self.stock_entry_times[symbol]
        min_hold = self.get_minimum_hold_time(equity)
        time_held = datetime.now() - entry_time

        if time_held < min_hold:
            remaining = min_hold - time_held
            hours = remaining.total_seconds() / 3600
            reason = f"Minimum hold time not met ({hours:.1f} hours remaining)"
            logger.warning(f"Stock exit denied for {symbol}: {reason}")
            return False, reason

        return self.can_close_position_today(equity, symbol, entry_time)

    def get_focus_assets(self, equity: float) -> List[str]:
        if self.is_pdt_unlocked(equity):
            return ["crypto", "etf", "stock"]

        pre_pdt_config = self.pdt_config.get("pre_pdt", {})
        return pre_pdt_config.get("focus_assets", ["crypto", "leveraged_etf"])

    def get_status_report(self, equity: float) -> Dict:
        is_unlocked = self.is_pdt_unlocked(equity)
        remaining_to_unlock = max(0, float(self.PDT_THRESHOLD - Decimal(str(equity))))

        report = {
            "pdt_unlocked": is_unlocked,
            "equity": equity,
            "pdt_threshold": float(self.PDT_THRESHOLD),
            "remaining_to_unlock": remaining_to_unlock,
            "focus_assets": self.get_focus_assets(equity),
            "stock_trading_allowed": self.is_stock_trading_allowed(equity)[0],
        }

        if not is_unlocked:
            report["day_trades_remaining"] = self.get_remaining_day_trades(equity)
            report["day_trades_used"] = len(self.day_trades)
            report["day_trades_history"] = self.day_trades

        return report

"""Account management for PulseTrader.01."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from loguru import logger


@dataclass
class Account:
    """Basic account representation."""

    account_id: str
    name: str
    account_type: str

    async def get_equity(self) -> float:
        return 0.0

    async def get_cash(self) -> float:
        return 0.0

    async def get_positions(self) -> List[Dict]:
        return []

    async def get_daily_pnl(self) -> float:
        return 0.0


class AccountManager:
    """Multi-account management."""

    def __init__(self, config: Dict) -> None:
        self.config = config
        self.accounts: Dict[str, Account] = {}

    async def initialize(self) -> None:
        """Initialize account objects from config."""
        default_config = self.config.get("accounts", {}).get("default", {})
        account = Account(
            account_id=default_config.get("account_id", ""),
            name=default_config.get("name", "Default"),
            account_type=default_config.get("type", "main"),
        )
        self.accounts["default"] = account
        logger.info("Account manager initialized")

    def get_primary_account(self) -> Account:
        """Return the primary account."""
        return self.accounts["default"]

    async def update_state(self) -> None:
        """Refresh account state."""
        return None

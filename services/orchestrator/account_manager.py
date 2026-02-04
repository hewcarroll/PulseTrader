"""Account management for PulseTrader.01."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class Account:
    """Account representation with real Alpaca data."""

    account_id: str
    name: str
    account_type: str
    equity: float = 0.0
    cash: float = 0.0
    buying_power: float = 0.0
    portfolio_value: float = 0.0
    pattern_day_trader: bool = False
    trading_blocked: bool = False
    account_blocked: bool = False
    currency: str = "USD"


class AccountManager:
    """Multi-account management with real Alpaca integration."""

    def __init__(self, config: Dict, alpaca_client) -> None:
        """
        Initialize AccountManager with AlpacaClient.
        
        Args:
            config: Configuration dictionary
            alpaca_client: AlpacaClient instance for API calls
        """
        self.config = config
        self.alpaca_client = alpaca_client
        self.accounts: Dict[str, Account] = {}
        
        # Cache management
        self.account_cache: Optional[Dict] = None
        self.positions_cache: List[Dict] = []
        self.last_update: Optional[datetime] = None
        self.update_interval = 30  # seconds - cache TTL

    async def initialize(self) -> None:
        """Initialize account state from Alpaca."""
        try:
            # Update account state from Alpaca
            await self.update_state()
            
            # Create Account object with real data
            if self.account_cache:
                default_config = self.config.get("accounts", {}).get("default", {})
                account = Account(
                    account_id=self.account_cache.get("account_id", ""),
                    name=default_config.get("name", "Default"),
                    account_type=default_config.get("type", "main"),
                    equity=self.account_cache.get("equity", 0.0),
                    cash=self.account_cache.get("cash", 0.0),
                    buying_power=self.account_cache.get("buying_power", 0.0),
                    portfolio_value=self.account_cache.get("portfolio_value", 0.0),
                    pattern_day_trader=self.account_cache.get("pattern_day_trader", False),
                    trading_blocked=self.account_cache.get("trading_blocked", False),
                    account_blocked=self.account_cache.get("account_blocked", False),
                    currency=self.account_cache.get("currency", "USD")
                )
                self.accounts["default"] = account
                logger.info(
                    f"Account manager initialized: "
                    f"Equity=${account.equity:.2f}, Cash=${account.cash:.2f}"
                )
            else:
                logger.error("Failed to initialize account: no data from Alpaca")
                
        except Exception as e:
            logger.error(f"Failed to initialize account manager: {e}")
            raise

    def get_primary_account(self) -> Account:
        """Return the primary account."""
        return self.accounts.get("default")

    async def update_state(self) -> None:
        """Refresh account and position data from Alpaca."""
        try:
            # Retrieve account data from Alpaca
            self.account_cache = self.alpaca_client.get_account()
            
            # Retrieve positions from Alpaca
            self.positions_cache = self.alpaca_client.get_positions()
            
            # Update timestamp
            self.last_update = datetime.now()
            
            # Update Account object if it exists
            if "default" in self.accounts and self.account_cache:
                account = self.accounts["default"]
                account.equity = self.account_cache.get("equity", 0.0)
                account.cash = self.account_cache.get("cash", 0.0)
                account.buying_power = self.account_cache.get("buying_power", 0.0)
                account.portfolio_value = self.account_cache.get("portfolio_value", 0.0)
                account.pattern_day_trader = self.account_cache.get("pattern_day_trader", False)
                account.trading_blocked = self.account_cache.get("trading_blocked", False)
                account.account_blocked = self.account_cache.get("account_blocked", False)
            
            logger.debug(
                f"Account state updated: Equity=${self.account_cache.get('equity', 0):.2f}, "
                f"Positions={len(self.positions_cache)}"
            )
            
        except Exception as e:
            logger.error(f"Failed to update account state: {e}")
            # Don't raise - allow system to continue with stale data
    
    async def _ensure_fresh_data(self) -> None:
        """Update data if cache is stale."""
        if self.last_update is None:
            # No data yet, fetch it
            await self.update_state()
        elif (datetime.now() - self.last_update).total_seconds() > self.update_interval:
            # Cache is stale, refresh it
            await self.update_state()
    
    async def get_equity(self) -> float:
        """
        Get current account equity.
        
        Returns:
            Current equity as float
        """
        await self._ensure_fresh_data()
        if self.account_cache:
            return float(self.account_cache.get("equity", 0.0))
        return 0.0
    
    async def get_cash(self) -> float:
        """
        Get available cash.
        
        Returns:
            Available cash as float
        """
        await self._ensure_fresh_data()
        if self.account_cache:
            return float(self.account_cache.get("cash", 0.0))
        return 0.0
    
    async def get_buying_power(self) -> float:
        """
        Get buying power.
        
        Returns:
            Buying power as float
        """
        await self._ensure_fresh_data()
        if self.account_cache:
            return float(self.account_cache.get("buying_power", 0.0))
        return 0.0
    
    async def get_positions(self) -> List[Dict]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries
        """
        await self._ensure_fresh_data()
        return self.positions_cache
    
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get a specific position by symbol.
        
        Args:
            symbol: Symbol to retrieve position for
            
        Returns:
            Position dictionary or None if not found
        """
        await self._ensure_fresh_data()
        for position in self.positions_cache:
            if position["symbol"] == symbol:
                return position
        return None

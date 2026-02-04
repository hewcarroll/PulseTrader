"""Unit tests for AccountManager."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from services.orchestrator.account_manager import AccountManager, Account


class TestAccountManagerInitialization:
    """Test AccountManager initialization."""
    
    @pytest.mark.asyncio
    async def test_initialize_with_valid_data(self):
        """Test initialization with valid Alpaca data."""
        # Mock AlpacaClient
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test_account_123",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        # Create AccountManager
        config = {
            "accounts": {
                "default": {
                    "account_id": "test_account_123",
                    "name": "Test Account",
                    "type": "main"
                }
            }
        }
        account_manager = AccountManager(config, mock_alpaca_client)
        
        # Initialize
        await account_manager.initialize()
        
        # Verify account was created with correct data
        assert "default" in account_manager.accounts
        account = account_manager.accounts["default"]
        assert account.account_id == "test_account_123"
        assert account.name == "Test Account"
        assert account.account_type == "main"
        assert account.equity == 100000.0
        assert account.cash == 50000.0
        assert account.buying_power == 200000.0
        assert account.portfolio_value == 100000.0
        assert account.pattern_day_trader is False
        assert account.trading_blocked is False
        assert account.account_blocked is False
        assert account.currency == "USD"
        
        # Verify AlpacaClient was called
        mock_alpaca_client.get_account.assert_called_once()
        mock_alpaca_client.get_positions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_with_alpaca_error(self):
        """Test initialization when Alpaca API fails."""
        # Mock AlpacaClient that raises error
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.side_effect = Exception("API Error")
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        
        # Initialize should raise exception
        with pytest.raises(Exception, match="API Error"):
            await account_manager.initialize()


class TestAccountManagerCaching:
    """Test AccountManager caching behavior."""
    
    @pytest.mark.asyncio
    async def test_cache_is_used_within_ttl(self):
        """Test that cached data is used when fresh."""
        # Mock AlpacaClient
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        account_manager.update_interval = 30  # 30 second TTL
        
        # Initialize (first call)
        await account_manager.initialize()
        assert mock_alpaca_client.get_account.call_count == 1
        
        # Get equity (should use cache)
        equity = await account_manager.get_equity()
        assert equity == 100000.0
        assert mock_alpaca_client.get_account.call_count == 1  # No additional call
        
        # Get cash (should use cache)
        cash = await account_manager.get_cash()
        assert cash == 50000.0
        assert mock_alpaca_client.get_account.call_count == 1  # No additional call
    
    @pytest.mark.asyncio
    async def test_cache_is_refreshed_after_ttl(self):
        """Test that cache is refreshed when stale."""
        # Mock AlpacaClient
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        account_manager.update_interval = 1  # 1 second TTL for testing
        
        # Initialize
        await account_manager.initialize()
        assert mock_alpaca_client.get_account.call_count == 1
        
        # Wait for cache to expire
        import asyncio
        await asyncio.sleep(1.1)
        
        # Get equity (should refresh cache)
        equity = await account_manager.get_equity()
        assert equity == 100000.0
        assert mock_alpaca_client.get_account.call_count == 2  # Cache refreshed


class TestAccountManagerEquityAndCash:
    """Test equity and cash retrieval methods."""
    
    @pytest.mark.asyncio
    async def test_get_equity_returns_correct_value(self):
        """Test get_equity returns correct equity value."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 123456.78,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 123456.78,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        equity = await account_manager.get_equity()
        assert equity == 123456.78
    
    @pytest.mark.asyncio
    async def test_get_cash_returns_correct_value(self):
        """Test get_cash returns correct cash value."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 67890.12,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        cash = await account_manager.get_cash()
        assert cash == 67890.12
    
    @pytest.mark.asyncio
    async def test_get_buying_power_returns_correct_value(self):
        """Test get_buying_power returns correct buying power."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 250000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        buying_power = await account_manager.get_buying_power()
        assert buying_power == 250000.0
    
    @pytest.mark.asyncio
    async def test_get_equity_with_no_cache_returns_zero(self):
        """Test get_equity returns 0 when cache is empty."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = None
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        account_manager.account_cache = None
        
        equity = await account_manager.get_equity()
        assert equity == 0.0


class TestAccountManagerPositions:
    """Test position retrieval methods."""
    
    @pytest.mark.asyncio
    async def test_get_positions_returns_all_positions(self):
        """Test get_positions returns all open positions."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = [
            {
                "symbol": "AAPL",
                "qty": 100,
                "side": "long",
                "market_value": 15000.0,
                "cost_basis": 14000.0,
                "unrealized_pl": 1000.0,
                "unrealized_plpc": 0.0714,
                "current_price": 150.0,
                "avg_entry_price": 140.0,
                "asset_class": "us_equity"
            },
            {
                "symbol": "TSLA",
                "qty": 50,
                "side": "long",
                "market_value": 10000.0,
                "cost_basis": 9500.0,
                "unrealized_pl": 500.0,
                "unrealized_plpc": 0.0526,
                "current_price": 200.0,
                "avg_entry_price": 190.0,
                "asset_class": "us_equity"
            }
        ]
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        positions = await account_manager.get_positions()
        assert len(positions) == 2
        assert positions[0]["symbol"] == "AAPL"
        assert positions[0]["qty"] == 100
        assert positions[1]["symbol"] == "TSLA"
        assert positions[1]["qty"] == 50
    
    @pytest.mark.asyncio
    async def test_get_position_returns_specific_position(self):
        """Test get_position returns specific position by symbol."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = [
            {
                "symbol": "AAPL",
                "qty": 100,
                "side": "long",
                "market_value": 15000.0,
                "cost_basis": 14000.0,
                "unrealized_pl": 1000.0,
                "unrealized_plpc": 0.0714,
                "current_price": 150.0,
                "avg_entry_price": 140.0,
                "asset_class": "us_equity"
            },
            {
                "symbol": "TSLA",
                "qty": 50,
                "side": "long",
                "market_value": 10000.0,
                "cost_basis": 9500.0,
                "unrealized_pl": 500.0,
                "unrealized_plpc": 0.0526,
                "current_price": 200.0,
                "avg_entry_price": 190.0,
                "asset_class": "us_equity"
            }
        ]
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        position = await account_manager.get_position("AAPL")
        assert position is not None
        assert position["symbol"] == "AAPL"
        assert position["qty"] == 100
        assert position["current_price"] == 150.0
    
    @pytest.mark.asyncio
    async def test_get_position_returns_none_for_nonexistent_symbol(self):
        """Test get_position returns None for symbol not in positions."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = [
            {
                "symbol": "AAPL",
                "qty": 100,
                "side": "long",
                "market_value": 15000.0,
                "cost_basis": 14000.0,
                "unrealized_pl": 1000.0,
                "unrealized_plpc": 0.0714,
                "current_price": 150.0,
                "avg_entry_price": 140.0,
                "asset_class": "us_equity"
            }
        ]
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        position = await account_manager.get_position("MSFT")
        assert position is None
    
    @pytest.mark.asyncio
    async def test_get_positions_returns_empty_list_when_no_positions(self):
        """Test get_positions returns empty list when no positions exist."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 100000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        positions = await account_manager.get_positions()
        assert len(positions) == 0
        assert positions == []


class TestAccountManagerStateUpdate:
    """Test account state update functionality."""
    
    @pytest.mark.asyncio
    async def test_update_state_refreshes_account_data(self):
        """Test update_state refreshes account and position data."""
        mock_alpaca_client = Mock()
        
        # Initial data
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        # Change mock data
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 110000.0,
            "cash": 55000.0,
            "buying_power": 220000.0,
            "portfolio_value": 110000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        
        # Update state
        await account_manager.update_state()
        
        # Verify updated data
        assert account_manager.account_cache["equity"] == 110000.0
        assert account_manager.account_cache["cash"] == 55000.0
        assert account_manager.accounts["default"].equity == 110000.0
        assert account_manager.accounts["default"].cash == 55000.0
    
    @pytest.mark.asyncio
    async def test_update_state_handles_errors_gracefully(self):
        """Test update_state doesn't crash on API errors."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {"accounts": {"default": {}}}
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        # Make API fail
        mock_alpaca_client.get_account.side_effect = Exception("API Error")
        
        # Update should not raise exception
        await account_manager.update_state()
        
        # Old data should still be available
        assert account_manager.account_cache["equity"] == 100000.0


class TestAccountManagerGetPrimaryAccount:
    """Test get_primary_account method."""
    
    @pytest.mark.asyncio
    async def test_get_primary_account_returns_default_account(self):
        """Test get_primary_account returns the default account."""
        mock_alpaca_client = Mock()
        mock_alpaca_client.get_account.return_value = {
            "account_id": "test_123",
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "portfolio_value": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
            "currency": "USD"
        }
        mock_alpaca_client.get_positions.return_value = []
        
        config = {
            "accounts": {
                "default": {
                    "account_id": "test_123",
                    "name": "Primary Account",
                    "type": "main"
                }
            }
        }
        account_manager = AccountManager(config, mock_alpaca_client)
        await account_manager.initialize()
        
        primary_account = account_manager.get_primary_account()
        assert primary_account is not None
        assert primary_account.account_id == "test_123"
        assert primary_account.name == "Primary Account"
        assert primary_account.equity == 100000.0

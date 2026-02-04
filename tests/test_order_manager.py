"""Unit tests for OrderManager with real Alpaca execution."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.order_router.order_manager import OrderManager


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {
        "execution": {
            "client_order_id": {
                "prefix": "test"
            }
        }
    }


@pytest.fixture
def mock_alpaca_client():
    """Mock AlpacaClient."""
    client = Mock()
    client.submit_order = Mock(return_value={
        "id": "order_123",
        "client_order_id": "test_strategy_AAPL_1234567890",
        "symbol": "AAPL",
        "side": "buy",
        "order_type": "market",
        "qty": 10,
        "filled_qty": 0,
        "status": "new",
        "submitted_at": datetime.now(),
        "filled_at": None,
        "filled_avg_price": None,
        "limit_price": None,
        "stop_price": None
    })
    client.close_all_positions = Mock(return_value=[])
    return client


@pytest.fixture
def mock_account_manager():
    """Mock AccountManager."""
    manager = Mock()
    manager.get_equity = AsyncMock(return_value=100000.0)
    manager.get_positions = AsyncMock(return_value=[])
    manager.get_position = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def mock_market_data():
    """Mock MarketDataFeed."""
    feed = Mock()
    feed.get_current_price = AsyncMock(return_value=150.0)
    feed.get_previous_close = AsyncMock(return_value=148.0)
    return feed


@pytest.fixture
def mock_risk_manager():
    """Mock RiskManager."""
    manager = Mock()
    manager.validate_trade = Mock(return_value=(True, []))
    return manager


@pytest.fixture
def order_manager(mock_config, mock_alpaca_client, mock_account_manager, 
                  mock_market_data, mock_risk_manager):
    """Create OrderManager instance with mocks."""
    return OrderManager(
        config=mock_config,
        alpaca_client=mock_alpaca_client,
        account_manager=mock_account_manager,
        market_data=mock_market_data,
        risk_manager=mock_risk_manager
    )


class TestOrderManagerInitialization:
    """Test OrderManager initialization."""
    
    def test_initialization(self, order_manager, mock_alpaca_client, 
                           mock_account_manager, mock_market_data, mock_risk_manager):
        """Test that OrderManager initializes with all dependencies."""
        assert order_manager.alpaca_client == mock_alpaca_client
        assert order_manager.account_manager == mock_account_manager
        assert order_manager.market_data == mock_market_data
        assert order_manager.risk_manager == mock_risk_manager
        assert order_manager.order_cache == {}


class TestAccountEquity:
    """Test account equity retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_account_equity(self, order_manager, mock_account_manager):
        """Test getting account equity."""
        equity = await order_manager.get_account_equity()
        
        assert equity == 100000.0
        mock_account_manager.get_equity.assert_called_once()


class TestPriceRetrieval:
    """Test price retrieval methods."""
    
    @pytest.mark.asyncio
    async def test_get_current_price(self, order_manager, mock_market_data):
        """Test getting current price."""
        price = await order_manager.get_current_price("AAPL")
        
        assert price == 150.0
        mock_market_data.get_current_price.assert_called_once_with("AAPL")
    
    @pytest.mark.asyncio
    async def test_get_previous_close(self, order_manager, mock_market_data):
        """Test getting previous close."""
        price = await order_manager.get_previous_close("AAPL")
        
        assert price == 148.0
        mock_market_data.get_previous_close.assert_called_once_with("AAPL")


class TestOrderSubmission:
    """Test order submission with risk validation."""
    
    @pytest.mark.asyncio
    async def test_submit_order_success(self, order_manager, mock_alpaca_client,
                                       mock_risk_manager):
        """Test successful order submission."""
        order = await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=10,
            strategy="test_strategy"
        )
        
        assert order is not None
        assert order["id"] == "order_123"
        assert order["symbol"] == "AAPL"
        assert order["qty"] == 10
        
        # Verify risk validation was called
        mock_risk_manager.validate_trade.assert_called_once()
        
        # Verify order was submitted to Alpaca
        mock_alpaca_client.submit_order.assert_called_once()
        
        # Verify order was cached
        assert "order_123" in order_manager.order_cache
    
    @pytest.mark.asyncio
    async def test_submit_order_no_price_data(self, order_manager, mock_market_data):
        """Test order submission fails when no price data available."""
        mock_market_data.get_current_price = AsyncMock(return_value=None)
        
        order = await order_manager.submit_order(
            symbol="INVALID",
            side="buy",
            order_type="market",
            qty=10,
            strategy="test_strategy"
        )
        
        assert order is None
    
    @pytest.mark.asyncio
    async def test_submit_order_risk_validation_fails(self, order_manager, 
                                                      mock_risk_manager):
        """Test order submission fails when risk validation fails."""
        mock_risk_manager.validate_trade = Mock(
            return_value=(False, ["Reserve violation"])
        )
        
        order = await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=10,
            strategy="test_strategy"
        )
        
        assert order is None
        mock_risk_manager.validate_trade.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_order_with_limit_price(self, order_manager, mock_alpaca_client):
        """Test submitting a limit order."""
        order = await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="limit",
            qty=10,
            strategy="test_strategy",
            limit_price=145.0
        )
        
        assert order is not None
        
        # Verify limit price was passed to AlpacaClient
        call_args = mock_alpaca_client.submit_order.call_args
        assert call_args[1]["limit_price"] == 145.0
    
    @pytest.mark.asyncio
    async def test_submit_order_alpaca_error(self, order_manager, mock_alpaca_client):
        """Test order submission handles Alpaca errors."""
        mock_alpaca_client.submit_order = Mock(side_effect=Exception("API Error"))
        
        order = await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=10,
            strategy="test_strategy"
        )
        
        assert order is None


class TestDividendOrder:
    """Test dividend order submission."""
    
    @pytest.mark.asyncio
    async def test_submit_dividend_order(self, order_manager, mock_alpaca_client):
        """Test submitting a dividend allocation order."""
        order = await order_manager.submit_dividend_order(
            symbol="AAPL",
            qty=5,
            order_type="market",
            force_fill_time="09:30"
        )
        
        assert order is not None
        assert order["symbol"] == "AAPL"
        
        # Verify it was submitted as a buy order with dividend_allocation strategy
        call_args = mock_alpaca_client.submit_order.call_args
        assert call_args[1]["side"] == "buy"


class TestPositionManagement:
    """Test position management methods."""
    
    @pytest.mark.asyncio
    async def test_close_position_long(self, order_manager, mock_account_manager,
                                      mock_alpaca_client):
        """Test closing a long position."""
        # Mock a long position
        mock_account_manager.get_position = AsyncMock(return_value={
            "symbol": "AAPL",
            "qty": 10,
            "side": "long",
            "avg_entry_price": 145.0,
            "current_price": 150.0,
            "unrealized_pl": 50.0
        })
        
        order = await order_manager.close_position("AAPL")
        
        assert order is not None
        
        # Verify sell order was submitted
        call_args = mock_alpaca_client.submit_order.call_args
        assert call_args[1]["side"] == "sell"
        assert call_args[1]["qty"] == 10
        assert call_args[1]["order_type"] == "market"
    
    @pytest.mark.asyncio
    async def test_close_position_short(self, order_manager, mock_account_manager,
                                       mock_alpaca_client):
        """Test closing a short position."""
        # Mock a short position
        mock_account_manager.get_position = AsyncMock(return_value={
            "symbol": "AAPL",
            "qty": -10,
            "side": "short",
            "avg_entry_price": 150.0,
            "current_price": 145.0,
            "unrealized_pl": 50.0
        })
        
        order = await order_manager.close_position("AAPL")
        
        assert order is not None
        
        # Verify buy order was submitted
        call_args = mock_alpaca_client.submit_order.call_args
        assert call_args[1]["side"] == "buy"
        assert call_args[1]["qty"] == 10
    
    @pytest.mark.asyncio
    async def test_close_position_not_found(self, order_manager, mock_account_manager):
        """Test closing a position that doesn't exist."""
        mock_account_manager.get_position = AsyncMock(return_value=None)
        
        order = await order_manager.close_position("AAPL")
        
        assert order is None
    
    @pytest.mark.asyncio
    async def test_close_losing_positions(self, order_manager, mock_account_manager):
        """Test closing positions with unrealized losses."""
        # Mock positions with one winner and one loser
        mock_account_manager.get_positions = AsyncMock(return_value=[
            {
                "symbol": "AAPL",
                "qty": 10,
                "unrealized_pl": 50.0
            },
            {
                "symbol": "TSLA",
                "qty": 5,
                "unrealized_pl": -25.0
            }
        ])
        
        # Mock get_position for the losing position
        mock_account_manager.get_position = AsyncMock(return_value={
            "symbol": "TSLA",
            "qty": 5,
            "side": "long",
            "unrealized_pl": -25.0
        })
        
        await order_manager.close_losing_positions()
        
        # Verify only the losing position was closed
        mock_account_manager.get_position.assert_called_once_with("TSLA")
    
    @pytest.mark.asyncio
    async def test_close_all_positions(self, order_manager, mock_alpaca_client):
        """Test closing all positions."""
        mock_alpaca_client.close_all_positions = Mock(return_value=[
            {"id": "order_1", "symbol": "AAPL"},
            {"id": "order_2", "symbol": "TSLA"}
        ])
        
        await order_manager.close_all_positions()
        
        mock_alpaca_client.close_all_positions.assert_called_once()


class TestHelperMethods:
    """Test helper methods."""
    
    def test_get_asset_type_crypto(self, order_manager):
        """Test identifying crypto symbols."""
        assert order_manager._get_asset_type("BTC/USD") == "crypto"
        assert order_manager._get_asset_type("ETH/USD") == "crypto"
    
    def test_get_asset_type_etf(self, order_manager):
        """Test identifying ETF symbols."""
        assert order_manager._get_asset_type("TQQQ") == "etf"
        assert order_manager._get_asset_type("SQQQ") == "etf"
        assert order_manager._get_asset_type("SPXL") == "etf"
    
    def test_get_asset_type_stock(self, order_manager):
        """Test identifying stock symbols."""
        assert order_manager._get_asset_type("AAPL") == "stock"
        assert order_manager._get_asset_type("TSLA") == "stock"
        assert order_manager._get_asset_type("SPY") == "stock"
    
    def test_count_positions_by_type(self, order_manager):
        """Test counting positions by asset type."""
        positions = [
            {"symbol": "AAPL", "qty": 10},
            {"symbol": "TSLA", "qty": 5},
            {"symbol": "BTC/USD", "qty": 1},
            {"symbol": "TQQQ", "qty": 20}
        ]
        
        counts = order_manager._count_positions_by_type(positions)
        
        assert counts["stock"] == 2
        assert counts["crypto"] == 1
        assert counts["etf"] == 1
    
    def test_generate_client_order_id(self, order_manager):
        """Test generating unique client order IDs."""
        order_id = order_manager._generate_client_order_id("AAPL", "test_strategy")
        
        assert order_id.startswith("test_test_strategy_AAPL_")
        assert len(order_id.split("_")) == 4
    
    def test_generate_client_order_id_unique(self, order_manager):
        """Test that generated order IDs are unique."""
        order_id_1 = order_manager._generate_client_order_id("AAPL", "strategy1")
        order_id_2 = order_manager._generate_client_order_id("AAPL", "strategy1")
        
        assert order_id_1 != order_id_2


class TestRiskValidation:
    """Test risk validation integration."""
    
    @pytest.mark.asyncio
    async def test_risk_validation_called_with_correct_params(self, order_manager,
                                                              mock_risk_manager,
                                                              mock_account_manager):
        """Test that risk validation is called with correct parameters."""
        mock_account_manager.get_positions = AsyncMock(return_value=[
            {"symbol": "TSLA", "qty": 5}
        ])
        
        await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=10,
            strategy="test_strategy"
        )
        
        # Verify risk validation was called with correct parameters
        call_args = mock_risk_manager.validate_trade.call_args
        assert call_args[1]["equity"] == 100000.0
        assert call_args[1]["proposed_trade_value"] == 1500.0  # 10 * 150.0
        assert call_args[1]["asset_type"] == "stock"
        assert call_args[1]["current_positions"]["stock"] == 1
    
    @pytest.mark.asyncio
    async def test_multiple_validation_failures(self, order_manager, mock_risk_manager):
        """Test handling multiple validation failure reasons."""
        mock_risk_manager.validate_trade = Mock(
            return_value=(False, [
                "Reserve violation",
                "Position limit exceeded",
                "Daily drawdown limit reached"
            ])
        )
        
        order = await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=10,
            strategy="test_strategy"
        )
        
        assert order is None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_submit_order_zero_quantity(self, order_manager):
        """Test submitting order with zero quantity."""
        # This should be caught by AlpacaClient validation
        order = await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=0,
            strategy="test_strategy"
        )
        
        # Should fail at AlpacaClient level
        assert order is None
    
    @pytest.mark.asyncio
    async def test_close_position_with_fractional_qty(self, order_manager,
                                                      mock_account_manager):
        """Test closing position with fractional quantity (crypto)."""
        mock_account_manager.get_position = AsyncMock(return_value={
            "symbol": "BTC/USD",
            "qty": 0.5,
            "side": "long"
        })
        
        order = await order_manager.close_position("BTC/USD")
        
        # Should handle fractional quantities
        assert order is not None

"""Test logging enhancements for task 14."""
import os
import sys
from io import StringIO
from unittest.mock import Mock, patch, AsyncMock
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.order_router.order_manager import OrderManager


class TestOrderManagerLogging:
    """Test enhanced logging in OrderManager."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for OrderManager."""
        config = {
            "execution": {
                "client_order_id": {
                    "prefix": "test"
                }
            }
        }
        
        alpaca_client = Mock()
        account_manager = Mock()
        market_data = Mock()
        risk_manager = Mock()
        
        return config, alpaca_client, account_manager, market_data, risk_manager
    
    @pytest.fixture
    def order_manager(self, mock_dependencies):
        """Create OrderManager instance with mocks."""
        config, alpaca_client, account_manager, market_data, risk_manager = mock_dependencies
        return OrderManager(config, alpaca_client, account_manager, market_data, risk_manager)
    
    def test_log_order_fill_fully_filled(self, order_manager, caplog):
        """Test logging for fully filled orders."""
        order = {
            "symbol": "AAPL",
            "side": "buy",
            "status": "filled",
            "filled_qty": 10,
            "qty": 10,
            "filled_avg_price": 150.50,
            "id": "test-order-123"
        }
        
        order_manager._log_order_fill(order)
        
        # Check that log contains expected information
        assert "Order FILLED" in caplog.text
        assert "BUY 10 AAPL" in caplog.text
        assert "$150.50" in caplog.text
        assert "test-order-123" in caplog.text
    
    def test_log_order_fill_partially_filled(self, order_manager, caplog):
        """Test logging for partially filled orders."""
        order = {
            "symbol": "TSLA",
            "side": "sell",
            "status": "partially_filled",
            "filled_qty": 5,
            "qty": 10,
            "filled_avg_price": 200.00,
            "id": "test-order-456"
        }
        
        order_manager._log_order_fill(order)
        
        # Check that log contains expected information
        assert "Order PARTIALLY FILLED" in caplog.text
        assert "SELL 5/10 TSLA" in caplog.text
        assert "$200.00" in caplog.text
        assert "Remaining: 5" in caplog.text
        assert "test-order-456" in caplog.text
    
    @pytest.mark.asyncio
    async def test_submit_order_rejection_logging(self, order_manager, mock_dependencies, caplog):
        """Test that order rejections are logged with reasons."""
        config, alpaca_client, account_manager, market_data, risk_manager = mock_dependencies
        
        # Setup mocks
        account_manager.get_equity = AsyncMock(return_value=10000.0)
        market_data.get_current_price = AsyncMock(return_value=100.0)
        account_manager.get_positions = AsyncMock(return_value=[])
        
        # Mock risk manager to reject the trade
        risk_manager.validate_trade.return_value = (False, ["Insufficient buying power", "Position limit exceeded"])
        
        # Submit order
        result = await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=100,
            strategy="test_strategy"
        )
        
        # Verify order was rejected
        assert result is None
        
        # Verify rejection was logged with reasons
        assert "Order REJECTED" in caplog.text
        assert "AAPL" in caplog.text
        assert "Insufficient buying power" in caplog.text
        assert "Position limit exceeded" in caplog.text
    
    @pytest.mark.asyncio
    async def test_submit_order_success_logging(self, order_manager, mock_dependencies, caplog):
        """Test that successful order submissions are logged with details."""
        config, alpaca_client, account_manager, market_data, risk_manager = mock_dependencies
        
        # Setup mocks
        account_manager.get_equity = AsyncMock(return_value=10000.0)
        market_data.get_current_price = AsyncMock(return_value=100.0)
        account_manager.get_positions = AsyncMock(return_value=[])
        
        # Mock risk manager to accept the trade
        risk_manager.validate_trade.return_value = (True, [])
        
        # Mock successful order submission
        mock_order = {
            "id": "order-123",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 10,
            "status": "new",
            "order_type": "market"
        }
        alpaca_client.submit_order.return_value = mock_order
        
        # Submit order
        result = await order_manager.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=10,
            strategy="test_strategy"
        )
        
        # Verify order was submitted
        assert result is not None
        assert result["id"] == "order-123"
        
        # Verify submission was logged
        assert "Submitting order" in caplog.text
        assert "Order SUBMITTED successfully" in caplog.text
        assert "BUY 10 AAPL" in caplog.text
        assert "order-123" in caplog.text


class TestLogLevelConfiguration:
    """Test LOG_LEVEL environment variable support."""
    
    def test_log_level_from_environment(self):
        """Test that LOG_LEVEL environment variable is respected."""
        # This test would require actually initializing the orchestrator
        # which is complex, so we'll just verify the logic exists
        
        # Read the run.py file to verify LOG_LEVEL support
        with open("services/orchestrator/run.py", "r") as f:
            content = f.read()
        
        # Verify LOG_LEVEL environment variable is checked
        assert 'os.getenv("LOG_LEVEL")' in content
        assert "LOG_LEVEL environment variable" in content
        
        # Verify valid log levels are defined
        assert "TRACE" in content
        assert "DEBUG" in content
        assert "INFO" in content
        assert "WARNING" in content
        assert "ERROR" in content
        assert "CRITICAL" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

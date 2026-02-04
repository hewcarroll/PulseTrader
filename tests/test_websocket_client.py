"""Unit tests for WebSocketClient."""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from services.connectors.websocket_client import WebSocketClient


class TestWebSocketClientInitialization:
    """Test WebSocketClient initialization."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Store original env vars
        self.original_env = {}
        for var in ["ALPACA_PAPER_API_KEY", "ALPACA_PAPER_API_SECRET"]:
            self.original_env[var] = os.getenv(var)
    
    def teardown_method(self):
        """Restore environment after each test."""
        for var, value in self.original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value
    
    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        os.environ.pop("ALPACA_PAPER_API_KEY", None)
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        with pytest.raises(ValueError, match="Missing Alpaca API credentials for WebSocket"):
            WebSocketClient({})
    
    def test_missing_api_secret_raises_error(self):
        """Test that missing API secret raises ValueError."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ.pop("ALPACA_PAPER_API_SECRET", None)
        
        with pytest.raises(ValueError, match="Missing Alpaca API credentials for WebSocket"):
            WebSocketClient({})
    
    def test_empty_api_key_raises_error(self):
        """Test that empty API key raises ValueError."""
        os.environ["ALPACA_PAPER_API_KEY"] = ""
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        with pytest.raises(ValueError, match="Missing Alpaca API credentials for WebSocket"):
            WebSocketClient({})
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    def test_successful_initialization(self, mock_crypto_stream, mock_stock_stream):
        """Test successful initialization with valid credentials."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        client = WebSocketClient({})
        
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert "trade" in client.callbacks
        assert "quote" in client.callbacks
        assert "bar" in client.callbacks
        assert len(client.callbacks["trade"]) == 0
        assert len(client.callbacks["quote"]) == 0
        
        # Verify streams were initialized
        mock_stock_stream.assert_called_once_with("test_key", "test_secret")
        mock_crypto_stream.assert_called_once_with("test_key", "test_secret")


class TestWebSocketClientConnection:
    """Test WebSocketClient connection management."""
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    @pytest.mark.asyncio
    async def test_connect_succeeds(self, mock_crypto_stream, mock_stock_stream):
        """Test that connect() completes successfully."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        client = WebSocketClient({})
        await client.connect()
        
        # Should complete without error
        assert True
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    @pytest.mark.asyncio
    async def test_disconnect_closes_streams(self, mock_crypto_stream, mock_stock_stream):
        """Test that disconnect() closes both streams."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        # Setup mock streams with async close methods
        mock_stock_instance = MagicMock()
        mock_stock_instance.close = AsyncMock()
        mock_stock_stream.return_value = mock_stock_instance
        
        mock_crypto_instance = MagicMock()
        mock_crypto_instance.close = AsyncMock()
        mock_crypto_stream.return_value = mock_crypto_instance
        
        client = WebSocketClient({})
        await client.disconnect()
        
        # Verify both streams were closed
        mock_stock_instance.close.assert_called_once()
        mock_crypto_instance.close.assert_called_once()


class TestWebSocketClientSubscriptions:
    """Test WebSocketClient subscription methods."""
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    def test_subscribe_trades_stock_symbols(self, mock_crypto_stream, mock_stock_stream):
        """Test subscribing to stock trade updates."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        mock_stock_instance = MagicMock()
        mock_stock_stream.return_value = mock_stock_instance
        
        client = WebSocketClient({})
        callback = Mock()
        
        client.subscribe_trades(["AAPL", "TSLA"], callback)
        
        # Verify callback was registered
        assert callback in client.callbacks["trade"]
        
        # Verify stock stream subscription was called
        mock_stock_instance.subscribe_trades.assert_called_once()
        call_args = mock_stock_instance.subscribe_trades.call_args
        assert "AAPL" in call_args[0]
        assert "TSLA" in call_args[0]
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    def test_subscribe_trades_crypto_symbols(self, mock_crypto_stream, mock_stock_stream):
        """Test subscribing to crypto trade updates."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        mock_crypto_instance = MagicMock()
        mock_crypto_stream.return_value = mock_crypto_instance
        
        client = WebSocketClient({})
        callback = Mock()
        
        client.subscribe_trades(["BTC/USD", "ETH/USD"], callback)
        
        # Verify callback was registered
        assert callback in client.callbacks["trade"]
        
        # Verify crypto stream subscription was called
        mock_crypto_instance.subscribe_trades.assert_called_once()
        call_args = mock_crypto_instance.subscribe_trades.call_args
        assert "BTC/USD" in call_args[0]
        assert "ETH/USD" in call_args[0]
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    def test_subscribe_trades_mixed_symbols(self, mock_crypto_stream, mock_stock_stream):
        """Test subscribing to both stock and crypto trade updates."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        mock_stock_instance = MagicMock()
        mock_stock_stream.return_value = mock_stock_instance
        
        mock_crypto_instance = MagicMock()
        mock_crypto_stream.return_value = mock_crypto_instance
        
        client = WebSocketClient({})
        callback = Mock()
        
        client.subscribe_trades(["AAPL", "BTC/USD", "TSLA"], callback)
        
        # Verify callback was registered
        assert callback in client.callbacks["trade"]
        
        # Verify both streams were subscribed
        mock_stock_instance.subscribe_trades.assert_called_once()
        mock_crypto_instance.subscribe_trades.assert_called_once()
        
        # Verify correct symbols went to correct streams
        stock_call_args = mock_stock_instance.subscribe_trades.call_args[0]
        assert "AAPL" in stock_call_args
        assert "TSLA" in stock_call_args
        assert "BTC/USD" not in stock_call_args
        
        crypto_call_args = mock_crypto_instance.subscribe_trades.call_args[0]
        assert "BTC/USD" in crypto_call_args
        assert "AAPL" not in crypto_call_args
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    def test_subscribe_quotes_stock_symbols(self, mock_crypto_stream, mock_stock_stream):
        """Test subscribing to stock quote updates."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        mock_stock_instance = MagicMock()
        mock_stock_stream.return_value = mock_stock_instance
        
        client = WebSocketClient({})
        callback = Mock()
        
        client.subscribe_quotes(["AAPL", "TSLA"], callback)
        
        # Verify callback was registered
        assert callback in client.callbacks["quote"]
        
        # Verify stock stream subscription was called
        mock_stock_instance.subscribe_quotes.assert_called_once()
        call_args = mock_stock_instance.subscribe_quotes.call_args
        assert "AAPL" in call_args[0]
        assert "TSLA" in call_args[0]
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    def test_subscribe_quotes_crypto_symbols(self, mock_crypto_stream, mock_stock_stream):
        """Test subscribing to crypto quote updates."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        mock_crypto_instance = MagicMock()
        mock_crypto_stream.return_value = mock_crypto_instance
        
        client = WebSocketClient({})
        callback = Mock()
        
        client.subscribe_quotes(["BTC/USD", "ETH/USD"], callback)
        
        # Verify callback was registered
        assert callback in client.callbacks["quote"]
        
        # Verify crypto stream subscription was called
        mock_crypto_instance.subscribe_quotes.assert_called_once()
        call_args = mock_crypto_instance.subscribe_quotes.call_args
        assert "BTC/USD" in call_args[0]
        assert "ETH/USD" in call_args[0]


class TestWebSocketClientMessageHandlers:
    """Test WebSocketClient message handlers."""
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    @pytest.mark.asyncio
    async def test_trade_handler_parses_and_forwards(self, mock_crypto_stream, mock_stock_stream):
        """Test that trade handler parses data and invokes callbacks."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        client = WebSocketClient({})
        
        # Create mock callback
        callback = AsyncMock()
        client.callbacks["trade"].append(callback)
        
        # Create mock trade object
        mock_trade = Mock()
        mock_trade.symbol = "AAPL"
        mock_trade.price = 150.25
        mock_trade.size = 100
        mock_trade.timestamp = "2024-01-01T12:00:00Z"
        
        # Call handler
        await client._trade_handler(mock_trade)
        
        # Verify callback was invoked with correct data
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["symbol"] == "AAPL"
        assert call_args["price"] == 150.25
        assert call_args["size"] == 100
        assert call_args["timestamp"] == "2024-01-01T12:00:00Z"
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    @pytest.mark.asyncio
    async def test_quote_handler_parses_and_forwards(self, mock_crypto_stream, mock_stock_stream):
        """Test that quote handler parses data and invokes callbacks."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        client = WebSocketClient({})
        
        # Create mock callback
        callback = AsyncMock()
        client.callbacks["quote"].append(callback)
        
        # Create mock quote object
        mock_quote = Mock()
        mock_quote.symbol = "AAPL"
        mock_quote.bid_price = 150.20
        mock_quote.ask_price = 150.30
        mock_quote.bid_size = 100
        mock_quote.ask_size = 200
        mock_quote.timestamp = "2024-01-01T12:00:00Z"
        
        # Call handler
        await client._quote_handler(mock_quote)
        
        # Verify callback was invoked with correct data
        callback.assert_called_once()
        call_args = callback.call_args[0][0]
        assert call_args["symbol"] == "AAPL"
        assert call_args["bid_price"] == 150.20
        assert call_args["ask_price"] == 150.30
        assert call_args["bid_size"] == 100
        assert call_args["ask_size"] == 200
        assert call_args["timestamp"] == "2024-01-01T12:00:00Z"
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    @pytest.mark.asyncio
    async def test_trade_handler_handles_callback_errors(self, mock_crypto_stream, mock_stock_stream):
        """Test that trade handler continues when callback raises error."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        client = WebSocketClient({})
        
        # Create mock callbacks - one that fails, one that succeeds
        failing_callback = AsyncMock(side_effect=Exception("Callback error"))
        success_callback = AsyncMock()
        client.callbacks["trade"].append(failing_callback)
        client.callbacks["trade"].append(success_callback)
        
        # Create mock trade object
        mock_trade = Mock()
        mock_trade.symbol = "AAPL"
        mock_trade.price = 150.25
        mock_trade.size = 100
        mock_trade.timestamp = "2024-01-01T12:00:00Z"
        
        # Call handler - should not raise exception
        await client._trade_handler(mock_trade)
        
        # Verify both callbacks were called
        failing_callback.assert_called_once()
        success_callback.assert_called_once()
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    @pytest.mark.asyncio
    async def test_quote_handler_handles_callback_errors(self, mock_crypto_stream, mock_stock_stream):
        """Test that quote handler continues when callback raises error."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        client = WebSocketClient({})
        
        # Create mock callbacks - one that fails, one that succeeds
        failing_callback = AsyncMock(side_effect=Exception("Callback error"))
        success_callback = AsyncMock()
        client.callbacks["quote"].append(failing_callback)
        client.callbacks["quote"].append(success_callback)
        
        # Create mock quote object
        mock_quote = Mock()
        mock_quote.symbol = "AAPL"
        mock_quote.bid_price = 150.20
        mock_quote.ask_price = 150.30
        mock_quote.bid_size = 100
        mock_quote.ask_size = 200
        mock_quote.timestamp = "2024-01-01T12:00:00Z"
        
        # Call handler - should not raise exception
        await client._quote_handler(mock_quote)
        
        # Verify both callbacks were called
        failing_callback.assert_called_once()
        success_callback.assert_called_once()


class TestWebSocketClientRun:
    """Test WebSocketClient run method."""
    
    @patch('services.connectors.websocket_client.StockDataStream')
    @patch('services.connectors.websocket_client.CryptoDataStream')
    def test_run_starts_streams(self, mock_crypto_stream, mock_stock_stream):
        """Test that run() starts both streams."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        mock_stock_instance = MagicMock()
        mock_stock_stream.return_value = mock_stock_instance
        
        mock_crypto_instance = MagicMock()
        mock_crypto_stream.return_value = mock_crypto_instance
        
        client = WebSocketClient({})
        
        # Note: run() is blocking, so we just verify it calls the right methods
        # In a real scenario, this would be tested differently
        try:
            client.run()
        except:
            pass  # Expected to fail in test environment
        
        # Verify both streams' run methods were called
        mock_stock_instance.run.assert_called_once()
        mock_crypto_instance.run.assert_called_once()

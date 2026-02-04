"""Unit tests for AlpacaClient."""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.connectors.alpaca_client import AlpacaClient
from alpaca.common.exceptions import APIError


class TestAlpacaClientInitialization:
    """Test AlpacaClient initialization and authentication."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        # Store original env vars
        self.original_env = {}
        for var in ["ALPACA_PAPER_API_KEY", "ALPACA_PAPER_API_SECRET", "ALPACA_MODE"]:
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
        
        with pytest.raises(ValueError, match="Missing Alpaca API credentials"):
            AlpacaClient({})
    
    def test_missing_api_secret_raises_error(self):
        """Test that missing API secret raises ValueError."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ.pop("ALPACA_PAPER_API_SECRET", None)
        
        with pytest.raises(ValueError, match="Missing Alpaca API credentials"):
            AlpacaClient({})
    
    def test_empty_api_key_raises_error(self):
        """Test that empty API key raises ValueError."""
        os.environ["ALPACA_PAPER_API_KEY"] = ""
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        
        with pytest.raises(ValueError, match="Missing Alpaca API credentials"):
            AlpacaClient({})
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_successful_initialization_paper_mode(self, mock_crypto, mock_stock, mock_trading):
        """Test successful initialization in paper mode."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
        
        client = AlpacaClient({})
        
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert client.mode == "paper"
        assert client.is_paper is True
        
        # Verify clients were initialized
        mock_trading.assert_called_once_with(
            api_key="test_key",
            secret_key="test_secret",
            paper=True
        )
        mock_stock.assert_called_once()
        mock_crypto.assert_called_once()
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_successful_initialization_live_mode(self, mock_crypto, mock_stock, mock_trading):
        """Test successful initialization in live mode."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "live"
        
        client = AlpacaClient({})
        
        assert client.is_paper is False
        
        mock_trading.assert_called_once_with(
            api_key="test_key",
            secret_key="test_secret",
            paper=False
        )
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_default_paper_mode_when_not_specified(self, mock_crypto, mock_stock, mock_trading):
        """Test that paper mode is default when ALPACA_MODE not specified."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ.pop("ALPACA_MODE", None)
        
        client = AlpacaClient({})
        
        assert client.mode == "paper"
        assert client.is_paper is True


class TestAlpacaClientAccountData:
    """Test AlpacaClient account data retrieval methods."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_account_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful account data retrieval."""
        # Create mock account object
        mock_account = Mock()
        mock_account.id = "test_account_123"
        mock_account.equity = "100000.50"
        mock_account.cash = "50000.25"
        mock_account.buying_power = "200000.00"
        mock_account.portfolio_value = "100000.50"
        mock_account.pattern_day_trader = False
        mock_account.trading_blocked = False
        mock_account.account_blocked = False
        mock_account.currency = "USD"
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_account.return_value = mock_account
        
        client = AlpacaClient({})
        account_data = client.get_account()
        
        assert account_data["account_id"] == "test_account_123"
        assert account_data["equity"] == 100000.50
        assert account_data["cash"] == 50000.25
        assert account_data["buying_power"] == 200000.00
        assert account_data["portfolio_value"] == 100000.50
        assert account_data["pattern_day_trader"] is False
        assert account_data["trading_blocked"] is False
        assert account_data["account_blocked"] is False
        assert account_data["currency"] == "USD"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_account_api_error(self, mock_crypto, mock_stock, mock_trading):
        """Test get_account handles API errors."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_account.side_effect = APIError("API Error", status_code=500)
        
        client = AlpacaClient({})
        
        with pytest.raises(APIError):
            client.get_account()
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_positions_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful positions retrieval."""
        # Create mock position objects
        mock_position1 = Mock()
        mock_position1.symbol = "AAPL"
        mock_position1.qty = "10"
        mock_position1.side = "long"
        mock_position1.market_value = "1500.00"
        mock_position1.cost_basis = "1400.00"
        mock_position1.unrealized_pl = "100.00"
        mock_position1.unrealized_plpc = "0.0714"
        mock_position1.current_price = "150.00"
        mock_position1.avg_entry_price = "140.00"
        mock_position1.asset_class = "us_equity"
        
        mock_position2 = Mock()
        mock_position2.symbol = "BTC/USD"
        mock_position2.qty = "0.5"
        mock_position2.side = "long"
        mock_position2.market_value = "25000.00"
        mock_position2.cost_basis = "24000.00"
        mock_position2.unrealized_pl = "1000.00"
        mock_position2.unrealized_plpc = "0.0417"
        mock_position2.current_price = "50000.00"
        mock_position2.avg_entry_price = "48000.00"
        mock_position2.asset_class = "crypto"
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_all_positions.return_value = [mock_position1, mock_position2]
        
        client = AlpacaClient({})
        positions = client.get_positions()
        
        assert len(positions) == 2
        assert positions[0]["symbol"] == "AAPL"
        assert positions[0]["qty"] == 10
        assert positions[0]["side"] == "long"
        assert positions[1]["symbol"] == "BTC/USD"
        assert positions[1]["asset_class"] == "crypto"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_positions_empty(self, mock_crypto, mock_stock, mock_trading):
        """Test get_positions with no positions."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_all_positions.return_value = []
        
        client = AlpacaClient({})
        positions = client.get_positions()
        
        assert positions == []
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_position_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful single position retrieval."""
        mock_position = Mock()
        mock_position.symbol = "TSLA"
        mock_position.qty = "5"
        mock_position.side = "long"
        mock_position.market_value = "1000.00"
        mock_position.cost_basis = "950.00"
        mock_position.unrealized_pl = "50.00"
        mock_position.unrealized_plpc = "0.0526"
        mock_position.current_price = "200.00"
        mock_position.avg_entry_price = "190.00"
        mock_position.asset_class = "us_equity"
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_open_position.return_value = mock_position
        
        client = AlpacaClient({})
        position = client.get_position("TSLA")
        
        assert position is not None
        assert position["symbol"] == "TSLA"
        assert position["qty"] == 5
        assert position["current_price"] == 200.00
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_position_not_found(self, mock_crypto, mock_stock, mock_trading):
        """Test get_position returns None when position doesn't exist."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_open_position.side_effect = APIError("Not found", status_code=404)
        
        client = AlpacaClient({})
        position = client.get_position("NONEXISTENT")
        
        assert position is None
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_position_api_error(self, mock_crypto, mock_stock, mock_trading):
        """Test get_position handles non-404 API errors."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_open_position.side_effect = APIError("Server error", status_code=500)
        
        client = AlpacaClient({})
        
        with pytest.raises(APIError):
            client.get_position("AAPL")


class TestAlpacaClientErrorHandling:
    """Test AlpacaClient error handling."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_rate_limit_error(self, mock_crypto, mock_stock, mock_trading):
        """Test handling of rate limit errors."""
        mock_trading_instance = mock_trading.return_value
        rate_limit_error = APIError("Rate limit exceeded", status_code=429)
        mock_trading_instance.get_account.side_effect = rate_limit_error
        
        client = AlpacaClient({})
        
        with pytest.raises(APIError):
            client.get_account()
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_auth_error(self, mock_crypto, mock_stock, mock_trading):
        """Test handling of authentication errors."""
        mock_trading_instance = mock_trading.return_value
        auth_error = APIError("Unauthorized", status_code=401)
        mock_trading_instance.get_account.side_effect = auth_error
        
        client = AlpacaClient({})
        
        with pytest.raises(APIError):
            client.get_account()


class TestAlpacaClientMarketData:
    """Test AlpacaClient market data retrieval methods."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_bars_stock_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful stock bar data retrieval."""
        import pandas as pd
        from datetime import datetime
        
        # Create mock bar data
        mock_bars_data = {
            'open': [100.0, 101.0, 102.0],
            'high': [101.0, 102.0, 103.0],
            'low': [99.0, 100.0, 101.0],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000, 1100, 1200],
            'trade_count': [50, 55, 60],
            'vwap': [100.25, 101.25, 102.25]
        }
        mock_df = pd.DataFrame(mock_bars_data)
        
        # Create mock bars response
        mock_bars = Mock()
        mock_bars.df = mock_df
        mock_bars.__contains__ = lambda self, key: key == "AAPL"
        mock_bars.__getitem__ = lambda self, key: mock_df if key == "AAPL" else None
        
        mock_stock_instance = mock_stock.return_value
        mock_stock_instance.get_stock_bars.return_value = mock_bars
        
        client = AlpacaClient({})
        result = client.get_bars("AAPL", "1Min", limit=3)
        
        assert result is not None
        assert len(result) == 3
        assert 'close' in result.columns
        assert result['close'].iloc[0] == 100.5
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_bars_crypto_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful crypto bar data retrieval."""
        import pandas as pd
        
        # Create mock bar data
        mock_bars_data = {
            'open': [50000.0, 50100.0],
            'high': [50200.0, 50300.0],
            'low': [49900.0, 50000.0],
            'close': [50050.0, 50150.0],
            'volume': [10.5, 11.2],
            'trade_count': [100, 110],
            'vwap': [50025.0, 50125.0]
        }
        mock_df = pd.DataFrame(mock_bars_data)
        
        # Create mock bars response
        mock_bars = Mock()
        mock_bars.df = mock_df
        mock_bars.__contains__ = lambda self, key: key == "BTC/USD"
        mock_bars.__getitem__ = lambda self, key: mock_df if key == "BTC/USD" else None
        
        mock_crypto_instance = mock_crypto.return_value
        mock_crypto_instance.get_crypto_bars.return_value = mock_bars
        
        client = AlpacaClient({})
        result = client.get_bars("BTC/USD", "1Hour", limit=2)
        
        assert result is not None
        assert len(result) == 2
        assert result['close'].iloc[0] == 50050.0
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_bars_invalid_timeframe(self, mock_crypto, mock_stock, mock_trading):
        """Test get_bars with invalid timeframe."""
        client = AlpacaClient({})
        
        with pytest.raises(ValueError, match="Invalid timeframe"):
            client.get_bars("AAPL", "10Min")
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_bars_no_data(self, mock_crypto, mock_stock, mock_trading):
        """Test get_bars when no data is available."""
        mock_bars = Mock()
        mock_bars.__contains__ = lambda self, key: False
        
        mock_stock_instance = mock_stock.return_value
        mock_stock_instance.get_stock_bars.return_value = mock_bars
        
        client = AlpacaClient({})
        result = client.get_bars("INVALID", "1Day")
        
        assert result is None
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_latest_trade_stock_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful stock latest trade retrieval."""
        from datetime import datetime
        
        # Create mock trade
        mock_trade = Mock()
        mock_trade.price = 150.50
        mock_trade.size = 100
        mock_trade.timestamp = datetime.now()
        
        mock_trades = {"AAPL": mock_trade}
        
        mock_stock_instance = mock_stock.return_value
        mock_stock_instance.get_stock_latest_trade.return_value = mock_trades
        
        client = AlpacaClient({})
        result = client.get_latest_trade("AAPL")
        
        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["price"] == 150.50
        assert result["size"] == 100
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_latest_trade_crypto_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful crypto latest trade retrieval."""
        from datetime import datetime
        
        # Create mock trade
        mock_trade = Mock()
        mock_trade.price = 50000.50
        mock_trade.size = 0.5
        mock_trade.timestamp = datetime.now()
        
        mock_trades = {"BTC/USD": mock_trade}
        
        mock_crypto_instance = mock_crypto.return_value
        mock_crypto_instance.get_crypto_latest_trade.return_value = mock_trades
        
        client = AlpacaClient({})
        result = client.get_latest_trade("BTC/USD")
        
        assert result is not None
        assert result["symbol"] == "BTC/USD"
        assert result["price"] == 50000.50
        assert result["size"] == 0.5
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_latest_trade_no_data(self, mock_crypto, mock_stock, mock_trading):
        """Test get_latest_trade when no data is available."""
        mock_stock_instance = mock_stock.return_value
        mock_stock_instance.get_stock_latest_trade.return_value = {}
        
        client = AlpacaClient({})
        result = client.get_latest_trade("INVALID")
        
        assert result is None
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_latest_quote_stock_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful stock latest quote retrieval."""
        from datetime import datetime
        
        # Create mock quote
        mock_quote = Mock()
        mock_quote.bid_price = 150.00
        mock_quote.ask_price = 150.10
        mock_quote.bid_size = 100
        mock_quote.ask_size = 200
        mock_quote.timestamp = datetime.now()
        
        mock_quotes = {"AAPL": mock_quote}
        
        mock_stock_instance = mock_stock.return_value
        mock_stock_instance.get_stock_latest_quote.return_value = mock_quotes
        
        client = AlpacaClient({})
        result = client.get_latest_quote("AAPL")
        
        assert result is not None
        assert result["symbol"] == "AAPL"
        assert result["bid_price"] == 150.00
        assert result["ask_price"] == 150.10
        assert result["bid_size"] == 100
        assert result["ask_size"] == 200
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_latest_quote_crypto_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful crypto latest quote retrieval."""
        from datetime import datetime
        
        # Create mock quote
        mock_quote = Mock()
        mock_quote.bid_price = 50000.00
        mock_quote.ask_price = 50010.00
        mock_quote.bid_size = 0.5
        mock_quote.ask_size = 0.6
        mock_quote.timestamp = datetime.now()
        
        mock_quotes = {"BTC/USD": mock_quote}
        
        mock_crypto_instance = mock_crypto.return_value
        mock_crypto_instance.get_crypto_latest_quote.return_value = mock_quotes
        
        client = AlpacaClient({})
        result = client.get_latest_quote("BTC/USD")
        
        assert result is not None
        assert result["symbol"] == "BTC/USD"
        assert result["bid_price"] == 50000.00
        assert result["ask_price"] == 50010.00
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_previous_close_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful previous close retrieval."""
        import pandas as pd
        
        # Create mock bar data with 2 days
        mock_bars_data = {
            'open': [100.0, 101.0],
            'high': [101.0, 102.0],
            'low': [99.0, 100.0],
            'close': [100.5, 101.5],
            'volume': [1000, 1100],
            'trade_count': [50, 55],
            'vwap': [100.25, 101.25]
        }
        mock_df = pd.DataFrame(mock_bars_data)
        
        # Create mock bars response
        mock_bars = Mock()
        mock_bars.df = mock_df
        mock_bars.__contains__ = lambda self, key: key == "AAPL"
        mock_bars.__getitem__ = lambda self, key: mock_df if key == "AAPL" else None
        
        mock_stock_instance = mock_stock.return_value
        mock_stock_instance.get_stock_bars.return_value = mock_bars
        
        client = AlpacaClient({})
        result = client.get_previous_close("AAPL")
        
        assert result is not None
        assert result == 100.5  # Second-to-last close
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_previous_close_single_bar(self, mock_crypto, mock_stock, mock_trading):
        """Test previous close with only one bar available."""
        import pandas as pd
        
        # Create mock bar data with 1 day
        mock_bars_data = {
            'open': [100.0],
            'high': [101.0],
            'low': [99.0],
            'close': [100.5],
            'volume': [1000],
            'trade_count': [50],
            'vwap': [100.25]
        }
        mock_df = pd.DataFrame(mock_bars_data)
        
        # Create mock bars response
        mock_bars = Mock()
        mock_bars.df = mock_df
        mock_bars.__contains__ = lambda self, key: key == "AAPL"
        mock_bars.__getitem__ = lambda self, key: mock_df if key == "AAPL" else None
        
        mock_stock_instance = mock_stock.return_value
        mock_stock_instance.get_stock_bars.return_value = mock_bars
        
        client = AlpacaClient({})
        result = client.get_previous_close("AAPL")
        
        assert result is not None
        assert result == 100.5  # Use the single bar's close
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_previous_close_no_data(self, mock_crypto, mock_stock, mock_trading):
        """Test previous close when no data is available."""
        mock_bars = Mock()
        mock_bars.__contains__ = lambda self, key: False
        
        mock_stock_instance = mock_stock.return_value
        mock_stock_instance.get_stock_bars.return_value = mock_bars
        
        client = AlpacaClient({})
        result = client.get_previous_close("INVALID")
        
        assert result is None


class TestAlpacaClientOrderSubmission:
    """Test AlpacaClient order submission methods."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_market_order_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful market order submission."""
        from datetime import datetime
        from alpaca.trading.enums import OrderSide, OrderType, OrderStatus
        
        # Create mock order response
        mock_order = Mock()
        mock_order.id = "order_123"
        mock_order.client_order_id = "client_order_123"
        mock_order.symbol = "AAPL"
        mock_order.side = OrderSide.BUY
        mock_order.order_type = OrderType.MARKET
        mock_order.qty = 10
        mock_order.filled_qty = 0
        mock_order.status = OrderStatus.NEW
        mock_order.submitted_at = datetime.now()
        mock_order.filled_at = None
        mock_order.filled_avg_price = None
        mock_order.limit_price = None
        mock_order.stop_price = None
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.submit_order.return_value = mock_order
        
        client = AlpacaClient({})
        result = client.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=10,
            client_order_id="client_order_123"
        )
        
        assert result is not None
        assert result["id"] == "order_123"
        assert result["symbol"] == "AAPL"
        assert result["side"] == "buy"
        assert result["order_type"] == "market"
        assert result["qty"] == 10
        assert result["status"] == "new"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_limit_order_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful limit order submission."""
        from datetime import datetime
        from alpaca.trading.enums import OrderSide, OrderType, OrderStatus
        
        # Create mock order response
        mock_order = Mock()
        mock_order.id = "order_456"
        mock_order.client_order_id = "client_order_456"
        mock_order.symbol = "TSLA"
        mock_order.side = OrderSide.SELL
        mock_order.order_type = OrderType.LIMIT
        mock_order.qty = 5
        mock_order.filled_qty = 0
        mock_order.status = OrderStatus.NEW
        mock_order.submitted_at = datetime.now()
        mock_order.filled_at = None
        mock_order.filled_avg_price = None
        mock_order.limit_price = 250.00
        mock_order.stop_price = None
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.submit_order.return_value = mock_order
        
        client = AlpacaClient({})
        result = client.submit_order(
            symbol="TSLA",
            side="sell",
            order_type="limit",
            qty=5,
            limit_price=250.00
        )
        
        assert result is not None
        assert result["id"] == "order_456"
        assert result["symbol"] == "TSLA"
        assert result["side"] == "sell"
        assert result["order_type"] == "limit"
        assert result["limit_price"] == 250.00
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_stop_order_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful stop order submission."""
        from datetime import datetime
        from alpaca.trading.enums import OrderSide, OrderType, OrderStatus
        
        # Create mock order response
        mock_order = Mock()
        mock_order.id = "order_789"
        mock_order.client_order_id = None
        mock_order.symbol = "SPY"
        mock_order.side = OrderSide.BUY
        mock_order.order_type = OrderType.STOP
        mock_order.qty = 20
        mock_order.filled_qty = 0
        mock_order.status = OrderStatus.NEW
        mock_order.submitted_at = datetime.now()
        mock_order.filled_at = None
        mock_order.filled_avg_price = None
        mock_order.limit_price = None
        mock_order.stop_price = 450.00
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.submit_order.return_value = mock_order
        
        client = AlpacaClient({})
        result = client.submit_order(
            symbol="SPY",
            side="buy",
            order_type="stop",
            qty=20,
            stop_price=450.00
        )
        
        assert result is not None
        assert result["id"] == "order_789"
        assert result["order_type"] == "stop"
        assert result["stop_price"] == 450.00
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_order_invalid_side(self, mock_crypto, mock_stock, mock_trading):
        """Test order submission with invalid side."""
        client = AlpacaClient({})
        
        with pytest.raises(ValueError, match="Invalid order side"):
            client.submit_order(
                symbol="AAPL",
                side="invalid",
                order_type="market",
                qty=10
            )
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_order_invalid_type(self, mock_crypto, mock_stock, mock_trading):
        """Test order submission with invalid order type."""
        client = AlpacaClient({})
        
        with pytest.raises(ValueError, match="Invalid order type"):
            client.submit_order(
                symbol="AAPL",
                side="buy",
                order_type="invalid",
                qty=10
            )
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_order_invalid_quantity(self, mock_crypto, mock_stock, mock_trading):
        """Test order submission with invalid quantity."""
        client = AlpacaClient({})
        
        with pytest.raises(ValueError, match="Invalid quantity"):
            client.submit_order(
                symbol="AAPL",
                side="buy",
                order_type="market",
                qty=0
            )
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_limit_order_missing_price(self, mock_crypto, mock_stock, mock_trading):
        """Test limit order submission without limit price."""
        client = AlpacaClient({})
        
        with pytest.raises(ValueError, match="Limit price is required"):
            client.submit_order(
                symbol="AAPL",
                side="buy",
                order_type="limit",
                qty=10
            )
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_stop_order_missing_price(self, mock_crypto, mock_stock, mock_trading):
        """Test stop order submission without stop price."""
        client = AlpacaClient({})
        
        with pytest.raises(ValueError, match="Stop price is required"):
            client.submit_order(
                symbol="AAPL",
                side="buy",
                order_type="stop",
                qty=10
            )
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_submit_order_api_error(self, mock_crypto, mock_stock, mock_trading):
        """Test order submission with API error."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.submit_order.side_effect = APIError("Insufficient buying power", status_code=403)
        
        client = AlpacaClient({})
        result = client.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            qty=10
        )
        
        assert result is None


class TestAlpacaClientOrderManagement:
    """Test AlpacaClient order management methods."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_order_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful order retrieval."""
        from datetime import datetime
        from alpaca.trading.enums import OrderSide, OrderType, OrderStatus
        
        # Create mock order
        mock_order = Mock()
        mock_order.id = "order_123"
        mock_order.client_order_id = "client_123"
        mock_order.symbol = "AAPL"
        mock_order.side = OrderSide.BUY
        mock_order.order_type = OrderType.MARKET
        mock_order.qty = 10
        mock_order.filled_qty = 10
        mock_order.status = OrderStatus.FILLED
        mock_order.submitted_at = datetime.now()
        mock_order.filled_at = datetime.now()
        mock_order.filled_avg_price = 150.50
        mock_order.limit_price = None
        mock_order.stop_price = None
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_order_by_id.return_value = mock_order
        
        client = AlpacaClient({})
        result = client.get_order("order_123")
        
        assert result is not None
        assert result["id"] == "order_123"
        assert result["status"] == "filled"
        assert result["filled_qty"] == 10
        assert result["filled_avg_price"] == 150.50
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_order_not_found(self, mock_crypto, mock_stock, mock_trading):
        """Test get_order returns None when order doesn't exist."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_order_by_id.side_effect = APIError("Not found", status_code=404)
        
        client = AlpacaClient({})
        result = client.get_order("nonexistent")
        
        assert result is None
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_orders_open(self, mock_crypto, mock_stock, mock_trading):
        """Test retrieving open orders."""
        from datetime import datetime
        from alpaca.trading.enums import OrderSide, OrderType, OrderStatus
        
        # Create mock orders
        mock_order1 = Mock()
        mock_order1.id = "order_1"
        mock_order1.client_order_id = "client_1"
        mock_order1.symbol = "AAPL"
        mock_order1.side = OrderSide.BUY
        mock_order1.order_type = OrderType.LIMIT
        mock_order1.qty = 10
        mock_order1.filled_qty = 0
        mock_order1.status = OrderStatus.NEW
        mock_order1.submitted_at = datetime.now()
        mock_order1.filled_at = None
        mock_order1.filled_avg_price = None
        mock_order1.limit_price = 150.00
        mock_order1.stop_price = None
        
        mock_order2 = Mock()
        mock_order2.id = "order_2"
        mock_order2.client_order_id = "client_2"
        mock_order2.symbol = "TSLA"
        mock_order2.side = OrderSide.SELL
        mock_order2.order_type = OrderType.MARKET
        mock_order2.qty = 5
        mock_order2.filled_qty = 0
        mock_order2.status = OrderStatus.PENDING_NEW
        mock_order2.submitted_at = datetime.now()
        mock_order2.filled_at = None
        mock_order2.filled_avg_price = None
        mock_order2.limit_price = None
        mock_order2.stop_price = None
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.get_orders.return_value = [mock_order1, mock_order2]
        
        client = AlpacaClient({})
        result = client.get_orders(status="open")
        
        assert len(result) == 2
        assert result[0]["id"] == "order_1"
        assert result[1]["id"] == "order_2"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_get_orders_invalid_status(self, mock_crypto, mock_stock, mock_trading):
        """Test get_orders with invalid status."""
        client = AlpacaClient({})
        
        with pytest.raises(ValueError, match="Invalid status"):
            client.get_orders(status="invalid")
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_cancel_order_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful order cancellation."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.cancel_order_by_id.return_value = None
        
        client = AlpacaClient({})
        result = client.cancel_order("order_123")
        
        assert result is True
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_cancel_order_not_found(self, mock_crypto, mock_stock, mock_trading):
        """Test cancel_order when order doesn't exist."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.cancel_order_by_id.side_effect = APIError("Not found", status_code=404)
        
        client = AlpacaClient({})
        result = client.cancel_order("nonexistent")
        
        assert result is False
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_cancel_order_not_cancelable(self, mock_crypto, mock_stock, mock_trading):
        """Test cancel_order when order is not cancelable."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.cancel_order_by_id.side_effect = APIError("Not cancelable", status_code=422)
        
        client = AlpacaClient({})
        result = client.cancel_order("order_123")
        
        assert result is False


class TestAlpacaClientPositionClosing:
    """Test AlpacaClient position closing methods."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_close_position_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful position closing."""
        from datetime import datetime
        from alpaca.trading.enums import OrderSide, OrderType, OrderStatus
        
        # Create mock close order
        mock_order = Mock()
        mock_order.id = "close_order_123"
        mock_order.client_order_id = None
        mock_order.symbol = "AAPL"
        mock_order.side = OrderSide.SELL
        mock_order.order_type = OrderType.MARKET
        mock_order.qty = 10
        mock_order.filled_qty = 0
        mock_order.status = OrderStatus.NEW
        mock_order.submitted_at = datetime.now()
        mock_order.filled_at = None
        mock_order.filled_avg_price = None
        mock_order.limit_price = None
        mock_order.stop_price = None
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.close_position.return_value = mock_order
        
        client = AlpacaClient({})
        result = client.close_position("AAPL")
        
        assert result is not None
        assert result["id"] == "close_order_123"
        assert result["symbol"] == "AAPL"
        assert result["side"] == "sell"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_close_position_not_found(self, mock_crypto, mock_stock, mock_trading):
        """Test close_position when no position exists."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.close_position.side_effect = APIError("Not found", status_code=404)
        
        client = AlpacaClient({})
        result = client.close_position("NONEXISTENT")
        
        assert result is None
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_close_all_positions_success(self, mock_crypto, mock_stock, mock_trading):
        """Test successful closing of all positions."""
        from datetime import datetime
        from alpaca.trading.enums import OrderSide, OrderType, OrderStatus
        
        # Create mock close orders
        mock_order1 = Mock()
        mock_order1.id = "close_1"
        mock_order1.client_order_id = None
        mock_order1.symbol = "AAPL"
        mock_order1.side = OrderSide.SELL
        mock_order1.order_type = OrderType.MARKET
        mock_order1.qty = 10
        mock_order1.filled_qty = 0
        mock_order1.status = OrderStatus.NEW
        mock_order1.submitted_at = datetime.now()
        mock_order1.filled_at = None
        mock_order1.filled_avg_price = None
        mock_order1.limit_price = None
        mock_order1.stop_price = None
        
        mock_order2 = Mock()
        mock_order2.id = "close_2"
        mock_order2.client_order_id = None
        mock_order2.symbol = "TSLA"
        mock_order2.side = OrderSide.SELL
        mock_order2.order_type = OrderType.MARKET
        mock_order2.qty = 5
        mock_order2.filled_qty = 0
        mock_order2.status = OrderStatus.NEW
        mock_order2.submitted_at = datetime.now()
        mock_order2.filled_at = None
        mock_order2.filled_avg_price = None
        mock_order2.limit_price = None
        mock_order2.stop_price = None
        
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.close_all_positions.return_value = [mock_order1, mock_order2]
        
        client = AlpacaClient({})
        result = client.close_all_positions()
        
        assert len(result) == 2
        assert result[0]["id"] == "close_1"
        assert result[1]["id"] == "close_2"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_close_all_positions_empty(self, mock_crypto, mock_stock, mock_trading):
        """Test close_all_positions when no positions exist."""
        mock_trading_instance = mock_trading.return_value
        mock_trading_instance.close_all_positions.return_value = []
        
        client = AlpacaClient({})
        result = client.close_all_positions()
        
        assert result == []



class TestRetryStrategy:
    """Test RetryStrategy class for exponential backoff retry logic."""
    
    def test_retry_strategy_success_first_attempt(self):
        """Test that successful function executes without retry."""
        from services.connectors.alpaca_client import RetryStrategy
        
        retry_strategy = RetryStrategy(max_attempts=3, base_delay=0.1)
        
        # Mock function that succeeds
        mock_func = Mock(return_value="success")
        
        result = retry_strategy.execute(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_strategy_success_after_retries(self):
        """Test that function succeeds after retries."""
        from services.connectors.alpaca_client import RetryStrategy
        
        retry_strategy = RetryStrategy(max_attempts=3, base_delay=0.1)
        
        # Mock function that fails twice then succeeds
        mock_func = Mock(side_effect=[
            APIError("Temporary error", status_code=500),
            APIError("Temporary error", status_code=500),
            "success"
        ])
        
        result = retry_strategy.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retry_strategy_fails_after_max_attempts(self):
        """Test that function raises exception after max attempts."""
        from services.connectors.alpaca_client import RetryStrategy
        
        retry_strategy = RetryStrategy(max_attempts=3, base_delay=0.1)
        
        # Mock function that always fails
        mock_func = Mock(side_effect=APIError("Persistent error", status_code=500))
        
        with pytest.raises(APIError):
            retry_strategy.execute(mock_func)
        
        assert mock_func.call_count == 3
    
    def test_retry_strategy_no_retry_on_auth_error(self):
        """Test that authentication errors are not retried."""
        from services.connectors.alpaca_client import RetryStrategy
        
        retry_strategy = RetryStrategy(max_attempts=3, base_delay=0.1)
        
        # Mock function that raises auth error
        mock_func = Mock(side_effect=APIError("Unauthorized", status_code=401))
        
        with pytest.raises(APIError):
            retry_strategy.execute(mock_func)
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    def test_retry_strategy_no_retry_on_validation_error(self):
        """Test that validation errors (4xx except 429) are not retried."""
        from services.connectors.alpaca_client import RetryStrategy
        
        retry_strategy = RetryStrategy(max_attempts=3, base_delay=0.1)
        
        # Mock function that raises validation error
        mock_func = Mock(side_effect=APIError("Bad request", status_code=400))
        
        with pytest.raises(APIError):
            retry_strategy.execute(mock_func)
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    def test_retry_strategy_retries_rate_limit(self):
        """Test that rate limit errors are retried."""
        from services.connectors.alpaca_client import RetryStrategy
        
        retry_strategy = RetryStrategy(max_attempts=2, base_delay=0.1)
        
        # Mock function that fails with rate limit then succeeds
        mock_func = Mock(side_effect=[
            APIError("Rate limit", status_code=429),
            "success"
        ])
        
        result = retry_strategy.execute(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_retry_strategy_exponential_backoff(self):
        """Test that retry delays follow exponential backoff."""
        from services.connectors.alpaca_client import RetryStrategy
        import time
        
        retry_strategy = RetryStrategy(max_attempts=3, base_delay=0.1)
        
        # Mock function that fails twice
        mock_func = Mock(side_effect=[
            APIError("Error", status_code=500),
            APIError("Error", status_code=500),
            "success"
        ])
        
        start_time = time.time()
        result = retry_strategy.execute(mock_func)
        elapsed_time = time.time() - start_time
        
        # Should have delays of 0.1s and 0.2s = 0.3s total minimum
        assert elapsed_time >= 0.3
        assert result == "success"


class TestAlpacaClientRetryIntegration:
    """Test AlpacaClient integration with RetryStrategy."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_client_has_retry_strategy(self, mock_crypto, mock_stock, mock_trading):
        """Test that AlpacaClient initializes with RetryStrategy."""
        from services.connectors.alpaca_client import RetryStrategy
        
        client = AlpacaClient({})
        
        assert hasattr(client, 'retry_strategy')
        assert isinstance(client.retry_strategy, RetryStrategy)
        assert client.retry_strategy.max_attempts == 3
        assert client.retry_strategy.base_delay == 1.0


class TestAlpacaClientEnhancedErrorHandling:
    """Test enhanced error handling in AlpacaClient."""
    
    def setup_method(self):
        """Setup test environment before each test."""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["ALPACA_MODE"] = "paper"
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_rate_limit_error_logging(self, mock_crypto, mock_stock, mock_trading):
        """Test that rate limit errors are logged with warning level."""
        client = AlpacaClient({})
        
        error = APIError("Rate limit exceeded", status_code=429)
        
        # Should not raise, just log
        client._handle_api_error(error, "test_operation")
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_auth_error_logging(self, mock_crypto, mock_stock, mock_trading):
        """Test that authentication errors are logged with critical level."""
        client = AlpacaClient({})
        
        error = APIError("Unauthorized", status_code=401)
        
        # Should not raise, just log
        client._handle_api_error(error, "test_operation")
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_forbidden_error_logging(self, mock_crypto, mock_stock, mock_trading):
        """Test that forbidden errors are logged appropriately."""
        client = AlpacaClient({})
        
        error = APIError("Forbidden", status_code=403)
        
        # Should not raise, just log
        client._handle_api_error(error, "test_operation")
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_not_found_error_logging(self, mock_crypto, mock_stock, mock_trading):
        """Test that not found errors are logged with debug level."""
        client = AlpacaClient({})
        
        error = APIError("Not found", status_code=404)
        
        # Should not raise, just log
        client._handle_api_error(error, "test_operation")
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_validation_error_logging(self, mock_crypto, mock_stock, mock_trading):
        """Test that validation errors are logged appropriately."""
        client = AlpacaClient({})
        
        error = APIError("Validation failed", status_code=422)
        
        # Should not raise, just log
        client._handle_api_error(error, "test_operation")
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_server_error_logging(self, mock_crypto, mock_stock, mock_trading):
        """Test that server errors are logged appropriately."""
        client = AlpacaClient({})
        
        error = APIError("Internal server error", status_code=500)
        
        # Should not raise, just log
        client._handle_api_error(error, "test_operation")
    
    @patch('services.connectors.alpaca_client.TradingClient')
    @patch('services.connectors.alpaca_client.StockHistoricalDataClient')
    @patch('services.connectors.alpaca_client.CryptoHistoricalDataClient')
    def test_handle_network_error_logging(self, mock_crypto, mock_stock, mock_trading):
        """Test that network errors (no status code) are logged appropriately."""
        client = AlpacaClient({})
        
        # Create error without status_code attribute
        error = APIError("Network error")
        
        # Should not raise, just log
        client._handle_api_error(error, "test_operation")

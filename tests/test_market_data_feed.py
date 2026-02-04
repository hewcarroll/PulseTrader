"""Tests for MarketDataFeed with real Alpaca integration."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import pandas as pd

from services.data_feeds.market_data import MarketDataFeed


@pytest.fixture
def mock_alpaca_client():
    """Create a mock AlpacaClient for testing."""
    client = Mock()
    return client


@pytest.fixture
def market_data_feed(mock_alpaca_client):
    """Create a MarketDataFeed instance with mock AlpacaClient."""
    config = {}
    return MarketDataFeed(config, mock_alpaca_client)


@pytest.mark.asyncio
async def test_connect(market_data_feed):
    """Test that connect logs successfully."""
    await market_data_feed.connect()
    # Should not raise any exceptions


@pytest.mark.asyncio
async def test_disconnect(market_data_feed):
    """Test that disconnect logs successfully."""
    await market_data_feed.disconnect()
    # Should not raise any exceptions


@pytest.mark.asyncio
async def test_get_bars_success(market_data_feed, mock_alpaca_client):
    """Test successful bar data retrieval."""
    # Setup mock data
    mock_df = pd.DataFrame({
        'open': [100.0, 101.0],
        'high': [102.0, 103.0],
        'low': [99.0, 100.0],
        'close': [101.0, 102.0],
        'volume': [1000, 1100]
    })
    mock_alpaca_client.get_bars.return_value = mock_df
    
    # Call method
    result = await market_data_feed.get_bars("AAPL", "1Min", 50)
    
    # Verify
    assert result is not None
    assert len(result) == 2
    mock_alpaca_client.get_bars.assert_called_once_with("AAPL", "1Min", 50)


@pytest.mark.asyncio
async def test_get_bars_empty_dataframe(market_data_feed, mock_alpaca_client):
    """Test bar retrieval with empty DataFrame."""
    # Setup mock to return empty DataFrame
    mock_alpaca_client.get_bars.return_value = pd.DataFrame()
    
    # Call method
    result = await market_data_feed.get_bars("AAPL", "1Min", 50)
    
    # Verify
    assert result is None
    mock_alpaca_client.get_bars.assert_called_once_with("AAPL", "1Min", 50)


@pytest.mark.asyncio
async def test_get_bars_none_response(market_data_feed, mock_alpaca_client):
    """Test bar retrieval when AlpacaClient returns None."""
    # Setup mock to return None
    mock_alpaca_client.get_bars.return_value = None
    
    # Call method
    result = await market_data_feed.get_bars("INVALID", "1Min", 50)
    
    # Verify
    assert result is None
    mock_alpaca_client.get_bars.assert_called_once_with("INVALID", "1Min", 50)


@pytest.mark.asyncio
async def test_get_bars_exception(market_data_feed, mock_alpaca_client):
    """Test bar retrieval when exception occurs."""
    # Setup mock to raise exception
    mock_alpaca_client.get_bars.side_effect = Exception("API error")
    
    # Call method
    result = await market_data_feed.get_bars("AAPL", "1Min", 50)
    
    # Verify - should return None and log error
    assert result is None


@pytest.mark.asyncio
async def test_get_bars_crypto_symbol(market_data_feed, mock_alpaca_client):
    """Test bar retrieval for crypto symbol."""
    # Setup mock data
    mock_df = pd.DataFrame({
        'open': [50000.0, 50100.0],
        'high': [50200.0, 50300.0],
        'low': [49900.0, 50000.0],
        'close': [50100.0, 50200.0],
        'volume': [10.5, 11.2]
    })
    mock_alpaca_client.get_bars.return_value = mock_df
    
    # Call method
    result = await market_data_feed.get_bars("BTC/USD", "1Min", 50)
    
    # Verify
    assert result is not None
    assert len(result) == 2
    mock_alpaca_client.get_bars.assert_called_once_with("BTC/USD", "1Min", 50)


@pytest.mark.asyncio
async def test_get_current_price_from_trade(market_data_feed, mock_alpaca_client):
    """Test current price retrieval from latest trade."""
    # Setup mock trade data
    mock_alpaca_client.get_latest_trade.return_value = {
        "symbol": "AAPL",
        "price": 150.25,
        "size": 100,
        "timestamp": datetime.now()
    }
    
    # Call method
    result = await market_data_feed.get_current_price("AAPL")
    
    # Verify
    assert result == 150.25
    mock_alpaca_client.get_latest_trade.assert_called_once_with("AAPL")
    # Should not call get_latest_quote since trade was available
    mock_alpaca_client.get_latest_quote.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_price_from_quote(market_data_feed, mock_alpaca_client):
    """Test current price retrieval from quote when trade is unavailable."""
    # Setup mock to return None for trade, quote for fallback
    mock_alpaca_client.get_latest_trade.return_value = None
    mock_alpaca_client.get_latest_quote.return_value = {
        "symbol": "AAPL",
        "bid_price": 150.00,
        "ask_price": 150.50,
        "bid_size": 100,
        "ask_size": 100,
        "timestamp": datetime.now()
    }
    
    # Call method
    result = await market_data_feed.get_current_price("AAPL")
    
    # Verify - should return midpoint
    assert result == 150.25
    mock_alpaca_client.get_latest_trade.assert_called_once_with("AAPL")
    mock_alpaca_client.get_latest_quote.assert_called_once_with("AAPL")


@pytest.mark.asyncio
async def test_get_current_price_no_data(market_data_feed, mock_alpaca_client):
    """Test current price retrieval when no data is available."""
    # Setup mock to return None for both trade and quote
    mock_alpaca_client.get_latest_trade.return_value = None
    mock_alpaca_client.get_latest_quote.return_value = None
    
    # Call method
    result = await market_data_feed.get_current_price("INVALID")
    
    # Verify
    assert result is None
    mock_alpaca_client.get_latest_trade.assert_called_once_with("INVALID")
    mock_alpaca_client.get_latest_quote.assert_called_once_with("INVALID")


@pytest.mark.asyncio
async def test_get_current_price_exception(market_data_feed, mock_alpaca_client):
    """Test current price retrieval when exception occurs."""
    # Setup mock to raise exception
    mock_alpaca_client.get_latest_trade.side_effect = Exception("API error")
    
    # Call method
    result = await market_data_feed.get_current_price("AAPL")
    
    # Verify - should return None and log error
    assert result is None


@pytest.mark.asyncio
async def test_get_current_price_cache(market_data_feed, mock_alpaca_client):
    """Test that current price uses cache within TTL."""
    # Setup mock trade data
    mock_alpaca_client.get_latest_trade.return_value = {
        "symbol": "AAPL",
        "price": 150.25,
        "size": 100,
        "timestamp": datetime.now()
    }
    
    # First call - should hit API
    result1 = await market_data_feed.get_current_price("AAPL")
    assert result1 == 150.25
    assert mock_alpaca_client.get_latest_trade.call_count == 1
    
    # Second call immediately - should use cache
    result2 = await market_data_feed.get_current_price("AAPL")
    assert result2 == 150.25
    # Should still be 1 call (cached)
    assert mock_alpaca_client.get_latest_trade.call_count == 1


@pytest.mark.asyncio
async def test_get_current_price_crypto(market_data_feed, mock_alpaca_client):
    """Test current price retrieval for crypto symbol."""
    # Setup mock trade data
    mock_alpaca_client.get_latest_trade.return_value = {
        "symbol": "BTC/USD",
        "price": 50000.50,
        "size": 0.5,
        "timestamp": datetime.now()
    }
    
    # Call method
    result = await market_data_feed.get_current_price("BTC/USD")
    
    # Verify
    assert result == 50000.50
    mock_alpaca_client.get_latest_trade.assert_called_once_with("BTC/USD")


@pytest.mark.asyncio
async def test_get_previous_close_success(market_data_feed, mock_alpaca_client):
    """Test successful previous close retrieval."""
    # Setup mock data with 2 days of bars
    mock_df = pd.DataFrame({
        'open': [100.0, 101.0],
        'high': [102.0, 103.0],
        'low': [99.0, 100.0],
        'close': [101.0, 102.0],
        'volume': [1000, 1100]
    })
    mock_alpaca_client.get_bars.return_value = mock_df
    
    # Call method
    result = await market_data_feed.get_previous_close("AAPL")
    
    # Verify - should return second-to-last close (101.0)
    assert result == 101.0
    mock_alpaca_client.get_bars.assert_called_once_with("AAPL", "1Day", 2)


@pytest.mark.asyncio
async def test_get_previous_close_insufficient_data(market_data_feed, mock_alpaca_client):
    """Test previous close retrieval with insufficient data."""
    # Setup mock data with only 1 bar
    mock_df = pd.DataFrame({
        'open': [100.0],
        'high': [102.0],
        'low': [99.0],
        'close': [101.0],
        'volume': [1000]
    })
    mock_alpaca_client.get_bars.return_value = mock_df
    
    # Call method
    result = await market_data_feed.get_previous_close("AAPL")
    
    # Verify - should return None and log warning
    assert result is None


@pytest.mark.asyncio
async def test_get_previous_close_no_data(market_data_feed, mock_alpaca_client):
    """Test previous close retrieval when no data is available."""
    # Setup mock to return None
    mock_alpaca_client.get_bars.return_value = None
    
    # Call method
    result = await market_data_feed.get_previous_close("INVALID")
    
    # Verify
    assert result is None
    mock_alpaca_client.get_bars.assert_called_once_with("INVALID", "1Day", 2)


@pytest.mark.asyncio
async def test_get_previous_close_exception(market_data_feed, mock_alpaca_client):
    """Test previous close retrieval when exception occurs."""
    # Setup mock to raise exception
    mock_alpaca_client.get_bars.side_effect = Exception("API error")
    
    # Call method
    result = await market_data_feed.get_previous_close("AAPL")
    
    # Verify - should return None and log error
    assert result is None


@pytest.mark.asyncio
async def test_get_previous_close_crypto(market_data_feed, mock_alpaca_client):
    """Test previous close retrieval for crypto symbol."""
    # Setup mock data with 2 days of bars
    mock_df = pd.DataFrame({
        'open': [50000.0, 50100.0],
        'high': [50200.0, 50300.0],
        'low': [49900.0, 50000.0],
        'close': [50100.0, 50200.0],
        'volume': [10.5, 11.2]
    })
    mock_alpaca_client.get_bars.return_value = mock_df
    
    # Call method
    result = await market_data_feed.get_previous_close("BTC/USD")
    
    # Verify - should return second-to-last close (50100.0)
    assert result == 50100.0
    mock_alpaca_client.get_bars.assert_called_once_with("BTC/USD", "1Day", 2)


@pytest.mark.asyncio
async def test_multiple_timeframes(market_data_feed, mock_alpaca_client):
    """Test bar retrieval with different timeframes."""
    # Setup mock data
    mock_df = pd.DataFrame({
        'open': [100.0],
        'high': [102.0],
        'low': [99.0],
        'close': [101.0],
        'volume': [1000]
    })
    mock_alpaca_client.get_bars.return_value = mock_df
    
    # Test different timeframes
    timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
    for tf in timeframes:
        result = await market_data_feed.get_bars("AAPL", tf, 50)
        assert result is not None
    
    # Verify all timeframes were called
    assert mock_alpaca_client.get_bars.call_count == len(timeframes)


@pytest.mark.asyncio
async def test_initialization_with_config(mock_alpaca_client):
    """Test MarketDataFeed initialization with configuration."""
    config = {"some_key": "some_value"}
    feed = MarketDataFeed(config, mock_alpaca_client)
    
    assert feed.config == config
    assert feed.alpaca_client == mock_alpaca_client
    assert feed.cache_ttl == 5
    assert feed.price_cache == {}

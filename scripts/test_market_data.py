"""Integration test script for Alpaca market data retrieval.

This script verifies:
- Historical bar retrieval for stocks
- Historical bar retrieval for crypto
- Current price retrieval
- Multiple timeframes

Requirements: 11.3
"""
import os
import sys
import time
from datetime import datetime
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.connectors.alpaca_client import AlpacaClient


def test_stock_bars(client: AlpacaClient):
    """Test historical bar retrieval for stocks."""
    logger.info("=" * 60)
    logger.info("TEST 1: Stock Historical Bars")
    logger.info("=" * 60)
    
    test_symbols = ["AAPL", "TSLA", "SPY"]
    results = {}
    
    for symbol in test_symbols:
        try:
            start_time = time.time()
            bars = client.get_bars(symbol, "1Day", limit=5)
            elapsed = time.time() - start_time
            
            if bars is not None and not bars.empty:
                logger.success(f"✓ {symbol}: Retrieved {len(bars)} bars in {elapsed:.3f}s")
                logger.info(f"  Columns: {list(bars.columns)}")
                logger.info(f"  Latest close: ${bars['close'].iloc[-1]:.2f}")
                logger.info(f"  Date range: {bars.index[0]} to {bars.index[-1]}")
                results[symbol] = True
            else:
                logger.error(f"✗ {symbol}: No data returned")
                results[symbol] = False
                
        except Exception as e:
            logger.error(f"✗ {symbol}: Failed - {e}")
            results[symbol] = False
    
    passed = sum(1 for result in results.values() if result)
    logger.info(f"\nStock bars test: {passed}/{len(test_symbols)} symbols passed")
    return passed == len(test_symbols)


def test_crypto_bars(client: AlpacaClient):
    """Test historical bar retrieval for crypto."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Crypto Historical Bars")
    logger.info("=" * 60)
    
    test_symbols = ["BTC/USD", "ETH/USD"]
    results = {}
    
    for symbol in test_symbols:
        try:
            start_time = time.time()
            bars = client.get_bars(symbol, "1Hour", limit=5)
            elapsed = time.time() - start_time
            
            if bars is not None and not bars.empty:
                logger.success(f"✓ {symbol}: Retrieved {len(bars)} bars in {elapsed:.3f}s")
                logger.info(f"  Columns: {list(bars.columns)}")
                logger.info(f"  Latest close: ${bars['close'].iloc[-1]:.2f}")
                logger.info(f"  Date range: {bars.index[0]} to {bars.index[-1]}")
                results[symbol] = True
            else:
                logger.error(f"✗ {symbol}: No data returned")
                results[symbol] = False
                
        except Exception as e:
            logger.error(f"✗ {symbol}: Failed - {e}")
            results[symbol] = False
    
    passed = sum(1 for result in results.values() if result)
    logger.info(f"\nCrypto bars test: {passed}/{len(test_symbols)} symbols passed")
    return passed == len(test_symbols)


def test_current_price(client: AlpacaClient):
    """Test current price retrieval."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Current Price Retrieval")
    logger.info("=" * 60)
    
    test_symbols = ["AAPL", "TSLA", "BTC/USD"]
    results = {}
    
    for symbol in test_symbols:
        try:
            # Test latest trade
            start_time = time.time()
            trade = client.get_latest_trade(symbol)
            elapsed_trade = time.time() - start_time
            
            if trade:
                logger.success(f"✓ {symbol} (trade): ${trade['price']:.2f} in {elapsed_trade:.3f}s")
                logger.info(f"  Size: {trade['size']}")
                logger.info(f"  Timestamp: {trade['timestamp']}")
            else:
                logger.warning(f"⚠ {symbol}: No trade data, trying quote...")
            
            # Test latest quote as fallback
            start_time = time.time()
            quote = client.get_latest_quote(symbol)
            elapsed_quote = time.time() - start_time
            
            if quote:
                midpoint = (quote['bid_price'] + quote['ask_price']) / 2
                logger.success(f"✓ {symbol} (quote): ${midpoint:.2f} in {elapsed_quote:.3f}s")
                logger.info(f"  Bid: ${quote['bid_price']:.2f} x {quote['bid_size']}")
                logger.info(f"  Ask: ${quote['ask_price']:.2f} x {quote['ask_size']}")
                logger.info(f"  Spread: ${quote['ask_price'] - quote['bid_price']:.2f}")
                results[symbol] = True
            else:
                logger.error(f"✗ {symbol}: No quote data available")
                results[symbol] = False
                
        except Exception as e:
            logger.error(f"✗ {symbol}: Failed - {e}")
            results[symbol] = False
    
    passed = sum(1 for result in results.values() if result)
    logger.info(f"\nCurrent price test: {passed}/{len(test_symbols)} symbols passed")
    return passed == len(test_symbols)


def test_previous_close(client: AlpacaClient):
    """Test previous close retrieval."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Previous Close Retrieval")
    logger.info("=" * 60)
    
    test_symbols = ["AAPL", "TSLA", "SPY"]
    results = {}
    
    for symbol in test_symbols:
        try:
            start_time = time.time()
            prev_close = client.get_previous_close(symbol)
            elapsed = time.time() - start_time
            
            if prev_close is not None:
                logger.success(f"✓ {symbol}: ${prev_close:.2f} in {elapsed:.3f}s")
                results[symbol] = True
            else:
                logger.error(f"✗ {symbol}: No previous close data")
                results[symbol] = False
                
        except Exception as e:
            logger.error(f"✗ {symbol}: Failed - {e}")
            results[symbol] = False
    
    passed = sum(1 for result in results.values() if result)
    logger.info(f"\nPrevious close test: {passed}/{len(test_symbols)} symbols passed")
    return passed == len(test_symbols)


def test_multiple_timeframes(client: AlpacaClient):
    """Test multiple timeframes."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Multiple Timeframes")
    logger.info("=" * 60)
    
    symbol = "AAPL"
    timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
    results = {}
    
    for timeframe in timeframes:
        try:
            start_time = time.time()
            bars = client.get_bars(symbol, timeframe, limit=5)
            elapsed = time.time() - start_time
            
            if bars is not None and not bars.empty:
                logger.success(f"✓ {timeframe}: Retrieved {len(bars)} bars in {elapsed:.3f}s")
                logger.info(f"  Latest close: ${bars['close'].iloc[-1]:.2f}")
                results[timeframe] = True
            else:
                logger.error(f"✗ {timeframe}: No data returned")
                results[timeframe] = False
                
        except Exception as e:
            logger.error(f"✗ {timeframe}: Failed - {e}")
            results[timeframe] = False
    
    passed = sum(1 for result in results.values() if result)
    logger.info(f"\nTimeframe test: {passed}/{len(timeframes)} timeframes passed")
    return passed == len(timeframes)


def test_data_format_consistency(client: AlpacaClient):
    """Test that bar data format is consistent."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Data Format Consistency")
    logger.info("=" * 60)
    
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    test_cases = [
        ("AAPL", "1Day"),
        ("TSLA", "1Hour"),
        ("BTC/USD", "1Hour")
    ]
    
    results = {}
    
    for symbol, timeframe in test_cases:
        try:
            bars = client.get_bars(symbol, timeframe, limit=5)
            
            if bars is not None and not bars.empty:
                # Check required columns
                missing_cols = [col for col in required_columns if col not in bars.columns]
                
                if missing_cols:
                    logger.error(f"✗ {symbol} ({timeframe}): Missing columns: {missing_cols}")
                    results[f"{symbol}_{timeframe}"] = False
                else:
                    logger.success(f"✓ {symbol} ({timeframe}): All required columns present")
                    logger.info(f"  Columns: {list(bars.columns)}")
                    
                    # Verify data types
                    for col in required_columns:
                        if col == 'volume':
                            logger.info(f"  {col}: {bars[col].dtype}")
                        else:
                            logger.info(f"  {col}: {bars[col].dtype}")
                    
                    results[f"{symbol}_{timeframe}"] = True
            else:
                logger.error(f"✗ {symbol} ({timeframe}): No data returned")
                results[f"{symbol}_{timeframe}"] = False
                
        except Exception as e:
            logger.error(f"✗ {symbol} ({timeframe}): Failed - {e}")
            results[f"{symbol}_{timeframe}"] = False
    
    passed = sum(1 for result in results.values() if result)
    logger.info(f"\nFormat consistency test: {passed}/{len(test_cases)} cases passed")
    return passed == len(test_cases)


def main():
    """Run all market data tests."""
    logger.info("Alpaca Market Data Test")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Initialize client
    try:
        client = AlpacaClient({})
        logger.success("✓ AlpacaClient initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize AlpacaClient: {e}")
        sys.exit(1)
    
    # Track test results
    results = {}
    
    # Test 1: Stock bars
    results['stock_bars'] = test_stock_bars(client)
    
    # Test 2: Crypto bars
    results['crypto_bars'] = test_crypto_bars(client)
    
    # Test 3: Current price
    results['current_price'] = test_current_price(client)
    
    # Test 4: Previous close
    results['previous_close'] = test_previous_close(client)
    
    # Test 5: Multiple timeframes
    results['multiple_timeframes'] = test_multiple_timeframes(client)
    
    # Test 6: Data format consistency
    results['format_consistency'] = test_data_format_consistency(client)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("\n✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"\n✗ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

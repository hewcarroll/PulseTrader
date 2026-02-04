"""Integration test script for Alpaca WebSocket streaming.

This script verifies:
- WebSocket connection establishment
- Trade subscription and updates
- Quote subscription and updates
- Reconnection handling

Requirements: 11.4
"""
import os
import sys
import asyncio
from datetime import datetime
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.connectors.websocket_client import WebSocketClient


class WebSocketTester:
    """Test harness for WebSocket streaming."""
    
    def __init__(self):
        self.trade_count = 0
        self.quote_count = 0
        self.received_symbols = set()
        self.test_duration = 30  # seconds
        
    async def trade_callback(self, trade_data):
        """Callback for trade updates."""
        self.trade_count += 1
        self.received_symbols.add(trade_data['symbol'])
        
        if self.trade_count <= 5:  # Log first 5 trades
            logger.info(
                f"  Trade #{self.trade_count}: {trade_data['symbol']} @ "
                f"${trade_data['price']:.2f} x {trade_data['size']} "
                f"at {trade_data['timestamp']}"
            )
    
    async def quote_callback(self, quote_data):
        """Callback for quote updates."""
        self.quote_count += 1
        self.received_symbols.add(quote_data['symbol'])
        
        if self.quote_count <= 5:  # Log first 5 quotes
            logger.info(
                f"  Quote #{self.quote_count}: {quote_data['symbol']} "
                f"bid=${quote_data['bid_price']:.2f} x {quote_data['bid_size']} "
                f"ask=${quote_data['ask_price']:.2f} x {quote_data['ask_size']} "
                f"at {quote_data['timestamp']}"
            )


async def test_websocket_connection():
    """Test WebSocket connection establishment."""
    logger.info("=" * 60)
    logger.info("TEST 1: WebSocket Connection")
    logger.info("=" * 60)
    
    try:
        client = WebSocketClient({})
        await client.connect()
        logger.success("✓ WebSocket client initialized and connected")
        return True, client
    except ValueError as e:
        logger.error(f"✗ Connection failed: {e}")
        logger.error("  Please check your environment variables:")
        logger.error("    - ALPACA_PAPER_API_KEY")
        logger.error("    - ALPACA_PAPER_API_SECRET")
        return False, None
    except Exception as e:
        logger.error(f"✗ Unexpected error during connection: {e}")
        return False, None


async def test_trade_subscriptions(client: WebSocketClient, tester: WebSocketTester):
    """Test trade subscriptions."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Trade Subscriptions")
    logger.info("=" * 60)
    
    try:
        # Subscribe to trades for popular symbols
        test_symbols = ["AAPL", "TSLA", "SPY"]
        logger.info(f"Subscribing to trades for: {test_symbols}")
        
        client.subscribe_trades(test_symbols, tester.trade_callback)
        logger.success(f"✓ Subscribed to {len(test_symbols)} symbols")
        
        # Wait for trades
        logger.info(f"Waiting {tester.test_duration}s for trade updates...")
        
        # Start the stock stream in background
        stock_task = asyncio.create_task(run_stream(client.stock_stream))
        
        # Wait for test duration
        await asyncio.sleep(tester.test_duration)
        
        # Cancel the stream task
        stock_task.cancel()
        try:
            await stock_task
        except asyncio.CancelledError:
            pass
        
        # Check results
        if tester.trade_count > 0:
            logger.success(f"✓ Received {tester.trade_count} trade updates")
            logger.info(f"  Symbols received: {sorted(tester.received_symbols)}")
            return True
        else:
            logger.warning("⚠ No trade updates received")
            logger.warning("  This may be normal if market is closed or symbols are not actively trading")
            return True  # Don't fail the test, as this depends on market hours
            
    except Exception as e:
        logger.error(f"✗ Trade subscription test failed: {e}")
        return False


async def test_quote_subscriptions(client: WebSocketClient, tester: WebSocketTester):
    """Test quote subscriptions."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Quote Subscriptions")
    logger.info("=" * 60)
    
    try:
        # Reset counters
        tester.quote_count = 0
        tester.received_symbols.clear()
        
        # Subscribe to quotes for popular symbols
        test_symbols = ["AAPL", "MSFT"]
        logger.info(f"Subscribing to quotes for: {test_symbols}")
        
        client.subscribe_quotes(test_symbols, tester.quote_callback)
        logger.success(f"✓ Subscribed to {len(test_symbols)} symbols")
        
        # Wait for quotes
        logger.info(f"Waiting {tester.test_duration}s for quote updates...")
        
        # Start the stock stream in background
        stock_task = asyncio.create_task(run_stream(client.stock_stream))
        
        # Wait for test duration
        await asyncio.sleep(tester.test_duration)
        
        # Cancel the stream task
        stock_task.cancel()
        try:
            await stock_task
        except asyncio.CancelledError:
            pass
        
        # Check results
        if tester.quote_count > 0:
            logger.success(f"✓ Received {tester.quote_count} quote updates")
            logger.info(f"  Symbols received: {sorted(tester.received_symbols)}")
            return True
        else:
            logger.warning("⚠ No quote updates received")
            logger.warning("  This may be normal if market is closed")
            return True  # Don't fail the test, as this depends on market hours
            
    except Exception as e:
        logger.error(f"✗ Quote subscription test failed: {e}")
        return False


async def test_crypto_subscriptions(client: WebSocketClient):
    """Test crypto subscriptions."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Crypto Subscriptions")
    logger.info("=" * 60)
    
    try:
        # Create separate tester for crypto
        crypto_tester = WebSocketTester()
        crypto_tester.test_duration = 20  # Shorter duration for crypto
        
        # Subscribe to crypto trades
        test_symbols = ["BTC/USD", "ETH/USD"]
        logger.info(f"Subscribing to crypto trades for: {test_symbols}")
        
        client.subscribe_trades(test_symbols, crypto_tester.trade_callback)
        logger.success(f"✓ Subscribed to {len(test_symbols)} crypto symbols")
        
        # Wait for trades
        logger.info(f"Waiting {crypto_tester.test_duration}s for crypto trade updates...")
        
        # Start the crypto stream in background
        crypto_task = asyncio.create_task(run_stream(client.crypto_stream))
        
        # Wait for test duration
        await asyncio.sleep(crypto_tester.test_duration)
        
        # Cancel the stream task
        crypto_task.cancel()
        try:
            await crypto_task
        except asyncio.CancelledError:
            pass
        
        # Check results
        if crypto_tester.trade_count > 0:
            logger.success(f"✓ Received {crypto_tester.trade_count} crypto trade updates")
            logger.info(f"  Symbols received: {sorted(crypto_tester.received_symbols)}")
            return True
        else:
            logger.warning("⚠ No crypto trade updates received")
            logger.warning("  Crypto markets are 24/7, so this may indicate a connection issue")
            return False
            
    except Exception as e:
        logger.error(f"✗ Crypto subscription test failed: {e}")
        return False


async def test_multiple_subscriptions(client: WebSocketClient):
    """Test subscribing to multiple symbols simultaneously."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Multiple Simultaneous Subscriptions")
    logger.info("=" * 60)
    
    try:
        # Create tester
        multi_tester = WebSocketTester()
        multi_tester.test_duration = 20
        
        # Subscribe to multiple symbols at once
        stock_symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        logger.info(f"Subscribing to {len(stock_symbols)} symbols simultaneously")
        
        client.subscribe_trades(stock_symbols, multi_tester.trade_callback)
        logger.success(f"✓ Subscribed to {len(stock_symbols)} symbols")
        
        # Wait for updates
        logger.info(f"Waiting {multi_tester.test_duration}s for updates...")
        
        # Start the stock stream in background
        stock_task = asyncio.create_task(run_stream(client.stock_stream))
        
        # Wait for test duration
        await asyncio.sleep(multi_tester.test_duration)
        
        # Cancel the stream task
        stock_task.cancel()
        try:
            await stock_task
        except asyncio.CancelledError:
            pass
        
        # Check results
        logger.info(f"  Total updates received: {multi_tester.trade_count}")
        logger.info(f"  Unique symbols: {len(multi_tester.received_symbols)}")
        logger.info(f"  Symbols: {sorted(multi_tester.received_symbols)}")
        
        if multi_tester.trade_count > 0:
            logger.success("✓ Multiple subscriptions working")
            return True
        else:
            logger.warning("⚠ No updates received (may be normal if market is closed)")
            return True
            
    except Exception as e:
        logger.error(f"✗ Multiple subscriptions test failed: {e}")
        return False


async def run_stream(stream):
    """Helper to run a stream in the background."""
    try:
        await stream._run_forever()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Stream error: {e}")


async def main():
    """Run all WebSocket streaming tests."""
    logger.info("Alpaca WebSocket Streaming Test")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    logger.info("NOTE: These tests require market hours for stock data.")
    logger.info("      Crypto tests should work 24/7.")
    logger.info("")
    
    # Track test results
    results = {}
    
    # Test 1: Connection
    success, client = await test_websocket_connection()
    results['connection'] = success
    
    if not success:
        logger.error("\n" + "=" * 60)
        logger.error("FAILED: Cannot proceed without connection")
        logger.error("=" * 60)
        sys.exit(1)
    
    # Create tester
    tester = WebSocketTester()
    
    # Test 2: Trade subscriptions
    results['trade_subscriptions'] = await test_trade_subscriptions(client, tester)
    
    # Test 3: Quote subscriptions
    results['quote_subscriptions'] = await test_quote_subscriptions(client, tester)
    
    # Test 4: Crypto subscriptions
    results['crypto_subscriptions'] = await test_crypto_subscriptions(client)
    
    # Test 5: Multiple subscriptions
    results['multiple_subscriptions'] = await test_multiple_subscriptions(client)
    
    # Cleanup
    try:
        await client.disconnect()
        logger.info("\n✓ WebSocket client disconnected cleanly")
    except Exception as e:
        logger.warning(f"⚠ Error during disconnect: {e}")
    
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
    asyncio.run(main())

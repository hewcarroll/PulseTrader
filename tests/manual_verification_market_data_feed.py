"""Manual verification script for MarketDataFeed with real Alpaca integration.

This script tests the MarketDataFeed implementation with real Alpaca API calls.
It requires valid ALPACA_PAPER_API_KEY and ALPACA_PAPER_API_SECRET in .env file.

Usage:
    python tests/manual_verification_market_data_feed.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger

from services.connectors.alpaca_client import AlpacaClient
from services.data_feeds.market_data import MarketDataFeed


async def test_market_data_feed():
    """Test MarketDataFeed with real Alpaca API."""
    
    # Load environment variables
    load_dotenv()
    
    # Check for required credentials
    if not os.getenv("ALPACA_PAPER_API_KEY") or not os.getenv("ALPACA_PAPER_API_SECRET"):
        logger.error("Missing Alpaca API credentials in .env file")
        logger.error("Please set ALPACA_PAPER_API_KEY and ALPACA_PAPER_API_SECRET")
        return False
    
    try:
        # Initialize clients
        config = {}
        alpaca_client = AlpacaClient(config)
        market_data_feed = MarketDataFeed(config, alpaca_client)
        
        logger.info("=" * 60)
        logger.info("MarketDataFeed Manual Verification")
        logger.info("=" * 60)
        
        # Test 1: Connect
        logger.info("\n[Test 1] Testing connect...")
        await market_data_feed.connect()
        logger.success("✓ Connect successful")
        
        # Test 2: Get bars for stock
        logger.info("\n[Test 2] Testing get_bars for stock (AAPL)...")
        bars = await market_data_feed.get_bars("AAPL", "1Min", 10)
        if bars is not None and not bars.empty:
            logger.success(f"✓ Retrieved {len(bars)} bars for AAPL")
            logger.info(f"  Latest bar: {bars.iloc[-1].to_dict()}")
        else:
            logger.warning("⚠ No bar data for AAPL (market may be closed)")
        
        # Test 3: Get bars for crypto
        logger.info("\n[Test 3] Testing get_bars for crypto (BTC/USD)...")
        bars = await market_data_feed.get_bars("BTC/USD", "1Min", 10)
        if bars is not None and not bars.empty:
            logger.success(f"✓ Retrieved {len(bars)} bars for BTC/USD")
            logger.info(f"  Latest bar: {bars.iloc[-1].to_dict()}")
        else:
            logger.warning("⚠ No bar data for BTC/USD")
        
        # Test 4: Get current price for stock
        logger.info("\n[Test 4] Testing get_current_price for stock (AAPL)...")
        price = await market_data_feed.get_current_price("AAPL")
        if price is not None:
            logger.success(f"✓ Current price for AAPL: ${price:.2f}")
        else:
            logger.warning("⚠ No price data for AAPL (market may be closed)")
        
        # Test 5: Get current price for crypto
        logger.info("\n[Test 5] Testing get_current_price for crypto (BTC/USD)...")
        price = await market_data_feed.get_current_price("BTC/USD")
        if price is not None:
            logger.success(f"✓ Current price for BTC/USD: ${price:.2f}")
        else:
            logger.warning("⚠ No price data for BTC/USD")
        
        # Test 6: Get previous close for stock
        logger.info("\n[Test 6] Testing get_previous_close for stock (AAPL)...")
        prev_close = await market_data_feed.get_previous_close("AAPL")
        if prev_close is not None:
            logger.success(f"✓ Previous close for AAPL: ${prev_close:.2f}")
        else:
            logger.warning("⚠ No previous close data for AAPL")
        
        # Test 7: Get previous close for crypto
        logger.info("\n[Test 7] Testing get_previous_close for crypto (BTC/USD)...")
        prev_close = await market_data_feed.get_previous_close("BTC/USD")
        if prev_close is not None:
            logger.success(f"✓ Previous close for BTC/USD: ${prev_close:.2f}")
        else:
            logger.warning("⚠ No previous close data for BTC/USD")
        
        # Test 8: Test price caching
        logger.info("\n[Test 8] Testing price caching...")
        price1 = await market_data_feed.get_current_price("AAPL")
        price2 = await market_data_feed.get_current_price("AAPL")
        if price1 == price2:
            logger.success("✓ Price caching working (same price returned)")
        else:
            logger.info("  Prices differ (cache may have expired or market moved)")
        
        # Test 9: Test multiple timeframes
        logger.info("\n[Test 9] Testing multiple timeframes...")
        timeframes = ["1Min", "5Min", "15Min", "1Hour", "1Day"]
        for tf in timeframes:
            bars = await market_data_feed.get_bars("AAPL", tf, 5)
            if bars is not None and not bars.empty:
                logger.success(f"✓ Retrieved {len(bars)} bars for AAPL at {tf}")
            else:
                logger.warning(f"⚠ No bar data for AAPL at {tf}")
        
        # Test 10: Test invalid symbol
        logger.info("\n[Test 10] Testing invalid symbol...")
        bars = await market_data_feed.get_bars("INVALID_SYMBOL_XYZ", "1Min", 10)
        if bars is None:
            logger.success("✓ Invalid symbol handled gracefully (returned None)")
        else:
            logger.warning("⚠ Expected None for invalid symbol")
        
        # Test 11: Disconnect
        logger.info("\n[Test 11] Testing disconnect...")
        await market_data_feed.disconnect()
        logger.success("✓ Disconnect successful")
        
        logger.info("\n" + "=" * 60)
        logger.success("All MarketDataFeed tests completed!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        logger.exception(e)
        return False


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="DEBUG"
    )
    
    # Run tests
    success = asyncio.run(test_market_data_feed())
    
    if success:
        logger.success("\n✓ MarketDataFeed verification PASSED")
        sys.exit(0)
    else:
        logger.error("\n✗ MarketDataFeed verification FAILED")
        sys.exit(1)

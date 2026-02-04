"""Integration test script for Alpaca API connection and authentication.

This script verifies:
- Alpaca Paper API authentication
- Account data retrieval
- API response times

Requirements: 11.1, 11.2
"""
import os
import sys
import time
from datetime import datetime
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.connectors.alpaca_client import AlpacaClient


def test_authentication():
    """Test Alpaca API authentication."""
    logger.info("=" * 60)
    logger.info("TEST 1: Authentication")
    logger.info("=" * 60)
    
    try:
        # Initialize client
        start_time = time.time()
        client = AlpacaClient({})
        elapsed = time.time() - start_time
        
        logger.success(f"✓ AlpacaClient initialized successfully in {elapsed:.3f}s")
        logger.info(f"  Mode: {'Paper' if client.is_paper else 'Live'}")
        return True, client
        
    except ValueError as e:
        logger.error(f"✗ Authentication failed: {e}")
        logger.error("  Please check your environment variables:")
        logger.error("    - ALPACA_PAPER_API_KEY")
        logger.error("    - ALPACA_PAPER_API_SECRET")
        return False, None
    except Exception as e:
        logger.error(f"✗ Unexpected error during authentication: {e}")
        return False, None


def test_account_data_retrieval(client: AlpacaClient):
    """Test account data retrieval."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Account Data Retrieval")
    logger.info("=" * 60)
    
    try:
        # Test get_account()
        start_time = time.time()
        account = client.get_account()
        elapsed = time.time() - start_time
        
        logger.success(f"✓ Account data retrieved in {elapsed:.3f}s")
        logger.info(f"  Account ID: {account['account_id']}")
        logger.info(f"  Equity: ${account['equity']:,.2f}")
        logger.info(f"  Cash: ${account['cash']:,.2f}")
        logger.info(f"  Buying Power: ${account['buying_power']:,.2f}")
        logger.info(f"  Portfolio Value: ${account['portfolio_value']:,.2f}")
        logger.info(f"  Pattern Day Trader: {account['pattern_day_trader']}")
        logger.info(f"  Trading Blocked: {account['trading_blocked']}")
        logger.info(f"  Account Blocked: {account['account_blocked']}")
        logger.info(f"  Currency: {account['currency']}")
        
        # Verify all required fields are present
        required_fields = [
            'account_id', 'equity', 'cash', 'buying_power', 
            'portfolio_value', 'pattern_day_trader', 'trading_blocked',
            'account_blocked', 'currency'
        ]
        
        missing_fields = [field for field in required_fields if field not in account]
        if missing_fields:
            logger.error(f"✗ Missing required fields: {missing_fields}")
            return False
        
        logger.success("✓ All required account fields present")
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to retrieve account data: {e}")
        return False


def test_positions_retrieval(client: AlpacaClient):
    """Test positions retrieval."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Positions Retrieval")
    logger.info("=" * 60)
    
    try:
        # Test get_positions()
        start_time = time.time()
        positions = client.get_positions()
        elapsed = time.time() - start_time
        
        logger.success(f"✓ Positions retrieved in {elapsed:.3f}s")
        logger.info(f"  Total positions: {len(positions)}")
        
        if positions:
            logger.info("\n  Position Details:")
            for pos in positions:
                logger.info(f"    {pos['symbol']}:")
                logger.info(f"      Qty: {pos['qty']} ({pos['side']})")
                logger.info(f"      Entry: ${pos['avg_entry_price']:.2f}")
                logger.info(f"      Current: ${pos['current_price']:.2f}")
                logger.info(f"      P/L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']*100:.2f}%)")
                logger.info(f"      Market Value: ${pos['market_value']:.2f}")
                logger.info(f"      Asset Class: {pos['asset_class']}")
        else:
            logger.info("  No open positions")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to retrieve positions: {e}")
        return False


def test_api_response_times(client: AlpacaClient):
    """Test API response times for various operations."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: API Response Times")
    logger.info("=" * 60)
    
    response_times = {}
    
    # Test account retrieval
    try:
        start_time = time.time()
        client.get_account()
        response_times['get_account'] = time.time() - start_time
        logger.success(f"✓ get_account: {response_times['get_account']:.3f}s")
    except Exception as e:
        logger.error(f"✗ get_account failed: {e}")
        response_times['get_account'] = None
    
    # Test positions retrieval
    try:
        start_time = time.time()
        client.get_positions()
        response_times['get_positions'] = time.time() - start_time
        logger.success(f"✓ get_positions: {response_times['get_positions']:.3f}s")
    except Exception as e:
        logger.error(f"✗ get_positions failed: {e}")
        response_times['get_positions'] = None
    
    # Test orders retrieval
    try:
        start_time = time.time()
        client.get_orders(status='all', limit=10)
        response_times['get_orders'] = time.time() - start_time
        logger.success(f"✓ get_orders: {response_times['get_orders']:.3f}s")
    except Exception as e:
        logger.error(f"✗ get_orders failed: {e}")
        response_times['get_orders'] = None
    
    # Calculate average response time
    valid_times = [t for t in response_times.values() if t is not None]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        logger.info(f"\n  Average response time: {avg_time:.3f}s")
        
        # Warn if response times are slow
        if avg_time > 2.0:
            logger.warning("  ⚠ Average response time is slow (>2s)")
            logger.warning("  This may indicate network issues or API throttling")
        elif avg_time > 1.0:
            logger.warning("  ⚠ Average response time is moderate (>1s)")
        else:
            logger.success("  ✓ Response times are good (<1s)")
    
    return len(valid_times) == len(response_times)


def main():
    """Run all connection tests."""
    logger.info("Alpaca API Connection Test")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Track test results
    results = {}
    
    # Test 1: Authentication
    success, client = test_authentication()
    results['authentication'] = success
    
    if not success:
        logger.error("\n" + "=" * 60)
        logger.error("FAILED: Cannot proceed without authentication")
        logger.error("=" * 60)
        sys.exit(1)
    
    # Test 2: Account data retrieval
    results['account_data'] = test_account_data_retrieval(client)
    
    # Test 3: Positions retrieval
    results['positions'] = test_positions_retrieval(client)
    
    # Test 4: API response times
    results['response_times'] = test_api_response_times(client)
    
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

"""Integration test script for Alpaca order submission.

This script verifies:
- Market order submission
- Limit order submission
- Order status retrieval
- Order cancellation

NOTE: This script uses PAPER TRADING - no real money is at risk.
      However, orders will be submitted to your paper trading account.

Requirements: 11.5
"""
import os
import sys
import time
from datetime import datetime
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.connectors.alpaca_client import AlpacaClient


def test_market_order_submission(client: AlpacaClient):
    """Test market order submission."""
    logger.info("=" * 60)
    logger.info("TEST 1: Market Order Submission")
    logger.info("=" * 60)
    
    try:
        # Submit a small market order for a liquid stock
        symbol = "SPY"
        qty = 1
        
        logger.info(f"Submitting market order: BUY {qty} {symbol}")
        
        start_time = time.time()
        order = client.submit_order(
            symbol=symbol,
            side="buy",
            order_type="market",
            qty=qty,
            client_order_id=f"test_market_{int(time.time())}"
        )
        elapsed = time.time() - start_time
        
        if order:
            logger.success(f"✓ Market order submitted in {elapsed:.3f}s")
            logger.info(f"  Order ID: {order['id']}")
            logger.info(f"  Client Order ID: {order['client_order_id']}")
            logger.info(f"  Symbol: {order['symbol']}")
            logger.info(f"  Side: {order['side']}")
            logger.info(f"  Quantity: {order['qty']}")
            logger.info(f"  Status: {order['status']}")
            logger.info(f"  Submitted at: {order['submitted_at']}")
            
            # Wait a moment for order to potentially fill
            time.sleep(2)
            
            # Check order status
            updated_order = client.get_order(order['id'])
            if updated_order:
                logger.info(f"  Updated status: {updated_order['status']}")
                if updated_order['filled_qty'] > 0:
                    logger.info(f"  Filled quantity: {updated_order['filled_qty']}")
                    if updated_order['filled_avg_price']:
                        logger.info(f"  Fill price: ${updated_order['filled_avg_price']:.2f}")
            
            return True, order['id']
        else:
            logger.error("✗ Market order submission returned None")
            return False, None
            
    except Exception as e:
        logger.error(f"✗ Market order submission failed: {e}")
        return False, None


def test_limit_order_submission(client: AlpacaClient):
    """Test limit order submission."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Limit Order Submission")
    logger.info("=" * 60)
    
    try:
        # Get current price for a liquid stock
        symbol = "AAPL"
        
        logger.info(f"Getting current price for {symbol}...")
        current_price = None
        
        # Try to get latest trade
        trade = client.get_latest_trade(symbol)
        if trade:
            current_price = trade['price']
            logger.info(f"  Current price (trade): ${current_price:.2f}")
        else:
            # Fall back to quote
            quote = client.get_latest_quote(symbol)
            if quote:
                current_price = (quote['bid_price'] + quote['ask_price']) / 2
                logger.info(f"  Current price (quote midpoint): ${current_price:.2f}")
        
        if not current_price:
            logger.error("✗ Could not get current price")
            return False, None
        
        # Submit limit order well below current price (unlikely to fill)
        limit_price = round(current_price * 0.95, 2)  # 5% below current
        qty = 1
        
        logger.info(f"Submitting limit order: BUY {qty} {symbol} @ ${limit_price:.2f}")
        
        start_time = time.time()
        order = client.submit_order(
            symbol=symbol,
            side="buy",
            order_type="limit",
            qty=qty,
            limit_price=limit_price,
            client_order_id=f"test_limit_{int(time.time())}"
        )
        elapsed = time.time() - start_time
        
        if order:
            logger.success(f"✓ Limit order submitted in {elapsed:.3f}s")
            logger.info(f"  Order ID: {order['id']}")
            logger.info(f"  Client Order ID: {order['client_order_id']}")
            logger.info(f"  Symbol: {order['symbol']}")
            logger.info(f"  Side: {order['side']}")
            logger.info(f"  Quantity: {order['qty']}")
            logger.info(f"  Limit Price: ${order['limit_price']:.2f}")
            logger.info(f"  Status: {order['status']}")
            logger.info(f"  Submitted at: {order['submitted_at']}")
            
            return True, order['id']
        else:
            logger.error("✗ Limit order submission returned None")
            return False, None
            
    except Exception as e:
        logger.error(f"✗ Limit order submission failed: {e}")
        return False, None


def test_order_status_retrieval(client: AlpacaClient, order_id: str):
    """Test order status retrieval."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Order Status Retrieval")
    logger.info("=" * 60)
    
    if not order_id:
        logger.warning("⚠ No order ID provided, skipping test")
        return False
    
    try:
        logger.info(f"Retrieving order status for: {order_id}")
        
        start_time = time.time()
        order = client.get_order(order_id)
        elapsed = time.time() - start_time
        
        if order:
            logger.success(f"✓ Order status retrieved in {elapsed:.3f}s")
            logger.info(f"  Order ID: {order['id']}")
            logger.info(f"  Symbol: {order['symbol']}")
            logger.info(f"  Side: {order['side']}")
            logger.info(f"  Type: {order['order_type']}")
            logger.info(f"  Quantity: {order['qty']}")
            logger.info(f"  Filled Quantity: {order['filled_qty']}")
            logger.info(f"  Status: {order['status']}")
            
            if order['filled_avg_price']:
                logger.info(f"  Fill Price: ${order['filled_avg_price']:.2f}")
            if order['limit_price']:
                logger.info(f"  Limit Price: ${order['limit_price']:.2f}")
            
            return True
        else:
            logger.error("✗ Order not found")
            return False
            
    except Exception as e:
        logger.error(f"✗ Order status retrieval failed: {e}")
        return False


def test_orders_list_retrieval(client: AlpacaClient):
    """Test retrieving list of orders."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Orders List Retrieval")
    logger.info("=" * 60)
    
    try:
        # Get open orders
        logger.info("Retrieving open orders...")
        start_time = time.time()
        open_orders = client.get_orders(status='open', limit=10)
        elapsed = time.time() - start_time
        
        logger.success(f"✓ Open orders retrieved in {elapsed:.3f}s")
        logger.info(f"  Total open orders: {len(open_orders)}")
        
        if open_orders:
            logger.info("\n  Open Orders:")
            for order in open_orders[:5]:  # Show first 5
                logger.info(f"    {order['symbol']}: {order['side']} {order['qty']} @ {order['order_type']}")
                logger.info(f"      Status: {order['status']}, ID: {order['id']}")
        
        # Get all recent orders
        logger.info("\nRetrieving all recent orders...")
        start_time = time.time()
        all_orders = client.get_orders(status='all', limit=10)
        elapsed = time.time() - start_time
        
        logger.success(f"✓ All orders retrieved in {elapsed:.3f}s")
        logger.info(f"  Total recent orders: {len(all_orders)}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Orders list retrieval failed: {e}")
        return False


def test_order_cancellation(client: AlpacaClient, order_id: str):
    """Test order cancellation."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Order Cancellation")
    logger.info("=" * 60)
    
    if not order_id:
        logger.warning("⚠ No order ID provided, skipping test")
        return False
    
    try:
        # First check if order is still open
        order = client.get_order(order_id)
        if not order:
            logger.warning(f"⚠ Order {order_id} not found")
            return False
        
        if order['status'] not in ['new', 'accepted', 'pending_new']:
            logger.warning(f"⚠ Order {order_id} is not cancelable (status: {order['status']})")
            return True  # Not a failure, just not cancelable
        
        logger.info(f"Canceling order: {order_id}")
        logger.info(f"  Symbol: {order['symbol']}")
        logger.info(f"  Status: {order['status']}")
        
        start_time = time.time()
        success = client.cancel_order(order_id)
        elapsed = time.time() - start_time
        
        if success:
            logger.success(f"✓ Order canceled in {elapsed:.3f}s")
            
            # Verify cancellation
            time.sleep(1)
            updated_order = client.get_order(order_id)
            if updated_order:
                logger.info(f"  Updated status: {updated_order['status']}")
                if updated_order['status'] in ['canceled', 'cancelled']:
                    logger.success("✓ Cancellation confirmed")
                else:
                    logger.warning(f"⚠ Order status is {updated_order['status']}, not canceled")
            
            return True
        else:
            logger.error("✗ Order cancellation failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Order cancellation failed: {e}")
        return False


def test_position_closing(client: AlpacaClient):
    """Test position closing (if any positions exist)."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Position Closing")
    logger.info("=" * 60)
    
    try:
        # Get current positions
        positions = client.get_positions()
        
        if not positions:
            logger.info("  No open positions to close")
            logger.info("  Skipping position closing test")
            return True
        
        logger.info(f"Found {len(positions)} open position(s)")
        
        # Close the first position as a test
        position = positions[0]
        symbol = position['symbol']
        
        logger.info(f"Closing position: {symbol}")
        logger.info(f"  Quantity: {position['qty']}")
        logger.info(f"  Side: {position['side']}")
        
        start_time = time.time()
        close_order = client.close_position(symbol)
        elapsed = time.time() - start_time
        
        if close_order:
            logger.success(f"✓ Position close order submitted in {elapsed:.3f}s")
            logger.info(f"  Order ID: {close_order['id']}")
            logger.info(f"  Status: {close_order['status']}")
            return True
        else:
            logger.error("✗ Position close order failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Position closing test failed: {e}")
        return False


def main():
    """Run all order submission tests."""
    logger.info("Alpaca Order Submission Test")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("IMPORTANT: This test uses PAPER TRADING")
    logger.info("No real money is at risk, but orders will be submitted")
    logger.info("to your Alpaca Paper trading account.")
    logger.info("=" * 60)
    logger.info("")
    
    # Initialize client
    try:
        client = AlpacaClient({})
        logger.success("✓ AlpacaClient initialized")
        
        # Verify paper mode
        if not client.is_paper:
            logger.error("✗ Client is not in paper mode!")
            logger.error("  Aborting to prevent live trading")
            sys.exit(1)
        
        logger.success("✓ Confirmed paper trading mode")
    except Exception as e:
        logger.error(f"✗ Failed to initialize AlpacaClient: {e}")
        sys.exit(1)
    
    # Track test results
    results = {}
    market_order_id = None
    limit_order_id = None
    
    # Test 1: Market order submission
    success, market_order_id = test_market_order_submission(client)
    results['market_order'] = success
    
    # Test 2: Limit order submission
    success, limit_order_id = test_limit_order_submission(client)
    results['limit_order'] = success
    
    # Test 3: Order status retrieval (use market order)
    if market_order_id:
        results['order_status'] = test_order_status_retrieval(client, market_order_id)
    else:
        logger.warning("⚠ Skipping order status test (no order ID)")
        results['order_status'] = False
    
    # Test 4: Orders list retrieval
    results['orders_list'] = test_orders_list_retrieval(client)
    
    # Test 5: Order cancellation (use limit order)
    if limit_order_id:
        results['order_cancellation'] = test_order_cancellation(client, limit_order_id)
    else:
        logger.warning("⚠ Skipping order cancellation test (no order ID)")
        results['order_cancellation'] = False
    
    # Test 6: Position closing
    results['position_closing'] = test_position_closing(client)
    
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
    
    # Cleanup warning
    logger.info("\n" + "=" * 60)
    logger.info("CLEANUP REMINDER")
    logger.info("=" * 60)
    logger.info("This test may have created open orders or positions")
    logger.info("in your paper trading account. You may want to:")
    logger.info("  1. Check your open orders and cancel any test orders")
    logger.info("  2. Close any test positions")
    logger.info("  3. Review your paper trading account activity")
    logger.info("=" * 60)
    
    if passed == total:
        logger.success("\n✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error(f"\n✗ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

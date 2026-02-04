# Alpaca Integration Test Scripts

This directory contains integration test scripts for verifying the Alpaca Paper trading integration in PulseTrader.

## Overview

These scripts test the actual connection to Alpaca's Paper trading API and verify that all components work correctly with real API responses. They are designed to be run manually to validate the integration before deploying strategies.

## Prerequisites

1. **Environment Variables**: Ensure you have the following environment variables set:
   ```bash
   ALPACA_PAPER_API_KEY=your_paper_api_key
   ALPACA_PAPER_API_SECRET=your_paper_api_secret
   ALPACA_MODE=paper
   ```

2. **Dependencies**: Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Alpaca Paper Account**: You need an active Alpaca Paper trading account. Sign up at [alpaca.markets](https://alpaca.markets) if you don't have one.

## Test Scripts

### 1. test_alpaca_connection.py

Tests basic API authentication and connectivity.

**What it tests:**
- Alpaca API authentication
- Account data retrieval
- Positions retrieval
- API response times

**Usage:**
```bash
python scripts/test_alpaca_connection.py
```

**Expected output:**
- ✓ Authentication successful
- ✓ Account data retrieved with all required fields
- ✓ Positions retrieved (may be empty)
- ✓ Response times under 2 seconds

### 2. test_market_data.py

Tests market data retrieval for stocks and crypto.

**What it tests:**
- Historical bar retrieval for stocks (AAPL, TSLA, SPY)
- Historical bar retrieval for crypto (BTC/USD, ETH/USD)
- Current price retrieval (trades and quotes)
- Previous close retrieval
- Multiple timeframes (1Min, 5Min, 15Min, 1Hour, 1Day)
- Data format consistency

**Usage:**
```bash
python scripts/test_market_data.py
```

**Expected output:**
- ✓ Stock bars retrieved with OHLCV data
- ✓ Crypto bars retrieved with OHLCV data
- ✓ Current prices available
- ✓ Previous close prices available
- ✓ All timeframes working
- ✓ Data format consistent across symbols

**Note:** Some tests may show warnings if the market is closed, but this is expected behavior.

### 3. test_websocket_streaming.py

Tests real-time WebSocket streaming for market data.

**What it tests:**
- WebSocket connection establishment
- Trade subscriptions for stocks
- Quote subscriptions for stocks
- Crypto trade subscriptions
- Multiple simultaneous subscriptions

**Usage:**
```bash
python scripts/test_websocket_streaming.py
```

**Expected output:**
- ✓ WebSocket connection established
- ✓ Trade updates received (during market hours)
- ✓ Quote updates received (during market hours)
- ✓ Crypto updates received (24/7)
- ✓ Multiple subscriptions working

**Note:** 
- Stock data is only available during market hours (9:30 AM - 4:00 PM ET, Monday-Friday)
- Crypto data is available 24/7
- The test runs for 30 seconds per subscription type

### 4. test_order_submission.py

Tests order submission and management (PAPER TRADING ONLY).

**What it tests:**
- Market order submission
- Limit order submission
- Order status retrieval
- Orders list retrieval
- Order cancellation
- Position closing

**Usage:**
```bash
python scripts/test_order_submission.py
```

**Expected output:**
- ✓ Market order submitted successfully
- ✓ Limit order submitted successfully
- ✓ Order status retrieved
- ✓ Orders list retrieved
- ✓ Order canceled successfully
- ✓ Position closed (if positions exist)

**IMPORTANT:**
- This script uses PAPER TRADING - no real money is at risk
- Orders will be submitted to your Alpaca Paper trading account
- You may need to manually clean up test orders/positions after running
- The script verifies paper mode before submitting any orders

## Running All Tests

To run all integration tests in sequence:

```bash
# Test 1: Connection
python scripts/test_alpaca_connection.py

# Test 2: Market Data
python scripts/test_market_data.py

# Test 3: WebSocket Streaming
python scripts/test_websocket_streaming.py

# Test 4: Order Submission
python scripts/test_order_submission.py
```

## Interpreting Results

### Success Indicators
- ✓ Green checkmarks indicate successful tests
- All tests should pass if the integration is working correctly

### Warning Indicators
- ⚠ Yellow warnings indicate expected behavior (e.g., no data during market close)
- These are not failures, just informational

### Failure Indicators
- ✗ Red X marks indicate test failures
- Check the error messages for details
- Common issues:
  - Missing or invalid API credentials
  - Network connectivity problems
  - Alpaca API service issues
  - Market closed (for some tests)

## Troubleshooting

### Authentication Errors
```
✗ Authentication failed: Missing Alpaca API credentials
```
**Solution:** Set the required environment variables:
```bash
export ALPACA_PAPER_API_KEY=your_key
export ALPACA_PAPER_API_SECRET=your_secret
export ALPACA_MODE=paper
```

### No Market Data
```
⚠ No trade updates received
```
**Solution:** This is normal if the market is closed. Try running during market hours (9:30 AM - 4:00 PM ET, Monday-Friday) or test with crypto symbols which trade 24/7.

### Slow Response Times
```
⚠ Average response time is slow (>2s)
```
**Solution:** This may indicate:
- Network latency issues
- Alpaca API throttling
- High API load
- Check your internet connection and try again

### Order Submission Failures
```
✗ Market order submission failed
```
**Solution:** Check:
- Paper trading mode is enabled
- Account has sufficient buying power
- Symbol is valid and tradeable
- Market is open (for stocks)

## Best Practices

1. **Run tests in order**: Start with connection tests before moving to more complex tests
2. **Check market hours**: Some tests require market hours for meaningful results
3. **Monitor paper account**: Review your paper trading account after running order tests
4. **Clean up test orders**: Cancel any remaining test orders after running
5. **Run regularly**: Run these tests after any changes to the Alpaca integration

## Requirements Validation

These integration tests validate the following requirements from the design document:

- **Requirement 11.1**: Authentication and connectivity verification
- **Requirement 11.2**: Account data retrieval and API response times
- **Requirement 11.3**: Market data retrieval for stocks and crypto
- **Requirement 11.4**: WebSocket streaming functionality
- **Requirement 11.5**: Order submission and management

## Support

If you encounter issues:

1. Check the [Alpaca API Status](https://status.alpaca.markets/)
2. Review the [Alpaca API Documentation](https://alpaca.markets/docs/)
3. Check the PulseTrader logs for detailed error messages
4. Verify your API credentials are correct and active

## Notes

- All tests use the Alpaca Paper trading environment
- No real money is ever at risk
- Tests are designed to be non-destructive (except for creating test orders)
- Some tests may take 30-60 seconds to complete
- WebSocket tests require an active internet connection
- Order tests may leave test orders/positions that need manual cleanup

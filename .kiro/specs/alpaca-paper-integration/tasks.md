# Implementation Plan: Alpaca Paper Trading Integration

## Overview

This implementation plan breaks down the Alpaca Paper trading integration into discrete, incremental coding tasks. Each task builds on previous work and includes validation through code execution. The plan follows the architecture defined in the design document and integrates seamlessly with PulseTrader's existing Risk Manager and Strategy system.

## Implementation Status

**Completed Core Components:**
- ✅ AlpacaClient with full API integration (account, market data, orders, positions)
- ✅ RetryStrategy with exponential backoff
- ✅ AccountManager with real Alpaca data and caching
- ✅ MarketDataFeed with real Alpaca data and caching
- ✅ Configuration validation utility
- ✅ Comprehensive unit test coverage (62+ tests for AlpacaClient, 18+ for AccountManager)

**In Progress:**
- 🔄 OrderManager integration (partially complete)
- 🔄 WebSocketClient (stub exists, needs full implementation)

**Remaining:**
- ⏳ Connection health monitoring
- ⏳ Integration test scripts
- ⏳ System initialization updates
- ⏳ End-to-end validation

## Tasks

- [x] 1. Setup and dependencies
  - Install alpaca-py SDK and add to requirements.txt
  - Create environment variable validation utility
  - Add hypothesis for property-based testing
  - _Requirements: 1.1, 1.2, 8.1_

- [x] 2. Implement AlpacaClient core functionality
  - [x] 2.1 Implement AlpacaClient initialization and authentication
    - Load credentials from environment variables
    - Initialize TradingClient, StockHistoricalDataClient, CryptoHistoricalDataClient
    - Validate credentials and raise descriptive errors if missing
    - Support paper/live mode switching
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ]* 2.2 Write property test for error handling consistency
    - **Property 1: Error Handling Consistency**
    - **Validates: Requirements 1.2, 1.6**
  
  - [x] 2.3 Implement account data retrieval methods
    - Implement get_account() to retrieve equity, cash, buying power
    - Implement get_positions() to retrieve all open positions
    - Implement get_position(symbol) to retrieve specific position
    - Convert Alpaca SDK types to PulseTrader dictionaries
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [ ]* 2.4 Write property test for position data completeness
    - **Property 2: Position Data Completeness**
    - **Validates: Requirements 2.2, 7.2**

- [x] 3. Implement market data retrieval
  - [x] 3.1 Implement historical bar data retrieval
    - Implement get_bars() for stocks and crypto
    - Support multiple timeframes (1Min, 5Min, 15Min, 1Hour, 1Day)
    - Convert Alpaca bars to pandas DataFrame
    - Handle missing data gracefully
    - _Requirements: 3.1, 3.4, 3.5, 3.6_
  
  - [ ]* 3.2 Write property test for bar data format consistency
    - **Property 3: Bar Data Format Consistency**
    - **Validates: Requirements 3.6**
  
  - [x] 3.3 Implement current price retrieval
    - Implement get_latest_trade() for current price
    - Implement get_latest_quote() as fallback
    - Calculate quote midpoint when needed
    - _Requirements: 3.2_
  
  - [x] 3.4 Implement previous close retrieval
    - Retrieve 2 days of daily bars
    - Extract previous day's close price
    - _Requirements: 3.3_

- [x] 4. Implement order submission and management
  - [x] 4.1 Implement order submission methods
    - Implement submit_order() for market, limit, and stop orders
    - Generate unique client order IDs
    - Convert order parameters to Alpaca SDK request objects
    - Handle order submission errors
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ]* 4.2 Write property test for order submission completeness
    - **Property 5: Order Submission Completeness**
    - **Validates: Requirements 5.1, 5.3, 5.4**
  
  - [x] 4.3 Implement order status and management methods
    - Implement get_order(order_id) to retrieve order details
    - Implement get_orders() with status filtering
    - Implement cancel_order(order_id)
    - _Requirements: 6.1_
  
  - [x] 4.4 Implement position closing methods
    - Implement close_position(symbol) to close specific position
    - Implement close_all_positions() to close all positions
    - _Requirements: 7.1, 7.6_
  
  - [ ]* 4.5 Write property test for position close order accuracy
    - **Property 9: Position Close Order Accuracy**
    - **Validates: Requirements 7.6**

- [x] 5. Implement error handling and retry logic
  - [x] 5.1 Implement centralized error handling
    - Create _handle_api_error() method
    - Handle rate limits with exponential backoff
    - Handle authentication errors
    - Handle network errors with retry
    - _Requirements: 1.5, 10.1, 10.2, 10.3_
  
  - [x] 5.2 Implement RetryStrategy class
    - Implement exponential backoff retry logic
    - Support configurable max attempts and base delay
    - _Requirements: 10.1_
  
  - [ ]* 5.3 Write property test for exception resilience
    - **Property 11: Exception Resilience**
    - **Validates: Requirements 10.5**

- [x] 6. Checkpoint - Verify AlpacaClient functionality
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement AccountManager with real data
  - [x] 7.1 Update AccountManager to use AlpacaClient
    - Replace stub methods with real AlpacaClient calls
    - Implement account state caching with TTL
    - Implement periodic state refresh
    - Update Account dataclass with real data
    - _Requirements: 2.4, 2.5, 2.6_
  
  - [x] 7.2 Implement equity and cash retrieval methods
    - Implement get_equity() with cache check
    - Implement get_cash() with cache check
    - Implement get_buying_power() with cache check
    - Implement _ensure_fresh_data() for cache management
    - _Requirements: 2.1_
  
  - [x] 7.3 Implement position retrieval methods
    - Implement get_positions() with cache
    - Implement get_position(symbol) with cache
    - _Requirements: 2.2, 7.1_

- [x] 8. Implement MarketDataFeed with real data
  - [x] 8.1 Update MarketDataFeed to use AlpacaClient
    - Replace stub methods with real AlpacaClient calls
    - Implement price caching with TTL
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 8.2 Implement get_bars() method
    - Call AlpacaClient.get_bars()
    - Handle errors gracefully
    - Return pandas DataFrame or None
    - _Requirements: 3.1, 3.4, 3.5_
  
  - [x] 8.3 Implement get_current_price() method
    - Check price cache first
    - Try latest trade, fall back to quote midpoint
    - Update cache on success
    - _Requirements: 3.2_
  
  - [x] 8.4 Implement get_previous_close() method
    - Retrieve 2 days of daily bars
    - Extract previous close
    - _Requirements: 3.3_

- [x] 9. Implement OrderManager with real execution
  - [x] 9.1 Update OrderManager to use AlpacaClient
    - Inject AlpacaClient, AccountManager, MarketDataFeed dependencies
    - Replace stub methods with real implementations
    - _Requirements: 5.1_
  
  - [x] 9.2 Implement order validation and submission
    - Implement submit_order() with risk validation
    - Call RiskManager.validate_trade() before submission
    - Generate client order IDs
    - Submit orders via AlpacaClient
    - Cache submitted orders
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  
  - [ ]* 9.3 Write property test for risk validation enforcement
    - **Property 6: Risk Validation Enforcement**
    - **Validates: Requirements 5.6**
  
  - [ ]* 9.4 Write property test for order cache consistency
    - **Property 7: Order Cache Consistency**
    - **Validates: Requirements 6.6**
  
  - [x] 9.5 Implement position management methods
    - Implement close_position() to close specific position
    - Implement close_all_positions() to close all positions
    - Calculate correct order side and quantity
    - _Requirements: 7.6_
  
  - [ ]* 9.6 Write property test for realized P/L calculation
    - **Property 8: Realized P/L Calculation Accuracy**
    - **Validates: Requirements 7.3**
  
  - [x] 9.7 Implement helper methods
    - Implement _get_asset_type() to determine asset type from symbol
    - Implement _count_positions_by_type() for risk validation
    - Implement _generate_client_order_id() for idempotency
    - _Requirements: 5.3_

- [x] 10. Implement WebSocketClient for real-time streaming
  - [x] 10.1 Implement WebSocketClient initialization
    - Initialize StockDataStream and CryptoDataStream
    - Setup callback registries
    - _Requirements: 4.1_
  
  - [x] 10.2 Implement connection management
    - Implement connect() method
    - Implement disconnect() method
    - Handle connection errors
    - _Requirements: 4.1, 4.5, 4.6_
  
  - [x] 10.3 Implement subscription methods
    - Implement subscribe_trades() for trade updates
    - Implement subscribe_quotes() for quote updates
    - Separate crypto and stock symbols
    - Register callbacks
    - _Requirements: 4.3, 4.4, 4.7_
  
  - [ ]* 10.4 Write property test for WebSocket subscription scalability
    - **Property 4: WebSocket Subscription Scalability**
    - **Validates: Requirements 4.7**
  
  - [x] 10.5 Implement message handlers
    - Implement _trade_handler() to parse and forward trades
    - Implement _quote_handler() to parse and forward quotes
    - Invoke registered callbacks
    - Handle callback errors gracefully
    - _Requirements: 4.3, 4.4_
  
  - [x] 10.6 Implement run() method
    - Start stock and crypto streams
    - Handle stream errors
    - _Requirements: 4.1_

- [x] 11. Checkpoint - Verify core integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement connection health monitoring
  - [x] 12.1 Implement ConnectionHealthMonitor class
    - Track error count and last success timestamp
    - Implement periodic health checks
    - Ping Alpaca API to verify connectivity
    - _Requirements: 9.1, 9.2_
  
  - [x] 12.2 Implement error threshold detection
    - Increment error count on failures
    - Reset error count on success
    - Trigger preservation mode when threshold exceeded
    - _Requirements: 9.3_
  
  - [ ]* 12.3 Write property test for error threshold preservation mode
    - **Property 10: Error Threshold Preservation Mode**
    - **Validates: Requirements 9.3**
  
  - [x] 12.4 Implement response time tracking
    - Track API response times
    - Log slow responses
    - _Requirements: 9.4_

- [x] 13. Implement configuration validation
  - [x] 13.1 Create configuration validation utility
    - Validate required environment variables at startup
    - Check for ALPACA_PAPER_API_KEY
    - Check for ALPACA_PAPER_API_SECRET
    - Check for JWT_SECRET_KEY
    - Raise descriptive errors for missing variables
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [x] 13.2 Implement .env file validation
    - Check if .env file exists
    - Provide clear instructions if missing
    - _Requirements: 8.6_
  
  - [x] 13.3 Implement ALPACA_MODE validation
    - Validate mode is "paper" or "live"
    - Default to "paper" if invalid
    - Log warning for invalid mode
    - _Requirements: 8.5_
  
  - [x] 13.4 Implement startup validation logging
    - Log successful validation
    - Log configuration summary
    - _Requirements: 8.7_

- [x] 14. Implement comprehensive logging
  - [x] 14.1 Add logging to AlpacaClient
    - Log API requests with endpoint and parameters
    - Log API responses with status
    - Sanitize sensitive data (API keys)
    - _Requirements: 12.1, 12.2, 12.6_
  
  - [x] 14.2 Add logging to OrderManager
    - Log order submissions with details
    - Log order fills with price and quantity
    - Log order rejections with reasons
    - _Requirements: 12.3, 12.4_
  
  - [ ]* 14.3 Write property test for comprehensive logging
    - **Property 12: Comprehensive Logging**
    - **Validates: Requirements 12.3, 12.5, 12.6**
  
  - [x] 14.4 Add logging to error handlers
    - Log errors with stack traces
    - Log context information
    - Sanitize sensitive data
    - _Requirements: 12.5, 12.6_
  
  - [x] 14.5 Implement log level configuration
    - Support LOG_LEVEL environment variable
    - Configure loguru with specified level
    - _Requirements: 12.7_

- [x] 15. Create integration test scripts
  - [x] 15.1 Create test_alpaca_connection.py script
    - Test authentication
    - Test account data retrieval
    - Test API response times
    - _Requirements: 11.1, 11.2_
  
  - [x] 15.2 Create test_market_data.py script
    - Test historical bar retrieval for stocks
    - Test historical bar retrieval for crypto
    - Test current price retrieval
    - Test multiple timeframes
    - _Requirements: 11.3_
  
  - [x] 15.3 Create test_websocket_streaming.py script
    - Test WebSocket connection
    - Test trade subscriptions
    - Test quote subscriptions
    - Test reconnection
    - _Requirements: 11.4_
  
  - [x] 15.4 Create test_order_submission.py script
    - Test market order submission
    - Test limit order submission
    - Test order status retrieval
    - Test order cancellation
    - _Requirements: 11.5_

- [x] 16. Update system initialization
  - [x] 16.1 Update main.py or orchestrator to use real clients
    - Initialize AlpacaClient with configuration
    - Pass AlpacaClient to AccountManager, MarketDataFeed, OrderManager
    - Initialize WebSocketClient
    - Start ConnectionHealthMonitor
    - _Requirements: 1.1, 2.4_
  
  - [x] 16.2 Add startup validation
    - Call configuration validation before initialization
    - Halt system if validation fails
    - Log successful startup
    - _Requirements: 8.1, 8.7_
  
  - [x] 16.3 Add graceful shutdown
    - Disconnect WebSocketClient on shutdown
    - Close all positions if configured
    - Log shutdown
    - _Requirements: 4.1_

- [x] 17. Final checkpoint - End-to-end validation
  - Run all integration test scripts
  - Verify account data retrieval
  - Verify market data retrieval
  - Verify WebSocket streaming
  - Verify order submission (paper trading)
  - Verify error handling and recovery
  - Verify logging completeness
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- All code uses Python 3.11+ with asyncio
- Integration tests require valid Alpaca Paper API credentials in .env file

## Progress Summary

**Phase 1 - Foundation (Complete):**
- ✅ AlpacaClient: Full REST API integration with 62+ unit tests
- ✅ RetryStrategy: Exponential backoff with smart error handling
- ✅ Configuration: Environment validation utility
- ✅ AccountManager: Real data with caching (18+ unit tests)
- ✅ MarketDataFeed: Real data with caching

**Phase 2 - Order Execution (In Progress):**
- 🔄 OrderManager: Needs completion of order submission with risk validation
- 🔄 WebSocketClient: Stub exists, needs full implementation

**Phase 3 - Monitoring & Integration (Remaining):**
- ⏳ Connection health monitoring
- ⏳ Integration test scripts
- ⏳ System initialization updates
- ⏳ End-to-end validation

**Test Coverage:**
- Unit tests: 80+ tests across AlpacaClient, AccountManager, MarketDataFeed
- Integration tests: Manual verification scripts created
- Property tests: Marked as optional, can be added later


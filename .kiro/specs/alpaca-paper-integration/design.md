# Design Document: Alpaca Paper Trading Integration

## Overview

This design document outlines the implementation of full Alpaca Paper trading integration for PulseTrader. The system currently has a well-architected foundation with stub implementations that need to be replaced with functional Alpaca API integration using the official `alpaca-py` SDK.

The integration will transform PulseTrader from a simulation system into a functional paper trading platform capable of:
- Authenticating with Alpaca's Paper trading environment
- Retrieving real-time and historical market data
- Managing account state with live updates
- Executing orders and tracking positions
- Streaming real-time market data via WebSocket
- Handling errors and connection issues gracefully

The design follows PulseTrader's existing architecture patterns and integrates seamlessly with the Risk Manager, Strategy system, and Admin UI.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PulseTrader System                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │  Strategies  │      │ Risk Manager │                     │
│  │  - Crypto    │      │ - Validation │                     │
│  │  - ETF       │      │ - Position   │                     │
│  │  - Stock     │      │   Sizing     │                     │
│  └──────┬───────┘      └──────┬───────┘                     │
│         │                     │                              │
│         └──────────┬──────────┘                              │
│                    │                                         │
│         ┌──────────▼──────────┐                             │
│         │   Order Manager     │                             │
│         │  - Order Submission │                             │
│         │  - Position Tracking│                             │
│         └──────────┬──────────┘                             │
│                    │                                         │
│    ┌───────────────┼───────────────┐                        │
│    │               │               │                        │
│ ┌──▼────────┐  ┌──▼────────┐  ┌──▼────────┐               │
│ │  Account  │  │  Market   │  │  WebSocket│               │
│ │  Manager  │  │  Data     │  │  Client   │               │
│ │           │  │  Feed     │  │           │               │
│ └─────┬─────┘  └─────┬─────┘  └─────┬─────┘               │
│       │              │              │                       │
│       └──────────────┼──────────────┘                       │
│                      │                                      │
│              ┌───────▼────────┐                             │
│              │ Alpaca Client  │                             │
│              │ - REST API     │                             │
│              │ - Auth         │                             │
│              │ - Error Handle │                             │
│              └───────┬────────┘                             │
└──────────────────────┼──────────────────────────────────────┘
                       │
                       │ HTTPS / WebSocket
                       │
              ┌────────▼─────────┐
              │  Alpaca Paper    │
              │  Trading API     │
              └──────────────────┘
```

### Component Responsibilities

**AlpacaClient**: Low-level wrapper around alpaca-py SDK
- Manages authentication and API credentials
- Provides methods for account, market data, and order operations
- Handles rate limiting and retries
- Converts between Alpaca SDK types and PulseTrader types

**AccountManager**: High-level account state management
- Retrieves and caches account data (equity, cash, buying power)
- Tracks positions and P/L
- Provides account information to Risk Manager and Strategies
- Refreshes state periodically

**MarketDataFeed**: Market data aggregation and distribution
- Retrieves historical bars for strategy analysis
- Provides current prices for order execution
- Converts Alpaca bar data to pandas DataFrames
- Caches recent data to reduce API calls

**OrderManager**: Order lifecycle management
- Validates orders with Risk Manager before submission
- Submits orders to Alpaca via AlpacaClient
- Tracks order status and fills
- Manages position entry and exit

**WebSocketClient**: Real-time data streaming
- Establishes WebSocket connection to Alpaca
- Subscribes to trade and quote updates
- Distributes updates to registered callbacks
- Handles reconnection on connection loss

## Components and Interfaces

### AlpacaClient

The AlpacaClient wraps the alpaca-py SDK and provides a clean interface for PulseTrader components.

**Dependencies**:
```python
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
```

**Configuration**:
```python
class AlpacaClient:
    def __init__(self, config: Dict) -> None:
        # Load credentials from environment
        self.api_key = os.getenv("ALPACA_PAPER_API_KEY")
        self.api_secret = os.getenv("ALPACA_PAPER_API_SECRET")
        self.mode = os.getenv("ALPACA_MODE", "paper")
        
        # Validate credentials
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing Alpaca API credentials")
        
        # Initialize clients
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.api_secret,
            paper=True  # Always True for paper mode
        )
        
        self.stock_data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.api_secret
        )
        
        self.crypto_data_client = CryptoHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.api_secret
        )
```

**Interface**:
```python
# Account Operations
def get_account(self) -> Dict:
    """Retrieve account information including equity, cash, buying power"""
    
def get_positions(self) -> List[Dict]:
    """Retrieve all open positions"""
    
def get_position(self, symbol: str) -> Optional[Dict]:
    """Retrieve a specific position by symbol"""

# Market Data Operations
def get_bars(
    self, 
    symbol: str, 
    timeframe: str, 
    limit: int = 50,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> pd.DataFrame:
    """Retrieve historical bar data"""
    
def get_latest_trade(self, symbol: str) -> Optional[Dict]:
    """Retrieve the latest trade for a symbol"""
    
def get_latest_quote(self, symbol: str) -> Optional[Dict]:
    """Retrieve the latest quote for a symbol"""

# Order Operations
def submit_order(
    self,
    symbol: str,
    side: str,  # "buy" or "sell"
    order_type: str,  # "market", "limit", "stop"
    qty: int,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    client_order_id: Optional[str] = None
) -> Optional[Dict]:
    """Submit an order to Alpaca"""
    
def get_order(self, order_id: str) -> Optional[Dict]:
    """Retrieve order details by ID"""
    
def get_orders(
    self,
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict]:
    """Retrieve orders with optional status filter"""
    
def cancel_order(self, order_id: str) -> bool:
    """Cancel an open order"""
    
def close_position(self, symbol: str) -> Optional[Dict]:
    """Close a position by submitting a market order"""
    
def close_all_positions(self) -> List[Dict]:
    """Close all open positions"""
```

**Error Handling**:
```python
def _handle_api_error(self, error: Exception, operation: str) -> None:
    """Centralized error handling with logging and retry logic"""
    if isinstance(error, APIError):
        if error.status_code == 429:  # Rate limit
            logger.warning(f"Rate limit hit for {operation}, retrying...")
            # Implement exponential backoff
        elif error.status_code == 401:  # Auth error
            logger.error(f"Authentication failed for {operation}")
            raise
        else:
            logger.error(f"API error in {operation}: {error}")
    else:
        logger.error(f"Unexpected error in {operation}: {error}")
```

### AccountManager

The AccountManager maintains account state and provides it to other components.

**Interface**:
```python
class AccountManager:
    def __init__(self, config: Dict, alpaca_client: AlpacaClient) -> None:
        self.config = config
        self.alpaca_client = alpaca_client
        self.account_cache: Optional[Dict] = None
        self.positions_cache: List[Dict] = []
        self.last_update: Optional[datetime] = None
        self.update_interval = 30  # seconds
        
    async def initialize(self) -> None:
        """Initialize account state from Alpaca"""
        await self.update_state()
        
    async def update_state(self) -> None:
        """Refresh account and position data from Alpaca"""
        try:
            self.account_cache = self.alpaca_client.get_account()
            self.positions_cache = self.alpaca_client.get_positions()
            self.last_update = datetime.now()
            logger.info(f"Account updated: Equity=${self.account_cache['equity']}")
        except Exception as e:
            logger.error(f"Failed to update account state: {e}")
            
    async def get_equity(self) -> float:
        """Get current account equity"""
        await self._ensure_fresh_data()
        return float(self.account_cache.get("equity", 0.0))
        
    async def get_cash(self) -> float:
        """Get available cash"""
        await self._ensure_fresh_data()
        return float(self.account_cache.get("cash", 0.0))
        
    async def get_buying_power(self) -> float:
        """Get buying power"""
        await self._ensure_fresh_data()
        return float(self.account_cache.get("buying_power", 0.0))
        
    async def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        await self._ensure_fresh_data()
        return self.positions_cache
        
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """Get a specific position"""
        await self._ensure_fresh_data()
        for position in self.positions_cache:
            if position["symbol"] == symbol:
                return position
        return None
        
    async def _ensure_fresh_data(self) -> None:
        """Update data if cache is stale"""
        if self.last_update is None:
            await self.update_state()
        elif (datetime.now() - self.last_update).seconds > self.update_interval:
            await self.update_state()
```

### MarketDataFeed

The MarketDataFeed provides market data to strategies.

**Interface**:
```python
class MarketDataFeed:
    def __init__(self, config: Dict, alpaca_client: AlpacaClient) -> None:
        self.config = config
        self.alpaca_client = alpaca_client
        self.price_cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_ttl = 5  # seconds
        
    async def connect(self) -> None:
        """Initialize market data feed"""
        logger.info("Market data feed connected")
        
    async def disconnect(self) -> None:
        """Cleanup market data feed"""
        logger.info("Market data feed disconnected")
        
    async def get_bars(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 50
    ) -> Optional[pd.DataFrame]:
        """Retrieve historical bars"""
        try:
            bars = self.alpaca_client.get_bars(symbol, timeframe, limit)
            if bars is not None and not bars.empty:
                return bars
            logger.warning(f"No bar data for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            return None
            
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price (latest trade or quote midpoint)"""
        # Check cache first
        if symbol in self.price_cache:
            price, timestamp = self.price_cache[symbol]
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return price
                
        try:
            # Try latest trade first
            trade = self.alpaca_client.get_latest_trade(symbol)
            if trade:
                price = float(trade["price"])
                self.price_cache[symbol] = (price, datetime.now())
                return price
                
            # Fall back to quote midpoint
            quote = self.alpaca_client.get_latest_quote(symbol)
            if quote:
                price = (float(quote["ask_price"]) + float(quote["bid_price"])) / 2
                self.price_cache[symbol] = (price, datetime.now())
                return price
                
            logger.warning(f"No price data for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            return None
            
    async def get_previous_close(self, symbol: str) -> Optional[float]:
        """Get previous day's closing price"""
        try:
            # Get 2 days of daily bars
            bars = self.alpaca_client.get_bars(symbol, "1Day", limit=2)
            if bars is not None and len(bars) >= 2:
                return float(bars.iloc[-2]["close"])
            logger.warning(f"No previous close for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Failed to get previous close for {symbol}: {e}")
            return None
```

### OrderManager

The OrderManager handles order submission and position tracking.

**Interface**:
```python
class OrderManager:
    def __init__(
        self,
        config: Dict,
        alpaca_client: AlpacaClient,
        account_manager: AccountManager,
        market_data: MarketDataFeed,
        risk_manager: RiskManager
    ) -> None:
        self.config = config
        self.alpaca_client = alpaca_client
        self.account_manager = account_manager
        self.market_data = market_data
        self.risk_manager = risk_manager
        self.order_cache: Dict[str, Dict] = {}
        
    async def get_account_equity(self) -> float:
        """Get current account equity"""
        return await self.account_manager.get_equity()
        
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        return await self.market_data.get_current_price(symbol)
        
    async def get_previous_close(self, symbol: str) -> Optional[float]:
        """Get previous close for a symbol"""
        return await self.market_data.get_previous_close(symbol)
        
    async def submit_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: int,
        strategy: str,
        limit_price: Optional[float] = None
    ) -> Optional[Dict]:
        """Submit an order with validation"""
        # Validate with risk manager
        equity = await self.get_account_equity()
        current_price = await self.get_current_price(symbol)
        
        if current_price is None:
            logger.error(f"Cannot submit order for {symbol}: no price data")
            return None
            
        trade_value = qty * current_price
        
        # Determine asset type
        asset_type = self._get_asset_type(symbol)
        
        # Get current position counts
        positions = await self.account_manager.get_positions()
        position_counts = self._count_positions_by_type(positions)
        
        # Validate trade
        is_valid, reasons = self.risk_manager.validate_trade(
            equity=equity,
            proposed_trade_value=trade_value,
            asset_type=asset_type,
            current_positions=position_counts
        )
        
        if not is_valid:
            logger.warning(f"Order rejected for {symbol}: {reasons}")
            return None
            
        # Generate client order ID
        client_order_id = self._generate_client_order_id(symbol, strategy)
        
        # Submit order
        try:
            order = self.alpaca_client.submit_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=qty,
                limit_price=limit_price,
                client_order_id=client_order_id
            )
            
            if order:
                self.order_cache[order["id"]] = order
                logger.info(
                    f"Order submitted: {side} {qty} {symbol} @ "
                    f"{order_type} (ID: {order['id']})"
                )
                return order
            else:
                logger.error(f"Order submission failed for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error submitting order for {symbol}: {e}")
            return None
            
    async def close_position(self, symbol: str) -> Optional[Dict]:
        """Close a position"""
        position = await self.account_manager.get_position(symbol)
        if not position:
            logger.warning(f"No position to close for {symbol}")
            return None
            
        qty = abs(int(position["qty"]))
        side = "sell" if float(position["qty"]) > 0 else "buy"
        
        return await self.submit_order(
            symbol=symbol,
            side=side,
            order_type="market",
            qty=qty,
            strategy="position_close"
        )
        
    async def close_all_positions(self) -> None:
        """Close all open positions"""
        try:
            results = self.alpaca_client.close_all_positions()
            logger.info(f"Closed {len(results)} positions")
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            
    def _get_asset_type(self, symbol: str) -> str:
        """Determine asset type from symbol"""
        if "/" in symbol:  # Crypto format: BTC/USD
            return "crypto"
        elif symbol in ["TQQQ", "SQQQ", "SPXL", "SPXS", "SOXL", "SOXS", "UDOW", "SDOW"]:
            return "etf"
        else:
            return "stock"
            
    def _count_positions_by_type(self, positions: List[Dict]) -> Dict[str, int]:
        """Count positions by asset type"""
        counts = {"crypto": 0, "etf": 0, "stock": 0}
        for position in positions:
            asset_type = self._get_asset_type(position["symbol"])
            counts[asset_type] += 1
        return counts
        
    def _generate_client_order_id(self, symbol: str, strategy: str) -> str:
        """Generate unique client order ID"""
        prefix = self.config.get("execution", {}).get("client_order_id", {}).get("prefix", "pt01")
        timestamp = int(datetime.now().timestamp() * 1000)
        return f"{prefix}_{strategy}_{symbol}_{timestamp}"
```

### WebSocketClient

The WebSocketClient handles real-time data streaming.

**Interface**:
```python
from alpaca.data.live import StockDataStream, CryptoDataStream

class WebSocketClient:
    def __init__(self, config: Dict) -> None:
        self.config = config
        self.api_key = os.getenv("ALPACA_PAPER_API_KEY")
        self.api_secret = os.getenv("ALPACA_PAPER_API_SECRET")
        
        # Initialize streams
        self.stock_stream = StockDataStream(self.api_key, self.api_secret)
        self.crypto_stream = CryptoDataStream(self.api_key, self.api_secret)
        
        self.callbacks: Dict[str, List[Callable]] = {
            "trade": [],
            "quote": [],
            "bar": []
        }
        
    async def connect(self) -> None:
        """Establish WebSocket connections"""
        try:
            logger.info("Connecting to Alpaca WebSocket streams...")
            # Streams connect automatically when subscriptions are made
            logger.info("WebSocket client ready")
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            raise
            
    async def disconnect(self) -> None:
        """Close WebSocket connections"""
        try:
            await self.stock_stream.close()
            await self.crypto_stream.close()
            logger.info("WebSocket connections closed")
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")
            
    def subscribe_trades(self, symbols: List[str], callback: Callable) -> None:
        """Subscribe to trade updates"""
        self.callbacks["trade"].append(callback)
        
        # Separate crypto and stock symbols
        crypto_symbols = [s for s in symbols if "/" in s]
        stock_symbols = [s for s in symbols if "/" not in s]
        
        if crypto_symbols:
            self.crypto_stream.subscribe_trades(self._trade_handler, *crypto_symbols)
            
        if stock_symbols:
            self.stock_stream.subscribe_trades(self._trade_handler, *stock_symbols)
            
        logger.info(f"Subscribed to trades: {symbols}")
        
    def subscribe_quotes(self, symbols: List[str], callback: Callable) -> None:
        """Subscribe to quote updates"""
        self.callbacks["quote"].append(callback)
        
        crypto_symbols = [s for s in symbols if "/" in s]
        stock_symbols = [s for s in symbols if "/" not in s]
        
        if crypto_symbols:
            self.crypto_stream.subscribe_quotes(self._quote_handler, *crypto_symbols)
            
        if stock_symbols:
            self.stock_stream.subscribe_quotes(self._quote_handler, *stock_symbols)
            
        logger.info(f"Subscribed to quotes: {symbols}")
        
    async def _trade_handler(self, trade) -> None:
        """Handle incoming trade updates"""
        trade_data = {
            "symbol": trade.symbol,
            "price": float(trade.price),
            "size": int(trade.size),
            "timestamp": trade.timestamp
        }
        
        for callback in self.callbacks["trade"]:
            try:
                await callback(trade_data)
            except Exception as e:
                logger.error(f"Error in trade callback: {e}")
                
    async def _quote_handler(self, quote) -> None:
        """Handle incoming quote updates"""
        quote_data = {
            "symbol": quote.symbol,
            "bid_price": float(quote.bid_price),
            "ask_price": float(quote.ask_price),
            "bid_size": int(quote.bid_size),
            "ask_size": int(quote.ask_size),
            "timestamp": quote.timestamp
        }
        
        for callback in self.callbacks["quote"]:
            try:
                await callback(quote_data)
            except Exception as e:
                logger.error(f"Error in quote callback: {e}")
                
    def run(self) -> None:
        """Start the WebSocket streams"""
        try:
            self.stock_stream.run()
            self.crypto_stream.run()
        except Exception as e:
            logger.error(f"Error running WebSocket streams: {e}")
```

## Data Models

### Account Data Model

```python
@dataclass
class AccountData:
    """Account information from Alpaca"""
    account_id: str
    equity: float
    cash: float
    buying_power: float
    portfolio_value: float
    pattern_day_trader: bool
    trading_blocked: bool
    account_blocked: bool
    created_at: datetime
    currency: str = "USD"
```

### Position Data Model

```python
@dataclass
class Position:
    """Position information from Alpaca"""
    symbol: str
    qty: int
    side: str  # "long" or "short"
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float
    avg_entry_price: float
    asset_class: str  # "us_equity" or "crypto"
```

### Order Data Model

```python
@dataclass
class Order:
    """Order information from Alpaca"""
    id: str
    client_order_id: str
    symbol: str
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit", "stop"
    qty: int
    filled_qty: int
    status: str  # "new", "filled", "partially_filled", "canceled", "rejected"
    submitted_at: datetime
    filled_at: Optional[datetime]
    filled_avg_price: Optional[float]
    limit_price: Optional[float]
    stop_price: Optional[float]
```

### Bar Data Model

```python
@dataclass
class Bar:
    """OHLCV bar data"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    trade_count: Optional[int] = None
    vwap: Optional[float] = None
```

## Error Handling

### Error Categories

1. **Authentication Errors**: Invalid API keys, expired tokens
   - Action: Log error, halt system, notify admin
   
2. **Rate Limit Errors**: Too many requests
   - Action: Exponential backoff, retry after delay
   
3. **Network Errors**: Connection timeouts, DNS failures
   - Action: Retry with exponential backoff, max 3 attempts
   
4. **Validation Errors**: Invalid order parameters
   - Action: Log error, reject order, continue operation
   
5. **Market Data Errors**: Symbol not found, no data available
   - Action: Log warning, return None, continue operation
   
6. **Order Rejection**: Insufficient buying power, position limits
   - Action: Log rejection reason, notify strategy, continue operation

### Retry Strategy

```python
class RetryStrategy:
    """Exponential backoff retry strategy"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_attempts - 1:
                    raise
                    
                delay = self.base_delay * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
```

### Connection Health Monitoring

```python
class ConnectionHealthMonitor:
    """Monitor API connection health"""
    
    def __init__(self, alpaca_client: AlpacaClient):
        self.alpaca_client = alpaca_client
        self.error_count = 0
        self.last_success: Optional[datetime] = None
        self.check_interval = 60  # seconds
        
    async def start(self) -> None:
        """Start health monitoring"""
        while True:
            try:
                # Ping API
                account = self.alpaca_client.get_account()
                if account:
                    self.error_count = 0
                    self.last_success = datetime.now()
                    logger.debug("API health check: OK")
                else:
                    self.error_count += 1
                    logger.warning("API health check: Failed")
                    
            except Exception as e:
                self.error_count += 1
                logger.error(f"API health check error: {e}")
                
            # Check if error threshold exceeded
            if self.error_count >= 5:
                logger.critical("API error threshold exceeded")
                # Trigger preservation mode
                
            await asyncio.sleep(self.check_interval)
```

## Testing Strategy

The testing strategy follows a dual approach combining unit tests for specific scenarios and property-based tests for universal correctness properties.

### Unit Testing

Unit tests will focus on:
- **Configuration validation**: Test missing credentials, invalid modes
- **Error handling**: Test specific error scenarios (rate limits, auth failures)
- **Data conversion**: Test Alpaca SDK types to PulseTrader types
- **Edge cases**: Test empty responses, malformed data
- **Integration points**: Test component interactions

Example unit tests:
```python
def test_alpaca_client_missing_credentials():
    """Test that missing credentials raise appropriate error"""
    with pytest.raises(ValueError, match="Missing Alpaca API credentials"):
        AlpacaClient({})

def test_order_manager_rejects_insufficient_buying_power():
    """Test order rejection when buying power is insufficient"""
    # Setup mock with low buying power
    # Attempt order
    # Assert order is rejected with correct reason

def test_market_data_feed_handles_missing_symbol():
    """Test graceful handling of invalid symbol"""
    # Request bars for invalid symbol
    # Assert None is returned and warning is logged
```

### Property-Based Testing

Property-based tests will verify universal correctness properties across many generated inputs. Each property test will run a minimum of 100 iterations with randomized inputs.

The testing framework will use `hypothesis` for Python property-based testing:
```python
from hypothesis import given, strategies as st
import hypothesis.strategies as st
```

Each property test must include a comment tag referencing the design property:
```python
# Feature: alpaca-paper-integration, Property 1: <property description>
@given(...)
def test_property_1(...):
    ...
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Error Handling Consistency

*For any* API error or invalid configuration, the system should log detailed error information and raise an appropriate exception type that allows the caller to distinguish between recoverable and non-recoverable errors.

**Validates: Requirements 1.2, 1.6**

### Property 2: Position Data Completeness

*For any* position returned by the system, the position data should contain all required fields: symbol, quantity, entry price, current price, unrealized P/L, and side (long/short).

**Validates: Requirements 2.2, 7.2**

### Property 3: Bar Data Format Consistency

*For any* historical bar data retrieved from Alpaca, the data should be converted to a pandas DataFrame with columns: timestamp, open, high, low, close, volume, and the DataFrame should be indexed by timestamp.

**Validates: Requirements 3.6**

### Property 4: WebSocket Subscription Scalability

*For any* list of symbols (up to 30 symbols per Alpaca's limit), subscribing to trades or quotes should successfully register all symbols and invoke callbacks when updates are received for any subscribed symbol.

**Validates: Requirements 4.7**

### Property 5: Order Submission Completeness

*For any* valid order (market, limit, or stop) with valid parameters (symbol, side, quantity, prices), the submitted order should include a unique client order ID, all specified parameters, and return order details with order ID and status upon successful submission.

**Validates: Requirements 5.1, 5.3, 5.4**

### Property 6: Risk Validation Enforcement

*For any* proposed order, if the order violates risk management rules (reserve violation, position limits, or daily drawdown limits), the order should be rejected before submission to Alpaca and the rejection reason should be logged.

**Validates: Requirements 5.6**

### Property 7: Order Cache Consistency

*For any* order submitted through the Order Manager, the order should be immediately added to the local order cache and retrievable by order ID.

**Validates: Requirements 6.6**

### Property 8: Realized P/L Calculation Accuracy

*For any* position that is closed, the realized P/L should be calculated as (exit_price - entry_price) * quantity, accounting for the position side (long positions profit when exit > entry, short positions profit when exit < entry).

**Validates: Requirements 7.3**

### Property 9: Position Close Order Accuracy

*For any* open position being closed, the close order quantity should exactly match the absolute value of the position quantity, and the order side should be opposite to the position side (sell for long positions, buy for short positions).

**Validates: Requirements 7.6**

### Property 10: Error Threshold Preservation Mode

*For any* error count that exceeds the configured threshold (default 5), the system should trigger preservation mode, which disables new entries and attempts to close risky positions.

**Validates: Requirements 9.3**

### Property 11: Exception Resilience

*For any* exception raised during strategy evaluation, market data retrieval, or order processing, the exception should be caught, logged with full context, and the main event loop should continue running without crashing.

**Validates: Requirements 10.5**

### Property 12: Comprehensive Logging

*For any* order submitted, the system should log the order details (symbol, side, quantity, order type) with a structured log entry that includes timestamp and strategy name, and *for any* error that occurs, the system should log the error with stack trace and context, and *for any* log entry, sensitive data (API keys, secrets) should be sanitized before logging.

**Validates: Requirements 12.3, 12.5, 12.6**



## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage:

**Unit Tests**: Verify specific examples, edge cases, and error conditions
- Configuration validation with missing credentials
- Specific error scenarios (rate limits, authentication failures)
- Data conversion edge cases (empty responses, malformed data)
- Integration between components (AccountManager ↔ AlpacaClient)
- Specific order scenarios (market orders, limit orders, order rejection)

**Property Tests**: Verify universal properties across all inputs
- Error handling consistency across all error types
- Position data completeness for all positions
- Bar data format consistency for all symbols and timeframes
- Order submission completeness for all order types
- Risk validation enforcement for all order scenarios

Both approaches are complementary and necessary for comprehensive coverage. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across the input space.

### Property-Based Testing Configuration

**Framework**: `hypothesis` for Python property-based testing

**Installation**:
```bash
pip install hypothesis
```

**Configuration**:
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `# Feature: alpaca-paper-integration, Property {number}: {property_text}`

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st

# Feature: alpaca-paper-integration, Property 2: Position Data Completeness
@given(
    symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu',))),
    qty=st.integers(min_value=1, max_value=1000),
    entry_price=st.floats(min_value=0.01, max_value=10000.0),
    current_price=st.floats(min_value=0.01, max_value=10000.0)
)
@settings(max_examples=100)
def test_position_data_completeness(symbol, qty, entry_price, current_price):
    """Property: All positions contain required fields"""
    position = create_position(symbol, qty, entry_price, current_price)
    
    assert "symbol" in position
    assert "qty" in position
    assert "avg_entry_price" in position
    assert "current_price" in position
    assert "unrealized_pl" in position
    assert "side" in position
```

### Test Organization

```
tests/
├── integration/
│   ├── test_alpaca_connection.py      # Integration tests with Alpaca API
│   ├── test_account_manager.py        # AccountManager integration tests
│   ├── test_market_data_feed.py       # MarketDataFeed integration tests
│   ├── test_order_manager.py          # OrderManager integration tests
│   └── test_websocket_client.py       # WebSocketClient integration tests
├── unit/
│   ├── test_alpaca_client.py          # AlpacaClient unit tests
│   ├── test_error_handling.py         # Error handling unit tests
│   ├── test_data_conversion.py        # Data conversion unit tests
│   └── test_configuration.py          # Configuration validation tests
└── properties/
    ├── test_error_properties.py       # Property 1: Error handling
    ├── test_position_properties.py    # Property 2, 7, 8, 9: Position-related
    ├── test_data_properties.py        # Property 3: Bar data format
    ├── test_websocket_properties.py   # Property 4: WebSocket subscriptions
    ├── test_order_properties.py       # Property 5, 6: Order submission
    ├── test_system_properties.py      # Property 10, 11: System resilience
    └── test_logging_properties.py     # Property 12: Logging
```

### Integration Test Scripts

The system will provide integration test scripts for manual verification:

**scripts/test_alpaca_connection.py**: Verify API authentication and connectivity
```python
# Test authentication with Alpaca Paper API
# Verify account data retrieval
# Check API response times
```

**scripts/test_market_data.py**: Verify market data retrieval
```python
# Test historical bar retrieval for stocks
# Test historical bar retrieval for crypto
# Test current price retrieval
# Test multiple timeframes
```

**scripts/test_websocket_streaming.py**: Verify WebSocket streaming
```python
# Test WebSocket connection establishment
# Test trade subscription and updates
# Test quote subscription and updates
# Test reconnection on disconnect
```

**scripts/test_order_submission.py**: Verify order submission (dry-run)
```python
# Test market order submission
# Test limit order submission
# Test order status retrieval
# Test order cancellation
# Note: Uses paper trading, no real money at risk
```

### Mocking Strategy

For unit tests that don't require actual Alpaca API calls:

**Mock AlpacaClient responses**:
```python
from unittest.mock import Mock, patch

@patch('services.connectors.alpaca_client.TradingClient')
def test_order_manager_validates_before_submission(mock_trading_client):
    """Test that OrderManager validates with RiskManager before submitting"""
    # Setup mocks
    mock_alpaca = Mock()
    mock_risk_manager = Mock()
    mock_risk_manager.validate_trade.return_value = (False, ["Reserve violation"])
    
    order_manager = OrderManager(config, mock_alpaca, mock_risk_manager)
    
    # Attempt order
    result = await order_manager.submit_order("AAPL", "buy", "market", 100, "test")
    
    # Assert validation was called and order was rejected
    mock_risk_manager.validate_trade.assert_called_once()
    assert result is None
```

### Test Coverage Goals

- **Unit Test Coverage**: Minimum 80% code coverage
- **Integration Test Coverage**: All major workflows (account retrieval, market data, order submission, WebSocket streaming)
- **Property Test Coverage**: All 12 correctness properties implemented
- **Edge Case Coverage**: All identified edge cases (missing credentials, invalid symbols, insufficient buying power, connection failures)

### Continuous Integration

Tests should be run automatically on:
- Every commit to the repository
- Before merging pull requests
- Nightly builds with extended property test iterations (1000+ per property)

**CI Configuration** (GitHub Actions example):
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install hypothesis pytest pytest-cov pytest-asyncio
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=services
      - name: Run property tests
        run: pytest tests/properties/ -v
      - name: Run integration tests
        run: pytest tests/integration/ -v
        env:
          ALPACA_PAPER_API_KEY: ${{ secrets.ALPACA_PAPER_API_KEY }}
          ALPACA_PAPER_API_SECRET: ${{ secrets.ALPACA_PAPER_API_SECRET }}
```

### Manual Testing Checklist

Before deploying to production:

- [ ] Verify Alpaca Paper API authentication
- [ ] Retrieve account data and verify all fields present
- [ ] Retrieve market data for stocks (AAPL, TSLA, SPY)
- [ ] Retrieve market data for crypto (BTC/USD, ETH/USD)
- [ ] Test WebSocket connection and receive trade updates
- [ ] Submit test market order and verify execution
- [ ] Submit test limit order and verify it appears in open orders
- [ ] Cancel test order and verify cancellation
- [ ] Verify risk validation rejects orders that violate rules
- [ ] Verify error handling for invalid symbols
- [ ] Verify error handling for insufficient buying power
- [ ] Verify connection health monitoring and reconnection
- [ ] Verify logging includes all required information
- [ ] Verify sensitive data is sanitized in logs
- [ ] Run system for 1 hour and verify stability
- [ ] Verify preservation mode triggers on error threshold


# Connection Health Monitor

## Overview

The `ConnectionHealthMonitor` provides automated health checking for the Alpaca API connection. It periodically pings the API to verify connectivity, tracks error rates and response times, and automatically triggers preservation mode when error thresholds are exceeded.

## Features

- **Periodic Health Checks**: Automatically pings the Alpaca API at configurable intervals
- **Error Tracking**: Tracks consecutive API errors and resets on success
- **Response Time Monitoring**: Tracks API response times with rolling average calculation
- **Slow Response Detection**: Logs warnings when API responses exceed threshold
- **Preservation Mode**: Automatically triggers preservation mode when error threshold is exceeded
- **Health Status API**: Provides real-time health status information

## Usage

### Basic Initialization

```python
from services.connectors.alpaca_client import AlpacaClient
from services.connectors.connection_health_monitor import ConnectionHealthMonitor

# Initialize AlpacaClient
alpaca_client = AlpacaClient(config)

# Initialize ConnectionHealthMonitor
health_monitor = ConnectionHealthMonitor(
    alpaca_client=alpaca_client,
    check_interval=60,  # Check every 60 seconds
    error_threshold=5,  # Trigger preservation mode after 5 consecutive errors
    slow_response_threshold=5.0  # Log warning if response > 5 seconds
)
```

### Setting Preservation Mode Callback

```python
async def preservation_mode_handler():
    """Handle preservation mode trigger."""
    logger.critical("Preservation mode triggered!")
    # Disable new entries
    # Close losing positions
    # Tighten stop losses
    # etc.

# Register callback
health_monitor.set_preservation_mode_callback(preservation_mode_handler)
```

### Starting and Stopping

```python
# Start health monitoring
await health_monitor.start()

# ... system runs ...

# Stop health monitoring
await health_monitor.stop()
```

### Getting Health Status

```python
# Get current health status
status = health_monitor.get_health_status()

print(f"Healthy: {status['is_healthy']}")
print(f"Error Count: {status['error_count']}")
print(f"Last Response Time: {status['last_response_time']}s")
print(f"Avg Response Time: {status['avg_response_time']}s")
print(f"Preservation Mode: {status['preservation_mode_triggered']}")
```

## Configuration

The ConnectionHealthMonitor can be configured via the main configuration file (`config/main.yaml`):

```yaml
monitoring:
  health_check_interval: 60  # Seconds between health checks
  error_threshold: 5  # Consecutive errors before preservation mode
  slow_response_threshold: 5.0  # Seconds - log warning if exceeded
```

## Health Check Process

1. **Ping API**: Calls `alpaca_client.get_account()` to verify connectivity
2. **Measure Response Time**: Tracks how long the API call takes
3. **Check Response**: 
   - **Success**: Reset error count, update last success timestamp
   - **Failure**: Increment error count, check threshold
4. **Threshold Check**: If error count >= threshold, trigger preservation mode
5. **Slow Response Check**: If response time > threshold, log warning

## Error Handling

### Error Count Behavior

- **On Success**: Error count is reset to 0
- **On Failure**: Error count is incremented by 1
- **Threshold Exceeded**: Preservation mode is triggered (only once)

### Preservation Mode

When the error threshold is exceeded:

1. `preservation_mode_triggered` flag is set to `True`
2. Preservation mode callback is invoked (if registered)
3. Critical log message is generated
4. Flag remains `True` until manually reset

To reset preservation mode after manual intervention:

```python
health_monitor.reset_preservation_mode()
```

## Response Time Tracking

The monitor tracks API response times with a rolling average:

- **Last Response Time**: Most recent API call duration
- **Average Response Time**: Rolling average of last 100 samples
- **Slow Response Threshold**: Configurable threshold for logging warnings

## Integration with PulseTrader

The ConnectionHealthMonitor is integrated into the main orchestrator (`services/orchestrator/run.py`):

```python
# In PulseTraderOrchestrator.__init__()
self.health_monitor = ConnectionHealthMonitor(
    alpaca_client=self.alpaca_client,
    check_interval=self.config.get("monitoring", {}).get("health_check_interval", 60),
    error_threshold=self.config.get("monitoring", {}).get("error_threshold", 5),
    slow_response_threshold=self.config.get("monitoring", {}).get("slow_response_threshold", 5.0)
)
self.health_monitor.set_preservation_mode_callback(self._enter_preservation_mode)

# In PulseTraderOrchestrator.start()
await self.health_monitor.start()

# In PulseTraderOrchestrator.stop()
await self.health_monitor.stop()
```

## Testing

### Unit Tests

Run unit tests with pytest:

```bash
pytest tests/test_connection_health_monitor.py -v
```

### Integration Test

Run the integration test script:

```bash
python scripts/test_connection_health.py
```

This script will:
1. Initialize AlpacaClient and ConnectionHealthMonitor
2. Start health monitoring
3. Run for 30 seconds, displaying health status every 5 seconds
4. Stop health monitoring and display final status

## Monitoring Best Practices

1. **Check Interval**: Set based on your trading frequency
   - High-frequency trading: 30-60 seconds
   - Low-frequency trading: 120-300 seconds

2. **Error Threshold**: Balance between false positives and quick response
   - Recommended: 3-5 consecutive errors
   - Too low: May trigger on temporary network issues
   - Too high: May delay preservation mode activation

3. **Slow Response Threshold**: Set based on acceptable latency
   - Recommended: 5.0 seconds
   - Consider your strategy's time sensitivity

4. **Preservation Mode Callback**: Ensure it's properly implemented
   - Disable new entries immediately
   - Close risky positions
   - Tighten stop losses
   - Notify administrators

## Troubleshooting

### Health Monitor Not Starting

- Check that AlpacaClient is properly initialized
- Verify API credentials are set in environment variables
- Check logs for initialization errors

### Preservation Mode Triggering Frequently

- Check network connectivity
- Verify Alpaca API status (https://status.alpaca.markets/)
- Consider increasing error threshold
- Check for rate limiting issues

### Slow Response Times

- Check network latency
- Verify Alpaca API performance
- Consider geographic location (closer to Alpaca servers = lower latency)
- Check for local system resource constraints

## API Reference

### ConnectionHealthMonitor

#### Constructor

```python
ConnectionHealthMonitor(
    alpaca_client: AlpacaClient,
    check_interval: int = 60,
    error_threshold: int = 5,
    slow_response_threshold: float = 5.0
)
```

#### Methods

- `set_preservation_mode_callback(callback: Callable)`: Register preservation mode callback
- `async start()`: Start health monitoring loop
- `async stop()`: Stop health monitoring loop
- `get_health_status() -> dict`: Get current health status
- `reset_preservation_mode()`: Reset preservation mode flag

#### Health Status Dictionary

```python
{
    "is_healthy": bool,  # Current health status
    "error_count": int,  # Consecutive error count
    "last_success": str,  # ISO timestamp of last success
    "last_check": str,  # ISO timestamp of last check
    "last_response_time": float,  # Last response time in seconds
    "avg_response_time": float,  # Average response time in seconds
    "preservation_mode_triggered": bool  # Preservation mode status
}
```

## Requirements

- Python 3.11+
- alpaca-py
- loguru
- asyncio

## License

Part of PulseTrader.01 autonomous trading system.

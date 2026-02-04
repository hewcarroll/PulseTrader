"""Unit tests for ConnectionHealthMonitor."""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.connectors.connection_health_monitor import ConnectionHealthMonitor


@pytest.fixture
def mock_alpaca_client():
    """Create a mock AlpacaClient."""
    client = Mock()
    client.get_account = Mock(return_value={
        "account_id": "test123",
        "equity": 10000.0,
        "cash": 5000.0,
        "buying_power": 10000.0
    })
    return client


@pytest.fixture
def health_monitor(mock_alpaca_client):
    """Create a ConnectionHealthMonitor instance."""
    return ConnectionHealthMonitor(
        alpaca_client=mock_alpaca_client,
        check_interval=1,  # Short interval for testing
        error_threshold=3,
        slow_response_threshold=2.0
    )


@pytest.mark.asyncio
async def test_initialization(health_monitor):
    """Test ConnectionHealthMonitor initialization."""
    assert health_monitor.error_count == 0
    assert health_monitor.last_success is None
    assert health_monitor.last_check is None
    assert health_monitor.is_healthy is True
    assert health_monitor.preservation_mode_triggered is False
    assert health_monitor.check_interval == 1
    assert health_monitor.error_threshold == 3
    assert health_monitor.slow_response_threshold == 2.0


@pytest.mark.asyncio
async def test_successful_health_check(health_monitor, mock_alpaca_client):
    """Test successful health check resets error count."""
    # Set initial error count
    health_monitor.error_count = 2
    
    # Perform health check
    await health_monitor._perform_health_check()
    
    # Verify error count reset
    assert health_monitor.error_count == 0
    assert health_monitor.is_healthy is True
    assert health_monitor.last_success is not None
    assert health_monitor.last_check is not None
    assert mock_alpaca_client.get_account.called


@pytest.mark.asyncio
async def test_failed_health_check_increments_error_count(health_monitor, mock_alpaca_client):
    """Test failed health check increments error count."""
    # Make API call fail
    mock_alpaca_client.get_account.side_effect = Exception("API Error")
    
    # Perform health check
    await health_monitor._perform_health_check()
    
    # Verify error count incremented
    assert health_monitor.error_count == 1
    assert health_monitor.is_healthy is False


@pytest.mark.asyncio
async def test_error_threshold_triggers_preservation_mode(health_monitor, mock_alpaca_client):
    """Test that exceeding error threshold triggers preservation mode."""
    # Make API call fail
    mock_alpaca_client.get_account.side_effect = Exception("API Error")
    
    # Set up preservation mode callback
    callback_called = False
    
    async def preservation_callback():
        nonlocal callback_called
        callback_called = True
    
    health_monitor.set_preservation_mode_callback(preservation_callback)
    
    # Perform health checks until threshold exceeded
    for _ in range(health_monitor.error_threshold):
        await health_monitor._perform_health_check()
        await asyncio.sleep(0.1)  # Give callback time to execute
    
    # Verify preservation mode triggered
    assert health_monitor.error_count == health_monitor.error_threshold
    assert health_monitor.preservation_mode_triggered is True
    assert callback_called is True


@pytest.mark.asyncio
async def test_error_count_resets_on_success(health_monitor, mock_alpaca_client):
    """Test that error count resets to zero on successful health check."""
    # Set initial error count
    health_monitor.error_count = 2
    
    # Perform successful health check
    await health_monitor._perform_health_check()
    
    # Verify error count reset
    assert health_monitor.error_count == 0
    assert health_monitor.is_healthy is True


@pytest.mark.asyncio
async def test_response_time_tracking(health_monitor, mock_alpaca_client):
    """Test response time tracking."""
    # Perform health check
    await health_monitor._perform_health_check()
    
    # Verify response time tracked
    assert health_monitor.last_response_time is not None
    assert health_monitor.avg_response_time is not None
    assert len(health_monitor.response_time_samples) == 1


@pytest.mark.asyncio
async def test_slow_response_logging(health_monitor, mock_alpaca_client, caplog):
    """Test that slow responses are logged."""
    # Make API call slow
    async def slow_get_account():
        await asyncio.sleep(2.5)  # Longer than slow_response_threshold
        return {"account_id": "test", "equity": 10000.0}
    
    # Replace with async mock
    mock_alpaca_client.get_account = slow_get_account
    
    # Perform health check
    await health_monitor._perform_health_check()
    
    # Verify slow response logged (check if response time > threshold)
    assert health_monitor.last_response_time > health_monitor.slow_response_threshold


@pytest.mark.asyncio
async def test_response_time_rolling_average(health_monitor, mock_alpaca_client):
    """Test response time rolling average calculation."""
    # Perform multiple health checks
    for _ in range(5):
        await health_monitor._perform_health_check()
    
    # Verify rolling average calculated
    assert len(health_monitor.response_time_samples) == 5
    assert health_monitor.avg_response_time is not None
    assert health_monitor.avg_response_time == sum(health_monitor.response_time_samples) / 5


@pytest.mark.asyncio
async def test_max_samples_limit(health_monitor, mock_alpaca_client):
    """Test that response time samples are limited to max_samples."""
    # Set low max_samples for testing
    health_monitor.max_samples = 10
    
    # Perform more health checks than max_samples
    for _ in range(15):
        await health_monitor._perform_health_check()
    
    # Verify samples limited to max_samples
    assert len(health_monitor.response_time_samples) == health_monitor.max_samples


@pytest.mark.asyncio
async def test_get_health_status(health_monitor, mock_alpaca_client):
    """Test get_health_status returns correct information."""
    # Perform health check
    await health_monitor._perform_health_check()
    
    # Get health status
    status = health_monitor.get_health_status()
    
    # Verify status contains expected keys
    assert "is_healthy" in status
    assert "error_count" in status
    assert "last_success" in status
    assert "last_check" in status
    assert "last_response_time" in status
    assert "avg_response_time" in status
    assert "preservation_mode_triggered" in status
    
    # Verify values
    assert status["is_healthy"] is True
    assert status["error_count"] == 0
    assert status["last_success"] is not None
    assert status["last_check"] is not None


@pytest.mark.asyncio
async def test_preservation_mode_callback_registration(health_monitor):
    """Test preservation mode callback registration."""
    callback = AsyncMock()
    health_monitor.set_preservation_mode_callback(callback)
    
    assert health_monitor.preservation_mode_callback is callback


@pytest.mark.asyncio
async def test_preservation_mode_only_triggered_once(health_monitor, mock_alpaca_client):
    """Test that preservation mode is only triggered once."""
    # Make API call fail
    mock_alpaca_client.get_account.side_effect = Exception("API Error")
    
    # Set up preservation mode callback
    callback_count = 0
    
    async def preservation_callback():
        nonlocal callback_count
        callback_count += 1
    
    health_monitor.set_preservation_mode_callback(preservation_callback)
    
    # Perform health checks beyond threshold
    for _ in range(health_monitor.error_threshold + 3):
        await health_monitor._perform_health_check()
        await asyncio.sleep(0.1)
    
    # Verify preservation mode triggered only once
    assert callback_count == 1


@pytest.mark.asyncio
async def test_reset_preservation_mode(health_monitor):
    """Test reset_preservation_mode resets the flag."""
    # Set preservation mode triggered
    health_monitor.preservation_mode_triggered = True
    
    # Reset
    health_monitor.reset_preservation_mode()
    
    # Verify reset
    assert health_monitor.preservation_mode_triggered is False


@pytest.mark.asyncio
async def test_start_and_stop(health_monitor):
    """Test starting and stopping the health monitor."""
    # Start monitor
    await health_monitor.start()
    assert health_monitor.running is True
    assert health_monitor._task is not None
    
    # Stop monitor
    await health_monitor.stop()
    assert health_monitor.running is False


@pytest.mark.asyncio
async def test_start_when_already_running(health_monitor, caplog):
    """Test starting monitor when already running logs warning."""
    # Start monitor
    await health_monitor.start()
    
    # Try to start again
    await health_monitor.start()
    
    # Verify warning logged
    assert "already running" in caplog.text.lower()
    
    # Cleanup
    await health_monitor.stop()


@pytest.mark.asyncio
async def test_stop_when_not_running(health_monitor, caplog):
    """Test stopping monitor when not running logs warning."""
    # Try to stop without starting
    await health_monitor.stop()
    
    # Verify warning logged
    assert "not running" in caplog.text.lower()


@pytest.mark.asyncio
async def test_monitor_loop_performs_periodic_checks(health_monitor, mock_alpaca_client):
    """Test that monitor loop performs periodic health checks."""
    # Start monitor
    await health_monitor.start()
    
    # Wait for a few checks
    await asyncio.sleep(2.5)  # Should perform 2-3 checks with 1s interval
    
    # Stop monitor
    await health_monitor.stop()
    
    # Verify checks were performed
    assert mock_alpaca_client.get_account.call_count >= 2
    assert health_monitor.last_check is not None


@pytest.mark.asyncio
async def test_preservation_mode_callback_error_handling(health_monitor, mock_alpaca_client, caplog):
    """Test that errors in preservation mode callback are handled gracefully."""
    # Make API call fail
    mock_alpaca_client.get_account.side_effect = Exception("API Error")
    
    # Set up preservation mode callback that raises error
    async def failing_callback():
        raise Exception("Callback error")
    
    health_monitor.set_preservation_mode_callback(failing_callback)
    
    # Perform health checks until threshold exceeded
    for _ in range(health_monitor.error_threshold):
        await health_monitor._perform_health_check()
        await asyncio.sleep(0.1)
    
    # Verify preservation mode still triggered despite callback error
    assert health_monitor.preservation_mode_triggered is True

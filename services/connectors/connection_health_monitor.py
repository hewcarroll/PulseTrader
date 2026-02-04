"""Connection health monitoring for Alpaca API."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional, Callable
from loguru import logger


class ConnectionHealthMonitor:
    """
    Monitor API connection health and track error rates.
    
    This class periodically pings the Alpaca API to verify connectivity,
    tracks error counts, and triggers preservation mode when error thresholds
    are exceeded.
    """
    
    def __init__(
        self,
        alpaca_client,
        check_interval: int = 60,
        error_threshold: int = 5,
        slow_response_threshold: float = 5.0
    ) -> None:
        """
        Initialize ConnectionHealthMonitor.
        
        Args:
            alpaca_client: AlpacaClient instance for API health checks
            check_interval: Interval between health checks in seconds (default: 60)
            error_threshold: Number of consecutive errors before triggering preservation mode (default: 5)
            slow_response_threshold: Response time threshold in seconds for logging slow responses (default: 5.0)
        """
        self.alpaca_client = alpaca_client
        self.check_interval = check_interval
        self.error_threshold = error_threshold
        self.slow_response_threshold = slow_response_threshold
        
        # Health tracking
        self.error_count = 0
        self.last_success: Optional[datetime] = None
        self.last_check: Optional[datetime] = None
        self.is_healthy = True
        self.preservation_mode_triggered = False
        
        # Response time tracking
        self.last_response_time: Optional[float] = None
        self.avg_response_time: Optional[float] = None
        self.response_time_samples: list[float] = []
        self.max_samples = 100  # Keep last 100 samples for average
        
        # Callbacks
        self.preservation_mode_callback: Optional[Callable] = None
        
        # Control
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
        logger.info(
            f"ConnectionHealthMonitor initialized: "
            f"check_interval={check_interval}s, error_threshold={error_threshold}, "
            f"slow_response_threshold={slow_response_threshold}s"
        )
    
    def set_preservation_mode_callback(self, callback: Callable) -> None:
        """
        Set callback to be invoked when preservation mode is triggered.
        
        Args:
            callback: Async function to call when error threshold is exceeded
        """
        self.preservation_mode_callback = callback
        logger.info("Preservation mode callback registered")
    
    async def start(self) -> None:
        """Start the health monitoring loop."""
        if self.running:
            logger.warning("ConnectionHealthMonitor is already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("ConnectionHealthMonitor started")
    
    async def stop(self) -> None:
        """Stop the health monitoring loop."""
        if not self.running:
            logger.warning("ConnectionHealthMonitor is not running")
            return
        
        self.running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("ConnectionHealthMonitor stopped")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop that performs periodic health checks."""
        logger.info("Health monitoring loop started")
        
        try:
            while self.running:
                await self._perform_health_check()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in health monitoring loop: {e}")
            raise
    
    async def _perform_health_check(self) -> None:
        """
        Perform a single health check by pinging the Alpaca API.
        
        Tracks response time, error count, and triggers preservation mode
        if error threshold is exceeded.
        """
        self.last_check = datetime.now()
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Ping API by retrieving account data
            account = self.alpaca_client.get_account()
            
            # Calculate response time
            end_time = asyncio.get_event_loop().time()
            response_time = end_time - start_time
            
            # Track response time
            self._track_response_time(response_time)
            
            # Check for slow response
            if response_time > self.slow_response_threshold:
                logger.warning(
                    f"Slow API response: {response_time:.2f}s "
                    f"(threshold: {self.slow_response_threshold}s)"
                )
            
            # Health check passed
            if account:
                self.error_count = 0
                self.last_success = datetime.now()
                self.is_healthy = True
                
                logger.debug(
                    f"API health check: OK (response_time={response_time:.2f}s, "
                    f"avg_response_time={self.avg_response_time:.2f}s)"
                )
            else:
                # Account data is None, which shouldn't happen
                self._handle_health_check_failure("Account data is None")
                
        except Exception as e:
            # Calculate response time even on error
            end_time = asyncio.get_event_loop().time()
            response_time = end_time - start_time
            self._track_response_time(response_time)
            
            # Health check failed
            self._handle_health_check_failure(str(e))
    
    def _track_response_time(self, response_time: float) -> None:
        """
        Track API response time and calculate rolling average.
        
        Args:
            response_time: Response time in seconds
        """
        self.last_response_time = response_time
        
        # Add to samples
        self.response_time_samples.append(response_time)
        
        # Keep only last N samples
        if len(self.response_time_samples) > self.max_samples:
            self.response_time_samples.pop(0)
        
        # Calculate average
        if self.response_time_samples:
            self.avg_response_time = sum(self.response_time_samples) / len(self.response_time_samples)
    
    def _handle_health_check_failure(self, error_message: str) -> None:
        """
        Handle health check failure by incrementing error count and
        triggering preservation mode if threshold is exceeded.
        
        Args:
            error_message: Description of the failure
        """
        self.error_count += 1
        self.is_healthy = False
        
        logger.error(
            f"API health check failed (error_count={self.error_count}/{self.error_threshold}): "
            f"{error_message}"
        )
        
        # Check if error threshold exceeded
        if self.error_count >= self.error_threshold and not self.preservation_mode_triggered:
            self._trigger_preservation_mode()
    
    def _trigger_preservation_mode(self) -> None:
        """
        Trigger preservation mode when error threshold is exceeded.
        
        Logs critical error and invokes preservation mode callback if registered.
        """
        self.preservation_mode_triggered = True
        
        logger.critical(
            f"API error threshold exceeded ({self.error_count} consecutive errors). "
            f"TRIGGERING PRESERVATION MODE"
        )
        
        # Invoke callback if registered
        if self.preservation_mode_callback:
            try:
                asyncio.create_task(self.preservation_mode_callback())
            except Exception as e:
                logger.error(f"Error invoking preservation mode callback: {e}")
        else:
            logger.warning("No preservation mode callback registered")
    
    def get_health_status(self) -> dict:
        """
        Get current health status.
        
        Returns:
            Dictionary containing health status information:
                - is_healthy: Boolean indicating if API is healthy
                - error_count: Current consecutive error count
                - last_success: Timestamp of last successful health check
                - last_check: Timestamp of last health check
                - last_response_time: Last API response time in seconds
                - avg_response_time: Average API response time in seconds
                - preservation_mode_triggered: Boolean indicating if preservation mode was triggered
        """
        return {
            "is_healthy": self.is_healthy,
            "error_count": self.error_count,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_response_time": self.last_response_time,
            "avg_response_time": self.avg_response_time,
            "preservation_mode_triggered": self.preservation_mode_triggered
        }
    
    def reset_preservation_mode(self) -> None:
        """
        Reset preservation mode flag.
        
        This should be called after manual intervention to restore normal operation.
        """
        self.preservation_mode_triggered = False
        logger.info("Preservation mode flag reset")

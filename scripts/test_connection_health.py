"""
Integration test script for ConnectionHealthMonitor.

This script demonstrates the ConnectionHealthMonitor functionality
by performing health checks against the Alpaca Paper API.

Usage:
    python scripts/test_connection_health.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

from services.connectors.alpaca_client import AlpacaClient
from services.connectors.connection_health_monitor import ConnectionHealthMonitor


async def preservation_mode_callback():
    """Callback invoked when preservation mode is triggered."""
    logger.critical("=" * 60)
    logger.critical("PRESERVATION MODE TRIGGERED")
    logger.critical("This would normally:")
    logger.critical("  - Disable new entries")
    logger.critical("  - Close losing positions")
    logger.critical("  - Tighten stop losses")
    logger.critical("=" * 60)


async def main():
    """Main test function."""
    # Load environment variables
    load_dotenv()
    
    logger.info("=" * 60)
    logger.info("ConnectionHealthMonitor Integration Test")
    logger.info("=" * 60)
    
    try:
        # Initialize AlpacaClient
        logger.info("Initializing AlpacaClient...")
        alpaca_client = AlpacaClient({})
        logger.info("✓ AlpacaClient initialized")
        
        # Test initial API connectivity
        logger.info("\nTesting initial API connectivity...")
        account = alpaca_client.get_account()
        logger.info(f"✓ API connection successful")
        logger.info(f"  Account ID: {account['account_id']}")
        logger.info(f"  Equity: ${account['equity']:,.2f}")
        
        # Initialize ConnectionHealthMonitor
        logger.info("\nInitializing ConnectionHealthMonitor...")
        health_monitor = ConnectionHealthMonitor(
            alpaca_client=alpaca_client,
            check_interval=5,  # Check every 5 seconds for testing
            error_threshold=3,  # Lower threshold for testing
            slow_response_threshold=2.0
        )
        
        # Set preservation mode callback
        health_monitor.set_preservation_mode_callback(preservation_mode_callback)
        logger.info("✓ ConnectionHealthMonitor initialized")
        
        # Start health monitoring
        logger.info("\nStarting health monitoring...")
        await health_monitor.start()
        logger.info("✓ Health monitoring started")
        
        # Run for 30 seconds
        logger.info("\nMonitoring API health for 30 seconds...")
        logger.info("(Press Ctrl+C to stop early)")
        
        for i in range(6):
            await asyncio.sleep(5)
            
            # Get health status
            status = health_monitor.get_health_status()
            
            logger.info(f"\n--- Health Check {i+1}/6 ---")
            logger.info(f"  Healthy: {status['is_healthy']}")
            logger.info(f"  Error Count: {status['error_count']}")
            logger.info(f"  Last Response Time: {status['last_response_time']:.3f}s" if status['last_response_time'] else "  Last Response Time: N/A")
            logger.info(f"  Avg Response Time: {status['avg_response_time']:.3f}s" if status['avg_response_time'] else "  Avg Response Time: N/A")
            logger.info(f"  Preservation Mode: {status['preservation_mode_triggered']}")
        
        # Stop health monitoring
        logger.info("\nStopping health monitoring...")
        await health_monitor.stop()
        logger.info("✓ Health monitoring stopped")
        
        # Final status
        logger.info("\n" + "=" * 60)
        logger.info("Test completed successfully!")
        logger.info("=" * 60)
        
        final_status = health_monitor.get_health_status()
        logger.info("\nFinal Health Status:")
        logger.info(f"  Healthy: {final_status['is_healthy']}")
        logger.info(f"  Total Errors: {final_status['error_count']}")
        logger.info(f"  Avg Response Time: {final_status['avg_response_time']:.3f}s" if final_status['avg_response_time'] else "  Avg Response Time: N/A")
        logger.info(f"  Preservation Mode Triggered: {final_status['preservation_mode_triggered']}")
        
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        if 'health_monitor' in locals():
            await health_monitor.stop()
    except Exception as e:
        logger.error(f"\nTest failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

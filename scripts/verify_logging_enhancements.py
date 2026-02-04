"""
Verification script for Task 14: Comprehensive Logging Enhancements

This script demonstrates the logging enhancements made to:
1. OrderManager - Enhanced order submission, fill, and rejection logging
2. Log level configuration - Support for LOG_LEVEL environment variable

Usage:
    python scripts/verify_logging_enhancements.py
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def verify_order_manager_logging():
    """Verify OrderManager has enhanced logging."""
    print("=" * 70)
    print("Verifying OrderManager Logging Enhancements")
    print("=" * 70)
    
    with open("services/order_router/order_manager.py", "r") as f:
        content = f.read()
    
    checks = [
        ("Order rejection logging", "Order REJECTED"),
        ("Order submission logging", "Submitting order"),
        ("Order success logging", "Order SUBMITTED successfully"),
        ("Order fill logging method", "def _log_order_fill"),
        ("Filled order logging", "Order FILLED"),
        ("Partially filled logging", "Order PARTIALLY FILLED"),
        ("Order status method", "async def get_order_status"),
        ("Close position enhanced logging", "Closing position"),
        ("Close all positions logging", "Position close order submitted"),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_string in checks:
        if check_string in content:
            print(f"✓ {check_name}: FOUND")
            passed += 1
        else:
            print(f"✗ {check_name}: NOT FOUND")
            failed += 1
    
    print(f"\nOrderManager Logging: {passed} passed, {failed} failed")
    return failed == 0


def verify_log_level_configuration():
    """Verify LOG_LEVEL environment variable support."""
    print("\n" + "=" * 70)
    print("Verifying LOG_LEVEL Environment Variable Support")
    print("=" * 70)
    
    with open("services/orchestrator/run.py", "r") as f:
        content = f.read()
    
    checks = [
        ("LOG_LEVEL environment variable", 'os.getenv("LOG_LEVEL")'),
        ("Environment variable precedence", "Environment variable takes precedence"),
        ("Log level validation", "valid_levels"),
        ("TRACE level support", '"TRACE"'),
        ("DEBUG level support", '"DEBUG"'),
        ("INFO level support", '"INFO"'),
        ("WARNING level support", '"WARNING"'),
        ("ERROR level support", '"ERROR"'),
        ("CRITICAL level support", '"CRITICAL"'),
        ("Invalid level handling", "Invalid log level"),
        ("Log level confirmation", "Logging configured with level"),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_string in checks:
        if check_string in content:
            print(f"✓ {check_name}: FOUND")
            passed += 1
        else:
            print(f"✗ {check_name}: NOT FOUND")
            failed += 1
    
    print(f"\nLog Level Configuration: {passed} passed, {failed} failed")
    return failed == 0


def verify_alpaca_client_logging():
    """Verify AlpacaClient already has comprehensive logging (task 14.1 - completed)."""
    print("\n" + "=" * 70)
    print("Verifying AlpacaClient Logging (Task 14.1 - Already Complete)")
    print("=" * 70)
    
    with open("services/connectors/alpaca_client.py", "r") as f:
        content = f.read()
    
    checks = [
        ("API request logging", "logger.debug"),
        ("API error logging", "logger.error"),
        ("Detailed error handling", "_handle_api_error"),
        ("Rate limit logging", "Rate limit"),
        ("Authentication error logging", "Authentication failed"),
        ("Order submission logging", "Order submitted"),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_string in checks:
        if check_string in content:
            print(f"✓ {check_name}: FOUND")
            passed += 1
        else:
            print(f"✗ {check_name}: NOT FOUND")
            failed += 1
    
    print(f"\nAlpacaClient Logging: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print("Task 14: Comprehensive Logging - Verification Report")
    print("=" * 70)
    
    results = []
    
    # Verify each component
    results.append(("OrderManager Logging (14.2)", verify_order_manager_logging()))
    results.append(("Log Level Configuration (14.5)", verify_log_level_configuration()))
    results.append(("AlpacaClient Logging (14.1)", verify_alpaca_client_logging()))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for component, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{component}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Task 14 Implementation Complete!")
    else:
        print("✗ SOME CHECKS FAILED - Review implementation")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

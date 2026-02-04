#!/usr/bin/env python3
"""Verification script for Task 1: Setup and dependencies

This script verifies that:
1. alpaca-py SDK is installed
2. hypothesis is installed
3. Environment variable validation utility works correctly
"""

import sys
import importlib.util


def check_package_installed(package_name: str) -> bool:
    """Check if a Python package is installed"""
    spec = importlib.util.find_spec(package_name)
    return spec is not None


def main():
    """Run verification checks"""
    print("=" * 60)
    print("Task 1 Setup Verification")
    print("=" * 60)
    
    all_passed = True
    
    # Check alpaca-py
    print("\n1. Checking alpaca-py installation...")
    if check_package_installed("alpaca"):
        print("   ✓ alpaca-py is installed")
    else:
        print("   ✗ alpaca-py is NOT installed")
        print("   Run: pip install alpaca-py")
        all_passed = False
    
    # Check hypothesis
    print("\n2. Checking hypothesis installation...")
    if check_package_installed("hypothesis"):
        print("   ✓ hypothesis is installed")
    else:
        print("   ✗ hypothesis is NOT installed")
        print("   Run: pip install hypothesis")
        all_passed = False
    
    # Check config validator
    print("\n3. Checking config validator utility...")
    try:
        from services.utils.config_validator import (
            ConfigValidator,
            ConfigValidationError,
            validate_config
        )
        print("   ✓ Config validator module imports successfully")
        
        # Test basic functionality
        validator = ConfigValidator()
        print("   ✓ ConfigValidator instantiates successfully")
        
    except ImportError as e:
        print(f"   ✗ Failed to import config validator: {e}")
        all_passed = False
    except Exception as e:
        print(f"   ✗ Error testing config validator: {e}")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All verification checks passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some verification checks failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

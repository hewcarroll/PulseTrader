"""Configuration validation utility for PulseTrader

This module provides utilities to validate required environment variables
and configuration settings at system startup.
"""

import os
from typing import List, Tuple, Optional
from pathlib import Path
from loguru import logger


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigValidator:
    """Validates system configuration and environment variables"""
    
    REQUIRED_ENV_VARS = [
        "ALPACA_PAPER_API_KEY",
        "ALPACA_PAPER_API_SECRET",
        "JWT_SECRET_KEY"
    ]
    
    OPTIONAL_ENV_VARS = {
        "ALPACA_MODE": "paper",
        "LOG_LEVEL": "INFO"
    }
    
    VALID_ALPACA_MODES = ["paper", "live"]
    
    def __init__(self):
        """Initialize the configuration validator"""
        self.missing_vars: List[str] = []
        self.invalid_vars: List[Tuple[str, str, str]] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> bool:
        """Validate all configuration requirements
        
        Returns:
            bool: True if all validations pass, False otherwise
            
        Raises:
            ConfigValidationError: If critical configuration is missing or invalid
        """
        self._check_env_file()
        self._validate_required_env_vars()
        self._validate_optional_env_vars()
        self._validate_alpaca_mode()
        
        if self.missing_vars or self.invalid_vars:
            self._log_validation_errors()
            raise ConfigValidationError(
                f"Configuration validation failed. "
                f"Missing: {self.missing_vars}, Invalid: {self.invalid_vars}"
            )
        
        if self.warnings:
            for warning in self.warnings:
                logger.warning(warning)
        
        self._log_success()
        return True
    
    def _check_env_file(self) -> None:
        """Check if .env file exists and provide instructions if missing"""
        env_path = Path(".env")
        if not env_path.exists():
            self.warnings.append(
                ".env file not found. Please create a .env file with required variables:\n"
                "  ALPACA_PAPER_API_KEY=your_api_key\n"
                "  ALPACA_PAPER_API_SECRET=your_api_secret\n"
                "  JWT_SECRET_KEY=your_jwt_secret\n"
                "  ALPACA_MODE=paper"
            )
    
    def _validate_required_env_vars(self) -> None:
        """Validate that all required environment variables are present"""
        for var in self.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if not value or value.strip() == "":
                self.missing_vars.append(var)
                logger.error(f"Required environment variable missing: {var}")
    
    def _validate_optional_env_vars(self) -> None:
        """Validate optional environment variables and set defaults"""
        for var, default in self.OPTIONAL_ENV_VARS.items():
            value = os.getenv(var)
            if not value:
                os.environ[var] = default
                logger.info(f"Using default value for {var}: {default}")
    
    def _validate_alpaca_mode(self) -> None:
        """Validate ALPACA_MODE is either 'paper' or 'live'"""
        mode = os.getenv("ALPACA_MODE", "paper").lower()
        
        if mode not in self.VALID_ALPACA_MODES:
            self.warnings.append(
                f"Invalid ALPACA_MODE '{mode}'. Must be 'paper' or 'live'. "
                f"Defaulting to 'paper'."
            )
            os.environ["ALPACA_MODE"] = "paper"
        else:
            logger.info(f"ALPACA_MODE set to: {mode}")
    
    def _log_validation_errors(self) -> None:
        """Log detailed validation errors"""
        logger.error("=" * 60)
        logger.error("CONFIGURATION VALIDATION FAILED")
        logger.error("=" * 60)
        
        if self.missing_vars:
            logger.error("Missing required environment variables:")
            for var in self.missing_vars:
                logger.error(f"  - {var}")
        
        if self.invalid_vars:
            logger.error("Invalid environment variables:")
            for var, value, reason in self.invalid_vars:
                logger.error(f"  - {var}={value}: {reason}")
        
        logger.error("=" * 60)
        logger.error("Please check your .env file and ensure all required variables are set.")
        logger.error("=" * 60)
    
    def _log_success(self) -> None:
        """Log successful validation"""
        logger.info("=" * 60)
        logger.info("CONFIGURATION VALIDATION SUCCESSFUL")
        logger.info("=" * 60)
        logger.info("Configuration summary:")
        logger.info(f"  ALPACA_MODE: {os.getenv('ALPACA_MODE')}")
        logger.info(f"  LOG_LEVEL: {os.getenv('LOG_LEVEL')}")
        logger.info(f"  ALPACA_PAPER_API_KEY: {'*' * 8}...{os.getenv('ALPACA_PAPER_API_KEY', '')[-4:]}")
        logger.info("=" * 60)


def validate_config() -> bool:
    """Convenience function to validate configuration
    
    Returns:
        bool: True if validation passes
        
    Raises:
        ConfigValidationError: If validation fails
    """
    validator = ConfigValidator()
    return validator.validate_all()


def get_required_env_var(var_name: str) -> str:
    """Get a required environment variable or raise an error
    
    Args:
        var_name: Name of the environment variable
        
    Returns:
        str: Value of the environment variable
        
    Raises:
        ConfigValidationError: If the variable is not set
    """
    value = os.getenv(var_name)
    if not value or value.strip() == "":
        raise ConfigValidationError(f"Required environment variable not set: {var_name}")
    return value


def get_optional_env_var(var_name: str, default: str) -> str:
    """Get an optional environment variable with a default value
    
    Args:
        var_name: Name of the environment variable
        default: Default value if not set
        
    Returns:
        str: Value of the environment variable or default
    """
    value = os.getenv(var_name)
    if not value or value.strip() == "":
        return default
    return value

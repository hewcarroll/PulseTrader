"""Tests for configuration validation utility"""

import os
import pytest
from services.utils.config_validator import (
    ConfigValidator,
    ConfigValidationError,
    validate_config,
    get_required_env_var,
    get_optional_env_var
)


class TestConfigValidator:
    """Test suite for ConfigValidator"""
    
    def setup_method(self):
        """Setup test environment before each test"""
        # Store original env vars
        self.original_env = {}
        for var in ["ALPACA_PAPER_API_KEY", "ALPACA_PAPER_API_SECRET", 
                    "JWT_SECRET_KEY", "ALPACA_MODE", "LOG_LEVEL"]:
            self.original_env[var] = os.getenv(var)
        
        # Clear env vars for testing
        for var in self.original_env.keys():
            if var in os.environ:
                del os.environ[var]
    
    def teardown_method(self):
        """Restore environment after each test"""
        # Restore original env vars
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_missing_required_env_vars(self):
        """Test that missing required environment variables raise error"""
        validator = ConfigValidator()
        
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate_all()
        
        assert "ALPACA_PAPER_API_KEY" in str(exc_info.value)
        assert len(validator.missing_vars) == 3
    
    def test_valid_configuration(self):
        """Test that valid configuration passes validation"""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key_123"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret_456"
        os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_789"
        os.environ["ALPACA_MODE"] = "paper"
        
        validator = ConfigValidator()
        result = validator.validate_all()
        
        assert result is True
        assert len(validator.missing_vars) == 0
        assert len(validator.invalid_vars) == 0
    
    def test_invalid_alpaca_mode(self):
        """Test that invalid ALPACA_MODE defaults to paper with warning"""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key_123"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret_456"
        os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_789"
        os.environ["ALPACA_MODE"] = "invalid_mode"
        
        validator = ConfigValidator()
        result = validator.validate_all()
        
        assert result is True
        assert os.getenv("ALPACA_MODE") == "paper"
        assert len(validator.warnings) > 0
    
    def test_optional_env_vars_defaults(self):
        """Test that optional environment variables get default values"""
        os.environ["ALPACA_PAPER_API_KEY"] = "test_key_123"
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret_456"
        os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_789"
        
        validator = ConfigValidator()
        validator.validate_all()
        
        assert os.getenv("ALPACA_MODE") == "paper"
        assert os.getenv("LOG_LEVEL") == "INFO"
    
    def test_get_required_env_var_success(self):
        """Test getting a required environment variable"""
        os.environ["TEST_VAR"] = "test_value"
        
        value = get_required_env_var("TEST_VAR")
        assert value == "test_value"
        
        del os.environ["TEST_VAR"]
    
    def test_get_required_env_var_missing(self):
        """Test that missing required env var raises error"""
        with pytest.raises(ConfigValidationError) as exc_info:
            get_required_env_var("NONEXISTENT_VAR")
        
        assert "NONEXISTENT_VAR" in str(exc_info.value)
    
    def test_get_optional_env_var_with_default(self):
        """Test getting optional environment variable with default"""
        value = get_optional_env_var("NONEXISTENT_VAR", "default_value")
        assert value == "default_value"
    
    def test_get_optional_env_var_existing(self):
        """Test getting existing optional environment variable"""
        os.environ["TEST_OPTIONAL"] = "actual_value"
        
        value = get_optional_env_var("TEST_OPTIONAL", "default_value")
        assert value == "actual_value"
        
        del os.environ["TEST_OPTIONAL"]
    
    def test_empty_string_env_var_treated_as_missing(self):
        """Test that empty string environment variables are treated as missing"""
        os.environ["ALPACA_PAPER_API_KEY"] = ""
        os.environ["ALPACA_PAPER_API_SECRET"] = "test_secret"
        os.environ["JWT_SECRET_KEY"] = "test_jwt"
        
        validator = ConfigValidator()
        
        with pytest.raises(ConfigValidationError):
            validator.validate_all()
        
        assert "ALPACA_PAPER_API_KEY" in validator.missing_vars

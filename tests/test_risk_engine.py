"""Test suite for Risk Engine."""

import pytest

from services.risk_engine.risk_manager import RiskManager


@pytest.fixture
def config():
    """Load test configuration."""
    return {
        "accounts": {
            "default": {
                "risk": {
                    "reserve_percentage": 20.0,
                    "tiers": {
                        "tier_100_25k": {
                            "range": [100, 25000],
                            "per_trade_min": 8.0,
                            "per_trade_max": 15.0,
                            "daily_max_drawdown": 6.0,
                            "aggression": "high",
                        }
                    },
                    "max_positions": {
                        "crypto": 3,
                        "etf": 1,
                        "stock": 2,
                    },
                    "milestone_floors": {
                        "enabled": True,
                        "thresholds": [32000, 150000],
                        "floor_percentage": 93.75,
                    },
                }
            }
        }
    }


def test_reserve_calculation(config):
    """Test 20% reserve is always enforced."""
    risk_manager = RiskManager(config)
    test_cases = [
        (500, 400),
        (1000, 800),
        (25000, 20000),
    ]

    for equity, expected_available in test_cases:
        available = risk_manager.calculate_available_capital(equity)
        assert abs(float(available) - expected_available) < 0.01, (
            f"Reserve calculation failed for ${equity}"
        )


def test_reserve_violation_prevention(config):
    """Test reserve violation is prevented."""
    risk_manager = RiskManager(config)
    equity = 1000.0

    is_valid, reason = risk_manager.check_reserve_violation(equity, 850.0)

    assert is_valid is False, "Reserve violation not prevented!"
    assert "reserve violation" in reason.lower()


def test_position_sizing(config):
    """Test position sizing respects tier limits."""
    risk_manager = RiskManager(config)
    equity = 1000.0
    result = risk_manager.calculate_position_size(equity, price=50.0, stop_loss_pct=2.0)

    assert 64 <= result["position_value"] <= 120, "Position size outside tier limits"
    assert result["shares"] is not None
    assert result["tier"] == "tier_100_25k"


def test_daily_drawdown_tracking(config):
    """Test daily drawdown calculation."""
    risk_manager = RiskManager(config)
    risk_manager.update_daily_drawdown(1000.0)

    drawdown = risk_manager.update_daily_drawdown(950.0)
    assert abs(float(drawdown) - 5.0) < 0.01

    is_valid, _ = risk_manager.check_daily_drawdown_limit(950.0)
    assert is_valid is True

    drawdown = risk_manager.update_daily_drawdown(940.0)

    is_valid, reason = risk_manager.check_daily_drawdown_limit(940.0)
    assert is_valid is False
    assert "drawdown limit" in reason.lower()


def test_position_limits(config):
    """Test position concurrency limits."""
    risk_manager = RiskManager(config)

    current_positions = {"crypto": 2}
    is_valid, _ = risk_manager.check_position_limits(current_positions, "crypto")
    assert is_valid is True

    current_positions = {"crypto": 3}
    is_valid, reason = risk_manager.check_position_limits(current_positions, "crypto")
    assert is_valid is False
    assert "position limit" in reason.lower()


def test_milestone_floors(config):
    """Test milestone floor setting and checking."""
    risk_manager = RiskManager(config)
    risk_manager.set_milestone_floor(32000)

    floors = risk_manager.get_milestone_floors(30000)
    assert len(floors) == 1
    assert floors[0]["floor"] == 30000.0

    is_approaching = risk_manager.is_approaching_milestone_floor(30500)
    assert is_approaching is True


def test_trade_validation_comprehensive(config):
    """Test comprehensive trade validation."""
    risk_manager = RiskManager(config)
    equity = 1000.0

    is_valid, reasons = risk_manager.validate_trade(
        equity=equity,
        proposed_trade_value=100.0,
        asset_type="crypto",
        current_positions={"crypto": 1},
    )
    assert is_valid is True
    assert len(reasons) == 0

    is_valid, reasons = risk_manager.validate_trade(
        equity=equity,
        proposed_trade_value=850.0,
        asset_type="crypto",
        current_positions={"crypto": 1},
    )
    assert is_valid is False
    assert len(reasons) > 0
    assert any("reserve" in reason.lower() for reason in reasons)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

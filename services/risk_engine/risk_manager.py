"""
Risk Manager - Core risk management system
Enforces the MANDATORY 20% reserve and tier-based risk parameters.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from loguru import logger


class RiskManager:
    """
    Core risk management system for PulseTrader.01.
    """

    RESERVE_PERCENTAGE = Decimal("20.0")

    def __init__(self, config: Dict) -> None:
        self.config = config
        self.risk_config = config.get("accounts", {}).get("default", {}).get("risk", {})
        self.tiers = self._load_tiers()
        self.milestone_floors: List[Dict] = []
        self.daily_start_equity: Optional[Decimal] = None
        self.daily_drawdown = Decimal("0.0")

        logger.info("Risk Manager initialized")

    def _load_tiers(self) -> Dict:
        tier_config = self.risk_config.get("tiers", {})
        tiers = {}

        for tier_name, tier_data in tier_config.items():
            tiers[tier_name] = {
                "name": tier_name,
                "range": tuple(tier_data["range"]),
                "per_trade_min": Decimal(str(tier_data["per_trade_min"])),
                "per_trade_max": Decimal(str(tier_data["per_trade_max"])),
                "daily_max_drawdown": Decimal(str(tier_data["daily_max_drawdown"])),
                "aggression": tier_data["aggression"],
            }

        return tiers

    def get_current_tier(self, equity: float) -> Dict:
        equity_decimal = Decimal(str(equity))

        for tier_data in self.tiers.values():
            min_equity, max_equity = tier_data["range"]
            if Decimal(str(min_equity)) <= equity_decimal < Decimal(str(max_equity)):
                return tier_data

        return self.tiers["tier_1m_plus"]

    def calculate_available_capital(self, equity: float) -> Decimal:
        equity_decimal = Decimal(str(equity))
        reserve_amount = equity_decimal * (self.RESERVE_PERCENTAGE / Decimal("100"))
        available = equity_decimal - reserve_amount

        logger.debug(
            "Equity: ${equity:.2f} | Reserve (20%): ${reserve:.2f} | Available: ${available:.2f}".format(
                equity=equity_decimal, reserve=reserve_amount, available=available
            )
        )

        return available

    def calculate_position_size(
        self,
        equity: float,
        risk_percentage: Optional[float] = None,
        price: Optional[float] = None,
        stop_loss_pct: Optional[float] = None,
    ) -> Dict:
        tier = self.get_current_tier(equity)
        available_capital = self.calculate_available_capital(equity)

        if risk_percentage is None:
            risk_pct = (tier["per_trade_min"] + tier["per_trade_max"]) / Decimal("2")
        else:
            risk_pct = Decimal(str(risk_percentage))
            risk_pct = max(tier["per_trade_min"], min(tier["per_trade_max"], risk_pct))

        position_value = available_capital * (risk_pct / Decimal("100"))

        shares = None
        if price is not None:
            shares = int(position_value / Decimal(str(price)))
            position_value = Decimal(str(shares)) * Decimal(str(price))

        risk_amount = None
        if stop_loss_pct is not None and price is not None and shares is not None:
            stop_loss_distance = abs(Decimal(str(stop_loss_pct))) / Decimal("100")
            risk_amount = Decimal(str(shares)) * Decimal(str(price)) * stop_loss_distance

        result = {
            "position_value": float(position_value),
            "shares": shares,
            "risk_percentage": float(risk_pct),
            "risk_amount": float(risk_amount) if risk_amount else None,
            "tier": tier["name"],
            "available_capital": float(available_capital),
        }

        logger.debug(f"Position sizing: {result}")

        return result

    def check_reserve_violation(self, equity: float, proposed_trade_value: float) -> Tuple[bool, str]:
        available_capital = self.calculate_available_capital(equity)

        if Decimal(str(proposed_trade_value)) > available_capital:
            reason = (
                f"Trade value ${proposed_trade_value:.2f} exceeds available capital "
                f"${available_capital:.2f} (reserve violation)"
            )
            logger.warning(f"RESERVE VIOLATION PREVENTED: {reason}")
            return False, reason

        return True, "OK"

    def check_position_limits(self, current_positions: Dict, asset_type: str) -> Tuple[bool, str]:
        max_positions = self.risk_config.get("max_positions", {})
        max_allowed = max_positions.get(asset_type, 0)
        current_count = current_positions.get(asset_type, 0)

        if current_count >= max_allowed:
            reason = f"{asset_type.upper()} position limit reached ({current_count}/{max_allowed})"
            logger.warning(f"POSITION LIMIT: {reason}")
            return False, reason

        return True, "OK"

    def update_daily_drawdown(self, current_equity: float) -> Decimal:
        today = date.today()
        if self.daily_start_equity is None or datetime.now().date() != today:
            self.daily_start_equity = Decimal(str(current_equity))
            self.daily_drawdown = Decimal("0.0")
            logger.info(f"Daily start equity set: ${self.daily_start_equity:.2f}")

        current_equity_decimal = Decimal(str(current_equity))
        drawdown = (
            (self.daily_start_equity - current_equity_decimal) / self.daily_start_equity
        ) * Decimal("100")
        self.daily_drawdown = max(self.daily_drawdown, drawdown)

        return self.daily_drawdown

    def check_daily_drawdown_limit(self, current_equity: float) -> Tuple[bool, str]:
        drawdown = self.update_daily_drawdown(current_equity)
        tier = self.get_current_tier(current_equity)
        max_drawdown = tier["daily_max_drawdown"]

        if drawdown >= max_drawdown:
            reason = f"Daily drawdown limit reached: {drawdown:.2f}% >= {max_drawdown:.2f}%"
            logger.error(f"DRAWDOWN LIMIT EXCEEDED: {reason}")
            return False, reason

        if drawdown >= max_drawdown * Decimal("0.8"):
            logger.warning(
                f"Daily drawdown approaching limit: {drawdown:.2f}% / {max_drawdown:.2f}%"
            )

        return True, "OK"

    def set_milestone_floor(self, milestone_equity: float) -> None:
        floor_config = self.risk_config.get("milestone_floors", {})
        if not floor_config.get("enabled", False):
            return

        floor_percentage = Decimal(str(floor_config.get("floor_percentage", 93.75))) / Decimal("100")
        floor_value = Decimal(str(milestone_equity)) * floor_percentage

        self.milestone_floors.append(
            {
                "milestone": milestone_equity,
                "floor": float(floor_value),
                "set_date": datetime.now().isoformat(),
            }
        )

        logger.info(f"Milestone floor set: ${milestone_equity:,.0f} → Floor: ${floor_value:,.2f}")

    def get_milestone_floors(self, current_equity: float) -> List[Dict]:
        return [floor for floor in self.milestone_floors if current_equity >= floor["floor"]]

    def is_approaching_milestone_floor(self, current_equity: float) -> bool:
        for floor_data in self.milestone_floors:
            floor = Decimal(str(floor_data["floor"]))
            threshold = floor * Decimal("1.02")

            if Decimal(str(current_equity)) <= threshold:
                logger.warning(f"Approaching milestone floor: ${current_equity:.2f} near ${floor:.2f}")
                return True

        return False

    async def should_enter_preservation_mode(self, current_equity: float, error_count: int = 0) -> bool:
        preservation_config = self.config.get("emergency", {}).get("preservation_mode", {})

        if not preservation_config.get("auto_trigger", False):
            return False

        triggers = preservation_config.get("trigger_conditions", [])

        if "approaching_milestone_floor" in triggers:
            if self.is_approaching_milestone_floor(current_equity):
                logger.critical("TRIGGER: Approaching milestone floor")
                return True

        if "daily_drawdown_exceeded" in triggers:
            is_valid, _ = self.check_daily_drawdown_limit(current_equity)
            if not is_valid:
                logger.critical("TRIGGER: Daily drawdown limit exceeded")
                return True

        if "api_errors_threshold" in triggers:
            if error_count >= 5:
                logger.critical(f"TRIGGER: API error threshold exceeded ({error_count} errors)")
                return True

        return False

    def validate_trade(
        self,
        equity: float,
        proposed_trade_value: float,
        asset_type: str,
        current_positions: Dict,
    ) -> Tuple[bool, List[str]]:
        reasons = []

        is_valid, reason = self.check_reserve_violation(equity, proposed_trade_value)
        if not is_valid:
            reasons.append(reason)

        is_valid, reason = self.check_position_limits(current_positions, asset_type)
        if not is_valid:
            reasons.append(reason)

        is_valid, reason = self.check_daily_drawdown_limit(equity)
        if not is_valid:
            reasons.append(reason)

        if self.is_approaching_milestone_floor(equity):
            reasons.append("Approaching milestone floor - high caution")

        is_valid = len(reasons) == 0

        if not is_valid:
            logger.warning(f"Trade validation FAILED: {', '.join(reasons)}")

        return is_valid, reasons

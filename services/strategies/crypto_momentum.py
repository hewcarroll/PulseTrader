"""
Crypto Momentum Strategy
24/7 fast compounding with crypto assets.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd
from loguru import logger

from services.strategies.base_strategy import BaseStrategy


class CryptoMomentumStrategy(BaseStrategy):
    """
    Crypto momentum strategy for fast compounding.
    """

    def __init__(self, config: Dict, risk_manager, order_manager, market_data) -> None:
        super().__init__(config, risk_manager, order_manager, market_data)

        self.assets = config.get("assets", [])
        self.timeframes = config.get("timeframes", ["5m", "15m"])
        self.entry_config = config.get("entry", {})
        self.exit_config = config.get("exit", {})

        self.positions: Dict[str, Dict] = {}

        logger.info(f"Crypto Momentum Strategy initialized for {len(self.assets)} assets")

    async def evaluate(self) -> None:
        if not self.is_running or self.new_entries_disabled:
            return

        for asset in self.assets:
            try:
                if asset in self.positions:
                    await self._manage_position(asset)
                else:
                    await self._check_entry_signal(asset)

            except Exception as exc:
                logger.error(f"Error evaluating {asset}: {exc}")

    async def _check_entry_signal(self, asset: str) -> None:
        timeframe = self.timeframes[0]
        bars = await self.market_data.get_bars(asset, timeframe, limit=50)

        if bars is None or len(bars) < 25:
            return

        close = bars["close"]
        volume = bars["volume"]

        ema21 = close.ewm(span=21).mean().iloc[-1]
        current_price = close.iloc[-1]

        vwap = (
            bars["volume"] * (bars["high"] + bars["low"] + bars["close"]) / 3
        ).cumsum() / bars["volume"].cumsum()
        current_vwap = vwap.iloc[-1]

        avg_volume_20 = volume.rolling(20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_impulse = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0

        price_above_ema21 = self.entry_config.get("price_above_ema21", True)
        price_above_vwap = self.entry_config.get("price_above_vwap", True)
        volume_threshold = self.entry_config.get("volume_impulse_multiplier", 1.5)

        signal_valid = True
        reasons = []

        if price_above_ema21 and current_price <= ema21:
            signal_valid = False
            reasons.append(f"price {current_price:.2f} <= EMA21 {ema21:.2f}")

        if price_above_vwap and current_price <= current_vwap:
            signal_valid = False
            reasons.append(f"price {current_price:.2f} <= VWAP {current_vwap:.2f}")

        if volume_impulse < volume_threshold:
            signal_valid = False
            reasons.append(f"volume impulse {volume_impulse:.2f}x < {volume_threshold}x")

        if signal_valid:
            logger.info(f"Entry signal: {asset} @ ${current_price:.2f}")
            await self._enter_position(asset, current_price)
        else:
            logger.debug(f"No entry for {asset}: {', '.join(reasons)}")

    async def _enter_position(self, asset: str, price: float) -> None:
        equity = await self.order_manager.get_account_equity()

        stop_loss_pct = abs(self.exit_config.get("hard_stop_pct", -1.5))
        position_info = self.risk_manager.calculate_position_size(
            equity=equity,
            price=price,
            stop_loss_pct=stop_loss_pct,
        )

        is_valid, reasons = self.risk_manager.validate_trade(
            equity=equity,
            proposed_trade_value=position_info["position_value"],
            asset_type="crypto",
            current_positions={"crypto": len(self.positions)},
        )

        if not is_valid:
            logger.warning(f"Trade rejected for {asset}: {reasons}")
            return

        order = await self.order_manager.submit_order(
            symbol=asset,
            side="buy",
            order_type="market",
            qty=position_info["shares"],
            strategy="crypto_momentum",
        )

        if order:
            self.positions[asset] = {
                "entry_price": price,
                "entry_time": order["submitted_at"],
                "qty": position_info["shares"],
                "stop_loss": price * (1 + stop_loss_pct / 100),
                "targets": self.exit_config.get("targets", [2.0, 4.0, 6.0]),
                "trailing_stop_active": False,
                "pyramid_added": False,
                "order_id": order["id"],
            }

            logger.info(
                f"Position entered: {asset} - {position_info['shares']} shares @ ${price:.2f}"
            )

    async def _manage_position(self, asset: str) -> None:
        position = self.positions[asset]

        current_price = await self.market_data.get_current_price(asset)
        if current_price is None:
            return

        entry_price = position["entry_price"]
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        pyramid_config = self.exit_config.get("pyramid", {})
        if (
            pyramid_config.get("enabled", False)
            and not position["pyramid_added"]
            and pnl_pct >= pyramid_config.get("add_after_profit_pct", 2.0)
        ):
            await self._pyramid_position(asset, current_price)

        trailing_config = self.exit_config.get("trailing_stop", {})
        if (
            trailing_config.get("enabled", False)
            and not position.get("trailing_stop_active")
            and pnl_pct >= trailing_config.get("activation_pct", 2.0)
        ):
            position["trailing_stop_active"] = True
            position["trailing_stop_price"] = current_price * (
                1 - trailing_config.get("trailing_pct", 1.0) / 100
            )
            logger.info(
                f"Trailing stop activated for {asset} @ ${position['trailing_stop_price']:.2f}"
            )

        if position.get("trailing_stop_active"):
            new_stop = current_price * (1 - trailing_config.get("trailing_pct", 1.0) / 100)
            if new_stop > position["trailing_stop_price"]:
                position["trailing_stop_price"] = new_stop
                logger.debug(f"Trailing stop updated for {asset}: ${new_stop:.2f}")

        should_exit = False
        exit_reason = ""

        for target in position["targets"]:
            if pnl_pct >= target:
                should_exit = True
                exit_reason = f"Target hit: +{target}%"
                break

        if position.get("trailing_stop_active") and current_price <= position["trailing_stop_price"]:
            should_exit = True
            exit_reason = f"Trailing stop: ${position['trailing_stop_price']:.2f}"

        if current_price <= position["stop_loss"]:
            should_exit = True
            exit_reason = f"Hard stop: ${position['stop_loss']:.2f}"

        if should_exit:
            await self._exit_position(asset, current_price, exit_reason)

    async def _pyramid_position(self, asset: str, current_price: float) -> None:
        position = self.positions[asset]
        pyramid_config = self.exit_config.get("pyramid", {})

        additional_size_pct = pyramid_config.get("additional_size_pct", 50.0)
        additional_qty = int(position["qty"] * (additional_size_pct / 100))

        if additional_qty > 0:
            order = await self.order_manager.submit_order(
                symbol=asset,
                side="buy",
                order_type="market",
                qty=additional_qty,
                strategy="crypto_momentum_pyramid",
            )

            if order:
                total_qty = position["qty"] + additional_qty
                avg_price = (
                    (position["entry_price"] * position["qty"]) + (current_price * additional_qty)
                ) / total_qty

                position["qty"] = total_qty
                position["entry_price"] = avg_price
                position["pyramid_added"] = True

                if pyramid_config.get("move_stop_to_breakeven", True):
                    position["stop_loss"] = avg_price

                logger.info(
                    f"Pyramid add: {asset} +{additional_qty} shares @ ${current_price:.2f} (avg: ${avg_price:.2f})"
                )

    async def _exit_position(self, asset: str, price: float, reason: str) -> None:
        position = self.positions[asset]

        order = await self.order_manager.submit_order(
            symbol=asset,
            side="sell",
            order_type="market",
            qty=position["qty"],
            strategy="crypto_momentum_exit",
        )

        if order:
            pnl_pct = ((price - position["entry_price"]) / position["entry_price"]) * 100
            pnl_amount = (price - position["entry_price"]) * position["qty"]

            logger.info(
                f"Position exited: {asset} - P/L: ${pnl_amount:.2f} ({pnl_pct:+.2f}%) - Reason: {reason}"
            )

            del self.positions[asset]

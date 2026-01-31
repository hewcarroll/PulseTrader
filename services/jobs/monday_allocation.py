"""
Monday Allocation Job
Executes weekly dividend stock purchases every Monday.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from loguru import logger


class MondayAllocationJob:
    """
    Handles Monday morning dividend allocation.
    """

    def __init__(self, config: Dict, account_manager, order_manager) -> None:
        self.config = config
        self.account_manager = account_manager
        self.order_manager = order_manager

        self.dividend_config = config.get("accounts", {}).get("default", {}).get("dividend", {})
        self.monday_config = self.dividend_config.get("monday_allocation", {})

        logger.info("Monday Allocation Job initialized")

    async def schedule(self) -> None:
        return None

    async def execute(self) -> None:
        if datetime.now().weekday() != 0:
            return

        if not self.monday_config.get("enabled", False):
            return

        logger.info("=" * 60)
        logger.info("Monday Allocation Job Starting")
        logger.info("=" * 60)

        try:
            account = self.account_manager.get_primary_account()
            equity = await account.get_equity()

            suspend_until = self.dividend_config.get("suspend_until_equity", 5000)
            if equity < suspend_until:
                logger.info(
                    f"Dividend allocation suspended until equity >= ${suspend_until:,.0f} "
                    f"(current: ${equity:,.2f})"
                )
                return

            allocation_pct = self._get_allocation_percentage(equity)

            if allocation_pct == 0:
                logger.info("No allocation scheduled for this equity level")
                return

            cash = await account.get_cash()
            allocation_amount = Decimal(str(cash)) * (
                Decimal(str(allocation_pct)) / Decimal("100")
            )

            logger.info(f"Allocation: {allocation_pct}% of ${cash:,.2f} = ${allocation_amount:,.2f}")

            universe = self.dividend_config.get("universe", [])

            holdings = await account.get_positions()
            dividend_holdings = {holding["symbol"]: holding["qty"] for holding in holdings if holding["symbol"] in universe}

            min_diversification = self.dividend_config.get("min_diversification", 3)
            num_holdings = max(min_diversification, len(dividend_holdings) + 1)

            amount_per_holding = allocation_amount / Decimal(str(num_holdings))

            selected_holdings = self._select_holdings(universe, dividend_holdings, num_holdings)

            market_sentiment = await self._assess_market_sentiment()
            order_type = self._get_order_type(market_sentiment)

            logger.info(f"Market sentiment: {market_sentiment} → Order type: {order_type}")

            orders = []
            for symbol in selected_holdings:
                price = await self.order_manager.get_current_price(symbol)
                if price is None:
                    continue
                qty = int(amount_per_holding / Decimal(str(price)))

                if qty > 0:
                    order = await self.order_manager.submit_dividend_order(
                        symbol=symbol,
                        qty=qty,
                        order_type=order_type,
                        force_fill_time=self.monday_config.get("force_fill_time", "10:30:00"),
                    )

                    if order:
                        orders.append(order)
                        logger.info(f"Order submitted: {symbol} x{qty} @ ~${price:.2f} ({order_type})")

            logger.info(f"Monday allocation complete: {len(orders)} orders submitted")

            await self._generate_report(equity, allocation_amount, orders)

        except Exception as exc:
            logger.exception(f"Error in Monday allocation: {exc}")

    def _get_allocation_percentage(self, equity: float) -> float:
        allocation_tiers = self.dividend_config.get("allocation_tiers", [])

        for tier in allocation_tiers:
            if tier["equity_min"] <= equity < tier["equity_max"]:
                return tier["weekly_percentage"]

        return 0.0

    def _select_holdings(self, universe: List[str], current_holdings: Dict, target_count: int) -> List[str]:
        if len(current_holdings) < target_count:
            available = [symbol for symbol in universe if symbol not in current_holdings]
            need = target_count - len(current_holdings)
            selected = list(current_holdings.keys()) + available[:need]
        else:
            selected = list(current_holdings.keys())[:target_count]

        return selected

    async def _assess_market_sentiment(self) -> str:
        spy_price = await self.order_manager.get_current_price("SPY")
        spy_prev_close = await self.order_manager.get_previous_close("SPY")

        if spy_price and spy_prev_close:
            change_pct = ((spy_price - spy_prev_close) / spy_prev_close) * 100

            if change_pct > 0.5:
                return "bullish"
            if change_pct < -0.5:
                return "bearish"

        return "neutral"

    def _get_order_type(self, sentiment: str) -> str:
        order_types = self.monday_config.get("order_types", {})
        return order_types.get(sentiment, "market")

    async def _generate_report(self, equity: float, allocation_amount: Decimal, orders: List) -> None:
        report = {
            "date": datetime.now().isoformat(),
            "equity": float(equity),
            "allocation_amount": float(allocation_amount),
            "orders": [
                {
                    "symbol": order["symbol"],
                    "qty": order["qty"],
                    "order_type": order["order_type"],
                    "status": order["status"],
                }
                for order in orders
            ],
        }

        report_path = f"reports/monday/allocation_{datetime.now().strftime('%Y%m%d')}.json"
        logger.info(f"Monday report saved: {report_path}")
        _ = report

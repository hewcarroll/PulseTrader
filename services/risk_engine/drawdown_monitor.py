"""Drawdown monitoring helper."""
from __future__ import annotations

from decimal import Decimal


def calculate_drawdown(start_equity: float, current_equity: float) -> Decimal:
    """Calculate drawdown percentage."""
    start = Decimal(str(start_equity))
    current = Decimal(str(current_equity))
    if start == 0:
        return Decimal("0")
    return ((start - current) / start) * Decimal("100")

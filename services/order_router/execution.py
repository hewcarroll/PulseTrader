"""Order execution helpers."""
from __future__ import annotations


def build_order_payload(symbol: str, side: str, qty: int, order_type: str) -> dict:
    """Construct basic order payload."""
    return {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "type": order_type,
    }

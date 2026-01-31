"""VWAP slicing algorithm placeholder."""
from __future__ import annotations

from typing import List


def build_vwap_slices(total_qty: int, slices: int) -> List[int]:
    """Split quantity into equal slices."""
    if slices <= 0:
        return []
    base = total_qty // slices
    remainder = total_qty % slices
    return [base + (1 if idx < remainder else 0) for idx in range(slices)]

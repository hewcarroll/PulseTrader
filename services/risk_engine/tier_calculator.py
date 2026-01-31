"""Tier calculation utilities."""
from __future__ import annotations

from typing import Dict


def calculate_tier(equity: float, tiers: Dict) -> Dict:
    """Return tier configuration based on equity."""
    for tier_data in tiers.values():
        min_equity, max_equity = tier_data["range"]
        if min_equity <= equity < max_equity:
            return tier_data
    return tiers.get("tier_1m_plus", {})

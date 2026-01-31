"""Signal tracking placeholder."""
from __future__ import annotations

from typing import Dict, List


class SignalTracker:
    """Track strategy signal performance."""

    def __init__(self) -> None:
        self.signals: List[Dict] = []

    def record(self, signal: Dict) -> None:
        self.signals.append(signal)

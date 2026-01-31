"""State persistence for PulseTrader.01."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from loguru import logger


class StateManager:
    """Handle runtime state persistence."""

    def __init__(self, state_path: str = "runtime/state.json") -> None:
        self.state_path = Path(state_path)

    async def load_state(self) -> Dict[str, Any]:
        """Load persisted state if available."""
        if not self.state_path.exists():
            logger.info("No existing state file found")
            return {}

        try:
            data = json.loads(self.state_path.read_text())
            logger.info("Runtime state loaded")
            return data
        except json.JSONDecodeError as exc:
            logger.warning(f"Failed to parse state file: {exc}")
            return {}

    async def save_state(self, state: Dict[str, Any]) -> None:
        """Persist runtime state to disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2))
        logger.debug("Runtime state saved")

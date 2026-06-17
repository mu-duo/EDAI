"""Agent configuration — load from JSON, use as a plain data object."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentConfig:
    """Configuration for a LangGraph-based EDA agent.

    Create from a JSON file or a plain dict.  Every field has a sensible
    default so you can start with an empty ``AgentConfig()``.
    """

    model: str = "mock"
    """Model identifier — ``"mock"`` uses the built-in keyword matcher."""

    system_prompt: str = (
        "You are an EDA assistant. Convert the user's natural language "
        "request into a Tcl command and execute it."
    )

    tools: list[str] = field(default_factory=list)
    """Allowed Tcl commands (e.g. ``["get_cells", "report_timing"]``)."""

    max_iterations: int = 10
    """Maximum number of agent→tool→agent loops before giving up."""

    delay: float = 0.3
    """Simulated latency in seconds when ``model == "mock"`` (for realistic feel)."""

    # ── factory methods ──────────────────────────────────────────────

    @classmethod
    def from_json(cls, path: str | Path) -> AgentConfig:
        """Load config from a JSON file.

        Example JSON::

            {
                "model": "mock",
                "system_prompt": "You are an EDA assistant.",
                "tools": ["get_cells", "report_timing"],
                "max_iterations": 5,
            }
        """
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise TypeError(f"Config JSON must be a dict, got {type(raw).__name__}")
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        """Create config from a plain dict (keys match field names)."""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in valid_keys})

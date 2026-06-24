"""Agent configuration — minimal data object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for the EDA agent.

    Parameters
    ----------
    model:
        LLM model identifier (e.g. ``"deepseek-v4-flash"``).
    max_iterations:
        Maximum number of agent→tool→agent loops before giving up.

    """

    model: str = "deepseek-v4-flash"
    max_iterations: int = 10

"""Mock LLM agent for natural-language → Tcl translation.

Drop-in placeholder that simulates an LLM-powered interface.
Swap the implementation with a real API call (OpenAI, Anthropic, etc.)
without changing the REPL code.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from edai.tool.tcl.engine import TclEngine

# ── keyword → Tcl command mapping for the mock ──────────────────────

_TRANSLATIONS: list[tuple[list[str], str]] = [
    (
        ["place all", "place design", "run placement", "place the design"],
        "place_design",
    ),
    (
        ["route all", "route design", "run routing", "route the design"],
        "route_design",
    ),
    (["timing", "report timing", "show timing"], "report_timing"),
    (["get cells", "list cells", "show cells", "what cells"], "get_cells"),
    (["get nets", "list nets", "show nets"], "get_nets"),
    (["get pins", "list pins", "show pins", "what pins"], "get_pins"),
    (["help", "what can you do", "commands", "?"], "help"),
]


class Agent:
    """Natural-language → Tcl translator.

    The mock implementation uses keyword matching.  Replace
    ``translate()`` with an actual LLM call for production use.
    """

    def __init__(self, engine: TclEngine | None = None) -> None:
        self.engine = engine
        self._simulate_delay = 0.3  # seconds — feels realistic

    async def translate(
        self,
        text: str,
        *,
        context: dict[str, object] | str | None = None,  # noqa: ARG002
    ) -> str:
        """Convert natural language *text* to a Tcl command.

        This is the single extension point: replace the body with
        an ``await openai.chat.completions.create(...)`` call.
        """
        # Simulate network latency
        await asyncio.sleep(self._simulate_delay)

        text_lower = text.lower().strip()

        # Exact or partial keyword match
        for keywords, tcl_cmd in _TRANSLATIONS:
            if any(kw in text_lower for kw in keywords):
                return tcl_cmd

        # Fallback: wrap as a Tcl comment
        return f"# (unrecognized) {text.strip()}"

    def translate_sync(
        self,
        text: str,
        *,
        context: dict[str, object] | str | None = None,  # noqa: ARG002
    ) -> str:
        """Wrap ``translate`` as a synchronous, blocking call."""
        return asyncio.run(self.translate(text, context=context))

    # ── configuration helpers for downstream real implementations ──

    @property
    def delay(self) -> float:
        """Simulated latency in seconds (mock only)."""
        return self._simulate_delay

    @delay.setter
    def delay(self, value: float) -> None:
        self._simulate_delay = value

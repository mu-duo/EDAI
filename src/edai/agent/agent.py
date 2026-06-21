"""Legacy-compatible mock Agent for natural-language → Tcl translation.

This module provides the ``Agent`` class that was the original EDAI agent.
It performs simple keyword matching (no real LLM) and uses the canonical
:class:`~edai.core.Message.Message` type for internal bookkeeping.

Use ``LangGraphAgent`` from :mod:`edai.agent.graph` for the full graph-based
agent; this module exists for backward compatibility and tests.
"""

from __future__ import annotations

import asyncio
from typing import Any

from edai.core.Message import Message

# Keyword → Tcl command mapping (mirrors graph.py for consistency)
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
    """Mock natural-language → Tcl translator.

    Performs keyword matching instead of a real LLM call.  Maintains a
    conversation history as ``list[Message]``.

    Parameters
    ----------
    engine:
        Optional TclEngine.  When provided, recognised commands are
        executed immediately.

    """

    def __init__(self, engine: Any = None) -> None:  # noqa: ANN401
        self._engine = engine
        self._delay: float = 0.3

        # Conversation history — list[Message]
        self._messages: list[Message] = [
            Message.system(
                "You are an EDA assistant that translates natural language "
                "into Tcl commands."
            ),
        ]

    # ── public API ─────────────────────────────────────────────────

    async def translate(
        self,
        text: str,
        *,
        context: dict | str | None = None,  # noqa: ARG002
    ) -> str:
        """Translate natural-language *text* into a Tcl command.

        Parameters
        ----------
        text:
            User input.
        context:
            Ignored by the mock (accepts for API compatibility).

        Returns
        -------
        str
            The matched Tcl command, or ``# (unrecognized) ...``.

        """
        if self._delay > 0:
            await asyncio.sleep(self._delay)

        user_msg = Message.human(text)
        self._messages.append(user_msg)

        tcl = self._mock_translate(text)

        ai_msg = Message.ai(f"Running: {tcl}")
        self._messages.append(ai_msg)

        return tcl

    def translate_sync(
        self,
        text: str,
        *,
        context: dict | str | None = None,
    ) -> str:
        """Wrap :meth:`translate` as a synchronous call."""
        return asyncio.run(self.translate(text, context=context))

    # ── simulated delay ────────────────────────────────────────────

    @property
    def delay(self) -> float:
        """Simulated latency in seconds (applied before each translation)."""
        return self._delay

    @delay.setter
    def delay(self, value: float) -> None:
        self._delay = max(0.0, value)

    # ── message-history accessors ──────────────────────────────────

    @property
    def messages(self) -> list[Message]:
        """Read-only conversation history."""
        return list(self._messages)

    def clear_history(self) -> None:
        """Reset the conversation, keeping only the initial system message."""
        self._messages = [self._messages[0]]

    # ── internal helpers ───────────────────────────────────────────

    @staticmethod
    def _mock_translate(text: str) -> str:
        """Run keyword match and return the Tcl command."""
        text_lower = text.lower().strip()
        for keywords, tcl_cmd in _TRANSLATIONS:
            if any(kw in text_lower for kw in keywords):
                return tcl_cmd
        return f"# (unrecognized) {text.strip()}"

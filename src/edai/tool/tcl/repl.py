"""EDA Tcl input-processing engine.

Provides the core dispatch logic shared by all UIs (Textual TUI and
any future interface).  All methods are UI-agnostic: they write via
the ``output`` callable instead of printing directly, and the sync
variant avoids ``asyncio`` for thread‑worker usage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from edai.agent.agent import Agent
    from edai.tool.tcl.engine import TclEngine


class EdaRepl:
    """EDAI input processor — pure logic, no UI dependency.

    Two dispatch entrypoints:

    * :meth:`_handle_input` — async, uses ``await agent.translate()``
    * :meth:`_handle_input_sync` — sync, uses ``agent.translate_sync()``
      (suitable for Textual thread workers)

    The ``output`` callable receives every line of text produced by the
    engine (command results, error messages, translations).
    """

    def __init__(
        self,
        engine: TclEngine,
        agent: Agent,
        *,
        verbose: bool = False,
        output: Callable[[str], None] = print,
    ) -> None:
        self.engine = engine
        self.agent = agent
        self.verbose = verbose
        self.output = output

    # ── dispatch : async ──────────────────────────────────────────

    async def _handle_input(self, text: str) -> int:
        """Process one line of user input (async).

        Dispatch order:
        1. ``/command`` → special command registry
        2. Valid Tcl command → engine execution
        3. Natural language → LLM agent translation
        """
        text = text.strip()
        if not text:
            return 0

        if text.startswith("/"):
            return self._handle_special(text)

        if self.engine.is_valid_tcl(text):
            return self._exec_tcl(text)

        # ── natural language (async agent call) ──
        if self.verbose:
            self.output("(translating via agent…)")

        try:
            tcl_cmd = await self.agent.translate(text, context=self._context())
        except Exception as exc:  # noqa: BLE001
            self.output(f"Agent error: {exc}")
            return 1

        return self._exec_translated(tcl_cmd)

    # ── dispatch : sync ───────────────────────────────────────────

    def _handle_input_sync(self, text: str) -> int:
        """Process one line of user input synchronously.

        Uses ``agent.translate_sync()`` so it can run in a thread
        worker without a running asyncio event loop.
        """
        text = text.strip()
        if not text:
            return 0

        if text.startswith("/"):
            return self._handle_special(text)

        if self.engine.is_valid_tcl(text):
            return self._exec_tcl(text)

        # ── natural language (sync wrapper) ──
        if self.verbose:
            self.output("(translating via agent…)")

        try:
            tcl_cmd = self.agent.translate_sync(text, context=self._context())
        except Exception as exc:  # noqa: BLE001
            self.output(f"Agent error: {exc}")
            return 1

        return self._exec_translated(tcl_cmd)

    # ── shared helpers ─────────────────────────────────────────────

    def _exec_tcl(self, text: str) -> int:
        """Execute a Tcl command and write output via ``self.output``."""
        try:
            output = self.engine.execute(text)
        except Exception as exc:  # noqa: BLE001
            self.output(f"Error: {exc}")
            return 1
        if output:
            self.output(output)
        return 0

    def _exec_translated(self, tcl_cmd: str) -> int:
        """Execute a Tcl command produced by the NL agent."""
        if tcl_cmd.startswith("#"):
            self.output(tcl_cmd)
            return 1

        self.output(f"→ {tcl_cmd}")
        try:
            output = self.engine.execute(tcl_cmd)
        except Exception as exc:  # noqa: BLE001
            self.output(f"Error: {exc}")
            return 1
        if output:
            self.output(output)
        return 0

    def _handle_special(self, text: str) -> int:
        """Handle a ``/``-prefixed special command."""
        from edai.core.cmd_registry import CommandError
        from edai.core.special_cmds import registry as special_registry

        parts = text[1:].split()
        if not parts:
            return 0
        cmd_name = parts[0]
        cmd_args = parts[1:]
        try:
            output = special_registry.execute(cmd_name, self.engine, self, cmd_args)
        except SystemExit:
            raise
        except CommandError as exc:
            self.output(f"Error: {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001
            self.output(f"Error: {exc}")
            return 1
        if output:
            self.output(output)
        return 0

    def _context(self) -> dict[str, object]:
        """Build context dict for the LLM agent."""
        return {
            "placed": self.engine._placed,  # noqa: SLF001
            "routed": self.engine._routed,  # noqa: SLF001
            "cell_count": len(self.engine.db["cells"]),
            "net_count": len(self.engine.db["nets"]),
        }

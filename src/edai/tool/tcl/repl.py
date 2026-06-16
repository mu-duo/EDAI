"""Interactive EDA Tcl REPL backed by ``prompt_toolkit``.

Provides a full-featured command-line interface with:
- Real-time tab completion (EDA objects, commands, variables)
- Tcl-style ``[...]`` subcommand completion
- LLM agent integration for natural-language commands
- Input history and vi/emacs bindings
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

if TYPE_CHECKING:
    from edai.agent.agent import Agent
    from edai.tool.tcl.completer import EdaCompleter
    from edai.tool.tcl.engine import TclEngine

# ── styling (subtle, EDA-tool inspired) ──────────────────────────────

_STYLE = Style.from_dict(
    {
        "prompt": "ansicyan bold",
        "status": "ansigreen",
        "error": "ansired bold",
        "warning": "ansiyellow",
        "llm-suggestion": "ansimagenta italic",
    }
)

# ── key bindings ────────────────────────────────────────────────────

_bindings = KeyBindings()


@_bindings.add("c-c")
def _exit(event):  # type: ignore[no-untyped-def]  # noqa: ANN201
    """Ctrl+C to exit (or interrupt current command)."""
    event.app.exit()


# ── main REPL class ─────────────────────────────────────────────────


class EdaRepl:
    """Interactive EDA Tcl REPL.

    Usage::

        engine = TclEngine()
        agent = Agent(engine)
        repl = EdaRepl(engine, agent)
        asyncio.run(repl.run())
    """

    def __init__(
        self,
        engine: TclEngine,
        agent: Agent,
        completer: EdaCompleter | None = None,
        *,
        verbose: bool = False,
        history_file: str = ".eda_history",
    ) -> None:
        self.engine = engine
        self.agent = agent
        self.verbose = verbose
        self._history_file = history_file

        # Lazy import to avoid circular deps at class load time
        if completer is None:
            from edai.tool.tcl.completer import EdaCompleter

            completer = EdaCompleter(engine)
        self.completer = completer
        self._session: PromptSession | None = None

    @property
    def session(self) -> PromptSession:
        """Lazy-initialized PromptSession (avoids Win32 console errors in tests)."""
        if self._session is None:
            self._session = PromptSession(
                completer=self.completer,
                complete_while_typing=True,
                history=FileHistory(self._history_file),
                key_bindings=_bindings,
                style=_STYLE,
                vi_mode=False,
                enable_history_search=True,
                mouse_support=True,
            )
        return self._session

    # ── public API ─────────────────────────────────────────────────

    async def run(self) -> int:
        """Start the REPL event loop. Returns exit code."""
        self._banner()
        while True:
            try:
                text = await self.session.prompt_async(self._mk_prompt())
            except (EOFError, KeyboardInterrupt):
                print()  # clear line
                break

            text = text.strip()
            if not text:
                continue
            if text in ("exit", "quit", "q", "exit()", "quit()"):
                break

            exit_code = await self._handle_input(text)
            if exit_code != 0 and self.verbose:
                print(f"(exit code: {exit_code})")

        self._goodbye()
        return 0

    # ── internals ─────────────────────────────────────────────────

    def _banner(self) -> None:
        print(
            "╔══════════════════════════════════════╗\n"
            "║  EDAI — EDA Interactive Shell  v0.1  ║\n"
            "╠══════════════════════════════════════╣\n"
            "║  Tab = complete    Ctrl+C = exit     ║\n"
            "║  Type 'help' for commands            ║\n"
            "║  Natural language is auto-translated ║\n"
            "╚══════════════════════════════════════╝"
        )

    def _goodbye(self) -> None:
        print("Goodbye.")

    def _mk_prompt(self) -> str:
        """Return the current prompt string."""
        placed = " P" if self.engine._placed else ""  # noqa: SLF001
        routed = " R" if self.engine._routed else ""  # noqa: SLF001
        status = f"[{placed}{routed}]" if (placed or routed) else ""
        return f"eda{status}> "

    async def _handle_input(self, text: str) -> int:
        """Process one line of user input.

        The dispatch order is:

        1. ``/command`` → special command registry (REPL meta-commands)
        2. Valid Tcl command → engine execution
        3. Everything else → LLM natural-language agent
        """
        text = text.strip()
        if not text:
            return 0

        # 1. Special /-commands (handled by the REPL, not the Tcl engine)
        if text.startswith("/"):
            return self._handle_special(text)

        # 2. Direct Tcl execution
        if self.engine.is_valid_tcl(text):
            try:
                output = self.engine.execute(text)
            except Exception as exc:  # noqa: BLE001
                print(f"Error: {exc}")
                return 1
            if output:
                print(output)
            return 0

        # 3. Natural language → LLM translation
        if self.verbose:
            print("(translating via agent…)")

        try:
            tcl_cmd = await self.agent.translate(text, context=self._context())
        except Exception as exc:  # noqa: BLE001
            print(f"Agent error: {exc}")
            return 1

        if tcl_cmd.startswith("#"):
            # Agent didn't understand — just echo as comment
            print(tcl_cmd)
            return 1

        # Show the translation and execute
        print(f"→ {tcl_cmd}")
        try:
            output = self.engine.execute(tcl_cmd)
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
            return 1
        if output:
            print(output)
        return 0

    def _handle_special(self, text: str) -> int:
        """Handle a ``/``-prefixed special command.

        Dispatches to the ``SpecialCommandRegistry`` singleton.
        """
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
            print(f"Error: {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
            return 1
        if output:
            print(output)
        return 0

    def _context(self) -> dict[str, object]:
        """Build context dict for the LLM agent."""
        return {
            "placed": self.engine._placed,  # noqa: SLF001
            "routed": self.engine._routed,  # noqa: SLF001
            "cell_count": len(self.engine.db["cells"]),
            "net_count": len(self.engine.db["nets"]),
        }


def run_repl(
    engine: TclEngine | None = None,
    agent: Agent | None = None,
    *,
    verbose: bool = False,
    history_file: str = ".eda_history",
) -> int:
    """Start the EDA interactive REPL synchronously.

    Creates default engine/agent if not provided, then starts the
    event loop via ``asyncio.run()``.
    """
    from edai.agent.agent import Agent
    from edai.tool.tcl.engine import TclEngine

    if engine is None:
        engine = TclEngine()
    if agent is None:
        agent = Agent(engine)

    repl = EdaRepl(engine, agent, verbose=verbose, history_file=history_file)
    return asyncio.run(repl.run())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run_repl())

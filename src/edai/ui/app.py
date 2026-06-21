"""Simplified TUI — tclsh wrapper with NL/Tcl dispatch.

On Enter:
* If the input is a registered Tcl command → execute directly via ``EDAInteractive``.
* Otherwise → pass to the agent (typo correction / NL translation), then execute.
"""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, HorizontalGroup
from textual.widgets import Footer, Header, Input, RichLog, Static

from edai.agent.EdaAgent import EdaAgent
from edai.core.cmd_registry import registry
from edai.core.eda_interactive import EDAInteractive


class EdaiApp(App[None]):
    """Minimal Textual app wrapping tclsh with NL→Tcl agent dispatch."""

    TITLE = "EDAI"
    SUB_TITLE = "EDA Interactive Toolkit"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_log", "Clear"),
    ]

    DEFAULT_CSS = """
    RichLog {
        border: solid $primary;
        height: 1fr;
        margin: 0 1;
    }
    Input {
        dock: bottom;
        margin: 0 1 1 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._interactive = EDAInteractive(
            bin_path="/usr/bin/tclsh",
            timeout=300,
        )
        self._agent = EdaAgent()

    def compose(self) -> ComposeResult:
        """Build minimal widget tree."""
        self._output = RichLog(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        self._input_text = Input(placeholder="Type a Tcl command or natural language\u2026")
        self._input = HorizontalGroup()
        with self._input:
            yield Static(f"{self._interactive.prompt} ", markup=True, id="prompt")
            yield self._input_text
        with Vertical():
            yield Header(show_clock=True)
            yield self._output
            yield self._input
            yield Footer()

    def on_mount(self) -> None:
        """Show banner and focus input."""
        self._banner()
        self._input.focus()

    # ── message handlers ──────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter key → dispatch input."""
        self._output.write(f"[bold cyan]{self._interactive.prompt}[/] {event.value}")
        self._run_in_worker(event.value)
        self._input_text.clear()

    # ── action handlers ───────────────────────────────────────────

    def action_clear_log(self) -> None:
        """Ctrl+L → clear the output log."""
        self._output.clear()
        self._banner()

    # ── helpers ───────────────────────────────────────────────────

    def _run_in_worker(self, text: str) -> None:
        """Dispatch *text* in a background thread worker."""

        def _task() -> None:
            try:
                result = self._dispatch(text)
                self._output.write(result)
            except Exception as exc:  # noqa: BLE001
                self._output.write(f"[red]Error: {exc}[/red]")
            except SystemExit:
                self.app.call_from_thread(self.app.exit)

        self.app.run_worker(_task, thread=True)

    def _dispatch(self, text: str) -> str:
        """Route *text* to EDA tool or agent translator."""
        stripped = text.strip()
        if not stripped:
            return ""

        response = self._interactive.send_command(stripped)
        if response and not response.startswith("invalid command name"):
            return response

        # Unknown → LLM reasoning (typo correction / NL translation)
        try:
            tcl_code = self._sync_translate(stripped)
            self._output.write(f"[dim]⟹ {tcl_code}[/dim]")
            return self._interactive.send_command(tcl_code)
        except Exception:
            return self._interactive.send_command(stripped)

    @staticmethod
    def _sync_translate(text: str) -> str:
        """Translate NL to Tcl via the agent (synchronous wrapper)."""
        return asyncio.run(EdaAgent().translate(text))

    def _banner(self) -> None:
        """Write the welcome banner."""
        self._output.write(
            "\n"
            "[bold cyan]"
            f"{' ' * 10} ███████╗██████╗  █████╗ ████╗\n"
            f"{' ' * 10} ██╔════╝██╔══██╗██╔══██╗ ██╔╝\n"
            f"{' ' * 10} █████╗  ██║  ██║███████║ ██║\n"
            f"{' ' * 10} ██╔══╝  ██║  ██║██╔══██║ ██║\n"
            f"{' ' * 10} ███████╗██████╔╝██║  ██║████╗\n"
            f"{' ' * 10} ╚══════╝╚═════╝ ╚═╝  ╚═╝╚═══╝[/]\n"
            "[bold yellow]                    EDAI  v0.1.0[/]\n"
            "[white]             EDA Interactive Toolkit[/]\n"
            "\n"
            "[dim]  Tab ↹ focus     ⌃C quit    ⌃L clear[/]"
        )


def run_tui() -> int:
    """Launch the Textual TUI synchronously."""
    app = EdaiApp()
    result = app.run()
    return result if result is not None else 0

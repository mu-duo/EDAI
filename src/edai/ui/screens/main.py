"""Main screen — command log and input bar, backed by ``EdaRepl`` dispatch."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog

from edai.tool.tcl.repl import EdaRepl
from edai.ui.widgets import CompletionDropdown, EdaiSuggester, EdaiTextArea


class MainScreen(Screen[None]):
    """Primary screen with command output log and TextArea input.

    Input processing is delegated to :class:`EdaRepl`, ensuring the
    same dispatch chain is used everywhere.
    """

    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }

    RichLog {
        border: solid $primary;
        height: 1fr;
        margin: 0 1;
    }

    TextArea {
        dock: bottom;
        height: 3;
        margin: 0 1 1 1;
    }

    #completion-dropdown {
        dock: bottom;
        margin: 0 1 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_log", "Clear"),
    ]

    def __init__(self) -> None:
        super().__init__()
        from edai.agent.agent import Agent
        from edai.tool.tcl.engine import TclEngine

        self._engine = TclEngine()
        agent = Agent(self._engine)
        self.repl = EdaRepl(engine=self._engine, agent=agent, output=print)
        self.suggester = EdaiSuggester(self._engine)
        self._dropdown = CompletionDropdown()

    def compose(self) -> ComposeResult:
        """Create the screen's widget tree."""
        self._output = RichLog(
            id="output",
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        self._input = EdaiTextArea(
            id="input",
            suggester=self.suggester,
            dropdown=self._dropdown,
        )
        with Vertical():
            yield Header()
            yield self._output
            yield self._dropdown
            yield self._input
            yield Footer()

    def on_mount(self) -> None:
        """Post-mount setup: wire output, show banner, focus input."""
        self.repl.output = self._output.write  # type: ignore[assignment]
        self._banner()
        self._input.focus()

    # ── message handlers ──────────────────────────────────────────

    def on_edai_text_area_submitted(self, event: EdaiTextArea.Submitted) -> None:
        """Handle Enter in the TextArea."""
        self._output.write(f"[bold cyan]>[/] {event.text}")
        self._run_in_worker(event.text)

    # ── action handlers ───────────────────────────────────────────

    def action_clear_log(self) -> None:
        """Clear the output log."""
        self._output.clear()
        self._banner()

    # ── helpers ───────────────────────────────────────────────────

    def _run_in_worker(self, text: str) -> None:
        """Run ``EdaRepl._handle_input_sync`` in a background thread."""

        def _task() -> None:
            try:
                self.repl._handle_input_sync(text)  # noqa: SLF001
            except SystemExit:
                self.app.call_from_thread(self.app.exit)

        self.app.run_worker(_task, thread=True)

    def _banner(self) -> None:
        """Write the welcome banner with ASCII art and Rich markup."""
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
            "[dim]  Tab ↹ complete    ⌃C quit    ⌃L clear    NL auto-translate[/]"
        )

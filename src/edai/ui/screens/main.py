"""Main screen — command log and input bar, backed by EDAInteractive dispatch."""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, RichLog

from edai.agent.EdaAgent import EdaAgent
from edai.core.cmd_registry import registry
from edai.core.eda_interactive import EDAInteractive
from edai.tool.eda_interpreter import EDAInterpreter
from edai.ui.widgets import CompletionDropdown, EdaiSuggester, EdaiTextArea

# ── completion engine ───────────────────────────────────────────────


class StaticCompletionEngine:
    """Read-only completion queries backed by the command registry.

    Provides command-name completions from the static command registry.
    Dynamic object-name queries (cells, pins, nets, properties) currently
    return empty lists — these will be wired to a live EDA session later.
    """

    def get_command_names(self, prefix: str) -> list[str]:
        return [n for n in registry.all_commands() if n.startswith(prefix)]

    def get_variable_names(self, prefix: str) -> list[str]:  # noqa: ARG002
        return []

    def get_cell_names(self, prefix: str) -> list[str]:  # noqa: ARG002
        return []

    def get_pin_names(self, prefix: str) -> list[str]:  # noqa: ARG002
        return []

    def get_net_names(self, prefix: str) -> list[str]:  # noqa: ARG002
        return []

    def get_property_names(self, prefix: str) -> list[str]:  # noqa: ARG002
        return []


class MainScreen(Screen[None]):
    """Primary screen with command output log and TextArea input.

    Input is dispatched in a background thread:

    * If the text matches a registered Tcl command it is sent directly
      to the EDA tool via :class:`EDAInteractive`.
    * Otherwise the text is sent to the agent for NL→Tcl translation
      before execution.
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
        self._interactive = EDAInteractive(
            bin_path="/usr/bin/tclsh",
            timeout=300,
        )
        self._engine = EDAInterpreter(interactive=self._interactive)
        self._agent = EdaAgent()
        self.suggester = EdaiSuggester(StaticCompletionEngine())
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
        """Post-mount setup: show banner and focus input."""
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
        """Route *text* to the EDA tool or agent translator."""
        stripped = text.strip()
        if not stripped:
            return ""

        # Special /-commands
        if stripped.startswith("/"):
            return self._handle_special(stripped)

        first_word = stripped.split(maxsplit=1)[0] if stripped else ""

        # Known Tcl command → execute directly
        if first_word in registry:
            return self._interactive.send_command(stripped)

        # NL → Tcl translation
        try:
            tcl_code = self._sync_translate(stripped)
            self._output.write(f"[dim]⟹ {tcl_code}[/dim]")
            return self._interactive.send_command(tcl_code)
        except Exception:
            return self._interactive.send_command(stripped)

    def _handle_special(self, cmd: str) -> str:
        """Handle ``/``-prefixed special commands."""
        parts = cmd.split(maxsplit=1)
        name = parts[0].lower()
        if name in ("/help", "/h"):
            return self._help_text()
        if name in ("/clear", "/c"):
            self._output.clear()
            return ""
        return f"[red]Unknown special command: {name}[/red]"

    @staticmethod
    def _sync_translate(text: str) -> str:
        """Translate NL to Tcl via the agent (synchronous wrapper)."""
        return asyncio.run(EdaAgent().translate(text))

    @staticmethod
    def _help_text() -> str:
        """Built-in help: list all registered commands by category."""
        categories = registry.get_categories()
        lines = ["[bold underline]EDAI Commands[/]"]
        for cat, cmds in sorted(categories.items()):
            lines.append(f"\n[bold]{cat}[/]")
            for name in sorted(cmds):
                cmd = registry.get(name)
                if cmd and cmd.description:
                    lines.append(f"  {name:<20} {cmd.description.split(chr(10))[0]}")
                else:
                    lines.append(f"  {name}")
        return "\n".join(lines)

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

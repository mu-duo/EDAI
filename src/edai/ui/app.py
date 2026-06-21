"""Simplified TUI — tclsh wrapper with NL/Tcl dispatch.

On Enter:
* If the input is a registered Tcl command → execute directly via ``EDAInteractive``.
* Otherwise → pass to the agent (typo correction / NL translation), then execute.

Message handling
----------------
Every user input and agent response is tracked as a :class:`~edai.core.Message`
object, providing a single source of truth for the conversation history.
"""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from edai.agent.EdaiAgent import EdaiAgent
from edai.core.eda_interactive import EDAInteractive
from edai.core.Message import Message, MessageRole


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
        self._agent = EdaiAgent()

        # Canonical conversation history — list[Message]
        self._conversation: list[Message] = []

    def compose(self) -> ComposeResult:
        """Build minimal widget tree."""
        self._output = RichLog(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        self._input_text = Input(
            placeholder="Type a Tcl command or natural language\u2026"
        )
        with Vertical():
            yield Header(show_clock=True)
            yield self._output
            with HorizontalGroup():
                yield Static(f"{self._interactive.prompt} ", markup=True, id="prompt")
                yield self._input_text
            yield Footer()

    def on_mount(self) -> None:
        """Show banner and focus input."""
        self._banner()
        self._input_text.focus()

    # ── message handlers ──────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter key → dispatch input."""
        # Record the user input as a Message
        user_msg = Message.human(event.value)
        self._conversation.append(user_msg)

        # Display it
        self._output.write(f"[bold cyan]{self._interactive.prompt}[/] {event.value}")
        self._run_in_worker(event.value)
        self._input_text.clear()

    # ── action handlers ───────────────────────────────────────────

    def action_clear_log(self) -> None:
        """Ctrl+L → clear the output log and conversation history."""
        self._output.clear()
        self._conversation.clear()
        self._banner()

    # ── helpers ───────────────────────────────────────────────────

    def _run_in_worker(self, text: str) -> None:
        """Dispatch *text* in a background thread worker."""

        def _task() -> None:
            try:
                result = self._dispatch(text)
                # Record the result as a Message
                if result:
                    result_msg = Message.ai(result)
                    self._conversation.append(result_msg)
                    self._output.write(result)
            except Exception as exc:  # noqa: BLE001
                err_msg = Message.tool(f"Error: {exc}")
                self._conversation.append(err_msg)
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
        if self._check_tcl_response(response):
            return response

        # Unknown → LLM reasoning (typo correction / NL execution)
        try:
            tcl_code = self._sync_translate(stripped)
            self._output.write(f"[dim]⟹ {tcl_code}[/dim]")
            return self._interactive.send_command(tcl_code)
        except Exception:
            return self._interactive.send_command(stripped)
        
    def _check_tcl_response(self, response: str) -> bool:
        """Check if the response indicates a valid Tcl command execution."""
        if not response:
            return True  # Empty response can be valid (e.g., successful command with no output)
        if response.startswith("invalid command name"):
            return False
        if response.startswith("can't read"):
            return False
        return True

    def _sync_translate(self, text: str) -> str:
        """Translate NL to Tcl via the agent (synchronous wrapper).

        Returns the LLM response content as a string.
        """
        return asyncio.run(self._agent.invoke(text))

    # ── conversation accessors ────────────────────────────────────

    @property
    def conversation(self) -> list[Message]:
        """Read-only conversation history."""
        return list(self._conversation)

    def last_user_message(self) -> Message | None:
        """Return the most recent human message, if any."""
        for msg in reversed(self._conversation):
            if msg.role == MessageRole.HUMAN:
                return msg
        return None

    # ── banner ────────────────────────────────────────────────────

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
            "[bold yellow]                EDAI  version 0.1.0[/]\n"
            "[white]             EDA Interactive Toolkit[/]\n"
            "\n"
            "[dim]  Tab ↹ focus     ⌃C quit    ⌃L clear[/]"
        )


def run_tui() -> int:
    """Launch the Textual TUI synchronously."""
    app = EdaiApp()
    result = app.run()
    return result if result is not None else 0

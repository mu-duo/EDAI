"""Simplified TUI — Tcl wrapper with NL/Tcl dispatch and mock fallback.

On Enter:
* If the input is a registered Tcl command → execute directly via backend.
* Otherwise → pass to the agent (typo correction / NL translation), then execute.

Backend selection:
* ``--mock`` flag → in-memory ``MockTclRepl`` simulation.
* ``--path`` / ``-p`` → real ``EDAInteractive`` subprocess at the given binary.
* ``tclsh`` on ``PATH`` → real ``EDAInteractive`` subprocess.
* No backend found → in-memory ``MockTclRepl`` simulation (fallback).

Message handling
----------------
Every user input and agent response is tracked as a :class:`~edai.core.Message`
object, providing a single source of truth for the conversation history.
"""

from __future__ import annotations

from typing import Protocol

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from edai.agent.EdaiAgent import EdaiAgent
from edai.core.backend_config import BackendConfig, create_backend
from edai.core.Message import Message, MessageRole


class TclBackend(Protocol):
    """Duck-typed protocol for the Tcl execution backend.

    Both ``EDAInteractive`` and ``MockTclRepl`` satisfy this.
    """

    prompt: str

    def send_command(self, code: str) -> str: ...


class EdaiApp(App[None]):
    """Minimal Textual app wrapping a Tcl backend with NL→Tcl agent dispatch."""

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

    def __init__(self, config: BackendConfig | None = None) -> None:
        super().__init__()
        self._interactive = create_backend(config)
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
        self._input_text = Input(placeholder="Type a Tcl command or natural language\u2026")
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

    def _check_tcl_response(self, response: str) -> bool:
        """Check if the response indicates a valid Tcl command execution."""
        if not response:
            return True
        if response.startswith("invalid command name"):
            return False
        return not response.startswith("can't read")

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

        # 1. Try the raw input as a direct Tcl command.
        response = self._interactive.send_command(stripped)
        if self._check_tcl_response(response):
            return response

        # 2. Not valid Tcl — ask the agent for analysis.
        try:
            llm_response = self._agent.invoke(stripped)
        except Exception as e:
            return f"{response}\n[red]Agent error: {e}[/red]"

        # 3. Agent decides output format:
        #    "[tcl command] <cmd>" → execute on _interactive
        #    otherwise             → regular LLM reply, display as-is
        tcl_cmd = _extract_tcl_command(llm_response)
        if tcl_cmd:
            tcl_result = self._interactive.send_command(tcl_cmd)
            if self._check_tcl_response(tcl_result):
                return f"[bold green]→ {tcl_cmd}[/]\n{tcl_result}"
            return f"[bold green]→ {tcl_cmd}[/]\n[red]{tcl_result}[/red]"

        # 4. Regular LLM reply — display as-is.
        return f"[bold green]Agent:[/] {llm_response}"

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


# ── module-level helpers ─────────────────────────────────────────────


_TCL_CMD_PREFIX = "[tcl command]"


def _extract_tcl_command(text: str) -> str:
    """If *text* starts with ``[tcl command]``, return the command part.

    The agent protocol is::

        [tcl command] <command>

    When there is no prefix, *text* is a regular LLM reply and the
    function returns an empty string (meaning "do not execute").
    """
    text = text.strip()
    if text.lower().startswith(_TCL_CMD_PREFIX):
        return text[len(_TCL_CMD_PREFIX) :].strip()
    return ""


def run_tui(config: BackendConfig | None = None) -> int:
    """Launch the Textual TUI synchronously.

    Parameters
    ----------
    config:
        Back-end configuration.  When *None* the default auto-detect
        behaviour is used (see :func:`~edai.core.backend_config.create_backend`).
    """
    app = EdaiApp(config)
    result = app.run()
    return result if result is not None else 0

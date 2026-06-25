"""Agent Info Modal Screen for EDAI TUI."""

from __future__ import annotations

from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from textual.containers import ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import RichLog, Static


class AgentInfoScreen(ModalScreen[None]):
    """Modal screen showing agent system prompt and metadata."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    AgentInfoScreen {
        align: center middle;
    }
    #agent-info-container {
        width: 90%;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    #agent-info-meta {
        height: auto;
        margin-bottom: 1;
    }
    #agent-info-prompt {
        height: 1fr;
        border: solid $primary;
    }
    """

    def __init__(
        self,
        system_prompt: str,
        metadata: dict[str, str],
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._system_prompt = system_prompt
        self._metadata = metadata

    def compose(self):
        with ScrollableContainer(id="agent-info-container"):
            yield Static(self._build_meta_panel(), id="agent-info-meta")
            yield Static(Rule(style="dim"))
            yield RichLog(
                id="agent-info-prompt",
                highlight=True,
                markup=True,
                wrap=True,
                auto_scroll=False,
            )

    def _build_meta_panel(self) -> Panel:
        """Build a Rich Panel showing agent metadata."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column(style="white")
        meta = self._metadata
        table.add_row("Role:", meta.get("role", "?"))
        table.add_row("Model:", meta.get("model", "?"))
        table.add_row("Max Iterations:", meta.get("max_iterations", "?"))
        table.add_row("Backend:", meta.get("backend_type", "?"))
        return Panel(table, title="Agent Info", border_style="cyan")

    def on_mount(self) -> None:
        """Render the system prompt once the widget is mounted."""
        log = self.query_one("#agent-info-prompt", RichLog)
        log.can_focus = False
        md = Markdown(self._system_prompt)
        log.write(md)
"""EDAI Textual application — main entry point."""

from __future__ import annotations

from textual.app import App

from edai.ui.screens.main import MainScreen


class EdaiApp(App[None]):
    """EDAI Textual TUI application.

    Provides an interactive Tcl-command environment with:
    - Rich output log for command history and results
    - Input bar with tab completion for EDA objects
    - Natural-language → Tcl translation via the agent
    - Status bar showing current design state
    """

    TITLE = "EDAI"
    SUB_TITLE = "EDA Interactive Toolkit"
    CSS_PATH = None  # Uses inline CSS via DEFAULT_CSS on screens/widgets

    SCREENS = {"main": MainScreen}

    def on_mount(self) -> None:
        """Push the main screen on startup."""
        self.push_screen("main")


def run_tui() -> int:
    """Launch the Textual TUI synchronously.

    Returns exit code 0 on clean exit.
    """
    app = EdaiApp()
    result = app.run()
    return result if result is not None else 0

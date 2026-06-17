"""``TextArea`` subclass tuned for EDAI command-line input."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.binding import Binding
from textual.events import Key
from textual.message import Message
from textual.widgets._text_area import TextArea

if TYPE_CHECKING:
    from edai.ui.widgets.completion_dropdown import CompletionDropdown
    from edai.ui.widgets.suggester import EdaiSuggester


class EdaiTextArea(TextArea):
    """Single-line command input with EDA-aware Tab completion.

    - **Tab** selects the highlighted completion from the dropdown (or
      accepts the inline ghost text if the dropdown is not shown).
    - **Up / Down** navigate the completion dropdown when visible.
    - **Enter** submits the command (no newline).
    """

    BINDINGS = [
        Binding("tab", "accept_suggestion", "Complete", show=False, priority=True),
    ]

    class Submitted(Message):
        """Posted when the user presses Enter with non-empty text."""

        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    def __init__(
        self,
        *,
        suggester: EdaiSuggester | None = None,
        dropdown: CompletionDropdown | None = None,
        placeholder: str = "Type a Tcl command or natural language\u2026",
        id: str | None = None,  # noqa: A002
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            id=id,
            classes=classes,
            disabled=disabled,
            show_line_numbers=False,
            tab_behavior="focus",
            placeholder=placeholder,
        )
        self._suggester = suggester
        self._dropdown = dropdown
        self._completions: list[str] = []

    # ── suggestion hook ─────────────────────────────────────────────

    def update_suggestion(self) -> None:
        """Compute inline ghost text and refresh the completion dropdown."""
        if self._suggester is None:
            self.suggestion = ""
            self._hide_dropdown()
            return

        value = self.text
        if not value:
            self.suggestion = ""
            self._completions = []
            self._hide_dropdown()
            return

        result = self._suggester.completions(value)
        self._completions = result.all if result else []
        prefix = result.prefix

        if self._completions:
            # Pick the first candidate that extends the prefix as ghost.
            self.suggestion = ""
            for candidate in self._completions:
                if candidate == value:
                    continue
                if prefix and candidate.lower().startswith(prefix.lower()):
                    self.suggestion = candidate[len(prefix):]
                else:
                    self.suggestion = candidate
                break

            # Show dropdown when there are multiple candidates.
            if len(self._completions) > 1:
                self._show_dropdown(self._completions)
            else:
                self._hide_dropdown()
        else:
            self.suggestion = ""
            self._hide_dropdown()

    # ── Tab action ──────────────────────────────────────────────────

    def action_accept_suggestion(self) -> None:
        """Tab: select from dropdown, accept ghost, or advance focus."""
        if not self._is_at_end():
            self.app.action_focus_next()
            return

        # Dropdown visible → select highlighted item.
        if self._dropdown_visible:
            selected = self._dropdown.highlighted  # type: ignore[union-attr]
            if selected is not None:
                self._replace_text(selected)
            self._hide_dropdown()
            return

        # No dropdown, but ghost text shown → accept suffix.
        if self.suggestion:
            self.text = self.text + self.suggestion
            self.suggestion = ""
            self._cursor_to_end()
            self._hide_dropdown()
            return

        self.app.action_focus_next()

    # ── key interception ────────────────────────────────────────────

    async def _on_key(self, event: Key) -> None:
        """Intercept Enter and dropdown navigation keys."""
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            text = self.text.strip()
            if text:
                self.post_message(self.Submitted(text))
                self.clear()
                self._hide_dropdown()
            return

        # Up / Down → navigate dropdown when visible.
        if self._dropdown_visible:
            if event.key == "down":
                event.prevent_default()
                event.stop()
                self._dropdown.action_cursor_down()  # type: ignore[union-attr]
                return
            if event.key == "up":
                event.prevent_default()
                event.stop()
                self._dropdown.action_cursor_up()  # type: ignore[union-attr]
                return

        await super()._on_key(event)

    # ── internal helpers ────────────────────────────────────────────

    @property
    def _dropdown_visible(self) -> bool:
        """Whether the completion dropdown is currently shown."""
        return self._dropdown is not None and self._dropdown.display

    def _show_dropdown(self, items: list[str]) -> None:
        if self._dropdown is not None:
            self._dropdown.show(items)

    def _hide_dropdown(self) -> None:
        if self._dropdown is not None and self._dropdown.display:
            self._dropdown.hide()

    def _replace_text(self, new_text: str) -> None:
        """Replace the entire text with *new_text* and move cursor to end."""
        self.text = new_text
        self.suggestion = ""
        self._cursor_to_end()

    def _cursor_to_end(self) -> None:
        """Move cursor to the end of the current text."""
        end = len(self.text)
        self.move_cursor((0, end))

    def _is_at_end(self) -> bool:
        """Check whether cursor is at the very end of the text."""
        return self.cursor_location[1] >= len(self.text)

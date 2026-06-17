"""Dropdown list for completion candidates, positioned near the input."""

from __future__ import annotations

from textual.widgets import Label, ListItem, ListView


class CompletionDropdown(ListView):
    """A non-focusable dropdown list showing completion candidates.

    Managed programmatically by :class:`EdaiTextArea`:
    - ``show(items)`` populates and reveals the list.
    - ``hide()`` clears and conceals it.
    - Highlight navigation via ``action_cursor_up/down`` (called from parent).
    - ``highlighted`` property returns the currently selected candidate text.
    """

    DEFAULT_CSS = """
    CompletionDropdown {
        display: none;
        height: auto;
        max-height: 12;
        border: solid $primary;
        background: $surface;
        margin: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__(id="completion-dropdown")
        self.can_focus = False
        self._items: list[str] = []

    # ── public API ──────────────────────────────────────────────────

    def show(self, items: list[str]) -> None:
        """Populate with *items* and make visible."""
        self.clear()
        self._items = list(items)
        for item in items:
            self.append(ListItem(Label(item)))
        self.index = 0
        self.display = True

    def hide(self) -> None:
        """Clear items and conceal."""
        self.display = False
        self.clear()
        self._items.clear()

    @property
    def highlighted(self) -> str | None:
        """The text of the currently highlighted item, or ``None``."""
        if self.index is not None and 0 <= self.index < len(self._items):
            return self._items[self.index]
        return None

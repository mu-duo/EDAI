"""Global debug/verbose infrastructure for EDAI.

Provides a module-level ``debug_print`` function that only emits output
when debug mode is globally enabled.  Use ``set_debug()`` to control the
flag at startup (typically from ``BackendConfig.verbose``).

Usage::

    from edai.core.debug import debug_print, set_debug

    set_debug(True)
    debug_print("cmd=get_cells args=[]")   # → "[DEBUG] cmd=get_cells args=[]"
"""

from __future__ import annotations

import sys

_enabled: bool = False


def set_debug(enabled: bool) -> None:
    """Enable or disable global debug output."""
    global _enabled  # noqa: PLW0603
    _enabled = bool(enabled)


def is_debug() -> bool:
    """Return the current global debug flag."""
    return _enabled


def debug_print(*args: object) -> None:
    """Print *args* to stderr when global debug mode is enabled.

    Each line is prefixed with ``[DEBUG] ``.
    """
    if not _enabled:
        return
    print("[DEBUG]", *args, file=sys.stderr)

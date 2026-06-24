"""Global debug/verbose infrastructure for EDAI.

Provides a module-level :func:`debug_print` that only emits output
when the global debug flag is on.  Use :func:`set_debug` to control
the flag, and :func:`set_debug_output` to redirect output (e.g. to a
TUI widget).  Default output goes to stdout.
"""

from __future__ import annotations

import sys

_enabled: bool = False
_output = lambda *a: print("[DEBUG]", *a, file=sys.stderr)  # noqa: E731


def set_debug(enabled: bool) -> None:
    """Enable or disable global debug output."""
    global _enabled  # noqa: PLW0603
    _enabled = bool(enabled)


def set_debug_output(func) -> None:
    """Redirect debug output to *func* instead of the default (stderr).

    *func* receives ``(*args)`` — the same arguments passed to
    :func:`debug_print` (without the ``[DEBUG]`` prefix).
    """
    global _output  # noqa: PLW0603
    _output = func


def debug_print(*args: object) -> None:
    """Emit debug output when the global debug flag is enabled.

    Output is sent to the function installed via :func:`set_debug_output`
    (default: ``print`` to stderr).  Does nothing when debug is off.
    """
    if not _enabled:
        return
    _output(*args)

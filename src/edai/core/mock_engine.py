"""Mock Tcl engine — in-memory EDA tool simulation.

Provides :class:`MockTclEngine`, a pure-Python replacement for a real EDA tool
backend.  Useful for:
    * Debugging the REPL, agent, or TUI without a licensed EDA tool.
    * Running tests that need an EDA session but don't need real execution.
    * Development / demo environments where the backend is unavailable.

The engine owns a static in-memory design database (6 cells, 5 nets, 5 ports,
1 library, 1 clock by default), tracks mutable state (placed / routed flags,
user variables), and provides query helpers for commands and the completer.
"""

from __future__ import annotations

import re
from typing import Any


class MockTclEngine:
    """In-memory mock of an EDA Tcl engine.

    Attributes:
        db: The in-memory design database (see :meth:`_build_mock_db`).
        variables: ``dict`` of user-defined Tcl variables (``name → value``).
        _placed: Whether ``place_design`` has been run.
        _routed: Whether ``route_design`` has been run.

    """

    def __init__(self) -> None:
        self.db: dict[str, Any] = self._build_mock_db()
        self.variables: dict[str, str] = {}
        self._placed = False
        self._routed = False

    # ── static mock database ────────────────────────────────────────

    @staticmethod
    def _build_mock_db() -> dict[str, Any]:
        """Return the static in-memory design database."""
        return {
            "library": "work",
            "cells": {
                "u1": {
                    "ref": "AND2",
                    "pins": ["u1/A", "u1/B", "u1/Z"],
                    "type": "combinational",
                },
                "u2": {
                    "ref": "OR2",
                    "pins": ["u2/A", "u2/B", "u2/Z"],
                    "type": "combinational",
                },
                "u3": {
                    "ref": "DFF",
                    "pins": ["u3/D", "u3/CK", "u3/Q", "u3/QN"],
                    "type": "sequential",
                },
                "u4": {
                    "ref": "DFF",
                    "pins": ["u4/D", "u4/CK", "u4/Q", "u4/QN"],
                    "type": "sequential",
                },
                "u5": {
                    "ref": "INV",
                    "pins": ["u5/A", "u5/Z"],
                    "type": "combinational",
                },
                "u6": {
                    "ref": "NAND2",
                    "pins": ["u6/A", "u6/B", "u6/Z"],
                    "type": "combinational",
                },
            },
            "nets": {
                "n1": {"source": "u1/Z", "sinks": ["u3/D", "u5/A"]},
                "n2": {"source": "u3/Q", "sinks": ["u2/A"]},
                "n3": {"source": "u2/Z", "sinks": ["u4/D", "u6/A"]},
                "n4": {"source": "u5/Z", "sinks": ["u1/A"]},
                "n5": {"source": "u4/Q", "sinks": ["u6/B"]},
            },
            "ports": {
                "clk": {"direction": "input"},
                "rst_n": {"direction": "input"},
                "data_in": {"direction": "input", "width": 8},
                "data_out": {"direction": "output", "width": 8},
                "ready": {"direction": "output"},
            },
            "clocks": {
                "clk": {"period_ns": 10.0, "waveform": [0.0, 5.0]},
            },
        }

    # ── query helpers ───────────────────────────────────────────────

    def get_cell_names(self) -> list[str]:
        """Return sorted cell instance names."""
        return sorted(self.db["cells"])

    def get_pin_names(self, cell_name: str | None = None) -> list[str]:
        """Return pin names, optionally filtered to one cell."""
        if cell_name:
            cell = self.db["cells"].get(cell_name)
            if cell is None:
                return []
            return list(cell["pins"])
        pins: list[str] = []
        for cell in self.db["cells"].values():
            pins.extend(cell["pins"])
        return pins

    def get_net_names(self) -> list[str]:
        """Return sorted net names."""
        return sorted(self.db["nets"])

    def get_port_names(self) -> list[str]:
        """Return sorted port names."""
        return sorted(self.db["ports"])

    def get_clock_names(self) -> list[str]:
        """Return sorted clock names."""
        return sorted(self.db["clocks"])

    # ── variable substitution ──────────────────────────────────────

    def substitute_vars(self, args: list[str]) -> list[str]:
        """Replace ``$var`` / ``${var}`` tokens with variable values.

        Unresolved variable references are left as-is so the caller can
        report a meaningful error.
        """
        result: list[str] = []
        for arg in args:
            result.append(self._substitute_var(arg))
        return result

    def _substitute_var(self, token: str) -> str:
        """Substitute ``$var`` and ``${var}`` in a single token."""

        def _replace(m: re.Match[str]) -> str:
            name = m.group(1) or m.group(2)
            return self.variables.get(name, m.group(0))

        return re.sub(r"\$(\w+)|(?:\$\{(\w+)\})", _replace, token)

    # ── variable helpers (used by ``set`` command) ──────────────────

    def set_var(self, name: str, value: str) -> str:
        """Set a Tcl variable and return its value."""
        self.variables[name] = value
        return value

    def get_var(self, name: str) -> str | None:
        """Return a variable value, or ``None`` if unset."""
        return self.variables.get(name)

    # ── state helpers ───────────────────────────────────────────────

    def place_design(self) -> None:
        """Mark the design as placed."""
        self._placed = True

    def route_design(self) -> None:
        """Mark the design as routed (also places if not yet placed)."""
        self._placed = True
        self._routed = True

"""Mock EDA Tcl execution engine.

Provides an in-memory design database and command-execution
environment driven by the ``cmd_registry``.
"""

from __future__ import annotations

import re
import shlex
from typing import Any

# Force command modules to register their handlers on import.
import edai.tool.tcl.cmd_defs  # noqa: F401
from edai.core.cmd_registry import CommandError, registry


class TclError(CommandError):
    """Raised on invalid Tcl command syntax or execution."""


def _build_mock_db() -> dict[str, Any]:
    """Construct a realistic but tiny mock EDA design database."""
    cells = {
        "u_clk_gen": {
            "type": "MMCM",
            "pins": ["clk_in", "clk_out", "locked", "rst"],
            "site": "MMCME2_X0Y0",
            "properties": {"FREQUENCY": "100MHz", "PHASE": "0"},
        },
        "u_cpu_core": {
            "type": "B1100",
            "pins": ["clk", "rst", "irq", "data_bus[31:0]", "addr_bus[31:0]"],
            "site": "SLICE_X0Y0",
            "properties": {"ARCH": "rv32i", "FREQ": "200MHz"},
        },
        "u_ram_0": {
            "type": "BRAM",
            "pins": ["clk", "addr[15:0]", "data[31:0]", "we", "en"],
            "site": "BRAM_X0Y0",
            "properties": {"DEPTH": "65536", "WIDTH": "32"},
        },
        "u_ram_1": {
            "type": "BRAM",
            "pins": ["clk", "addr[15:0]", "data[31:0]", "we", "en"],
            "site": "BRAM_X0Y1",
            "properties": {"DEPTH": "65536", "WIDTH": "32"},
        },
        "u_dsp_0": {
            "type": "DSP48E2",
            "pins": ["a[29:0]", "b[17:0]", "c[47:0]", "p[47:0]", "clk"],
            "site": "DSP_X0Y0",
            "properties": {"MODE": "MULTIPLY"},
        },
        "u_uart": {
            "type": "UART16550",
            "pins": ["clk", "rxd", "txd", "cts", "rts"],
            "site": "SLICE_X1Y0",
            "properties": {"BAUD": "115200", "DATA_BITS": "8"},
        },
    }

    nets = {
        "clk_100m": {
            "type": "CLOCK",
            "source": "u_clk_gen.clk_out",
            "sinks": [
                "u_cpu_core.clk",
                "u_ram_0.clk",
                "u_ram_1.clk",
                "u_dsp_0.clk",
            ],
        },
        "rst_n": {
            "type": "RESET",
            "source": "u_clk_gen.locked",
            "sinks": ["u_cpu_core.rst"],
        },
        "data_bus": {
            "type": "DATA",
            "source": "u_cpu_core.data_bus[31:0]",
            "sinks": ["u_ram_0.data[31:0]", "u_ram_1.data[31:0]"],
        },
        "uart_tx": {
            "type": "IO",
            "source": "u_uart.txd",
            "sinks": ["(top_level_pad)"],
        },
        "uart_rx": {
            "type": "IO",
            "source": "(top_level_pad)",
            "sinks": ["u_uart.rxd"],
        },
    }

    libs = {
        "typical.lib": {
            "cells": {
                "BUF": {"pins": ["A", "Z"], "area": 1.0},
                "INV": {"pins": ["A", "ZN"], "area": 1.0},
                "NAND2": {"pins": ["A", "B", "ZN"], "area": 2.0},
                "NOR2": {"pins": ["A", "B", "ZN"], "area": 2.0},
                "DFF": {"pins": ["D", "CK", "Q", "QN"], "area": 8.0},
                "B1100": {"pins": ["clk", "rst", "irq"], "area": 500.0},
                "MMCM": {"pins": ["clk_in", "clk_out", "locked"], "area": 200.0},
                "BRAM": {"pins": ["clk", "addr", "data", "we"], "area": 400.0},
                "DSP48E2": {"pins": ["A", "B", "C", "P", "clk"], "area": 300.0},
                "UART16550": {"pins": ["clk", "rxd", "txd"], "area": 150.0},
            }
        }
    }

    clocks = {
        "clk_100m": {"period": "10.0", "waveform": [0.0, 5.0]},
    }

    ports = {
        "clk": {"direction": "input"},
        "rst_n": {"direction": "input"},
        "txd": {"direction": "output"},
        "rxd": {"direction": "input"},
        "data_in": {"direction": "input", "bus_width": 32},
        "data_out": {"direction": "output", "bus_width": 32},
    }

    return {
        "cells": cells,
        "nets": nets,
        "libs": libs,
        "clocks": clocks,
        "ports": ports,
        "collections": {},
        "app_vars": {
            "search_path": ".",
            "target_library": "typical.lib",
            "synthetic_library": "",
            "link_library": "* typical.lib",
        },
        "attributes": {},
        "sta_config": {
            "timing_analysis_mode": "bc_wc",
            "operating_condition": "typical",
        },
    }


class TclEngine:
    """Mock Tcl execution engine for EDA flows.

    Maintains an in-memory design database and variable namespace.
    Command dispatch is handled by the global ``CommandRegistry``.
    """

    def __init__(self) -> None:
        self.db = _build_mock_db()
        self.variables: dict[str, str] = {}
        self._placed = False
        self._routed = False

    # ── query helpers (used by command handlers & completers) ───

    def get_cell_names(self, prefix: str = "") -> list[str]:
        """Return cell names matching *prefix*."""
        return [n for n in self.db["cells"] if n.startswith(prefix)]

    def get_pin_names(self, prefix: str = "", cell: str | None = None) -> list[str]:
        """Return pin names matching *prefix*, optionally filtered by *cell*."""
        if cell:
            if cell not in self.db["cells"]:
                return []
            return [p for p in self.db["cells"][cell]["pins"] if p.startswith(prefix)]
        pins: list[str] = []
        for c in self.db["cells"].values():
            pins.extend(p for p in c["pins"] if p.startswith(prefix))
        return sorted(pins)

    def get_net_names(self, prefix: str = "") -> list[str]:
        """Return net names matching *prefix*."""
        return [n for n in self.db["nets"] if n.startswith(prefix)]

    def get_property_names(self, prefix: str = "") -> list[str]:
        """Return common EDA property names matching *prefix*."""
        props = [
            "FREQUENCY",
            "PHASE",
            "BAUD",
            "DATA_BITS",
            "DEPTH",
            "WIDTH",
            "MODE",
            "ARCH",
            "FREQ",
            "CLOCK_DEDICATED_ROUTE",
            "IOSTANDARD",
            "LOC",
            "SLEW",
        ]
        return [p for p in props if p.startswith(prefix.upper())]

    def get_variable_names(self, prefix: str = "") -> list[str]:
        """Return variable names matching *prefix*."""
        return [v for v in self.variables if v.startswith(prefix)]

    def get_command_names(self, prefix: str = "") -> list[str]:
        """Return registered Tcl command names matching *prefix*."""
        return [n for n in registry.all_commands() if n.startswith(prefix)]

    def get_clock_names(self, prefix: str = "") -> list[str]:
        """Return clock names matching *prefix*."""
        return [n for n in self.db["clocks"] if n.startswith(prefix)]

    def get_port_names(self, prefix: str = "") -> list[str]:
        """Return port names matching *prefix*."""
        return [n for n in self.db["ports"] if n.startswith(prefix)]

    def is_valid_tcl(self, text: str) -> bool:
        """Return True if *text* looks like a valid registered command."""
        text = text.strip()
        if not text:
            return False
        first_word = text.split()[0] if " " in text else text
        return first_word in registry

    # ── variable management ──────────────────────────────────

    def set_variable(self, name: str, value: str) -> None:
        """Set a Tcl variable."""
        self.variables[name] = value

    def get_variable(self, name: str) -> str:
        """Get a Tcl variable, raising ``TclError`` if undefined."""
        if name not in self.variables:
            raise TclError(f'can\'t read "{name}": no such variable')
        return self.variables[name]

    # ── execution ────────────────────────────────────────────

    def _subst_vars(self, text: str) -> str:
        """Replace ``$var`` / ``${var}`` with variable values."""

        def replacer(m: re.Match) -> str:
            name = m.group(1) or m.group(2)
            if not name:
                name = m.group(0)
            try:
                return self.get_variable(name or "")
            except TclError:
                return m.group(0)  # type: ignore[no-any-return]

        pattern = r"\$(\w+)|(?:\$\{(\w+)\})"
        return re.sub(pattern, replacer, text)

    def execute(self, command: str) -> str:
        """Parse and execute a Tcl command string.

        Returns the command output (stdout-equivalent).
        """
        text = command.strip()
        if not text:
            return ""

        # Variable substitution ($var → value)
        text = self._subst_vars(text)

        try:
            tokens = shlex.split(text)
        except ValueError as exc:
            raise TclError(f"Syntax error: {exc}") from exc

        if not tokens:
            return ""

        cmd_name = tokens[0]
        cmd_args = tokens[1:]

        try:
            return registry.execute(cmd_name, self, cmd_args)
        except CommandError as exc:
            raise TclError(str(exc)) from exc
        except Exception as exc:
            raise TclError(str(exc)) from exc

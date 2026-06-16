"""Mock EDA Tcl execution engine.

Provides a lightweight, in-memory Tcl-like command environment
for EDA (Electronic Design Automation) tool interactions.
"""

from __future__ import annotations

import shlex
from typing import Any


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
            "sinks": ["u_cpu_core.clk", "u_ram_0.clk", "u_ram_1.clk", "u_dsp_0.clk"],
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

    return {"cells": cells, "nets": nets}


# Map of Tcl command → (usage, description, handler)
_COMMANDS: dict[str, tuple[str, str]] = {
    "get_cells": (
        "get_cells [-hier] [-filter <expr>] [pattern]",
        "Return cell names matching pattern",
    ),
    "get_pins": (
        "get_pins [-of_objects <cells>] [pattern]",
        "Return pin names matching pattern",
    ),
    "get_nets": (
        "get_nets [-of_objects <cells>] [pattern]",
        "Return net names matching pattern",
    ),
    "set_property": (
        "set_property <name> <value> <objects>",
        "Set property on design objects",
    ),
    "report_timing": (
        "report_timing [-from <pins>] [-to <pins>] [-nworst <N>]",
        "Report timing paths",
    ),
    "place_design": (
        "place_design",
        "Run placement for the current design",
    ),
    "route_design": (
        "route_design",
        "Run routing for the current design",
    ),
    "help": (
        "help [command]",
        "Show help for commands",
    ),
}


class TclError(Exception):
    """Raised on invalid Tcl command syntax or execution."""


class TclEngine:
    """Mock Tcl execution engine for EDA flows.

    Maintains an in-memory design database and variable namespace.
    """

    def __init__(self) -> None:
        self.db = _build_mock_db()
        self.variables: dict[str, str] = {}
        self._placed = False
        self._routed = False

    # ── query helpers (used by prompt_toolkit completers) ──────────────

    def get_command_names(self, prefix: str = "") -> list[str]:
        """Return known Tcl command names matching *prefix*."""
        return [c for c in _COMMANDS if c.startswith(prefix)]

    def get_cell_names(self, prefix: str = "") -> list[str]:
        """Return cell names matching *prefix*."""
        return [n for n in self.db["cells"] if n.startswith(prefix)]

    def get_pin_names(self, prefix: str = "", cell: str | None = None) -> list[str]:
        """Return pin names matching *prefix*, optionally filtered by *cell*."""
        if cell:
            if cell not in self.db["cells"]:
                return []
            return [p for p in self.db["cells"][cell]["pins"] if p.startswith(prefix)]
        # all pins across all cells
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

    def is_valid_tcl(self, text: str) -> bool:
        """Return True if *text* looks like a valid Tcl command."""
        text = text.strip()
        if not text:
            return False
        first_word = text.split()[0] if " " in text else text
        return first_word in _COMMANDS

    # ── execution ───────────────────────────────────────────────────

    def set_variable(self, name: str, value: str) -> None:
        """Set a Tcl variable."""
        self.variables[name] = value

    def get_variable(self, name: str) -> str:
        """Get a Tcl variable, raising ``TclError`` if undefined."""
        if name not in self.variables:
            raise TclError(f'can\'t read "{name}": no such variable')
        return self.variables[name]

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
            tokens = shlex.split(text)  # handle quoted strings
        except ValueError as exc:
            raise TclError(f"Syntax error: {exc}") from exc

        if not tokens:
            return ""

        cmd = tokens[0]
        args = tokens[1:]

        handler = getattr(self, f"_cmd_{cmd.replace('-', '_')}", None)
        if handler is None:
            raise TclError(f"unknown command: {cmd}")

        result: str = handler(args)
        return result

    def _subst_vars(self, text: str) -> str:
        """Replace ``$var`` / ``${var}`` with variable values."""
        import re

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

    # ── subcommand handlers ─────────────────────────────────────────

    def _cmd_help(self, args: list[str]) -> str:
        if not args:
            lines = ["Available commands:"]
            for name, (_usage, desc) in sorted(_COMMANDS.items()):
                lines.append(f"  {name:<20s} {desc}")
            return "\n".join(lines)
        topic = args[0]
        info = _COMMANDS.get(topic)
        if info is None:
            return f"No help for unknown command '{topic}'"
        return f"Usage: {info[0]}\n  {info[1]}"

    def _cmd_get_cells(self, args: list[str]) -> str:
        pattern = args[-1] if args and not args[-1].startswith("-") else ""
        names = self.get_cell_names(pattern)
        return "\n".join(names) if names else ""

    def _cmd_get_pins(self, args: list[str]) -> str:
        pattern = ""
        cell: str | None = None
        i = 0
        while i < len(args):
            if args[i] == "-of_objects" and i + 1 < len(args):
                cell = args[i + 1]
                i += 2
            else:
                pattern = args[i]
                i += 1
        names = self.get_pin_names(pattern, cell)
        return "\n".join(names) if names else ""

    def _cmd_get_nets(self, args: list[str]) -> str:
        pattern = args[-1] if args and not args[-1].startswith("-") else ""
        names = self.get_net_names(pattern)
        return "\n".join(names) if names else ""

    def _cmd_set_property(self, args: list[str]) -> str:
        if len(args) < 3:
            raise TclError("wrong # args: set_property <name> <value> <objects>")
        name, value = args[0], args[1]
        objects = args[2:]
        results: list[str] = []
        for obj in objects:
            if obj in self.db["cells"]:
                self.db["cells"][obj]["properties"][name] = value
                results.append(f"set {obj}.{name} = {value}")
            else:
                results.append(f"warning: object '{obj}' not found")
        return "\n".join(results)

    def _cmd_report_timing(self, args: list[str]) -> str:  # noqa: ARG002
        if not self._placed:
            return "Timing report: (design not yet placed)"
        return (
            "====================================================\n"
            "  Timing Report\n"
            "====================================================\n"
            "  Data Path Delay:    2.345 ns\n"
            "  Clock Path Skew:    0.012 ns\n"
            "  Slack:              0.543 ns\n"
            "  Worst Negative Slack (WNS): 0.432 ns\n"
            "  Total Negative Slack (TNS): 1.234 ns\n"
            "  Failing Endpoints:  0\n"
            "===================================================="
        )

    def _cmd_place_design(self, args: list[str]) -> str:  # noqa: ARG002
        self._placed = True
        return "Placement completed successfully."

    def _cmd_route_design(self, args: list[str]) -> str:  # noqa: ARG002
        if not self._placed:
            return "Error: design must be placed before routing."
        self._routed = True
        return "Routing completed successfully."

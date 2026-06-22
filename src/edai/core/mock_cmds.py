"""Mock Tcl commands for the EDA tool simulation.

Each command is registered via the ``@command`` decorator from
:mod:`edai.core.cmd_registry`, so they automatically participate in
the REPL's command dispatch and (future) tab completion.

This module is force-imported by :mod:`edai.core.mock_repl` so that
all commands are registered at REPL startup.
"""

from __future__ import annotations

from typing import Any

from edai.core.cmd_registry import CommandError, command

# ── helpers ────────────────────────────────────────────────────────────


def _require_placed(engine: Any) -> None:
    """Raise ``CommandError`` if the design has not been placed."""
    if not getattr(engine, "_placed", False):
        msg = "Design has not been placed. Run 'place_design' first."
        raise CommandError(msg)


# ── COMMON commands ────────────────────────────────────────────────────


@command(
    category="COMMON",
    usage="get_cells [-hier]",
    description="Return all cell instance names in the design.",
    flags=("-hier",),
    positional_categories={0: ("cells",)},
)
def get_cells(engine: Any, args: list[str]) -> str:
    """Return all cell instance names in the design."""
    # Parse flags (just -hier for demo — same output for now)
    if "-hier" in args:
        args = [a for a in args if a != "-hier"]

    cells = engine.get_cell_names()
    if not cells:
        return "No cells found."
    return "\n".join(cells)


@command(
    category="COMMON",
    usage="get_nets",
    description="Return all net names in the design.",
)
def get_nets(engine: Any, args: list[str]) -> str:  # noqa: ARG001
    """Return all net names in the design."""
    nets = engine.get_net_names()
    if not nets:
        return "No nets found."
    return "\n".join(nets)


@command(
    category="COMMON",
    usage="get_ports",
    description="Return all port names in the design.",
)
def get_ports(engine: Any, args: list[str]) -> str:  # noqa: ARG001
    """Return all port names in the design."""
    ports = engine.get_port_names()
    if not ports:
        return "No ports found."
    return "\n".join(ports)


# ── STA / SDC commands ────────────────────────────────────────────────


@command(
    category="STA/SDC",
    usage="create_clock -name <name> -period <period_ns> [ -waveform <rise> <fall> ]",
    description="Create a clock definition.",
    flags=("-name", "-period", "-waveform"),
    flag_value_categories={"-name": ("clocks",)},
)
def create_clock(engine: Any, args: list[str]) -> str:
    """Create a clock definition."""
    # Minimal flag parser
    name: str | None = None
    period: float | None = None
    waveform: list[float] | None = None

    i = 0
    while i < len(args):
        if args[i] == "-name" and i + 1 < len(args):
            name = args[i + 1]
            i += 2
        elif args[i] == "-period" and i + 1 < len(args):
            try:
                period = float(args[i + 1])
            except ValueError:
                msg = f"Invalid period value: {args[i + 1]}"
                raise CommandError(msg) from None
            i += 2
        elif args[i] == "-waveform" and i + 2 < len(args):
            try:
                waveform = [float(args[i + 1]), float(args[i + 2])]
            except ValueError:
                msg = "Invalid waveform values (expected two floats)"
                raise CommandError(msg) from None
            i += 3
        else:
            i += 1

    if name is None or period is None:
        msg = (
            "Usage: create_clock -name <name> -period <period_ns>"
            " [-waveform <rise> <fall>]"
        )
        raise CommandError(msg)

    engine.db["clocks"][name] = {
        "period_ns": period,
        "waveform": waveform or [0.0, period / 2.0],
    }
    return f"Created clock '{name}' with period {period} ns."


@command(
    category="STA/SDC",
    usage="report_timing",
    description="Report timing summary for the design.",
)
def report_timing(engine: Any, args: list[str]) -> str:  # noqa: ARG001
    """Report timing summary for the design. Requires placement."""
    _require_placed(engine)

    lines = [
        "  Timing Report",
        "  =============",
        f"  Design    : {engine.db['library']}",
        f"  Placed    : {engine._placed}",
        f"  Routed    : {engine._routed}",
        "",
    ]

    if engine.db["clocks"]:
        lines.append("  Clocks:")
        for clk_name, clk_data in engine.db["clocks"].items():
            lines.append(f"    {clk_name}  period={clk_data['period_ns']} ns")
        lines.append("")

    # Mock timing numbers
    if engine._routed:
        slack = 0.12
        lines.append(f"  Slack (setup)  : {slack:.3f} ns")
        lines.append(f"  Slack (hold)   : {slack + 0.05:.3f} ns")
    else:
        lines.append("  (post-placement estimate — route for accurate timing)")
        slack = -0.45
        lines.append(f"  Slack (setup)  : {slack:.3f} ns (estimated)")

    lines.append("")
    lines.append("  Path type: max (setup)")
    return "\n".join(lines)


# ── PLACE / ROUTE commands ────────────────────────────────────────────


@command(
    category="PLACE",
    usage="place_design",
    description="Place the design (mock).  Required before report_timing.",
)
def place_design(engine: Any, args: list[str]) -> str:  # noqa: ARG001
    """Place the design (mock)."""
    engine.place_design()
    cells = engine.get_cell_names()
    return f"Design placed successfully ({len(cells)} cells placed)."


@command(
    category="ROUTE",
    usage="route_design",
    description="Route the design (mock).  Requires place_design first.",
)
def route_design(engine: Any, args: list[str]) -> str:  # noqa: ARG001
    """Route the design (mock)."""
    _require_placed(engine)
    engine.route_design()
    nets = engine.get_net_names()
    return f"Design routed successfully ({len(nets)} nets routed)."

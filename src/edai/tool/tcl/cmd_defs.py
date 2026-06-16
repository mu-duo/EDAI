"""All EDA Tcl command definitions, organised by category.

Each command is registered via the ``@command()`` decorator which
picks up the function name (transforming ``_`` → ``-``) and docstring.
"""

from __future__ import annotations

from edai.core.cmd_registry import command

# ═══════════════════════════════════════════════════════════════
# Helper patterns
# ═══════════════════════════════════════════════════════════════


def _ok(engine, args):  # noqa: ARG001
    """Return generic success code."""
    return "1"


def _empty(engine, args):  # noqa: ARG001
    """Return empty output."""
    return ""


def _list_objects(db_key: str):
    """Factory: return a handler that lists object names from ``engine.db[key]``."""

    def handler(engine, args):
        pattern = args[-1] if args and not args[-1].startswith("-") else ""
        objects = engine.db.get(db_key, {})
        names = [n for n in objects if n.startswith(pattern)]
        return "\n".join(sorted(names)) if names else ""

    return handler


def _set_property(engine, args):
    """Generic setter: set property on a design object."""
    if len(args) < 3:
        name = args[0] if args else ""
        return f"1  # {name} set"
    prop, value, *objects = args
    results = []
    for obj in objects:
        if obj in engine.db.get("cells", {}):
            engine.db["cells"][obj].setdefault("properties", {})[prop] = value
            results.append(f"{obj}.{prop} = {value}")
        else:
            results.append(f"warning: object '{obj}' not found")
    return "\n".join(results)


def _report_template(title: str, fields: list[tuple[str, str]]):
    """Factory: return a handler that prints a styled report."""

    def handler(engine, args):  # noqa: ARG001
        lines = [
            "=" * 52,
            f"  {title}",
            "=" * 52,
        ]
        for key, val in fields:
            lines.append(f"  {key:<30s} {val}")
        lines.append("=" * 52)
        return "\n".join(lines)

    return handler


# ═══════════════════════════════════════════════════════════════
# COMMON
# ═══════════════════════════════════════════════════════════════


@command(category="COMMON")
def add_to_collection(engine, args):
    """Add object(s) to a collection. Result is new collection."""
    objects = [a for a in args if not a.startswith("-")]
    return f"collection:{' '.join(objects) if objects else ''}"


@command(category="COMMON")
def exit(engine, args):  # noqa: A001  # shadow builtin intentionally
    """Exit the program."""
    raise SystemExit(0)


@command(category="COMMON")
def get_app_var(engine, args):
    """Get an app_var; use __all__ to view all configuration items."""
    if not args or args[0] == "__all__":
        items = engine.db.get("app_vars", {})
        return "\n".join(f"{k} = {v}" for k, v in sorted(items.items()))
    name = args[0]
    return engine.db.get("app_vars", {}).get(name, f"warning: app_var '{name}' not set")


@command(category="COMMON")
def get_attribute(engine, args):
    """Get attribute values from design objects."""
    if not args:
        return ""
    obj_pattern = args[-1]
    attr_name = args[0] if len(args) >= 2 and not args[0].startswith("-") else "all"
    attrs = engine.db.get("attributes", {})
    results = []
    for obj_name, obj_attrs in attrs.items():
        if obj_pattern in obj_name:
            if attr_name == "all":
                for k, v in obj_attrs.items():
                    results.append(f"{obj_name} [{k}] = {v}")
            else:
                val = obj_attrs.get(attr_name, "?")
                results.append(f"{obj_name} [{attr_name}] = {val}")
    return "\n".join(results) if results else ""


@command(category="COMMON")
def get_object_name(engine, args):
    """Get full_name of an object."""
    if not args:
        return ""
    obj = args[-1]
    return obj


@command(category="COMMON")
def getenv(engine, args):
    """Get the value of a system environment variable."""
    import os

    name = args[0] if args else ""
    return os.environ.get(name, f"warning: env '{name}' not set")


@command(
    category="COMMON",
    positional_categories={0: ("commands",)},
)
def help(engine, args):  # noqa: A001  # shadow builtin
    """List the help information."""
    from edai.core.cmd_registry import registry

    if args:
        topic = args[0]
        cmd = registry.get(topic)
        if cmd is None:
            return f"No help for unknown command '{topic}'"
        return f"Usage: {cmd.usage}\n  {cmd.description}"

    lines = ["Available commands (by category):", ""]
    for cat, names in sorted(registry.get_categories().items()):
        lines.append(f"  [{cat}]")
        for n in sorted(names):
            cmd = registry.get(n)
            if cmd is not None:
                lines.append(f"    {n:<30s} {cmd.description}")
        lines.append("")
    return "\n".join(lines)


@command(category="COMMON")
def list_libs(engine, args):  # noqa: ARG001
    """List libraries currently available in memory."""
    libs = engine.db.get("libs", {})
    return "\n".join(sorted(libs.keys())) if libs else "(no libraries loaded)"


@command(category="COMMON")
def log_begin(engine, args):
    """Specify the file to save output log."""
    filename = args[0] if args else "edai.log"
    engine.variables["_log_file"] = filename
    return f"1  # logging to {filename}"


@command(category="COMMON")
def log_end(engine, args):  # noqa: ARG001
    """Close the log file and restore stdout."""
    engine.variables.pop("_log_file", None)
    return "1"


@command(category="COMMON")
def log_output(engine, args):
    """Redirect log output to a file."""
    filename = args[0] if args else "edai.log"
    engine.variables["_log_file"] = filename
    return f"1  # output redirected to {filename}"


@command(category="COMMON")
def output_libs_info(engine, args):  # noqa: ARG001
    """Output all libs info for internal checking."""
    import json

    return json.dumps(engine.db.get("libs", {}), indent=2, default=str)


@command(category="COMMON")
def query_objects(engine, args):
    """Display objects in collections in order."""
    if not args:
        return ""
    col = args[-1]
    # Check if it's a collection reference
    collection = engine.db.get("collections", {}).get(col)
    if collection is not None:
        return "\n".join(str(o) for o in collection)
    return col


@command(category="COMMON")
def quit(engine, args):  # noqa: A001
    """Exit the program."""
    raise SystemExit(0)


@command(category="COMMON")
def read_db(engine, args):
    """Read the design database from file."""
    filename = args[0] if args else "design.db"
    return f"1  # read {filename}"


@command(category="COMMON")
def read_liberty(engine, args):
    """Read the liberty file."""
    filename = args[0] if args else "lib.lib"
    return f"1  # read liberty {filename}"


@command(category="COMMON")
def read_verilog(engine, args):
    """Read the verilog file into the design."""
    filename = args[0] if args else "design.v"
    return f"1  # read verilog {filename}"


@command(category="COMMON")
def redirect(engine, args):
    """Redirect output of a command to a file / var / tcl channel."""
    if not args:
        return "0"
    if args[0] == "-tee":
        target = args[1] if len(args) > 1 else ""
    else:
        target = args[0]
    return f"1  # output redirected to {target}"


@command(category="COMMON")
def remove_attribute(engine, args):
    """Remove attribute values from objects."""
    return _ok(engine, args)


@command(category="COMMON")
def remove_from_collection(engine, args):
    """Iteratively remove objects from a collection."""
    return _ok(engine, args)


@command(category="COMMON")
def remove_lib(engine, args):
    """Remove a library from memory."""
    names = [a for a in args if not a.startswith("-")]
    removed = []
    for n in names:
        if n in engine.db.get("libs", {}):
            del engine.db["libs"][n]
            removed.append(n)
    return "\n".join(f"removed lib '{n}'" for n in removed) if removed else "0"


@command(category="COMMON")
def set_app_var(engine, args):
    """Configure an app_var to change configuration."""
    if len(args) >= 2:
        engine.db.setdefault("app_vars", {})[args[0]] = " ".join(args[1:])
    return "1"


@command(category="COMMON", usage="set_attribute <name> <value> <objects>")
def set_attribute(engine, args):
    """Set attribute values."""
    if len(args) < 3:
        return "0"
    name, value = args[0], args[1]
    objects = args[2:]
    results = []
    for obj in objects:
        engine.db.setdefault("attributes", {}).setdefault(obj, {})[name] = value
        results.append(f"set {obj}[{name}] = {value}")
    return "\n".join(results) if results else "1"


@command(category="COMMON")
def set_black_box(engine, args):
    """Set a module/entity/netlist to be a black box."""
    return _ok(engine, args)


@command(category="COMMON")
def set_disable_path_max_fanout(engine, args):
    """Set disable_path_max_fanout (default 10000)."""
    return _ok(engine, args)


@command(category="COMMON")
def set_dont_touch(engine, args):
    """Set nets/modules/instances as not allowed to optimize."""
    return _ok(engine, args)


@command(category="COMMON")
def set_dont_use(engine, args):
    """Set library cells as not allowed to use."""
    return _ok(engine, args)


@command(category="COMMON")
def set_message_level(engine, args):
    """Set the severity level of messages with specific tag."""
    return _ok(engine, args)


@command(category="COMMON")
def set_parallel_options(engine, args):
    """Enable parallel computing."""
    return _ok(engine, args)


@command(category="COMMON")
def set_print_config(engine, args):
    """Control information output."""
    return _ok(engine, args)


@command(category="COMMON")
def setenv(engine, args):
    """Set the value of a system environment variable."""
    import os

    if len(args) >= 2:
        os.environ[args[0]] = " ".join(args[1:])
    return "1"


@command(category="COMMON")
def sizeof_collection(engine, args):
    """Return size of a collection."""
    if not args:
        return "0"
    col = engine.db.get("collections", {}).get(args[-1])
    return str(len(col)) if col is not None else "0"


@command(category="COMMON")
def unsetenv(engine, args):
    """Unset the value of a system environment variable."""
    import os

    name = args[0] if args else ""
    os.environ.pop(name, None)
    return "1"


@command(category="COMMON")
def write_file(engine, args):
    """Write design to file."""
    filename = args[-1] if args else "design_out"
    return f"1  # wrote {filename}"


# ── backward-compat mock commands ────────────────────────────


@command(
    category="COMMON",
    flags=("-hier", "-filter"),
    positional_categories={0: ("cells",)},
)
def get_cells(engine, args):
    """Collect cell instances from the mock database."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    names = engine.get_cell_names(pattern)
    return "\n".join(names) if names else ""


@command(
    category="COMMON",
    flags=("-of_objects",),
    positional_categories={0: ("nets",)},
    flag_value_categories={"-of_objects": ("cells",)},
)
def get_nets(engine, args):
    """Collect net instances from the mock database."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    names = engine.get_net_names(pattern)
    return "\n".join(names) if names else ""


@command(
    category="COMMON",
    flags=("-of_objects",),
    positional_categories={0: ("pins",)},
    flag_value_categories={"-of_objects": ("cells",)},
)
def get_pins(engine, args):
    """Collect pin names from the mock database."""
    pattern = ""
    cell = None
    i = 0
    while i < len(args):
        if args[i] == "-of_objects" and i + 1 < len(args):
            cell = args[i + 1]
            i += 2
        elif not args[i].startswith("-"):
            pattern = args[i]
            i += 1
        else:
            i += 1
    names = engine.get_pin_names(pattern, cell)
    return "\n".join(names) if names else ""


@command(
    category="COMMON",
    positional_categories={0: ("properties",), 2: ("cells", "pins")},
)
def set_property(engine, args):
    """Set property values on design objects."""
    if len(args) < 3:
        from edai.core.cmd_registry import CommandError

        raise CommandError("wrong # args: set_property <name> <value> <objects>")
    name, value = args[0], args[1]
    objects = args[2:]
    results = []
    for obj in objects:
        if obj in engine.db.get("cells", {}):
            engine.db["cells"][obj].setdefault("properties", {})[name] = value
            results.append(f"set {obj}.{name} = {value}")
        else:
            results.append(f"warning: object '{obj}' not found")
    return "\n".join(results)


@command(category="SYNTHESIS")
def place_design(engine, args):  # noqa: ARG001
    """Run placement for the current design."""
    engine._placed = True  # noqa: SLF001
    return "Placement completed successfully."


@command(category="SYNTHESIS")
def route_design(engine, args):  # noqa: ARG001
    """Run routing for the current design."""
    if not engine._placed:  # noqa: SLF001
        return "Error: design must be placed before routing."
    engine._routed = True  # noqa: SLF001
    return "Routing completed successfully."


# ═══════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════


@command(category="REPORT")
def check_design(engine, args):  # noqa: ARG001
    """Check the current design for consistency."""
    return (
        "====================================================\n"
        "  Design Consistency Check\n"
        "====================================================\n"
        "  Status:                      PASSED\n"
        "  Errors:                      0\n"
        "  Warnings:                    2\n"
        "  Unconnected pins:            3\n"
        "  Single-fanout nets:          1\n"
        "===================================================="
    )


@command(category="REPORT")
def get_fanin_pins(engine, args):
    """Show the fan-in logic cone of a net or pin."""
    target = args[-1] if args else "(current)"
    return f"(fanin pins of {target})"


@command(category="REPORT")
def get_fanout_pins(engine, args):
    """Show the fan-out logic cone of a net or pin."""
    target = args[-1] if args else "(current)"
    return f"(fanout pins of {target})"


@command(category="REPORT")
def report_area(engine, args):  # noqa: ARG001
    """Report area information."""
    return _report_template(
        "Area Report",
        [
            ("Combinational Area:", "12345.67"),
            ("Sequential Area:", "87654.32"),
            ("Physical Cell Area:", "0.00"),
            ("Total Cell Area:", "100000.00"),
        ],
    )(engine, args)


@command(category="REPORT")
def report_attribute(engine, args):
    """Report attribute values."""
    return get_attribute(engine, args)


@command(category="REPORT")
def report_buffer_tree(engine, args):  # noqa: ARG001
    """Report buffer tree and its level information at the given driver pin."""
    return "  Buffer Tree Report\n" "  Driver: u_clk_gen/clk_out\n" "  Levels: 3\n" "  Buffers inserted: 2\n"


@command(category="REPORT")
def report_bus(engine, args):  # noqa: ARG001
    """List the bused ports and nets in the current design."""
    return "  Buses:\n    data_bus[31:0]\n    addr_bus[31:0]\n    data[31:0]\n"


@command(category="REPORT")
def report_cell(engine, args):
    """Display information about cells in the current design."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    cells = engine.db.get("cells", {})
    lines = ["  Cell Report", "-" * 40]
    for name, info in sorted(cells.items()):
        if name.startswith(pattern):
            lines.append(f"  {name:<20s} type={info.get('type', '?')}")
    return "\n".join(lines)


@command(category="REPORT")
def report_constraint(engine, args):  # noqa: ARG001
    """Report design constraints."""
    return _report_template(
        "Constraint Report",
        [
            ("False paths:", "0"),
            ("Multicycle paths:", "2"),
            ("Max delay:", "10.0 ns"),
            ("Min delay:", "2.0 ns"),
        ],
    )(engine, args)


@command(category="REPORT")
def report_design(engine, args):  # noqa: ARG001
    """Display attributes of the current design."""
    return _report_template(
        "Design Summary",
        [
            ("Design name:", engine.variables.get("current_design", "top")),
            ("Number of cells:", str(len(engine.db.get("cells", {})))),
            ("Number of nets:", str(len(engine.db.get("nets", {})))),
            ("Number of ports:", str(len(engine.db.get("ports", {})))),
            ("Number of clocks:", str(len(engine.db.get("clocks", {})))),
        ],
    )(engine, args)


@command(category="REPORT")
def report_hierarchy(engine, args):  # noqa: ARG001
    """Display the reference hierarchy of the current design."""
    return (
        "  Hierarchy:\n"
        "    top (B1100)\n"
        "      u_cpu_core (B1100)\n"
        "      u_ram_0 (BRAM)\n"
        "      u_ram_1 (BRAM)\n"
        "      u_dsp_0 (DSP48E2)\n"
        "      u_uart (UART16550)\n"
        "      u_clk_gen (MMCM)\n"
    )


@command(category="REPORT")
def report_lib(engine, args):
    """Display information about a logic/physical/symbol library."""
    lib_name = args[-1] if args else "default"
    libs = engine.db.get("libs", {})
    lib = libs.get(lib_name)
    if lib is None:
        return f"warning: library '{lib_name}' not found"
    return f"  Library: {lib_name}\n  Cells: {len(lib.get('cells', {}))}\n"


@command(category="REPORT")
def report_net(engine, args):
    """Display information about nets in the current design."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    nets = engine.db.get("nets", {})
    lines = ["  Net Report", "-" * 40]
    for name, info in sorted(nets.items()):
        if name.startswith(pattern):
            lines.append(f"  {name:<20s} type={info.get('type', '?')}")
    return "\n".join(lines)


@command(category="REPORT")
def report_net_fanout(engine, args):  # noqa: ARG001
    """Display net fanout information."""
    return _report_template(
        "Net Fanout",
        [
            ("Max fanout:", "8"),
            ("Min fanout:", "1"),
            ("Avg fanout:", "3.2"),
        ],
    )(engine, args)


@command(category="REPORT")
def report_port(engine, args):
    """Display information about ports."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    ports = engine.db.get("ports", {})
    lines = ["  Port Report", "-" * 40]
    for name, info in sorted(ports.items()):
        if name.startswith(pattern):
            lines.append(f"  {name:<20s} dir={info.get('direction', '?')}")
    return "\n".join(lines)


@command(category="REPORT")
def report_reference(engine, args):  # noqa: ARG001
    """Display information about all references."""
    return "  References:\n    B1100 (1)\n    BRAM (2)\n    DSP48E2 (1)\n    UART16550 (1)\n    MMCM (1)"


@command(category="REPORT")
def report_units(engine, args):  # noqa: ARG001
    """Display the units used by the current design."""
    return _report_template(
        "Units",
        [
            ("Time:", "1ns"),
            ("Capacitance:", "1pF"),
            ("Resistance:", "1kOhm"),
            ("Voltage:", "1V"),
            ("Current:", "1mA"),
            ("Area:", "1um2"),
        ],
    )(engine, args)


# ═══════════════════════════════════════════════════════════════
# ECO
# ═══════════════════════════════════════════════════════════════


@command(category="ECO")
def all_connected(engine, args):
    """Return the objects connected to a net, port, or pin."""
    target = args[-1] if args else ""
    if not target:
        return ""
    nets = engine.db.get("nets", {})
    for net_name, net_info in nets.items():
        if net_name == target or target in net_info.get("sinks", []):
            parts = [net_info.get("source", "")]
            parts.extend(net_info.get("sinks", []))
            return "\n".join(parts)
    return target


@command(category="ECO")
def connect_net(engine, args):
    """Connect a net to specified pins or ports."""
    return _ok(engine, args)


@command(category="ECO")
def connect_pin(engine, args):
    """Connect pins or ports at any hierarchical level."""
    return _ok(engine, args)


@command(category="ECO")
def create_bus(engine, args):
    """Create a bus in the current design."""
    return _ok(engine, args)


@command(category="ECO")
def create_cell(engine, args):
    """Create new leaf or hierarchical cells."""
    if not args:
        return "0"
    cell_name = args[-1]
    cell_type = args[-2] if len(args) >= 2 else "BUF"
    engine.db.setdefault("cells", {})[cell_name] = {
        "type": cell_type,
        "pins": [],
        "site": "",
        "properties": {},
    }
    return cell_name


@command(category="ECO")
def create_design(engine, args):
    """Create a design in memory."""
    name = args[-1] if args else "unnamed"
    engine.variables["current_design"] = name
    return name


@command(category="ECO")
def create_net(engine, args):
    """Create nets in the current design."""
    if not args:
        return "0"
    net_name = args[-1]
    engine.db.setdefault("nets", {})[net_name] = {
        "type": "SIGNAL",
        "source": "",
        "sinks": [],
    }
    return net_name


@command(category="ECO")
def create_port(engine, args):
    """Create ports in the current design."""
    if not args:
        return "0"
    port_name = args[-1]
    direction = "input"
    if "-direction" in args:
        idx = args.index("-direction")
        if idx + 1 < len(args):
            direction = args[idx + 1]
    engine.db.setdefault("ports", {})[port_name] = {
        "direction": direction,
        "properties": {},
    }
    return port_name


@command(category="ECO")
def current_design_name(engine, args):  # noqa: ARG001
    """Return the current design name."""
    return engine.variables.get("current_design", "top")


@command(category="ECO")
def current_instance(engine, args):
    """Set the working instance object."""
    if args:
        engine.variables["current_instance"] = args[0]
    return engine.variables.get("current_instance", "top")


@command(category="ECO")
def disconnect_net(engine, args):
    """Break connections between a net and its pins/ports."""
    return _ok(engine, args)


@command(category="ECO")
def insert_buffer(engine, args):
    """Insert buffer cells on specified nets or ports/pins."""
    return _ok(engine, args)


@command(category="ECO")
def redo(engine, args):  # noqa: ARG001
    """Reverse the effects of a previous undo."""
    return "1  # redo complete"


@command(category="ECO")
def remove_buffer(engine, args):
    """Remove buffer cells at a specified driver pin or net."""
    return _ok(engine, args)


@command(category="ECO")
def remove_bus(engine, args):
    """Remove ports from the current design or subdesign."""
    return _ok(engine, args)


@command(category="ECO")
def remove_cell(engine, args):
    """Remove cells from the current design."""
    names = [a for a in args if not a.startswith("-")]
    for n in names:
        engine.db.get("cells", {}).pop(n, None)
    return _ok(engine, args)


@command(category="ECO")
def remove_design(engine, args):
    """Remove a design from memory."""
    return _ok(engine, args)


@command(category="ECO")
def remove_net(engine, args):
    """Remove nets from the current design."""
    names = [a for a in args if not a.startswith("-")]
    for n in names:
        engine.db.get("nets", {}).pop(n, None)
    return _ok(engine, args)


@command(category="ECO")
def remove_port(engine, args):
    """Remove ports from the current design."""
    names = [a for a in args if not a.startswith("-")]
    for n in names:
        engine.db.get("ports", {}).pop(n, None)
    return _ok(engine, args)


@command(category="ECO")
def size_cell(engine, args):
    """Relink leaf cells to a new library cell."""
    return _ok(engine, args)


@command(category="ECO")
def undo(engine, args):  # noqa: ARG001
    """Reverse effects of ECO editing commands."""
    return "1  # undo complete"


@command(category="ECO")
def undo_config(engine, args):
    """Configure the undo stack."""
    return _ok(engine, args)


# ═══════════════════════════════════════════════════════════════
# POWER/UPF
# ═══════════════════════════════════════════════════════════════


for _name in [
    "add_port_state",
    "add_power_state",
    "add_pst_state",
    "associate_supply_set",
    "connect_supply_net",
    "create_power_domain",
    "create_power_switch",
    "create_pst",
    "create_supply_net",
    "create_supply_port",
    "create_supply_set",
    "map_isolation_cell",
    "map_level_shifter_cell",
    "map_retention_cell",
    "set_domain_supply_net",
    "set_isolation",
    "set_level_shifter",
    "set_port_attributes",
    "set_retention",
    "use_interface_cell",
]:
    _fn = eval(
        f"lambda engine, args, *, _n='{_name}': _ok(engine, args)",
        {"_ok": _ok},
    )
    _fn.__name__ = _name
    _fn.__qualname__ = _name
    _fn.__doc__ = f"{_name.replace('_', ' ').title()} — UPF power intent command."
    command(name=_name, category="POWER/UPF")(_fn)

# Explicit entries for UPF commands needing custom descriptions
for _name, _usage, _desc in [
    ("read_upf", None, "Read a UPF file."),
    ("report_isolation", None, "Report isolation strategy information."),
    ("report_level_shifter", None, "Report level shifter strategy information."),
    ("report_power_domain", None, "Report power domain information."),
    ("report_power_state", None, "Report power state information."),
    ("report_power_switch", None, "Report power switch information."),
    ("report_pst", None, "Report power state table information."),
    ("report_retention", None, "Report retention strategy information."),
    ("report_supply_net", None, "Report supply net information."),
    ("report_supply_set", None, "Report supply set information."),
    ("save_upf", None, "Save the current UPF information to a file."),
]:
    _fn = lambda engine, args, *, _n=_name: _report_template(_n.replace("_", " ").title(), [])(engine, args)  # noqa: E731
    _fn.__name__ = _name
    _fn.__qualname__ = _name
    _fn.__doc__ = _desc
    if _usage:
        command(name=_name, category="POWER/UPF", usage=_usage)(_fn)
    else:
        command(name=_name, category="POWER/UPF")(_fn)


# ═══════════════════════════════════════════════════════════════
# POWER/COMMAND
# ═══════════════════════════════════════════════════════════════


@command(category="POWER/COMMAND")
def read_saif(engine, args):
    """Read a SAIF file and annotate switching activity."""
    filename = args[-1] if args else "activity.saif"
    return f"1  # read {filename}"


@command(category="POWER/COMMAND")
def read_vcd(engine, args):
    """Read a VCD file for power calculation."""
    filename = args[-1] if args else "sim.vcd"
    return f"1  # read {filename}"


@command(category="POWER/COMMAND")
def report_power(engine, args):  # noqa: ARG001
    """Generate a power report."""
    return _report_template(
        "Power Report",
        [
            ("Total Power:", "125.3 mW"),
            ("Dynamic Power:", "98.2 mW"),
            ("Leakage Power:", "27.1 mW"),
            ("Switching Power:", "65.4 mW"),
            ("Internal Power:", "32.8 mW"),
        ],
    )(engine, args)


@command(category="POWER/COMMAND")
def report_power_calculation(engine, args):  # noqa: ARG001
    """Display power calculation details for a pin/cell/net."""
    return _report_template(
        "Power Calculation",
        [
            ("  Pin / Cell / Net", "..."),
            ("  Internal Power:", "12.3 uW"),
            ("  Leakage Power:", "5.6 uW"),
            ("  Switching Power:", "7.8 uW"),
        ],
    )(engine, args)


@command(category="POWER/COMMAND")
def set_net_activity(engine, args):
    """Set net activity for power analysis."""
    return _ok(engine, args)


@command(category="POWER/COMMAND")
def set_sim_clk(engine, args):
    """Set simulation clock."""
    return _ok(engine, args)


@command(category="POWER/COMMAND")
def set_sim_input(engine, args):
    """Set simulation input stimulus."""
    return _ok(engine, args)


@command(category="POWER/COMMAND")
def set_sim_reset(engine, args):
    """Set simulation reset."""
    return _ok(engine, args)


@command(category="POWER/COMMAND")
def sim(engine, args):
    """Run simulation and dump VCD."""
    cycles = args[-1] if args else "100"
    return f"1  # simulated {cycles} cycles, dumped sim.vcd"


# ═══════════════════════════════════════════════════════════════
# STA/COMMON
# ═══════════════════════════════════════════════════════════════


@command(category="STA/COMMON")
def get_sta_config(engine, args):
    """Get the value of a STA configuration."""
    if not args:
        items = engine.db.get("sta_config", {})
        return "\n".join(f"{k} = {v}" for k, v in sorted(items.items()))
    return engine.db.get("sta_config", {}).get(args[0], "")


@command(category="STA/COMMON")
def read_sdc(engine, args):
    """Read the SDC constraint file."""
    filename = args[-1] if args else "design.sdc"
    return f"1  # read {filename}"


@command(category="STA/COMMON")
def read_sdf(engine, args):
    """Read the SDF delay file."""
    filename = args[-1] if args else "design.sdf"
    return f"1  # read {filename}"


@command(category="STA/COMMON")
def read_spef(engine, args):
    """Read the SPEF parasitic file."""
    filename = args[-1] if args else "design.spef"
    return f"1  # read {filename}"


@command(category="STA/COMMON")
def set_sta_config(engine, args):
    """Configure a STA configuration value."""
    if len(args) >= 2:
        engine.db.setdefault("sta_config", {})[args[0]] = " ".join(args[1:])
    return "1"


@command(category="STA/COMMON")
def test_sta_units(engine, args):  # noqa: ARG001
    """Test the scale of STA units."""
    return "Units: time=1ns, cap=1pF, res=1kOhm, volt=1V"


@command(category="STA/COMMON")
def update_timing(engine, args):  # noqa: ARG001
    """Update timing for the design."""
    engine.variables["timing_updated"] = "1"
    return "1  # timing updated"


@command(category="STA/COMMON")
def write_graph(engine, args):
    """Write timing graph for the design."""
    filename = args[-1] if args else "timing.graph"
    return f"1  # wrote {filename}"


@command(category="STA/COMMON")
def write_sdf(engine, args):
    """Write SDF delay file."""
    filename = args[-1] if args else "design.sdf"
    return f"1  # wrote {filename}"


# ═══════════════════════════════════════════════════════════════
# STA/SDC
# ═══════════════════════════════════════════════════════════════


@command(category="STA/SDC")
def all_clocks(engine, args):  # noqa: ARG001
    """Collect clocks from the current design."""
    clocks = engine.db.get("clocks", {})
    return "\n".join(sorted(clocks.keys())) if clocks else ""


@command(category="STA/SDC")
def all_inputs(engine, args):  # noqa: ARG001
    """Collect input or inout ports from current design."""
    ports = engine.db.get("ports", {})
    names = [n for n, p in ports.items() if p.get("direction") in ("input", "inout")]
    return "\n".join(sorted(names)) if names else ""


@command(category="STA/SDC")
def all_outputs(engine, args):  # noqa: ARG001
    """Collect output or inout ports from current design."""
    ports = engine.db.get("ports", {})
    names = [n for n, p in ports.items() if p.get("direction") in ("output", "inout")]
    return "\n".join(sorted(names)) if names else ""


@command(category="STA/SDC")
def all_register(engine, args):  # noqa: ARG001
    """Collect cells or pins from the current design."""
    cells = engine.db.get("cells", {})
    # Return sequential cells (flops, etc.)
    names = [n for n, c in cells.items() if "FF" in c.get("type", "").upper()]
    return "\n".join(sorted(names)) if names else ""


@command(category="STA/SDC")
def characterize(engine, args):
    """Characterize constraints for a subdesign."""
    return _ok(engine, args)


@command(category="STA/SDC")
def create_clock(engine, args):
    """Create or specify the clock."""
    name = "clk"
    period = "10.0"
    for i, a in enumerate(args):
        if a == "-name" and i + 1 < len(args):
            name = args[i + 1]
        if a == "-period" and i + 1 < len(args):
            period = args[i + 1]
    engine.db.setdefault("clocks", {})[name] = {
        "period": period,
        "waveform": [0.0, float(period) / 2],
    }
    return name


@command(category="STA/SDC")
def create_generated_clock(engine, args):
    """Create a generated clock."""
    return _ok(engine, args)


@command(category="STA/SDC")
def current_design(engine, args):
    """Set the current design."""
    if args:
        engine.variables["current_design"] = args[0]
    return engine.variables.get("current_design", "top")


@command(
    category="STA/SDC",
    flags=("-hier", "-filter"),
    positional_categories={0: ("cells",)},
)
def get_cell(engine, args):
    """Collect cells from current design."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    cells = engine.db.get("cells", {})
    names = [n for n in cells if n.startswith(pattern)]
    return "\n".join(sorted(names)) if names else ""


@command(category="STA/SDC")
def get_clock(engine, args):
    """Collect clocks from the current design."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    clocks = engine.db.get("clocks", {})
    names = [n for n in clocks if n.startswith(pattern)]
    return "\n".join(sorted(names)) if names else ""


@command(category="STA/SDC")
def get_lib(engine, args):
    """Collect libraries from liberty files."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    libs = engine.db.get("libs", {})
    names = [n for n in libs if n.startswith(pattern)]
    return "\n".join(sorted(names)) if names else ""


@command(category="STA/SDC")
def get_lib_cell(engine, args):
    """Collect library cells from liberty files."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    cells = []
    for lib in engine.db.get("libs", {}).values():
        for cname in lib.get("cells", {}):
            if cname.startswith(pattern):
                cells.append(cname)
    return "\n".join(sorted(cells)) if cells else ""


@command(category="STA/SDC")
def get_lib_pin(engine, args):
    """Collect library cell pins from liberty files."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    pins = []
    for lib in engine.db.get("libs", {}).values():
        for cname, cinfo in lib.get("cells", {}).items():
            for pname in cinfo.get("pins", []):
                full = f"{cname}/{pname}"
                if full.startswith(pattern):
                    pins.append(full)
    return "\n".join(sorted(pins)) if pins else ""


@command(
    category="STA/SDC",
    flags=("-of_objects",),
    positional_categories={0: ("nets",)},
    flag_value_categories={"-of_objects": ("cells",)},
)
def get_net(engine, args):
    """Collect nets from current design."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    nets = engine.db.get("nets", {})
    names = [n for n in nets if n.startswith(pattern)]
    return "\n".join(sorted(names)) if names else ""


@command(
    category="STA/SDC",
    positional_categories={0: ("pins",)},
)
def get_pin(engine, args):
    """Collect pins from current design."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    pins = []
    for cname, cinfo in engine.db.get("cells", {}).items():
        for pname in cinfo.get("pins", []):
            full = f"{cname}/{pname}"
            if full.startswith(pattern):
                pins.append(full)
    return "\n".join(sorted(pins)) if pins else ""


@command(category="STA/SDC")
def get_port(engine, args):
    """Collect ports from current design."""
    pattern = args[-1] if args and not args[-1].startswith("-") else ""
    ports = engine.db.get("ports", {})
    names = [n for n in ports if n.startswith(pattern)]
    return "\n".join(sorted(names)) if names else ""


@command(category="STA/SDC")
def group_path(engine, args):
    """Group paths for analysis."""
    return _ok(engine, args)


@command(category="STA/SDC")
def remove_case_analysis(engine, args):
    """Remove case-analysis value from input ports or pins."""
    return _ok(engine, args)


@command(category="STA/SDC")
def remove_propagated_clock(engine, args):
    """Remove propagated clock latency."""
    return _ok(engine, args)


# ── set_* SDC commands ───────────────────────────────────────


@command(category="STA/SDC")
def set_case_analysis(engine, args):
    """Specify constant logic value on a port or pin."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_clock_gating_check(engine, args):
    """Set up setup/hold checks on clock-gating cells."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_clock_group(engine, args):
    """Set clock groups."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_clock_latency(engine, args):
    """Specify clock latency for clocks, ports, or pins."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_clock_sense(engine, args):
    """Set clock sense."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_clock_transition(engine, args):
    """Set transition time at clock pins."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_clock_uncertainty(engine, args):
    """Specify clock network uncertainty (skew)."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_data_check(engine, args):
    """Set data-to-data checks."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_disable_clock_gating_check(engine, args):
    """Disable clock-gating check for specified objects."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_disable_timing(engine, args):
    """Disable timing arcs in the current design."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_drive(engine, args):
    """Set the rise_drive or fall_drive attributes."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_driving_cell(engine, args):
    """Specify a library cell driving the specified ports."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_false_path(engine, args):
    """Remove timing constraints from particular paths."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_fanout_load(engine, args):
    """Specify the value for the fanout_load attribute."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_hierarchy_separator(engine, args):
    """Set the hierarchy separator character."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_ideal_latency(engine, args):
    """Specify ideal network latency."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_ideal_network(engine, args):
    """Specify ideal network sources."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_ideal_transition(engine, args):
    """Specify ideal transition for ideal networks/nets."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_input_delay(engine, args):
    """Set input delay on pins or input ports relative to a clock."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_input_transition(engine, args):
    """Specified transition values on input/inout ports."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_load(engine, args):
    """Set the load attribute on specified ports and nets."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_logic_dc(engine, args):
    """Specify input ports driven by don't care."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_logic_one(engine, args):
    """Specify input ports driven by logic one."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_logic_zero(engine, args):
    """Specify input ports driven by logic zero."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_max_area(engine, args):
    """Set the max_area attribute."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_max_capacitance(engine, args):
    """Set max_capacitance on clocks, ports, and designs."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_max_delay(engine, args):
    """Specify a maximum delay target for paths."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_max_fanout(engine, args):
    """Set max_fanout on input ports and designs."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_max_time_borrow(engine, args):
    """Set max_time_borrow."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_max_transition(engine, args):
    """Set maximum transition time."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_min_capacitance(engine, args):
    """Set min_capacitance on input ports."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_min_delay(engine, args):
    """Specify a minimum delay target for paths."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_min_pulse_width(engine, args):
    """Set min pulse width."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_mode(engine, args):
    """Select active mode of a multi-functional cell."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_multicycle_path(engine, args):
    """Modify the single-cycle timing relationship."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_operating_conditions(engine, args):
    """Set operating conditions."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_output_delay(engine, args):
    """Set output delay on pins or output ports relative to a clock."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_port_fanout_number(engine, args):
    """Set the fanout number on specified ports."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_propagated_clock(engine, args):
    """Set propagated clock."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_resistance(engine, args):
    """Set annotated lumped net resistance."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_timing_derate(engine, args):
    """Set a derating factor on the design or objects."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_units(engine, args):
    """Set units for checking."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_wire_load_min_block_size(engine, args):
    """Set wire load min block size."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_wire_load_mode(engine, args):
    """Set wire load mode."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_wire_load_model(engine, args):
    """Set wire load model."""
    return _ok(engine, args)


@command(category="STA/SDC")
def set_wire_load_selection_group(engine, args):
    """Set wire load selection group."""
    return _ok(engine, args)


@command(category="STA/SDC")
def write_sdc(engine, args):
    """Write SDC constraint script for current design."""
    filename = args[-1] if args else "design.sdc"
    return f"1  # wrote {filename}"


# ═══════════════════════════════════════════════════════════════
# STA/REPORT
# ═══════════════════════════════════════════════════════════════


@command(category="STA/REPORT")
def get_pin_info(engine, args):
    """Get pin information."""
    if not args:
        return ""
    pin = args[-1]
    return f"  Pin: {pin}\n  Capacitance: 0.015 pF\n  Slew: 0.120 ns\n"


@command(category="STA/REPORT")
def report_clock(engine, args):  # noqa: ARG001
    """Display clock-related information."""
    clocks = engine.db.get("clocks", {})
    lines = ["  Clock Report", "-" * 40]
    for name, info in sorted(clocks.items()):
        lines.append(f"  {name:<20s} period={info.get('period', '?')}ns")
    return "\n".join(lines)


@command(category="STA/REPORT")
def report_clock_fanout(engine, args):  # noqa: ARG001
    """Alias for report_transive_fanout -clock_tree."""
    return _report_template(
        "Clock Fanout",
        [
            ("Max fanout:", "32"),
            ("Clock nets:", "5"),
        ],
    )(engine, args)


@command(category="STA/REPORT")
def report_clock_gating(engine, args):  # noqa: ARG001
    """Report clock-gating details."""
    return _report_template(
        "Clock Gating",
        [
            ("Gating cells:", "3"),
            ("Gated clocks:", "2"),
            ("Ungated endpoints:", "12"),
        ],
    )(engine, args)


@command(category="STA/REPORT")
def report_delay_calculation(engine, args):  # noqa: ARG001
    """Display timing arc delay calculation for a cell or net."""
    return _report_template(
        "Delay Calculation",
        [
            ("  Cell / Net:", "..."),
            ("  Rise delay:", "0.245 ns"),
            ("  Fall delay:", "0.198 ns"),
            ("  Slew rate:", "0.120 ns/V"),
        ],
    )(engine, args)


@command(category="STA/REPORT")
def report_min_pulse_width(engine, args):  # noqa: ARG001
    """Report minimum pulse width."""
    return _report_template(
        "Min Pulse Width",
        [
            ("  Clock:", "clk_100m"),
            ("  Min high pulse:", "2.5 ns"),
            ("  Min low pulse:", "2.5 ns"),
            ("  Violations:", "0"),
        ],
    )(engine, args)


@command(category="STA/REPORT")
def report_qor(engine, args):  # noqa: ARG001
    """Display QoR information and statistics."""
    return _report_template(
        "QoR Summary",
        [
            ("WNS (ns):", "-0.123"),
            ("TNS (ns):", "-1.456"),
            ("FEP:", "5"),
            ("Total cells:", str(len(engine.db.get("cells", {})))),
            ("Combo cells:", "4"),
            ("Seq cells:", "2"),
            ("Macros:", "3"),
            ("Area (um2):", "100000.00"),
        ],
    )(engine, args)


@command(
    category="STA/REPORT",
    flags=("-from", "-to", "-nworst"),
    flag_value_categories={"-from": ("pins",), "-to": ("pins",)},
)
def report_timing(engine, args):  # noqa: ARG001
    """Display timing information about a design."""
    if not engine._placed:  # noqa: SLF001
        return "Timing report: (design not yet placed)"
    return (
        "====================================================\n"
        "  Timing Report\n"
        "====================================================\n"
        "  Data Path Delay:    2.345 ns\n"
        "  Clock Path Skew:    0.012 ns\n"
        "  Slack:              0.543 ns\n"
        "  WNS:                0.432 ns\n"
        "  TNS:                1.234 ns\n"
        "  Failing Endpoints:  0\n"
        "===================================================="
    )


@command(category="STA/REPORT")
def report_timing_derate(engine, args):  # noqa: ARG001
    """Report timing derating factors."""
    return _report_template(
        "Timing Derate",
        [
            ("Early (data path):", "0.95"),
            ("Late (clock path):", "1.05"),
            ("Cell early:", "0.95"),
            ("Cell late:", "1.05"),
            ("Net early:", "1.00"),
            ("Net late:", "1.00"),
        ],
    )(engine, args)


@command(category="STA/REPORT")
def report_wire_load(engine, args):  # noqa: ARG001
    """Display wire-load model characteristics."""
    return _report_template(
        "Wire Load",
        [
            ("Model:", "wl20k"),
            ("Resistance (kOhm/um):", "0.008"),
            ("Capacitance (pF/um):", "0.0002"),
            ("Area (um2/um):", "0.07"),
            ("Slope:", "0.5"),
            ("Fanout length (um):", "Fanout_length(1) = 20"),
        ],
    )(engine, args)


# ═══════════════════════════════════════════════════════════════
# SYNTHESIS
# ═══════════════════════════════════════════════════════════════


@command(category="SYNTHESIS")
def add_tieoffs(engine, args):
    """Tie constants 1'b0 and 1'b1 to tie-high/tie-low cells."""
    return _ok(engine, args)


@command(category="SYNTHESIS")
def group(engine, args):
    """Create new hierarchy."""
    return _ok(engine, args)


@command(category="SYNTHESIS")
def optimize(engine, args):  # noqa: ARG001
    """Optimize netlist timing and physical information."""
    return "1  # optimization complete  (slack improved by 0.023 ns)"


@command(category="SYNTHESIS")
def read_file(engine, args):
    """Read a design file."""
    filename = args[-1] if args else "design.v"
    return f"1  # read {filename}"


@command(category="SYNTHESIS")
def resyn(engine, args):  # noqa: ARG001
    """Re-synthesize for mapped netlist."""
    return "1  # re-synthesis complete"


@command(category="SYNTHESIS")
def run_analyze(engine, args):
    """Analyze HDL files."""
    targets = [a for a in args if not a.startswith("-")]
    names = " ".join(targets) if targets else "(all)"
    return f"1  # analyzed {names}"


@command(category="SYNTHESIS")
def run_elaborate(engine, args):
    """Elaborate the design."""
    top = args[-1] if args else "top"
    engine.variables["current_design"] = top
    engine.variables["elaborated"] = "1"
    return f"1  # elaborated {top}"


@command(category="SYNTHESIS")
def run_synth(engine, args):  # noqa: ARG001
    """Run generic synthesis."""
    return "1  # synthesis complete\n" "  Area: 12345.67 um2\n" "  Slack: 0.543 ns\n" "  Cell count: 42"


@command(category="SYNTHESIS")
def run_synth_netlist(engine, args):  # noqa: ARG001
    """Synthesize netlist."""
    return "1  # netlist synthesis complete"


@command(category="SYNTHESIS")
def set_hls_config(engine, args):
    """Configure high-level synthesis configuration."""
    return _ok(engine, args)


@command(category="SYNTHESIS")
def ungroup(engine, args):
    """Flatten a module's cells into the parent module."""
    return _ok(engine, args)


# ═══════════════════════════════════════════════════════════════
# HIGHLEVELSYN
# ═══════════════════════════════════════════════════════════════


@command(category="HIGHLEVELSYN")
def high_level_synth(engine, args):  # noqa: ARG001
    """Execute a high-level synthesis flow."""
    return "1  # high-level synthesis complete"

"""Tests for the mock EDA Tcl engine."""

from __future__ import annotations

import pytest

from edai.tool.tcl.engine import TclEngine, TclError


@pytest.fixture
def engine() -> TclEngine:
    """Fresh engine instance per test."""
    return TclEngine()


class TestCoreCommands:
    """Basic command execution."""

    def test_get_cells(self, engine: TclEngine) -> None:
        result = engine.execute("get_cells")
        lines = result.strip().split("\n")
        assert "u_cpu_core" in lines
        assert "u_clk_gen" in lines
        assert "u_ram_0" in lines

    def test_get_cells_with_pattern(self, engine: TclEngine) -> None:
        result = engine.execute("get_cells u_ram")
        lines = result.strip().split("\n")
        assert "u_ram_0" in lines
        assert "u_ram_1" in lines
        assert "u_cpu_core" not in lines

    def test_get_cells_no_match(self, engine: TclEngine) -> None:
        result = engine.execute("get_cells nonexistent")
        assert result.strip() == ""

    def test_get_nets(self, engine: TclEngine) -> None:
        result = engine.execute("get_nets")
        lines = result.strip().split("\n")
        assert "clk_100m" in lines
        assert "rst_n" in lines
        assert "data_bus" in lines

    def test_get_nets_with_pattern(self, engine: TclEngine) -> None:
        result = engine.execute("get_nets clk")
        lines = result.strip().split("\n")
        assert "clk_100m" in lines
        assert "rst_n" not in lines

    def test_get_pins(self, engine: TclEngine) -> None:
        result = engine.execute("get_pins")
        lines = result.strip().split("\n")
        assert "clk" in lines
        assert "txd" in lines
        assert "data[31:0]" in lines

    def test_get_pins_with_cell(self, engine: TclEngine) -> None:
        result = engine.execute("get_pins -of_objects u_uart")
        lines = result.strip().split("\n")
        assert "rxd" in lines
        assert "txd" in lines
        # pins from other cells should not appear
        assert "data_bus[31:0]" not in lines


class TestSetProperty:
    """Property mutation commands."""

    def test_set_property(self, engine: TclEngine) -> None:
        result = engine.execute("set_property FREQUENCY 200MHz u_clk_gen")
        assert "u_clk_gen.FREQUENCY = 200MHz" in result
        # verify the property was actually set
        assert engine.db["cells"]["u_clk_gen"]["properties"]["FREQUENCY"] == "200MHz"

    def test_set_property_wrong_args(self, engine: TclEngine) -> None:
        with pytest.raises(TclError, match="wrong # args"):
            engine.execute("set_property FOO bar")

    def test_set_property_unknown_object(self, engine: TclEngine) -> None:
        result = engine.execute("set_property FOO bar nonexistent_cell")
        assert "not found" in result


class TestFlowCommands:
    """Design flow commands (place → route → timing)."""

    def test_timing_before_place(self, engine: TclEngine) -> None:
        result = engine.execute("report_timing")
        assert "not yet placed" in result.lower()

    def test_place_design(self, engine: TclEngine) -> None:
        result = engine.execute("place_design")
        assert "successfully" in result.lower()
        assert engine._placed is True  # noqa: SLF001

    def test_route_before_place(self, engine: TclEngine) -> None:
        engine.execute("place_design")
        result = engine.execute("route_design")
        assert "successfully" in result.lower()
        assert engine._routed is True  # noqa: SLF001

    def test_route_without_place(self, engine: TclEngine) -> None:
        result = engine.execute("route_design")
        assert "must be placed" in result.lower()

    def test_full_flow(self, engine: TclEngine) -> None:
        engine.execute("place_design")
        engine.execute("route_design")
        result = engine.execute("report_timing")
        assert "Timing Report" in result
        assert "Slack:" in result


class TestHelp:
    """Help command."""

    def test_help_all(self, engine: TclEngine) -> None:
        result = engine.execute("help")
        assert "Available commands" in result
        assert "get_cells" in result
        assert "place_design" in result

    def test_help_topic(self, engine: TclEngine) -> None:
        result = engine.execute("help get_cells")
        assert "Usage:" in result
        assert "get_cells" in result

    def test_help_unknown(self, engine: TclEngine) -> None:
        result = engine.execute("help foobar")
        assert "unknown" in result.lower()


class TestVariables:
    """Tcl variable substitution."""

    def test_set_and_get_variable(self, engine: TclEngine) -> None:
        engine.set_variable("design", "top")
        assert engine.get_variable("design") == "top"

    def test_get_undefined_variable(self, engine: TclEngine) -> None:
        with pytest.raises(TclError, match="no such variable"):
            engine.get_variable("nonexistent")

    def test_variable_substitution_in_command(self, engine: TclEngine) -> None:
        engine.set_variable("cell_name", "u_uart")
        result = engine.execute("get_cells $cell_name")
        assert "u_uart" in result
        assert "u_cpu_core" not in result

    def test_variable_subst_with_braces(self, engine: TclEngine) -> None:
        engine.set_variable("my_cell", "u_dsp_0")
        result = engine.execute("get_cells ${my_cell}")
        assert "u_dsp_0" in result


class TestErrorHandling:
    """Error cases."""

    def test_unknown_command(self, engine: TclEngine) -> None:
        with pytest.raises(TclError, match="unknown command"):
            engine.execute("nonexistent_command")

    def test_empty_command(self, engine: TclEngine) -> None:
        assert engine.execute("") == ""
        assert engine.execute("   ") == ""

    def test_is_valid_tcl(self, engine: TclEngine) -> None:
        assert engine.is_valid_tcl("get_cells") is True
        assert engine.is_valid_tcl("set_property A B C") is True
        assert engine.is_valid_tcl("random gibberish") is False
        assert engine.is_valid_tcl("") is False


class TestQueryHelpers:
    """Completer-facing query methods."""

    def test_get_command_names(self, engine: TclEngine) -> None:
        names = engine.get_command_names()
        assert "get_cells" in names
        assert "help" in names

    def test_get_command_names_with_prefix(self, engine: TclEngine) -> None:
        names = engine.get_command_names("get_")
        assert "get_cells" in names
        assert "get_pins" in names
        assert "help" not in names

    def test_get_cell_names(self, engine: TclEngine) -> None:
        names = engine.get_cell_names()
        assert len(names) == 6

    def test_get_cell_names_prefix(self, engine: TclEngine) -> None:
        names = engine.get_cell_names("u_ram")
        assert names == ["u_ram_0", "u_ram_1"]

    def test_get_pin_names_all(self, engine: TclEngine) -> None:
        names = engine.get_pin_names()
        assert "clk" in names
        assert "txd" in names

    def test_get_pin_names_by_cell(self, engine: TclEngine) -> None:
        names = engine.get_pin_names(cell="u_uart")
        assert "rxd" in names
        assert "txd" in names
        # u_ram pins should NOT appear in u_uart's pin list
        assert "addr[15:0]" not in names

    def test_get_net_names(self, engine: TclEngine) -> None:
        names = engine.get_net_names()
        assert "clk_100m" in names
        assert "uart_tx" in names

    def test_get_property_names(self, engine: TclEngine) -> None:
        names = engine.get_property_names()
        assert "FREQUENCY" in names
        assert "IOSTANDARD" in names

    def test_get_property_names_prefix(self, engine: TclEngine) -> None:
        names = engine.get_property_names("IO")
        assert names == ["IOSTANDARD"]


class TestCompletionMetadata:
    """CommandRegistry completion metadata integration."""

    def test_get_command_flags(self) -> None:
        from edai.core.cmd_registry import registry as r

        flags = r.get_command_flags("get_cells")
        assert "-hier" in flags
        assert "-filter" in flags

    def test_get_command_flags_default(self) -> None:
        from edai.core.cmd_registry import registry as r

        assert r.get_command_flags("place_design") == ()

    def test_get_command_flags_unknown(self) -> None:
        from edai.core.cmd_registry import registry as r

        assert r.get_command_flags("nonexistent") == ()

    def test_get_positional_categories(self) -> None:
        from edai.core.cmd_registry import registry as r

        cats = r.get_positional_categories("get_cells", 0)
        assert "cells" in cats

        cats = r.get_positional_categories("set_property", 0)
        assert "properties" in cats

        cats = r.get_positional_categories("set_property", 2)
        assert "cells" in cats or "pins" in cats

    def test_get_positional_categories_default(self) -> None:
        from edai.core.cmd_registry import registry as r

        assert r.get_positional_categories("place_design", 0) == ()

    def test_get_positional_categories_out_of_range(self) -> None:
        from edai.core.cmd_registry import registry as r

        assert r.get_positional_categories("get_cells", 99) == ()

    def test_get_flag_value_categories(self) -> None:
        from edai.core.cmd_registry import registry as r

        cats = r.get_flag_value_categories("get_pins", "-of_objects")
        assert "cells" in cats

        cats = r.get_flag_value_categories("report_timing", "-from")
        assert "pins" in cats

        cats = r.get_flag_value_categories("report_timing", "-to")
        assert "pins" in cats

    def test_get_flag_value_categories_default(self) -> None:
        from edai.core.cmd_registry import registry as r

        assert r.get_flag_value_categories("get_cells", "-hier") == ()

    def test_get_flag_value_categories_unknown_flag(self) -> None:
        from edai.core.cmd_registry import registry as r

        assert r.get_flag_value_categories("get_cells", "-nonexistent") == ()

    def test_register_with_metadata(self) -> None:
        from edai.core.cmd_registry import registry as r

        def _handler(eng, args):  # noqa: ARG001
            return "ok"

        r.register(
            "_test_meta_cmd",
            category="TEST",
            handler=_handler,
            flags=("-a", "-b"),
            positional_categories={0: ("cells",), 1: ("pins",)},
            flag_value_categories={"-a": ("nets",)},
        )
        try:
            assert r.get_command_flags("_test_meta_cmd") == ("-a", "-b")
            assert r.get_positional_categories("_test_meta_cmd", 0) == ("cells",)
            assert r.get_positional_categories("_test_meta_cmd", 1) == ("pins",)
            assert r.get_flag_value_categories("_test_meta_cmd", "-a") == ("nets",)
        finally:
            # Cleanup
            r._commands.pop("_test_meta_cmd", None)  # noqa: SLF001
            r._categories.get("TEST", []).remove("_test_meta_cmd")

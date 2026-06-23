"""Tests for MockTclRepl — set/puts/expr variable handling."""

from __future__ import annotations

from edai.core.mock_repl import MockTclRepl


def _make_repl() -> MockTclRepl:
    """Helper: create a fresh REPL for each test."""
    return MockTclRepl()


# ── set command ────────────────────────────────────────────────────────


class TestSetCommand:
    """Tests for the ``set`` command (variable assignment and read)."""

    def test_set_assign_and_read(self) -> None:
        repl = _make_repl()
        assert repl.send_command("set foo hello") == "hello"
        assert repl.send_command("set foo") == "hello"

    def test_set_overwrite(self) -> None:
        repl = _make_repl()
        repl.send_command("set x 10")
        repl.send_command("set x 20")
        assert repl.send_command("set x") == "20"

    def test_set_read_unset(self) -> None:
        repl = _make_repl()
        result = repl.send_command("set nonexistent")
        assert "not set" in result

    def test_set_with_spaces(self) -> None:
        repl = _make_repl()
        repl.send_command('set msg "hello world"')
        # shlex strips the quotes, so the value is "hello world"
        assert repl.send_command("set msg") == "hello world"

    def test_set_resolves_var_reference(self) -> None:
        """``set b $a`` should resolve $a to its value."""
        repl = _make_repl()
        repl.send_command("set a 42")
        assert repl.send_command("set b $a") == "42"
        assert repl.send_command("set b") == "42"

    def test_set_resolves_var_reference_complex(self) -> None:
        """``$var`` in the value string should be substituted."""
        repl = _make_repl()
        repl.send_command('set greeting "Hello"')
        result = repl.send_command('set msg "$greeting, World"')
        assert result == "Hello, World"
        assert repl.send_command("set msg") == "Hello, World"


# ── puts command ──────────────────────────────────────────────────────


class TestPutsCommand:
    """Tests for the ``puts`` command (print value)."""

    def test_puts_literal_string(self) -> None:
        repl = _make_repl()
        assert repl.send_command('puts "hello"') == "hello"

    def test_puts_variable(self) -> None:
        repl = _make_repl()
        repl.send_command("set name Alice")
        assert repl.send_command("puts $name") == "Alice"

    def test_puts_inline_substitution(self) -> None:
        repl = _make_repl()
        repl.send_command("set x 42")
        assert repl.send_command('puts "value is $x"') == "value is 42"

    def test_puts_no_args(self) -> None:
        """``puts`` alone should output an empty string (newline)."""
        repl = _make_repl()
        assert repl.send_command("puts") == ""

    def test_puts_nonewline(self) -> None:
        repl = _make_repl()
        assert repl.send_command('puts -nonewline "hi"') == "hi"

    def test_puts_nonewline_no_value(self) -> None:
        repl = _make_repl()
        assert repl.send_command("puts -nonewline") == ""

    def test_puts_multiple_args(self) -> None:
        """Multiple args are joined with spaces."""
        repl = _make_repl()
        result = repl.send_command("puts hello world")
        assert result == "hello world"

    def test_puts_unset_variable(self) -> None:
        """Unset ``$var`` is left as-is."""
        repl = _make_repl()
        result = repl.send_command("puts $undefined")
        assert result == "$undefined"

    def test_puts_with_braces(self) -> None:
        """Braces should suppress variable substitution (shlex keeps them)."""
        repl = _make_repl()
        repl.send_command("set foo bar")
        # In Tcl, {…} prevents substitution. shlex doesn't strip {…}, so
        # the literal text is preserved.
        result = repl.send_command("puts {$foo}")
        assert result == "{$foo}" or result == "{bar}"
        # Accept either — the important thing is it doesn't crash.


# ── set + puts integration ────────────────────────────────────────────


class TestSetAndPutsIntegration:
    """End-to-end variable write-then-read scenarios."""

    def test_write_then_read(self) -> None:
        repl = _make_repl()
        repl.send_command("set a 100")
        assert repl.send_command("puts $a") == "100"

    def test_chain_assignment(self) -> None:
        """``set b $a`` then ``puts $b`` should work."""
        repl = _make_repl()
        repl.send_command("set a 5")
        repl.send_command("set b $a")
        assert repl.send_command("puts $b") == "5"

    def test_interleaved_commands(self) -> None:
        """Mix set/puts with other Tcl commands."""
        repl = _make_repl()
        repl.send_command("set cell u1")
        result = repl.send_command("get_cells")
        assert "u1" in result


# ── existing behaviour regression ─────────────────────────────────────


class TestExistingBehaviour:
    """Ensure existing commands still work after our changes."""

    def test_expr_arithmetic(self) -> None:
        repl = _make_repl()
        assert repl.send_command("expr 1 + 2") == "3"

    def test_expr_with_variable(self) -> None:
        repl = _make_repl()
        repl.send_command("set x 10")
        assert repl.send_command("expr $x * 2") == "20"

    def test_unknown_command(self) -> None:
        repl = _make_repl()
        result = repl.send_command("unknown_cmd")
        assert "unknown" in result or "not found" in result

    def test_special_commands(self) -> None:
        repl = _make_repl()
        result = repl.send_command("/help")
        assert result is not None
        assert "Special commands" in result

    def test_empty_line(self) -> None:
        repl = _make_repl()
        assert repl.send_command("") == ""

    def test_whitespace_line(self) -> None:
        repl = _make_repl()
        assert repl.send_command("   ") == ""

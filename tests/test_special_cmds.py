"""Tests for the special /-command registry and built-in commands."""

from __future__ import annotations

from typing import Any

import pytest

from edai.core.cmd_registry import CommandError
from edai.core.Message import Message
from edai.core.special_cmds import SpecialCommandRegistry


@pytest.fixture
def special_reg() -> SpecialCommandRegistry:
    """Fresh registry per test."""
    return SpecialCommandRegistry()


class TestSpecialCommandRegistry:
    """Registry mechanics."""

    def test_register_and_get(self, special_reg: SpecialCommandRegistry) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "test ok"

        special_reg.register("test", handler=handler, description="A test command")
        cmd = special_reg.get("test")
        assert cmd is not None
        assert cmd.name == "test"
        assert cmd.description == "A test command"

    def test_get_strips_leading_slash(
        self, special_reg: SpecialCommandRegistry
    ) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "ok"

        special_reg.register("test", handler=handler)
        assert special_reg.get("/test") is not None

    def test_register_aliases(self, special_reg: SpecialCommandRegistry) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "test ok"

        special_reg.register("test", handler=handler, aliases=("t", "ts"))
        assert special_reg.get("test") is special_reg.get("t")
        assert special_reg.get("t") is special_reg.get("ts")

    def test_get_names_excludes_aliases(
        self, special_reg: SpecialCommandRegistry
    ) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "ok"

        special_reg.register("test", handler=handler, aliases=("t",))
        names = special_reg.get_names()
        assert "test" in names
        assert "t" not in names

    def test_get_names_with_prefix(self, special_reg: SpecialCommandRegistry) -> None:
        def handler_a(engine: Any, repl: Any, args: list[str]) -> None:  # noqa: ARG001
            return None

        def handler_b(engine: Any, repl: Any, args: list[str]) -> None:  # noqa: ARG001
            return None

        special_reg.register("alpha", handler=handler_a)
        special_reg.register("beta", handler=handler_b)
        names = special_reg.get_names("a")
        assert names == ["alpha"]

    def test_execute_unknown_raises(self, special_reg: SpecialCommandRegistry) -> None:
        with pytest.raises(CommandError, match="unknown special command"):
            special_reg.execute("nonexistent", None, None, [])

    def test_execute_returns_output(self, special_reg: SpecialCommandRegistry) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return f"Hello, {args[0] if args else 'world'}!"

        special_reg.register("hello", handler=handler)
        result = special_reg.execute("hello", None, None, ["EDAI"])
        assert result == "Hello, EDAI!"

    def test_function_decorator(self, special_reg: SpecialCommandRegistry) -> None:
        @special_reg.special_command()
        def decorated(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "decorated ok"

        cmd = special_reg.get("decorated")
        assert cmd is not None
        result = special_reg.execute("decorated", None, None, [])
        assert result == "decorated ok"

    def test_decorator_with_args(self, special_reg: SpecialCommandRegistry) -> None:
        @special_reg.special_command(name="greet", description="Say hi")
        def my_fn(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "hi"

        cmd = special_reg.get("greet")
        assert cmd is not None
        assert cmd.description == "Say hi"
        result = special_reg.execute("greet", None, None, [])
        assert result == "hi"

    def test_execute_passes_engine_repl_args(
        self, special_reg: SpecialCommandRegistry
    ) -> None:
        captured: dict[str, Any] = {}

        def handler(engine: Any, repl: Any, args: list[str]) -> None:
            captured["engine"] = engine
            captured["repl"] = repl
            captured["args"] = args
            return None

        special_reg.register("capture", handler=handler)
        special_reg.execute("capture", "eng_val", "repl_val", ["a", "b"])
        assert captured == {"engine": "eng_val", "repl": "repl_val", "args": ["a", "b"]}

    def test_execute_with_leading_slash(
        self, special_reg: SpecialCommandRegistry
    ) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "slash ok"

        special_reg.register("slash", handler=handler)
        result = special_reg.execute("/slash", None, None, [])
        assert result == "slash ok"

    def test_contains(self, special_reg: SpecialCommandRegistry) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "ok"

        special_reg.register("mycmd", handler=handler)
        assert "mycmd" in special_reg
        assert "/mycmd" in special_reg
        assert "unknown" not in special_reg

    def test_len(self, special_reg: SpecialCommandRegistry) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "ok"

        assert len(special_reg) == 0
        special_reg.register("a", handler=handler)
        assert len(special_reg) == 1
        special_reg.register("b", handler=handler)
        assert len(special_reg) == 2

    def test_len_counts_primary_names_only(
        self, special_reg: SpecialCommandRegistry
    ) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "ok"

        special_reg.register("x", handler=handler, aliases=("x_alias",))
        assert len(special_reg) == 1

    def test_register_returns_handler(
        self, special_reg: SpecialCommandRegistry
    ) -> None:
        def handler(engine: Any, repl: Any, args: list[str]) -> str:  # noqa: ARG001
            return "ok"

        returned = special_reg.register("check", handler=handler)
        assert returned is handler


class TestBuiltinCommands:
    """Built-in / commands provided by the module."""

    def test_help_command(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("help")
        assert cmd is not None
        assert "help" in cmd.name
        assert "?" in cmd.aliases or "h" in cmd.aliases

    def test_help_output(self) -> None:
        from edai.core.special_cmds import registry

        output = registry.execute("help", None, None, [])
        assert output is not None
        assert "Special commands" in output
        assert "/help" in output

    def test_clear_command(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("clear")
        assert cmd is not None
        assert "cls" in cmd.aliases

    def test_exit_command(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("exit")
        assert cmd is not None
        with pytest.raises(SystemExit):
            registry.execute("exit", None, None, [])

    def test_exit_via_quit_alias(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("quit")
        assert cmd is not None
        assert cmd.name == "exit"

    def test_debug_command(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("debug")
        assert cmd is not None

    def test_env_command(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("env")
        assert cmd is not None

    def test_env_output(self) -> None:
        from edai.core.special_cmds import registry
        from edai.tool.tcl.engine import TclEngine

        engine = TclEngine()
        output = registry.execute("env", engine, None, [])
        assert output is not None
        assert "Environment" in output
        assert "Cells:" in output
        assert "Nets:" in output

    def test_debug_toggle(self) -> None:
        from edai.core.special_cmds import registry

        class FakeRepl:
            def __init__(self) -> None:
                self.verbose = False

        repl = FakeRepl()
        assert repl.verbose is False

        result = registry.execute("debug", None, repl, [])
        assert "enabled" in (result or "")
        assert repl.verbose is True

        result2 = registry.execute("debug", None, repl, [])
        assert "disabled" in (result2 or "")
        assert repl.verbose is False

    def test_help_does_not_show_hidden(self) -> None:
        from edai.core.special_cmds import registry

        output = registry.execute("help", None, None, [])
        assert output is not None
        assert "/help" in output

    def test_help_shows_history(self) -> None:
        """/history is not hidden, so it should appear in /help output."""
        from edai.core.special_cmds import registry

        output = registry.execute("help", None, None, [])
        assert output is not None
        assert "/history" in output


class TestHistoryCommand:
    """Tests for the ``/history`` special command."""

    @pytest.fixture
    def mock_repl_with_history(self) -> Any:
        """A repl-like object with a `_conversation` containing sample messages."""

        class MockRepl:
            def __init__(self) -> None:
                self._conversation = [
                    Message.human("get_cells"),
                    Message.ai("Found 6 cells."),
                    Message.human("report_timing -max_paths 5"),
                    Message.ai("Timing report generated."),
                    Message.human("place_design"),
                    Message.tool("Placement completed successfully."),
                ]

        return MockRepl()

    @pytest.fixture
    def empty_repl(self) -> Any:
        """A repl-like object with an empty conversation."""

        class MockRepl:
            def __init__(self) -> None:
                self._conversation: list[Message] = []

        return MockRepl()

    @pytest.fixture
    def bare_repl(self) -> Any:
        """A repl-like object with no conversation attribute at all."""

        class MockRepl:
            pass

        return MockRepl()

    # ── registration ──────────────────────────────────────────────

    def test_history_registered(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("history")
        assert cmd is not None
        assert cmd.description.startswith("Show conversation history")

    def test_history_has_hist_alias(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("hist")
        assert cmd is not None
        assert cmd.name == "history"

    # ── edge cases ────────────────────────────────────────────────

    def test_history_no_conversation(self, bare_repl: Any) -> None:
        from edai.core.special_cmds import registry

        result = registry.execute("history", None, bare_repl, [])
        assert result == "No conversation history available."

    def test_history_empty(self, empty_repl: Any) -> None:
        from edai.core.special_cmds import registry

        result = registry.execute("history", None, empty_repl, [])
        assert result == "No conversation history available."

    def test_history_via_alias(self, mock_repl_with_history: Any) -> None:
        from edai.core.special_cmds import registry

        result = registry.execute("hist", None, mock_repl_with_history, [])
        assert result is not None
        assert "Conversation history" in result

    # ── output format ─────────────────────────────────────────────

    def test_history_output(self, mock_repl_with_history: Any) -> None:
        from edai.core.special_cmds import registry

        result = registry.execute("history", None, mock_repl_with_history, [])
        assert result is not None

        # Has header
        assert result.startswith("Conversation history:")

        # Contains numbered entries
        assert "  1." in result
        assert "  6." in result

        # Contains role labels
        assert "HUMAN:" in result
        assert "AI:" in result
        assert "TOOL:" in result

        # Contains message content
        assert "get_cells" in result
        assert "Found 6 cells." in result
        assert "Placement completed successfully." in result

        # Contains Rich markup tags
        assert "[bold cyan]" in result
        assert "[bold green]" in result
        assert "[bold yellow]" in result
        assert "[/]" in result

    # ── numeric argument ──────────────────────────────────────────

    def test_history_n_returns_last_n(self, mock_repl_with_history: Any) -> None:
        from edai.core.special_cmds import registry

        result = registry.execute("history", None, mock_repl_with_history, ["3"])
        assert result is not None
        # Should show only the last 3 messages (indices 4, 5, 6)
        assert "  4." in result
        assert "  5." in result
        assert "  6." in result
        assert "  1." not in result
        assert "  2." not in result
        assert "  3." not in result

    def test_history_n_more_than_total(self, mock_repl_with_history: Any) -> None:
        """Asking for more than available shows all messages."""
        from edai.core.special_cmds import registry

        result = registry.execute("history", None, mock_repl_with_history, ["99"])
        assert result is not None
        assert "  1." in result
        assert "  6." in result

    @pytest.mark.parametrize(
        "bad_arg, expected_substr",
        [
            ("abc", "Invalid argument"),
            ("-1", "must be positive"),
            ("0", "must be positive"),
        ],
    )
    def test_history_invalid_n(
        self, mock_repl_with_history: Any, bad_arg: str, expected_substr: str
    ) -> None:
        from edai.core.special_cmds import registry

        result = registry.execute("history", None, mock_repl_with_history, [bad_arg])
        assert result is not None
        assert expected_substr in result

    # ── interaction with /help ────────────────────────────────────

    def test_history_not_hidden(self) -> None:
        from edai.core.special_cmds import registry

        cmd = registry.get("history")
        assert cmd is not None
        assert not cmd.hidden

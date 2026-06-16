"""Tests for the EDA REPL (non-interactive parts)."""

from __future__ import annotations

import pytest

from edai.agent.agent import Agent
from edai.tool.tcl.completer import EdaCompleter
from edai.tool.tcl.engine import TclEngine
from edai.tool.tcl.repl import EdaRepl


@pytest.fixture
def repl() -> EdaRepl:
    """REPL instance with no I/O side effects (session not started)."""
    engine = TclEngine()
    agent = Agent(engine)
    return EdaRepl(engine, agent, verbose=False)


class TestHandleInput:
    """Test the input processing logic directly."""

    @pytest.mark.asyncio
    async def test_tcl_command_executes(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("get_cells")
        assert code == 0

    @pytest.mark.asyncio
    async def test_natural_language_translates(self, repl: EdaRepl) -> None:
        """NL "place all" → translated → executed."""
        code = await repl._handle_input("place all")
        assert code == 0
        assert repl.engine._placed is True  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_natural_language_routing(self, repl: EdaRepl) -> None:
        repl.engine._placed = True  # noqa: SLF001
        code = await repl._handle_input("route the design")
        assert code == 0
        assert repl.engine._routed is True  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_unrecognized_nl_returns_error(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("do something completely random")
        assert code == 1

    @pytest.mark.asyncio
    async def test_empty_input(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("")
        assert code == 0

    @pytest.mark.asyncio
    async def test_prompt_reflects_state(self, repl: EdaRepl) -> None:
        prompt = repl._mk_prompt()
        assert prompt == "eda> "

        repl.engine.execute("place_design")
        prompt2 = repl._mk_prompt()
        assert "P" in prompt2

        repl.engine.execute("route_design")
        prompt3 = repl._mk_prompt()
        assert "R" in prompt3


class TestEdaCompleter:
    """Verify the completer is wired correctly."""

    def test_completer_creation(self) -> None:
        engine = TclEngine()
        completer = EdaCompleter(engine)
        assert completer.engine is engine

    def test_get_command_completions(self) -> None:
        engine = TclEngine()
        completer = EdaCompleter(engine)
        from prompt_toolkit.document import Document

        doc = Document("get_")
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "get_cells" in names
        assert "get_pins" in names
        assert all(n.startswith("get_") for n in names)

    def test_get_cell_name_completions(self) -> None:
        engine = TclEngine()
        completer = EdaCompleter(engine)
        from prompt_toolkit.document import Document

        doc = Document("get_cells u_ram")
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "u_ram_0" in names
        assert "u_ram_1" in names

    def test_variable_completion(self) -> None:
        engine = TclEngine()
        engine.set_variable("my_cell", "u_uart")
        completer = EdaCompleter(engine)
        from prompt_toolkit.document import Document

        doc = Document("get_cells $my_")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        # Variable name with underscore gets ${...} wrapping
        assert any("my_cell" in t for t in texts)

    def test_no_completions_for_unknown_command(self) -> None:
        engine = TclEngine()
        completer = EdaCompleter(engine)
        from prompt_toolkit.document import Document

        doc = Document("foobar ")
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_flag_completion(self) -> None:
        engine = TclEngine()
        completer = EdaCompleter(engine)
        from prompt_toolkit.document import Document

        doc = Document("get_cells -")
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "-hier" in names
        assert "-filter" in names

    def test_flag_completion_from_registry(self) -> None:
        """Flag completion reads from registry metadata, not hardcoded dict."""
        engine = TclEngine()
        completer = EdaCompleter(engine)
        from prompt_toolkit.document import Document

        # get_pins has -of_objects from registry metadata
        doc = Document("get_pins -")
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "-of_objects" in names

    def test_flag_value_completion_from_registry(self) -> None:
        """Flag value completion reads from registry metadata."""
        engine = TclEngine()
        completer = EdaCompleter(engine)
        from prompt_toolkit.document import Document

        # get_pins -of_objects → completes cell names
        doc = Document("get_pins -of_objects u_")
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "u_cpu_core" in names
        assert "u_ram_0" in names

    def test_report_timing_flag_completion(self) -> None:
        """report_timing flags from registry metadata."""
        engine = TclEngine()
        completer = EdaCompleter(engine)
        from prompt_toolkit.document import Document

        doc = Document("report_timing -")
        completions = list(completer.get_completions(doc, None))
        names = [c.text for c in completions]
        assert "-from" in names
        assert "-to" in names
        assert "-nworst" in names


class TestSpecialCommandRouting:
    """Tests for /command routing in the REPL."""

    @pytest.mark.asyncio
    async def test_help_special_command(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("/help")
        assert code == 0

    @pytest.mark.asyncio
    async def test_clear_special_command(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("/clear")
        assert code == 0

    @pytest.mark.asyncio
    async def test_debug_toggle(self, repl: EdaRepl) -> None:
        initial = repl.verbose
        code = await repl._handle_input("/debug")
        assert code == 0
        assert repl.verbose != initial

    @pytest.mark.asyncio
    async def test_env_special_command(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("/env")
        assert code == 0

    @pytest.mark.asyncio
    async def test_unknown_special_command(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("/nonexistent")
        assert code == 1

    @pytest.mark.asyncio
    async def test_exit_special_command(self, repl: EdaRepl) -> None:
        with pytest.raises(SystemExit):
            await repl._handle_input("/exit")

    @pytest.mark.asyncio
    async def test_special_command_with_args(self, repl: EdaRepl) -> None:
        """Extra args after the /command name are passed through."""
        code = await repl._handle_input("/help xyz")
        assert code == 0

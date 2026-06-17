"""Tests for the EDA REPL dispatch logic."""

from __future__ import annotations

import pytest

from edai.agent.agent import Agent
from edai.tool.tcl.engine import TclEngine
from edai.tool.tcl.repl import EdaRepl


@pytest.fixture
def repl() -> EdaRepl:
    """REPL instance with engine and agent ready for testing."""
    engine = TclEngine()
    agent = Agent(engine)
    return EdaRepl(engine, agent, verbose=False)


class TestHandleInput:
    """Test the input processing logic directly."""

    @pytest.mark.asyncio
    async def test_tcl_command_executes(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("get_cells")  # noqa: SLF001
        assert code == 0

    @pytest.mark.asyncio
    async def test_natural_language_translates(self, repl: EdaRepl) -> None:
        """NL "place all" → translated → executed."""
        code = await repl._handle_input("place all")  # noqa: SLF001
        assert code == 0
        assert repl.engine._placed is True  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_natural_language_routing(self, repl: EdaRepl) -> None:
        repl.engine._placed = True  # noqa: SLF001
        code = await repl._handle_input("route the design")  # noqa: SLF001
        assert code == 0
        assert repl.engine._routed is True  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_unrecognized_nl_returns_error(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("do something completely random")  # noqa: SLF001
        assert code == 1

    @pytest.mark.asyncio
    async def test_empty_input(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("")  # noqa: SLF001
        assert code == 0

    def test_sync_handle_input(self, repl: EdaRepl) -> None:
        """Sync variant works for thread workers."""
        code = repl._handle_input_sync("get_cells")  # noqa: SLF001
        assert code == 0


class TestSpecialCommandRouting:
    """Tests for /command routing in the REPL."""

    @pytest.mark.asyncio
    async def test_help_special_command(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("/help")  # noqa: SLF001
        assert code == 0

    @pytest.mark.asyncio
    async def test_clear_special_command(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("/clear")  # noqa: SLF001
        assert code == 0

    @pytest.mark.asyncio
    async def test_debug_toggle(self, repl: EdaRepl) -> None:
        initial = repl.verbose
        code = await repl._handle_input("/debug")  # noqa: SLF001
        assert code == 0
        assert repl.verbose != initial

    @pytest.mark.asyncio
    async def test_env_special_command(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("/env")  # noqa: SLF001
        assert code == 0

    @pytest.mark.asyncio
    async def test_unknown_special_command(self, repl: EdaRepl) -> None:
        code = await repl._handle_input("/nonexistent")  # noqa: SLF001
        assert code == 1

    @pytest.mark.asyncio
    async def test_exit_special_command(self, repl: EdaRepl) -> None:
        with pytest.raises(SystemExit):
            await repl._handle_input("/exit")  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_special_command_with_args(self, repl: EdaRepl) -> None:
        """Extra args after the /command name are passed through."""
        code = await repl._handle_input("/help xyz")  # noqa: SLF001
        assert code == 0

"""Tests for the mock LLM agent."""

from __future__ import annotations

import pytest

from edai.agent.agent import Agent


@pytest.fixture
def agent() -> Agent:
    """Fresh agent instance per test."""
    return Agent()


class TestTranslation:
    """Natural language → Tcl translation."""

    @pytest.mark.asyncio
    async def test_place_design(self, agent: Agent) -> None:
        agent.delay = 0  # no delay for tests
        result = await agent.translate("please place all the design")
        assert result == "place_design"

    @pytest.mark.asyncio
    async def test_route_design(self, agent: Agent) -> None:
        agent.delay = 0
        result = await agent.translate("run routing for the design")
        assert result == "route_design"

    @pytest.mark.asyncio
    async def test_timing_report(self, agent: Agent) -> None:
        agent.delay = 0
        result = await agent.translate("show me the timing report")
        assert result == "report_timing"

    @pytest.mark.asyncio
    async def test_get_cells(self, agent: Agent) -> None:
        agent.delay = 0
        result = await agent.translate("list cells")
        assert result == "get_cells"

    @pytest.mark.asyncio
    async def test_get_nets(self, agent: Agent) -> None:
        agent.delay = 0
        result = await agent.translate("show nets")
        assert result == "get_nets"

    @pytest.mark.asyncio
    async def test_get_pins(self, agent: Agent) -> None:
        agent.delay = 0
        result = await agent.translate("show pins")
        assert result == "get_pins"

    @pytest.mark.asyncio
    async def test_help_query(self, agent: Agent) -> None:
        agent.delay = 0
        result = await agent.translate("what can you do")
        assert result == "help"

    @pytest.mark.asyncio
    async def test_unrecognized_input(self, agent: Agent) -> None:
        agent.delay = 0
        result = await agent.translate("sing me a song about FPGAs")
        assert result.startswith("#")

    @pytest.mark.asyncio
    async def test_empty_input(self, agent: Agent) -> None:
        agent.delay = 0
        result = await agent.translate("")
        assert result.startswith("#")

    @pytest.mark.asyncio
    async def test_simulated_delay(self, agent: Agent) -> None:
        import time

        agent.delay = 0.1
        start = time.monotonic()
        await agent.translate("place all")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.08  # allow small tolerance

    @pytest.mark.asyncio
    async def test_context_is_ignored_by_mock(self, agent: Agent) -> None:
        """The mock doesn't use context, but should accept it gracefully."""
        agent.delay = 0
        result = await agent.translate(
            "place all",
            context={"placed": False, "routed": False, "cell_count": 6, "net_count": 5},
        )
        assert result == "place_design"


class TestSyncWrapper:
    """Synchronous convenience wrapper."""

    def test_translate_sync(self, agent: Agent) -> None:
        agent.delay = 0
        result = agent.translate_sync("route all")
        assert result == "route_design"

    def test_translate_sync_unknown(self, agent: Agent) -> None:
        agent.delay = 0
        result = agent.translate_sync("do something weird")
        assert result.startswith("#")

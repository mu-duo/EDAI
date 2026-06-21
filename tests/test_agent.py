"""Tests for the mock LLM agent and Message integration."""

from __future__ import annotations

import pytest

from edai.agent.agent import Agent
from edai.core.Message import Message, MessageRole, messages_from_langchain


@pytest.fixture
def agent() -> Agent:
    """Fresh agent instance per test."""
    return Agent()


# ── Translation tests (legacy Agent API) ─────────────────────────────


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


# ── Message integration tests ────────────────────────────────────────


class TestMessageHistory:
    """Agent conversation history is tracked via Message objects."""

    def test_initial_messages_contains_system_prompt(self, agent: Agent) -> None:
        assert len(agent.messages) >= 1
        assert agent.messages[0].role == MessageRole.SYSTEM
        assert "EDA assistant" in agent.messages[0].content

    @pytest.mark.asyncio
    async def test_translate_appends_human_and_ai_messages(self, agent: Agent) -> None:
        agent.delay = 0
        initial_count = len(agent.messages)

        await agent.translate("place the design")

        assert len(agent.messages) == initial_count + 2  # human + ai
        assert agent.messages[-2].role == MessageRole.HUMAN
        assert "place the design" in agent.messages[-2].content
        assert agent.messages[-1].role == MessageRole.AI

    @pytest.mark.asyncio
    async def test_clear_history(self, agent: Agent) -> None:
        agent.delay = 0
        await agent.translate("place all")
        assert len(agent.messages) > 1

        agent.clear_history()
        assert len(agent.messages) == 1
        assert agent.messages[0].role == MessageRole.SYSTEM

    def test_messages_are_read_only_copy(self, agent: Agent) -> None:
        msgs = agent.messages
        msgs.clear()
        # Agent's internal list should be unaffected
        assert len(agent.messages) >= 1


class TestMessageClass:
    """Unit tests for the Message class itself."""

    def test_factory_methods(self) -> None:
        sys_msg = Message.system("system text")
        assert sys_msg.role == MessageRole.SYSTEM
        assert sys_msg.content == "system text"

        human_msg = Message.human("human text")
        assert human_msg.role == MessageRole.HUMAN
        assert human_msg.content == "human text"

        ai_msg = Message.ai("ai text")
        assert ai_msg.role == MessageRole.AI
        assert ai_msg.content == "ai text"

        tool_msg = Message.tool("tool text", tool_call_id="tcl_1")
        assert tool_msg.role == MessageRole.TOOL
        assert tool_msg.content == "tool text"
        assert tool_msg.metadata["tool_call_id"] == "tcl_1"

    def test_langchain_roundtrip(self) -> None:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

        original = Message.system("system content")
        lc = original.to_langchain()
        assert isinstance(lc, SystemMessage)
        assert lc.content == "system content"
        restored = Message.from_langchain(lc)
        assert restored == original

        original = Message.human("human content")
        lc = original.to_langchain()
        assert isinstance(lc, HumanMessage)
        restored = Message.from_langchain(lc)
        assert restored == original

        original = Message.ai("ai content")
        lc = original.to_langchain()
        assert isinstance(lc, AIMessage)
        restored = Message.from_langchain(lc)
        assert restored == original

        original = Message.tool("tool content", tool_call_id="tcl_x")
        lc = original.to_langchain()
        assert isinstance(lc, ToolMessage)
        assert lc.tool_call_id == "tcl_x"
        restored = Message.from_langchain(lc)
        assert restored == original

    def test_dict_roundtrip(self) -> None:
        original = Message.ai("hello", extra="value")
        data = original.to_dict()
        assert data["role"] == "ai"
        assert data["content"] == "hello"
        assert data["metadata"]["extra"] == "value"

        restored = Message.from_dict(data)
        assert restored == original

    def test_equality(self) -> None:
        a = Message.human("hello")
        b = Message.human("hello")
        c = Message.human("world")
        assert a == b
        assert a != c

    def test_repr(self) -> None:
        msg = Message.human("test")
        assert "human" in repr(msg)
        assert "test" in repr(msg)

    def test_to_markup(self) -> None:
        msg = Message.human("hello")
        markup = msg.to_markup()
        assert "User" in markup
        assert "hello" in markup

    def test_role_setter(self) -> None:
        msg = Message.human("content")
        assert msg.role == MessageRole.HUMAN
        msg.role = "ai"
        assert msg.role == MessageRole.AI
        msg.role = MessageRole.TOOL
        assert msg.role == MessageRole.TOOL

    def test_content_setter(self) -> None:
        msg = Message.human("old")
        msg.content = "new"
        assert msg.content == "new"

    def test_metadata_mutable(self) -> None:
        msg = Message.human("hello")
        msg.metadata["key"] = "value"
        assert msg.metadata["key"] == "value"


class TestMessageHelpers:
    """Tests for the module-level helper functions."""

    def test_messages_to_langchain(self) -> None:
        from edai.core.Message import messages_to_langchain

        msgs = [Message.system("sys"), Message.human("usr")]
        lc = messages_to_langchain(msgs)
        assert len(lc) == 2
        assert lc[0].content == "sys"
        assert lc[1].content == "usr"

    def test_messages_from_langchain(self) -> None:
        from edai.core.Message import messages_from_langchain
        from langchain_core.messages import HumanMessage, SystemMessage

        lc = [SystemMessage(content="sys"), HumanMessage(content="usr")]
        msgs = messages_from_langchain(lc)
        assert len(msgs) == 2
        assert msgs[0].role == MessageRole.SYSTEM
        assert msgs[1].role == MessageRole.HUMAN

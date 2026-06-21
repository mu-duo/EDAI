"""Tests for Message-based agent dispatch and UI-level integration.

Since the Textual TUI cannot run in a headless test environment, this
module tests the core dispatch and Message-tracking logic that the UI
depends on.
"""

from __future__ import annotations

import pytest

from edai.agent.agent import Agent
from edai.core.Message import Message, MessageRole


# ── Agent dispatch (used by the UI's _dispatch and _sync_translate) ──


class TestAgentDispatch:
    """The UI depends on Agent.translate() for NL→Tcl dispatch."""

    def test_agent_importable(self) -> None:
        """Agent class must be importable (UI imports via EdaiAgent)."""
        from edai.agent import Agent

        assert Agent is not None

    @pytest.mark.asyncio
    async def test_agent_translate_returns_string(self) -> None:
        agent = Agent()
        agent.delay = 0
        result = await agent.translate("place all")
        assert isinstance(result, str)
        assert result == "place_design"

    @pytest.mark.asyncio
    async def test_agent_preserves_conversation(self) -> None:
        """After translate(), agent.messages should contain Message objects."""
        agent = Agent()
        agent.delay = 0
        await agent.translate("list cells")

        msgs = agent.messages
        assert all(isinstance(m, Message) for m in msgs)

        # Find the human message
        human_msgs = [m for m in msgs if m.role == MessageRole.HUMAN]
        assert len(human_msgs) == 1
        assert human_msgs[0].content == "list cells"

        # Find the AI response
        ai_msgs = [m for m in msgs if m.role == MessageRole.AI]
        assert len(ai_msgs) == 1
        assert "get_cells" in ai_msgs[0].content


class TestConversationHistory:
    """Tests for conversation tracking with Message objects."""

    def test_conversation_initial_state(self) -> None:
        """Agent starts with a system message."""
        agent = Agent()
        assert len(agent.messages) >= 1
        assert agent.messages[0].role == MessageRole.SYSTEM

    @pytest.mark.asyncio
    async def test_multiple_turns(self) -> None:
        """Multiple translations accumulate in the conversation."""
        agent = Agent()
        agent.delay = 0

        await agent.translate("list cells")
        await agent.translate("show nets")
        await agent.translate("help")

        human_msgs = [m for m in agent.messages if m.role == MessageRole.HUMAN]
        assert len(human_msgs) == 3
        assert human_msgs[0].content == "list cells"
        assert human_msgs[1].content == "show nets"
        assert human_msgs[2].content == "help"

    @pytest.mark.asyncio
    async def test_clear_resets_conversation(self) -> None:
        agent = Agent()
        agent.delay = 0
        await agent.translate("place all")
        assert len(agent.messages) > 1

        agent.clear_history()
        assert len(agent.messages) == 1
        assert agent.messages[0].role == MessageRole.SYSTEM


class TestMessageLangchainConversion:
    """The agent uses Message ↔ langchain conversion internally."""

    def test_human_message_to_langchain(self) -> None:
        msg = Message.human("test input")
        lc = msg.to_langchain()
        from langchain_core.messages import HumanMessage

        assert isinstance(lc, HumanMessage)
        assert lc.content == "test input"

    def test_ai_message_from_langchain(self) -> None:
        from langchain_core.messages import AIMessage

        lc = AIMessage(content="response text")
        msg = Message.from_langchain(lc)
        assert msg.role == MessageRole.AI
        assert msg.content == "response text"

    def test_tool_message_roundtrip(self) -> None:
        from langchain_core.messages import ToolMessage

        lc = ToolMessage(content="tool output", tool_call_id="tcl_42")
        msg = Message.from_langchain(lc)
        assert msg.role == MessageRole.TOOL
        assert msg.content == "tool output"
        assert msg.metadata["tool_call_id"] == "tcl_42"

        back = msg.to_langchain()
        assert isinstance(back, ToolMessage)
        assert back.tool_call_id == "tcl_42"

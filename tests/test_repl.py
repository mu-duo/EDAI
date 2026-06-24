"""Tests for Message-based agent dispatch and UI-level integration.

Since the Textual TUI cannot run in a headless test environment, this
module tests the core dispatch and Message-tracking logic that the UI
depends on.
"""

from __future__ import annotations

import pytest

from edai.core.Message import Message, MessageRole


# ── Agent dispatch (used by the UI's _dispatch and _sync_translate) ──


class TestAgentDispatch:
    """The UI depends on Agent being importable."""

    def test_agent_importable(self) -> None:
        from edai.agent import Agent

        assert Agent is not None


class TestConversationHistory:
    """Tests for conversation tracking with Message objects."""

    def test_conversation_initial_state(self) -> None:
        from edai.agent import Agent
        from edai.core.mock_repl import MockTclRepl

        agent = Agent(backend=MockTclRepl())
        assert agent.messages == []
        assert agent.delay == 0.0

    def test_clear_history(self) -> None:
        from edai.agent import Agent
        from edai.core.mock_repl import MockTclRepl

        agent = Agent(backend=MockTclRepl())
        agent.clear_history()
        assert agent.messages == []


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

"""Tests for Agent construction and Message integration."""

from __future__ import annotations

from edai.core.Message import Message, MessageRole, messages_from_langchain


# ── Agent construction tests ───────────────────────────────────────────


class TestAgentConstruction:
    """Agent class must be constructable with a mock backend."""

    def test_agent_importable(self) -> None:
        from edai.agent import Agent

        assert Agent is not None

    def test_agent_construct_with_mock_backend(self) -> None:
        from edai.agent import Agent
        from edai.core.mock_repl import MockTclRepl

        agent = Agent(backend=MockTclRepl(), role="EDAI")
        assert agent.backend is not None
        assert agent._role == "EDAI"
        assert agent.graph is not None

    def test_agent_backend_type_detected(self) -> None:
        from edai.agent import Agent
        from edai.core.mock_repl import MockTclRepl

        agent = Agent(backend=MockTclRepl())
        bt = getattr(agent.backend, "backend_type", "")
        assert bt == "mock"

    def test_agent_backward_compat_aliases(self) -> None:
        from edai.agent import Agent
        from edai.core.mock_repl import MockTclRepl

        agent = Agent(backend=MockTclRepl())
        # These should not raise
        assert agent.messages == []
        assert agent.delay == 0.0
        agent.delay = 99
        assert agent.delay == 0.0  # setter is no-op
        agent.clear_history()  # should not raise


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

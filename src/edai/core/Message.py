"""Core message class for EDAI — unifies LLM, tool, and user-cmd message handling.

The :class:`Message` class is the canonical representation of all messages
flowing through the system:

* **User commands** — natural-language or Tcl input from the user
* **LLM messages** — system prompts, AI responses
* **Tool messages** — output from EDA tool execution

It wraps ``langchain_core.messages.BaseMessage`` with EDAI-specific factory
methods and bidirectional conversion, so agents and UI code can work with a
single message type and convert to/from langchain only at the LLM boundary.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


class MessageRole(str, Enum):
    """Role identifiers for every message in the system."""

    SYSTEM = "system"
    """System-level instructions or role descriptions."""
    HUMAN = "human"
    """End-user input (natural language or raw Tcl)."""
    AI = "ai"
    """LLM-generated response."""
    TOOL = "tool"
    """Output from an EDA tool or other external execution."""


# ── public helpers for langgraph's add_messages reducer ──────────────

# add_messages expects BaseMessage subclasses.
# Rather than patching langgraph internals, Message is kept as a pure
# domain object and the agent graph state uses langchain messages.
# The helpers below streamline that conversion.

def messages_to_langchain(messages: list[Message]) -> list[BaseMessage]:
    """Convert a list of :class:`Message` to langchain :class:`BaseMessage`."""
    return [m.to_langchain() for m in messages]


def messages_from_langchain(
    lc_messages: list[BaseMessage],
) -> list[Message]:
    """Convert a list of langchain :class:`BaseMessage` to :class:`Message`."""
    return [Message.from_langchain(m) for m in lc_messages]


# ── the Message class ────────────────────────────────────────────────


class Message:
    """Canonical message in the EDAI system.

    Use the factory classmethods to create instances::

        msg = Message.system("You are an EDA assistant.")
        msg = Message.human("place the design")
        msg = Message.ai("Running: place_design")
        msg = Message.tool("Placement completed.", tool_call_id="tcl_1")

    Convert to/from langchain when talking to the LLM::

        lc_msg = msg.to_langchain()
        msg = Message.from_langchain(lc_msg)

    Parameters
    ----------
    role:
        Message role (system, human, ai, tool).
    content:
        The text payload.
    metadata:
        Optional key-value pairs for routing info, timestamps, etc.

    """

    def __init__(
        self,
        role: MessageRole | str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._role = MessageRole(role) if isinstance(role, str) else role
        self._content = content
        self._metadata = metadata or {}

    # ── properties ─────────────────────────────────────────────────

    @property
    def role(self) -> MessageRole:
        """Message role."""
        return self._role

    @role.setter
    def role(self, value: MessageRole | str) -> None:
        self._role = MessageRole(value) if isinstance(value, str) else value

    @property
    def content(self) -> str:
        """Text payload."""
        return self._content

    @content.setter
    def content(self, value: str) -> None:
        self._content = value

    @property
    def metadata(self) -> dict[str, Any]:
        """Mutable metadata dict (routing, timestamps, etc.)."""
        return self._metadata

    # ── factory methods ────────────────────────────────────---------

    @classmethod
    def system(cls, content: str, **metadata: Any) -> Message:
        """Create a system message."""
        return cls(MessageRole.SYSTEM, content, metadata)

    @classmethod
    def human(cls, content: str, **metadata: Any) -> Message:
        """Create a human (user) message."""
        return cls(MessageRole.HUMAN, content, metadata)

    @classmethod
    def ai(cls, content: str, **metadata: Any) -> Message:
        """Create an AI (assistant) message."""
        return cls(MessageRole.AI, content, metadata)

    @classmethod
    def tool(
        cls, content: str, tool_call_id: str = "tcl_exec", **metadata: Any
    ) -> Message:
        """Create a tool message.

        Parameters
        ----------
        content:
            Tool execution output.
        tool_call_id:
            Identifier linking this result to the tool invocation.
        **metadata:
            Extra metadata attached to the message.

        """
        m = cls(MessageRole.TOOL, content, metadata)
        m._metadata["tool_call_id"] = tool_call_id
        return m

    # ── langchain bridge ───────────────────────────────────────────

    def to_langchain(self) -> BaseMessage:
        """Convert to a langchain ``BaseMessage``.

        The returned object is one of ``SystemMessage``, ``HumanMessage``,
        ``AIMessage``, or ``ToolMessage`` depending on the role.
        """
        raw: BaseMessage
        if self._role == MessageRole.SYSTEM:
            raw = SystemMessage(content=self._content)
        elif self._role == MessageRole.HUMAN:
            raw = HumanMessage(content=self._content)
        elif self._role == MessageRole.AI:
            raw = AIMessage(content=self._content)
        elif self._role == MessageRole.TOOL:
            raw = ToolMessage(
                content=self._content,
                tool_call_id=self._metadata.get("tool_call_id", "tcl_exec"),
            )
        else:
            # fallback — treat unknown roles as human
            raw = HumanMessage(content=self._content)
        return raw

    @classmethod
    def from_langchain(cls, msg: BaseMessage) -> Message:
        """Create a :class:`Message` from a langchain ``BaseMessage``."""
        content = str(msg.content)
        if isinstance(msg, SystemMessage):
            return cls.system(content)
        if isinstance(msg, HumanMessage):
            return cls.human(content)
        if isinstance(msg, AIMessage):
            return cls.ai(content)
        if isinstance(msg, ToolMessage):
            return cls.tool(content, tool_call_id=msg.tool_call_id)
        # fallback
        return cls.human(content)

    # ── serialization ──────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-compatible dict."""
        return {
            "role": self._role.value,
            "content": self._content,
            "metadata": dict(self._metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Deserialize from a dict (reverse of :meth:`to_dict`)."""
        return cls(
            role=data["role"],
            content=data["content"],
            metadata=data.get("metadata"),
        )

    # ── display helpers ────────────────────────────────────────────

    def to_markup(self) -> str:
        """Return a rich-markup string for the UI."""
        prefix = {
            MessageRole.SYSTEM: "[dim]╭─ System[/]",
            MessageRole.HUMAN: "[bold cyan]╰─ User[/]",
            MessageRole.AI: "[bold green]╭─ Agent[/]",
            MessageRole.TOOL: "[bold yellow]╭─ Tool[/]",
        }.get(self._role, "[bold]╭─ Message[/]")
        return f"{prefix} {self._content}"

    def __repr__(self) -> str:
        return f"Message({self._role.value}, content={self._content!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            return NotImplemented
        return (
            self._role == other._role
            and self._content == other._content
            and self._metadata == other._metadata
        )

    def __hash__(self) -> int:
        return hash((self._role, self._content))

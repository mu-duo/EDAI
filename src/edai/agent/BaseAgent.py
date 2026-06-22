"""Base agent with Message-based conversation management.

All agents in the system extend :class:`BaseAgent`, which maintains a
conversation history as ``list[Message]`` and converts to/from langchain
message types only at the LLM invocation boundary.
"""

from __future__ import annotations

import os
from typing import Any

import rich
from langchain_deepseek import ChatDeepSeek

from edai.core.Message import Message, messages_to_langchain


class BaseAgent:
    """Foundation agent with message history management.

    Parameters
    ----------
    model_name:
        LLM model identifier.  Falls back to ``LLM_MODEL`` env var.
    api_key:
        API key.  Falls back to ``LLM_API_KEY`` env var.

    """

    def __init__(self, model_name: str = "", api_key: str = "") -> None:
        if not model_name:
            model_name = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
        if not api_key:
            api_key = os.environ.get("LLM_API_KEY", "")

        if not api_key:
            raise ValueError("LLM_API_KEY is not set in environment variables.")

        self.model = ChatDeepSeek(
            model=model_name,
            temperature=0.9,
            api_key=api_key,
        )

        # Internal message history — always list[Message]
        self._messages: list[Message] = [
            Message.system(
                "You are an EDA assistant that translates natural language "
                "into Tcl commands."
            ),
        ]

    # ── message-history accessors ──────────────────────────────────

    @property
    def messages(self) -> list[Message]:
        """Read-only view of the conversation history."""
        return list(self._messages)

    def add_message(self, msg: Message) -> None:
        """Append a *Message* to the history."""
        self._messages.append(msg)

    def clear_history(self) -> None:
        """Clear all messages except the initial system prompt."""
        self._messages = [self._messages[0]]

    # ── LLM invocation ─────────────────────────────────────────────

    def invoke(self, text: str) -> str:
        """Send a user text to the LLM and return the response content.

        Internally converts the conversation history to langchain
        messages, calls the LLM, converts the result back, and
        appends both the user message and the response to history.

        Parameters
        ----------
        text:
            User input (natural language or Tcl command).

        Returns
        -------
        str
            The response content from the LLM.

        """
        user_msg = Message.human(text)
        self._messages.append(user_msg)

        lc_messages = messages_to_langchain(self._messages)
        response = self.model.invoke(lc_messages)

        # Extract content from the AIMessage response
        content = _extract_content(response)
        ai_msg = Message.ai(content)
        self._messages.append(ai_msg)

        return content

    # ── role description ───────────────────────────────────────────

    def read_role_description(self, file_path: str) -> str:
        """Read a role description from *file_path* and add it as a system message.

        Parameters
        ----------
        file_path:
            Path to a text file containing the role/system prompt.

        Returns
        -------
        str
            Status message.

        """
        try:
            with open(file_path, encoding="utf-8") as f:
                self._messages.append(Message.system(f.read()))
            return f"Role description loaded from {file_path}."
        except FileNotFoundError:
            rich.print(f"[red]Role description file not found: {file_path}[/red]")
            return ""
        except Exception as e:
            rich.print(
                f"[red]Error reading role description from {file_path}: {e}[/red]"
            )
            return ""


# ── extraction helpers ───────────────────────────────────────────────


def _extract_content(response: Any) -> str:
    """Extract a string from whatever the LLM returns.

    Handles ``AIMessage``, plain strings, and compound content lists.
    """
    content = response.content if hasattr(response, "content") else str(response)

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        # e.g. [{"text": "..."}, ...] or ["..."]
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", str(item)))
            else:
                parts.append(str(item))
        return "\n".join(parts).strip()
    return str(content).strip()

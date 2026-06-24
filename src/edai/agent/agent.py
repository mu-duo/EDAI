"""ReAct agent for NL → backend-command translation.

The :class:`Agent` builds a LangGraph ReAct loop around any backend that
satisfies the ``send_command(code: str) -> str`` protocol (``MockTclRepl``,
``EDAInteractive``, ``PythonInteractive``, etc.).

Role & backend descriptions are loaded from ``roles/agents/{role}.md`` and
``roles/backends/{type}.md`` files — no hardcoded system prompts.
"""

from __future__ import annotations

import importlib.resources
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any

from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.prebuilt import create_react_agent

from edai.agent.config import AgentConfig
from edai.core.Message import Message


# ── role / backend doc helpers ─────────────────────────────────────────


def _load_md(package: str, *path_segments: str) -> str:
    """Read a markdown file from the package's resources.

    Returns an empty string if the file does not exist.
    """
    try:
        return importlib.resources.files(package).joinpath(
            *path_segments
        ).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        return ""


# ── the Agent ──────────────────────────────────────────────────────────


class Agent:
    """ReAct agent for EDA / Python backends.

    Parameters
    ----------
    backend:
        Any object that satisfies ``send_command(code: str) -> str``.
        Must expose a ``backend_type`` class attribute (``"mock"``,
        ``"tclsh"``, ``"python"``, …) used to load the capabilities doc.
    role:
        Agent role name.  Loads ``roles/agents/{role}.md`` as the
        system prompt.
    model:
        LLM model identifier.  Falls back to ``LLM_MODEL`` env var,
        then ``"deepseek-v4-flash"``.
    max_iterations:
        Maximum ReAct loop iterations before giving up.

    Usage::

        from edai.agent import Agent
        from edai.core.mock_repl import MockTclRepl

        agent = Agent(backend=MockTclRepl(), role="EDAI")
        result = await agent.run("list all cells")
    """

    def __init__(
        self,
        backend: Any,
        role: str = "EDAI",
        *,
        model: str = "",
        max_iterations: int = 10,
    ) -> None:
        self.backend = backend
        self._role = role
        self._config = AgentConfig(
            model=model or os.environ.get("LLM_MODEL", "deepseek-v4-flash"),
            max_iterations=max_iterations,
        )
        self.graph: Any = self._build_graph()

    # ── prompt construction ─────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Combine agent role + backend capabilities into one system prompt."""
        parts: list[str] = []

        # Agent role doc
        role_md = _load_md("edai.roles", "agents", f"{self._role}.md")
        if role_md:
            parts.append(role_md)

        # Backend capabilities doc
        bt = getattr(self.backend, "backend_type", "tclsh")
        backend_md = _load_md("edai.roles", "backends", f"{bt}.md")
        if backend_md:
            parts.append("\n## Available Backend\n")
            parts.append(backend_md)

        return "\n\n".join(parts)

    # ── graph construction ──────────────────────────────────────────

    def _build_graph(self) -> Any:
        """Build a ReAct graph: LLM + single ``execute`` tool."""
        raw_key = os.environ.get("LLM_API_KEY", "")
        if not raw_key:
            raw_key = os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = os.environ.get(
            "LLM_BASE_URL", "https://api.deepseek.com/v1"
        )

        llm = ChatDeepSeek(
            model=self._config.model,
            temperature=0.1,
            api_key=raw_key,  # type: ignore[arg-type]
            base_url=base_url,
        )

        backend = self.backend

        @tool
        def execute(command: str) -> str:
            """Send a command to the backend and return the result.

            Use this tool to run any backend command.
            The available commands depend on the connected backend.
            """
            return backend.send_command(command)

        system_prompt = self._build_system_prompt()
        return create_react_agent(llm, [execute], prompt=system_prompt, version="v2")

    # ── public API ──────────────────────────────────────────────────

    async def run(self, text: str) -> str:
        """Process *text* through the ReAct graph and return the final answer."""
        from langchain_core.messages import HumanMessage

        state = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=text)]},
            {"recursion_limit": self._config.max_iterations + 1},
        )
        messages = state.get("messages", [])
        return str(messages[-1].content) if messages else ""

    def run_sync(self, text: str) -> str:
        """Synchronous wrapper for :meth:`run`."""
        import asyncio

        return asyncio.run(self.run(text))

    # ── streaming ───────────────────────────────────────────────────

    async def run_stream(self, text: str) -> AsyncGenerator[tuple[str, str], None]:
        """Async generator yielding ``(type, content)`` events.

        Event types
        -----------
        ``"tool_call"``
            Agent is about to call a tool.
        ``"tool_result"``
            Output returned from tool execution.
        ``"token"``
            A chunk of agent response text.
        ``"error"``
            An error occurred.
        ``"done"``
            Streaming complete.
        """
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

        seen_count = 0

        try:
            async for state in self.graph.astream(
                {"messages": [HumanMessage(content=text)]},
                {"recursion_limit": self._config.max_iterations + 1},
            ):
                for _node_name, snapshot in state.items():
                    step_msgs = snapshot.get("messages", [])
                    for i in range(seen_count, len(step_msgs)):
                        msg = step_msgs[i]

                        if isinstance(msg, ToolMessage):
                            yield ("tool_result", str(msg.content))
                        elif isinstance(msg, AIMessage):
                            tool_calls = getattr(msg, "tool_calls", [])
                            if tool_calls:
                                for tc in tool_calls:
                                    name = tc.get("name", "execute")
                                    yield ("tool_call", name)
                            content = str(msg.content) if msg.content else ""
                            if content:
                                yield ("token", content)

                    seen_count = len(step_msgs)

        except Exception as exc:  # noqa: BLE001
            yield ("error", str(exc))

        yield ("done", "")

    def run_stream_sync(
        self, text: str
    ) -> Generator[tuple[str, str], None, None]:
        """Synchronous wrapper for :meth:`run_stream`."""
        import asyncio

        gen = self.run_stream(text)
        while True:
            try:
                val: tuple[str, str] = asyncio.run(gen.asend(None))  # type: ignore[func-returns-value]
                yield val
            except StopAsyncIteration:
                break

    # ── backward-compat aliases ─────────────────────────────────────

    async def translate(self, text: str) -> str:
        """Alias for :meth:`run`."""
        return await self.run(text)

    def translate_sync(self, text: str) -> str:
        """Alias for :meth:`run_sync`."""
        return self.run_sync(text)

    @property
    def messages(self) -> list[Message]:
        """Backward-compat: return empty list (state lives in the graph)."""
        return []

    def clear_history(self) -> None:
        """Backward-compat no-op."""

    @property
    def delay(self) -> float:
        """Backward-compat: always 0 (no mock mode)."""
        return 0.0

    @delay.setter
    def delay(self, value: float) -> None:
        """Backward-compat no-op."""

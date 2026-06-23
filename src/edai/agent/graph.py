"""LangGraph-based agent for natural-language → Tcl translation.

Two modes
---------
* ``config.model == "mock"`` — legacy keyword-matching graph (backward compat)
* ``config.model != "mock"`` — proper ReAct agent via ``create_react_agent``
  with ``ChatDeepSeek`` + a Tcl execution tool.

In ReAct mode the agent decides when to call the Tcl tool, so the caller
does not need to parse ``[tcl command]`` markers — the tool call loop is
handled internally by LangGraph.

Message handling
----------------
The graph state uses **langchain ``BaseMessage``** objects because
langgraph's ``add_messages`` reducer expects them.  The
:class:`~edai.core.Message.Message` domain class is used for construction
and is converted to langchain form at node boundaries via
:func:`~edai.core.Message.messages_to_langchain`.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Annotated, Any, TypedDict

from langchain.tools import BaseTool, tool
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.prebuilt import create_react_agent

from edai.agent.config import AgentConfig
from edai.core.Message import Message

# ── keyword → Tcl command mapping (shared with the mock agent) ──────

_TRANSLATIONS: list[tuple[list[str], str]] = [
    (
        ["place all", "place design", "run placement", "place the design"],
        "place_design",
    ),
    (
        ["route all", "route design", "run routing", "route the design"],
        "route_design",
    ),
    (["timing", "report timing", "show timing"], "report_timing"),
    (["get cells", "list cells", "show cells", "what cells"], "get_cells"),
    (["get nets", "list nets", "show nets"], "get_nets"),
    (["get pins", "list pins", "show pins", "what pins"], "get_pins"),
    (["help", "what can you do", "commands", "?"], "help"),
]


# ── state (mock graph only) ──────────────────────────────────────────


class AgentState(TypedDict):
    """State flowing through the mock LangGraph agent.

    ``messages`` uses the ``add_messages`` reducer so new messages are
    appended (not overwritten) on every node update.  Items are langchain
    ``BaseMessage`` subclasses — the domain ``Message`` type is converted
    at the node boundary.
    """

    messages: Annotated[list, add_messages]
    tcl_command: str
    engine_result: str


# ── the agent ───────────────────────────────────────────────────────


class LangGraphAgent:
    """Natural-language → Tcl translator backed by a LangGraph state graph.

    Parameters
    ----------
    config:
        Agent configuration.  When ``config.model == "mock"`` a simple
        keyword-matching graph is used; otherwise a full ReAct agent with
        ``ChatDeepSeek`` and a Tcl execution tool is built.
    backend:
        Any object that satisfies the ``send_command(code: str) -> str``
        protocol (e.g. ``MockTclRepl`` or ``EDAInteractive``).  Passed as
        the tool execution target in both modes.

    Usage::

        agent = LangGraphAgent(AgentConfig(), backend=my_backend)
        result = await agent.run("place the design")  # async
        result = agent.run_sync("place the design")   # blocking

    """

    def __init__(
        self,
        config: AgentConfig,
        backend: Any = None,
    ) -> None:
        self.config = config
        self.backend = backend
        self.graph: Any = self._build_graph()

    # ── graph construction ────────────────────────────────────────

    def _build_graph(self) -> Any:
        """Return the appropriate graph for the current config mode."""
        if self.config.model == "mock":
            return self._build_mock_graph()
        return self._build_react_graph()

    # ── mock graph (keyword matching, no LLM) ─────────────────────

    def _build_mock_graph(self) -> Any:
        builder = StateGraph(AgentState)

        builder.add_node("agent", self._agent_node_mock)
        builder.add_node("tools", self._tools_node_mock)

        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            self._router_mock,
            {"tools": "tools", END: END},
        )
        builder.add_edge("tools", "agent")

        return builder.compile()

    async def _agent_node_mock(self, state: AgentState) -> dict:
        """Mock LLM: translate user input, or summarize after tool execution."""
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

        if self.config.delay > 0:
            await asyncio.sleep(self.config.delay)

        last_msg = state["messages"][-1] if state["messages"] else None

        # After tool execution: produce a final summary and stop the loop
        if isinstance(last_msg, ToolMessage):
            result = state.get("engine_result", "Done.")
            reply = AIMessage(content=f"Result: {result}")
            return {"messages": [reply], "tcl_command": "# done"}

        # Fresh user input: translate natural language → Tcl
        user_text = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                content = msg.content
                user_text = content if isinstance(content, str) else str(content)
                break

        tcl = self._mock_translate(user_text)

        reply = AIMessage(content=f"Running: {tcl}")
        return {"messages": [reply], "tcl_command": tcl}

    def _tools_node_mock(self, state: AgentState) -> dict:
        """Execute the Tcl command via the backend (if available)."""
        from langchain_core.messages import ToolMessage

        tcl = state.get("tcl_command", "")
        result = "No backend available."

        if self.backend is not None:
            try:
                result = self.backend.send_command(tcl)
            except Exception as exc:  # noqa: BLE001
                result = f"ERROR: {exc}"

        return {
            "messages": [ToolMessage(content=result, tool_call_id="tcl_exec")],
            "engine_result": result,
            "tcl_command": "",
        }

    def _router_mock(self, state: AgentState) -> str:
        """Decide: execute the Tcl command or stop."""
        tcl = state.get("tcl_command", "")
        if tcl and not tcl.startswith("#"):
            return "tools"
        return END  # type: ignore[return-value]

    # ── ReAct graph (real LLM + Tcl tool, using create_react_agent) ──

    def _build_react_graph(self) -> Any:
        """Build a full ReAct agent with ``ChatDeepSeek`` + Tcl tool."""
        model_name = self.config.model
        raw_key = os.environ.get("LLM_API_KEY", "")
        if not raw_key:
            raw_key = os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")

        llm = ChatDeepSeek(
            model=model_name,
            temperature=0.1,
            api_key=raw_key,  # type: ignore[arg-type]
            base_url=base_url,
        )

        tools: list[BaseTool] = []
        if self.backend is not None:
            backend = self.backend

            @tool
            def tcl_command(code: str) -> str:
                """Execute a Tcl command in the EDA tool and return the result.

                Use this tool when you need to run any Tcl command such as
                ``get_cells``, ``report_timing``, ``place_design``, etc.
                """
                return backend.send_command(code)

            tools.append(tcl_command)

        # Bind tools so the LLM knows it can call them, then wrap in the
        # prebuilt ReAct loop (model → tool → model → …).
        llm_with_tools = llm.bind_tools(tools)
        return create_react_agent(
            llm_with_tools,
            tools,
            prompt=self.config.system_prompt,
            version="v2",
        )

    # ── mock translation ──────────────────────────────────────────

    @staticmethod
    def _mock_translate(text: str) -> str:
        """Run keyword match (same logic as the legacy ``Agent``)."""
        text_lower = text.lower().strip()
        for keywords, tcl_cmd in _TRANSLATIONS:
            if any(kw in text_lower for kw in keywords):
                return tcl_cmd
        return f"# (unrecognized) {text.strip()}"

    # ── public API ─────────────────────────────────────────────────

    async def run(self, text: str, *, context: dict | str | None = None) -> str:  # noqa: ARG002
        """Process *text* through the graph and return the final response.

        In mock mode the return value is the engine result (or a comment for
        unrecognised input).  In ReAct mode the return value is the final
        AI message content after the tool-calling loop completes.
        """
        from langchain_core.messages import HumanMessage

        state = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=text)]},
            {"recursion_limit": self.config.max_iterations + 1},
        )

        # Mock mode uses custom state keys
        if self.config.model == "mock":
            engine_result: str = state.get("engine_result", "")
            if not engine_result:
                tcl_cmd: str = state.get("tcl_command", "")
                return tcl_cmd or engine_result
            return engine_result

        # ReAct mode: the last message in the state is the final answer
        messages = state.get("messages", [])
        if messages:
            return str(messages[-1].content)
        return ""

    def run_sync(self, text: str, *, context: dict | str | None = None) -> str:
        """Wrap :meth:`run` as a synchronous, blocking call."""
        return asyncio.run(self.run(text, context=context))

    # ── streaming ─────────────────────────────────────────────────

    async def run_stream(
        self,
        text: str,
        *,
        context: dict | str | None = None,  # noqa: ARG002
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Async generator yielding ``(type, content)`` for streaming display.

        Used by the TUI to show agent output progressively.

        Types
        -----
        ``"token"``
            A chunk of agent response text.  Concatenate to build the
            full response.
        ``"tool_call"``
            The agent is about to call a tool (content is the tool name).
        ``"tool_result"``
            Output returned from a tool execution.
        ``"error"``
            An error occurred (content is the error message).
        ``"done"``
            Streaming is complete (content is empty).

        Mock mode
        ---------
        Yields a single ``("token", result)`` followed by ``("done", "")``.
        """
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

        if self.config.model == "mock":
            result = await self.run(text)
            yield ("token", result)
            yield ("done", "")
            return

        seen_count = 0

        try:
            async for state in self.graph.astream(
                {"messages": [HumanMessage(content=text)]},
                {"recursion_limit": self.config.max_iterations + 1},
            ):
                # state is {node_name: state_snapshot}
                for _node_name, snapshot in state.items():
                    step_msgs = snapshot.get("messages", [])
                    for i in range(seen_count, len(step_msgs)):
                        msg = step_msgs[i]

                        if isinstance(msg, ToolMessage):
                            yield ("tool_result", str(msg.content))
                        elif isinstance(msg, AIMessage):
                            # Check for tool calls the LLM wants to make
                            tool_calls = getattr(msg, "tool_calls", [])
                            if tool_calls:
                                for tc in tool_calls:
                                    name = tc.get("name", "tcl_command")
                                    yield ("tool_call", name)
                            # Stream any text content from the AI message
                            content = str(msg.content) if msg.content else ""
                            if content:
                                yield ("token", content)

                    seen_count = len(step_msgs)

        except Exception as exc:  # noqa: BLE001
            yield ("error", str(exc))

        yield ("done", "")

    def run_stream_sync(
        self,
        text: str,
        *,
        context: dict | str | None = None,
    ) -> Generator[tuple[str, str], None, None]:
        """Wrap :meth:`run_stream` as a synchronous generator.

        Yields ``(type, content)`` tuples.  Runs the async generator in
        an event loop created for this call (same pattern as ``run_sync``).
        """
        gen = self.run_stream(text, context=context)
        while True:
            try:
                # Advance the async generator one step using asyncio.run
                val: tuple[str, str] = asyncio.run(gen.asend(None))  # type: ignore[func-returns-value]
                yield val
            except StopAsyncIteration:
                break

    # ── compatibility aliases (drop-in for legacy Agent) ──────────

    async def translate(self, text: str, *, context: dict | str | None = None) -> str:
        """Alias for :meth:`run` — compatible with ``Agent.translate()``."""
        return await self.run(text, context=context)

    def translate_sync(self, text: str, *, context: dict | str | None = None) -> str:
        """Alias for :meth:`run_sync`."""
        return self.run_sync(text, context=context)

    # ── conversation access (compatible with EdaiAgent / BaseAgent) ──

    @property
    def messages(self) -> list[Message]:
        """Return an empty list — ReAct state is not stored as Message objects yet.

        This property exists for API compatibility with ``BaseAgent``.
        Conversation history is managed inside the LangGraph checkpoint
        in future iterations.
        """
        return []

    def clear_history(self) -> None:
        """No-op for API compatibility with ``BaseAgent``."""
        # Future: reset graph checkpoint when we add checkpointer support.

    # ── simulated delay ───────────────────────────────────────────

    @property
    def delay(self) -> float:
        """Simulated latency in seconds (mock mode only)."""
        return self.config.delay

    @delay.setter
    def delay(self, value: float) -> None:
        self.config.delay = max(0.0, value)

    # ── Message helpers ───────────────────────────────────────────

    def build_human_message(self, text: str) -> Any:
        """Build a langchain ``HumanMessage`` from *text* via the domain type.

        Example::

            msg = agent.build_human_message("place the design")
            state = await agent.graph.ainvoke({"messages": [msg]})
        """
        return Message.human(text).to_langchain()

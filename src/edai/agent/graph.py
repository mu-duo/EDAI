"""LangGraph-based agent for natural-language → Tcl translation.

Minimal prototype — three nodes connected in a loop::

    START → agent → [router] ─→ tools ─→ agent
                      └──→ END

``agent`` translates user input into a Tcl command (mock keyword match).
``tools`` executes the Tcl via ``TclEngine`` and feeds results back.
``router`` decides whether to call a tool or stop.

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
from typing import TYPE_CHECKING, Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph, add_messages

from edai.agent.config import AgentConfig
from edai.core.Message import Message

if TYPE_CHECKING:
    from edai.tool.tcl.engine import TclEngine

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


# ── state ───────────────────────────────────────────────────────────


class AgentState(TypedDict):
    """State flowing through the LangGraph agent.

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

    Usage::

        agent = LangGraphAgent(config=AgentConfig(), engine=some_engine)
        result = await agent.run("place the design")  # async
        result = agent.run_sync("place the design")  # blocking

    Or use the ``translate`` / ``translate_sync`` aliases for drop-in
    compatibility with the legacy ``Agent`` class.
    """

    def __init__(self, config: AgentConfig, engine: TclEngine | None = None) -> None:
        self.config = config
        self.engine = engine
        self.graph: Any = self._build_graph()  # CompiledStateGraph (missing stubs)

    # ── graph construction ────────────────────────────────────────

    def _build_graph(self) -> Any:  # CompiledStateGraph (missing stubs)
        builder = StateGraph(AgentState)

        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", self._tools_node)

        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            self._router,
            {"tools": "tools", END: END},
        )
        builder.add_edge("tools", "agent")

        return builder.compile()

    # ── nodes ─────────────────────────────────────────────────────

    async def _agent_node(self, state: AgentState) -> dict:
        """Mock LLM: translate user input, or summarize after tool execution."""
        from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

        if self.config.model == "mock" and self.config.delay > 0:
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

    def _tools_node(self, state: AgentState) -> dict:
        """Execute the Tcl command via the engine (if available)."""
        from langchain_core.messages import ToolMessage  # local

        tcl = state.get("tcl_command", "")
        result = "No engine available."

        if self.engine is not None:
            try:
                result = self.engine.execute(tcl)  # type: ignore[union-attr]
            except Exception as exc:  # noqa: BLE001
                result = f"ERROR: {exc}"

        return {
            "messages": [ToolMessage(content=result, tool_call_id="tcl_exec")],
            "engine_result": result,
            "tcl_command": "",  # clear for next round
        }

    # ── routing ───────────────────────────────────────────────────

    def _router(self, state: AgentState) -> str:
        """Decide: execute the Tcl command or stop."""
        tcl = state.get("tcl_command", "")
        if tcl and not tcl.startswith("#"):
            return "tools"
        return END  # type: ignore[return-value]

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
        """Process *text* through the graph and return the engine result.

        *context* is reserved for future use (e.g. injecting extra
        messages or system prompts).
        """
        from langchain_core.messages import HumanMessage

        state = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=text)]},
            {"recursion_limit": self.config.max_iterations + 1},
        )
        engine_result: str = state.get("engine_result", "")
        if not engine_result:
            # Tool was never called (e.g. unrecognized input) —
            # return the last AI message or the raw Tcl comment.
            tcl_cmd: str = state.get("tcl_command", "")
            return tcl_cmd or engine_result
        return engine_result

    def run_sync(self, text: str, *, context: dict | str | None = None) -> str:
        """Wrap :meth:`run` as a synchronous, blocking call."""
        return asyncio.run(self.run(text, context=context))

    # ── compatibility aliases (drop-in for legacy Agent) ──────────

    async def translate(self, text: str, *, context: dict | str | None = None) -> str:
        """Alias for :meth:`run` — compatible with ``Agent.translate()``."""
        return await self.run(text, context=context)

    def translate_sync(self, text: str, *, context: dict | str | None = None) -> str:
        """Alias for :meth:`run_sync`."""
        return self.run_sync(text, context=context)

    @property
    def delay(self) -> float:
        """Simulated latency (matches ``Agent.delay``)."""
        return self.config.delay

    @delay.setter
    def delay(self, value: float) -> None:
        self.config.delay = value

    # ── Message helpers ───────────────────────────────────────────

    def build_human_message(self, text: str) -> Any:
        """Build a langchain ``HumanMessage`` from *text* via the domain type.

        Example::

            msg = agent.build_human_message("place the design")
            state = await agent.graph.ainvoke({"messages": [msg]})
        """
        return Message.human(text).to_langchain()

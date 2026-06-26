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
import subprocess
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek

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


# ── env.md helpers ──────────────────────────────────────────────────────


def _build_env_prompt() -> str:
    """Read and merge env.md from team, user, and project levels.

    Layers (lowest to highest priority):
      1. ``/etc/.edai/env.md``  — team level
      2. ``~/.edai/env.md``     — user level
      3. ``{cwd}/.edai/env.md`` — project level

    Each layer is appended after the previous one with a ``##`` header
    identifying its source.  Missing files are silently skipped.
    Returns an empty string if no env.md files exist.
    """
    layers = [
        ("/etc/.edai/env.md", "## 团队环境 (Team)"),
        (os.path.expanduser("~/.edai/env.md"), "## 个人环境 (User)"),
        (os.path.join(os.getcwd(), ".edai/env.md"), "## 项目环境 (Project)"),
    ]
    parts: list[str] = []
    for path, header in layers:
        try:
            content = open(path, encoding="utf-8").read().strip()
        except (FileNotFoundError, PermissionError):
            continue
        if content:
            parts.append(f"{header}\n\n{content}")
    return "\n\n".join(parts)


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
        # Build and cache the system prompt as a public attribute
        self.system_prompt = self._build_system_prompt()
        # Expose env prompt separately for /env_info
        self.env_prompt = _build_env_prompt()
        # Expose role and backend type publicly
        self.role = role
        self.backend_type = getattr(backend, "backend_type", "tclsh")
        self.graph: Any = self._build_graph()
        # Conversation history (langchain messages) — persists across calls
        self._messages: list = []

    @property
    def config(self) -> AgentConfig:
        """Public accessor for agent configuration."""
        return self._config

    # ── prompt construction ─────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        """Combine agent role + env + backend capabilities into one system prompt."""
        parts: list[str] = []

        # Agent role doc
        role_md = _load_md("edai.roles", "agents", f"{self._role}.md")
        if role_md:
            parts.append(role_md)

        # Environment configuration (merged from team / user / project layers)
        env_md = _build_env_prompt()
        if env_md:
            parts.append("## 环境配置\n")
            parts.append(env_md)

        # Backend capabilities doc
        bt = getattr(self.backend, "backend_type", "tclsh")
        backend_md = _load_md("edai.roles", "backends", f"{bt}.md")
        if not backend_md:
            # fallback to tclsh.md for unrecognised backends
            backend_md = _load_md("edai.roles", "backends", "tclsh.md")
        if backend_md:
            parts.append(f"## 当前后端：{bt}\n")
            parts.append(
                f"你当前连接的是 **{bt}** 后端。通过 `execute` 工具发送的**所有命令**"
                f"必须使用 **{bt}** 的语法和命令约定。"
                f"**禁止**使用其他 EDA 工具（如 dc_shell、Genus、Innovus、Vivado 等）"
                f"的命令，除非用户明确要求切换到其他工具。"
            )
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
        bt = getattr(backend, "backend_type", "tclsh")

        @tool
        def execute(command: str) -> str:
            """Send a command to the backend and return the result.

            Use this tool to run any backend command.
            The available commands depend on the connected backend.
            """
            return backend.send_command(command)

        # Dynamically anchor the tool description to the current backend
        # so the agent always sees which tool it is connected to when
        # deciding whether to call `execute`.
        execute.description = (
            f"Send a **{bt}** command to the backend and return the result.\n\n"
            f"The connected backend is **{bt}**. "
            f"All commands MUST follow {bt} syntax and conventions. "
            f"Do NOT use commands from other EDA tools."
        )

        # ── workspace-scoped tools ────────────────────────────────────

        workspace_root = Path.cwd().resolve()

        @tool
        def bash_executor(command: str) -> str:
            """Execute a shell command in the workspace directory.

            Run a single command via the system shell.  The working directory
            is fixed to the workspace root.  Commands are limited to 60
            seconds and output is truncated to 50 000 characters.
            Do NOT run destructive commands (rm, force push, etc.) unless
            the user explicitly requests it.
            """
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=str(workspace_root),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()

                output = stdout if stdout else ""
                if stderr:
                    output += f"\n[stderr]\n{stderr}" if output else stderr

                if result.returncode != 0:
                    prefix = f"Command failed (rc={result.returncode})"
                    output = f"{prefix}\n{output}" if output else prefix

                max_out = 50_000
                if len(output) > max_out:
                    output = (
                        output[:max_out]
                        + f"\n... (truncated, {len(output)} chars total)"
                    )

                return output if output else "(no output)"
            except subprocess.TimeoutExpired:
                return "Command timed out (60s)"
            except Exception as exc:  # noqa: BLE001
                return f"Command error: {exc}"

        _WORKSPACE = str(workspace_root)
        bash_executor.description = (
            f"Execute a shell command in the workspace directory.\n\n"
            f"Working directory: {_WORKSPACE}. "
            f"Commands run via the system shell, limited to 60 seconds. "
            f"Output is truncated at 50 000 characters. "
            f"Do NOT run destructive commands unless the user explicitly asks."
        )

        @tool
        def read(file: str, start: int = 1, end: int = -1) -> str:
            """Read a file from the workspace with optional line range.

            Read a file within the project workspace.  Supports 1-indexed
            line ranges: *start* (default 1), *end* (default -1 = EOF).
            Binary files and paths escaping the workspace are rejected.
            """
            try:
                path = Path(file)
                if not path.is_absolute():
                    path = workspace_root / path
                path = path.resolve()

                # Security: must be inside workspace
                try:
                    path.relative_to(workspace_root)
                except ValueError:
                    return f"Access denied: {file} is outside the workspace"

                # Symlink escape guard
                if path.is_symlink():
                    real = path.resolve()
                    try:
                        real.relative_to(workspace_root)
                    except ValueError:
                        return (
                            f"Access denied: {file} is a symlink pointing "
                            f"outside the workspace"
                        )

                if not path.is_file():
                    return f"File not found: {file}"

                # Binary guard
                with open(path, "rb") as fh:
                    chunk = fh.read(1024)
                    if b"\x00" in chunk:
                        return f"Cannot read binary file: {file}"

                with open(path, encoding="utf-8") as fh:
                    lines = fh.readlines()

                total = len(lines)
                if start < 1:
                    start = 1
                if end < 0 or end > total:
                    end = total
                if start > total:
                    return f"Line {start} is beyond end of file ({total} lines)"

                selected = lines[start - 1 : end]
                width = len(str(end))
                numbered = [
                    f"{i:>{width}}: {line}" for i, line in enumerate(selected, start=start)
                ]

                rel = path.relative_to(workspace_root)
                header = f"File: {rel} (lines {start}-{end} of {total})\n"
                return header + "".join(numbered)

            except UnicodeDecodeError:
                return f"Cannot decode file as UTF-8: {file}"
            except Exception as exc:  # noqa: BLE001
                return f"Read error: {exc}"

        read.description = (
            f"Read a file from the workspace directory.\n\n"
            f"Workspace root: {_WORKSPACE}. "
            f"Accepts relative paths (resolved under workspace) or absolute paths "
            f"(must stay inside workspace).  Supports 1-indexed line ranges: "
            f"`start` (default 1), `end` (default -1 = read to EOF). "
            f"Binary files are rejected with an error message."
        )

        system_prompt = self._build_system_prompt()
        return create_agent(
            llm,
            tools=[execute, bash_executor, read],
            system_prompt=system_prompt,
        )

    # ── public API ──────────────────────────────────────────────────

    async def run(self, text: str) -> str:
        """Process *text* through the ReAct graph and return the final answer."""
        from langchain_core.messages import HumanMessage

        self._messages.append(HumanMessage(content=text))

        state = await self.graph.ainvoke(
            {"messages": list(self._messages)},
            {"recursion_limit": self._config.max_iterations + 1},
        )
        self._messages = state.get("messages", [])
        msgs = self._messages
        return str(msgs[-1].content) if msgs else ""

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

        self._messages.append(HumanMessage(content=text))
        seen_count = len(self._messages) - 1  # only the just-appended msg is new

        final_state: Any = None
        try:
            async for state in self.graph.astream(
                {"messages": list(self._messages)},
                {"recursion_limit": self._config.max_iterations + 1},
                stream_mode="values",
            ):
                final_state = state
                step_msgs = state.get("messages", [])
                for i in range(seen_count, len(step_msgs)):
                    msg = step_msgs[i]

                    if isinstance(msg, ToolMessage):
                        yield ("tool_result", str(msg.content))
                    elif isinstance(msg, AIMessage):
                        tool_calls = getattr(msg, "tool_calls", [])
                        if tool_calls:
                            for tc in tool_calls:
                                args = tc.get("args", {})
                                cmd = (
                                    args.get("command", "")
                                    if isinstance(args, dict)
                                    else ""
                                )
                                yield ("tool_call", cmd if cmd else tc.get("name", "execute"))
                        content = str(msg.content) if msg.content else ""
                        if content:
                            yield ("token", content)

                seen_count = len(step_msgs)

            # Persist the full accumulated state as history
            if final_state is not None:
                self._messages = final_state.get("messages", [])

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
        """Reset conversation history."""
        self._messages = []

    def record_command(self, command: str, result: str) -> None:
        """Record a user command and its backend result into the agent's context.

        This lets the agent see direct Tcl command executions that bypassed
        the ReAct loop (e.g. the fast-path in ``EdaiApp``).

        The *command* is stored as a ``HumanMessage`` and *result* as an
        ``AIMessage`` so the message sequence forms a valid conversation
        (``Human→AI``) that the LLM API can accept.  A bare ``ToolMessage``
        without a preceding ``AIMessage.tool_calls`` with a matching ID would
        cause a 400 error from the API.
        """
        from langchain_core.messages import AIMessage, HumanMessage

        self._messages.append(HumanMessage(content=command))
        self._messages.append(AIMessage(content=result))

    @property
    def delay(self) -> float:
        """Backward-compat: always 0 (no mock mode)."""
        return 0.0

    @delay.setter
    def delay(self, value: float) -> None:
        """Backward-compat no-op."""

"""Simplified TUI — Tcl wrapper with ReAct agent dispatch and mock fallback.

On Enter:
* If the input is a registered Tcl command → execute directly via backend.
* Otherwise → pass to the ReAct agent which decides whether to call the
  Tcl tool (via function calling) or respond with text.

Backend selection:
* ``--mock`` flag → in-memory ``MockTclRepl`` simulation.
* ``--path`` / ``-p`` → real ``EDAInteractive`` subprocess at the given binary.
* ``tclsh`` on ``PATH`` → real ``EDAInteractive`` subprocess.
* No backend found → in-memory ``MockTclRepl`` simulation (fallback).

Agent mode
----------
By default the ``LangGraphAgent`` runs in ReAct mode using ``ChatDeepSeek``
with a Tcl execution tool.  Set ``LLM_MODEL=mock`` to fall back to the
legacy keyword-matching graph (no LLM required).

Streaming
---------
Agent responses are streamed token‑by‑token and displayed in real‑time
inside an inline ``Static`` widget.  Tool‑call notifications and results
appear as dimmed log lines.  When streaming finishes the full response is
committed to the ``RichLog`` conversation log in italic style.
"""

from __future__ import annotations

import asyncio
import os
from typing import Protocol

from rich.rule import Rule
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from edai.agent.config import AgentConfig
from edai.agent.graph import LangGraphAgent
from edai.core.backend_config import BackendConfig, create_backend
from edai.core.Message import Message, MessageRole

# ── 常量 ──────────────────────────────────────────────────────────────

_STREAM_PLACEHOLDER = "[dim]▌[/dim]"
"""流式输出时的闪烁光标占位符."""


class TclBackend(Protocol):
    """Duck-typed protocol for the Tcl execution backend.

    Both ``EDAInteractive`` and ``MockTclRepl`` satisfy this.
    """

    prompt: str

    def send_command(self, code: str) -> str: ...


# ── 模型选择 ──────────────────────────────────────────────────────────

_DEFAULT_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
"""ReAct 代理使用的模型标识。

设为 ``mock`` 则使用传统的关键词匹配图（无需 API key）.
"""


class EdaiApp(App[None]):
    """Textual 应用——封装 Tcl 后端 + ReAct 代理调度."""

    TITLE = "EDAI"
    SUB_TITLE = "EDA Interactive Toolkit"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_log", "Clear"),
    ]

    DEFAULT_CSS = """
    RichLog {
        border: solid $primary;
        height: 1fr;
        margin: 0 1;
    }
    #stream-area {
        margin: 0 1 0 1;
        min-height: 1;
    }
    Input {
        dock: bottom;
        margin: 0 1 1 1;
    }
    """

    def __init__(self, config: BackendConfig | None = None) -> None:
        super().__init__()
        self._interactive = create_backend(config)

        # 默认使用真实模型；LLM_MODEL=mock 或无 API key 时回退到关键词匹配。
        model = _DEFAULT_MODEL
        if model == "mock":
            agent_config = AgentConfig(model="mock")
        else:
            agent_config = AgentConfig(
                model=model,
                system_prompt=(
                    "You are an EDA assistant. Convert the user's natural-language "
                    "request into Tcl commands. You have a Tcl execution tool "
                    "available — use it to run commands and return results. "
                    "When the user types a natural-language request, translate it "
                    "into the appropriate Tcl command and execute it."
                ),
            )

        self._agent = LangGraphAgent(config=agent_config, backend=self._interactive)

        # 规范对话历史——list[Message]
        self._conversation: list[Message] = []

    def compose(self) -> ComposeResult:
        """构建最小化小部件树."""
        self._output = RichLog(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        self._stream_output = Static("", markup=True, id="stream-area")
        self._input_text = Input(
            placeholder="Enter Tcl commands or natural language.\u2026"
        )
        with Vertical():
            yield Header(show_clock=True)
            yield self._output
            yield self._stream_output
            with HorizontalGroup():
                yield Static(f"{self._interactive.prompt} ", markup=True, id="prompt")
                yield self._input_text
            yield Footer()

    def on_mount(self) -> None:
        """显示 banner 并聚焦输入框."""
        self._banner()
        self._input_text.focus()

    # ── 消息处理 ────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter → 分发输入."""
        text = event.value.strip()
        if not text:
            return

        # 清除上轮对话残留的流式内容
        self._stream_output.update("")

        # 对话块之间的视觉分隔线
        if self._conversation:
            self._output.write(Rule(style="dim"))

        user_msg = Message.human(text)
        self._conversation.append(user_msg)

        self._output.write(f"[bold cyan]{self._interactive.prompt}[/] {text}")
        self._run_worker_stream(text)
        self._input_text.clear()

    # ── 动作处理 ─────────────────────────────────────────────────────

    def action_clear_log(self) -> None:
        """Ctrl+L → 清空输出日志和对话历史."""
        self._output.clear()
        self._stream_output.update("")
        self._conversation.clear()
        self._banner()

    # ── 辅助方法 ────────────────────────────────────────────────────

    @staticmethod
    def _check_tcl_response(response: str) -> bool:
        """检查响应是否为有效的 Tcl 命令执行结果."""
        if not response:
            return True
        if response.startswith("invalid command name"):
            return False
        return not response.startswith("can't read")

    # ── 流式工作器 ─────────────────────────────────────────────────

    def _run_worker_stream(self, text: str) -> None:
        """启动异步工作器，逐步流式输出代理响应."""

        async def _stream_task() -> None:
            stripped = text.strip()

            # --- 快速路径：直接将输入作为 Tcl 命令执行 --------------------------
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                self._interactive.send_command,
                stripped,
            )
            if self._check_tcl_response(response):
                result_msg = Message.ai(response)
                self._conversation.append(result_msg)
                self._output.write(response)
                return

            # --- 代理路径：从 ReAct 代理流式读取结果 -----------------------------
            self._stream_output.update(_STREAM_PLACEHOLDER)
            full_response = ""

            try:
                async for event_type, content in self._agent.run_stream(stripped):
                    if event_type == "token":
                        full_response += content
                        self._stream_output.update(
                            f"[italic]{full_response}[/italic]"
                            if full_response
                            else _STREAM_PLACEHOLDER,
                        )
                    elif event_type == "tool_call":
                        self._output.write(
                            f"[dim]⚡ 调用工具: [italic]{content}[/italic][/]"
                        )
                    elif event_type == "tool_result":
                        if content.strip():
                            self._output.write(
                                f"[dim]  └─ {content.strip()}[/]"
                            )
                    elif event_type == "error":
                        self._stream_output.update("")
                        self._output.write(f"[red]Error: {content}[/red]")

            except Exception as exc:  # noqa: BLE001
                self._stream_output.update("")
                self._output.write(f"[red]Stream error: {exc}[/red]")
                return

            # --- 流式完成：提交到日志 -------------------------------------------
            self._stream_output.update("")

            if full_response:
                self._output.write(
                    f"[bold green][italic]Agent:[/][/] [italic]{full_response}[/italic]"
                )
                result_msg = Message.ai(full_response)
                self._conversation.append(result_msg)

        self.app.run_worker(_stream_task(), exclusive=True)

    # ── 同步分发（测试 / 外部调用用）─────────────────────────────────

    def _dispatch(self, text: str) -> str:
        """收集流式输出为单个字符串.

        供测试和程序化调用使用。交互式 UI 请使用 :meth:`_run_worker_stream`。
        """
        stripped = text.strip()
        if not stripped:
            return ""

        # 1. 尝试直接执行 Tcl 命令
        response = self._interactive.send_command(stripped)
        if self._check_tcl_response(response):
            return response

        # 2. 不是有效 Tcl——交给 ReAct 代理处理
        try:
            full_response = ""
            for event_type, content in self._agent.run_stream_sync(stripped):
                if event_type == "token":
                    full_response += content
                elif event_type == "error":
                    return f"[red]Error: {content}[/red]"
            if full_response:
                return f"[bold green]Agent:[/] {full_response}"
        except Exception as e:
            return f"{response}\n[red]Agent error: {e}[/red]"

        return response

    # ── 对话历史访问器 ────────────────────────────────────────────

    @property
    def conversation(self) -> list[Message]:
        """只读的对话历史."""
        return list(self._conversation)

    def last_user_message(self) -> Message | None:
        """返回最近一条用户消息（如有）."""
        for msg in reversed(self._conversation):
            if msg.role == MessageRole.HUMAN:
                return msg
        return None

    # ── Banner ──────────────────────────────────────────────────────

    def _banner(self) -> None:
        """输出欢迎 Banner."""
        self._output.write(
            "\n"
            "[bold cyan]"
            f"{' ' * 10} ███████╗██████╗  █████╗ ████╗\n"
            f"{' ' * 10} ██╔════╝██╔══██╗██╔══██╗ ██╔╝\n"
            f"{' ' * 10} █████╗  ██║  ██║███████║ ██║\n"
            f"{' ' * 10} ██╔══╝  ██║  ██║██╔══██║ ██║\n"
            f"{' ' * 10} ███████╗██████╔╝██║  ██║████╗\n"
            f"{' ' * 10} ╚══════╝╚═════╝ ╚═╝  ╚═╝╚═══╝[/]\n"
            "[bold yellow]                EDAI  version 0.1.0[/]\n"
            "\n"
            "[dim]  Tab ↹ focus     ⌃C quit    ⌃L clear[/]"
        )


# ── 模块级辅助函数 ────────────────────────────────────────────────────


def run_tui(config: BackendConfig | None = None) -> int:
    """同步启动 Textual TUI.

    Parameters
    ----------
    config:
        后端配置。为 *None* 时使用默认自动检测行为
        （参见 :func:`~edai.core.backend_config.create_backend`）。

    """
    app = EdaiApp(config)
    result = app.run()
    return result if result is not None else 0

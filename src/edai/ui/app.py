"""Simplified TUI — backend wrapper with ReAct agent dispatch.

On Enter:
* If the input is a recognisable backend command → execute directly via backend.
* Otherwise → pass to the ReAct agent which understands intent and calls
  the ``execute`` tool as needed.

Backend selection:
* ``--mock`` flag → in-memory ``MockTclRepl`` simulation.
* ``--path`` / ``-p`` → real ``EDAInteractive`` subprocess at the given binary.
* ``tclsh`` on ``PATH`` → real ``EDAInteractive`` subprocess.
* No backend found → in-memory ``MockTclRepl`` simulation (fallback).

Streaming
---------
Agent responses are streamed token‑by‑token and displayed in real‑time
inside an inline ``Static`` widget.  Tool‑call notifications and results
appear as dimmed log lines.  When streaming finishes the full response is
committed to the ``RichLog`` conversation log in italic style.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from rich.rule import Rule
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import HorizontalGroup, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from edai.agent import Agent
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

        self._agent = Agent(backend=self._interactive, role="EDAI")

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

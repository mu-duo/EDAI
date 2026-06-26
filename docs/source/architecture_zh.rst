.. _zh-architecture:

架构
====

EDAI 采用三层解耦设计，每层职责单一：

.. image:: /imgs/edai_architecture_detailed.png
   :alt: 详细架构图
   :width: 100 %

1 — UI 层（``edai.ui``）
------------------------

UI 基于 `Textual <https://textual.textualize.io/>`__ 构建，一个 Python
终端应用框架。

.. code-block:: text

    EdaiApp (textual.app.App)
     ├── RichLog          ← 对话日志
     ├── Static           ← 流式区域
     ├── Input            ← 用户输入
     └── Footer / Header

**App 职责：**

* 路由用户输入：``/``-命令 → ``_handle_tui_special()``；
  Tcl 命令 → ``send_command()``；其他 → Agent。
* 维护 ``_conversation: list[Message]`` 用于 ``/history`` 和 Agent 上下文。
* 通过 ``set_debug_output()`` 安装调试输出路由，后端调试信息显示在 RichLog 中。
* 在 TUI 层直接处理 ``/clear``（≡ Ctrl+L）和 ``/exit``，不涉及后端。

2 — Agent 层（``edai.agent``）
------------------------------

Agent 是基于 LangChain ``create_agent`` 工厂构建的 LangGraph ReAct 循环。

.. code-block:: text

    +--------+     +--------+     +----------+
    |  LLM   | ←→  | Tools  | ←→  | Backend  |
    +--------+     +--------+     +----------+
         ↑                            ↑
      HumanMessage               ToolMessage
         ↑                            ↑
      用户输入                   后端输出

**Agent 职责：**

* 跨调用维护对话历史（``_messages: list[BaseMessage]``）。
* 通过 ``execute`` 工具将自然语言翻译为 Tcl 命令。
* 通过 ``record_command()`` 将快速路径的 Tcl 命令记入历史，
  使 Agent 能感知绕过 ReAct 循环的命令。

3 — 后端层（``edai.core``）
---------------------------

**MockTclRepl** — 内存模拟，含静态设计数据库（6 个 cell、5 个 net、
5 个 port、1 个 library、1 个 clock）。适用于：

* 无需许可的 EDA 工具即可调试 Agent 或 UI。
* 运行集成测试。
* 在没有后端的机器上进行开发/演示。

**EDAInteractive** — 通过 ``pexpect.spawn`` 持久化子进程连接真实 EDA 工具，
会话在连续命令间保持存活。

.. note::

   ``pexpect.spawn`` 默认:strong:`不捕获 stderr`。EDAI 通过
   ``/bin/sh -c "... 2>&1"`` 包装调用，使错误信息（如
   ``invalid command name``）与 stdout 一同被捕获。

横切关注点
----------

**消息模型** （``edai.core.Message``）
  规范 ``Message`` 类，基于角色的工厂方法（``human``、``ai``、``tool``、
  ``system``），与 LangChain 基础消息双向转换。

**命令注册中心**

  * ``edai.core.cmd_registry`` — 基于装饰器的 Tcl 命令注册中心
    （约 150 条命令，分类：COMMON、STA/SDC、SYNTHESIS）。
  * ``edai.core.special_cmds`` — 基于装饰器的 ``/``-前缀 REPL 元命令
    注册中心。

**调试基础设施** （``edai.core.debug``）
  ``set_debug()`` / ``debug_print()`` / ``set_debug_output()`` —
  模块级标志，由 ``--verbose`` CLI 参数和运行时的 ``/debug`` 命令控制。
  输出可路由到 stderr（默认）或 TUI 控件。

数据流
------

.. image:: /imgs/edai_data_flow.png
   :alt: 数据流图
   :width: 100 %

**快速路径（已知 Tcl 命令）：**

::

    用户输入 ──→ EdaiApp ──→ send_command() ──→ 后端
                           ↓
                     record_command() → Agent._messages
                           ↓
                     Message.tool() → _conversation

**Agent 路径（自然语言）：**

::

    用户输入 ──→ EdaiApp ──→ Agent.run_stream() ──→ LLM
                                ↓
                          execute tool ──→ 后端
                                ↓
                          Token 流 ──→ 流式区域 → _conversation

**特殊命令路径（``/`` 前缀）：**

::

    用户输入 ──→ EdaiApp._handle_tui_special()
                      ├── /exit  → self.exit()
                      ├── /clear → action_clear_log()
                      └── other  → special_registry.execute()

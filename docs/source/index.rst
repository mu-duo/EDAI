.. only:: not language_zh

   ====================================
   EDAI — AI-Powered EDA Toolkit
   ====================================

   **EDAI** (Electronic Design AI) is an intelligent CLI toolkit that bridges
   natural language and Electronic Design Automation (EDA) tool commands.  It
   provides a Textual-based TUI where designers can type Tcl commands directly
   *or* describe their intent in natural language — the built-in LLM agent
   translates and executes the appropriate backend commands.

   .. image:: imgs/edai_banner.png
      :alt: EDAI Banner
      :width: 100 %

   Key highlights
   ==============

   * **Hybrid input** — raw Tcl for power users, natural language for rapid
     prototyping and learning.
   * **LLM-powered agent** — understands design intent, generates multi-step
     Tcl command sequences, and can self-correct on errors.
   * **Pluggable backends** — in-memory mock for development and testing, or
     connect to real EDA tools (``tclsh``, ``dc_shell``, ``genus``, etc.).
   * **Persistent sessions** — tool variables, design data, and timing reports
     are preserved across consecutive commands.
   * **Special REPL commands** — ``/help``, ``/debug``, ``/history``, and more
     for controlling the agent environment.
   * **Global debug infrastructure** — toggle verbose logging with ``/debug``
     to inspect every command and agent decision.

   Documentation
   =============

   .. toctree::
      :maxdepth: 2

      overview
      usage
      architecture

   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`search`

.. only:: language_zh

   ============================================
   EDAI — AI 驱动的 EDA 工具包
   ============================================

   **EDAI** （Electronic Design AI）是一个智能化的 CLI 工具包，它在自然语言与 EDA
   （电子设计自动化）工具命令之间架起了桥梁。它提供一个基于 Textual 的 TUI，
   设计人员可以直接输入 Tcl 命令，也可以用自然语言描述意图——内置的 LLM Agent
   会将其翻译为相应的后端指令并执行。

   .. image:: imgs/edai_banner.png
      :alt: EDAI Banner
      :width: 100 %

   核心亮点
   ========

   * **混合输入** — 熟练用户直接输入 Tcl 命令，新手或快速原型用自然语言。
   * **LLM 驱动 Agent** — 理解设计意图、生成多步 Tcl 命令序列，可自主纠错。
   * **可插拔后端** — 内存 Mock 用于开发/测试，或连接真实 EDA 工具
     （``tclsh``、``dc_shell``、``genus`` 等）。
   * **持久会话** — 工具变量、设计数据、时序报告在连续命令间完整保留。
   * **特殊命令** — ``/help``、``/debug``、``/history`` 等用于控制 Agent 环境。
   * **全局调试** — 通过 ``/debug`` 开启详细日志，检查每条命令和 Agent 决策。

   文档目录
   ========

   .. toctree::
      :maxdepth: 2

      zh/overview
      zh/usage
      zh/architecture

   索引与表格
   ==========

   * :ref:`genindex`
   * :ref:`search`

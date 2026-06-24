.. _zh-overview:

概述与愿景
==========

什么是 EDAI？
-------------

EDAI 是一个命令行工具包，为你的 EDA 工作流配备了一个 **AI 副驾驶**。
你无需记忆几十条 Tcl 命令、也无需在文档和终端之间来回切换——
只需用自然语言描述需求，EDAI 负责翻译执行。

名称 **EDAI** 代表 **E**\ lectronic **D**\ esign **AI** （电子设计 AI），
它既是工具名也是愿景：一个 AI 原生的半导体设计流程接口。

.. image:: ../_static/edai-session.png
   :alt: EDAI TUI 会话截图
   :width: 100 %

核心功能
--------

**1. 混合命令接口**

用户可以输入原生 Tcl 命令（``get_cells``、``report_timing`` 等），
这些命令被直接转发给后端执行。同时自然语言输入会被识别并提交给 LLM Agent，
由 Agent 将意图翻译为多步 Tcl 命令序列。

**2. LLM 驱动的 Agent**

Agent 使用 LangGraph ReAct 循环理解用户请求、调用后端工具、解读结果
并决定下一步动作。它维护对话历史，使后续问题可以引用之前的执行结果。

**3. 可插拔后端**

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - 后端
     - 适用场景
   * - ``MockTclRepl``
     - 内存 Mock，含静态设计数据库；适合开发、测试和演示。
   * - ``EDAInteractive``
     - 通过 pexpect 连接真实 EDA 工具子进程
       （``tclsh``、``dc_shell``、``genus``、``innovus``）。

后端在启动时自动选择（``PATH`` 上有 ``tclsh`` → 真实后端；否则 → Mock），
可通过 ``--mock`` 或 ``--path`` 参数强制指定。

**4. 会话持久化**

工具变量、设计状态、时序数据在命令间持续存在。pexpect 子进程保持存活，
设计人员可以逐步构建流程而无需重启。

**5. 调试与可观测性**

全局 ``/debug`` 命令切换详细日志模式。开启后每条 Tcl 命令和 Agent 工具调用
都会实时打印——对开发和故障排查极有价值。

架构一览
--------

.. image:: ../_static/edai-architecture.png
   :alt: EDAI 架构图
   :width: 100 %

架构采用三层设计：

1. **UI 层** （Textual TUI）—— 捕获用户输入、展示结果、路由 ``/``-前缀特殊命令。
2. **Agent 层** （LangGraph ReAct）—— 将自然语言翻译为工具调用，维护对话上下文。
3. **后端层** （Mock / 真实 EDA）—— 执行 Tcl 命令，返回输出。

各层通过协议和依赖注入解耦，后端可在不修改 Agent 或 UI 的前提下自由替换。

未来愿景——从 Spec 到 GDSII
============================

EDAI 是更大愿景的第一步：**AI 原生的 EDA 流程，连接设计意图与硅片实现。**

近期路线图
----------

.. image:: ../_static/edai-roadmap.png
   :alt: EDAI 路线图
   :width: 100 %

* **多 Agent 编排** — 为综合、布局、CTS、布线、签核分配专门的 Agent，
  由指挥 Agent 统一协调。
* **文件和项目感知** — 让 Agent 读取 RTL、SDC、Liberty 文件以提供上下文
  感知的建议。
* **时序收敛助手** — Agent 引导的优化循环：``report_timing`` → 识别违例 →
  建议修复 → 重新运行并验证。
* **CI/CD 集成** — 将流程作为回归流水线的一部分运行，辅以 LLM 驱动的
  故障分类。

长远目标：Spec → GDSII
-----------------------

最终目标是构建一个 AI 系统，接受 **自然语言规格** 并驱动物理设计流程
**从概念到 GDSII**，只需最少的人工干预。

.. image:: ../_static/edai-spec-to-gdsii.png
   :alt: Spec 到 GDSII 流程图
   :width: 100 %

**阶段：**

1. **规格解析** — Agent 读取高层次规格（英文/中文/结构化 YAML），
   推断设计约束、时钟域、功耗目标和接口协议。
2. **RTL 生成** — Agent 编写符合规格的可综合 RTL，包含形式验证断言。
3. **综合与布局规划** — Agent 驱动 ``dc_shell`` 或 ``genus``，
   迭代优化时序并创建布局规划。
4. **布局布线** — Agent 编排 ``innovus`` 等 P&R 工具，收敛时序和 DRC。
5. **签核** — Agent 运行 STA、功耗分析和物理验证，生成 GDSII 交付包。
6. **总结报告** — Agent 生成人类可读的最终 QoR 报告（时序、功耗、面积）。

使能技术
--------

**SiliconCompiler 作为 EDA 抽象层**
  `SiliconCompiler <https://www.siliconcompiler.com/>`__ 标准化了综合、
  P&R 和签核的工具接口。将其作为 EDAI 的执行引擎，可为 Agent 提供
  统一的 RTL-to-GDSII 流程 API。

**模型上下文协议（MCP）**
  `Model Context Protocol <https://modelcontextprotocol.io/>`__ 标准化了
  AI 模型与工具的交互方式。一个针对 EDA 工具的 MCP 服务器可让任何
  MCP 兼容的 Agent 驱动整个流程，无需工具特定的胶水代码。

**多 Agent 协作**
  受 `CrewAI <https://www.crewai.com/>`__ 等框架启发，未来版本可能为
  "综合工程师"、"时序专家"、"物理设计工程师"等角色分配独立的 Agent
  实例，协同完成设计。

.. note::

   EDAI 是一个开源项目。欢迎通过 https://github.com/tanlinfeng/EDAI
   提交功能请求、Bug 报告和贡献。

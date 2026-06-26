:orphan:

============================================
EDAI — AI 驱动的 EDA 工具包
============================================

**EDAI** （Electronic Design AI）是一个智能化的 CLI 工具包，它在自然语言与 EDA
（电子设计自动化）工具命令之间架起了桥梁。它提供一个基于 Textual 的 TUI，
设计人员可以直接输入 Tcl 命令，也可以用自然语言描述意图——内置的 LLM Agent
会将其翻译为相应的后端指令并执行。

.. image:: /imgs/edai_banner.png
   :alt: EDAI Banner
   :width: 100 %
   :target: https://github.com/tanlinfeng/EDAI

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

   overview_zh
   usage_zh
   architecture_zh

索引与表格
==========

* :ref:`genindex`
* :ref:`search`

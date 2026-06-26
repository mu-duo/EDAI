.. _zh-usage:

使用指南
========

命令行接口
----------

::

    edai [options] [tui]

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - 参数
     - 说明
   * - ``-v``, ``--verbose``
     - 启动时开启调试/详细输出。
   * - ``-p``, ``--path``
     - EDA 工具二进制路径（如 ``/usr/bin/dc_shell``）。
   * - ``--prompt``
     - 工具期望的提示符正则（默认从二进制名推断）。
   * - ``--mock``
     - 强制使用内存 Mock 后端（覆盖 ``--path``）。
   * - ``--version``
     - 打印版本后退出。
   * - ``tui``
     - 启动 Textual TUI（无子命令时默认启动）。

示例::

    edai                          # 自动检测后端，启动 TUI
    edai --mock                   # 强制使用 Mock 后端
    edai --path /bin/tclsh -v     # 真实 tclsh + 调试模式

Textual TUI
-----------

启动 EDAI 后会打开一个全屏 TUI，包含三个区域：

.. image:: /imgs/edai_tui_layout.png
   :alt: EDAI TUI 布局
   :width: 100 %

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - 区域
     - 功能
   * - **日志面板** （顶部）
     - 可滚动的对话日志，显示所有命令和 Agent 回复。
   * - **流式区域** （中部）
     - 内联区域，用于流式展示 Agent 回复 token。
   * - **输入栏** （底部）
     - 输入 Tcl 命令或自然语言，回车发送。

快捷键:

* :kbd:`Ctrl+L` — 清空日志和对话历史。
* :kbd:`Ctrl+C` — 退出。

特殊命令
--------

所有以 ``/`` 开头的命令均由 TUI 自身处理（不会转发给后端），且
:strong:`不会` 记录到对话历史中。

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - 命令
     - 别名
     - 说明
   * - ``/help``
     - ``h``, ``?``
     - 列出所有可用的特殊命令。
   * - ``/exit``
     - ``quit``
     - 退出 TUI。
   * - ``/clear``
     - ``cls``
     - 清空输出日志和对话历史。
   * - ``/debug``
     -
     - 切换/开启/关闭/查询调试模式。
       子命令：``on``，``off``，``--status``。
   * - ``/env``
     -
     - 显示当前引擎状态（cell、net、port、clock、
       variable、调试模式）。
   * - ``/history``
     - ``hist``
     - 显示对话历史。``/history N`` 显示最近 *N* 条
       消息，附带 Rich markup 颜色标记。

Agent 交互
----------

当输入不匹配已知 Tcl 命令时，会被转发给 LLM Agent。Agent 使用 ReAct 循环：

1. 理解用户的自然语言请求。
2. 调用 ``execute`` 工具执行一条或多条 Tcl 命令。
3. 读取后端输出，判断是否需要更多步骤。
4. 将最终答案呈现给用户。

对话示例::

    tcl> 执行 placement
    Agent: 正在执行 place_design...
    └─ Placement completed.
    Agent: 设计已布局。线长估计：1.2 mm。

    tcl> 查看时序报告
    Agent: 正在执行 report_timing...
    └─ Timing report generated.
    Agent: 最差 slack 为 -0.05 ns，路径 clk→reg1/D。

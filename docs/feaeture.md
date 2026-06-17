# EDAI

一款支持 LLM 的 EDA 工具，旨在为 designer 提供一个智能化的 eda 工具。

## Features

1. **LLM 支持**：EDAI 内置了对大型语言模型（LLM）的支持，能够理解自然语言指令并生成相应的 EDA 命令。
2. **命令行交互**：提供了一个 TUI 界面，用户可以直接输入原生 EDA 指令（tcl 指令）此时 EDAI 会直接执行；同时，若输入自然语言指令，EDAI 会解析并执行相应的操作。

## 架构

EDAI 的架构主要分为以下几个模块：

### **1. Agent 模块**：负责与 LLM 进行交互，解析自然语言指令并生成相应的 EDA 命令。
### **2. Tool 模块**：可由 agent 进行调用的工具集合，tcl 后端是其 tools 之一，agent 调用这些工具执行并将结果返回给用户。
### **3. UI 模块**：提供了一个 TUI 界面，用户可以直接输入原生 EDA 指令（tcl 指令）此时 EDAI 会直接执行；同时，若输入自然语言指令，EDAI 会解析并执行相应的操作。

总的来说，EDAI 的架构可以概括为：
Agent层（大脑）：如果团队对LangChain熟悉，可以基于LangChain构建，参考IICPilot的架构。如果想尝试更结构化的多角色协作，可以研究CrewAI。
工具集成层（手脚）：强烈建议引入 SiliconCompiler 作为核心的Python EDA抽象层，它能将复杂的工具调用标准化。对于需要保持工具状态（session）的复杂任务，可以研究 FluxEDA。
协议与标准化（未来）：密切关注 MCP (Model Context Protocol) 在EDA领域的应用，它可能是未来Agent与EDA工具交互的标准方式。

## 考虑使用的第三方库

1. **textual**：用于构建 TUI 界面，提供丰富的文本样式和布局支持。
2. **rich**：用于在终端中渲染丰富的文本和图形，增强用户体验。
3. **LangGraph**：用于构建与 LLM 的交互逻辑，支持多种语言模型和工具集成。
4. **SiliconCompiler**：作为核心的 Python EDA 抽象层，标准化复杂的工具调用。
5. **FluxEDA**：用于处理需要保持工具状态（session）的复杂任务，提供更灵活的 EDA 工具集成。
6. **pytcl**：用于在 Python 中执行 Tcl 指令，方便与现有的 EDA 工具进行交互。
7. **pytcl-eda**：专门为 EDA 工具设计的 Tcl 扩展库，提供更丰富的 EDA 指令支持。
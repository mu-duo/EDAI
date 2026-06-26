# dc_shell 使用文档（Agent 版）

> **受众**：调用 Synopsys Design Compiler (dc_shell) 的 AI agent。本文档提供 RTL 综合核心流程所需的精确命令签名、参数类型、典型流程和脚本模板。
>
> **注意**：dc_shell 基于 Tcl，命令不区分大小写。本文档覆盖核心流程命令子集，完整命令列表请使用 `help` 或 `man` 查询。

---

## 目录

1. [概述](#1-概述)
2. [典型工作流](#2-典型工作流)
3. [Agent 操作指南](#3-agent-操作指南)
4. [核心命令详解](#4-核心命令详解)
   - [4.1 库与路径配置](#41-库与路径配置)
   - [4.2 设计输入](#42-设计输入)
   - [4.3 综合](#43-综合)
   - [4.4 设计输出](#44-设计输出)
   - [4.5 STA 约束](#45-sta-约束)
   - [4.6 报告](#46-报告)
   - [4.7 日志与重定向](#47-日志与重定向)
5. [查询命令速查](#5-查询命令速查)
6. [配置命令速查](#6-配置命令速查)
7. [完整脚本模板](#7-完整脚本模板)
8. [命令索引](#8-命令索引)

---

## 1. 概述

dc_shell 是 Synopsys Design Compiler 的 Tcl 命令行接口。主要功能：

- 读入 RTL 设计文件（Verilog/SystemVerilog/VHDL）
- 配置工艺库（target_library, link_library）
- 施加 SDC 时序约束
- 执行逻辑综合（`compile_ultra` / `compile`）
- 输出综合后网表、SDC、SDF
- 生成时序/面积/功耗报告

### 运行方式

```bash
dc_shell -f run.tcl              # 执行 Tcl 脚本
dc_shell                          # 交互模式
dc_shell -f run.tcl -output_log_file run.log  # 带日志输出
```

### 命令约定

- 选项格式：`-option_name value`
- 布尔选项：`-flag` 表示启用
- 位置参数：无需选项名的参数，按顺序传递
- 集合对象：`get_*` 命令返回对象集合，可传递给其他命令
- 文件名中的通配符：在大括号 `{}` 内使用 `*` 和 `?`

---

## 2. 典型工作流

dc_shell 的 RTL 综合标准流程如下：

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 配置库和路径    set target_library / link_library / ...  │
│ 2. 读入 RTL         analyze / read_verilog                  │
│ 3. 细化设计         elaborate                               │
│ 4. 施加 SDC 约束    create_clock / set_input_delay / ...    │
│ 5. 执行综合         compile_ultra                           │
│ 6. 输出网表/SDC     write_file / write_sdc                  │
│ 7. 生成报告         report_area / report_timing / ...       │
│ 8. 退出             exit                                    │
└─────────────────────────────────────────────────────────────┘
```

### 最小完整示例

```tcl
# 1. 库配置
set search_path [list . /path/to/libs /path/to/rtl]
set target_library [list typical.db]
set link_library   [list * typical.db]

# 2. 读入 RTL + 细化
analyze -format verilog {src/top.v src/sub.v}
elaborate top_module

# 3. SDC 约束
create_clock -name clk -period 2.0 [get_ports clk]
set_input_delay 0.4 -clock clk [all_inputs]
set_output_delay 0.4 -clock clk [all_outputs]

# 4. 综合
compile_ultra

# 5. 输出
write_file -format verilog -hierarchy -output report/synth.v
write_sdc report/synth.sdc

# 6. 报告
report_area  > report/area.rpt
report_timing > report/timing.rpt
report_power  > report/power.rpt
report_qor    > report/qor.rpt

exit
```

---

## 3. Agent 操作指南

### 3.1 使用 `help` 和 `man` 命令

```tcl
help                    ;# 列出所有命令
help -verbose           ;# 列出所有命令及简要描述
help compile_ultra      ;# 查看 compile_ultra 的详细用法
man compile_ultra       ;# 查看 compile_ultra 的 man 页面
man get_ports           ;# 查看 get_ports 的 man 页面
```

### 3.2 错误处理策略

dc_shell 的错误消息格式为 `Error: <message> (错误码)`。

#### 常见错误及处理

| 错误模式 | 含义 | 处理方式 |
|---------|------|---------|
| `Error: Can't find lib_cell ...` | 工艺库中找不到指定单元 | 检查 `target_library` / `link_library` 配置，确认库文件路径正确 |
| `Error: Module 'X' is not defined.` | 未定义模块 | 检查 `analyze` 是否成功，文件名和路径是否正确 |
| `Error: Design 'X' not found.` | 未找到设计 | 检查 `elaborate` 是否执行，设计名拼写是否正确 |
| `Error: current_design is not defined.` | 当前设计未设置 | 先执行 `elaborate <top>` 或 `current_design <name>` |
| `Error: target library not set.` | 未配置目标库 | 先 `set target_library <libs>` |
| `Error: link library not set.` | 未配置链接库 | 先 `set link_library [list * <libs>]`，注意 `*` 表示当前设计 |
| `Error: Can't find file ...` | 文件不存在 | 检查 `search_path` 和文件路径 |
| `Warning: Unable to resolve reference ...` | 无法解析引用 | 检查 `link_library` 是否包含所需库，`*` 是否在首位 |

#### Agent 错误处理流程

```
1. 捕获错误消息
2. 检查库配置状态：
   - get_app_var target_library
   - get_app_var link_library
3. 检查当前设计状态：
   - current_design
4. 根据上表确定处理策略
5. 若无法定位，使用 help/man 查询相关命令
6. 重试最多 3 次，若仍失败则报告给用户
```

#### 关键前置检查

```tcl
# 检查库配置
set libs [get_app_var target_library]
if {$libs eq ""} {
    error "target_library is not set. Please configure target_library first."
}

# 检查当前设计
set cur_design [current_design]
if {$cur_design eq ""} {
    error "No current design. Please elaborate a design first."
}
```

#### 常用诊断命令

```tcl
current_design              ;# 返回当前设计名
get_app_var target_library  ;# 查看目标库
get_app_var link_library    ;# 查看链接库
get_app_var search_path     ;# 查看搜索路径
list_designs                ;# 列出所有已加载的设计
list_libs                   ;# 列出所有已加载的库
```

---

## 4. 核心命令详解

### 4.1 库与路径配置

dc_shell 通过全局 Tcl 变量配置工艺库，而非通过命令参数。这些变量**必须在**读入设计之前设置。

#### `set target_library` — 设置目标工艺库

指定综合时映射到的目标工艺库。可以包含多个 `.db` 文件。

```tcl
set target_library [list typical.db]
set target_library [list typical.db best.db worst.db]
```

#### `set link_library` — 设置链接库

指定解析设计引用所需的所有库。**`*` 必须放在首位**，表示当前内存中的设计。

```tcl
set link_library [list * typical.db]
set link_library [list * typical.db ram.db pad.db]
```

#### `set search_path` — 设置搜索路径

指定 dc_shell 查找文件（.db, .v, .sv, .sdc 等）的目录列表。

```tcl
set search_path [list . /path/to/libs /path/to/rtl /path/to/scripts]
```

#### `set synthetic_library` — 设置综合库（可选）

指定 DesignWare 综合库，用于推断算术/控制逻辑。

```tcl
set synthetic_library [list dw_foundation.sldb]
```

#### `set symbol_library` — 设置符号库（可选）

指定用于 GUI 显示的符号库。

```tcl
set symbol_library [list typical.sdb]
```

#### 完整库配置示例

```tcl
# 设置搜索路径
set search_path [list . \
    /share1/silibraries/nangate45 \
    /home/user/rtl \
    /home/user/scripts]

# 设置库
set target_library    [list NangateOpenCellLibrary_typical.db]
set link_library      [list * NangateOpenCellLibrary_typical.db]
set synthetic_library [list dw_foundation.sldb]
# set symbol_library  [list NangateOpenCellLibrary.sdb]
```

---

### 4.2 设计输入

#### `analyze` — 分析 HDL 文件

将 HDL 文件编译为中间格式（`.pvl` 文件），但不构建设计层次。

```
analyze -format <format> [-library <lib>] [-define <macros>] [-work <lib>] <file_list>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file_list` | list | 是 | HDL 文件列表 |
| `-format` | string | 是 | 文件格式：`verilog`、`sverilog`、`vhdl` |
| `-library` | string | 否 | 库名 |
| `-define` | list | 否 | 宏定义 |
| `-work` | string | 否 | 工作库名，默认 `WORK` |

```tcl
analyze -format verilog {src/top.v src/alu.v src/ctrl.v}
analyze -format sverilog -define {WIDTH=32 DEBUG} {src/top.sv}
analyze -format verilog -library my_lib {src/lib_cells.v}
```

---

#### `elaborate` — 细化设计

构建设计的层次结构，解析所有引用。

```
elaborate <design_name> [-library <lib>] [-parameters <params>] [-update] [-work <lib>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `design_name` | string | 是 | 顶层设计名 |
| `-library` | string | 否 | 设计所在的库 |
| `-parameters` | list | 否 | 参数化设计的具体参数值 |
| `-update` | flag | 否 | 仅更新已细化的设计 |
| `-work` | string | 否 | 工作库名 |

```tcl
elaborate top_module
elaborate top_module -parameters {WIDTH=32 DEPTH=16}
elaborate top_module -library my_lib
```

---

#### `read_verilog` — 读入 Verilog（快捷方式）

不经过 `analyze` 阶段，直接读入 Verilog 文件。适用于简单设计。

```
read_verilog [-netlist] <file_list>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file_list` | list | 是 | Verilog 文件列表 |
| `-netlist` | flag | 否 | 以网表模式读取 |

```tcl
read_verilog {src/top.v src/alu.v}
read_verilog -netlist {src/synth.v}
```

---

#### `read_file` — 读入多种格式文件

通用的文件读入命令，自动检测格式。

```
read_file [-format <format>] [-autoread] <file_list>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file_list` | list | 是 | 文件列表 |
| `-format` | string | 否 | 格式：`verilog`、`sverilog`、`vhdl`、`db`、`ddc`、`sdc` |
| `-autoread` | flag | 否 | 自动检测格式 |

```tcl
read_file -format verilog {src/top.v src/sub.v}
read_file -format db design.db
read_file -autoread {src/top.v libs/ram.db}
```

---

#### `read_vhdl` / `read_sverilog` / `read_ddc` / `read_sdc`

专门格式的快捷读入命令。

```tcl
read_vhdl    {src/top.vhd}
read_sverilog {src/top.sv}
read_ddc     design.ddc
read_sdc     constraints.sdc
```

---

### 4.3 综合

#### 综合命令选择

| 命令 | 适用场景 | 特点 |
|------|---------|------|
| `compile_ultra` | 标准 RTL 综合 | 高级优化，包含 `-gate_clock`、`-retime` 等，推荐首选 |
| `compile` | 简单/快速综合 | 基础优化，较少选项 |

> **注意**：`compile_ultra` 需要 Design Compiler Ultra 或更高版本的 license。如果不可用，降级为 `compile`。

#### `compile_ultra` — 高级综合

```
compile_ultra [-gate_clock] [-retime] [-no_autoungroup] [-no_boundary_optimization]
    [-scan] [-timing] [-area_high_effort] [-incremental]
    [-no_seq_output_inversion] [-spg]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `-gate_clock` | flag | 启用时钟门控插入 |
| `-retime` | flag | 启用寄存器重定时 |
| `-no_autoungroup` | flag | 禁止自动展平小层次 |
| `-no_boundary_optimization` | flag | 禁止跨层次边界优化 |
| `-scan` | flag | 启用扫描链替换 |
| `-timing` | flag | 时序驱动优化 |
| `-area_high_effort` | flag | 面积高努力优化 |
| `-incremental` | flag | 增量综合 |
| `-no_seq_output_inversion` | flag | 禁止时序输出反相 |
| `-spg` | flag | 启用 SPG 模式 |

```tcl
# 标准高级综合
compile_ultra

# 带时钟门控和重定时
compile_ultra -gate_clock -retime

# 面积优化，保持层次
compile_ultra -no_autoungroup -area_high_effort

# 增量综合（对已有综合结果做进一步优化）
compile_ultra -incremental
```

---

#### `compile` — 基础综合

```
compile [-map_effort <low|medium|high>] [-area_effort <none|low|medium|high>]
    [-boundary_optimization] [-gate_clock] [-scan] [-incremental]
    [-exact_map] [-no_design_rule] [-ungroup_all]
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `-map_effort` | string | 映射努力程度：`low`、`medium`、`high`，默认 `medium` |
| `-area_effort` | string | 面积努力程度：`none`、`low`、`medium`、`high` |
| `-boundary_optimization` | flag | 跨层次边界优化 |
| `-gate_clock` | flag | 启用时钟门控 |
| `-scan` | flag | 启用扫描链替换 |
| `-incremental` | flag | 增量综合 |
| `-exact_map` | flag | 精确映射 |
| `-no_design_rule` | flag | 忽略设计规则 |
| `-ungroup_all` | flag | 展平所有层次 |

```tcl
compile -map_effort high -area_effort high
compile -gate_clock -scan
```

---

### 4.4 设计输出

#### `write_file` — 写出设计

```
write_file -format <format> [-hierarchy] [-output <file>] [<design_list>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `-format` | string | 是 | 输出格式：`verilog`、`vhdl`、`db`、`ddc`、`equation` |
| `-hierarchy` | flag | 否 | 保持层次输出 |
| `-output` | string | 否 | 输出文件名 |
| `design_list` | list | 否 | 设计列表，默认当前设计 |

```tcl
write_file -format verilog -hierarchy -output report/synth.v
write_file -format db -output report/design.db
write_file -format ddc -output report/design.ddc
```

---

#### `write_sdc` — 写出 SDC 约束

```
write_sdc [-version <1.7|2.0|2.1>] [<file>]
```

```tcl
write_sdc report/synth.sdc
write_sdc -version 2.1 report/synth.sdc
```

---

#### `write_sdf` — 写出 SDF 延迟文件

```
write_sdf [-version <2.1|3.0|4.0>] [-significant_digits <int>] [<file>]
```

```tcl
write_sdf report/synth.sdf
write_sdf -significant_digits 4 report/synth.sdf
```

---

#### `write_script` — 写出约束脚本

生成用于后续流程（如 ICC2、PrimeTime）的约束脚本。

```tcl
write_script -output report/design_constraints.tcl
```

---

### 4.5 STA 约束

以下 SDC 命令为主要约束命令，dc_shell 遵循 SDC 标准。

#### `create_clock` — 创建时钟

```
create_clock [-name <name>] [-period <float>] [-waveform <float_list>] [-add] [-comment <str>] <source_objects>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `source_objects` | list | 是 | 时钟源端口/pin |
| `-name` | string | 否 | 时钟名称，默认使用端口名 |
| `-period` | float | 否 | 时钟周期（库单位） |
| `-waveform` | list | 否 | 波形 `{rise_edge fall_edge}`，默认 `{0 period/2}` |
| `-add` | flag | 否 | 添加额外时钟源（不覆盖已有） |
| `-comment` | string | 否 | 注释 |

```tcl
create_clock -name clk -period 2.0 [get_ports clk]
create_clock -name clk -period 10.0 -waveform {0 5} [get_ports sys_clk]
create_clock -period 2.5 [get_ports clk1]
```

---

#### `create_generated_clock` — 创建生成时钟

```
create_generated_clock [-name <name>] [-add] -source <master_pin>
    [-master_clock <name>] [-divide_by <int>] [-multiply_by <int>]
    [-duty_cycle <float>] [-invert] [-edges <int_list>] [-edge_shift <float_list>]
    [-combinational] [-comment <str>] <source_objects>
```

```tcl
create_generated_clock -name div_clk -divide_by 2 -source [get_ports clk] [get_pins div_reg/Q]
```

---

#### `current_design` — 设置/获取当前工作设计

```
current_design [<design>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `design` | string | 否 | 设计名；无参数时返回当前设计名 |

```tcl
current_design top_module        ;# 设置当前设计
set cur [current_design]         ;# 获取当前设计名
```

---

#### `set_input_delay` — 设置输入延迟

```
set_input_delay <delay> [-clock <clock>] [-clock_fall] [-rise] [-fall]
    [-min] [-max] [-add_delay] [-network_latency_included]
    [-source_latency_included] [-reference_pin <pin>] <port_pin_list>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `delay` | float | 是 (位置) | 延迟值 |
| `port_pin_list` | list | 是 | 目标端口/pin 列表 |
| `-clock` | string | 否 | 参考时钟名 |
| `-clock_fall` | flag | 否 | 相对时钟下降沿 |
| `-rise` / `-fall` | flag | 否 | 仅上升/下降沿 |
| `-min` / `-max` | flag | 否 | 最小/最大延迟 |
| `-add_delay` | flag | 否 | 追加而非覆盖已有延迟 |

```tcl
set_input_delay 0.4 -clock clk [all_inputs]
set_input_delay 0.2 -clock clk -min [get_ports data_in]
set_input_delay 0.5 -clock clk -max [get_ports data_in]
```

---

#### `set_output_delay` — 设置输出延迟

```
set_output_delay <delay> [-clock <clock>] [-clock_fall] [-rise] [-fall]
    [-min] [-max] [-add_delay] [-network_latency_included]
    [-source_latency_included] [-reference_pin <pin>] <port_pin_list>
```

```tcl
set_output_delay 0.4 -clock clk [all_outputs]
set_output_delay 0.3 -clock clk [get_ports data_out]
```

---

#### `set_drive` — 设置驱动强度

```
set_drive <resistance> [-rise] [-fall] [-min] [-max] <port_list>
```

```tcl
set_drive 0.1 [all_inputs]
set_drive 0.05 [get_ports clk rst_n]
```

---

#### `set_driving_cell` — 设置驱动单元

```
set_driving_cell -lib_cell <cell> [-library <lib>] [-pin <pin>]
    [-rise] [-fall] [-min] [-max] [-dont_scale] [-no_design_rule]
    [-input_transition_rise <float>] [-input_transition_fall <float>]
    [-multiply_by <float>] <port_list>
```

```tcl
set_driving_cell -lib_cell BUF_X4 -library typical [all_inputs]
set_driving_cell -lib_cell DFF_X1 -pin Q [get_ports data_in]
```

---

#### `set_load` — 设置负载电容

```
set_load <load> [-min] [-max] [-subtract_pin_load] [-pin_load] [-wire_load] <object_list>
```

```tcl
set_load 0.05 [all_outputs]
set_load 0.02 [get_ports data_out]
```

---

#### `set_false_path` — 设置伪路径

```
set_false_path [-rise] [-fall] [-setup] [-hold]
    [-from <objects>] [-through <objects>] [-to <objects>]
    [-rise_from <objects>] [-fall_from <objects>]
    [-rise_through <objects>] [-fall_through <objects>]
    [-rise_to <objects>] [-fall_to <objects>]
    [-comment <str>]
```

```tcl
set_false_path -from [get_ports rst_n]
set_false_path -from [get_clocks clk1] -to [get_clocks clk2]
set_false_path -through [get_pins u_ctrl/scan_enable]
```

---

#### `set_multicycle_path` — 设置多周期路径

```
set_multicycle_path <path_multiplier> [-rise] [-fall] [-setup] [-hold]
    [-start] [-end] [-from <objects>] [-through <objects>] [-to <objects>]
    [-rise_from <objects>] [-fall_from <objects>]
    [-rise_through <objects>] [-fall_through <objects>]
    [-rise_to <objects>] [-fall_to <objects>]
    [-comment <str>]
```

```tcl
set_multicycle_path 2 -from [get_ports A] -to [get_ports Z]
set_multicycle_path 3 -setup -from [get_clocks slow_clk] -to [get_clocks fast_clk]
set_multicycle_path 2 -hold  -from [get_clocks slow_clk] -to [get_clocks fast_clk]
```

---

#### `set_clock_groups` — 设置时钟组

```
set_clock_groups [-name <name>] [-group <group_list>]
    [-physically_exclusive] [-logically_exclusive] [-asynchronous]
    [-allow_paths] [-comment <str>]
```

```tcl
set_clock_groups -asynchronous -group {clk_a} -group {clk_b}
set_clock_groups -logically_exclusive -group {clk1 clk2} -group {clk3}
```

---

#### `set_clock_uncertainty` — 设置时钟不确定性

```
set_clock_uncertainty <uncertainty> [-from <clock>] [-to <clock>]
    [-rise] [-fall] [-setup] [-hold] [<object_list>]
```

```tcl
set_clock_uncertainty 0.1 [get_clocks clk]
set_clock_uncertainty 0.05 -setup [get_clocks clk]
set_clock_uncertainty 0.02 -hold  [get_clocks clk]
```

---

#### `set_clock_latency` — 设置时钟延迟

```
set_clock_latency <delay> [-clock <clock>] [-source] [-rise] [-fall]
    [-min] [-max] [-early] [-late] [-dynamic <float>] [<object_list>]
```

```tcl
set_clock_latency 0.5 [get_clocks clk]
set_clock_latency 0.8 -source [get_clocks clk]
```

---

#### `set_clock_transition` — 设置时钟跳变

```
set_clock_transition <transition> [-rise] [-fall] [-min] [-max] <clock_list>
```

```tcl
set_clock_transition 0.1 [get_clocks clk]
set_clock_transition 0.05 -min [get_clocks clk]
set_clock_transition 0.15 -max [get_clocks clk]
```

---

#### `set_input_transition` — 设置输入跳变

```
set_input_transition <transition> [-rise] [-fall] [-min] [-max] <port_list>
```

```tcl
set_input_transition 0.1 [all_inputs]
set_input_transition 0.05 [get_ports data_in]
```

---

#### `set_max_fanout` — 设置最大扇出

```
set_max_fanout <fanout> [<object_list>]
```

```tcl
set_max_fanout 20 [current_design]
set_max_fanout 10 [get_ports critical_out]
```

---

#### `set_max_capacitance` — 设置最大电容

```
set_max_capacitance <capacitance> [<object_list>]
```

```tcl
set_max_capacitance 0.5 [all_outputs]
```

---

#### `set_max_transition` — 设置最大跳变

```
set_max_transition <transition> [-data_path] [-clock_path] [<object_list>]
```

```tcl
set_max_transition 0.3 [current_design]
set_max_transition 0.15 -clock_path [get_clocks clk]
```

---

#### `set_max_area` — 设置最大面积

```
set_max_area <area>
```

```tcl
set_max_area 0
set_max_area 5000
```

---

#### `set_case_analysis` — 设置 case 分析

```
set_case_analysis <value> <pin_port_list>
```

| value | 说明 |
|-------|------|
| `0` | 逻辑 0 |
| `1` | 逻辑 1 |
| `rising` | 上升沿 |
| `falling` | 下降沿 |

```tcl
set_case_analysis 0 [get_ports scan_enable]
set_case_analysis 1 [get_ports test_mode]
```

---

#### `remove_case_analysis` — 移除 case 分析

```
remove_case_analysis [-all] [<pin_port_list>]
```

```tcl
remove_case_analysis -all
remove_case_analysis [get_ports scan_enable]
```

---

#### `set_operating_conditions` — 设置工作条件

```
set_operating_conditions [-min <cond>] [-max <cond>] [-analysis_type <type>]
    [-library <lib>] [<object_list>]
```

```tcl
set_operating_conditions typical
set_operating_conditions -min min_cond -max max_cond
```

---

#### `set_timing_derate` — 设置时序减免

```
set_timing_derate [-early] [-late] [-rise] [-fall]
    [-cell_delay] [-net_delay] [-data] [-clock] [-cell_check]
    <derate_value> [<object_list>]
```

```tcl
set_timing_derate -early 0.9 -cell_delay [current_design]
set_timing_derate -late  1.1 -cell_delay [current_design]
```

---

#### `set_disable_timing` — 禁用时序弧

```
set_disable_timing [-from <pin>] [-to <pin>] [<object_list>]
```

```tcl
set_disable_timing [get_cells u_mux]
set_disable_timing -from A -to Z [get_cells u_gate]
```

---

#### `group_path` — 路径分组

```
group_path [-name <name>] [-weight <float>] [-critical_range <float>]
    [-from <objects>] [-through <objects>] [-to <objects>]
    [-default] [-comment <str>]
```

```tcl
group_path -name critical_path -weight 10 -from [get_ports A] -to [get_ports Z]
group_path -name default_path -default
```

---

#### `set_propagated_clock` — 设置传播时钟

```
set_propagated_clock [<object_list>]
```

综合后使用，告知工具使用实际时钟网络延迟。

```tcl
set_propagated_clock [all_clocks]
```

---

### 4.6 报告

#### `report_area` — 报告面积

```
report_area [-nosplit] [-hierarchy] [-physical] [-design_rule] [-verbose]
```

```tcl
report_area
report_area -hierarchy
report_area > report/area.rpt
```

---

#### `report_timing` — 报告时序

```
report_timing [-max_paths <int>] [-nworst <int>] [-slack_lesser_than <float>]
    [-slack_greater_than <float>] [-significant_digits <int>]
    [-from <objects>] [-through <objects>] [-to <objects>]
    [-rise] [-fall] [-early] [-late] [-nosplit]
    [-input_pins] [-net] [-capacitance] [-derate]
    [-sort_by <field>] [-group <group_name>] [-path_type <type>]
    [-delay_type <type>] [-verbose]
```

```tcl
report_timing
report_timing -nworst 10 -slack_lesser_than 0.1
report_timing -from [get_ports A] -to [get_ports Z]
report_timing -delay_type max
report_timing -delay_type min
```

---

#### `report_power` — 报告功耗

```
report_power [-hierarchy] [-nosplit] [-verbose] [-significant_digits <int>]
```

```tcl
report_power
report_power -hierarchy
report_power > report/power.rpt
```

---

#### `report_qor` — 报告综合质量

```
report_qor [-significant_digits <int>] [-nosplit]
```

```tcl
report_qor
report_qor > report/qor.rpt
```

---

#### `report_constraint` — 报告约束违例

```
report_constraint [-all_violators] [-verbose] [-significant_digits <int>]
    [-max_delay] [-min_delay] [-max_capacitance] [-min_capacitance]
    [-max_transition] [-max_fanout] [-max_area] [-nosplit]
```

```tcl
report_constraint -all_violators -verbose
report_constraint -max_transition -max_fanout
```

---

#### `report_design` — 报告设计属性

```
report_design [-nosplit] [-physical]
```

```tcl
report_design
```

---

#### `report_port` — 报告端口

```
report_port [-verbose] [-nosplit] [-significant_digits <int>] [<port_list>]
```

```tcl
report_port
report_port -verbose [get_ports clk]
```

---

#### `report_cell` — 报告单元

```
report_cell [-nosplit] [-connections] [-verbose] [<cell_list>]
```

```tcl
report_cell
report_cell [get_cells -hierarchical *]
```

---

#### `report_net` — 报告线网

```
report_net [-nosplit] [-connections] [-verbose] [-significant_digits <int>] [<net_list>]
```

```tcl
report_net
report_net -connections [get_nets clk]
```

---

#### `report_hierarchy` — 报告层次

```
report_hierarchy [-nosplit] [-full] [-noleaf]
```

```tcl
report_hierarchy
report_hierarchy -full
```

---

#### `report_lib` — 报告工艺库

```
report_lib [-cell <cell>] [-timing] [-power] [<lib_name>]
```

```tcl
report_lib typical
report_lib -cell BUF_X4 typical
```

---

#### `report_clock_gating` — 报告时钟门控

```
report_clock_gating [-nosplit] [-verbose]
```

```tcl
report_clock_gating
```

---

#### `report_reference` — 报告引用

```
report_reference [-nosplit] [-hierarchy]
```

```tcl
report_reference -hierarchy
```

---

#### `check_design` — 设计检查

```
check_design [-summary] [-nosplit] [-multiple_designs] [-html <file>]
```

```tcl
check_design
check_design -summary
```

---

#### `check_timing` — 时序检查

检查是否有未约束的路径。

```
check_timing [-verbose] [-include <type_list>]
```

```tcl
check_timing
check_timing -verbose
```

---

### 4.7 日志与重定向

#### `redirect` — 命令输出重定向

```
redirect [-append] [-tee] [-file] [-variable <var>] <target> <command_string>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `target` | string | 是 | 目标文件名或变量名 |
| `command_string` | string | 是 | 要执行的命令（用大括号括起） |
| `-append` | flag | 否 | 追加模式 |
| `-tee` | flag | 否 | 同时输出到屏幕和文件 |
| `-file` | flag | 否 | 输出到文件（默认） |
| `-variable` | flag | 否 | 输出到 Tcl 变量 |

```tcl
redirect -tee report/timing.rpt {report_timing}
redirect -variable my_var {get_ports}
redirect -append report/log.rpt {report_area}
```

---

#### Tcl 原生重定向

```tcl
report_area  > report/area.rpt       ;# 覆盖写入
report_area >> report/area.rpt       ;# 追加写入
```

---

#### 日志文件记录

```tcl
# 使用 shell 重定向运行 dc_shell
# dc_shell -f run.tcl -output_log_file run.log
```

---

## 5. 查询命令速查

| 命令 | 说明 | 关键参数 |
|------|------|---------|
| `get_ports` | 获取端口集合 | `-hierarchical`, `-quiet`, `-filter`, `patterns` (位置) |
| `get_pins` | 获取 pin 集合 | `-hierarchical`, `-quiet`, `-filter`, `-leaf`, `patterns` (位置) |
| `get_cells` | 获取 cell 集合 | `-hierarchical`, `-quiet`, `-filter`, `patterns` (位置) |
| `get_nets` | 获取 net 集合 | `-hierarchical`, `-quiet`, `-filter`, `patterns` (位置) |
| `get_clocks` | 获取时钟集合 | `-quiet`, `-filter`, `patterns` (位置) |
| `get_libs` | 获取库集合 | `-quiet`, `-filter`, `patterns` (位置) |
| `get_lib_cells` | 获取库单元集合 | `-quiet`, `-filter`, `patterns` (位置) |
| `get_lib_pins` | 获取库 pin 集合 | `-quiet`, `-filter`, `patterns` (位置) |
| `get_designs` | 获取设计集合 | `-quiet`, `-filter`, `patterns` (位置) |
| `all_clocks` | 获取所有时钟 | 无参数 |
| `all_inputs` | 获取所有输入端口 | `-no_clocks`（排除时钟端口） |
| `all_outputs` | 获取所有输出端口 | 无参数 |
| `all_registers` | 获取所有寄存器 | `-no_hierarchy`, `-clock`, `-cells`, `-data_pins`, `-clock_pins`, `-output_pins`, `-level_sensitive`, `-edge_triggered` |
| `all_connected` | 获取连接对象 | `-leaf`, `object` (位置) |
| `sizeof_collection` | 集合大小 | `collection` (位置) |
| `query_objects` | 按序显示集合对象 | `objects` (位置) |
| `get_object_name` | 获取对象全名 | `object` (位置) |
| `add_to_collection` | 添加对象到集合 | `target_collection` (位置), `object_spec` (位置) |
| `remove_from_collection` | 从集合移除对象 | `target_collection` (位置), `remove_object` (位置) |
| `filter_collection` | 过滤集合 | `collection` (位置), `expression` (位置) |
| `get_attribute` | 获取属性值 | `object_list` (位置), `attribute_name` (位置), `-quiet` |
| `set_attribute` | 设置属性值 | `object_list` (位置), `attribute_name` (位置), `attribute_value` (位置) |
| `list_designs` | 列出所有设计 | 无参数 |
| `list_libs` | 列出所有库 | 无参数 |
| `current_design` | 获取/设置当前设计 | `design` (位置) |

---

## 6. 配置命令速查

| 命令 | 说明 | 关键参数 |
|------|------|---------|
| `set_app_var` | 设置应用变量 | `name` (位置), `value` (位置) |
| `get_app_var` | 获取应用变量 | `name` (位置) |
| `set target_library` | 设置目标库 | 值为库文件列表 |
| `set link_library` | 设置链接库 | 值为 `[list * ...]` |
| `set search_path` | 设置搜索路径 | 值为目录列表 |
| `set synthetic_library` | 设置综合库 | 值为 .sldb 文件 |
| `set symbol_library` | 设置符号库 | 值为 .sdb 文件 |
| `set_dont_use` | 禁用库单元 | `object_list` (位置) |
| `set_dont_touch` | 禁止优化 | `object_list` (位置) |
| `set_ideal_network` | 设置理想网络 | `-no_propagate`, `object_list` (位置) |
| `set_ideal_latency` | 设置理想延迟 | `delay` (位置), `object_list` (位置) |
| `set_ideal_transition` | 设置理想跳变 | `transition_time` (位置), `object_list` (位置) |
| `ungroup` | 展平层次 | `-flatten`, `-all`, `-start_level`, `cell_list` (位置) |
| `group` | 创建新层次 | `-design_name`, `-cell_name`, `cell_set` (位置) |
| `uniquify` | 唯一化实例 | `-force`, `design_list` (位置) |
| `set_clock_gating_style` | 设置时钟门控风格 | `-pos`, `-neg`, `-control_point`, `-max_fanout`, `-min_bitwidth` |

---

## 7. 完整脚本模板

> **Agent 注意**：以下模板中 `<<<...>>>` 为占位符，agent 执行前必须替换为实际值。
> 常见占位符：
> - `<<<LIB_DIR>>>` → 工艺库 .db 文件所在目录
> - `<<<LIB_NAME>>>` → 目标库 .db 文件名
> - `<<<SRC_DIR>>>` → RTL 源文件目录
> - `<<<TOP_MODULE>>>` → 顶层模块名
> - `<<<CLK_PORT>>>` → 顶层时钟端口名（通常为 `clk`）
> - `<<<CLK_PERIOD>>>` → 时钟周期（库单位），如 `2.0`

### 模板 1：RTL 综合标准流程

```tcl
# ============================================================
# dc_shell RTL 综合标准流程
# 用法: dc_shell -f this_script.tcl
# ============================================================

# ---- 1. 库与路径配置 ----
set search_path [list . <<<LIB_DIR>>> <<<SRC_DIR>>>]
set target_library    [list <<<LIB_NAME>>>]
set link_library      [list * <<<LIB_NAME>>>]
# set synthetic_library [list dw_foundation.sldb]
# set symbol_library   [list <<<LIB_NAME>>>.sdb]

# ---- 2. 读入 RTL 设计 ----
# 方式 A: analyze + elaborate（推荐）
analyze -format verilog {
    <<<SRC_DIR>>>/module_a.v
    <<<SRC_DIR>>>/module_b.v
    <<<SRC_DIR>>>/top.v
}
elaborate <<<TOP_MODULE>>>

# 方式 B: read_verilog（快捷方式）
# read_verilog {<<<SRC_DIR>>>/top.v <<<SRC_DIR>>>/sub.v}

# ---- 3. 检查设计 ----
current_design
check_design

# ---- 4. SDC 约束 ----
# 时钟定义
set clk_name       core_clock
set clk_port_name  <<<CLK_PORT>>>
set clk_period     <<<CLK_PERIOD>>>
set clk_port       [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port

# 输入/输出延迟
set_input_delay  [expr $clk_period * 0.2] -clock $clk_name [all_inputs]
set_output_delay [expr $clk_period * 0.2] -clock $clk_name [all_outputs]

# 负载
set_load 0.05 [all_outputs]

# 时钟不确定性
set_clock_uncertainty [expr $clk_period * 0.05] -setup [get_clocks $clk_name]
set_clock_uncertainty [expr $clk_period * 0.02] -hold  [get_clocks $clk_name]

# 设计规则
set_max_fanout    20 [current_design]
set_max_transition 0.3 [current_design]

# 检查约束完整性
check_timing

# ---- 5. 综合 ----
compile_ultra

# 如需传播时钟（综合后使用实际时钟网络）
# set_propagated_clock [all_clocks]

# ---- 6. 输出 ----
write_file -format verilog -hierarchy -output report/synth.v
write_sdc  report/synth.sdc
# write_sdf  report/synth.sdf

# ---- 7. 报告 ----
report_area       > report/area.rpt
report_timing     > report/timing.rpt
report_power      > report/power.rpt
report_qor        > report/qor.rpt
report_constraint -all_violators > report/constraint.rpt
report_clock_gating > report/clock_gating.rpt

# ---- 8. 退出 ----
exit
```

### 模板 2：带高级优化的综合流程

```tcl
# ============================================================
# dc_shell 高级综合流程（时钟门控 + 重定时）
# 用法: dc_shell -f this_script.tcl
# ============================================================

# ---- 1. 库配置 ----
set search_path [list . <<<LIB_DIR>>> <<<SRC_DIR>>>]
set target_library    [list <<<LIB_NAME>>>]
set link_library      [list * <<<LIB_NAME>>>]
set synthetic_library [list dw_foundation.sldb]

# ---- 2. 读入设计 ----
analyze -format verilog {
    <<<SRC_DIR>>>/module_a.v
    <<<SRC_DIR>>>/module_b.v
    <<<SRC_DIR>>>/top.v
}
elaborate <<<TOP_MODULE>>>

# ---- 3. 时钟约束 ----
set clk_name       core_clock
set clk_port_name  <<<CLK_PORT>>>
set clk_period     <<<CLK_PERIOD>>>
set clk_port       [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port

# ---- 4. IO 约束 ----
set_input_delay  [expr $clk_period * 0.2] -clock $clk_name [all_inputs]
set_output_delay [expr $clk_period * 0.2] -clock $clk_name [all_outputs]
set_driving_cell -lib_cell BUF_X4 [all_inputs]
set_load 0.05 [all_outputs]

# ---- 5. 时钟门控配置 ----
set_clock_gating_style -pos integrated \
    -max_fanout 16 \
    -min_bitwidth 3 \
    -control_point before

# ---- 6. 高级综合 ----
compile_ultra -gate_clock -retime -no_autoungroup

# ---- 7. 输出 ----
write_file -format verilog -hierarchy -output report/synth.v
write_sdc  report/synth.sdc

# ---- 8. 报告 ----
report_area       > report/area.rpt
report_timing     > report/timing.rpt
report_power      > report/power.rpt
report_qor        > report/qor.rpt
report_constraint -all_violators > report/constraint.rpt
report_clock_gating > report/clock_gating.rpt

exit
```

---

## 8. 命令索引

### 库与路径
`set target_library` · `set link_library` · `set search_path` · `set synthetic_library` · `set symbol_library`

### 设计输入
`analyze` · `elaborate` · `read_verilog` · `read_file` · `read_vhdl` · `read_sverilog` · `read_ddc` · `read_sdc`

### 综合
`compile_ultra` · `compile`

### 综合前处理
`ungroup` · `group` · `uniquify` · `set_clock_gating_style`

### 设计输出
`write_file` · `write_sdc` · `write_sdf` · `write_script`

### STA 约束
`create_clock` · `create_generated_clock` · `current_design` · `set_input_delay` · `set_output_delay` · `set_drive` · `set_driving_cell` · `set_load` · `set_false_path` · `set_multicycle_path` · `set_clock_groups` · `set_clock_uncertainty` · `set_clock_latency` · `set_clock_transition` · `set_input_transition` · `set_max_fanout` · `set_max_capacitance` · `set_max_transition` · `set_max_area` · `set_case_analysis` · `remove_case_analysis` · `set_operating_conditions` · `set_timing_derate` · `set_disable_timing` · `group_path` · `set_propagated_clock` · `set_ideal_network` · `set_ideal_latency` · `set_ideal_transition`

### 报告
`report_area` · `report_timing` · `report_power` · `report_qor` · `report_constraint` · `report_design` · `report_port` · `report_cell` · `report_net` · `report_hierarchy` · `report_lib` · `report_reference` · `report_clock_gating` · `check_design` · `check_timing`

### 查询
`get_ports` · `get_pins` · `get_cells` · `get_nets` · `get_clocks` · `get_libs` · `get_lib_cells` · `get_lib_pins` · `get_designs` · `all_clocks` · `all_inputs` · `all_outputs` · `all_registers` · `all_connected` · `sizeof_collection` · `query_objects` · `get_object_name` · `add_to_collection` · `remove_from_collection` · `filter_collection` · `get_attribute` · `set_attribute` · `list_designs` · `list_libs` · `current_design`

### 配置
`set_app_var` · `get_app_var` · `set_dont_use` · `set_dont_touch`

### 日志与工具
`redirect` · `help` · `man` · `exit` · `quit`
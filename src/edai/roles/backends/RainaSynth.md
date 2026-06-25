# RainaSynth 使用文档（Agent 版）

> **受众**：调用 RainaSynth 的 AI agent。本文档提供精确的命令签名、参数类型、典型流程和完整脚本模板。

---

## 目录

1. [概述](#1-概述)
2. [典型工作流](#2-典型工作流)
3. [Agent 操作指南](#3-agent-操作指南)
4. [核心命令详解](#4-核心命令详解)
   - [4.1 设计输入](#41-设计输入)
   - [4.2 综合](#42-综合)
   - [4.3 设计输出](#43-设计输出)
   - [4.4 STA 约束](#44-sta-约束)
   - [4.5 报告](#45-报告)
   - [4.6 日志与重定向](#46-日志与重定向)
5. [ECO / 网表编辑命令速查](#5-eco--网表编辑命令速查)
6. [查询命令速查](#6-查询命令速查)
7. [配置与工具命令速查](#7-配置与工具命令速查)
8. [GUI 命令](#8-gui-命令)
9. [完整脚本模板](#9-完整脚本模板)
10. [命令索引](#10-命令索引)

---

## 1. 概述

RainaSynth 是一个 EDA 综合工具，通过 Tcl 接口交互。主要功能：

- 读入 RTL 设计文件（Verilog/SystemVerilog）和工艺库（Liberty/DB）
- 执行逻辑综合（`synth`）或网表综合（`synth_netlist`）
- 施加 STA 时序约束并分析
- 输出综合后网表、报告
- 支持 ECO 网表编辑

### 运行方式

```bash
./raina_synth -f run.tcl        # 执行 Tcl 脚本
./raina_synth                    # 交互模式
```

### 命令约定

- 选项格式：`-option_name value`
- 布尔选项：`-flag` 表示启用，无 `-flag` 表示禁用
- 位置参数：无需选项名的参数，按顺序传递
- 集合对象：`get_*` 命令返回对象集合，可传递给其他命令

---

## 2. 典型工作流

基于 `regressioncases/Basic/` 下的回归案例总结，RainaSynth 的标准使用流程如下：

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 读入设计文件    read_verilog / read_file / analyze       │
│ 2. 读入工艺库      read_liberty                              │
│ 3. （可选）展平/分组  elaborate / ungroup / group             │
│ 4. 执行综合         synth -top <top>                         │
│ 5. 输出网表         write_file -netlist <file>               │
│ 6. 施加 STA 约束    create_clock / set_input_delay ...       │
│ 7. 生成报告         report_area / report_timing / ...        │
│ 8. 退出             exit                                     │
└─────────────────────────────────────────────────────────────┘
```

### 最小完整示例

```tcl
# 1. 读入
read_verilog src/design.v
read_liberty /path/to/NangateOpenCellLibrary_typical.lib

# 2. 综合
synth -top top_module

# 3. 输出
write_file -netlist report/synth.v

# 4. STA 约束
set clk_port [get_ports clk]
create_clock -name core_clock -period 0.46 $clk_port

# 5. 报告
report_area  > report/area.rpt
report_timing > report/timing.rpt
report_power  > report/power.rpt
report_qor    > report/qor.rpt

exit
```

---

## 3. Agent 操作指南

### 3.1 使用 `help` 命令

`help` 命令列出所有可用的命令。当遇到不确定的命令签名或参数时，agent 应优先使用 `help` 查询，而非猜测。

```tcl
help                    ;# 列出所有命令
help synth              ;# 查看 synth 命令的详细用法
help get_ports          ;# 查看 get_ports 命令的详细用法
```

### 3.2 错误处理策略

RainaSynth 的错误消息遵循 `[Error-<Module>_<Code>]` 格式，信息消息遵循 `[Info-<Module>_<Code>]` 格式。

#### 常见错误及处理

| 错误模式 | 含义 | 处理方式 |
|---------|------|---------|
| 命令执行后无输出或报语法错误 | 可能缺少 `current_design` | 先执行 `current_design_name` 检查当前设计；若为空，用 `current_design <name>` 设置 |
| `[Error-ECO_053] Design 'X' already exists.` | 设计名重复 | 先用 `remove_design` 移除旧设计，或改用不同名称 |
| `[Error-ECO_008] Net 'X' is already exist.` | 线网名冲突 | 目标线网已存在，无需创建；或先 `remove_net` |
| `[Error-ECO_007] Can not find parent cell 'X'` | 父 cell 不存在 | 检查层次路径是否正确，用 `get_cells` 确认 |
| `[Error-ECO_018] Can't create_net for instance 'X' which is leaf cell.` | 对叶子单元创建 net | 叶子单元是库单元，不能在其中创建 net |
| `[Error-ECO_014] Cannot perform create_net on the instance 'X' because it is not unique.` | 实例非唯一化 | 需要先 uniquify 该实例 |
| `[Info-ECO_061] Removing design 'X'.` | 设计被移除 | 之后的 `current_design_name` 将返回空，需重新设置当前设计 |

#### Agent 错误处理流程

```
1. 捕获错误消息
2. 解析错误码（如 ECO_053）
3. 根据上表确定处理策略
4. 若无法定位，使用 help 查询相关命令，或检查 current_design 状态
5. 重试最多 3 次，若仍失败则报告给用户
```

#### 关键前置检查

在执行任何网表操作（ECO 命令、查询命令）前，确保：

```tcl
# 检查当前设计是否已设置
set cur_design [current_design_name]
if {$cur_design eq ""} {
    # 当前无设计：需要先读入设计并综合，或 create_design
    error "No current design. Please read and synthesize a design first."
}
```

---

## 4. 核心命令详解

### 4.1 设计输入

#### `read_verilog` — 读入 Verilog 文件

```
read_verilog [-netlist] <file>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file` | STRING | 是 (位置) | Verilog 文件路径 |
| `-netlist` | flag | 否 | 以网表模式读取 |

**多文件设计**：多次调用 `read_verilog`，每次读入一个文件。

```tcl
# RTL 模式
read_verilog src/top.v
read_verilog src/sub.v

# 网表模式
read_verilog -netlist src/synth.v
```

**注意**：`read_verilog` 读入文件后不自动做顶层绑定，需在 `synth` 阶段通过 `-top` 指定。

---

#### `read_file` — 读入设计文件（支持参数化）

```
read_file [-f <file>] [-define <macros>] [-work <lib>] [-format <fmt>] [-top <name>] [-param <params>] <file_list>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file_list` | STRLIST | 是 (位置) | 设计文件列表 |
| `-f` | STRING | 否 | 从文件读取文件列表 |
| `-define` | STRLIST | 否 | 顶层宏定义 |
| `-work` | STRING | 否 | 工作库名称 |
| `-format` | STRING | 否 | 文件格式：`verilog` 或 `sv`，默认 `verilog` |
| `-top` | STRING | 否 | 指定顶层模块 |
| `-param` | STRLIST | 否 | 设计参数 |

```tcl
read_file -format sv -top my_top -define {MACRO1 MACRO2=5} {src/top.sv src/sub.sv}
```

---

#### `analyze` — 分析 HDL 文件（别名：`run_analyze`）

```
analyze [-f <file>] [-format <fmt>] [-work <lib>] [-define <macros>] [-top <name>] [-incdir <dirs>] [-undef <macros>] <file_list>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file_list` | STRLIST | 是 (位置) | 待分析文件列表 |
| `-f` | STRING | 否 | 从文件读取文件列表 |
| `-format` | STRING | 否 | `verilog` 或 `sv`，默认 `verilog` |
| `-work` | STRING | 否 | 工作库 |
| `-define` | STRLIST | 否 | 宏定义 |
| `-top` | STRING | 否 | 顶层模块 |
| `-incdir` | STRLIST | 否 | include 目录 |
| `-undef` | STRLIST | 否 | 取消宏定义 |

---

#### `elaborate` — 细化设计（别名：`run_elaborate`）

在综合前构建设计的层次结构。通常与 `ungroup -flatten` 配合使用。

```
elaborate [-work <lib>] [-param <params>] <design_name>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `design_name` | STRING | 是 (位置) | 要细化的设计名 |
| `-work` | STRING | 否 | 工作库 |
| `-param` | STRLIST | 否 | 设计参数 |

```tcl
# 多文件 + elaborate + flatten 流程
read_verilog src/a.v
read_verilog src/b.v
read_liberty /path/to/lib.lib
elaborate
ungroup -flatten -all
synth -top top_module
```

---

#### `read_liberty` — 读入 Liberty 工艺库

```
read_liberty [-db] [-output_cell_analyze <file>] <files>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `files` | STRLIST | 是 (位置) | Liberty 文件路径列表 |
| `-db` | flag | 否 | 以 DB 格式读取 |
| `-output_cell_analyze` | STRING | 否 | 输出 cell 分析报告到文件 |

```tcl
read_liberty /share1/silibraries/nangate45/NangateOpenCellLibrary_typical.lib
```

---

#### `read_db` — 读入设计数据库

```
read_db <file>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file` | STRING | 是 (位置) | DB 文件路径 |

---

### 4.2 综合

#### 综合命令选择

| 输入类型 | 读取命令 | 综合命令 | 适用场景 |
|---------|---------|---------|---------|
| RTL (.v/.sv) | `read_verilog` 或 `read_file` | `synth -top <top>` | 从 RTL 源码开始综合 |
| 网表 (.v) | `read_verilog -netlist` | `synth_netlist -top <top>` | 已有综合网表，做优化/ECO/STA 分析 |

> **注意**：`synth` 和 `synth_netlist` 不可互换。如果用 `read_verilog -netlist` 读入网表，必须用 `synth_netlist` 而非 `synth`。

#### `synth` — 通用综合（别名：`run_synth`）

```
synth [-top <name>] [-area] [-hierarchical] [-no_boundary_optimization]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `-top` | STRING | 否 | 顶层模块名（如未在 read 阶段指定则必须） |
| `-area` | BOOL | 否 | 启用面积驱动综合 |
| `-hierarchical` | BOOL | 否 | 按拓扑顺序层次化综合 |
| `-no_boundary_optimization` | flag | 否 | 禁止层次边界优化 |

```tcl
# 标准综合
synth -top top

# 面积优化综合
synth -top top -area true

# 层次化综合
synth -top top -hierarchical true
```

---

#### `synth_netlist` — 网表综合（别名：`run_synth_netlist`）

用于对已读取的网表进行综合优化。

```
synth_netlist [-top <name>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `-top` | STRING | 否 | 顶层模块名 |

```tcl
# 网表综合流程
read_verilog -netlist src/synth.v
read_liberty /path/to/lib.lib
synth_netlist -top top
write_file -netlist report/synth_out.v
```

---

#### `ungroup` — 展平层次

```
ungroup [-prefix <str>] [-all] [-flatten] [-start_level <int>] [<cell_list>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `cell_list` | STRLIST | 否 (位置) | 要展平的 cell 列表 |
| `-all` | flag | 否 | 展平所有 cell（与 cell_list 冲突） |
| `-flatten` | flag | 否 | 展平所有层次（与 start_level 冲突） |
| `-start_level` | INT | 否 | 从指定层级开始展平 |
| `-prefix` | STRING | 否 | 命名 cell 的前缀 |

```tcl
ungroup -flatten -all
```

---

#### `group` — 创建新层次

```
group [-design_name <name>] [-cell_name <name>] <cell_set>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `cell_set` | STRLIST | 是 (位置) | 要归组的 cell |
| `-design_name` | STRING | 至少一 | 新层次的设计名 |
| `-cell_name` | STRING | 至少一 | 新层次的 cell 名 |

---

#### `optimize` — 优化网表

```
optimize [-remapping <bool>] [-physical <bool>] [-resynth <bool>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `-remapping` | BOOL | 否 | 时序驱动映射，默认 false |
| `-physical` | BOOL | 否 | 包含物理优化，默认 false |
| `-resynth` | BOOL | 否 | 使用重综合迭代优化，默认 false |

---

#### `resyn` — 映射后网表重综合

```
resyn [-target <target>] [-level <int>] [<design>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `design` | STRING | 否 (位置) | 目标设计，默认当前设计 |
| `-target` | STRING | 否 | 目标：`timing` 或 `area`，默认 `timing` |
| `-level` | INT | 否 | 优化级别：timing={0,1,2,3}, area={0,1,2}，默认 0 |

```tcl
resyn -target timing -level 2
```

---

#### `add_tieoffs` — 插入 TIE 单元

```
add_tieoffs [-high <cell>] [-low <cell>] [<design>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `design` | STRING | 否 (位置) | 目标设计，默认当前设计 |
| `-high` | STRING | 否 | 常量 1 的 tie-high cell |
| `-low` | STRING | 否 | 常量 0 的 tie-low cell |

---

### 4.3 设计输出

#### `write_file` — 写出设计

```
write_file [-db] [-sdc] [-netlist] [-library <name>] <file>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `file` | STRING | 是 (位置) | 输出文件路径 |
| `-db` | flag | 否 | 输出 DB 格式 |
| `-sdc` | flag | 否 | 输出 SDC 格式 |
| `-netlist` | flag | 否 | 输出网表格式 |
| `-library` | STRING | 否 | 指定库名（仅 DB 格式） |

```tcl
write_file -netlist report/synth.v
write_file -db report/design.db
write_file -sdc report/design.sdc
```

---

### 4.4 STA 约束

以下 STA 命令为 RainaSynth 内置，基于 SDC 标准。

#### `create_clock` — 创建时钟

```
create_clock [-name <name>] [-period <float>] [-waveform <float_list>] [-add] [-comment <str>] <source_objects>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `source_objects` | STRLIST | 是 | 时钟源端口/pin |
| `-name` | STRING | 否 | 时钟名称 |
| `-period` | FLOAT | 否 | 时钟周期 |
| `-waveform` | FLOAT_LIST | 否 | 波形 {rise fall} |
| `-add` | BOOL | 否 | 添加额外时钟（不覆盖已有） |
| `-comment` | STRING | 否 | 注释 |

```tcl
set clk_port [get_ports clk]
create_clock -name core_clock -period 0.46 $clk_port
create_clock -name sys_clk -period 10.0 -waveform {0 5} [get_ports sys_clk]
```

---

#### `create_generated_clock` — 创建生成时钟

```
create_generated_clock [-name <name>] [-add] [-source <objects>] [-master_clock <name>]
    [-divide_by <int>] [-multiply_by <int>] [-duty_cycle <float>]
    [-invert] [-preinvert] [-edges <int_list>] [-edge_shift <float_list>]
    [-combinational] [-comment <str>] <source_objects>
```

---

#### `current_design` — 设置当前工作设计

```
current_design [-force] [<design>]
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `design` | STRING | 否 | 设计名；无参数时返回当前设计名 |
| `-force` | BOOL | 否 | 强制切换 |

```tcl
current_design top
current_design              ;# 返回当前设计名
```

---

#### `set_input_delay` — 设置输入延迟

```
set_input_delay <delay> [-rise] [-fall] [-min] [-max] [-clock <clocks>] [-clock_fall]
    [-reference_pin <pins>] [-level_sensitive] [-source_latency_included]
    [-network_latency_included] [-add_delay] <port_pin_list>
```

---

#### `set_output_delay` — 设置输出延迟

```
set_output_delay <delay> [-rise] [-fall] [-min] [-max] [-clock <clocks>] [-clock_fall]
    [-reference_pin <pins>] [-level_sensitive] [-source_latency_included]
    [-network_latency_included] [-add_delay] <port_pin_list>
```

---

#### `set_drive` — 设置驱动强度

```
set_drive <resistance> [-rise] [-fall] [-min] [-max] <port_list>
```

---

#### `set_driving_cell` — 设置驱动单元

```
set_driving_cell [-lib_cell <cell>] [-library <libs>] [-rise] [-fall] [-min] [-max]
    [-pin <pins>] [-from_pin <pins>] [-dont_scale] [-no_design_rule]
    [-input_transition_rise <float>] [-input_transition_fall <float>]
    [-multiply_by <float>] <port_list>
```

---

#### `set_load` — 设置负载

```
set_load <load> [-min] [-max] [-subtract_pin_load] [-pin_load] [-wire_load] <object_list>
```

---

#### `set_false_path` — 设置伪路径

```
set_false_path [-rise] [-fall] [-setup] [-hold] [-from <objects>] [-rise_from <objects>]
    [-fall_from <objects>] [-through <objects>] [-rise_through <objects>]
    [-fall_through <objects>] [-to <objects>] [-rise_to <objects>] [-fall_to <objects>]
    [-reset_path] [-comment <str>]
```

---

#### `set_multicycle_path` — 设置多周期路径

```
set_multicycle_path <path_multiplier> [-rise] [-fall] [-setup] [-hold] [-start] [-end]
    [-from <objects>] [-rise_from <objects>] [-fall_from <objects>]
    [-through <objects>] [-rise_through <objects>] [-fall_through <objects>]
    [-to <objects>] [-rise_to <objects>] [-fall_to <objects>]
    [-reset_path] [-comment <str>]
```

---

#### `set_max_delay` / `set_min_delay` — 设置最大/最小时延

```
set_max_delay <delay> [-rise] [-fall] [-ignore_clock_latency]
    [-from <objs>] [-through <objs>] [-to <objs>] ... <更多路径限定选项>
set_min_delay <delay> [... 同上 ...]
```

---

#### `set_clock_groups` — 设置时钟组

```
set_clock_groups [-name <name>] [-comment <str>]
    [-group <group_list>] [-physically_exclusive] [-logically_exclusive]
    [-asynchronous] [-allow_paths]
```

---

#### `set_clock_uncertainty` — 设置时钟不确定性

```
set_clock_uncertainty <uncertainty> [-from <clocks>] [-to <clocks>]
    [-rise] [-fall] [-setup] [-hold] [<object_list>]
```

---

#### `set_clock_latency` — 设置时钟延迟

```
set_clock_latency <delay> [-clock <clocks>] [-source] [-rise] [-fall]
    [-min] [-max] [-early] [-late] [-dynamic <float>] [<object_list>]
```

---

#### `set_clock_transition` — 设置时钟跳变

```
set_clock_transition <transition> [-rise] [-fall] [-min] [-max] <clock_list>
```

---

#### `set_input_transition` — 设置输入跳变

```
set_input_transition <transition> [-rise] [-fall] [-min] [-max] <port_list>
```

---

#### `set_max_fanout` — 设置最大扇出

```
set_max_fanout <fanout> [<object_list>]
```

---

#### `set_max_capacitance` / `set_min_capacitance` — 设置最大/最小电容

```
set_max_capacitance <capacitance> [-data_path] [-clock_path] [<object_list>]
set_min_capacitance <capacitance> [<object_list>]
```

---

#### `set_max_transition` — 设置最大跳变

```
set_max_transition <transition> [-data_path] [-clock_path] [<object_list>]
```

---

#### `set_max_area` — 设置最大面积

```
set_max_area [-ignore_tns] <area>
```

---

#### `set_case_analysis` — 设置 case 分析

```
set_case_analysis <case> <pin_port_list>
```

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `case` | STRING | 是 | 值：`0`, `1`, `rising`, `falling` |
| `pin_port_list` | STRLIST | 是 | 目标 pin/port 列表 |

```tcl
set_case_analysis 0 [get_ports scan_enable]
set_case_analysis 1 [get_pins u_reg/Q]
```

---

#### `remove_case_analysis` — 移除 case 分析

```
remove_case_analysis [-all] [<pin_port_list>]
```

---

#### `set_operating_conditions` — 设置工作条件

```
set_operating_conditions [-min <cond>] [-max <cond>] [-analysis_type <type>] [<lib_cell_list>]
```

---

#### `set_timing_derate` — 设置时序减免

```
set_timing_derate [-early] [-late] [-rise] [-fall] [-cell_delay] [-net_delay]
    [-data] [-clock] [-cell_check] <derate> [<object_list>]
```

---

#### `set_disable_timing` — 禁用时序弧

```
set_disable_timing [-from <pin>] [-to <pin>] [<object_list>]
```

---

#### `set_logic_one` / `set_logic_zero` / `set_logic_dc` — 设置逻辑常量

```
set_logic_one <port_list>
set_logic_zero <port_list>
set_logic_dc <port_list>
```

---

#### `set_ideal_network` — 设置理想网络

```
set_ideal_network [-no_propagate] [-dont_care_placement] <object_list>
```

---

#### `set_ideal_latency` / `set_ideal_transition` — 设置理想延迟/跳变

```
set_ideal_latency <delay> [-rise] [-fall] [-min] [-max] <object_list>
set_ideal_transition <transition_time> [-rise] [-fall] [-min] [-max] <object_list>
```

---

#### `group_path` — 路径分组

```
group_path [-name <name>] [-weight <float>] [-critical_range <float>]
    [-from <objs>] [-through <objs>] [-to <objs>] [-default] [-comment <str>]
```

---

#### `read_sdc` — 读入 SDC 文件

```
read_sdc [-silence] <file>
```

---

#### `write_sdc` — 写出 SDC 文件

```
write_sdc <file>
```

---

#### `read_spef` — 读入 SPEF 寄生参数

```
read_spef [-min] [-max] [-arnoldi] <file>
```

---

#### `read_sdf` — 读入 SDF 延迟文件

```
read_sdf [-min] [-max] <file>
```

---

#### `write_sdf` — 写出 SDF 延迟文件

```
write_sdf [-significant_digits <int>] <file>
```

---

#### `update_timing` — 更新时序

```
update_timing [-full]
```

---

#### `set_propagated_clock` — 设置传播时钟

```
set_propagated_clock [<object_list>]
```

---

#### `remove_propagated_clock` — 移除传播时钟

```
remove_propagated_clock [-all] [<object_list>]
```

---

### 4.5 报告

#### `report_area` — 报告面积

```
report_area [-nosplit] [-physical] [-individual_site_def_util] [-hierarchy] [-verbose]
```

```tcl
report_area
report_area > report/area.rpt
```

---

#### `report_timing` — 报告时序

```
report_timing [-significant_digits <int>] [-nworst <int>] [-max_paths <int>]
    [-slack_lesser_than <float>] [-slack_greater_than <float>]
    [-from <objects>] [-through <objects>] [-to <objects>]
    [-rise] [-fall] [-early] [-late] [-nosplit] [-input_pins] [-net]
    [-capacitance] [-crosstalk_delta] [-derate] [-sort_by <field>]
    [-group <group_name>] [-path_type <type>] [-delay_type <type>]
    [-pba_mode <mode>] [-exclude_clear_arcs] [-include_loop]
    [-unconstrained] [-verbose]
```

```tcl
report_timing
report_timing -nworst 10 -slack_lesser_than 0.1
report_timing -from [get_ports A] -to [get_ports Z]
```

---

#### `report_power` — 报告功耗

```
report_power [-significant_digits <int>] [-nosplit] [-hierarchy] [-verbose]
```

```tcl
report_power
report_power > report/power.rpt
```

---

#### `report_qor` — 报告综合质量

```
report_qor [-significant_digits <int>] [-nosplit]
```

---

#### `report_design` — 报告设计属性

```
report_design [-nosplit] [-physical]
```

---

#### `report_constraint` — 报告约束违例

```
report_constraint [-all_violators] [-verbose] [-significant_digits <int>]
    [-max_area] [-max_delay] [-critical_range] [-min_delay]
    [-max_capacitance] [-min_capacitance] [-max_transition]
    [-max_fanout] [-cell_degradation] [-max_toggle_rate]
    [-min_porosity] [-max_dynamic_power] [-max_leakage_power]
    [-max_total_power] [-max_net_length] [-min_pulse_width]
    [-min_period] [-connection_class] [-multiport_net]
    [-nosplit] [-ignore_infeasible_paths]
```

```tcl
report_constraint -all_violators -verbose
report_constraint -max_transition -max_fanout
```

---

#### `report_port` — 报告端口

```
report_port [-drive] [-verbose] [-physical] [-only_physical] [-nosplit]
    [-significant_digits <int>] [<port_list>]
```

---

#### `report_cell` — 报告单元

```
report_cell [-nosplit] [-connections] [-verbose] [-physical] [-only_physical]
    [-significant_digits <int>] [<cell_list>]
```

---

#### `report_net` — 报告线网

```
report_net [-nosplit] [-noflat] [-transition_times] [-only_physical] [-verbose]
    [-cell_degradation] [-connections] [-physical] [-min]
    [-significant_digits <int>] [-max_toggle_rate] [-max_capacitance]
    [-scenarios] [<net_list>]
```

---

#### `report_net_fanout` — 报告线网扇出

```
report_net_fanout [-nosplit] [-high_fanout] [-threshold <int>] [-bound <int>]
    [-verbose] [-connections] [-physical] [-min] [-tree] [-depth <int>]
    [<net_list>]
```

---

#### `report_reference` — 报告引用

```
report_reference [-nosplit] [-hierarchy]
```

---

#### `report_hierarchy` — 报告层次

```
report_hierarchy [-nosplit] [-full] [-noleaf]
```

---

#### `report_lib` — 报告工艺库

```
report_lib [-cell_list <list>] [-all] [-timing] [-power] [-noise] ...
    [<libname>]
```

---

#### `report_bus` — 报告总线

```
report_bus [-nosplit]
```

---

#### `report_units` — 报告单位

```
report_units
```

---

#### `report_attribute` — 报告属性

```
report_attribute [-cell] [-net] [-design] [-reference] [-port] [-pin] [<object_list>]
```

---

#### `report_clock_gating` — 报告时钟门控

```
report_clock_gating
```

---

#### `report_buffer_tree` — 报告缓冲树

```
report_buffer_tree [-from <pins>] [-net <nets>] [-depth <int>] [-connections]
    [-hierarchy] [-physical] [-nosplit]
```

---

#### `get_fanin_pins` / `get_fanout_pins` — 获取扇入/扇出

```
get_fanin_pins [-level <int>] [-verbose] <object_list>
get_fanout_pins [-level <int>] [-verbose] <object_list>
```

---

#### `check_design` — 设计检查

```
check_design [-summary] [-no_warnings] [-one_level] [-multiple_designs]
    [-no_connection_class] [-nosplit] [-unmapped]
    [-cells] [-ports] [-designs] [-nets] [-loop] [-tristates]
    [-html_file_name <file>]
```

---

### 4.6 日志与重定向

#### `log_begin` / `log_end` — 日志记录

```
log_begin [-append] [-screen_printing_off] <file>
log_end
```

```tcl
log_begin report/output.log
get_ports
get_nets
log_end
```

---

#### `redirect` — 命令输出重定向

```
redirect [-append] [-tee] [-file] [-compress] [-variable] [-channel]
    [-bg] [-max_cores <int>] <target> <command_string>
```

```tcl
redirect -tee report/timing.rpt {report_timing}
redirect -variable my_var {get_ports}
```

---

#### Tcl 原生重定向

```tcl
report_area > report/area.rpt         ;# 覆盖写入
report_area >> report/area.rpt        ;# 追加写入
```

---

## 5. ECO / 网表编辑命令速查

| 命令 | 说明 | 关键参数 |
|------|------|---------|
| `create_design` | 创建空设计 | `-design_name`, `-file_name` |
| `remove_design` | 移除设计 | `-design_list`, `-designs`, `-all`, `-hierarchy`, `-quiet` |
| `current_design_name` | 返回当前设计名 | 无参数 |
| `current_instance` | 设置当前实例 | `instance` (位置) |
| `create_net` | 创建线网 | `-net_list`, `-power`, `-ground` |
| `remove_net` | 移除线网 | `-net_list`, `-all`, `-only_physical` |
| `connect_net` | 连接线网 | `-net_name`, `-object_list` |
| `disconnect_net` | 断开线网连接 | `-net`, `-object_list`, `-all` |
| `create_cell` | 创建单元 | `-cell_list`, `-reference_name`, `-hierarchical`, `-logic`, `-only_physical` |
| `remove_cell` | 移除单元 | `-cell_list`, `-all` |
| `create_port` | 创建端口 | `-port_list`, `-direction` |
| `remove_port` | 移除端口 | `-port_list` |
| `create_bus` | 创建总线 | `-object_list`, `-bus_name`, `-type`, `-sort`, `-start`, `-end` |
| `remove_bus` | 移除总线 | `-bus_list` |
| `connect_pin` | 跨层次连接 pin | `-from`, `-to`, `-port_name`, `-verbose` |
| `insert_buffer` | 插入缓冲器 | `-object_list`, `-buffer_lib_cell`, `-no_of_cells`, `-new_net_names`, `-new_cell_names`, `-inverter_pair` |
| `remove_buffer` | 移除缓冲器 | `-from`, `-net`, `-to`, `-level`, `-cell_list` |
| `size_cell` | 更换单元 | `-cell_object`, `-lib_cell_object` |
| `all_connected` | 获取连接对象 | `-leaf`, `-object` |
| `undo` | 撤销 ECO 操作 | `-levels`, `-check_only`, `-silent` |
| `redo` | 重做 ECO 操作 | `-levels`, `-check_only`, `-silent` |
| `undo_config` | 配置 undo 栈 | `-enable`, `-disable` |

---

## 6. 查询命令速查

| 命令 | 说明 | 关键参数 |
|------|------|---------|
| `get_ports` | 获取端口集合 | `-hierarchical`, `-exact`, `-regexp`, `-nocase`, `-quiet`, `-filter`, `-of_objects`, `patterns` (位置) |
| `get_pins` | 获取 pin 集合 | `-hierarchical`, `-exact`, `-regexp`, `-nocase`, `-quiet`, `-filter`, `-leaf`, `-of_objects`, `patterns` (位置) |
| `get_cells` | 获取 cell 集合 | `-hierarchical`, `-exact`, `-regexp`, `-nocase`, `-quiet`, `-filter`, `-rtl`, `-of_objects`, `patterns` (位置) |
| `get_nets` | 获取 net 集合 | `-hierarchical`, `-exact`, `-regexp`, `-nocase`, `-quiet`, `-filter`, `-rtl`, `-of_objects`, `patterns` (位置) |
| `get_clocks` | 获取时钟集合 | `-regexp`, `-nocase`, `-quiet`, `-filter`, `patterns` (位置) |
| `get_libs` | 获取库集合 | `-exact`, `-regexp`, `-nocase`, `-quiet`, `-filter`, `-scenarios`, `-of_objects`, `patterns` (位置) |
| `get_lib_cells` | 获取库单元集合 | `-exact`, `-regexp`, `-nocase`, `-quiet`, `-filter`, `-scenarios`, `-of_objects`, `patterns` (位置) |
| `get_lib_pins` | 获取库 pin 集合 | `-exact`, `-regexp`, `-nocase`, `-quiet`, `-filter`, `-of_objects`, `patterns` (位置) |
| `all_clocks` | 获取所有时钟 | 无参数 |
| `all_inputs` | 获取所有输入 | `-clock`, `-edge_triggered`, `-level_sensitive` |
| `all_outputs` | 获取所有输出 | `-clock`, `-edge_triggered`, `-level_sensitive` |
| `all_registers` | 获取所有寄存器 | `-no_hierarchy`, `-clock`, `-cells`, `-data_pins`, `-clock_pins`, `-output_pins`, `-level_sensitive`, `-edge_triggered`, `-include_icg`, `patterns` (位置) |
| `list_libs` | 列出库 | `-all`, `-all_liberty`, `-all_lef`, `-all_def`, `-all_design`, `lib_list` (位置) |
| `remove_lib` | 移除库 | `-all`, `-all_liberty`, `-all_lef`, `-all_def`, `-all_design`, `lib_list` (位置) |
| `sizeof_collection` | 集合大小 | `collection` (位置) |
| `query_objects` | 按序显示集合对象 | `objects` (位置) |
| `get_object_name` | 获取对象全名 | `object` (位置) |
| `add_to_collection` | 添加对象到集合 | `target_collection` (位置), `object_spec` (位置) |
| `remove_from_collection` | 从集合移除对象 | `target_collection` (位置), `remove_object` (位置), `-intersect` |
| `get_attribute` | 获取属性值 | `object_list` (位置), `attribute_name` (位置), `-quiet`, `-bus`, `-return_null_values` |
| `set_attribute` | 设置属性值 | `object_list` (位置), `attribute_name` (位置), `attribute_value` (位置), `-type`, `-bus`, `-quiet` |
| `remove_attribute` | 移除属性 | `object_list` (位置), `attribute_name` (位置), `-quiet`, `-bus` |
| `get_pin_info` | 获取 pin 详情 | 返回 pin 的时序信息 |

---

## 7. 配置与工具命令速查

| 命令 | 说明 | 关键参数 |
|------|------|---------|
| `set_app_var` | 设置应用配置变量 | `name` (位置), `value` (位置) |
| `get_app_var` | 获取应用配置变量 | `name` (位置)；`__all__` 获取所有 |
| `set_message_level` | 设置消息级别 | `msg_tag` (位置), `level` (位置) |
| `set_print_config` | 控制信息输出 | `-scope`, `-threshold`, `-default`, `-file`, `-max_wrap`, `-max_flod`, `-allow_fileline`, `-cmd_flag` |
| `set_parallel_options` | 设置并行计算 | `-max_cores`, `-max_timing_cores`, `-max_read_spef_cores`, `-max_highlevel_cores`, `-enable_dist` |
| `set_dont_use` | 禁用库单元 | `-power`, `object_list` (位置) |
| `set_dont_touch` | 禁止优化 | `object_list` (位置), `flag` (位置, 默认 `true`) |
| `set_black_box` | 设置黑盒 | `-work`, `-module` |
| `set_disable_path_max_fanout` | 设置路径最大扇出 | `-max_fanout` (位置, 默认 10000) |
| `set_hls_config` | 配置 HLS | `name` (位置), `value` (位置) |
| `setenv` | 设置环境变量 | `name` (位置), `value` (位置), `-overwrite_en` |
| `getenv` | 获取环境变量 | `name` (位置) |
| `unsetenv` | 删除环境变量 | `name` (位置) |
| `set_sta_config` | 设置 STA 配置 | `-name`, `-value` |
| `get_sta_config` | 获取 STA 配置 | `-name` |
| `test_sta_units` | 测试 STA 单位 | 无参数 |
| `write_graph` | 写出时序图 | `-file` |
| `set_mode` | 设置模式 | `-mode_list`, `-instance_list` |
| `set_hierarchy_separator` | 设置层次分隔符 | `-separator` |
| `set_clock_sense` | 设置时钟感知 | `-type`, `-pins`, `-clocks`, `-pulse`, `-positive`, `-negative`, `-stop_propagation` |
| `characterize` | 特征化 | `-cell_list`, `-no_timing`, `-constraint`, `-connection`, `-power` |
| `help` | 列出帮助信息 | 无参数 |
| `exit` / `quit` | 退出程序 | 无参数 |

### 常用 app_var

```tcl
set_app_var enable_clock_gating false   ;# 禁用时钟门控
get_app_var __all__                      ;# 查看所有配置项
```

---

## 8. GUI 命令

| 命令 | 说明 |
|------|------|
| `start_gui` | 启动 GUI |
| `stop_gui` | 停止 GUI |

---

## 9. 完整脚本模板

> **Agent 注意**：以下模板中 `<<<...>>>` 为占位符，agent 执行前必须替换为实际值。
> 常见占位符：
> - `<<<LIB_PATH>>>` → 工艺库 .lib 文件路径
> - `<<<SRC_DIR>>>` → RTL 源文件目录
> - `<<<TOP_MODULE>>>` → 顶层模块名
> - `<<<CLK_PORT>>>` → 顶层时钟端口名（通常为 `clk`）
> - `<<<CLK_PERIOD>>>` → 时钟周期（ns），如 `0.46`

### 模板 1：RTL 综合标准流程

```tcl
# ============================================================
# RainaSynth RTL 综合标准流程
# 用法: ./raina_synth -f this_script.tcl
# ============================================================

# ---- 1. 读入 RTL 设计 ----
# 多文件设计：逐个 read_verilog
read_verilog <<<SRC_DIR>>>/module_a.v
read_verilog <<<SRC_DIR>>>/module_b.v
read_verilog <<<SRC_DIR>>>/top.v

# ---- 2. 读入工艺库 ----
read_liberty <<<LIB_PATH>>>

# ---- 3. 执行综合 ----
synth -top <<<TOP_MODULE>>>

# ---- 4. 输出网表 ----
write_file -netlist report/synth.v

# ---- 5. STA 约束 ----
set_app_var enable_clock_gating false

# 时钟定义
set clk_name core_clock
set clk_port_name <<<CLK_PORT>>>
set clk_period <<<CLK_PERIOD>>>
set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port

# 输入/输出延迟（可选，按需）
# set_input_delay [expr $clk_period * 0.2] -clock $clk_name [all_inputs]
# set_output_delay [expr $clk_period * 0.2] -clock $clk_name [all_outputs]

# ---- 6. 生成报告 ----
report_area    > report/area.rpt
report_timing  > report/timing.rpt
report_power   > report/power.rpt
report_qor     > report/qor.rpt

# ---- 7. 检查设计 ----
check_design

# ---- 8. 退出 ----
exit
```

### 模板 2：网表读入 + 综合优化流程

```tcl
# ============================================================
# RainaSynth 网表综合流程
# 适用场景: 已有综合后网表，需要做优化或 STA 分析
# 参考: regressioncases/Basic/defLink/run.tcl
# ============================================================

# ---- 1. 读入网表和工艺库 ----
read_verilog -netlist <<<SRC_DIR>>>/synth_input.v
read_liberty <<<LIB_PATH>>>

# ---- 2. 网表综合 ----
synth_netlist -top <<<TOP_MODULE>>>

# ---- 3. 输出优化后网表 ----
write_file -netlist report/synth_optimized.v

# ---- 4. STA 约束 ----
set_app_var enable_clock_gating false
set clk_name core_clock
set clk_port_name <<<CLK_PORT>>>
set clk_period <<<CLK_PERIOD>>>
set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port

# ---- 5. 报告 ----
report_area    > report/area.rpt
report_timing  > report/timing.rpt
report_power   > report/power.rpt
report_qor     > report/qor.rpt

exit
```

### 模板 3：带展平 + 综合流程

```tcl
# ============================================================
# RainaSynth 展平 + 综合流程
# 适用场景: 多文件层次化 RTL，需要先展平再综合
# 参考: regressioncases/Basic/aes/run.tcl
# ============================================================

# ---- 1. 读入多文件 RTL ----
read_verilog <<<SRC_DIR>>>/a.v
read_verilog <<<SRC_DIR>>>/b.v
read_verilog <<<SRC_DIR>>>/top.v

# ---- 2. 读入工艺库 ----
read_liberty <<<LIB_PATH>>>

# ---- 3. 细化设计 -> 展平层次 ----
elaborate
ungroup -flatten -all

# ---- 4. 综合 ----
synth -top <<<TOP_MODULE>>>

# ---- 5. 输出网表 ----
write_file -netlist report/synth.v

# ---- 6. STA 约束 ----
set_app_var enable_clock_gating false
set clk_name core_clock
set clk_port_name <<<CLK_PORT>>>
set clk_period <<<CLK_PERIOD>>>
set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port

# ---- 7. 报告 ----
report_area    > report/area.rpt
report_timing  > report/timing.rpt
report_power   > report/power.rpt
report_qor     > report/qor.rpt

exit
```

### 模板 4：带 ECO 编辑的流程

```tcl
# ============================================================
# RainaSynth ECO 编辑流程
# 适用场景: 综合后需要手动修改网表
# 参考: regressioncases/Basic/create_net/run.tcl
# ============================================================

# ---- 1. 读入 ----
read_verilog -netlist <<<SRC_DIR>>>/synth.v
read_liberty <<<LIB_PATH>>>
synth_netlist -top <<<TOP_MODULE>>>

# ---- 2. 查看当前设计 ----
current_design_name
get_ports
get_nets

# ---- 3. ECO 编辑 ----
# 创建新线网
create_net -net_list {new_net}

# 创建新单元
create_cell -cell_list {buf_1} -reference_name BUF_X1

# 连接线网
connect_net -net_name new_net -object_list {buf_1/A in_port}

# 插入缓冲器
insert_buffer -object_list {critical_net} -buffer_lib_cell BUF_X4 -no_of_cells 2

# 更换单元
size_cell -cell_object {u_old} -lib_cell_object AND2_X2

# 断开连接
disconnect_net -net old_net -object_list {u_old/Z}

# 删除单元
remove_cell -cell_list {unused_cell}

# 如果需要撤销
# undo -levels 1

# ---- 4. 输出 ----
write_file -netlist report/synth_eco.v

# ---- 5. STA 约束和报告 ----
set_app_var enable_clock_gating false
set clk_name core_clock
set clk_port_name <<<CLK_PORT>>>
set clk_period <<<CLK_PERIOD>>>
set clk_port [get_ports $clk_port_name]
create_clock -name $clk_name -period $clk_period $clk_port

report_area    > report/area.rpt
report_timing  > report/timing.rpt

exit
```

---

## 10. 命令索引

### 设计输入
`read_verilog` · `read_file` · `analyze` · `elaborate` · `read_liberty` · `read_db`

### 综合
`synth` · `synth_netlist` · `ungroup` · `group` · `optimize` · `resyn` · `add_tieoffs`

### 设计输出
`write_file` · `write_sdc` · `write_sdf` · `write_graph`

### STA 约束
`create_clock` · `create_generated_clock` · `current_design` · `set_input_delay` · `set_output_delay` · `set_drive` · `set_driving_cell` · `set_load` · `set_false_path` · `set_multicycle_path` · `set_max_delay` · `set_min_delay` · `set_clock_groups` · `set_clock_uncertainty` · `set_clock_latency` · `set_clock_transition` · `set_input_transition` · `set_max_fanout` · `set_max_capacitance` · `set_min_capacitance` · `set_max_transition` · `set_max_area` · `set_case_analysis` · `remove_case_analysis` · `set_operating_conditions` · `set_timing_derate` · `set_disable_timing` · `set_logic_one` · `set_logic_zero` · `set_logic_dc` · `set_ideal_network` · `set_ideal_latency` · `set_ideal_transition` · `group_path` · `read_sdc` · `read_spef` · `read_sdf` · `update_timing` · `set_propagated_clock` · `remove_propagated_clock`

### 报告
`report_area` · `report_timing` · `report_power` · `report_qor` · `report_design` · `report_constraint` · `report_port` · `report_cell` · `report_net` · `report_net_fanout` · `report_reference` · `report_hierarchy` · `report_lib` · `report_bus` · `report_units` · `report_attribute` · `report_clock_gating` · `report_buffer_tree` · `get_fanin_pins` · `get_fanout_pins` · `check_design`

### ECO
`create_design` · `remove_design` · `current_design_name` · `current_instance` · `create_net` · `remove_net` · `connect_net` · `disconnect_net` · `create_cell` · `remove_cell` · `create_port` · `remove_port` · `create_bus` · `remove_bus` · `connect_pin` · `insert_buffer` · `remove_buffer` · `size_cell` · `all_connected` · `undo` · `redo` · `undo_config`

### 查询
`get_ports` · `get_pins` · `get_cells` · `get_nets` · `get_clocks` · `get_libs` · `get_lib_cells` · `get_lib_pins` · `all_clocks` · `all_inputs` · `all_outputs` · `all_registers` · `list_libs` · `remove_lib` · `sizeof_collection` · `query_objects` · `get_object_name` · `add_to_collection` · `remove_from_collection` · `get_attribute` · `set_attribute` · `remove_attribute` · `get_pin_info`

### 配置
`set_app_var` · `get_app_var` · `set_message_level` · `set_print_config` · `set_parallel_options` · `set_dont_use` · `set_dont_touch` · `set_black_box` · `set_hls_config` · `setenv` · `getenv` · `unsetenv` · `set_sta_config` · `get_sta_config` · `set_mode` · `set_hierarchy_separator` · `set_clock_sense` · `characterize`

### 日志与工具
`log_begin` · `log_end` · `redirect` · `output_libs_info` · `help` · `exit` · `quit`

### GUI
`start_gui` · `stop_gui`
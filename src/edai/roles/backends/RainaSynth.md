# RainaSynth Backend

RainaSynth — a Synopsys Design Compiler compatible logic synthesis shell.
Provides RTL-to-gate synthesis with Tcl-based control, supporting standard
SDC timing constraints and industry-standard report formats.

## Command Categories

- **Synthesis flow:** `analyze`, `elaborate`, `link`, `uniquify`, `compile`,
  `compile_ultra`, `write`
- **SDC / timing constraints:** `create_clock`, `set_input_delay`,
  `set_output_delay`, `set_max_delay`, `set_false_path`, `set_clock_groups`,
  `set_clock_latency`, `set_clock_uncertainty`
- **Reports:** `report_timing`, `report_area`, `report_power`,
  `report_qor`, `report_clock`, `report_resources`, `report_design`,
  `check_design`, `report_constraint`
- **Power analysis:** `read_saif`, `set_switching_activity`, `report_power`
- **Output:** `write -format verilog`, `write -format ddc`, `write_sdf`,
  `write_sdc`, `write_sdc2`, `set_svf`
- **Utility:** `current_design`, `list_libs`, `get_cells`, `get_nets`,
  `get_pins`, `get_ports`, `all_registers`, `all_inputs`, `all_outputs`,
  `change_names`

## Key Concepts

- **target_library** — compiled Liberty (`.db`) files for the standard-cell
  library to map to
- **link_library** — all libraries loaded at link time (`"*"` includes the
  in-memory design); typically `"* $target_library"`
- **synthetic_library** — DesignWare-style `.sldb` files for datapath
  components (adders, multipliers, etc.)
- **search_path** — directories searched for library and source files
- **define_design_lib WORK** — sets up the working design library
- `.ddc` — Synopsys-compatible binary format (full design state)
- `.db` — compiled Liberty library binary format

## File Formats

| Direction | Formats |
|-----------|---------|
| Read      | Verilog (`.v`, `.sv`), VHDL (`.vhd`), SystemVerilog, Liberty (`.lib`), `.db`, `.ddc`, SDC, SDF, SAIF |
| Write     | Verilog (`.v`), `.ddc`, SDC, SDF, SAIF, `.sldb` |

## Typical Flow

```
analyze -format verilog {source files}
elaborate <top_module>
current_design <top_module>
link
uniquify
create_clock -name clk -period 10.0 [get_ports clk]
set_input_delay  -clock clk 2.0 [all_inputs]
set_output_delay -clock clk 3.0 [all_outputs]
compile_ultra -gate_clock -scan
write -format ddc -hierarchy -output <output>.ddc
write -format verilog -hierarchy -output <output>.v
write_sdc <output>.sdc
report_timing -nworst 10 -max_paths 100
report_area -hierarchy
report_power -analysis_effort high
```

## Notes

- Command set and SDC constraint syntax are broadly compatible with
  Synopsys Design Compiler.
- `compile_ultra` is the primary synthesis command.  Use `-gate_clock` to
  insert clock gating and `-scan` for test-ready scan chains.
- `change_names -rules verilog -hierarchy` is typically run before writing
  netlists to produce synthesis-friendly names.
- The shell is a superset of standard Tcl — all Tcl control flow, variables,
  and procedures are available.

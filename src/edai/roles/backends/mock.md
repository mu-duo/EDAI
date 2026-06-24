# Mock Tcl Backend

An in-memory simulation of an EDA tool (Synopsys / Cadence style).
No real backend required — all data is static.

## Available Commands

| Command | Description |
|---------|-------------|
| `get_cells` | List all cells in the design |
| `get_nets` | List all nets |
| `get_ports` | List all ports |
| `get_pins [<cell>]` | List pins, optionally for one cell |
| `create_clock <name> <period>` | Create a clock definition |
| `report_timing` | Report timing (requires placement first) |
| `place_design` | Run placement |
| `route_design` | Run routing (also places first) |

## Variables

Use `set` to assign and read variables, `puts` to print values,
`expr` for arithmetic.  Refer to variables as `$name` or `${name}`.

## Design Database

- 6 cells (AND2, OR2, DFF, INV, NAND2)
- 5 nets
- 5 ports (clk, rst_n, data_in, data_out, ready)
- 1 clock (clk, 10.0 ns period)

# Tclsh Backend

A standard Tcl shell (tclsh).  Any valid Tcl command can be executed.

## Capabilities

- Full Tcl language: variables, control flow, procedures, lists, strings
- Standard Tcl commands: `set`, `puts`, `expr`, `string`, `list`, `lappend`,
  `lindex`, `llength`, `foreach`, `if`, `while`, `for`, `proc`, `format`,
  `scan`, `regexp`, `regsub`, `open`, `close`, `gets`, `puts`, `file`,
  `source`, `package`, etc.
- No EDA-specific commands (this is plain tclsh, not dc_shell or innovus).

## Use

Call the `execute` tool with any valid Tcl code as the argument.
The code is evaluated in a persistent session — variables, procedures,
and state carry over between calls.

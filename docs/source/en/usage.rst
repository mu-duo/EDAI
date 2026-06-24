.. _en-usage:

Usage
=====

Command-Line Interface
----------------------

::

    edai [options] [tui]

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Flag
     - Description
   * - ``-v``, ``--verbose``
     - Enable debug/verbose output at startup.
   * - ``-p``, ``--path``
     - Path to the EDA tool binary (e.g. ``/usr/bin/dc_shell``).
   * - ``--prompt``
     - Prompt regex expected by the tool (default: inferred from
       binary name).
   * - ``--mock``
     - Force in-memory mock backend (overrides ``--path``).
   * - ``--version``
     - Print version and exit.
   * - ``tui``
     - Start the Textual TUI (default when no subcommand given).

Examples::

    edai                          # auto-detect backend, start TUI
    edai --mock                   # force mock backend
    edai --path /bin/tclsh -v     # real tclsh with debug on

Textual TUI
-----------

When you start EDAI, a full-screen TUI opens with three areas:

.. image:: ../_static/edai-tui-layout.png
   :alt: EDAI TUI Layout
   :width: 100 %

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Area
     - Purpose
   * - **Log panel** (top)
     - Scrollable conversation log showing all commands and agent
       responses.
   * - **Stream** (middle)
     - Inline area for streaming agent response tokens.
   * - **Input bar** (bottom)
     - Type Tcl commands or natural language; press Enter to send.

Keyboard shortcuts:

* :kbd:`Ctrl+L` — clear log and conversation history.
* :kbd:`Ctrl+C` — quit.

Special Commands
----------------

All ``/``-prefixed commands are handled by the TUI itself (never forwarded to
the backend) and are **not** recorded in the conversation history.

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Command
     - Aliases
     - Description
   * - ``/help``
     - ``h``, ``?``
     - List all available special commands.
   * - ``/exit``
     - ``quit``
     - Exit the TUI.
   * - ``/clear``
     - ``cls``
     - Clear the output log and conversation history.
   * - ``/debug``
     -
     - Toggle / enable / disable / query debug mode.
       Sub-commands: ``on``, ``off``, ``--status``.
   * - ``/env``
     -
     - Show the current engine state (cells, nets, ports, clocks,
       variables, debug mode).
   * - ``/history``
     - ``hist``
     - Display conversation history.  ``/history N`` shows the last
       *N* messages with Rich markup colouring.

Agent Interaction
-----------------

When input does not match a known Tcl command, it is forwarded to the
LLM agent.  The agent uses a ReAct loop:

1. Interpret the user's natural language request.
2. Call the ``execute`` tool with one or more Tcl commands.
3. Read the backend output and decide whether more steps are needed.
4. Present the final answer to the user.

Example dialogue::

    tcl> place the design
    Agent: Running place_design...
    └─ Placement completed.
    Agent: The design has been placed.  Wirelength estimate: 1.2 mm.

    tcl> report timing
    Agent: Running report_timing...
    └─ Timing report generated.
    Agent: Worst slack is -0.05 ns on path clk→reg1/D.

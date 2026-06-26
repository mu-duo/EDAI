.. _en-architecture:

Architecture
============

EDAI is organised into three decoupled layers, each with a single
responsibility:

.. image:: _static/edai-architecture-detailed.png
   :alt: Detailed Architecture Diagram
   :width: 100 %

1 — UI Layer (``edai.ui``)
--------------------------

The UI is built with `Textual <https://textual.textualize.io/>`__, a Python
framework for terminal applications.

.. code-block:: text

    EdaiApp (textual.app.App)
     ├── RichLog          ← conversation log
     ├── Static           ← streaming area
     ├── Input            ← user input
     └── Footer / Header

**App responsibilities:**

* Route user input: ``/``-commands → ``_handle_tui_special()``;
  Tcl commands → ``send_command()``; everything else → agent.
* Maintain ``_conversation: list[Message]`` for ``/history`` and
  agent context.
* Install debug output routing via ``set_debug_output()`` so backend
  debug messages appear in the RichLog.
* Provide ``/clear`` (≡ Ctrl+L) and ``/exit`` handlers at the TUI
  level without involving the backend.

2 — Agent Layer (``edai.agent``)
--------------------------------

The agent is a LangGraph ReAct loop built with LangChain's
``create_agent`` factory.

.. code-block:: text

    +--------+     +--------+     +----------+
    |  LLM   | ←→  | Tools  | ←→  | Backend  |
    +--------+     +--------+     +----------+
         ↑                            ↑
      HumanMessage               ToolMessage
         ↑                            ↑
      User input                 Backend output

**Agent responsibilities:**

* Maintain conversation history (``_messages: list[BaseMessage]``)
  across calls.
* Translate natural language → Tcl via ``execute`` tool.
* Record fast-path Tcl commands into history via ``record_command()``
  so the agent remembers commands that bypassed the ReAct loop.

3 — Backend Layer (``edai.core``)
----------------------------------

**MockTclRepl** — in-memory simulation with a static design database
(6 cells, 5 nets, 5 ports, 1 library, 1 clock).  Useful for:

* Debugging the agent or UI without a licensed EDA tool.
* Running integration tests.
* Development / demo on machines without a backend.

**EDAInteractive** — persistent ``pexpect.spawn`` subprocess to a real
EDA tool.  The session stays alive across consecutive commands.

.. note::

   ``pexpect.spawn`` does **not** capture stderr by default.  EDAI
   wraps the invocation in ``/bin/sh -c "... 2>&1"`` so error messages
   (e.g. ``invalid command name``) are captured alongside stdout.

Cross-Cutting Concerns
----------------------

**Message Model** (``edai.core.Message``)
  Canonical ``Message`` class with role-based factories (``human``,
  ``ai``, ``tool``, ``system``) and bidirectional conversion to/from
  LangChain base messages.

**Command Registries**

  * ``edai.core.cmd_registry`` — decorator-based registry for Tcl
    commands (~150 commands in categories: COMMON, STA/SDC, SYNTHESIS).
  * ``edai.core.special_cmds`` — decorator-based registry for ``/``-
    prefixed REPL meta-commands.

**Debug Infrastructure** (``edai.core.debug``)
  ``set_debug()`` / ``debug_print()`` / ``set_debug_output()`` —
  module-level flag controlled by ``--verbose`` CLI flag and
  ``/debug`` at runtime.  Output can be routed to stderr (default)
  or a TUI widget.

Data Flow
---------

.. image:: _static/edai-data-flow.png
   :alt: Data Flow Diagram
   :width: 100 %

**Fast path (known Tcl command):**

::

    User Input ──→ EdaiApp ──→ send_command() ──→ Backend
                            ↓
                      record_command() → Agent._messages
                            ↓
                      Message.tool() → _conversation

**Agent path (natural language):**

::

    User Input ──→ EdaiApp ──→ Agent.run_stream() ──→ LLM
                                 ↓
                           execute tool ──→ Backend
                                 ↓
                           Token stream ──→ Stream area → _conversation

**Special command path (``/`` prefix):**

::

    User Input ──→ EdaiApp._handle_tui_special()
                      ├── /exit  → self.exit()
                      ├── /clear → action_clear_log()
                      └── other  → special_registry.execute()

.. _en-overview:

Overview & Vision
=================

What is EDAI?
-------------

EDAI is a command-line toolkit that puts an **AI co-pilot** inside your EDA
tool workflow.  Instead of memorising dozens of Tcl commands or switching
between documentation and your terminal, you describe what you want in plain
English (or Chinese) and EDAI handles the translation.

The name stands for **E**\ lectronic **D**\ esign **AI** — it is both the
tool name and the vision: an AI-native interface to the semiconductor design
flow.

.. image:: ../_static/edai-session.png
   :alt: EDAI TUI Session
   :width: 100 %

Key Features
------------

**1.  Hybrid Command Interface**

Users can type raw Tcl commands (``get_cells``, ``report_timing``, …) which
are forwarded directly to the backend for execution.  At the same time,
natural-language input is recognised and dispatched to the LLM agent, which
translates the intent into multi-step Tcl sequences.

**2.  LLM-Powered Agent**

The agent uses a LangGraph ReAct loop to reason about the user's request,
call backend tools, interpret results, and decide on the next action.  It
maintains conversation history so follow-up questions can refer to earlier
results.

**3.  Pluggable Back-ends**

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Backend
     - Use case
   * - ``MockTclRepl``
     - In-memory mock with static design database; ideal for development,
       testing, and demos.
   * - ``EDAInteractive``
     - Real EDA tool subprocess (``tclsh``, ``dc_shell``, ``genus``,
       ``innovus``) via pexpect.

The back-end is selected automatically at startup (``tclsh`` on ``PATH`` →
real; fallback → mock) and can be overridden with ``--mock`` or ``--path``.

**4.  Session Persistence**

Tool variables, design state, and timing data survive across commands.
The pexpect sub-process stays alive so the designer can incrementally build
up a flow without restarting.

**5.  Debug & Observability**

The global ``/debug`` command toggles verbose logging.  When enabled, every
Tcl command and agent tool invocation is printed in real time — invaluable
for development and troubleshooting.

Architecture at a Glance
------------------------

.. image:: ../_static/edai-architecture.png
   :alt: EDAI Architecture Diagram
   :width: 100 %

The architecture follows a three-layer design:

1. **UI Layer** (Textual TUI) — captures user input, displays results,
   routes ``/``-prefixed special commands.
2. **Agent Layer** (LangGraph ReAct) — translates natural language into
   tool calls, maintains conversation context.
3. **Backend Layer** (Mock / Real EDA) — executes Tcl commands, returns
   output.

Each layer is decoupled by protocols and dependency injection, so backends
can be swapped without changing the agent or UI.

Future Vision — From Spec to GDSII
===================================

EDAI is the first step toward a broader vision: **AI-native EDA flows that
bridge the gap between design intent and silicon.**

Near-Term Roadmap
-----------------

.. image:: ../_static/edai-roadmap.png
   :alt: EDAI Roadmap
   :width: 100 %

* **Multi-agent orchestration** — specialised agents for synthesis,
  floorplanning, CTS, routing, and sign-off, coordinated by a
  conductor agent.
* **File and project awareness** — let the agent read RTL, SDC, and
  Liberty files to provide context-aware suggestions.
* **Timing closure assistant** — agent-guided optimisation loops:
  ``report_timing`` → identify top violations → suggest fixes →
  re-run and verify.
* **CI/CD integration** — run flows as part of a regression pipeline
  with LLM-powered failure triage.

The Long View: Spec → GDSII
----------------------------

The ultimate goal is an AI system that can take a **natural-language
specification** and drive the physical design flow **from concept to
GDSII** with minimal human intervention.

.. image:: ../_static/edai-spec-to-gdsii.png
   :alt: Spec to GDSII Flow
   :width: 100 %

**Phases:**

1. **Spec parsing** — the agent reads a high-level specification
   (English / Chinese / structured YAML) and infers design constraints,
   clock domains, power targets, and interface protocols.
2. **RTL generation** — the agent writes synthesizable RTL consistent
   with the spec, with assertions for formal verification.
3. **Synthesis & floorplanning** — the agent drives ``dc_shell`` or
   ``genus``, iterates on timing, and creates a floorplan.
4. **Place & route** — the agent orchestrates ``innovus`` or similar
   P&R tools, closing timing and DRCs.
5. **Sign-off** — the agent runs STA, power analysis, and physical
   verification, producing a GDSII tape-out package.
6. **Summary report** — the agent generates a human-readable report
   of the final QoR (timing, power, area).

Enabling Technologies
---------------------

**SiliconCompiler as the EDA abstraction layer**
  `SiliconCompiler <https://www.siliconcompiler.com/>`__ normalises
  tool interfaces across synthesis, P&R, and sign-off.  Integrating it
  as EDAI's execution engine would give the agent a single, consistent
  API to the entire RTL-to-GDSII flow.

**Model Context Protocol (MCP)**
  The `Model Context Protocol <https://modelcontextprotocol.io/>`__
  standardises how AI models interact with tools.  An MCP server for
  EDA tools would allow any MCP-compatible agent to drive the flow
  without tool-specific glue code.

**Multi-Agent Collaboration**
  Inspired by frameworks like `CrewAI <https://www.crewai.com/>`__,
  future versions may assign different roles ("Synthesis Engineer",
  "Timing Expert", "Physical Design Engineer") to separate agent
  instances that collaborate on the design.

.. note::

   EDAI is an open-source project.  Feature requests, bug reports, and
   contributions are welcome at
   https://github.com/tanlinfeng/EDAI.

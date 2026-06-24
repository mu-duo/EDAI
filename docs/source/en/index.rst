====================================
EDAI — AI-Powered EDA Toolkit
====================================

**EDAI** (Electronic Design AI) is an intelligent CLI toolkit that bridges
natural language and Electronic Design Automation (EDA) tool commands.  It
provides a Textual-based TUI where designers can type Tcl commands directly
*or* describe their intent in natural language — the built-in LLM agent
translates and executes the appropriate backend commands.

.. image:: ../_static/edai-banner.png
   :alt: EDAI Banner
   :width: 100 %
   :target: https://github.com/tanlinfeng/EDAI

Key highlights
==============

* **Hybrid input** — raw Tcl for power users, natural language for rapid
  prototyping and learning.
* **LLM-powered agent** — understands design intent, generates multi-step
  Tcl command sequences, and can self-correct on errors.
* **Pluggable backends** — in-memory mock for development and testing, or
  connect to real EDA tools (``tclsh``, ``dc_shell``, ``genus``, etc.).
* **Persistent sessions** — tool variables, design data, and timing reports
  are preserved across consecutive commands.
* **Special REPL commands** — ``/help``, ``/debug``, ``/history``, and more
  for controlling the agent environment.
* **Global debug infrastructure** — toggle verbose logging with ``/debug``
  to inspect every command and agent decision.

Documentation
=============

.. toctree::
   :maxdepth: 2

   overview
   usage
   architecture

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

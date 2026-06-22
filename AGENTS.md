# EDAI — agent instructions

## What this is

A Python CLI toolkit (`edai`) for EDA (Electronic Design Automation) workflows.
Provides a **Textual TUI** with:
* Direct Tcl command execution — real EDA tool via pexpect session, or in-memory mock
* NL→Tcl agent translation — keyword-matching mock agent or LangGraph-based graph agent
* LLM-powered agent via `BaseAgent` (`langchain-deepseek` / `ChatDeepSeek`)

## Entrypoints

| Purpose | Location |
|---------|----------|
| CLI entry (console_scripts) | `edai.cli:main` |
| Package version | `edai.__version__` (`src/edai/__init__.py`, currently `"0.1.0"`) |
| `python -m edai` | `edai/__main__.py` |
| Subcommands | `tui` (defined in `edai/cli.py`; default when no subcommand given) |

## Dev workflow

```powershell
# One-time setup
pip install -e ".[dev]"

# Run everything (pre-commit does this order)
ruff check src tests
ruff format src tests          # add --check to validate only
mypy src
pytest

# Run a single test file
pytest tests/test_agent.py -v

# Build and check distribution
python -m build
twine check dist/*
```

## Architecture notes

- **`src/edai/core/cmd_registry.py`** — decorator-based command registration. Module-level singleton `registry`.
  Add new Tcl commands via `@command(category="...")` in any module. The handler signature is `def handler(engine, args: list[str]) -> str`.
- **`src/edai/tool/tcl/cmd_defs.py`** — all ~150 registered Tcl commands, organized in categories (COMMON, STA/SDC, SYNTHESIS, etc.). **Force-imported** by `engine.py` line 16 (`import edai.tool.tcl.cmd_defs  # noqa: F401`). If you add a new command module, import it the same way.
- **`src/edai/core/mock_cmds.py`** — replacement for the old `cmd_defs.py`. ~7 registered mock Tcl commands (`get_cells`, `get_nets`, `get_ports`, `create_clock`, `report_timing`, `place_design`, `route_design`). **Force-imported** by `mock_repl.py` line 35 (`import edai.core.mock_cmds  # noqa: F401`).
- **`src/edai/core/mock_engine.py`** — in-memory mock EDA engine (`MockTclEngine`) with static design database (6 cells, 5 nets, 5 ports, 1 library, 1 clock). Exposes query helpers (`get_cell_names`, `get_pin_names`, etc.) used by commands and agents.
- **`src/edai/core/mock_repl.py`** — self-contained mock Tcl REPL (`MockTclRepl`) using stdlib `input()`. Dispatches `/`-prefixed special commands and registered Tcl commands. Also handles `set` (variables) and `expr` (safe arithmetic).
- **`src/edai/core/special_cmds.py`** — registry and built-in commands for `/`-prefixed REPL meta-commands (`/help`, `/exit`, `/clear`, `/debug`, `/env`). Uses dedicated `SpecialCommandRegistry`; handler signature `(engine, repl, args) -> str | None`.
- **`src/edai/core/eda_interactive.py`** — `EDAInteractive`: persistent pexpect subprocess to a real EDA tool (tclsh, dc_shell, etc.). Session stays alive across commands.
- **`src/edai/core/python_interactive.py`** — `PythonInteractive`: persistent Python REPL subprocess via pexpect, with real prompt detection (`>>>` / `...`).
- **`src/edai/core/Message.py`** — canonical `Message` class for all messages (system, human, ai, tool). Provides langchain bridging (`to_langchain` / `from_langchain`) and dict serialization.
- **`src/edai/agent/BaseAgent.py`** — foundation agent with real LLM integration via `langchain_deepseek.ChatDeepSeek`. Maintains conversation history as `list[Message]`.
- **`src/edai/agent/EdaiAgent.py`** — extends `BaseAgent` with EDA role description from `src/edai/roles/EDAI.md`.
- **`src/edai/agent/DesignAgent.py`** — extends `BaseAgent` for design-task NL→Tcl translation.
- **`src/edai/agent/graph.py`** — `LangGraphAgent`: state-graph NL→Tcl translator using `langgraph`. Three-node loop (`agent → router → tools → agent`). Uses langchain `BaseMessage` in graph state; converts from/to `Message` at node boundaries.
- **`src/edai/agent/agent.py`** — legacy mock `Agent` (keyword matching, no real LLM). Backward-compatible; `translate()` / `translate_sync()` API matches the old interface.
- **`src/edai/agent/config.py`** — `AgentConfig` dataclass (model, tools, max_iterations, delay). Loadable from JSON via `from_json()`.
- **`src/edai/tool/eda_interpreter.py`** — LangChain `BaseTool` wrapping `EDAInteractive`. Sends Tcl commands to a real EDA tool.
- **`src/edai/tool/python_interpreter.py`** — LangChain `BaseTool` wrapping `PythonInteractive`. Executes Python code in a persistent REPL.
- **`src/edai/ui/app.py`** — `EdaiApp`: Textual TUI wrapping an EDA back-end (real or mock) with NL→Tcl agent dispatch. Every input/response is tracked as a `Message`. Auto-selects back-end (tclsh on PATH → real; else mock).
- **`src/edai/roles/`** — role description markdown files (`EDAI.md`, `Designer.md`) loaded as system prompts by the agents.

## Config quirks

| Setting | Detail |
|---------|--------|
| `pyproject.toml` build | setuptools, version from `edai.__version__` attribute, package discover under `src/` |
| ruff | line-length=88, double quotes, docstring-code-format=true |
| ruff lint | selects E/W/F/I/N/D/UP/B/SIM/ARG. Ignores D100-D107, D203, D213. Tests ignore D/N/ARG. |
| mypy | `strict = true` but many `disallow_any_* = false`. `mock_cmds.py` has `ignore_errors = true`. |
| pytest | asyncio_mode=auto, `pythonpath = ["src"]`, `--cov=edai --cov-report=term-missing` |
| pre-commit hooks | ruff --fix, ruff-format, mypy |

## Testing

- `tests/conftest.py` provides `cli_runner` fixture — captures stdout from `edai.cli.main()`.
- Agent tests use `@pytest.mark.asyncio` and set `agent.delay = 0` to avoid timer overhead.
- REPL tests test `_handle_input` directly (non-interactive path).
- Special-command tests cover registry mechanics and built-in `/` commands.
- REPL session is never started in tests (`MockTclRepl` is created, `run()` is not called).

## Operational gotchas

- Default REPL history file: `.eda_history` (in CWD).
- The mock design DB has 6 cells, 5 nets, 1 library, 1 clock, 5 ports. Any command that mutates state acts on this in-memory DB.
- `report_timing` requires `place_design` first (checks `engine._placed`).
- `route_design` requires `place_design` first.
- The `cmds.txt` file at root is a reference command list, NOT imported by code.
- `MANIFEST.in` excludes `tests/`, `docs/`, `.github/` from sdist.

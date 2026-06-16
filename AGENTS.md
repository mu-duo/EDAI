# EDAI — agent instructions

## What this is

A Python CLI toolkit (`edai`) for EDA (Electronic Design Automation) workflows.
Provides an interactive Tcl REPL with a mock LLM agent for natural-language → Tcl translation.

## Entrypoints

| Purpose | Location |
|---------|----------|
| CLI entry (console_scripts) | `edai.cli:main` |
| Package version | `edai.__version__` (`src/edai/__init__.py`, currently `"0.1.0"`) |
| `python -m edai` | `edai/__main__.py` |
| Subcommands | `hello`, `repl` (both defined in `edai/cli.py`) |

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
pytest tests/test_tcl_engine.py -v

# Build and check distribution
python -m build
twine check dist/*
```

## Architecture notes

- **`src/edai/core/cmd_registry.py`** — decorator-based command registration. Module-level singleton `registry`.
  Add new Tcl commands via `@command(category="...")` in any module. The handler signature is `def handler(engine, args: list[str]) -> str`.
- **`src/edai/tool/tcl/cmd_defs.py`** — all ~150 registered Tcl commands, organized in categories (COMMON, STA/SDC, SYNTHESIS, etc.). **Force-imported** by `engine.py` line 16 (`import edai.tool.tcl.cmd_defs  # noqa: F401`). If you add a new command module, import it the same way.
- **`src/edai/tool/tcl/engine.py`** — mock Tcl engine with in-memory design database (`_build_mock_db()`). Exposes query helpers (`get_cell_names`, `get_pin_names`, etc.) used by both commands and the completer.
- **`src/edai/tool/tcl/repl.py`** — `prompt_toolkit` REPL. The `PromptSession` is **lazy-initialized** (`EdaRepl.session` property) to avoid Win32 console errors in tests.
- **`src/edai/tool/tcl/completer.py`** — context-aware tab completer: handles `$var`, `[...]` subcommands, flags, and positional EDA object names.
- **`src/edai/agent/agent.py`** — mock LLM agent. `translate()` is async; `translate_sync()` wraps it with `asyncio.run()`. Has `delay` property (default `0.3s`). Replace body with a real LLM API call.

## Config quirks

| Setting | Detail |
|---------|--------|
| `pyproject.toml` build | setuptools, version from `edai.__version__` attribute, package discover under `src/` |
| ruff | line-length=88, double quotes, docstring-code-format=true |
| ruff lint | selects E/W/F/I/N/D/UP/B/SIM/ARG. Ignores D100-D107, D203, D213. Tests ignore D/N/ARG. |
| mypy | `strict = true` but many `disallow_any_* = false`. `cmd_defs.py` has `ignore_errors = true`. |
| pytest | asyncio_mode=auto, `pythonpath = ["src"]`, `--cov=edai --cov-report=term-missing` |
| pre-commit hooks | ruff --fix, ruff-format, mypy |

## Testing

- `tests/conftest.py` provides `cli_runner` fixture — captures stdout from `edai.cli.main()`.
- Agent tests use `@pytest.mark.asyncio` and set `agent.delay = 0` to avoid timer overhead.
- REPL tests test `_handle_input` directly (non-interactive path).
- Completer tests create `prompt_toolkit.Document` objects manually.
- REPL session is never started in tests (`EdaRepl` is created, `run()` is not called).

## Operational gotchas

- Default REPL history file: `.eda_history` (in CWD).
- The mock design DB has 6 cells, 5 nets, 1 library, 1 clock, 5 ports. Any command that mutates state acts on this in-memory DB.
- `report_timing` requires `place_design` first (checks `engine._placed`).
- `route_design` requires `place_design` first.
- The `cmds.txt` file at root is a reference command list, NOT imported by code.
- `MANIFEST.in` excludes `tests/`, `docs/`, `.github/` from sdist.

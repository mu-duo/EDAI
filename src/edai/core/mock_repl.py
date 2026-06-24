"""Mock Tcl REPL — interactive session without a real EDA backend.

Provides :class:`MockTclRepl`, a self-contained Tcl-like REPL that simulates
an EDA tool (Synopsys / Cadence) entirely in memory.  Useful for:
    * Debugging the agent or UI without a licensed EDA tool.
    * Running integration tests that need an interactive Tcl session.
    * Development / demo on machines without the backend installed.

Commands:

    * **Registered Tcl commands** (``get_cells``, ``report_timing``, …)
      are dispatched via :data:`edai.core.cmd_registry.registry`.
    * **Special REPL commands** (``/help``, ``/exit``, …) are dispatched
      via :data:`edai.core.special_cmds.registry`.
    * ``set <var> <value>`` — set a Tcl variable (``$var`` references in the value are resolved).
    * ``set <var>`` — print a variable's value.
    * ``puts [-nonewline] <value>`` — print a value (with ``$var`` substitution).
    * ``expr <expression>`` — evaluate an arithmetic expression.
    * ``$var`` / ``${var}`` substitution in command arguments.

Usage::

    from edai.core.mock_repl import MockTclRepl

    repl = MockTclRepl()
    repl.run()
"""

from __future__ import annotations

import ast
import operator
import shlex
import sys

import edai.core.mock_cmds  # noqa: F401  -- force-register mock commands
from edai.core.cmd_registry import CommandError
from edai.core.cmd_registry import registry as cmd_registry
from edai.core.mock_engine import MockTclEngine
from edai.core.special_cmds import registry as special_registry

# ── safe arithmetic evaluator ─────────────────────────────────────────


_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(expr_str: str, variables: dict[str, str]) -> str:
    """Evaluate a simple arithmetic expression using only ``int`` / ``float``.

    Supports numbers, basic operators, and ``$var`` references.
    """
    # Resolve $var references first
    for name, value in variables.items():
        expr_str = expr_str.replace(f"${name}", f"({value})")

    try:
        tree = ast.parse(expr_str.strip(), mode="eval")
    except SyntaxError:
        return f"Syntax error in expression: {expr_str}"

    def _eval_node(node: ast.AST) -> complex | int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp):
            operand = _eval_node(node.operand)
            op_fn = _ALLOWED_OPS.get(type(node.op))
            if op_fn is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_fn(operand)  # type: ignore[no-any-return,operator]
        if isinstance(node, ast.BinOp):
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            op_fn = _ALLOWED_OPS.get(type(node.op))
            if op_fn is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_fn(left, right)  # type: ignore[no-any-return,operator]
        raise ValueError(f"Unsupported expression: {type(node).__name__}")

    try:
        result = _eval_node(tree.body)
    except (ValueError, ZeroDivisionError) as exc:
        return f"Error: {exc}"

    # Format nicely
    formatted = f"{result:g}" if isinstance(result, float) else str(result)
    return formatted


# ── REPL class ────────────────────────────────────────────────────────


class MockTclRepl:
    """Interactive mock Tcl REPL.

    Parameters
    ----------
    engine:
        A :class:`MockTclEngine` instance.  Created automatically if omitted.
    prompt:
        REPL prompt string.
    intro:
        Message printed at startup (set to ``None`` to suppress).

    """

    backend_type = "mock"
    """Identifier for backend MD docs (``roles/backends/mock.md``)."""

    def __init__(
        self,
        engine: MockTclEngine | None = None,
        prompt: str = "tcl> ",
        intro: str | None = None,
    ) -> None:
        self.engine = engine or MockTclEngine()
        self.prompt = prompt
        self.intro = intro or (
            "Mock Tcl REPL — EDA tool simulation (no real backend required).\n"
            "Type /help for available commands."
        )
        self.verbose = False  # toggled by /debug

    # ── public API ───────────────────────────────────────────────────

    def run(self) -> None:
        """Start the interactive REPL loop.

        Reads lines from stdin, dispatches commands, and prints results.
        Exits on ``/exit``, ``/quit``, EOF, or KeyboardInterrupt.
        """
        if self.intro:
            print(self.intro)

        while True:
            try:
                line = input(self.prompt)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                break

            result = self._handle_input(line)
            if result:  # non-None and non-empty
                print(result)

    def _handle_input(self, line: str) -> str | None:
        """Process a single line of input and return the output.

        Returns ``None`` when there is nothing to print (empty line, /clear).
        """
        line = line.strip()
        if not line:
            return None

        # ── special commands (/exit, /help, …) ──────────────────
        if line.startswith("/"):
            return self._handle_special(line)

        # ── puts command (print) ────────────────────────────────
        if line.startswith("puts") and (len(line) == 4 or line[4:5] in (" ", "-")):
            return self._handle_puts(line)

        # ── set command (variable assignment) ───────────────────
        if line.startswith("set ") or line == "set":
            return self._handle_set(line)

        # ── expr command (arithmetic) ───────────────────────────
        if line.startswith("expr "):
            expr_str = line[5:].strip()
            return _safe_eval(expr_str, self.engine.variables)

        # ── registered Tcl commands ─────────────────────────────
        return self._handle_tcl_cmd(line)

    # ── internal dispatchers ────────────────────────────────────────

    def _handle_special(self, line: str) -> str | None:
        """Dispatch a ``/``-prefixed special command."""
        parts = shlex.split(line)
        raw_name = parts[0]  # e.g. "/help"
        cmd_name = raw_name.lstrip("/")
        cmd_args = parts[1:]

        try:
            return special_registry.execute(cmd_name, self.engine, self, cmd_args)
        except CommandError as exc:
            return str(exc)
        except SystemExit:
            raise  # let /exit propagate

    def _handle_set(self, line: str) -> str:
        """Handle ``set <var>`` or ``set <var> <value>``."""
        args = shlex.split(line)
        # args[0] == "set"
        if len(args) == 1:
            return "Usage: set <var> [<value>]"
        if len(args) == 2:
            # ``set var`` — return current value
            value = self.engine.get_var(args[1])
            if value is None:
                return f"Variable '{args[1]}' is not set."
            return value
        # ``set var value value2…`` — join remaining as value
        var_name = args[1]
        var_value = " ".join(args[2:])
        # Resolve $var / ${var} references in the value (real Tcl behavior)
        var_value = self.engine._substitute_var(var_value)
        return self.engine.set_var(var_name, var_value)

    def _handle_puts(self, line: str) -> str:
        """Handle ``puts [-nonewline] <value>`` — print a value.

        In real Tcl, ``puts`` outputs text to stdout.  In the REPL, the
        returned string is printed by the caller (``_handle_input``).

        Supports ``$var`` / ``${var}`` variable substitution.
        """
        args = shlex.split(line)
        # args[0] == "puts"
        if len(args) == 1:
            # ``puts`` — print a newline (return empty string)
            return ""

        no_newline = False
        start_idx = 1
        if args[1] == "-nonewline":
            no_newline = True
            start_idx = 2

        if len(args) <= start_idx:
            # nothing to print
            return ""

        value = " ".join(args[start_idx:])
        # Variable substitution
        value = self.engine._substitute_var(value)
        return value

    def _handle_tcl_cmd(self, line: str) -> str:
        """Dispatch a registered Tcl command (with ``$var`` subst)."""
        parts = shlex.split(line)
        if not parts:
            return ""

        cmd_name = parts[0]
        raw_args = parts[1:]

        # Variable substitution
        substituted = self.engine.substitute_vars(raw_args)

        if self.verbose:
            print(f"[debug] cmd={cmd_name!r} args={substituted}")

        try:
            return cmd_registry.execute(cmd_name, self.engine, substituted)
        except CommandError as exc:
            return str(exc)

    # ── convenience (non-interactive) ────────────────────────────────

    def send_command(self, code: str) -> str:
        """Send a single command and return the output (non-interactive).

        Useful for testing or programmatic use.
        """
        result = self._handle_input(code)
        return result or ""


# ── entry-point helper ────────────────────────────────────────────────


def run_mock_repl() -> int:
    """Create and start a :class:`MockTclRepl`.

    Returns ``0`` on normal exit.
    """
    import contextlib

    repl = MockTclRepl()
    with contextlib.suppress(SystemExit):
        repl.run()
    return 0


if __name__ == "__main__":
    sys.exit(run_mock_repl())

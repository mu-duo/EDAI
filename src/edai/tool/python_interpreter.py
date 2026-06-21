"""Python code execution tool for the EDAI agent.

Provides a LangChain ``BaseTool`` that executes Python code in a persistent
pexpect REPL session.  State (imports, variables, classes, etc.) is preserved
across consecutive calls within the same session.
"""

from __future__ import annotations

import sys

import pexpect
import rich
from langchain.tools import BaseTool
from pydantic import PrivateAttr
from rich.markup import escape


class PythonInterpreter(BaseTool):
    """Execute Python code on the host machine and return the output.

    Uses a persistent interactive Python REPL — state (imports, variables,
    classes, functions, etc.) is preserved between consecutive calls within
    the same session.

    * Use ``print()`` to see expression values::

          result = sum(range(100))
          print(f"sum = {result}")

    * Each invocation is subject to a 30-second timeout.
    * Code that calls ``exit()`` / ``quit()`` will end the REPL session
      (it will be restarted automatically on the next call).
    """

    name: str = "python_interpreter"
    description: str = (
        "Execute Python code on the host machine and return the output. "
        "Use print() to see expression values."
    )
    return_direct: bool = True

    # ── private: persistent REPL child ────────────────────────────────

    EDA_tool: pexpect.spawn | None = PrivateAttr(default=None)

    def _get_repl(self) -> pexpect.spawn:
        """Return a persistent Python REPL, (re)starting if needed."""
        if self.EDA_tool is None or not self.EDA_tool.isalive():
            self.EDA_tool = pexpect.spawn(
                sys.executable, ["-q"], timeout=30, encoding="utf-8"
            )
            self.EDA_tool.expect(">>> ")
        return self.EDA_tool

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _clean_output(raw: str, sent: str) -> str:
        """Strip echoed command and trailing whitespace from REPL output."""
        lines = raw.splitlines()
        # First line is the echoed command — remove it
        if lines and sent.strip() in lines[0]:
            lines = lines[1:]
        # Remove trailing blank lines from REPL prompt artifacts
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines).strip()

    # ── tool interface ────────────────────────────────────────────────

    def _run(self, code: str) -> str:
        """Execute Python code and return the output."""
        # Echo to console so callers can see what is being executed
        rich.print(f"{escape('[tool][python]')} {code}")

        if not code.strip():
            return "No code provided."

        try:
            child = self._get_repl()
        except Exception as exc:  # noqa: BLE001
            return f"Failed to start Python REPL: {exc}"

        # Build a single-line command that exec()s arbitrary user code.
        # repr() guarantees valid Python string escaping (handles all quote
        # styles, multiline, etc.), so it is safe to inline into exec().
        send = f"exec({repr(code)})"

        try:
            child.sendline(send)
            index = child.expect([">>> ", pexpect.EOF, pexpect.TIMEOUT], timeout=30)
        except Exception as exc:  # noqa: BLE001
            return f"REPL communication error: {exc}"

        # Before the prompt we get the echoed command + stdout/stderr
        raw = child.before or ""
        output = self._clean_output(raw, send)

        if index == 1:  # EOF — REPL exited unexpectedly
            self.EDA_tool = None  # will be re-spawned on next call
            return f"REPL closed.\n{output}" if output else "REPL closed unexpectedly."

        if index == 2:  # TIMEOUT — code took too long
            msg = "Execution timed out (30s)."
            return f"{msg}\n{output}" if output else msg

        if not output:
            # Code ran successfully but produced no stdout/stderr
            return "Done (no output)."

        return output

    async def _arun(self, code: str) -> str:
        """Execute Python code asynchronously (synchronous wrapper)."""
        return self._run(code)

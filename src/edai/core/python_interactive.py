"""Python interactive session manager.

Manages a persistent pexpect subprocess for a Python REPL. The session stays
alive across consecutive calls — state (imports, variables, classes, functions)
is preserved.  Sends code line by line with real prompt detection.
"""

from __future__ import annotations

import re
import sys

import pexpect
import rich
from rich.markup import escape


class PythonInteractive:
    """Manage a persistent interactive Python REPL subprocess.

    Wraps a ``pexpect.spawn`` child that runs the Python REPL (``python -q``).
    Send Python code with :meth:`send_command` — the session (imports, variables,
    classes, functions, etc.) is preserved across calls.

    Code is sent line by line.  After each line the actual prompt (``>>> `` or
    ``... ``) is detected to determine whether the REPL expects more input.
    If the REPL is still waiting after all user lines have been sent, blank
    lines are sent automatically to complete the compound statement.

    Parameters
    ----------
    prompt:
        Primary prompt string (display and pattern). Default ``">>> "``.
    timeout:
        Seconds to wait for each REPL interaction (per line).

    """

    def __init__(
        self,
        prompt: str = ">>> ",
        timeout: int = 30,
    ) -> None:
        self.prompt = prompt
        self._primary = prompt  # current primary prompt (regex-safe literal)
        self._initial_prompt = ">>> "  # what a fresh REPL shows
        self._secondary = "... "  # continuation prompt
        self._timeout = timeout

        self._child: pexpect.spawn | None = None

    # ── public API ───────────────────────────────────────────────────

    def send_command(self, code: str) -> str:
        """Send Python code to the REPL and return the output.

        Lines are sent one at a time with real prompt detection.
        If the REPL shows the continuation prompt (``... ``) after all
        user lines have been sent, blank lines are submitted automatically
        to complete the compound statement.

        Parameters
        ----------
        code:
            Python source code (may span multiple lines).

        Returns
        -------
        str
            Combined stdout output with echo and prompt artifacts removed.

        """
        self._echo(code)

        if not code.strip():
            return ""

        try:
            child = self._get_repl()
        except Exception as exc:  # noqa: BLE001
            return f"Failed to start Python REPL: {exc}"

        lines = code.splitlines()
        output_parts: list[str] = []

        try:
            last_was_continuation = self._send_lines(child, lines, output_parts)
            if last_was_continuation:
                self._close_continuation(child, output_parts)
        except Exception as exc:  # noqa: BLE001
            return f"REPL communication error: {exc}"

        if not output_parts:
            return "Done (no output)."

        return "\n".join(output_parts)

    def close(self) -> None:
        """Close the REPL subprocess if it is still alive."""
        if self._child is not None and self._child.isalive():
            self._child.close(force=True)
        self._child = None

    def set_prompt(self, primary: str, secondary: str = "... ") -> None:
        """Update the REPL prompt strings via ``sys.ps1`` / ``sys.ps2``.

        Parameters
        ----------
        primary:
            New primary prompt (e.g. ``"py> "``).
        secondary:
            New continuation prompt (e.g. ``"py.. "``).

        """
        try:
            child = self._get_repl()
        except Exception as exc:  # noqa: BLE001
            return rich.print(f"[red]Failed to set prompt: {exc}[/red]")

        self._set_prompt_raw(child, primary, secondary)
        self.prompt = primary
        self._primary = primary
        self._secondary = secondary
        self._echo(f"Prompt updated to: {primary}")

    # ── internal helpers ─────────────────────────────────────────────

    def _get_repl(self) -> pexpect.spawn:
        """Return the persistent REPL subprocess, (re)starting if needed."""
        if self._child is not None and self._child.isalive():
            return self._child

        self._child = pexpect.spawn(
            sys.executable,
            ["-q"],
            timeout=self._timeout,
            encoding="utf-8",
        )
        # Wait for the initial Python REPL prompt
        self._child.expect(re.escape(self._initial_prompt), timeout=30)

        # If a non-default prompt was requested, configure it now
        if self._primary != self._initial_prompt:
            self._set_prompt_raw(self._child, self._primary, self._secondary)

        return self._child

    def _set_prompt_raw(
        self,
        child: pexpect.spawn,
        primary: str,
        secondary: str,
    ) -> None:
        """Set prompts on an already-running REPL child (raw pexpect)."""
        code = (
            f"import sys; sys.ps1 = {repr(primary)};"
            f" sys.ps2 = {repr(secondary)}"
        )
        child.sendline(f"exec({repr(code)})")
        child.expect(re.escape(primary), timeout=30)  # consume echo
        child.expect(re.escape(primary), timeout=30)  # actual next prompt

    def _send_lines(
        self,
        child: pexpect.spawn,
        lines: list[str],
        output_parts: list[str],
    ) -> bool:
        """Send user lines one by one, detecting prompts.

        Returns ``True`` if the REPL ended on the continuation prompt
        (``... ``) and needs blank-line completion.
        """
        if not lines:
            return False

        index = -1
        for _i, line in enumerate(lines):
            child.sendline(line)
            index = child.expect(
                [
                    re.escape(self._primary),
                    re.escape(self._secondary),
                    pexpect.EOF,
                    pexpect.TIMEOUT,
                ],
                timeout=self._timeout,
            )

            raw = child.before or ""
            output = self._clean_output(raw, line)
            if output:
                output_parts.append(output)

            if index == 2:  # EOF — REPL exited
                self._child = None
                result = "\n".join(output_parts)
                raise _ReplClosedError(
                    f"REPL closed.\n{result}" if result else "REPL closed unexpectedly."
                )

            if index == 3:  # TIMEOUT
                self._child = None
                if child.isalive():
                    child.close(force=True)
                result = "\n".join(output_parts)
                msg = (
                    f"Execution timed out ({self._timeout}s).\n{result}"
                    if result
                    else f"Execution timed out ({self._timeout}s)."
                )
                raise _ReplClosedError(msg)

            if index == 1:
                # Still on continuation prompt
                pass

        # Check final state
        return index == 1  # True if last prompt was continuation

    def _close_continuation(
        self,
        child: pexpect.spawn,
        output_parts: list[str],
    ) -> None:
        """Send blank lines until the REPL returns to the primary prompt."""
        while True:
            child.sendline("")
            index = child.expect(
                [
                    re.escape(self._primary),
                    re.escape(self._secondary),
                    pexpect.EOF,
                    pexpect.TIMEOUT,
                ],
                timeout=self._timeout,
            )

            raw = child.before or ""
            output = self._clean_output(raw, "")
            if output:
                output_parts.append(output)

            if index == 1:  # Still in continuation — send another blank
                continue

            if index == 2:  # EOF
                self._child = None
                raise _ReplClosedError(
                    "REPL closed unexpectedly."
                )

            if index == 3:  # TIMEOUT
                self._child = None
                if child.isalive():
                    child.close(force=True)
                raise _ReplClosedError(
                    f"Execution timed out ({self._timeout}s)."
                )

            # index == 0 — back to primary prompt
            return

    @staticmethod
    def _clean_output(raw: str, sent: str) -> str:
        """Strip echoed command and trailing whitespace from REPL output."""
        lines = raw.splitlines()
        # First line is typically the echoed command — remove it
        if lines and sent.strip() in lines[0]:
            lines = lines[1:]
        # Remove trailing blank lines
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines).strip()

    def _echo(self, code: str) -> None:
        """Print the code to the console with a python prefix."""
        if not code.strip():
            return
        rich.print(f"{escape('[tool][python]')} {code.strip()}")


class _ReplClosedError(Exception):
    """Internal exception used to unwind the send loop when the REPL dies."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


if __name__ == "__main__":
    # Example usage — simple one-line-at-a-time interactive loop
    py = PythonInteractive(prompt=">>> ", timeout=30)
    print(repr(py.send_command("1 + 1")))
    print(repr(py.send_command("x = 42")))
    print(repr(py.send_command("print(f'x = {x}')")))
    print(repr(py.send_command("def foo():\n    return 42")))
    print(repr(py.send_command("foo()")))
    py.set_prompt("py> ")
    while True:
        try:
            cmd = input(f"{py.prompt}")
        except (EOFError, KeyboardInterrupt):
            break
        if cmd.strip().lower() in ("exit", "quit"):
            break
        output = py.send_command(cmd)
        if output:
            print(output)
    py.close()

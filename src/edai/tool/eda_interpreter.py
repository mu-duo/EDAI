"""EDA tool execution tool for the EDAI agent.

Provides a LangChain ``BaseTool`` that interacts with an external EDA tool
(e.g. Synopsys DC, Cadence Genus, Cadence Innovus) via a persistent pexpect
subprocess.  The EDA session stays alive across consecutive calls so the user
can incrementally build up a design flow.
"""

from __future__ import annotations

import os

import pexpect
import rich
from langchain.tools import BaseTool
from pydantic import PrivateAttr
from rich.markup import escape


class EDAInterpreter(BaseTool):
    """Send commands to an external EDA tool and return the output.

    Uses a persistent interactive subprocess — the EDA tool session (variables,
    design data, timing reports, etc.) is preserved across consecutive calls.

    * The tool is spawned once and reused.  If the process exits unexpectedly
      it is restarted on the next call.
    * Set ``bin_path`` to the full path of the EDA tool binary (e.g.
      ``/usr/bin/dc_shell``, ``genus``, ``innovus``).
    * The ``prompt`` argument controls what string/regex is expected as the
      command prompt (default ``r'\\\\% '`` — a literal ``% `` prompt
      common in many EDA tools).
    * Each invocation has a configurable timeout (default 300 s).
    """  # noqa: D301

    name: str = "eda_interpreter"
    description: str = (
        "Send a Tcl command to an external EDA tool and return the output. "
        "The EDA session persists across calls."
    )
    return_direct: bool = True

    # ── user-facing configuration (Pydantic fields) ────────────────────

    bin_path: str
    """Path to the EDA tool binary (e.g. ``/usr/bin/dc_shell``)."""

    tool_args: list[str] = []
    """Extra command-line arguments passed to the EDA tool on startup."""

    prompt: str = r"\% "
    """Prompt pattern expected by ``pexpect`` (regex string).

    Most EDA tools display ``% `` as the interactive prompt.
    Override for tools with a different prompt (e.g. ``dc_shell> `` or
    ``genus> ``).
    """

    timeout: int = 300
    """Seconds to wait for a command to complete (default 300)."""

    # ── private: persistent subprocess ─────────────────────────────────

    _child: pexpect.spawn | None = PrivateAttr(default=None)

    def _get_repl(self) -> pexpect.spawn:
        """Return a persistent EDA tool subprocess, (re)starting if needed."""
        if self._child is not None and self._child.isalive():
            return self._child

        bin_path = self.bin_path
        if not os.path.isfile(bin_path) and not any(
            os.path.isfile(p + "/" + bin_path)
            for p in os.environ.get("PATH", "").split(os.pathsep)
        ):
            raise FileNotFoundError(f"EDA tool binary not found: {bin_path}")

        self._child = pexpect.spawn(
            bin_path,
            self.tool_args,
            timeout=self.timeout,
            encoding="utf-8",
            echo=False,
        )
        # Wait for the initial prompt
        self._child.expect(self.prompt, timeout=30)
        return self._child

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _clean_output(raw: str, sent: str) -> str:
        """Strip echoed command and trailing whitespace from output."""
        lines = raw.splitlines()
        # First line is typically the echoed command — remove it
        if lines and sent.strip() in lines[0]:
            lines = lines[1:]
        # Remove trailing blank lines
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines).strip()

    def _echo(self, code: str) -> None:
        """Print the command to the console with a tool prefix."""
        rich.print(f"{escape('[tool][eda]')} {code.strip() or '<empty>'}")

    # ── tool interface ────────────────────────────────────────────────

    def _run(self, code: str) -> str:
        """Send a Tcl command to the EDA tool and return the output."""
        self._echo(code)

        if not code.strip():
            return "No command provided."

        try:
            child = self._get_repl()
        except Exception as exc:  # noqa: BLE001
            return f"Failed to start EDA tool: {exc}"

        try:
            child.sendline(code)
            index = child.expect(
                [self.prompt, pexpect.EOF, pexpect.TIMEOUT],
                timeout=self.timeout,
            )
        except Exception as exc:  # noqa: BLE001
            return f"Communication error: {exc}"

        raw = child.before or ""
        output = self._clean_output(raw, code)

        if index == 1:  # EOF — tool exited
            self._child = None
            return f"Tool closed.\n{output}" if output else "Tool closed unexpectedly."

        if index == 2:  # TIMEOUT
            # Kill the stale process so next call starts fresh
            self._child = None
            if child.isalive():
                child.close(force=True)
            return (
                f"Command timed out ({self.timeout}s).\n{output}"
                if output
                else f"Command timed out ({self.timeout}s)."
            )

        if not output:
            return "Done (no output)."

        return output

    async def _arun(self, code: str) -> str:
        """Send a Tcl command asynchronously (synchronous wrapper)."""
        return self._run(code)

    # ── factory helper ────────────────────────────────────────────────

    @classmethod
    def for_tool(
        cls,
        bin_path: str,
        *,
        name: str = "eda_interpreter",
        tool_args: list[str] | None = None,
        prompt: str = r"\% ",
        timeout: int = 300,
    ) -> EDAInterpreter:
        """Quick constructor that returns a configured instance.

        Parameters match the field names on the class.
        """
        return cls(
            name=name,
            bin_path=bin_path,
            tool_args=tool_args or [],
            prompt=prompt,
            timeout=timeout,
        )

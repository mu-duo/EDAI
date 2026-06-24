"""EDA tool interactive session manager.

Manages a persistent pexpect subprocess for interacting with an external EDA
tool (e.g. Synopsys DC, Cadence Genus, Cadence Innovus). The session stays
alive across consecutive commands.
"""

from __future__ import annotations

import os

import pexpect
import rich
from rich.markup import escape


class EDAInteractive:
    """Manage a persistent interactive EDA tool subprocess.

    Wraps a ``pexpect.spawn`` child that runs the EDA tool binary.
    Send Tcl commands with :meth:`send_command` — the session (variables,
    design data, timing reports, etc.) is preserved across calls.

    Parameters
    ----------
    bin_path:
        Full path to the EDA tool binary (e.g. ``/usr/bin/dc_shell``).
    tool_args:
        Extra command-line arguments passed on startup.
    prompt:
        Prompt pattern expected by pexpect (regex string).
        Most EDA tools display ``% ``; override for ``dc_shell> `` etc.
    timeout:
        Seconds to wait for a command to complete.

    """

    backend_type = "tclsh"
    """Identifier for backend MD docs (``roles/backends/tclsh.md``)."""

    def __init__(
        self,
        bin_path: str,
        tool_args: list[str] | None = None,
        prompt: str = r"\% ",
        timeout: int = 300,
    ) -> None:
        self.bin_path = bin_path
        self.tool_args = tool_args or []
        self.prompt = prompt
        self._initial_prompt = prompt  # saved for respawn detection
        self.timeout = timeout

        self._child: pexpect.spawn | None = None

        # self.set_prompt("edai>>> ")

    # ── public API ───────────────────────────────────────────────────

    def send_command(self, code: str) -> str:
        """Send a Tcl command to the EDA tool and return the output."""
        self._echo(code)

        if not code.strip():
            return ""

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
            self._child = None
            if child.isalive():
                child.close(force=True)
            return (
                f"Command timed out ({self.timeout}s).\n{output}"
                if output
                else f"Command timed out ({self.timeout}s)."
            )

        return output

    def close(self) -> None:
        """Close the EDA tool subprocess if it is still alive."""
        if self._child is not None and self._child.isalive():
            self._child.close(force=True)
        self._child = None

    def set_prompt(self, prompt: str) -> None:
        """Update the expected prompt pattern for pexpect."""
        try:
            child = self._get_repl()
        except Exception as exc:  # noqa: BLE001
            return rich.print(f"[red]Failed to set prompt: {exc}[/red]")

        # Direct child interaction — do NOT use send_command() which would
        # wait for the *old* prompt pattern that is no longer produced.
        child.sendline(f'set tcl_prompt1 {{puts -nonewline "{prompt}"}}')
        child.expect(prompt, timeout=30) # cmd echo
        child.expect(prompt, timeout=30) # wait for new prompt
        self.prompt = prompt
        self._echo(f"Prompt updated to: {prompt}")

    # ── internal helpers ─────────────────────────────────────────────

    def _get_repl(self) -> pexpect.spawn:
        """Return the persistent subprocess, (re)starting if needed."""
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
        # Wait for the initial prompt (always use the saved initial prompt,
        # since self.prompt may have been changed by set_prompt)
        self._child.expect(self._initial_prompt, timeout=30)
        return self._child

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
        if not code.strip():
            return
        else:
            rich.print(f"{escape('[tool][eda]')} {code.strip()}")


if __name__ == "__main__":
    # Example usage
    eda = EDAInteractive(bin_path="tclsh", prompt=r"% ", timeout=10)
    print(eda.send_command("version"))
    print(eda.send_command("set a 5"))
    print(eda.send_command("puts $a"))
    eda.set_prompt(r"tclsh>>> ")
    while True:
        cmd = input(f"{eda.prompt}")
        if cmd.strip().lower() == "exit":
            break
        output = eda.send_command(cmd)
        if output:
            print(output)
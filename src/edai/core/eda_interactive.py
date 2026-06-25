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
    more_pattern:
        Pattern (regex string) for the pager prompt (e.g. ``--More--``).
        Set to ``None`` to disable pager handling.

    """

    backend_type = "tclsh"
    """Identifier for backend MD docs (``roles/backends/tclsh.md``)."""

    def __init__(
        self,
        bin_path: str,
        tool_args: list[str] | None = None,
        prompt: str = r"\% ",
        timeout: int = 300,
        more_pattern: str | None = r"--More--",
    ) -> None:
        self.bin_path = bin_path
        self.tool_args = tool_args or []
        self.prompt = prompt
        self._initial_prompt = prompt  # saved for respawn detection
        self.timeout = timeout
        self.more_pattern = more_pattern

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

        # Split into lines and send each with \r (CR) instead of \n (LF).
        # Many EDA tools (dc_shell, etc.) operate in raw mode where CR is
        # needed to trigger line processing via gets/read.
        lines = code.split("\n")
        output_parts: list[str] = []

        try:
            for line in lines:
                child.send(line + "\r")

            # Loop until prompt/EOF/timeout, accumulating output across
            # --More-- pages.
            while True:
                # Build expect candidates every iteration (prompt order can't
                # change, but we keep it DRY via a local).
                expect_items = [self.prompt, pexpect.EOF, pexpect.TIMEOUT]
                more_index = None
                if self.more_pattern is not None:
                    more_index = len(expect_items)
                    expect_items.insert(more_index, self.more_pattern)

                idx = child.expect(expect_items, timeout=self.timeout)

                raw = child.before or ""

                if idx == 0:  # PROMPT
                    output_parts.append(raw)
                    break
                elif more_index is not None and idx == more_index:  # --More--
                    output_parts.append(raw)
                    child.send(" ")
                elif idx == 1:  # EOF — tool exited
                    self._child = None
                    output_parts.append(raw)
                    joined = "".join(output_parts)
                    output = self._clean_output(joined, code)
                    return (
                        f"Tool closed.\n{output}"
                        if output
                        else "Tool closed unexpectedly."
                    )
                else:  # TIMEOUT
                    self._child = None
                    output_parts.append(raw)
                    if child.isalive():
                        child.close(force=True)
                    joined = "".join(output_parts)
                    output = self._clean_output(joined, code)
                    return (
                        f"Command timed out ({self.timeout}s).\n{output}"
                        if output
                        else f"Command timed out ({self.timeout}s)."
                    )
        except Exception as exc:  # noqa: BLE001
            return f"Communication error: {exc}"

        joined = "".join(output_parts)
        return self._clean_output(joined, code)

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
        # Use \r to be consistent with send_command (EDA tools in raw mode).
        child.send(f'set tcl_prompt1 {{puts -nonewline "{prompt}"}}{chr(13)}')
        child.expect(prompt, timeout=30)  # cmd echo
        child.expect(prompt, timeout=30)  # wait for new prompt
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
        """Strip echoed command and trailing blank lines from output.

        For multi-line commands the EDA tool typically echoes only the
        first line — this method removes any line that exactly matches
        ``sent``'s first line (trimmed).
        """
        first_line = sent.split("\n", 1)[0].strip()
        lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        # Remove echo line (the first occurrence of the sent first line)
        filtered: list[str] = []
        echo_removed = False
        for ln in lines:
            if not echo_removed and ln.strip() == first_line:
                echo_removed = True
                continue
            filtered.append(ln)
        # Remove trailing blank lines
        while filtered and not filtered[-1].strip():
            filtered.pop()
        return "\n".join(filtered).strip()

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

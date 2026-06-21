"""EDA tool execution tool for the EDAI agent.

Provides a LangChain ``BaseTool`` that delegates to an
:class:`EDAInteractive` session.  The EDA session stays alive across
consecutive calls so the user can incrementally build up a design flow.
"""

from __future__ import annotations

from langchain.tools import BaseTool

from edai.core.eda_interactive import EDAInteractive


class EDAInterpreter(BaseTool):
    """Send commands to an external EDA tool and return the output.

    Uses a persistent interactive subprocess managed by an
    :class:`EDAInteractive` instance — the EDA tool session (variables,
    design data, timing reports, etc.) is preserved across consecutive calls.

    * Pass an :class:`EDAInteractive` instance to the constructor, or use
      the :meth:`for_tool` factory to create both at once.
    * Each invocation has a configurable timeout (default 300 s).
    """

    name: str = "eda_interpreter"
    description: str = (
        "Send a Tcl command to an external EDA tool and return the output. "
        "The EDA session persists across calls."
    )
    return_direct: bool = True

    interactive: EDAInteractive
    """The EDA interactive session backing this tool."""

    # ── tool interface ────────────────────────────────────────────────

    def _run(self, code: str) -> str:
        """Send a Tcl command to the EDA tool and return the output."""
        return self.interactive.send_command(code)

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
        """Create an :class:`EDAInteractive` and wrap it in a tool.

        Parameters match :class:`EDAInteractive` constructor fields.
        """
        interactive = EDAInteractive(
            bin_path=bin_path,
            tool_args=tool_args or [],
            prompt=prompt,
            timeout=timeout,
        )
        return cls(name=name, interactive=interactive)

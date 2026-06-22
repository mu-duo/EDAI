"""Python code execution tool for the EDAI agent.

Provides a LangChain ``BaseTool`` that delegates to a
:class:`PythonInteractive` session.  The Python REPL stays alive across
consecutive calls so state (imports, variables, classes, etc.) is preserved.
"""

from __future__ import annotations

from langchain.tools import BaseTool

from edai.core.python_interactive import PythonInteractive


class PythonInterpreter(BaseTool):
    """Execute Python code on the host machine and return the output.

    Uses a persistent interactive Python REPL managed by a
    :class:`PythonInteractive` instance — state (imports, variables, classes,
    functions, etc.) is preserved between consecutive calls within the same
    session.

    * Use ``print()`` to see expression values::

          result = sum(range(100))
          print(f"sum = {result}")

    * Each invocation is subject to a configurable timeout (default 30 s).
    * Code that calls ``exit()`` / ``quit()`` will end the REPL session
      (it will be restarted automatically on the next call).
    """

    name: str = "python_interpreter"
    description: str = (
        "Execute Python code on the host machine and return the output. "
        "Use print() to see expression values."
    )
    return_direct: bool = True

    interactive: PythonInteractive
    """The Python interactive session backing this tool."""

    # ── tool interface ────────────────────────────────────────────────

    def _run(self, code: str) -> str:
        """Execute Python code and return the output."""
        return self.interactive.send_command(code)

    async def _arun(self, code: str) -> str:
        """Execute Python code asynchronously (synchronous wrapper)."""
        return self._run(code)

    # ── factory helper ────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        *,
        name: str = "python_interpreter",
        prompt: str = ">>> ",
        timeout: int = 30,
    ) -> PythonInterpreter:
        """Create a :class:`PythonInteractive` and wrap it in a tool.

        Parameters match :class:`PythonInteractive` constructor fields.
        """
        interactive = PythonInteractive(prompt=prompt, timeout=timeout)
        return cls(name=name, interactive=interactive)

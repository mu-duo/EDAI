"""Design agent — extends BaseAgent with design-task translation."""

from __future__ import annotations

from edai.agent.BaseAgent import BaseAgent
from edai.core.Message import Message


class DesignAgent(BaseAgent):
    """Agent for design tasks, extending BaseAgent with design-specific methods.

    The ``translate`` method accepts natural-language input and returns a
    Tcl command string, using :class:`~edai.core.Message` factory methods
    internally.
    """

    async def translate(self, natural_language_input: str) -> str:
        """Translate natural language input into a Tcl command.

        Parameters
        ----------
        natural_language_input:
            User request in plain English.

        Returns
        -------
        str
            The translated Tcl command.

        """
        # Build messages using the canonical Message factory
        messages = [
            Message.system(
                "You are a design assistant that translates natural "
                "language into Tcl commands."
            ),
            Message.human(natural_language_input),
        ]

        # BaseAgent.invoke expects a single string — concatenate context
        combined = "\n".join(m.content for m in messages)
        response = self.invoke(combined)
        return response

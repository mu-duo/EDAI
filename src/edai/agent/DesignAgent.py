from .BaseAgent import BaseAgent
from langchain.messages import HumanMessage, SystemMessage, AIMessage


class DesignAgent(BaseAgent):
    """Agent for design tasks, extending BaseAgent with design-specific methods."""

    async def translate(self, natural_language_input: str) -> str:
        """Translate natural language input into a Tcl command."""
        messages = [
            SystemMessage(content="You are a design assistant that translates natural language into Tcl commands."),
            HumanMessage(content=natural_language_input),
        ]
        response = self.invoke(messages)
        if isinstance(response, AIMessage):
            content = response.content
            if isinstance(content, str):
                return content.strip()
            elif isinstance(content, list) and content and isinstance(content[0], str):
                return content[0].strip()
            else:
                raise ValueError("Unexpected content type in AIMessage response.")
        else:
            raise ValueError("Unexpected response type from agent.")
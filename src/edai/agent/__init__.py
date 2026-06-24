"""Agent / LLM integration layer.

Quick start::

    from edai.agent import Agent, AgentConfig
    from edai.core.mock_repl import MockTclRepl

    agent = Agent(backend=MockTclRepl(), role="EDAI")

    result = await agent.run("list all cells")
    result = agent.run_sync("list all cells")
"""

from edai.agent.agent import Agent
from edai.agent.config import AgentConfig

__all__ = ["Agent", "AgentConfig"]

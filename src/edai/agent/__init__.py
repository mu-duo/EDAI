"""Agent / LLM integration layer.

Quick start::

    from edai.agent import LangGraphAgent, AgentConfig

    config = AgentConfig.from_json("agent_config.json")
    agent = LangGraphAgent(config, engine=my_engine)

    result = await agent.run("place the design")
    result = agent.run_sync("place the design")

The legacy mock ``Agent`` (keyword matcher) is available at
``edai.agent.agent.Agent``.  Both use :class:`~edai.core.Message.Message`
as the canonical message type.
"""

from edai.agent.agent import Agent
from edai.agent.config import AgentConfig
from edai.agent.graph import LangGraphAgent

__all__ = ["Agent", "AgentConfig", "LangGraphAgent"]

"""Agent / LLM integration layer.

Quick start::

    from edai.agent import LangGraphAgent, AgentConfig

    config = AgentConfig.from_json("agent_config.json")
    agent = LangGraphAgent(config, engine=my_engine)

    result = await agent.run("place the design")
    result = agent.run_sync("place the design")

The legacy ``Agent`` (mock keyword matcher) remains available at
``edai.agent.agent.Agent``.
"""

from edai.agent.config import AgentConfig
from edai.agent.graph import LangGraphAgent

__all__ = ["AgentConfig", "LangGraphAgent"]

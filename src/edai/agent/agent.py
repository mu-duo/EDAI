import os
import rich


from langchain_deepseek import ChatDeepSeek
from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.store.memory import InMemoryStore


class Agent:
    def __init__(self, model_name: str = "", api_key: str = ""):
        if not model_name:
            model_name = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
        if not api_key:
            api_key = os.environ.get("LLM_API_KEY", "")

        if not api_key:
            raise ValueError("LLM_API_KEY is not set in environment variables.")

        self.model = ChatDeepSeek(model=model_name, temperature=0.9, api_key=api_key)  # type: ignore
        self.memory_store = InMemoryStore()
        self.agent = create_agent(model=self.model)

    def invoke(self, messages):
        response = self.agent.invoke({"messages": messages})
        return response

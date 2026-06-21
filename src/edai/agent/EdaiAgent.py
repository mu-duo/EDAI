"""EDAI-specific agent — extends BaseAgent with EDA role description."""

from __future__ import annotations

from .BaseAgent import BaseAgent


class EdaiAgent(BaseAgent):
    """EdaiAgent extends BaseAgent with EDA-specific methods.

    On construction it loads the role description from
    ``src/edai/roles/EDAI.md``, adding it as a system message.
    """

    def __init__(self, model_name: str = "", api_key: str = "") -> None:
        super().__init__(model_name, api_key)
        self.read_role_description("src/edai/roles/EDAI.md")

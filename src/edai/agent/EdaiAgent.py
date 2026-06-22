"""EDAI-specific agent — extends BaseAgent with EDA role description."""

from __future__ import annotations

import importlib.resources

from .BaseAgent import BaseAgent


class EdaiAgent(BaseAgent):
    """EdaiAgent extends BaseAgent with EDA-specific methods.

    On construction it loads the role description from
    ``edai.roles/EDAI.md`` via ``importlib.resources``,
    adding it as a system message.
    """

    def __init__(self, model_name: str = "", api_key: str = "") -> None:
        super().__init__(model_name, api_key)
        path = importlib.resources.files("edai.roles").joinpath("EDAI.md")
        self.read_role_description(str(path))

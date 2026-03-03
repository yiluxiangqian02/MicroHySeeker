"""Knowledge manager agent."""

from __future__ import annotations

from src.agents.base import BaseAgent


class KnowledgeManagerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="knowledge_mgr",
            system_prompt=(
                "You are the KnowledgeManager agent. Organize experiment insights, extract reusable "
                "knowledge, and provide traceable context for future runs."
            ),
        )


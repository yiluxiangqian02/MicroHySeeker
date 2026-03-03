"""Data analyst agent."""

from __future__ import annotations

from src.agents.base import BaseAgent


class DataAnalystAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="data_analyst",
            system_prompt=(
                "You are the DataAnalyst agent for electrochemical experiments. "
                "Focus on CV/EIS signal interpretation, uncertainty, and concise findings."
            ),
        )


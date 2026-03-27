"""DataAnalystAgent — lightweight wrapper for data-analysis tasks.

Converted from a full agent to a thin BaseAgent subclass so that
``src.skills.analyze_cv`` can still instantiate it.
"""

from __future__ import annotations

from src.agents.base import BaseAgent

_SYSTEM_PROMPT = (
    "You are a data analyst specializing in electrochemical experiments. "
    "Interpret CV, EIS, and LSV data; extract key metrics such as peak "
    "current, onset potential, Tafel slope, and charge-transfer resistance."
)


class DataAnalystAgent(BaseAgent):
    """Agent that analyses electrochemical experiment data."""

    def __init__(self) -> None:
        super().__init__(
            name="orchestrator",  # reuse orchestrator config (no dedicated section)
            system_prompt=_SYSTEM_PROMPT,
        )

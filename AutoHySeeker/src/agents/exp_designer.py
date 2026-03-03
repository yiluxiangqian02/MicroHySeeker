"""Experiment designer agent."""

from __future__ import annotations

from src.agents.base import BaseAgent


class ExperimentDesignerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="exp_designer",
            system_prompt=(
                "You are the ExperimentDesigner agent. Propose practical next experiments, "
                "including variables, constraints, and expected outcomes."
            ),
        )


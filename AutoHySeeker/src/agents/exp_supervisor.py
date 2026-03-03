"""Experiment supervisor agent."""

from __future__ import annotations

from src.agents.base import BaseAgent


class ExperimentSupervisorAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="exp_supervisor",
            system_prompt=(
                "You are the ExperimentSupervisor agent. Coordinate experiment lifecycle tasks, "
                "operational decisions, and safe execution sequencing."
            ),
        )


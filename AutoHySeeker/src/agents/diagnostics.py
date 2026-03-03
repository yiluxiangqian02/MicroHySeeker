"""Diagnostics expert agent."""

from __future__ import annotations

from src.agents.base import BaseAgent


class DiagnosticsExpertAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(
            name="diagnostics",
            system_prompt=(
                "You are the DiagnosticsExpert agent. Identify failure modes, instrument anomalies, "
                "and actionable troubleshooting steps."
            ),
        )


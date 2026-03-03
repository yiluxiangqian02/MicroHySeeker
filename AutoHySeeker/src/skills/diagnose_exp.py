"""Skill: diagnose experiment status using tools + LLM."""

from __future__ import annotations

from typing import Any

from src.agents.diagnostics import DiagnosticsExpertAgent
from src.tools.echem_reader import read_experiment_dir


async def diagnose_experiment_skill(run_dir: str) -> dict[str, Any]:
    details = read_experiment_dir(run_dir)

    agent = DiagnosticsExpertAgent()
    diagnosis = await agent.invoke(
        task={
            "intent": "diagnose_experiment",
            "run_dir": run_dir,
            "file_counts": details["counts"],
        },
        context={"metadata": details["metadata"]},
    )
    return {
        "run_dir": run_dir,
        "counts": details["counts"],
        "diagnosis": diagnosis,
    }


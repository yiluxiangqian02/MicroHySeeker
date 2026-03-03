"""Skill: analyze CV data using tools + LLM."""

from __future__ import annotations

from typing import Any

from src.agents.data_analyst import DataAnalystAgent
from src.tools.echem_reader import read_cv_csv, read_experiment_dir


def _cv_summary(df: Any) -> dict[str, float]:
    return {
        "rows": int(len(df)),
        "potential_min": float(df["Potential(V)"].min()),
        "potential_max": float(df["Potential(V)"].max()),
        "current_min": float(df["Current(A)"].min()),
        "current_max": float(df["Current(A)"].max()),
    }


async def analyze_cv_skill(run_dir: str, cv_file: str | None = None) -> dict[str, Any]:
    details = read_experiment_dir(run_dir)
    cv_files = details["files"]["cv"]
    selected = cv_file or (cv_files[0] if cv_files else None)
    if not selected:
        raise ValueError(f"no CV file found in run_dir: {run_dir}")

    df = read_cv_csv(selected)
    summary = _cv_summary(df)

    agent = DataAnalystAgent()
    analysis = await agent.invoke(
        task={
            "intent": "analyze_cv",
            "run_dir": run_dir,
            "cv_file": selected,
            "summary": summary,
        },
        context={"experiment": details["metadata"]},
    )
    return {
        "run_dir": run_dir,
        "cv_file": selected,
        "summary": summary,
        "analysis": analysis,
    }


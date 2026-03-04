"""Smart scheduler skill for multi-experiment optimization."""

from __future__ import annotations

from typing import Any

from src.skills.base import BaseSkill, SkillResult


class SmartSchedulerSkill(BaseSkill):
    """Optimize execution order for multiple experiments."""

    name = "smart_scheduler"
    description = "Schedule multiple experiments considering dependencies, time, and resources"
    required_tools = []

    # Experiment type priorities (higher = more urgent)
    _TYPE_PRIORITIES = {
        "calibration": 100,
        "baseline": 90,
        "screening": 80,
        "optimization": 70,
        "validation": 60,
        "characterization": 50,
    }

    # Estimated durations by experiment type (minutes)
    _TYPE_DURATIONS = {
        "calibration": 10,
        "baseline": 15,
        "screening": 20,
        "optimization": 30,
        "validation": 25,
        "characterization": 40,
    }

    async def execute(
        self, experiments: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> SkillResult:
        """Schedule experiments with optimization.

        Args:
            experiments: List of experiment dicts with keys:
                - id: str
                - type: str (calibration, baseline, screening, etc.)
                - priority: int (optional, overrides type priority)
                - estimated_duration_min: float (optional)
                - depends_on: list[str] (optional, IDs of prerequisite experiments)
                - equipment: list[str] (optional, required equipment)
            **kwargs: Additional options

        Returns:
            SkillResult with optimized schedule
      """
        if not experiments:
            return SkillResult(
                success=False,
                data={},
                message="experiments parameter is required",
                artifacts=[],
            )

        # Build dependency graph
        dep_graph: dict[str, list[str]] = {}
        for exp in experiments:
            exp_id = exp.get("id", "")
            depends_on = exp.get("depends_on", [])
            dep_graph[exp_id] = depends_on

        # Topological sort with priority
        scheduled: list[dict[str, Any]] = []
        remaining = {exp["id"]: exp for exp in experiments}
        completed: set[str] = set()

        while remaining:
            # Find experiments with satisfied dependencies
            ready = []
            for exp_id, exp in remaining.items():
                deps = dep_graph.get(exp_id, [])
                if all(d in completed for d in deps):
                    ready.append(exp)

            if not ready:
                # Circular dependency detected
                return SkillResult(
                    success=False,
                    data={"remaining": list(remaining.keys())},
                    message="Circular dependency detected in experiments",
                    artifacts=[],
                )

            # Sort ready experiments by priority
            ready.sort(
                key=lambda e: (
                    -(e.get("priority") or self._TYPE_PRIORITIES.get(e.get("type", ""), 0)),
                    e.get("id", ""),
                ),
            )

            # Check equipment conflicts
            used_equipment: set[str] = set()
            batch: list[dict[str, Any]] = []

            for exp in ready:
                exp_equipment = set(exp.get("equipment", []))
                if not exp_equipment or not exp_equipment.intersection(used_equipment):
                    batch.append(exp)
                    used_equipment.update(exp_equipment)
                    completed.add(exp["id"])
                    del remaining[exp["id"]]

            # Add batch to schedule
            for exp in batch:
                duration = exp.get(
                    "estimated_duration_min",
                    self._TYPE_DURATIONS.get(exp.get("type", ""), 30),
                )
                scheduled.append(
                    {
                        "id": exp["id"],
                        "type": exp.get("type", "unknown"),
                        "priority": exp.get("priority")
                        or self._TYPE_PRIORITIES.get(exp.get("type", ""), 0),
                        "estimated_duration_min": duration,
                        "depends_on": dep_graph.get(exp["id"], []),
                        "equipment": exp.get("equipment", []),
                        "batch": len(scheduled) // len(batch) if batch else 0,
                    }
                )

        # Calculate total time
        total_duration = sum(e["estimated_duration_min"] for e in scheduled)

        schedule_data = {
            "scheduled_experiments": scheduled,
            "total_experiments": len(scheduled),
            "total_duration_min": total_duration,
            "total_duration_hours": total_duration / 60,
            "batches": max((e["batch"] for e in scheduled), default=0) + 1,
        }

        return SkillResult(
            success=True,
            data=schedule_data,
            message=f"Scheduled {len(scheduled)} experiments in {schedule_data['batches']} batches",
            artifacts=[],
        )

    def get_schema(self) -> dict:
        """Return JSON Schema for this skill's inputs."""
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "experiments": {
                    "type": "array",
                    "description": "List of experiments to schedule",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string"},
                            "priority": {"type": "integer"},
                            "estimated_duration_min": {"type": "number"},
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "equipment": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["id"],
                    },
                }
            },
            "required": ["experiments"],
        }

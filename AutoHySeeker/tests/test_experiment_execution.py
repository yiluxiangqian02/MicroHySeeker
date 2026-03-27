"""Tests for experiment_execution skills: SmartSchedulerSkill and ExecutionMonitorSkill."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


# ── SmartSchedulerSkill ────────────────────────────────────────────────────────

class TestSmartSchedulerSkill:
    def test_import(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill, smart_scheduler_skill
        assert isinstance(smart_scheduler_skill, SmartSchedulerSkill)

    def test_no_experiments_returns_failure(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        result = run_async(skill.execute(experiments=None))
        assert result.success is False
        assert "experiments" in result.message.lower()

    def test_empty_list_returns_failure(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        result = run_async(skill.execute(experiments=[]))
        assert result.success is False

    def test_single_experiment(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        experiments = [{"id": "exp1", "type": "calibration"}]
        result = run_async(skill.execute(experiments=experiments))
        assert result.success is True
        assert result.data["total_experiments"] == 1

    def test_multiple_experiments_ordered_by_priority(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        experiments = [
            {"id": "exp_opt", "type": "optimization"},
            {"id": "exp_cal", "type": "calibration"},
            {"id": "exp_val", "type": "validation"},
        ]
        result = run_async(skill.execute(experiments=experiments))
        assert result.success is True
        scheduled = result.data["scheduled_experiments"]
        # calibration (priority 100) should come before optimization (70)
        ids = [e["id"] for e in scheduled]
        assert ids.index("exp_cal") < ids.index("exp_opt")

    def test_dependency_ordering(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        experiments = [
            {"id": "exp2", "type": "validation", "depends_on": ["exp1"]},
            {"id": "exp1", "type": "baseline"},
        ]
        result = run_async(skill.execute(experiments=experiments))
        assert result.success is True
        scheduled = result.data["scheduled_experiments"]
        ids = [e["id"] for e in scheduled]
        assert ids.index("exp1") < ids.index("exp2")

    def test_circular_dependency_detected(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        experiments = [
            {"id": "a", "depends_on": ["b"]},
            {"id": "b", "depends_on": ["a"]},
        ]
        result = run_async(skill.execute(experiments=experiments))
        assert result.success is False
        assert "circular" in result.message.lower()

    def test_equipment_conflict_batching(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        experiments = [
            {"id": "exp1", "type": "screening", "equipment": ["potentiostat"]},
            {"id": "exp2", "type": "screening", "equipment": ["potentiostat"]},
        ]
        result = run_async(skill.execute(experiments=experiments))
        assert result.success is True
        # Both scheduled despite conflict (different batches)
        assert result.data["total_experiments"] == 2

    def test_custom_priority_overrides_type(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        experiments = [
            {"id": "low_type", "type": "calibration", "priority": 5},
            {"id": "high_custom", "type": "characterization", "priority": 200},
        ]
        result = run_async(skill.execute(experiments=experiments))
        assert result.success is True
        scheduled = result.data["scheduled_experiments"]
        ids = [e["id"] for e in scheduled]
        assert ids.index("high_custom") < ids.index("low_type")

    def test_total_duration_calculated(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        experiments = [
            {"id": "e1", "type": "calibration", "estimated_duration_min": 10},
            {"id": "e2", "type": "baseline", "estimated_duration_min": 20},
        ]
        result = run_async(skill.execute(experiments=experiments))
        assert result.success is True
        assert result.data["total_duration_min"] == 30

    def test_get_schema_returns_dict(self) -> None:
        from src.skills.experiment_execution import SmartSchedulerSkill
        skill = SmartSchedulerSkill()
        schema = skill.get_schema()
        assert isinstance(schema, dict)
        assert "experiments" in schema["properties"]


# ── ExecutionMonitorSkill ──────────────────────────────────────────────────────

def _write_run_dir(
    path: Path,
    *,
    success: bool = True,
    steps: list[dict] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    write_log: bool = False,
) -> Path:
    """Write a minimal run directory suitable for ExecutionMonitorSkill."""
    summary = {
        "run_id": "run_test",
        "success": success,
        "elapsed_seconds": 42.0,
        "steps": steps or [],
        "errors": errors or [],
        "warnings": warnings or [],
    }
    (path / "run_summary.json").write_text(json.dumps(summary))
    if write_log:
        (path / "run_log.log").write_text(
            "[2024-01-01 00:00:00.000] [INFO] [test] experiment started\n"
        )
    return path


class TestExecutionMonitorSkill:
    def test_import(self) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill, execution_monitor_skill
        assert isinstance(execution_monitor_skill, ExecutionMonitorSkill)

    def test_missing_run_dir_returns_failure(self) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill
        skill = ExecutionMonitorSkill()
        result = run_async(skill.execute(run_dir=""))
        assert result.success is False
        assert "run_dir" in result.message.lower()

    def test_nonexistent_run_dir_returns_failure(self) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill
        skill = ExecutionMonitorSkill()
        result = run_async(skill.execute(run_dir="/nonexistent/path/xyz"))
        assert result.success is False

    def test_successful_run_basic(self, tmp_path: Path) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill
        steps = [
            {"id": "s1", "success": True, "type": "init"},
            {"id": "s2", "success": True, "type": "measure"},
        ]
        _write_run_dir(tmp_path, success=True, steps=steps)
        skill = ExecutionMonitorSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert result.data["success_rate"] == pytest.approx(1.0)
        assert result.data["total_steps"] == 2

    def test_failed_run_low_success_rate(self, tmp_path: Path) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill
        steps = [
            {"id": "s1", "success": False, "type": "init"},
            {"id": "s2", "success": False, "type": "measure"},
            {"id": "s3", "success": False, "type": "cleanup"},
        ]
        _write_run_dir(tmp_path, success=False, steps=steps)
        skill = ExecutionMonitorSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True  # skill itself succeeds
        assert result.data["success_rate"] < 0.5
        # Should have a critical diagnostic
        sev = [d["severity"] for d in result.data["diagnostics"]]
        assert "critical" in sev

    def test_moderate_failure_generates_warning(self, tmp_path: Path) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill
        steps = [
            {"id": "s1", "success": True, "type": "init"},
            {"id": "s2", "success": False, "type": "measure"},
            {"id": "s3", "success": True, "type": "cleanup"},
        ]
        _write_run_dir(tmp_path, success=False, steps=steps)
        skill = ExecutionMonitorSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        sev = [d["severity"] for d in result.data["diagnostics"]]
        assert "warning" in sev or "critical" in sev

    def test_report_artifact_created(self, tmp_path: Path) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill
        _write_run_dir(tmp_path, success=True)
        skill = ExecutionMonitorSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True
        assert len(result.artifacts) > 0
        report_path = Path(result.artifacts[0])
        assert report_path.exists()

    def test_with_run_log(self, tmp_path: Path) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill
        _write_run_dir(tmp_path, success=True, write_log=True)
        skill = ExecutionMonitorSkill()
        result = run_async(skill.execute(run_dir=str(tmp_path)))
        assert result.success is True

    def test_get_schema_returns_dict(self) -> None:
        from src.skills.experiment_execution import ExecutionMonitorSkill
        skill = ExecutionMonitorSkill()
        schema = skill.get_schema()
        assert isinstance(schema, dict)
        assert "run_dir" in schema["properties"]

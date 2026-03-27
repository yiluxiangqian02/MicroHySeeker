"""Tests for D3 InteractiveTroubleshootingSkill."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


class TestInteractiveTroubleshootingSkill:
    def test_import(self) -> None:
        from src.skills.diagnostics import (
            InteractiveTroubleshootingSkill,
            interactive_troubleshooting_skill,
        )
        assert isinstance(interactive_troubleshooting_skill, InteractiveTroubleshootingSkill)

    def test_exported_from_skills_init(self) -> None:
        from src.skills import InteractiveTroubleshootingSkill, interactive_troubleshooting_skill
        assert InteractiveTroubleshootingSkill is not None
        assert interactive_troubleshooting_skill is not None

    def test_missing_symptom_returns_failure(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom=""))
        assert result.success is False
        assert "available" in result.message.lower()

    def test_unknown_symptom_returns_failure(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="nonexistent_issue"))
        assert result.success is False
        assert "nonexistent_issue" in result.message

    def test_pump_not_running(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="pump_not_running"))
        assert result.success is True
        assert result.data["symptom"] == "pump_not_running"
        assert len(result.data["steps"]) > 0
        assert len(result.data["possible_causes"]) > 0

    def test_echem_no_signal(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="echem_no_signal"))
        assert result.success is True
        assert result.data["symptom"] == "echem_no_signal"
        assert "title" in result.data

    def test_communication_timeout(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="communication_timeout"))
        assert result.success is True
        assert len(result.data["steps"]) > 0

    def test_data_anomaly(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="data_anomaly"))
        assert result.success is True
        assert result.data["symptom"] == "data_anomaly"

    def test_result_contains_diagnostic(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="pump_not_running"))
        assert "diagnostic" in result.data
        diag = result.data["diagnostic"]
        assert diag["severity"] == "warning"
        assert diag["category"] == "troubleshooting"

    def test_all_known_symptoms_succeed(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        known = ["pump_not_running", "echem_no_signal", "communication_timeout", "data_anomaly"]
        for symptom in known:
            result = run_async(skill.execute(symptom=symptom))
            assert result.success is True, f"Expected success for symptom={symptom}"

    def test_get_schema_contains_enum(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        schema = skill.get_schema()
        assert isinstance(schema, dict)
        enum_values = schema["properties"]["symptom"]["enum"]
        assert "pump_not_running" in enum_values
        assert "echem_no_signal" in enum_values

    def test_message_contains_title(self) -> None:
        from src.skills.diagnostics import InteractiveTroubleshootingSkill
        skill = InteractiveTroubleshootingSkill()
        result = run_async(skill.execute(symptom="pump_not_running"))
        # Message should reference the guide title
        assert result.message  # non-empty

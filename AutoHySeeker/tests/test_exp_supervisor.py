"""Unit tests for ExperimentSupervisorAgent.monitor_experiment().

All external I/O (RealtimeMonitorSkill, LLM chat_completion) is mocked so that
the tests run without a live MicroHySeeker service or an LLM API.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from src.skills.base import SkillResult


# ── Helpers ────────────────────────────────────────────────────────────────────

def run_async(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_skill_result(
    *,
    anomalies: list[dict[str, Any]] | None = None,
    state: str = "completed",
    poll_count: int = 3,
    elapsed: float = 6.0,
    has_error: bool = False,
    is_running: bool = False,
) -> SkillResult:
    """Build a realistic SkillResult matching RealtimeMonitorSkill output."""
    _anomalies = anomalies if anomalies is not None else []
    critical = sum(1 for a in _anomalies if a.get("severity") == "critical")
    return SkillResult(
        success=critical == 0,
        data={
            "status": {
                "state": state,
                "is_running": is_running,
                "has_error": has_error,
            },
            "anomalies": _anomalies,
            "suggestions": ["No anomalies detected; experiment completed normally."],
            "poll_count": poll_count,
            "elapsed_seconds": elapsed,
        },
        message=f"Monitoring complete: state={state}, {len(_anomalies)} anomaly(ies) detected",
        artifacts=[],
    )


def _make_mock_skill(skill_result: SkillResult) -> MagicMock:
    """Return a mock RealtimeMonitorSkill instance whose execute() returns *skill_result*."""
    mock = MagicMock()
    mock.execute = AsyncMock(return_value=skill_result)
    return mock


# ── Import & construction ──────────────────────────────────────────────────────

class TestExperimentSupervisorAgentInit:
    def test_import(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        assert ExperimentSupervisorAgent is not None

    def test_name(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        assert agent.name == "exp_supervisor"

    def test_system_prompt_mentions_coordinator(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        lp = agent.system_prompt.lower()
        assert "coordinat" in lp or "supervis" in lp or "lifecycle" in lp

    def test_is_monitoring_initially_false(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        assert agent.is_monitoring is False

    def test_stop_monitoring_noop_when_not_running(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        agent.stop_monitoring()  # must not raise


# ── _has_anomalies_above_threshold ─────────────────────────────────────────────

class TestHasAnomaliesAboveThreshold:
    def test_empty_returns_false(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        assert _has_anomalies_above_threshold([], "critical") is False

    def test_critical_meets_critical_threshold(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        assert _has_anomalies_above_threshold(
            [{"severity": "critical"}], "critical"
        ) is True

    def test_warning_below_critical_threshold(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        assert _has_anomalies_above_threshold(
            [{"severity": "warning"}], "critical"
        ) is False

    def test_error_below_critical_threshold(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        assert _has_anomalies_above_threshold(
            [{"severity": "error"}], "critical"
        ) is False

    def test_warning_at_warning_threshold(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        assert _has_anomalies_above_threshold(
            [{"severity": "warning"}], "warning"
        ) is True

    def test_error_at_error_threshold(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        assert _has_anomalies_above_threshold(
            [{"severity": "error"}], "error"
        ) is True

    def test_unknown_severity_excluded(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        assert _has_anomalies_above_threshold(
            [{"severity": "unknown"}], "warning"
        ) is False

    def test_mixed_only_critical_qualifies(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        anomalies = [
            {"severity": "warning"},
            {"severity": "critical"},
        ]
        assert _has_anomalies_above_threshold(anomalies, "critical") is True

    def test_missing_severity_key_excluded(self) -> None:
        from src.agents.exp_supervisor import _has_anomalies_above_threshold
        assert _has_anomalies_above_threshold([{}], "warning") is False


# ── monitor_experiment: result structure ──────────────────────────────────────

class TestMonitorExperimentResultStructure:
    def test_returns_expected_keys(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        skill_result = _make_skill_result()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(skill_result),
        ), patch(
            "src.agents.base.chat_completion", new=AsyncMock(return_value="ok")
        ):
            result = run_async(agent.monitor_experiment(exp_id="exp_001"))

        assert set(result.keys()) >= {
            "exp_id", "monitor", "stopped_manually", "diagnostics", "analysis", "optimization"
        }

    def test_exp_id_echoed(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        skill_result = _make_skill_result()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(skill_result),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            result = run_async(agent.monitor_experiment(exp_id="my_exp"))

        assert result["exp_id"] == "my_exp"

    def test_monitor_data_populated(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        skill_result = _make_skill_result(poll_count=5, elapsed=10.0)
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(skill_result),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            result = run_async(agent.monitor_experiment(exp_id="e1"))

        assert result["monitor"]["poll_count"] == 5
        assert result["monitor"]["elapsed_seconds"] == 10.0

    def test_stopped_manually_false_on_normal_run(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result()),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            result = run_async(agent.monitor_experiment(exp_id="e"))

        assert result["stopped_manually"] is False


# ── monitor_experiment: anomaly dispatch ──────────────────────────────────────

class TestMonitorExperimentAnomalyDispatch:
    def test_no_anomalies_no_diagnostics(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(anomalies=[])),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            result = run_async(agent.monitor_experiment(exp_id="clean"))

        assert result["diagnostics"] is None

    def test_critical_anomaly_triggers_diagnostics(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        anomalies = [
            {"type": "pump_fault", "severity": "critical", "message": "pump broken", "detail": ""}
        ]
        skill_result = _make_skill_result(anomalies=anomalies, state="failed")
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(skill_result),
        ), patch(
            "src.agents.base.chat_completion", new=AsyncMock(return_value="check pump")
        ):
            result = run_async(agent.monitor_experiment(exp_id="pump_exp"))

        assert result["diagnostics"] is not None
        assert result["diagnostics"]["content"] == "check pump"
        assert result["diagnostics"]["agent"] == "diagnostics"

    def test_warning_below_critical_threshold_no_diagnostics(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        anomalies = [
            {"type": "stall", "severity": "warning", "message": "slow step", "detail": ""}
        ]
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(anomalies=anomalies, state="completed")),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            result = run_async(
                agent.monitor_experiment(exp_id="warn_exp", anomaly_threshold="critical")
            )

        assert result["diagnostics"] is None

    def test_warning_at_warning_threshold_triggers_diagnostics(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        anomalies = [
            {"type": "stall", "severity": "warning", "message": "slow step", "detail": ""}
        ]
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(anomalies=anomalies, state="completed")),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="review logs")):
            result = run_async(
                agent.monitor_experiment(exp_id="warn_exp2", anomaly_threshold="warning")
            )

        assert result["diagnostics"] is not None

    def test_diagnostics_task_contains_anomalies(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        anomalies = [
            {"type": "pump_fault", "severity": "critical", "message": "broken", "detail": "x"}
        ]
        captured_task: list[dict[str, Any]] = []

        async def fake_cc(messages: Any, **kwargs: Any) -> str:
            # Extract what was sent to the LLM from the last user message
            import json
            payload = json.loads(messages[-1]["content"])
            captured_task.append(payload["task"])
            return "diag result"

        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(anomalies=anomalies, state="failed")),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(side_effect=fake_cc)):
            run_async(agent.monitor_experiment(exp_id="e_check"))

        assert len(captured_task) == 1
        assert captured_task[0]["type"] == "diagnose_anomalies"
        assert captured_task[0]["anomalies"] == anomalies


# ── monitor_experiment: completion dispatch ────────────────────────────────────

class TestMonitorExperimentCompletionDispatch:
    def test_completed_state_triggers_analysis(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(state="completed", anomalies=[])),
        ), patch(
            "src.agents.base.chat_completion", new=AsyncMock(return_value="analysis report")
        ):
            result = run_async(agent.monitor_experiment(exp_id="done_exp", run_dir="/tmp/run"))

        assert result["analysis"] is not None
        assert result["analysis"]["content"] == "analysis report"
        assert result["analysis"]["agent"] == "data_analyst"

    def test_idle_state_triggers_analysis(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(state="idle", anomalies=[])),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="idle analysis")):
            result = run_async(agent.monitor_experiment(exp_id="idle_exp"))

        assert result["analysis"] is not None

    def test_failed_state_no_analysis(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(state="failed", anomalies=[])),
        ):
            result = run_async(agent.monitor_experiment(exp_id="fail_exp"))

        assert result["analysis"] is None

    def test_completed_with_error_no_analysis(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(
                _make_skill_result(state="completed", has_error=True, anomalies=[])
            ),
        ):
            result = run_async(agent.monitor_experiment(exp_id="err_exp"))

        assert result["analysis"] is None

    def test_analysis_task_contains_run_dir(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        captured: list[dict[str, Any]] = []

        async def fake_cc(messages: Any, **kwargs: Any) -> str:
            import json
            payload = json.loads(messages[-1]["content"])
            captured.append(payload["task"])
            return "done"

        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(state="completed", anomalies=[])),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(side_effect=fake_cc)):
            run_async(agent.monitor_experiment(exp_id="e", run_dir="/data/run42"))

        assert len(captured) == 1
        assert captured[0]["run_dir"] == "/data/run42"
        assert captured[0]["type"] == "analyze_completed_experiment"


# ── monitor_experiment: optimisation ──────────────────────────────────────────

class TestMonitorExperimentOptimisation:
    def test_request_optimization_false_no_designer(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result()),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            result = run_async(
                agent.monitor_experiment(exp_id="e", request_optimization=False)
            )

        assert result["optimization"] is None

    def test_request_optimization_true_invokes_designer(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result()),
        ), patch(
            "src.agents.base.chat_completion", new=AsyncMock(return_value="next exp plan")
        ):
            result = run_async(
                agent.monitor_experiment(
                    exp_id="opt_exp",
                    request_optimization=True,
                    optimization_goal="maximize HER",
                )
            )

        assert result["optimization"] is not None
        assert result["optimization"]["content"] == "next exp plan"
        assert result["optimization"]["agent"] == "exp_designer"

    def test_optimization_task_contains_goal(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        captured: list[dict[str, Any]] = []

        async def fake_cc(messages: Any, **kwargs: Any) -> str:
            import json
            payload = json.loads(messages[-1]["content"])
            captured.append(payload["task"])
            return "plan"

        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(anomalies=[])),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(side_effect=fake_cc)):
            run_async(
                agent.monitor_experiment(
                    exp_id="g",
                    request_optimization=True,
                    optimization_goal="find best catalyst",
                )
            )

        # analysis (completed) + optimization = 2 calls; optimization is last
        opt_tasks = [t for t in captured if t.get("type") == "suggest_next_experiment"]
        assert len(opt_tasks) == 1
        assert opt_tasks[0]["goal"] == "find best catalyst"


# ── manual stop ────────────────────────────────────────────────────────────────

class TestStopMonitoring:
    def test_stop_before_start_is_noop(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        agent.stop_monitoring()
        assert agent.is_monitoring is False

    def test_stop_monitoring_cancels_task(self) -> None:
        """stop_monitoring() causes monitor_experiment to return early with stopped_manually=True."""
        from src.agents.exp_supervisor import ExperimentSupervisorAgent

        async def run() -> None:
            agent = ExperimentSupervisorAgent()
            started = asyncio.Event()

            async def slow_execute(*args: Any, **kwargs: Any) -> SkillResult:
                started.set()
                await asyncio.sleep(60)  # simulate long-running monitoring
                return _make_skill_result()

            mock_skill = MagicMock()
            mock_skill.execute = AsyncMock(side_effect=slow_execute)

            with patch("src.agents.exp_supervisor.RealtimeMonitorSkill", return_value=mock_skill):
                monitor_task = asyncio.create_task(
                    agent.monitor_experiment(exp_id="exp_stop")
                )
                await started.wait()  # wait until monitoring has started
                agent.stop_monitoring()
                result = await monitor_task

            assert result["stopped_manually"] is True

        run_async(run())

    def test_is_monitoring_true_while_running(self) -> None:
        """is_monitoring reflects the running state of the task."""
        from src.agents.exp_supervisor import ExperimentSupervisorAgent

        async def run() -> None:
            agent = ExperimentSupervisorAgent()
            started = asyncio.Event()

            async def slow_execute(*args: Any, **kwargs: Any) -> SkillResult:
                started.set()
                await asyncio.sleep(60)
                return _make_skill_result()

            mock_skill = MagicMock()
            mock_skill.execute = AsyncMock(side_effect=slow_execute)

            with patch("src.agents.exp_supervisor.RealtimeMonitorSkill", return_value=mock_skill):
                task = asyncio.create_task(agent.monitor_experiment(exp_id="e"))
                await started.wait()
                assert agent.is_monitoring is True
                agent.stop_monitoring()
                await task

            assert agent.is_monitoring is False

        run_async(run())

    def test_is_monitoring_false_after_normal_completion(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result()),
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            run_async(agent.monitor_experiment(exp_id="e"))

        assert agent.is_monitoring is False


# ── error handling ─────────────────────────────────────────────────────────────

class TestMonitorExperimentErrorHandling:
    def test_diagnostics_llm_error_returns_error_dict(self) -> None:
        """LLM failure in DiagnosticsExpertAgent yields error dict, not raised exception."""
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        anomalies = [
            {"type": "pump_fault", "severity": "critical", "message": "bad pump", "detail": ""}
        ]
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(anomalies=anomalies, state="failed")),
        ), patch(
            "src.agents.base.chat_completion",
            new=AsyncMock(side_effect=RuntimeError("LLM offline")),
        ):
            result = run_async(agent.monitor_experiment(exp_id="err1"))

        assert result["diagnostics"] is not None
        assert "error" in result["diagnostics"]
        assert result["diagnostics"]["agent"] == "diagnostics"

    def test_analysis_llm_error_returns_error_dict(self) -> None:
        """LLM failure in DataAnalystAgent yields error dict, not raised exception."""
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(state="completed", anomalies=[])),
        ), patch(
            "src.agents.base.chat_completion",
            new=AsyncMock(side_effect=RuntimeError("LLM offline")),
        ):
            result = run_async(agent.monitor_experiment(exp_id="err2", run_dir="/tmp"))

        assert result["analysis"] is not None
        assert "error" in result["analysis"]
        assert result["analysis"]["agent"] == "data_analyst"

    def test_optimization_llm_error_returns_error_dict(self) -> None:
        """LLM failure in ExperimentDesignerAgent yields error dict, not raised exception."""
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill",
            return_value=_make_mock_skill(_make_skill_result(state="failed", anomalies=[])),
        ), patch(
            "src.agents.base.chat_completion",
            new=AsyncMock(side_effect=RuntimeError("LLM offline")),
        ):
            result = run_async(
                agent.monitor_experiment(exp_id="err3", request_optimization=True)
            )

        assert result["optimization"] is not None
        assert "error" in result["optimization"]
        assert result["optimization"]["agent"] == "exp_designer"


# ── skill is called with correct parameters ────────────────────────────────────

class TestSkillParameterForwarding:
    def test_poll_interval_forwarded(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        mock_skill = _make_mock_skill(_make_skill_result())
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill", return_value=mock_skill
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            run_async(agent.monitor_experiment(exp_id="e", poll_interval=5.0))

        mock_skill.execute.assert_called_once()
        call_kwargs = mock_skill.execute.call_args[1]
        assert call_kwargs["poll_interval"] == 5.0

    def test_max_duration_forwarded(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        mock_skill = _make_mock_skill(_make_skill_result())
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill", return_value=mock_skill
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            run_async(agent.monitor_experiment(exp_id="e", max_duration=120.0))

        call_kwargs = mock_skill.execute.call_args[1]
        assert call_kwargs["max_duration"] == 120.0

    def test_exp_id_forwarded_to_skill(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        mock_skill = _make_mock_skill(_make_skill_result())
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill", return_value=mock_skill
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            run_async(agent.monitor_experiment(exp_id="test_id_42"))

        call_kwargs = mock_skill.execute.call_args[1]
        assert call_kwargs["exp_id"] == "test_id_42"

    def test_default_poll_interval_is_two_seconds(self) -> None:
        from src.agents.exp_supervisor import ExperimentSupervisorAgent
        agent = ExperimentSupervisorAgent()
        mock_skill = _make_mock_skill(_make_skill_result())
        with patch(
            "src.agents.exp_supervisor.RealtimeMonitorSkill", return_value=mock_skill
        ), patch("src.agents.base.chat_completion", new=AsyncMock(return_value="ok")):
            run_async(agent.monitor_experiment(exp_id="e"))

        call_kwargs = mock_skill.execute.call_args[1]
        assert call_kwargs["poll_interval"] == 2.0

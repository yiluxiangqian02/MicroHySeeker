"""Tests for /api/optimization routes."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

_TEST_LOOP: asyncio.AbstractEventLoop | None = None


def run_async(coro):
    global _TEST_LOOP
    if _TEST_LOOP is None or _TEST_LOOP.is_closed():
        _TEST_LOOP = asyncio.new_event_loop()
    return _TEST_LOOP.run_until_complete(coro)


@pytest.fixture(autouse=True)
def reset_optimization_state() -> None:
    import src.api.routes.optimization as optimization_routes
    global _TEST_LOOP

    optimization_routes._loop_instance = None
    optimization_routes._loop_task = None
    optimization_routes._last_state = {}
    optimization_routes._start_time = None
    optimization_routes._config = {}
    yield
    optimization_routes._loop_instance = None
    optimization_routes._loop_task = None
    optimization_routes._last_state = {}
    optimization_routes._start_time = None
    optimization_routes._config = {}
    if _TEST_LOOP is not None and not _TEST_LOOP.is_closed():
        _TEST_LOOP.close()
    _TEST_LOOP = None


class TestOptimizationAPI:
    def test_start_and_status_snapshot(self) -> None:
        import src.api.routes.optimization as optimization_routes

        fake_result = {
            "status": "completed",
            "total_rounds": 2,
            "best_result": {"round": 2, "metrics": {"overpotential_mV": 180}},
            "experiment_history": [{"round": 1}, {"round": 2}],
            "history_count": 2,
            "final_decision": "stop",
        }

        with patch("src.run_optimization.run_optimization", new=AsyncMock(return_value=fake_result)):
            response = run_async(
                optimization_routes.start_optimization(
                    optimization_routes.OptimizationStartRequest(goal="test", dry_run=True),
                )
            )
            assert response["status"] == "started"
            run_async(optimization_routes._loop_task)
            data = run_async(optimization_routes.get_optimization_status())

        assert data["status"] == "completed"
        assert data["current_round"] == 2
        assert data["best_result"]["metrics"]["overpotential_mV"] == 180

    def test_stop_requests_running_loop(self) -> None:
        import src.api.routes.optimization as optimization_routes

        async def fake_run_optimization(**kwargs):
            progress_callback = kwargs.get("progress_callback")
            should_stop = kwargs.get("should_stop")
            if progress_callback:
                progress_callback(
                    {
                        "status": "running",
                        "current_round": 1,
                        "experiment_history": [],
                        "optimization": {
                            "goal": "test",
                            "target_metric": "overpotential_mV",
                            "max_rounds": 3,
                        },
                    }
                )
            for _ in range(20):
                if should_stop and should_stop():
                    return {
                        "status": "stopped",
                        "total_rounds": 1,
                        "best_result": None,
                        "experiment_history": [],
                        "history_count": 0,
                        "final_decision": "stopped",
                    }
                await asyncio.sleep(0.01)
            return {
                "status": "completed",
                "total_rounds": 1,
                "best_result": None,
                "experiment_history": [],
                "history_count": 0,
                "final_decision": "stop",
            }

        with patch("src.run_optimization.run_optimization", new=fake_run_optimization):
            start = run_async(
                optimization_routes.start_optimization(
                    optimization_routes.OptimizationStartRequest(goal="test", dry_run=True),
                )
            )
            assert start["status"] == "started"
            run_async(asyncio.sleep(0.03))
            stop = run_async(optimization_routes.stop_optimization())
            assert stop["status"] == "stop_requested"
            run_async(optimization_routes._loop_task)
            status = run_async(optimization_routes.get_optimization_status())

        assert status["status"] in {"stopped", "stopping"}

    def test_reset_clears_state(self) -> None:
        import src.api.routes.optimization as optimization_routes

        with patch(
            "src.run_optimization.run_optimization",
            new=AsyncMock(
                return_value={
                    "status": "completed",
                    "total_rounds": 0,
                    "best_result": None,
                    "experiment_history": [],
                    "history_count": 0,
                    "final_decision": "stop",
                }
            ),
        ):
            run_async(
                optimization_routes.start_optimization(
                    optimization_routes.OptimizationStartRequest(goal="test", dry_run=True),
                )
            )
            run_async(optimization_routes._loop_task)

        reset = run_async(optimization_routes.reset_optimization())
        assert reset["status"] == "reset"

        data = run_async(optimization_routes.get_optimization_status())
        assert data["status"] == "idle"
        assert data["current_round"] == 0

    def test_status_exposes_pending_approval_when_paused(self) -> None:
        import src.api.routes.optimization as optimization_routes

        async def fake_run_optimization(**kwargs):
            progress_callback = kwargs.get("progress_callback")
            should_stop = kwargs.get("should_stop")
            if progress_callback:
                progress_callback(
                    {
                        "status": "paused",
                        "current_round": 1,
                        "experiment_history": [{"round": 1}],
                        "optimization": {
                            "goal": "test",
                            "target_metric": "overpotential_mV",
                            "max_rounds": 3,
                        },
                        "pending_approval": {"approval_id": "approval_123"},
                        "pause_reason": "initial_round_confirmation",
                        "latest_decision": {"action": "pause_for_human"},
                    }
                )
            for _ in range(20):
                if should_stop and should_stop():
                    return {
                        "status": "stopped",
                        "total_rounds": 1,
                        "best_result": None,
                        "experiment_history": [{"round": 1}],
                        "history_count": 1,
                        "final_decision": "stopped",
                    }
                await asyncio.sleep(0.01)
            return {
                "status": "paused",
                "total_rounds": 1,
                "best_result": None,
                "experiment_history": [{"round": 1}],
                "history_count": 1,
                "final_decision": "pause_for_human",
            }

        with patch("src.run_optimization.run_optimization", new=fake_run_optimization):
            run_async(
                optimization_routes.start_optimization(
                    optimization_routes.OptimizationStartRequest(goal="test", dry_run=True),
                )
            )
            run_async(asyncio.sleep(0.03))
            status = run_async(optimization_routes.get_optimization_status())
            stop = run_async(optimization_routes.stop_optimization())
            run_async(optimization_routes._loop_task)

        assert status["running"] is True
        assert status["status"] == "paused"
        assert status["pending_approval"]["approval_id"] == "approval_123"
        assert status["pause_reason"] == "initial_round_confirmation"
        assert stop["status"] == "stop_requested"

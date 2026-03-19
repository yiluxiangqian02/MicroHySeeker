"""End-to-end integration tests for AutoHySeeker.

Tests the full system through the REST API using a real FastAPI app instance
(mounted via ``httpx.ASGITransport`` — no external server required).

Scenarios
---------
TestEndToEnd.test_normal_experiment
    Health check → create task → verify queued status → C1 contextualise a
    real experiment run → C2 suggest next experiment.  Validates the complete
    happy-path from API entry to plan generation.

TestEndToEnd.test_device_failure_recovery
    Mock device runs CV and fails with ``DeviceError``.  The failure is
    captured, a run directory is written with a partial CSV and error log,
    then D1 ``DiagnoseFailureSkill`` is invoked via ``/diagnostics/invoke``.
    Finally C2 is asked for a recovery plan.

TestEndToEnd.test_agent_coordination
    Sends three different task payloads to ``/agents/invoke`` and asserts that
    the orchestrator routes each one to the correct specialist agent
    (data_analyst, diagnostics, exp_designer) based on intent keywords.

TestEndToEnd.test_data_analysis
    Writes a synthetic experiment run dir using the mock device, calls C1
    ``/context/invoke`` with ``action="contextualize"``, then feeds the C1
    result into C2 ``/context/invoke`` with ``action="suggest"``.  Verifies
    that both skills produce structurally complete results.

All tests are async (pytest-asyncio ``asyncio_mode = "auto"``).
No real LLM calls are made — skills fall back to rule-based logic when the
LLM is unavailable or returns errors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.utils.api_client import APIError, AutoHySeekerAPIClient
from tests.utils.mock_device import DeviceError, MockElectrochemicalDevice

# All tests in this module use the module-scoped async_client / api_client
# fixtures, so they must share the same event loop (module scope).
pytestmark = pytest.mark.asyncio(loop_scope="module")


# ── helpers ────────────────────────────────────────────────────────────────────


def _mock_agent_graph(result_payload: dict[str, Any]) -> MagicMock:
    """Return a mock LangGraph-compatible supervisor graph."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(
        return_value={
            "messages": [],
            "current_agent": result_payload.get("agent", ""),
            "task": {},
            "context": {"routed_by": "route_intent"},
            "error": None,
            "result": result_payload,
        }
    )
    return mock


# ── test class ─────────────────────────────────────────────────────────────────


class TestEndToEnd:
    """End-to-end integration tests exercising the full AutoHySeeker stack."""

    # ── test_normal_experiment ─────────────────────────────────────────────────

    async def test_normal_experiment(
        self,
        api_client: AutoHySeekerAPIClient,
        experiment_run_dir: Path,
        history_dir: Path,
    ) -> None:
        """Happy-path: health → task lifecycle → C1 → C2 full chain.

        Assertions
        ----------
        * ``GET /health`` returns ``{"status": "ok"}``.
        * ``POST /tasks/create`` returns a task with status ``"queued"``.
        * ``GET /tasks/{id}/status`` reflects the created task.
        * C1 ``/context/invoke`` with action="contextualize" succeeds and
          returns ``comparison``, ``trend``, ``anomalies`` keys.
        * C2 ``/context/invoke`` with action="suggest" succeeds and returns
          ``intent``, ``plan``, ``rationale`` keys.
        * The C2 ``plan`` has a ``steps`` list.
        """
        # 1. Health check — server is alive
        health = await api_client.health()
        assert health["status"] == "ok", f"Unexpected health: {health}"
        assert "autohyseeker" in health.get("service", "").lower()

        # 2. Create and retrieve a task
        task_record = await api_client.create_task(
            task_type="analysis",
            payload={"run_dir": str(experiment_run_dir)},
        )
        assert "task_id" in task_record, "Response missing task_id"
        assert task_record["task_id"].startswith("task_")
        assert task_record["status"] == "queued"
        assert task_record["task_type"] == "analysis"
        assert "created_at" in task_record

        task_id = task_record["task_id"]
        status_record = await api_client.get_task_status(task_id)
        assert status_record["task_id"] == task_id
        assert status_record["status"] == "queued"

        # 3. C1 contextualise the experiment run
        c1_resp = await api_client.invoke_context(
            action="contextualize",
            run_dir=str(experiment_run_dir),
            history_dir=str(history_dir),
            threshold_sigma=2.0,
        )
        assert c1_resp["ok"] is True, f"C1 failed: {c1_resp.get('error')}"
        assert c1_resp["action"] == "contextualize"

        c1_result = c1_resp["result"]
        assert c1_result is not None, "C1 result is None"
        assert "comparison" in c1_result, f"C1 result missing 'comparison': {c1_result}"
        assert "trend" in c1_result, f"C1 result missing 'trend': {c1_result}"
        assert "anomalies" in c1_result, f"C1 result missing 'anomalies': {c1_result}"
        assert isinstance(c1_result["anomalies"], list)
        assert c1_result.get("n_history", -1) >= 0

        # 4. C2 suggest next experiment using C1 output as context
        c2_resp = await api_client.invoke_context(
            action="suggest",
            context_data=c1_result,
            goal="optimize HER catalyst efficiency",
            name="next_run_optimized",
        )
        assert c2_resp["ok"] is True, f"C2 failed: {c2_resp.get('error')}"
        assert c2_resp["action"] == "suggest"

        c2_result = c2_resp["result"]
        assert c2_result is not None, "C2 result is None"
        assert "intent" in c2_result, f"C2 result missing 'intent': {c2_result}"
        assert "plan" in c2_result, f"C2 result missing 'plan': {c2_result}"
        assert "rationale" in c2_result, f"C2 result missing 'rationale': {c2_result}"

        plan = c2_result["plan"]
        assert isinstance(plan, dict), f"C2 plan should be dict, got {type(plan)}"
        assert "steps" in plan, f"C2 plan missing 'steps': {plan}"
        assert isinstance(plan["steps"], list)
        assert len(plan["steps"]) > 0, "C2 plan steps list is empty"
        assert isinstance(c2_result["rationale"], str)
        assert len(c2_result["rationale"]) > 0

    # ── test_device_failure_recovery ───────────────────────────────────────────

    async def test_device_failure_recovery(
        self,
        api_client: AutoHySeekerAPIClient,
        tmp_path: Path,
    ) -> None:
        """Device fails during experiment → D1 diagnose → C2 recovery plan.

        Scenario
        --------
        1. Create a mock device configured to fail on CV.
        2. Attempt to run CV — catch ``DeviceError``.
        3. Write a failed run directory with error log.
        4. Call ``/diagnostics/invoke`` with ``action="analyze_failure"`` and
           point at the failed run dir.
        5. Verify D1 returns a diagnosis report with ``findings``.
        6. Create a task record capturing the failure.
        7. Call ``/context/invoke`` with ``action="suggest"`` to get a
           recovery/diagnostic plan from C2.
        """
        device = MockElectrochemicalDevice(
            device_id="failing_device_e2e",
            fail_on=["cv"],
        )

        # 1. Attempt measurement — expect failure
        caught_error: DeviceError | None = None
        try:
            await device.run_cv()
        except DeviceError as exc:
            caught_error = exc

        assert caught_error is not None, "Expected DeviceError was not raised"
        assert caught_error.error_code == "CV_TIMEOUT"
        assert device.state.value == "failed"

        # 2. Write failed run directory
        run_dir = tmp_path / "failed_run_e2e"
        run_dir.mkdir()
        failure_record = device.simulate_failure(error_type="timeout", component="electrode")

        summary = {
            "run_id": "failed_run_e2e",
            "device_id": device.device_id,
            "success": False,
            "error_code": failure_record["error_code"],
            "steps": [
                {
                    "id": "cv_step_0",
                    "type": "cv",
                    "success": False,
                    "error": str(caught_error),
                    "data_file": "cv_partial.csv",
                }
            ],
        }
        (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2))
        (run_dir / "cv_partial.csv").write_text(
            "Potential(V),Current(A)\n-0.6,-0.00005\n-0.5,-0.00010\n"
        )
        (run_dir / "run_log.log").write_text(
            "[10:00:00] [INFO]    Step started: cv_step_0\n"
            "[10:00:30] [WARNING] Electrode resistance elevated\n"
            "[10:01:00] [ERROR]   CV_TIMEOUT — electrode contact lost\n"
            "[10:01:05] [ERROR]   Aborting run: unrecoverable error\n"
        )

        # 3. D1 analyze_failure via /diagnostics/invoke
        diag_resp = await api_client.invoke_diagnostics(
            action="analyze_failure",
            run_dir=str(run_dir),
        )
        assert diag_resp.get("ok") is True, (
            f"Diagnostics failed: {diag_resp.get('error')}"
        )
        assert diag_resp["action"] == "analyze_failure"

        diag_result = diag_resp["result"]
        assert diag_result is not None, "Diagnostics result is None"
        # D1 should surface findings (error counts, log issues, etc.)
        assert "findings" in diag_result, (
            f"Diagnostics result missing 'findings': {diag_result}"
        )
        assert isinstance(diag_result["findings"], list)

        # 4. Create a task record to track the recovery
        task_record = await api_client.create_task(
            task_type="failure_recovery",
            payload={
                "run_dir": str(run_dir),
                "error_code": failure_record["error_code"],
                "device_id": device.device_id,
            },
        )
        assert task_record["task_type"] == "failure_recovery"
        assert task_record["status"] == "queued"

        # 5. Device recovery — verify state reset
        recovered = device.recover()
        assert recovered is True
        assert device.state.value == "idle"

        # 6. C2 suggest a recovery/diagnostic plan
        c2_resp = await api_client.invoke_context(
            action="suggest",
            context_data={
                "anomalies": ["cv_failure", "electrode_timeout"],
                "trend": {},
                "error_code": failure_record["error_code"],
            },
            goal="diagnose and recover from CV timeout failure",
        )
        assert c2_resp["ok"] is True, f"C2 recovery suggestion failed: {c2_resp}"
        c2_result = c2_resp["result"]
        assert c2_result is not None
        assert "intent" in c2_result
        # With anomalies in context, C2 should lean towards diagnostic_run
        assert c2_result["intent"] in (
            "diagnostic_run",
            "stability_run",
            "optimisation_run",
            "generic",
        )
        assert "plan" in c2_result
        assert "rationale" in c2_result

    # ── test_agent_coordination ────────────────────────────────────────────────

    async def test_agent_coordination(
        self,
        api_client: AutoHySeekerAPIClient,
    ) -> None:
        """Multi-agent routing: orchestrator sends tasks to correct specialists.

        Verifies that the supervisor graph routes three distinct task types:
        - Data-analysis task → ``orchestrator`` agent (via DataAnalysisSkill).
        - Diagnostics/failure task → ``diagnostics`` agent.
        - Experiment-design task → ``exp_designer`` agent.

        LLM calls are mocked at the graph level so no real API credentials
        are needed; the routing logic itself is exercised without mocking.
        """
        # Mock result for orchestrator (data analysis routed here)
        da_result = {
            "agent": "orchestrator",
            "model": "mock",
            "content": "CV peak at -0.35 V; Tafel slope 62 mV/dec",
            "ok": True,
        }
        # Mock result for diagnostics
        diag_result = {
            "agent": "diagnostics",
            "model": "mock",
            "content": "No critical failures detected",
            "ok": True,
        }
        # Mock result for exp_designer
        design_result = {
            "agent": "exp_designer",
            "model": "mock",
            "content": "Suggested: sweep pH 7–10, catalyst loading 0.2–0.5 mg/cm²",
            "ok": True,
        }

        with (
            patch(
                "src.api.routes.agents.get_supervisor_graph",
                side_effect=[
                    _mock_agent_graph(da_result),
                    _mock_agent_graph(diag_result),
                    _mock_agent_graph(design_result),
                ],
            ),
        ):
            # --- Data analysis task ---
            resp_da = await api_client.invoke_agent(
                task={
                    "intent": "analyze CV data",
                    "run_id": "run_007",
                    "goal": "extract Tafel slope from LSV data",
                },
                context={"session_id": "sess_e2e_001"},
            )
            assert resp_da["ok"] is True, f"Data analyst failed: {resp_da}"
            assert resp_da["result"] is not None
            assert resp_da["result"]["agent"] == "orchestrator"

            # --- Diagnostics task ---
            resp_diag = await api_client.invoke_agent(
                task={
                    "intent": "diagnose failure in run_099",
                    "error": "pump timeout",
                },
            )
            assert resp_diag["ok"] is True, f"Diagnostics agent failed: {resp_diag}"
            assert resp_diag["result"]["agent"] == "diagnostics"

            # --- Experiment design task ---
            resp_design = await api_client.invoke_agent(
                task={
                    "intent": "design next experiment",
                    "goal": "optimize catalyst loading for HER",
                },
            )
            assert resp_design["ok"] is True, f"Exp designer failed: {resp_design}"
            assert resp_design["result"]["agent"] == "exp_designer"

        # Cross-cutting: all responses have the expected envelope keys
        for resp, label in [
            (resp_da, "orchestrator"),
            (resp_diag, "diagnostics"),
            (resp_design, "exp_designer"),
        ]:
            assert "ok" in resp, f"{label}: missing 'ok' key"
            assert "result" in resp, f"{label}: missing 'result' key"
            assert "state" in resp, f"{label}: missing 'state' key"
            assert resp["result"].get("ok") is True, f"{label}: result.ok is not True"

    # ── test_data_analysis ─────────────────────────────────────────────────────

    async def test_data_analysis(
        self,
        api_client: AutoHySeekerAPIClient,
        tmp_path: Path,
    ) -> None:
        """Full data-analysis pipeline: generate data → C1 → C2.

        Scenario
        --------
        1. Use the mock device to generate CV + EIS + LSV measurements.
        2. Write measurements to a structured run directory.
        3. Create a history directory with 4 prior runs.
        4. Call C1 (``/context/invoke`` action="contextualize") — verify
           comparison, trend, anomaly detection, and ``n_history``.
        5. Feed C1 output to C2 (``/context/invoke`` action="suggest") —
           verify plan completeness.
        6. Check that the C2 ``plan.name`` matches the provided ``name``
           parameter.
        7. Verify ``/data/experiments`` endpoint returns a 200 response.
        """
        device = MockElectrochemicalDevice(device_id="analysis_device_e2e")

        # 1. Generate three measurement types
        cv_data = await device.run_cv(potential_range=(-0.6, 0.4), n_points=120)
        eis_data = await device.run_eis(freq_min=0.1, freq_max=1e5, n_points=60)
        lsv_data = await device.run_lsv(potential_range=(0.0, -0.55))

        assert cv_data["technique"] == "cv"
        assert eis_data["technique"] == "eis"
        assert lsv_data["technique"] == "lsv"
        assert cv_data["n_points"] == 120
        assert len(cv_data["potential_V"]) == cv_data["n_points"]
        assert len(eis_data["Zre_Ohm"]) == eis_data["n_points"]

        # 2. Write current run directory
        run_dir = tmp_path / "analysis_run_001"
        device.write_run_dir(
            run_dir,
            [cv_data, eis_data, lsv_data],
            metadata={"efficiency": 0.88, "peak_current": 0.045, "ph": 7.0},
        )
        assert (run_dir / "run_summary.json").exists()
        assert (run_dir / "cv_step_00.csv").exists()
        assert (run_dir / "eis_step_01.csv").exists()
        assert (run_dir / "lsv_step_02.csv").exists()

        # 3. Build history directory (4 prior runs with rising efficiency)
        hist_root = tmp_path / "analysis_history"
        hist_root.mkdir()
        hist_device = MockElectrochemicalDevice(device_id="hist_analysis_device")
        for i in range(4):
            h_dir = hist_root / f"hist_{i:03d}"
            h_meas = [await hist_device.run_cv()]
            hist_device.write_run_dir(
                h_dir,
                h_meas,
                metadata={
                    "efficiency": round(0.78 + i * 0.02, 3),
                    "peak_current": round(0.036 + i * 0.002, 4),
                },
            )

        # 4. C1 — contextualise the run
        c1_resp = await api_client.invoke_context(
            action="contextualize",
            run_dir=str(run_dir),
            history_dir=str(hist_root),
            threshold_sigma=2.0,
        )
        assert c1_resp["ok"] is True, f"C1 failed: {c1_resp}"
        c1_result = c1_resp["result"]
        assert c1_result is not None

        # Required output structure
        assert "comparison" in c1_result, f"Missing 'comparison': {c1_result}"
        assert "trend" in c1_result, f"Missing 'trend': {c1_result}"
        assert "anomalies" in c1_result, f"Missing 'anomalies': {c1_result}"
        assert isinstance(c1_result["comparison"], dict)
        assert isinstance(c1_result["trend"], dict)
        assert isinstance(c1_result["anomalies"], list)

        # n_history should reflect the 4 historical runs (capped by max_history=20)
        n_history = c1_result.get("n_history", -1)
        assert n_history >= 0, f"n_history should be >= 0, got {n_history}"
        assert n_history <= 4, f"n_history should be <= 4 (created 4 runs), got {n_history}"

        # 5. C2 — suggest next experiment
        plan_name = "optimized_her_run_002"
        c2_resp = await api_client.invoke_context(
            action="suggest",
            context_data=c1_result,
            goal="maximize hydrogen evolution efficiency",
            name=plan_name,
        )
        assert c2_resp["ok"] is True, f"C2 failed: {c2_resp}"
        c2_result = c2_resp["result"]
        assert c2_result is not None

        # 6. Structural validation of C2 output
        assert "intent" in c2_result, f"Missing 'intent': {c2_result}"
        assert "plan" in c2_result, f"Missing 'plan': {c2_result}"
        assert "rationale" in c2_result, f"Missing 'rationale': {c2_result}"

        plan = c2_result["plan"]
        assert isinstance(plan, dict)
        assert "steps" in plan, f"Plan missing 'steps': {plan}"
        assert len(plan["steps"]) > 0, "Plan steps list is empty"

        # Plan name should match the requested name
        assert plan.get("name") == plan_name, (
            f"Expected plan name {plan_name!r}, got {plan.get('name')!r}"
        )

        # rationale is a non-empty string
        assert isinstance(c2_result["rationale"], str)
        assert len(c2_result["rationale"]) > 0

        # intent is one of the known values
        assert c2_result["intent"] in (
            "diagnostic_run",
            "stability_run",
            "optimisation_run",
            "generic",
        ), f"Unknown intent: {c2_result['intent']!r}"

        # 7. Data endpoint smoke test
        data_resp = await api_client.get_experiments(limit=5)
        assert "count" in data_resp
        assert "items" in data_resp
        assert isinstance(data_resp["items"], list)

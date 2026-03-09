"""Integration test fixtures for AutoHySeeker end-to-end tests.

Provides:
- ``async_client``: httpx.AsyncClient mounted on the FastAPI app via
  ASGITransport (equivalent to starting/stopping a real API server but
  fully in-process — no ports, no subprocesses).
- ``api_client``: typed ``AutoHySeekerAPIClient`` wrapping ``async_client``.
- ``mock_device`` / ``failing_device``: mock electrochemical workstations.
- ``experiment_run_dir``: a fully populated run directory produced by the
  mock device, ready for C1/D1 skill inputs.
- ``history_dir``: a parent directory containing 3 historical run directories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

import pytest
import pytest_asyncio

from tests.utils.api_client import AutoHySeekerAPIClient
from tests.utils.mock_device import MockElectrochemicalDevice

if TYPE_CHECKING:
    import httpx


# ── API lifecycle fixtures ─────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def async_client() -> AsyncGenerator["httpx.AsyncClient", None]:
    """Start the AutoHySeeker API and yield an async HTTP client.

    Uses ``httpx.ASGITransport`` to mount the FastAPI app in-process.
    This is functionally equivalent to starting a real server (all
    middleware, routers, and lifespan hooks run) but without network
    overhead or port conflicts.

    Startup is verified with a ``GET /health`` call; teardown happens
    automatically when the ``AsyncClient`` context manager exits.
    """
    import httpx
    from httpx import ASGITransport

    from src.api.main import app

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200, (
            f"API startup health-check failed (status={resp.status_code}): {resp.text}"
        )
        yield client
    # AsyncClient.__aexit__ tears down the transport — server "stopped"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def api_client(async_client: "httpx.AsyncClient") -> AutoHySeekerAPIClient:
    """Return a typed :class:`AutoHySeekerAPIClient` backed by ``async_client``."""
    return AutoHySeekerAPIClient(async_client, timeout=30.0)


# ── mock device fixtures ───────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def mock_device() -> MockElectrochemicalDevice:
    """A healthy mock electrochemical device (no injected failures)."""
    return MockElectrochemicalDevice(device_id="test_device_001")


@pytest.fixture(scope="module")
def failing_device() -> MockElectrochemicalDevice:
    """A mock device pre-configured to fail on CV measurements."""
    return MockElectrochemicalDevice(
        device_id="failing_device_001",
        fail_on=["cv"],
    )


# ── data directory fixtures ────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def experiment_run_dir(
    tmp_path: Path, mock_device: MockElectrochemicalDevice
) -> Path:
    """Create a complete experiment run directory using the mock device.

    Runs CV + EIS measurements and writes results plus a ``run_summary.json``
    that includes ``efficiency`` and ``peak_current`` metrics suitable for
    C1 anomaly detection.
    """
    run_dir = tmp_path / "exp_run_001"
    measurements = [
        await mock_device.run_cv(),
        await mock_device.run_eis(),
    ]
    mock_device.write_run_dir(
        run_dir,
        measurements,
        metadata={
            "efficiency": 0.85,
            "peak_current": 0.042,
            "exp_name": "HER_NiFe_integration_test",
        },
    )
    return run_dir


@pytest_asyncio.fixture()
async def history_dir(tmp_path: Path) -> Path:
    """Create a history directory containing 3 prior experiment run dirs.

    Each historical run has slightly increasing ``efficiency`` and
    ``peak_current`` metrics to produce detectable trends in C1.
    """
    hist_root = tmp_path / "history"
    hist_root.mkdir()
    device = MockElectrochemicalDevice(device_id="hist_device")
    for i in range(3):
        run_dir = hist_root / f"hist_run_{i:03d}"
        measurements = [await device.run_cv()]
        device.write_run_dir(
            run_dir,
            measurements,
            metadata={
                "efficiency": round(0.80 + i * 0.02, 3),
                "peak_current": round(0.038 + i * 0.002, 4),
            },
        )
    return hist_root


@pytest_asyncio.fixture()
async def failed_run_dir(tmp_path: Path) -> Path:
    """Create a run directory that represents a failed experiment.

    Writes a ``run_summary.json`` with ``success=False``, a partial data
    CSV, and a ``run_log.log`` containing WARNING/ERROR entries so that
    D1 ``DiagnoseFailureSkill`` can surface findings.
    """
    run_dir = tmp_path / "failed_run_001"
    run_dir.mkdir()

    summary = {
        "run_id": "failed_run_001",
        "device_id": "test_device_001",
        "success": False,
        "steps": [
            {
                "id": "cv_step_0",
                "type": "cv",
                "success": False,
                "data_file": "cv_step_00.csv",
                "n_points": 0,
                "error": "CV_TIMEOUT — electrode contact lost",
            }
        ],
        "error_code": "CV_TIMEOUT",
    }
    (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2))

    # Partial CSV (incomplete data)
    (run_dir / "cv_step_00.csv").write_text(
        "Potential(V),Current(A)\n"
        "-0.6,-0.00005\n-0.5,-0.00010\n-0.4,-0.00020\n"
    )

    # Log with errors
    log_lines = (
        "[2024-01-15 10:00:00] [INFO]    [experiment_ctrl] Step started: cv_step_0\n"
        "[2024-01-15 10:00:30] [WARNING] [pump_controller] pump pressure elevated\n"
        "[2024-01-15 10:01:00] [ERROR]   [pump_controller] pump timeout error\n"
        "[2024-01-15 10:01:05] [ERROR]   [experiment_ctrl] CV_TIMEOUT: aborting run\n"
    )
    (run_dir / "run_log.log").write_text(log_lines)

    return run_dir

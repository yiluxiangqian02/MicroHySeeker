"""Shared pytest fixtures for AutoHySeeker tests.

Provides common test data builders and tmp_path-based run directories
so individual test modules do not duplicate setup code.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


# ── DataFrame helpers ─────────────────────────────────────────────────────────

@pytest.fixture()
def cv_df() -> pd.DataFrame:
    """Synthetic cyclic voltammogram DataFrame."""
    n = 200
    t = np.linspace(0, 2 * np.pi, n)
    potential = np.sin(t)
    current = np.cos(t) * 1e-3
    return pd.DataFrame({"Potential(V)": potential, "Current(A)": current})


@pytest.fixture()
def lsv_df() -> pd.DataFrame:
    """Synthetic linear sweep voltammogram DataFrame (cathodic)."""
    potential = np.linspace(0, -0.6, 100)
    current = -np.abs(potential) * 0.01
    return pd.DataFrame({"Potential(V)": potential, "Current(A)": current})


@pytest.fixture()
def eis_df() -> pd.DataFrame:
    """Synthetic EIS Nyquist DataFrame."""
    freq = np.logspace(5, -1, 50)
    zre = 10 + 50 * np.exp(-((np.log10(freq) - 2) ** 2))
    zim = 40 * np.exp(-((np.log10(freq) - 2) ** 2))
    return pd.DataFrame({"Freq(Hz)": freq, "Zre(Ohm)": zre, "Zim(Ohm)": zim})


# ── File-based fixtures ───────────────────────────────────────────────────────

_CV_CSV_CONTENT = (
    "Potential(V),Current(A)\n"
    "-1.0,-0.00050\n-0.8,-0.00030\n-0.6,-0.00010\n"
    "-0.4,0.00010\n-0.2,0.00030\n0.0,0.00050\n"
    "0.2,0.00080\n0.4,0.00095\n0.6,0.00070\n"
    "0.8,0.00040\n1.0,0.00010\n0.8,-0.00020\n"
    "0.6,-0.00060\n0.4,-0.00090\n0.2,-0.00080\n"
    "0.0,-0.00060\n-0.2,-0.00040\n-0.4,-0.00020\n"
    "-0.6,-0.00010\n-0.8,-0.00005\n-1.0,-0.00050\n"
)

_LSV_CSV_CONTENT = (
    "Potential(V),Current(A)\n"
    "0.0,-0.00001\n-0.05,-0.00005\n-0.10,-0.00020\n"
    "-0.15,-0.00080\n-0.20,-0.00200\n-0.25,-0.00400\n"
    "-0.30,-0.00600\n-0.35,-0.00750\n-0.40,-0.00850\n"
    "-0.45,-0.00920\n-0.50,-0.00960\n-0.55,-0.00980\n"
    "-0.60,-0.01000\n"
)

_EIS_CSV_CONTENT = (
    "Freq(Hz),Zre(Ohm),Zim(Ohm)\n"
    "100000,10.05,0.50\n50000,10.20,1.20\n10000,11.50,5.00\n"
    "5000,14.00,10.00\n1000,30.00,35.00\n500,55.00,40.00\n"
    "100,80.00,25.00\n50,90.00,15.00\n10,98.00,6.00\n"
    "5,100.50,3.00\n1,101.00,1.00\n0.5,101.20,0.50\n0.1,101.30,0.20\n"
)

_RUN_SUMMARY = {
    "run_id": "test_run_001",
    "exp_name": "HER_NiFe_screening",
    "success": True,
    "elapsed_seconds": 312.5,
    "steps": [
        {
            "id": "cv_step_0",
            "type": "cv",
            "success": True,
            "details": "CV completed normally",
            "data_file": "cv_sample.csv",
            "duration_s": 120.0,
        },
        {
            "id": "eis_step_1",
            "type": "eis",
            "success": True,
            "details": "EIS completed normally",
            "data_file": "eis_sample.csv",
            "duration_s": 192.5,
        },
    ],
}

_RUN_LOG_CONTENT = (
    "[2024-01-15 10:00:00.000] [INFO] [experiment_ctrl] Step started: cv_step_0\n"
    "[2024-01-15 10:01:00.000] [INFO] [experiment_ctrl] Step finished: cv_step_0\n"
    "[2024-01-15 10:02:00.000] [INFO] [pump_controller] pump flow rate 2.5 mL/min\n"
    "[2024-01-15 10:05:00.000] [WARNING] [pump_controller] pump pressure slightly elevated\n"
    "[2024-01-15 10:06:00.000] [ERROR] [pump_controller] pump timeout error detected\n"
    "[2024-01-15 10:07:00.000] [INFO] [experiment_ctrl] Step started: eis_step_1\n"
    "[2024-01-15 10:10:00.000] [INFO] [experiment_ctrl] Step finished: eis_step_1\n"
)


@pytest.fixture()
def cv_csv_file(tmp_path: Path) -> Path:
    """Write a sample CV CSV to tmp_path and return its path."""
    p = tmp_path / "cv_sample.csv"
    p.write_text(_CV_CSV_CONTENT)
    return p


@pytest.fixture()
def lsv_csv_file(tmp_path: Path) -> Path:
    """Write a sample LSV CSV to tmp_path and return its path."""
    p = tmp_path / "lsv_sample.csv"
    p.write_text(_LSV_CSV_CONTENT)
    return p


@pytest.fixture()
def eis_csv_file(tmp_path: Path) -> Path:
    """Write a sample EIS CSV to tmp_path and return its path."""
    p = tmp_path / "eis_sample.csv"
    p.write_text(_EIS_CSV_CONTENT)
    return p


@pytest.fixture()
def mock_run_dir(tmp_path: Path) -> Path:
    """Create a mock run directory with CV/EIS CSVs, run_summary.json, and run_log.log."""
    run_dir = tmp_path / "test_run_001"
    run_dir.mkdir()

    (run_dir / "cv_sample.csv").write_text(_CV_CSV_CONTENT)
    (run_dir / "lsv_sample.csv").write_text(_LSV_CSV_CONTENT)
    (run_dir / "eis_sample.csv").write_text(_EIS_CSV_CONTENT)
    (run_dir / "run_summary.json").write_text(json.dumps(_RUN_SUMMARY))
    (run_dir / "run_log.log").write_text(_RUN_LOG_CONTENT)
    return run_dir

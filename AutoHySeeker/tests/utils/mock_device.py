"""Mock electrochemical device for AutoHySeeker integration tests.

Simulates an electrochemical workstation capable of running CV, EIS, and LSV
measurements. Supports configurable failure injection for failure-recovery tests.
"""

from __future__ import annotations

import asyncio
import csv
import json
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np


class DeviceState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    RECOVERING = "recovering"


class DeviceError(RuntimeError):
    """Raised when the mock device encounters a simulated hardware failure."""

    def __init__(self, message: str, error_code: str = "UNKNOWN") -> None:
        super().__init__(message)
        self.error_code = error_code


class MockElectrochemicalDevice:
    """Simulates an electrochemical measurement workstation.

    Args:
        device_id: Identifier string shown in generated run summaries.
        fail_on: Set of measurement types (``"cv"``, ``"eis"``, ``"lsv"``,
            ``"all"``) that should raise :class:`DeviceError`.
        latency_s: Optional artificial async delay per measurement (seconds).
    """

    def __init__(
        self,
        device_id: str = "mock_device_001",
        fail_on: list[str] | None = None,
        latency_s: float = 0.0,
    ) -> None:
        self.device_id = device_id
        self.fail_on: set[str] = set(fail_on or [])
        self.latency_s = latency_s
        self.state = DeviceState.IDLE
        self._run_count = 0
        self._last_error: str | None = None

    # ── measurement methods ────────────────────────────────────────────────────

    async def run_cv(
        self,
        potential_range: tuple[float, float] = (-0.6, 0.4),
        scan_rate: float = 0.05,
        n_points: int = 100,
    ) -> dict[str, Any]:
        """Run a cyclic voltammetry sweep.

        Returns a dict with ``technique``, ``potential_V``, ``current_A``,
        ``n_points``, and ``scan_rate_V_per_s``.

        Raises:
            DeviceError: if ``"cv"`` or ``"all"`` is in ``fail_on``.
        """
        if self.latency_s > 0:
            await asyncio.sleep(self.latency_s)
        if "cv" in self.fail_on or "all" in self.fail_on:
            self.state = DeviceState.FAILED
            self._last_error = "CV_TIMEOUT"
            raise DeviceError(
                "CV measurement timeout — electrode contact lost",
                error_code="CV_TIMEOUT",
            )

        self.state = DeviceState.RUNNING
        self._run_count += 1

        v_min, v_max = potential_range
        half = n_points // 2
        forward = np.linspace(v_min, v_max, half)
        reverse = np.linspace(v_max, v_min, half)
        potential = np.concatenate([forward, reverse])

        peak_v = (v_min + v_max) / 2
        current = (
            1e-3 * np.exp(-((potential - peak_v) ** 2) / 0.02)
            - 8e-4 * np.exp(-((potential - (peak_v - 0.1)) ** 2) / 0.02)
        )

        self.state = DeviceState.IDLE
        return {
            "technique": "cv",
            "scan_rate_V_per_s": scan_rate,
            "n_points": int(len(potential)),
            "potential_V": potential.tolist(),
            "current_A": current.tolist(),
        }

    async def run_eis(
        self,
        freq_min: float = 0.1,
        freq_max: float = 100_000.0,
        n_points: int = 50,
    ) -> dict[str, Any]:
        """Run electrochemical impedance spectroscopy (Randles-circuit model).

        Returns a dict with ``technique``, ``freq_Hz``, ``Zre_Ohm``,
        ``Zim_Ohm``, and ``n_points``.

        Raises:
            DeviceError: if ``"eis"`` or ``"all"`` is in ``fail_on``.
        """
        if self.latency_s > 0:
            await asyncio.sleep(self.latency_s)
        if "eis" in self.fail_on or "all" in self.fail_on:
            self.state = DeviceState.FAILED
            self._last_error = "EIS_OVERLOAD"
            raise DeviceError(
                "EIS potentiostat overload — current compliance exceeded",
                error_code="EIS_OVERLOAD",
            )

        self.state = DeviceState.RUNNING
        self._run_count += 1

        freq = np.logspace(np.log10(freq_min), np.log10(freq_max), n_points)
        # Simple Randles circuit: Rsol + Rct||(1/jωCdl)
        R_sol, R_ct, C_dl = 10.0, 100.0, 20e-6
        omega = 2 * np.pi * freq
        Z_dl = 1.0 / (1j * omega * C_dl)
        Z = R_sol + (R_ct * Z_dl) / (R_ct + Z_dl)

        self.state = DeviceState.IDLE
        return {
            "technique": "eis",
            "n_points": n_points,
            "freq_Hz": freq.tolist(),
            "Zre_Ohm": Z.real.tolist(),
            "Zim_Ohm": (-Z.imag).tolist(),  # convention: positive Zim axis
        }

    async def run_lsv(
        self,
        potential_range: tuple[float, float] = (0.0, -0.6),
        scan_rate: float = 0.01,
        n_points: int = 61,
    ) -> dict[str, Any]:
        """Run a linear sweep voltammetry scan (cathodic, Butler-Volmer model).

        Returns a dict with ``technique``, ``potential_V``, ``current_A``,
        ``n_points``, and ``scan_rate_V_per_s``.

        Raises:
            DeviceError: if ``"lsv"`` or ``"all"`` is in ``fail_on``.
        """
        if self.latency_s > 0:
            await asyncio.sleep(self.latency_s)
        if "lsv" in self.fail_on or "all" in self.fail_on:
            self.state = DeviceState.FAILED
            self._last_error = "LSV_TIMEOUT"
            raise DeviceError("LSV scan timeout", error_code="LSV_TIMEOUT")

        self.state = DeviceState.RUNNING
        self._run_count += 1

        v_start, v_end = potential_range
        potential = np.linspace(v_start, v_end, n_points)
        overpotential = potential - (-0.3)
        current = -0.01 / (1.0 + np.exp(20.0 * overpotential))

        self.state = DeviceState.IDLE
        return {
            "technique": "lsv",
            "scan_rate_V_per_s": scan_rate,
            "n_points": int(len(potential)),
            "potential_V": potential.tolist(),
            "current_A": current.tolist(),
        }

    # ── failure / recovery ─────────────────────────────────────────────────────

    def simulate_failure(
        self,
        error_type: str = "timeout",
        component: str = "pump",
    ) -> dict[str, Any]:
        """Force the device into a failed state.

        Returns:
            Failure record dict with ``device_id``, ``error_type``,
            ``component``, ``state``, and ``error_code``.
        """
        self.state = DeviceState.FAILED
        self._last_error = f"{component.upper()}_{error_type.upper()}"
        return {
            "device_id": self.device_id,
            "error_type": error_type,
            "component": component,
            "state": self.state.value,
            "error_code": self._last_error,
        }

    def recover(self) -> bool:
        """Attempt to reset the device from a failed state to idle.

        Returns:
            ``True`` if recovery succeeded, ``False`` if device was not failed.
        """
        if self.state == DeviceState.FAILED:
            self.state = DeviceState.RECOVERING
            self._last_error = None
            self.state = DeviceState.IDLE
            return True
        return False

    # ── data persistence ───────────────────────────────────────────────────────

    def write_run_dir(
        self,
        run_dir: str | Path,
        measurements: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Persist measurement results to a run directory.

        Creates CSV files for each measurement and a ``run_summary.json``
        compatible with C1/C2 skill inputs.

        Args:
            run_dir: Target directory path (created if absent).
            measurements: List of measurement dicts returned by run_* methods.
            metadata: Extra key-value pairs merged into ``run_summary.json``.

        Returns:
            Path to the created run directory.
        """
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        step_records: list[dict[str, Any]] = []
        for i, m in enumerate(measurements):
            technique = m.get("technique", "unknown")
            filename = f"{technique}_step_{i:02d}.csv"
            filepath = run_dir / filename

            if technique in ("cv", "lsv"):
                rows = list(zip(m["potential_V"], m["current_A"]))
                with open(filepath, "w", newline="") as fh:
                    w = csv.writer(fh)
                    w.writerow(["Potential(V)", "Current(A)"])
                    w.writerows(rows)
            elif technique == "eis":
                rows = list(zip(m["freq_Hz"], m["Zre_Ohm"], m["Zim_Ohm"]))
                with open(filepath, "w", newline="") as fh:
                    w = csv.writer(fh)
                    w.writerow(["Freq(Hz)", "Zre(Ohm)", "Zim(Ohm)"])
                    w.writerows(rows)

            step_records.append({
                "id": f"{technique}_step_{i}",
                "type": technique,
                "success": True,
                "data_file": filename,
                "n_points": m.get("n_points", 0),
            })

        summary: dict[str, Any] = {
            "run_id": run_dir.name,
            "device_id": self.device_id,
            "success": True,
            "steps": step_records,
            **(metadata or {}),
        }
        (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2))
        return run_dir

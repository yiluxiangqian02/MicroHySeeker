"""Extended tool-layer tests — echem_reader, file_watcher, log_analysis,
registry, report_generator, visualization."""

from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")

import pandas as pd
import pytest


# ── echem_reader ──────────────────────────────────────────────────────────────

class TestReadCvCsv:
    def test_reads_valid_csv(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_cv_csv

        f = tmp_path / "cv.csv"
        f.write_text("Potential(V),Current(A)\n0.1,0.001\n0.2,0.002\n")
        df = read_cv_csv(str(f))
        assert len(df) == 2
        assert "Potential(V)" in df.columns
        assert "Current(A)" in df.columns

    def test_alias_columns_normalised(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_cv_csv

        f = tmp_path / "cv_alias.csv"
        f.write_text("Ewe/V,I/A\n0.5,0.003\n")
        df = read_cv_csv(str(f))
        assert "Potential(V)" in df.columns
        assert "Current(A)" in df.columns

    def test_missing_file_raises(self) -> None:
        from src.tools.echem_reader import read_cv_csv

        with pytest.raises(FileNotFoundError):
            read_cv_csv("/nonexistent/cv.csv")

    def test_missing_columns_raises(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_cv_csv

        f = tmp_path / "bad.csv"
        f.write_text("A,B\n1,2\n")
        with pytest.raises(ValueError, match="missing required columns"):
            read_cv_csv(str(f))


class TestReadEisCsv:
    def test_reads_valid_csv(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_eis_csv

        f = tmp_path / "eis.csv"
        f.write_text("Freq(Hz),Zre(Ohm),Zim(Ohm)\n1000,10,5\n100,20,15\n")
        df = read_eis_csv(str(f))
        assert len(df) == 2

    def test_missing_file_raises(self) -> None:
        from src.tools.echem_reader import read_eis_csv

        with pytest.raises(FileNotFoundError):
            read_eis_csv("/nonexistent/eis.csv")


class TestReadExperimentDir:
    def test_valid_dir(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_experiment_dir

        (tmp_path / "cv_001.csv").write_text("Potential(V),Current(A)\n0,0\n")
        (tmp_path / "eis_001.csv").write_text("Freq,Zre,Zim\n1,2,3\n")
        (tmp_path / "experiment.json").write_text(json.dumps({"name": "test"}))
        result = read_experiment_dir(str(tmp_path))
        assert result["counts"]["csv"] == 2
        assert result["counts"]["cv"] == 1
        assert result["counts"]["eis"] == 1
        assert result["metadata"]["experiment"]["name"] == "test"

    def test_nonexistent_dir_raises(self) -> None:
        from src.tools.echem_reader import read_experiment_dir

        with pytest.raises(FileNotFoundError):
            read_experiment_dir("/nonexistent/run")

    def test_file_not_dir_raises(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_experiment_dir

        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(NotADirectoryError):
            read_experiment_dir(str(f))


class TestListRecentExperiments:
    def test_returns_empty_when_no_data_root(self) -> None:
        from src.tools.echem_reader import list_recent_experiments

        with patch("src.tools.echem_reader.DATA_ROOT", Path("/nonexistent")):
            assert list_recent_experiments() == []

    def test_returns_empty_for_zero(self) -> None:
        from src.tools.echem_reader import list_recent_experiments

        assert list_recent_experiments(n=0) == []

    def test_discovers_run_dirs(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import list_recent_experiments

        day = tmp_path / "2025-01-01"
        day.mkdir()
        run = day / "2025-01-01_10-00-00_run"
        run.mkdir()
        (run / "cv.csv").write_text("x")

        with patch("src.tools.echem_reader.DATA_ROOT", tmp_path):
            results = list_recent_experiments(n=5)
        assert len(results) == 1
        assert results[0]["csv_count"] == 1


# ── file_watcher ──────────────────────────────────────────────────────────────

class TestFileWatcher:
    def test_snapshot_run_dirs(self, tmp_path: Path) -> None:
        from src.tools.file_watcher import _snapshot_run_dirs

        day = tmp_path / "2025-01-01"
        day.mkdir()
        (day / "run_a").mkdir()
        (day / "run_b").mkdir()
        dirs = _snapshot_run_dirs(tmp_path)
        assert len(dirs) == 2

    def test_snapshot_empty(self) -> None:
        from src.tools.file_watcher import _snapshot_run_dirs

        assert _snapshot_run_dirs(Path("/nonexistent")) == set()

    def test_watch_yields_new_dirs(self, tmp_path: Path) -> None:
        from src.tools.file_watcher import watch_data_dir

        day = tmp_path / "2025-01-01"
        day.mkdir()
        (day / "run_a").mkdir()

        gen = watch_data_dir(
            data_root=str(tmp_path), poll_interval=0.01, max_polls=1
        )
        # Create a new dir after initial snapshot is taken by patching sleep
        (day / "run_b").mkdir()
        results = list(gen)
        assert any("run_b" in r for r in results)


# ── log_analysis ──────────────────────────────────────────────────────────────

_SAMPLE_LOG = textwrap.dedent("""\
    [2025-01-01 10:00:00.000] [INFO] [main] Step started: init
    [2025-01-01 10:00:01.500] [WARNING] [pump] Flow rate low
    [2025-01-01 10:00:02.000] [ERROR] [pump] pump timeout detected
    [2025-01-01 10:00:03.000] [INFO] [main] Step finished: init
""")


class TestParseRunLog:
    def test_parses_entries(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import parse_run_log

        f = tmp_path / "run_log.log"
        f.write_text(_SAMPLE_LOG, encoding="utf-8")
        entries = parse_run_log(str(f))
        assert len(entries) == 4
        assert entries[0].level == "INFO"
        assert entries[2].level == "ERROR"

    def test_empty_log(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import parse_run_log

        f = tmp_path / "empty.log"
        f.write_text("", encoding="utf-8")
        assert parse_run_log(str(f)) == []


class TestClassifyErrors:
    def test_groups_by_source(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import classify_errors, parse_run_log

        f = tmp_path / "run_log.log"
        f.write_text(_SAMPLE_LOG, encoding="utf-8")
        entries = parse_run_log(str(f))
        errors = classify_errors(entries)
        assert "pump" in errors
        assert len(errors["pump"]) == 1


class TestDetectPumpAnomalies:
    def test_detects_pump_timeout(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import detect_pump_anomalies, parse_run_log

        f = tmp_path / "run_log.log"
        f.write_text(_SAMPLE_LOG, encoding="utf-8")
        entries = parse_run_log(str(f))
        results = detect_pump_anomalies(entries)
        assert len(results) == 1
        assert results[0].category == "pump"

    def test_no_anomalies(self) -> None:
        from src.tools.log_analysis import detect_pump_anomalies

        assert detect_pump_anomalies([]) == []


class TestExtractStepTimeline:
    def test_extracts_start_and_end(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import extract_step_timeline, parse_run_log

        f = tmp_path / "run_log.log"
        f.write_text(_SAMPLE_LOG, encoding="utf-8")
        entries = parse_run_log(str(f))
        timeline = extract_step_timeline(entries)
        starts = [e for e in timeline if e["event"] == "start"]
        ends = [e for e in timeline if e["event"] == "end"]
        assert len(starts) >= 1
        assert len(ends) >= 1


class TestSummarizeRun:
    def test_summarize_with_log_and_json(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import summarize_run

        (tmp_path / "run_log.log").write_text(_SAMPLE_LOG, encoding="utf-8")
        (tmp_path / "run_summary.json").write_text(
            json.dumps({
                "run_id": "run_001",
                "exp_name": "test_exp",
                "success": True,
                "steps": [
                    {"id": "s0", "type": "cv", "success": True, "details": "ok"},
                ],
            }),
            encoding="utf-8",
        )
        summary = summarize_run(str(tmp_path))
        assert summary.run_id == "run_001"
        assert len(summary.step_results) == 1
        assert len(summary.errors) == 1  # 1 ERROR line

    def test_summarize_empty_dir(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import summarize_run

        summary = summarize_run(str(tmp_path))
        assert summary.errors == []
        assert summary.success is True


# ── registry ──────────────────────────────────────────────────────────────────

class TestToolRegistry:
    def test_register_and_get(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.register("echo", lambda x: x, "Echo tool")
        assert reg.get("echo")("hello") == "hello"

    def test_empty_name_raises(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        with pytest.raises(ValueError):
            reg.register("", lambda: None)

    def test_get_missing_raises(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_unregister(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.register("tmp", lambda: 1)
        reg.unregister("tmp")
        with pytest.raises(KeyError):
            reg.get("tmp")

    def test_list_tools(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.register("a", lambda: None, "Tool A")
        reg.register("b", lambda: None, "Tool B")
        tools = reg.list_tools()
        names = {t["name"] for t in tools}
        assert names == {"a", "b"}

    def test_invoke_sync_handler(self) -> None:
        import asyncio
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.register("add", lambda a, b: a + b)
        result = asyncio.run(reg.invoke("add", 2, 3))
        assert result == 5

    def test_invoke_async_handler(self) -> None:
        import asyncio
        from src.tools.registry import ToolRegistry

        async def async_fn(x: int) -> int:
            await asyncio.sleep(0)
            return x * 2

        reg = ToolRegistry()
        reg.register("double", async_fn)

        async def _run() -> int:
            return await reg.invoke("double", 5)

        assert asyncio.run(_run()) == 10


class TestBuildDefaultRegistry:
    def test_default_registry_has_expected_tools(self) -> None:
        from src.tools.registry import build_default_registry

        reg = build_default_registry()
        names = {t["name"] for t in reg.list_tools()}
        assert "read_cv_csv" in names
        assert "read_eis_csv" in names
        assert "watch_data_dir" in names


# ── report_generator ──────────────────────────────────────────────────────────

class TestGenerateRunReport:
    def test_generates_markdown(self, tmp_path: Path) -> None:
        from src.tools.report_generator import generate_run_report

        (tmp_path / "run_log.log").write_text(_SAMPLE_LOG, encoding="utf-8")
        (tmp_path / "run_summary.json").write_text(
            json.dumps({
                "run_id": "rpt_test",
                "exp_name": "report_exp",
                "success": True,
                "steps": [],
            }),
            encoding="utf-8",
        )
        out = tmp_path / "report.md"
        result = generate_run_report(str(tmp_path), str(out))
        assert Path(result).exists()
        content = out.read_text(encoding="utf-8")
        assert "rpt_test" in content
        assert "report_exp" in content


class TestGenerateHealthReport:
    def test_generates_health_markdown(self, tmp_path: Path) -> None:
        from src.common.types import HealthStatus
        from src.tools.report_generator import generate_health_report

        statuses = [
            HealthStatus(
                component="pump",
                status="ok",
                message="All good",
                last_checked=datetime(2025, 1, 1, 12, 0, 0),
            ),
            HealthStatus(
                component="echem",
                status="error",
                message="Disconnected",
                last_checked=datetime(2025, 1, 1, 12, 0, 0),
            ),
        ]
        out = tmp_path / "health.md"
        result = generate_health_report(statuses, str(out))
        assert Path(result).exists()
        content = out.read_text(encoding="utf-8")
        assert "pump" in content
        assert "Disconnected" in content


# ── visualization ─────────────────────────────────────────────────────────────

class TestPlotCvCurve:
    def test_saves_png(self, tmp_path: Path) -> None:
        import numpy as np
        from src.tools.visualization import plot_cv_curve

        df = pd.DataFrame({
            "Potential(V)": np.linspace(-1, 1, 50),
            "Current(A)": np.sin(np.linspace(0, 2 * 3.14159, 50)) * 1e-3,
        })
        out = tmp_path / "cv_plot.png"
        result = plot_cv_curve(df, "Test CV", str(out))
        assert Path(result).exists()
        assert out.stat().st_size > 0


class TestPlotStepTimeline:
    def test_saves_png(self, tmp_path: Path) -> None:
        from src.tools.visualization import plot_step_timeline

        timeline = [
            {"event": "start", "source": "pump", "timestamp": "2025-01-01T10:00:00", "status": "running"},
            {"event": "end", "source": "pump", "timestamp": "2025-01-01T10:00:05", "duration_s": 5.0, "status": "done"},
            {"event": "start", "source": "echem", "timestamp": "2025-01-01T10:00:05", "status": "running"},
            {"event": "end", "source": "echem", "timestamp": "2025-01-01T10:00:15", "duration_s": 10.0, "status": "failed"},
        ]
        out = tmp_path / "timeline.png"
        result = plot_step_timeline(timeline, str(out))
        assert Path(result).exists()

    def test_empty_timeline(self, tmp_path: Path) -> None:
        from src.tools.visualization import plot_step_timeline

        out = tmp_path / "empty_timeline.png"
        result = plot_step_timeline([], str(out))
        assert Path(result).exists()


class TestPlotMultiCvOverlay:
    def test_overlay_saves_png(self, tmp_path: Path) -> None:
        from src.tools.visualization import plot_multi_cv_overlay

        for i in range(2):
            f = tmp_path / f"cv_{i}.csv"
            f.write_text("Potential(V),Current(A)\n0.0,0.001\n0.5,0.002\n1.0,0.003\n")

        out = tmp_path / "overlay.png"
        files = [str(tmp_path / f"cv_{i}.csv") for i in range(2)]
        result = plot_multi_cv_overlay(files, ["Run 1", "Run 2"], str(out))
        assert Path(result).exists()

    def test_labels_padded(self, tmp_path: Path) -> None:
        from src.tools.visualization import plot_multi_cv_overlay

        f = tmp_path / "cv_0.csv"
        f.write_text("Potential(V),Current(A)\n0.0,0.001\n0.5,0.002\n")
        out = tmp_path / "pad.png"
        # 1 file but 0 labels → should auto-pad
        result = plot_multi_cv_overlay([str(f)], [], str(out))
        assert Path(result).exists()

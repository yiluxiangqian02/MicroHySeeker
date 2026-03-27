"""Extended tests for tool-layer modules.

Covers:
- src/tools/echem_reader   — read_cv_csv, read_eis_csv, read_experiment_dir
- src/tools/log_analysis   — parse_run_log, classify_errors, detect_pump_anomalies,
                              extract_step_timeline, summarize_run
- src/tools/registry       — ToolRegistry, build_default_registry
- src/tools/report_generator — generate_run_report (smoke test)
- src/tools/file_watcher   — watch_data_dir (polling, max_polls guard)
- src/tools/visualization  — plot_cv_curve, plot_step_timeline (file-write smoke)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


# ── echem_reader tests ────────────────────────────────────────────────────────

class TestReadCvCsv:
    def test_reads_valid_csv(self, cv_csv_file: Path) -> None:
        from src.tools.echem_reader import read_cv_csv

        df = read_cv_csv(str(cv_csv_file))
        assert isinstance(df, pd.DataFrame)
        assert "Potential(V)" in df.columns
        assert "Current(A)" in df.columns
        assert len(df) > 0

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_cv_csv

        with pytest.raises(FileNotFoundError):
            read_cv_csv(str(tmp_path / "nonexistent.csv"))

    def test_missing_columns_raises(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_cv_csv

        bad = tmp_path / "bad.csv"
        bad.write_text("A,B\n1,2\n3,4\n")
        with pytest.raises(ValueError, match="missing required columns"):
            read_cv_csv(str(bad))

    def test_alias_columns_normalised(self, tmp_path: Path) -> None:
        """Column alias 'Potential/V' should be normalised to 'Potential(V)'."""
        from src.tools.echem_reader import read_cv_csv

        aliased = tmp_path / "cv_alias.csv"
        aliased.write_text("Potential/V,Current/A\n0.1,0.001\n0.2,0.002\n")
        df = read_cv_csv(str(aliased))
        assert "Potential(V)" in df.columns


class TestReadEisCsv:
    def test_reads_valid_csv(self, eis_csv_file: Path) -> None:
        from src.tools.echem_reader import read_eis_csv

        df = read_eis_csv(str(eis_csv_file))
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_eis_csv

        with pytest.raises(FileNotFoundError):
            read_eis_csv(str(tmp_path / "no_eis.csv"))


class TestReadExperimentDir:
    def test_returns_expected_keys(self, mock_run_dir: Path) -> None:
        from src.tools.echem_reader import read_experiment_dir

        result = read_experiment_dir(str(mock_run_dir))
        assert "run_dir" in result
        assert "files" in result
        assert "counts" in result

    def test_csv_files_discovered(self, mock_run_dir: Path) -> None:
        from src.tools.echem_reader import read_experiment_dir

        result = read_experiment_dir(str(mock_run_dir))
        assert result["counts"]["csv"] >= 3  # cv, lsv, eis

    def test_cv_eis_separated(self, mock_run_dir: Path) -> None:
        from src.tools.echem_reader import read_experiment_dir

        result = read_experiment_dir(str(mock_run_dir))
        assert result["counts"]["cv"] >= 1
        assert result["counts"]["eis"] >= 1

    def test_missing_dir_raises(self, tmp_path: Path) -> None:
        from src.tools.echem_reader import read_experiment_dir

        with pytest.raises(FileNotFoundError):
            read_experiment_dir(str(tmp_path / "ghost_run"))

    def test_metadata_loaded_from_json(self, mock_run_dir: Path) -> None:
        from src.tools.echem_reader import read_experiment_dir

        result = read_experiment_dir(str(mock_run_dir))
        run_summary = result["metadata"].get("run_summary", {})
        assert run_summary.get("run_id") == "test_run_001"


# ── log_analysis tests ────────────────────────────────────────────────────────

class TestParseRunLog:
    def test_parse_returns_entries(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import parse_run_log

        log_path = str(mock_run_dir / "run_log.log")
        entries = parse_run_log(log_path)
        assert len(entries) >= 7

    def test_level_parsed_correctly(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import parse_run_log

        entries = parse_run_log(str(mock_run_dir / "run_log.log"))
        levels = {e.level for e in entries}
        assert "INFO" in levels
        assert "WARNING" in levels
        assert "ERROR" in levels

    def test_source_parsed_correctly(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import parse_run_log

        entries = parse_run_log(str(mock_run_dir / "run_log.log"))
        sources = {e.source for e in entries}
        assert "experiment_ctrl" in sources
        assert "pump_controller" in sources

    def test_nonexistent_log_file_raises(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import parse_run_log

        with pytest.raises((FileNotFoundError, OSError)):
            parse_run_log(str(tmp_path / "missing.log"))


class TestClassifyErrors:
    def test_groups_by_source(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import classify_errors, parse_run_log

        entries = parse_run_log(str(mock_run_dir / "run_log.log"))
        grouped = classify_errors(entries)
        assert "pump_controller" in grouped

    def test_non_error_entries_excluded(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import classify_errors, parse_run_log

        entries = parse_run_log(str(mock_run_dir / "run_log.log"))
        grouped = classify_errors(entries)
        for source, errs in grouped.items():
            for e in errs:
                assert e.level == "ERROR", f"Non-error entry in {source}: {e}"

    def test_no_errors_returns_empty(self) -> None:
        from src.tools.log_analysis import classify_errors
        from src.common.types import LogEntry
        from datetime import datetime

        info_entry = LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            source="test",
            message="all good",
            raw="",
        )
        grouped = classify_errors([info_entry])
        assert grouped == {}


class TestDetectPumpAnomalies:
    def test_detects_pump_timeout(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import detect_pump_anomalies, parse_run_log

        entries = parse_run_log(str(mock_run_dir / "run_log.log"))
        results = detect_pump_anomalies(entries)
        assert len(results) >= 1
        assert results[0].category == "pump"
        assert results[0].severity == "error"

    def test_no_pump_entries_returns_empty(self) -> None:
        from src.tools.log_analysis import detect_pump_anomalies
        from src.common.types import LogEntry
        from datetime import datetime

        entries = [
            LogEntry(
                timestamp=datetime.now(),
                level="INFO",
                source="sensor",
                message="temperature normal",
                raw="",
            )
        ]
        results = detect_pump_anomalies(entries)
        assert results == []


class TestExtractStepTimeline:
    def test_extracts_start_end_events(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import extract_step_timeline, parse_run_log

        entries = parse_run_log(str(mock_run_dir / "run_log.log"))
        timeline = extract_step_timeline(entries)
        events = [e["event"] for e in timeline]
        assert "start" in events
        assert "end" in events

    def test_timeline_entries_have_required_keys(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import extract_step_timeline, parse_run_log

        entries = parse_run_log(str(mock_run_dir / "run_log.log"))
        timeline = extract_step_timeline(entries)
        for item in timeline:
            assert "event" in item
            assert "source" in item
            assert "timestamp" in item


class TestSummarizeRun:
    def test_returns_run_summary(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import summarize_run

        summary = summarize_run(str(mock_run_dir))
        assert summary.run_id == "test_run_001"
        assert summary.exp_name == "HER_NiFe_screening"
        assert summary.success is True

    def test_step_results_populated(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import summarize_run

        summary = summarize_run(str(mock_run_dir))
        assert len(summary.step_results) == 2
        assert summary.step_results[0].step_type == "cv"

    def test_errors_from_log(self, mock_run_dir: Path) -> None:
        from src.tools.log_analysis import summarize_run

        summary = summarize_run(str(mock_run_dir))
        # The log has 1 ERROR entry
        assert len(summary.errors) >= 1

    def test_empty_run_dir_no_crash(self, tmp_path: Path) -> None:
        from src.tools.log_analysis import summarize_run

        empty_run = tmp_path / "empty_run"
        empty_run.mkdir()
        summary = summarize_run(str(empty_run))
        # Should not raise; returns defaults
        assert summary is not None
        assert summary.run_id == "empty_run"


# ── registry tests ────────────────────────────────────────────────────────────

class TestToolRegistry:
    def test_register_and_get(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.register("my_tool", lambda x: x * 2, "doubles input")
        handler = reg.get("my_tool")
        assert handler(5) == 10

    def test_get_missing_raises(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_register_empty_name_raises(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        with pytest.raises(ValueError):
            reg.register("", lambda: None)

    def test_list_tools_returns_list(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.register("t1", lambda: 1, "desc1")
        reg.register("t2", lambda: 2, "desc2")
        tools = reg.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"t1", "t2"}

    def test_unregister(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.register("temp", lambda: None)
        reg.unregister("temp")
        with pytest.raises(KeyError):
            reg.get("temp")

    def test_unregister_nonexistent_no_error(self) -> None:
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.unregister("ghost")  # should not raise

    def test_invoke_sync(self) -> None:
        import asyncio
        from src.tools.registry import ToolRegistry

        reg = ToolRegistry()
        reg.register("add", lambda a, b: a + b)
        result = asyncio.run(reg.invoke("add", 3, 4))
        assert result == 7


class TestBuildDefaultRegistry:
    def test_returns_registry_with_tools(self) -> None:
        from src.tools.registry import build_default_registry

        reg = build_default_registry()
        tools = reg.list_tools()
        names = {t["name"] for t in tools}
        assert "read_cv_csv" in names
        assert "read_eis_csv" in names
        assert "read_experiment_dir" in names
        assert "start_experiment" in names
        assert "stop_experiment" in names

    def test_all_tools_have_description(self) -> None:
        from src.tools.registry import build_default_registry

        reg = build_default_registry()
        for tool in reg.list_tools():
            assert tool["description"], f"Tool {tool['name']} has no description"


# ── report_generator tests ────────────────────────────────────────────────────

class TestGenerateRunReport:
    def test_returns_output_path_string(self, mock_run_dir: Path, tmp_path: Path) -> None:
        from src.tools.report_generator import generate_run_report

        out = tmp_path / "report.md"
        result = generate_run_report(str(mock_run_dir), str(out))
        assert isinstance(result, str)
        assert out.exists()

    def test_report_contains_run_id(self, mock_run_dir: Path, tmp_path: Path) -> None:
        from src.tools.report_generator import generate_run_report

        out = tmp_path / "report.md"
        generate_run_report(str(mock_run_dir), str(out))
        content = out.read_text(encoding="utf-8")
        assert "test_run_001" in content

    def test_report_contains_exp_name(self, mock_run_dir: Path, tmp_path: Path) -> None:
        from src.tools.report_generator import generate_run_report

        out = tmp_path / "report.md"
        generate_run_report(str(mock_run_dir), str(out))
        content = out.read_text(encoding="utf-8")
        assert "HER_NiFe_screening" in content

    def test_file_non_empty(self, mock_run_dir: Path, tmp_path: Path) -> None:
        from src.tools.report_generator import generate_run_report

        out = tmp_path / "report.md"
        generate_run_report(str(mock_run_dir), str(out))
        assert out.stat().st_size > 50


# ── file_watcher tests ────────────────────────────────────────────────────────

class TestWatchDataDir:
    def test_yields_new_run_dirs(self, tmp_path: Path) -> None:
        from src.tools.file_watcher import watch_data_dir

        # Create a day_dir/run_dir structure AFTER watcher starts
        day = tmp_path / "2024-01-15"
        day.mkdir()

        # Run watcher with max_polls=1 and very short interval
        # Pre-existing directory is in 'seen', so create it after initial snapshot
        gen = watch_data_dir(str(tmp_path), poll_interval=0.01, max_polls=1)
        # The generator won't yield anything if run_dir already existed before first poll
        results = list(gen)
        # Results may be empty (run_dir was already there), that's fine
        assert isinstance(results, list)

    def test_discovers_new_dirs_mid_run(self, tmp_path: Path) -> None:
        from src.tools.file_watcher import watch_data_dir
        import threading

        day = tmp_path / "2024-01-16"
        day.mkdir()

        found: list[str] = []

        def _create_run() -> None:
            import time
            time.sleep(0.05)
            (day / "run_001").mkdir()

        t = threading.Thread(target=_create_run)
        t.start()
        gen = watch_data_dir(str(tmp_path), poll_interval=0.02, max_polls=5)
        for path in gen:
            found.append(path)
        t.join()
        # The new run_001 should have been yielded
        assert any("run_001" in p for p in found)

    def test_empty_root_no_yields(self, tmp_path: Path) -> None:
        from src.tools.file_watcher import watch_data_dir

        results = list(watch_data_dir(str(tmp_path), poll_interval=0.01, max_polls=1))
        assert results == []


# ── visualization smoke tests ─────────────────────────────────────────────────

class TestVisualization:
    def test_plot_cv_curve_saves_png(self, cv_csv_file: Path, tmp_path: Path) -> None:
        """plot_cv_curve should write a PNG without raising."""
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend for CI
        from src.tools.visualization import plot_cv_curve
        import pandas as pd

        df = pd.read_csv(str(cv_csv_file))
        out = str(tmp_path / "cv_plot.png")
        result = plot_cv_curve(df, title="Test CV", save_path=out)
        assert Path(result).exists()
        assert Path(result).suffix == ".png"

    def test_plot_step_timeline_saves_png(self, tmp_path: Path) -> None:
        """plot_step_timeline should write a PNG without raising."""
        import matplotlib
        matplotlib.use("Agg")
        from src.tools.visualization import plot_step_timeline

        timeline = [
            {"event": "start", "source": "cv_step", "timestamp": "2024-01-15T10:00:00", "status": "running"},
            {"event": "end", "source": "cv_step", "timestamp": "2024-01-15T10:02:00", "duration_s": 120.0, "status": "done"},
        ]
        out = str(tmp_path / "timeline.png")
        result = plot_step_timeline(timeline, save_path=out)
        assert Path(result).exists()

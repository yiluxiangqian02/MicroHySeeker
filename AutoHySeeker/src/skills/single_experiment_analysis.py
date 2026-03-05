"""A1 — SingleExperimentAnalysisSkill: analyse all echem data in a run directory.

Loads every electrochemical CSV from a run directory, auto-detects technique,
runs the appropriate analysis (CV / LSV / EIS / generic), and returns a
structured summary as a :class:`~src.skills.base.SkillResult`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.skills.base import BaseSkill, SkillResult
from src.tools.data_reader import load_run_echem_files, read_run_metadata
from src.tools.echem_analysis import analyze_cv, analyze_eis, analyze_lsv


class SingleExperimentAnalysisSkill(BaseSkill):
    """Analyse all electrochemical data files in a single experiment run.

    This skill is purely data-driven and does **not** call any LLM.  It:

    1. Loads all ``*.csv`` files from *run_dir* via :func:`~src.tools.data_reader.load_run_echem_files`.
    2. Runs technique-specific analysis (:func:`~src.tools.echem_analysis.analyze_cv`,
       :func:`~src.tools.echem_analysis.analyze_lsv`, or
       :func:`~src.tools.echem_analysis.analyze_eis`).
    3. Returns a :class:`~src.skills.base.SkillResult` whose ``data`` field is a
       list of per-file analysis dicts.
    """

    name = "single_experiment_analysis"
    description = "分析单次实验运行的所有电化学数据文件并输出结构化结果"
    required_tools = [
        "load_run_echem_files",
        "read_run_metadata",
        "analyze_cv",
        "analyze_lsv",
        "analyze_eis",
    ]

    async def execute(self, run_dir: str = "", **kwargs: Any) -> SkillResult:
        """Analyse all echem CSV files found in *run_dir*.

        Args:
            run_dir: Path to the experiment run directory.
            **kwargs: Ignored additional arguments.

        Returns:
            :class:`~src.skills.base.SkillResult` where ``data`` is a list of
            dicts, each containing ``file``, ``technique``, and
            technique-specific analysis keys.
        """
        if not run_dir:
            return SkillResult(
                success=False,
                data=[],
                message="run_dir parameter is required",
                artifacts=[],
            )

        run_path = Path(run_dir)
        if not run_path.exists():
            return SkillResult(
                success=False,
                data=[],
                message=f"Run directory not found: {run_dir}",
                artifacts=[],
            )

        # ── Step 1: read run metadata (best-effort) ───────────────────────────
        try:
            metadata = read_run_metadata(run_dir)
        except Exception:
            metadata = {"run_dir": run_dir}

        # ── Step 2: load all CSV files ────────────────────────────────────────
        try:
            echem_files = load_run_echem_files(run_dir)
        except FileNotFoundError as exc:
            return SkillResult(
                success=False,
                data=[],
                message=str(exc),
                artifacts=[],
            )

        if not echem_files:
            return SkillResult(
                success=True,
                data=[],
                message=f"No electrochemical CSV files found in {run_dir}",
                artifacts=[],
            )

        # ── Step 3: analyse each file by technique ────────────────────────────
        results: list[dict[str, Any]] = []
        for echem in echem_files:
            df = echem.data
            technique = echem.technique
            base: dict[str, Any] = {
                "file": echem.file_path,
                "technique": technique,
                "n_points": echem.points,
                "metadata": echem.metadata,
            }
            try:
                if technique == "cv":
                    analysis = analyze_cv(df)
                elif technique == "lsv":
                    analysis = analyze_lsv(df)
                elif technique == "eis":
                    analysis = analyze_eis(df)
                else:
                    # Generic numeric summary for unknown techniques
                    numeric_cols = df.select_dtypes(include="number").columns.tolist()
                    analysis = {
                        "columns": list(df.columns),
                        "numeric_columns": numeric_cols,
                        "shape": list(df.shape),
                    }
                base.update(analysis)
            except Exception as exc:
                base["error"] = str(exc)
            results.append(base)

        # ── Step 4: build summary stats ───────────────────────────────────────
        techniques_found = list({r["technique"] for r in results})
        n_with_errors = sum(1 for r in results if "error" in r)

        return SkillResult(
            success=True,
            data=results,
            message=(
                f"Analysed {len(results)} file(s) "
                f"[{', '.join(sorted(techniques_found))}] "
                f"in {run_dir}"
                + (f" — {n_with_errors} file(s) had errors" if n_with_errors else "")
            ),
            artifacts=[r["file"] for r in results],
        )

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "run_dir": {
                    "type": "string",
                    "description": "Path to the experiment run directory containing CSV files",
                }
            },
            "required": ["run_dir"],
        }


# Convenience singleton
single_experiment_analysis_skill = SingleExperimentAnalysisSkill()

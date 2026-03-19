"""Data analysis skill — extracts metrics and assesses experiment quality.

Converted from the former DataAnalystAgent.  This skill is deterministic
(no LLM calls) and is owned by the OrchestratorAgent.

Key outputs:
- ``metrics``: overpotential_mV, current_density, tafel_slope, etc.
- ``data_quality``: score 0–1, issues list, ``reliable`` boolean.
- ``comparison``: vs-best tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from src.skills.base import BaseSkill, SkillResult

_logger = logging.getLogger("autohyseeker.skill.data_analysis")


class DataAnalysisSkill(BaseSkill):
    """Extract electrochemistry metrics and assess data quality.

    This is a pure-computation skill — it does **not** call any LLM.
    """

    name = "data_analysis"
    description = "Extract metrics, assess quality, and compare with best result."
    required_tools: list[str] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Run the full analysis pipeline.

        Keyword Args:
            run_id: Experiment run identifier.
            data_path: Path to the run data directory.
            params: Element ratios used in this experiment.
            target_metric: Primary metric to focus on.
            best_result: Current best result for comparison.

        Returns:
            SkillResult with analysis data.
        """
        run_id: str = kwargs.get("run_id", "")
        data_path: str = kwargs.get("data_path", "")
        params: dict[str, float] | None = kwargs.get("params")
        target_metric: str = kwargs.get("target_metric", "overpotential_mV")
        best_result: dict[str, Any] | None = kwargs.get("best_result")

        _logger.info(
            "DataAnalysisSkill: analyze run_id=%s path=%s", run_id, data_path
        )

        # 1. Extract metrics
        metrics = await self._extract_metrics(data_path, run_id)

        # 2. Assess quality
        quality = self.assess_quality(metrics, data_path)

        # 3. Compare with best
        comparison: dict[str, Any] = {}
        if best_result and metrics:
            comparison = self.compare_with_best(metrics, best_result, target_metric)

        # 4. Generate simple interpretation (no LLM)
        interpretation = self._make_interpretation(metrics, quality, comparison)

        data = {
            "status": "analyzed",
            "run_id": run_id,
            "params": params or {},
            "metrics": metrics,
            "data_quality": quality,
            "interpretation": interpretation,
            "comparison": comparison,
        }

        return SkillResult(
            success=True,
            data=data,
            message=f"Analysis complete for {run_id}",
            artifacts=[],
        )

    # ── Metric Extraction ──────────────────────────────────────────────────────

    async def _extract_metrics(
        self, data_path: str, run_id: str
    ) -> dict[str, float]:
        """Extract metrics from experiment data files."""
        metrics: dict[str, float] = {}

        # Strategy 1: Use SingleExperimentAnalysisSkill
        if data_path:
            try:
                from src.skills.single_experiment_analysis import (
                    SingleExperimentAnalysisSkill,
                )

                skill = SingleExperimentAnalysisSkill()
                result = await skill.execute(run_dir=data_path)
                if result.success and result.data:
                    metrics = self._extract_from_skill_result(result.data)
                    if metrics:
                        return metrics
            except Exception as exc:
                _logger.debug("Skill-based analysis failed: %s", exc)

        # Strategy 2: Get data from API
        try:
            from src.tools import experiment_ctrl as ctrl

            detail = ctrl.get_run_detail(run_id)
            if detail.get("metrics"):
                return {
                    k: float(v)
                    for k, v in detail["metrics"].items()
                    if isinstance(v, (int, float))
                }
        except Exception as exc:
            _logger.debug("API data retrieval failed: %s", exc)

        return metrics

    def _extract_from_skill_result(
        self, skill_data: list[dict[str, Any]] | dict[str, Any]
    ) -> dict[str, float]:
        """Extract standard metrics from SingleExperimentAnalysisSkill output."""
        metrics: dict[str, float] = {}

        if isinstance(skill_data, dict):
            skill_data = [skill_data]

        for analysis in skill_data:
            technique = analysis.get("technique", "").upper()

            if technique == "LSV":
                lsv = analysis.get("analysis", {})
                if "onset_potential_V" in lsv:
                    metrics["onset_potential_V"] = float(lsv["onset_potential_V"])
                if "overpotential_mV" in lsv:
                    metrics["overpotential_mV"] = float(lsv["overpotential_mV"])

            elif technique == "CV":
                cv = analysis.get("analysis", {})
                if "peak_current_A" in cv:
                    metrics["peak_current_A"] = float(cv["peak_current_A"])
                if "ecsa_cm2" in cv:
                    metrics["ecsa_cm2"] = float(cv["ecsa_cm2"])

            elif technique == "EIS":
                eis = analysis.get("analysis", {})
                if "charge_transfer_resistance_ohm" in eis:
                    metrics["rct_ohm"] = float(eis["charge_transfer_resistance_ohm"])

        return metrics

    # ── Quality Assessment ─────────────────────────────────────────────────────

    def assess_quality(
        self, metrics: dict[str, float], data_path: str = ""
    ) -> dict[str, Any]:
        """Assess data quality based on metrics completeness and values.

        This is a public method so it can be called directly (e.g. by
        ``_simulate_dry_run_analysis``).
        """
        issues: list[str] = []
        score = 1.0

        # Check completeness
        expected = {"overpotential_mV", "onset_potential_V"}
        missing = expected - set(metrics.keys())
        if missing:
            issues.append(f"缺少指标: {', '.join(missing)}")
            score -= 0.2 * len(missing)

        # Check for unreasonable values
        ovp = metrics.get("overpotential_mV")
        if ovp is not None:
            if ovp < 0:
                issues.append("过电位为负值，数据可能异常")
                score -= 0.3
            elif ovp > 1000:
                issues.append("过电位过大 (>1000 mV)，催化活性极低或数据异常")
                score -= 0.2

        tafel = metrics.get("tafel_slope_mV_dec")
        if tafel is not None and tafel > 200:
            issues.append("Tafel 斜率过大 (>200 mV/dec)")
            score -= 0.1

        # No data at all
        if not metrics:
            issues.append("未提取到任何指标")
            score = 0.0

        # No data path
        if not data_path:
            issues.append("无数据文件路径")
            score -= 0.1

        score = max(0.0, min(1.0, score))

        return {
            "score": round(score, 2),
            "issues": issues,
            "reliable": score >= 0.6,
        }

    # ── Comparison ─────────────────────────────────────────────────────────────

    def compare_with_best(
        self,
        metrics: dict[str, float],
        best_result: dict[str, Any],
        target_metric: str,
    ) -> dict[str, Any]:
        """Compare current metrics with the best result so far."""
        best_metrics = best_result.get("metrics", {})
        current_val = metrics.get(target_metric)
        best_val = best_metrics.get(target_metric)

        if current_val is None or best_val is None:
            return {"vs_best": {"comparable": False}}

        change = round(current_val - best_val, 2)
        pct_change = (
            round(change / abs(best_val) * 100, 1) if best_val != 0 else 0.0
        )

        return {
            "vs_best": {
                "comparable": True,
                f"{target_metric}_current": current_val,
                f"{target_metric}_best": best_val,
                f"{target_metric}_change": change,
                "change_pct": pct_change,
                "is_improvement": change < 0,  # for minimize
            }
        }

    # ── Interpretation (template-based, no LLM) ───────────────────────────────

    def _make_interpretation(
        self,
        metrics: dict[str, float],
        quality: dict[str, Any],
        comparison: dict[str, Any],
    ) -> str:
        """Generate a simple textual interpretation without LLM."""
        parts = [f"{k}: {v}" for k, v in metrics.items()]
        text = f"指标提取完成: {', '.join(parts)}。质量评分: {quality.get('score', 'N/A')}"

        vs = comparison.get("vs_best", {})
        if vs.get("comparable"):
            pct = vs.get("change_pct", 0)
            direction = "改善" if vs.get("is_improvement") else "劣于"
            text += f"。与最优结果比较: {direction} {abs(pct)}%"

        return text

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "title": self.name,
            "description": self.description,
            "properties": {
                "run_id": {"type": "string"},
                "data_path": {"type": "string"},
                "params": {"type": "object"},
                "target_metric": {"type": "string"},
                "best_result": {"type": "object"},
            },
            "required": ["run_id"],
        }

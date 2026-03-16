"""Data analyst agent — extracts metrics and assesses experiment quality.

The analyst processes completed experiment data (CV/LSV/EIS) and returns
structured metrics that the Orchestrator uses for optimization decisions.

Key outputs:
- ``metrics``: overpotential_mV, current_density, tafel_slope, etc.
- ``data_quality``: score 0–1, issues list, ``reliable`` boolean.
- ``interpretation``: LLM-generated textual analysis.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent

_logger = logging.getLogger("autohyseeker.data_analyst")

ANALYST_SYSTEM_PROMPT = """\
你是数据分析 Agent（Data Analyst），负责分析电化学实验数据并提取关键指标。

## 工作流程
1. 读取实验数据文件（CV/LSV/EIS CSV 文件）
2. 提取关键指标（过电位、电流密度、Tafel 斜率等）
3. 评估数据质量（完整性、可靠性）
4. 给出结构化分析结果

## 关键指标
- overpotential_mV: HER 过电位（在 10 mA/cm² 时）
- current_density_mA_cm2: 电流密度
- tafel_slope_mV_dec: Tafel 斜率
- onset_potential_V: 起始电位
- ecsa_cm2: 电化学活性面积

## 数据质量评估
- score: 0-1 之间的质量评分
- reliable: score ≥ 0.6 则为 true
- issues: 数据问题列表（噪声大、数据点少、异常值等）

## 输出格式（严格 JSON）
```json
{
  "status": "analyzed",
  "metrics": {
    "overpotential_mV": 182.5,
    "current_density_mA_cm2": 15.3,
    "tafel_slope_mV_dec": 68.2,
    "onset_potential_V": -0.15
  },
  "data_quality": {
    "score": 0.92,
    "issues": [],
    "reliable": true
  },
  "interpretation": "分析解读文本",
  "comparison": {}
}
```
"""


class DataAnalystAgent(BaseAgent):
    """Data analyst — extracts metrics and assesses quality from echem data."""

    def __init__(self) -> None:
        super().__init__(
            name="data_analyst",
            system_prompt=ANALYST_SYSTEM_PROMPT,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def analyze_experiment(
        self,
        run_id: str,
        data_path: str = "",
        params: dict[str, float] | None = None,
        target_metric: str = "overpotential_mV",
        best_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze a completed experiment and extract structured metrics.

        Args:
            run_id: Experiment run identifier.
            data_path: Path to the run data directory.
            params: Element ratios used in this experiment.
            target_metric: Primary metric to focus on.
            best_result: Current best result for comparison.

        Returns:
            Analysis dict with ``metrics``, ``data_quality``, ``interpretation``.
        """
        _logger.info(
            "DataAnalystAgent: analyze_experiment run_id=%s path=%s",
            run_id, data_path,
        )

        # ── 1. Try to extract metrics from data files ─────────────────────────
        metrics = await self._extract_metrics(data_path, run_id)

        # ── 2. Assess data quality ────────────────────────────────────────────
        quality = self._assess_quality(metrics, data_path)

        # ── 3. Compare with best ──────────────────────────────────────────────
        comparison = {}
        if best_result and metrics:
            comparison = self._compare_with_best(
                metrics, best_result, target_metric,
            )

        # ── 4. LLM interpretation ────────────────────────────────────────────
        interpretation = await self._interpret(
            metrics, quality, params, comparison,
        )

        return {
            "status": "analyzed",
            "run_id": run_id,
            "params": params or {},
            "metrics": metrics,
            "data_quality": quality,
            "interpretation": interpretation,
            "comparison": comparison,
        }

    # ── Private: Metric Extraction ────────────────────────────────────────────

    async def _extract_metrics(
        self,
        data_path: str,
        run_id: str,
    ) -> dict[str, float]:
        """Extract metrics from experiment data files.

        Tries the SingleExperimentAnalysisSkill first, then falls back to
        API-based data retrieval.
        """
        metrics: dict[str, float] = {}

        # Strategy 1: Use existing skill
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
            # Extract from run detail metadata
            if detail.get("metrics"):
                return {k: float(v) for k, v in detail["metrics"].items()
                        if isinstance(v, (int, float))}
        except Exception as exc:
            _logger.debug("API data retrieval failed: %s", exc)

        return metrics

    def _extract_from_skill_result(
        self,
        skill_data: list[dict[str, Any]] | dict[str, Any],
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
                # Extract overpotential at 10 mA/cm2
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

    # ── Private: Quality Assessment ───────────────────────────────────────────

    def _assess_quality(
        self,
        metrics: dict[str, float],
        data_path: str,
    ) -> dict[str, Any]:
        """Assess data quality based on metrics completeness and values."""
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

    # ── Private: Comparison ───────────────────────────────────────────────────

    def _compare_with_best(
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
        pct_change = round(change / abs(best_val) * 100, 1) if best_val != 0 else 0.0

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

    # ── Private: LLM Interpretation ───────────────────────────────────────────

    async def _interpret(
        self,
        metrics: dict[str, float],
        quality: dict[str, Any],
        params: dict[str, float] | None,
        comparison: dict[str, Any],
    ) -> str:
        """Use LLM to generate a textual interpretation of the results."""
        task = {
            "type": "interpret_results",
            "metrics": metrics,
            "quality": quality,
        }
        context = {
            "params": params or {},
            "comparison": comparison,
        }

        try:
            result = await self.invoke(task=task, context=context)
            return result.get("content", "")[:500]
        except Exception as exc:
            _logger.warning("LLM interpretation failed: %s", exc)
            # Fallback text
            parts = [f"{k}: {v}" for k, v in metrics.items()]
            return f"指标提取完成: {', '.join(parts)}。质量评分: {quality.get('score', 'N/A')}"



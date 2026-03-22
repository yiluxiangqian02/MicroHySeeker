"""Orchestrator agent — closed-loop optimization coordinator.

The orchestrator is the "brain" of the multi-agent system.  It:

1. Manages the optimization goal and search state.
2. Dispatches tasks to specialist agents (Designer → Executor).
3. Analyses experiment data via DataAnalysisSkill (built-in).
4. Archives results via KnowledgeArchiveSkill (built-in).
5. Evaluates results and decides: *continue / stop / retry / diagnose*.
6. Handles anomaly escalation from the Executor.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any
from uuid import uuid4

from src.agents.base import BaseAgent
from src.common.config import ORCHESTRATOR_CONFIG
from src.ml.performance_predictor import PerformancePredictor

_logger = logging.getLogger("autohyseeker.orchestrator")

ORCHESTRATOR_SYSTEM_PROMPT = """\
你是 AutoHySeeker 的运行管控 Agent（Orchestrator），即多 Agent 闭环优化系统的总调度器。

## 你的职责
1. 接收用户的优化目标（如"找到最优 Fe:Co:Ni 配比使 HER 过电位最小"）。
2. 基于历史实验结果和当前最优结果，做出决策：
   - "continue": 继续优化——让实验设计 Agent 生成下一组参数
   - "stop": 目标达成或到达最大轮次——生成总结报告
   - "retry": 上一次实验数据不可靠——用相同参数重做
   - "adjust_strategy": 优化陷入局部最优——建议改变搜索策略
3. 你需要综合判断实验趋势：是否在持续改善？是否已收敛？是否需要更多探索？

## 输出格式（严格 JSON）
```json
{
  "action": "continue|stop|retry|adjust_strategy",
  "reason": "简要解释决策原因",
  "next_params_hint": {"element": "direction"},  // 可选的方向提示
  "confidence": 0.8,  // 0-1 的决策置信度
  "summary": "当前优化进展摘要"
}
```

## 安全规则
- 所有泵转速不得超过 300 RPM
- 遇到严重硬件异常必须建议停止
- 优化不应无限运行——到达 max_rounds 必须停止
"""


class OrchestratorAgent(BaseAgent):
    """Orchestrator agent — decides next action in the optimization loop.

    Owns two built-in skills:

    * :class:`DataAnalysisSkill` — metric extraction and quality assessment.
    * :class:`KnowledgeArchiveSkill` — experiment archival and retrieval.
    """

    def __init__(self, archive_path: str | None = None) -> None:
        super().__init__(
            name="orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        )

        # ── Built-in skills ───────────────────────────────────────────────────
        from src.skills.data_analysis_skill import DataAnalysisSkill
        from src.skills.knowledge_archive_skill import KnowledgeArchiveSkill
        from src.skills.knowledge_query_skill import KnowledgeQuerySkill

        self._analysis_skill = DataAnalysisSkill()
        self._knowledge_skill = KnowledgeArchiveSkill(archive_path=archive_path)
        self._knowledge_query_skill = KnowledgeQuerySkill()
        self._config = dict(ORCHESTRATOR_CONFIG)
        self._work_mode = str(self._config.get("work_mode", "semi_auto"))
        self._max_no_improve_rounds = int(self._config.get("max_no_improve_rounds", 3))
        self._pause_on_strategy_change = bool(self._config.get("pause_on_strategy_change", True))
        self._pause_on_anomaly_fix = bool(self._config.get("pause_on_anomaly_fix", True))
        self._pending_approvals: dict[str, dict[str, Any]] = {}
        self._approval_history: list[dict[str, Any]] = []
        self._predictor = PerformancePredictor()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def analyze_experiment(
        self,
        run_id: str,
        data_path: str = "",
        params: dict[str, float] | None = None,
        target_metric: str = "overpotential_mV",
        best_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze a completed experiment (delegates to DataAnalysisSkill).

        Returns analysis dict with ``metrics``, ``data_quality``,
        ``interpretation``, ``comparison``.
        """
        result = await self._analysis_skill.execute(
            run_id=run_id,
            data_path=data_path,
            params=params,
            target_metric=target_metric,
            best_result=best_result,
        )
        return result.data

    async def archive_experiment(
        self,
        run_id: str,
        params: dict[str, float],
        metrics: dict[str, float],
        data_quality: dict[str, Any] | None = None,
        round_num: int | None = None,
        interpretation: str = "",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Archive experiment result (delegates to KnowledgeArchiveSkill)."""
        return await self._knowledge_skill.archive_experiment(
            run_id=run_id,
            params=params,
            metrics=metrics,
            data_quality=data_quality,
            round_num=round_num,
            interpretation=interpretation,
            extra=extra,
        )

    async def retrieve_knowledge(
        self,
        query: str,
        search_type: str = "both",
        top_k: int = 5,
        elements: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve knowledge via the shared read-only knowledge query skill."""
        if search_type == "literature":
            results = await self._knowledge_query_skill.get_literature_insights(query, top_k=top_k)
        elif search_type == "experiment_history" and elements:
            params = {element: 1.0 / len(elements) for element in elements}
            results = await self._knowledge_query_skill.get_similar_experiments(
                params=params,
                threshold=0.5,
                top_k=top_k,
            )
        elif search_type == "fault_history":
            results = await self._knowledge_query_skill.get_fault_history(query, top_k=top_k)
        else:
            partitions = None
            if search_type == "literature":
                partitions = ["literature"]
            elif search_type == "experiment_history":
                partitions = ["experiments"]
            elif search_type == "fault_history":
                partitions = ["operations"]
            results = await self._knowledge_query_skill.search(
                query=query,
                partitions=partitions,
                top_k=top_k,
            )

        return {
            "status": "retrieved",
            "results": results,
            "summary": f"找到 {len(results)} 条相关记录",
        }

    async def evaluate_and_decide(
        self,
        optimization: dict[str, Any],
        experiment_history: list[dict[str, Any]],
        current_result: dict[str, Any] | None,
        best_result: dict[str, Any] | None,
        current_round: int,
    ) -> dict[str, Any]:
        """Evaluate latest round and decide next action.

        Returns a dict with keys: action, reason, confidence, next_params_hint,
        summary.
        """
        task = {
            "type": "evaluate_and_decide",
            "optimization_goal": optimization.get("goal", ""),
            "target_metric": optimization.get("target_metric", ""),
            "optimization_direction": optimization.get("optimization_direction", ""),
            "max_rounds": optimization.get("max_rounds", 20),
            "current_round": current_round,
            "search_space": optimization.get("search_space", {}),
        }

        context = {
            "experiment_history": experiment_history[-10:],  # last 10 for context
            "current_result": current_result,
            "best_result": best_result,
            "total_experiments": len(experiment_history),
        }

        _logger.info(
            "OrchestratorAgent: evaluate_and_decide round=%d/%d history=%d",
            current_round,
            optimization.get("max_rounds", 20),
            len(experiment_history),
        )

        # Hard stop: max rounds reached
        if current_round >= optimization.get("max_rounds", 20):
            _logger.info("OrchestratorAgent: max rounds reached, forcing stop")
            decision = {
                "action": "stop",
                "reason": f"已达到最大轮次 {current_round}",
                "confidence": 1.0,
                "next_params_hint": {},
                "summary": self._build_summary(experiment_history, best_result),
            }
            return await self._apply_human_collaboration(
                decision=decision,
                optimization=optimization,
                experiment_history=experiment_history,
                current_result=current_result,
                best_result=best_result,
                current_round=current_round,
            )

        try:
            result = await self.invoke(task=task, context=context)
            decision = self._parse_decision(result.get("content", ""))
        except Exception as exc:
            _logger.warning("Orchestrator LLM decision failed, using rule fallback: %s", exc)
            decision = self._fallback_decision(
                optimization=optimization,
                experiment_history=experiment_history,
                current_result=current_result,
                best_result=best_result,
                current_round=current_round,
                error=exc,
            )
        return await self._apply_human_collaboration(
            decision=decision,
            optimization=optimization,
            experiment_history=experiment_history,
            current_result=current_result,
            best_result=best_result,
            current_round=current_round,
        )

    async def handle_anomaly(
        self,
        anomaly: dict[str, Any],
        optimization: dict[str, Any],
        current_round: int,
    ) -> dict[str, Any]:
        """Decide how to handle an anomaly reported by the Executor.

        Returns: {"action": "diagnose|emergency_stop|log_and_continue",
                  "severity": str, ...}
        """
        severity = anomaly.get("severity", "medium").lower()

        if severity == "critical":
            _logger.warning(
                "OrchestratorAgent: CRITICAL anomaly — recommending emergency stop"
            )
            decision = {
                "action": "emergency_stop",
                "severity": "critical",
                "reason": f"严重异常: {anomaly.get('type', 'unknown')}",
                "need_user": True,
            }
            return await self._apply_anomaly_collaboration(decision, anomaly, optimization, current_round)

        if severity == "high":
            _logger.warning(
                "OrchestratorAgent: HIGH anomaly — dispatching to diagnostics"
            )
            decision = {
                "action": "diagnose",
                "severity": "high",
                "anomaly": anomaly,
                "reason": f"高级异常: {anomaly.get('type', 'unknown')}，需要诊断",
            }
            return await self._apply_anomaly_collaboration(decision, anomaly, optimization, current_round)

        # medium / low
        _logger.info(
            "OrchestratorAgent: %s anomaly — logging and continuing", severity
        )
        return {
            "action": "log_and_continue",
            "severity": severity,
            "reason": f"低级异常: {anomaly.get('type', 'unknown')}，记录并继续",
        }

    async def request_human_approval(
        self,
        decision: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a pending approval record for a key orchestration decision."""
        approval_id = f"approval_{uuid4().hex[:8]}"
        pending = {
            "approval_id": approval_id,
            "status": "pending",
            "decision": decision,
            "context": context,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._pending_approvals[approval_id] = pending
        return {
            "approved": False,
            "approval_id": approval_id,
            "pending_approval": pending,
        }

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Return all pending approvals."""
        return list(self._pending_approvals.values())

    def get_approval_status(self, approval_id: str) -> dict[str, Any] | None:
        """Return a pending or resolved approval by id."""
        pending = self._pending_approvals.get(approval_id)
        if pending is not None:
            return dict(pending)

        for item in reversed(self._approval_history):
            if item.get("approval_id") == approval_id:
                return dict(item)
        return None

    def get_approval_history(self) -> list[dict[str, Any]]:
        """Return resolved approval records."""
        return list(self._approval_history)

    def respond_human_approval(
        self,
        approval_id: str,
        approved: bool,
        feedback: str = "",
    ) -> dict[str, Any]:
        """Resolve a pending approval."""
        pending = self._pending_approvals.pop(approval_id, None)
        if pending is None:
            return {
                "found": False,
                "approval_id": approval_id,
                "status": "missing",
            }

        resolved = dict(pending)
        resolved.update(
            {
                "status": "approved" if approved else "rejected",
                "approved": approved,
                "human_feedback": feedback,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._approval_history.append(resolved)
        return {"found": True, "approval": resolved}

    async def update_ml_training_data(self, experiment_result: dict[str, Any]) -> dict[str, Any]:
        """Update the internal predictor from completed experiment history."""
        history = experiment_result.get("history", [])
        if not isinstance(history, list):
            history = []
        return self._predictor.fit(history)

    def update_best_result(
        self,
        experiment_history: list[dict[str, Any]],
        optimization: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Scan history and return the best result so far."""
        if not experiment_history:
            return None

        target = optimization.get("target_metric", "overpotential_mV")
        direction = optimization.get("optimization_direction", "minimize")

        valid = [
            e for e in experiment_history
            if e.get("metrics", {}).get(target) is not None
            and e.get("data_quality", {}).get("reliable", True)
        ]
        if not valid:
            return None

        if direction == "minimize":
            best = min(valid, key=lambda e: e["metrics"][target])
        else:
            best = max(valid, key=lambda e: e["metrics"][target])

        return {
            "params": best.get("params"),
            "metrics": best.get("metrics"),
            "round": best.get("round"),
            "run_id": best.get("run_id"),
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _parse_decision(self, content: str) -> dict[str, Any]:
        """Parse LLM response into a structured decision."""
        # Try to extract JSON from the response
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                decision = json.loads(json_match.group())
                # Validate required fields
                action = decision.get("action", "continue")
                if action not in ("continue", "stop", "retry", "adjust_strategy"):
                    action = "continue"
                return {
                    "action": action,
                    "reason": decision.get("reason", ""),
                    "confidence": float(decision.get("confidence", 0.5)),
                    "next_params_hint": decision.get("next_params_hint", {}),
                    "summary": decision.get("summary", ""),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: try to infer action from text
        content_lower = content.lower()
        if "stop" in content_lower or "完成" in content_lower or "达成" in content_lower:
            action = "stop"
        elif "retry" in content_lower or "重试" in content_lower or "重做" in content_lower:
            action = "retry"
        elif "adjust" in content_lower or "调整" in content_lower:
            action = "adjust_strategy"
        else:
            action = "continue"

        return {
            "action": action,
            "reason": content[:200],
            "confidence": 0.5,
            "next_params_hint": {},
            "summary": "",
        }

    def _build_summary(
        self,
        history: list[dict[str, Any]],
        best: dict[str, Any] | None,
    ) -> str:
        """Build a quick text summary of the optimization progress."""
        lines = [f"共完成 {len(history)} 轮实验。"]
        if best:
            lines.append(f"最优结果: {best.get('metrics', {})}")
            lines.append(f"最优参数: {best.get('params', {})}")
            lines.append(f"来自第 {best.get('round', '?')} 轮")
        return " ".join(lines)

    async def _apply_human_collaboration(
        self,
        *,
        decision: dict[str, Any],
        optimization: dict[str, Any],
        experiment_history: list[dict[str, Any]],
        current_result: dict[str, Any] | None,
        best_result: dict[str, Any] | None,
        current_round: int,
    ) -> dict[str, Any]:
        decision = dict(decision)
        decision.setdefault("work_mode", self._work_mode)

        approval_reason = self._approval_reason_for_decision(
            decision=decision,
            experiment_history=experiment_history,
            current_round=current_round,
        )
        if approval_reason is None:
            return decision

        approval = await self.request_human_approval(
            decision={
                **decision,
                "decision_type": approval_reason,
            },
            context={
                "optimization": optimization,
                "current_round": current_round,
                "current_result": current_result,
                "best_result": best_result,
                "history_size": len(experiment_history),
            },
        )
        return {
            "action": "pause_for_human",
            "reason": approval_reason,
            "work_mode": self._work_mode,
            "pending_approval": approval["pending_approval"],
            "original_decision": decision,
        }

    async def _apply_anomaly_collaboration(
        self,
        decision: dict[str, Any],
        anomaly: dict[str, Any],
        optimization: dict[str, Any],
        current_round: int,
    ) -> dict[str, Any]:
        if self._work_mode == "full_auto":
            return decision
        if not self._pause_on_anomaly_fix:
            return decision
        if decision.get("action") == "emergency_stop":
            approval = await self.request_human_approval(
                decision={
                    **decision,
                    "decision_type": "anomaly_fix",
                },
                context={
                    "optimization": optimization,
                    "current_round": current_round,
                    "anomaly": anomaly,
                },
            )
            enriched = dict(decision)
            enriched["pending_approval"] = approval["pending_approval"]
            enriched["work_mode"] = self._work_mode
            return enriched

        approval = await self.request_human_approval(
            decision={
                **decision,
                "decision_type": "anomaly_fix",
            },
            context={
                "optimization": optimization,
                "current_round": current_round,
                "anomaly": anomaly,
            },
        )
        return {
            "action": "pause_for_human",
            "reason": "anomaly_fix",
            "work_mode": self._work_mode,
            "pending_approval": approval["pending_approval"],
            "original_decision": decision,
        }

    def _approval_reason_for_decision(
        self,
        *,
        decision: dict[str, Any],
        experiment_history: list[dict[str, Any]],
        current_round: int,
    ) -> str | None:
        if self._work_mode == "full_auto":
            return None
        if self._work_mode == "manual":
            return "manual_round_confirmation"

        action = decision.get("action")
        if current_round <= 1:
            return "initial_round_confirmation"
        if action == "stop":
            return "stop_decision"
        if action == "adjust_strategy" and self._pause_on_strategy_change:
            return "strategy_change"
        if self._count_no_improvement_rounds(experiment_history) >= self._max_no_improve_rounds:
            return "no_improvement_threshold"
        return None

    def _count_no_improvement_rounds(
        self,
        history: list[dict[str, Any]],
    ) -> int:
        if len(history) < 2:
            return 0

        values = [
            item.get("metrics", {})
            for item in history
            if item.get("metrics")
        ]
        if len(values) < 2:
            return 0

        metric_name = None
        for metrics in reversed(values):
            if metrics:
                metric_name = next(iter(metrics.keys()))
                break
        if metric_name is None:
            return 0

        consecutive = 0
        best_so_far: float | None = None
        for item in history:
            metrics = item.get("metrics", {})
            value = metrics.get(metric_name)
            if not isinstance(value, (int, float)):
                continue
            value_f = float(value)
            if best_so_far is None or value_f < best_so_far:
                best_so_far = value_f
                consecutive = 0
            else:
                consecutive += 1
        return consecutive

    def _fallback_decision(
        self,
        optimization: dict[str, Any],
        experiment_history: list[dict[str, Any]],
        current_result: dict[str, Any] | None,
        best_result: dict[str, Any] | None,
        current_round: int,
        error: Exception,
    ) -> dict[str, Any]:
        """Deterministic fallback when the LLM is unavailable."""
        quality = (current_result or {}).get("data_quality", {})
        metrics = (current_result or {}).get("metrics", {})
        target_metric = optimization.get("target_metric", "overpotential_mV")
        direction = optimization.get("optimization_direction", "minimize")
        current_value = metrics.get(target_metric)
        best_value = (best_result or {}).get("metrics", {}).get(target_metric)

        if quality and not quality.get("reliable", True):
            action = "continue"
            reason = "LLM 不可用，当前数据质量不足，继续收集更多实验结果"
        elif current_value is not None and best_value is not None:
            improved = (
                current_value <= best_value
                if direction == "minimize"
                else current_value >= best_value
            )
            if improved:
                action = "continue"
                reason = "LLM 不可用，但当前结果仍在改进，继续优化"
            elif len(experiment_history) >= 3:
                action = "adjust_strategy"
                reason = "LLM 不可用，近期结果未改善，建议调整搜索策略"
            else:
                action = "continue"
                reason = "LLM 不可用，历史数据仍不足，继续优化"
        else:
            action = "continue"
            reason = "LLM 不可用，采用保守策略继续下一轮"

        return {
            "action": action,
            "reason": f"{reason}（fallback: {type(error).__name__}）",
            "confidence": 0.35,
            "next_params_hint": {},
            "summary": self._build_summary(experiment_history, best_result),
        }

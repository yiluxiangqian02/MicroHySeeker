"""Orchestrator agent — closed-loop optimization coordinator.

The orchestrator is the "brain" of the multi-agent system.  It does NOT
execute experiments or analyse data itself; instead it:

1. Manages the optimization goal and search state.
2. Dispatches tasks to specialist agents (Designer → Executor → Analyst).
3. Evaluates results and decides: *continue / stop / retry / diagnose*.
4. Handles anomaly escalation from the Executor.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.agents.base import BaseAgent

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
    """Orchestrator agent — decides next action in the optimization loop."""

    def __init__(self) -> None:
        super().__init__(
            name="orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

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
            return {
                "action": "stop",
                "reason": f"已达到最大轮次 {current_round}",
                "confidence": 1.0,
                "next_params_hint": {},
                "summary": self._build_summary(experiment_history, best_result),
            }

        result = await self.invoke(task=task, context=context)
        return self._parse_decision(result.get("content", ""))

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
            return {
                "action": "emergency_stop",
                "severity": "critical",
                "reason": f"严重异常: {anomaly.get('type', 'unknown')}",
                "need_user": True,
            }

        if severity == "high":
            _logger.warning(
                "OrchestratorAgent: HIGH anomaly — dispatching to diagnostics"
            )
            return {
                "action": "diagnose",
                "severity": "high",
                "anomaly": anomaly,
                "reason": f"高级异常: {anomaly.get('type', 'unknown')}，需要诊断",
            }

        # medium / low
        _logger.info(
            "OrchestratorAgent: %s anomaly — logging and continuing", severity
        )
        return {
            "action": "log_and_continue",
            "severity": severity,
            "reason": f"低级异常: {anomaly.get('type', 'unknown')}，记录并继续",
        }

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

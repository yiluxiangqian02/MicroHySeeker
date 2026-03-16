"""Diagnostics expert agent — fault diagnosis and auto-recovery.

This agent acts as the system's "emergency doctor".  It is **not** proactive;
it only activates when the Orchestrator sends an anomaly task.

Workflow:
1. Receive anomaly report from Orchestrator.
2. Diagnose root cause (known pattern matching + LLM analysis for unknowns).
3. For known fault types, attempt automatic recovery.
4. Verify fix success via health check.
5. Report result back to Orchestrator (resolved/unresolved, can_continue).

The Diagnostics agent does NOT resume experiments — that decision belongs to
the Orchestrator, which delegates to the Executor.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.agents.base import BaseAgent

_logger = logging.getLogger("autohyseeker.diagnostics")

DIAGNOSTICS_SYSTEM_PROMPT = """\
你是故障排查 Agent（Diagnostics Expert），负责诊断和修复 MicroHySeeker 硬件系统中的异常。

## 工作流程
1. 收到 Orchestrator 发来的异常报告
2. 分析异常类型、严重程度、相关日志
3. 判断根本原因
4. 如果是已知故障模式，尝试自动修复
5. 验证修复结果
6. 返回诊断报告给 Orchestrator

## 已知故障模式
- communication_timeout: 串口通信超时 → 断开→等待→重连
- pump_error: 泵异常 → 停泵→检查→重启
- pump_speed_deviation: 转速偏差 → 重设速度
- echem_failure: 电化学仪器故障 → 需人工检查
- serial_failure: 串口连接断开 → 重连串口

## 输出格式（严格 JSON）
```json
{
  "status": "resolved|unresolved",
  "diagnosis": {
    "root_cause": "故障原因描述",
    "confidence": 0.8,
    "category": "communication|hardware|calibration|software|unknown"
  },
  "action_taken": "执行的修复操作",
  "recovery_steps": [{"step": "操作名", "result": "ok|failed"}],
  "can_continue": true,
  "recommendation": "后续建议",
  "need_human": false
}
```

## 安全规则
- 修复操作不得使任何泵超过 300 RPM
- 无法确定故障原因时，建议人工介入而非冒险操作
- 修复后必须验证系统恢复正常才能报告 can_continue=true
"""

# ── Known fault registry ──────────────────────────────────────────────────────

_KNOWN_FAULTS: dict[str, dict[str, Any]] = {
    "communication_timeout": {
        "category": "communication",
        "auto_fix": "_fix_communication",
        "max_retries": 3,
        "description": "RS485 通信超时",
    },
    "pump_error": {
        "category": "hardware",
        "auto_fix": "_fix_pump",
        "max_retries": 2,
        "description": "泵运行异常",
    },
    "pump_failure": {
        "category": "hardware",
        "auto_fix": "_fix_pump",
        "max_retries": 2,
        "description": "泵故障",
    },
    "serial_failure": {
        "category": "communication",
        "auto_fix": "_fix_communication",
        "max_retries": 3,
        "description": "串口连接故障",
    },
    "status_poll_failed": {
        "category": "communication",
        "auto_fix": "_fix_communication",
        "max_retries": 2,
        "description": "状态查询失败",
    },
}


class DiagnosticsExpertAgent(BaseAgent):
    """Diagnostics expert — fault diagnosis and auto-recovery."""

    def __init__(self) -> None:
        super().__init__(
            name="diagnostics",
            system_prompt=DIAGNOSTICS_SYSTEM_PROMPT,
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    async def diagnose_and_fix(self, task: dict[str, Any]) -> dict[str, Any]:
        """Full diagnose → fix → verify pipeline.

        Args:
            task: Dict with ``anomaly`` (required) and ``context`` (optional).

        Returns:
            Result dict with ``status``, ``diagnosis``, ``can_continue``, etc.
        """
        anomaly = task.get("anomaly", {})
        context = task.get("context", {})
        anomaly_type = anomaly.get("type", "unknown")

        _logger.info(
            "DiagnosticsExpertAgent: diagnosing anomaly type=%s severity=%s",
            anomaly_type,
            anomaly.get("severity", "unknown"),
        )

        # ── 1. Diagnose root cause ────────────────────────────────────────────
        diagnosis = await self._diagnose(anomaly, context)

        # ── 2. Check if auto-fixable ──────────────────────────────────────────
        fault_info = _KNOWN_FAULTS.get(anomaly_type)
        if fault_info is None:
            return await self._handle_unknown_fault(anomaly, diagnosis, context)

        # ── 3. Attempt auto-fix with retries ──────────────────────────────────
        fix_method_name = fault_info["auto_fix"]
        fix_method = getattr(self, fix_method_name, None)
        if fix_method is None:
            _logger.error("Fix method %s not found", fix_method_name)
            return self._build_unresolved(
                diagnosis, "修复方法未实现", [], anomaly
            )

        max_retries = fault_info["max_retries"]
        all_steps: list[dict[str, str]] = []

        for attempt in range(1, max_retries + 1):
            _logger.info(
                "DiagnosticsExpertAgent: fix attempt %d/%d via %s",
                attempt, max_retries, fix_method_name,
            )
            fix_result = await fix_method(anomaly, context)
            all_steps.extend(fix_result.get("steps", []))

            # ── 4. Verify fix ─────────────────────────────────────────────────
            if await self._verify_fix(anomaly):
                _logger.info("DiagnosticsExpertAgent: fix verified on attempt %d", attempt)
                return {
                    "status": "resolved",
                    "diagnosis": diagnosis,
                    "action_taken": fix_result.get("description", ""),
                    "recovery_steps": all_steps,
                    "can_continue": True,
                    "recommendation": diagnosis.get("recommendation", ""),
                    "attempts": attempt,
                }

            # Brief pause before retry
            if attempt < max_retries:
                await asyncio.sleep(1.0)

        # ── All retries exhausted ─────────────────────────────────────────────
        _logger.warning(
            "DiagnosticsExpertAgent: all %d fix attempts failed", max_retries
        )
        return self._build_unresolved(
            diagnosis,
            f"尝试修复 {max_retries} 次均失败",
            all_steps,
            anomaly,
        )

    # ── Private: Diagnosis ────────────────────────────────────────────────────

    async def _diagnose(
        self,
        anomaly: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Diagnose root cause — pattern match first, then LLM if needed."""
        anomaly_type = anomaly.get("type", "unknown")
        fault_info = _KNOWN_FAULTS.get(anomaly_type)

        if fault_info:
            return {
                "root_cause": fault_info["description"],
                "confidence": 0.8,
                "category": fault_info["category"],
                "recommendation": f"建议检查与 {anomaly_type} 相关的硬件和连接",
            }

        # Unknown fault → use LLM
        try:
            result = await self.invoke(
                task={
                    "type": "diagnose_anomaly",
                    "anomaly": anomaly,
                },
                context=context,
            )
            content = result.get("content", "")
            return self._parse_diagnosis(content, anomaly)
        except Exception as exc:
            _logger.warning("LLM diagnosis failed: %s", exc)
            return {
                "root_cause": f"未知故障: {anomaly.get('details', anomaly_type)}",
                "confidence": 0.3,
                "category": "unknown",
                "recommendation": "建议人工检查",
            }

    def _parse_diagnosis(
        self,
        content: str,
        anomaly: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse LLM diagnosis response."""
        import json
        import re

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                diag = parsed.get("diagnosis", parsed)
                return {
                    "root_cause": diag.get("root_cause", "LLM 分析结果"),
                    "confidence": float(diag.get("confidence", 0.5)),
                    "category": diag.get("category", "unknown"),
                    "recommendation": diag.get("recommendation", parsed.get("recommendation", "")),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        return {
            "root_cause": content[:200] if content else "无法确定",
            "confidence": 0.3,
            "category": "unknown",
            "recommendation": "建议人工检查",
        }

    # ── Private: Auto-fix strategies ──────────────────────────────────────────

    async def _fix_communication(
        self,
        anomaly: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Fix communication timeout: disconnect → wait → reconnect."""
        steps: list[dict[str, str]] = []

        try:
            from src.tools import experiment_ctrl as ctrl
        except ImportError:
            return {"steps": [{"step": "import_ctrl", "result": "failed - module unavailable"}],
                    "description": "无法加载控制模块"}

        # 1. Get current connection info
        try:
            conn = ctrl.get_connection_info()
            port = conn.get("port", "")
            baud = conn.get("baudrate", 9600)
            steps.append({"step": "get_connection_info", "result": f"port={port}"})
        except Exception as exc:
            steps.append({"step": "get_connection_info", "result": f"failed - {exc}"})
            port = ""
            baud = 9600

        # 2. Disconnect
        try:
            ctrl.disconnect_port()
            steps.append({"step": "disconnect", "result": "ok"})
        except Exception as exc:
            steps.append({"step": "disconnect", "result": f"failed - {exc}"})

        # 3. Wait
        await asyncio.sleep(2.0)
        steps.append({"step": "wait_2s", "result": "ok"})

        # 4. Reconnect
        if port:
            try:
                ctrl.connect_port(port, baud)
                steps.append({"step": "reconnect", "result": "ok"})
            except Exception as exc:
                steps.append({"step": "reconnect", "result": f"failed - {exc}"})
        else:
            steps.append({"step": "reconnect", "result": "skipped - no port info"})

        return {"steps": steps, "description": "重新建立串口连接"}

    async def _fix_pump(
        self,
        anomaly: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Fix pump error: stop pump → check → optionally restart."""
        steps: list[dict[str, str]] = []
        addr = anomaly.get("pump_address", 1)

        try:
            from src.tools import experiment_ctrl as ctrl
        except ImportError:
            return {"steps": [{"step": "import_ctrl", "result": "failed"}],
                    "description": "无法加载控制模块"}

        # 1. Stop the faulty pump
        try:
            ctrl.pump_stop(addr)
            steps.append({"step": f"stop_pump_{addr}", "result": "ok"})
        except Exception as exc:
            steps.append({"step": f"stop_pump_{addr}", "result": f"failed - {exc}"})

        # 2. Brief wait
        await asyncio.sleep(1.0)
        steps.append({"step": "wait_1s", "result": "ok"})

        # 3. Health check
        try:
            health = ctrl.health_check()
            health_status = health.get("status", "unknown")
            steps.append({"step": "health_check", "result": health_status})
        except Exception as exc:
            steps.append({"step": "health_check", "result": f"failed - {exc}"})

        return {"steps": steps, "description": f"停止并检查泵{addr}"}

    # ── Private: Verify fix ───────────────────────────────────────────────────

    async def _verify_fix(self, anomaly: dict[str, Any]) -> bool:
        """Verify that the system has recovered after a fix attempt."""
        try:
            from src.tools import experiment_ctrl as ctrl
        except ImportError:
            return False

        # Basic health check
        try:
            health = ctrl.health_check()
            if health.get("status") != "ok":
                return False
        except Exception:
            return False

        # Check connection
        try:
            conn = ctrl.get_connection_info()
            if not conn.get("connected"):
                return False
        except Exception:
            return False

        return True

    # ── Private: Unknown fault handling ───────────────────────────────────────

    async def _handle_unknown_fault(
        self,
        anomaly: dict[str, Any],
        diagnosis: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle faults not in the known registry — LLM-based analysis."""
        _logger.info("DiagnosticsExpertAgent: unknown fault type=%s", anomaly.get("type"))

        # Ask LLM for recommendation
        try:
            result = await self.invoke(
                task={
                    "type": "suggest_manual_fix",
                    "anomaly": anomaly,
                    "diagnosis": diagnosis,
                },
                context=context,
            )
            recommendation = result.get("content", "建议人工检查系统状态")
        except Exception:
            recommendation = "LLM 不可用，建议人工检查"

        return {
            "status": "unresolved",
            "diagnosis": diagnosis,
            "action_taken": "未知故障类型，无法自动修复",
            "recovery_steps": [],
            "can_continue": False,
            "need_human": True,
            "recommendation": recommendation[:500],
        }

    # ── Private: Helpers ──────────────────────────────────────────────────────

    def _build_unresolved(
        self,
        diagnosis: dict[str, Any],
        action_taken: str,
        steps: list[dict[str, str]],
        anomaly: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a standard unresolved result."""
        return {
            "status": "unresolved",
            "diagnosis": diagnosis,
            "action_taken": action_taken,
            "recovery_steps": steps,
            "can_continue": False,
            "need_human": True,
            "recommendation": diagnosis.get("recommendation", "建议人工检查"),
        }



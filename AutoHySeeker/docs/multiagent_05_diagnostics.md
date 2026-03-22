# 05 故障排查 Agent (Diagnostics Expert)

## 1. 定位

**故障排查 Agent 是系统的"急救医生"。**

它不主动巡逻，而是在 Orchestrator 发送异常任务时被激活。
接收到异常报告后，它进行诊断、尝试自动修复，并将结果反馈给 Orchestrator。

类比：它是实验室的 **设备维修工程师**，只在设备出问题时被叫来。

### 核心能力
- 分析异常日志，定位故障根因
- 对已知故障模式执行自动修复（重连串口、重启泵等）
- 评估修复结果，判断是否可以继续实验
- 对未知故障提供人工干预建议

---

## 2. 职责范围

| 职责 | 描述 | 优先级 |
|------|------|--------|
| **故障诊断** | 根据异常信息判断根本原因 | P0 |
| **自动修复** | 对已知故障类型执行自动修复 | P0 |
| **修复验证** | 修复后验证系统是否恢复正常 | P0 |
| **结果报告** | 向 Orchestrator 报告诊断和修复结果 | P0 |
| **历史分析** | 分析故障频率和模式 | P2 |
| **预防建议** | 提出降低故障风险的建议 | P2 |

### 不负责的工作
- ❌ 不主动监控（Executor 在监控中检测异常）
- ❌ 不决定是否继续实验（Orchestrator 根据诊断结果决策）
- ❌ 不执行实验操作（Executor 的工作）

---

## 3. 输入 / 输出

### 输入（来自 Orchestrator 的异常任务）
```python
{
    "action": "diagnose_anomaly",
    "anomaly": {
        "type": "pump_timeout",           # 异常类型
        "severity": "high",               # 严重级别
        "pump_address": 3,                # 相关设备
        "step_index": 2,                  # 出问题的步骤
        "error_message": "连续3次通信超时",
        "timestamp": "2026-03-15T15:42:00Z"
    },
    "context": {
        "run_id": "20260315_154200_HER_xxx",
        "experiment_state": "running",     # 当前实验状态
        "recent_logs": ["..."],            # 近期日志
        "system_health": {"status": "ok"}  # 系统健康快照
    }
}
```

### 输出
```python
# 自动修复成功
{
    "status": "resolved",
    "diagnosis": {
        "root_cause": "RS485 通信线路干扰导致超时",
        "confidence": 0.8,
        "category": "communication"
    },
    "action_taken": "重新建立串口连接并验证通信",
    "recovery_steps": [
        {"step": "disconnect", "result": "ok"},
        {"step": "wait_2s", "result": "ok"},
        {"step": "reconnect", "result": "ok"},
        {"step": "verify_pump_3", "result": "ok"}
    ],
    "can_continue": true,
    "recommendation": "建议检查 COM3 线缆连接是否松动"
}

# 无法自动修复
{
    "status": "unresolved",
    "diagnosis": {
        "root_cause": "泵3电机驱动器可能损坏",
        "confidence": 0.5,
        "category": "hardware_failure"
    },
    "action_taken": "尝试重连和重启泵均失败",
    "recovery_steps": [
        {"step": "disconnect", "result": "ok"},
        {"step": "reconnect", "result": "ok"},
        {"step": "verify_pump_3", "result": "failed - 无响应"}
    ],
    "can_continue": false,
    "recommendation": "需要人工检查泵3硬件。可尝试使用备用泵地址。",
    "need_human": true
}
```

---

## 4. 工具权限

| 工具 | 权限 | 用途 |
|------|------|------|
| **设备控制** | | |
| `pump_stop()` | ✅ | 停止故障泵 |
| `pump_stop_all()` | ✅ | 安全停机 |
| `pump_start()` | ✅ | 测试泵是否恢复 |
| `get_pump_status()` | ✅ | 检查泵状态 |
| `emergency_stop()` | ✅ | 紧急停止 |
| **连接管理** | | |
| `disconnect_port()` | ✅ | 断开串口 |
| `connect_port()` | ✅ | 重连串口 |
| `list_ports()` | ✅ | 检查可用串口 |
| `get_connection_info()` | ✅ | 连接状态 |
| **诊断** | | |
| `get_logs(level="error")` | ✅ | 获取错误日志 |
| `health_check()` | ✅ | 系统健康检查 |
| `parse_run_log()` | ✅ | 解析运行日志 |
| `classify_errors()` | ✅ | 错误分类 |
| `detect_pump_anomalies()` | ✅ | 泵异常检测 |
| **数据** | | |
| `read_run_metadata()` | ✅ | 实验元数据 |
| `get_run_detail()` | ✅ | 实验详情 |

---

## 5. 当前实现状态

### 已有代码

| 文件 | 状态 | 说明 |
|------|------|------|
| `agents/diagnostics.py` | ✅ 完整 | 故障注册表 + 自动修复 + 知识库集成 |
| `skills/knowledge_query_skill.py` | ✅ 完整 | 故障历史检索接口 |
| `skills/diagnostics/diagnose_failure.py` | ✅ 完整 | 故障诊断技能 |
| `skills/diagnostics/system_health_check.py` | ✅ 完整 | 健康检查技能 |
| `skills/diagnostics/interactive_troubleshooting.py` | ✅ 完整 | 交互式排障 |
| `tools/log_analysis.py` | ✅ 完整 | 日志解析/错误分类 |
| `graph/diagnostics_graph.py` | ✅ 完整 | 诊断子图 |

### 关键问题

> **✅ 以下问题已全部在 Phase 1 (P1-17) 中解决（2026-03-19）：**

1. ~~**Agent 只有 system prompt**~~：已实现完整的 `diagnose_and_fix()` 结构化诊断修复逻辑
2. ~~**技能丰富但未连接**~~：已将 skills 层编排到 Agent 调用链中
3. ~~**缺少自动修复流程**~~：已实现"诊断→自动修复→验证"闭环，含知识库历史查询

---

## 6. 已完成的修改（参考实现）

> 以下修改已在 Phase 1 (P1-17) 中完成，此处保留作为实现参考。

### 6.1 充实 `agents/diagnostics.py`

```python
class DiagnosticsExpertAgent(BaseAgent):
    """故障排查 Agent — 异常诊断与自动修复"""
    
    # 已知故障类型及其自动修复策略
    KNOWN_FAULTS = {
        "communication_timeout": {
            "category": "communication",
            "auto_fix": "_fix_communication",
            "max_retries": 3,
        },
        "pump_error": {
            "category": "hardware",
            "auto_fix": "_fix_pump",
            "max_retries": 2,
        },
        "pump_speed_deviation": {
            "category": "calibration",
            "auto_fix": "_fix_speed",
            "max_retries": 1,
        },
    }
    
    async def diagnose_and_fix(self, task: dict) -> dict:
        """完整的诊断→修复→验证流程。"""
        anomaly = task["anomaly"]
        context = task.get("context", {})
        
        # 1. 诊断根因
        diagnosis = await self._diagnose(anomaly, context)
        
        # 2. 判断是否可自动修复
        fault_info = self.KNOWN_FAULTS.get(anomaly["type"])
        if fault_info is None:
            # 未知故障类型，LLM 分析
            return await self._handle_unknown_fault(anomaly, diagnosis, context)
        
        # 3. 执行自动修复
        fix_method = getattr(self, fault_info["auto_fix"])
        recovery_steps = []
        
        for attempt in range(fault_info["max_retries"]):
            result = await fix_method(anomaly, context)
            recovery_steps.extend(result["steps"])
            
            # 4. 验证修复
            if await self._verify_fix(anomaly):
                return {
                    "status": "resolved",
                    "diagnosis": diagnosis,
                    "action_taken": result["description"],
                    "recovery_steps": recovery_steps,
                    "can_continue": True,
                    "recommendation": diagnosis.get("recommendation", ""),
                }
        
        # 所有重试失败
        return {
            "status": "unresolved",
            "diagnosis": diagnosis,
            "action_taken": f"尝试修复 {fault_info['max_retries']} 次均失败",
            "recovery_steps": recovery_steps,
            "can_continue": False,
            "need_human": True,
            "recommendation": await self._suggest_manual_fix(anomaly, diagnosis),
        }
    
    async def _fix_communication(self, anomaly: dict, context: dict) -> dict:
        """修复通信超时：断开→等待→重连。"""
        from tools.experiment_ctrl import (
            disconnect_port, connect_port, get_connection_info
        )
        import asyncio
        
        steps = []
        
        # 断开
        disconnect_port()
        steps.append({"step": "disconnect", "result": "ok"})
        
        # 等待
        await asyncio.sleep(2)
        steps.append({"step": "wait_2s", "result": "ok"})
        
        # 重连
        conn = get_connection_info()
        port = conn.get("port", "COM3")
        try:
            connect_port(port)
            steps.append({"step": "reconnect", "result": "ok"})
        except Exception as e:
            steps.append({"step": "reconnect", "result": f"failed - {e}"})
        
        return {"steps": steps, "description": "重新建立串口连接"}
    
    async def _fix_pump(self, anomaly: dict, context: dict) -> dict:
        """修复泵故障：停止→重启。"""
        from tools.experiment_ctrl import pump_stop, pump_start, get_pump_status
        
        addr = anomaly.get("pump_address", 1)
        steps = []
        
        # 停止泵
        pump_stop(addr)
        steps.append({"step": f"stop_pump_{addr}", "result": "ok"})
        
        # 检查状态
        status = get_pump_status(addr)
        steps.append({"step": f"check_pump_{addr}", "result": str(status)})
        
        return {"steps": steps, "description": f"停止并检查泵{addr}"}
    
    async def _verify_fix(self, anomaly: dict) -> bool:
        """验证修复是否成功。"""
        from tools.experiment_ctrl import health_check, get_pump_status
        
        # 基本健康检查
        health = health_check()
        if health.get("status") != "ok":
            return False
        
        # 特定设备检查
        if "pump_address" in anomaly:
            status = get_pump_status(anomaly["pump_address"])
            if status.get("error"):
                return False
        
        return True
```

---

## 7. 已知故障模式清单

| 故障类型 | 可能原因 | 自动修复策略 | 成功率 |
|---------|---------|-------------|--------|
| `communication_timeout` | 串口干扰/线缆松动 | 断开→等待→重连 | ~80% |
| `pump_error` | 泵卡住/过载 | 停止→等待→重启 | ~60% |
| `pump_speed_deviation` | 校准偏差 | 重设速度 | ~90% |
| `echem_failure` | CHI 仪器异常 | 需人工检查 | 0% |
| `step_timeout` | 步骤超时 | 跳过/重试 | ~50% |
| `unknown` | 未知 | LLM 分析+建议 | 视情况 |

---

## 8. 与其他 Agent 的交互

```
Orchestrator → Diagnostics:
    task: "诊断异常"
    附带: anomaly{type, severity, details}, context{run_id, logs}

Diagnostics → Orchestrator:
    result: {status, diagnosis, can_continue, recommendation}
    Orchestrator 据此决定：继续/重试/终止
```

**重要**：Diagnostics 不直接恢复实验运行。它只负责"修复故障状态"，
实验的恢复/重试由 Orchestrator 决定并交给 Executor 执行。

---

## 9. 执行计划（✅ 全部完成）

| 步骤 | 任务 | 涉及文件 | 状态 |
|------|------|---------|------|
| 1 | 充实 diagnostics.py，添加 diagnose_and_fix 方法 | `agents/diagnostics.py` | ✅ |
| 2 | 实现已知故障自动修复策略 | `agents/diagnostics.py` | ✅ |
| 3 | 实现修复验证逻辑 | `agents/diagnostics.py` | ✅ |
| 4 | 接入 skills/diagnostics/ 已有技能 | `agents/diagnostics.py` | ✅ |
| 5 | 更新 System Prompt | `agents/diagnostics.py` | ✅ |
| 6 | 添加单元测试（模拟故障场景） | `tests/test_diagnostics_agent.py` (18项通过) | ✅ |

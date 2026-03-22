# 03 实验执行 Agent (Experiment Executor)

## 1. 定位

**实验执行 Agent 是系统中唯一直接操作硬件的 Agent。**

它接收实验参数（来自 Designer 经 Orchestrator 转发），通过 MicroHySeeker API 
执行实验、实时监控进度、检测异常，并在实验完成后收集数据。

类比：它是实验室的 **实验操作员**，严格按照方案操作仪器并记录。

### 核心能力
- 通过模板实例化 API 启动实验
- 实时轮询实验状态
- 检测硬件异常（泵故障、通信超时等）
- 实验完成后收集数据文件
- 紧急情况下执行安全停机

---

## 2. 职责范围

| 职责 | 描述 | 优先级 |
|------|------|--------|
| **实验启动** | 调用 instantiate API 启动实验 | P0 |
| **状态监控** | 轮询实验状态直到完成 | P0 |
| **异常检测** | 识别硬件异常并上报 | P0 |
| **安全停机** | 紧急情况执行 emergency_stop | P0 |
| **数据收集** | 实验完成后获取数据路径 | P0 |
| **预检查** | 实验前检查系统健康状态 | P1 |
| **设备控制** | 手动操作泵/清洗/配液 | P1 |

### 不负责的工作
- ❌ 不设计实验参数（Designer 的工作）
- ❌ 不分析实验数据（Analyst 的工作）
- ❌ 不做策略决策（Orchestrator 的工作）

---

## 3. 输入 / 输出

### 输入（来自 Orchestrator 的任务）
```python
{
    "action": "execute_experiment",
    "template_id": "tpl_her_standard",
    "step_overrides": {
        "0": {
            "prep_sol_params": {
                "target_concentrations": {"Fe": 0.6, "Co": 0.25, "Ni": 0.15},
                "total_volume_ul": 1000
            }
        }
    },
    "exp_name": "HER_Fe6Co25Ni15_round_3",
    "pre_check": true,        # 是否执行预检查
    "monitor_interval_s": 5   # 状态轮询间隔
}
```

### 输出
```python
# 成功
{
    "status": "completed",
    "run_id": "20260315_154200_HER_Fe6Co25Ni15",
    "duration_s": 180.5,
    "data_path": "data/2026-03-15/20260315_154200_HER_Fe6Co25Ni15/",
    "steps_completed": 5,
    "steps_total": 5,
    "anomalies": []    # 执行过程中的异常（即使完成也可能有警告）
}

# 失败
{
    "status": "failed",
    "run_id": "20260315_154200_HER_Fe6Co25Ni15",
    "error": "Pump 3 communication timeout at step 2",
    "anomaly": {
        "type": "pump_timeout",
        "severity": "high",
        "step_index": 2,
        "pump_address": 3,
        "details": "连续3次通信超时"
    },
    "steps_completed": 2,
    "steps_total": 5
}
```

---

## 4. 工具权限

| 工具 | 权限 | 用途 |
|------|------|------|
| **实验控制** | | |
| `start_experiment()` | ✅ | 启动实验 |
| `stop_experiment()` | ✅ | 停止实验 |
| `pause_experiment()` | ✅ | 暂停实验 |
| `resume_experiment()` | ✅ | 恢复实验 |
| `get_experiment_status()` | ✅ | 查询状态 |
| **设备控制** | | |
| `pump_start()` | ✅ | 启动泵 |
| `pump_stop()` | ✅ | 停止泵 |
| `pump_stop_all()` | ✅ | 停止所有泵 |
| `get_pump_status()` | ✅ | 泵状态 |
| `flusher_start()` | ✅ | 清洗 |
| `flusher_stop()` | ✅ | 停止清洗 |
| `diluter_start()` | ✅ | 配液 |
| `diluter_stop()` | ✅ | 停止配液 |
| `emergency_stop()` | ✅ | 紧急停止 |
| **模板** | | |
| `instantiate_template()` | ✅ | 实例化并运行 |
| `validate_experiment()` | ✅ | 验证参数 |
| **系统** | | |
| `health_check()` | ✅ | 健康检查 |
| `get_logs(level)` | ✅ | 日志查询 |
| `list_ports()` | ✅ | 串口列表 |
| `connect_port()` | ✅ | 连接串口 |

---

## 5. 当前实现状态

### 已有代码

| 文件 | 状态 | 说明 |
|------|------|------|
| `agents/exp_executor.py` | ✅ 完整 | 实验执行 + L1/L2 两层监控集成 |
| `skills/realtime_monitor_skill.py` | ✅ 完整 | L1 规则引擎（6 条规则） |
| `skills/heartbeat_inspector_skill.py` | ✅ 完整 | L2 心跳巡检（LLM 综合判断） |
| `tools/experiment_ctrl.py` | ✅ 完整 | 全部 API 客户端函数 |
| `api/routes/monitor.py` | ✅ 完整 | 监控控制路由（toggle/status/config） |

### 关键洞察

> **✅ 以下迁移已全部在 Phase 1 (P1-09, P1-10) 中完成（2026-03-19）：**

原 `ExperimentSupervisorAgent` 已移除。监控循环、异常检测、状态轮询等逻辑已迁移到 `exp_executor.py`，并集成了 L1 (RealtimeMonitorSkill) 和 L2 (HeartbeatInspectorSkill) 两层监控。

---

## 6. 已完成的新增内容（参考实现）

> 以下新增已在 Phase 1 中完成，此处保留作为实现参考。

### 6.1 创建 `agents/exp_executor.py`

```python
class ExperimentExecutorAgent(BaseAgent):
    """实验执行 Agent — 实验生命周期管理"""
    
    def __init__(self):
        super().__init__(
            name="experiment_executor",
            system_prompt=EXECUTOR_SYSTEM_PROMPT,
        )
        self._monitoring = False
        self._current_run_id = None
    
    async def execute_experiment(self, task: dict) -> dict:
        """执行完整的实验流程：预检查 → 启动 → 监控 → 收集。"""
        
        # 1. 预检查
        if task.get("pre_check", True):
            health = await self._pre_check()
            if not health["ok"]:
                return {"status": "pre_check_failed", "error": health["error"]}
        
        # 2. 验证参数
        validation = await self._validate_params(task)
        if not validation["valid"]:
            return {"status": "validation_failed", "errors": validation["errors"]}
        
        # 3. 实例化并启动实验
        try:
            result = await self._start_experiment(task)
            self._current_run_id = result.get("run_id")
        except Exception as e:
            return {"status": "start_failed", "error": str(e)}
        
        # 4. 监控实验直到完成
        monitor_result = await self._monitor_until_complete(
            interval_s=task.get("monitor_interval_s", 5)
        )
        
        # 5. 收集结果数据
        if monitor_result["status"] == "completed":
            data = await self._collect_data(self._current_run_id)
            monitor_result["data_path"] = data.get("data_path")
        
        return monitor_result
    
    async def _pre_check(self) -> dict:
        """执行前检查系统健康状态。"""
        from tools.experiment_ctrl import health_check, get_connection_info
        
        health = health_check()
        if health.get("status") != "ok":
            return {"ok": False, "error": "系统健康检查失败"}
        
        conn = get_connection_info()
        if not conn.get("connected"):
            return {"ok": False, "error": "RS485 未连接"}
        
        return {"ok": True}
    
    async def _validate_params(self, task: dict) -> dict:
        """验证实验参数。"""
        from tools.experiment_ctrl import validate_experiment
        
        # dry_run 模式验证
        result = instantiate_template(
            template_id=task["template_id"],
            overrides={"step_overrides": task.get("step_overrides", {})},
            dry_run=True,
        )
        
        if result.get("status") == "validation_failed":
            return {"valid": False, "errors": result.get("errors", [])}
        
        return {"valid": True}
    
    async def _start_experiment(self, task: dict) -> dict:
        """启动实验。"""
        from tools.experiment_ctrl import instantiate_template
        
        result = instantiate_template(
            template_id=task["template_id"],
            overrides={"step_overrides": task.get("step_overrides", {})},
            exp_name=task.get("exp_name"),
            dry_run=False,
        )
        
        if result.get("status") != "started":
            raise RuntimeError(f"实验启动失败: {result}")
        
        return result
    
    async def _monitor_until_complete(self, interval_s: float = 5) -> dict:
        """轮询监控实验直到完成或异常。"""
        import asyncio
        from tools.experiment_ctrl import get_experiment_status, get_logs
        
        self._monitoring = True
        anomalies = []
        
        while self._monitoring:
            status = get_experiment_status()
            state = status.get("state", "unknown")
            
            if state == "idle":
                # 实验完成
                return {
                    "status": "completed",
                    "run_id": self._current_run_id,
                    "steps_completed": status.get("steps_completed", 0),
                    "steps_total": status.get("steps_total", 0),
                    "anomalies": anomalies,
                }
            
            if state == "error":
                return {
                    "status": "failed",
                    "run_id": self._current_run_id,
                    "error": status.get("error_message", "unknown error"),
                    "anomaly": self._classify_error(status),
                }
            
            # 检查警告日志
            warnings = get_logs(n=10, level="warning")
            new_anomalies = self._detect_anomalies(warnings, status)
            if new_anomalies:
                anomalies.extend(new_anomalies)
                # 严重异常上报
                for a in new_anomalies:
                    if a["severity"] in ("high", "critical"):
                        self._monitoring = False
                        return {
                            "status": "failed",
                            "run_id": self._current_run_id,
                            "anomaly": a,
                            "anomalies": anomalies,
                        }
            
            await asyncio.sleep(interval_s)
        
        return {"status": "stopped", "run_id": self._current_run_id}
    
    def stop_monitoring(self):
        """外部调用停止监控。"""
        self._monitoring = False
    
    def _detect_anomalies(self, log_entries: list, status: dict) -> list:
        """从日志和状态中检测异常。"""
        anomalies = []
        
        for entry in log_entries.get("logs", []):
            if "timeout" in entry.lower():
                anomalies.append({
                    "type": "communication_timeout",
                    "severity": "medium",
                    "details": entry,
                })
            elif "error" in entry.lower() and "pump" in entry.lower():
                anomalies.append({
                    "type": "pump_error",
                    "severity": "high",
                    "details": entry,
                })
        
        return anomalies
    
    def _classify_error(self, status: dict) -> dict:
        """将错误状态分类。"""
        error_msg = status.get("error_message", "")
        
        if "pump" in error_msg.lower():
            return {"type": "pump_failure", "severity": "high", "details": error_msg}
        elif "timeout" in error_msg.lower():
            return {"type": "timeout", "severity": "medium", "details": error_msg}
        elif "chi" in error_msg.lower() or "echem" in error_msg.lower():
            return {"type": "echem_failure", "severity": "high", "details": error_msg}
        else:
            return {"type": "unknown", "severity": "medium", "details": error_msg}
```

### 6.2 System Prompt

```python
EXECUTOR_SYSTEM_PROMPT = """你是实验执行 Agent，负责通过 MicroHySeeker 硬件系统执行电化学实验。

## 工作流程
1. 执行预检查：确认系统健康、串口连接正常
2. 验证参数：通过 dry_run 模式确认参数合法
3. 启动实验：调用模板实例化 API
4. 监控进度：轮询实验状态，检测异常
5. 收集数据：实验完成后获取数据路径

## 安全规则（最高优先级）
- 所有泵转速不得超过 300 RPM
- 检测到高严重度异常时必须立即上报
- 检测到 CRITICAL 异常时必须执行紧急停止
- 不确定的操作宁可停止也不冒险继续

## 异常分类
- LOW: 记录日志，继续执行
- MEDIUM: 上报 Orchestrator，等待指示
- HIGH: 停止当前步骤，上报 Orchestrator
- CRITICAL: 执行 emergency_stop，立即上报
"""
```

---

## 7. 与其他 Agent 的交互

```
Orchestrator → Executor:
    task: "执行实验"
    附带: template_id, step_overrides, exp_name

Executor → Orchestrator:
    result: "实验完成" / alert: "检测到异常"
    附带: run_id, data_path, anomalies, duration_s

Orchestrator → Executor:
    task: "暂停/恢复/停止实验"（Orchestrator 的紧急指令）

Executor → Diagnostics:  ❌ (不直接通信，通过 Orchestrator 中转)
```

---

## 8. 关键工作流

### 工作流: 完整实验执行

```
Executor 收到任务
    │
    ├─ 1. 预检查
    │   ├─ health_check() → 确认系统正常
    │   ├─ get_connection_info() → 确认串口连接
    │   └─ 失败 → 返回 pre_check_failed
    │
    ├─ 2. 参数验证
    │   ├─ instantiate_template(dry_run=true) → 验证参数
    │   └─ 失败 → 返回 validation_failed
    │
    ├─ 3. 启动实验
    │   ├─ instantiate_template(dry_run=false) → 启动
    │   └─ 失败 → 返回 start_failed
    │
    ├─ 4. 监控循环
    │   ├─ 每 5s 轮询 get_experiment_status()
    │   ├─ 每 5s 检查 get_logs(level="warning")
    │   ├─ 检测到 LOW 异常 → 记录，继续
    │   ├─ 检测到 MEDIUM 异常 → 上报 Orchestrator
    │   ├─ 检测到 HIGH 异常 → 停止步骤，上报
    │   ├─ 检测到 CRITICAL → emergency_stop()
    │   └─ state == "idle" → 实验完成
    │
    └─ 5. 数据收集
        ├─ get_run_detail(run_id) → 获取数据路径
        └─ 返回 completed + data_path
```

---

## 9. 从 ExperimentSupervisor 迁移（✅ 已完成）

> 以下迁移已全部完成，`exp_supervisor.py` 已移除。

| 原位置 (exp_supervisor.py) | 迁移到 | 状态 |
|---------------------------|--------|------|
| `_monitor_experiment_loop()` | exp_executor.py | ✅ |
| `_poll_status()` | exp_executor.py | ✅ |
| `_check_anomalies()` | exp_executor.py | ✅ |
| 异常严重度分类 | exp_executor.py | ✅ |
| Agent 协调/调度 | orchestrator.py | ✅ |
| `_dispatch_to_analyst()` | orchestrator.py | ✅ |
| `_dispatch_to_diagnostics()` | orchestrator.py | ✅ |

---

## 10. 执行计划（✅ 全部完成）

| 步骤 | 任务 | 涉及文件 | 状态 |
|------|------|---------|------|
| 1 | 创建 exp_executor.py 基础框架 | `agents/exp_executor.py` | ✅ |
| 2 | 迁移监控逻辑 | `agents/exp_executor.py` | ✅ |
| 3 | 实现预检查流程 | `agents/exp_executor.py` | ✅ |
| 4 | 实现异常检测和分类 | `agents/exp_executor.py` | ✅ |
| 5 | 注册到 graph nodes | `graph/nodes.py` | ✅ |
| 6 | 移除 exp_supervisor.py | ~~`agents/exp_supervisor.py`~~ 已删除 | ✅ |
| 7 | 添加集成测试 | `tests/test_executor_agent.py` (23项通过) | ✅ |

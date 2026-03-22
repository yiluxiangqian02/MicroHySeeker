# 01 运行管控 Agent (Orchestrator)

> **最后更新：2026-03-22 — Phase 1 全部实现完成**

## 1. 定位

**运行管控 Agent 是整个 Multi-Agent 系统的大脑。**

它不直接执行任何实验操作，而是作为 **调度中心** 负责：
- 接收用户优化目标
- 将任务分配给专业 Agent
- 跟踪优化进度
- 做出"下一步做什么"的决策
- 异常时协调故障排查
- **通过内置 Skill 完成数据分析和知识管理**（Phase 10 新增）

类比：它是实验室的 **项目负责人 (PI)**，指挥但不亲自操作。

### 内置 Skill（Phase 10 新增）

| Skill | 文件 | 功能 |
|-------|------|------|
| `DataAnalysisSkill` | `skills/data_analysis_skill.py` | 电化学指标提取、质量评估、历史对比 |
| `KnowledgeArchiveSkill` | `skills/knowledge_archive_skill.py` | 实验归档、文献/历史检索 |

这两个 Skill 原为独立 Agent（DataAnalystAgent、KnowledgeManagerAgent），
因其逻辑为确定性/模板化操作（无需独立 LLM 推理），已转为 Orchestrator 的内置技能。

---

## 2. 职责范围

| 职责 | 描述 | 优先级 |
|------|------|--------|
| **目标管理** | 解析用户的优化目标（如"找到最优 Fe:Co:Ni 配比"） | P0 |
| **任务调度** | 决定何时调用 Designer/Executor/Analyst | P0 |
| **进度跟踪** | 维护 OptimizationState，记录每轮结果 | P0 |
| **决策判断** | 判断是否继续优化、调整策略、或终止 | P0 |
| **异常处理** | 收到异常后决定：忽略/调查/停止 | P0 |
| **用户交互** | 接收用户指令、报告进展 | P1 |
| **紧急停止** | 在严重异常时执行 emergency_stop | P0 |

### 不负责的工作
- ❌ 不生成实验参数（Designer 的工作）
- ❌ 不执行实验（Executor 的工作）
- ❌ 不诊断故障（Diagnostics 的工作）

> 注意：数据分析和知识管理现在由 Orchestrator 内置 Skill 完成，不再是独立 Agent。

---

## 3. 输入 / 输出

### 输入
```python
# 用户发起优化任务
{
    "goal": "优化 Fe-Co-Ni 三元催化剂的 HER 性能",
    "target_metric": "overpotential",
    "optimization_direction": "minimize",
    "search_space": {
        "Fe": {"min": 0.0, "max": 1.0},
        "Co": {"min": 0.0, "max": 1.0},
        "Ni": {"min": 0.0, "max": 1.0}
    },
    "constraints": {
        "sum_equals": 1.0,           # 各元素比例之和 = 1
        "min_component": 0.05        # 每个元素至少 5%
    },
    "max_rounds": 20,
    "template_id": "tpl_her_standard",
    "total_volume_ul": 1000
}
```

### 输出
```python
# 优化完成报告
{
    "status": "completed",
    "best_params": {"Fe": 0.3, "Co": 0.5, "Ni": 0.2},
    "best_metric": {"overpotential_mV": 182.5},
    "total_rounds": 12,
    "all_results": [...],  # 所有实验的结果摘要
    "conclusion": "LLM 生成的结论文本",
    "recommendations": ["建议进一步探索 Co > 0.4 区间"]
}
```

---

## 4. 工具权限

| 工具 | 权限 | 用途 |
|------|------|------|
| `emergency_stop()` | ✅ | 紧急情况直接停机 |
| `get_experiment_status()` | ✅ | 监控实验进展 |
| `health_check()` | ✅ | 系统健康检查 |
| `get_logs(level="warning")` | ✅ | 获取警告日志 |
| `list_templates()` | ✅ | 查看可用模板 |
| `get_system_config()` | ✅ | 了解系统能力 |
| `generate_run_report()` | ✅ | 生成最终报告 |

---

## 5. 当前实现状态

### 已有代码

| 文件 | 状态 | 说明 |
|------|------|------|
| `graph/orchestrator.py` | ✅ 完整 | LangGraph 图构建 — 4 Agent 节点 + 回退机制 |
| `graph/nodes.py` | ✅ 完整 | 路由节点 + _AGENT_ALIASES 向后兼容 |
| `graph/state.py` | ✅ 基础 | AutoHySeekerState TypedDict |
| `agents/orchestrator.py` | ✅ 完整 | 决策/异常处理 + DataAnalysisSkill + KnowledgeArchiveSkill |
| `skills/data_analysis_skill.py` | ✅ 完整 | 指标提取、质量评估、历史对比 |
| `skills/knowledge_archive_skill.py` | ✅ 完整 | 归档、检索、文献知识 |

### 问题分析

> **✅ 以下问题已全部在 Phase 1 (P1-13~P1-15) 中解决（2026-03-19）：**

1. ~~**exp_supervisor 职责过重**~~：已拆分为 Orchestrator（调度） + Executor（执行），ExperimentSupervisorAgent 已移除
2. ~~**路由是关键词匹配**~~：已增强为多层路由（优化状态路由 + 意图关键词 + ChatAgent 兼容别名）
3. ~~**缺少闭环状态**~~：`OptimizationLoop` 已实现完整优化进度追踪，含 `pending_approval` 暂停/恢复
4. ~~**缺少决策逻辑**~~：`evaluate_and_decide()` 已实现，支持 continue/stop/retry/adjust_strategy

---

## 6. 已完成的修改（参考实现）

> 以下所有修改已在 Phase 1 中完成，此处保留作为实现参考。

### 6.1 重构 `graph/state.py` — 扩展状态定义

```python
# 在现有 AutoHySeekerState 基础上扩展
class AutoHySeekerState(TypedDict):
    messages: list
    current_agent: str
    task: dict
    context: dict
    error: Optional[str]
    result: Optional[dict]
    
    # 🆕 新增优化状态字段
    optimization: Optional[dict]     # OptimizationState 序列化
    experiment_history: list[dict]   # 已完成实验列表
    current_round: int               # 当前轮次
    best_result: Optional[dict]      # 最优结果
```

### 6.2 重构 `graph/nodes.py` — 增强路由

```python
# 当前: 关键词匹配
def route_intent(state):
    text = state["task"]["prompt"].lower()
    if "cv" in text or "eis" in text:
        return "data_analyst"
    ...

# 目标: 加入优化循环路由
def route_intent(state):
    # 1. 如果在优化循环中，按状态路由
    opt = state.get("optimization")
    if opt and opt["status"] != "completed":
        return _route_optimization_step(opt)
    
    # 2. 否则用 LLM 或关键词路由
    return _infer_agent(state)

def _route_optimization_step(opt):
    """根据优化状态决定下一个 Agent"""
    status = opt["status"]
    if status == "idle" or status == "need_design":
        return "exp_designer"
    elif status == "need_execute":
        return "exp_executor"
    elif status == "need_analyze":
        return "data_analyst"
    elif status == "need_diagnose":
        return "diagnostics"
    elif status == "evaluating":
        return "orchestrator"  # 回到自身做决策
```

### 6.3 重构 `agents/exp_supervisor.py` → `agents/orchestrator.py`

将现有 `ExperimentSupervisorAgent` 中的 **调度逻辑** 提取为 Orchestrator，
将 **执行逻辑** 移入新的 Executor。

保留的部分（移入 Orchestrator）：
- 异常严重度评估逻辑
- Agent 协调调度
- 状态管理

移出的部分（移入 Executor）：
- `_monitor_experiment_loop()` 
- `_poll_status()` 
- 直接的 API 调用

---

## 7. 已完成的新增内容（参考实现）

> 以下所有新增已在 Phase 1 中完成，此处保留作为实现参考。

### 7.1 闭环决策方法

```python
class OrchestratorAgent(BaseAgent):
    """运行管控 Agent — 闭环优化调度器"""
    
    async def evaluate_and_decide(self, state: dict) -> dict:
        """评估当前轮次结果，决定下一步动作。
        
        Returns:
            {"action": "continue|stop|retry|adjust_strategy",
             "reason": "...",
             "next_params_hint": {...}}  # 可选的方向提示
        """
        history = state["experiment_history"]
        current_result = state.get("result")
        best = state.get("best_result")
        
        # 构建 LLM prompt
        prompt = self._build_decision_prompt(
            goal=state["optimization"]["goal"],
            history=history,
            current=current_result,
            best=best,
            round_num=state["current_round"],
            max_rounds=state["optimization"]["max_rounds"],
        )
        
        decision = await self.invoke(prompt)
        return self._parse_decision(decision)
    
    async def handle_anomaly(self, anomaly: dict, state: dict) -> dict:
        """处理异常报告，决定升级路径。"""
        severity = anomaly.get("severity", "medium")
        
        if severity == "critical":
            # 直接紧急停止
            await emergency_stop()
            return {"action": "emergency_stopped", "need_user": True}
        
        if severity == "high":
            # 交给 Diagnostics 处理
            return {"action": "diagnose", "anomaly": anomaly}
        
        # medium/low: 记录并继续
        return {"action": "log_and_continue", "anomaly": anomaly}
```

### 7.2 优化循环子图 (`graph/optimization_loop.py`)

```python
def build_optimization_subgraph():
    """构建闭环优化子图。
    
    START → design → execute → analyze → evaluate → {
        continue → design (循环)
        stop → report → END
        retry → execute (重试)
        diagnose → diagnostics → evaluate (异常处理)
    }
    """
    graph = StateGraph(AutoHySeekerState)
    
    graph.add_node("design", run_designer)
    graph.add_node("execute", run_executor)
    graph.add_node("analyze", run_analyst)
    graph.add_node("evaluate", run_orchestrator_decide)
    graph.add_node("diagnose", run_diagnostics)
    graph.add_node("report", generate_final_report)
    
    graph.add_edge(START, "design")
    graph.add_edge("design", "execute")
    graph.add_edge("execute", "analyze")
    graph.add_edge("analyze", "evaluate")
    
    # 条件路由
    graph.add_conditional_edges("evaluate", route_decision, {
        "continue": "design",
        "stop": "report",
        "retry": "execute",
        "diagnose": "diagnose",
    })
    
    graph.add_edge("diagnose", "evaluate")
    graph.add_edge("report", END)
    
    return graph.compile()
```

---

## 8. 与其他 Agent / Skill 的交互

```
Orchestrator ──task──▶ Designer
    "设计下一组实验参数，搜索空间: {...}，历史结果: [...]"

Orchestrator ──task──▶ Executor
    "执行实验，模板: tpl_xxx，参数覆盖: {concentrations: {...}}"

Orchestrator ──skill──▶ DataAnalysisSkill (内置)
    analyze_experiment(run_id, data_path, params, target_metric, best_result)

Orchestrator ──task──▶ Diagnostics
    "诊断异常: {type: 'pump_timeout', pump_addr: 3, error_msg: '...'}"

Orchestrator ──skill──▶ KnowledgeArchiveSkill (内置)
    archive_experiment(run_id, params, metrics, interpretation)
    retrieve_knowledge(query, search_type, top_k)

Designer ──result──▶ Orchestrator
    {params: {Fe: 0.3, Co: 0.5, Ni: 0.2}, strategy: "bayesian", confidence: 0.8}

Executor ──result──▶ Orchestrator
    {status: "completed", run_id: "xxx", duration_s: 120}

Executor ──alert──▶ Orchestrator
    {severity: "medium", type: "pump_speed_deviation", details: {...}}

Diagnostics ──result──▶ Orchestrator
    {resolved: true, action_taken: "重启串口连接", recommendation: "检查 COM3 线缆"}
```

---

## 9. 执行计划（✅ 全部完成）

| 步骤 | 任务 | 涉及文件 | 状态 |
|------|------|---------|------|
| 1 | 扩展 `AutoHySeekerState` 加入优化字段 | `graph/state.py` | ✅ |
| 2 | 创建 `OrchestratorAgent` 类 | `agents/orchestrator.py` | ✅ |
| 3 | 创建优化循环子图 | `graph/optimization_loop.py` | ✅ |
| 4 | 重构路由节点支持优化状态 | `graph/nodes.py` | ✅ |
| 5 | 更新主图注册优化子图 | `graph/orchestrator.py` | ✅ |
| 6 | 将 exp_supervisor 的调度逻辑迁移 | ~~`agents/exp_supervisor.py`~~ 已移除 | ✅ |
| 7 | 添加集成测试 | `tests/test_orchestrator_agent.py` (24项通过) | ✅ |

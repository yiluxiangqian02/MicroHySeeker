# Agent C — ExperimentSupervisor 开发指南

> 代号：ES | 优先级：P1 (Week 3-4) | 域：实验执行与监控
> 总体架构参考：[`langgraph_architecture.md`](langgraph_architecture.md) | Tool/Skill定义参考：[`skills_architecture.md`](skills_architecture.md)

---

## 一、Agent 概览

### 1.1 职责定位

ExperimentSupervisor 是整个系统的**核心枢纽** — 它负责：

```
接收实验需求/方案 → 校验 → 排程 → 执行 → 监控 → 保存结果
                                          ↓ (出错时)
                                    调用 DiagnosticsExpert
                                          ↓
                                  根据诊断决策：重试 / 跳过 / 中止
                                          ↓ (重试)
                                       继续执行
```

**这是用户描述的核心目标**：
> "C 能够根据各种需求/B的规划自动调用 MicroHySeeker 做实验，并监控运行过程，保存实验结果；如果运行过程有问题，可以决策是否使用 D 来进行分析，诊断并维修；然后再继续进行实验"

### 1.2 拥有的 Skills

| Skill | 名称 | 阶段 | 输入 | 输出 |
|-------|------|------|------|------|
| **C1** | `execution_monitor` | P1:后分析 / P4:实时 | run_dir 或实时流 | 每步质量评分+汇总 |
| **C2** | `smart_scheduler` | P1 | 实验列表+约束 | 优化排程 |
| **C3** | `adaptive_experiment_loop` | P4 | 目标+初始方案 | 优化结果+收敛历史 |

### 1.3 跨 Agent 协作

```
ExperimentDesigner (B) ──方案JSON──→ ExperimentSupervisor (C)
                                           │
                                     执行+监控
                                           │
                                     出错? ─┤
                                     │      │
                                     ▼      ▼
                              DiagnosticsExpert (D)
                                     │
                                  诊断结果
                                     │
                              决策: retry/skip/abort
                                     │
                              ←──────┘
                                     │
                              (P4: 自适应模式)
                                     │
                              DataAnalyst (A) ── 分析中间结果
                                     │
                              ExperimentDesigner (B) ── 生成新方案
                                     │
                              ←──── 循环 ────→
```

---

## 二、LangGraph Subgraph 设计（★ 核心）

### 2.1 State 定义

```python
class SupervisorState(TypedDict):
    """实验执行管家 — 最复杂的 State"""
    messages: Annotated[list[BaseMessage], add_messages]
    
    # === 输入 ===
    experiment_plan: dict              # 实验方案 JSON (来自 B 或用户)
    execution_mode: Literal[
        "post_analysis",    # Phase 1: 读已有数据（模拟）
        "single_run",       # Phase 4: 执行一次实验
        "adaptive_loop",    # Phase 4: C3 自适应闭环
    ]
    
    # === 排程 ===
    schedule: list[dict]               # [{order, plan, estimated_duration, ...}]
    
    # === 执行跟踪 ===
    status: Literal[
        "validating", "scheduling", "executing", "monitoring",
        "diagnosing", "deciding", "saving", "completed", "aborted"
    ]
    current_step_index: int
    total_steps: int
    
    # === 各步骤结果 ===
    step_results: list[dict]           # [{step_index, status, quality_score, data, ...}]
    current_step_data: dict | None     # 当前步骤的执行数据
    
    # === 质量监控 (C1) ===
    quality_scores: list[float]        # 每步质量评分
    overall_quality: float | None
    alerts: list[dict]                 # 触发的告警
    
    # === 错误处理 (C→D) ===
    error_info: dict | None            # 当前错误 {step_index, error_type, error_msg, ...}
    diagnosis_result: dict | None      # D 的诊断结果
    decision: str | None               # "retry" | "skip" | "abort"
    retry_count: int
    max_retries: int                   # 默认 2
    
    # === 产出 ===
    run_dir: str | None                # 实验数据目录
    final_report: str | None           # 实验质量报告 (Markdown)
    
    # === C3 自适应 (Phase 4) ===
    objective: str | None              # 优化目标
    iteration: int                     # 当前迭代轮次
    max_iterations: int
    convergence_history: list[dict]
```

### 2.2 Graph 定义

```python
def build_supervisor_graph():
    graph = StateGraph(SupervisorState)
    
    # === 节点 ===
    graph.add_node("validate_plan", validate_plan_node)
    graph.add_node("schedule", schedule_node)
    graph.add_node("execute_step", execute_step_node)
    graph.add_node("monitor_step", monitor_step_node)
    graph.add_node("handle_success", handle_success_node)
    graph.add_node("diagnose_failure", diagnose_failure_node)
    graph.add_node("decide_action", decide_action_node)
    graph.add_node("save_results", save_results_node)
    graph.add_node("generate_report", generate_report_node)
    
    # === 边 ===
    graph.add_edge(START, "validate_plan")
    
    graph.add_conditional_edges("validate_plan", check_plan_valid, {
        "valid": "schedule",
        "invalid": END,
    })
    
    graph.add_edge("schedule", "execute_step")
    graph.add_edge("execute_step", "monitor_step")
    
    graph.add_conditional_edges("monitor_step", check_step_result, {
        "success": "handle_success",
        "failure": "diagnose_failure",
    })
    
    graph.add_conditional_edges("handle_success", check_more_steps, {
        "more": "execute_step",
        "done": "save_results",
    })
    
    graph.add_edge("diagnose_failure", "decide_action")
    
    graph.add_conditional_edges("decide_action", get_decision, {
        "retry": "execute_step",
        "skip": "handle_success",    # skip = 当做成功跳过
        "abort": "save_results",
    })
    
    graph.add_edge("save_results", "generate_report")
    graph.add_edge("generate_report", END)
    
    return graph.compile()
```

### 2.3 Graph 可视化

```
    START
      │
      ▼
 ┌──────────┐
 │ validate  │──invalid──→ END (返回校验错误)
 │ plan      │
 └────┬──────┘
   valid
      │
 ┌────▼──────┐
 │ schedule  │
 └────┬──────┘
      │
 ┌────▼──────────┐ ◄─── retry ────────────┐
 │ execute_step  │                          │
 └────┬──────────┘                          │
      │                                     │
 ┌────▼──────────┐                          │
 │ monitor_step  │                          │
 └──┬─────────┬──┘                          │
 success   failure                          │
    │         │                             │
    │    ┌────▼──────────┐                  │
    │    │ diagnose      │ ← 调用 D Agent   │
    │    │ failure       │                  │
    │    └────┬──────────┘                  │
    │         │                             │
    │    ┌────▼──────────┐                  │
    │    │ decide_action │ ← LLM 决策       │
    │    └──┬────┬────┬──┘                  │
    │   retry skip  abort                   │
    │     │    │      │                     │
    │     └────┼──────┼─────────────────────┘
    │          │      │
 ┌──▼──────────▼┐     │
 │ handle       │     │
 │ success      │     │
 └──┬────────┬──┘     │
  more     done       │
    │        │        │
    │   ┌────▼────────▼──┐
    │   │ save_results   │
    │   └────┬───────────┘
    │        │
    │   ┌────▼───────────┐
    │   │generate_report │
    │   └────┬───────────┘
    │        │
    └────────┤
             ▼
            END
```

---

## 三、节点函数详细设计

### 3.1 `validate_plan_node` — 方案校验

```python
async def validate_plan_node(state: SupervisorState) -> dict:
    """
    校验实验方案的合法性和安全性。
    
    不需要 LLM — 纯规则校验。
    使用 experiment_builder.validate_experiment()
    """
    plan = state["experiment_plan"]
    
    # 调用 Tool
    validation = experiment_builder.validate_experiment(plan)
    
    if not validation["valid"]:
        return {
            "status": "aborted",
            "messages": [AIMessage(content=f"方案校验失败:\n" + 
                         "\n".join(f"  ❌ {e}" for e in validation["errors"]))],
        }
    
    # 警告不阻止执行，但记录
    if validation["warnings"]:
        alerts = [{"type": "plan_warning", "message": w} for w in validation["warnings"]]
    else:
        alerts = []
    
    # 计算步骤数
    steps = plan.get("program", {}).get("steps", [])
    
    return {
        "status": "scheduling",
        "total_steps": len(steps),
        "alerts": alerts,
    }
```

### 3.2 `schedule_node` — 智能排程 (C2)

```python
async def schedule_node(state: SupervisorState) -> dict:
    """
    C2 Skill: 优化实验执行顺序。
    
    对于单个实验：直接按步骤顺序执行。
    对于 combo 实验（浓度梯度等）：优化组合顺序，减少冲洗。
    
    LLM: 可选（给优化建议），核心是算法。
    """
    plan = state["experiment_plan"]
    steps = plan.get("program", {}).get("steps", [])
    
    # 简单模式：按原顺序
    schedule = []
    for i, step in enumerate(steps):
        schedule.append({
            "order": i,
            "step_index": i,
            "step_type": step.get("type", "unknown"),
            "estimated_duration_s": estimate_step_duration(step),
        })
    
    total_duration = sum(s["estimated_duration_s"] for s in schedule)
    
    return {
        "schedule": schedule,
        "status": "executing",
        "current_step_index": 0,
        "messages": [AIMessage(content=
            f"排程完成: {len(schedule)} 步, 预估耗时 {total_duration/60:.1f} 分钟")]
    }


def estimate_step_duration(step: dict) -> float:
    """估算步骤耗时（秒）"""
    step_type = step.get("type", "")
    if step_type == "echem":
        # 根据技术类型和参数估算
        technique = step.get("technique", "")
        if technique == "CV":
            scan_rate = step.get("scan_rate", 0.1)
            potential_range = abs(step.get("e_high", 0.5) - step.get("e_low", -0.5))
            return potential_range / scan_rate * 2 * step.get("segments", 2)
        elif technique in ("i-t", "OCPT"):
            return step.get("run_time", 60)
        return 120  # 默认 2 分钟
    elif step_type == "prep_sol":
        return 60  # 配液约 1 分钟
    elif step_type == "flush":
        return step.get("cycles", 3) * 20  # 每次冲洗约 20 秒
    elif step_type == "transfer":
        return 30
    elif step_type == "blank":
        return step.get("duration", 10)
    elif step_type == "evacuate":
        return step.get("duration", 30)
    return 60
```

### 3.3 `execute_step_node` — 执行步骤

```python
async def execute_step_node(state: SupervisorState) -> dict:
    """
    执行当前步骤。
    
    Phase 1 (post_analysis): 读取已有实验数据（模拟执行）
    Phase 4 (single_run/adaptive): 通过 IPC 真正控制 MicroHySeeker
    
    不需要 LLM — 纯执行操作。
    """
    mode = state.get("execution_mode", "post_analysis")
    step_index = state["current_step_index"]
    
    if mode == "post_analysis":
        return await _execute_post_analysis(state, step_index)
    elif mode in ("single_run", "adaptive_loop"):
        return await _execute_real(state, step_index)


async def _execute_post_analysis(state: SupervisorState, step_index: int) -> dict:
    """Phase 1: 读取已有实验数据作为执行结果"""
    run_dir = state["run_dir"]
    
    # 读取该步骤的数据
    plan = state["experiment_plan"]
    step = plan["program"]["steps"][step_index]
    step_type = step.get("type", "")
    
    step_data = {
        "step_index": step_index,
        "step_type": step_type,
        "executed_at": None,  # 后分析模式无精确时间
    }
    
    if step_type == "echem":
        # 读取对应的 echem CSV 文件
        echem_files = data_reader.list_echem_files(run_dir)
        matching = [f for f in echem_files if f.get("step_index") == step_index]
        if matching:
            step_data["echem_csv_path"] = matching[0]["path"]
            step_data["echem_data"] = data_reader.read_echem_csv(matching[0]["path"])
    
    elif step_type == "prep_sol":
        # 读取配液结果
        prep_sol_path = Path(run_dir) / f"step_{step_index}_prep_sol.json"
        if prep_sol_path.exists():
            step_data["prep_sol_result"] = json.loads(prep_sol_path.read_text())
    
    # 从 run_summary 获取步骤状态
    summary = data_reader.read_run_summary(run_dir)
    step_details = summary.get("steps", {}).get(str(step_index), {})
    step_data["status"] = step_details.get("status", "unknown")
    step_data["error_msg"] = step_details.get("error_msg", None)
    
    return {
        "current_step_data": step_data,
        "status": "monitoring",
    }


async def _execute_real(state: SupervisorState, step_index: int) -> dict:
    """Phase 4: 真正通过 IPC 执行实验"""
    plan = state["experiment_plan"]
    
    # 加载实验到 MicroHySeeker
    await experiment_control.load_experiment(plan)
    
    # 启动执行（指定从 step_index 开始）
    await experiment_control.start_experiment(from_step=step_index)
    
    # 等待当前步骤完成
    result = await experiment_control.wait_for_step_completion(
        step_index=step_index,
        timeout=3600,  # 最长 1 小时
    )
    
    return {
        "current_step_data": result,
        "status": "monitoring",
    }
```

### 3.4 `monitor_step_node` — 监控+质量评估 (C1)

```python
async def monitor_step_node(state: SupervisorState) -> dict:
    """
    C1 Skill: 评估当前步骤的执行质量。
    
    Phase 1: 后分析（读已有数据评估）
    Phase 4: 实时（边执行边评估）
    
    不一定需要 LLM — 规则评分为主，LLM 做异常解读（可选）。
    """
    step_data = state["current_step_data"]
    step_index = state["current_step_index"]
    step_type = step_data.get("step_type", "")
    
    quality_score = 100.0  # 满分起评
    alerts = list(state.get("alerts", []))
    
    # 1. 检查步骤状态
    if step_data.get("status") == "error" or step_data.get("error_msg"):
        return {
            "error_info": {
                "step_index": step_index,
                "step_type": step_type,
                "error_type": "execution_error",
                "error_msg": step_data.get("error_msg", "未知错误"),
            },
            "status": "diagnosing",  # → 进入诊断流程
        }
    
    # 2. 电化学数据质量评估
    if step_type == "echem" and step_data.get("echem_data") is not None:
        df = step_data["echem_data"]
        
        # 数据质量评分
        quality = echem_analysis.assess_data_quality(df, step_data.get("technique", ""))
        quality_score = quality["score"]
        
        if quality["noise_level"] > 0.5:
            alerts.append({
                "type": "high_noise",
                "step_index": step_index,
                "message": f"步骤 {step_index} 噪声水平偏高: {quality['noise_level']:.2f}",
                "severity": "warning",
            })
        
        if quality.get("anomalies"):
            for anomaly in quality["anomalies"]:
                alerts.append({
                    "type": "data_anomaly",
                    "step_index": step_index,
                    "message": f"步骤 {step_index} 检测到异常: {anomaly['type']}",
                    "severity": anomaly.get("severity", "info"),
                })
        
        # 低于阈值视为失败
        if quality_score < 30:
            return {
                "error_info": {
                    "step_index": step_index,
                    "step_type": step_type,
                    "error_type": "quality_too_low",
                    "error_msg": f"数据质量评分过低: {quality_score:.0f}/100",
                    "quality_details": quality,
                },
                "status": "diagnosing",
            }
    
    # 3. 配液步骤质量检查
    if step_type == "prep_sol" and step_data.get("prep_sol_result"):
        result = step_data["prep_sol_result"]
        # 检查体积偏差
        expected = result.get("expected_total_volume")
        actual = result.get("actual_total_volume")
        if expected and actual:
            deviation = abs(actual - expected) / expected
            if deviation > 0.05:  # 偏差超过 5%
                quality_score -= 20
                alerts.append({
                    "type": "volume_deviation",
                    "step_index": step_index,
                    "message": f"配液体积偏差 {deviation:.1%}",
                    "severity": "warning",
                })
    
    # 更新质量评分列表
    quality_scores = list(state.get("quality_scores", []))
    quality_scores.append(quality_score)
    
    return {
        "quality_scores": quality_scores,
        "alerts": alerts,
        "status": "executing",  # 继续
    }
```

### 3.5 `handle_success_node` — 处理成功步骤

```python
async def handle_success_node(state: SupervisorState) -> dict:
    """
    当前步骤成功完成，记录结果并推进索引。
    不需要 LLM。
    """
    step_data = state["current_step_data"]
    step_index = state["current_step_index"]
    
    # 记录结果
    step_results = list(state.get("step_results", []))
    step_results.append({
        "step_index": step_index,
        "status": "success",
        "quality_score": state.get("quality_scores", [0])[-1] if state.get("quality_scores") else 100,
        "data_summary": _summarize_step_data(step_data),
    })
    
    return {
        "step_results": step_results,
        "current_step_index": step_index + 1,
        "current_step_data": None,
        "error_info": None,
        "diagnosis_result": None,
        "retry_count": 0,  # 重置重试计数
    }
```

### 3.6 `diagnose_failure_node` — 调用 DiagnosticsExpert

```python
async def diagnose_failure_node(state: SupervisorState) -> dict:
    """
    ★ C→D 联动的关键节点。
    当步骤失败时，调用 DiagnosticsExpert Agent 进行诊断。
    
    不直接使用 LLM — 委托给 D Agent。
    """
    error_info = state["error_info"]
    run_dir = state.get("run_dir")
    
    # 构造 D Agent 的输入
    dx_input = DiagnosticsState(
        messages=[],
        task="diagnose",
        run_dir=run_dir,
        symptom=None,
        check_depth="standard",
        error_info=error_info,
        # ... 其他字段
    )
    
    # 调用 DiagnosticsExpert subgraph
    from src.graph.diagnostics_graph import build_diagnostics_graph
    dx_graph = build_diagnostics_graph()
    dx_result = await dx_graph.ainvoke(dx_input)
    
    diagnosis = {
        "root_cause": dx_result.get("root_cause", "未知"),
        "confidence": dx_result.get("confidence", 0),
        "category": dx_result.get("error_classification", {}).get("category", "unknown"),
        "recommended_actions": dx_result.get("recommended_actions", []),
        "auto_fixable": any(
            a.get("auto_fixable") for a in dx_result.get("recommended_actions", [])
        ),
        "diagnosis_report": dx_result.get("diagnosis_report", ""),
    }
    
    return {
        "diagnosis_result": diagnosis,
        "status": "deciding",
        "messages": [AIMessage(content=
            f"诊断完成: {diagnosis['root_cause']} (置信度: {diagnosis['confidence']:.0%})")],
    }
```

### 3.7 `decide_action_node` — 关键决策点（★ LLM）

```python
async def decide_action_node(state: SupervisorState) -> dict:
    """
    ★ 这是 LLM 发挥最关键作用的节点。
    
    根据诊断结果决定：
    - retry: 重试当前步骤（可能调整参数）
    - skip:  跳过当前步骤继续
    - abort: 中止整个实验
    
    决策逻辑：
    1. 重试次数 < max_retries 且问题可修复 → retry
    2. 当前步骤不关键 → skip
    3. 已达重试上限或严重问题 → abort
    
    Phase 1 (无 IPC): retry 实际上等于 skip（不能真正重新执行）
    Phase 4 (有 IPC): retry 会真正重新执行该步骤
    """
    diagnosis = state["diagnosis_result"]
    retry_count = state["retry_count"]
    max_retries = state.get("max_retries", 2)
    step_index = state["current_step_index"]
    total_steps = state["total_steps"]
    
    # 规则预判（简单情况不需要 LLM）
    if retry_count >= max_retries:
        # 已达重试上限
        decision = "abort" if _is_critical_step(state) else "skip"
        reason = f"重试次数已达上限 ({retry_count}/{max_retries})"
    
    elif diagnosis.get("category") == "parameter" and diagnosis.get("auto_fixable"):
        # 参数问题，可自动修复 → 重试
        decision = "retry"
        reason = f"参数问题可自动修正: {diagnosis['root_cause']}"
    
    else:
        # 复杂情况：交给 LLM 决策
        prompt = DECISION_PROMPT.format(
            step_index=step_index,
            total_steps=total_steps,
            error_info=json.dumps(state["error_info"], ensure_ascii=False),
            diagnosis=json.dumps(diagnosis, ensure_ascii=False, indent=2),
            retry_count=retry_count,
            max_retries=max_retries,
            step_results_summary=_summarize_past_steps(state),
        )
        
        response = await llm_client.chat(
            system=SUPERVISOR_SYSTEM_PROMPT,
            user=prompt,
            response_format=DecisionResult,
        )
        decision = response.decision
        reason = response.reasoning
    
    # Human-in-the-loop: 严重问题暂停等待确认
    if diagnosis.get("confidence", 0) < 0.5 and decision == "abort":
        # 低置信度中止决策 → 请用户确认
        raise NodeInterrupt(
            f"低置信度决策需要确认:\n"
            f"诊断: {diagnosis['root_cause']} (置信度: {diagnosis['confidence']:.0%})\n"
            f"建议: {decision} — {reason}\n"
            f"请确认: retry / skip / abort"
        )
    
    return {
        "decision": decision,
        "retry_count": retry_count + 1 if decision == "retry" else retry_count,
        "messages": [AIMessage(content=f"决策: {decision} — {reason}")],
    }


class DecisionResult(BaseModel):
    decision: Literal["retry", "skip", "abort"]
    reasoning: str
    suggested_modification: dict | None = None  # retry 时可能调整参数


def _is_critical_step(state: SupervisorState) -> bool:
    """判断当前步骤是否关键（如 echem 测量是关键，blank 等待不关键）"""
    plan = state["experiment_plan"]
    step_index = state["current_step_index"]
    steps = plan.get("program", {}).get("steps", [])
    if step_index < len(steps):
        return steps[step_index].get("type") in ("echem", "prep_sol")
    return True
```

### 3.8 `save_results_node` — 保存结果

```python
async def save_results_node(state: SupervisorState) -> dict:
    """
    保存所有结果。
    不需要 LLM — 纯数据操作。
    """
    quality_scores = state.get("quality_scores", [])
    overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    results_summary = {
        "total_steps": state["total_steps"],
        "completed_steps": len(state.get("step_results", [])),
        "status": state["status"],
        "overall_quality": overall_quality,
        "quality_scores": quality_scores,
        "alerts": state.get("alerts", []),
        "step_results": state.get("step_results", []),
    }
    
    # 保存到文件（Phase 1: 存到 AutoHySeeker 自己的 data/ 下）
    # Phase 4: 数据已由 MicroHySeeker 保存
    
    return {
        "overall_quality": overall_quality,
    }
```

### 3.9 `generate_report_node` — 生成实验报告

```python
async def generate_report_node(state: SupervisorState) -> dict:
    """
    生成实验质量报告。
    
    LLM: 可选（增强解读）。没有 LLM 也能生成结构化报告。
    """
    # 模板报告（不需要 LLM）
    report_parts = [
        f"# 实验质量报告",
        f"",
        f"**总步骤**: {state['total_steps']}",
        f"**完成步骤**: {len(state.get('step_results', []))}",
        f"**整体质量**: {state.get('overall_quality', 0):.0f}/100",
        f"**状态**: {state['status']}",
        f"",
        f"## 各步骤评分",
    ]
    
    for i, score in enumerate(state.get("quality_scores", [])):
        emoji = "✅" if score >= 70 else "⚠️" if score >= 30 else "❌"
        report_parts.append(f"  {emoji} 步骤 {i}: {score:.0f}/100")
    
    if state.get("alerts"):
        report_parts.append(f"\n## 告警")
        for alert in state["alerts"]:
            report_parts.append(f"  - [{alert['severity']}] {alert['message']}")
    
    template_report = "\n".join(report_parts)
    
    # LLM 增强（可选）
    if llm_available:
        prompt = f"""基于以下实验执行数据，生成一份简洁的实验质量报告。
重点关注：数据质量、异常事件、改进建议。

{template_report}

步骤详情:
{json.dumps(state.get('step_results', []), ensure_ascii=False, indent=2)}
"""
        enhanced_report = await llm_client.chat(
            system=SUPERVISOR_SYSTEM_PROMPT,
            user=prompt,
        )
        return {"final_report": enhanced_report}
    
    return {"final_report": template_report}
```

---

## 四、System Prompt

```python
SUPERVISOR_SYSTEM_PROMPT = """你是 AutoHySeeker 系统的实验执行管家（ExperimentSupervisor）。

你的职责：
1. 监控实验执行过程，评估每个步骤的质量
2. 当出现问题时，根据诊断结果做出决策（重试/跳过/中止）
3. 生成实验质量报告

决策原则：
- 安全第一：如果存在可能损坏设备的风险，立即中止
- 数据质量：如果电化学数据质量过低（<30分），建议重试
- 容错性：非关键步骤（flush, blank）失败时倾向于跳过
- 效率：重试次数不超过上限，避免无意义循环
- 坦诚：如果不确定，建议暂停让用户确认

你了解的硬件系统：
- 12 路 RS485 蠕动泵（Longer BT100-2J），泵 1-4 配液，泵 5 废液，泵 6-8 冲洗
- CHI 660F 电化学工作站
- 6 种步骤类型：prep_sol, transfer, flush, echem, blank, evacuate
- 关键步骤：echem（核心测量）、prep_sol（影响浓度准确性）
- 非关键步骤：flush（冲洗）、blank（等待）、evacuate（排空）

输出要求：
- 决策要给出明确的 reasoning
- 报告使用 Markdown 格式，简洁有重点
"""

DECISION_PROMPT = """实验执行中遇到错误，请决策下一步操作。

## 当前状态
- 步骤: {step_index}/{total_steps}
- 已重试: {retry_count}/{max_retries}

## 错误信息
{error_info}

## 诊断结果
{diagnosis}

## 已完成步骤摘要
{step_results_summary}

请决策：
- retry: 重试当前步骤
- skip: 跳过当前步骤继续
- abort: 中止整个实验

返回 JSON: {{"decision": "retry|skip|abort", "reasoning": "...", "suggested_modification": null}}
"""
```

---

## 五、依赖的 Tools

| Tool 函数 | 所属模块 | 在哪个节点使用 |
|-----------|---------|--------------|
| `validate_experiment` | experiment_builder | validate_plan |
| `list_echem_files` | data_reader | execute_step (post_analysis) |
| `read_echem_csv` | data_reader | execute_step (post_analysis) |
| `read_run_summary` | data_reader | execute_step (post_analysis) |
| `assess_data_quality` | echem_analysis | monitor_step |
| `detect_anomalies` | echem_analysis | monitor_step |
| `render_markdown_report` | report_generator | generate_report |
| `load_experiment` | experiment_control | execute_step (Phase 4) |
| `start_experiment` | experiment_control | execute_step (Phase 4) |
| `get_engine_status` | experiment_control | execute_step (Phase 4) |
| `subscribe_events` | experiment_control | monitor_step (Phase 4) |

---

## 六、Phase 1 vs Phase 4 差异

| 功能 | Phase 1 (后分析) | Phase 4 (实时) |
|------|------------------|----------------|
| execute_step | 读已有数据 | IPC 控制 MicroHySeeker |
| monitor_step | 评估已有数据质量 | 实时数据流评估 |
| decide_action→retry | 等同于 skip（无法重新执行） | 真正重新执行步骤 |
| C3 adaptive_loop | 不支持 | 全流程自适应 |
| Human-in-the-loop | 无（后分析不需要） | 关键决策暂停 |
| subscribe_events | 不需要 | WebSocket 实时事件 |

**Phase 1 的价值**：即使是后分析模式，也能验证整个图的流转逻辑、校验+排程+监控+诊断+决策的完整链路。当 Phase 4 的 IPC 就绪后，只需替换 `execute_step_node` 的实现即可。

---

## 七、测试计划

### 7.1 Graph 流转测试

```python
async def test_supervisor_all_success():
    """全部步骤成功的情况"""
    graph = build_supervisor_graph()
    result = await graph.ainvoke({
        "experiment_plan": SAMPLE_PLAN,
        "execution_mode": "post_analysis",
        "run_dir": "tests/fixtures/successful_run",
        "max_retries": 2,
        "retry_count": 0,
        "current_step_index": 0,
    })
    assert result["status"] == "completed"
    assert result["overall_quality"] > 70

async def test_supervisor_with_failure_and_retry():
    """步骤失败 → 诊断 → 重试 → 成功"""
    # 需要一个第一次失败、第二次成功的模拟数据
    ...

async def test_supervisor_abort_on_critical_failure():
    """关键步骤严重失败 → 诊断 → 中止"""
    ...

async def test_supervisor_skip_non_critical():
    """非关键步骤失败 → 跳过 → 继续"""
    ...
```

### 7.2 C→D 集成测试

```python
async def test_supervisor_calls_diagnostics():
    """验证 C 出错时确实调用了 D 并拿到诊断结果"""
    graph = build_supervisor_graph()
    result = await graph.ainvoke({
        "experiment_plan": SAMPLE_PLAN_WITH_ERROR,
        "execution_mode": "post_analysis",
        "run_dir": "tests/fixtures/failed_run",
        ...
    })
    # 验证诊断结果存在
    assert result.get("diagnosis_result") is not None
    assert result["diagnosis_result"]["root_cause"] != ""
```

---

## 八、开发清单（Week 3-4）

```
Week 3:
  ☐ graph/state.py — SupervisorState
  ☐ graph/supervisor_graph.py — 完整图定义
  ☐ agents/supervisor_nodes.py — validate_plan, schedule, execute_step (post_analysis)
  ☐ agents/supervisor_nodes.py — monitor_step (C1 核心)
  ☐ agents/supervisor_nodes.py — handle_success
  ☐ tools/experiment_builder.py — validate_experiment (供 validate_plan 用)
  ☐ tools/echem_analysis.py — assess_data_quality (供 monitor_step 用)

Week 4:
  ☐ agents/supervisor_nodes.py — diagnose_failure (调用 D)
  ☐ agents/supervisor_nodes.py — decide_action (★ LLM 决策)
  ☐ agents/supervisor_nodes.py — save_results, generate_report
  ☐ agents/prompts.py — SUPERVISOR_SYSTEM_PROMPT, DECISION_PROMPT
  ☐ skills/experiment_execution/execution_monitor.py (C1 Skill)
  ☐ skills/experiment_execution/smart_scheduler.py (C2 Skill)
  ☐ C→D 集成测试
  ☐ CLI: python -m autohyseeker.cli review <run_dir>
```

---

## 九、注意事项

### 9.1 Phase 1 的"后分析"执行模式

Phase 1 的 ExperimentSupervisor **不控制真实硬件**。它的工作方式是：

1. 给它一个已完成的实验 run_dir
2. 它假装"执行"每个步骤（实际是读取该步骤的数据）
3. 然后评估每个步骤的质量
4. 如果发现质量问题，调用 D 诊断
5. 决策 retry/skip/abort（retry 在后分析模式下等于 skip）
6. 生成完整质量报告

**这模拟了完整的 C→D→C 闭环**，验证了图的所有条件边和节点逻辑。

### 9.2 estimate_step_duration 的精确化

Phase 1 的耗时估算基于参数推导。后续可以：
- 从历史数据学习真实耗时（A3 趋势追踪）
- 用回归模型预测（Phase 4）

### 9.3 Combo 实验的排程策略

Combo 实验（浓度梯度等）的排程考虑：
- **同浓度分组**：减少冲洗次数
- **从低到高**：避免高浓度污染低浓度测量
- **交替测量/冲洗**：避免电极累积
- 这些策略在 C2 `schedule_node` 中实现

---

*此文档可直接作为 ExperimentSupervisor Agent 的开发执行依据。*

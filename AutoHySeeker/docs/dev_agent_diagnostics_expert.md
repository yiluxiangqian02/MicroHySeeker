# Agent D — DiagnosticsExpert 开发指南

> 代号：DX | 优先级：P1 (Week 2-3) | 域：故障诊断与运维
> 总体架构参考：[`langgraph_architecture.md`](langgraph_architecture.md) | Tool/Skill定义参考：[`skills_architecture.md`](skills_architecture.md)

---

## 一、Agent 概览

### 1.1 职责定位

DiagnosticsExpert 是**实验故障的医生**：

- 实验失败 → 分析原因、给出解决方案（D1）
- 日常巡检 → 综合评估系统健康状态（D2）
- 用户报告症状 → 多轮对话引导排查（D3）

### 1.2 在系统中的位置

```
Orchestrator ──→ DiagnosticsExpert       ← 用户直接提问
ExperimentSupervisor ──→ DiagnosticsExpert  ← 执行出错自动调用（★ 最关键场景）
```

**两种调用方式**：
1. **用户触发**：`"为什么今天的实验失败了？"` → Orchestrator 路由到 DX
2. **Supervisor 触发**：C 执行实验时检测到异常 → 自动调用 DX → DX 返回诊断 → C 决策

### 1.3 拥有的 Skills

| Skill | 名称 | 输入 | 输出 | LLM |
|-------|------|------|------|-----|
| **D1** | `diagnose_failed_experiment` | 实验目录 | 根因分析+解决建议 | ✅ 根因推理 |
| **D2** | `system_health_check` | 检查深度 | 健康评分+维护建议 | ⚠️ 可降级 |
| **D3** | `interactive_troubleshooting` | 症状描述 | 诊断步骤+解决方案 | ✅ 对话推理 |

---

## 二、LangGraph Subgraph 设计

### 2.1 State 定义

```python
class DiagnosticsState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 任务类型
    task: Literal["diagnose", "health_check", "troubleshoot"]
    
    # 输入
    run_dir: str | None           # D1: 要诊断的实验目录
    symptom: str | None           # D3: 用户描述的症状
    check_depth: str              # D2: "quick"|"standard"|"deep"
    
    # 中间数据
    error_info: dict | None       # 提取的错误信息
    log_context: list[dict] | None # 相关日志条目
    pump_anomalies: list[dict] | None
    evidence: list[str]           # 收集到的证据列表
    
    # 诊断结果
    error_classification: dict | None  # {category, subcategory, severity}
    root_cause: str | None
    confidence: float
    similar_cases: list[dict]      # RAG 搜到的类似案例
    recommended_actions: list[dict]
    
    # D2 专用
    health_score: float | None
    component_status: dict | None
    
    # 输出
    diagnosis_report: str | None   # 最终诊断报告 (Markdown)
```

### 2.2 Graph 结构

```python
def build_diagnostics_graph():
    graph = StateGraph(DiagnosticsState)
    
    # 节点
    graph.add_node("classify_issue", classify_issue_node)
    graph.add_node("collect_evidence", collect_evidence_node)
    graph.add_node("analyze_root_cause", analyze_root_cause_node)
    graph.add_node("search_solutions", search_solutions_node)
    graph.add_node("recommend_actions", recommend_actions_node)
    
    # D2 分支
    graph.add_node("run_health_check", run_health_check_node)
    
    # 边
    graph.add_edge(START, "classify_issue")
    graph.add_conditional_edges("classify_issue", route_diagnosis_task, {
        "diagnose": "collect_evidence",
        "health_check": "run_health_check",
        "troubleshoot": "collect_evidence",  # D3 共用证据收集
    })
    graph.add_edge("collect_evidence", "analyze_root_cause")
    graph.add_edge("analyze_root_cause", "search_solutions")
    graph.add_edge("search_solutions", "recommend_actions")
    graph.add_edge("run_health_check", "recommend_actions")
    graph.add_edge("recommend_actions", END)
    
    return graph.compile()
```

```
    ┌────── START ──────┐
    │                   │
    ▼                   │
 classify_issue         │
    │                   │
    ├── diagnose ──────►│──► collect_evidence
    ├── health_check ──►│──► run_health_check
    └── troubleshoot ──►│──► collect_evidence
                        │
    collect_evidence ───►│──► analyze_root_cause
                        │
    analyze_root_cause ─►│──► search_solutions
                        │
    search_solutions ───►│──► recommend_actions
                        │
    run_health_check ───►│──► recommend_actions
                        │
    recommend_actions ──►│──► END
```

---

## 三、节点函数详细设计

### 3.1 `classify_issue_node` — 问题分类

```python
async def classify_issue_node(state: DiagnosticsState) -> dict:
    """
    根据输入判断走哪条诊断路径。
    - 有 run_dir → "diagnose" (D1)
    - 有 symptom 且无 run_dir → "troubleshoot" (D3)
    - task == "health_check" → "health_check" (D2)
    
    不需要 LLM — 纯规则判断。
    """
    if state.get("task") == "health_check":
        return {"task": "health_check"}
    
    if state.get("run_dir"):
        return {"task": "diagnose"}
    
    if state.get("symptom"):
        return {"task": "troubleshoot"}
    
    # 兜底：尝试从 messages 中用 LLM 提取意图
    # ...
```

### 3.2 `collect_evidence_node` — 证据收集

```python
async def collect_evidence_node(state: DiagnosticsState) -> dict:
    """
    收集所有可用的诊断证据。
    
    对于 D1 (有 run_dir):
      1. read_run_summary → 定位失败步骤
      2. read_run_log + extract_errors → 错误详情
      3. read_pump_operations + detect_pump_anomalies → 泵异常
      4. extract_timing_info → 时间异常检测
    
    对于 D3 (有 symptom):
      1. 解析症状关键词 → 确定检查方向
      2. 如有最近实验 → 读取最近的 run_log
      3. get_hardware_status → 当前硬件状态 (Phase 4)
    
    不需要 LLM — 纯 Tool 调用。
    """
    evidence = []
    error_info = None
    log_context = None
    pump_anomalies = None
    
    if state["task"] == "diagnose" and state["run_dir"]:
        run_dir = state["run_dir"]
        
        # 1. 读取 run_summary
        summary = data_reader.read_run_summary(run_dir)
        if summary.get("status") == "error":
            error_info = {
                "error_step": summary.get("error_step"),
                "error_msg": summary.get("error_message", ""),
                "total_steps": summary.get("total_steps"),
                "completed_steps": summary.get("completed_steps"),
            }
            evidence.append(f"实验在第 {error_info['error_step']} 步失败: {error_info['error_msg']}")
        
        # 2. 读取并解析日志
        log_entries = log_analysis.parse_run_log(
            data_reader.read_run_log(run_dir)
        )
        errors = log_analysis.extract_errors(log_entries)
        warnings = log_analysis.extract_warnings(log_entries)
        timing = log_analysis.extract_timing_info(log_entries)
        
        log_context = errors + warnings  # 错误和警告原文
        for e in errors:
            evidence.append(f"ERROR: {e['message']}")
        for w in warnings:
            evidence.append(f"WARNING: {w['message']}")
        
        # 3. 泵操作异常
        try:
            pump_df = data_reader.read_pump_operations(run_dir)
            pump_anomalies = log_analysis.detect_pump_anomalies(pump_df)
            for a in pump_anomalies:
                evidence.append(f"泵异常: {a['description']}")
        except FileNotFoundError:
            evidence.append("注意: 无 pump_operations.csv 文件")
        
        # 4. 时间异常
        if timing.get("gaps"):
            for gap in timing["gaps"]:
                evidence.append(f"时间间隙: {gap['description']}")
    
    elif state["task"] == "troubleshoot":
        symptom = state["symptom"]
        evidence.append(f"用户报告症状: {symptom}")
        
        # 查最近的实验日志
        recent_runs = data_reader.list_experiment_runs(
            data_dir=config.microhyseeker_data_dir,
            limit=3
        )
        for run in recent_runs:
            summary = data_reader.read_run_summary(run["path"])
            evidence.append(f"最近实验 {run['name']}: 状态={summary['status']}")
    
    return {
        "error_info": error_info,
        "log_context": log_context,
        "pump_anomalies": pump_anomalies,
        "evidence": evidence,
    }
```

### 3.3 `analyze_root_cause_node` — 根因分析

```python
async def analyze_root_cause_node(state: DiagnosticsState) -> dict:
    """
    根因分析 — 这里 LLM 发挥核心作用。
    
    步骤：
    1. 规则引擎先做初步分类 (classify_error)
    2. LLM 综合所有证据做深层推理
    
    ★ 这是 LLM 最能加速的环节 — 人类需要几分钟浏览日志，LLM 秒级完成。
    """
    evidence = state["evidence"]
    error_info = state.get("error_info", {})
    
    # 1. 规则引擎初分类
    classification = None
    if error_info and error_info.get("error_msg"):
        classification = log_analysis.classify_error(error_info["error_msg"])
    
    # 2. LLM 深度分析
    prompt = ROOT_CAUSE_ANALYSIS_PROMPT.format(
        evidence="\n".join(f"  - {e}" for e in evidence),
        classification=json.dumps(classification, ensure_ascii=False) if classification else "无",
        error_info=json.dumps(error_info, ensure_ascii=False) if error_info else "无",
    )
    
    response = await llm_client.chat(
        system=DIAGNOSTICS_SYSTEM_PROMPT,
        user=prompt,
        response_format=RootCauseAnalysis,  # Pydantic 结构化输出
    )
    
    return {
        "error_classification": classification,
        "root_cause": response.root_cause,
        "confidence": response.confidence,
    }

# Pydantic 模型用于结构化输出
class RootCauseAnalysis(BaseModel):
    root_cause: str                  # "RS485 通讯超时导致泵未响应转速指令"
    category: str                    # "hardware" | "software" | "parameter" | "reagent" | "communication"
    confidence: float                # 0.0 ~ 1.0
    reasoning: str                   # 推理过程
    contributing_factors: list[str]  # 次要因素
```

### 3.4 `search_solutions_node` — 搜索解决方案

```python
async def search_solutions_node(state: DiagnosticsState) -> dict:
    """
    在知识库中搜索类似问题和解决方案。
    
    Phase 1: 用硬编码的 error_knowledge_base（规则表）
    Phase 3+: 用 RAG 搜索 error_solutions collection
    
    不一定需要 LLM — RAG 检索本身不需要。
    """
    root_cause = state.get("root_cause", "")
    error_info = state.get("error_info", {})
    
    # 方案 A: 规则表（Phase 1 立刻可用）
    known_solutions = log_analysis.get_error_knowledge_base()
    classification = state.get("error_classification", {})
    if classification:
        category = classification.get("category", "")
        subcategory = classification.get("subcategory", "")
        key = f"{category}.{subcategory}"
        if key in known_solutions:
            return {"similar_cases": [known_solutions[key]]}
    
    # 方案 B: RAG 搜索（Phase 3+）
    if rag_available:
        results = rag_tools.semantic_search(
            query=f"{root_cause} {error_info.get('error_msg', '')}",
            collection="error_solutions",
            top_k=3,
        )
        return {"similar_cases": results}
    
    return {"similar_cases": []}
```

### 3.5 `recommend_actions_node` — 生成建议

```python
async def recommend_actions_node(state: DiagnosticsState) -> dict:
    """
    综合所有分析结果，生成结构化建议 + 人类可读报告。
    
    ★ LLM 在这里生成最终的诊断报告。
    没有 LLM 也能运行：只返回结构化分类+规则表方案，无自然语言报告。
    """
    # 结构化建议（不需要 LLM）
    actions = []
    
    classification = state.get("error_classification", {})
    root_cause = state.get("root_cause", "未知")
    similar_cases = state.get("similar_cases", [])
    
    # 从规则表/RAG 提取建议
    for case in similar_cases:
        if "solution" in case:
            actions.append({
                "action": case["solution"],
                "priority": "high",
                "source": "knowledge_base",
            })
    
    # LLM 生成完整报告（可选但推荐）
    report = None
    if llm_available:
        prompt = DIAGNOSIS_REPORT_PROMPT.format(
            evidence="\n".join(f"  - {e}" for e in state["evidence"]),
            root_cause=root_cause,
            confidence=state.get("confidence", 0),
            similar_cases=json.dumps(similar_cases, ensure_ascii=False),
            existing_actions=json.dumps(actions, ensure_ascii=False),
        )
        report = await llm_client.chat(
            system=DIAGNOSTICS_SYSTEM_PROMPT,
            user=prompt,
        )
    else:
        # 降级：模板生成
        report = f"""## 诊断报告

**根因分析**: {root_cause}
**错误分类**: {classification}
**置信度**: {state.get('confidence', 'N/A')}

### 证据
{chr(10).join('- ' + e for e in state['evidence'])}

### 建议操作
{chr(10).join('- [' + a['priority'] + '] ' + a['action'] for a in actions)}
"""
    
    return {
        "recommended_actions": actions,
        "diagnosis_report": report,
    }
```

### 3.6 `run_health_check_node` — 系统健康检查 (D2)

```python
async def run_health_check_node(state: DiagnosticsState) -> dict:
    """
    D2: 系统健康检查 — 扫描近期数据，给出综合评分。
    
    ★ 不需要实时 IPC — 分析已有数据即可。Phase 1 立刻可用。
    """
    depth = state.get("check_depth", "standard")
    data_dir = config.microhyseeker_data_dir
    
    # 1. 收集近期实验数据
    days = {"quick": 1, "standard": 7, "deep": 30}[depth]
    recent_runs = data_reader.list_experiment_runs(data_dir, days=days)
    
    # 2. 统计各维度
    total = len(recent_runs)
    failed = sum(1 for r in recent_runs if r["status"] == "error")
    
    # 3. 泵异常统计
    all_pump_anomalies = []
    for run in recent_runs:
        try:
            pump_df = data_reader.read_pump_operations(run["path"])
            anomalies = log_analysis.detect_pump_anomalies(pump_df)
            all_pump_anomalies.extend(anomalies)
        except FileNotFoundError:
            pass
    
    # 4. 错误频率统计
    error_categories = {}
    for run in recent_runs:
        if run["status"] == "error":
            log_entries = log_analysis.parse_run_log(
                data_reader.read_run_log(run["path"])
            )
            errors = log_analysis.extract_errors(log_entries)
            for e in errors:
                cat = log_analysis.classify_error(e["message"]).get("category", "unknown")
                error_categories[cat] = error_categories.get(cat, 0) + 1
    
    # 5. 计算健康分
    failure_rate = failed / total if total > 0 else 0
    base_score = max(0, 100 - failure_rate * 200)  # 50%失败率→0分
    pump_penalty = min(30, len(all_pump_anomalies) * 5)
    health_score = max(0, base_score - pump_penalty)
    
    component_status = {
        "experiments": {"total": total, "failed": failed, "success_rate": 1 - failure_rate},
        "pumps": {"anomaly_count": len(all_pump_anomalies), "details": all_pump_anomalies[:5]},
        "errors": error_categories,
    }
    
    evidence = [
        f"近 {days} 天: {total} 次实验, {failed} 次失败 ({failure_rate:.0%})",
        f"泵异常: {len(all_pump_anomalies)} 次",
        f"错误分类: {error_categories}",
    ]
    
    return {
        "health_score": health_score,
        "component_status": component_status,
        "evidence": evidence,
    }
```

---

## 四、System Prompt

```python
DIAGNOSTICS_SYSTEM_PROMPT = """你是 AutoHySeeker 系统的故障诊断专家（DiagnosticsExpert）。

你的专业领域：
- MicroHySeeker 微流控电化学实验平台
- 12 路 RS485 蠕动泵（Longer BT100-2J，地址 1-12）
- CHI 660F 电化学工作站（支持 CV/LSV/EIS/i-t/OCPT 等 13 种技术）
- 稀释器、冲洗器、定位器等辅助设备
- 实验步骤类型：prep_sol（配液）、transfer（移液）、flush（冲洗）、echem（电化学测量）、blank（等待）、evacuate（排空）

你的分析框架：
1. 首先确认错误发生在哪个步骤、什么时间
2. 分类错误类型：hardware（硬件）/ software（软件）/ parameter（参数）/ reagent（试剂）/ communication（通讯）
3. 根据日志上下文和泵操作数据推断根因
4. 给出可操作的解决建议，按优先级排列

常见错误模式：
- RS485 通讯超时：通常是线路接触不良或地址冲突
- 泵转速异常：校准漂移或管路堵塞
- CHI 仪器无响应：DDE 连接断开或仪器忙
- 电化学数据异常：电极污染、溶液配制错误、参数超范围
- 配液体积偏差：泵校准不准或管路有气泡

输出要求：
- 使用 Markdown 格式
- 根因分析要给出推理过程
- 建议要具体可操作（不要说"检查设备"，要说"检查泵1 RS485线缆的A+/B-接线端子"）
- 如果不确定，诚实说明置信度
"""

ROOT_CAUSE_ANALYSIS_PROMPT = """请分析以下实验故障的根本原因。

## 收集到的证据
{evidence}

## 规则引擎初步分类
{classification}

## 错误详情
{error_info}

请输出结构化分析结果（JSON），包含：
- root_cause: 最可能的根本原因（一句话）
- category: hardware / software / parameter / reagent / communication
- confidence: 置信度 0.0~1.0
- reasoning: 你的推理过程
- contributing_factors: 可能的辅助因素列表
"""

DIAGNOSIS_REPORT_PROMPT = """请根据以下分析结果生成完整的诊断报告。

## 证据
{evidence}

## 根因分析
{root_cause}（置信度: {confidence}）

## 历史相似案例
{similar_cases}

## 已有建议
{existing_actions}

请生成 Markdown 格式的诊断报告，包含：
1. 故障摘要（一段话）
2. 根因分析（推理过程）
3. 解决方案（按优先级排列，每条包含具体步骤）
4. 预防建议（防止再次发生）
"""
```

---

## 五、依赖的 Tools

| Tool 函数 | 所属模块 | 在哪个节点使用 |
|-----------|---------|--------------|
| `read_run_summary` | data_reader | collect_evidence |
| `read_run_log` | data_reader | collect_evidence |
| `read_pump_operations` | data_reader | collect_evidence |
| `list_experiment_runs` | data_reader | run_health_check |
| `parse_run_log` | log_analysis | collect_evidence |
| `extract_errors` | log_analysis | collect_evidence |
| `extract_warnings` | log_analysis | collect_evidence |
| `extract_timing_info` | log_analysis | collect_evidence |
| `classify_error` | log_analysis | analyze_root_cause |
| `detect_pump_anomalies` | log_analysis | collect_evidence |
| `check_calibration_drift` | log_analysis | run_health_check |
| `get_error_knowledge_base` | log_analysis | search_solutions |
| `semantic_search` | rag_tools | search_solutions (Phase 3+) |
| `render_markdown_report` | report_generator | recommend_actions |

---

## 六、与其他 Agent 的交互

### 6.1 被 ExperimentSupervisor 调用

```python
# supervisor_nodes.py 中的 diagnose_failure 节点
async def diagnose_failure_node(state: SupervisorState) -> dict:
    """C 检测到执行失败 → 调用 D"""
    
    # 构造 DiagnosticsExpert 的输入
    dx_input = {
        "task": "diagnose",
        "run_dir": state["run_dir"],
        "error_info": state["error_info"],
    }
    
    # 调用 DiagnosticsExpert subgraph
    dx_result = await diagnostics_graph.ainvoke(dx_input)
    
    return {
        "diagnosis_result": {
            "root_cause": dx_result["root_cause"],
            "confidence": dx_result["confidence"],
            "recommended_actions": dx_result["recommended_actions"],
            "report": dx_result["diagnosis_report"],
        }
    }
```

### 6.2 调用 KnowledgeManager

```python
# Phase 3+: search_solutions 中调用 E2
# 目前 Phase 1 用硬编码规则表代替
```

---

## 七、测试计划

### 7.1 单元测试

```python
# tests/test_tools/test_log_analysis.py
def test_classify_error_rs485_timeout():
    result = classify_error("RS485 通讯超时: 泵 addr=3 未响应")
    assert result["category"] == "communication"
    assert result["subcategory"] == "rs485_timeout"

def test_classify_error_chi_no_response():
    result = classify_error("CHI 仪器无响应")
    assert result["category"] == "hardware"
    assert result["subcategory"] == "instrument_no_response"

def test_detect_pump_anomalies():
    # 用真实 pump_operations.csv 测试
    df = pd.read_csv("data/2026-02-13/xxx/pump/pump_operations.csv")
    anomalies = detect_pump_anomalies(df)
    # 验证检测到的异常有合理结构
    for a in anomalies:
        assert "type" in a
        assert "severity" in a
```

### 7.2 Graph 集成测试

```python
# tests/test_graphs/test_diagnostics_graph.py
async def test_diagnose_failed_experiment():
    """端到端测试: 给一个失败实验目录 → 出诊断报告"""
    graph = build_diagnostics_graph()
    result = await graph.ainvoke({
        "task": "diagnose",
        "run_dir": "data/2026-02-13/153000_failed_test",
        "messages": [],
    })
    
    assert result["root_cause"] is not None
    assert result["confidence"] > 0
    assert len(result["recommended_actions"]) > 0
    assert result["diagnosis_report"] is not None

async def test_health_check():
    graph = build_diagnostics_graph()
    result = await graph.ainvoke({
        "task": "health_check",
        "check_depth": "standard",
        "messages": [],
    })
    
    assert 0 <= result["health_score"] <= 100
    assert result["component_status"] is not None
```

### 7.3 测试数据准备

需要准备的测试数据（放在 `tests/fixtures/` 下）：
1. 一个成功的实验目录（验证 D2）
2. 一个 RS485 超时失败的实验目录（验证 D1 - 通讯类）
3. 一个 CHI 错误的实验目录（验证 D1 - 仪器类）
4. 一个泵异常的实验目录（验证 D1 - 硬件类）
5. 连续多天的实验数据（验证 D2 趋势分析）

---

## 八、实现注意事项

### 8.1 Phase 1 优先级

1. **最先实现**：`data_reader` + `log_analysis` Tools（D 的基础）
2. **然后实现**：`collect_evidence_node` + `classify_error`（不需要 LLM）
3. **接着实现**：`analyze_root_cause_node`（LLM 核心）
4. **最后实现**：`search_solutions_node`（Phase 1 用规则表，Phase 3 升级 RAG）

### 8.2 降级策略

```
没有 LLM:
  - classify_error → 纯规则匹配（关键词表）
  - analyze_root_cause → 返回规则分类结果，不做深层推理
  - recommend_actions → 从知识库表匹配，不生成报告

没有 RAG:
  - search_solutions → 用硬编码的 error_knowledge_base dict

没有实时 IPC:
  - D3 interactive_troubleshooting → 只能基于文件数据，不能实时检查硬件
```

### 8.3 错误知识库数据结构

```python
# Phase 1: 硬编码，后续迁移到 RAG
ERROR_KNOWLEDGE_BASE = {
    "communication.rs485_timeout": {
        "description": "RS485 通讯超时",
        "common_causes": [
            "线缆接触不良（A+/B-端子松动）",
            "泵地址冲突（两个泵设为同一地址）",
            "波特率不匹配",
            "USB-RS485 转换器驱动问题",
        ],
        "solution": "1. 检查目标泵的 RS485 线缆连接\n2. 验证泵面板显示的地址是否正确\n3. 重启泵电源\n4. 如反复出现，更换 RS485 转换器",
        "auto_fixable": False,
    },
    "hardware.instrument_no_response": {
        "description": "CHI 660F 无响应",
        "common_causes": [
            "DDE 连接断开",
            "仪器正在执行上一个命令",
            "仪器软件未启动",
        ],
        "solution": "1. 确认 CHI 软件已打开且在前台\n2. 从 MicroHySeeker 重新初始化 DDE 连接\n3. 如无效，重启 CHI 软件",
        "auto_fixable": False,
    },
    "hardware.pump_stall": {
        "description": "泵堵转/不转",
        "common_causes": [
            "管路堵塞",
            "泵头卡住",
            "电机故障",
        ],
        "solution": "1. 检查管路是否有结晶或堵塞\n2. 手动转动泵头确认可自由旋转\n3. 检查泵电源连接",
        "auto_fixable": False,
    },
    "parameter.echem_out_of_range": {
        "description": "电化学参数超范围",
        "common_causes": [
            "电位设置超出仪器量程",
            "电流量程选择不当",
            "扫速过快",
        ],
        "solution": "1. 检查电位范围是否在 ±10V 内\n2. 调整电流灵敏度\n3. 降低扫速或减小电位窗口",
        "auto_fixable": True,  # 可自动调参重试
    },
}
```

---

## 九、开发清单（Week 2-3）

```
Week 2:
  ☐ tools/log_analysis.py 全部 8 函数
  ☐ ERROR_KNOWLEDGE_BASE 初始数据
  ☐ graph/state.py — DiagnosticsState
  ☐ graph/diagnostics_graph.py — 图定义
  ☐ agents/diagnostics_nodes.py — classify_issue, collect_evidence
  ☐ 单元测试: log_analysis 全覆盖

Week 3:
  ☐ agents/diagnostics_nodes.py — analyze_root_cause, search_solutions, recommend_actions
  ☐ agents/diagnostics_nodes.py — run_health_check
  ☐ agents/prompts.py — DIAGNOSTICS_SYSTEM_PROMPT
  ☐ skills/diagnostics/diagnose_failure.py (D1 Skill wrapper)
  ☐ skills/diagnostics/system_health_check.py (D2 Skill wrapper)
  ☐ 端到端测试: test_diagnostics_graph.py
  ☐ CLI: python -m autohyseeker.cli diagnose <run_dir>
  ☐ CLI: python -m autohyseeker.cli health-check
```

---

*此文档可直接作为 DiagnosticsExpert Agent 的开发执行依据。*

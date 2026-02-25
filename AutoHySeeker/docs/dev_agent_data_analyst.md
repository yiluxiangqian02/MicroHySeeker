# Agent A — DataAnalyst 开发指南

> 代号：DA | 优先级：P2 (Week 5-6) | 域：数据处理与分析
> 总体架构参考：[`langgraph_architecture.md`](langgraph_architecture.md) | Tool/Skill定义参考：[`skills_architecture.md`](skills_architecture.md)

---

## 一、Agent 概览

### 1.1 职责定位

DataAnalyst 是**电化学数据分析专家**：

- 单次实验 → 完整分析报告+图表+解读（A1）
- 多次实验 → 对比分析（A2）
- 跨天数据 → 趋势追踪（A3）
- 自然语言 → 数据查询（A4）

### 1.2 拥有的 Skills

| Skill | 名称 | LLM 角色 | 没有 LLM 能否运行 |
|-------|------|----------|-------------------|
| **A1** | `single_experiment_analysis` | 结果解读 | ⚠️ 降级（仅数值+图，无解读） |
| **A2** | `multi_experiment_comparison` | 对比总结 | ⚠️ 降级 |
| **A3** | `trend_tracking` | 趋势解读 | ⚠️ 降级 |
| **A4** | `natural_language_data_query` | NL→查询 | ❌ 不可运行 |

### 1.3 在系统中的位置

```
Orchestrator ──→ DataAnalyst        ← "帮我分析今天的实验"
ExperimentSupervisor ──→ DataAnalyst   ← C3 自适应模式中分析中间结果
```

**独立运行**：DA 不依赖任何其他 Agent，只依赖 Tools。

---

## 二、LangGraph Subgraph 设计

### 2.1 State 定义

```python
class AnalystState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 任务路由
    task: Literal["single_analysis", "comparison", "trend", "nl_query"]
    
    # 输入
    run_dirs: list[str]            # 要分析的实验目录列表
    query: str | None              # A4: 自然语言查询
    metric: str | None             # A3: 追踪指标
    date_range: tuple[str, str] | None  # A3: 日期范围
    
    # 中间结果
    raw_data: dict | None          # 读取的原始数据
    analysis_results: dict | None  # 分析结果（数值+指标）
    
    # 产出
    figures: list[str]             # 生成的图表路径列表
    report: str | None             # Markdown 分析报告
    interpretation: str | None     # LLM 自然语言解读
```

### 2.2 Graph 结构

```python
def build_analyst_graph():
    graph = StateGraph(AnalystState)
    
    graph.add_node("classify_task", classify_analysis_task)
    graph.add_node("gather_data", gather_data_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("visualize", visualize_node)
    graph.add_node("interpret", interpret_node)
    
    # A4 走特殊路径
    graph.add_node("nl_query", nl_query_node)
    
    graph.add_edge(START, "classify_task")
    graph.add_conditional_edges("classify_task", route_task, {
        "standard": "gather_data",  # A1/A2/A3
        "nl_query": "nl_query",     # A4
    })
    graph.add_edge("gather_data", "analyze")
    graph.add_edge("analyze", "visualize")
    graph.add_edge("visualize", "interpret")
    graph.add_edge("nl_query", "interpret")
    graph.add_edge("interpret", END)
    
    return graph.compile()
```

```
    START
      │
  classify_task
      │
   ┌──┴──┐
standard  nl_query
   │       │
gather   nl_query_node
 data      │
   │       │
analyze    │
   │       │
visualize  │
   │       │
   └──┬────┘
   interpret
      │
     END
```

---

## 三、节点函数设计

### 3.1 `classify_analysis_task` — 任务分类

```python
async def classify_analysis_task(state: AnalystState) -> dict:
    """
    根据输入判断走哪种分析流程。
    
    简单规则（不需要 LLM）：
    - 有 query → A4 (nl_query)
    - 1 个 run_dir → A1 (single)
    - 多个 run_dirs → A2 (comparison)
    - 有 metric + date_range → A3 (trend)
    """
    if state.get("query"):
        return {"task": "nl_query"}
    
    run_dirs = state.get("run_dirs", [])
    if state.get("metric"):
        return {"task": "trend"}
    elif len(run_dirs) == 1:
        return {"task": "single_analysis"}
    elif len(run_dirs) > 1:
        return {"task": "comparison"}
    
    return {"task": "single_analysis"}
```

### 3.2 `gather_data_node` — 数据收集

```python
async def gather_data_node(state: AnalystState) -> dict:
    """
    收集所有需要的实验数据。不需要 LLM。
    
    A1: 读单个实验的全部数据
    A2: 读多个实验的关键数据
    A3: 读时间范围内所有实验
    """
    task = state["task"]
    raw_data = {}
    
    if task == "single_analysis":
        run_dir = state["run_dirs"][0]
        raw_data = {
            "summary": data_reader.read_run_summary(run_dir),
            "plan": data_reader.read_experiment_plan(run_dir),
            "echem_files": [],
            "pump_ops": None,
        }
        
        for f in data_reader.list_echem_files(run_dir):
            df = data_reader.read_echem_csv(f["path"])
            raw_data["echem_files"].append({
                **f,
                "data": df,
            })
        
        try:
            raw_data["pump_ops"] = data_reader.read_pump_operations(run_dir)
        except FileNotFoundError:
            pass
    
    elif task == "comparison":
        raw_data = {"runs": []}
        for run_dir in state["run_dirs"]:
            run_data = {
                "run_dir": run_dir,
                "summary": data_reader.read_run_summary(run_dir),
                "echem_files": [],
            }
            for f in data_reader.list_echem_files(run_dir):
                df = data_reader.read_echem_csv(f["path"])
                run_data["echem_files"].append({**f, "data": df})
            raw_data["runs"].append(run_data)
    
    elif task == "trend":
        runs = data_reader.list_experiment_runs(
            data_dir=config.microhyseeker_data_dir,
            date_range=state.get("date_range"),
        )
        raw_data = {"runs": runs, "metric": state["metric"]}
    
    return {"raw_data": raw_data}
```

### 3.3 `analyze_node` — 数据分析

```python
async def analyze_node(state: AnalystState) -> dict:
    """
    对收集的数据执行分析。不需要 LLM — 纯算法。
    
    根据电化学技术选择对应的分析函数：
    - CV → detect_cv_peaks
    - LSV → calculate_tafel_slope
    - EIS → fit_eis_circuit
    - i-t → extract_steady_state, calculate_charge
    - OCPT → extract_steady_state
    """
    task = state["task"]
    raw_data = state["raw_data"]
    results = {}
    
    if task == "single_analysis":
        results["echem_analysis"] = []
        for echem_file in raw_data.get("echem_files", []):
            df = echem_file["data"]
            technique = echem_file.get("technique", "")
            
            analysis = {
                "file": echem_file["path"],
                "technique": technique,
                "quality": echem_analysis.assess_data_quality(df, technique),
            }
            
            if technique == "CV":
                analysis["peaks"] = echem_analysis.detect_cv_peaks(df)
            elif technique == "LSV":
                analysis["tafel"] = echem_analysis.calculate_tafel_slope(df)
            elif technique == "EIS":
                analysis["eis_fit"] = echem_analysis.fit_eis_circuit(df)
            elif technique in ("i-t", "CA"):
                analysis["steady_state"] = echem_analysis.extract_steady_state(df)
                analysis["charge"] = echem_analysis.calculate_charge(df)
            elif technique == "OCPT":
                analysis["steady_state"] = echem_analysis.extract_steady_state(df)
            
            results["echem_analysis"].append(analysis)
        
        # 泵操作摘要
        if raw_data.get("pump_ops") is not None:
            results["pump_summary"] = _summarize_pump_ops(raw_data["pump_ops"])
    
    elif task == "comparison":
        results["comparison_table"] = _build_comparison_table(raw_data["runs"])
    
    elif task == "trend":
        results["trend_data"] = _extract_trend(raw_data["runs"], raw_data["metric"])
    
    return {"analysis_results": results}
```

### 3.4 `visualize_node` — 生成图表

```python
async def visualize_node(state: AnalystState) -> dict:
    """
    生成分析图表。不需要 LLM。
    """
    task = state["task"]
    results = state["analysis_results"]
    figures = []
    
    if task == "single_analysis":
        for item in results.get("echem_analysis", []):
            technique = item.get("technique", "")
            df = ...  # 从 raw_data 获取
            
            if technique == "CV":
                fig_path = visualization.plot_cv(df, peaks=item.get("peaks"))
                figures.append(fig_path)
            elif technique == "EIS":
                fig_path = visualization.plot_eis_nyquist(df, fit=item.get("eis_fit"))
                figures.append(fig_path)
            elif technique in ("i-t", "CA", "OCPT"):
                fig_path = visualization.plot_it_curve(df)
                figures.append(fig_path)
    
    elif task == "comparison":
        fig_path = visualization.plot_comparison_bar(results["comparison_table"])
        figures.append(fig_path)
    
    elif task == "trend":
        fig_path = visualization.plot_trend(results["trend_data"])
        figures.append(fig_path)
    
    return {"figures": figures}
```

### 3.5 `interpret_node` — LLM 解读

```python
async def interpret_node(state: AnalystState) -> dict:
    """
    ★ LLM 核心价值：将数值结果转化为人类可理解的自然语言解读。
    
    没有 LLM 也能运行 — 直接返回结构化数据，无解读文本。
    """
    if not llm_available:
        # 降级：生成模板报告
        return {"report": _template_report(state), "interpretation": None}
    
    prompt = ANALYSIS_INTERPRETATION_PROMPT.format(
        task=state["task"],
        results=json.dumps(state["analysis_results"], ensure_ascii=False, indent=2, default=str),
        figures=state.get("figures", []),
    )
    
    interpretation = await llm_client.chat(
        system=ANALYST_SYSTEM_PROMPT,
        user=prompt,
    )
    
    # 组合完整报告
    report = _build_full_report(state, interpretation)
    
    return {"report": report, "interpretation": interpretation}
```

### 3.6 `nl_query_node` — 自然语言查询 (A4)

```python
async def nl_query_node(state: AnalystState) -> dict:
    """
    A4: 自然语言 → 数据查询。
    
    ★ 完全依赖 LLM — 这是 AI 最核心的交互方式。
    
    流程：
    1. LLM 理解问题 → 生成查询计划（要读哪些数据、做什么过滤）
    2. 执行查询（调 data_reader + echem_analysis Tools）
    3. LLM 组织答案
    
    实现方式：LLM Tool Calling 循环
    """
    query = state["query"]
    
    # 给 LLM 提供可用的 Tools
    tools = registry.get_openai_tools(categories=["data", "analysis"])
    
    messages = [
        SystemMessage(content=ANALYST_SYSTEM_PROMPT),
        HumanMessage(content=f"请回答: {query}"),
    ]
    
    # Tool Calling 循环
    max_rounds = 5
    for _ in range(max_rounds):
        response = await llm_client.chat_with_tools(
            messages=messages,
            tools=tools,
        )
        
        if response.tool_calls:
            # 执行 Tool 调用
            for tool_call in response.tool_calls:
                result = registry.call(
                    tool_call.function.name,
                    **json.loads(tool_call.function.arguments)
                )
                messages.append(ToolMessage(
                    content=json.dumps(result, ensure_ascii=False, default=str),
                    tool_call_id=tool_call.id,
                ))
        else:
            # 没有更多 Tool 调用，LLM 直接回答
            return {
                "report": response.content,
                "interpretation": response.content,
            }
    
    return {"report": "查询超过最大轮次限制", "interpretation": None}
```

---

## 四、System Prompt

```python
ANALYST_SYSTEM_PROMPT = """你是 AutoHySeeker 系统的数据分析专家（DataAnalyst）。

你的专业领域：
- 电化学分析方法：CV（循环伏安法）、LSV（线性扫描伏安法）、EIS（电化学阻抗谱）、i-t（计时电流法）、OCPT（开路电位）等
- 关键指标：峰电流(Ip)、峰电位(Ep)、半波电位(E1/2)、峰电位差(ΔEp)、Tafel斜率、电荷转移电阻(Rct)、扩散系数、库伦效率等
- 数据质量评估：噪声水平、基线漂移、异常检测

你的分析框架：
1. 先概述实验基本信息（名称、日期、步骤数、成功/失败）
2. 逐步骤分析电化学数据，提取关键特征
3. 评估数据质量
4. 综合解读：这些数据说明了什么化学/电化学现象
5. 如有多个实验，做对比分析，指出显著差异

MicroHySeeker 平台的数据特点：
- 数据目录结构: data/{date}/{timestamp}_{name}/
- 电化学数据: echem/step_N_{technique}.csv（CSV格式，有#注释头）
- 运行摘要: run_summary.json（包含状态、步骤详情）
- 泵操作: pump/pump_operations.csv
- 运行日志: run_log.log

输出要求：
- 使用 Markdown 格式
- 数值用合适的单位和有效数字
- 图表引用使用 [图N] 标记
- 如果数据质量有问题，要明确说明
"""

ANALYSIS_INTERPRETATION_PROMPT = """请对以下电化学实验分析结果进行自然语言解读。

## 分析类型
{task}

## 分析结果（数值）
{results}

## 生成的图表
{figures}

请生成：
1. 实验概况（一段话）
2. 关键发现（列表）
3. 数据质量评估
4. 结论与建议
"""
```

---

## 五、依赖的 Tools

| Tool 函数 | 所属模块 | 在哪个节点使用 |
|-----------|---------|--------------|
| `read_run_summary` | data_reader | gather_data |
| `read_experiment_plan` | data_reader | gather_data |
| `list_echem_files` | data_reader | gather_data |
| `read_echem_csv` | data_reader | gather_data |
| `read_pump_operations` | data_reader | gather_data |
| `list_experiment_runs` | data_reader | gather_data (A3) |
| `detect_cv_peaks` | echem_analysis | analyze |
| `calculate_tafel_slope` | echem_analysis | analyze |
| `fit_eis_circuit` | echem_analysis | analyze |
| `assess_data_quality` | echem_analysis | analyze |
| `extract_steady_state` | echem_analysis | analyze |
| `calculate_charge` | echem_analysis | analyze |
| `detect_anomalies` | echem_analysis | analyze |
| `plot_cv` | visualization | visualize |
| `plot_eis_nyquist` | visualization | visualize |
| `plot_it_curve` | visualization | visualize |
| `plot_trend` | visualization | visualize |
| `plot_comparison_bar` | visualization | visualize |
| `plot_multi_cv` | visualization | visualize |
| `render_markdown_report` | report_generator | interpret |

---

## 六、与其他 Agent 的交互

| 交互 | 场景 | 数据流向 |
|------|------|---------|
| ES → DA | C3 自适应循环中分析中间结果 | run_dir → analysis report |
| DA → KM | 分析时检索相关知识 | query → RAG results (Phase 3) |

DA 是最独立的 Agent，Phase 2 中不需要其他 Agent 支持。

---

## 七、前置依赖（Phase 1 提供）

DA 依赖的 Tools 有部分在 Phase 1 已实现：

| Tool 模块 | Phase 1 已实现 | Phase 2 新增 |
|-----------|---------------|-------------|
| data_reader | ✅ 全部 8 函数 | — |
| log_analysis | ✅ 全部 8 函数 | — |
| visualization | ⚠️ 基础版（CV/i-t） | EIS Nyquist/Bode, Tafel, 对比图, 趋势图 |
| echem_analysis | ❌ | ✅ 全部 8 函数 |
| report_generator | ⚠️ 基础版 | 完整模板 |

---

## 八、开发清单（Week 5-6）

```
Week 5:
  ☐ tools/echem_analysis.py — 全部 8 分析函数
      detect_cv_peaks, calculate_tafel_slope, fit_eis_circuit,
      calculate_diffusion_coeff, assess_data_quality, detect_anomalies,
      calculate_charge, extract_steady_state
  ☐ tools/visualization.py — 补全所有图表类型
  ☐ graph/state.py — AnalystState
  ☐ graph/analyst_graph.py — 图定义
  ☐ agents/analyst_nodes.py — classify, gather_data, analyze, visualize
  ☐ 单元测试: echem_analysis 全覆盖（CV/LSV/EIS/i-t/OCPT）

Week 6:
  ☐ agents/analyst_nodes.py — interpret (LLM), nl_query (A4)
  ☐ agents/prompts.py — ANALYST_SYSTEM_PROMPT
  ☐ skills/data_analysis/single_experiment_analysis.py (A1)
  ☐ skills/data_analysis/multi_experiment_comparison.py (A2)
  ☐ skills/data_analysis/trend_tracking.py (A3)
  ☐ skills/data_analysis/nl_data_query.py (A4)
  ☐ DataAnalyst Agent（Orchestrator 路由集成）
  ☐ CLI: python -m autohyseeker.cli analyze <run_dir>
  ☐ CLI: python -m autohyseeker.cli compare <dir1> <dir2> ...
  ☐ CLI: python -m autohyseeker.cli ask "..."
```

---

## 九、注意事项

### 9.1 电化学分析的技术选择

不同电化学技术需要不同分析方法，映射表：

| 技术 | 分析函数 | 关键指标 |
|------|---------|---------|
| CV | `detect_cv_peaks` | Ip_ox, Ip_red, Ep_ox, Ep_red, ΔEp, Ip_ratio |
| LSV | `calculate_tafel_slope` | Tafel slope, exchange current, overpotential |
| EIS | `fit_eis_circuit` | Rs, Rct, Cdl, Warburg, chi² |
| i-t / CA | `extract_steady_state`, `calculate_charge` | I_ss, t_steady, Q |
| OCPT | `extract_steady_state` | E_oc, t_stable |

### 9.2 CSV 数据格式

MicroHySeeker 的 echem CSV 格式（已优化后）：
```csv
# technique: CV
# step_index: 2
# timestamp: 2026-02-13T15:30:45
# params: {"e_init": 0.0, "e_high": 0.5, "e_low": -0.5, "scan_rate": 0.1}
Potential/V,Current/A
-0.500,1.234e-06
-0.495,1.245e-06
...
```

`data_reader.read_echem_csv` 需要正确处理 `#` 注释行。

### 9.3 降级策略

```
没有 LLM:
  - A1/A2/A3: 返回结构化数据 + 图表，无自然语言解读
  - A4: 完全不可用

没有某些分析库 (e.g., impedance for EIS):
  - 跳过 EIS 拟合，返回 "EIS 拟合需要 impedance 库"
```

---

*此文档可直接作为 DataAnalyst Agent 的开发执行依据。*

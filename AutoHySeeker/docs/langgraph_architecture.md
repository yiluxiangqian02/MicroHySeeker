# AutoHySeeker — LangGraph 多 Agent 架构设计

> 2026-02-25 | v1.1（2026-02-26 重构：提取共享内容至独立文档）
> 关联文档：[architecture_overview.md](architecture_overview.md) · [skills_architecture.md](skills_architecture.md) · [project_plan.md](project_plan.md)
> Agent 开发指南：各 `dev_agent_*.md`
>
> **本文档职责**：State 定义、Graph 拓扑、条件边、Checkpointing（唯一源）
> 项目结构/依赖/路线图 → [project_plan.md](project_plan.md)
> 系统总览/四层架构 → [architecture_overview.md](architecture_overview.md)

---

## 一、架构总览

### 1.1 为什么用 LangGraph

| 需求 | 原始方案（手写 Orchestrator） | LangGraph |
|------|------------------------------|-----------|
| C→D→C 闭环 | 需自己写状态机+条件分支 | **StateGraph 原生支持条件边** |
| 实验执行中断恢复 | 无 | **Checkpointing — 可恢复到任意节点** |
| Human-in-the-loop | 需手写轮询 | **内置 interrupt/resume** |
| 多 Agent 协作 | 手写 Orchestrator 路由 | **Supervisor + Subgraph 模式** |
| 可观测性 | printf 调试 | **LangSmith 追踪每步** |
| 流式输出 | 需自己实现 | **原生 stream_mode** |

### 1.2 架构与拓扑

> 四层架构图、系统拓扑图已移至 → [architecture_overview.md](architecture_overview.md) §一/§二

---

## 二、Agent 清单与职责

### 2.1 Agent 总表

| # | Agent 名称 | 代号 | 职责定位 | 拥有的 Skills | LLM 必要性 |
|---|-----------|------|---------|--------------|------------|
| 0 | **Orchestrator** | ORCH | 顶层路由，理解用户意图，分配给对应 Agent | 无 Skill（纯路由） | ✅ 必须：意图分类 |
| 1 | **DataAnalyst** | DA | 电化学数据分析专家，出图、出报告、做对比、回答数据问题 | A1, A2, A3, A4 | ✅ 必须：数据解读、NL查询 |
| 2 | **ExperimentDesigner** | ED | 实验方案设计师，NL→方案、参数优化、方案审查 | B1, B2, B3, B4 | ✅ 必须：NL→结构化方案 |
| 3 | **ExperimentSupervisor** | ES | 实验执行管家，排程→执行→监控→异常处理→结果保存 | C1, C2, C3 | ✅ 必须：执行决策 |
| 4 | **DiagnosticsExpert** | DX | 故障诊断医生，找原因、给方案、引导排查 | D1, D2, D3 | ✅ 必须：根因推理 |
| 5 | **KnowledgeManager** | KM | 知识库管理员，文档入库、知识问答、实验归档 | E1, E2, E3 | ⚠️ 部分需要：QA必须，入库可选 |

### 2.2 每个 Skill 是否需要 LLM

| Skill | 名称 | LLM 角色 | 没有 LLM 能否运行 |
|-------|------|----------|-------------------|
| A1 | 单次实验分析 | 自然语言解读分析结果 | ⚠️ 降级运行：只出数值+图表，无解读 |
| A2 | 多实验对比 | 对比结论总结 | ⚠️ 降级运行 |
| A3 | 趋势追踪 | 趋势解读 | ⚠️ 降级运行 |
| A4 | NL数据查询 | 理解自然语言→生成查询 | ❌ 不可运行 |
| B1 | NL→方案 | 自然语言→实验JSON | ❌ 不可运行 |
| B2 | 参数优化 | 解释优化建议 | ⚠️ 降级运行（Optuna纯算法） |
| B3 | 方案审查 | 领域知识安全审查 | ⚠️ 降级运行（仅规则校验） |
| B4 | 文献复现 | 文献方法提取+适配 | ❌ 不可运行 |
| C1 | 实验监控 | 异常解读 | ⚠️ 降级运行（规则检查） |
| C2 | 排程 | 优化建议 | ⚠️ 降级运行（启发式排序） |
| C3 | 自适应闭环 | 关键决策（继续/终止/调整） | ❌ 不可运行 |
| D1 | 失败诊断 | 根因推理+解决建议 | ⚠️ 降级运行（仅错误分类） |
| D2 | 健康检查 | 综合评估报告 | ⚠️ 降级运行（仅分值） |
| D3 | 交互排错 | 对话式引导 | ❌ 不可运行 |
| E1 | 知识库构建 | 文档摘要 | ✅ 可运行（不生成摘要） |
| E2 | 知识问答 | RAG QA | ❌ 不可运行 |
| E3 | 自动归档 | 归档摘要 | ✅ 可运行（不生成摘要） |

**结论**：
- **4 个 Skill 完全依赖 LLM**：A4、B1、B4、C3、D3、E2（核心是 NL 理解）
- **9 个 Skill 可降级运行**：AI 增强但不强依赖
- **2 个 Skill 不需要 LLM**：E1、E3（纯数据处理）

### 2.3 Agent 间调用关系

```
Orchestrator
  ├─→ DataAnalyst         独立运行
  ├─→ ExperimentDesigner  可调用 KnowledgeManager (E2 for RAG)
  ├─→ ExperimentSupervisor
  │     ├─→ DiagnosticsExpert  (C 执行出错时调用)
  │     ├─→ DataAnalyst        (C 需要分析中间结果时)
  │     └─→ ExperimentDesigner (C3 自适应需要重新设计实验)
  ├─→ DiagnosticsExpert   可调用 KnowledgeManager (E2 for error KB)
  └─→ KnowledgeManager    独立运行

跨 Agent 调用只发生在：
  1. ES → DX：执行出错 → 诊断（最常见、最关键）
  2. ES → DA：监控中需要分析中间数据
  3. ES → ED：C3 自适应需要生成新方案
  4. ED → KM：设计方案时查文献/知识
  5. DX → KM：诊断时查错误解决方案库
```

---

## 三、LangGraph State 设计

### 3.1 全局共享 State

```python
# src/graph/state.py
from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AutoHySeekerState(TypedDict):
    """顶层 Orchestrator State"""
    # 对话
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 路由
    current_agent: str | None          # 当前活跃 Agent
    task_type: str | None              # "analyze"|"design"|"execute"|"diagnose"|"knowledge"
    
    # 上下文（跨 Agent 共享）
    active_run_dir: str | None         # 当前关注的实验目录
    active_plan: dict | None           # 当前实验方案
    
    # 结果收集
    agent_results: dict                # {agent_name: SkillResult}
    
    # 控制
    needs_human_approval: bool         # 是否需要人工确认
    final_response: str | None         # 最终回复给用户的内容
```

### 3.2 ExperimentSupervisor 专用 State（最复杂）

```python
class SupervisorState(TypedDict):
    """实验执行管家子图 State — 体现 C→D→C 闭环"""
    messages: Annotated[list[BaseMessage], add_messages]
    
    # === 计划 ===
    experiment_plan: dict              # 完整实验方案 JSON
    schedule: list[dict]               # 排程后的执行顺序
    
    # === 执行状态 ===
    status: Literal[
        "validating",      # 校验方案
        "scheduling",      # 排程
        "executing",       # 执行中
        "monitoring",      # 监控中
        "diagnosing",      # 诊断中（调用 D）
        "deciding",        # 决策中（retry/skip/abort）
        "saving",          # 保存结果
        "completed",       # 完成
        "aborted"          # 中止
    ]
    current_step_index: int            # 当前执行到第几步
    
    # === 执行结果 ===
    step_results: list[dict]           # 每步结果
    current_step_data: dict | None     # 当前步骤的运行数据
    
    # === 错误处理 ===
    error_info: dict | None            # 当前错误信息
    diagnosis_result: dict | None      # D agent 的诊断结果
    retry_count: int                   # 当前步骤重试次数
    max_retries: int                   # 最大重试次数（默认 2）
    
    # === 最终产出 ===
    run_dir: str | None                # 实验数据保存目录
    final_report: str | None           # 最终实验报告
```

### 3.3 其他 Agent State

```python
class AnalystState(TypedDict):
    """DataAnalyst 子图 State"""
    messages: Annotated[list[BaseMessage], add_messages]
    task: Literal["single_analysis", "comparison", "trend", "nl_query"]
    run_dirs: list[str]
    analysis_results: dict | None
    figures: list[str]                 # 生成的图表路径
    report: str | None

class DesignerState(TypedDict):
    """ExperimentDesigner 子图 State"""
    messages: Annotated[list[BaseMessage], add_messages]
    task: Literal["generate", "optimize", "review", "replicate"]
    user_description: str | None
    experiment_plan: dict | None
    validation_result: dict | None
    review_passed: bool
    iteration_count: int               # 设计→审查 迭代次数

class DiagnosticsState(TypedDict):
    """DiagnosticsExpert 子图 State"""
    messages: Annotated[list[BaseMessage], add_messages]
    task: Literal["diagnose", "health_check", "troubleshoot"]
    run_dir: str | None
    symptom: str | None
    error_info: dict | None
    diagnosis: dict | None
    recommended_actions: list[dict]

class KnowledgeState(TypedDict):
    """KnowledgeManager 子图 State"""
    messages: Annotated[list[BaseMessage], add_messages]
    task: Literal["ingest", "query", "archive"]
    source_path: str | None
    query: str | None
    results: dict | None
```

---

## 四、Graph 定义

### 4.1 顶层 Orchestrator Graph

```python
# src/graph/orchestrator.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def build_orchestrator_graph():
    graph = StateGraph(AutoHySeekerState)
    
    # 节点
    graph.add_node("router", router_node)           # LLM 意图分类
    graph.add_node("analyst", analyst_subgraph)      # DataAnalyst 子图
    graph.add_node("designer", designer_subgraph)    # ExperimentDesigner 子图
    graph.add_node("supervisor", supervisor_subgraph)# ExperimentSupervisor 子图
    graph.add_node("diagnostics", diagnostics_subgraph)
    graph.add_node("knowledge", knowledge_subgraph)
    graph.add_node("synthesize", synthesize_node)    # 汇总结果给用户
    
    # 边
    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_to_agent, {
        "analyst": "analyst",
        "designer": "designer",
        "supervisor": "supervisor",
        "diagnostics": "diagnostics",
        "knowledge": "knowledge",
        "direct_response": "synthesize",  # 简单问题直接回答
    })
    
    # 所有 Agent 完成后汇总
    graph.add_edge("analyst", "synthesize")
    graph.add_edge("designer", "synthesize")
    graph.add_edge("supervisor", "synthesize")
    graph.add_edge("diagnostics", "synthesize")
    graph.add_edge("knowledge", "synthesize")
    
    graph.add_edge("synthesize", END)
    
    return graph.compile(checkpointer=MemorySaver())


def route_to_agent(state: AutoHySeekerState) -> str:
    """根据 router_node 设置的 task_type 路由"""
    return state["current_agent"] or "direct_response"
```

### 4.2 ★ ExperimentSupervisor Subgraph（核心闭环）

这是整个系统最关键的图——体现了"执行→监控→出错→诊断→决策→重试/跳过/中止"的闭环。

```python
# src/graph/supervisor_graph.py
from langgraph.graph import StateGraph, START, END

def build_supervisor_graph():
    graph = StateGraph(SupervisorState)
    
    # === 节点 ===
    graph.add_node("validate_plan", validate_plan_node)       # 校验实验方案
    graph.add_node("schedule", schedule_node)                 # 智能排程 (C2)
    graph.add_node("execute_step", execute_step_node)         # 执行当前步骤
    graph.add_node("monitor_step", monitor_step_node)         # 监控+质量评估 (C1)
    graph.add_node("handle_success", handle_success_node)     # 成功：保存结果
    graph.add_node("diagnose_failure", diagnose_failure_node) # 失败：调用 D1
    graph.add_node("decide_action", decide_action_node)       # LLM 决策：重试/跳过/中止
    graph.add_node("save_results", save_results_node)         # 保存所有结果
    graph.add_node("generate_report", generate_report_node)   # 生成实验报告
    
    # === 边 ===
    graph.add_edge(START, "validate_plan")
    
    # 校验 → 通过则排程，不通过则结束
    graph.add_conditional_edges("validate_plan", check_plan_valid, {
        "valid": "schedule",
        "invalid": END,             # 直接返回校验错误
    })
    
    graph.add_edge("schedule", "execute_step")
    graph.add_edge("execute_step", "monitor_step")
    
    # 监控 → 成功/失败
    graph.add_conditional_edges("monitor_step", check_step_result, {
        "success": "handle_success",
        "failure": "diagnose_failure",
    })
    
    # 成功 → 还有步骤? → 继续/完成
    graph.add_conditional_edges("handle_success", check_more_steps, {
        "more": "execute_step",
        "done": "save_results",
    })
    
    # 诊断 → 决策
    graph.add_edge("diagnose_failure", "decide_action")
    
    # 决策 → 重试/跳过/中止
    graph.add_conditional_edges("decide_action", get_decision, {
        "retry": "execute_step",     # ← C→D→C 闭环的关键
        "skip": "handle_success",    # 跳过当前步骤继续
        "abort": "save_results",     # 中止整个实验
    })
    
    # 保存 → 报告 → 结束
    graph.add_edge("save_results", "generate_report")
    graph.add_edge("generate_report", END)
    
    return graph.compile()
```

**可视化此图**：

```
         ┌──── START ────┐
         │               │
    ┌────▼─────┐         │
    │ validate │         │
    │ plan     │         │
    └────┬─────┘         │
    valid│    invalid─────┘──→ END
         │
    ┌────▼─────┐
    │ schedule │
    └────┬─────┘
         │
    ┌────▼──────────┐◄─── retry ──┐
    │ execute_step  │              │
    └────┬──────────┘              │
         │                         │
    ┌────▼──────────┐              │
    │ monitor_step  │              │
    └────┬─────┬────┘              │
  success│     │failure            │
         │     │                   │
    ┌────▼───┐ ┌──▼──────────┐     │
    │handle  │ │ diagnose    │     │
    │success │ │ failure (D1)│     │
    └──┬──┬──┘ └──────┬──────┘     │
  more │  │done       │            │
       │  │    ┌──────▼──────┐     │
       │  │    │ decide      │     │
       │  │    │ action      │     │
       │  │    └──┬────┬──┬──┘     │
       │  │  retry│skip│  │abort   │
       │  │       │    │  │        │
       │  │    ┌──┘  ┌─┘  │        │
       │  │    │     │    │        │
       │  │    └─────┼────┼────────┘
       │  │          │    │
       │  │   ┌──────▼────▼──┐
       │  └──►│ save_results │
       │      └──────┬───────┘
       │             │
       │      ┌──────▼────────┐
       │      │generate_report│
       │      └──────┬────────┘
       │             │
       └─────────────┤
                     END
```

### 4.3 其他 Agent Subgraph 概要

#### DataAnalyst Subgraph
```python
def build_analyst_graph():
    graph = StateGraph(AnalystState)
    graph.add_node("classify_task", classify_analysis_task)   # 判断A1/A2/A3/A4
    graph.add_node("gather_data", gather_data_node)           # 收集实验数据
    graph.add_node("analyze", analyze_node)                   # 执行分析 Skill
    graph.add_node("visualize", visualize_node)               # 生成图表
    graph.add_node("interpret", interpret_node)               # LLM 解读
    
    graph.add_edge(START, "classify_task")
    graph.add_edge("classify_task", "gather_data")
    graph.add_edge("gather_data", "analyze")
    graph.add_edge("analyze", "visualize")
    graph.add_edge("visualize", "interpret")
    graph.add_edge("interpret", END)
    return graph.compile()
```

#### ExperimentDesigner Subgraph
```python
def build_designer_graph():
    graph = StateGraph(DesignerState)
    graph.add_node("understand_intent", understand_intent_node)  # NL→结构化意图
    graph.add_node("search_knowledge", search_knowledge_node)    # RAG 检索参考
    graph.add_node("generate_plan", generate_plan_node)          # 生成方案 (B1)
    graph.add_node("validate_plan", validate_plan_node)          # 校验+审查 (B3)
    graph.add_node("output_plan", output_plan_node)              # 输出方案
    
    graph.add_edge(START, "understand_intent")
    graph.add_edge("understand_intent", "search_knowledge")
    graph.add_edge("search_knowledge", "generate_plan")
    graph.add_edge("generate_plan", "validate_plan")
    graph.add_conditional_edges("validate_plan", check_review, {
        "passed": "output_plan",
        "needs_revision": "generate_plan",   # 循环修正
    })
    graph.add_edge("output_plan", END)
    return graph.compile()
```

#### DiagnosticsExpert Subgraph
```python
def build_diagnostics_graph():
    graph = StateGraph(DiagnosticsState)
    graph.add_node("classify_issue", classify_issue_node)        # 分类问题
    graph.add_node("collect_evidence", collect_evidence_node)    # 收集证据
    graph.add_node("analyze_root_cause", analyze_root_cause_node)# 根因分析
    graph.add_node("search_solutions", search_solutions_node)    # RAG 搜索方案
    graph.add_node("recommend_actions", recommend_actions_node)  # 给出建议
    
    graph.add_edge(START, "classify_issue")
    graph.add_edge("classify_issue", "collect_evidence")
    graph.add_edge("collect_evidence", "analyze_root_cause")
    graph.add_edge("analyze_root_cause", "search_solutions")
    graph.add_edge("search_solutions", "recommend_actions")
    graph.add_edge("recommend_actions", END)
    return graph.compile()
```

---

## 五、关键设计决策

### 5.1 Phase 1 的"模拟执行"模式

Phase 1 (CD构建期) 不需要实时 IPC，采用**后分析模式**：

```python
# Phase 1 的 execute_step_node — 读取已有数据（模拟执行）
async def execute_step_node_phase1(state: SupervisorState) -> SupervisorState:
    """Phase 1: 不真正执行实验，而是读取已有的实验数据"""
    run_dir = state["run_dir"]
    step_index = state["current_step_index"]
    
    # 从已有数据目录读取该步骤的结果
    step_data = read_step_data(run_dir, step_index)
    
    return {**state, "current_step_data": step_data, "status": "monitoring"}

# Phase 4 的 execute_step_node — 真正控制 MicroHySeeker
async def execute_step_node_phase4(state: SupervisorState) -> SupervisorState:
    """Phase 4: 通过 IPC 真正执行实验"""
    plan = state["experiment_plan"]
    step_index = state["current_step_index"]
    
    # 通过 WebSocket 发送执行命令
    await experiment_control.load_experiment(plan)
    await experiment_control.start_experiment()
    
    # 等待完成，收集数据
    result = await experiment_control.wait_for_completion(timeout=3600)
    
    return {**state, "current_step_data": result, "status": "monitoring"}
```

### 5.2 Human-in-the-loop 集成

对于关键决策点，可以暂停等待用户确认：

```python
# 在 decide_action 节点中
async def decide_action_node(state: SupervisorState) -> SupervisorState:
    diagnosis = state["diagnosis_result"]
    
    if diagnosis["severity"] == "critical":
        # 严重问题：暂停，等待人工确认
        raise NodeInterrupt(
            f"严重错误: {diagnosis['root_cause']}\n"
            f"建议操作: {diagnosis['recommended_actions']}\n"
            f"请确认: retry / skip / abort ?"
        )
    
    # 非严重问题：LLM 自动决策
    decision = await llm_decide(state)
    return {**state, "decision": decision}
```

### 5.3 Checkpointing — 实验恢复

```python
# 使用持久化 checkpointer
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("./data/checkpoints.db")
graph = build_supervisor_graph().compile(checkpointer=checkpointer)

# 每个实验用 thread_id 追踪
config = {"configurable": {"thread_id": f"exp_{run_id}"}}

# 中断后恢复
state = graph.get_state(config)
if state.next:  # 有待执行的节点
    graph.invoke(None, config)  # 从中断处继续
```

---

## 六、项目结构 / 依赖 / 路线图

> 已移至 → [project_plan.md](project_plan.md)
> 包含：项目目录结构、pyproject.toml、配置文件示例、四阶段详细路线图、Skill↔Tool↔库关系表

---

## 七、Agent 开发文档索引（原§九）

每个 Agent 有独立的开发指南文档，包含详细的节点实现、Prompt 设计、测试计划：

| Agent | 开发文档 | 优先级 |
|-------|---------|--------|
| Orchestrator | [`dev_agent_orchestrator.md`](dev_agent_orchestrator.md) | P1 (Week 4) |
| DataAnalyst (A) | [`dev_agent_data_analyst.md`](dev_agent_data_analyst.md) | P2 (Week 5-6) |
| ExperimentDesigner (B) | [`dev_agent_experiment_designer.md`](dev_agent_experiment_designer.md) | P3 (Week 7-9) |
| ExperimentSupervisor (C) | [`dev_agent_experiment_supervisor.md`](dev_agent_experiment_supervisor.md) | P1 (Week 3-4) |
| DiagnosticsExpert (D) | [`dev_agent_diagnostics_expert.md`](dev_agent_diagnostics_expert.md) | P1 (Week 2-3) |
| KnowledgeManager (E) | [`dev_agent_knowledge_manager.md`](dev_agent_knowledge_manager.md) | P3 (Week 7) |

---

## 八、注意事项

### 8.1 LangGraph 版本策略
- 使用 `langgraph>=0.2` 稳定 API
- 避免使用实验性功能（如 `langgraph-supervisor` 预构建组件暂不使用，自己定义图更可控）
- Checkpointer 初期用 `MemorySaver`（内存），Phase 2 切 `SqliteSaver`

### 8.2 LLM 模型选择
- **意图路由 (Orchestrator)**：gpt-4o-mini 即可（简单分类）
- **数据分析解读 (DA)**：gpt-4o（需要领域知识）
- **方案生成 (ED)**：gpt-4o（复杂推理）
- **执行决策 (ES)**：gpt-4o（关键决策）
- **故障诊断 (DX)**：gpt-4o（因果推理）
- **知识问答 (KM)**：gpt-4o-mini（RAG 检索+简单生成）

可随时切换到本地模型（Qwen2.5/DeepSeek）通过 `llm_config.toml` 配置。

### 8.3 测试策略
- **Tool 层**：纯单元测试（不需要 LLM）
- **Skill 层**：集成测试（可 mock LLM）
- **Graph 层**：端到端测试（用真实 LLM 或 LangSmith 录放）
- **固定数据**：用 `data/2026-02-13/` 作为黄金测试数据集

### 8.4 成本控制
- 所有 LLM 调用经过 `llm_client.py` 统一管理
- 内置 token 统计 + 成本估算
- 支持 LLM 响应缓存（相同输入不重复调用）
- 非关键路径优先使用 gpt-4o-mini

---

*本文档是 LangGraph Graph/State/条件边的唯一定义源。项目结构与路线图 → [project_plan.md](project_plan.md)，系统总览 → [architecture_overview.md](architecture_overview.md)。*

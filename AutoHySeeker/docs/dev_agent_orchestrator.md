# Orchestrator — 顶层路由 开发指南

> 代号：ORCH | 优先级：P1 (Week 4 基础版) → P3 (Week 9 完整版)
> 总体架构参考：[`langgraph_architecture.md`](langgraph_architecture.md)

---

## 一、Agent 概览

### 1.1 职责定位

Orchestrator 是**系统的唯一入口**，负责：

1. 接收用户自然语言输入
2. 理解意图，分类任务类型
3. 路由到对应的专家 Agent
4. 汇总 Agent 结果返回给用户
5. 处理多轮对话上下文

### 1.2 不拥有任何 Skill

Orchestrator 本身**不做分析、不做诊断、不做设计**——只做路由和汇总。

---

## 二、LangGraph 设计

### 2.1 Graph 结构

```python
def build_orchestrator_graph():
    graph = StateGraph(AutoHySeekerState)
    
    graph.add_node("router", router_node)
    graph.add_node("analyst", analyst_subgraph)
    graph.add_node("designer", designer_subgraph)
    graph.add_node("supervisor", supervisor_subgraph)
    graph.add_node("diagnostics", diagnostics_subgraph)
    graph.add_node("knowledge", knowledge_subgraph)
    graph.add_node("synthesize", synthesize_node)
    
    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_to_agent, {
        "analyst": "analyst",
        "designer": "designer",
        "supervisor": "supervisor",
        "diagnostics": "diagnostics",
        "knowledge": "knowledge",
        "direct_response": "synthesize",
    })
    
    for agent_name in ["analyst", "designer", "supervisor", "diagnostics", "knowledge"]:
        graph.add_edge(agent_name, "synthesize")
    
    graph.add_edge("synthesize", END)
    
    return graph.compile(checkpointer=MemorySaver())
```

### 2.2 路由逻辑

```python
ROUTING_PROMPT = """将用户请求分类到以下类别之一：

1. analyst — 数据分析：分析实验、对比实验、查看趋势、数据查询
   关键词：分析、对比、趋势、峰电流、图表、看看、查一下
   
2. designer — 实验设计：设计方案、生成实验、优化参数、审查方案
   关键词：设计、做实验、方案、浓度梯度、怎么做
   
3. supervisor — 实验执行：执行实验、排程、监控、检查质量
   关键词：执行、运行、跑、排程、安排、质量
   
4. diagnostics — 故障诊断：失败原因、错误分析、设备检查、排错
   关键词：失败、错误、为什么、怎么回事、坏了、不工作
   
5. knowledge — 知识管理：入库文献、知识问答、归档
   关键词：知识、文献、入库、归档、问答、手册

6. direct_response — 简单问候/闲聊/不属于以上类别

返回 JSON: {"agent": "analyst|designer|supervisor|diagnostics|knowledge|direct_response", "reason": "..."}
"""

async def router_node(state: AutoHySeekerState) -> dict:
    """LLM 意图分类 — 用 gpt-4o-mini 即可（成本低、速度快）"""
    last_message = state["messages"][-1].content
    
    response = await llm_client.chat(
        model="gpt-4o-mini",  # 路由用小模型
        system=ROUTING_PROMPT,
        user=last_message,
        response_format=RoutingResult,
    )
    
    return {"current_agent": response.agent, "task_type": response.agent}
```

### 2.3 `synthesize_node` — 汇总

```python
async def synthesize_node(state: AutoHySeekerState) -> dict:
    """
    汇总 Agent 返回的结果，组织成用户友好的回复。
    简单情况直接转发 Agent 结果，复杂情况 LLM 润色。
    """
    agent_results = state.get("agent_results", {})
    
    # 如果 Agent 已经返回了格式良好的报告，直接使用
    for agent_name, result in agent_results.items():
        if isinstance(result, dict) and result.get("report"):
            return {"final_response": result["report"]}
    
    # 否则 LLM 汇总
    return {"final_response": str(agent_results)}
```

---

## 三、分阶段实现

### Phase 1 (Week 4) — 基础版

只路由到 DiagnosticsExpert 和 ExperimentSupervisor：

```python
# Phase 1: 简化路由，只支持 diagnostics + supervisor
def route_to_agent_phase1(state) -> str:
    agent = state["current_agent"]
    if agent in ("diagnostics", "supervisor"):
        return agent
    return "direct_response"
```

### Phase 2 (Week 6) — 增加 DataAnalyst

```python
# Phase 2: 新增 analyst
if agent in ("diagnostics", "supervisor", "analyst"):
    return agent
```

### Phase 3 (Week 9) — 完整版

所有 5 个 Agent 全部可用。

---

## 四、CLI 入口设计

```python
# scripts/cli.py
import click

@click.group()
def cli():
    """AutoHySeeker — AI 电化学实验助手"""
    pass

# === P1 命令 ===
@cli.command()
@click.argument("run_dir")
def diagnose(run_dir: str):
    """诊断失败实验的原因"""
    graph = build_diagnostics_graph()
    result = asyncio.run(graph.ainvoke({"task": "diagnose", "run_dir": run_dir}))
    print(result["diagnosis_report"])

@cli.command()
@click.option("--depth", default="standard")
def health_check(depth: str):
    """系统健康检查"""
    ...

@cli.command()
@click.argument("run_dir")
def review(run_dir: str):
    """实验质量报告"""
    ...

# === P2 命令 ===
@cli.command()
@click.argument("run_dir")
def analyze(run_dir: str):
    """分析实验数据"""
    ...

@cli.command()
@click.argument("run_dirs", nargs=-1)
def compare(run_dirs: tuple[str]):
    """对比多个实验"""
    ...

@cli.command()
@click.argument("question")
def ask(question: str):
    """自然语言数据查询"""
    ...

# === P3 命令 ===
@cli.command()
@click.argument("description")
def design(description: str):
    """设计实验方案"""
    ...

@cli.command()
@click.argument("question")
def ask_kb(question: str):
    """知识库问答"""
    ...

# === 通用入口 ===
@cli.command()
def chat():
    """交互式对话（走 Orchestrator）"""
    graph = build_orchestrator_graph()
    config = {"configurable": {"thread_id": "chat_session"}}
    
    print("AutoHySeeker 就绪。输入 'quit' 退出。")
    while True:
        user_input = input("\n你: ")
        if user_input.lower() in ("quit", "exit", "q"):
            break
        
        result = asyncio.run(graph.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        ))
        print(f"\nAutoHySeeker: {result['final_response']}")
```

---

## 五、开发清单

```
Week 4 (P1):
  ☐ graph/orchestrator.py — 基础版（仅 diagnostics + supervisor）
  ☐ agents/router.py — 规则路由（不用 LLM，按命令行参数）
  ☐ scripts/cli.py — diagnose, health-check, review 命令

Week 6 (P2):
  ☐ 路由增加 analyst
  ☐ CLI: analyze, compare, ask 命令

Week 9 (P3):
  ☐ 路由增加 designer + knowledge
  ☐ agents/router.py — LLM 路由（gpt-4o-mini）
  ☐ synthesize_node 完善
  ☐ CLI: design, ask-kb, ingest, archive, chat 命令
```

---

## 六、注意事项

### 6.1 路由准确性

路由错误会导致用户体验差。措施：
- 关键词表兜底（LLM 分类不确定时用关键词回退）
- 用户反馈修正（"这不是我想问的"→ 重新路由）

### 6.2 多轮对话上下文

LangGraph 的 `MemorySaver` + `thread_id` 自动管理对话历史。同一个 `thread_id` 内的多轮对话会保持上下文。

### 6.3 复合任务

暂不支持"分析完数据再帮我设计下一步实验"这种跨 Agent 的复合任务。Phase 4 的 C3 自适应闭环本质上就是这种复合任务。

---

*此文档可直接作为 Orchestrator 的开发执行依据。*

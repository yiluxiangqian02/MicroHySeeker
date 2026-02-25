# Agent B — ExperimentDesigner 开发指南

> 代号：ED | 优先级：P3 (Week 8) | 域：实验设计
> 总体架构参考：[`langgraph_architecture.md`](langgraph_architecture.md) | Tool/Skill定义参考：[`skills_architecture.md`](skills_architecture.md)

---

## 一、Agent 概览

### 1.1 职责定位

ExperimentDesigner 是**实验方案设计师**：

- 自然语言描述 → 完整实验方案 JSON（B1）
- 参数空间探索 → 优化建议（B2，Phase 4）
- 生成的方案 → 自动审查安全性/合理性（B3）
- 文献方法 → 适配本平台的方案（B4，Phase 4）

### 1.2 拥有的 Skills

| Skill | 名称 | 阶段 | LLM 角色 | 必须 LLM? |
|-------|------|------|----------|-----------|
| **B1** | `generate_experiment_plan` | P3 | NL→结构化方案 | ✅ 是 |
| **B2** | `optimize_parameters` | P4 | 解释优化建议 | ⚠️ 算法核心不需要 |
| **B3** | `validate_and_review_plan` | P3 | 领域知识审查 | ⚠️ 降级为规则校验 |
| **B4** | `replicate_literature_method` | P4 | 文献提取+适配 | ✅ 是 |

### 1.3 与其他 Agent 协作

```
用户                      ExperimentDesigner (B)
  │                              │
  │  "做浓度梯度CV"              │
  ├─────────────────────────────►│
  │                              ├─── B1: NL→方案
  │                              │       ├── [RAG] 查知识库参考
  │                              │       ├── [LLM] 理解意图, 生成步骤
  │                              │       └── experiment_builder.* 构建JSON
  │                              │
  │                              ├─── B3: 审查
  │                              │       ├── validate_experiment (规则)
  │                              │       ├── [RAG] 对比历史参数
  │                              │       └── [LLM] 安全+合理性审查
  │                              │
  │◄─────────────────────────────┤  方案 JSON + 解释
  │                              │
  │  "确认执行"                   │
  ├─────────────────────────────►│
  │                              ├──→ ExperimentSupervisor (C)
  │                              │    加载方案 → 执行
```

---

## 二、LangGraph Subgraph 设计

### 2.1 State 定义

```python
class DesignerState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 任务类型
    task: Literal["generate", "optimize", "review", "replicate"]
    
    # 输入
    user_description: str | None    # B1: "做浓度梯度CV，Fe 0.1-0.5M"
    existing_plan: dict | None      # B3: 要审查的方案
    paper_path: str | None          # B4: 论文 PDF 路径
    parameter_space: dict | None    # B2: 参数空间
    objective: str | None           # B2: 优化目标
    
    # 中间
    intent: dict | None             # 解析后的意图结构
    knowledge_context: list[dict]   # RAG 检索到的参考资料
    system_config: dict | None      # MicroHySeeker 硬件配置
    
    # 方案
    experiment_plan: dict | None    # 生成的实验方案 JSON
    validation_result: dict | None  # 校验结果
    review_comments: list[str]      # 审查意见
    review_passed: bool
    iteration_count: int            # 生成→审查 迭代次数（防无限循环）
    max_iterations: int             # 默认 3
    
    # 产出
    final_plan: dict | None         # 最终方案
    explanation: str | None         # 方案解释
    warnings: list[str]
    estimated_duration: float | None
```

### 2.2 Graph 结构

```python
def build_designer_graph():
    graph = StateGraph(DesignerState)
    
    graph.add_node("understand_intent", understand_intent_node)
    graph.add_node("search_knowledge", search_knowledge_node)
    graph.add_node("read_hardware_config", read_hardware_config_node)
    graph.add_node("generate_plan", generate_plan_node)
    graph.add_node("validate_plan", validate_plan_node)
    graph.add_node("review_plan", review_plan_node)
    graph.add_node("output_plan", output_plan_node)
    
    graph.add_edge(START, "understand_intent")
    graph.add_edge("understand_intent", "search_knowledge")
    graph.add_edge("search_knowledge", "read_hardware_config")
    graph.add_edge("read_hardware_config", "generate_plan")
    graph.add_edge("generate_plan", "validate_plan")
    
    graph.add_conditional_edges("validate_plan", check_validation, {
        "valid": "review_plan",
        "invalid": "generate_plan",    # 校验不过 → 重新生成
    })
    
    graph.add_conditional_edges("review_plan", check_review, {
        "passed": "output_plan",
        "needs_revision": "generate_plan",  # 审查不过 → 修正
        "max_iterations": "output_plan",    # 达到上限 → 输出但带警告
    })
    
    graph.add_edge("output_plan", END)
    
    return graph.compile()
```

```
    START
      │
  understand_intent  (LLM)
      │
  search_knowledge   (RAG, Phase 3+)
      │
  read_hardware_config
      │
  ┌──►generate_plan  (LLM)
  │     │
  │   validate_plan  (规则)
  │     │
  │   invalid──┘
  │   valid
  │     │
  │   review_plan   (LLM)
  │     │
  │   needs_revision──┘ (最多循环 3 次)
  │   passed
  │     │
  │   output_plan
  │     │
  └    END
```

---

## 三、节点函数设计

### 3.1 `understand_intent_node` — 意图理解

```python
async def understand_intent_node(state: DesignerState) -> dict:
    """
    ★ LLM 核心: 将用户自然语言描述转为结构化意图。
    
    输入: "做 Fe 浓度梯度 0.1-0.5M 间隔0.1 的 CV 扫描，扫速 50mV/s"
    输出: {
        "technique": "CV",
        "variable": "concentration",
        "variable_range": [0.1, 0.2, 0.3, 0.4, 0.5],
        "fixed_params": {"scan_rate": 0.05},
        "analyte": "Fe",
        "needs_prep_sol": true,
        "needs_flush": true,
    }
    """
    prompt = INTENT_PARSING_PROMPT.format(
        description=state["user_description"]
    )
    
    response = await llm_client.chat(
        system=DESIGNER_SYSTEM_PROMPT,
        user=prompt,
        response_format=ExperimentIntent,
    )
    
    return {"intent": response.model_dump()}


class ExperimentIntent(BaseModel):
    """结构化的实验意图"""
    technique: str                        # CV, LSV, EIS, i-t, OCPT
    variable: str | None                  # concentration, scan_rate, potential, time ...
    variable_values: list[float] | None   # [0.1, 0.2, 0.3, 0.4, 0.5]
    fixed_params: dict                    # 固定参数
    analyte: str | None                   # 分析物
    solvent: str | None                   # 溶剂
    electrode: str | None                 # 电极信息
    needs_prep_sol: bool                  # 是否需要配液
    needs_flush: bool                     # 是否需要冲洗
    needs_blank: bool                     # 是否需要等待稳定
    special_requirements: list[str]       # 特殊要求
```

### 3.2 `search_knowledge_node` — RAG 检索

```python
async def search_knowledge_node(state: DesignerState) -> dict:
    """
    Phase 3+: 从知识库检索相关实验参数参考。
    Phase 1-2: 跳过，返回空。
    """
    if not rag_available:
        return {"knowledge_context": []}
    
    intent = state["intent"]
    
    # 构造搜索查询
    query = f"{intent['technique']} {intent.get('analyte', '')} 参数 实验条件"
    
    results = rag_tools.semantic_search(
        query=query,
        collection="experiment_archive",
        top_k=3,
    )
    
    # 也搜仪器手册
    manual_results = rag_tools.semantic_search(
        query=f"{intent['technique']} 参数范围 推荐设置",
        collection="instrument_manual",
        top_k=2,
    )
    
    return {"knowledge_context": results + manual_results}
```

### 3.3 `generate_plan_node` — 生成方案

```python
async def generate_plan_node(state: DesignerState) -> dict:
    """
    ★ LLM 核心: 根据意图+硬件配置+知识参考，生成完整方案 JSON。
    
    步骤：
    1. LLM 决定实验步骤序列和参数
    2. 调用 experiment_builder.build_*_step() 构建每个步骤
    3. assemble_experiment() 组装完整方案
    4. 如果是梯度实验，generate_combo_matrix() 生成组合
    """
    intent = state["intent"]
    config = state["system_config"]
    knowledge = state.get("knowledge_context", [])
    
    # 如果是修正轮（从 validate/review 回来的）
    review_comments = state.get("review_comments", [])
    
    prompt = PLAN_GENERATION_PROMPT.format(
        intent=json.dumps(intent, ensure_ascii=False, indent=2),
        hardware_config=json.dumps(config, ensure_ascii=False, indent=2),
        knowledge_context=_format_knowledge(knowledge),
        review_feedback="\n".join(review_comments) if review_comments else "无",
        available_step_types="prep_sol, transfer, flush, echem, blank, evacuate",
    )
    
    # LLM 生成步骤描述
    response = await llm_client.chat(
        system=DESIGNER_SYSTEM_PROMPT,
        user=prompt,
        response_format=ExperimentPlanDraft,
    )
    
    # 用 experiment_builder 构建标准 JSON
    steps = []
    for step_draft in response.steps:
        if step_draft.type == "cv":
            step = experiment_builder.build_cv_step(**step_draft.params)
        elif step_draft.type == "prep_sol":
            step = experiment_builder.build_prep_sol_step(**step_draft.params)
        elif step_draft.type == "flush":
            step = experiment_builder.build_flush_step(**step_draft.params)
        # ... 其他步骤类型
        steps.append(step)
    
    plan = experiment_builder.assemble_experiment(
        name=response.experiment_name,
        steps=steps,
        combo_params=response.combo_params,
    )
    
    # 估算耗时
    estimated_duration = _estimate_total_duration(plan)
    
    return {
        "experiment_plan": plan,
        "explanation": response.explanation,
        "estimated_duration": estimated_duration,
        "iteration_count": state.get("iteration_count", 0) + 1,
    }
```

### 3.4 `validate_plan_node` — 规则校验

```python
async def validate_plan_node(state: DesignerState) -> dict:
    """
    规则校验。不需要 LLM。
    """
    plan = state["experiment_plan"]
    result = experiment_builder.validate_experiment(plan)
    
    return {
        "validation_result": result,
        "review_comments": [f"校验错误: {e}" for e in result.get("errors", [])] 
                          if not result["valid"] else [],
    }
```

### 3.5 `review_plan_node` — 方案审查 (B3)

```python
async def review_plan_node(state: DesignerState) -> dict:
    """
    B3: 方案审查 — 安全性、合理性、优化建议。
    
    ★ LLM 做领域知识审查（重要！）。
    降级模式：仅规则校验，不做深层审查。
    """
    plan = state["experiment_plan"]
    knowledge = state.get("knowledge_context", [])
    
    review_comments = list(state.get("review_comments", []))
    
    # 规则审查（不需要 LLM）
    rule_issues = _rule_based_review(plan)
    review_comments.extend(rule_issues)
    
    # LLM 审查（推荐）
    if llm_available:
        prompt = REVIEW_PROMPT.format(
            plan=json.dumps(plan, ensure_ascii=False, indent=2),
            knowledge=_format_knowledge(knowledge),
        )
        
        response = await llm_client.chat(
            system=DESIGNER_SYSTEM_PROMPT,
            user=prompt,
            response_format=ReviewResult,
        )
        
        review_comments.extend(response.issues)
        passed = response.approved and len(rule_issues) == 0
    else:
        passed = len(rule_issues) == 0
    
    return {
        "review_comments": review_comments,
        "review_passed": passed,
    }


def _rule_based_review(plan: dict) -> list[str]:
    """硬编码的安全规则检查"""
    issues = []
    steps = plan.get("program", {}).get("steps", [])
    
    for i, step in enumerate(steps):
        if step.get("type") == "echem":
            # 电位范围检查
            e_high = step.get("e_high", 0)
            e_low = step.get("e_low", 0)
            if abs(e_high) > 5 or abs(e_low) > 5:
                issues.append(f"步骤{i}: 电位 {e_low}~{e_high}V 超出安全范围（±5V）")
            
            # 扫速检查
            scan_rate = step.get("scan_rate", 0)
            if scan_rate > 10:
                issues.append(f"步骤{i}: 扫速 {scan_rate}V/s 过高，可能损坏电极")
        
        elif step.get("type") == "prep_sol":
            # 总体积检查
            total_vol = step.get("total_volume", 0)
            if total_vol > 50:  # mL
                issues.append(f"步骤{i}: 配液体积 {total_vol}mL 过大")
    
    # 检查是否缺少冲洗步骤
    echem_steps = [i for i, s in enumerate(steps) if s.get("type") == "echem"]
    if len(echem_steps) > 1:
        for j in range(1, len(echem_steps)):
            between = steps[echem_steps[j-1]+1 : echem_steps[j]]
            has_flush = any(s.get("type") == "flush" for s in between)
            if not has_flush:
                issues.append(f"步骤{echem_steps[j-1]}和{echem_steps[j]}之间没有冲洗步骤")
    
    return issues
```

---

## 四、System Prompt

```python
DESIGNER_SYSTEM_PROMPT = """你是 AutoHySeeker 系统的实验方案设计师（ExperimentDesigner）。

你的任务是将用户的自然语言实验需求转化为 MicroHySeeker 可执行的实验方案 JSON。

MicroHySeeker 支持的步骤类型：
1. prep_sol: 配液 — 使用蠕动泵按比例混合溶液
   参数: concentrations(dict), total_volume(mL), pumps(list)
2. transfer: 移液 — 将溶液转移到电解池
   参数: pump_addr, volume(mL), direction
3. flush: 冲洗 — 用纯水/溶剂冲洗管路和电解池
   参数: cycles, flush_volume(mL)
4. echem: 电化学测量 — CV/LSV/EIS/i-t/OCPT等
   参数: technique, 各技术特有参数
5. blank: 等待 — 静置等待（如开路电位稳定）
   参数: duration(s)
6. evacuate: 排空 — 排出电解池溶液
   参数: duration(s)

典型实验流程：
  冲洗 → 配液 → 转移 → 等待 → 电化学测量 → 排空
  (如果是浓度梯度：按不同浓度重复上述流程)

硬件约束：
- 12 路蠕动泵，地址 1-12
- 泵 1-4: 通常用于配液（对应不同母液储罐）
- 泵 5: 废液泵
- 泵 6-8: 冲洗泵
- 所有泵体积精度约 ±5%
- CHI 660F 电位范围: ±10V，典型使用 ±2V

安全注意事项：
- 每次更换溶液前必须冲洗
- 电位范围不应超过 ±5V（除非用户明确要求）
- 扫速不应超过 5V/s（常规实验）
- 浓度梯度应从低到高排列（减少污染）
"""
```

---

## 五、开发清单（Week 8）

```
Week 8:
  ☐ tools/experiment_builder.py — 全部 11 函数
      build_cv_step, build_lsv_step, build_eis_step,
      build_prep_sol_step, build_flush_step, build_transfer_step,
      build_blank_step, build_evacuate_step,
      assemble_experiment, validate_experiment, generate_combo_matrix
  ☐ graph/state.py — DesignerState
  ☐ graph/designer_graph.py — 图定义（含审查循环）
  ☐ agents/designer_nodes.py — 全部节点
  ☐ agents/prompts.py — DESIGNER_SYSTEM_PROMPT
  ☐ skills/experiment_design/generate_experiment_plan.py (B1)
  ☐ skills/experiment_design/validate_and_review.py (B3)
  ☐ ExperimentDesigner Agent（Orchestrator 路由集成）
  ☐ CLI: python -m autohyseeker.cli design "..."
  ☐ 测试: NL→方案 的端到端测试
```

---

## 六、注意事项

### 6.1 B3 审查循环的防死循环

```python
def check_review(state: DesignerState) -> str:
    if state["review_passed"]:
        return "passed"
    if state["iteration_count"] >= state.get("max_iterations", 3):
        return "max_iterations"  # 强制输出，但带警告
    return "needs_revision"
```

### 6.2 experiment.json 的格式兼容

生成的方案 JSON 必须与 MicroHySeeker 的 `ExperimentEngine` 完全兼容，字段命名、类型、结构都要严格匹配。参考 `MicroHySeeker/src/models/` 中的定义。

### 6.3 B1 → C 的交接

B1 生成的方案 JSON 可以：
1. 保存为文件 → 用户手动加载到 MicroHySeeker
2. Phase 4: 直接传给 C Agent → 自动加载执行

---

*此文档可直接作为 ExperimentDesigner Agent 的开发执行依据。*

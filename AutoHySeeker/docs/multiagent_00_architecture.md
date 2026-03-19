# AutoHySeeker Multi-Agent 系统架构总览

> **最后更新：2026-03-18 — Phase 10 架构精简（7→4 Agent）**

## 1. 系统目��

AutoHySeeker 是一个 **闭环自驱动实验室 (Self-Driving Lab, SDL)** 的 AI 代理层，
目标是 **自主优化析氢反应 (HER) 催化剂的元素配比**。

核心循环：
```
设定优化目标 → 设计实验参数 → 执行实验 → 分析数据 → 决策下一步 → 循环
```

主要变化量是 **元素配比**（各液体体积/浓度），通过 MicroHySeeker 的模板实例化 API
（`/api/template/{id}/instantiate`）调整 `target_concentrations` 和 `total_volume_ul` 来控制。

---

## 2. Agent 总览（4 Agent + 2 Skill 架构）

| # | 名称 | 英文标识 | 定位 | 类型 |
|---|------|---------|------|------|
| 1 | **运行管控 Agent** | `orchestrator` | 多Agent系统大脑，闭环调度 + 数据分析 + 知识管理 | Agent |
| 2 | **实���设计 Agent** | `exp_designer` | 生成实验参数（元素配比） | Agent |
| 3 | **实验执行 Agent** | `exp_executor` | 执行/监控单次实验 | Agent |
| 4 | **故障排查 Agent** | `diagnostics` | 异常诊断与自动修复 | Agent |
| — | *数据分析技能* | `DataAnalysisSkill` | 电化学数据指标提取与质量评估 | Orchestrator Skill |
| — | *知识归档技能* | `KnowledgeArchiveSkill` | 实验归档与文献/历史检索 | Orchestrator Skill |

> **Phase 10 架构精简**：原 7 个 Agent 精简为 4 个。
> - `DataAnalystAgent` → 转为 `DataAnalysisSkill`（确定性逻辑，无需独立 LLM）
> - `KnowledgeManagerAgent` → 转为 `KnowledgeArchiveSkill`（模板化归档/检索，无需独立 LLM）
> - `ExperimentSupervisorAgent` → 已消除（职责与 Orchestrator 重叠）
>
> 旧 Agent 名称通过 `_AGENT_ALIASES` 向后兼容路由到 `orchestrator`。

---

## 3. 核心工作流

### 3.1 闭环优化主循环 (Optimization Loop)

```
┌───────────────────────────────────���──────────────────────────┐
│              运行管控 Agent (Orchestrator)                      │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐                 │
│  │ 接收目标 │───▶│ 分配任务  │───▶│ 决策判断 │──▶ 完成/继续     │
│  └─────────┘    └──────────┘    └──────────┘                 │
│       │              │               ▲                        │
│       │              │               │                        │
│       │         ┌──────────┐    ┌──────────────┐             │
│       │         │ 知识归档  │    │ 数据分析      │             │
│       │         │  Skill   │    │  Skill       │             │
│       │         └──────────┘    └──────────────┘             │
│       │              │               ▲                        │
│       ▼              ▼               │                        │
│  ┌──────────┐   ┌──────────┐         │                        │
│  │实验设计   │   │实验执行   │─────────┘                        │
│  │ Agent    │──▶│ Agent    │                                  │
│  └──────────┘   └──────────┘                                  │
│                      │                                        │
│                      ▼ (异常时)                                │
│                 ┌──────────┐                                  │
│                 │故障排查   │                                  │
│                 │ Agent    │                                  │
│                 └──────────┘                                  │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 单次实验流程

```
Orchestrator: "以 Fe:Co:Ni = 3:5:2 配比运行 HER 实验"
    │
    ▼
Designer: 计算 target_concentrations = {"Fe": 0.3, "Co": 0.5, "Ni": 0.2}
          选择模板 → 生成 step_overrides
    │
    ▼
Executor: 调用 POST /api/template/{id}/instantiate
          → 监控实验状态 (轮询 /api/experiment/status)
          → 等待完成或检测到异常
    │
    ├─── 正常完成 ──▶ Orchestrator (DataAnalysisSkill):
    │                          分析 CV/LSV 数据
    │                          提取 overpotential, current density
    │                          返回结构化结果
    │
    └─── 异常 ──────▶ Diagnostics: 诊断故障
                                    尝试自动修复
                                    返回修复结果
    │
    ▼
Orchestrator: 汇总结果 → 决策:
    ├── 继续优化 → 回到 Designer（调整配比）
    ├── 需要重试 → 回到 Executor（重新执行）
    └── 目标达成 → 生成报告 → 结束
```

### 3.3 异常处理流程

```
Executor 检测到异常
    │
    ├─ severity: LOW → 记录日志，继续执行
    │
    ├─ severity: MEDIUM → 上报 Orchestrator
    │     │
    │     ▼
    │   Orchestrator → Diagnostics
    │     │
    │     ▼
    │   Diagnostics 返回 {can_resolve: true/false, action: "..."}
    │     │
    │     ├─ can_resolve → 执行修复 → 继续实验
    │     └─ cannot_resolve → Orchestrator 暂停/终止 → 通知用户
    │
    └─ severity: HIGH/CRITICAL → 紧急停止 (emergency_stop)
                                  → 通知用户
```

---

## 4. Agent 间通信协议

### 4.1 消息格式

所有 Agent 间通信使用统一的 **AgentMessage** 格式：

```python
@dataclass
class AgentMessage:
    msg_id: str                   # 唯一消息ID
    from_agent: str               # 发送方 agent 标识
    to_agent: str                 # 接收方 agent 标识
    msg_type: str                 # "task" | "result" | "query" | "alert"
    payload: dict                 # 消息内容
    context: dict                 # 上下文（实验历史、当前状态等）
    timestamp: str                # ISO 时间戳
    priority: str                 # "low" | "normal" | "high" | "critical"
```

### 4.2 Agent 路由表

| 源 | 目标 | 消息类型 | 触发条件 |
|----|------|---------|---------|
| Orchestrator | Designer | task | 需要新实验参数 |
| Orchestrator | Executor | task | 有实验需要执行 |
| Orchestrator | DataAnalysisSkill | skill_call | 实验完成需分析 |
| Orchestrator | KnowledgeArchiveSkill | skill_call | 需要归档/检索知识 |
| Orchestrator | Diagnostics | task | 收到异常报告 |
| Designer | Orchestrator | result | 实验参数已生成 |
| Executor | Orchestrator | result/alert | 实验完成/异常 |
| Diagnostics | Orchestrator | result | 诊断/修复结果 |

### 4.3 共享状态 (Optimization State)

```python
@dataclass
class OptimizationState:
    goal: str                          # 优化目标描述
    target_metric: str                 # "overpotential" | "current_density" | "tafel_slope"
    optimization_direction: str        # "minimize" | "maximize"
    
    # 实验历史
    completed_experiments: list[dict]   # [{params, results, run_id, timestamp}]
    best_result: dict | None           # 当前最优结果
    
    # 当前轮次
    current_round: int                 # 当前优化轮次
    max_rounds: int                    # 最大轮次
    current_experiment: dict | None    # 正在执行的实验
    
    # 控制
    status: str                        # "idle" | "designing" | "executing" | "analyzing" | "diagnosing" | "completed"
    stop_criteria_met: bool            # 是否满足停止条件
    errors: list[str]                  # 累积的错误信息
```

---

## 5. 工具权限矩阵

每个 Agent 只能使用其权限范围内的工具，遵循最小权限原则：

| 工具类别 | Orchestrator | Designer | Executor | Diagnostics |
|---------|:---:|:---:|:---:|:---:|
| **实验控制** (start/stop/pause) | — | — | ✅ | ✅ |
| **泵控制** (pump_start/stop) | — | — | ✅ | ✅ |
| **清洗控制** (flusher) | — | — | ✅ | ✅ |
| **配液控制** (diluter) | — | — | ✅ | ✅ |
| **紧急停止** | ✅ | — | ✅ | ✅ |
| **模板管理** (list/get/save) | ✅ | ✅ | ✅ | — |
| **模板实例化** (instantiate) | — | — | ✅ | — |
| **参数验证** (validate) | — | ✅ | ✅ | — |
| **系统配置查询** | ✅ | ✅ | ✅ | ✅ |
| **数据读取** (run data/echem) | ✅* | ✅ | — | ✅ |
| **电化学分析** (CV/EIS/LSV) | ✅* | — | — | — |
| **可视化** (plot) | ✅* | — | — | — |
| **日志查询** | ✅ | — | ✅ | ✅ |
| **日志分析** (parse/classify) | — | — | — | ✅ |
| **健康检查** | ✅ | — | ✅ | ✅ |
| **知识检索** (RAG) | ✅* | ✅ | — | — |
| **报告生成** | ✅ | — | — | — |

> ✅* = 通过 Orchestrator 内置的 DataAnalysisSkill / KnowledgeArchiveSkill 调用

---

## 6. 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| Agent 框架 | LangGraph + 自定义回退 | 图编排、状态管理 |
| LLM | GLM-4.7 (智谱) | Agent 推理 |
| 工具调用 | OpenAI function calling 格式 | LLM → Tool |
| 向量存储 | ChromaDB | RAG 知识库 |
| API 通信 | httpx (async) | Agent → MicroHySeeker |
| 优化算法 | Optuna (可选) | 贝叶斯优化 |
| 日志 | Python logging + 结构化 JSON | 系统可观测性 |

---

## 7. 文件结构（当前状态）

```
AutoHySeeker/src/
├── agents/
│   ├── base.py                    # BaseAgent (✅)
│   ├── orchestrator.py            # 运行管控 Agent + Skills (✅)
│   ├── exp_designer.py            # 实验设计 Agent (✅)
│   ├── exp_executor.py            # 实验执行 Agent (✅)
│   ├── diagnostics.py             # 故障排查 Agent (✅)
│   └── __init__.py                # 导出 4 个 Agent
│
├── skills/
│   ├── data_analysis_skill.py     # DataAnalysisSkill (✅)
│   ├── knowledge_archive_skill.py # KnowledgeArchiveSkill (✅)
│   ├── experiment_execution/      # 执行技能 (✅)
│   ├── diagnostics/               # 诊断技能 (✅)
│   └── __init__.py
│
├── graph/
│   ├── state.py                   # AutoHySeekerState (✅)
│   ├── orchestrator.py            # 主图 — 4 Agent 节点 (✅)
│   ├── nodes.py                   # 路由 + _AGENT_ALIASES (✅)
│   ├── optimization_loop.py       # 闭环优化子图 (✅)
│   └── diagnostics_graph.py       # 诊断子图 (✅)
│
├── tools/
│   ├── experiment_ctrl.py         # MicroHySeeker API 客户端 (✅)
│   ├── experiment_builder.py      # 实验构建工具 (✅)
│   ├── echem_analysis.py          # 电化学分析 (✅)
│   ├── registry.py                # 工具注册表 (✅)
│   └── ...
│
└── common/
    ├── llm_client.py              # LLM 客户端 — 4 Agent 配置 (✅)
    ├── agent_manager.py           # Agent 状态管理 — 4 Agent (✅)
    ├── config.py                  # 配置管理 (✅)
    └── ...
```

---

## 8. 实施阶段

### Phase 1~9: 已完成（详见 VALIDATION_AND_TESTING_GUIDE.md 第十四节）

### Phase 10: 架构精简（当前阶段 — 已完成）
1. ✅ 评估 7 个 Agent 必要性，确定 4 Agent + 2 Skill 架构
2. ✅ 创建 `DataAnalysisSkill`（从 DataAnalystAgent 转化）
3. ✅ 创建 `KnowledgeArchiveSkill`（从 KnowledgeManagerAgent 转化）
4. ✅ 更新 Orchestrator 集成两个 Skill
5. ✅ 更新 LangGraph 图（7→4 节点）+ 路由别名兼容
6. ✅ 更新全部测试文件（9 个文件）
7. ✅ 更新配置文件（agent_models.toml、llm_client.py、agent_manager.py）
8. ✅ 更新文档

### Phase 11: 下一步（待规划）
- [ ] 前端 UI 适配 4 Agent 架构（UI_PLAN_V3）
- [ ] 真实 LLM 联调验证
- [ ] MicroHySeeker 硬件联调
- [ ] OptimizationLoop.run() 端到端测试

---

## 9. 与 MicroHySeeker 的接口

### 已就绪的 API 端点

| 类别 | 端点 | 用途 |
|------|------|------|
| 实验控制 | `/api/experiment/*` | 实验生命周期 |
| 设备控制 | `/api/device/*` | 泵/清洗/配液/紧急停止 |
| 模板管理 | `/api/template/*` | CRUD + 实例化 + 验证 |
| 系统配置 | `/api/config/*` | 能力查询/通道/泵配置 |
| 系统监控 | `/api/system/*` | 健康检查/日志/重启 |
| 数据查询 | `/api/data/*` | 实验运行数据 |

### 元素配比控制接口

Agent 调整元素配比的核心 API：

```python
# 1. 查询系统能力
GET /api/config/dilution-channels
→ {"channels": [{"id": 0, "solution_name": "Fe", ...}, {"id": 1, "solution_name": "Co", ...}]}

# 2. 从模板实例化（覆盖元素配比）
POST /api/template/{template_id}/instantiate
{
  "overrides": {
    "step_overrides": {
      "0": {                              // 覆盖第0步 (prep_sol 步骤)
        "prep_sol_params": {
          "target_concentrations": {
            "Fe": 0.3,                    // Fe 浓度比
            "Co": 0.5,                    // Co 浓度比
            "Ni": 0.2                     // Ni 浓度比
          },
          "total_volume_ul": 1000         // 总体积 μL
        }
      }
    }
  },
  "exp_name": "HER_Fe3Co5Ni2_round_5",
  "dry_run": false
}

# 3. 监控执行
GET /api/experiment/status

# 4. 获取结果数据
GET /api/data/runs/{run_id}
```

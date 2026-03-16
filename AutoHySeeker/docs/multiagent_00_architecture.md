# AutoHySeeker Multi-Agent 系统架构总览

## 1. 系统目标

AutoHySeeker 是一个 **闭环自驱动实验室 (Self-Driving Lab, SDL)** 的 AI 代理层，
目标是 **自主优化析氢反应 (HER) 催化剂的元素配比**。

核心循环：
```
设定优化目标 → 设计实验参数 → 执行实验 → 分析数据 → 决策下一步 → 循环
```

主要变化量是 **元素配比**（各液体体积/浓度），通过 MicroHySeeker 的模板实例化 API
（`/api/template/{id}/instantiate`）调整 `target_concentrations` 和 `total_volume_ul` 来控制。

---

## 2. Agent 总览

| # | Agent 名称 | 英文标识 | 定位 | 当前状态 |
|---|-----------|---------|------|---------|
| 1 | **运行管控 Agent** | `orchestrator` | 多Agent系统大脑，闭环调度 | 图/路由已实现，闭环逻辑待构建 |
| 2 | **实验设计 Agent** | `exp_designer` | 生成实验参数（元素配比） | Stub（仅 system prompt） |
| 3 | **实验执行 Agent** | `exp_executor` | 执行/监控单次实验 | 需新建（当前由 supervisor 兼任） |
| 4 | **数据分析 Agent** | `data_analyst` | 分析电化学数据 | Stub + 丰富工具/技能 |
| 5 | **故障排查 Agent** | `diagnostics` | 异常诊断与自动修复 | Stub（仅 system prompt） |
| 6 | **知识管理 Agent** | `knowledge_mgr` | RAG 文献检索与知识沉淀 | Stub + RAG 基础设施 |

> **关键调整**：将现有 `ExperimentSupervisorAgent`（314行，已完整实现）拆分为
> **运行管控 Agent**（高层调度）+ **实验执行 Agent**（单次实验生命周期管理）。

---

## 3. 核心工作流

### 3.1 闭环优化主循环 (Optimization Loop)

```
┌─────────────────────────────────────────────────────────┐
│                   运行管控 Agent (Orchestrator)           │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐           │
│  │ 接收目标 │───▶│ 分配任务  │───▶│ 决策判断 │──▶ 完成/继续│
│  └─────────┘    └──────────┘    └──────────┘           │
│       │              │               ▲                  │
│       │              │               │                  │
│       ▼              ▼               │                  │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐           │
│  │知识管理  │    │实验设计   │    │数据分析   │           │
│  │ Agent   │    │ Agent    │    │ Agent    │           │
│  └─────────┘    └──────────┘    └──────────┘           │
│                      │               ▲                  │
│                      ▼               │                  │
│                 ┌──────────┐         │                  │
│                 │实验执行   │─────────┘                  │
│                 │ Agent    │                            │
│                 └──────────┘                            │
│                      │                                  │
│                      ▼ (异常时)                          │
│                 ┌──────────┐                            │
│                 │故障排查   │                            │
│                 │ Agent    │                            │
│                 └──────────┘                            │
└─────────────────────────────────────────────────────────┘
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
    ├─── 正常完成 ──▶ Analyst: 分析 CV/LSV 数据
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

| 源 Agent | 目标 Agent | 消息类型 | 触发条件 |
|----------|-----------|---------|---------|
| Orchestrator | Designer | task | 需要新实验参数 |
| Orchestrator | Executor | task | 有实验需要执行 |
| Orchestrator | Analyst | task | 实验完成需分析 |
| Orchestrator | Diagnostics | task | 收到异常报告 |
| Orchestrator | Knowledge | query | 需要文献/历史上下文 |
| Designer | Orchestrator | result | 实验参数已生成 |
| Executor | Orchestrator | result/alert | 实验完成/异常 |
| Analyst | Orchestrator | result | 分析结果 |
| Diagnostics | Orchestrator | result | 诊断/修复结果 |
| Knowledge | Orchestrator | result | 检索结果 |

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

| 工具类别 | Orchestrator | Designer | Executor | Analyst | Diagnostics | Knowledge |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| **实验控制** (start/stop/pause) | — | — | ✅ | — | ✅ | — |
| **泵控制** (pump_start/stop) | — | — | ✅ | — | ✅ | — |
| **清洗控制** (flusher) | — | — | ✅ | — | ✅ | — |
| **配液控制** (diluter) | — | — | ✅ | — | ✅ | — |
| **紧急停止** | ✅ | — | ✅ | — | ✅ | — |
| **模板管理** (list/get/save) | ✅ | ✅ | ✅ | — | — | — |
| **模板实例化** (instantiate) | — | — | ✅ | — | — | — |
| **参数验证** (validate) | — | ✅ | ✅ | — | — | — |
| **系统配置查询** | ✅ | ✅ | ✅ | — | ✅ | — |
| **数据读取** (run data/echem) | — | ✅ | — | ✅ | ✅ | ✅ |
| **电化学分析** (CV/EIS/LSV) | — | — | — | ✅ | — | — |
| **可视化** (plot) | — | — | — | ✅ | — | — |
| **日志查询** | ✅ | — | ✅ | — | ✅ | — |
| **日志分析** (parse/classify) | — | — | — | — | ✅ | — |
| **健康检查** | ✅ | — | ✅ | — | ✅ | — |
| **知识检索** (RAG) | — | ✅ | — | ✅ | — | ✅ |
| **报告生成** | ✅ | — | — | ✅ | — | — |

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

## 7. 文件结构（目标状态）

```
AutoHySeeker/src/
├── agents/
│   ├── base.py                    # BaseAgent (已有 ✅)
│   ├── orchestrator.py            # 运行管控 Agent (需重构)
│   ├── exp_designer.py            # 实验设计 Agent (需充实)
│   ├── exp_executor.py            # 实验执行 Agent (需新建 🆕)
│   ├── data_analyst.py            # 数据分析 Agent (需充实)
│   ├── diagnostics.py             # 故障排查 Agent (需充实)
│   ├── knowledge_mgr.py           # 知识管理 Agent (需充实)
│   └── __init__.py
│
├── graph/
│   ├── state.py                   # OptimizationState (需扩展)
│   ├── orchestrator.py            # 主图构建 (需重构)
│   ├── nodes.py                   # 路由节点 (需增强)
│   ├── optimization_loop.py       # 闭环优化子图 (需新建 🆕)
│   └── diagnostics_graph.py       # 诊断子图 (已有 ✅)
│
├── tools/
│   ├── experiment_ctrl.py         # MicroHySeeker API 客户端 (已完善 ✅)
│   ├── experiment_builder.py      # 实验构建工具 (已有 ✅)
│   ├── echem_analysis.py          # 电化学分析 (已有 ✅)
│   ├── registry.py                # 工具注册表 (已有，需添加权限 🔧)
│   └── ...
│
├── skills/
│   ├── experiment_execution/      # 执行技能 (已有 ✅)
│   ├── diagnostics/               # 诊断技能 (已有 ✅)
│   └── optimization/              # 优化技能 (需新建 🆕)
│       ├── bayesian_optimizer.py
│       ├── grid_search.py
│       └── result_evaluator.py
│
└── common/
    ├── agent_message.py           # Agent 通信协议 (需新建 🆕)
    ├── optimization_state.py      # 优化状态管理 (需新建 🆕)
    └── ...
```

---

## 8. 实施阶段

### Phase 1: 核心循环 (当前阶段)
1. 实现 `OptimizationState` 共享状态
2. 重构 Orchestrator 为闭环调度器
3. 充实 Designer（元素配比生成 + 参数验证）
4. 新建 Executor（从 Supervisor 拆分）
5. 充实 Analyst（结构化分析输出）

### Phase 2: 智能增强
6. 充实 Diagnostics（结构化诊断流程）
7. 充实 Knowledge Manager（RAG + 实验历史索引）
8. 替换关键词路由为 LLM 路由
9. 添加工具权限控制

### Phase 3: 优化与可靠性
10. 集成 Optuna 贝叶斯优化
11. 添加 Agent 测试套件
12. 添加分布式追踪 (OpenTelemetry)
13. 构建优化结果仪表板

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

# 多端协作开发指南

> 版本：1.0 | 日期：2026-03-18
> 目标：让多个 AI 模型（或开发者）能够并发开发 AutoHySeeker，互不冲突，进度透明。

---

## 一、核心原则

1. 所有开发者（人或 AI）共享同一份进度文档 `docs/PROGRESS_TRACKER.md`
2. 开始任务前先认领，完成后立即更新状态
3. 严格按照 `PLAN_PHASE1_EXPERIMENT_LOOP.md` 和 `PLAN_PHASE2_RESEARCH_OUTPUT.md` 的设计实现
4. 任何偏离规划的设计决策，必须在进度文档中记录原因
5. 不要修改其他人正在开发的文件，除非协商一致

---

## 二、进度文档格式

文件路径：`AutoHySeeker/docs/PROGRESS_TRACKER.md`

每个任务条目格式如下：

```markdown
### [任务编号] 任务名称

- 状态: `待认领` | `进行中` | `已完成` | `阻塞`
- 负责人: (认领时填写，如 "Claude-A" / "开发者-张三")
- 开始时间: 2026-03-18
- 完成时间: (完成时填写)
- 关联文件:
  - `src/skills/knowledge_query_skill.py` (新增)
  - `src/agents/orchestrator.py` (修改)
- 依赖: [任务编号] (如果有前置依赖)
- 备注: (遇到的问题、设计偏离说明等)
```

---

## 三、任务分解与认领规则

### 3.1 Phase 1 任务列表

以下任务从 `PLAN_PHASE1_EXPERIMENT_LOOP.md` 第九节拆解而来。

```markdown
## Phase 1 进度

### Step 1: 基础设施（知识库 + 配置）

#### [P1-01] OpenViking 客户端封装
- 状态: `待认领`
- 关联文件:
  - `src/knowledge/__init__.py` (新增)
  - `src/knowledge/viking_client.py` (新增)
- 产出: OpenViking 的 CRUD 封装，支持按分区读写
- 验收标准: 能连接 OpenViking，写入/查询 experiments/ 分区成功

#### [P1-02] 知识库数据模型
- 状态: `待认领`
- 关联文件:
  - `src/knowledge/schema.py` (新增)
- 产出: 定义 literature/experiments/operations/analysis/projects 五个分区的数据模型
- 验收标准: 数据模型能序列化/反序列化，字段完整

#### [P1-03] 公共知识库查询 Skill
- 状态: `待认领`
- 依赖: P1-01, P1-02
- 关联文件:
  - `src/skills/knowledge_query_skill.py` (新增)
- 产出: KnowledgeQuerySkill，支持 search/get_similar_experiments/get_fault_history/get_literature_insights
- 验收标准: 所有 Agent 可调用，只读查询正常

#### [P1-04] 增强知识归档 Skill
- 状态: `待认领`
- 依赖: P1-01, P1-02
- 关联文件:
  - `src/skills/knowledge_archive_skill.py` (修改)
- 产出: 支持按分区写入（experiments/operations），记录环境快照
- 验收标准: 归档实验结果到 OpenViking experiments/ 分区成功

#### [P1-05] 配置文件创建
- 状态: `待认领`
- 关联文件:
  - `configs/orchestrator.toml` (新增)
  - `configs/monitor.toml` (新增)
  - `configs/designer.toml` (新增)
  - `configs/knowledge.toml` (新增)
  - `configs/projects/her_feconi.toml` (新增)
- 产出: 所有配置文件，含默认值和注释
- 验收标准: config.py 能正确加载所有配置

#### [P1-06] 增强配置加载
- 状态: `待认领`
- 依赖: P1-05
- 关联文件:
  - `src/common/config.py` (修改)
- 产出: 支持加载 orchestrator/monitor/designer/knowledge/projects 配置
- 验收标准: 所有新配置文件可通过 config 模块访问

### Step 2: 智能监控

#### [P1-07] L1 实时监控规则引擎
- 状态: `待认领`
- 依赖: P1-05
- 关联文件:
  - `src/skills/realtime_monitor_skill.py` (新增)
- 产出: RealtimeMonitorSkill，6 条规则，从 monitor.toml 读取阈值
- 验收标准: 能检测泵偏差/通信超时/步骤超时等，返回 severity 级别

#### [P1-08] L2 心跳巡检
- 状态: `待认领`
- 依赖: P1-03, P1-05
- 关联文件:
  - `src/skills/heartbeat_inspector_skill.py` (新增)
- 产出: HeartbeatInspectorSkill，可配置间隔，LLM 综合判断
- 验收标准: 开关控制正常，能按间隔执行心跳，查询知识库

#### [P1-09] Executor 集成两层监控
- 状态: `待认领`
- 依赖: P1-07, P1-08
- 关联文件:
  - `src/agents/exp_executor.py` (修改)
- 产出: execute_experiment 中集成 L1+L2，监控开关，环境快照记录
- 验收标准: 实验执行时 L1 持续运行，L2 开关可控，异常正确上报

#### [P1-10] 监控控制路由
- 状态: `待认领`
- 依赖: P1-09
- 关联文件:
  - `src/api/routes/monitor.py` (新增)
- 产出: toggle/status/config 三个路由
- 验收标准: API 可开关监控、查询状态、修改配置

### Step 3: 实验设计增强

#### [P1-11] ML 预测模型
- 状态: `待认领`
- 关联文件:
  - `src/ml/__init__.py` (新增)
  - `src/ml/performance_predictor.py` (新增)
- 产出: PerformancePredictor，支持 fit/predict_candidates，自动选择模型类型
- 验收标准: 给定 10+ 历史数据点，能训练模型并生成候选点

#### [P1-12] Designer 三阶段策略
- 状态: `待认领`
- 依赖: P1-03, P1-11
- 关联文件:
  - `src/agents/exp_designer.py` (修改)
- 产出: 文献引导 → LLM 引导 → ML 混合三阶段自动切换
- 验收标准: 第 0 轮查知识库，1-4 轮 LLM，≥5 轮 ML+LLM 审核

### Step 4: 决策与人机协作

#### [P1-13] Orchestrator 人机协作增强
- 状态: `待认领`
- 依赖: P1-03, P1-04, P1-06
- 关联文件:
  - `src/agents/orchestrator.py` (修改)
- 产出: 三种工作模式，request_human_approval，ML 训练数据管理
- 验收标准: semi_auto 模式下关键决策点暂停等待人工确认

#### [P1-14] 审批路由
- 状态: `待认领`
- 依赖: P1-13
- 关联文件:
  - `src/api/routes/approval.py` (新增)
- 产出: pending/respond 两个路由
- 验收标准: 能获取待审批决策，提交审批结果

#### [P1-15] OptimizationLoop 暂停/恢复
- 状态: `待认领`
- 依赖: P1-13
- 关联文件:
  - `src/graph/optimization_loop.py` (修改)
- 产出: 支持 pause_for_human 状态，恢复后继续执行
- 验收标准: 暂停时循环挂起，收到审批后恢复

### Step 5: ChatAgent + 诊断增强

#### [P1-16] ChatAgent
- 状态: `待认领`
- 依赖: P1-03
- 关联文件:
  - `src/agents/chat_agent.py` (新增)
- 产出: 意图识别 + 多轮对话 + 调用各 Agent 能力
- 验收标准: 能回答实验进度、知识库查询、控制指令等

#### [P1-17] Diagnostics 知识库集成
- 状态: `待认领`
- 依赖: P1-03, P1-04
- 关联文件:
  - `src/agents/diagnostics.py` (修改)
- 产出: 诊断前查知识库，修复后写入知识库
- 验收标准: 相同故障第二次出现时能找到历史记录

#### [P1-18] Chat 路由增强
- 状态: `待认领`
- 依赖: P1-16
- 关联文件:
  - `src/api/routes/chat.py` (修改)
- 产出: 接入 ChatAgent，支持对话历史
- 验收标准: POST /api/chat 能正确路由到 ChatAgent

### Step 6: 项目管理 + 集成

#### [P1-19] 项目管理路由
- 状态: `待认领`
- 关联文件:
  - `src/api/routes/projects.py` (新增)
- 产出: 项目 CRUD 路由
- 验收标准: 能创建/查询/切换项目

#### [P1-20] 知识库查询路由
- 状态: `待认领`
- 依赖: P1-03
- 关联文件:
  - `src/api/routes/knowledge.py` (新增)
- 产出: search/experiments/faults 三个路由
- 验收标准: API 能查询知识库各分区

#### [P1-21] LangGraph 路由增强
- 状态: `待认领`
- 依赖: P1-16
- 关联文件:
  - `src/graph/orchestrator.py` (修改)
  - `src/graph/nodes.py` (修改)
- 产出: 路由 ChatAgent，更新 Agent 注册表
- 验收标准: 新 Agent 能通过 LangGraph 正确调度

#### [P1-22] 端到端集成测试
- 状态: `待认领`
- 依赖: 所有 P1 任务
- 关联文件:
  - `tests/integration/test_e2e.py` (修改)
  - `tests/test_monitoring.py` (新增)
  - `tests/test_chat_agent.py` (新增)
- 产出: 覆盖完整优化闭环的集成测试
- 验收标准: 模拟完整优化流程通过
```

### 3.2 认领规则

1. 开始任务前，将状态改为 `进行中`，填写负责人和开始时间
2. 同一时间一个负责人最多认领 2 个任务
3. 有依赖关系的任务不能跳过前置任务
4. 如果任务阻塞，将状态改为 `阻塞`，在备注中说明原因
5. 完成后必须通过验收检查清单（见第八节），才能将状态改为 `已完成`
6. **严禁在未完成全部验收标准的情况下标记为 `已完成`**。如果只完成了部分工作，状态应保持 `进行中`，并在备注中说明已完成和未完成的部分

### 3.3 并发安全

以下任务组可以并行开发（无文件冲突）：

```text
并行组 A（可同时进行）:
  P1-01 + P1-02    知识库基础（knowledge/ 目录）
  P1-05             配置文件（configs/ 目录）
  P1-11             ML 预测模型（ml/ 目录）

并行组 B（A 完成后）:
  P1-03 + P1-04    知识库 Skill（skills/ 目录）
  P1-06             配置加载（common/config.py）
  P1-07             L1 监控（skills/ 目录，不同文件）

并行组 C（B 完成后）:
  P1-08             L2 心跳（skills/ 目录）
  P1-12             Designer 增强（agents/exp_designer.py）
  P1-16             ChatAgent（agents/chat_agent.py，新文件）
  P1-17             Diagnostics 增强（agents/diagnostics.py）

并行组 D（C 完成后）:
  P1-09             Executor 集成（agents/exp_executor.py）
  P1-13             Orchestrator 增强（agents/orchestrator.py）
  P1-10 + P1-14    API 路由（api/routes/，不同文件）
  P1-18 + P1-19 + P1-20  更多 API 路由

最后:
  P1-15             OptimizationLoop
  P1-21             LangGraph 路由
  P1-22             集成测试
```

---

## 四、代码规范

### 4.1 必须遵守

- 所有新 Agent 继承 `BaseAgent`
- 所有新 Skill 放在 `src/skills/` 目录
- 所有新 API 路由放在 `src/api/routes/` 目录
- 配置文件使用 TOML 格式，放在 `configs/` 目录
- 异步方法统一使用 `async def`
- 类型注解：所有公共方法的参数和返回值必须有类型注解
- 日志：使用 `logging` 模块，格式 `logger = logging.getLogger(__name__)`
- 错误处理：Agent 方法不应抛出未捕获异常，统一返回 `{"error": "..."}` 格式

### 4.2 命名规范

```text
文件名:     snake_case.py
类名:       PascalCase
方法名:     snake_case
常量:       UPPER_SNAKE_CASE
配置键:     snake_case

Agent 类:   XxxAgent (如 ChatAgent)
Skill 类:   XxxSkill (如 KnowledgeQuerySkill)
路由文件:   对应功能名 (如 monitor.py, approval.py)
```

### 4.3 Agent 方法返回格式

所有 Agent 的核心方法统一返回 dict：

```python
# 成功
{
    "status": "success",
    "data": {...},          # 业务数据
    "agent": "agent_name",
    "timestamp": "..."
}

# 失败
{
    "status": "error",
    "error": "错误描述",
    "agent": "agent_name",
    "timestamp": "..."
}
```

---

## 五、设计偏离记录

如果实现过程中发现规划文档的设计不合理，需要偏离，按以下格式记录在 PROGRESS_TRACKER.md 底部：

```markdown
## 设计偏离记录

### [偏离-001] KnowledgeQuerySkill 改为直接查询而非通过 OpenViking
- 任务: P1-03
- 原设计: 通过 OpenViking API 查询
- 实际实现: 直接查询本地 JSON（因 OpenViking 尚未部署）
- 原因: OpenViking 部署需要额外环境配置，先用本地方案跑通
- 影响: 后续需要替换为 OpenViking 客户端
- 负责人: Claude-A
- 日期: 2026-03-19
```

---

## 六、沟通协议

### 6.1 进度同步

- 每完成一个任务，立即更新 PROGRESS_TRACKER.md
- 遇到阻塞，立即在备注中说明，不要等
- 发现规划文档有歧义，在偏离记录中说明你的理解和实现方式

### 6.2 文件冲突处理

- 如果需要修改其他人正在开发的文件，在 PROGRESS_TRACKER.md 中留言说明
- 优先通过接口隔离避免冲突（比如新增方法而不是修改现有方法）
- 如果必须修改同一个文件，协商分工（比如"你改 A 方法，我改 B 方法"）

### 6.3 质量检查（自查）

每个任务完成后，自查以下清单：

```text
[ ] 代码能正常运行（无语法错误）
[ ] 类型注解完整
[ ] 有基本的错误处理
[ ] 遵循返回格式规范
[ ] 不影响现有功能（没有破坏性修改）
[ ] PROGRESS_TRACKER.md 已更新
[ ] 如有偏离，已记录原因
```

---

## 七、参考文档索引

| 文档 | 路径 | 用途 |
| --- | --- | --- |
| Phase 1 规划 | `docs/PLAN_PHASE1_EXPERIMENT_LOOP.md` | Agent/Skill/API 的详细设计 |
| Phase 2 规划 | `docs/PLAN_PHASE2_RESEARCH_OUTPUT.md` | 文献自动化 + 科研产出设计 |
| 协作指南 | `docs/COLLABORATION_GUIDE.md` | 本文档，开发流程和规范 |
| 进度追踪 | `docs/PROGRESS_TRACKER.md` | 实时进度（需创建） |
| 架构总览 | `docs/multiagent_00_architecture.md` | 现有架构参考 |
| 验证指南 | `docs/VALIDATION_AND_TESTING_GUIDE.md` | 测试方法参考 |

---

> 所有参与开发的模型/开发者在开始工作前，必须先阅读本文档和对应 Phase 的规划文档。任何不确定的地方，优先查阅规划文档，其次在 PROGRESS_TRACKER.md 中提问。

---

## 八、任务完成验收机制（强制执行）

> **核心原则：未通过验收的任务严禁标记为 `已完成`。**
> 此规则对所有 AI 模型和人类开发者同等适用。

### 8.1 完成标记的前置条件

将任务状态从 `进行中` 改为 `已完成` 之前，**必须逐项确认以下所有条件**：

```text
═══════════════════════════════════════════════════════════
  任务完成验收清单（每项必须为 ✅ 才能标记已完成）
═══════════════════════════════════════════════════════════

1. 代码完整性
   [ ] 任务描述中列出的所有「关联文件」均已创建或修改
   [ ] 任务描述中的「产出」全部实现（不是部分实现）
   [ ] 没有留下 TODO / FIXME / placeholder / pass 等占位代码

2. 验收标准
   [ ] 任务描述中的「验收标准」逐条满足
   [ ] 如果验收标准要求"能连接 X"，必须实际测试过连接
   [ ] 如果验收标准要求"能查询 X"，必须实际执行过查询

3. 运行验证
   [ ] 新增/修改的代码无语法错误（python -c "import xxx" 通过）
   [ ] 相关测试通过（pytest 对应测试文件）
   [ ] 不破坏现有功能（pytest 全量测试无新增失败）

4. 文档同步
   [ ] PROGRESS_TRACKER.md 状态已更新
   [ ] 如有设计偏离，已在「设计偏离记录」中说明
   [ ] 备注中写明了实际完成的内容摘要

═══════════════════════════════════════════════════════════
```

### 8.2 部分完成的处理方式

如果只完成了任务的一部分，**不得标记为 `已完成`**，应按以下方式处理：

```markdown
#### [P1-xx] 任务名称
- 状态: `进行中`          ← 保持进行中，不改为已完成
- 负责人: Claude-A
- 备注:
  - ✅ 已完成：viking_client.py 基础 CRUD 封装 + fallback 测试
  - ❌ 未完成：真实 OpenViking 环境写入/查询联调验收
  - 阻塞原因：OpenViking 服务未部署，无法进行真实环境测试
```

### 8.3 验收标准不可达时的处理

如果验收标准因外部原因（如服务未部署、硬件不可用）无法满足：

1. 状态改为 `阻塞`（不是 `已完成`）
2. 备注中明确说明哪些验收标准无法满足、原因是什么
3. 说明已完成的部分和剩余工作量
4. 等待阻塞解除后继续完成

### 8.4 PROGRESS_TRACKER 更新格式

更新进度时，必须包含以下信息：

```markdown
#### [P1-xx] 任务名称
- 状态: `已完成`
- 负责人: `模型名称或开发者`
- 关联文件: `src/xxx.py` (新增/修改)
- 备注: 简述实际完成内容。如："实现了 5 分区数据模型，含序列化/反序列化，
  通过 tests/test_knowledge_foundation.py 全部 12 个测试用例。"
```

**禁止的更新方式：**
- ❌ 只改状态为 `已完成`，不写备注
- ❌ 备注只写"已完成"两个字
- ❌ 未实际运行测试就声称测试通过
- ❌ 代码中留有 `pass` / `TODO` / `NotImplementedError` 就标记完成

### 8.5 审计与追溯

项目负责人可以随时对 `已完成` 的任务进行抽查：

1. 检查关联文件是否存在且内容完整
2. 运行对应测试是否通过
3. 验收标准是否真正满足
4. 如发现虚假完成，将状态回退为 `进行中`，并在备注中记录

---

*此文档是 AutoHySeeker 多端协作的唯一规范。所有参与者必须遵守。*

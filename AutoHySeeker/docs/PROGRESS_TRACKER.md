# AutoHySeeker 开发进度追踪

> 最后更新：2026-03-18
> 规则：参见 `COLLABORATION_GUIDE.md`

---

## Phase 1: 实验闭环

### Step 1: 基础设施

#### [P1-01] OpenViking 客户端封装
- 状态: `待认领`
- 负责人:
- 关联文件: `src/knowledge/viking_client.py` (新增)

#### [P1-02] 知识库数据模型
- 状态: `待认领`
- 负责人:
- 关联文件: `src/knowledge/schema.py` (新增)

#### [P1-03] 公共知识库查询 Skill
- 状态: `待认领`
- 负责人:
- 依赖: P1-01, P1-02
- 关联文件: `src/skills/knowledge_query_skill.py` (新增)

#### [P1-04] 增强知识归档 Skill
- 状态: `待认领`
- 负责人:
- 依赖: P1-01, P1-02
- 关联文件: `src/skills/knowledge_archive_skill.py` (修改)

#### [P1-05] 配置文件创建
- 状态: `待认领`
- 负责人:
- 关联文件: `configs/orchestrator.toml`, `configs/monitor.toml`, `configs/designer.toml`, `configs/knowledge.toml`, `configs/projects/her_feconi.toml` (新增)

#### [P1-06] 增强配置加载
- 状态: `待认领`
- 负责人:
- 依赖: P1-05
- 关联文件: `src/common/config.py` (修改)

### Step 2: 智能监控

#### [P1-07] L1 实时监控规则引擎
- 状态: `待认领`
- 负责人:
- 依赖: P1-05
- 关联文件: `src/skills/realtime_monitor_skill.py` (新增)

#### [P1-08] L2 心跳巡检
- 状态: `待认领`
- 负责人:
- 依赖: P1-03, P1-05
- 关联文件: `src/skills/heartbeat_inspector_skill.py` (新增)

#### [P1-09] Executor 集成两层监控
- 状态: `待认领`
- 负责人:
- 依赖: P1-07, P1-08
- 关联文件: `src/agents/exp_executor.py` (修改)

#### [P1-10] 监控控制路由
- 状态: `待认领`
- 负责人:
- 依赖: P1-09
- 关联文件: `src/api/routes/monitor.py` (新增)

### Step 3: 实验设计增强

#### [P1-11] ML 预测模型
- 状态: `待认领`
- 负责人:
- 关联文件: `src/ml/performance_predictor.py` (新增)

#### [P1-12] Designer 三阶段策略
- 状态: `待认领`
- 负责人:
- 依赖: P1-03, P1-11
- 关联文件: `src/agents/exp_designer.py` (修改)

### Step 4: 决策与人机协作

#### [P1-13] Orchestrator 人机协作增强
- 状态: `待认领`
- 负责人:
- 依赖: P1-03, P1-04, P1-06
- 关联文件: `src/agents/orchestrator.py` (修改)

#### [P1-14] 审批路由
- 状态: `待认领`
- 负责人:
- 依赖: P1-13
- 关联文件: `src/api/routes/approval.py` (新增)

#### [P1-15] OptimizationLoop 暂停/恢复
- 状态: `待认领`
- 负责人:
- 依赖: P1-13
- 关联文件: `src/graph/optimization_loop.py` (修改)

### Step 5: ChatAgent + 诊断增强

#### [P1-16] ChatAgent
- 状态: `待认领`
- 负责人:
- 依赖: P1-03
- 关联文件: `src/agents/chat_agent.py` (新增)

#### [P1-17] Diagnostics 知识库集成
- 状态: `待认领`
- 负责人:
- 依赖: P1-03, P1-04
- 关联文件: `src/agents/diagnostics.py` (修改)

#### [P1-18] Chat 路由增强
- 状态: `待认领`
- 负责人:
- 依赖: P1-16
- 关联文件: `src/api/routes/chat.py` (修改)

### Step 6: 项目管理 + 集成

#### [P1-19] 项目管理路由
- 状态: `待认领`
- 负责人:
- 关联文件: `src/api/routes/projects.py` (新增)

#### [P1-20] 知识库查询路由
- 状态: `待认领`
- 负责人:
- 依赖: P1-03
- 关联文件: `src/api/routes/knowledge.py` (新增)

#### [P1-21] LangGraph 路由增强
- 状态: `待认领`
- 负责人:
- 依赖: P1-16
- 关联文件: `src/graph/orchestrator.py` (修改), `src/graph/nodes.py` (修改)

#### [P1-22] 端到端集成测试
- 状态: `待认领`
- 负责人:
- 依赖: 所有 P1 任务
- 关联文件: `tests/` (新增/修改)

---

## Phase 1: 前端（PySide6 Dashboard）

### Step F1: Tab 架构 + Client 扩展

#### [F1-01] 重构 agent_dashboard.py 为 Tab 架构
- 状态: `待认领`
- 负责人:
- 关联文件: `MicroHySeeker/src/ui/widgets/agent_dashboard.py` (重写)

#### [F1-09] autohyseeker_client.py 扩展
- 状态: `待认领`
- 负责人:
- 关联文件: `MicroHySeeker/src/services/autohyseeker_client.py` (修改)

### Step F2: 各 Tab 实现（F1-01 完成后可全部并行）

#### [F1-02] 优化控制台 Tab
- 状态: `待认领`
- 负责人:
- 依赖: F1-01
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/optimization_tab.py` (新增)

#### [F1-03] Agent 状态 Tab
- 状态: `待认领`
- 负责人:
- 依赖: F1-01
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/agent_status_tab.py` (新增)

#### [F1-04] 实验历史 Tab
- 状态: `待认领`
- 负责人:
- 依赖: F1-01
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/history_tab.py` (新增)

#### [F1-05] 监控面板 Tab
- 状态: `待认领`
- 负责人:
- 依赖: F1-01, P1-10
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/monitor_tab.py` (新增)

#### [F1-06] 审批面板 Tab
- 状态: `待认领`
- 负责人:
- 依赖: F1-01, P1-14
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/approval_tab.py` (新增)

#### [F1-07] 对话面板 Tab
- 状态: `待认领`
- 负责人:
- 依赖: F1-01, P1-18
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/chat_tab.py` (新增)

#### [F1-08] 实时日志 Tab
- 状态: `待认领`
- 负责人:
- 依赖: F1-01
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/log_tab.py` (新增)

### Step F3: 集成测试

#### [F1-10] Phase 1 前端集成测试
- 状态: `待认领`
- 负责人:
- 依赖: 所有 F1 任务
- 关联文件: 手动测试清单

---

## Phase 2: 前端（文献 + 科研产出）

#### [F2-01] 文献管理 Tab
- 状态: `待认领`
- 负责人:
- 依赖: 后端 Phase 2A
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/literature_tab.py` (新增)

#### [F2-02] 科研分析 Tab
- 状态: `待认领`
- 负责人:
- 依赖: 后端 Phase 2B
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/research_tab.py` (新增)

#### [F2-03] 论文辅助 Tab
- 状态: `待认领`
- 负责人:
- 依赖: 后端 Phase 2B
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/writing_tab.py` (新增)

#### [F2-04] autohyseeker_client.py Phase 2 扩展
- 状态: `待认领`
- 负责人:
- 关联文件: `MicroHySeeker/src/services/autohyseeker_client.py` (修改)

#### [F2-05] Phase 2 集成测试
- 状态: `待认领`
- 负责人:
- 依赖: 所有 F2 任务

---

## 设计偏离记录

(暂无)

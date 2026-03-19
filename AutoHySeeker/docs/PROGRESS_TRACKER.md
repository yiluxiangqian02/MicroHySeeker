# AutoHySeeker 开发进度追踪

> 最后更新：2026-03-19
> 规则：参见 `COLLABORATION_GUIDE.md`

---

## Phase 1: 实验闭环

### Step 1: 基础设施

#### [P1-01] OpenViking 客户端封装
- 状态: `进行中`
- 负责人: `Copilot(GPT-5.3-Codex)`
- 关联文件: `src/knowledge/viking_client.py` (新增)
- 备注: 已完成分区 CRUD 封装与 fallback 测试；尚未完成“真实 OpenViking 环境写入/查询 experiments 分区”的联调验收。

#### [P1-02] 知识库数据模型
- 状态: `已完成`
- 负责人: `Copilot(GPT-5.3-Codex)`
- 关联文件: `src/knowledge/schema.py` (新增)
- 备注: 5 分区模型已实现并完成序列化/反序列化测试（tests/test_knowledge_foundation.py）。

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

## Phase 1: 前端（React Web Dashboard）

> 技术栈：React 18 + TypeScript + Vite + Tailwind + zustand + react-query + recharts
> 代码位置：`AutoHySeeker/frontend/src/`
> 详细修改指南：`docs/FRONTEND_MODIFICATION_GUIDE.md`

### Step F1: 路由 + 基础调整

#### [F1-01] App.tsx 添加新路由 + 侧边栏菜单
- 状态: `待认领`
- 负责人:
- 关联文件: `frontend/src/App.tsx` (修改)

#### [F1-02] Dashboard.tsx 增加优化循环状态卡片
- 状态: `待认领`
- 负责人:
- 依赖: F1-01, P1-15
- 关联文件: `frontend/src/pages/Dashboard.tsx` (修改)

### Step F2: 新页面实现（F1-01 完成后可全部并行）

#### [F1-03] Optimization.tsx 优化循环主页
- 状态: `待认领`
- 负责人:
- 依赖: F1-01, P1-15
- 关联文件: `frontend/src/pages/Optimization.tsx` (新增), `frontend/src/api/optimization.ts` (新增), `frontend/src/stores/optimizationStore.ts` (新增)

#### [F1-04] Chat.tsx Agent 对话页
- 状态: `待认领`
- 负责人:
- 依赖: F1-01, P1-18
- 关联文件: `frontend/src/pages/Chat.tsx` (新增), `frontend/src/api/chat.ts` (新增), `frontend/src/stores/chatStore.ts` (新增)

#### [F1-05] Knowledge.tsx 知识库页
- 状态: `待认领`
- 负责人:
- 依赖: F1-01, P1-20
- 关联文件: `frontend/src/pages/Knowledge.tsx` (新增), `frontend/src/api/knowledge.ts` (新增)

#### [F1-06] Diagnostics.tsx 诊断页
- 状态: `待认领`
- 负责人:
- 依赖: F1-01
- 关联文件: `frontend/src/pages/Diagnostics.tsx` (新增)

### Step F3: 已有页面增强

#### [F1-07] ExperimentDetail.tsx 接入真实 Agent 响应
- 状态: `待认领`
- 负责人:
- 依赖: F1-04, P1-16
- 关联文件: `frontend/src/pages/ExperimentDetail.tsx` (修改)

#### [F1-08] Experiments.tsx 迁移到 react-query + 增强筛选
- 状态: `待认领`
- 负责人:
- 关联文件: `frontend/src/pages/Experiments.tsx` (修改)

### Step F4: 国际化 + 集成测试

#### [F1-09] i18n 补充新页面翻译
- 状态: `待认领`
- 负责人:
- 依赖: 所有 F1 新页面
- 关联文件: `frontend/src/i18n/zh-CN.json` (修改), `frontend/src/i18n/en-US.json` (修改)

#### [F1-10] Phase 1 前端集成测试
- 状态: `待认领`
- 负责人:
- 依赖: 所有 F1 任务
- 关联文件: 手动测试 + Playwright E2E

### 已完成的前端基础

以下页面/组件已完成，无需重写：

- ✅ `Settings.tsx` — 4 Tab 完整设置页（通用/Agent/界面/通知）
- ✅ `Templates.tsx` — 模板管理页
- ✅ `ExperimentDetail.tsx` — 实验工作页框架（步骤链/结果摘要/AI 解读占位/数据图表）
- ✅ `Experiments.tsx` — 实验列表页
- ✅ `stores/settingsStore.ts` — 通用设置 store
- ✅ `stores/agentStore.ts` — 7 Agent 配置 store
- ✅ `api/client.ts` — axios 实例 + 拦截器
- ✅ `hooks/usePolling.ts` — 通用轮询 hook
- ✅ 所有 components（AgentCard, TemplateCard, TemplateDialog, StatusBadge, ModelSelector, ApiKeyInput）

---

## Phase 2: 前端（文献 + 科研产出）

#### [F2-01] 文献管理页
- 状态: `待认领`
- 负责人:
- 依赖: 后端 Phase 2A
- 关联文件: `frontend/src/pages/Literature.tsx` (新增)

#### [F2-02] 科研分析页
- 状态: `待认领`
- 负责人:
- 依赖: 后端 Phase 2B
- 关联文件: `frontend/src/pages/Research.tsx` (新增)

#### [F2-03] 论文辅助页
- 状态: `待认领`
- 负责人:
- 依赖: 后端 Phase 2B
- 关联文件: `frontend/src/pages/Writing.tsx` (新增)

#### [F2-04] Phase 2 集成测试
- 状态: `待认领`
- 负责人:
- 依赖: 所有 F2 任务

---

## 设计偏离记录

(暂无)

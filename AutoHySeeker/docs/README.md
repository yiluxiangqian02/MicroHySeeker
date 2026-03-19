# AutoHySeeker 文档导航

> 2026-03-18 | 文档体系 v4.0 — 多 Agent 实验闭环 + 科研产出

---

## 项目简介

AutoHySeeker 是 MicroHySeeker（微流控电化学实验桌面端）的 AI 多 Agent 科研助手。基于 LangGraph 编排 Agent，覆盖实验设计、执行监控、数据分析、故障诊断、知识管理、文献检索、科研产出全流程。

前端形态：PySide6 嵌入式 Dashboard（嵌入 MicroHySeeker 主窗口右侧面板）。

---

## 文档阅读顺序

### 第一步：理解架构（5 分钟）

| 顺序 | 文档 | 内容 |
| --- | --- | --- |
| 1 | `multiagent_00_architecture.md` | 系统总览：4 Agent 架构、交互流程 |
| 2 | `multiagent_01_orchestrator.md` | Orchestrator 详设：决策引擎、人机协作 |
| 3 | `multiagent_02_experiment_designer.md` | Designer 详设：三阶段策略、ML 切换 |
| 4 | `multiagent_03_experiment_executor.md` | Executor 详设：两层监控、实验执行 |
| 5 | `multiagent_05_diagnostics.md` | Diagnostics 详设：故障模式库 |

### 第二步：了解规划（10 分钟）

| 顺序 | 文档 | 内容 |
| --- | --- | --- |
| 6 | `PLAN_PHASE1_EXPERIMENT_LOOP.md` | Phase 1 后端规划：5 Agent + 5 Skill + 22 步实施 |
| 7 | `PLAN_PHASE2_RESEARCH_OUTPUT.md` | Phase 2 后端规划：LiteratureAgent + ResearchAnalystAgent |
| 8 | `UI_PLAN_V3.md` | 前端规划：10 Tab Dashboard（Phase 1 + Phase 2） |

### 第三步：开始开发

| 顺序 | 文档 | 内容 |
| --- | --- | --- |
| 9 | `COLLABORATION_GUIDE.md` | 多端协作规范：认领规则、冲突避免、提交格式 |
| 10 | `PROGRESS_TRACKER.md` | 实时进度：后端 P1-01~P1-22 + 前端 F1-01~F2-05 |
| 11 | `VALIDATION_AND_TESTING_GUIDE.md` | 测试验证指南 |

---

## 文档职责矩阵

| 主题 | 唯一归属文档 |
| --- | --- |
| 系统架构、Agent 职责 | `multiagent_00_architecture.md` |
| Orchestrator 详设 | `multiagent_01_orchestrator.md` |
| Designer 详设 | `multiagent_02_experiment_designer.md` |
| Executor 详设 | `multiagent_03_experiment_executor.md` |
| Diagnostics 详设 | `multiagent_05_diagnostics.md` |
| Phase 1 后端实施计划 | `PLAN_PHASE1_EXPERIMENT_LOOP.md` |
| Phase 2 后端实施计划 | `PLAN_PHASE2_RESEARCH_OUTPUT.md` |
| 前端 UI 技术方案 | `UI_PLAN_V3.md` |
| 协作规范 | `COLLABORATION_GUIDE.md` |
| 开发进度追踪 | `PROGRESS_TRACKER.md` |
| 测试验证 | `VALIDATION_AND_TESTING_GUIDE.md` |

---

## 任务编号体系

| 前缀 | 含义 | 范围 | 追踪位置 |
| --- | --- | --- | --- |
| P1-xx | Phase 1 后端任务 | P1-01 ~ P1-22 | `PROGRESS_TRACKER.md` |
| F1-xx | Phase 1 前端任务 | F1-01 ~ F1-10 | `PROGRESS_TRACKER.md` |
| F2-xx | Phase 2 前端任务 | F2-01 ~ F2-05 | `PROGRESS_TRACKER.md` |

---

## 快速定位

- 想认领任务？→ `PROGRESS_TRACKER.md`，找 `待认领` 状态的任务
- 想了解协作规则？→ `COLLABORATION_GUIDE.md`
- 想看后端 API 设计？→ `PLAN_PHASE1_EXPERIMENT_LOOP.md` 第七节
- 想看前端 Tab 设计？→ `UI_PLAN_V3.md` 第三~四节
- 想看 Agent 详细设计？→ `multiagent_0x_*.md` 系列
- 想跑测试？→ `VALIDATION_AND_TESTING_GUIDE.md`

---

## 已归档文档（历史参考，不再维护）

以下文档保留供历史参考，新开发请以上方文档为准：

- `architecture_overview.md` — 旧架构总览（已被 multiagent_00 替代）
- `langgraph_architecture.md` — 旧编排架构
- `skills_architecture.md` — 旧 Skill 架构
- `dev_backend.md` / `dev_frontend.md` — 旧开发指南
- `dev_agent_*.md` — 旧 Agent 开发指南（已被 multiagent_0x 替代）
- `project_plan.md` — 旧路线图
- `UI_PLAN.md` / `UI_PLAN_V2.md` — 旧前端规划（已被 UI_PLAN_V3 替代）
- `MODEL_PLANNING.md` / `MODEL_REQUIREMENTS.md` / `LLM_CONFIG.md` — 模型配置参考
- `dual_config_system.md` — 双配置系统说明
- `file-bridge-*.md` / `http-api-task.md` / `web-ui-task.md` — 旧任务文档

---

*此文档是 AutoHySeeker 文档体系的唯一入口。任何 AI 或开发者应从此文档开始阅读。*

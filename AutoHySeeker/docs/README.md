# AutoHySeeker 文档导航

> 2026-03-19 | 文档体系 v5.0 — 多 Agent 实验闭环 + 科研产出

---

## 项目定位

AutoHySeeker 是一个 AI 多 Agent 科研助手平台，服务于微流控电化学实验的全流程自动化。

- 后端：Python + FastAPI + LangGraph，4 个独立 Agent + 2 个内置 Skill
- 前端：React 18 + TypeScript + Vite + Tailwind CSS（独立 Web Dashboard）
- 知识库：OpenViking（向量检索 + 结构化存储）
- 桌面端：MicroHySeeker（PySide6，独立项目，通过 HTTP API 与 AutoHySeeker 通信）

**注意：AutoHySeeker 和 MicroHySeeker 是两个独立项目，各有独立的前端。**

---

## 文档索引

### 第一步：理解架构（必读）

| 顺序 | 文档 | 内容 |
| --- | --- | --- |
| 1 | `multiagent_00_architecture.md` | 系统总览：4 Agent + 2 Skill 架构、交互流程 |
| 2 | `multiagent_01_orchestrator.md` | Orchestrator 详设：调度、决策、人机协作、内置 Skill |
| 3 | `multiagent_02_experiment_designer.md` | Designer 详设：三阶段策略（文献→LLM→ML+LLM） |
| 4 | `multiagent_03_experiment_executor.md` | Executor 详设：两层监控、实验执行 |
| 5 | `multiagent_05_diagnostics.md` | Diagnostics 详设：故障诊断、知识库集成 |

### 第二步：了解规划

| 顺序 | 文档 | 内容 |
| --- | --- | --- |
| 6 | `PLAN_PHASE1_EXPERIMENT_LOOP.md` | Phase 1 后端：实验闭环（监控、设计增强、人机协作、Chat） |
| 7 | `PLAN_PHASE2_RESEARCH_OUTPUT.md` | Phase 2 后端：文献检索下载 + 科研分析绘图写作 |
| 8 | `FRONTEND_MODIFICATION_GUIDE.md` | 前端逐文件修改指南（保留/调整/新增分类） |
| 9 | `UI_PLAN_V3.md` | 前端页面设计方案 |

### 第三步：认领任务并开发

| 顺序 | 文档 | 内容 |
| --- | --- | --- |
| 10 | `COLLABORATION_GUIDE.md` | **必读** — 协作规范、认领规则、验收机制 |
| 11 | `PROGRESS_TRACKER.md` | 实时进度 — 在这里找 `待认领` 的任务 |
| 12 | `VALIDATION_AND_TESTING_GUIDE.md` | 测试验证指南 |

---

## AI 模型工作流程

如果你是一个 AI 模型，被要求参与 AutoHySeeker 开发，请严格按以下流程操作：

```text
1. 阅读本文件（docs/README.md）了解文档结构
       ↓
2. 阅读 COLLABORATION_GUIDE.md 了解协作规则和验收机制
       ↓
3. 阅读 PROGRESS_TRACKER.md 找到 `待认领` 的任务
       ↓
4. 阅读任务对应的设计文档（PLAN_PHASE1 或 PLAN_PHASE2）理解需求
       ↓
5. 阅读相关的 multiagent_0x 文档理解 Agent 设计细节
       ↓
6. 在 PROGRESS_TRACKER.md 中认领任务（改状态为 `进行中`）
       ↓
7. 开发实现
       ↓
8. 按 COLLABORATION_GUIDE 第八节的验收清单逐项检查
       ↓
9. 全部通过后，更新 PROGRESS_TRACKER.md（改状态为 `已完成` + 写备注）
```

**关键警告：**

- 未通过验收清单的任务，严禁标记为 `已完成`
- 只完成部分工作时，状态保持 `进行中`，在备注中说明已完成和未完成的部分
- 代码中不得留有 `pass` / `TODO` / `NotImplementedError` 等占位就声称完成
- 详见 `COLLABORATION_GUIDE.md` 第八节「任务完成验收机制」

---

## 任务编号体系

| 前缀 | 含义 | 范围 | 追踪位置 |
| --- | --- | --- | --- |
| P1-xx | Phase 1 后端任务 | P1-01 ~ P1-22 | `PROGRESS_TRACKER.md` |
| F1-xx | Phase 1 前端任务 | F1-01 ~ F1-10 | `PROGRESS_TRACKER.md` |
| F2-xx | Phase 2 前端任务 | F2-01 ~ F2-04 | `PROGRESS_TRACKER.md` |

---

## 快速定位

- 想认领任务？→ `PROGRESS_TRACKER.md`，找 `待认领` 状态的任务
- 想了解协作规则和验收标准？→ `COLLABORATION_GUIDE.md`
- 想看后端 API 设计？→ `PLAN_PHASE1_EXPERIMENT_LOOP.md`
- 想看前端修改方案？→ `FRONTEND_MODIFICATION_GUIDE.md`
- 想看 Agent 详细设计？→ `multiagent_0x_*.md` 系列
- 想跑测试？→ `VALIDATION_AND_TESTING_GUIDE.md`
- 想看代码目录结构和开发环境搭建？→ `../README_DEV.md`

---

## 技术栈速览

| 层面 | 技术 |
| --- | --- |
| 后端框架 | FastAPI + uvicorn |
| Agent 编排 | LangGraph |
| LLM 客户端 | OpenAI-compatible（支持多模型） |
| 知识库 | OpenViking |
| ML 优化 | Optuna + scikit-learn |
| 前端框架 | React 18 + TypeScript |
| 前端构建 | Vite 5 |
| 前端样式 | Tailwind CSS 3 |
| 前端状态 | zustand 5 |
| 前端异步 | @tanstack/react-query 5 |
| 前端图表 | recharts 3 |
| 包管理 | uv（后端）/ npm（前端） |

---

*此文档是 AutoHySeeker 文档体系的唯一入口。任何 AI 或开发者应从此文档开始阅读。*

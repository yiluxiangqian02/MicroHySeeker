# AutoHySeeker — 系统架构总览

> 2026-02-26 | v2.0 — 从 skills_architecture.md §一 提取并扩展
> 关联文档：[README.md](README.md) · [langgraph_architecture.md](langgraph_architecture.md) · [open_source_integration.md](open_source_integration.md)

---

## 一、项目定位

### 1.1 AutoHySeeker 与 MicroHySeeker 的关系

```
MicroHySeeker/              ← 实验室设备控制桌面端（PySide6）
  ├── src/                  ← 硬件驱动、实验引擎、UI
  ├── data/                 ← 实验数据产出
  └── config/               ← 系统配置

AutoHySeeker/               ← AI Agent 系统（独立项目，uv 管理）
  ├── src/
  │   ├── graph/            ← LangGraph 编排（谁先谁后、出错怎么办）
  │   ├── agents/           ← Agent 节点函数（决策逻辑 + System Prompt）
  │   ├── skills/           ← Skill 模块（多 Tool + LLM → 完整科研子任务）
  │   ├── tools/            ← 原子 Tool（一个函数做一件事）
  │   ├── rag/              ← OpenViking 集成层
  │   └── common/           ← 共享工具（配置、日志、LLM 客户端）
  └── data/                 ← Agent 自己的数据（知识库、检查点、缓存）
```

### 1.2 交互方式

```
┌──────────────────┐        ┌──────────────────────────────────┐
│  MicroHySeeker   │        │         AutoHySeeker             │
│  (桌面端)         │        │                                  │
│                  │  文件   │  ┌────────────────────┐          │
│  data/ ──────────┼───────►│  │  Tools (读取数据)   │          │
│  config/ ────────┼───────►│  │  - read_experiment  │          │
│  logs/ ──────────┼───────►│  │  - read_csv         │          │
│                  │        │  └────────┬───────────┘          │
│                  │  API   │  ┌────────┴───────────┐          │
│  Engine ◄────────┼────────│  │  Tools (控制实验)   │          │
│  (start/stop/    │  调用  │  │  - start_experiment │ Phase 4  │
│   load_program)  │        │  │  - stop_experiment  │          │
│                  │        │  └────────┬───────────┘          │
│                  │        │           │                      │
│                  │        │  ┌────────▼───────────┐          │
│                  │        │  │  Skills + Agents    │          │
│                  │        │  │  ↕ LLM 编排调用     │          │
│                  │        │  └────────┬───────────┘          │
│                  │        │           │                      │
│                  │        │  ┌────────▼───────────┐          │
│                  │        │  │ OpenViking 知识库    │          │
│                  │        │  │ viking://resources/  │          │
│                  │        │  └────────────────────┘          │
└──────────────────┘        └──────────────────────────────────┘
```

**三种交互模式**：
- **文件读取**：AutoHySeeker 直接读 MicroHySeeker 的 `data/`、`config/`、`logs/`（文件级耦合，Phase 1 立即可用）
- **实验控制**：通过 MicroHySeeker 暴露的 API（Phase 4，HTTP/WebSocket/IPC）
- **完全独立**：AutoHySeeker 即使没有 MicroHySeeker 也能分析已有数据

---

## 二、四层架构

```
Layer 4 — LangGraph      Graph 定义, State 管理, 条件路由, 检查点, 流式输出
Layer 3 — Agents          System Prompt + 决策函数 (Graph 中的节点)
Layer 2 — Skills          多 Tool + LLM 编排 → 完整科研子任务
Layer 1 — Tools           原子操作（ToolRegistry 管理, Function Calling 可用）
Layer 0 — OpenViking      上下文数据库：记忆、资源、技能的统一存储与检索
```

**各层职责**：

| 层级 | 职责 | 示例 | 是否需要 LLM |
|------|------|------|-------------|
| **Layer 4 — LangGraph** | 管"编排"：谁先谁后、出错怎么办、要不要问人 | `build_supervisor_graph()` | 否 |
| **Layer 3 — Agents** | 管"决策"：根据当前状态决定调哪个 Skill | `decide_action_node()` | 是（关键决策） |
| **Layer 2 — Skills** | 管"执行"：调多个 Tool + LLM → 产出结果 | `diagnose_failed_experiment()` | 视情况 |
| **Layer 1 — Tools** | 管"操作"：一个函数做一件事 | `read_echem_csv(path)` | 否 |
| **Layer 0 — OpenViking** | 管"记忆"：统一知识存储、分层检索、经验积累 | `viking://resources/experiments/` | 内置 VLM |

### 2.1 Tool vs Skill vs Agent 区分

```
Tool:   read_cv_csv(path) → DataFrame           纯数据操作，无推理，一调一用
Skill:  analyze_cv_experiment(run_dir) → Report  调多个 Tool + LLM → 完整分析报告
Agent:  DataAnalyst + System Prompt + 对话历史    持有多个 Skill，与用户交互
```

---

## 三、系统拓扑图

```
                          用户输入
                            │
                    ┌───────▼───────┐
                    │  Orchestrator  │  LangGraph Supervisor
                    │  (意图路由)     │  Node
                    └───┬───┬───┬───┘
                        │   │   │
          ┌─────────────┤   │   ├─────────────┐
          │             │   │   │             │
    ┌─────▼─────┐ ┌─────▼─┐│┌──▼──────┐ ┌───▼───────────┐
    │ DataAnalyst│ │Experi-│││Diagnos- │ │Knowledge      │
    │ Subgraph   │ │ment   │││tics     │ │Manager        │
    │ (A)        │ │Design │││Expert   │ │Subgraph       │
    │            │ │(B)    │││(D)      │ │(E)            │
    │ A1-A4     │ │B1-B4  │││D1-D3   │ │ E1-E3         │
    └────────────┘ └───────┘│└─────────┘ └───────────────┘
                            │
                   ┌────────▼────────┐
                   │  Experiment     │
                   │  Supervisor (C) │  ★ 核心 Subgraph
                   │                 │
                   │  C1-C3          │
                   │  ↕ D1-D3        │  ← C 出错时调用 D
                   └─────────────────┘
                            │
                   ┌────────▼────────┐
                   │   OpenViking    │
                   │  viking://      │  Layer 0 — 跨 Agent 共享
                   │  resources/     │
                   │  agent/memories │
                   │  user/memories  │
                   └─────────────────┘
```

---

## 四、核心设计原则

### 4.1 开源优先

> **不重复造轮子**。优先复用成熟开源项目，只在领域特定需求上做定制。

| 需求 | 选型 | 替代的自建工作 |
|------|------|--------------|
| 多 Agent 编排 | **LangGraph** | 手写状态机+条件分支 |
| 知识库 / RAG | **OpenViking** | ChromaDB + 手写分块/检索/记忆管线 |
| Skill 模板 | **SkillsMCP 生态** | 从零设计 17 个 Skill |
| 参数优化 | **Optuna** | 手写贝叶斯优化 |
| PDF 解析 | **pymupdf + marker** | 手写 PDF 提取器 |
| LLM 接口 | **OpenAI SDK** (兼容 Ollama) | 手写多 LLM 适配 |

详见 [open_source_integration.md](open_source_integration.md)。

### 4.2 渐进式实现

四个阶段，从最痛的点开始：

```
Phase 1 (CD)     → "实验出了问题，我知道为什么"       — 诊断 + 监控
Phase 2 (A)      → "实验数据出来了，AI 帮我分析"      — 数据分析
Phase 3 (B+E)    → "AI 帮我设计下一步实验"            — 设计 + 知识库
Phase 4 (联调)   → "AI 自主迭代实验"                  — 实时控制 + 自适应闭环
```

详见 [project_plan.md](project_plan.md)。

### 4.3 可降级运行

每个 Skill 标注了 LLM 依赖程度。核心 Tool 层不依赖 LLM，保证即使 API 不可用也能处理基础数据操作。

---

## 五、需求域覆盖

| 域 | 覆盖内容 | 对应 Agent | 对应 Skills |
|----|---------|-----------|------------|
| ②实验设计 | NL→方案、参数优化、方案审查、文献复现 | ExperimentDesigner (B) | B1-B4 |
| ③实验执行与监控 | 排程、执行、监控、自适应闭环 | ExperimentSupervisor (C) | C1-C3 |
| ④数据处理与分析 | 单实验分析、对比、趋势、NL查询 | DataAnalyst (A) | A1-A4 |
| ⑤故障诊断与运维 | 失败诊断、健康检查、交互排错 | DiagnosticsExpert (D) | D1-D3 |
| ⑥RAG知识检索 | 文档入库、知识问答、实验归档 | KnowledgeManager (E) | E1-E3 |
| ①文献获取（远期） | 搜索→下载→解析→入库 | 独立管线 | 详见 literature_automation_plan.md |

---

*此文档定义了 AutoHySeeker 的顶层架构视图。各层的细节分别在对应文档中展开。*

# AutoHySeeker 规划文档导航

> 2026-02-26 | 文档体系 v2.0 — 重组后消除重复，建立单一事实来源

---

## 项目简介

AutoHySeeker 是与 MicroHySeeker（微流控电化学实验桌面端）配套的 **AI 多 Agent 科研助手系统**。基于 LangGraph 编排 5 个专家 Agent，覆盖实验执行监控、故障诊断、数据分析、实验设计、知识管理全流程。

**核心理念**：充分利用开源生态（OpenViking、SkillsMCP 等）加速构建，而非从零造轮子。

---

## 文档阅读顺序

```
1. 系统总览         → architecture_overview.md        （项目定位、四层架构、交互方式）
2. 开源集成策略     → open_source_integration.md      （OpenViking、SkillsMCP、复用策略）
3. 编排架构         → langgraph_architecture.md        （State 设计、Graph 拓扑、编排逻辑）
4. 工具与技能规格   → tools_and_skills_spec.md         （Tool 清单、Skill 详细设计、依赖关系）
5. 开发指南（按优先级）：
   ├── P1: dev_agent_diagnostics_expert.md   → dev_agent_experiment_supervisor.md
   ├── P2: dev_agent_data_analyst.md
   ├── P3: dev_agent_knowledge_manager.md    → dev_agent_experiment_designer.md
   └── 路由: dev_agent_orchestrator.md
6. 项目路线图       → project_plan.md                  （优先级、四阶段路线图、依赖、配置）
7. 未来规划         → literature_automation_plan.md     （文献自动获取，暂不实施）
```

---

## 文档职责矩阵（每个主题只有一个归属文档）

| 主题 | **唯一归属文档** | 说明 |
|------|-----------------|------|
| 项目定位、与 MicroHySeeker 关系 | `architecture_overview.md` | 四层架构、交互模式 |
| OpenViking / SkillsMCP / 开源策略 | `open_source_integration.md` | 引入评估、替换映射、改造方案 |
| Agent 清单与职责总览 | `langgraph_architecture.md` §二 | 6 个 Agent 的职责和协作 |
| **所有 State TypedDict 定义** | `langgraph_architecture.md` §三 | 其他文档引用此处 |
| **所有 Graph 拓扑定义** | `langgraph_architecture.md` §四 | 其他文档引用此处 |
| Tool 函数清单（输入/输出/依赖） | `tools_and_skills_spec.md` §二 | 全部 50+ Tool 函数 |
| Skill 详细设计（流程/依赖/LLM角色） | `tools_and_skills_spec.md` §三 | 全部 17 个 Skill |
| Skill ↔ Tool ↔ 外部库关系表 | `tools_and_skills_spec.md` §四 | 一张总表 |
| Agent 节点函数实现 | 各 `dev_agent_*.md` | 每个 Agent 一份独立开发指南 |
| System Prompt 设计 | 各 `dev_agent_*.md` | Agent 专属 Prompt |
| 测试计划 | 各 `dev_agent_*.md` | 每个 Agent 的测试清单 |
| **优先级排序与路线图** | `project_plan.md` | 四阶段路线图+周粒度清单 |
| **项目结构与依赖** | `project_plan.md` | 目录结构、pyproject.toml、配置 |
| 文献自动化管线 | `literature_automation_plan.md` | 独立规划，暂不实施 |

---

## 关键架构决策记录（ADR）

| # | 决策 | 理由 | 归属文档 |
|---|------|------|---------|
| ADR-01 | 使用 LangGraph 而非手写编排 | StateGraph 原生条件边、Checkpoint 可恢复、HiL 内置 | `langgraph_architecture.md` §1.1 |
| ADR-02 | 用 ToolRegistry + Function Calling，不用 MCP | 项目规模不需要 MCP 服务化开销，ToolRegistry 更轻量直接 | `tools_and_skills_spec.md` §四 |
| ADR-03 | Phase 1 用"后分析模式"模拟执行 | 无需 IPC 即可验证完整 C→D→C 闭环 | `dev_agent_experiment_supervisor.md` §九 |
| ADR-04 | 引入 OpenViking 替代手写 RAG 管线 | 文件系统范式天然契合实验数据、L0/L1/L2 分层降低 Token、记忆自迭代 | `open_source_integration.md` §一 |
| ADR-05 | 利用 SkillsMCP 生态加速 Skill 开发 | 28万+ 开源 Skill，适配改造比从零写更快 | `open_source_integration.md` §二 |
| ADR-06 | 文献 RAG 不再独立建设，复用 OpenViking | OpenViking 统一资源管理能力覆盖文献入库/检索 | `open_source_integration.md` §三 |

---

## 文档间引用约定

- 跨文档引用统一格式：`详见 [文档名](文档名.md) §X.Y`
- State 定义引用：`State 定义详见 langgraph_architecture.md §三`
- Graph 拓扑引用：`Graph 定义详见 langgraph_architecture.md §四`
- Tool/Skill 规格引用：`详见 tools_and_skills_spec.md §二/§三`
- 路线图引用：`详见 project_plan.md §X`

---

*此文档是 AutoHySeeker 规划体系的入口。所有重要内容都有且仅有一个归属文档，杜绝信息重复和版本不一致。*

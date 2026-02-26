# AutoHySeeker — 项目计划与路线图

> 2026-02-26 | v1.0（合并自 langgraph_architecture.md §6-8 + skills_architecture.md §6-8）
> 关联文档：[architecture_overview.md](architecture_overview.md) · [open_source_integration.md](open_source_integration.md)

---

## 一、项目结构

```
AutoHySeeker/
├── pyproject.toml
├── README.md
├── configs/
│   ├── settings.toml            # AutoHySeeker 自身配置
│   ├── llm_config.toml          # LLM API 配置
│   ├── openviking.toml          # ★ OpenViking 配置（Phase 3 引入）
│   └── microhyseeker.toml       # MicroHySeeker 路径映射
│
├── src/
│   ├── __init__.py
│   │
│   ├── graph/                   # ★ LangGraph 图定义
│   │   ├── __init__.py
│   │   ├── state.py             # 所有 State TypedDict（唯一源）
│   │   ├── orchestrator.py      # 顶层 Orchestrator Graph
│   │   ├── analyst_graph.py     # DataAnalyst Subgraph
│   │   ├── designer_graph.py    # ExperimentDesigner Subgraph
│   │   ├── supervisor_graph.py  # ★ ExperimentSupervisor Subgraph
│   │   ├── diagnostics_graph.py # DiagnosticsExpert Subgraph
│   │   └── knowledge_graph.py   # KnowledgeManager Subgraph
│   │
│   ├── agents/                  # Agent 逻辑（节点函数 + System Prompt）
│   │   ├── __init__.py
│   │   ├── prompts.py           # 所有 System Prompt 集中管理
│   │   ├── router.py            # Orchestrator 路由逻辑
│   │   ├── analyst_nodes.py     # DataAnalyst 图的节点函数
│   │   ├── designer_nodes.py    # ExperimentDesigner 图的节点函数
│   │   ├── supervisor_nodes.py  # ExperimentSupervisor 图的节点函数
│   │   ├── diagnostics_nodes.py # DiagnosticsExpert 图的节点函数
│   │   └── knowledge_nodes.py   # KnowledgeManager 图的节点函数
│   │
│   ├── skills/                  # Skill 层
│   │   ├── __init__.py
│   │   ├── base.py              # Skill 基类 + SkillResult
│   │   ├── data_analysis/       # A1-A4
│   │   │   ├── single_experiment_analysis.py
│   │   │   ├── multi_experiment_comparison.py
│   │   │   ├── trend_tracking.py
│   │   │   └── nl_data_query.py
│   │   ├── experiment_design/   # B1-B4
│   │   │   ├── generate_experiment_plan.py
│   │   │   ├── optimize_parameters.py
│   │   │   ├── validate_and_review.py
│   │   │   └── replicate_literature.py
│   │   ├── experiment_execution/# C1-C3
│   │   │   ├── execution_monitor.py
│   │   │   ├── smart_scheduler.py
│   │   │   └── adaptive_loop.py
│   │   ├── diagnostics/         # D1-D3
│   │   │   ├── diagnose_failure.py
│   │   │   ├── system_health_check.py
│   │   │   └── interactive_troubleshooting.py
│   │   └── knowledge/           # E1-E3
│   │       ├── build_knowledge_base.py
│   │       ├── knowledge_qa.py
│   │       └── auto_archive.py
│   │
│   ├── tools/                   # Tool 层（原子操作）
│   │   ├── __init__.py
│   │   ├── data_reader.py       # 数据读取
│   │   ├── echem_analysis.py    # 电化学分析算法
│   │   ├── visualization.py     # 图表生成
│   │   ├── experiment_builder.py# 实验方案构建
│   │   ├── experiment_control.py# 实验控制（IPC，Phase 4）
│   │   ├── log_analysis.py      # 日志解析
│   │   ├── rag_tools.py         # → Phase 3 用 OpenViking 封装替代
│   │   └── report_generator.py  # 报告生成
│   │
│   ├── rag/                     # RAG 管线 → Phase 3 用 OpenViking 替代
│   │   ├── __init__.py
│   │   └── openviking_client.py # ★ VikingKnowledgeBase 封装
│   │   # 以下文件不再需要（OpenViking 内置）：
│   │   # embeddings.py / vector_store.py / chunker.py / pdf_parser.py / collections.py
│   │
│   └── common/                  # 共享工具
│       ├── __init__.py
│       ├── config.py            # 配置加载
│       ├── llm_client.py        # LLM API 统一封装
│       ├── tool_registry.py     # ToolRegistry + Function Calling
│       ├── types.py             # 共享类型定义
│       └── logger.py            # 日志
│
├── data/
│   ├── viking_workspace/        # ★ OpenViking 工作空间（替代 vector_db/）
│   ├── checkpoints/             # LangGraph Checkpoint DB
│   ├── cache/                   # LLM 响应缓存
│   └── templates/               # 报告模板
│
├── tests/
│   ├── test_tools/
│   ├── test_skills/
│   ├── test_graphs/             # Graph 集成测试
│   └── test_agents/
│
└── scripts/
    ├── cli.py                   # CLI 入口
    ├── init_knowledge_base.py   # 初始化知识库（→ OpenViking 导入）
    └── batch_analyze.py         # 批量分析历史数据
```

---

## 二、依赖管理

### 2.1 pyproject.toml

```toml
[project]
name = "autohyseeker"
version = "0.1.0"
description = "AI-powered experiment assistant for MicroHySeeker"
requires-python = ">=3.11"

dependencies = [
    # === 核心 ===
    "pydantic>=2.0",
    
    # === LangGraph 多 Agent 编排 ===
    "langgraph>=0.2",
    "langchain-core>=0.3",
    "langchain-openai>=0.3",
    
    # === 数据处理 ===
    "pandas>=2.0",
    "numpy>=1.24",
    "scipy>=1.11",
    
    # === 可视化 ===
    "matplotlib>=3.7",
    
    # === RAG（Phase 3 — OpenViking 替代 ChromaDB） ===
    "openviking>=0.1",                # ★ 上下文数据库
    "pymupdf>=1.23",                  # PDF 预处理（配合 OpenViking）
    
    # === 报告 ===
    "jinja2>=3.1",
    "python-docx>=1.0",
    
    # === 参数优化 ===
    "optuna>=3.0",
    
    # === 工具 ===
    "tomli>=2.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "ruff", "langsmith"]
eis = ["impedance>=1.7"]
plotly = ["plotly>=5.0"]

[tool.uv]
dev-dependencies = ["pytest", "pytest-asyncio", "ruff"]
```

> **注意**：原方案中的 `chromadb`, `sentence-transformers`, `langchain-text-splitters` 已被 `openviking` 替代。

### 2.2 环境初始化

```bash
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
uv init
uv add pydantic langgraph langchain-core langchain-openai pandas numpy scipy matplotlib openviking pymupdf jinja2 python-docx optuna tomli rich
uv add --dev pytest pytest-asyncio ruff langsmith
```

---

## 三、配置文件

### 3.1 configs/microhyseeker.toml

```toml
# MicroHySeeker 数据路径映射
[paths]
data_dir = "D:/AI4S/MicroHySeeker/MicroHySeeker/data"
config_dir = "D:/AI4S/MicroHySeeker/MicroHySeeker/config"
system_config = "D:/AI4S/MicroHySeeker/MicroHySeeker/config/system.json"
logs_dir = "D:/AI4S/MicroHySeeker/MicroHySeeker/logs"

[engine]
# 与 MicroHySeeker 引擎的通信方式
mode = "file"  # "file" | "websocket" | "ipc"
# websocket_url = "ws://localhost:9876"  # Phase 4 启用
```

### 3.2 configs/llm_config.toml

```toml
[default]
provider = "openai"     # "openai" | "ollama" | "azure"
model = "gpt-4o"
temperature = 0.1
max_tokens = 4096

[openai]
api_key_env = "OPENAI_API_KEY"
base_url = "https://api.openai.com/v1"

[ollama]
base_url = "http://localhost:11434/v1"
model = "qwen2.5:72b"

# LLM 模型选择策略：
# - Orchestrator (意图路由): gpt-4o-mini（简单分类）
# - DataAnalyst (数据解读): gpt-4o（需领域知识）
# - ExperimentDesigner (方案生成): gpt-4o（复杂推理）
# - ExperimentSupervisor (执行决策): gpt-4o（关键决策）
# - DiagnosticsExpert (故障诊断): gpt-4o（因果推理）
# - KnowledgeManager (知识问答): gpt-4o-mini（RAG+简单生成）

[embedding]
provider = "openai"               # Phase 3 用 OpenViking 的 embedding 配置
model = "text-embedding-3-small"
```

### 3.3 configs/openviking.toml

```toml
# Phase 3 引入 — 替代 ChromaDB + 手写 RAG 管线
[storage]
workspace = "./data/viking_workspace"

[embedding]
api_base = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
provider = "openai"
model = "text-embedding-3-small"
dimension = 1536

[vlm]
api_base = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
provider = "openai"
model = "gpt-4o-mini"
```

---

## 四、Skill 优先级矩阵

| 阶段 | Skill | 名称 | 为什么在这个阶段 | LLM 必要性 |
|------|-------|------|-----------------|------------|
| **P1** | **D1** | 失败实验诊断 | 最痛的点：实验失败了不知道为什么 | ⚠️ 降级可运行 |
| **P1** | **D2** | 系统健康检查 | 设备状态一目了然，预防问题 | ⚠️ 降级可运行 |
| **P1** | **D3** | 交互式排错 | "泵不转了"→引导排查→解决 | ❌ 必须 LLM |
| **P1** | **C1** | 实验监控（后分析） | 实验结束后自动出质量报告 | ⚠️ 降级可运行 |
| **P1** | **C2** | 实验排程 | 多实验排列优化 | ⚠️ 降级可运行 |
| **P2** | **A1** | 单次实验分析 | 完整分析报告+图表+LLM解读 | ⚠️ 降级可运行 |
| **P2** | **A2** | 多实验对比 | 浓度/扫速梯度对比 | ⚠️ 降级可运行 |
| **P2** | **A3** | 趋势追踪 | 跨天跨批次趋势 | ⚠️ 降级可运行 |
| **P2** | **A4** | NL数据查询 | "找出峰电流最大的实验" | ❌ 必须 LLM |
| **P3** | **E1** | 知识库构建 | ★ 用 OpenViking 替代 ChromaDB | ⚠️ 部分需要 |
| **P3** | **E2** | 知识问答 | 文献/手册问答 | ❌ 必须 LLM |
| **P3** | **B1** | NL→方案 | "帮我设计浓度梯度CV" | ❌ 必须 LLM |
| **P3** | **B3** | 方案审查 | 自动安全审查 | ⚠️ 降级可运行 |
| **P3** | **E3** | 自动归档 | 实验结果→OpenViking | ⚠️ 可无 LLM |
| **P4** | **C1** | 实验监控（实时） | 需要 MicroHySeeker IPC | ⚠️ 降级可运行 |
| **P4** | **C3** | 自适应闭环 | AI自主迭代实验 | ❌ 必须 LLM |
| **P4** | **B2** | 参数优化 | 贝叶斯优化需闭环数据 | ⚠️ 降级可运行 |
| **P4** | **B4** | 文献方法复现 | 依赖文献自动化管线 | ❌ 必须 LLM |

---

## 五、四阶段详细路线图

### Phase 1 — CD 构建期：监控与诊断基础（3-4 周）

> **目标**：跑完实验后，AI 能告诉你"发生了什么、为什么失败、设备状况如何"
> **特点**：只依赖文件读取，不需要实时 IPC，现有 `data/` 目录立刻可用

```
Week 1 — 基础设施 + 数据读取
  ☐ 项目初始化（uv init + 依赖安装 + 目录结构 + configs/）
  ☐ common/config.py — 配置加载（读 MicroHySeeker 的 data/config/ 路径）
  ☐ common/llm_client.py — LLM 统一调用封装（OpenAI/Ollama）
  ☐ common/tool_registry.py — ToolRegistry + Function Calling
  ☐ common/types.py — RunSummary, LogEntry, EchemData 等类型定义
  ☐ tools/data_reader.py — 全部 8 个 Tool 函数
  ☐ 单元测试：用 data/2026-02-13/ 真实数据验证

Week 2 — 日志分析 + 诊断工具
  ☐ tools/log_analysis.py — 日志解析/错误分类/泵异常检测
  ☐ tools/visualization.py — 基础图表（CV/LSV/i-t 曲线，泵时序图）
  ☐ tools/report_generator.py — Markdown 报告模板
  ☐ skills/base.py — Skill 基类 + SkillResult
  ☐ graph/state.py — DiagnosticsState TypedDict（★ 唯一定义位置）
  ☐ 单元测试：用失败实验数据测试 log_analysis

Week 3 — D1/D2 + LangGraph DiagnosticsExpert
  ☐ skills/diagnostics/diagnose_failure.py (D1)
  ☐ skills/diagnostics/system_health_check.py (D2)
  ☐ agents/diagnostics_nodes.py — 5 个节点函数
  ☐ graph/diagnostics_graph.py — DiagnosticsExpert Subgraph
  ☐ 端到端测试：diagnose <run_dir>

Week 4 — D3/C1/C2 + Orchestrator 雏形
  ☐ skills/diagnostics/interactive_troubleshooting.py (D3)
  ☐ skills/experiment_execution/execution_monitor.py (C1 后分析)
  ☐ skills/experiment_execution/smart_scheduler.py (C2)
  ☐ graph/state.py — 追加 SupervisorState
  ☐ graph/supervisor_graph.py — 基础版（后分析模式）
  ☐ graph/orchestrator.py — 路由（仅 Supervisor + Diagnostics）
  ☐ CLI: python -m autohyseeker.cli diagnose|health|review|schedule
```

**Phase 1 交付物**：
| 命令 | 功能 |
|------|------|
| `diagnose <run_dir>` | 失败原因 + 解决建议 |
| `health-check` | 系统健康评分 |
| `review <run_dir>` | 实验质量报告 |
| `schedule <experiments>` | 优化排程 |

---

### Phase 2 — 数据分析构建期（2-3 周）

> **目标**：AI 完整分析电化学数据，出图、提指标、做对比
> **前置**：Phase 1 的 data_reader / visualization / report_generator 已就绪

```
Week 5 — 电化学分析工具 + A1
  ☐ tools/echem_analysis.py — 全部分析 Tool
      detect_cv_peaks, calculate_tafel_slope, fit_eis_circuit,
      assess_data_quality, detect_anomalies, calculate_charge,
      extract_steady_state
  ☐ tools/visualization.py — 补全（EIS Nyquist/Bode, Tafel, 趋势图, 对比图）
  ☐ skills/data_analysis/single_experiment_analysis.py (A1)
  ☐ graph/state.py — 追加 AnalystState
  ☐ graph/analyst_graph.py — DataAnalyst Subgraph
  ☐ 单元测试：各电化学技术特征提取

Week 6 — A2/A3/A4 + DataAnalyst Agent
  ☐ skills/data_analysis/multi_experiment_comparison.py (A2)
  ☐ skills/data_analysis/trend_tracking.py (A3)
  ☐ skills/data_analysis/nl_data_query.py (A4)
  ☐ agents/analyst_nodes.py — 全部节点函数
  ☐ Orchestrator 追加 analyst 路由
  ☐ Checkpointer 切换：MemorySaver → SqliteSaver
  ☐ CLI: analyze | compare | trend | ask
```

**Phase 2 交付物**：
| 命令 | 功能 |
|------|------|
| `analyze <run_dir>` | 完整分析报告（图表+指标+LLM解读） |
| `compare <dirs>` | 多实验对比表+图 |
| `trend --metric peak_current --days 7` | 趋势图+解读 |
| `ask "上周哪个实验峰电流最大？"` | NL 查询 |

---

### Phase 3 — 实验设计期（2-3 周）

> **目标**：AI 帮设计实验方案 + 知识库支撑
> **关键变化**：★ 引入 OpenViking，替代 ChromaDB + 手写 RAG 管线
> **详见**：[open_source_integration.md](open_source_integration.md)

```
Week 7 — ★ OpenViking 集成 + 知识库
  ☐ pip install openviking
  ☐ rag/openviking_client.py — VikingKnowledgeBase 封装
  ☐ configs/openviking.toml — 配置
  ☐ skills/knowledge/build_knowledge_base.py (E1) — 使用 Viking API
  ☐ skills/knowledge/knowledge_qa.py (E2) — 使用 Viking 搜索
  ☐ graph/knowledge_graph.py — KnowledgeManager Subgraph
  ☐ 初始化知识库：灌入 CHI 660F 手册 + 电化学基础知识
  ☐ D1 升级：search_solutions 改用 OpenViking

Week 8 — 实验方案构建 B1/B3/E3
  ☐ tools/experiment_builder.py — step builder + 校验
  ☐ skills/experiment_design/generate_experiment_plan.py (B1)
  ☐ skills/experiment_design/validate_and_review.py (B3)
  ☐ skills/knowledge/auto_archive.py (E3) — 归档到 OpenViking
  ☐ graph/designer_graph.py — ExperimentDesigner Subgraph（含审查循环）
  ☐ CLI: design | review | ask-kb | archive

Week 9（可选）— Orchestrator + UI
  ☐ graph/orchestrator.py — 完整路由（全部 5 个 Agent）
  ☐ 简单 Chat UI（Gradio 或 Streamlit）
  ☐ Agent 记忆模式启用（viking://agent/memories/）
```

**Phase 3 交付物**：
| 命令 | 功能 |
|------|------|
| `design "做浓度梯度CV"` | 完整方案 JSON + 解释 |
| `review <experiment.json>` | 安全审查 + 建议 |
| `ask-kb "CV扫速一般用多少？"` | RAG 知识问答 |
| `archive <run_dir>` | 归档到 OpenViking |

---

### Phase 4 — 系统完善与联调期（后续迭代）

> **目标**：实时监控、自适应闭环、多 Agent 协作
> **前置**：MicroHySeeker 暴露 WebSocket/HTTP API

```
  ☐ MicroHySeeker 侧：暴露 WebSocket API
      get_engine_status, load_experiment, start/stop/pause,
      subscribe_events (实时数据流)
  ☐ tools/experiment_control.py — 实时版
  ☐ C1 升级：execution_monitor（实时模式——边跑边评估）
  ☐ skills/experiment_execution/adaptive_loop.py (C3)
  ☐ skills/experiment_design/optimize_parameters.py (B2, Optuna)
  ☐ skills/experiment_design/replicate_literature.py (B4)
  ☐ Human-in-the-loop 全面启用
  ☐ LangSmith 监控
  ☐ Chat UI 集成到 MicroHySeeker（PySide6 panel 或独立 Web）
```

---

## 六、Skill ↔ Tool ↔ 外部库 关系总表

```
Skill                          直接使用的 Tools                外部库依赖
─────────────────────────────────────────────────────────────────────────
A1 single_experiment_analysis  data_reader.*                   pandas, scipy
                               echem_analysis.*                matplotlib
                               visualization.*
                               LLM (解读)                      openai

A2 multi_experiment_comparison data_reader.*                   pandas, scipy
                               echem_analysis.*                matplotlib
                               visualization.*
                               LLM (对比解读)                  openai

A3 trend_tracking              data_reader.*                   pandas
                               echem_analysis.*                matplotlib
                               visualization.plot_trend
                               LLM (趋势解读)                  openai

A4 nl_data_query               data_reader.*                   pandas
                               echem_analysis.*
                               visualization.*
                               LLM (意图理解+编排)             openai

B1 generate_experiment_plan    data_reader.read_system_config  jsonschema
                               experiment_builder.*            pydantic
                               ★ viking_kb.search_literature   openviking
                               LLM (NL→方案)                   openai

B2 optimize_parameters         data_reader.*                   optuna
                               echem_analysis.*                scipy.optimize
                               LLM (解释)                      openai

B3 validate_and_review         experiment_builder.validate     jsonschema
                               ★ viking_kb.search              openviking
                               data_reader.read_system_config
                               LLM (审查)                      openai

B4 replicate_literature        ★ viking_kb.search_literature   openviking
                               experiment_builder.*            pymupdf
                               data_reader.read_system_config
                               LLM (方法提取)                  openai

C1 execution_monitor           experiment_control.*            (IPC, Phase 4)
                               echem_analysis.*                scipy
                               LLM (异常解读)                  openai

C2 smart_scheduler             experiment_builder.validate
                               data_reader.read_system_config
                               LLM (优化建议)                  openai

C3 adaptive_loop               所有上述 Skills (meta-skill)    optuna
                               LLM (决策)                      openai

D1 diagnose_failure            data_reader.*                   pandas, re
                               log_analysis.*
                               ★ viking_kb.search_error_sols   openviking (Phase 3+)
                               LLM (根因推理)                  openai

D2 system_health_check         data_reader.*                   pandas
                               log_analysis.*
                               LLM (评估)                      openai

D3 interactive_troubleshooting experiment_control.*            (IPC, Phase 4)
                               ★ viking_kb.search              openviking (Phase 3+)
                               log_analysis.*
                               LLM (对话式排查)                openai

E1 build_knowledge_base        ★ viking_kb.ingest_document     openviking
                               LLM (摘要, 可选)                openai

E2 knowledge_qa                ★ viking_kb.search              openviking
                               LLM (RAG生成)                   openai

E3 auto_archive                data_reader.*
                               echem_analysis.*
                               ★ viking_kb.ingest_experiment   openviking
```

---

## 七、测试策略

| 层 | 方法 | 依赖 | 示例 |
|----|------|------|------|
| **Tool** | 纯单元测试 | 不需要 LLM | `test_read_echem_csv()` |
| **Skill** | 集成测试 | 可 mock LLM | `test_diagnose_failure(mock_llm)` |
| **Graph** | 端到端测试 | 真实 LLM 或 LangSmith 录放 | `test_diagnostics_graph(real_data)` |

**测试数据**：用 `data/2026-02-13/` 作为黄金测试数据集（包含成功和失败实验）。

---

## 八、成本控制

- 所有 LLM 调用经过 `llm_client.py` 统一管理
- 内置 token 统计 + 成本估算
- 支持 LLM 响应缓存（相同输入不重复调用）
- 非关键路径优先使用 gpt-4o-mini
- OpenViking 的 L0/L1/L2 分层上下文大幅减少 token 消耗

---

*此文档是 AutoHySeeker 的唯一项目计划来源。路线图总览见 §5，依赖关系见 §6。*

# AutoHySeeker — 系统校验文档 (VALIDATION)

> 生成时间：2026-03-05  
> 分支：`feat/validation-plan`  
> 最后更新：2026-03-05（深度审计后修订）

---

## 一、已实现功能清单

### 1. 配置模块 (Phase 1)

| ID | 功能 | 文件路径 | 状态 |
|----|------|----------|------|
| CFG-01 | TOML 配置加载（settings / llm_config / microhyseeker） | `src/configs.py` | ✅ |
| CFG-02 | 懒加载单例（`get_settings` / `get_llm_config` / `get_microhyseeker_config`） | `src/configs.py` | ✅ |
| CFG-03 | 配置文件不存在时返回默认值（不抛异常） | `src/configs.py` | ✅ |

### 2. 公共模块 (Phase 1)

| ID | 功能 | 文件路径 | 状态 |
|----|------|----------|------|
| CMN-01 | `@registry.tool` 装饰器注册机制 | `src/common/tool_registry.py` | ✅ |
| CMN-02 | log_analysis 工具自动注册（5个工具） | `src/common/tool_registry.py` | ✅ |
| CMN-03 | OpenAI function calling JSON Schema 生成 | `src/common/tool_registry.py` | ✅ |
| CMN-04 | 扩展类型定义（7种新类型） | `src/common/types.py` | ✅ |
| CMN-05 | LLM 客户端封装（`chat_completion`） | `src/common/llm_client.py` | ✅ |
| CMN-06 | 结构化日志（`get_logger`） | `src/common/logger.py` | ✅ |

### 3. 工具层 Tools (Phase 2)

| ID | 功能 | 文件路径 | 状态 |
|----|------|----------|------|
| TOOL-01 | `load_echem_file` — 加载电化学 CSV 文件 | `src/tools/data_reader.py` | ✅ |
| TOOL-02 | `load_run_echem_files` — 批量加载 run 目录下所有 CSV | `src/tools/data_reader.py` | ✅ |
| TOOL-03 | `read_run_metadata` — 读取 run_summary.json | `src/tools/data_reader.py` | ✅ |
| TOOL-04 | `list_run_files` — 列出 run 目录文件树 | `src/tools/data_reader.py` | ✅ |
| TOOL-05 | `analyze_cv` — CV 峰值/面积分析 | `src/tools/echem_analysis.py` | ✅ |
| TOOL-06 | `analyze_lsv` — LSV 起始电位/Tafel 斜率分析 | `src/tools/echem_analysis.py` | ✅ |
| TOOL-07 | `analyze_eis` — EIS 阻抗拟合分析 | `src/tools/echem_analysis.py` | ✅ |
| TOOL-08 | `analyze_echem_files` — 批量文件分析（自动注册到 registry） | `src/tools/echem_analysis.py` | ✅ |
| TOOL-09 | `build_step` — 构建单个实验步骤 | `src/tools/experiment_builder.py` | ✅ |
| TOOL-10 | `build_experiment_plan` — 构建完整实验方案 | `src/tools/experiment_builder.py` | ✅ |
| TOOL-11 | `generate_param_grid` — 参数网格生成 | `src/tools/experiment_builder.py` | ✅ |
| TOOL-12 | `build_plans_from_grid` — 从网格批量生成 plan | `src/tools/experiment_builder.py` | ✅ |
| TOOL-13 | `validate_plan` — 方案合规性验证 | `src/tools/experiment_builder.py` | ✅ |
| TOOL-14 | `plan_to_dict` — Plan 序列化（含 datetime 转换） | `src/tools/experiment_builder.py` | ✅ |
| TOOL-15 | 日志解析工具（parse/classify/anomaly/summarize/timeline） | `src/tools/log_analysis.py` | ✅ |
| TOOL-16 | 实验控制接口 | `src/tools/experiment_ctrl.py` | ⚠️ 桩函数 |
| TOOL-17 | 文件监视器（`FileWatcher`） | `src/tools/file_watcher.py` | ✅ |
| TOOL-18 | 报告生成器（`ReportGenerator`） | `src/tools/report_generator.py` | ✅ |
| TOOL-19 | 数据可视化（`visualization.py`） | `src/tools/visualization.py` | ✅ |
| TOOL-20 | 知识检索器（`KnowledgeRetriever`） | `src/tools/knowledge_retriever.py` | ✅ |

### 4. Skills 层 (Phase 2–4)

| ID | 功能 | 文件路径 | 类型 | 状态 |
|----|------|----------|------|------|
| SK-A1 | `SingleExperimentAnalysisSkill` — 单实验数据分析 | `src/skills/single_experiment_analysis.py` | LLM-free | ✅ |
| SK-B1 | `GenerateExperimentPlanSkill` — 实验方案生成（含模板+参数网格） | `src/skills/generate_experiment_plan.py` | LLM-free | ✅ |
| SK-C1 | `ContextualizeExperimentSkill` — OpenViking KB 上下文合成 | `src/skills/contextualize_experiment.py` | LLM+降级 | ✅ |
| SK-C2 | `SuggestNextExperimentSkill` — 规则推荐下一实验 | `src/skills/suggest_next_experiment.py` | LLM-free | ✅ |
| SK-D1 | `DiagnoseFailureSkill` — 实验失败规则诊断 | `src/skills/diagnostics/diagnose_failure.py` | LLM-free | ✅ |
| SK-D2 | `SystemHealthCheckSkill` — 系统健康检查（4维度） | `src/skills/diagnostics/system_health_check.py` | LLM-free | ✅ |
| SK-D3 | `InteractiveTroubleshootingSkill` — 交互式故障决策树 | `src/skills/diagnostics/interactive_troubleshooting.py` | LLM-free | ✅ |
| SK-E1 | `ExecutionMonitorSkill` — 实验执行监控 | `src/skills/experiment_execution/execution_monitor.py` | LLM-free | ✅ |
| SK-E2 | `SmartSchedulerSkill` — 多实验智能调度 | `src/skills/experiment_execution/smart_scheduler.py` | LLM-free | ✅ |
| SK-LEGACY | `analyze_cv_skill` / `diagnose_experiment_skill` — 遗留功能函数 | `src/skills/analyze_cv.py`, `src/skills/diagnose_exp.py` | 函数式 | ✅ |

### 5. LangGraph 图层 (Phase 3–4)

| ID | 功能 | 文件路径 | 状态 |
|----|------|----------|------|
| GRAPH-01 | `DiagnosticsExpert` 子图（D1/D2 节点 + 条件路由） | `src/graph/diagnostics_graph.py` | ✅ |
| GRAPH-02 | `SupervisorGraph`（5路任务路由：monitor/schedule/diagnose/contextualize/suggest） | `src/graph/supervisor_graph.py` | ✅ |
| GRAPH-03 | `Orchestrator` 多 Agent 路由图 | `src/graph/orchestrator.py` | ✅ |
| GRAPH-04 | 共享状态类型 `AutoHySeekerState` | `src/graph/state.py` | ✅ |
| GRAPH-05 | `_FallbackDiagnosticsGraph` / `_FallbackSupervisorGraph`（无 LangGraph 降级） | `src/graph/*.py` | ✅ |

### 6. RAG / 知识库 (Phase 4)

| ID | 功能 | 文件路径 | 状态 |
|----|------|----------|------|
| RAG-01 | `VikingKnowledgeBase` — OpenViking SDK 封装 | `src/rag.py` | ✅ |
| RAG-02 | `search_literature` — 学术文献检索 | `src/rag.py` | ✅ |
| RAG-03 | `search_experiments` — 历史实验检索 | `src/rag.py` | ✅ |
| RAG-04 | `get_viking_kb()` 缓存单例 | `src/rag.py` | ✅ |
| RAG-05 | 无 SDK 时优雅降级（返回 `[]`，不抛异常） | `src/rag.py` | ✅ |

### 7. API 路由层 (Phase 3–4)

| ID | 功能 | 路径 | 文件 | 状态 |
|----|------|------|------|------|
| API-01 | `POST /diagnostics/invoke` — 通用诊断入口 | `/diagnostics/invoke` | `src/api/routes/diagnostics.py` | ✅ |
| API-02 | `POST /diagnostics/analyze-failure` — D1 快捷方式 | `/diagnostics/analyze-failure` | `src/api/routes/diagnostics.py` | ✅ |
| API-03 | `POST /diagnostics/check-health` — D2 快捷方式 | `/diagnostics/check-health` | `src/api/routes/diagnostics.py` | ✅ |
| API-04 | `POST /context/invoke` — 通用上下文入口 | `/context/invoke` | `src/api/routes/context.py` | ✅ |
| API-05 | `POST /context/contextualize` — C1 快捷方式 | `/context/contextualize` | `src/api/routes/context.py` | ✅ |
| API-06 | `POST /context/suggest-next` — C2 快捷方式 | `/context/suggest-next` | `src/api/routes/context.py` | ✅ |
| API-07 | 数据路由 `/data` | `/data/*` | `src/api/routes/data.py` | ✅ |
| API-08 | 任务路由 `/tasks` | `/tasks/*` | `src/api/routes/tasks.py` | ✅ |
| API-09 | Agent 路由 `/agents` | `/agents/*` | `src/api/routes/agents.py` | ✅ |

### 8. 优化模块 (Phase 1)

| ID | 功能 | 文件路径 | 状态 |
|----|------|----------|------|
| OPT-01 | `BayesianOptimizer` — 基于 Optuna 的贝叶斯优化 | `src/optimization/bayesian_optimizer.py` | ✅ |
| OPT-02 | `ParameterDefinition` — 搜索空间定义（float/int/categorical） | `src/optimization/bayesian_optimizer.py` | ✅ |
| OPT-03 | 目标函数库（HER/OER 效率目标） | `src/optimization/objective_functions.py` | ✅ |

### 9. Agent 层 (Phase 1)

| ID | 功能 | 文件路径 | 状态 |
|----|------|----------|------|
| AGT-01 | `BaseAgent` — LLM Agent 基类（`invoke` / `build_messages`） | `src/agents/base.py` | ✅ |
| AGT-02 | `DataAnalystAgent` — CV/EIS 信号解读 | `src/agents/data_analyst.py` | ✅ |
| AGT-03 | `DiagnosticsExpertAgent` — 故障诊断 | `src/agents/diagnostics.py` | ✅ |
| AGT-04 | `ExperimentDesignerAgent` — 实验设计 | `src/agents/exp_designer.py` | ✅ |
| AGT-05 | `ExperimentSupervisorAgent` — 实验监控协调 | `src/agents/exp_supervisor.py` | ✅ |
| AGT-06 | `KnowledgeManagerAgent` — 知识管理 | `src/agents/knowledge_mgr.py` | ✅ |

---

## 二、依赖完整性检查

### 2.1 Python 版本要求

| 要求 | 状态 |
|------|------|
| Python `>=3.11,<3.12`（使用内置 `tomllib`） | ✅ `pyproject.toml` 已指定 |

### 2.2 核心依赖（pyproject.toml 声明）

| 包 | 版本约束 | 用途 | 声明 | 状态 |
|----|---------|------|------|------|
| `langgraph` | `>=0.2` | LangGraph StateGraph / 子图 / 条件路由 | ✅ | ✅ OK |
| `openai` | `>=1.0` | LLM 调用（claude via OpenAI-compat API） | ✅ | ✅ OK |
| `fastapi` | `>=0.110` | REST API 框架 | ✅ | ✅ OK |
| `uvicorn[standard]` | `>=0.27` | ASGI 服务器 | ✅ | ✅ OK |
| `pandas` | `>=2.0` | CSV/DataFrame 数据处理 | ✅ | ✅ OK |
| `numpy` | `>=1.26` | 数值计算（峰值检测、统计） | ✅ | ✅ OK |
| `python-dotenv` | `>=1.0` | `.env` 文件加载 | ✅ | ✅ OK |
| `pydantic` | `>=2.0` | 数据模型验证 | ✅ | ✅ OK |
| `httpx` | `>=0.27` | 异步 HTTP 客户端 | ✅ | ✅ OK |
| `optuna` | `>=3.5` | 贝叶斯优化 | ✅ | ✅ OK |

### 2.3 缺失/未声明依赖

| 包 | 用途 | 实际使用位置 | 严重性 | 说明 |
|----|------|-------------|--------|------|
| `openviking` | OpenViking 知识库 SDK | `src/rag.py` | 🟡 中 | 代码含优雅降级，但应在 `[project.optional-dependencies]` 中声明 |
| `scipy` | 潜在的峰值检测依赖 | `src/tools/echem_analysis.py` | 🟢 低 | 需验证是否实际 import — 若使用了需加入依赖 |
| `matplotlib` | 数据可视化 | `src/tools/visualization.py` | 🟢 低 | 代码含 try/except 降级，但应在可选依赖中声明 |

### 2.4 可选依赖降级行为

| 包 | 降级行为 | 验证状态 |
|----|----------|---------|
| `openviking` | `is_available=False`；`search_*()` 返回 `[]` | ✅ 已实现 |
| `langchain-anthropic` | 回退至 OpenAI-compat 接口 | ✅ 已实现 |
| `matplotlib` | `visualization.py` 内部 try/except | ✅ 已实现 |

### 2.5 结构性问题

| 问题 | 严重性 | 详情 | 影响 |
|------|--------|------|------|
| **`experiment_execution/__init__.py` 为空** | 🔴 高 | 文件仅含 `"""Experiment execution skills package."""` 一行 docstring。`ExecutionMonitorSkill` 和 `SmartSchedulerSkill` 已完整实现但无法通过包导入。 | `from src.skills.experiment_execution import ExecutionMonitorSkill` 失败 |
| **`experiment_ctrl.py` 仅为桩函数** | 🟡 中 | `start_experiment()` 和 `stop_experiment()` 返回 `{"status": "stub", "message": "Hardware execution is not implemented in this phase."}` | 从 `src/tools/__init__.py` 正常导出但功能不可用 |
| **`microhyseeker.toml` 含硬编码绝对路径** | 🟡 中 | `data_dir = 'D:/AI4S/MicroHySeeker/MicroHySeeker/data'` — 不可移植 | 换环境后路径失效 |
| **双配置系统并存** | 🟡 中 | `src/common/config.py` 从 `.env` 加载 + `src/configs.py` 从 TOML 加载 — 存在同名配置冲突的可能（如 `DEFAULT_MODEL`） | 运行时取值可能不一致 |
| **`data/` 目录近乎为空** | 🟢 低 | 仅含 `templates/` 子目录，无样本数据 | 测试需手动构建 mock 数据 |
| **缺少项目级 `.gitignore`** | 🟢 低 | `AutoHySeeker/` 目录下无 `.gitignore`，依赖父仓库 | `__pycache__/`、`.venv/`、`logs/` 可能被误提交 |

### 2.6 配置文件完整性

| 文件 | 必需 | 状态 |
|------|------|------|
| `configs/settings.toml` | 必需（可为空） | ✅ 存在 |
| `configs/llm_config.toml` | 必需（可为空） | ✅ 存在 |
| `configs/microhyseeker.toml` | 必需（可为空） | ✅ 存在 |
| `pyproject.toml` | 必需 | ✅ 存在 |
| `.env.example` | 参考 | ✅ 存在 |
| `uv.lock` | 推荐（版本锁定） | ✅ 存在 |

### 2.7 模块导出完整性

| 包 `__init__.py` | 预期导出 | 状态 |
|------------------|----------|------|
| `src/skills/__init__.py` | D1/D2/D3 + A1/B1/C1/C2 + 遗留 skills | ✅ 正常 |
| `src/skills/diagnostics/__init__.py` | DiagnoseFailureSkill / SystemHealthCheckSkill / InteractiveTroubleshootingSkill + 单例 | ✅ 正常 |
| `src/skills/experiment_execution/__init__.py` | ExecutionMonitorSkill / SmartSchedulerSkill | ❌ **为空** — 未导出任何内容 |
| `src/graph/__init__.py` | build_diagnostics_graph / get_diagnostics_graph / build_supervisor_graph / get_supervisor_graph | ✅ 正常 |
| `src/tools/__init__.py` | 所有工具函数 + registry | ✅ 正常 |
| `src/agents/__init__.py` | 5 个 Agent 类 | ✅ 正常 |
| `src/optimization/__init__.py` | BayesianOptimizer + 目标函数 | ✅ 正常 |

---

## 三、验证测试清单

### 3.1 现有测试文件（6 个文件，~139 个测试函数）

| 测试文件 | 覆盖模块 | 测试数量 | 状态 |
|----------|----------|----------|------|
| `tests/test_import_smoke.py` | 核心导入 | 1 | ✅ |
| `tests/test_tools_phase2.py` | data_reader / echem_analysis / experiment_builder | 19 | ✅ |
| `tests/test_skills_phase2.py` | A1 / B1 + skills `__init__` 导出 | 17 | ✅ |
| `tests/test_phase3.py` | DiagnosticsGraph + diagnostics API routes + D1/D2 | 20 | ✅ |
| `tests/test_phase4_c1.py` | VikingKnowledgeBase + C1 ContextualizeExperiment | 25 | ✅ |
| `tests/test_phase4.py` | C1/C2 Skills + SupervisorGraph + /context API routes | 57 | ✅ |

### 3.2 缺失测试 — 🔴 高优先级

| 测试领域 | 涉及模块 | 建议测试文件 | 理由 |
|----------|---------|-------------|------|
| **Orchestrator 图路由** | `src/graph/orchestrator.py`, `src/graph/nodes.py` | `test_orchestrator.py` | 核心路由逻辑零覆盖；`route_intent()`、5 个 `run_*` agent runner 均未测试 |
| **SupervisorGraph 单元测试** | `src/graph/supervisor_graph.py` | `test_supervisor_graph.py` | 仅通过 Phase 4 集成测试间接覆盖 |
| **Agent 类** | `src/agents/base.py` + 5 个专业 agent | `test_agents.py` | 零覆盖；`BaseAgent.invoke()`、`build_messages()`、系统提示均未测试 |
| **LLM 客户端** | `src/common/llm_client.py` | `test_llm_client.py` | 重试逻辑（3次 + 2秒退避）、fallback model、超时行为均未测试 |
| **A1→C1→C2 端到端流水线** | A1 + C1 + C2 skills | `test_pipeline_e2e.py` | 验证数据从分析→上下文→建议的完整流转 |
| **API /agents/invoke 端到端** | `src/api/routes/agents.py` | `test_api_routes.py` | HTTP → orchestrator → agent → LLM → response 全链路未测试 |

### 3.3 缺失测试 — 🟡 中优先级

| 测试领域 | 涉及模块 | 建议测试文件 | 理由 |
|----------|---------|-------------|------|
| **优化模块** | `bayesian_optimizer.py`, `objective_functions.py` | `test_optimization.py` | Optuna 集成、搜索空间定义、目标函数评估零覆盖 |
| **实验执行 Skills** | `execution_monitor.py`, `smart_scheduler.py` | `test_experiment_execution.py` | 完整实现但零测试 |
| **API routes (agents/data/tasks)** | `agents.py`, `data.py`, `tasks.py` | `test_api_routes.py` | 仅 diagnostics 和 context 路由已测试 |
| **D3 交互式故障排查** | `interactive_troubleshooting.py` | 扩展 `test_phase3.py` | D1/D2 已测试但 D3 的 4 类故障决策树未覆盖 |
| **遗留 Skills** | `analyze_cv.py`, `diagnose_exp.py` | `test_legacy_skills.py` | 从 `skills.__init__` 导出但无专门测试 |
| **LLM 客户端重试** | `src/common/llm_client.py` | `test_llm_client.py` | mock HTTP 测试 3 次重试 + fallback model 切换 |
| **降级路径（无 LLM）** | C1 skill | `test_degradation.py` | C1 在 LLM 不可用时降级为 raw_chunks — 需显式验证 |

### 3.4 缺失测试 — 🟢 低优先级

| 测试领域 | 涉及模块 | 建议测试文件 | 理由 |
|----------|---------|-------------|------|
| **工具层（未覆盖部分）** | `echem_reader.py`, `file_watcher.py`, `log_analysis.py`, `registry.py`, `report_generator.py`, `visualization.py` | `test_tools_extended.py` | 预置工具层，无专门测试 |
| **配置模块** | `common/config.py`, `configs.py`, `common/logger.py` | `test_config.py` | env 加载和 TOML 解析边界情况 |
| **experiment_ctrl 桩** | `experiment_ctrl.py` | N/A | 桩函数 — 实现后再测试 |

### 3.5 模块级测试覆盖率评估

| 模块分类 | 模块总数 | 有测试覆盖 | 覆盖率 |
|----------|---------|-----------|--------|
| src/skills/ (含 diagnostics) | 10 | 6 (A1, B1, C1, C2, D1, D2) | ~60% |
| src/tools/ | 11 | 4 (data_reader, echem_analysis, experiment_builder, knowledge_retriever) | ~36% |
| src/graph/ | 5 | 1 (diagnostics_graph) | ~20% |
| src/agents/ | 7 | 1 (diagnostics_nodes) | ~14% |
| src/api/routes/ | 5 | 2 (diagnostics, context) | ~40% |
| src/common/ | 5 | 0 | 0% |
| src/optimization/ | 2 | 0 | 0% |
| **总计** | **45** | **14** | **~31%** |

---

## 四、行动项

### 🔴 紧急（上线前必须修复）

| # | 行动 | 涉及文件 | 预估工时 |
|---|------|---------|---------|
| **A1** | **填充 `experiment_execution/__init__.py`** — 导出 `ExecutionMonitorSkill` 和 `SmartSchedulerSkill` | `src/skills/experiment_execution/__init__.py` | 5 分钟 |
| **A2** | **在 `pyproject.toml` 中声明 `openviking` 为可选依赖** — 添加 `[project.optional-dependencies]` 段：`kb = ["openviking"]` | `pyproject.toml` | 5 分钟 |
| **A3** | **编写 `test_orchestrator.py`** — 测试 `orchestrator.py` 路由逻辑 + `nodes.py` 各 agent runner（mock LLM） | `tests/test_orchestrator.py` | 2 小时 |
| **A4** | **编写 `test_agents.py`** — 测试 `BaseAgent.invoke()`、`build_messages()` 和各专业 agent 系统提示（mock `chat_completion`） | `tests/test_agents.py` | 2 小时 |
| **A5** | **编写集成测试 `test_pipeline_e2e.py`** — 验证 A1→C1→C2 数据流水线端到端 | `tests/test_pipeline_e2e.py` | 3 小时 |
| **A6** | **编写 `test_api_routes.py`** — 覆盖 `/agents/invoke`、`/data/experiments`、`/tasks/create`、`/tasks/{id}/status` | `tests/test_api_routes.py` | 2 小时 |

### 🟡 重要（Beta 前修复）

| # | 行动 | 涉及文件 | 预估工时 |
|---|------|---------|---------|
| **B1** | **替换 `microhyseeker.toml` 中的硬编码路径** — 改为相对路径或环境变量插值 | `configs/microhyseeker.toml` | 30 分钟 |
| **B2** | **实现或标记 `experiment_ctrl.py`** — 实现真实硬件接口或在导出时添加 "stub" 警告日志 | `src/tools/experiment_ctrl.py` | 2 小时 |
| **B3** | **编写 `test_optimization.py`** — 测试 Bayesian 优化器参数空间、目标函数和 Optuna study | `tests/test_optimization.py` | 2 小时 |
| **B4** | **编写 `test_experiment_execution.py`** — 测试 ExecutionMonitorSkill 和 SmartSchedulerSkill | `tests/test_experiment_execution.py` | 2 小时 |
| **B5** | **补充 D3 测试** — 在 `test_phase3.py` 中新增 4 类故障决策树覆盖 | `tests/test_phase3.py` | 1 小时 |
| **B6** | **编写 `test_llm_client.py`** — 测试重试逻辑（3次 + 退避）、fallback model 和超时 | `tests/test_llm_client.py` | 1 小时 |
| **B7** | **统一或文档化双配置系统** — 明确 `.env` 与 TOML 的优先级关系 | `docs/` 或 `src/configs.py` | 1 小时 |

### 🟢 增强（加固阶段）

| # | 行动 | 涉及文件 | 预估工时 |
|---|------|---------|---------|
| **C1** | **编写 `test_tools_extended.py`** — 覆盖 echem_reader、file_watcher、log_analysis、registry、report_generator、visualization | `tests/test_tools_extended.py` | 3 小时 |
| **C2** | **编写 `test_config.py`** — 测试 TOML 加载边界情况、缺失文件、env 覆盖 | `tests/test_config.py` | 1 小时 |
| **C3** | **添加项目级 `.gitignore`** — 排除 `__pycache__/`、`.venv/`、`logs/`、`.env` | `AutoHySeeker/.gitignore` | 5 分钟 |
| **C4** | **验证 `scipy` 依赖** — 检查 `echem_analysis.py` 是否使用 scipy 峰值检测；若有则加入 `pyproject.toml` | `pyproject.toml` | 15 分钟 |
| **C5** | **添加 CI 工作流** — GitHub Actions 运行 `uv run pytest tests/` | `.github/workflows/ci.yml` | 1 小时 |
| **C6** | **添加测试数据夹具** — 在 `tests/fixtures/` 放置样本 CV/LSV/EIS CSV 和 mock run 目录 | `tests/fixtures/` | 1 小时 |
| **C7** | **添加 `pytest-asyncio`** — 替换 `asyncio.get_event_loop().run_until_complete()` | `pyproject.toml` + tests | 1 小时 |
| **C8** | **添加 `pytest-cov`** — CI 中强制 80%+ 行覆盖率 | `pyproject.toml` + CI config | 30 分钟 |

---

## 五、已知限制与风险

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|----------|
| `openviking` SDK 未安装 | 低 | RAG 功能不可用，但系统正常运行 | 已实现双层降级 |
| LLM API 密钥未配置 | 低 | C1 退化为 raw_chunks 输出 | 已实现降级 |
| `asyncio.get_event_loop()` deprecation | 中 | Python 3.10+ 已有警告 | 待迁移至 pytest-asyncio |
| Pydantic v2 `model_dump` 日期序列化 | 低 | 已在 `plan_to_dict()` 手动处理 | 已修复 |
| Windows 路径分隔符 | 低 | 代码均使用 `pathlib.Path` | 已兼容 |
| `experiment_ctrl.py` 为桩函数 | 中 | 硬件接口未实现 | 后续 Phase 实现 |

---

## 六、运行验证的完整步骤

```bash
# 1. 进入项目目录
cd AutoHySeeker

# 2. 安装依赖（使用锁文件确保可复现）
uv sync

# 3. 运行所有现有测试
uv run pytest tests/ -v

# 4. 仅运行验证测试
uv run pytest tests/test_validation.py -v

# 5. 带覆盖率报告（需安装 pytest-cov）
uv run pytest tests/ --cov=src --cov-report=term-missing
```

---

## 七、总结

| 指标 | 值 |
|------|---|
| 已实现功能模块 | 45 个 |
| 已完成 Phase | 4/4（Phase 1–4） |
| 现有测试文件 | 6 |
| 现有测试函数 | ~139 |
| 模块级测试覆盖率 | ~31%（14/45 模块有测试） |
| 结构性缺陷 | 3 个（空 `__init__`、桩函数、硬编码路径） |
| 未声明可选依赖 | 1 个（`openviking`） |
| 紧急行动项 | 6 |
| 重要行动项 | 7 |
| 增强行动项 | 8 |

---

*文档由深度代码审计生成 | 分支：`feat/validation-plan`*

# Agent Coordination

## Active Tasks

| Task ID | Agent | Branch | Status | Description | Started At | Notes |
|---|---|---|---|---|---|---|
| TASK_013 | Copilot (claude-sonnet-4.6) | feat/fix-a3-a6-tests | done | Fix A3-A6: Write critical tests - test_orchestrator.py, test_agents.py, test_pipeline_e2e.py, test_api_routes.py. Mock LLM calls. Update VALIDATION.md | 2026-03-05 | - |
| TASK_014 | Copilot (claude-sonnet-4.6) | feat/fix-b1-paths | done | Fix B1: Replace hardcoded paths in configs/microhyseeker.toml with relative paths + ${VAR:-default} env var syntax. Updated src/configs.py with _expand_path(). | 2026-03-05 | - |
| TASK_017 | Copilot (claude-sonnet-4.6) | feat/fix-b3-b7 | done | Fix B3-B7: Write tests for optimization, experiment_execution, D3 diagnostics, llm_client. Document dual config system. | 2026-03-06 | - |

Status values: `pending` | `running` | `done` | `failed` | `review`

## Completed Tasks (latest)

| Task ID | Agent | Branch | Result | Completed At |
|---|---|---|---|---|
| TASK_001 | Codex (GPT-5) | feat/autohyseeker-core-scaffold | done | 2026-03-03 |
| TASK_002 | Copilot (claude-sonnet-4.6) | feat/phase2-tools-skills | done | 2026-03-05 |
| TASK_003 | Copilot (claude-sonnet-4.6) | feat/phase3-langgraph-api | done | 2026-03-05 |
| TASK_006 | Copilot (claude-sonnet-4.6) | feat/phase4-context-supervisor | done | 2026-03-05 |
| TASK_007 | Copilot (claude-sonnet-4.6) | feat/phase4-context-supervisor | done | 2026-03-05 |
| TASK_010 | Copilot (claude-sonnet-4.6) | feat/phase4-c2 | done | 2026-03-05 |
| TASK_011 | Copilot (claude-sonnet-4.6) | feat/validation-plan | done | 2026-03-05 |
| TASK_013 | Copilot (claude-sonnet-4.6) | feat/fix-a3-a6-tests | done | 2026-03-05 |
| TASK_014 | Copilot (claude-sonnet-4.6) | feat/fix-b1-paths | done | 2026-03-05 |
| TASK_017 | Copilot (claude-sonnet-4.6) | feat/fix-b3-b7 | done | 2026-03-06 |

## Safety Rules

Do not delete or overwrite these paths:

```text
MicroHySeeker/src/
MicroHySeeker/config/system.json
data/
logs/
AutoHySeeker/OpenViking/
.git/
```

## 经验库

| 经验 | 适用场景 |
|---|---|
| 在 PowerShell 不可用的环境中（缺少 pwsh），只能用 `create`/`edit`/`view` 工具操作文件，无法建新目录 → 新 Skill 直接平铺在 `src/skills/` 下（与 `analyze_cv.py` 同级），不建子包 | 无 Shell 访问的 Windows 环境 |
| Tool 层已在模块 import 时自动向 `tool_registry` 注册（`_register()` 模式），新 Skill 无需手动注册 | 调用 `registry.list_tools()` 时工具已可用 |
| Skill 基类 `BaseSkill.execute()` 是 `async`，测试时用 `asyncio.get_event_loop().run_until_complete()` 驱动（pytest-asyncio 不在默认依赖中） | 编写 Skill 单元测试 |
| `ExperimentPlan` 使用 Pydantic v2，`plan.model_dump()` 不会自动把 `datetime` 转成字符串 → `plan_to_dict()` 需手动 `.isoformat()` | 序列化 ExperimentPlan 为 JSON |
| langgraph `set_conditional_entry_point` 已废弃，改用 `add_conditional_edges(START, route_fn, path_map)` —— 参见 `src/graph/diagnostics_graph.py` | 编写 LangGraph StateGraph |
| 图模块中应加 `_FallbackGraph` 以支持无 langgraph 环境；`get_*_graph()` 缓存单例避免重复编译 | 新建 LangGraph subgraph |
| FastAPI POST 端点中 `dict[str, Any] \| None` 类型参数会导致解析歧义，快捷路由 query param 应只用简单标量类型 | 设计 FastAPI 路由参数 |
| C1/C2 Skills 平铺在 `src/skills/` 下（`contextualize_experiment.py`, `suggest_next_experiment.py`），LLM-free，使用 `statistics` 标准库做均值/σ/趋势分析 | 无 LLM 依赖的对比分析场景 |
| `supervisor_graph.py` 应独立于 `orchestrator.py`（二者都存在）：`orchestrator.py` 是多 Agent 路由，`supervisor_graph.py` 是特定任务类型路由（monitor/schedule/diagnose/contextualize/suggest） | 新增任务类型节点时修改 `supervisor_graph.py` |
| C1→C2 数据流可通过 `state["context"]["context_data"]` 传递（`contextualize_node` 写入，`suggest_node` 读取），也可在 API 请求 `context_data` 字段直接传递 | 设计 C1/C2 串联流程 |
| PROGRESS.md 需在每个 Phase 完成后更新总体状态表 + 任务状态表 + 详细说明三个部分，确保文档与代码同步 | 多 Phase 项目文档管理 |
| C2 SuggestNextExperimentSkill 完全 LLM-free，规则优先级：anomalies > declining trend > goal keywords > generic；context_data 为 None 时只看 goal | 实现无 LLM 的推荐系统 |
| `src/skills/__init__.py` 导出每个新 Skill 时需同时导出 Class 和 singleton 实例，并在 `__all__` 中注册两者 | 维护 skills 包导出规范 |
| `experiment_execution/__init__.py` 应导出 `ExecutionMonitorSkill`/`SmartSchedulerSkill` 及其 singleton（`execution_monitor_skill`/`smart_scheduler_skill`），模式与 `diagnostics/__init__.py` 一致 | 新增 A1/A2 Skill 包导出 |
| `openviking` 是可选依赖，应放在 `pyproject.toml` 的 `[project.optional-dependencies]` 下，extra 名为 `rag`，安装命令 `pip install autohyseeker[rag]` | 管理可选 RAG 依赖 |
| TASK_011 校验文档：`VALIDATION.md` 记录全量功能清单（61项）、26+个新验证测试（`tests/test_validation.py`）、依赖完整性检查表；可用 `uv run pytest tests/test_validation.py -v` 直接运行 | 系统校验/健康检查场景 |
| TASK_013 测试最佳实践：mock LLM 时用 `patch("src.agents.base.chat_completion", new=AsyncMock(...))` + `patch("src.common.llm_client.OPENAI_API_KEY", "test-key")`；避免 patch 字典 `AGENT_MAP`（会破坏 `__getitem__`） | 编写 Agent/Orchestrator 测试 |
| TASK_013 FastAPI TestClient 测试：在 `@pytest.fixture` 中创建 `TestClient(app)`；route 级 mock 用 `patch("src.api.routes.agents.get_supervisor_graph", return_value=mock_graph)`（不 patch src.graph.orchestrator 全局函数） | 编写 FastAPI 路由集成测试 |
| `configs/microhyseeker.toml` 中的路径值支持 `${VAR:-default}` 语法；`src/configs.py` 的 `_expand_path()` 在 `MicroHySeekerConfig.load()` 中展开 env var 并将相对路径解析到 `_CONFIGS_DIR.parent`（AutoHySeeker/） | 任何需要跨机器可移植路径的 TOML 配置场景 |
| TASK_017 双配置系统：`src/common/config.py`（环境变量/`.env`，用于 LLM 客户端和 API 服务器）与 `src/configs.py`（TOML 文件，用于结构化应用配置），二者并存。文档见 `docs/dual_config_system.md` | 需要理解两套配置来源时 |
| TASK_017 测试 `asyncio.sleep` 时需 patch 模块内的引用：`patch("src.common.llm_client.asyncio.sleep", new=AsyncMock())`，而非全局 `patch("asyncio.sleep")`，否则不能阻止实际 sleep | 测试包含 `asyncio.sleep` 重试逻辑的异步函数 |
| TASK_017 BayesianOptimizer 测试：用 `seed=42` 保证可重复性；`ParameterSpace` 可直接从 `Mapping` 构造（`{"x": [0.0, 1.0]}`），不必手动 `add_float`；`MultiObjectiveBayesianOptimizer` 要求至少 2 个方向 | 编写 Optuna 优化器单元测试 |


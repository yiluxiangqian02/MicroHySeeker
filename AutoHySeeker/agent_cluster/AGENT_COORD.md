# Agent Coordination

## Active Tasks

| Task ID | Agent | Branch | Status | Description | Started At | Notes |
|---|---|---|---|---|---|---|
| _(none)_ | - | - | - | - | - | - |

Status values: `pending` | `running` | `done` | `failed` | `review`

## Completed Tasks (latest)

| Task ID | Agent | Branch | Result | Completed At |
|---|---|---|---|---|
| TASK_001 | Codex (GPT-5) | feat/autohyseeker-core-scaffold | done | 2026-03-03 |
| TASK_002 | Copilot (claude-sonnet-4.6) | feat/phase2-tools-skills | done | 2026-03-05 |
| TASK_003 | Copilot (claude-sonnet-4.6) | feat/phase3-langgraph-api | done | 2026-03-05 |

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
| TASK_004 与 TASK_002 任务目标相同（Phase 2 Tool/Skill 实现），代码已在 `feat/phase2-tools-skills` 分支存在；重复派发时直接验证文件完整性并更新 AGENT_COORD 即可 | 防止重复派发造成重复劳动 |


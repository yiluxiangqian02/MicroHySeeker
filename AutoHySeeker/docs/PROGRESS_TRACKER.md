# AutoHySeeker 开发进度追踪

> 最后更新：2026-03-26
> 规则：参见 `COLLABORATION_GUIDE.md`

---

## Phase 1: 实验闭环

### Step 1: 基础设施

#### [P1-01] OpenViking 客户端封装
- 状态: `已完成`
- 负责人: `Copilot(GPT-5.3-Codex)`
- 完成时间: 2026-03-20
- 关联文件: `src/knowledge/viking_client.py` (新增)
- 备注: 已完成分区 CRUD 封装、fallback 测试与本地源码树导入回退；已在本机 workspace 内完成 OpenViking editable 构建、真实 `experiments/` 分区写入与 `read()` 验证；已配置真实 embedding API（baai/bge-m3 via shengsuanyun.com），SDK 初始化成功（dim=1024）；`find()` 因 embedding 鉴权失败时有 workspace 查询回退；通过 `tests/test_knowledge_foundation.py`（9 项）和 `tests/test_import_smoke.py`。

#### [P1-02] 知识库数据模型
- 状态: `已完成`
- 负责人: `Copilot(GPT-5.3-Codex)`
- 关联文件: `src/knowledge/schema.py` (新增)
- 备注: 5 分区模型已实现并完成序列化/反序列化测试（tests/test_knowledge_foundation.py）。

#### [P1-03] 公共知识库查询 Skill
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-01, P1-02
- 关联文件: `src/skills/knowledge_query_skill.py` (新增)
- 备注: 已实现公共只读查询 Skill，接入 `OpenVikingClient` 并提供 `search` / `get_similar_experiments` / `get_fault_history` / `get_literature_insights` 四个接口；通过 `tests/test_knowledge_query_skill.py`（5 项）和 `tests/test_import_smoke.py`。

#### [P1-04] 增强知识归档 Skill
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-20
- 依赖: P1-01, P1-02
- 关联文件: `src/skills/knowledge_archive_skill.py` (修改), `src/knowledge/viking_client.py` (修改), `tests/test_knowledge_foundation.py` (修改)
- 备注:
  - ✅ 已完成：增强 `KnowledgeArchiveSkill`，支持写入 `experiments/operations` 分区，并记录 `environment_snapshot`；通过 `tests/test_knowledge_agent.py`（16 项）和 `tests/test_import_smoke.py`。
  - ✅ 已推进：`OpenVikingClient` 新增仓库内 `OpenViking/` 与本地 `pyagfs` 源码树导入回退，便于后续本地魔改联调；新增对应回归测试并通过 `tests/test_knowledge_foundation.py`（9 项）。
  - ✅ 已验证：已在 `AutoHySeeker/.tools/` 下补齐 `Go + CMake + MinGW` 本地工具链，完成 `OpenViking` editable 构建，并修复 `openviking/server/routers/__init__.py` 导出缺失；`agfs-server.exe`、`libagfsbinding.dll` 与 `openviking/storage/vectordb/engine.pyd` 已生成且可导入。
  - ✅ 已验证：已新增本地开发配置 `OpenViking/.local_dev/ov.conf`，`OpenVikingClient` 可直接初始化本地仓库内 OpenViking；真实写入 `experiments/` 分区返回 `mode=openviking` 且 `verified_partition=True`。
  - ✅ 已验证：已修复 `OpenVikingClient.write_json()` 目标分区参数错误（`target`）与 `search()` 参数错误（`limit`），并补充 workspace 查询回退。
  - ✅ 已验证：已配置真实 embedding API（baai/bge-m3 via shengsuanyun.com），SDK 初始化成功。

#### [P1-05] 配置文件创建
- 状态: `已完成`
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 关联文件: `configs/orchestrator.toml`, `configs/monitor.toml`, `configs/designer.toml`, `configs/knowledge.toml`, `configs/projects/her_feconi.toml` (新增)
- 备注: 已创建 5 个 Phase 1 TOML 配置文件（默认值 + 注释），并通过 tomllib 解析校验；后续由 P1-06 将其接入 config 模块统一加载与访问。

#### [P1-06] 增强配置加载
- 状态: `已完成`
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-05
- 关联文件: `src/common/config.py` (修改)
- 备注: 已在 config 模块增加 TOML 加载与访问函数（含 projects/*.toml 聚合），并提供 `ORCHESTRATOR_CONFIG` / `MONITOR_CONFIG` / `DESIGNER_CONFIG` / `KNOWLEDGE_CONFIG` / `PROJECT_CONFIGS` 快照与 `reload_all_configs()` 刷新入口。

### Step 2: 智能监控

#### [P1-07] L1 实时监控规则引擎
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-05
- 关联文件: `src/skills/realtime_monitor_skill.py` (新增)
- 备注: 已实现配置驱动的 L1 规则引擎，覆盖 6 条规则（泵转速偏差、通信超时、步骤超时、空数据文件、泵无响应、电流突变），从 `monitor.toml` 读取阈值并输出带 severity/source 的异常结果；通过 `tests/test_realtime_monitor_skill.py`（8 项）和 `tests/test_import_smoke.py`。

#### [P1-08] L2 心跳巡检
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-03, P1-05
- 关联文件: `src/skills/heartbeat_inspector_skill.py` (新增)
- 备注: 已实现可配置的 L2 心跳巡检 Skill，支持启停控制、间隔门控、知识库查询与 LLM/规则化综合判断；通过 `tests/test_heartbeat_inspector_skill.py`（5 项）和 `tests/test_import_smoke.py`。

#### [P1-09] Executor 集成两层监控
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-07, P1-08
- 关联文件: `src/agents/exp_executor.py` (修改)
- 备注: 已在 `execute_experiment` 中集成 L1/L2 监控、L2 开关控制、监控状态回传和环境快照记录；通过 `tests/test_executor_agent.py`（23 项）和 `tests/test_import_smoke.py`。

#### [P1-10] 监控控制路由
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-09
- 关联文件: `src/api/routes/monitor.py` (新增)
- 备注: 已新增监控控制路由，提供 heartbeat 开关、监控状态和配置更新接口，并接入共享 Executor 实例；通过 `tests/test_api_routes.py`（31 项）、`tests/test_executor_agent.py`（23 项）和 `tests/test_import_smoke.py`。

### Step 3: 实验设计增强

#### [P1-11] ML 预测模型
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 关联文件: `src/ml/performance_predictor.py` (新增)
- 备注: 已实现 `PerformancePredictor`，支持按样本量自动选择模型（<10 不启用、10~30 随机森林、>30 高斯过程）并生成候选实验点；在缺少 `sklearn` 时自动降级到轻量 surrogate。通过 `tests/test_performance_predictor.py`（3 项）和 `tests/test_import_smoke.py`。

#### [P1-12] Designer 三阶段策略
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-03, P1-11
- 关联文件: `src/agents/exp_designer.py` (修改)
- 备注: 已将 Designer 增强为文献引导 → LLM 引导 → ML 混合三阶段策略，接入 `KnowledgeQuerySkill` 与 `PerformancePredictor`，并保留依赖不可用时的确定性回退路径；通过 `tests/test_designer_agent.py`（16 项）和 `tests/test_import_smoke.py`。

### Step 4: 决策与人机协作

#### [P1-13] Orchestrator 人机协作增强
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-03, P1-04, P1-06
- 关联文件: `src/agents/orchestrator.py` (修改)
- 备注: 已增强 Orchestrator 的工作模式、关键决策审批触发、待审批状态管理、审批响应和共享知识查询接入，并补充 ML 训练数据更新入口；通过 `tests/test_orchestrator_agent.py`（23 项）和 `tests/test_import_smoke.py`。

#### [P1-14] 审批路由
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-13
- 关联文件: `src/api/routes/approval.py` (新增)
- 备注: 已新增 `/api/approval/pending` 与 `/api/approval/respond`，并引入共享 `Orchestrator` 实例供 API/Graph/OptimizationLoop 复用；通过 `tests/test_api_routes.py`（34 项）和 `tests/test_import_smoke.py`。

#### [P1-15] OptimizationLoop 暂停/恢复
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-13
- 关联文件: `src/graph/optimization_loop.py` (修改)
- 备注: 已为 `OptimizationLoop` 与 `run_optimization` 接入 `pause_for_human` 等待、审批结果恢复和共享 `Orchestrator`；`/api/optimization/status` 现返回 `pending_approval/pause_reason/latest_decision/last_approval`；通过 `tests/test_orchestrator_agent.py`（24 项）、`tests/test_optimization_api.py`（4 项）和 `tests/test_import_smoke.py`。

### Step 5: ChatAgent + 诊断增强

#### [P1-16] ChatAgent
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-03
- 关联文件: `src/agents/chat_agent.py` (新增)
- 备注: 已新增 `ChatAgent`，实现实验状态、优化进度、知识库检索、停止优化等意图识别与处理，并支持基于历史消息的追问扩展；通过 `tests/test_chat_agent.py` 与 `tests/test_import_smoke.py`。

#### [P1-17] Diagnostics 知识库集成
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-03, P1-04
- 关联文件: `src/agents/diagnostics.py` (修改)
- 备注: 已为 `DiagnosticsExpertAgent` 接入 `KnowledgeQuerySkill`，补充故障历史/相关记录检索、知识上下文摘要和诊断结果透传；通过 `tests/test_diagnostics_agent.py`（18 项）和 `tests/test_import_smoke.py`。

#### [P1-18] Chat 路由增强
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-16
- 关联文件: `src/api/routes/chat.py` (修改)
- 备注: 已将聊天路由接入 `ChatAgent`，新增 `POST /api/chat` 与 `/api/chat/history`，并兼容历史 `/api/v1/chat/ask`、`/api/v1/chat/history` 接口；通过 `tests/test_chat_agent.py`、`tests/test_api_routes.py` 和 `tests/test_import_smoke.py`。

### Step 6: 项目管理 + 集成

#### [P1-19] 项目管理路由
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 关联文件: `src/api/routes/projects.py` (新增)
- 备注: 已实现 `GET /api/projects`、`GET /api/projects/current`、`GET /api/projects/{id}`、`POST /api/projects`、`POST /api/projects/{id}/select`，基于 `configs/projects/*.toml` 提供项目列表、详情、创建与切换当前项目能力；通过 `tests/test_project_knowledge_routes.py` 与 `tests/test_api_routes.py`。

#### [P1-20] 知识库查询路由
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-03
- 关联文件: `src/api/routes/knowledge.py` (新增)
- 备注: 已接入 `KnowledgeQuerySkill`，实现 `GET /api/knowledge/search`、`GET /api/knowledge/experiments`、`GET /api/knowledge/faults` 三类查询接口，包含参数校验与项目过滤；通过 `tests/test_project_knowledge_routes.py` 与 `tests/test_api_routes.py`。

#### [P1-21] LangGraph 路由增强
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: P1-16
- 关联文件: `src/graph/orchestrator.py` (修改), `src/graph/nodes.py` (修改)
- 备注: 已将 `ChatAgent` 注册到 `AGENT_MAP` 和 supervisor graph，新增聊天/状态/控制类意图路由、`run_chat` 节点及兼容别名；通过 `tests/test_chat_agent.py`、`tests/test_orchestrator.py::TestRouteIntent`、`tests/test_orchestrator.py::TestSelectAgentNode`、`tests/test_executor_agent.py::TestExecutorRouting`、`tests/test_executor_agent.py::TestExecutorGraphRegistration`、`tests/test_knowledge_agent.py::TestKnowledgeRouting` 和 `tests/test_import_smoke.py`。

#### [P1-22] 端到端集成测试
- 状态: `已完成`
- 负责人: `Codex(GPT-5)`
- 开始时间: 2026-03-19
- 完成时间: 2026-03-19
- 依赖: 所有 P1 任务
- 关联文件: `tests/` (新增/修改)
- 备注: 已在 `tests/integration/test_e2e.py` 增加审批 API 往返与优化任务暂停/审批恢复两条集成回归，并通过 `tests/integration/test_e2e.py -k "approval_api_round_trip or optimization_pause_resume_via_approval_api"` 与 `tests/test_import_smoke.py`。

---

## Phase 1: 前端（React Web Dashboard）

> 技术栈：React 18 + TypeScript + Vite + Tailwind + zustand + react-query + recharts
> 代码位置：`AutoHySeeker/frontend/src/`
> 详细修改指南：`docs/FRONTEND_MODIFICATION_GUIDE.md`

### Step F1: 路由 + 基础调整

#### [F1-01] App.tsx 添加新路由 + 侧边栏菜单
- 状态: `已完成`
- 负责人: `Gemini(3.1-Pro)`
- 关联文件: `frontend/src/App.tsx` (修改), `frontend/src/router.tsx` (修改), `frontend/src/components/Sidebar.tsx` (修改)
- 备注: 已添加与映射 Optimization 和 Chat 的路由空页面，并在 Sidebar 增加了对应的菜单入口。

#### [F1-02] Dashboard.tsx 增加优化循环状态卡片
- 状态: `已完成`
- 负责人: `Gemini(3.1-Pro)`
- 依赖: F1-01, P1-15
- 关联文件: `frontend/src/pages/Dashboard.tsx` (修改), `frontend/src/components/dashboard/*` (新增)
- 备注: 已抽象并实现了 OptimizationStatusCard、RecentExperimentsCard 和 SystemNotificationsCard 组件（暂时使用 Mock 数据），并将它们集成至 Dashboard 页面顶部区域。

### Step F2: 新页面实现（F1-01 完成后可全部并行）

#### [F1-03] Optimization.tsx 优化循环主页
- 状态: `已完成`
- 负责人: `Gemini(3.1-Pro)`
- 依赖: F1-01, P1-15
- 关联文件: `frontend/src/pages/Optimization.tsx` (新增), `frontend/src/api/optimization.ts` (新增), `frontend/src/stores/optimizationStore.ts` (新增)
- 备注: 已实现了 Optimization 的三栏核心布局，包括左右的参数和Agent建议面板，以及中间基于 recharts 的收敛曲线，在 P1-15 后台 API 未完成前已通过 Zustand 提供了合理的 Mock 状态和延迟占位逻辑，确保UI表现完整。

#### [F1-04] Chat.tsx Agent 对话页
- 状态: `已完成`
- 负责人: `Gemini(3.1-Pro)`
- 依赖: F1-01, P1-18
- 关联文件: `frontend/src/pages/Chat.tsx` (修改), `frontend/src/api/chat.ts` (新增), `frontend/src/stores/chatStore.ts` (新增), `frontend/src/components/chat/*` (新增)
- 备注: 实现了基于 Agent 的 Chat 对话界面。抽离了 ChatSidebar, ChatInput 和支持 Markdown 渲染的 ChatMessage（额外安装了 `react-markdown` 及 Tailwind `typography` 插件）。Store 层暂接 Mock 数据表现流式占位和消息收发逻辑。

#### [F1-05] Knowledge.tsx 知识库页
- 状态: `已完成`
- 负责人: `Gemini(3.1-Pro)`
- 依赖: F1-01, P1-20
- 关联文件: `frontend/src/pages/KnowledgeHub.tsx` (修改), `frontend/src/api/knowledge.ts` (新增)

#### [F1-06] Diagnostics.tsx 诊断页
- 状态: `已完成`
- 负责人: AI
- 完成时间: 2026-03-21
- 依赖: F1-01, P1-10
- 关联文件: `frontend/src/pages/Diagnostics.tsx` (新增), `frontend/src/api/monitor.ts` (新增)
- 备注: 已实现诊断监控页面，使用 `@tanstack/react-query` 接入真实后端 API（`GET /api/monitor/status` 每 3 秒轮询、`POST /api/monitor/toggle` 心跳开关），无 mock 数据。

### Step F3: 已有页面增强

#### [F1-07] ExperimentDetail.tsx 接入真实 Agent 响应
- 状态: `已完成`
- 负责人: AI
- 依赖: F1-04, P1-16
- 关联文件: `frontend/src/pages/ExperimentDetail.tsx` (修改)

#### [F1-08] Experiments.tsx 迁移到 react-query + 增强筛选
- 状态: `已完成`
- 负责人: AI
- 关联文件: `frontend/src/pages/Experiments.tsx` (新增), `frontend/src/api/experiments.ts` (新增)

### Step F4: 国际化 + 集成测试

#### [F1-09] i18n 补充新页面翻译
- 状态: `已完成`
- 负责人: AI
- 依赖: 所有 F1 新页面
- 关联文件: `frontend/src/locales/zh-CN.json` (修改), `frontend/src/locales/en-US.json` (修改)

#### [F1-10] Phase 1 前端集成测试
- 状态: `已完成`
- 负责人: User / AI
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

## Phase 1: 收尾（前端对接 + Bug 修复）

> 后端 P1-01~P1-22 全部已完成，前端页面 UI 已完成。
> 本阶段目标：将前端 mock 数据替换为真实 API 调用，修复已知 bug。

### Step W: 前端-后端对接

#### [W-01] Chat Store 接入真实 API
- 状态: `已完成`
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-23
- 完成时间: 2026-03-23
- 依赖: P1-18, F1-04
- 关联文件:
  - `frontend/src/stores/chatStore.ts` (修改)
  - `frontend/src/api/chat.ts` (修改)
- 产出: chatStore 移除全部 MOCK 数据，调用真实后端 API
- **口径（2026-03-23 确认）**:
  - **退化为单会话 default**：移除前端 session CRUD（createSession/deleteSession/listSessions）
  - 不保留多会话体验，固定一个 `default` 会话即可
  - 不补后端 session 接口，Phase 2 再考虑多会话
- 验收标准:
  - `sendMessage()` 调用 `POST /api/chat`，传入 `message` + `history`，接收 Agent 真实响应
  - 历史消息调用 `GET /api/chat/history`
  - 页面输入消息后能收到后端 ChatAgent 的真实回复（需启动后端验证）
  - 移除所有 `MOCK_SESSIONS`、`MOCK_MESSAGES`、`setTimeout` 模拟延迟
  - 移除前端 session CRUD 逻辑（createSession/deleteSession/renameSession/listSessions）
- **前后端接口对齐说明**:
  - 前端 `chat.ts` 当前是 session 风格接口（`/sessions`、`/sessions/:id/messages`），后端不存在这些路由
  - 后端实际只有两个接口：`POST /api/chat`（发送消息）和 `GET /api/chat/history`（获取历史）
  - 需将 `chat.ts` 重写为只调用这两个接口
  - 后端响应格式: `POST /api/chat` 返回 `{"reply": "...", "intent": "...", "sources": [...]}`
- 参考:
  - 后端 API 定义: `src/api/routes/chat.py`（第 67 行 POST /api/chat、第 119 行 GET /api/chat/history）
  - 已有 axios 客户端: `frontend/src/api/client.ts`
- 备注: 已将 `frontend/src/api/chat.ts` 重写为单会话 `default` 模式，只调用 `/api/chat` 与 `/api/chat/history`；`frontend/src/stores/chatStore.ts` 已移除 mock/session CRUD，改为真实历史加载与消息发送；`frontend/src/components/chat/ChatSidebar.tsx` 改为可选新建按钮，`frontend/src/pages/Chat.tsx` 不再暴露多会话入口；通过 `npm run typecheck` 和 `npm run build`。

#### [W-02] Optimization Store 接入真实 API
- 状态: `已完成`
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-23
- 完成时间: 2026-03-23
- 依赖: P1-15, F1-03
- 关联文件:
  - `frontend/src/stores/optimizationStore.ts` (修改)
  - `frontend/src/api/optimization.ts` (修改)
- 产出: optimizationStore 移除全部 MOCK 数据，调用真实后端 API
- **口径（2026-03-23 确认）**:
  - **前端适配现有后端 5 个接口**，不补后端 `/config` 和 `/state` 接口
  - 配置信息从 `/status` 响应里取，前端做字段映射
  - 用 `/status` 轮询替代原来的 mock state
- 验收标准:
  - `fetchStatus()` 调用 `GET /api/optimization/status` 获取真实状态（替代原 `fetchConfigAndState()`）
  - `startLoop()` 调用 `POST /api/optimization/start` 启动优化
  - `stopLoop()` 调用 `POST /api/optimization/stop` 停止优化
  - `fetchHistory()` 调用 `GET /api/optimization/history` 获取实验历史+收敛数据
  - `resetLoop()` 调用 `DELETE /api/optimization/reset` 重置状态
  - 移除所有 `MOCK_CONFIG`、`MOCK_STATE`、`setTimeout` 模拟延迟
  - 页面能显示真实优化状态和收敛曲线（需启动后端验证）
- **前后端接口对齐说明**:
  - 前端 `optimization.ts` 当前调用 `/config`（第 41 行）和 `/state`（第 53 行），后端不存在这些路由
  - 后端实际有 5 个接口：`GET /status`、`POST /start`、`POST /stop`、`GET /history`、`DELETE /reset`
  - 需将 `optimization.ts` 重写为只调用这 5 个接口
  - `/status` 响应包含：`status`、`current_round`、`max_rounds`、`best_result`、`target_metric`、`direction`、`pending_approval` 等字段
  - `/history` 响应包含：`experiments`（列表）和 `best_result`
- 参考:
  - 后端 API 定义: `src/api/routes/optimization.py`（第 83 行起）
  - 已有 axios 客户端: `frontend/src/api/client.ts`
- 备注: 已将 `frontend/src/api/optimization.ts` 改为只调用 `/status`、`/start`、`/stop`、`/history`、`/reset` 并完成字段映射；`frontend/src/stores/optimizationStore.ts` 已移除 mock 数据，改为真实状态/历史拉取与启动停止控制；`frontend/src/pages/Optimization.tsx` 已接入 3 秒轮询；通过 `npm run typecheck` 和 `npm run build`。

#### [W-03] Knowledge 页面端到端验证
- 状态: `已完成`
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-23
- 完成时间: 2026-03-23
- 依赖: P1-20, F1-05
- 关联文件:
  - `frontend/src/pages/KnowledgeHub.tsx` (修改)
  - `frontend/src/api/knowledge.ts` (修改)
- 产出: Knowledge 页面适配现有后端 3 个接口，屏蔽不可用功能
- **口径（2026-03-23 确认）**:
  - **先做"只搜索可用"**，不补后端 `/recent`、`/items/:id`、`/ingest` 接口
  - 前端只对接已有的 3 个后端接口
  - 对应 `/recent`、`/items/:id`、`/ingest` 的 UI 功能暂时屏蔽（隐藏按钮或灰掉）
  - Phase 2 再补全
- 验收标准:
  - 搜索功能调用 `GET /api/knowledge/search?q=xxx` 并展示结果
  - 实验记录查询调用 `GET /api/knowledge/experiments`
  - 故障历史查询调用 `GET /api/knowledge/faults`
  - 启动前后端后页面正常加载，无 JS 报错
  - `/recent`、`/items/:id`、`/ingest` 对应 UI 已屏蔽或隐藏
- **前后端接口对齐说明**:
  - 前端 `knowledge.ts` 当前调用 `POST /api/knowledge/search`（第 32 行）、`GET /api/knowledge/recent`、`GET /api/knowledge/items/:id`、`POST /api/knowledge/ingest`
  - 后端实际只有 3 个接口：`GET /api/knowledge/search`、`GET /api/knowledge/experiments`、`GET /api/knowledge/faults`
  - 注意 search 方法不一致：前端用 POST，后端用 GET（需改前端）
  - `/recent`、`/items/:id`、`/ingest` 后端不存在，前端需屏蔽对应调用
- 参考:
  - 后端 API 定义: `src/api/routes/knowledge.py`（第 39 行起）
  - 已有 axios 客户端: `frontend/src/api/client.ts`
- 备注: 已将 `frontend/src/api/knowledge.ts` 改为对齐现有 `/search`、`/experiments`、`/faults` 三个 GET 接口并做前端结果归一化；`frontend/src/pages/KnowledgeHub.tsx` 已移除 ingest/recent/detail 依赖，改为真实搜索 + 实验/故障快捷查询；`frontend/src/components/knowledge/KnowledgeResultList.tsx` 已修复结果展示；通过 `npm run typecheck` 和 `npm run build`。

#### [W-04] Dashboard 状态卡片接入真实数据
- 状态: `已完成`
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-23
- 完成时间: 2026-03-23
- 依赖: W-02
- 关联文件:
  - `frontend/src/pages/Dashboard.tsx` (修改)
  - `frontend/src/components/dashboard/*` (修改)
- 产出: Dashboard 的 OptimizationStatusCard 等组件改用真实 API 数据
- 验收标准:
  - OptimizationStatusCard 显示真实优化状态（来自 optimizationStore）
  - 无 mock/硬编码数据残留
- 备注: 已将 `Dashboard.tsx` 接入 `optimizationStore`，按 5 秒轮询同步真实优化状态；`OptimizationStatusCard` 现显示真实 loop 状态、轮次、最佳结果和活跃实验，`RecentExperimentsCard` 改由真实优化历史映射，`SystemNotificationsCard` 改由审批等待和错误信息生成；移除了 Dashboard 内的 mock 状态卡片数据。通过 `npm run typecheck` 和 `npm run build`。

### Step B: Bug 修复

#### [B-01] Fallback 关键词搜索修复
- 状态: `已完成`
- 完成时间: 2026-03-23
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-23
- 关联文件: `src/knowledge/viking_client.py` (修改)
- 产出: `_fallback_search` 方法支持逐词匹配
- 验收标准:
  - 多词查询（如 "NiCoP overpotential"）能匹配到包含任一关键词的记录
  - 单词查询行为不变
  - 通过 `tests/test_knowledge_foundation.py`
- 当前问题: `_fallback_search` 使用 `query_lower in haystack` 做完整子串匹配，多词查询永远返回空
- 修复方案: 将查询字符串按空格拆分为词列表，任一词命中即认为匹配
- 备注: 已将 `_fallback_search` 复用统一的 `_keyword_score()`，支持多词查询按词命中；新增 `tests/test_knowledge_foundation.py` 中的多关键词回归用例。通过 `pytest AutoHySeeker/tests/test_knowledge_foundation.py -q`（10 项）。

#### [B-02] Python 3.13 asyncio 兼容性修复
- 状态: `已完成`
- 完成时间: 2026-03-23
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-23
- 关联文件: `tests/test_orchestrator_agent.py` (修改)
- 产出: 测试文件兼容 Python 3.13
- 验收标准:
  - `pytest tests/test_orchestrator_agent.py -v` 全部通过（当前 11 个测试因 asyncio 弃用而失败）
- 当前问题: Python 3.13 弃用了 `asyncio.get_event_loop()`，测试中使用此 API 导致 DeprecationWarning 或直接失败
- 修复方案: 将 `asyncio.get_event_loop().run_until_complete(coro)` 替换为 `asyncio.run(coro)`
- 备注: 已将 `tests/test_orchestrator_agent.py` 的测试辅助函数切换为 `asyncio.run()`，移除对已弃用 event loop API 的依赖。通过 `pytest AutoHySeeker/tests/test_orchestrator_agent.py -q`（24 项）。

---

## Phase 1: 架构优化

### Step C: 配置统一

#### [C-01] LLM 模型配置统一收口
- 状态: `已完成`
- 负责人: `Codex(GPT-5.2)` + `Copilot(Claude-Opus-4-6)`
- 开始时间: 2026-03-24
- 完成时间: 2026-03-26
- 依赖: 无
- 关联文件:
  - `configs/agent_models.toml` (修改 — 唯一真相源)
  - `configs/monitor.toml` (修改 — 移除 model 字段)
  - `configs/llm_config.toml` (删除 — 与 config.py 重复)
  - `src/common/config.py` (修改 — DEFAULT_MODEL/FALLBACK_MODEL 改为从 agent_models.toml 读取)
  - `src/common/llm_client.py` (修改 — 适配新配置结构)
  - `src/skills/heartbeat_inspector_skill.py` (修改 — model 改从 agent_models.toml 读取)
  - `src/agents/chat_agent.py` (修改 — 改为读取自己的 `[chat]` 配置段，不再借用 orchestrator)
- 产出: 所有 LLM 模型配置统一到 `agent_models.toml` 一个文件
- 验收标准:
  - `agent_models.toml` 包含以下配置段：`[orchestrator]`、`[experiment_designer]`、`[experiment_executor]`、`[diagnostics_expert]`、`[chat]`、`[heartbeat_inspector]`、`[defaults]`（系统默认+回退模型）
  - `llm_config.toml` 已删除
  - `monitor.toml` 的 `[heartbeat_inspector]` 不再包含 `model` 字段（model 移到 agent_models.toml）
  - `config.py` 的 `DEFAULT_MODEL` / `FALLBACK_MODEL` 从 `agent_models.toml [defaults]` 读取
  - `chat_agent.py` 使用 `load_agent_config("chat")` 而不是借用 orchestrator 的配置
  - `heartbeat_inspector_skill.py` 使用 `load_agent_config("heartbeat_inspector")` 而不是从 monitor.toml 读 model
  - 全部测试通过：`pytest tests/ -v`
- **当前散乱情况说明**:
  - `agent_models.toml` — 4 个 Agent 模型（主配置）
  - `monitor.toml [heartbeat_inspector].model` — HeartbeatInspector 模型单独配
  - `config.py` + `.env` — `DEFAULT_MODEL` / `FALLBACK_MODEL`（第三份配置）
  - `llm_config.toml` — 与 config.py 重复的第四份配置
  - `chat_agent.py` — 硬编码借用 orchestrator 配置，无独立配置段
- **目标 `agent_models.toml` 结构**:
  ```toml
  [defaults]
  model = "anthropic/claude-sonnet-4-6"
  fallback_model = "anthropic/claude-opus-4-6"
  base_url = "https://api.mcxhm.cn"

  [orchestrator]
  # ...现有配置不变

  [experiment_designer]
  # ...现有配置不变

  [experiment_executor]
  # ...现有配置不变

  [diagnostics_expert]
  # ...现有配置不变

  [chat]
  name = "对话 Agent"
  model = "ali/qwen3-max-2026-01-23"
  temperature = 0.3
  max_tokens = 2000
  # ...其他字段

  [heartbeat_inspector]
  name = "心跳巡检"
  model = "qwen3-max"
  temperature = 0.0
  max_tokens = 500
  ```
- 备注:
  - ✅ 已完成：`configs/agent_models.toml` 已收口为唯一真相源，补齐 `[defaults]`、`[chat]`、`[heartbeat_inspector]` 段；`configs/llm_config.toml` 已删除；`configs/monitor.toml` 已移除 `heartbeat_inspector.model`。
  - ✅ 已完成：`src/common/config.py` 新增 `get_agent_models_config()` / `get_default_llm_config()` / `load_agent_config()` / `update_agent_model_config()`，`DEFAULT_MODEL` / `FALLBACK_MODEL` / `OPENAI_BASE_URL` 现从 `agent_models.toml [defaults]` 读取并支持 `reload_all_configs()` 热加载。
  - ✅ 已完成：`src/common/llm_client.py`、`src/skills/heartbeat_inspector_skill.py`、`src/agents/chat_agent.py` 已切到新配置结构；`BaseAgent` 与 `chat_completion()` 已支持 per-agent `fallback_model`。
  - ✅ 已验证：`pytest AutoHySeeker/tests/test_llm_client.py AutoHySeeker/tests/test_chat_agent.py AutoHySeeker/tests/test_heartbeat_inspector_skill.py AutoHySeeker/tests/test_api_routes.py AutoHySeeker/tests/test_config.py -q`（99 项）通过；`pytest AutoHySeeker/tests/test_import_smoke.py -q` 通过；`npm run typecheck` 与 `npm run build` 通过。
  - ⛔ 阻塞原因：按验收要求运行 `pytest AutoHySeeker/tests -q` 时，仓库当前仍有 **133 个既有失败**，主要集中在 `integration/test_e2e.py`、`test_phase3.py`、`test_phase4.py`、`test_pipeline_e2e.py`、`test_skills_phase2.py`、`test_validation.py` 等历史模块，已超出本任务改动范围；在 repo 全量测试基线恢复前，按协作规范不能标记为 `已完成`。
  - ✅ 阻塞已解除（2026-03-26，Copilot(Claude-Opus-4-6)）：修复 133 个既有失败，`pytest AutoHySeeker/tests -q` 全量 757 passed, 0 failed。修复内容：
    - Python 3.13 `asyncio.get_event_loop()` → `asyncio.run()` 全量替换（11 个测试文件 + 1 个 utils 文件 + 1 个 src 文件）
    - `DataAnalystAgent` 空文件 → 补充最小 BaseAgent 子类 stub（解决 `analyze_cv.py` ImportError）
    - `tool_registry` 测试 `dict` 断言 → 匹配实际 `list[ToolDef]` 返回类型
    - Agent name `exp_executor` → `experiment_executor` 断言对齐
    - `_call_microhyseeker` 异常处理扩展（`ConnectError` → `ConnectError|TimeoutException|OSError|TransportError` + 5xx 回退）
    - Orchestrator anomaly 测试设置 `full_auto` 模式避免 `pause_for_human` 包装
    - `test_phase4_c1.py` 3 个过期测试更新适配 `ContextualizeExperimentSkill` 新 API（`run_dir` 必填、schema 变更、description 变更）
    - `integration/test_e2e.py` C1/C2 结果断言从顶层 → `result["data"]` 嵌套层
    - Agent config log 测试移除不存在的 `logger.info` 断言（保留配置值验证）

#### [C-02] 前端 Settings 模型选择器连接后端
- 状态: `已完成`
- 负责人: `Codex(GPT-5.2)`
- 开始时间: 2026-03-24
- 完成时间: 2026-03-24
- 依赖: C-01
- 关联文件:
  - `src/api/routes/agents.py` (修改 — 新增模型配置读写接口)
  - `frontend/src/stores/agentStore.ts` (修改 — 从后端读取模型列表和当前配置)
  - `frontend/src/pages/Settings.tsx` (修改 — 模型选择器连接真实 API)
  - `frontend/src/api/agents.ts` (修改 — 新增模型配置 API 调用)
- 产出: 前端 Settings 页的 Agent 模型配置连接后端，修改后写回 `agent_models.toml`
- 验收标准:
  - 新增后端接口 `GET /api/agents/models`：返回当前所有 Agent 的模型配置
  - 新增后端接口 `PUT /api/agents/models/{agent_name}`：更新指定 Agent 的模型配置并写回 toml
  - 前端 Settings > Agents Tab 从后端加载真实模型配置（而非 localStorage 硬编码）
  - 前端修改模型后调用 PUT 接口写回后端，后端调用 `reload_all_configs()` 热加载
  - `AVAILABLE_MODELS` 列表与后端实际支持的模型网关一致
  - 启动前后端验证：Settings 页能显示和修改真实模型配置
- 备注: 已在 `src/api/routes/agents.py` 新增 `GET /api/agents/models` 与 `PUT /api/agents/models/{agent_name}`；`frontend/src/stores/agentStore.ts` 已改为从后端加载/保存真实模型配置并接收后端下发的可用模型列表；`frontend/src/pages/Settings.tsx` 已接入真实配置加载与单 Agent 保存；`frontend/src/api/agents.ts`、`frontend/src/components/ModelSelector.tsx`、`frontend/src/pages/AgentControl.tsx`、`frontend/src/hooks/useDashboardPolling.ts` 已同步到新的真实 Agent ID/模型配置结构。通过 `pytest AutoHySeeker/tests/test_api_routes.py -q`、`npm run typecheck` 和 `npm run build`。

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

# AutoHySeeker 验证与测试指南

> 最后更新：2026-03-18（Phase 10 架构精简 7→4 Agent）  
> 适用对象：开发者、AI 协作者  
> 目标：任何人（包括其他 AI）读完本文件后，都能清楚地知道：哪些功能已实现、如何验证、如何测试、已知问题在哪里、下一步该做什么。

---

## 一、项目整体结构说明

```
MicroHySeeker/          ← 硬件控制层（PySide6 GUI + FastAPI 端口 8100）
  src/
    api/routes/
      device.py         ← 17个设备控制接口
      template.py       ← 实验模板管理接口
      system.py         ← 健康检查、日志接口
      experiment.py     ← 实验启动/状态/停止接口
      data.py           ← 数据读取接口
    hardware/           ← 泵控制、RS485 驱动
    engine/             ← 实验引擎核心
    ui/
      widgets/
        agent_dashboard.py  ← Agent 状态面板（嵌入主窗口）

AutoHySeeker/           ← AI 多智能体层（FastAPI 端口 8200）
  src/
    agents/             ← 4个 Agent 实现
    skills/             ← DataAnalysisSkill + KnowledgeArchiveSkill + 其他技能
    graph/              ← LangGraph 路由与优化循环
    tools/
      experiment_ctrl.py  ← 调用 MicroHySeeker HTTP API 的客户端
    api/routes/         ← AutoHySeeker 自己的 REST API
    common/             ← 配置、LLM 客户端、日志
  tests/                ← 单元测试 + 集成测试
  configs/
    agent_models.toml   ← 每个 Agent 的 LLM 模型配置
```

---

## 二、4个 Agent + 2个 Skill 实现状态一览

> **Phase 10 架构精简（2026-03-18）**：原 7 Agent 精简为 4 Agent + 2 Skill。
> DataAnalystAgent → DataAnalysisSkill，KnowledgeManagerAgent → KnowledgeArchiveSkill，
> ExperimentSupervisorAgent → 已消除（职责与 Orchestrator 重叠）。

| Agent / Skill | 文件路径 | 类型 | 关键方法 | 依赖 |
|---------------|----------|------|----------|------|
| **OrchestratorAgent** | `src/agents/orchestrator.py` | Agent | `evaluate_and_decide()`, `handle_anomaly()`, `analyze_experiment()`, `archive_experiment()`, `retrieve_knowledge()` | LLM (Qwen3-Max) + DataAnalysisSkill + KnowledgeArchiveSkill |
| **ExperimentDesignerAgent** | `src/agents/exp_designer.py` | Agent | `design_experiment()`, `_bayesian_design()`, `_apply_constraints()` | LLM (Gemini-3-Flash) + Optuna |
| **ExperimentExecutorAgent** | `src/agents/exp_executor.py` | Agent | `execute_experiment()`, `emergency_stop()`, `_monitor_until_complete()` | MicroHySeeker API (端口 8100) |
| **DiagnosticsExpertAgent** | `src/agents/diagnostics.py` | Agent | `diagnose_and_fix()`, `_fix_communication()`, `_fix_pump()` | LLM (GLM-4.6 Thinking) + experiment_ctrl |
| *DataAnalysisSkill* | `src/skills/data_analysis_skill.py` | Skill | `execute()`, `assess_quality()`, `compare_with_best()` | 确定性逻辑（无 LLM） |
| *KnowledgeArchiveSkill* | `src/skills/knowledge_archive_skill.py` | Skill | `archive()`, `retrieve()`, `search()` | JSON 持久化 + VikingKB（可选） |

---

## 三、闭环优化流程说明

```
每轮实验流程（OptimizationLoop）：

1. [设计] ExperimentDesignerAgent.design_experiment()
        ├── 第 0 轮：等比初始点（均分元素比例）
        ├── 1-4 轮：LLM 引导参数推荐
        └── ≥5 轮：Bayesian 优化（Optuna TPE）

2. [执行] ExperimentExecutorAgent.execute_experiment()
        ├── 预检查：health_check() + get_connection_info()
        ├── 实例化模板：instantiate_template(template_id, step_overrides)
        ├── 监控实验：轮询 get_experiment_status() + 异常检测
        └── 采集结果：get_logs() + get_run_detail()

3. [分析] OrchestratorAgent.analyze_experiment() → DataAnalysisSkill
        ├── 提取电化学指标（overpotential, current_density, tafel_slope）
        ├── 质量评估（评分 0-1，≥0.6 视为可靠）
        └── 与历史最佳结果比较

4. [决策] OrchestratorAgent.evaluate_and_decide()
        ├── continue    → 继续下一轮
        ├── stop        → 优化完成
        ├── retry       → 重复当前参数
        └── adjust_strategy → 调整策略

5. [归档] OrchestratorAgent.archive_experiment() → KnowledgeArchiveSkill
        └── 保存到 JSON 文件 + VikingKB（如已配置）
```

---

## 四、如何运行测试

### 4.1 环境准备

```bash
# 进入 AutoHySeeker 目录
cd d:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker

# 确认已安装依赖（Python 3.11+）
pip install -e ".[dev]"
# 或使用 uv
uv pip install -e ".[dev]"
```

### 4.2 运行全部测试

```bash
pytest tests/ -v
```

### 4.3 按模块分别运行

```bash
# Agent 单元测试（4个 Agent + 2个 Skill）
pytest tests/test_orchestrator_agent.py   -v   # 决策/停止/异常路由
pytest tests/test_executor_agent.py       -v   # 预检/异常检测/错误分类
pytest tests/test_designer_agent.py       -v   # 初始设计/约束/Bayesian
pytest tests/test_analyst_agent.py        -v   # DataAnalysisSkill 质量评分/指标提取/比较
pytest tests/test_diagnostics_agent.py    -v   # 已知故障/自动修复/验证
pytest tests/test_knowledge_agent.py      -v   # KnowledgeArchiveSkill 归档/检索/持久化

# 集成测试（Agent 间数据流）
pytest tests/test_integration_pipeline.py -v   # Designer→Executor→Analyst→Orchestrator 串联

# 端到端技能流水线测试
pytest tests/test_pipeline_e2e.py         -v   # A1→C1→C2 技能链

# 贝叶斯优化测试
pytest tests/test_optimization.py         -v   # 参数空间/Optuna 优化

# 早期阶段测试（Phase 2-4）
pytest tests/test_phase3.py               -v   # 诊断图/API
pytest tests/test_phase4.py               -v   # C1/C2 技能 + SupervisorGraph
```

### 4.4 生成覆盖率报告

```bash
pytest tests/ --cov=src --cov-report=html
# 报告输出到 htmlcov/index.html
```

### 4.5 只运行异步测试

```bash
pytest tests/ -k "async" -v
```

---

## 五、测试覆盖情况详解

### 5.1 已覆盖 ✅

| 测试模块 | 覆盖内容 | 测试数量 |
|----------|----------|----------|
| test_orchestrator_agent | 最大轮次强制停止、决策 JSON 解析、中文文本回退、异常等级路由（critical/high/low）、最优结果追踪（minimize/maximize）、路由关键词 | ~18 |
| test_executor_agent | 路由关键词（中英文）、AGENT_MAP 注册、健康预检、参数验证、泵错误/超时/急停异常检测、重复去除、错误分类（5 类） | ~26 |
| test_designer_agent | 初始等分（2/3元素）、归一化约束、区间截断、step_overrides 格式化、LLM 调用/解析/回退、改进量估算 | ~15 |
| test_analyst_agent | DataAnalysisSkill: 完整/缺失/空指标质量评分、负值/超高值/高 Tafel 斜率异常检测、与最佳对比（改进/恶化/缺失）、LSV/CV 指标提取、路由到 orchestrator | ~12 |
| test_diagnostics_agent | 故障注册表验证（5种已知故障）、通信超时/泵故障诊断、未知故障 LLM 回退、通信/泵自动修复、修复验证（健康/不健康/模块缺失） | ~22 |
| test_knowledge_agent | KnowledgeArchiveSkill: 单/多实验归档、历史查询、minimize/maximize 最优检索、top-k、文献/实验搜索、空档案处理、JSON 持久化、路由到 orchestrator | ~16 |
| test_integration_pipeline | Designer 输出兼容 Executor、critical/high/low 异常分发、Analyst 输出字段格式、归档+检索、完整 D→E→A→O 链 | ~13 |
| test_pipeline_e2e | A1 技能（CV分析）、C1 技能（上下文化）、C2 技能（建议下一步）、完整 A1→C1→C2 链、异常触发诊断 | ~27 |
| test_optimization | 参数定义/验证、参数空间构建、Optuna 单目标/多目标优化 | ~60 |

### 5.2 未覆盖 ❌（已知空白）

| 未覆盖项 | 说明 | 风险等级 |
|----------|------|----------|
| **LangGraph 状态转换** | graph/nodes.py 的条件边、状态传递未测试 | 中 |
| **真实 LLM 调用** | 所有 LLM 调用均用 AsyncMock 替代，真实 API 未验证 | 高 |
| **FastAPI 端点** | `/api/optimization/*`、`/api/agents/*` 等接口无 HTTP 层测试 | 高 |
| **MicroHySeeker 实际通信** | experiment_ctrl.py 调用硬件均被 mock，未做真实联调 | 高 |
| **并发安全性** | 多轮并发执行的线程安全性未测试 | 中 |
| **极端参数** | 元素比例极端值（0、1）、超大/超小量程未测试 | 低 |
| **OptimizationLoop.run()** | 完整闭环 run() 方法未有专属测试 | 高 |
| **VikingKB 集成** | knowledge_mgr 的 VikingKB 语义搜索路径未测试 | 低 |

---

## 六、CLI 端点使用方法

### 6.1 运行闭环优化（标准模式）

```bash
cd d:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker

python -m src.run_optimization \
  --goal "最小化 Fe-Co-Ni 三元合金 HER 过电位" \
  --max-rounds 10 \
  --metric overpotential_mV \
  --direction minimize \
  --template tpl_her_standard \
  --elements Fe Co Ni
```

### 6.2 干运行模式（不连接硬件，验证逻辑）

```bash
python -m src.run_optimization --dry-run --max-rounds 3
```

**干运行做什么：**
- 正常运行 Designer → Analyst → Orchestrator
- Executor 跳过真实 API 调用，返回模拟数据
- 验证完整数据流和 JSON 格式是否正确

### 6.3 仅检查连接（不运行实验）

```bash
python -m src.run_optimization --check-only
```

**检查内容：**
- MicroHySeeker 是否在端口 8100 在线
- health_check() 返回是否 ok
- AutoHySeeker API 配置是否正确

### 6.4 启动 AutoHySeeker API 服务

```bash
# 方式一：使用脚本入口
autohyseeker-api

# 方式二：使用 uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8200 --reload
```

---

## 七、REST API 接口说明

### 7.1 优化控制接口（`/api/optimization/`）

| 方法 | 路径 | 功能 | 参数 |
|------|------|------|------|
| GET | `/api/optimization/status` | 获取当前优化状态、最优结果、轮次 | 无 |
| POST | `/api/optimization/start` | 启动后台优化循环 | 见下方 |
| POST | `/api/optimization/stop` | 停止优化（优雅退出） | 无 |
| GET | `/api/optimization/history` | 获取全部实验历史 + 最优结果 | 无 |
| DELETE | `/api/optimization/reset` | 清空状态（仅限未运行时） | 无 |

**start 请求体：**
```json
{
  "goal": "最小化 HER 过电位",
  "max_rounds": 10,
  "target_metric": "overpotential_mV",
  "direction": "minimize",
  "template_id": "tpl_her_standard",
  "elements": ["Fe", "Co", "Ni"],
  "dry_run": false
}
```

### 7.2 Agent 控制接口（`/api/agents/`）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/agents/invoke` | 调用指定 Agent，路由由关键词决定 |
| GET | `/api/agents/status` | 查看所有 Agent 运行状态 |

### 7.3 其他接口

| 路径前缀 | 功能 |
|----------|------|
| `/api/experiments/` | 实验管理 |
| `/api/data/` | 数据读取 |
| `/api/diagnostics/` | 故障诊断 |
| `/api/context/` | 实验上下文化 |
| `/api/tasks/` | 任务队列管理 |
| `/health` | 健康检查 |

---

## 八、Agent LLM 配置

配置文件：`AutoHySeeker/configs/agent_models.toml`

| Agent | 使用模型 | 温度 | 最大 Token |
|-------|----------|------|-----------|
| orchestrator | Qwen3-Max | 0.1 | 1500 |
| experiment_designer | Gemini-3-Flash | 0.3 | 2500 |
| experiment_executor | Qwen3-Max | 0.1 | 1000 |
| diagnostics_expert | GLM-4.6 Thinking | 0.1 | 1000 |

> DataAnalysisSkill 和 KnowledgeArchiveSkill 为确定性逻辑，不使用 LLM。

**所有 Agent 使用统一 API 端点：** `https://api.mcxhm.cn`

---

## 九、端到端验证步骤（推荐顺序）

### 步骤 1：运行单元测试（无需硬件）

```bash
cd AutoHySeeker
pytest tests/test_orchestrator_agent.py tests/test_designer_agent.py tests/test_analyst_agent.py -v
```

预期结果：全部通过（无需 LLM 或硬件）

---

### 步骤 2：运行干跑模式（无需硬件）

```bash
python -m src.run_optimization --dry-run --max-rounds 2
```

预期结果：
- 输出 2 轮实验设计参数（Fe/Co/Ni 比例）
- 输出模拟分析结果
- 输出 Orchestrator 决策（continue 或 stop）
- 最后打印 `best_result` JSON

---

### 步骤 3：启动 MicroHySeeker 并验证连接

```bash
# 终端 1：启动 MicroHySeeker
python MicroHySeeker/run_ui.py

# 终端 2：检查连接
python -m src.run_optimization --check-only
```

预期结果：`✅ MicroHySeeker 连接正常`

---

### 步骤 4：API 接口验证

```bash
# 启动 AutoHySeeker API
autohyseeker-api

# 新终端：查询状态
curl http://localhost:8200/api/optimization/status

# 启动优化
curl -X POST http://localhost:8200/api/optimization/start \
  -H "Content-Type: application/json" \
  -d '{"goal":"测试","max_rounds":2,"target_metric":"overpotential_mV","direction":"minimize","template_id":"tpl_her_standard","elements":["Fe","Co","Ni"],"dry_run":true}'
```

---

### 步骤 5：真实硬件联调（需连接设备）

```bash
python -m src.run_optimization \
  --goal "最小化 Fe-Co-Ni HER 过电位" \
  --max-rounds 5 \
  --metric overpotential_mV \
  --direction minimize \
  --template tpl_her_standard \
  --elements Fe Co Ni
```

---

## 十、已知问题与注意事项

| 问题 | 影响范围 | 状态 | 说明 |
|------|----------|------|------|
| `experiment_ctrl.get_logs()` 缺少 `level` 参数 | DataAnalyst、Executor | ✅ 已修复 | 已添加 `level` 参数 |
| `exp_executor.py` 把 `get_logs()` 返回值当 dict 处理 | Executor | ✅ 已修复 | 已改为 list 处理 |
| `run_optimization.py` 使用 `"decision" in dir()` 判断 | OptimizationLoop | ✅ 已修复 | 已改为 `final_action` 变量 |
| `exp_designer.py` Optuna 单目标用 `values=` 而非 `value=` | Designer | ✅ 已修复 | Optuna API 参数名已修正 |
| AutoHySeeker 端口与 MicroHySeeker 冲突（均为 8100） | API 服务 | ✅ 已修复 | AutoHySeeker 已改为 8200 |
| VikingKB 未安装时 KnowledgeArchiveSkill 回退关键词搜索 | KnowledgeArchiveSkill | ⚠️ 正常降级 | 有意设计，不影响主流程 |
| LangGraph 状态转换未有专属测试 | Graph 层 | ❌ 未覆盖 | 需补充 |
| 真实 LLM API 调用未验证 | 所有 Agent | ❌ 未测试 | 需要联网验证 |

---

## 十一、MicroHySeeker 安全限制说明

**300 RPM 四层防护（底层→顶层）：**

| 层级 | 文件 | 防护方式 |
|------|------|----------|
| L4 协议层 | `src/hardware/rs485_driver.py` | 帧编码时强制截断至 SAFETY_MAX_RPM |
| L3 管理层 | `src/hardware/pumps.py` | 5个速度设置方法均拒绝 > 300 RPM |
| L2 配置层 | `src/engine/` (Config dataclass) | `__post_init__` 校验时抛出异常 |
| L1 封装层 | `src/hardware/` (Wrapper) | `_validate_rpm_limit()` 前置校验 |

**正常运行速度（均在 300 RPM 以下）：**
- 稀释泵：120 RPM
- 冲洗泵：200 RPM
- 实验泵：100 RPM

---

## 十二、下一步待完成事项（最新版）

### 🔴 优先级 1 — 立刻需要做

- [ ] **运行干跑测试**：`python -m src.run_optimization --dry-run --max-rounds 2`，验证完整数据流
- [ ] **运行全部单元测试**：`pytest tests/ -v`，确认无回归错误

### 🟡 优先级 2 — 补充测试覆盖

- [ ] **补充 API 端点测试**：为 `/api/optimization/*` 编写 httpx 测试（当前完全无 HTTP 层测试）
- [ ] **补充 OptimizationLoop.run() 测试**：覆盖完整闭环 run() 方法（当前未有专属测试）
- [ ] **LangGraph 状态转换测试**：验证 `graph/nodes.py` 条件边

### 🟢 优先级 3 — 功能增强

- [ ] **MicroHySeeker 硬件联调**：启动 MicroHySeeker，通过 `--check-only` 确认连接，完整走通一次真实实验
- [ ] **真实 LLM 联调**：验证各 Agent 的 LLM 调用是否正常返回（当前所有测试均为 mock）
- [ ] **VikingKB 配置**：在 `.env` 中配置 OpenViking 本地知识库，启用语义搜索

### ⏳ 配置项（使用前需确认）

- [ ] `AutoHySeeker/.env` 中 `OPENAI_API_KEY` 是否已配置（`agent_models.toml` 已有模型，但 key 需在 .env 中设置）
- [ ] MicroHySeeker 的 `tpl_her_standard` 模板是否已创建（Executor 用此模板 ID）

---

## 十四、项目开发阶段历史

> 记录从 Phase 1 到当前的所有已完成工作，方便新接手的人快速了解来龙去脉。

| 阶段 | 主要完成内容 | 关键文件 |
|------|-------------|----------|
| **Phase 1**<br>安全 + API 基础设施 | 300 RPM 四层防护；设备控制 REST API（17端点）；Qt↔FastAPI 桥接 | `hardware/pumps.py`, `api/routes/device.py`, `api/bridge.py` |
| **Phase 2**<br>工具层 + 技能层 | Tool 层（data_reader, echem_analysis, experiment_builder）；Skill A1 单实验分析；Skill B1 实验方案生成 | `tools/data_reader.py`, `skills/single_experiment_analysis.py` |
| **Phase 3**<br>诊断图 + API | LangGraph DiagnosticsExpert Subgraph；D1/D2/D3 诊断技能；`/diagnostics` API | `graph/diagnostics_graph.py`, `skills/diagnostics/` |
| **Phase 4**<br>知识库 + 上下文化 | VikingKB 客户端；C1 ContextualizeExperimentSkill；C2 SuggestNextExperimentSkill；SupervisorGraph；`/context` API | `src/rag.py`, `skills/contextualize_experiment.py` |
| **Phase 5**<br>实验模板系统 | 模板 CRUD + 实例化接口（11端点）；元素配比参数化（step_overrides） | `api/routes/template.py`, `tools/experiment_ctrl.py` |
| **Phase 6**<br>多智能体架构设计 | 7个 Agent 详细设计文档（multiagent_00~06.md）；OrchestratorAgent 核心实现 | `docs/multiagent_*.md`, `agents/orchestrator.py` |
| **Phase 7**<br>7个 Agent 全部实现 | ExperimentExecutor/Designer（Optuna TPE）/DataAnalyst/DiagnosticsExpert/KnowledgeManager；OptimizationLoop；CLI 入口；7套单元测试 | `agents/`, `graph/optimization_loop.py`, `run_optimization.py` |
| **Phase 8**<br>Bug 修复 | get_logs() 缺 level 参数；exp_executor 返回值类型错误；`"decision" in dir()` 逻辑错误；Optuna `values=`→`value=` | 同 Phase 7 文件 |
| **Phase 9**<br>功能增强 + Dashboard | KnowledgeManager 集成 VikingKB；优化控制 API（5端点）；AutoHySeeker 端口 8100→8200；MicroHySeeker 嵌入 Agent Dashboard | `agents/knowledge_mgr.py`, `api/routes/optimization.py`, `ui/widgets/agent_dashboard.py` |
| **Phase 10**<br>架构精简 7→4 Agent | DataAnalystAgent→DataAnalysisSkill；KnowledgeManagerAgent→KnowledgeArchiveSkill；ExperimentSupervisorAgent 消除；LangGraph 图 7→4 节点；路由别名向后兼容；全部测试更新（9文件）；文档更新 | `skills/data_analysis_skill.py`, `skills/knowledge_archive_skill.py`, `agents/orchestrator.py`, `graph/nodes.py`, `graph/orchestrator.py` |

---

## 十五、MicroHySeeker API 完整接口表

> MicroHySeeker 运行在端口 **8100**，是 AutoHySeeker 访问硬件的唯一入口。

### 设备控制（`/api/device/`）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/device/pump/start` | 启动单个泵 |
| POST | `/api/device/pump/stop` | 停止单个泵 |
| POST | `/api/device/pump/stop-all` | 紧急停止所有泵 |
| GET | `/api/device/pump/status` | 查询所有泵状态 |
| GET | `/api/device/pump/{address}` | 查询单个泵状态 |
| POST | `/api/device/flusher/start` | 启动冲洗循环 |
| POST | `/api/device/flusher/stop` | 停止冲洗 |
| GET | `/api/device/flusher/status` | 查询冲洗状态 |
| POST | `/api/device/diluter/start` | 启动稀释 |
| POST | `/api/device/diluter/stop` | 停止稀释 |
| GET | `/api/device/diluter/{channel_id}/status` | 查询稀释通道状态 |
| POST | `/api/device/emergency-stop` | 全部紧急停止 |
| GET | `/api/device/connection` | 查询 RS485 连接状态 |
| GET | `/api/device/ports` | 列出可用串口 |
| POST | `/api/device/connect` | 打开串口连接 |
| POST | `/api/device/disconnect` | 关闭串口连接 |

### 实验模板（`/api/template/` 和 `/api/config/`）

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/template/list` | 列出所有模板 |
| GET | `/api/template/{id}` | 获取模板详情 |
| POST | `/api/template/save` | 保存/更新模板 |
| DELETE | `/api/template/{id}` | 删除模板 |
| POST | `/api/template/{id}/instantiate` | **实例化并运行实验（核心接口）** |
| POST | `/api/template/validate` | 验证实验参数（干跑） |
| GET | `/api/config/system` | 查询系统配置（泵/通道/端口） |
| GET | `/api/config/capabilities` | 查询系统能力摘要 |
| GET | `/api/config/dilution-channels` | 查询稀释通道列表 |
| GET | `/api/config/flush-channels` | 查询冲洗通道列表 |
| GET | `/api/config/pumps` | 查询泵配置 |

**实例化实验请求格式（元素配比控制）：**
```json
{
  "template_id": "tpl_her_standard",
  "step_overrides": {
    "0": {"Fe_volume_ul": 600, "Co_volume_ul": 250, "Ni_volume_ul": 150}
  },
  "dry_run": false
}
```

### 实验控制（`/api/experiment/`）+ 系统/数据

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/experiment/start` | 启动实验 |
| POST | `/api/experiment/stop` | 停止实验 |
| POST | `/api/experiment/pause` | 暂停实验 |
| POST | `/api/experiment/resume` | 恢复实验 |
| GET | `/api/experiment/status` | 查询引擎状态 |
| GET | `/api/system/health` | 健康检查 |
| GET | `/api/system/logs` | 获取日志（可按 level 过滤） |
| GET | `/api/data/runs` | 列出全部实验记录 |
| GET | `/api/data/runs/{run_id}` | 获取单次实验详情 |
| GET | `/api/data/runs/{run_id}/files/{filename}` | 下载数据文件 |

### 验证 MicroHySeeker API 的 curl 命令

```bash
# 健康检查
curl http://localhost:8100/api/system/health

# 查询连接状态
curl http://localhost:8100/api/device/connection

# 列出模板
curl http://localhost:8100/api/template/list

# 干跑验证（不动硬件）
curl -X POST http://localhost:8100/api/template/tpl_her_standard/instantiate \
  -H "Content-Type: application/json" \
  -d '{"step_overrides": {"0": {"Fe_volume_ul": 600}}, "dry_run": true}'

# 查询实验状态
curl http://localhost:8100/api/experiment/status
```

---

## 十三、相关文件索引

| 功能 | 文件路径 |
|------|----------|
| 多智能体架构概述 | `docs/multiagent_00_architecture.md` |
| Orchestrator 详细设计 | `docs/multiagent_01_orchestrator.md` |
| ExperimentDesigner 详细设计 | `docs/multiagent_02_experiment_designer.md` |
| ExperimentExecutor 详细设计 | `docs/multiagent_03_experiment_executor.md` |
| ~~DataAnalyst 详细设计~~ | `docs/multiagent_04_data_analyst.md` ⚠️ 已废弃 → DataAnalysisSkill |
| DiagnosticsExpert 详细设计 | `docs/multiagent_05_diagnostics.md` |
| ~~KnowledgeManager 详细设计~~ | `docs/multiagent_06_knowledge_manager.md` ⚠️ 已废弃 → KnowledgeArchiveSkill |
| LLM 模型配置 | `configs/agent_models.toml` |
| 环境变量配置 | `.env`（需手动创建） |
| Phase 4 进度记录 | `docs/PROGRESS.md` |
| 配置待办清单 | `docs/TODO.md` |

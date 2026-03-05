# AutoHySeeker — Phase 4 开发进度

> 最后更新：2026-03-05

---

## 总体状态

| 模块 | 状态 | 文件路径 | 备注 |
|------|------|----------|------|
| configs 配置模块 | ✅ 完成 | `src/configs.py` | 以单文件模块实现（等同于 `src/configs/__init__.py`） |
| tool_registry 工具注册 | ✅ 完成 | `src/common/tool_registry.py` | 新增 `@registry.tool` 装饰器 + log_analysis 工具自动注册 |
| types 类型定义 | ✅ 完成 | `src/common/types.py` | 新增 ProgStep / ExperimentPlan / SystemConfig / EngineStatus / RunStatus / KnowledgeChunk / LiteratureRef |
| D1 DiagnoseFailureSkill | ✅ 完成 | `src/skills/diagnostics/diagnose_failure.py` | 规则引擎，不依赖 LLM |
| D2 SystemHealthCheckSkill | ✅ 完成 | `src/skills/diagnostics/system_health_check.py` | 4 维度健康检查 |
| D3 InteractiveTroubleshootingSkill | ✅ 完成 | `src/skills/diagnostics/interactive_troubleshooting.py` | 4 类故障决策树 |
| diagnostics __init__ | ✅ 完成 | `src/skills/diagnostics/__init__.py` | 导出 D1/D2/D3 类 + 单例实例 |
| skills __init__ | ✅ 完成 | `src/skills/__init__.py` | 整合 diagnostics + A1/B1 到顶层 skills 包 |
| Tool: data_reader | ✅ 完成 | `src/tools/data_reader.py` | load_echem_file / load_run_echem_files / read_run_metadata / list_run_files |
| Tool: echem_analysis | ✅ 完成 | `src/tools/echem_analysis.py` | analyze_cv / analyze_lsv / analyze_eis / analyze_echem_files（自动注册到 registry） |
| Tool: experiment_builder | ✅ 完成 | `src/tools/experiment_builder.py` | build_step / build_experiment_plan / generate_param_grid / build_plans_from_grid / validate_plan / plan_to_dict |
| A1 SingleExperimentAnalysisSkill | ✅ 完成 | `src/skills/single_experiment_analysis.py` | 纯数据驱动，不调用 LLM，自动检测 CV/LSV/EIS 技术 |
| B1 GenerateExperimentPlanSkill | ✅ 完成 | `src/skills/generate_experiment_plan.py` | 无 LLM，内置 HER/OER/稳定性/CV 模板 + 参数网格搜索 |
| LangGraph Subgraph：diagnostics_graph | ✅ 完成 | `src/graph/diagnostics_graph.py` | START + add_conditional_edges；D1/D2 节点；fallback；缓存 get_diagnostics_graph() |
| API 路由完善：/diagnostics | ✅ 完成 | `src/api/routes/diagnostics.py` | POST /invoke + /analyze-failure + /check-health |
| C1 ContextualizeExperimentSkill | ✅ 完成 | `src/skills/contextualize_experiment.py` | LLM-free，statistics 标准库做均值/σ/趋势；异常检测；OpenViking 知识库文献检索 |
| Tool: knowledge_retriever | ✅ 完成 | `src/tools/knowledge_retriever.py` | OpenViking find() 封装；retrieve_knowledge / retrieve_literature；优雅降级 |
| C2 SuggestNextExperimentSkill | ✅ 完成 | `src/skills/suggest_next_experiment.py` | 规则驱动推荐；依赖 C1 context_data 或 goal 字符串 |
| LangGraph Subgraph：supervisor_graph | ✅ 完成 | `src/graph/supervisor_graph.py` | 5路路由：monitor/schedule/diagnose/contextualize/suggest；fallback；缓存 get_supervisor_graph() |
| API 路由：/context | ✅ 完成 | `src/api/routes/context.py` | POST /invoke + /contextualize + /suggest-next |

---

## 详细说明

### 1. `src/configs.py` — 配置模块

**功能：** 用 Python 3.11 内置 `tomllib` 加载 `configs/` 目录下的 3 个 TOML 文件，暴露带类型标注的数据类。

**暴露接口：**

```python
from src.configs import get_settings, get_llm_config, get_microhyseeker_config

s   = get_settings()            # → Settings(general, api)
llm = get_llm_config()          # → LLMConfig(default, fallback)
mhs = get_microhyseeker_config() # → MicroHySeekerConfig(paths, engine)
```

**关键信息：**
- 使用懒加载单例（首次调用时读取 TOML，后续直接返回缓存）
- TOML 文件不存在时返回默认值，不抛出异常
- 对应 TOML 文件：`configs/settings.toml`、`configs/llm_config.toml`、`configs/microhyseeker.toml`

**注意：** 架构文档规划了 `src/configs/` 包目录，但因环境限制（无 shell 访问）以 `src/configs.py` 单文件代替，功能完全等价。后续如需扩展可重命名为包目录。

---

### 2. `src/common/tool_registry.py` — 工具注册增强

**新增功能：**

1. **`@registry.tool` 装饰器**
   ```python
   @registry.tool(description="Analyze CV data peaks")
   def detect_cv_peaks(df) -> dict: ...
   ```

2. **log_analysis 工具自动注册**（模块导入时自动执行）：
   - `parse_run_log` — 将日志文件解析为结构化 `LogEntry` 列表
   - `classify_errors` — 按来源分组 ERROR 级别日志
   - `detect_pump_anomalies` — 检测泵异常事件
   - `summarize_run` — 从 run_log + run_summary.json 构建 `RunSummary`
   - `extract_step_timeline` — 提取步骤时间线

3. **OpenAI function calling schema** 已为上述工具配置完整 JSON Schema

---

### 3. `src/common/types.py` — 类型定义扩展

**新增类型：**

| 类型 | 用途 |
|------|------|
| `ProgStep` | 实验方案中的单个可编程步骤（CV/LSV/EIS/冲洗等） |
| `ExperimentPlan` | 完整实验方案（步骤列表 + 组合参数） |
| `SystemConfig` | 系统运行时配置（设备端口、目录等） |
| `EngineStatus` | MicroHySeeker 引擎当前状态（idle/running/paused/error） |
| `RunStatus` | 实验运行实时状态快照（进度百分比、当前步骤等） |
| `KnowledgeChunk` | 从知识库检索到的文本块 |
| `LiteratureRef` | 解析后的文献条目 |

**原有类型保持不变：** `LogEntry`、`StepResult`、`RunSummary`、`EchemData`、`DiagnosticResult`、`HealthStatus`

---

### 4. D1/D2/D3 诊断 Skills

#### D1 — `DiagnoseFailureSkill` (`diagnose_failure.py`)

- **输入：** `run_dir: str`
- **输出：** `SkillResult.data` = `List[DiagnosticResult]`
- **内部流程：**
  1. 读取 `run_summary.json` 确认失败状态
  2. 解析 `run_log.log` → `LogEntry` 列表
  3. `classify_errors()` → 按来源分组错误
  4. `detect_pump_anomalies()` → 泵异常检测
  5. 关联 `run_summary.steps` 中失败步骤
  6. `summarize_run()` → 整体时长与错误数
- **特点：** 纯规则引擎，不调用 LLM

#### D2 — `SystemHealthCheckSkill` (`system_health_check.py`)

- **输入：** `data_dir: str`, `recent_n: int = 10`
- **输出：** `SkillResult.data` = `List[HealthStatus]`
- **四维度检查：**
  1. 数据目录可访问性
  2. 最近 N 次实验成功率（≥80% OK / ≥50% warning / <50% error）
  3. 日志 ERROR 频率（≥15% critical / ≥5% warning / <5% OK）
  4. 泵校准文件完整性

#### D3 — `InteractiveTroubleshootingSkill` (`interactive_troubleshooting.py`)

- **输入：** `symptom: str`（枚举值之一）
- **输出：** `SkillResult.data` = 决策树指南 dict
- **支持的故障类型：**
  - `pump_not_running` — 泵不转动（6步排查，5个可能原因）
  - `echem_no_signal` — 电化学工作站无信号（6步排查，5个可能原因）
  - `communication_timeout` — 通信超时（6步排查，5个可能原因）
  - `data_anomaly` — 数据异常（6步排查，5个可能原因）

---

## Phase 3 任务状态

| 模块 | 状态 |
|------|------|
| LangGraph Subgraph：`diagnostics_graph.py` | ✅ 完成 |
| API 路由：`/diagnostics` | ✅ 完成 |
| 测试：`test_phase3.py` | ✅ 新增 |

---

## Phase 4 任务状态

| 模块 | 状态 |
|------|------|
| C1 Skill：`contextualize_experiment.py` | ✅ 完成（含 OpenViking KB 集成） |
| Tool：`knowledge_retriever.py` | ✅ 新增 |
| C2 Skill：`suggest_next_experiment.py` | ✅ 完成 |
| LangGraph Subgraph：`supervisor_graph.py` | ✅ 完成 |
| API 路由：`/context` | ✅ 完成 |
| 测试：`test_phase4.py` | ✅ 新增 |

---

## Phase 2 任务状态

| 模块 | 状态 |
|------|------|
| Tool 层：`tools/data_reader.py` | ✅ 完成 |
| Tool 层：`tools/echem_analysis.py` | ✅ 完成 |
| Tool 层：`tools/experiment_builder.py` | ✅ 完成 |
| Skill A1：`single_experiment_analysis` | ✅ 完成 |
| Skill B1：`generate_experiment_plan` | ✅ 完成 |

---

## Phase 2 新增详细说明

### A1 — `SingleExperimentAnalysisSkill` (`src/skills/single_experiment_analysis.py`)

- **输入：** `run_dir: str`
- **输出：** `SkillResult.data` = 每文件分析结果列表（含 technique / 分析数据 / 文件元数据）
- **内部流程：**
  1. `read_run_metadata()` 读取 JSON 元数据（best-effort）
  2. `load_run_echem_files()` 加载所有 CSV
  3. 按技术类型调用 `analyze_cv/lsv/eis` 或通用统计
  4. 返回含 artifacts 路径列表的 SkillResult
- **特点：** 纯数据驱动，不调用 LLM

### B1 — `GenerateExperimentPlanSkill` (`src/skills/generate_experiment_plan.py`)

- **输入：** `goal: str`, `name?`, `step_specs?`, `param_ranges?`, `target_step_index?`, `tags?`
- **输出：** `SkillResult.data` = 验证后的 plan dict 列表
- **内置模板：** `her` / `oer` / `stability` / `cv_characterise` / `generic`
- **参数网格：** 提供 `param_ranges` 时生成多份 plan（一个组合一份）
- **特点：** 无 LLM，每份 plan 自动经过 `validate_plan` 验证，含 `_validation` 报告

---

## Phase 3 新增详细说明

### LangGraph DiagnosticsExpert Subgraph (`src/graph/diagnostics_graph.py`)

- **状态类型：** `DiagnosticsState(AutoHySeekerState, total=False)` — 继承所有父字段，新增 `diagnostics_results: list[dict]`
- **图拓扑：**
  ```
  START ──(route_diagnostics)──► analyze_failure ──► generate_diagnosis_report ──► END
                             └──► check_health   ──┘
  ```
- **路由逻辑：** `state['task']['action'] == "analyze_failure"` → D1；否则 → D2（默认 check_health）
- **节点：**
  - `analyze_failure` — 调用 `DiagnoseFailureSkill.execute(run_dir=...)`
  - `check_health` — 调用 `SystemHealthCheckSkill.execute(data_dir=..., recent_n=...)`
  - `generate_diagnosis_report` — 聚合 findings，统计 severity，返回 `result` dict
- **实现特点：**
  - 使用现代 `add_conditional_edges(START, ...)` API（替代废弃的 `set_conditional_entry_point`）
  - 含 `_FallbackDiagnosticsGraph` — 无 LangGraph 依赖时退化为串行调用
  - `get_diagnostics_graph()` 缓存单例，避免重复编译

### Diagnostics API Routes (`src/api/routes/diagnostics.py`)

**新增端点：**

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/diagnostics/invoke` | 通用入口，JSON body 含 `action` / `run_dir` / `data_dir` / `recent_n` |
| POST | `/diagnostics/analyze-failure` | D1 快捷方式，query param `run_dir` |
| POST | `/diagnostics/check-health` | D2 快捷方式，query params `data_dir` + `recent_n` |

**返回格式（`/invoke`）：**
```json
{
  "ok": true,
  "action": "check_health",
  "result": {
    "action": "check_health",
    "total_findings": 4,
    "severity_counts": {"ok": 2, "warning": 1, "error": 1},
    "findings": [...]
  },
  "error": null
}
```

---

## 测试状态

```
tests/test_import_smoke.py   — ✅ 通过（核心导入测试）
tests/test_tools_phase2.py   — ✅ 新增（Tool 层：data_reader / echem_analysis / experiment_builder）
tests/test_skills_phase2.py  — ✅ 新增（Skill A1 / B1 + skills __init__ 导出验证）
tests/test_phase3.py         — ✅ 新增（DiagnosticsGraph + diagnostics API routes，共 20 个测试）
tests/test_phase4.py         — ✅ 新增（C1/C2 Skills + knowledge_retriever + KB集成 + SupervisorGraph + /context API routes，共 45+ 个测试）
```

运行方式：
```bash
cd AutoHySeeker
uv run pytest tests/
```

---

## Phase 4 新增详细说明

### C1 — `ContextualizeExperimentSkill` (`src/skills/contextualize_experiment.py`)

- **输入：** `run_dir: str`, `history_dir?`, `previous_results?`, `metrics?`, `threshold_sigma=2.0`, `max_history=20`, `kb_path?`, `kb_query?`, `kb_limit=5`, `kb_score_threshold=0.3`
- **输出：** `SkillResult.data` = 结构化上下文 dict
- **内部流程：**
  1. `read_run_metadata()` 读取 JSON 元数据
  2. `load_run_echem_files()` 提取电化学统计均值
  3. 扫描 `history_dir` 或使用 `previous_results` 构建历史数据
  4. 逐指标计算 delta / trend (前后半段均值对比) / σ-anomaly
  5. 若提供 `kb_path`，调用 `retrieve_literature()` 和 `retrieve_knowledge()` 从 OpenViking 知识库检索相关文献与实验记录
  6. 自动构建 KB 查询（基于实验名、异常指标、指标名称），也可通过 `kb_query` 手动指定
- **输出结构：**
  ```json
  {
    "run_dir": "...",
    "comparison": {"metric": {"current": 0.05, "historical_mean": 0.04, "delta": 0.01}},
    "trend":      {"metric": "improving"},
    "anomalies":  ["metric"],
    "literature": [{"title": "...", "authors": [...], "doi": "..."}],
    "knowledge_chunks": [{"chunk_id": "...", "content": "...", "score": 0.8}],
    "n_history":  10,
    "summary":    "Contextualised 3 metric(s) against 10 historical run(s). Found 2 relevant literature reference(s)."
  }
  ```
- **特点：** 纯 LLM-free，使用 `statistics` 标准库；支持直接传入 `previous_results` 绕过磁盘扫描；OpenViking 知识库检索（可选，不可用时优雅降级）

### `knowledge_retriever` 工具 (`src/tools/knowledge_retriever.py`)

- **功能：** 封装 OpenViking `find()` API，提供文献检索和知识片段检索
- **暴露接口：**
  - `retrieve_knowledge(query, kb_path, limit, score_threshold)` → `list[KnowledgeChunk]`
  - `retrieve_literature(query, kb_path, limit, score_threshold)` → `list[LiteratureRef]`
- **特点：**
  - OpenViking 未安装时优雅降级，返回空列表
  - 自动解析文献元数据（标题、作者、年份、DOI）
  - 惰性导入守卫，避免不必要的导入开销

### C2 — `SuggestNextExperimentSkill` (`src/skills/suggest_next_experiment.py`)

- **输入：** `context_data?`, `goal?`, `name?`, `description?`, `tags?`
- **输出：** `SkillResult.data` = `{intent, rationale, plan, valid}`
- **决策逻辑（优先级从高到低）：**
  1. 存在 anomalies → `diagnostic_run`（诊断性实验）
  2. 存在 declining 趋势 → `stability_run`（稳定性实验）
  3. goal 含 "optim/scan/sweep/grid" → `optimisation_run`
  4. goal 含 "stable/durabil/chronic" → `stability_run`
  5. goal 含 "diagnos/debug/check" → `diagnostic_run`
  6. 默认 → `generic`
- **特点：** 无 LLM；调用 `build_experiment_plan()` + `validate_plan()` 自动生成验证过的方案

### ExperimentSupervisor Subgraph (`src/graph/supervisor_graph.py`)

- **图拓扑：**
  ```
  START ──(route_task)──► monitor       ──► END
                       ├──► schedule      ──► END
                       ├──► diagnose      ──► END
                       ├──► contextualize ──► END
                       └──► suggest       ──► END
  ```
- **C1→C2 数据流：** `contextualize_node` 将 C1 输出写入 `state["context"]["context_data"]`，`suggest_node` 优先读取 `task["context_data"]`，其次读取 `state["context"]["context_data"]`
- **实现特点：** `_FallbackSupervisorGraph` 支持无 LangGraph 环境；`get_supervisor_graph()` 单例缓存

### Context API Routes (`src/api/routes/context.py`)

**新增端点：**

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/context/invoke` | 通用入口，JSON body 含 `action` ("contextualize"/"suggest") |
| POST | `/context/contextualize` | C1 快捷方式，query params `run_dir` + `history_dir` |
| POST | `/context/suggest-next` | C2 快捷方式，query params `goal` + `name` |

**返回格式（`/context/invoke`）：**
```json
{
  "ok": true,
  "action": "suggest",
  "result": {
    "success": true,
    "data": {
      "intent": "optimisation_run",
      "rationale": "Goal requests optimisation; advancing to parameter sweep.",
      "plan": {...},
      "valid": true
    },
    "message": "Suggested 'optimisation_run' plan with 5 step(s)."
  },
  "error": null
}
```

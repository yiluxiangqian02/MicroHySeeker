# AutoHySeeker — Phase 1 开发进度

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
| skills __init__ | ✅ 完成 | `src/skills/__init__.py` | 整合 diagnostics 到顶层 skills 包 |

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

## Phase 2 预计任务

| 模块 | 状态 |
|------|------|
| Tool 层：`tools/data_reader.py` | 🔲 待开发 |
| Tool 层：`tools/echem_analysis.py` | 🔲 待开发 |
| Tool 层：`tools/experiment_builder.py` | 🔲 待开发 |
| Skill A1：`single_experiment_analysis` | 🔲 待开发 |
| Skill B1：`generate_experiment_plan` | 🔲 待开发 |
| LangGraph Subgraph：`diagnostics_graph.py` | 🔲 待开发 |
| API 路由完善 | 🔲 待开发 |

---

## 测试状态

```
tests/test_import_smoke.py   — ✅ 通过（核心导入测试）
```

运行方式：
```bash
cd AutoHySeeker
uv run pytest tests/
```

# AutoHySeeker — Skills 架构详细设计文档

> 2026-02-23 | v3 2026-02-25 | 定位：与 MicroHySeeker 并行的 AI 科研Agent系统
> 核心理念：**LangGraph 编排 + Skills 解耦 + Tools 原子化 + LLM 推理**
> 选定需求域：② 实验设计 · ③ 实验执行与监控 · ④ 数据处理与分析 · ⑤ 故障诊断与运维 · ⑥ RAG 知识检索
>
> **关联文档**：
> - 多 Agent 编排总设计 → [`langgraph_architecture.md`](langgraph_architecture.md)
> - Agent 开发文档 → [`dev_agent_data_analyst.md`](dev_agent_data_analyst.md) · [`dev_agent_experiment_designer.md`](dev_agent_experiment_designer.md) · [`dev_agent_experiment_supervisor.md`](dev_agent_experiment_supervisor.md) · [`dev_agent_diagnostics_expert.md`](dev_agent_diagnostics_expert.md) · [`dev_agent_knowledge_manager.md`](dev_agent_knowledge_manager.md) · [`dev_agent_orchestrator.md`](dev_agent_orchestrator.md)

---

## 一、项目总览

### 1.1 AutoHySeeker 与 MicroHySeeker 的关系

```
MicroHySeeker/              ← 实验室设备控制桌面端（PySide6）
  ├── src/                  ← 硬件驱动、实验引擎、UI
  ├── data/                 ← 实验数据产出
  └── config/               ← 系统配置

AutoHySeeker/               ← AI Agent 系统（独立项目，uv管理）
  ├── src/
  │   ├── skills/           ← 各个解耦的 Skill 模块
  │   ├── tools/            ← 原子化 Tool（供 Skill 内部和 LLM Function Calling 使用）
  │   ├── agents/           ← Agent 定义（System Prompt + Skill 绑定）
  │   ├── rag/              ← RAG 管线（文档处理、向量库、检索）
  │   └── common/           ← 共享工具（配置、日志、类型定义）
  ├── configs/
  ├── data/                 ← Agent 自己的数据（知识库、缓存等）
  ├── tests/
  ├── pyproject.toml        ← uv 管理
  └── README.md
```

### 1.2 交互方式

```
┌──────────────────┐        ┌──────────────────────────────────┐
│  MicroHySeeker   │        │         AutoHySeeker             │
│  (桌面端)         │        │                                  │
│                  │  文件   │  ┌────────────────────┐          │
│  data/ ──────────┼───────►│  │  Tools (读取数据)   │          │
│  config/ ────────┼───────►│  │  - read_experiment  │          │
│  run_log ────────┼───────►│  │  - read_csv         │          │
│                  │        │  │  - read_log         │          │
│                  │  API   │  └────────┬───────────┘          │
│  Engine ◄────────┼────────│  │  Tools (控制实验)   │          │
│  (start/stop/    │  调用  │  │  - start_experiment │          │
│   load_program)  │        │  │  - stop_experiment  │          │
│                  │        │  └────────┬───────────┘          │
│                  │        │           │                      │
│                  │        │  ┌────────▼───────────┐          │
│                  │        │  │   Skills Layer      │          │
│                  │        │  │   (LLM 编排调用)    │          │
│                  │        │  └────────┬───────────┘          │
│                  │        │           │                      │
│                  │        │  ┌────────▼───────────┐          │
│                  │        │  │  Agents / Chat UI   │          │
│                  │        │  └────────────────────┘          │
└──────────────────┘        └──────────────────────────────────┘
```

**交互模式**：
- **数据读取**：AutoHySeeker 直接读 MicroHySeeker 的 `data/`、`config/`、`logs/` 目录（文件级耦合）
- **实验控制**：通过 MicroHySeeker 暴露的 API（后续可加 HTTP/WebSocket/IPC）
- **完全独立运行**：AutoHySeeker 即使没有 MicroHySeeker 也能分析已有数据

### 1.3 三层架构

```
Layer 3 — Agents     用户对话 → 意图理解 → 选择 Skill → 组合调用 → 返回结果
Layer 2 — Skills     一组 Tools 的有意义编排，完成一个完整的科研子任务
Layer 1 — Tools      最小粒度的原子操作，无状态，一调一用
```

**区分**：
- **Tool**：`read_cv_csv(path) → DataFrame` — 纯数据操作，无推理
- **Skill**：`analyze_cv_experiment(run_dir)` — 调用多个 Tool + LLM 推理 → 完整分析报告
- **Agent**：持有 System Prompt + 多个 Skill + 对话历史 → 与用户交互

---

## 二、Tool 层设计（原子工具）

> Tool 是最小粒度的操作单元。每个 Tool 是一个 Python 函数，带有类型标注和 docstring。
> 它们既可以被 Skill 内部调用，也可以通过 ToolRegistry 注册为 OpenAI Function Calling。

### 2.1 数据读取 Tools（`tools/data_reader.py`）

| Tool 函数 | 输入 | 输出 | 说明 |
|-----------|------|------|------|
| `list_experiment_runs(data_dir, date?, status?)` | 路径+过滤 | `List[RunSummary]` | 列出所有实验运行 |
| `read_run_summary(run_dir)` | 目录路径 | `RunSummary` dict | 读取 run_summary.json |
| `read_experiment_plan(run_dir)` | 目录路径 | `ExperimentPlan` dict | 读取 experiment.json |
| `read_echem_csv(csv_path)` | CSV 路径 | `DataFrame` (列: Potential/V, Current/A 等) | 读取电化学CSV数据 |
| `read_pump_operations(run_dir)` | 目录路径 | `DataFrame` | 读取 pump_operations.csv |
| `read_run_log(run_dir, level?)` | 目录+级别过滤 | `List[LogEntry]` | 读取并解析 run_log.log |
| `read_system_config(config_path)` | 配置路径 | `SystemConfig` dict | 读取 system.json |
| `list_echem_files(run_dir)` | 目录路径 | `List[{path, technique, step_index}]` | 列出 echem/ 下所有文件 |

**实现依赖**：`pandas`, `json`, `pathlib`, `re`（全部标准库或轻量级）

### 2.2 数据分析 Tools（`tools/echem_analysis.py`）

| Tool 函数 | 输入 | 输出 | 说明 |
|-----------|------|------|------|
| `detect_cv_peaks(df)` | CV DataFrame | `{ox_peak, red_peak, delta_ep, peak_ratio, reversibility}` | CV 氧化/还原峰检测 |
| `calculate_tafel_slope(df, potential_range?)` | LSV/CV DataFrame | `{slope_mV_dec, exchange_current, r_squared}` | Tafel 斜率拟合 |
| `fit_eis_circuit(df, model?)` | EIS DataFrame | `{parameters, chi_squared, equivalent_circuit}` | EIS 等效电路拟合 |
| `calculate_diffusion_coeff(peak_currents, scan_rates, ...)` | 多组数据 | `{D, r_squared}` | Randles-Sevcik 公式 |
| `assess_data_quality(df, technique)` | DataFrame+技术 | `{score, noise_level, baseline_drift, anomalies}` | 数据质量评分 |
| `detect_anomalies(df)` | DataFrame | `List[{index, type, severity}]` | 异常点检测 |
| `calculate_charge(df)` | i-t DataFrame | `{charge_C, charge_mC}` | 积分求电荷量 |
| `extract_steady_state(df, window?)` | i-t DataFrame | `{steady_current, time_to_steady, std}` | 稳态电流提取 |

**实现依赖**：`scipy.signal.find_peaks`, `scipy.optimize.curve_fit`, `numpy`, `pandas`
**可选依赖**：`impedance`（EIS 拟合）, `lmfit`（高级拟合）

### 2.3 数据可视化 Tools（`tools/visualization.py`）

| Tool 函数 | 输入 | 输出 | 说明 |
|-----------|------|------|------|
| `plot_cv(df, peaks?, title?, save_path?)` | DF+选项 | `Figure` 或 PNG路径 | 绘制 CV 曲线+标注峰值 |
| `plot_multi_cv(dfs_dict, title?)` | `{"label": df}` | `Figure` | 多条 CV 叠加对比 |
| `plot_eis_nyquist(df, fit?, title?)` | DF+拟合 | `Figure` | Nyquist 图 |
| `plot_eis_bode(df, title?)` | DF | `Figure` | Bode 图 |
| `plot_tafel(df, fit?, title?)` | DF+拟合 | `Figure` | Tafel 图 |
| `plot_it_curve(df, title?)` | DF | `Figure` | i-t 曲线 |
| `plot_trend(series, xlabel, ylabel, title?)` | 时间序列 | `Figure` | 趋势图 |
| `plot_calibration_curve(concs, currents, fit?)` | 数据+拟合 | `Figure` | 标定曲线 |
| `plot_comparison_bar(data, labels, metrics)` | 多组指标 | `Figure` | 柱状对比图 |

**实现依赖**：`matplotlib`
**可选**：`plotly`（交互式）

### 2.4 实验方案 Tools（`tools/experiment_builder.py`）

| Tool 函数 | 输入 | 输出 | 说明 |
|-----------|------|------|------|
| `build_cv_step(e_init, e_high, e_low, scan_rate, ...)` | 参数 | `ProgStep` JSON | 构建一个 CV 步骤 |
| `build_lsv_step(...)` | 参数 | `ProgStep` JSON | 构建 LSV 步骤 |
| `build_eis_step(...)` | 参数 | `ProgStep` JSON | 构建 EIS 步骤 |
| `build_prep_sol_step(concentrations, total_volume, ...)` | 参数 | `ProgStep` JSON | 构建配液步骤 |
| `build_flush_step(cycles, ...)` | 参数 | `ProgStep` JSON | 构建冲洗步骤 |
| `build_transfer_step(...)` | 参数 | `ProgStep` JSON | 构建移液步骤 |
| `build_blank_step(duration_s)` | 秒数 | `ProgStep` JSON | 构建等待步骤 |
| `build_evacuate_step(duration_s)` | 秒数 | `ProgStep` JSON | 构建排空步骤 |
| `assemble_experiment(name, steps, combo_params?)` | 步骤列表 | 完整 `ExperimentPlan` JSON | 组装完整实验方案 |
| `validate_experiment(plan_json)` | JSON | `{valid, errors, warnings}` | 校验方案合法性 |
| `generate_combo_matrix(param_ranges)` | 参数范围 | `List[Dict]` | 生成组合参数矩阵 |

**实现依赖**：`jsonschema`, `pydantic`, `itertools`

### 2.5 实验控制 Tools（`tools/experiment_control.py`）

| Tool 函数 | 输入 | 输出 | 说明 |
|-----------|------|------|------|
| `get_engine_status()` | — | `EngineStatus` | 查询当前引擎状态 |
| `load_experiment(plan_json)` | 实验方案 | `bool` | 加载方案到引擎 |
| `start_experiment(combo_mode?)` | 选项 | `bool` | 启动实验 |
| `stop_experiment()` | — | `bool` | 停止实验 |
| `pause_experiment()` | — | `bool` | 暂停 |
| `resume_experiment()` | — | `bool` | 恢复 |
| `get_hardware_status()` | — | `Dict` | 查询泵/仪器状态 |
| `subscribe_events(event_types)` | 事件列表 | `AsyncIterator` | 订阅引擎事件流 |

**实现方式**：通过与 MicroHySeeker 的 IPC 通道（初期可用文件+命令，后续升级为 WebSocket）
**注意**：这组 Tool 需要 MicroHySeeker 运行中才可用

### 2.6 日志与诊断 Tools（`tools/log_analysis.py`）

| Tool 函数 | 输入 | 输出 | 说明 |
|-----------|------|------|------|
| `parse_run_log(log_path)` | 日志路径 | `List[LogEntry]` 结构化 | 解析日志为结构化数据 |
| `extract_errors(log_entries)` | 日志列表 | `List[ErrorEntry]` | 提取所有错误 |
| `extract_warnings(log_entries)` | 日志列表 | `List[WarningEntry]` | 提取所有警告 |
| `classify_error(error_msg)` | 错误文本 | `{category, subcategory, severity}` | 错误分类（规则引擎） |
| `extract_timing_info(log_entries)` | 日志列表 | `{step_durations, total, gaps}` | 提取时间信息 |
| `detect_pump_anomalies(pump_df)` | 泵操作DF | `List[Anomaly]` | 泵操作异常检测 |
| `check_calibration_drift(calibration_history)` | 历史校准 | `{drift, recommendation}` | 校准漂移检查 |
| `get_error_knowledge_base()` | — | `Dict` | 获取已知错误→解决方案映射 |

**实现依赖**：`re`, `pandas`, `datetime`

### 2.7 RAG Tools（`tools/rag_tools.py`）

| Tool 函数 | 输入 | 输出 | 说明 |
|-----------|------|------|------|
| `ingest_pdf(pdf_path, collection?)` | PDF路径 | `{doc_id, chunks_count}` | PDF → 分块 → 入向量库 |
| `ingest_text(text, metadata, collection?)` | 文本+元数据 | `{doc_id}` | 文本入库 |
| `ingest_experiment_knowledge(run_dir)` | 运行目录 | `{doc_id}` | 实验结果→知识库 |
| `semantic_search(query, collection?, top_k?)` | 查询 | `List[{chunk, score, metadata}]` | 语义搜索 |
| `list_collections()` | — | `List[str]` | 列出所有知识库集合 |
| `delete_document(doc_id)` | 文档ID | `bool` | 删除文档 |
| `get_collection_stats(collection)` | 集合名 | `{count, sources}` | 集合统计 |

**实现依赖**：
- PDF 解析：`pymupdf`(fitz) 或 `pdfplumber`
- 分块：`langchain_text_splitters` 或自定义
- Embedding：`sentence-transformers` (本地) 或 `OpenAI Embeddings`
- 向量库：`chromadb`（本地轻量）或 `faiss`
- **集合设计**：
  - `literature` — 文献 PDF
  - `experiment_archive` — 历史实验结果和经验
  - `instrument_manual` — 仪器手册（CHI 660F 等）
  - `error_solutions` — 错误解决方案
  - `domain_knowledge` — 电化学领域知识

### 2.8 报告生成 Tools（`tools/report_generator.py`）

| Tool 函数 | 输入 | 输出 | 说明 |
|-----------|------|------|------|
| `render_markdown_report(template, data)` | 模板+数据 | `str` (Markdown) | 渲染 Markdown 报告 |
| `render_html_report(template, data)` | 模板+数据 | `str` (HTML) | 渲染 HTML |
| `markdown_to_pdf(md_content, output_path)` | Markdown | PDF 路径 | 转 PDF |
| `markdown_to_docx(md_content, output_path)` | Markdown | DOCX 路径 | 转 Word |
| `embed_figure_base64(figure)` | matplotlib Fig | `str` (base64) | 图表嵌入 |
| `save_figure(figure, path, dpi?)` | Fig+路径 | 路径 | 保存高清图表 |

**实现依赖**：`jinja2`, `markdown`, `python-docx`, `weasyprint`(PDF)

---

## 三、Skill 层设计（科研任务单元）

> Skill = 一组 Tools + LLM 推理 + 结构化流程，完成一个**有意义的科研子任务**。
> 每个 Skill 有明确的输入/输出，可被 Agent 独立调用。

### 3.1 Skill 基类

```python
# src/skills/base.py

class BaseSkill:
    """Skill 基类 — 所有 Skill 继承此类"""
    
    name: str                    # Skill 名称（唯一标识）
    description: str             # 给 LLM 看的描述
    input_schema: dict           # JSON Schema 描述输入
    output_schema: dict          # JSON Schema 描述输出
    required_tools: List[str]    # 依赖的 Tool 列表
    
    async def execute(self, params: dict, llm: LLMClient | None = None) -> SkillResult:
        """执行 Skill。llm 参数可选，有些 Skill 不需要 LLM。"""
        raise NotImplementedError
    
    def validate_input(self, params: dict) -> bool: ...
    def get_tool(self, name: str) -> Callable: ...

@dataclass
class SkillResult:
    success: bool
    data: dict                   # 结构化结果
    summary: str                 # 人类可读摘要（可由 LLM 生成）
    artifacts: List[str]         # 生成的文件路径（图表、报告等）
    errors: List[str]
```

---

### 域 A：数据处理与分析 Skills（对应需求域④）

#### Skill A1：`single_experiment_analysis` — 单次实验完整分析

```
输入：{run_dir: str}
输出：{
  summary: {name, date, duration, success, steps_count},
  echem_results: [{technique, peaks?, tafel?, quality_score, ...}],
  pump_operations_summary: {...},
  data_quality: {overall_score, issues: []},
  figures: [path1, path2, ...],
  interpretation: str  ← LLM 生成的自然语言解读
}

内部流程：
  1. read_run_summary(run_dir)           → 基本信息
  2. list_echem_files(run_dir)           → 电化学文件列表
  3. for each echem file:
     a. read_echem_csv(path)             → DataFrame
     b. detect_cv_peaks(df) / calculate_tafel_slope(df) / ...  → 特征值
     c. assess_data_quality(df, technique) → 质量评分
     d. plot_cv(df, peaks) / plot_eis_nyquist(df) / ...  → 图表
  4. read_pump_operations(run_dir)       → 泵操作分析
  5. [LLM] 综合所有分析结果 → 生成自然语言解读

依赖 Tools：
  - data_reader: read_run_summary, list_echem_files, read_echem_csv, read_pump_operations
  - echem_analysis: detect_cv_peaks, calculate_tafel_slope, assess_data_quality
  - visualization: plot_cv, plot_eis_nyquist, plot_tafel, plot_it_curve
  - LLM: 结果解读

不需要 LLM 也能运行：只是没有自然语言解读
```

#### Skill A2：`multi_experiment_comparison` — 多实验对比分析

```
输入：{run_dirs: List[str], comparison_dimension?: str, metrics?: List[str]}
输出：{
  comparison_table: DataFrame,    # 关键指标对比表
  trends: [{metric, direction, significance}],
  best_run: str,
  worst_run: str,
  figures: [comparison_plots],
  interpretation: str  ← LLM
}

内部流程：
  1. for each run_dir: single_experiment_analysis(run_dir) → 各自结果
  2. 提取关键指标对齐到对比表
  3. 统计分析（均值、方差、相关性）
  4. plot_multi_cv / plot_comparison_bar / plot_trend → 对比图
  5. [LLM] 综合对比 → 哪个最好、为什么、建议

依赖 Tools：
  - 所有 A1 的 Tools
  - echem_analysis: detect_anomalies
  - visualization: plot_multi_cv, plot_comparison_bar, plot_trend
  - LLM: 对比解读
```

#### Skill A3：`trend_tracking` — 跨天/跨批次趋势追踪

```
输入：{date_range?: [start, end], metric: str, filter?: dict}
输出：{
  timeline: [{date, value, run_id}],
  trend_direction: "up|down|stable",
  change_points: [...],
  figures: [trend_plot],
  interpretation: str
}

内部流程：
  1. list_experiment_runs(date_range) → 所有相关实验
  2. for each run: 提取目标指标
  3. 时序分析（趋势、变化点检测）
  4. plot_trend → 趋势图
  5. [LLM] 趋势解读 + 建议

依赖 Tools：
  - data_reader: list_experiment_runs, read_run_summary, read_echem_csv
  - echem_analysis: 特定指标提取
  - visualization: plot_trend
  - LLM: 解读
```

#### Skill A4：`natural_language_data_query` — 自然语言数据查询

```
输入：{question: str}  e.g. "找出上周所有 CV 实验中峰电流最大的那个"
输出：{
  answer: str,
  data: Any,         # 查询到的具体数据
  figures: [...],     # 如果需要图表
  sql_or_filter: str  # 生成的查询条件（可审计）
}

内部流程：
  1. [LLM] 理解用户问题 → 生成数据查询计划
  2. 执行查询（list_runs + filter + 读取分析）
  3. [LLM] 组织答案
  
核心是 LLM + Tool Calling 的动态编排
```

---

### 域 B：实验设计 Skills（对应需求域②）

#### Skill B1：`generate_experiment_plan` — 自然语言→实验方案

```
输入：{description: str, constraints?: dict}
  e.g. "我想做 Fe 浓度梯度（0.1-0.5M，间隔0.1）的 CV 扫描，扫速 50mV/s"
输出：{
  experiment_json: dict,     # 完整的 MicroHySeeker 实验方案 JSON
  explanation: str,          # 解释为什么这样设计
  warnings: List[str],       # 潜在问题提醒
  estimated_duration: float  # 预估总时长
}

内部流程：
  1. [LLM] 解析用户自然语言意图 → 确定步骤类型、参数
  2. read_system_config → 获取可用通道、泵地址、校准信息
  3. [LLM] 结合硬件约束 → 生成方案
  4. build_*_step / assemble_experiment → 构建 JSON
  5. validate_experiment → 校验
  6. [LLM] 安全审查 + 合理性检查
  7. 计算预估时长

依赖 Tools：
  - data_reader: read_system_config
  - experiment_builder: build_cv_step, build_prep_sol_step, ... , assemble_experiment, validate_experiment
  - LLM: 意图理解 + 方案生成 + 安全审查
  
RAG 增强：检索相关文献中的方法参数作为参考
```

#### Skill B2：`optimize_parameters` — 参数优化建议

```
输入：{
  objective: str,             # "最大化峰电流" / "最小化过电位"
  parameter_space: dict,      # {"scan_rate": [10, 200], "concentration": [0.1, 1.0]}
  existing_results?: List     # 已有实验结果（可选）
}
输出：{
  suggested_params: List[dict],   # 建议的下一组参数
  method: str,                    # "bayesian" | "doe" | "grid"
  rationale: str,                 # LLM 解释
  expected_improvement: float
}

内部流程：
  1. 如有历史数据 → 拟合代理模型
  2. DOE / 贝叶斯优化 → 生成建议参数
  3. [LLM] 解释建议 + 结合领域知识调整

依赖 Tools：
  - data_reader (历史数据)
  - echem_analysis (提取目标指标)
  
外部库：`optuna` / `botorch` / `scipy.optimize`
```

#### Skill B3：`validate_and_review_plan` — 实验方案审查

```
输入：{experiment_json: dict}
输出：{
  validation: {valid, errors, warnings},
  review: {
    safety_issues: [...],
    parameter_concerns: [...],
    optimization_suggestions: [...],
    estimated_duration: float,
    reagent_consumption: dict
  },
  revised_plan?: dict  # 如果有建议修改，给出修改后版本
}

内部流程：
  1. validate_experiment → 结构校验
  2. 规则检查（电位范围、扫速范围、浓度极限）
  3. [RAG] 检索类似实验的典型参数作对比
  4. [LLM] 综合审查 → 安全、合理性、优化建议

依赖 Tools：
  - experiment_builder: validate_experiment
  - rag_tools: semantic_search (检索类似实验)
  - data_reader: read_system_config (硬件约束)
  - LLM: 专业审查
```

#### Skill B4：`replicate_literature_method` — 文献方法复现

```
输入：{paper_pdf_path?: str, method_text?: str, target_platform: "MicroHySeeker"}
输出：{
  extracted_method: dict,        # 从文献提取的方法参数
  adapted_plan: dict,            # 适配本平台的实验方案 JSON
  adaptations: List[str],        # 做了哪些调整，为什么
  missing_info: List[str]        # 文献中缺失的信息
}

内部流程：
  1. [LLM + PDF] 提取文献中的方法参数
  2. 映射到 MicroHySeeker 的步骤类型和参数格式
  3. 结合 read_system_config 适配硬件
  4. assemble_experiment → 生成方案
  5. [LLM] 标注差异和缺失

依赖 Tools：
  - rag_tools: ingest_pdf（如需）
  - experiment_builder: 全部
  - data_reader: read_system_config
  - LLM: 方法提取 + 适配推理
```

---

### 域 C：实验执行与监控 Skills（对应需求域③）

#### Skill C1：`experiment_execution_monitor` — 实验实时监控

```
输入：{run_dir: str, alert_config?: dict}
输出：（持续输出）{
  status_updates: stream,
  alerts: [{time, type, message, severity}],
  quality_checkpoints: [{step, quality_score}],
  final_summary: SkillResult
}

内部流程（持续运行）：
  1. subscribe_events([DATA, STEP, ERROR]) → 监听实验事件
  2. 每收到 echem_data 事件 → assess_data_quality 在线评估
  3. 数据质量低于阈值 → 报警
  4. 步骤完成 → 快速分析 → 汇总
  5. 实验结束 → single_experiment_analysis → 完整报告

依赖 Tools：
  - experiment_control: subscribe_events, get_engine_status
  - echem_analysis: assess_data_quality, detect_anomalies
  - LLM: 异常解读（可选）
  
注意：此 Skill 需要 MicroHySeeker 实时运行
```

#### Skill C2：`smart_experiment_scheduler` — 智能实验排程

```
输入：{
  experiments: List[ExperimentPlan],   # 要运行的实验列表
  priorities?: List[int],
  constraints?: {max_duration_h?, reagent_limits?}
}
输出：{
  schedule: [{order, experiment_name, estimated_start, estimated_duration}],
  optimization_notes: str,
  total_duration: float,
  reagent_budget: dict
}

内部流程：
  1. 分析每个实验的耗时、试剂消耗
  2. 分析冲洗需求和切换成本
  3. 优化排列顺序（减少冲洗次数、相似条件分组）
  4. [LLM] 综合建议

依赖 Tools：
  - experiment_builder: validate_experiment
  - data_reader: read_system_config
  - LLM: 优化建议
```

#### Skill C3：`adaptive_experiment_loop` — 自适应实验闭环（高级）

```
输入：{
  objective: str,
  initial_plan: ExperimentPlan,
  max_iterations: int,
  convergence_criteria: dict
}
输出：{
  iterations: [{params, results, decision}],
  optimal_params: dict,
  convergence_history: [...],
  final_conclusion: str
}

内部流程（循环）：
  1. load_experiment + start_experiment → 执行
  2. experiment_execution_monitor → 监控
  3. single_experiment_analysis → 分析结果
  4. optimize_parameters → 决定下一组参数
  5. [LLM] 判断是否继续/终止/调整方向
  6. generate_experiment_plan(下一组) → 循环

这是最高级的 Skill，本质是 Multi-Agent 循环调用其他 Skills
```

---

### 域 D：故障诊断与运维 Skills（对应需求域⑤）

#### Skill D1：`diagnose_failed_experiment` — 失败实验诊断

```
输入：{run_dir: str}
输出：{
  error_summary: {error_type, error_msg, occurred_at, step_index},
  root_cause_analysis: {
    category: "hardware|software|parameter|reagent|communication",
    likely_cause: str,
    confidence: float,
    evidence: List[str]
  },
  similar_past_errors: List[{run_id, error, solution}],
  recommended_actions: List[{action, priority}],
  auto_fixable: bool
}

内部流程：
  1. read_run_summary → 定位失败步骤和错误信息  
  2. read_run_log → 提取上下文日志  
  3. extract_errors + classify_error → 错误分类  
  4. read_pump_operations → 检查泵操作异常  
  5. [RAG] semantic_search("error_solutions", error_msg) → 历史方案
  6. [LLM] 综合推理 → 根因分析 + 解决建议

依赖 Tools：
  - data_reader: read_run_summary, read_run_log, read_pump_operations
  - log_analysis: parse_run_log, extract_errors, classify_error, detect_pump_anomalies
  - rag_tools: semantic_search
  - LLM: 根因推理 + 解决建议
```

#### Skill D2：`system_health_check` — 系统健康检查

```
输入：{check_depth?: "quick|standard|deep"}
输出：{
  overall_health: float (0-100),
  components: {
    pumps: [{addr, health, issues}],
    chi_instrument: {status, notes},
    calibration: [{pump, drift, last_calibrated}],
    communication: {rs485_status, error_rate}
  },
  maintenance_suggestions: List[{component, action, urgency}],
  next_check_recommended: datetime
}

内部流程：
  1. read_system_config → 当前配置
  2. 分析近期所有实验的 pump_operations → 异常频率统计
  3. 分析近期 run_logs → 错误频率和类型
  4. check_calibration_drift → 校准状态
  5. [LLM] 综合评估 + 维护建议

依赖 Tools：
  - data_reader: read_system_config, list_experiment_runs
  - log_analysis: parse_run_log, detect_pump_anomalies, check_calibration_drift
  - LLM: 综合评估
```

#### Skill D3：`interactive_troubleshooting` — 交互式排错

```
输入：{symptom: str}  e.g. "泵1不转了" / "CV数据全是噪声" / "RS485超时"
输出：（对话式）{
  diagnosis_steps: [{question, check_action, expected_vs_actual}],
  probable_cause: str,
  solution: str
}

内部流程：
  1. [LLM] 理解症状 → 生成诊断决策树
  2. get_hardware_status → 收集当前状态
  3. [RAG] 检索类似问题解决方案
  4. [LLM] 引导用户逐步排查（多轮对话）

依赖 Tools：
  - experiment_control: get_hardware_status
  - rag_tools: semantic_search
  - log_analysis: get_error_knowledge_base
  - LLM: 对话式推理
```

---

### 域 E：RAG 知识管理 Skills（跨域支撑）

#### Skill E1：`build_knowledge_base` — 知识库构建

```
输入：{
  source_type: "pdf|experiment|manual|text",
  source_path: str,
  collection: str,
  metadata?: dict
}
输出：{
  doc_id: str,
  chunks_count: int,
  collection: str,
  summary: str  ← LLM 自动生成摘要
}

内部流程：
  1. 根据 source_type 选择解析方式
  2. PDF → pymupdf 提取文本（图表用 VL 模型识别）
  3. 文本分块（overlap 策略）
  4. [LLM] 生成文档摘要（存入 metadata）
  5. Embedding → 入向量库

依赖 Tools：
  - rag_tools: ingest_pdf, ingest_text, ingest_experiment_knowledge
  - LLM: 摘要生成
```

#### Skill E2：`knowledge_qa` — 知识问答

```
输入：{question: str, collections?: List[str], mode?: "precise|broad"}
输出：{
  answer: str,
  sources: [{doc_id, chunk_text, score, source_file}],
  confidence: float
}

内部流程：
  1. semantic_search(question, collections) → top-k 相关片段
  2. [LLM] 基于检索结果 + question → 生成回答
  3. 标注来源可追溯

依赖 Tools：
  - rag_tools: semantic_search
  - LLM: RAG 生成
```

#### Skill E3：`auto_archive_experiment` — 自动归档实验知识

```
输入：{run_dir: str}
输出：{doc_id, archived_items: [...]}

内部流程：
  1. single_experiment_analysis → 完整分析
  2. 将 {方案 + 参数 + 结果 + 结论} 格式化为知识条目
  3. ingest_experiment_knowledge → 入库

供后续实验参考：
  "之前用 0.3M Fe 做 CV 效果如何？" → 从知识库检索
```

---

## 四、Tool 注册与 Function Calling

> 不使用 MCP。所有 Tools 通过 **ToolRegistry** 统一管理，直接生成 OpenAI Function Calling 的 JSON Schema，
> 供 Agent 层的 LLM 调用。

### 4.1 ToolRegistry 设计

```python
# src/common/tool_registry.py
import inspect
from typing import Callable, get_type_hints

class ToolRegistry:
    """Tool 统一注册中心 — 收集所有 Tool 函数并生成 Function Calling Schema"""
    
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: list[dict] = []
    
    def register(self, func: Callable, *, category: str = ""):
        """注册一个 Tool 函数。自动从 type hints + docstring 生成 JSON Schema。"""
        name = func.__name__
        self._tools[name] = func
        self._schemas.append(self._build_schema(func, category))
    
    def tool(self, category: str = ""):
        """装饰器方式注册"""
        def decorator(func):
            self.register(func, category=category)
            return func
        return decorator
    
    def get_openai_tools(self, categories: list[str] | None = None) -> list[dict]:
        """返回 OpenAI Function Calling 格式的 tools 列表"""
        if categories is None:
            return [{"type": "function", "function": s} for s in self._schemas]
        return [
            {"type": "function", "function": s}
            for s in self._schemas if s.get("_category") in categories
        ]
    
    def call(self, name: str, **kwargs):
        """按名称调用已注册的 Tool"""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        return self._tools[name](**kwargs)
    
    def _build_schema(self, func: Callable, category: str) -> dict:
        """从函数签名 + docstring 自动构建 JSON Schema"""
        hints = get_type_hints(func)
        sig = inspect.signature(func)
        properties = {}
        required = []
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            ptype = hints.get(pname, str)
            properties[pname] = {"type": self._py_to_json_type(ptype)}
            if param.default is inspect.Parameter.empty:
                required.append(pname)
        return {
            "name": func.__name__,
            "description": (func.__doc__ or "").strip().split("\n")[0],
            "_category": category,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }
    
    @staticmethod
    def _py_to_json_type(py_type) -> str:
        mapping = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array"}
        return mapping.get(py_type, "string")

# 全局实例
registry = ToolRegistry()
```

### 4.2 Tool 注册示例

```python
# src/tools/data_reader.py
from src.common.tool_registry import registry

@registry.tool(category="data")
def list_experiment_runs(data_dir: str, date_filter: str = "") -> list[dict]:
    """列出所有实验运行记录。date_filter 格式: YYYY-MM-DD"""
    ...

@registry.tool(category="data")
def read_run_summary(run_dir: str) -> dict:
    """读取指定实验运行目录下的 run_summary.json"""
    ...
```

### 4.3 Agent 调用方式

```python
# Agent 发起 LLM 请求时
from src.common.tool_registry import registry

response = openai_client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=registry.get_openai_tools(categories=["data", "analysis"]),
)

# 处理 tool_call
for tool_call in response.choices[0].message.tool_calls:
    result = registry.call(tool_call.function.name, **json.loads(tool_call.function.arguments))
```

---

## 五、Agent 层设计

> **详细的多 Agent LangGraph 编排设计见 → [`langgraph_architecture.md`](langgraph_architecture.md)**
> 各 Agent 开发指南见下方链接。

### 5.1 Agent 定义

| Agent | 代号 | 绑定 Skills | LangGraph 子图 | 开发文档 |
|-------|------|------------|---------------|----------|
| **DataAnalyst** | DA | A1, A2, A3, A4, E2 | AnalystGraph | [`dev_agent_data_analyst.md`](dev_agent_data_analyst.md) |
| **ExperimentDesigner** | ED | B1, B2, B3, B4, E2 | DesignerGraph | [`dev_agent_experiment_designer.md`](dev_agent_experiment_designer.md) |
| **ExperimentSupervisor** | ES | C1, C2, C3 + 调用 DX | SupervisorGraph | [`dev_agent_experiment_supervisor.md`](dev_agent_experiment_supervisor.md) |
| **DiagnosticsExpert** | DX | D1, D2, D3, E2 | DiagnosticsGraph | [`dev_agent_diagnostics_expert.md`](dev_agent_diagnostics_expert.md) |
| **KnowledgeManager** | KM | E1, E2, E3 | KnowledgeGraph | [`dev_agent_knowledge_manager.md`](dev_agent_knowledge_manager.md) |
| **Orchestrator** | ORCH | 路由→上述5个Agent | OrchestratorGraph | [`dev_agent_orchestrator.md`](dev_agent_orchestrator.md) |

### 5.2 Orchestrator 路由逻辑

```python
# src/agents/orchestrator.py

ROUTING_PROMPT = """
用户的请求属于以下哪个类别？
1. 数据分析（查看/分析/对比/趋势）→ DataAnalyst
2. 实验设计（设计/生成/优化参数/方案）→ ExperimentDesigner  
3. 故障诊断（错误/失败/异常/维护）→ DiagnosticsExpert
4. 实验执行（运行/监控/排程/调度）→ ExperimentSupervisor
5. 知识查询（文献/理论/方法）→ DataAnalyst + RAG
6. 复合任务 → 需要多个 Agent 协作

返回 JSON: {"agents": ["DataAnalyst"], "reason": "..."}
"""
```

---

## 六、项目结构与依赖

### 6.1 目录结构

```
AutoHySeeker/
├── pyproject.toml
├── README.md
├── uv.lock
├── configs/
│   ├── settings.toml          # AutoHySeeker 自身配置
│   ├── llm_config.toml        # LLM API 配置
│   ├── rag_config.toml        # RAG 相关配置
│   └── microhyseeker.toml     # MicroHySeeker 数据/配置路径映射
├── src/
│   ├── __init__.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── data_reader.py       # 2.1 数据读取
│   │   ├── echem_analysis.py    # 2.2 电化学分析
│   │   ├── visualization.py     # 2.3 可视化
│   │   ├── experiment_builder.py # 2.4 方案构建
│   │   ├── experiment_control.py # 2.5 实验控制
│   │   ├── log_analysis.py      # 2.6 日志分析
│   │   ├── rag_tools.py         # 2.7 RAG
│   │   └── report_generator.py  # 2.8 报告
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── base.py              # Skill 基类
│   │   ├── data_analysis/
│   │   │   ├── single_experiment_analysis.py    # A1
│   │   │   ├── multi_experiment_comparison.py   # A2
│   │   │   ├── trend_tracking.py                # A3
│   │   │   └── nl_data_query.py                 # A4
│   │   ├── experiment_design/
│   │   │   ├── generate_experiment_plan.py      # B1
│   │   │   ├── optimize_parameters.py           # B2
│   │   │   ├── validate_and_review.py           # B3
│   │   │   └── replicate_literature.py          # B4
│   │   ├── experiment_execution/
│   │   │   ├── execution_monitor.py             # C1
│   │   │   ├── smart_scheduler.py               # C2
│   │   │   └── adaptive_loop.py                 # C3
│   │   ├── diagnostics/
│   │   │   ├── diagnose_failure.py              # D1
│   │   │   ├── system_health_check.py           # D2
│   │   │   └── interactive_troubleshooting.py   # D3
│   │   └── knowledge/
│   │       ├── build_knowledge_base.py          # E1
│   │       ├── knowledge_qa.py                  # E2
│   │       └── auto_archive.py                  # E3
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── data_analyst.py
│   │   ├── experiment_designer.py
│   │   ├── diagnostics_expert.py
│   │   ├── experiment_supervisor.py
│   │   └── knowledge_manager.py
│   ├── graph/                     # ← LangGraph 图定义
│   │   ├── __init__.py
│   │   ├── state.py               # 所有 State TypedDict
│   │   ├── orchestrator.py        # 顶层 Orchestrator 图
│   │   ├── analyst_graph.py       # DataAnalyst 子图
│   │   ├── designer_graph.py      # ExperimentDesigner 子图
│   │   ├── supervisor_graph.py    # ExperimentSupervisor 子图 (★C→D→C)
│   │   ├── diagnostics_graph.py   # DiagnosticsExpert 子图
│   │   └── knowledge_graph.py     # KnowledgeManager 子图
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embeddings.py        # Embedding 模型封装
│   │   ├── vector_store.py      # ChromaDB 封装
│   │   ├── chunker.py           # 文本分块策略
│   │   ├── pdf_parser.py        # PDF 解析
│   │   └── collections.py       # 集合管理
│   └── common/
│       ├── __init__.py
│       ├── config.py            # 配置加载
│       ├── llm_client.py        # LLM API 统一封装
│       ├── types.py             # 类型定义
│       └── logger.py            # 日志
├── data/
│   ├── vector_db/               # ChromaDB 持久化
│   ├── cache/                   # LLM 响应缓存
│   └── templates/               # 报告模板
├── tests/
│   ├── test_tools/
│   ├── test_skills/
│   └── test_agents/
└── scripts/
    ├── init_knowledge_base.py   # 初始化知识库
    └── batch_analyze.py         # 批量分析历史数据
```

### 6.2 pyproject.toml

```toml
[project]
name = "autohyseeker"
version = "0.1.0"
description = "AI-powered experiment assistant for MicroHySeeker"
requires-python = ">=3.11"

dependencies = [
    # === 核心 ===
    "pydantic>=2.0",
    
    # === 数据处理 ===
    "pandas>=2.0",
    "numpy>=1.24",
    "scipy>=1.11",
    
    # === 电化学分析 ===
    # "impedance>=1.7",       # EIS 拟合（可选）
    
    # === 可视化 ===
    "matplotlib>=3.7",
    
    # === LLM ===
    "openai>=1.0",             # OpenAI API (也兼容 Ollama OpenAI-compatible)
    "litellm>=1.0",            # 多 LLM 统一接口（可选）
    
    # === LangGraph 多 Agent 编排 ===
    "langgraph>=0.2",
    "langchain-core>=0.3",
    "langchain-openai>=0.3",
    
    # === RAG ===
    "chromadb>=0.4",
    "sentence-transformers>=2.2",
    "pymupdf>=1.23",           # PDF 解析
    "langchain-text-splitters>=0.0.1",
    
    # === 报告 ===
    "jinja2>=3.1",
    "python-docx>=1.0",
    
    # === 参数优化 ===
    "optuna>=3.0",
    
    # === 工具 ===
    "tomli>=2.0",
    "rich>=13.0",              # 终端美化输出
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "ruff"]
eis = ["impedance>=1.7"]
plotly = ["plotly>=5.0"]

[tool.uv]
dev-dependencies = ["pytest", "pytest-asyncio", "ruff"]
```

### 6.3 环境初始化

```bash
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
uv init
uv add pydantic pandas numpy scipy matplotlib openai chromadb sentence-transformers pymupdf langchain-text-splitters jinja2 python-docx optuna tomli rich
```

---

## 七、实施优先级与四阶段路线图

> 2026-02-23 v2 修订。以**实验闭环**为核心逻辑：先能监控和诊断（CD），再能分析数据（A），再能设计实验（BE），最后系统联调。

### 7.1 四阶段总览

```
阶段 1 — CD 构建期（基础中的基础，立刻能用）
  "实验跑完了，我能看懂发生了什么；出了问题，我知道为什么"
  
阶段 2 — 数据分析构建期
  "实验数据出来了，AI 帮我提特征、出报告、做对比"

阶段 3 — 实验设计期
  "基于已有数据和知识，AI 帮我设计下一步实验"

阶段 4 — 系统完善与联调期
  "自适应闭环、多 Agent 协作、实时监控"
```

### 7.2 Skill 优先级重排

| 阶段 | Skill | 名称 | 为什么在这个阶段 |
|------|-------|------|-----------------|
| **P1** | **D1** | 失败实验诊断 | 最痛的点：实验失败了不知道为什么 |
| **P1** | **D2** | 系统健康检查 | 设备状态一目了然，预防问题 |
| **P1** | **D3** | 交互式排错 | "泵不转了"→引导排查→解决 |
| **P1** | **C1** | 实验监控（后分析模式） | 实验结束后自动出质量报告 |
| **P1** | **C2** | 实验排程 | 多实验排列优化（不需要实时IPC） |
| **P2** | **A1** | 单次实验分析 | 完整分析报告+图表+LLM解读 |
| **P2** | **A2** | 多实验对比 | 浓度/扫速梯度对比 |
| **P2** | **A3** | 趋势追踪 | 跨天跨批次趋势 |
| **P2** | **A4** | 自然语言数据查询 | "找出峰电流最大的实验" |
| **P3** | **E1** | 知识库构建 | RAG 基础设施 |
| **P3** | **E2** | 知识问答 | 文献/手册问答 |
| **P3** | **B1** | 自然语言→方案 | "帮我设计浓度梯度CV" |
| **P3** | **B3** | 方案审查 | 生成后自动安全审查 |
| **P3** | **E3** | 自动归档 | 实验结果→知识库 |
| **P4** | **C1** | 实验监控（实时模式） | 需要 MicroHySeeker IPC |
| **P4** | **C3** | 自适应闭环 | 最高级：AI自主迭代实验 |
| **P4** | **B2** | 参数优化 | 贝叶斯优化需闭环数据 |
| **P4** | **B4** | 文献方法复现 | 依赖文献自动化管线 |

---

## 八、实施路线图

### Phase 1 — CD 构建期：监控与诊断基础（3-4 周）

> **目标**：跑完实验后，AI 能告诉你"发生了什么、为什么失败、设备状况如何"。
> **特点**：只依赖文件读取，不需要实时 IPC，现有 `data/` 目录数据立刻可用。

```
Week 1 — 基础设施 + 数据读取
  ☐ 项目初始化（uv init, 目录结构, configs/）
  ☐ common/config.py — 配置加载（读 MicroHySeeker 的 data/config/ 路径）
  ☐ common/llm_client.py — LLM 统一调用封装（OpenAI/Ollama）
  ☐ common/tool_registry.py — ToolRegistry + Function Calling
  ☐ common/types.py — 共享类型定义（RunSummary, LogEntry, EchemData...）
  ☐ tools/data_reader.py — 全部 8 个 Tool 函数
      list_experiment_runs, read_run_summary, read_experiment_plan,
      read_echem_csv, read_pump_operations, read_run_log,
      read_system_config, list_echem_files
  ☐ 单元测试：用 data/2026-02-13/ 的真实数据验证所有 reader

Week 2 — 日志分析 + 诊断工具
  ☐ tools/log_analysis.py — 日志解析/错误分类/泵异常检测
      parse_run_log, extract_errors, extract_warnings,
      classify_error, extract_timing_info,
      detect_pump_anomalies, check_calibration_drift
  ☐ tools/visualization.py — 基础图表（CV/LSV/i-t 曲线，泵时序图）
  ☐ tools/report_generator.py — Markdown 报告模板
  ☐ skills/base.py — Skill 基类 + SkillResult
  ☐ 单元测试：用失败实验数据测试 log_analysis

Week 3 — D1/D2 核心 Skill
  ☐ Skill D1: diagnose_failed_experiment
      读 run_summary → 定位失败步骤 → 读 run_log 上下文
      → 错误分类 → 泵操作异常检测 → [LLM] 根因分析+建议
  ☐ Skill D2: system_health_check
      读近期所有实验的 run_summary/pump_ops → 统计异常频率
      → 校准漂移检查 → [LLM] 综合健康评分+维护建议
  ☐ DiagnosticsExpert Agent — System Prompt + D1/D2 绑定
  ☐ 端到端测试：用真实失败实验跑 D1

Week 4 — D3/C1(后分析)/C2
  ☐ Skill D3: interactive_troubleshooting（多轮对话排错）
  ☐ Skill C1: execution_monitor（后分析模式）
      实验完成后扫描 run_dir → 每步质量评分 → 汇总报告
  ☐ Skill C2: smart_scheduler（离线排程）
      输入实验列表 → 估算耗时/试剂 → 优化顺序 → 输出排程
  ☐ ExperimentSupervisor Agent（基础版）
  ☐ 简单 CLI 入口：python -m autohyseeker.cli diagnose <run_dir>
```

**Phase 1 交付物**：
- `diagnose <run_dir>` → 失败原因 + 解决建议
- `health-check` → 系统健康评分
- `review <run_dir>` → 实验质量报告
- `schedule <experiments>` → 优化排程
- 所有 Tool 100% 单测覆盖

---

### Phase 2 — 数据分析构建期（2-3 周）

> **目标**：AI 完整分析电化学数据，出图、提指标、做对比。
> **前置**：Phase 1 的 data_reader/visualization/report_generator 已就绪。

```
Week 5 — 电化学分析工具 + A1
  ☐ tools/echem_analysis.py — 全部分析 Tool
      detect_cv_peaks, calculate_tafel_slope, fit_eis_circuit,
      assess_data_quality, detect_anomalies, calculate_charge,
      extract_steady_state
  ☐ tools/visualization.py — 补全（EIS Nyquist/Bode, Tafel, 趋势图, 对比图）
  ☐ Skill A1: single_experiment_analysis
      读数据 → 逐步骤分析电化学特征 → 质量评分 → 出图 → [LLM] 解读
  ☐ 单元测试：CV/LSV/EIS/i-t/OCPT 各技术的特征提取

Week 6 — A2/A3/A4 + DataAnalyst Agent
  ☐ Skill A2: multi_experiment_comparison
  ☐ Skill A3: trend_tracking
  ☐ Skill A4: natural_language_data_query
  ☐ DataAnalyst Agent — System Prompt + A1-A4 绑定
  ☐ CLI: python -m autohyseeker.cli analyze <run_dir>
  ☐ CLI: python -m autohyseeker.cli compare <run_dir1> <run_dir2> ...
```

**Phase 2 交付物**：
- `analyze <run_dir>` → 完整分析报告（图表+指标+LLM解读）
- `compare <dirs>` → 多实验对比表+图
- `trend --metric peak_current --days 7` → 趋势图+解读
- `ask "上周哪个实验峰电流最大？"` → 自然语言查询

---

### Phase 3 — 实验设计期（2-3 周）

> **目标**：AI 帮设计实验方案，结合知识库审查参数合理性。
> **前置**：A1 的分析能力为设计提供数据支撑；RAG 为设计提供知识支撑。

```
Week 7 — RAG 基础设施
  ☐ rag/embeddings.py — Embedding 模型封装（BGE-M3 本地 / OpenAI）
  ☐ rag/vector_store.py — ChromaDB 封装
  ☐ rag/chunker.py — 文本分块策略
  ☐ rag/pdf_parser.py — PDF 解析（pymupdf）
  ☐ tools/rag_tools.py — 全部 RAG Tool
  ☐ Skill E1: build_knowledge_base
  ☐ Skill E2: knowledge_qa
  ☐ 初始化知识库：灌入 CHI 660F 手册 + 电化学基础知识

Week 8 — 实验方案构建 + B1/B3
  ☐ tools/experiment_builder.py — 全部 step builder + 校验
  ☐ Skill B1: generate_experiment_plan（NL→实验方案JSON）
  ☐ Skill B3: validate_and_review_plan（方案审查）
  ☐ Skill E3: auto_archive_experiment（实验结果归档到知识库）
  ☐ ExperimentDesigner Agent
  ☐ CLI: python -m autohyseeker.cli design "做浓度梯度CV"

Week 9（可选）
  ☐ Orchestrator Agent — 统一入口，意图路由到 DataAnalyst/Designer/Diagnostics
  ☐ 简单 Web/Chat UI（Gradio 或 Streamlit）
```

**Phase 3 交付物**：
- `design "..."` → 完整实验方案 JSON + 解释
- `review <experiment.json>` → 安全审查 + 建议
- `ask-kb "CV扫速一般用多少？"` → RAG 知识问答
- `archive <run_dir>` → 归档到知识库

---

### Phase 4 — 系统完善与联调期（后续迭代）

> **目标**：实时监控、自适应闭环、多 Agent 协作。
> **前置**：需要 MicroHySeeker 暴露 IPC/WebSocket API。

```
  ☐ MicroHySeeker 侧：暴露 WebSocket/HTTP API
      get_engine_status, load_experiment, start/stop/pause,
      subscribe_events (实时数据流)
  ☐ tools/experiment_control.py — 实时版
  ☐ Skill C1: execution_monitor（实时模式 — 边跑边评估）
  ☐ Skill C3: adaptive_experiment_loop（自主实验闭环）
  ☐ Skill B2: optimize_parameters（贝叶斯优化）
  ☐ Skill B4: replicate_literature_method（文献→方案）
  ☐ Chat UI 集成到 MicroHySeeker（PySide6 panel 或 独立 Web）
  ☐ 实验知识图谱（可选）
```

---

## 九、Skill ↔ Tool ↔ 外部库 关系总表

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
                               rag_tools.semantic_search       chromadb
                               LLM (NL→方案)                   openai

B2 optimize_parameters         data_reader.*                   optuna/botorch
                               echem_analysis.*                scipy.optimize
                               LLM (解释)                      openai

B3 validate_and_review         experiment_builder.validate     jsonschema
                               rag_tools.semantic_search       chromadb
                               data_reader.read_system_config
                               LLM (审查)                      openai

B4 replicate_literature        rag_tools.ingest_pdf            pymupdf
                               experiment_builder.*            jsonschema
                               data_reader.read_system_config
                               LLM (方法提取)                  openai

C1 execution_monitor           experiment_control.*            (IPC依赖)
                               echem_analysis.*                scipy
                               LLM (异常解读)                  openai

C2 smart_scheduler             experiment_builder.validate     
                               data_reader.read_system_config
                               LLM (优化建议)                  openai

C3 adaptive_loop               所有上述 Skills (meta-skill)    optuna
                               LLM (决策)                      openai

D1 diagnose_failure            data_reader.*                   pandas, re
                               log_analysis.*
                               rag_tools.semantic_search       chromadb
                               LLM (根因推理)                  openai

D2 system_health_check         data_reader.*                   pandas
                               log_analysis.*
                               LLM (评估)                      openai

D3 interactive_troubleshooting experiment_control.*            (IPC依赖)
                               rag_tools.semantic_search       chromadb
                               log_analysis.*
                               LLM (对话式排查)                openai

E1 build_knowledge_base        rag_tools.ingest_*              pymupdf
                               LLM (摘要生成)                  chromadb
                                                               sentence-transformers

E2 knowledge_qa                rag_tools.semantic_search       chromadb
                               LLM (RAG生成)                   openai

E3 auto_archive                data_reader.*                   chromadb
                               echem_analysis.*
                               rag_tools.ingest_experiment
```

---

## 十、配置示例

### configs/microhyseeker.toml

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
# websocket_url = "ws://localhost:9876"  # 后续启用
```

### configs/llm_config.toml

```toml
[default]
provider = "openai"     # "openai" | "ollama" | "azure"
model = "gpt-4o"
temperature = 0.1
max_tokens = 4096

[openai]
api_key_env = "OPENAI_API_KEY"  # 从环境变量读取
base_url = "https://api.openai.com/v1"

[ollama]
base_url = "http://localhost:11434/v1"
model = "qwen2.5:72b"

[embedding]
provider = "local"       # "local" | "openai"
model = "BAAI/bge-m3"   # 本地 embedding 模型
```

### configs/rag_config.toml

```toml
[vector_store]
type = "chromadb"
persist_dir = "./data/vector_db"

[chunking]
chunk_size = 1000
chunk_overlap = 200
separators = ["\n\n", "\n", ". ", " "]

[collections]
literature = { description = "学术文献 PDF", embedding_model = "BAAI/bge-m3" }
experiment_archive = { description = "历史实验结果与经验", embedding_model = "BAAI/bge-m3" }
instrument_manual = { description = "仪器手册", embedding_model = "BAAI/bge-m3" }
error_solutions = { description = "错误→解决方案映射", embedding_model = "BAAI/bge-m3" }
domain_knowledge = { description = "电化学领域知识", embedding_model = "BAAI/bge-m3" }
```

---

*此文档可直接作为开发执行依据。每个 Tool / Skill 的定义已精确到输入/输出/内部流程/依赖库，可逐一实现。*

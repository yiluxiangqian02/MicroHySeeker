# MicroHySeeker 数据管理分析平台 + AI Agent 方案

## 一、数据管理分析平台 — 现有实现

### 1.1 数据浏览器（已实现）

菜单入口：文件 → 数据浏览器

功能：
- 按日期/状态筛选运行记录
- 查看运行摘要（耗时、步骤结果、错误/警告）
- 查看运行日志（毫秒级时间戳）
- 预览电化学数据 CSV / 图表 PNG
- 查看实验方案 JSON
- 打开数据目录 / 导出 / 删除

### 1.2 数据目录结构

```
data/
  2026-02-13/
    2026-02-13_19-51-47_CV扫描/
      experiment.json       ← 实验方案
      run_summary.json      ← 运行结果
      run_log.log           ← 详细日志
      echem/
        step_1_CV.csv       ← 原始数据
        step_1_CV.png       ← 图表截图
      pump/
        pump_operations.csv ← 泵操作记录
```

---

## 二、AI Agent / Workflow 集成方案

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                MicroHySeeker 主程序                       │
│  ┌────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐ │
│  │实验编辑│ │实验运行  │ │数据浏览器 │ │ AI 助手面板  │ │
│  └────────┘ └──────────┘ └───────────┘ └──────┬───────┘ │
│                                                │         │
│                                         ┌──────▼───────┐ │
│                                         │  AI Agent    │ │
│                                         │  Service     │ │
│                                         └──────┬───────┘ │
└────────────────────────────────────────────────┼─────────┘
                                                 │
                    ┌────────────────────────────┼──────────────┐
                    │    本地 / 远程 LLM API     │              │
                    │                            ▼              │
                    │  ┌──────────────────────────────────────┐ │
                    │  │ Tools / Function Calling             │ │
                    │  │  - read_experiment_data()            │ │
                    │  │  - query_run_history()               │ │
                    │  │  - analyze_echem_csv()               │ │
                    │  │  - compare_experiments()             │ │
                    │  │  - plot_echem_data()                 │ │
                    │  │  - suggest_parameters()              │ │
                    │  │  - generate_report()                 │ │
                    │  └──────────────────────────────────────┘ │
                    └──────────────────────────────────────────┘
```

### 2.2 可用 AI 优化的场景

#### 场景 A：实验数据自动分析

| 功能 | 描述 | 实现难度 |
|------|------|----------|
| CV 峰值自动识别 | 自动检测氧化/还原峰电位、峰电流 | ⭐⭐ |
| 电化学数据质量评估 | 判断数据噪声、基线漂移、异常点 | ⭐⭐ |
| 多次实验对比分析 | 自动对比不同条件下的电化学响应差异 | ⭐⭐⭐ |
| 趋势分析 | 跨天/跨批次追踪性能指标变化趋势 | ⭐⭐⭐ |

#### 场景 B：实验设计辅助

| 功能 | 描述 | 实现难度 |
|------|------|----------|
| 参数推荐 | 根据历史数据推荐最优实验参数 | ⭐⭐⭐ |
| 浓度计算验证 | 验证配液参数数学正确性 | ⭐ |
| 实验方案生成 | 根据自然语言描述生成实验步骤 JSON | ⭐⭐⭐ |
| 组合实验规划 | 推荐浓度梯度/电位扫描范围 | ⭐⭐⭐ |

#### 场景 C：运维诊断

| 功能 | 描述 | 实现难度 |
|------|------|----------|
| 故障日志分析 | 分析 run_log.log 诊断失败原因 | ⭐⭐ |
| 泵操作异常检测 | 分析 pump_operations.csv 发现异常模式 | ⭐⭐ |
| 校准漂移监测 | 追踪泵校准精度随时间变化 | ⭐⭐ |

#### 场景 D：报告生成

| 功能 | 描述 | 实现难度 |
|------|------|----------|
| 实验日报 | 自动汇总当天所有实验结果 | ⭐⭐ |
| 数据导出报告 | 生成带图表的 PDF/Word 报告 | ⭐⭐⭐ |
| 实验记录归档 | 按项目/课题组织实验记录 | ⭐⭐ |

### 2.3 推荐实现路线

#### 第一阶段：本地分析工具（无需 LLM）
- CV 峰值自动检测（scipy.signal.find_peaks）
- 多实验数据对比图表
- 实验日报自动生成（模板化）
- 数据导出为 Excel/PDF

#### 第二阶段：LLM 集成 — AI 助手面板
- 在主窗口右侧或独立窗口添加聊天面板
- 接入 OpenAI / 本地 Ollama API
- 提供 Function Calling Tools：
  - `read_experiment(run_dir)` → 读取实验数据
  - `list_experiments(date, status)` → 查询实验列表
  - `analyze_cv(csv_path)` → 分析 CV 数据
  - `compare_runs(run_dirs)` → 对比多次实验
  - `generate_report(run_dirs, format)` → 生成报告

#### 第三阶段：自动化 Workflow
- 基于 LangChain / AutoGen 构建 Agent Chain
- 支持复杂指令：
  - "分析今天所有 CV 实验的峰电流变化趋势"
  - "对比 0.1M 和 0.5M Fe 的 CV 响应差异"
  - "生成本周实验总结报告"

### 2.4 技术选型建议

| 组件 | 推荐方案 | 备选 |
|------|----------|------|
| LLM API | OpenAI GPT-4o | 本地 Ollama + Qwen2.5 |
| Agent 框架 | LangChain | 自定义 Function Calling |
| 数据分析 | pandas + scipy | numpy |
| 图表 | matplotlib | plotly |
| 报告生成 | python-docx + matplotlib | Jinja2 + HTML |
| 向量数据库 | ChromaDB (实验语义检索) | FAISS |

### 2.5 AI 助手面板 UI 设计

```
┌─────────────────────────────────────┐
│  🤖 AI 实验助手                      │
├─────────────────────────────────────┤
│                                     │
│  AI: 你好，我可以帮你分析实验数据、   │
│      推荐参数、生成报告。            │
│                                     │
│  用户：分析今天第一个 CV 实验的峰值   │
│                                     │
│  AI: 已读取 CV 数据 (3500 点)        │
│  📊 氧化峰: E=0.42V, I=15.2μA      │
│  📊 还原峰: E=0.28V, I=-12.8μA     │
│  ΔE = 0.14V (准可逆过程)            │
│  峰值比 |Ipa/Ipc| = 1.19            │
│  建议: 增大扫描速率可提高信号强度    │
│                                     │
├─────────────────────────────────────┤
│  [输入消息...]              [发送]  │
└─────────────────────────────────────┘
```

### 2.6 实现优先级

1. **🟢 立即可做**：数据浏览器（已完成）
2. **🟢 下一步**：CV 峰值自动检测 + matplotlib 对比图
3. **🟡 中期**：AI 助手面板 + OpenAI Function Calling
4. **🔴 长期**：自动化 Workflow + 实验方案 AI 生成

---

## 三、快速启动：CV 分析工具 API 设计

```python
# 未来实现参考 — src/services/echem_analyzer.py

class EChemAnalyzer:
    """电化学数据分析工具"""
    
    @staticmethod
    def detect_cv_peaks(csv_path: str) -> dict:
        """检测 CV 氧化/还原峰
        Returns: {
            "oxidation_peak": {"potential": 0.42, "current": 15.2e-6},
            "reduction_peak": {"potential": 0.28, "current": -12.8e-6},
            "delta_e": 0.14,
            "peak_ratio": 1.19,
            "reversibility": "quasi-reversible"
        }
        """
    
    @staticmethod
    def compare_cv_runs(csv_paths: List[str]) -> dict:
        """对比多次 CV 实验"""
    
    @staticmethod  
    def generate_daily_report(date: str, data_dir: str) -> str:
        """生成当天实验日报 (Markdown)"""
```

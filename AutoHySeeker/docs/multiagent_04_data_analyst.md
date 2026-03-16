# 04 数据分析 Agent (Data Analyst)

## 1. 定位

**数据分析 Agent 是闭环优化中的"评审官"。**

它接收实验完成后的电化学数据（CV、LSV、EIS），提取关键性能指标
（过电位、电流密度、Tafel 斜率等），并返回结构化分析结果给 Orchestrator
用于优化决策。

类比：它是实验室的 **分析化学家**，处理原始数据并生成可操作的洞察。

### 核心能力
- 解析 CV/LSV/EIS 原始数据文件（CHI 格式 CSV）
- 提取 HER 关键指标（overpotential @ 10 mA/cm², Tafel slope, ECSA 等）
- 跨实验结果比较
- 数据质量评估（噪声、漂移、异常信号）
- 生成结构化 JSON 结果供 Orchestrator 使用

---

## 2. 职责范围

| 职责 | 描述 | 优先级 |
|------|------|--------|
| **指标提取** | 从 CV/LSV 提取 overpotential、current density | P0 |
| **结果结构化** | 输出标准化 JSON 供优化循环使用 | P0 |
| **数据质量评估** | 判断数据是否可靠，是否需要重做 | P0 |
| **趋势分析** | 对比多轮实验结果，识别配比→性能趋势 | P1 |
| **可视化** | 生成 CV 曲线、Tafel 图、优化进度图 | P2 |
| **EIS 分析** | 阻抗谱解析（Nyquist、Bode） | P2 |

### 不负责的工作
- ❌ 不设计实验（Designer 的工作）
- ❌ 不执行实验（Executor 的工作）
- ❌ 不做优化决策（Orchestrator 的工作）

---

## 3. 输入 / 输出

### 输入（来自 Orchestrator 的任务）
```python
{
    "action": "analyze_experiment",
    "run_id": "20260315_154200_HER_Fe6Co25Ni15",
    "data_path": "data/2026-03-15/20260315_154200_HER_Fe6Co25Ni15/",
    "params": {"Fe": 0.6, "Co": 0.25, "Ni": 0.15},
    "target_metric": "overpotential",
    "analysis_type": "single",     # "single" | "compare" | "trend"
    "compare_with": []             # 对比分析时使用
}
```

### 输出
```python
{
    "status": "analyzed",
    "run_id": "20260315_154200_HER_Fe6Co25Ni15",
    "metrics": {
        "overpotential_mV": 182.5,         # 过电位 (@ 10 mA/cm²)
        "current_density_mA_cm2": 15.3,    # 电流密度 (@ -0.3V vs RHE)
        "tafel_slope_mV_dec": 68.2,        # Tafel 斜率
        "onset_potential_V": -0.15,        # 起始电位
        "ecsa_cm2": 12.8,                  # 电化学活性面积
    },
    "data_quality": {
        "score": 0.92,                     # 0-1 数据质量评分
        "issues": [],                      # 质量问题列表
        "reliable": true                   # 是否可靠
    },
    "interpretation": "LLM 生成的分析解读文本",
    "comparison": {                        # 可选：与历史最优对比
        "vs_best": {
            "overpotential_change_mV": -12.5,  # 负值=改善
            "improvement_pct": 6.4
        }
    }
}
```

---

## 4. 工具权限

| 工具 | 权限 | 用途 |
|------|------|------|
| `read_cv_csv()` | ✅ | 读取 CV 数据 |
| `read_eis_csv()` | ✅ | 读取 EIS 数据 |
| `read_experiment_dir()` | ✅ | 读取实验目录 |
| `load_run_echem_files()` | ✅ | 批量加载电化学文件 |
| `read_run_metadata()` | ✅ | 读取实验元数据 |
| `analyze_cv()` | ✅ | CV 分析 |
| `analyze_eis()` | ✅ | EIS 分析 |
| `analyze_lsv()` | ✅ | LSV 分析 |
| `plot_cv_curve()` | ✅ | 可视化 CV |
| `plot_multi_cv_overlay()` | ✅ | 多曲线叠加 |
| `generate_run_report()` | ✅ | 生成报告 |
| `retrieve_knowledge()` | ✅ | 查询参考文献 |
| `list_recent_experiments()` | ✅ | 查看近期实验 |
| `get_run_detail()` | ✅ | 获取实验详情 |

---

## 5. 当前实现状态

### 已有代码

| 文件 | 行数 | 状态 | 说明 |
|------|------|------|------|
| `agents/data_analyst.py` | ~18 | ⚠️ Stub | 仅有类定义 + system prompt |
| `tools/echem_analysis.py` | ~300 | ✅ 完整 | analyze_cv, analyze_eis, analyze_lsv |
| `tools/echem_reader.py` | ~200 | ✅ 完整 | read_cv_csv, read_eis_csv |
| `tools/data_reader.py` | ~150 | ✅ 完整 | 通用数据读取 |
| `tools/visualization.py` | ~200 | ✅ 完整 | 绘图工具 |
| `skills/single_experiment_analysis.py` | ~100 | ✅ 完整 | 单实验分析技能 |
| `skills/suggest_next_experiment.py` | ~80 | ✅ 完整 | 下一实验建议 |

### 关键问题

1. **Agent 本身是 stub**：只有 system prompt，没有结构化的分析方法
2. **工具和技能丰富但未绑定**：tools 和 skills 已实现但 Agent 没有调用逻辑
3. **缺少标准化输出**：工具返回原始数据，缺少面向优化循环的结构化指标

---

## 6. 需要修改的内容

### 6.1 充实 `agents/data_analyst.py`

```python
class DataAnalystAgent(BaseAgent):
    """数据分析 Agent — 电化学数据分析与指标提取"""
    
    EXTRACTABLE_METRICS = [
        "overpotential_mV",
        "current_density_mA_cm2",
        "tafel_slope_mV_dec",
        "onset_potential_V",
        "ecsa_cm2",
    ]
    
    async def analyze_single(self, task: dict) -> dict:
        """分析单次实验结果，提取关键指标。"""
        run_id = task["run_id"]
        data_path = task.get("data_path")
        
        # 1. 加载数据
        echem_data = self._load_echem_data(run_id, data_path)
        
        # 2. 提取指标（工具层）
        metrics = self._extract_metrics(echem_data)
        
        # 3. 评估数据质量
        quality = self._assess_quality(echem_data, metrics)
        
        # 4. LLM 解读
        interpretation = await self._interpret(metrics, quality, task)
        
        return {
            "status": "analyzed",
            "run_id": run_id,
            "metrics": metrics,
            "data_quality": quality,
            "interpretation": interpretation,
        }
    
    async def compare_experiments(self, task: dict) -> dict:
        """对比多次实验结果。"""
        current_id = task["run_id"]
        compare_ids = task.get("compare_with", [])
        
        results = []
        for rid in [current_id] + compare_ids:
            data = self._load_echem_data(rid)
            metrics = self._extract_metrics(data)
            results.append({"run_id": rid, "metrics": metrics})
        
        # LLM 比较分析
        comparison = await self._compare_analysis(results, task)
        
        return {
            "status": "compared",
            "results": results,
            "comparison": comparison,
        }
    
    def _extract_metrics(self, echem_data: dict) -> dict:
        """从电化学数据中提取 HER 关键指标。"""
        from tools.echem_analysis import analyze_cv, analyze_lsv
        
        metrics = {}
        
        # LSV 分析 → overpotential, onset potential
        if "lsv" in echem_data:
            lsv_result = analyze_lsv(echem_data["lsv"])
            metrics["overpotential_mV"] = lsv_result.get("overpotential_10mA")
            metrics["onset_potential_V"] = lsv_result.get("onset_potential")
            metrics["tafel_slope_mV_dec"] = lsv_result.get("tafel_slope")
        
        # CV 分析 → ECSA, current density
        if "cv" in echem_data:
            cv_result = analyze_cv(echem_data["cv"])
            metrics["ecsa_cm2"] = cv_result.get("ecsa")
            metrics["current_density_mA_cm2"] = cv_result.get("peak_current_density")
        
        return metrics
    
    def _assess_quality(self, echem_data: dict, metrics: dict) -> dict:
        """评估数据质量。"""
        issues = []
        score = 1.0
        
        # 检查指标完整性
        for key in self.EXTRACTABLE_METRICS:
            if metrics.get(key) is None:
                issues.append(f"缺少指标: {key}")
                score -= 0.1
        
        # 检查异常值
        op = metrics.get("overpotential_mV")
        if op is not None and (op < 0 or op > 1000):
            issues.append(f"过电位异常: {op} mV")
            score -= 0.3
        
        return {
            "score": max(0, round(score, 2)),
            "issues": issues,
            "reliable": score >= 0.6,
        }
```

---

## 7. 面向优化循环的输出标准

**Orchestrator 期望从 Analyst 收到的标准输出：**

```python
{
    "metrics": {
        # 必须包含 target_metric 对应的值
        "<target_metric>": float,  # e.g., "overpotential_mV": 182.5
    },
    "data_quality": {
        "reliable": bool,  # Orchestrator 用此判断是否需要重做
    }
}
```

Orchestrator 的决策逻辑：
- `reliable == false` → 标记实验无效，可能重试
- `reliable == true` → 将 metrics 加入 experiment_history，传给 Designer

---

## 8. 与其他 Agent 的交互

```
Orchestrator → Analyst:
    "分析实验 run_id=xxx 的数据"
    附带: run_id, data_path, target_metric, params

Analyst → Orchestrator:
    返回: {metrics, data_quality, interpretation}

Analyst → Knowledge Manager:  (可选)
    "查询 Fe-Co-Ni 催化剂的典型 overpotential 范围"
    用于: 判断数据是否在合理范围
```

---

## 9. 执行计划

| 步骤 | 任务 | 涉及文件 | 依赖 |
|------|------|---------|------|
| 1 | 充实 data_analyst.py，添加 analyze_single 方法 | `agents/data_analyst.py` | 无 |
| 2 | 实现 _extract_metrics（调用 echem_analysis 工具） | `agents/data_analyst.py` | 步骤 1 |
| 3 | 实现 _assess_quality（数据质量评估） | `agents/data_analyst.py` | 步骤 1 |
| 4 | 实现 compare_experiments（跨实验对比） | `agents/data_analyst.py` | 步骤 1 |
| 5 | 标准化输出格式（与 Orchestrator 对齐） | `agents/data_analyst.py` | 步骤 1 |
| 6 | 更新 System Prompt | `agents/data_analyst.py` | 步骤 1 |
| 7 | 添加单元测试 | `tests/test_analyst.py` | 步骤 1-4 |

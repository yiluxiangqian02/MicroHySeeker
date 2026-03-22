# 02 实验设计 Agent (Experiment Designer)

## 1. 定位

**实验设计 Agent 是优化循环中的参数生成器。**

它接收 Orchestrator 的任务（包含搜索空间、历史结果、约束条件），
输出 **下一组实验参数**（元素配比），并可选地解释其选择策略。

类比：它是实验室中的 **实验方案设计师**，根据过去的数据决定下一步探索什么配比。

### 核心能力
- 根据搜索空间和约束生成合法的元素配比
- 利用历史实验结果指导参数选择（贝叶斯优化/LLM 推理）
- 输出标准化的 MicroHySeeker 模板覆盖参数
- 验证参数合法性（RPM ≤ 300、比例和 = 1 等）

---

## 2. 职责范围

| 职责 | 描述 | 优先级 |
|------|------|--------|
| **参数生成** | 生成 target_concentrations（元素配比） | P0 |
| **策略选择** | 选择探索/利用策略（exploration vs exploitation） | P0 |
| **参数验证** | 验证生成的参数满足约束 | P0 |
| **模板适配** | 将参数转换为 template step_overrides 格式 | P0 |
| **初始设计** | 生成初始实验网格（第一轮无历史数据时） | P1 |
| **文献参考** | 查询知识库获取参考配比范围 | P2 |

### 不负责的工作
- ❌ 不执行实验（Executor 的工作）
- ❌ 不分析结果（Analyst 的工作）
- ❌ 不决定何时停止优化（Orchestrator 的工作）

---

## 3. 输入 / 输出

### 输入（来自 Orchestrator 的任务）
```python
{
    "action": "design_next_experiment",
    "search_space": {
        "Fe": {"min": 0.05, "max": 0.8},
        "Co": {"min": 0.05, "max": 0.8},
        "Ni": {"min": 0.05, "max": 0.8}
    },
    "constraints": {
        "sum_equals": 1.0,
        "min_component": 0.05
    },
    "history": [
        {
            "round": 1,
            "params": {"Fe": 0.33, "Co": 0.33, "Ni": 0.34},
            "result": {"overpotential_mV": 245.0, "j_mA_cm2": 8.5}
        },
        {
            "round": 2,
            "params": {"Fe": 0.5, "Co": 0.3, "Ni": 0.2},
            "result": {"overpotential_mV": 210.0, "j_mA_cm2": 12.1}
        }
    ],
    "target_metric": "overpotential",
    "optimization_direction": "minimize",
    "template_id": "tpl_her_standard",
    "total_volume_ul": 1000,
    "hint": "上一轮 Fe 增加有改善，建议继续探索高 Fe 区间"  # Orchestrator 的方向提示
}
```

### 输出
```python
{
    "params": {
        "Fe": 0.6,
        "Co": 0.25,
        "Ni": 0.15
    },
    "step_overrides": {
        "0": {
            "prep_sol_params": {
                "target_concentrations": {
                    "Fe": 0.6,
                    "Co": 0.25,
                    "Ni": 0.15
                },
                "total_volume_ul": 1000
            }
        }
    },
    "strategy": "bayesian_exploitation",
    "confidence": 0.72,
    "reasoning": "基于贝叶斯优化后验分布，Fe=0.6 区域的 expected improvement 最高。 "
                 "前两轮数据显示 Fe 增加与 overpotential 降低正相关。",
    "expected_improvement": 15.2  # 预期改善 mV
}
```

---

## 4. 工具权限

| 工具 | 权限 | 用途 |
|------|------|------|
| `list_templates()` | ✅ | 查看可用模板 |
| `get_template(id)` | ✅ | 获取模板详情 |
| `validate_experiment(steps)` | ✅ | 验证参数合法性 |
| `get_system_config()` | ✅ | 查询通道配置 |
| `get_dilution_channels()` | ✅ | 查询配液通道→元素映射 |
| `retrieve_knowledge(query)` | ✅ | 查询文献参考配比 |
| `generate_param_grid()` | ✅ | 生成初始参数网格 |
| `build_experiment_plan()` | ✅ | 构建实验计划 |

---

## 5. 当前实现状态

### 已有代码

| 文件 | 状态 | 说明 |
|------|------|------|
| `agents/exp_designer.py` | ✅ 完整 | 三阶段策略（文献引导→LLM引导→ML混合），含约束处理和 step_overrides 格式化 |
| `skills/knowledge_query_skill.py` | ✅ 完整 | 文献检索接口，Designer 第 0 轮使用 |
| `ml/performance_predictor.py` | ✅ 完整 | ML 预测模型，≥5 轮时启用 |
| `tools/experiment_builder.py` | ✅ 完整 | build_experiment_plan, generate_param_grid |
| `skills/generate_experiment_plan.py` | ✅ 完整 | 高级技能封装 |
| `skills/suggest_next_experiment.py` | ✅ 完整 | 下一实验建议 |

### 关键问题

> **✅ 以下问题已全部在 Phase 1 (P1-12) 中解决（2026-03-19）：**

1. ~~**Agent 只有 system prompt**~~：已实现完整的三阶段策略和参数生成逻辑
2. ~~**缺少优化算法集成**~~：已集成 PerformancePredictor（随机森林/高斯过程/轻量 surrogate）
3. ~~**缺少约束处理**~~：已实现 `_apply_constraints()`（归一化、最小值截断）
4. ~~**输出格式不标准**~~：已实现标准 `step_overrides` 格式输出

---

## 6. 已完成的修改（参考实现）

> 以下修改已在 Phase 1 (P1-12) 中完成，此处保留作为实现参考。

### 6.1 充实 `agents/exp_designer.py`

```python
class ExperimentDesignerAgent(BaseAgent):
    """实验设计 Agent — 元素配比参数生成器"""
    
    def __init__(self):
        super().__init__(
            name="experiment_designer",
            system_prompt=DESIGNER_SYSTEM_PROMPT,
        )
        self._optimizer = None  # 可选的 Optuna 优化器
    
    async def design_experiment(self, task: dict) -> dict:
        """生成下一组实验参数。
        
        策略选择：
        1. 无历史数据 → 初始采样 (Latin Hypercube / Grid)
        2. 有少量数据 (< 5轮) → LLM 推理 + 随机探索
        3. 有足够数据 (≥ 5轮) → 贝叶斯优化 (Optuna) + LLM 校验
        """
        history = task.get("history", [])
        
        if len(history) == 0:
            return await self._initial_design(task)
        elif len(history) < 5:
            return await self._llm_guided_design(task)
        else:
            return await self._bayesian_design(task)
    
    async def _initial_design(self, task: dict) -> dict:
        """无历史数据时的初始设计：等间距采样或 LLM 建议。"""
        search_space = task["search_space"]
        constraints = task.get("constraints", {})
        
        # 方案A: 均匀分布的初始配比
        # 方案B: 查询文献获取推荐起点
        knowledge_hint = await self._query_literature(task)
        
        prompt = f"""基于以下搜索空间设计第一组实验参数：
搜索空间: {search_space}
约束: {constraints}
文献参考: {knowledge_hint}
目标: {task['target_metric']} ({task['optimization_direction']})

请输出 JSON 格式的元素配比。"""
        
        result = await self.invoke(prompt)
        params = self._parse_params(result)
        return self._format_output(params, task, "initial_sampling")
    
    async def _llm_guided_design(self, task: dict) -> dict:
        """少量数据时的 LLM 指导设计。"""
        prompt = self._build_design_prompt(task)
        result = await self.invoke(prompt)
        params = self._parse_params(result)
        
        # 验证约束
        params = self._apply_constraints(params, task["constraints"])
        
        return self._format_output(params, task, "llm_guided")
    
    async def _bayesian_design(self, task: dict) -> dict:
        """使用贝叶斯优化生成参数（Optuna 后端）。"""
        try:
            import optuna
            params = self._optuna_suggest(task)
        except ImportError:
            # 回退到 LLM
            return await self._llm_guided_design(task)
        
        # 用 LLM 校验和解释
        explanation = await self._explain_choice(params, task)
        
        return self._format_output(params, task, "bayesian", explanation)
    
    def _apply_constraints(self, params: dict, constraints: dict) -> dict:
        """应用约束条件（如比例和 = 1）。"""
        if constraints.get("sum_equals"):
            target_sum = constraints["sum_equals"]
            current_sum = sum(params.values())
            if current_sum > 0:
                factor = target_sum / current_sum
                params = {k: round(v * factor, 4) for k, v in params.items()}
        
        if constraints.get("min_component"):
            min_val = constraints["min_component"]
            for k, v in params.items():
                if v < min_val:
                    params[k] = min_val
            # 重新归一化
            params = self._apply_constraints(params, {"sum_equals": constraints.get("sum_equals", 1.0)})
        
        return params
    
    def _format_output(self, params: dict, task: dict, strategy: str, reasoning: str = "") -> dict:
        """将参数格式化为标准 step_overrides。"""
        template_id = task.get("template_id")
        total_vol = task.get("total_volume_ul", 1000)
        prep_step_idx = task.get("prep_step_index", 0)
        
        return {
            "params": params,
            "step_overrides": {
                str(prep_step_idx): {
                    "prep_sol_params": {
                        "target_concentrations": params,
                        "total_volume_ul": total_vol,
                    }
                }
            },
            "strategy": strategy,
            "reasoning": reasoning,
            "template_id": template_id,
        }
```

---

## 7. 已完成的新增内容（参考实现）

> 以下新增已在 Phase 1 中完成，此处保留作为实现参考。

### 7.1 优化策略模块 (`skills/optimization/`)

```
skills/optimization/
├── __init__.py
├── bayesian_optimizer.py     # Optuna 后端的贝叶斯优化
├── grid_search.py            # 初始网格采样
├── latin_hypercube.py        # Latin Hypercube 采样
└── constraint_handler.py     # 约束条件处理
```

#### bayesian_optimizer.py 核心逻辑

```python
class BayesianOptimizer:
    """基于 Optuna 的贝叶斯优化器。"""
    
    def __init__(self, search_space: dict, constraints: dict, direction: str = "minimize"):
        self.search_space = search_space
        self.constraints = constraints
        self.study = optuna.create_study(direction=direction)
    
    def tell(self, params: dict, value: float):
        """记录一次实验结果。"""
        trial = self.study.ask()
        for k, v in params.items():
            trial.suggest_float(k, self.search_space[k]["min"], self.search_space[k]["max"])
        self.study.tell(trial, value)
    
    def ask(self) -> dict:
        """建议下一组参数。"""
        trial = self.study.ask()
        params = {}
        for element, bounds in self.search_space.items():
            params[element] = trial.suggest_float(
                element, bounds["min"], bounds["max"]
            )
        
        # 应用约束
        params = apply_sum_constraint(params, self.constraints)
        return params
```

### 7.2 System Prompt 更新

```python
DESIGNER_SYSTEM_PROMPT = """你是一个电化学催化剂实验设计专家 Agent。

你的任务是根据优化目标和历史实验数据，设计下一组催化剂元素配比实验。

## 能力
1. 分析历史实验结果，找出元素配比与性能之间的趋势
2. 使用贝叶斯优化或智能搜索策略生成下一组参数
3. 考虑实验约束（元素比例和=1, 最小组分≥5%等）
4. 输出标准化的 MicroHySeeker 模板覆盖参数

## 输出要求
- 必须输出 JSON 格式的 target_concentrations
- 必须满足所有约束条件
- 必须解释选择策略和预期改善

## 重要限制
- 所有泵转速不得超过 300 RPM
- 每个元素配比必须在搜索空间范围内
- 配比之和必须等于约束指定的值（通常为 1.0）
"""
```

---

## 8. 与其他 Agent 的交互

```
Orchestrator → Designer:
    "设计下一组实验参数"
    附带: search_space, history, constraints, hint

Designer → Knowledge Manager:
    "查询 Fe-Co-Ni 催化剂的最优配比文献"
    用于: 初始设计参考 / LLM 推理辅助

Designer → Orchestrator:
    返回: {params, step_overrides, strategy, reasoning}
```

**注意**：Designer 不直接与 Executor 通信。它将参数返回给 Orchestrator，
由 Orchestrator 传递给 Executor 执行。这保证了所有决策都经过 Orchestrator 的审批。

---

## 9. 关键工作流

### 工作流 1: 初始实验设计

```
Designer 收到任务（无历史数据）
  │
  ├─ 查询 Knowledge Manager 获取文献参考
  │
  ├─ 生成初始采样点
  │   ├─ 方案A: 等间距网格（如 3元素各取 3个值 = 27组）
  │   ├─ 方案B: Latin Hypercube（更少点覆盖更大空间）
  │   └─ 方案C: LLM 基于文献建议起始点
  │
  ├─ 验证约束 + 格式化
  │
  └─ 返回第一组参数
```

### 工作流 2: 基于历史的设计

```
Designer 收到任务（有 N 轮历史数据）
  │
  ├─ 分析趋势：哪些元素增加/减少改善了性能？
  │
  ├─ 选择策略:
  │   ├─ N < 5: LLM 推理（理解能力强，数据量不够做 BO）
  │   └─ N ≥ 5: 贝叶斯优化（Optuna EI acquisition）
  │
  ├─ 生成候选参数
  │
  ├─ (可选) LLM 校验：这组参数合理吗？
  │
  ├─ 应用约束（归一化、最小值）
  │
  ├─ 调用 validate_experiment() 验证
  │
  └─ 返回参数 + 策略说明
```

---

## 10. 执行计划（✅ 全部完成）

| 步骤 | 任务 | 涉及文件 | 状态 |
|------|------|---------|------|
| 1 | 充实 exp_designer.py，添加 design_experiment 方法 | `agents/exp_designer.py` | ✅ |
| 2 | 实现约束处理逻辑 | `agents/exp_designer.py` | ✅ |
| 3 | 实现 step_overrides 格式化输出 | `agents/exp_designer.py` | ✅ |
| 4 | ML 预测模型替代独立 BO | `ml/performance_predictor.py` | ✅ |
| 5 | 约束处理集成到 Designer | `agents/exp_designer.py` | ✅ |
| 6 | 更新 System Prompt | `agents/exp_designer.py` | ✅ |
| 7 | 添加单元测试 | `tests/test_designer_agent.py` (16项通过) | ✅ |

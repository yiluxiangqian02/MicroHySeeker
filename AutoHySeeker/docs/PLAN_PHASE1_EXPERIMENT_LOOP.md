# Phase 1 规划：实验闭环系统

> 版本：1.0 | 日期：2026-03-18
> 目标：构建完整的 AI 驱动实验闭环，覆盖从实验设计到数据分析到决策优化的全流程。
> 前提：文献检索与下载功能在 Phase 2 实现，Phase 1 中知识库的文献数据通过手动导入。

---

## 一、系统定位

AutoHySeeker 是一个 **AI 多智能体科研平台**，核心能力是自主优化析氢反应 (HER) 催化剂的元素配比。

Phase 1 聚焦 **实验闭环（场景 A）**：

```
实验设计 → 实验执行 → 智能监控 → 数据分析 → 决策优化 → 归档 → 循环
     ↑                                                        │
     └────────────────────────────────────────────────────────┘
```

同时提供 **Chat 综合窗口**，让用户可以用自然语言与系统交互。

---

## 二、Agent 架构

### 2.1 Agent 清单（6 个 Agent）

| # | Agent | 标识 | 职责 | LLM | 新增/已有 |
|---|-------|------|------|-----|----------|
| 1 | OrchestratorAgent | `orchestrator` | 调度中心 + 决策 + 人机协作 | Qwen3-Max | 已有，需增强 |
| 2 | ExperimentDesignerAgent | `exp_designer` | 参数生成（LLM + ML 混合优化） | Gemini-3-Flash | 已有，需增强 |
| 3 | ExperimentExecutorAgent | `exp_executor` | 实验执行 + 两层智能监控 | Qwen3-Max (轻量) | 已有，需增强 |
| 4 | DiagnosticsExpertAgent | `diagnostics` | 故障诊断 + 自动修复 + 知识库查询 | GLM-4.6 Thinking | 已有，需增强 |
| 5 | ChatAgent | `chat` | 综合问答入口（实验进度/知识库/指令） | Qwen3-Max | 新增 |
| 6 | LiteratureAgent | `literature` | 文献检索 + 下载 + 解析入库 | Gemini-3-Flash | Phase 2 新增 |

> Agent 5 (ChatAgent) 在 Phase 1 实现。
> Agent 6 (LiteratureAgent) 在 Phase 2 实现，Phase 1 中文献通过手动导入。

### 2.2 Skill 清单（5 个 Skill）

| Skill | 文件 | 归属 | 共享/专属 | 功能 |
|-------|------|------|----------|------|
| DataAnalysisSkill | `skills/data_analysis_skill.py` | Orchestrator | 专属 | 在线指标提取、质量评估、历史对比 |
| KnowledgeArchiveSkill | `skills/knowledge_archive_skill.py` | Orchestrator | 专属 | 实验归档、检索 |
| RealtimeMonitorSkill | `skills/realtime_monitor_skill.py` | Executor | 专属 | L1 代码级规则引擎监控 |
| HeartbeatInspectorSkill | `skills/heartbeat_inspector_skill.py` | Executor | 专属 | L2 Agent 级心跳巡检 |
| KnowledgeQuerySkill | `skills/knowledge_query_skill.py` | 公共 | 共享 | 查询 OpenViking 知识库（只读） |

#### Skill 权限说明

- **专属 Skill**：只有归属 Agent 可以调用
  - DataAnalysisSkill / KnowledgeArchiveSkill → 只有 Orchestrator 调用
  - RealtimeMonitorSkill / HeartbeatInspectorSkill → 只有 Executor 调用
- **共享 Skill**：多个 Agent 可以调用
  - KnowledgeQuerySkill → 所有 Agent 均可调用（只读查询知识库）
    - DiagnosticsExpert 查询："之前有无相同错误？怎么修的？"
    - ExperimentDesigner 查询："之前跑过类似配比吗？效果如何？"
    - ChatAgent 查询：回答用户的知识库相关问题
    - Orchestrator 查询：决策时参考历史数据

### 2.3 架构层次图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│  Chat 窗口（自然语言交互）  |  优化控制台  |  Agent Dashboard │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP API (端口 8200)
┌──────────────────────────▼──────────────────────────────────┐
│                     LangGraph 路由层                         │
│  route_intent() → 关键词/LLM 意图识别 → 分发到对应 Agent    │
│  _AGENT_ALIASES: 旧名称向后兼容                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      Agent 层（6 个）                        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ OrchestratorAgent (大脑)                             │    │
│  │  ├── DataAnalysisSkill (专属)                        │    │
│  │  ├── KnowledgeArchiveSkill (专属)                    │    │
│  │  └── KnowledgeQuerySkill (共享)                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Designer     │ │ Executor     │ │ Diagnostics  │        │
│  │ + Knowledge  │ │ + Realtime   │ │ + Knowledge  │        │
│  │   QuerySkill │ │   Monitor    │ │   QuerySkill │        │
│  │              │ │ + Heartbeat  │ │              │        │
│  │              │ │ + Knowledge  │ │              │        │
│  │              │ │   QuerySkill │ │              │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
│  ┌──────────────┐ ┌──────────────────────────────┐          │
│  │ ChatAgent    │ │ LiteratureAgent (Phase 2)    │          │
│  │ + Knowledge  │ │ + AI 浏览器                   │          │
│  │   QuerySkill │ │ + KnowledgeArchive (写入)     │          │
│  └──────────────┘ └──────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      工具层 (Tools)                          │
│  experiment_ctrl.py | echem_analysis.py | report_generator  │
│  experiment_builder.py | data_reader.py | visualization.py  │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   知识库层 (OpenViking)                      │
│  文献库 | 实验库 | 运维库 | 分析库 | 项目库                 │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                MicroHySeeker (端口 8100)                     │
│                硬件控制 + 数据采集                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、各 Agent 详细设计

### 3.1 OrchestratorAgent（运行管控）

**职责**：闭环调度中心 + 决策引擎 + 人机协作入口

**内置 Skill**：
- `DataAnalysisSkill`（专属）— 在线数据分析
- `KnowledgeArchiveSkill`（专属）— 实验归档
- `KnowledgeQuerySkill`（共享）— 知识库查询

**核心方法**：

```python
class OrchestratorAgent(BaseAgent):
    # === 决策方法 ===
    async def evaluate_and_decide(self, state: dict) -> dict:
        """评估当前轮次结果，决定下一步。
        返回: {"action": "continue|stop|retry|adjust_strategy|pause_for_human",
               "reason": "...", "next_params_hint": {...}}
        """

    async def handle_anomaly(self, anomaly: dict, state: dict) -> dict:
        """处理异常报告，决定升级路径。
        critical → 紧急停止
        high → 交给 DiagnosticsExpert
        medium/low → 记录并继续
        """

    # === 数据分析（通过 DataAnalysisSkill）===
    async def analyze_experiment(self, run_id, data_path, params,
                                 target_metric, best_result=None) -> dict:
        """调用 DataAnalysisSkill 分析实验数据。
        返回: {metrics, data_quality, interpretation, comparison}
        """

    # === 知识管理（通过 KnowledgeArchiveSkill）===
    async def archive_experiment(self, run_id, params, metrics,
                                  interpretation) -> dict:
        """归档实验结果到知识库。"""

    async def retrieve_knowledge(self, query, search_type="both",
                                  top_k=5) -> dict:
        """检索知识库。"""

    # === 人机协作 ===
    async def request_human_approval(self, decision: dict,
                                      context: dict) -> dict:
        """关键决策点暂停，等待人工确认。
        触发条件（可配置）：
        - 连续 N 轮无改善
        - 要切换元素体系
        - 异常修复失败
        - 达到预算上限
        返回: {"approved": bool, "human_feedback": "..."}
        """

    # === ML 模型管理 ===
    async def update_ml_training_data(self, experiment_result: dict):
        """每轮实验完成后，更新 ML 预测模型的训练数据。"""
```

**人机协作工作模式**：

```
┌─────────────────────────────────────────────────────────┐
│ 工作模式（可配置）                                       │
├─────────────────────────────────────────────────────────┤
│ 全自动模式：                                             │
│   Agent 自主决策，仅在 critical 异常时通知人工            │
│   适用：成熟实验方案的批量优化                           │
│                                                          │
│ 半自动模式（推荐）：                                     │
│   Agent 自主执行，关键决策点暂停等人工确认               │
│   关键决策点：                                           │
│   - 首轮实验参数确认                                     │
│   - 连续 3 轮无改善时的策略调整                          │
│   - 异常修复方案确认                                     │
│   - 优化终止判断                                         │
│   适用：日常科研                                         │
│                                                          │
│ 手动模式：                                               │
│   每轮都需人工确认，Agent 仅提供建议                     │
│   适用：新课题探索、高风险实验                           │
└─────────────────────────────────────────────────────────┘
```

**配置项**（`configs/orchestrator.toml`）：

```toml
[orchestrator]
work_mode = "semi_auto"          # "full_auto" | "semi_auto" | "manual"
max_no_improve_rounds = 3        # 连续无改善轮次阈值
pause_on_strategy_change = true  # 策略变更时暂停
pause_on_anomaly_fix = true      # 异常修复时暂停
```

---

### 3.2 ExperimentDesignerAgent（实验设计）

**职责**：根据历史数据、知识库和优化算法，生成下一组实验参数

**使用 Skill**：
- `KnowledgeQuerySkill`（共享）— 查询文献推荐配比、历史实验结果

**核心方法**：

```python
class ExperimentDesignerAgent(BaseAgent):
    async def design_experiment(self, state: dict) -> dict:
        """生成下一组实验参数。

        三阶段策略自动切换：
        - 第 0 轮：查知识库获取文献推荐范围，生成初始点
        - 1~4 轮：LLM 引导（结合历史结果 + 知识库）
        - ≥5 轮：ML 预测模型生成候选点 → LLM 审核选择

        返回:
        {
            "params": {"Fe": 0.3, "Co": 0.5, "Ni": 0.2},
            "strategy": "literature_guided|llm_guided|ml_hybrid",
            "confidence": 0.85,
            "reasoning": "根据文献，Co>40% 区间过电位较低...",
            "step_overrides": {...}  # MicroHySeeker 模板覆盖参数
        }
        """

    async def _literature_guided_design(self, state: dict) -> dict:
        """第 0 轮：查知识库获取文献推荐，生成初始实验点。"""
        # 1. KnowledgeQuerySkill 查询文献推荐配比范围
        # 2. 如果有文献数据 → 在推荐范围内生成初始点
        # 3. 如果无文献数据 → 等比均分（现有逻辑）

    async def _llm_guided_design(self, state: dict) -> dict:
        """1~4 轮：LLM 根据历史结果推理下一组参数。"""
        # 1. 构建 prompt：历史结果 + 趋势 + 知识库上下文
        # 2. LLM 推理 → 解析 JSON → 约束校验

    async def _ml_hybrid_design(self, state: dict) -> dict:
        """≥5 轮：ML 预测 + LLM 审核。"""
        # 1. Optuna/高斯过程生成 N 个候选点 + 预测值
        # 2. 构建 prompt：候选点 + 预测值 + 历史数据 + 知识库
        # 3. LLM 从候选点中选择最优 + 解释原因
        # 4. 约束校验

    def _apply_constraints(self, params: dict) -> dict:
        """约束校验：比例和=1、最小组分≥5%、RPM≤300 等。"""
```

**ML 预测模型设计**：

```python
class PerformancePredictor:
    """轻量 ML 模型，预测 配比 → 性能。

    - 数据量 < 10：不启用，返回 None
    - 数据量 10~30：随机森林回归
    - 数据量 > 30：高斯过程回归（带不确定性估计）

    训练数据来源：OptimizationLoop 每轮实验结果
    特征：元素配比（Fe, Co, Ni, ...）
    目标：target_metric（如 overpotential_mV）
    """

    def fit(self, experiments: list[dict]):
        """用历史实验数据训练/更新模型。"""

    def predict_candidates(self, n_candidates: int = 10) -> list[dict]:
        """生成 N 个候选点 + 预测值 + 不确定性。
        返回: [{"params": {...}, "predicted_value": 180.5,
                "uncertainty": 15.2}, ...]
        使用 Optuna TPE 采样 + 模型预测排序。
        """
```

---

### 3.3 ExperimentExecutorAgent（实验执行 + 智能监控）

**职责**：执行实验、两层智能监控、数据收集

**内置 Skill**：
- `RealtimeMonitorSkill`（专属）— L1 代码级规则引擎
- `HeartbeatInspectorSkill`（专属）— L2 Agent 级心跳巡检
- `KnowledgeQuerySkill`（共享）— 查询历史运维记录

**核心方法**：

```python
class ExperimentExecutorAgent(BaseAgent):
    async def execute_experiment(self, params: dict) -> dict:
        """执行单次实验的完整生命周期。

        流程：
        1. 预检查（health_check + 设备状态）
        2. 实例化模板（instantiate_template）
        3. 启动两层监控
        4. 等待实验完成
        5. 收集数据
        6. 记录环境快照（可复现性）

        返回:
        {
            "status": "completed|failed|aborted",
            "run_id": "20260318_xxx",
            "data_path": "data/2026-03-18/xxx/",
            "duration_s": 120,
            "anomalies": [],
            "environment_snapshot": {...}  # 可复现性
        }
        """

    async def _pre_check(self) -> dict:
        """实验前预检查。
        - health_check()
        - get_connection_info()
        - 检查模板是否存在
        - 检查设备状态（泵、CHI）
        """

    async def _record_environment_snapshot(self) -> dict:
        """记录实验环境快照（可复现性保障）。
        返回:
        {
            "timestamp": "2026-03-18T18:05:00",
            "device_status": {...},       # 泵状态、连接状态
            "software_version": "1.2.0",  # AutoHySeeker 版本
            "config_hash": "abc123",      # 配置文件哈希
            "params_source": "ml_hybrid", # 参数来源
            "template_id": "tpl_her_standard",
            "template_hash": "def456"     # 模板内容哈希
        }
        """
```

**两层监控机制详细设计**：

```
┌─────────────────────────────────────────────────────────┐
│ 监控开关: [关闭] / [开启]                                │
│ 默认关闭。开启后激活 L2 心跳巡检。L1 始终运行。          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ L1: RealtimeMonitorSkill（代码级，始终运行）             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 规则引擎，确定性检测，无 LLM：                      │ │
│ │                                                      │ │
│ │ 规则 1: 泵转速偏差 > 5% → severity: MEDIUM          │ │
│ │ 规则 2: 通信超时 > 3s → severity: HIGH               │ │
│ │ 规则 3: 实验步骤超时 > 2x 预期时间 → severity: HIGH  │ │
│ │ 规则 4: 数据文件大小为 0 → severity: MEDIUM          │ │
│ │ 规则 5: 泵地址无响应 → severity: CRITICAL            │ │
│ │ 规则 6: 电化学数据电流突变 > 50% → severity: MEDIUM  │ │
│ │                                                      │ │
│ │ 检测频率: 每次轮询状态时执行（~2s 间隔）             │ │
│ │ 触发动作: 直接上报 Orchestrator → DiagnosticsExpert  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ L2: HeartbeatInspectorSkill（Agent级，开关控制）         │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ LLM 综合判断，需要监控开关开启：                     │ │
│ │                                                      │ │
│ │ 间隔: 可配置（默认 30s，范围 10s~300s）              │ │
│ │                                                      │ │
│ │ 每次心跳做什么：                                     │ │
│ │ 1. 收集系统快照（泵状态、实验进度、最近日志）       │ │
│ │ 2. 查知识库：最近有无类似异常模式？                  │ │
│ │ 3. LLM 综合判断：                                    │ │
│ │    - 系统状态是否正常？                               │ │
│ │    - 实验进度是否符合预期？                           │ │
│ │    - 有无潜在风险？                                   │ │
│ │ 4. 判断结果：                                        │ │
│ │    - normal → 记录日志，继续                          │ │
│ │    - warning → 上报 Orchestrator                      │ │
│ │    - critical → 触发 DiagnosticsExpert               │ │
│ │                                                      │ │
│ │ 配置项 (configs/monitor.toml):                       │ │
│ │   heartbeat_enabled = false                           │ │
│ │   heartbeat_interval_s = 30                           │ │
│ │   heartbeat_model = "qwen3-max"                      │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**L1 和 L2 的协作关系**：

```
正常情况：
  L1 持续检测 → 全部通过 → 无动作
  L2 定时心跳 → LLM 判断正常 → 记录日志

L1 发现异常：
  L1 检测到规则触发 → 直接上报 Orchestrator
  → Orchestrator 决定是否调用 DiagnosticsExpert
  （不等 L2，立即响应）

L2 发现隐患：
  L2 心跳时 LLM 发现"虽然没触发 L1 规则，但数据趋势异常"
  → 上报 Orchestrator → 人工确认或自动处理

两层互补：
  L1 = 快速、确定性、覆盖已知异常模式
  L2 = 慢速、智能、发现未知/复合异常
```

---

### 3.4 DiagnosticsExpertAgent（故障排查）

**职责**：故障诊断、自动修复、经验沉淀

**使用 Skill**：
- `KnowledgeQuerySkill`（共享）— 查询历史故障记录

**核心方法**：

```python
class DiagnosticsExpertAgent(BaseAgent):
    # 已知故障注册表
    KNOWN_FAULTS = {
        "communication_timeout": {"auto_fix": "_fix_communication", "severity": "high"},
        "pump_error": {"auto_fix": "_fix_pump", "severity": "high"},
        "pump_speed_deviation": {"auto_fix": "_fix_pump_speed", "severity": "medium"},
        "data_file_empty": {"auto_fix": None, "severity": "medium"},
        "echem_current_spike": {"auto_fix": None, "severity": "medium"},
    }

    async def diagnose_and_fix(self, anomaly: dict) -> dict:
        """诊断故障并尝试修复。

        流程：
        1. 查知识库：之前有无相同/类似错误？
           - 有 → 参考历史修复方案
           - 无 → 进入 LLM 诊断
        2. 匹配已知故障注册表
           - 匹配 → 执行自动修复
           - 不匹配 → LLM 推理根因
        3. 执行修复（如果可以）
        4. 验证修复结果（health_check）
        5. 记录到知识库（无论成功失败）

        返回:
        {
            "resolved": bool,
            "fault_type": "communication_timeout",
            "root_cause": "COM3 串口连接断开",
            "action_taken": "重启串口连接",
            "verification": {"healthy": true},
            "recommendation": "检查 COM3 线缆是否松动",
            "knowledge_entry_id": "ops_20260318_xxx"  # 已写入知识库
        }
        """

    async def _query_historical_faults(self, anomaly: dict) -> list:
        """查知识库：历史上有无相同错误？
        返回匹配的历史记录列表，包含修复方案和成功率。
        """

    async def _record_to_knowledge_base(self, diagnosis: dict):
        """将诊断结果写入知识库运维库。
        包含：错误类型、根因、修复方案、是否成功、时间戳。
        下次遇到相同问题时可以直接参考。
        """
```

---

### 3.5 ChatAgent（综合问答）

**职责**：自然语言交互入口，综合回答实验相关问题

**使用 Skill**：
- `KnowledgeQuerySkill`（共享）— 查询知识库

**核心方法**：

```python
class ChatAgent(BaseAgent):
    """综合问答 Agent。

    接收用户自然语言输入，识别意图，调用对应能力回答。
    维护对话历史，支持多轮对话。
    """

    # 意图分类
    INTENTS = {
        "experiment_status": "查询实验进度/状态",
        "optimization_status": "查询优化进度/最优结果",
        "knowledge_query": "查询知识库（文献/历史实验）",
        "data_analysis": "请求分析某次实验数据",
        "design_request": "请求设计实验参数",
        "system_status": "查询系统/设备状态",
        "control_command": "控制指令（启动/停止/暂停优化）",
        "general_qa": "一般科研问题",
    }

    async def chat(self, user_message: str,
                   conversation_history: list = None) -> dict:
        """处理用户消息。

        流程：
        1. LLM 意图识别（基于消息 + 对话历史）
        2. 根据意图调用对应能力：
           - experiment_status → 查询 OptimizationLoop 状态
           - knowledge_query → KnowledgeQuerySkill
           - data_analysis → 转发给 Orchestrator.analyze_experiment()
           - design_request → 转发给 ExperimentDesigner
           - control_command → 调用优化控制 API
           - general_qa → LLM 直接回答
        3. 构建回复（结合查询结果 + LLM 生成自然语言）

        返回:
        {
            "reply": "当前正在进行第 5 轮优化...",
            "intent": "optimization_status",
            "data": {...},  # 结构化数据（可选，供 UI 展示）
            "suggestions": ["查看详细结果", "停止优化"]  # 建议操作
        }
        """

    async def _classify_intent(self, message: str,
                                history: list) -> str:
        """LLM 意图分类。"""

    def _build_context(self, intent: str) -> str:
        """根据意图构建上下文（当前优化状态、系统状态等）。"""
```

**Chat 对话示例**：

```
用户: "现在实验跑到哪了？"
ChatAgent: "当前正在第 5 轮优化，Executor 正在执行实验（步骤 5/8）。
           当前最优结果：Fe=0.30, Co=0.50, Ni=0.20，过电位 182.5 mV。"

用户: "之前有没有跑过 Co 含量超过 60% 的实验？"
ChatAgent: "查到 2 条相关记录：
           - 第 2 轮：Co=0.65, 过电位 210.3 mV（质量 0.88）
           - 文献记录：Co>60% 时过电位通常在 200-250 mV 范围。"

用户: "帮我停一下优化"
ChatAgent: "已发送停止指令。优化将在当前轮次完成后优雅退出。"

用户: "Fe-Co-Ni 催化剂的 Tafel 斜率一般是多少？"
ChatAgent: "根据知识库中的文献记录，Fe-Co-Ni 三元合金 HER 催化剂的
           Tafel 斜率通常在 60-120 mV/dec 范围，其中 Co 含量较高
           的配比倾向于较低的 Tafel 斜率（~65-80 mV/dec）。"
```

---

## 四、知识库设计（OpenViking 集成）

### 4.1 知识库分区

```text
OpenViking 知识库
├── literature/          # 文献库（Phase 1 手动导入，Phase 2 自动）
│   ├── 论文摘要、关键结论、方法论
│   ├── 性能数据表（文献报道的催化剂性能）
│   └── 元数据（DOI、期刊、年份、关键词）
│
├── experiments/         # 实验库
│   ├── 每次实验记录：
│   │   ├── run_id, timestamp
│   │   ├── params（元素配比 + 步骤参数）
│   │   ├── results（指标数据）
│   │   ├── quality_score（数据质量评分）
│   │   ├── interpretation（分析结论）
│   │   ├── decision（Orchestrator 的决策 + 原因）
│   │   └── environment_snapshot（可复现性快照）
│   └── 索引：按配比、按性能、按时间
│
├── operations/          # 运维库
│   ├── 故障记录：
│   │   ├── fault_type, severity, timestamp
│   │   ├── root_cause（根因分析）
│   │   ├── fix_action（修复方案）
│   │   ├── fix_success（是否成功）
│   │   └── related_faults（关联故障 ID）
│   └── 设备维护记录、配置变更历史
│
├── analysis/            # 分析库（Phase 2 主要使用）
│   ├── 数据分析结论
│   ├── 科研绘图配置和结果
│   └── 论文草稿片段
│
└── projects/            # 项目库
    ├── project_001_HER_FeCoNi/
    │   ├── config（搜索空间、目标、约束）
    │   ├── experiments → 指向 experiments/ 中的记录
    │   └── literature → 指向 literature/ 中的记录
    └── project_002_OER_IrRu/（未来扩展）
```

### 4.2 知识库读写权限

```text
写入权限（严格隔离）：
  Orchestrator  → experiments/（通过 KnowledgeArchiveSkill）
  Diagnostics   → operations/（通过 _record_to_knowledge_base）
  Literature    → literature/（Phase 2）
  ResearchAnalyst → analysis/（Phase 2）

读取权限（共享）：
  所有 Agent → 通过 KnowledgeQuerySkill 只读查询任意分区
```

### 4.3 KnowledgeQuerySkill 接口

```python
class KnowledgeQuerySkill:
    """公共只读查询 Skill，所有 Agent 可用。"""

    async def search(self, query: str, partitions: list[str] = None,
                     top_k: int = 5) -> list[dict]:
        """语义搜索知识库。
        partitions: ["literature", "experiments", "operations", "analysis"]
                    None 表示搜索全部分区。
        """

    async def get_similar_experiments(self, params: dict,
                                       threshold: float = 0.8) -> list[dict]:
        """查找配比相似的历史实验。"""

    async def get_fault_history(self, fault_type: str) -> list[dict]:
        """查找历史故障记录及修复方案。"""

    async def get_literature_insights(self, topic: str) -> list[dict]:
        """查找文献中关于某主题的关键结论。"""
```

---

## 五、优化闭环流程（OptimizationLoop）

### 5.1 完整流程

```text
OptimizationLoop.run()
│
├── 1. 初始化
│   ├── 加载项目配置（搜索空间、目标、约束）
│   ├── 加载历史数据（从知识库）
│   └── 初始化 ML 预测模型（如果有历史数据）
│
├── 2. 循环开始 ─────────────────────────────────────┐
│   │                                                  │
│   ├── 2.1 实验设计                                   │
│   │   ├── Designer.design_experiment(state)          │
│   │   ├── 人工审批（semi_auto/manual 模式）          │
│   │   └── 记录设计决策到知识库                       │
│   │                                                  │
│   ├── 2.2 实验执行                                   │
│   │   ├── Executor.execute_experiment(params)        │
│   │   ├── L1 + L2 监控运行中                         │
│   │   ├── 异常 → Diagnostics.diagnose_and_fix()     │
│   │   └── 收集数据 + 环境快照                        │
│   │                                                  │
│   ├── 2.3 数据分析                                   │
│   │   ├── Orchestrator.analyze_experiment(data)      │
│   │   ├── 指标提取 + 质量评估                        │
│   │   └── 历史对比 + 趋势分析                        │
│   │                                                  │
│   ├── 2.4 归档                                       │
│   │   ├── Orchestrator.archive_experiment(result)    │
│   │   └── 更新 ML 训练数据                           │
│   │                                                  │
│   ├── 2.5 决策                                       │
│   │   ├── Orchestrator.evaluate_and_decide(state)    │
│   │   ├── continue → 回到 2.1                        │
│   │   ├── stop → 退出循环                            │
│   │   ├── retry → 重新执行 2.2（相同参数）           │
│   │   ├── adjust_strategy → 修改搜索策略后回到 2.1   │
│   │   └── pause_for_human → 等待人工确认             │
│   │                                                  │
│   └── 回到 2.1 ────────────────────────────────────┘
│
└── 3. 结束
    ├── 生成优化报告
    ├── 归档最终结果
    └── 通知用户（Chat / UI）
```

### 5.2 状态管理

```python
# LangGraph State 定义
class OptimizationState(TypedDict):
    # 基本信息
    project_id: str
    run_id: str
    round_number: int
    max_rounds: int

    # 搜索空间
    search_space: dict          # {"Fe": [0.1, 0.8], "Co": [0.1, 0.8], ...}
    target_metric: str          # "overpotential_mV"
    optimization_direction: str # "minimize"
    constraints: dict           # {"min_fraction": 0.05, "max_rpm": 300}

    # 当前轮次
    current_params: dict        # {"Fe": 0.3, "Co": 0.5, "Ni": 0.2}
    current_result: dict        # 实验结果
    current_analysis: dict      # 分析结论

    # 历史
    history: list[dict]         # 所有历史轮次
    best_result: dict           # 历史最优

    # ML 模型
    ml_model_ready: bool        # ML 模型是否可用
    ml_candidates: list[dict]   # ML 生成的候选点

    # 监控
    monitor_enabled: bool       # 监控开关
    anomalies: list[dict]       # 当前轮次异常记录

    # 人机协作
    work_mode: str              # "full_auto" | "semi_auto" | "manual"
    pending_approval: dict      # 等待人工确认的决策
    human_feedback: str         # 人工反馈

    # 状态
    status: str                 # "running" | "paused" | "completed" | "failed"
    messages: list              # LangGraph 消息列表
```

---

## 六、API 路由设计

### 6.1 现有路由（保留并增强）

```text
POST /api/chat              → ChatAgent.chat()
POST /api/optimization/start → OptimizationLoop.start()
POST /api/optimization/stop  → OptimizationLoop.stop()
GET  /api/optimization/status → OptimizationLoop.get_status()
GET  /api/data/experiments   → 查询实验历史
GET  /api/diagnostics/health → 系统健康检查
```

### 6.2 新增路由

```text
# 监控控制
POST /api/monitor/toggle     → 开启/关闭 L2 心跳监控
GET  /api/monitor/status     → 获取监控状态（L1 规则 + L2 心跳）
PUT  /api/monitor/config     → 修改监控配置（心跳间隔等）

# 人机协作
GET  /api/approval/pending   → 获取待审批决策
POST /api/approval/respond   → 提交审批结果（approve/reject + feedback）

# 知识库
GET  /api/knowledge/search   → 搜索知识库
GET  /api/knowledge/experiments → 查询实验记录
GET  /api/knowledge/faults   → 查询故障记录

# 项目管理
GET  /api/projects           → 项目列表
POST /api/projects           → 创建新项目
GET  /api/projects/{id}      → 项目详情
```

---

## 七、配置文件结构

```text
AutoHySeeker/configs/
├── agent_models.toml        # Agent ↔ LLM 模型映射（已有）
├── orchestrator.toml        # Orchestrator 配置（工作模式等）
├── monitor.toml             # 监控配置（心跳间隔、规则阈值）
├── designer.toml            # Designer 配置（ML 切换阈值等）
├── knowledge.toml           # 知识库配置（OpenViking 连接等）
└── projects/                # 项目配置目录
    └── her_feconi.toml      # 具体项目（搜索空间、目标等）
```

**monitor.toml 示例**：

```toml
[realtime_monitor]
enabled = true                    # L1 始终启用
poll_interval_s = 2               # 轮询间隔

[realtime_monitor.rules]
pump_speed_deviation_pct = 5.0    # 泵转速偏差阈值 %
communication_timeout_s = 3.0    # 通信超时阈值 s
step_timeout_multiplier = 2.0    # 步骤超时倍数
current_spike_pct = 50.0         # 电流突变阈值 %

[heartbeat_inspector]
enabled = false                   # L2 默认关闭
interval_s = 30                   # 心跳间隔
model = "qwen3-max"              # 心跳巡检用的 LLM
```

**designer.toml 示例**：

```toml
[designer]
ml_switch_threshold = 5           # ≥5 轮切换到 ML 混合模式
ml_min_data_points = 10           # ML 模型最少需要 10 个数据点
ml_candidate_count = 10           # ML 生成候选点数量
ml_model_type = "auto"            # "auto" | "random_forest" | "gaussian_process"

[designer.constraints]
min_fraction = 0.05               # 最小组分比例
max_rpm = 300                     # 最大转速
sum_tolerance = 0.001             # 比例和容差
```

---

## 八、文件结构（Phase 1 目标）

```text
AutoHySeeker/
├── configs/
│   ├── agent_models.toml
│   ├── orchestrator.toml          # 新增
│   ├── monitor.toml               # 新增
│   ├── designer.toml              # 新增
│   ├── knowledge.toml             # 新增
│   └── projects/
│       └── her_feconi.toml        # 新增
│
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseAgent（已有）
│   │   ├── orchestrator.py        # 增强：人机协作 + ML 管理
│   │   ├── exp_designer.py        # 增强：三阶段策略 + ML 混合
│   │   ├── exp_executor.py        # 增强：两层监控
│   │   ├── diagnostics.py         # 增强：知识库查询 + 经验沉淀
│   │   └── chat_agent.py          # 新增
│   │
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── data_analysis_skill.py      # 已有，增强
│   │   ├── knowledge_archive_skill.py  # 已有，增强
│   │   ├── knowledge_query_skill.py    # 新增（公共只读查询）
│   │   ├── realtime_monitor_skill.py   # 新增（L1 规则引擎）
│   │   └── heartbeat_inspector_skill.py # 新增（L2 心跳巡检）
│   │
│   ├── ml/                         # 新增目录
│   │   ├── __init__.py
│   │   └── performance_predictor.py # ML 预测模型
│   │
│   ├── graph/
│   │   ├── orchestrator.py         # LangGraph 路由（增强）
│   │   ├── optimization_loop.py    # 优化闭环（增强）
│   │   └── nodes.py                # 节点定义（增强）
│   │
│   ├── api/routes/
│   │   ├── chat.py                 # 增强：接入 ChatAgent
│   │   ├── optimization.py         # 增强：人机协作路由
│   │   ├── monitor.py              # 新增：监控控制路由
│   │   ├── approval.py             # 新增：审批路由
│   │   ├── knowledge.py            # 新增：知识库查询路由
│   │   └── projects.py             # 新增：项目管理路由
│   │
│   ├── knowledge/                  # 新增目录
│   │   ├── __init__.py
│   │   ├── viking_client.py        # OpenViking 客户端封装
│   │   └── schema.py               # 知识库数据模型定义
│   │
│   ├── common/
│   │   ├── config.py               # 增强：加载新配置文件
│   │   ├── llm_client.py           # 已有
│   │   └── agent_manager.py        # 已有
│   │
│   └── tools/
│       ├── experiment_ctrl.py      # 已有
│       └── report_generator.py     # 已有
│
├── data/
│   └── experiment_archive.json     # 已有（将迁移到 OpenViking）
│
└── docs/
    ├── PLAN_PHASE1_EXPERIMENT_LOOP.md   # 本文档
    ├── PLAN_PHASE2_RESEARCH_OUTPUT.md   # Phase 2 规划
    └── COLLABORATION_GUIDE.md           # 多端协作指南
```

---

## 九、实施步骤（建议顺序）

### Step 1：基础设施（知识库 + 配置）

1. 创建 `knowledge/viking_client.py` — OpenViking 客户端封装
2. 创建 `knowledge/schema.py` — 知识库数据模型
3. 创建 `skills/knowledge_query_skill.py` — 公共查询 Skill
4. 增强 `skills/knowledge_archive_skill.py` — 按分区写入
5. 创建配置文件：`orchestrator.toml`, `monitor.toml`, `designer.toml`, `knowledge.toml`
6. 增强 `common/config.py` — 加载新配置

### Step 2：智能监控

7. 创建 `skills/realtime_monitor_skill.py` — L1 规则引擎
8. 创建 `skills/heartbeat_inspector_skill.py` — L2 心跳巡检
9. 增强 `agents/exp_executor.py` — 集成两层监控
10. 创建 `api/routes/monitor.py` — 监控控制路由

### Step 3：实验设计增强

11. 创建 `ml/performance_predictor.py` — ML 预测模型
12. 增强 `agents/exp_designer.py` — 三阶段策略 + ML 混合
13. 增强 Designer 的知识库查询能力

### Step 4：决策与人机协作

14. 增强 `agents/orchestrator.py` — 人机协作 + ML 管理
15. 创建 `api/routes/approval.py` — 审批路由
16. 增强 `graph/optimization_loop.py` — 暂停/恢复机制

### Step 5：ChatAgent + 诊断增强

17. 创建 `agents/chat_agent.py` — 综合问答 Agent
18. 增强 `agents/diagnostics.py` — 知识库查询 + 经验沉淀
19. 增强 `api/routes/chat.py` — 接入 ChatAgent

### Step 6：项目管理 + 集成测试

20. 创建 `api/routes/projects.py` — 项目管理路由
21. 创建 `api/routes/knowledge.py` — 知识库查询路由
22. 增强 `graph/orchestrator.py` — 路由新 Agent
23. 端到端集成测试

---

## 十、Agent 间交互协议

### 10.1 消息格式

所有 Agent 间通信通过 LangGraph State 传递，格式统一：

```python
# Agent 输出格式
{
    "agent": "exp_designer",           # 发送方
    "action": "design_complete",       # 动作类型
    "data": {...},                     # 业务数据
    "timestamp": "2026-03-18T18:05:00",
    "trace_id": "opt_round_5"         # 追踪 ID
}

# 异常上报格式
{
    "agent": "exp_executor",
    "action": "anomaly_detected",
    "data": {
        "anomaly_type": "communication_timeout",
        "severity": "high",            # critical | high | medium | low
        "details": "COM3 no response for 5s",
        "source": "L1_realtime_monitor" # L1 or L2
    },
    "timestamp": "2026-03-18T18:05:00",
    "trace_id": "opt_round_5"
}

# 人工审批请求格式
{
    "agent": "orchestrator",
    "action": "approval_required",
    "data": {
        "decision_type": "strategy_change",
        "proposed_action": "切换到高 Co 区间探索",
        "reason": "连续 3 轮无改善，当前区间可能已饱和",
        "options": ["approve", "reject", "modify"],
        "context": {...}               # 历史数据摘要
    },
    "timestamp": "2026-03-18T18:05:00",
    "trace_id": "opt_round_5"
}
```

### 10.2 调用关系图

```text
                    用户（Chat / UI）
                         │
                    ┌────▼────┐
                    │  Chat   │
                    │  Agent  │
                    └────┬────┘
                         │ 意图路由
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    ┌───────────┐ ┌────────────┐ ┌──────────┐
    │ Designer  │ │Orchestrator│ │ Executor │
    └─────┬─────┘ └──────┬─────┘ └────┬─────┘
          │              │             │
          │    ┌─────────┼─────────┐   │
          │    ▼         ▼         ▼   │
          │ DataAnalysis Knowledge  │   │
          │ Skill       Archive     │   │
          │             Skill       │   │
          │                         │   │
          │              │          │   │
          │              ▼          │   │
          │         evaluate_       │   │
          │         and_decide      │   │
          │              │          │   │
          │    ┌─────────┤          │   │
          │    ▼         ▼          │   │
          │  continue   stop        │   │
          │    │                    │   │
          ◄────┘                    │   │
                                    │   │
                              异常时 │   │
                                    ▼   │
                            ┌───────────┐
                            │Diagnostics│
                            │  Expert   │
                            └───────────┘

    ─── 所有 Agent 共享 KnowledgeQuerySkill（只读）───
```

---

## 十一、安全与审计

### 11.1 审计日志

所有 Agent 行为记录到 OpenViking operations/ 分区：

```python
# 审计日志条目
{
    "log_type": "agent_action",
    "agent": "exp_executor",
    "action": "start_experiment",
    "params": {"Fe": 0.3, "Co": 0.5, "Ni": 0.2},
    "result": "success",
    "timestamp": "2026-03-18T18:05:00",
    "trace_id": "opt_round_5",
    "project_id": "her_feconi"
}
```

### 11.2 硬件操作安全

- 只有 ExperimentExecutorAgent 有硬件写权限（通过 experiment_ctrl.py）
- DiagnosticsExpert 的修复操作需要通过 Executor 代理执行
- 所有硬件操作记录审计日志
- CRITICAL 异常自动触发紧急停止（emergency_stop）

---

> 本文档定义了 Phase 1 的完整技术方案。实现时应严格按照本文档的 Agent 职责、Skill 归属、知识库分区、API 路由和交互协议进行开发。任何偏离需在 COLLABORATION_GUIDE.md 中记录原因。

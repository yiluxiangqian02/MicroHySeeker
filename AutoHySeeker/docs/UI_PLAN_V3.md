# AutoHySeeker 前端规划 V3 — PySide6 Agent Dashboard

> 版本：3.0 | 日期：2026-03-18
> 前端形态：PySide6 桌面端嵌入式 Dashboard（非 Web UI）
> 后端对接：AutoHySeeker FastAPI（端口 8200）
> 分阶段：Phase 1（实验闭环 UI）+ Phase 2（文献 + 科研产出 UI）

---

## 一、现有前端资产

### 1.1 已有文件

| 文件 | 行数 | 功能 |
| --- | --- | --- |
| `MicroHySeeker/src/ui/main_window.py` | ~1074 | 主窗口，硬件可视化，实验流程 |
| `MicroHySeeker/src/ui/widgets/agent_dashboard.py` | ~321 | 基础 Agent Dashboard（已嵌入主窗口） |
| `MicroHySeeker/src/services/autohyseeker_client.py` | ~348 | AutoHySeeker API 客户端 |
| `MicroHySeeker/src/services/experiment_data_manager.py` | ~441 | 实验数据管理 |

### 1.2 agent_dashboard.py 现有能力

- 连接状态指示（绿/红点）
- 优化轮次进度条
- 最优结果展示（指标 + 参数）
- 启动/停止按钮
- 每 5 秒轮询 `/api/optimization/status`

### 1.3 autohyseeker_client.py 现有 API

- `health_check()` → `/health`
- `analyze_experiment()` → `/agents/invoke`
- `suggest_next_experiment()` → `/api/experiments/suggestions`
- `diagnose_failure()` → `/diagnostics/invoke`
- `list_templates()` / `get_template()` / `create_template()` → `/templates`
- 优化控制 → `/api/optimization/start|stop|status`

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────┐
│  MicroHySeeker 桌面端 (PySide6)                          │
│  ├── 主窗口：实验编辑器 + 硬件控制 + 数据查看            │
│  └── Agent Dashboard（嵌入式面板，本文档规划）            │
│       ├── Phase 1: 优化控制 + Agent 状态 + 实验历史      │
│       │            + 监控面板 + 审批面板 + 对话           │
│       └── Phase 2: 文献管理 + 科研绘图 + 论文辅助        │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP API (端口 8200)
┌────────────────▼────────────────────────────────────────┐
│  AutoHySeeker Backend (FastAPI + LangGraph)              │
│  Phase 1: 5 Agent + 5 Skill                             │
│  Phase 2: +2 Agent + 2 Skill                            │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP API (端口 8100)
┌────────────────▼────────────────────────────────────────┐
│  MicroHySeeker 硬件控制层                                │
│  蠕动泵 (RS485) + CHI 电化学工作站 + 微流控芯片         │
└─────────────────────────────────────────────────────────┘
```

---

## 三、Phase 1 前端规划 — 实验闭环 UI

### 3.1 Dashboard 整体布局

Dashboard 嵌入 MicroHySeeker 主窗口右侧面板，分为 7 个 Tab。

```
┌─────────────────────────────────────────────────────────┐
│  Agent Dashboard                                         │
│  [优化] [Agent] [历史] [监控] [审批] [对话] [日志]      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│              (Tab 内容区域)                               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### 3.2 Tab 1: 优化控制台

核心页面，控制闭环优化流程。

```
┌─────────────────────────────────────────────────────────┐
│ 优化控制台                                               │
├─────────────────────────────────────────────────────────┤
│ 项目: her_feconi          工作模式: [semi_auto ▼]       │
│ 目标: 最小化 HER 过电位   方向: minimize                │
│ 元素: Fe, Co, Ni          轮次: 3 / 10                  │
│ 状态: ● 运行中            策略: LLM 引导 (< 5轮)       │
├─────────────────────────────────────────────────────────┤
│ 当前最优:                                                │
│   配比: Fe=0.30, Co=0.50, Ni=0.20                       │
│   过电位: 182.5 mV  质量评分: 0.92                      │
│   vs 文献最优: -28 mV (改善 13.3%)                      │
├─────────────────────────────────────────────────────────┤
│ 当前轮次流水线:                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │ 设计   │→│ 执行   │→│ 分析   │→│ 决策   │      │
│   │ ✅完成 │  │ ●进行  │  │ ○等待  │  │ ○等待  │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│                                                          │
│   Designer: Fe=0.25, Co=0.55, Ni=0.20 (LLM推荐)        │
│   Executor: 实验运行中 (步骤 3/8)                        │
│   监控: L1 ● 正常  L2 ○ 关闭                            │
├─────────────────────────────────────────────────────────┤
│ [启动优化] [暂停] [停止] [干运行 ☐]                     │
└─────────────────────────────────────────────────────────┘
```

启动优化弹窗（QDialog）：

```
┌─────────────────────────────────────────────────────────┐
│ 启动闭环优化                                             │
├─────────────────────────────────────────────────────────┤
│ 项目配置: [her_feconi ▼]  (从 configs/projects/ 加载)   │
│                                                          │
│ 优化目标: [最小化 HER 过电位          ]                  │
│ 目标指标: [overpotential_mV ▼]                           │
│ 方向:     [minimize ▼]                                   │
│ 最大轮次: [10    ]                                       │
│                                                          │
│ 工作模式: [semi_auto ▼]                                  │
│   ○ full_auto  — 全自动，仅 CRITICAL 异常暂停           │
│   ● semi_auto  — 关键决策点需人工确认                    │
│   ○ manual     — 每步都需人工确认                        │
│                                                          │
│ 模板 ID:  [tpl_her_standard ▼]                           │
│ 元素:     [☑ Fe] [☑ Co] [☑ Ni]                          │
│ 干运行:   [☐]                                            │
│                                                          │
│ 高级选项:                                                │
│   ML 切换阈值: [5] 轮                                    │
│   L2 心跳监控: [☐ 启用]  间隔: [30] 秒                  │
│                                                          │
│              [取消]  [启动]                               │
└─────────────────────────────────────────────────────────┘
```


**对应后端 API**：

| 操作 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 启动优化 | POST | `/api/optimization/start` | body: goal/max_rounds/metric/direction/template/elements/work_mode/dry_run |
| 暂停优化 | POST | `/api/optimization/stop` | 优雅退出当前轮次 |
| 优化状态 | GET | `/api/optimization/status` | 返回 round/best/status/strategy/monitor_status |
| 重置 | DELETE | `/api/optimization/reset` | 仅限未运行时 |

**PySide6 组件**：

| 组件 | Qt 类 | 说明 |
| --- | --- | --- |
| 控制台面板 | QWidget + QVBoxLayout | 主容器 |
| 流水线进度 | 4 个 QLabel + QHBoxLayout | 设计→执行→分析→决策 |
| 最优结果 | QGroupBox | 配比 + 指标 |
| 启动弹窗 | QDialog | 参数输入表单 |
| 工作模式选择 | QComboBox | full_auto/semi_auto/manual |
| 按钮组 | QPushButton x3 | 启动/暂停/停止 |

**刷新策略**：轮询 `GET /api/optimization/status`，间隔 2 秒。

---

### 3.3 Tab 2: Agent 状态

展示 5 个 Agent + 5 个 Skill 的运行状态。

```
┌─────────────────────────────────────────────────────────┐
│ Agent 状态                                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ┌─ Orchestrator (运行管控) ──────────────────────────┐  │
│ │ 状态: ● 运行中  |  模型: Qwen3-Max                │  │
│ │ 内置技能:                                          │  │
│ │   DataAnalysisSkill      ● 就绪                    │  │
│ │   KnowledgeArchiveSkill  ● 就绪                    │  │
│ │ 共享技能:                                          │  │
│ │   KnowledgeQuerySkill    ● 就绪                    │  │
│ │ 最近: evaluate_and_decide -> continue              │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ┌─ ExperimentDesigner (实验设计) ────────────────────┐  │
│ │ 状态: ○ 空闲  |  模型: Gemini-3-Flash              │  │
│ │ 共享技能: KnowledgeQuerySkill ● 就绪               │  │
│ │ 策略: LLM 引导 (round < 5)                         │  │
│ │ ML 模型: 未就绪 (需 >= 10 数据点，当前 3)          │  │
│ │ 最近: design_experiment (round 3)                   │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ┌─ ExperimentExecutor (实验执行) ────────────────────┐  │
│ │ 状态: ● 运行中  |  LLM: Qwen3-Max (轻量)          │  │
│ │ 内置技能:                                          │  │
│ │   RealtimeMonitorSkill   ● 运行中 (L1)             │  │
│ │   HeartbeatInspector     ○ 关闭 (L2)               │  │
│ │ 共享技能: KnowledgeQuerySkill ● 就绪               │  │
│ │ 当前: 监控 run_20260318_xxx (步骤 3/8)             │  │
│ │ 连接: MicroHySeeker ● 端口 8100                    │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ┌─ DiagnosticsExpert (故障排查) ─────────────────────┐  │
│ │ 状态: ○ 空闲  |  模型: GLM-4.6 Thinking            │  │
│ │ 共享技能: KnowledgeQuerySkill ● 就绪               │  │
│ │ 已知故障库: 5 种模式                                │  │
│ │ 历史修复: 12 次 (成功率 83%)                        │  │
│ │ 最近: 无异常                                        │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ┌─ ChatAgent (综合问答) ─────────────────────────────┐  │
│ │ 状态: ● 就绪  |  模型: Qwen3-Max                   │  │
│ │ 共享技能: KnowledgeQuerySkill ● 就绪               │  │
│ │ 对话数: 15 条                                       │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ [刷新] [测试全部连接]                                    │
└─────────────────────────────────────────────────────────┘
```

**关键设计点**：
- 每个 Agent 卡片内嵌显示其专属 Skill 和共享 Skill 状态
- Executor 卡片显示 L1/L2 监控状态
- Designer 卡片显示 ML 模型就绪状态
- Diagnostics 卡片显示历史修复成功率

**对应后端 API**：`GET /api/agents/status`，间隔 5 秒。

**PySide6 组件**：

| 组件 | Qt 类 | 说明 |
| --- | --- | --- |
| Agent 卡片 | QGroupBox + QFormLayout | 每个 Agent 一个 |
| 状态指示 | QLabel (彩色圆点) | 绿/黄/红 |
| Skill 列表 | QLabel 列表 | 内嵌在 Agent 卡片中 |
| 滚动区域 | QScrollArea | 5 个卡片可能超出高度 |

---

### 3.4 Tab 3: 实验历史

```
┌─────────────────────────────────────────────────────────┐
│ 实验历史                                                 │
├─────────────────────────────────────────────────────────┤
│ 优化进度图 (pyqtgraph):                                 │
│                                                          │
│  过电位(mV)                                              │
│  250 | *                                                 │
│  225 |    *                                              │
│  200 |       *  *                                        │
│  182 |             * <- 当前最优                         │
│  150 |----------------------- 目标线                     │
│      +--+--+--+--+--+--                                 │
│         1  2  3  4  5  轮次                              │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ 轮次 | 配比              | 过电位  | 质量  | 决策       │
│------+-------------------+---------+-------+------------│
│  5   | Fe=0.30 Co=0.50   | 182.5   | 0.92  | continue   │
│  4   | Fe=0.35 Co=0.45   | 198.0   | 0.88  | continue   │
│  3   | Fe=0.40 Co=0.40   | 205.3   | 0.90  | continue   │
│  2   | Fe=0.25 Co=0.50   | 220.1   | 0.85  | continue   │
│  1   | Fe=0.33 Co=0.33   | 245.0   | 0.91  | continue   │
├─────────────────────────────────────────────────────────┤
│ [导出 CSV] [生成报告]                                    │
└─────────────────────────────────────────────────────────┘
```

点击某一轮展开详情（QDialog 或内嵌展开）：

```
┌─────────────────────────────────────────────────────────┐
│ 第 5 轮详情                                              │
├─────────────────────────────────────────────────────────┤
│ 设计参数:                                                │
│   Fe=0.30, Co=0.50, Ni=0.20                             │
│   策略: LLM 引导  来源: exp_designer                    │
│                                                          │
│ 分析结果 (DataAnalysisSkill):                            │
│   过电位: 182.5 mV  电流密度: 15.3 mA/cm2              │
│   Tafel 斜率: 68.2 mV/dec  质量评分: 0.92              │
│   vs 最优: -12.5 mV (改善 6.4%)                         │
│                                                          │
│ 决策 (Orchestrator):                                     │
│   动作: continue  原因: 性能持续改善                     │
│                                                          │
│ 环境快照:                                                │
│   时间: 2026-03-18 18:05:00                              │
│   设备: 全部正常  配置哈希: abc123                       │
│                                                          │
│ 归档: 已保存到知识库 experiments/ 分区                   │
└─────────────────────────────────────────────────────────┘
```

**对应后端 API**：`GET /api/optimization/history`，间隔 10 秒。

**PySide6 组件**：

| 组件 | Qt 类 | 说明 |
| --- | --- | --- |
| 进度图 | pyqtgraph.PlotWidget | 过电位趋势折线图 |
| 历史表格 | QTableWidget | 可点击展开详情 |
| 详情弹窗 | QDialog | 单轮完整信息 |
| 导出按钮 | QPushButton | CSV 导出 |


---

### 3.5 Tab 4: 监控面板（Phase 1 新增）

展示两层监控系统的实时状态。

```
┌─────────────────────────────────────────────────────────┐
│ 监控面板                                                 │
├─────────────────────────────────────────────────────────┤
│ L1 实时监控 (规则引擎)                    [● 运行中]    │
│ ┌───────────────────────────────────────────────────┐   │
│ │ 规则              │ 状态  │ 最近触发              │   │
│ │───────────────────┼───────┼───────────────────────│   │
│ │ 泵流速偏差 >15%   │ ● 正常│ -                     │   │
│ │ 通信超时 >10s     │ ● 正常│ -                     │   │
│ │ 步骤超时 >300s    │ ● 正常│ -                     │   │
│ │ 电位异常跳变      │ ● 正常│ -                     │   │
│ │ 泵压力异常        │ ● 正常│ -                     │   │
│ │ 数据质量 <0.5     │ ● 正常│ -                     │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ L2 心跳巡检 (Agent 级)          [○ 关闭] [开启/关闭]   │
│ ┌───────────────────────────────────────────────────┐   │
│ │ 间隔: 30s  上次巡检: 18:05:00                     │   │
│ │ 综合评估: 系统正常，无异常趋势                     │   │
│ │ 历史巡检: 12 次 (异常 0 次)                        │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ 异常历史:                                                │
│ ┌───────────────────────────────────────────────────┐   │
│ │ 时间       │ 级别    │ 来源 │ 描述                │   │
│ │────────────┼─────────┼──────┼─────────────────────│   │
│ │ 18:03:15   │ WARNING │ L1   │ 泵流速偏差 12%      │   │
│ │ 17:45:00   │ INFO    │ L2   │ 心跳正常            │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ [配置阈值] [清空历史] [导出]                             │
└─────────────────────────────────────────────────────────┘
```

配置阈值弹窗（QDialog）：

```
┌─────────────────────────────────────────────────────────┐
│ 监控阈值配置                                             │
├─────────────────────────────────────────────────────────┤
│ L1 规则引擎:                                             │
│   泵流速偏差阈值:    [15  ] %                            │
│   通信超时阈值:      [10  ] 秒                           │
│   步骤超时阈值:      [300 ] 秒                           │
│   电位跳变阈值:      [50  ] mV                           │
│   数据质量下限:      [0.5 ]                              │
│                                                          │
│ L2 心跳巡检:                                             │
│   巡检间隔:          [30  ] 秒                           │
│   启用:              [☐]                                 │
│                                                          │
│              [取消]  [保存]                               │
└─────────────────────────────────────────────────────────┘
```

**对应后端 API**：

| 操作 | 方法 | 路径 |
| --- | --- | --- |
| 监控状态 | GET | `/api/monitor/status` |
| 开关监控 | POST | `/api/monitor/toggle` |
| 修改配置 | PUT | `/api/monitor/config` |

**PySide6 组件**：

| 组件 | Qt 类 | 说明 |
| --- | --- | --- |
| L1 规则表 | QTableWidget | 6 条规则状态 |
| L2 状态区 | QGroupBox | 心跳巡检信息 |
| 异常历史表 | QTableWidget | 时间+级别+描述 |
| 配置弹窗 | QDialog + QFormLayout | 阈值编辑 |
| 开关按钮 | QPushButton (toggle) | L2 开关 |

**刷新策略**：轮询 `GET /api/monitor/status`，间隔 3 秒。

---

### 3.6 Tab 5: 审批面板（Phase 1 新增）

semi_auto 和 manual 模式下，关键决策需要人工确认。

```
┌─────────────────────────────────────────────────────────┐
│ 待审批决策                                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ┌─ 决策 #1 ─────────────────────────────────────────┐   │
│ │ 类型: 终止优化                                     │   │
│ │ 来源: Orchestrator                                 │   │
│ │ 时间: 2026-03-18 18:05:32                          │   │
│ │                                                    │   │
│ │ 建议: 终止优化                                     │   │
│ │ 原因: 连续 3 轮无显著改善 (< 2%)，                 │   │
│ │       当前最优 182.5 mV 已接近理论极限              │   │
│ │                                                    │   │
│ │ 当前最优: Fe=0.30 Co=0.50 Ni=0.20 → 182.5 mV     │   │
│ │ 改善趋势: 1.2% → 0.8% → 0.3% (递减)              │   │
│ │                                                    │   │
│ │ [批准终止]  [拒绝，继续优化]  [修改参数后继续]     │   │
│ └────────────────────────────────────────────────────┘   │
│                                                          │
│ ┌─ 决策 #2 ─────────────────────────────────────────┐   │
│ │ 类型: 异常处理                                     │   │
│ │ 来源: DiagnosticsExpert                            │   │
│ │ 时间: 2026-03-18 17:58:10                          │   │
│ │                                                    │   │
│ │ 建议: 重新校准泵并重试                             │   │
│ │ 原因: 泵 A 流速偏差 18%，超过阈值                  │   │
│ │ 修复方案: 执行泵校准程序 → 重试当前实验            │   │
│ │                                                    │   │
│ │ [批准修复]  [跳过此实验]  [手动处理]               │   │
│ └────────────────────────────────────────────────────┘   │
│                                                          │
│ 历史审批: 8 条 (批准 6 / 拒绝 2)                        │
│ [查看历史]                                               │
└─────────────────────────────────────────────────────────┘
```

**对应后端 API**：

| 操作 | 方法 | 路径 |
| --- | --- | --- |
| 获取待审批 | GET | `/api/approval/pending` |
| 提交审批 | POST | `/api/approval/respond` |

**PySide6 组件**：

| 组件 | Qt 类 | 说明 |
| --- | --- | --- |
| 决策卡片 | QGroupBox | 每个待审批决策一个 |
| 按钮组 | QPushButton x3 | 批准/拒绝/修改 |
| 滚动区域 | QScrollArea | 多个决策时滚动 |
| 历史弹窗 | QDialog + QTableWidget | 历史审批记录 |
| 通知徽章 | QLabel (红色圆点) | Tab 标题上显示待审批数量 |

**刷新策略**：轮询 `GET /api/approval/pending`，间隔 3 秒。有新审批时 Tab 标题显示红色徽章。

---

### 3.7 Tab 6: 对话面板（Phase 1 新增）

ChatAgent 的对话界面，支持自然语言查询和控制。

```
┌─────────────────────────────────────────────────────────┐
│ AI 对话                                                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [用户] 当前优化进度怎么样？                             │
│                                                          │
│  [AI] 当前第 5 轮，最优配比 Fe=0.30 Co=0.50 Ni=0.20，  │
│  过电位 182.5 mV。相比第 1 轮改善了 25.5%。             │
│  趋势：最近 3 轮改善幅度递减（6.4% → 3.2% → 0.3%），   │
│  建议考虑是否终止或调整搜索范围。                        │
│                                                          │
│  [用户] 知识库里有没有类似的 Fe-Co-Ni 催化剂文献？      │
│                                                          │
│  [AI] 找到 3 篇相关文献：                                │
│  1. "Fe-Co-Ni ternary HER catalyst" (2024) - 210 mV    │
│  2. "Optimization of Fe-Co alloy" (2025) - 195 mV      │
│  3. "Ni-based HER in alkaline" (2023) - 230 mV         │
│  你的当前结果 182.5 mV 优于所有文献报道。               │
│                                                          │
│  [用户] 暂停优化                                         │
│                                                          │
│  [AI] 已暂停优化。当前在第 5 轮结束后暂停。             │
│  输入"继续优化"可恢复。                                  │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ [输入消息...                                    ] [发送] │
│                                                          │
│ 快捷指令: [查看进度] [查知识库] [暂停] [生成报告]       │
└─────────────────────────────────────────────────────────┘
```

**对应后端 API**：

| 操作 | 方法 | 路径 |
| --- | --- | --- |
| 发送消息 | POST | `/api/chat` |
| 获取历史 | GET | `/api/chat/history` |

**PySide6 组件**：

| 组件 | Qt 类 | 说明 |
| --- | --- | --- |
| 消息列表 | QScrollArea + QVBoxLayout | 气泡式消息 |
| 用户消息 | QLabel (右对齐，蓝色背景) | 用户输入 |
| AI 消息 | QLabel (左对齐，灰色背景) | AI 回复 |
| 输入框 | QLineEdit | 消息输入 |
| 发送按钮 | QPushButton | 发送 |
| 快捷指令 | QPushButton x4 | 常用操作 |


---

### 3.8 Tab 7: 实时日志

```
┌─────────────────────────────────────────────────────────┐
│ 实时日志                                                 │
│ 筛选: [全部 ▼] [orchestrator ▼]  [搜索...          ]    │
├─────────────────────────────────────────────────────────┤
│ 18:05:32 [orchestrator] evaluate_and_decide -> continue │
│ 18:05:30 [orchestrator] DataAnalysisSkill 质量=0.92     │
│ 18:05:28 [exp_executor] 实验完成 run_20260318_xxx       │
│ 18:04:15 [exp_executor] L1 监控: 全部正常               │
│ 18:03:02 [exp_executor] 监控中... 步骤 5/8              │
│ 18:01:45 [exp_executor] 实验启动 tpl_her_standard       │
│ 18:01:40 [exp_designer] 设计完成 Fe=0.30 Co=0.50       │
│ 18:01:38 [orchestrator] 开始第 5 轮                     │
│ 18:01:35 [orchestrator] KnowledgeArchiveSkill 归档完成  │
│ ...                                                      │
├─────────────────────────────────────────────────────────┤
│ [清空] [导出日志] [自动滚动 ☑]                          │
└─────────────────────────────────────────────────────────┘
```

**对应后端 API**：WebSocket `/ws/agent-logs`（实时推送）。

**PySide6 组件**：

| 组件 | Qt 类 | 说明 |
| --- | --- | --- |
| 日志视图 | QPlainTextEdit (只读) | 实时日志 |
| Agent 筛选 | QComboBox | 按 Agent 过滤 |
| 级别筛选 | QComboBox | INFO/WARNING/ERROR |
| 搜索框 | QLineEdit | 关键词搜索 |
| 自动滚动 | QCheckBox | 自动滚到底部 |

---

### 3.9 Phase 1 前端任务列表

```
## Phase 1 前端任务

### [F1-01] 重构 agent_dashboard.py 为 Tab 架构
- 关联文件: `MicroHySeeker/src/ui/widgets/agent_dashboard.py` (重写)
- 产出: 7 Tab 框架（QTabWidget），保留现有连接逻辑
- 验收: Tab 切换正常，现有功能不丢失

### [F1-02] 优化控制台 Tab
- 依赖: F1-01
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/optimization_tab.py` (新增)
- 产出: 流水线进度、最优结果、启动弹窗、工作模式选择
- 验收: 能启动/暂停/停止优化，状态实时刷新

### [F1-03] Agent 状态 Tab
- 依赖: F1-01
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/agent_status_tab.py` (新增)
- 产出: 5 Agent 卡片 + Skill 状态内嵌
- 验收: 5 秒刷新，状态颜色正确

### [F1-04] 实验历史 Tab
- 依赖: F1-01
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/history_tab.py` (新增)
- 产出: pyqtgraph 趋势图 + 历史表格 + 详情弹窗
- 验收: 图表渲染正确，点击展开详情

### [F1-05] 监控面板 Tab
- 依赖: F1-01, 后端 P1-10
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/monitor_tab.py` (新增)
- 产出: L1 规则表 + L2 状态 + 异常历史 + 配置弹窗
- 验收: L1/L2 状态实时显示，阈值可配置

### [F1-06] 审批面板 Tab
- 依赖: F1-01, 后端 P1-14
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/approval_tab.py` (新增)
- 产出: 决策卡片 + 审批按钮 + 通知徽章
- 验收: 能接收待审批决策，提交审批结果

### [F1-07] 对话面板 Tab
- 依赖: F1-01, 后端 P1-18
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/chat_tab.py` (新增)
- 产出: 气泡式消息 + 输入框 + 快捷指令
- 验收: 能发送消息并收到 AI 回复

### [F1-08] 实时日志 Tab
- 依赖: F1-01
- 关联文件: `MicroHySeeker/src/ui/widgets/tabs/log_tab.py` (新增)
- 产出: WebSocket 日志推送 + 筛选 + 搜索
- 验收: 日志实时显示，筛选功能正常

### [F1-09] autohyseeker_client.py 扩展
- 关联文件: `MicroHySeeker/src/services/autohyseeker_client.py` (修改)
- 产出: 新增 monitor/approval/chat/knowledge API 调用方法
- 验收: 所有新 API 端点可调用

### [F1-10] 前端集成测试
- 依赖: 所有 F1 任务
- 产出: 手动测试清单 + 截图
- 验收: 所有 Tab 功能正常，与后端联调通过
```

### 3.10 Phase 1 前端并发安全

```
并行组 A（可同时进行）:
  F1-01  Tab 架构重构
  F1-09  client 扩展（不同文件）

并行组 B（A 完成后，全部可并行，各自独立文件）:
  F1-02  优化控制台 Tab
  F1-03  Agent 状态 Tab
  F1-04  实验历史 Tab
  F1-05  监控面板 Tab
  F1-06  审批面板 Tab
  F1-07  对话面板 Tab
  F1-08  实时日志 Tab

最后:
  F1-10  集成测试
```

---

## 四、Phase 2 前端规划 — 文献 + 科研产出 UI

Phase 2 在 Dashboard 中新增 3 个 Tab。

### 4.1 Dashboard 布局扩展

```
┌─────────────────────────────────────────────────────────┐
│  Agent Dashboard                                         │
│  [优化] [Agent] [历史] [监控] [审批] [对话] [日志]      │
│  [文献] [科研] [论文]                    ← Phase 2 新增 │
├─────────────────────────────────────────────────────────┤
│              (Tab 内容区域)                               │
└─────────────────────────────────────────────────────────┘
```

---

### 4.2 Tab 8: 文献管理（Phase 2A）

```
┌─────────────────────────────────────────────────────────┐
│ 文献管理                                                 │
├─────────────────────────────────────────────────────────┤
│ 检索:                                                    │
│ [Fe-Co-Ni HER electrocatalyst        ] [检索] [高级]    │
│ 来源: [☑ Google Scholar] [☑ Web of Science] [☐ PubMed] │
│ 最大结果: [50]                                           │
├─────────────────────────────────────────────────────────┤
│ 检索结果 (42 篇新文献):                                  │
│ ┌───────────────────────────────────────────────────┐   │
│ │ ☑ Fe-Co-Ni ternary catalyst for HER (2025)       │   │
│ │   DOI: 10.1021/xxx  相关度: 0.95  来源: Scholar  │   │
│ │ ☑ Optimization of Fe-Co alloy... (2024)           │   │
│ │   DOI: 10.1039/xxx  相关度: 0.88  来源: WoS      │   │
│ │ ☐ Ni-based catalyst review (2023)                 │   │
│ │   DOI: 10.1002/xxx  相关度: 0.72  来源: Scholar  │   │
│ │ ...                                               │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ [全选] [反选] [下载选中 (35篇)] [生成下载清单]          │
├─────────────────────────────────────────────────────────┤
│ 下载进度:                                                │
│ ████████████░░░░░░░░ 60% (21/35)  失败: 2              │
├─────────────────────────────────────────────────────────┤
│ 已入库文献: 128 篇                                       │
│ [查看已入库] [手动导入 PDF] [刷新]                       │
└─────────────────────────────────────────────────────────┘
```

手动导入弹窗：

```
┌─────────────────────────────────────────────────────────┐
│ 手动导入 PDF                                             │
├─────────────────────────────────────────────────────────┤
│ 将 PDF 文件放入以下目录:                                 │
│ AutoHySeeker/data/literature/                            │
│                                                          │
│ 检测到 5 个未入库 PDF:                                   │
│ ☑ paper_001.pdf (2.3 MB)                                │
│ ☑ paper_002.pdf (1.8 MB)                                │
│ ☑ paper_003.pdf (3.1 MB)                                │
│ ☐ paper_004.pdf (0.5 MB) - 已入库                       │
│ ☑ paper_005.pdf (2.0 MB)                                │
│                                                          │
│ [解析并入库 (4篇)]  [取消]                               │
└─────────────────────────────────────────────────────────┘
```

**对应后端 API**：

| 操作 | 方法 | 路径 |
| --- | --- | --- |
| 检索文献 | POST | `/api/literature/search` |
| 下载文献 | POST | `/api/literature/download` |
| 解析入库 | POST | `/api/literature/ingest` |
| 已入库列表 | GET | `/api/literature/list` |


---

### 4.3 Tab 9: 科研分析（Phase 2B）

```
┌─────────────────────────────────────────────────────────┐
│ 科研分析                                                 │
├─────────────────────────────────────────────────────────┤
│ 分析范围:                                                │
│ 项目: [her_feconi]  实验: [全部] / [选择特定轮次]       │
├─────────────────────────────────────────────────────────┤
│ 深度分析:                                                │
│   性能排名:                                              │
│     #1 Fe=0.30 Co=0.50 Ni=0.20 -> 182.5 mV             │
│     #2 Fe=0.35 Co=0.45 Ni=0.20 -> 198.0 mV             │
│                                                          │
│   配比-性能关系:                                         │
│     Co 含量与过电位呈 U 型关系，最优区间 45-55%         │
│     Fe 含量 > 40% 时性能显著下降                         │
│                                                          │
│   机理推断:                                              │
│     Tafel 斜率 68 mV/dec -> Volmer-Heyrovsky 机理       │
│                                                          │
│   统计显著性:                                            │
│     最优 vs 次优: p=0.023 (显著)                         │
│                                                          │
│ 数据缺口:                                                │
│   ! 缺少 EIS 数据 (优先级: 高)                           │
│   ! 未做稳定性测试 (优先级: 高)                          │
│   ? Co 45-55% 区间数据不足 (优先级: 中)                 │
│   数据完整度: 65%                                        │
│                                                          │
│ [运行深度分析] [识别数据缺口] [文献对比]                │
├─────────────────────────────────────────────────────────┤
│ 科研绘图:                                                │
│ 期刊风格: [Nature Energy]                                │
│ 图表类型:                                                │
│   [x LSV 极化曲线] [x Tafel 图] [ EIS Nyquist]         │
│   [x 优化收敛图] [x 配比热力图] [x 文献对比柱状图]    │
│                                                          │
│ [生成图表]                                               │
│                                                          │
│ 已生成图表:                                              │
│ [LSV 曲线] [Tafel 图] [收敛图]                          │
│ 每个可 [预览] [导出]                                     │
└─────────────────────────────────────────────────────────┘
```

对应后端 API：

| 操作 | 方法 | 路径 |
| --- | --- | --- |
| 深度分析 | POST | `/api/research/deep-analysis` |
| 数据缺口 | POST | `/api/research/data-gaps` |
| 生成图表 | POST | `/api/research/figures` |
| 文献对比 | POST | `/api/research/comparison` |

---

### 4.4 Tab 10: 论文辅助（Phase 2B）

```
┌─────────────────────────────────────────────────────────┐
│ 论文撰写辅助                                             │
├─────────────────────────────────────────────────────────┤
│ 项目: [her_feconi]  语言: [English]                     │
├─────────────────────────────────────────────────────────┤
│ 段落生成:                                                │
│ [Results & Discussion]  [Experimental]                   │
│ [Introduction snippet]  [Figure Captions]                │
│ [Abstract]                                               │
│                                                          │
│ 生成结果:                                                │
│   Results and Discussion                                 │
│                                                          │
│   The optimized Fe0.3Co0.5Ni0.2 catalyst exhibited      │
│   an overpotential of 182.5 mV at 10 mA/cm2, which     │
│   is among the lowest reported for Fe-Co-Ni ternary     │
│   catalysts (Table 1). The Tafel slope of 68 mV/dec     │
│   suggests a Volmer-Heyrovsky mechanism...               │
│                                                          │
│   References used: [12], [15], [23]                      │
│   Word count: 850                                        │
│                                                          │
│ [复制到剪贴板] [导出 Word] [重新生成]                   │
├─────────────────────────────────────────────────────────┤
│ 参考文献:                                                │
│ 格式: [ACS]                                              │
│ [生成参考文献列表] [导出 BibTeX] [导出 EndNote]         │
└─────────────────────────────────────────────────────────┘
```

对应后端 API：

| 操作 | 方法 | 路径 |
| --- | --- | --- |
| 生成段落 | POST | `/api/research/draft` |
| 参考文献 | POST | `/api/research/references` |


---

### 4.5 Phase 2 前端任务列表

```
[F2-01] 文献管理 Tab
- 依赖: 后端 Phase 2A
- 文件: MicroHySeeker/src/ui/widgets/tabs/literature_tab.py (新增)
- 产出: 检索 + 下载清单 + 进度条 + 手动导入
- 验收: 能检索、下载、手动导入 PDF

[F2-02] 科研分析 Tab
- 依赖: 后端 Phase 2B
- 文件: MicroHySeeker/src/ui/widgets/tabs/research_tab.py (新增)
- 产出: 深度分析 + 数据缺口 + 科研绘图 + 文献对比
- 验收: 能生成图表并预览，文献对比表格正确

[F2-03] 论文辅助 Tab
- 依赖: 后端 Phase 2B
- 文件: MicroHySeeker/src/ui/widgets/tabs/writing_tab.py (新增)
- 产出: 段落生成 + 参考文献导出
- 验收: 能生成论文段落，导出 BibTeX

[F2-04] autohyseeker_client.py Phase 2 扩展
- 文件: MicroHySeeker/src/services/autohyseeker_client.py (修改)
- 产出: 新增 literature/research API 调用方法
- 验收: 所有 Phase 2 API 端点可调用

[F2-05] Phase 2 集成测试
- 依赖: 所有 F2 任务
- 产出: 手动测试清单 + 截图
- 验收: 所有新 Tab 功能正常
```

---

## 五、前端文件结构（完整）

```
MicroHySeeker/src/
  ui/
    main_window.py                    # 主窗口（已有，需微调嵌入点）
    widgets/
      agent_dashboard.py              # 重构为 Tab 架构（F1-01）
      tabs/                           # 新增目录
        __init__.py
        optimization_tab.py           # Tab 1: 优化控制台（F1-02）
        agent_status_tab.py           # Tab 2: Agent 状态（F1-03）
        history_tab.py                # Tab 3: 实验历史（F1-04）
        monitor_tab.py                # Tab 4: 监控面板（F1-05）
        approval_tab.py               # Tab 5: 审批面板（F1-06）
        chat_tab.py                   # Tab 6: 对话面板（F1-07）
        log_tab.py                    # Tab 7: 实时日志（F1-08）
        literature_tab.py             # Tab 8: 文献管理（F2-01）
        research_tab.py               # Tab 9: 科研分析（F2-02）
        writing_tab.py                # Tab 10: 论文辅助（F2-03）
    dialogs/
      ...（已有弹窗）

  services/
    autohyseeker_client.py            # 扩展（F1-09, F2-04）
    experiment_data_manager.py        # 已有，不修改
```

---

## 六、数据刷新策略汇总

| Tab | 数据源 | 刷新方式 | 频率 |
| --- | --- | --- | --- |
| 优化控制台 | /api/optimization/status | QTimer 轮询 | 2 秒 |
| Agent 状态 | /api/agents/status | QTimer 轮询 | 5 秒 |
| 实验历史 | /api/optimization/history | QTimer 轮询 | 10 秒 |
| 监控面板 | /api/monitor/status | QTimer 轮询 | 3 秒 |
| 审批面板 | /api/approval/pending | QTimer 轮询 | 3 秒 |
| 对话面板 | /api/chat | 用户触发 | 按需 |
| 实时日志 | WebSocket /ws/agent-logs | 推送 | 实时 |
| 文献管理 | /api/literature/* | 用户触发 | 按需 |
| 科研分析 | /api/research/* | 用户触发 | 按需 |
| 论文辅助 | /api/research/* | 用户触发 | 按需 |


---

## 七、PySide6 技术要点

### 7.1 异步 HTTP 请求

所有 API 调用必须在后台线程执行，避免阻塞 UI：

```python
# 使用 QThread + Signal 模式
class ApiWorker(QThread):
    result_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, client_method, *args):
        super().__init__()
        self.client_method = client_method
        self.args = args

    def run(self):
        try:
            result = self.client_method(*self.args)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
```

### 7.2 WebSocket 连接

实时日志使用 WebSocket：

```python
from PySide6.QtWebSockets import QWebSocket

class LogWebSocket(QObject):
    log_received = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.ws = QWebSocket()
        self.ws.textMessageReceived.connect(self._on_message)
        self.ws.open(QUrl(url))

    def _on_message(self, message: str):
        self.log_received.emit(message)
```

### 7.3 Tab 通知徽章

审批面板有新待审批时显示红色徽章：

```python
def update_approval_badge(self, count: int):
    if count > 0:
        self.tab_widget.setTabText(4, f"审批 ({count})")
    else:
        self.tab_widget.setTabText(4, "审批")
```

### 7.4 PySide6 组件总表

| 组件 | Qt 类 | 用途 |
| --- | --- | --- |
| Dashboard 面板 | QDockWidget | 嵌入主窗口右侧 |
| Tab 切换 | QTabWidget | 10 个 Tab |
| 优化进度图 | pyqtgraph.PlotWidget | 过电位趋势 |
| Agent 卡片 | QGroupBox + QFormLayout | 状态展示 |
| 实验表格 | QTableWidget | 历史记录 |
| 日志视图 | QPlainTextEdit | 实时日志 |
| 启动弹窗 | QDialog | 优化参数输入 |
| 监控规则表 | QTableWidget | L1 规则状态 |
| 审批卡片 | QGroupBox | 决策审批 |
| 对话气泡 | QLabel (styled) | 聊天消息 |
| 图表预览 | QLabel + QPixmap | matplotlib 渲染 |

---

## 八、向后兼容

旧 Agent 名称（data_analyst、knowledge_mgr、exp_supervisor）在 API 路由中通过 _AGENT_ALIASES 自动映射到 orchestrator，UI 无需特殊处理。

---

> 本文档定义了 AutoHySeeker 前端的完整技术方案（Phase 1 + Phase 2）。
> 前端任务编号以 F 开头（F1-xx / F2-xx），后端任务编号以 P 开头（P1-xx）。
> 前端任务需在 PROGRESS_TRACKER.md 中认领和追踪，规则同后端。

**更新日期**: 2026-03-18
**版本**: 3.0
**状态**: 待审核

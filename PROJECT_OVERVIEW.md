# MicroHySeeker × AutoHySeeker 项目全景学习文档

> 适用读者：希望快速了解本课题全貌的新成员、合作者或 AI 助手
> 文档日期：2026-04-02

---

## 一、课题背景：我们在研究什么？

本课题研究的核心问题是：**如何用自动化实验手段，高效筛选出性能最优的可以抵抗反向电流的析氢反应的（Hydrogen Evolution Reaction, HER）催化剂的元素配比？**

HER 是电解水制氢的关键半反应，催化剂的性能（过电位、电流密度等）强烈依赖于活性元素的组合比例（例如 Fe、Co、Ni 三种金属的混合浓度）。传统手动实验需要反复配液、反复测量，效率极低；本课题的目标是构建一套**硬件自动化 + AI 智能决策**的联合系统，让实验"自己跑"、"自己优化"。

```
目标：
  给定优化目标（最大化 HER 电流密度、最小化过电位、提升反向电流耐受性）
  → 自动设计实验参数（元素配比）
  → 自动控制仪器完成实验
  → 自动分析采集到的电化学数据（析氢性能 + 反向电流特性）
  → 自动决策下一组参数
  → 循环，直到找到最优配比
```

整个系统由两个模块协同实现：**MicroHySeeker**（硬件控制端）和 **AutoHySeeker**（AI 决策端）。

---

## 二、两个模块的定位与分工

```
┌──────────────────────────────────────────────────────────────────┐
│                        AutoHySeeker                              │
│   AI 多 Agent 科研平台（Python + FastAPI + LangGraph）           │
│   职责：实验设计 / 闭环决策 / 数据分析 / 知识积累 / 科研产出     │
│   端口：8200                                                     │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP API 调用（POST /api/...）
                            │ 下达：实验参数（元素配比、步骤参数）
                            │ 上报：实验状态/数据/异常
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                        MicroHySeeker                             │
│   硬件控制桌面应用（Python + PySide6 + RS485 + CHI DLL）         │
│   职责：驱动真实仪器完成实验 / 采集电化学数据                    │
│   端口：8100                                                     │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼ 物理连接（RS485 串口 / CHI DLL）
              ┌─────────────────────────────────┐
              │         真实实验硬件              │
              │  RS485 蠕动泵（配液）             │
              │  CHI 电化学工作站（测量）         │
              │  冲洗泵系统（清洗管路）           │
              └─────────────────────────────────┘
```

| 维度      | MicroHySeeker                                      | AutoHySeeker                                       |
| --------- | -------------------------------------------------- | -------------------------------------------------- |
| 定位      | 硬件控制层                                         | AI 决策层                                          |
| 技术栈    | Python + PySide6（桌面 GUI）+ RS485 驱动 + CHI DLL | Python + FastAPI + LangGraph + React Web Dashboard |
| 运行方式  | 本地桌面程序，直接连接仪器                         | Web 服务，HTTP API 对外暴露                        |
| 知识/数据 | 实时采集电化学曲线、日志                           | 存储实验历史、分析结果、文献知识                   |
| 主动性    | 被动执行（收到指令后动作）                         | 主动决策（自主规划实验方向）                       |

**协作方式**：AutoHySeeker 通过 HTTP 调用 MicroHySeeker 的 API（如 `/api/template/{id}/instantiate`）下达实验任务；MicroHySeeker 驱动真实仪器，并通过 API 返回实验状态和数据给 AutoHySeeker。

---

## 三、MicroHySeeker 详解：大致组成

MicroHySeeker 是从 C# WinForms 项目（eChemSDL）迁移而来的 Python 重写版本，采用 **PySide6** 构建桌面 GUI，以 **FastAPI** 暴露 HTTP 接口供 AutoHySeeker 调用。

### 3.1 整体架构图

```
┌──────────────────────────────────┐
│         UI Layer (PySide6)       │
│  主窗口 / 实验配置 / 程序编辑     │
│  手动控制 / 冲洗调试 / 日志查看   │
└─────────────┬────────────────────┘
              │ Qt 信号/槽
┌─────────────▼────────────────────┐
│         Context / Engine         │
│  LibContext（依赖注入容器）       │
│  ExperimentEngine（实验状态机）   │
│  ExpProgram + ProgStep           │
└─────────────┬────────────────────┘
              │ 调用
┌─────────────▼────────────────────┐
│         Service Layer            │
│  SettingsService（配置读写）      │
│  LoggerService（带信号的日志）    │
│  TranslatorService（多语言）      │
│  DataExporter（CSV/Excel 导出）   │
│  KafkaClient（可选消息队列）      │
└─────────────┬────────────────────┘
              │ 调用
┌─────────────▼────────────────────┐
│          Hardware Layer          │
│  RS485Driver（RS485 串口驱动）    │
│  PumpManager（泵管理器）          │
│  Diluter × N（配液泵，动态数量）  │
│  Flusher（冲洗泵系统）            │
│  CHIInstrument（电化学工作站）    │
└─────────────┬────────────────────┘
              │ 物理连接
         真实仪器设备
```

### 3.2 各层模块说明

#### A. 硬件层（Hardware）— 直接与仪器通信

| 模块                    | 文件                         | 职责                                                                                                                                  |
| ----------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **RS485Driver**   | `hardware/rs485_driver.py` | RS485 串口驱动：帧封装/发送/接收/校验/回调分发；支持任意数量设备，地址由配置决定                                                      |
| **Diluter**       | `hardware/diluter.py`      | 单个配液泵的业务封装：计算注射体积→转换分度→发送 RS485 命令→状态跟踪；泵数量完全动态（6、9 或更多），由配置文件定义                |
| **Flusher**       | `hardware/flusher.py`      | 冲洗/管路清洁控制：管理进液泵/出液泵/转移泵三个角色，按顺序定时驱动完成冲洗循环                                                       |
| **CHIInstrument** | `hardware/chi.py`          | 封装 CH Instruments 电化学工作站 DLL（libec.dll）：设置 CV/LSV/i-t 技术参数，启动实验，轮询采集数据，导出 CSV；支持无设备时的模拟模式 |

**RS485 协议关键点**：

- 帧头 `0xFA`（请求）/ `0xFB`（响应）；逐字节求和校验
- 串口默认 38400 baud, 8N2
- 驱动层不感知泵的业务含义，只按地址路由帧

#### B. Context / Engine — 实验核心

| 模块                       | 职责                                                                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **LibContext**       | 依赖注入容器：持有所有设备实例、配置、运行时数据（曲线、ExpID）；按 RS485 地址动态路由帧到正确的 Diluter 实例                               |
| **ExperimentEngine** | 实验状态机：QTimer 驱动 1s tick；调度 Diluter/Flusher/CHI 按步骤顺序执行；管理组合参数矩阵遍历                                   |
| **ExpProgram**       | 实验程序：维护步骤列表和可变参数（起始值/终值/步长）；生成参数组合矩阵（笛卡尔积），支持跳过指定组合                                        |
| **ProgStep**         | 单个实验步骤：类型包括 PrepSol（配液）/ EChem（电化学）/ Flush（冲洗）/ Transfer（移液）/ Blank（空白等待）；含状态判定逻辑 |

**实验状态机流程**：

```
加载 ExpProgram
  → FillParamMatrix（生成组合矩阵）
  → PrepareSteps（预计算每步参数与时长）
  → Tick 驱动：
      当前步骤 idle → 初始化并执行（调用硬件）
      当前步骤 running → 查询硬件状态（pumps/CHI）
      当前步骤完成 → 前进到下一步
      全部步骤完成 → 切换下一组参数，重新执行
      全部组合完成 → 实验结束，导出数据
```

#### C. 服务层（Services）

| 模块                  | 职责                                                          |
| --------------------- | ------------------------------------------------------------- |
| `SettingsService`   | 读写 `settings.json`/`defaults.json`；配置合并与校验      |
| `LoggerService`     | 线程安全结构化日志，通过 Qt 信号推送到 UI 和日志文件          |
| `TranslatorService` | 键值翻译，支持热切换中/英语言                                 |
| `DataExporter`      | 实验结束后将曲线数据导出为 CSV/Excel，文件名含 ExpID 和时间戳 |
| `KafkaClient`       | 可选：将实验事件发布到 Kafka（用于外部系统集成）              |

#### D. UI 层（PySide6 桌面 GUI）

| 界面组件                | 职责                                                   |
| ----------------------- | ------------------------------------------------------ |
| `MainWindow`          | 主窗口：实验启动/停止、状态显示、曲线渲染、心跳 QTimer |
| `ConfigDialog`        | 系统配置（泵参数、串口、路径等）                       |
| `ProgramEditorDialog` | 实验程序编辑（步骤列表、参数范围）                     |
| `ComboEditorDialog`   | 组合参数矩阵预览与管理                                 |
| `ManualControlDialog` | 手动控制各泵（调试用）                                 |
| `FlusherDialog`       | 冲洗系统调试界面                                       |
| `RS485TestDialog`     | RS485 通信测试界面                                     |
| `LogViewerDialog`     | 实验日志全文查看                                       |

#### E. HTTP API 层（供 AutoHySeeker 调用）

MicroHySeeker 通过本地 FastAPI 服务（端口 8100）对外暴露控制接口，AutoHySeeker 通过这些接口下达任务：

- `POST /api/template/{id}/instantiate` — 实例化实验模板（指定元素配比和体积）
- `GET /api/experiment/status` — 查询当前实验运行状态
- `GET /api/optimization/status` — 查询优化任务状态（health 等）

---

## 四、AutoHySeeker 详解：目标与架构

### 4.1 核心定位

AutoHySeeker 是一个 **闭环自驱动实验室（Self-Driving Lab, SDL）的 AI 代理层**，其目标是：

> **自主规划、执行并优化 HER 催化剂的元素配比实验，最终在人工监督下找到最优配比，并产出可发表级科研成果。**

### 4.2 当前架构（4 Agent + Skill）

```
┌────────────────────────────────────────────────────────────────┐
│                      用户交互层                                 │
│   Web Dashboard（React 18 + Vite + Tailwind）                  │
│   Chat 窗口 / 实验控制台 / Agent 状态面板                      │
└──────────────────────────┬─────────────────────────────────────┘
                           │ HTTP (端口 8200)
┌──────────────────────────▼─────────────────────────────────────┐
│                   LangGraph 路由层                              │
│   意图识别 → 分发到对应 Agent                                  │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                ┌──────────▼──────────┐
                │  Orchestrator Agent  │  ← 大脑/调度中心
                │  LLM: Qwen3-Max      │
                │  ┌─DataAnalysis Skill │
                │  └─KnowledgeArchive  │
                └──────────┬──────────┘
              ┌────────────┼─────────────────┐
              ▼            ▼                  ▼
    ┌──────────────┐  ┌───────────────┐  ┌──────────────┐
    │  Designer    │  │   Executor    │  │  Diagnostics │
    │  实验设计    │  │   实验执行    │  │  故障排查    │
    │ Gemini-Flash │  │  Qwen3-Max   │  │ GLM-4.6 Think│
    └──────────────┘  └───────────────┘  └──────────────┘
              │            │                  │
              └────────────▼──────────────────┘
                    知识库工具 (OpenViking)
                    实验控制工具 (MicroHySeeker API)
```

### 4.3 各 Agent 职责

#### Orchestrator（运行管控 Agent）— 整个系统的大脑

- 接收优化目标（如"Fe:Co:Ni 最优配比，最大化 HER 催化性能并兼顾反向电流耐受性"）
- 协调 Designer/Executor/Diagnostics 三个 Agent 的工作流程
- 调用 **DataAnalysisSkill** 提取电化学数据指标（过电位 overpotential、电流密度 current density、反向电流耐受性 reverse-current stability）
- 调用 **KnowledgeArchiveSkill** 将实验结果归档到知识库
- 做出"继续优化/重试/目标达成"的决策
- 维持人机协作（需要用户确认时暂停并通知）

#### ExperimentDesigner（实验设计 Agent）— 参数生成

- 接收 Orchestrator 下发的优化方向
- 三阶段策略生成实验参数：
  1. **文献阶段**：查询 OpenViking 知识库中的已有文献，寻找有效配比区间
  2. **LLM 阶段**：基于 LLM 推断有价值的新配比
  3. **ML+LLM 阶段**（后期）：结合历史实验数据用机器学习模型（贝叶斯优化等）推荐配比
- 输出结构化参数：`target_concentrations = {"Fe": 0.3, "Co": 0.5, "Ni": 0.2}`

#### ExperimentExecutor（实验执行 Agent）— 实验监控

- 接收 Designer 生成的参数，调用 MicroHySeeker API 实例化并启动实验
- 双层监控：
  - **L1（代码级规则引擎）**：监控泵转速偏差、通信超时、步骤超时、空数据、电流突变等
  - **L2（Agent 级心跳巡检）**：定期轮询实验进度，检测卡死/异常
- 异常分级：LOW（记录继续）/ MEDIUM（上报 Orchestrator）/ HIGH（紧急停止）
- 实验完成后汇报结果给 Orchestrator

#### DiagnosticsExpert（故障排查 Agent）— 异常诊断

- 接收 Orchestrator 转发的异常上报
- 查询 OpenViking 知识库（运维库）中的历史故障记录，判断是否见过类似问题
- LLM 推断故障原因，生成修复方案
- 返回 `{can_resolve: bool, action: "..."}`，可解决时由 Executor 执行修复

### 4.4 知识库层（OpenViking）

OpenViking 是 AutoHySeeker 的向量知识库引擎（embedded mode），存储跨越多个维度的知识：

| 分区             | 存储内容                             |
| ---------------- | ------------------------------------ |
| `experiments/` | 每次实验的参数、结果、数据分析指标   |
| `literature/`  | 解析后的文献（标题、方法、性能数据） |
| `operations/`  | 运维日志、故障处理记录               |
| `analysis/`    | 数据分析报告、绘图                   |
| `projects/`    | 项目级的配置和里程碑记录             |

写入后自动触发 LLM 摘要生成 + embedding 向量化，支持语义搜索。

### 4.5 前端 Web Dashboard

React 18 + TypeScript + Vite + Tailwind CSS 构建独立 Web 界面：

- **实验控制台**：启动/停止优化循环，查看实验进度
- **Agent 状态面板**：实时显示各 Agent 运行状态
- **Chat 窗口**：自然语言交互（"上一次 Fe:Co 1:1 的结果怎么样？"/"帮我暂停实验"）
- **数据看板**：历史实验的性能指标趋势图

---

## 五、两个模块的协作详解

### 5.1 典型实验循环（端到端）

```
用户在 AutoHySeeker Dashboard 设定优化目标
         │
         ▼
Orchestrator 启动闭环优化循环
         │
         ▼
Designer 生成配比：Fe=30%, Co=50%, Ni=20%，总体积 1000µL
         │
         ▼
Executor 调用 MicroHySeeker API：
  POST http://localhost:8100/api/template/{id}/instantiate
  {
    "target_concentrations": {"Fe": 0.3, "Co": 0.5, "Ni": 0.2},
    "total_volume_ul": 1000
  }
         │
         ▼
MicroHySeeker 接收任务
  → 计算各泵注射体积（Diluter.Prepare）
  → RS485 驱动泵注液（Diluter.Infuse）
  → 冲洗系统清洗管路（Flusher.flush）
  → CHI 工作站运行 CV/LSV/i-t（CHIInstrument.RunExperiment）
  → 实验完成，数据已保存为 CSV
         │
         ▼
Executor 轮询状态：GET /api/experiment/status → "completed"
         │
         ▼
Orchestrator.DataAnalysisSkill 读取 CSV 数据：
  提取 overpotential = -180 mV, current density = 42 mA/cm²
  反向电流稳定性指标（i-t 曲线衰减率）
         │
         ▼
Orchestrator.KnowledgeArchiveSkill 归档本次实验到 OpenViking
         │
         ▼
Orchestrator 决策：性能有提升，指示 Designer 继续优化
         │
         ▼
↩ 循环，直到达到目标或用户终止
```

### 5.2 异常处理链路

```
MicroHySeeker 泵卡死（无响应）
         │
         ▼
Executor 的 L1 监控规则引擎触发（泵无响应超阈值）
         │
         ▼
Executor 上报 Orchestrator（severity: MEDIUM）
         │
         ▼
Orchestrator 派发到 DiagnosticsExpert
         │
         ▼
Diagnostics 查询知识库：以前遇到过类似问题吗？
  → 检索到：该问题通常是 RS485 地址冲突，重置地址后恢复
         │
         ▼
Diagnostics 返回修复方案，Executor 执行
  → MicroHySeeker 重置泵地址
         │
         ▼
实验恢复继续
```

---

## 六、AutoHySeeker 的科研创新潜力

当前系统处于 Phase 1（实验闭环）阶段，已具备基本的闭环自动化能力。其科研创新价值体现在以下几个层次：

### 6.1 当前已实现的科研基础

- [x] 基础 Agent 框架（Orchestrator / Designer / Executor / Diagnostics）
- [x] OpenViking 知识库集成与分区 CRUD
- [x] L1/L2 双层实验监控
- [x] 前后端连通（FastAPI + React Dashboard）
- [x] 16 项 E2E 测试通过
- [ ] Chat Agent（自然语言交互入口）
- [ ] 贝叶斯/ML 优化算法接入 Designer
- [ ] 完整的人机协作决策节点

### 6.2 近期科研创新目标（Phase 2）

**文献驱动的假设生成**
- LiteratureAgent 自动解析 HER 文献，提取成功配比区间与关键结论
- Designer 将文献知识与 ML 优化模型结合，生成**有文献依据的实验假设**，而非盲目搜索
- 实验结果可与文献 benchmark 自动对标，量化本课题催化剂的相对竞争力

**双目标协同优化**
- 同时优化两个科学问题：**HER 催化活性**（过电位、Tafel 斜率、交换电流密度）与**反向电流耐受性**（i-t 稳定性、衰减率）
- 通过帕累托前沿分析找到两者的最优权衡区间，提供传统手动实验无法高效实现的多维性能地图

**数据驱动的催化机理理解**
- 累积大量系统性实验数据后，AI 可从中挖掘**元素配比–电化学性能的内在规律**（如 Co 含量与反向电流稳定性的相关性、Ni 加入对 Tafel 斜率的影响等）
- 这些规律形成新的科学知识，而非仅仅是"最优点"，具备独立发表价值

### 6.3 长远科研创新方向

| 创新方向 | 科研意义 |
| -------- | -------- |
| **AI 辅助科学假设生成** | 系统根据知识库自主提出新的催化机理假设，供研究者验证；从"优化工具"升级为"科研伙伴" |
| **实验知识自动积累** | 每次实验结果入库后自动更新优化模型；随时间推移，系统对 Fe-Co-Ni 体系的认知持续深化，形成领域专有知识库 |
| **论文级数据分析与写作辅助** | 自动生成符合期刊标准的电化学图表（Tafel plot、CV、i-t、EIS）以及结果描述草稿，缩短从实验到发表的周期 |
| **跨体系迁移** | 积累的优化方法论和 Agent 框架可迁移到 OER、CO₂RR 等其他电化学体系，形成通用 AI 辅助电化学科研范式 |
| **开放科学贡献** | 完整的实验参数、流程、数据自动存档，支持科学可重复性；为 AI for Science 领域提供真实物理实验的标准数据集 |

---

## 七、快速上手指南

### 启动 MicroHySeeker

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 运行桌面应用（PySide6 GUI）
python -m src.app
```

- 连接 RS485 串口（COM3 等），配置泵参数
- 可独立运行，无需 AutoHySeeker 也能完成实验

### 启动 AutoHySeeker

```bash
cd AutoHySeeker

# 后端（FastAPI，端口 8200）
python -m uvicorn src.main:app --host 0.0.0.0 --port 8200

# 前端（Vite，端口 5174）
cd frontend
npm run dev
```

- 访问 `http://localhost:5174` 打开 Web Dashboard
- 前端通过 Vite proxy 转发 `/api` 请求到后端 8200

### 关键接口

| 接口                                                         | 说明                      |
| ------------------------------------------------------------ | ------------------------- |
| `GET http://localhost:8200/health`                         | AutoHySeeker 后端健康检查 |
| `GET http://localhost:8100/api/optimization/status`        | MicroHySeeker 状态        |
| `POST http://localhost:8200/api/experiments`               | 创建实验任务              |
| `POST http://localhost:8100/api/template/{id}/instantiate` | 实例化实验模板            |

---

## 八、技术栈速查

| 组件              | 技术                                                               |
| ----------------- | ------------------------------------------------------------------ |
| MicroHySeeker GUI | Python + PySide6（Qt）                                             |
| MicroHySeeker API | FastAPI（端口 8100）                                               |
| 硬件通信          | RS485 串口（38400, 8N2）+ CHI DLL（libec.dll）                     |
| AutoHySeeker 后端 | Python + FastAPI + LangGraph（端口 8200）                          |
| AutoHySeeker 前端 | React 18 + TypeScript + Vite + Tailwind CSS                        |
| AI 模型（Agent）  | Qwen3-Max / Gemini-3-Flash / GLM-4.6 Thinking                      |
| 知识库            | OpenViking（embedded，LevelDB + 向量索引）                         |
| 向量模型          | baai/bge-m3（1024 dim，via shengsuanyun.com）                      |
| 配置格式          | JSON（MicroHySeeker settings.json）+ TOML（AutoHySeeker configs/） |

---

*如需深入了解某一模块，请参阅 `docs/` 目录下对应的详细开发文档（`dev_hardware_*.md`、`multiagent_0*.md` 等）。*

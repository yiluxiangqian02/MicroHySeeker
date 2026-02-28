# AutoHySeeker 创新提案 — OpenViking 魔改 + Agent 架构创新

> 2026-02-27 | 状态：**提案讨论阶段**
> 基于对 OpenViking 源码（本地 clone）的深度分析 + MicroHySeeker 现有架构
> **原则：创新必须有效，不为创新而创新**

---

## 〇、背景

通读 OpenViking 全部源码后，发现其核心架构（AGFS 文件系统 + L0/L1/L2 分层 + Session 记忆自迭代 + 层级检索）是一个非常好的基底，但它是为 **通用 AI Agent** 设计的——对电化学实验这种 **数值密集 + 硬件交互 + 多 Agent 协作** 的场景有明确的 gap。

以下 5 个提案从最高价值到最低排列，每个都标注了:
- **创新点**：为什么不是简单的"安装使用"
- **实际价值**：解决什么真实问题
- **实现复杂度**：改多少代码
- **对论文的贡献**：是否有学术发表价值

---

## 提案 1：电化学数据 Parser + 自动分层摘要（ECDataParser）

### 问题

OpenViking 擅长处理文本/文档，但完全不理解电化学时序数据（CV曲线、EIS谱图、i-t曲线）。如果把 CSV 原样入库，L0 摘要会是毫无意义的文本截断。

### 方案

利用 OpenViking 的 `ParserRegistry.register_custom()` 机制（见 `openviking/parse/custom.py` `CustomParserProtocol`），编写 `ECDataParser`：

```python
class ECDataParser:
    """电化学数据专用 Parser — 将 CV/LSV/EIS/i-t 的 CSV 数据
    转化为语义化的 Markdown + 自动生成 L0/L1/L2 分层摘要"""
    
    @property
    def supported_extensions(self) -> list[str]:
        return [".csv"]  # CHI 660F 输出格式
    
    def can_handle(self, source) -> bool:
        # 检查 CSV 头部的 # technique: 注释来判断
        ...
    
    async def parse(self, source, **kwargs) -> ParseResult:
        """
        1. 读取 CSV + # 注释头
        2. 根据 technique 类型执行特征提取
        3. 生成三层 Markdown：
           - L0 (abstract ~30 tokens):
             "CV扫描 Fe 0.3M, -0.5~0.5V, 50mV/s, Ip=12.3μA, ΔEp=72mV"
           - L1 (overview ~500 tokens):
             关键参数表 + 曲线特征描述 + 数据质量评分
           - L2 (detail — full data):
             完整数据表 + 特征点标注 + 拟合结果
        """
```

**关键差异 vs 通用 Parser**：
- L0 不是文本摘要，是从**数值中提取的电化学指纹**（峰电流、峰电位差、Tafel 斜率等）
- L1 包含**领域专业 Markdown 表格**（对比文献值、标注异常、评估可逆性）
- 检索时，Agent 搜 "Fe CV 峰电流" 能精确命中，因为 L0 中已包含这些语义标签

### 创新点

**数值数据的语义化分层摘要是 OpenViking 没有的能力**。现有 Parser 全部面向文本/文档——对于 CSV 时序数据，它会当作 plain text 处理，丢失所有电化学语义。这个 Parser 让向量检索可以用于数值型实验数据，是 "让上下文数据库理解科学数据" 的一步。

### 实现复杂度

中等 — 1 个 Python 文件 (~300行)，依赖已有的 `echem_analysis` 模块。

### 论文价值

★★★ — "Domain-Specific Parser for Scientific Data in Context Databases" 是一个有明确 contribution 的方向。可以做消融实验（有 ECDataParser vs 纯文本 Parser 的检索精度对比）。

---

## 提案 2：电化学实验记忆分类体系（Extended Memory Categories）

### 问题

OpenViking 的 `MemoryCategory` 只有 6 类（profile/preferences/entities/events + cases/patterns），这是为通用对话设计的。电化学实验有独特的"隐性知识"无法被这 6 类覆盖：

- "NiFe-LDH 催化剂在 pH=14 时 HER 过电位约 350mV" — 这是 **材料性质知识**
- "泵3 在 30rpm 以下精度下降明显" — 这是 **设备校准知识**
- "用 Fe(CN)₆³⁻/⁴⁻ 做 CV 看到分裂峰，原因是参比电极有气泡" — 这是 **失败教训**
- "浓度梯度实验应从低到高，减少电极污染" — 这是 **实验方法论**

### 方案

在 `openviking/session/memory_extractor.py` 的 `MemoryCategory` 枚举中扩展：

```python
class MemoryCategory(str, Enum):
    # --- 原有 6 类（保留） ---
    PROFILE = "profile"
    PREFERENCES = "preferences"  
    ENTITIES = "entities"
    EVENTS = "events"
    CASES = "cases"
    PATTERNS = "patterns"
    
    # --- 电化学领域扩展（新增 4 类） ---
    MATERIALS = "materials"        # 材料性质知识
    CALIBRATIONS = "calibrations"  # 设备校准与状态记忆
    FAILURES = "failures"          # 失败实验教训（比 cases 更聚焦于"什么不该做"）
    METHODOLOGY = "methodology"    # 实验方法论与 SOP 优化建议
```

同时修改 `MemoryExtractor` 的 Prompt 模板（`openviking/prompts/templates/compression.memory_extraction`），增加电化学领域的提取规则。

**记忆目录映射**：
```
viking://agent/memories/
├── cases/          # 通用案例（保留）
├── patterns/       # 通用模式（保留）
├── materials/      # 新：NiFe-LDH.md, Fe(CN)6.md, ...
├── calibrations/   # 新：pump_3_precision.md, chi_reference_electrode.md
├── failures/       # 新：split_peak_air_bubble.md, ...
└── methodology/    # 新：concentration_gradient_ordering.md, ...
```

### 创新点

**领域特化的记忆分类让 Agent 能在正确的上下文中检索正确类型的知识**。通用 `cases` 类别会把材料性质和设备校准混在一起——当 Agent 问 "泵3 精度如何？" 时，不需要搜到催化剂数据。分类使检索更精准，token 消耗更低。

### 实现复杂度

低 — 修改 1 个枚举 + 2 个 Prompt 模板 + 目录映射表。

### 论文价值

★★☆ — "Domain-Adapted Memory Taxonomy for Scientific Agents" 可作为消融实验项（有/无领域记忆分类的知识检索准确率对比）。

---

## 提案 3：实验上下文总线（Experiment Context Bus）

### 问题

当前 MicroHySeeker（PySide6 桌面端）和 AutoHySeeker（AI Agent）之间没有通信机制。现有方案是通过文件系统间接交互（实验数据存文件 → Agent 读文件），但这种方式：
1. 无法实时传递实验状态
2. 没有统一的上下文记录（谁做了什么决策？为什么？）
3. Agent 的建议无法追溯"哪个上下文导致了这个建议"

### 方案

利用 OpenViking Session 作为 **MicroHySeeker ↔ AutoHySeeker 的通信协议层**：

```
┌─────────────────┐           ┌──────────────────┐
│  MicroHySeeker  │           │  AutoHySeeker     │
│  (PySide6)      │           │  (LangGraph)      │
│                 │           │                   │
│  Engine 每步    │  Session  │  Agent 检索       │
│  写入状态消息   │ ◄═══════► │  获取实验上下文   │
│                 │  (OV)     │                   │
│  接收 Agent     │           │  返回决策建议     │
│  决策指令       │           │  记录推理过程     │
└─────────────────┘           └──────────────────┘
```

**具体实现**：

```python
# MicroHySeeker 侧 — ExperimentEngine 的 tick 回调
async def on_step_completed(step_index: int, step_result: dict):
    """每个实验步骤完成后，写入 OpenViking Session"""
    ov_session.add_message(
        role="system",
        parts=[
            {"type": "text", "text": f"步骤 {step_index} 完成: {step_result['status']}"},
            {"type": "context", "uri": f"viking://experiments/{run_id}/step_{step_index}.md"},
        ]
    )

# AutoHySeeker 侧 — Supervisor Agent
async def check_experiment_context(session_id: str):
    """Agent 通过 Session 检索实验上下文"""
    results = viking.search(
        query="当前实验执行状态和数据质量",
        session_id=session_id,
    )
    # results 自动包含：当前步骤数据 + 历史记忆 + 相关失败案例
```

**关键特性**：
- Session `commit()` 时自动提取长期记忆 → 实验经验永久积累
- `used()` 追踪 Agent 实际采纳了哪些上下文 → 可审计、可回溯
- Session 压缩机制自动管理 token 窗口 → 长时间实验不溢出

### 创新点

**用上下文数据库的 Session 机制作为"硬件控制层"和"AI 决策层"的通信协议**。传统方式是 RPC/REST API 直接调用，我们用 Session 消息流做中介——好处是：(1) 自动留痕可审计，(2) 记忆自迭代，(3) 解耦（MicroHySeeker 不需要知道 Agent 内部结构）。

### 实现复杂度

高 — 需要在 MicroHySeeker Engine 中添加 Session 钩子 + AutoHySeeker 的 Agent 读写 Session + 可能需要 WebSocket 实时通知。

### 论文价值

★★★ — "Context-Database-Mediated Communication for Scientific Instrument Control" — 这是一个新颖的系统设计模式。

---

## 提案 4：Viking URI 驱动的实验因果图谱

### 问题

实验数据是孤岛——每个 run_dir 独立存储，没有"实验 A 的失败教训导致了实验 B 的参数调整"这种因果关系的显式记录。

### 方案

利用 OpenViking 的 `link()`/`relations()` API 建立实验间的**因果链接**：

```python
# 实验 B 是基于实验 A 的失败教训改进的
viking.link(
    from_uri="viking://experiments/2026-02-27/exp_002/",
    uris=["viking://experiments/2026-02-27/exp_001/"],
    reason="基于 exp_001 的 split peak 失败，增加了参比电极除气步骤"
)

# 实验 B 使用了某个记忆
viking.link(
    from_uri="viking://experiments/2026-02-27/exp_002/",
    uris=["viking://agent/memories/failures/split_peak_air_bubble.md"],
    reason="应用了失败教训"
)

# 实验 B 使用了某种材料
viking.link(
    from_uri="viking://experiments/2026-02-27/exp_002/",
    uris=["viking://resources/materials/NiFe-LDH.md"],
    reason="测试材料"
)
```

**检索时自动沿关系图谱展开**：搜索 "NiFe-LDH 最佳 HER 条件" → 检索器从 materials 定位到材料 → 沿 relations 找到所有相关实验 → 从实验记忆中提取 patterns → 返回综合答案。

### 创新点

实验数据的**知识图谱化**。OpenViking 的 `HierarchicalRetriever` 已支持 `related_uri` 字段的关系跟踪（见 `hierarchical_retriever.py` 的 `_get_relations()` 方法），但默认只做目录层级——我们可以利用这个机制做跨目录的因果推理。

### 实现复杂度

低 — 主要是在 Agent 的 `save_results_node` 中添加 `link()` 调用。OpenViking 的底层已支持。

### 论文价值

★★☆ — "Causal Knowledge Graph for Automated Electrochemical Experiments" 可作为系统特性描述。

---

## 提案 5：多 Agent 共享上下文空间（Multi-Agent Context Sharing）

### 问题

OpenViking 的 Session 是 **单用户单 Agent** 设计（`user_space` / `agent_space`）。AutoHySeeker 有 5 个协作 Agent，它们需要：
- **共享实验上下文**：Supervisor 执行的数据，Analyst 需要分析，Designer 需要参考
- **独立记忆空间**：Diagnostics 的故障经验不应与 Designer 的方案模式混在一起
- **跨 Agent 可见性**：Analyst 的分析结论应该对 Designer 可见

### 方案

在 OpenViking 的 URI 体系上设计 AutoHySeeker 专用的命名空间：

```
viking://
├── resources/                    # 全局可读
│   ├── experiments/              # 实验数据（ECDataParser 处理）
│   ├── literature/               # 文献
│   └── manuals/                  # 仪器手册
│
├── agent/                        # Agent 空间
│   ├── shared/                   # ★ 新增：Agent 间共享区
│   │   ├── experiment_context/   # 当前实验上下文（Supervisor 写、所有 Agent 读）
│   │   └── analysis_results/     # 分析结论（Analyst 写、Designer/Supervisor 读）
│   │
│   ├── memories/                 # 共享记忆（所有 Agent 可读写）
│   │   ├── cases/
│   │   ├── patterns/
│   │   ├── materials/            # 提案2 扩展
│   │   ├── calibrations/
│   │   ├── failures/
│   │   └── methodology/
│   │
│   └── private/                  # ★ 新增：Agent 私有区
│       ├── diagnostics/          # D Agent 的内部工作记录
│       ├── designer/             # B Agent 的方案草稿
│       └── analyst/              # A Agent 的分析中间结果
│
└── session/                      # Session 空间（OpenViking 原有）
    └── {user}/{session_id}/
```

**检索时按 Agent 角色过滤**：

```python
# Diagnostics Agent 搜索时，优先搜 failures + calibrations
results = viking.search(
    query="RS485 通讯超时解决方案",
    filter={"category": {"$in": ["failures", "calibrations", "cases"]}},
)

# Designer Agent 搜索时，优先搜 methodology + materials + shared
results = viking.search(
    query="Fe HER CV 参数参考", 
    target_uri="viking://agent/shared/",  # 只搜共享区
)
```

### 创新点

在 OpenViking 的 AGFS + URI 体系上构建 **Multi-Agent 上下文协作协议**。OpenViking 原生不支持多 Agent——我们通过目录命名约定 + `target_uri` 过滤实现了轻量级的 Agent 间上下文隔离与共享，无需修改 OpenViking 内核。

### 实现复杂度

低 — 纯目录命名约定 + search 时传 `target_uri` 参数。不需要改 OpenViking 代码。

### 论文价值

★★☆ — "Context-Aware Multi-Agent Collaboration via Shared Knowledge Spaces" — 是 Multi-Agent 系统的一个轻量级创新。

---

## 优先级建议

| 排名 | 提案 | 实现复杂度 | 论文价值 | 建议阶段 |
|------|------|-----------|---------|---------|
| 1 | ECDataParser（提案1） | 中 | ★★★ | Phase 2 — 随 DataAnalyst 一起开发 |
| 2 | 多 Agent 上下文空间（提案5） | 低 | ★★☆ | Phase 1 — OpenViking 初始化时定义目录结构 |
| 3 | 实验记忆分类（提案2） | 低 | ★★☆ | Phase 3 — 随 KnowledgeManager 一起开发 |
| 4 | 实验因果图谱（提案4） | 低 | ★★☆ | Phase 3 — 随知识管理一起 |
| 5 | 实验上下文总线（提案3） | 高 | ★★★ | Phase 4 — 需 IPC 基础设施就绪 |

---

## 与 OpenViking 原版的改动范围总结

| 改动类型 | 改动位置 | 侵入性 |
|---------|---------|--------|
| **新增文件** | `echem_parser.py`（注册到 ParserRegistry） | 零侵入 — 调用公开 API |
| **修改枚举** | `memory_extractor.py` → `MemoryCategory` 新增 4 值 | 低侵入 — 枚举扩展 |
| **修改 Prompt** | `prompts/templates/compression.memory_extraction` | 低侵入 — Prompt 调整 |
| **目录约定** | `viking://agent/shared/`, `viking://agent/private/` | 零侵入 — 纯命名约定 |
| **Session 集成** | MicroHySeeker Engine → Session 钩子 | 中侵入 — 需 Engine 改动 |

> **总体策略**：尽量通过 OpenViking 的扩展机制（Custom Parser、Prompt 模板、URI 约定）实现魔改，避免 fork 内核导致无法跟进上游更新。只有提案2（MemoryCategory 枚举扩展）需要改 OpenViking 源码。

---

*本文档为提案讨论稿。请审阅后反馈哪些值得推进、哪些需要调整。确认后会更新到 `open_source_integration.md` 和 `project_plan.md` 中。*

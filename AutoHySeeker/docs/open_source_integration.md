# AutoHySeeker — 开源生态集成策略

> 2026-02-28 | v2.0（新增 OpenClaw 章节，重新定义 AI 基础设施层）
> 核心理念：**站在巨人肩膀上构建，而非从零造轮子**
> 关联文档：[architecture_overview.md](architecture_overview.md) · [project_plan.md](project_plan.md) · [dev_openclaw.md](dev_openclaw.md)

---

## 总体策略

AutoHySeeker 是一个复杂的多 Agent 科研系统，从零构建每个组件既不现实也不经济。我们采用 **"核心定制 + 生态复用"** 策略：

```
┌─────────────────────────────────────────────────────────────┐
│                 AutoHySeeker 构建策略                         │
│                                                             │
│  自研（领域专属，无法替代）：                                  │
│    ├── 电化学分析 Tools（echem_analysis.py）                  │
│    ├── MicroHySeeker 数据读取 Tools（data_reader.py）         │
│    ├── 实验方案构建 Tools（experiment_builder.py）             │
│    ├── Agent System Prompts（电化学领域知识）                  │
│    └── Graph 编排逻辑（C→D→C 闭环等）                         │
│                                                             │
│  复用开源（通用能力，有成熟方案）：                              │
│    ├── OpenClaw    → 本地 AI 网关 + Skills 编排 + 多渠道      │
│    ├── OpenViking  → 替代 RAG 管线 + 记忆系统                 │
│    ├── LangGraph   → 替代 手写状态机编排                       │
│    ├── SkillsMCP   → 参考/适配 通用 Skill 模板                │
│    ├── Optuna      → 替代 手写贝叶斯优化                       │
│    ├── pymupdf     → 替代 手写 PDF 解析                       │
│    └── Playwright  → 替代 手写浏览器自动化（文献下载）           │
└─────────────────────────────────────────────────────────────┘
```

**判断标准**：
| 问题 | 自研 | 复用 |
|------|------|------|
| 这个功能是电化学/MicroHySeeker 特有的吗？ | ✅ | |
| 有成熟的开源项目能解决 80%+ 需求吗？ | | ✅ |
| 自建预计需要多少周？复用+改造需要多少天？ | >1周 → 考虑复用 | <3天 → 直接用 |

---

## 一、OpenViking — 替代 RAG 管线 + 补足记忆系统

### 1.1 为什么引入

OpenViking 是字节跳动火山引擎开源的 **AI Agent 上下文数据库**。 

| 我们的需求 | 原规划方案 | OpenViking 方案 | 优势 |
|-----------|-----------|----------------|------|
| 文档入库+检索 | ChromaDB + 手写分块/Embedding/检索 | `client.add_resource()` + `client.find()` | 省去 4 个模块开发 |
| 实验数据归档 | 手写 `ingest_experiment_knowledge()` | 整个 run_dir 直接 `add_resource` | 自动分块+摘要 |
| 分层上下文 | 无 | L0(摘要)/L1(概览)/L2(详情) 按需加载 | 大幅降低 Token 消耗 |
| 文献 RAG | 手写 PDF→分块→入库管线 | `add_resource(pdf_path)` | 内置 PDF 解析 |
| 检索质量 | 扁平向量搜索 | 目录递归检索（先定位目录再精搜） | 更准确 |
| 检索可观测 | 无 | 可视化检索轨迹 | 方便调试 |
| Agent 记忆 | **无（原规划缺失）** | `viking://agent/memories/` 自动提取 | 新增重要能力 |
| 用户偏好 | **无** | `viking://user/memories/` | 新增能力 |

### 1.2 替换映射

```
原规划的 RAG 模块          →  OpenViking 替代
─────────────────────────────────────────────────
rag/embeddings.py           → OpenViking 内置 Embedding
rag/vector_store.py         → OpenViking Storage（viking:// 文件系统）
rag/chunker.py              → OpenViking 自动分层处理
rag/pdf_parser.py           → OpenViking parse/ 模块
rag/collections.py          → viking:// 目录结构
tools/rag_tools.py (7函数)  → OpenViking SDK 封装（~3个 wrapper 函数）
```

### 1.3 知识库目录结构设计

原来的 5 个 ChromaDB Collection 映射为 OpenViking 虚拟文件系统：

```
viking://
├── resources/                      # 资源目录
│   ├── experiments/                # 实验档案（E3 归档）
│   │   ├── 2026-02-13/
│   │   │   ├── 153000_cv_fe_gradient/
│   │   │   │   ├── run_summary.json
│   │   │   │   ├── echem/
│   │   │   │   └── pump/
│   │   │   └── 160000_eis_baseline/
│   │   ├── 2026-02-23/
│   │   └── ...
│   ├── literature/                 # 学术文献
│   │   ├── 2025_wang_microfluidic_cv/
│   │   ├── 2025_li_eis_catalyst/
│   │   └── ...
│   ├── manuals/                    # 仪器手册
│   │   ├── chi660f_manual/
│   │   ├── longer_bt100_pump/
│   │   └── microhyseeker_user_guide/
│   ├── error_solutions/            # 错误解决方案
│   │   ├── rs485_timeout/
│   │   ├── chi_no_response/
│   │   └── pump_stall/
│   └── domain_knowledge/           # 电化学领域知识
│       ├── cv_theory/
│       ├── eis_interpretation/
│       └── tafel_analysis/
│
├── agent/                          # Agent 记忆（★ 新增能力）
│   ├── memories/
│   │   ├── experiment_tips/        # "0.3M Fe CV 最佳扫速 50mV/s"
│   │   ├── error_patterns/         # "泵1卡住通常是管路堵塞"
│   │   ├── parameter_ranges/       # "CV扫速一般 10-200 mV/s"
│   │   └── user_feedback/          # 从用户反馈中学到的偏好
│   ├── skills/                     # Skill 描述（供 Orchestrator 路由参考）
│   │   ├── diagnose_failure/
│   │   ├── analyze_experiment/
│   │   └── design_experiment/
│   └── instructions/               # Agent 行为指令
│       ├── safety_rules/
│       └── output_format/
│
└── user/                           # 用户记忆（★ 新增能力）
    └── memories/
        ├── preferences/            # "用户偏好 Markdown 报告"
        ├── research_context/       # "当前研究课题: OER 催化剂筛选"
        └── hardware_setup/         # "当前使用 3 号泵有漏液"
```

### 1.4 集成代码设计

```python
# src/rag/openviking_client.py
"""OpenViking 统一封装 — 替代原来的 rag/ 全部模块"""

import openviking as ov
from pathlib import Path

class VikingKnowledgeBase:
    """AutoHySeeker 的 OpenViking 封装"""
    
    def __init__(self, workspace_path: str):
        self.client = ov.SyncOpenViking(path=workspace_path)
        self.client.initialize()
    
    # === E1: 资源入库 ===
    def ingest_document(self, path: str, target_dir: str = "resources/literature") -> dict:
        """入库文档（PDF/文本/目录）"""
        result = self.client.add_resource(path=path, uri=f"viking://{target_dir}/")
        self.client.wait_processed()  # 等待自动分块+Embedding+摘要生成
        return result
    
    def ingest_experiment(self, run_dir: str) -> dict:
        """E3: 实验归档 — 整个实验目录入库"""
        return self.ingest_document(run_dir, target_dir="resources/experiments")
    
    def ingest_error_solution(self, error_type: str, solution_text: str) -> dict:
        """入库错误解决方案"""
        return self.client.add_resource(
            content=solution_text,
            uri=f"viking://resources/error_solutions/{error_type}"
        )
    
    # === E2: 知识检索 ===
    def search(self, query: str, target_uri: str = "viking://resources/", top_k: int = 5) -> list:
        """语义搜索（自动目录递归检索）"""
        results = self.client.find(query, target_uri=target_uri, top_k=top_k)
        return results.resources
    
    def search_experiments(self, query: str, top_k: int = 5) -> list:
        return self.search(query, target_uri="viking://resources/experiments/", top_k=top_k)
    
    def search_literature(self, query: str, top_k: int = 5) -> list:
        return self.search(query, target_uri="viking://resources/literature/", top_k=top_k)
    
    def search_error_solutions(self, query: str, top_k: int = 3) -> list:
        return self.search(query, target_uri="viking://resources/error_solutions/", top_k=top_k)
    
    # === 分层上下文 ===
    def get_abstract(self, uri: str) -> str:
        """L0: 摘要（~100 tokens）— 快速判断相关性"""
        return self.client.abstract(uri)
    
    def get_overview(self, uri: str) -> str:
        """L1: 概览（~2k tokens）— 了解结构和要点"""
        return self.client.overview(uri)
    
    def get_full_content(self, uri: str) -> str:
        """L2: 完整内容 — 按需深入"""
        return self.client.read(uri)
    
    # === 记忆管理（★ 新增） ===
    def save_agent_memory(self, category: str, content: str) -> dict:
        """保存 Agent 经验记忆"""
        return self.client.add_resource(
            content=content,
            uri=f"viking://agent/memories/{category}/"
        )
    
    def save_user_memory(self, category: str, content: str) -> dict:
        """保存用户偏好记忆"""
        return self.client.add_resource(
            content=content,
            uri=f"viking://user/memories/{category}/"
        )
    
    def recall_agent_memories(self, query: str, top_k: int = 3) -> list:
        """检索 Agent 相关记忆"""
        return self.search(query, target_uri="viking://agent/memories/", top_k=top_k)
    
    def recall_user_memories(self, query: str, top_k: int = 3) -> list:
        """检索用户相关记忆"""
        return self.search(query, target_uri="viking://user/memories/", top_k=top_k)
    
    # === 目录浏览 ===
    def ls(self, uri: str) -> dict:
        """列出目录内容"""
        return self.client.ls(uri)
    
    def glob(self, pattern: str, uri: str = "viking://") -> list:
        """文件模式匹配"""
        return self.client.glob(pattern=pattern, uri=uri)
    
    def close(self):
        self.client.close()
```

### 1.5 替换后的 Tools 变化

原 `tools/rag_tools.py` 的 7 个函数简化为 3 个 wrapper：

| 原函数 | OpenViking 替代 | 备注 |
|--------|----------------|------|
| `ingest_pdf(path, collection)` | `viking_kb.ingest_document(path, "resources/literature")` | 自动解析+分块 |
| `ingest_text(text, metadata, collection)` | `viking_kb.client.add_resource(content=text, uri=...)` | 直接写入 |
| `ingest_experiment_knowledge(run_dir)` | `viking_kb.ingest_experiment(run_dir)` | 整目录入库 |
| `semantic_search(query, collection, top_k)` | `viking_kb.search(query, target_uri=..., top_k=...)` | 递归检索更优 |
| `list_collections()` | `viking_kb.ls("viking://resources/")` | 目录浏览 |
| `delete_document(doc_id)` | 暂不需要 | OpenViking 支持但优先级低 |
| `get_collection_stats(collection)` | `viking_kb.ls(...)` + 统计 | 目录结构自带 |

### 1.6 对各 Agent 的影响

| Agent | 变化 | 详情 |
|-------|------|------|
| KnowledgeManager (E) | **大幅简化** | E1/E2/E3 都通过 OpenViking SDK 实现，无需手写 RAG 管线 |
| DiagnosticsExpert (D) | **增强** | `search_solutions` 节点从硬编码 dict → OpenViking 搜索 |
| ExperimentDesigner (B) | **增强** | `search_knowledge` 节点使用 L0/L1 分层检索参考文献 |
| DataAnalyst (A) | 无直接变化 | 但 A4 NL查询可借助 OpenViking 记忆增强上下文 |
| ExperimentSupervisor (C) | **新增记忆** | 实验后自动归档 + Agent 经验记忆积累 |

### 1.7 引入时机

**Phase 3 Week 7**（RAG 基础设施建设阶段），直接用 OpenViking 替代原计划的 ChromaDB + 手写管线。

Phase 1-2 不受影响：
- Phase 1 的 D1 `search_solutions` 仍用硬编码 `ERROR_KNOWLEDGE_BASE` dict
- Phase 2 不需要 RAG
- Phase 3 引入 OpenViking 后，D1 升级为 OpenViking 搜索

### 1.8 配置

```toml
# configs/openviking.toml
[storage]
workspace = "./data/viking_workspace"

[embedding]
api_base = "https://api.openai.com/v1"  # 或本地模型
api_key_env = "OPENAI_API_KEY"
provider = "openai"                     # "openai" | "volcengine" | "jina"
model = "text-embedding-3-small"
dimension = 1536

[vlm]
api_base = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
provider = "openai"
model = "gpt-4o-mini"                  # 用于生成摘要/概览
```

### 1.9 电化学数据的适配

OpenViking 可能不原生理解 MicroHySeeker 的 echem CSV 格式（带 `#` 注释头）。解决方案：

**方案 A（推荐）：入库前预处理**
```python
def ingest_experiment_enhanced(self, run_dir: str) -> dict:
    """增强版实验归档：先生成可读的 README，再整目录入库"""
    # 1. 自动生成实验 README.md（让 OpenViking 理解实验内容）
    summary = data_reader.read_run_summary(run_dir)
    plan = data_reader.read_experiment_plan(run_dir)
    
    readme_content = f"""# {summary['name']}
    
- 日期: {summary['date']}
- 状态: {summary['status']}
- 步骤数: {summary['total_steps']}
- 技术: {', '.join(extract_techniques(plan))}
- 关键参数: {format_key_params(plan)}
"""
    # 写入 README.md 到实验目录
    (Path(run_dir) / "README.md").write_text(readme_content, encoding="utf-8")
    
    # 2. 整目录入库（OpenViking 会读 README 理解上下文）
    return self.ingest_document(run_dir, "resources/experiments")
```

**方案 B：自定义 Parser（如需更深度解析 CSV）**
- OpenViking 支持扩展 Parser，后续如果需要对 echem CSV 做细粒度索引再考虑

---

## 二、SkillsMCP 生态 — 加速 Skill 开发

### 2.1 什么是 SkillsMCP

[SkillsMCP](https://skillsmp.com/) 是最大的 Agent Skills 聚合平台，收录 28万+ 开源 SKILL.md 文件。每个 Skill 是一个模块化能力描述文件，包含指令、脚本和模板。

**对我们的价值**：不用从零设计 Skill 的结构和流程——参考已有 Skill 的模式，适配到我们的领域。

### 2.2 可利用的类别

| SkillsMCP 类别 | 收录数量 | 对 AutoHySeeker 的价值 |
|----------------|---------|----------------------|
| **Data & AI** | 39,583 | 数据分析模式、可视化、报告生成模板 |
| **Research** | 10,912 | 论文处理、知识提取、RAG 模式 |
| **Tools** | 78,171 | 通用工具模式（文件处理、日志分析） |
| **Testing & Security** | 31,810 | 测试框架、安全审查模式 |
| **Documentation** | 22,322 | 报告生成、文档模板 |

### 2.3 Skill 适配策略（务实路线）

**核心原则**：检索成本小 → 找到就改；检索不到 / 成本大 → 按经典模式自己写。不为复用而复用。

```
决策流程（每个 Skill 单独评估）：

1. 花 10 分钟在 SkillsMCP 搜索相关关键词
   │
   ├── 找到匹配度 ≥60% 的 Skill
   │   → 阅读 SKILL.md，提取可复用模式（Prompt、流程、输出格式）
   │   → 适配到我们的 BaseSkill 框架 + 填入电化学领域知识
   │   → 标记来源，方便后续追踪更新
   │
   └── 未找到 / 匹配度低 / 搜索困难
       → 不浪费时间，直接按以下经典模式自己编写：
         ① 明确 Skill 的输入/输出/边界条件
         ② 参考 skills_architecture.md 中的 BaseSkill 基类
         ③ 按 "数据采集 → 预处理 → LLM 推理 → 结构化输出" 四步模板
         ④ 优先覆盖 happy path，再补错误处理
```

### 2.4 每个 Skill 的复用评估

| AutoHySeeker Skill | SkillsMCP 检索方向 | 预估复用度 | 策略 |
|--------------------|-------------------|-----------|------|
| **D1 失败诊断** | `troubleshooting` / `extract-errors` | ★★★ 高（通用错误分析模式） | **检索改造**：参考错误分类框架、根因分析模板 |
| **D3 交互排错** | `interactive-debug` | ★★☆ 中 | **检索参考**：借鉴多轮诊断树结构 |
| **A1 单次实验分析** | `data-analysis` / `data-visualization` | ★★☆ 中（通用分析框架可用） | **检索改造**：参考报告结构和图表渲染模式 |
| **A4 NL数据查询** | `natural-language-sql` / `data-query` | ★★★ 高（NL→查询是成熟模式） | **检索改造**：参考 NL→结构化查询的 Prompt 设计 |
| **B1 NL→方案** | `code-generation` | ★☆☆ 低（电化学方案特有） | **自主编写**：无通用映射，按经典模板自建 |
| **B3 方案审查** | `code-review` / `verify` | ★★☆ 中 | **检索参考**：借鉴审查循环和检查清单模式 |
| **B2 参数优化** | — | ☆☆☆ 无 | **自主编写**：纯领域逻辑，直接用 Optuna |
| **B4 Protocol 生成** | — | ☆☆☆ 无 | **自主编写**：MicroHySeeker JSON 特有格式 |
| **C1 实验合规检查** | `validation` / `safety-check` | ★☆☆ 低 | **自主编写**：安全阈值是领域特有的 |
| **C2 实时监控** | — | ☆☆☆ 无 | **自主编写**：硬件实时性无通用 Skill |
| **C3 自适应控制** | — | ☆☆☆ 无 | **自主编写**：闭环控制逻辑完全定制 |
| **D2 日志检索** | `log-analysis` / `log-parser` | ★★★ 高 | **检索改造**：日志解析是通用模式 |
| **E1 文档入库** | `document-processing` | ★★☆ 中 | **部分参考**：OpenViking 已覆盖大部分 |
| **E2 知识问答** | `rag-qa` / `research` | ★★★ 高（RAG QA 是成熟模式） | **检索改造**：参考 RAG Prompt 和置信度评估 |
| **E3 实验归档** | — | ☆☆☆ 无 | **自主编写**：实验 → OpenViking 入库是定制流程 |
| **报告生成** | `report-generation` / `documentation` | ★★★ 高 | **检索改造**：参考 Markdown 报告模板 |
| **图表解读** | `data-visualization` | ★★☆ 中 | **检索参考**：参考图表描述 Prompt |

**汇总**：17 个 Skill 中 ~7 个可从 SkillsMCP 检索改造，~10 个按经典模式自主编写。

### 2.5 自主编写 Skill 的标准模板

对于无法从 SkillsMCP 复用的 Skill，统一按以下模板编写：

```python
# skills/experiment_design/b1_nl_to_plan.py
"""B1: 自然语言 → 实验方案（自主编写 — SkillsMCP 无匹配）"""

from autohyseeker.skills.base import BaseSkill, SkillResult

class NLToExperimentPlanSkill(BaseSkill):
    """将自然语言实验需求转换为结构化实验方案"""
    
    name = "nl_to_experiment_plan"
    description = "将自然语言实验需求转换为结构化实验方案"
    version = "0.1.0"
    
    # 标准四步流程
    async def execute(self, user_request: str, **kwargs) -> SkillResult:
        # Step 1: 数据采集 — 收集上下文
        domain_context = await self.tools.search_knowledge(
            query=user_request, top_k=3
        )
        hardware_config = await self.tools.get_hardware_config()
        
        # Step 2: 预处理 — 结构化输入
        structured_input = {
            "request": user_request,
            "available_hardware": hardware_config,
            "domain_context": [r.summary for r in domain_context],
        }
        
        # Step 3: LLM 推理 — 生成方案
        plan = await self.llm.generate(
            prompt=self.prompts.NL_TO_PLAN,
            input=structured_input,
            output_schema=ExperimentPlanSchema,
        )
        
        # Step 4: 结构化输出 — 验证 + 返回
        validation = self._validate_plan(plan)
        return SkillResult(
            success=validation.is_valid,
            data=plan,
            warnings=validation.warnings,
            metadata={"source": "self_written", "skillsmcp_ref": None},
        )
```

### 2.6 示例：参考 `extract-errors` Skill 优化 D1

```markdown
# 从 SkillsMCP 的 facebook/react extract-errors Skill 学到的模式：

1. 错误消息的结构化提取（不只是文本匹配，而是语义分类）
2. 错误代码注册表（类似我们的 ERROR_KNOWLEDGE_BASE）
3. 自动化的修复建议生成

→ 应用到 D1: 
  - 将 classify_error() 升级为语义分类（不只关键词匹配）
  - 维护结构化的错误知识图谱（迁移到 OpenViking）
  - 自动生成"下一步操作"脚本
```

---

## 三、OpenClaw — 本地 AI 网关 + 开发自动化中枢

### 3.1 重新认识 OpenClaw

> **最初误判**：将 OpenClaw 视为"聊天机器人"，认为不能替代 LangGraph/OpenViking/FastAPI。
>
> **正确认知**：AutoHySeeker 开源生态中**最关键的基础设施层之一**。它不是聊天 App，而是一个本地运行的 AI 网关平台，配合 Claude Code Skill 可以实现"一个人就能搭建完整开发团队"。

| 维度 | 错误理解 | 正确理解 |
|------|---------|---------|
| 定位 | 个人聊天助手 | 本地 AI Agent 网关平台 |
| 核心能力 | 回答问题 | bash执行 + 文件读写 + 浏览器控制 + Skills 体系 |
| 与编码的关系 | 无关 | Claude Code Skill = 自主编写代码、运行测试、迭代修复 |
| 与项目的关系 | 可选附属 | 可驱动 AutoHySeeker 全栈自主开发 |
| 运行方式 | 需要人工触发 | 24/7 常驻守护进程，心跳主动运行 |

### 3.2 OpenClaw 核心架构

```
┌────────────────────────────────────────────────────────────────┐
│                 OpenClaw Gateway (ws://127.0.0.1:18789)         │
│                                                                 │
│  ┌─────────────────┐      ┌──────────────────────────────────┐ │
│  │   Pi Agent      │      │         多渠道接入                 │ │
│  │  (LLM智能核心)  │      │ WebChat · Telegram · Discord      │ │
│  │  Claude Opus/  │      │ WhatsApp · iMessage · Slack        │ │
│  │  GPT-4o        │      └──────────────────────────────────┘ │
│  └────────┬────────┘                                            │
│           │ 调用                                                 │
│  ┌────────▼─────────────────────────────────────────────────┐  │
│  │                    Skills 系统                              │  │
│  │  claude-code    → 自主写代码/测试/调试（★ 核心）             │  │
│  │  autohyseeker   → 项目上下文 + 实验控制（自定义）            │  │
│  │  bash           → 任意 shell 命令                           │  │
│  │  browser        → Chromium 浏览器控制                       │  │
│  │  file           → 读写工作区文件                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  工作区: ~/clawd/                                                 │
│    AGENTS.md  SOUL.md  TOOLS.md  USER.md  HEARTBEAT.md          │
│    skills/autohyseeker/SKILL.md                                 │
└────────────────────────────────────────────────────────────────┘
```

### 3.3 在 AutoHySeeker 中的角色

OpenClaw 承担三层角色：

**层 1：自主开发加速器**（最重要，参见 [dev_openclaw.md](dev_openclaw.md) §2）

```
你（WebChat/Telegram） → "帮我实现 B2 Skill 的贝叶斯优化部分"
        ↓
OpenClaw Pi Agent 接收任务
        ↓
调用 claude-code Skill（Claude Code 编码代理）
        ↓
Claude Code 读项目文件 → 写代码 → pytest → 修复 → 提交
        ↓
Agent 回复："B2 Skill 已实现，测试通过，PR 已创建"
```

**层 2：实验命令接口**（Phase 2 后引入）

```
你（手机 Telegram） → "分析今天的 CV 实验，推荐下一步参数"
        ↓
Pi Agent 读取 data/ 目录（bash + file 工具）
        ↓
调用 autohyseeker Skill 中定义的分析流程
        ↓
回复分析结论，并可直接驱动下一次实验（Phase 4 IPC）
```

**层 3：24/7 主动监控**（heartbeat 模式）

```
每 30 分钟自动触发
        ↓
读取 HEARTBEAT.md（监控任务清单）
        ↓
检查最新实验数据、错误日志、构建状态
        ↓
有异常则通过 Telegram/WebChat 推送告警
```

### 3.4 与其他组件的分工边界

| 组件 | 职责 | 不做什么 |
|------|------|---------|
| **OpenClaw** | 任务接收、Skills 调度、多渠道通信、代码自动化 | 不替代 LangGraph 的实验编排 |
| **LangGraph** | 实验工作流状态机（C→D→C 闭环） | 不处理用户交互和通知 |
| **OpenViking** | 知识库 + Agent 记忆（RAG） | 不执行代码或操作文件 |
| **FastAPI** | AutoHySeeker Web API 服务层 | 不主动推送/通知 |
| **React** | Web 前端 UI（数据可视化） | 不支持移动端消息接入 |

**关键点**：OpenClaw 是面向"操作者"的接口层（接收指令/发出通知），LangGraph 是面向"实验"的执行层（运行工作流）。

### 3.5 安装与配置（Windows）

> 详细步骤见 [dev_openclaw.md](dev_openclaw.md)，此处仅列概要。

**环境要求**：Node.js ≥22（当前已满足：v22.12.0）

**安装**：
```powershell
# 方式一：npm 直装（推荐）
npm install -g openclaw-cn@latest

# 方式二：PS1 脚本（自动处理 Node 检测）
iwr -useb https://clawd.org.cn/install.ps1 | iex
```

**快速启动**：
```bash
openclaw-cn onboard --install-daemon   # 引导向导（配置 LLM API Key）
openclaw-cn gateway status             # 检查守护进程
openclaw-cn dashboard                  # 打开 WebChat UI (127.0.0.1:18789)
```

**核心配置文件** `~/.openclaw/openclaw.json`：
```json5
{
  logging: { level: "info" },
  agent: {
    model: "anthropic/claude-opus-4-5",
    workspace: "D:/AI4S/openclaw-workspace",
    thinkingDefault: "high",
    timeoutSeconds: 1800,
    heartbeat: { every: "0m" }   // 先禁用，稳定后启用
  }
}
```

**AutoHySeeker 专属 Skill**（`skills/autohyseeker/SKILL.md`）：
```markdown
---
name: autohyseeker
description: AutoHySeeker 电化学自动化平台技能。项目位于 D:/AI4S/MicroHySeeker/MicroHySeeker/。
  包含 MicroHySeeker（电化学工作站GUI）、AutoHySeeker（AI后端）。
  数据目录：D:/AI4S/MicroHySeeker/MicroHySeeker/data/
  源码目录：D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/src/
metadata: {"openclaw":{"always":true,"os":["win32"]}}
---

## 项目背景
[项目详细上下文见此...]
```

### 3.6 引入时机

| 阶段 | OpenClaw 使用方式 | 优先级 |
|------|-----------------|--------|
| **立即（Phase 0）** | WebChat UI + claude-code Skill 加速代码开发 | ★★★ 最高 |
| **Phase 1** | autohyseeker Skill + 文件监控实验数据 | ★★☆ |
| **Phase 2** | Telegram channel + 实验结果推送 | ★★☆ |
| **Phase 4** | heartbeat 主动监控 + 异常告警 | ★★☆ |

---

## 四、文献 RAG 不需要独立建设

### 4.1 原有疑问

> "后续的文献自动获取与知识沉淀部分的 RAG 需要自己再做一个吗？"

**答案：不需要。** OpenViking 的资源管理能力完全覆盖文献入库和检索。

### 4.2 映射关系

| literature_automation_plan 中的组件 | OpenViking 实现 |
|------------------------------------|----------------|
| L3 PDF 解析 | OpenViking 内置解析 + pymupdf 预处理 |
| L4 结构化提取 | LLM 提取 → 存为 metadata 写入 OpenViking |
| L5 摘要生成 | OpenViking 自动生成 L0(摘要) + L1(概览) |
| L6 知识入库 | `viking_kb.ingest_document(pdf_path, "resources/literature")` |
| L8 文献对比表 | 通过 L0/L1 检索多篇文献 + LLM 对比 |
| 以前的 ChromaDB 集合 | `viking://resources/literature/` 目录 |

### 4.3 文献管线简化后的流程

```
原流程（6步）：
  PDF → pymupdf提取 → 手写分块 → Embedding → ChromaDB → 手写检索

简化后（3步）：
  PDF → (可选)LLM结构化提取 → OpenViking.add_resource()
                                     ↓
                            自动: 解析+分块+Embedding+摘要+入库

检索也简化了：
  原来: ChromaDB.query(embedding) → 扁平结果
  现在: OpenViking.find(query, target_uri="viking://resources/literature/") → 递归精搜
```

---

## 五、其他可利用的开源项目

| 项目 | 用途 | 替代什么 | 引入时机 |
|------|------|---------|---------|
| **Optuna** | 参数优化（B2 Skill） | 手写贝叶斯优化 | Phase 4 |
| **Playwright** | 文献自动下载（浏览器自动化） | 手写爬虫 | 远期 |
| **marker-pdf** | 学术 PDF→Markdown 转换 | 手写 PDF 结构化解析 | Phase 3 |
| **LangSmith** | Agent 调用追踪与调试 | 手写日志追踪 | Phase 2+ |
| **Gradio / Streamlit** | 快速原型验证（非主前端） | — | Phase 2（Agent 调试面板） |
| **pytest-asyncio** | 异步测试框架 | 手写测试工具 | Phase 1 |
| **rich** | 终端美化输出（CLI） | 手写格式化 | Phase 1 |
| **impedance.py** | EIS 等效电路拟合 | 手写 EIS 拟合算法 | Phase 2 |

---

## 六、风险与注意事项

### 6.1 OpenViking 风险

| 风险 | 缓解措施 |
|------|---------|
| 项目尚年轻（2026年1月开源） | 保持 `VikingKnowledgeBase` 封装层，必要时可替换底层 |
| API 可能不稳定 | 锁定版本，写好降级逻辑（fallback 到 ChromaDB） |
| 电化学 CSV 格式不识别 | 入库前预处理（生成 README.md），不依赖 OpenViking 解析 CSV |

### 6.2 SkillsMCP 风险

| 风险 | 缓解措施 |
|------|---------|
| Skill 质量参差不齐 | 只参考模式设计，不直接安装运行 |
| 与我们的 BaseSkill 基类不兼容 | 只借鉴思路，代码全部自己写 |

### 6.3 降级策略

```python
# 所有 OpenViking 调用都有降级路径
def search_knowledge(query: str, target_uri: str) -> list:
    try:
        return viking_kb.search(query, target_uri=target_uri)
    except Exception:
        # 降级到硬编码知识库
        logger.warning("OpenViking 不可用，降级到本地知识库")
        return local_knowledge_base.search(query)
```

---

*此文档定义了 AutoHySeeker 的开源集成策略。OpenClaw 是最优先落地的基础设施（立即安装，驱动代码自动化开发）；OpenViking 将在 Phase 3 Week 7 替代手写 RAG 管线。详细的 OpenClaw 配置与使用指南见 [dev_openclaw.md](dev_openclaw.md)。*

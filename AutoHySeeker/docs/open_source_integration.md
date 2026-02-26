# AutoHySeeker — 开源生态集成策略

> 2026-02-26 | v1.0
> 核心理念：**站在巨人肩膀上构建，而非从零造轮子**
> 关联文档：[architecture_overview.md](architecture_overview.md) · [project_plan.md](project_plan.md)

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
│    ├── OpenViking   → 替代 RAG 管线 + 记忆系统                │
│    ├── LangGraph    → 替代 手写状态机编排                      │
│    ├── SkillsMCP    → 参考/适配 通用 Skill 模板               │
│    ├── Optuna       → 替代 手写贝叶斯优化                      │
│    ├── pymupdf      → 替代 手写 PDF 解析                      │
│    └── Playwright   → 替代 手写浏览器自动化（文献下载）          │
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

### 2.3 Skill 适配策略

我们不直接安装 SkillsMCP 的 Skill（它们是给 Claude Code/Codex CLI 的），而是**参考其设计模式**来构建我们的 Skill。

```
SkillsMCP 参考路径：

1. 搜索关键词 → 找到相关 Skill
2. 阅读 SKILL.md → 理解其结构、输入输出、错误处理模式
3. 提取可复用的模式（Prompt 模板、流程设计、输出格式）
4. 适配到我们的 BaseSkill 基类 → 填入电化学领域知识
```

### 2.4 具体参考映射

| AutoHySeeker Skill | SkillsMCP 参考方向 | 可借鉴内容 |
|--------------------|-------------------|-----------|
| A1 单次实验分析 | `data-analysis` / `data-visualization` 类 | 分析报告结构、图表生成模式 |
| A4 NL数据查询 | `data-query` / `natural-language-sql` 类 | NL→查询的 Prompt 设计 |
| B1 NL→方案 | `code-generation` 类 | NL→结构化输出的 Prompt 模板 |
| B3 方案审查 | `code-review` / `verify` 类 | 审查循环模式、检查清单设计 |
| D1 失败诊断 | `troubleshooting` / `extract-errors` 类 | 错误分类、根因分析框架 |
| D3 交互排错 | `interactive-debug` 类 | 多轮对话诊断树设计 |
| E2 知识问答 | `research` / `rag-qa` 类 | RAG Prompt 模板、置信度评估 |

### 2.5 示例：参考 `extract-errors` Skill 优化 D1

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

## 三、文献 RAG 不需要独立建设

### 3.1 原有疑问

> "后续的文献自动获取与知识沉淀部分的 RAG 需要自己再做一个吗？"

**答案：不需要。** OpenViking 的资源管理能力完全覆盖文献入库和检索。

### 3.2 映射关系

| literature_automation_plan 中的组件 | OpenViking 实现 |
|------------------------------------|----------------|
| L3 PDF 解析 | OpenViking 内置解析 + pymupdf 预处理 |
| L4 结构化提取 | LLM 提取 → 存为 metadata 写入 OpenViking |
| L5 摘要生成 | OpenViking 自动生成 L0(摘要) + L1(概览) |
| L6 知识入库 | `viking_kb.ingest_document(pdf_path, "resources/literature")` |
| L8 文献对比表 | 通过 L0/L1 检索多篇文献 + LLM 对比 |
| 以前的 ChromaDB 集合 | `viking://resources/literature/` 目录 |

### 3.3 文献管线简化后的流程

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

## 四、其他可利用的开源项目

| 项目 | 用途 | 替代什么 | 引入时机 |
|------|------|---------|---------|
| **Optuna** | 参数优化（B2 Skill） | 手写贝叶斯优化 | Phase 4 |
| **Playwright** | 文献自动下载（浏览器自动化） | 手写爬虫 | 远期 |
| **marker-pdf** | 学术 PDF→Markdown 转换 | 手写 PDF 结构化解析 | Phase 3 |
| **LangSmith** | Agent 调用追踪与调试 | 手写日志追踪 | Phase 2+ |
| **Gradio / Streamlit** | 快速搭建 Chat UI | 手写 Web 前端 | Phase 3 |
| **pytest-asyncio** | 异步测试框架 | 手写测试工具 | Phase 1 |
| **rich** | 终端美化输出（CLI） | 手写格式化 | Phase 1 |
| **impedance.py** | EIS 等效电路拟合 | 手写 EIS 拟合算法 | Phase 2 |

---

## 五、风险与注意事项

### 5.1 OpenViking 风险

| 风险 | 缓解措施 |
|------|---------|
| 项目尚年轻（2026年1月开源） | 保持 `VikingKnowledgeBase` 封装层，必要时可替换底层 |
| API 可能不稳定 | 锁定版本，写好降级逻辑（fallback 到 ChromaDB） |
| 电化学 CSV 格式不识别 | 入库前预处理（生成 README.md），不依赖 OpenViking 解析 CSV |

### 5.2 SkillsMCP 风险

| 风险 | 缓解措施 |
|------|---------|
| Skill 质量参差不齐 | 只参考模式设计，不直接安装运行 |
| 与我们的 BaseSkill 基类不兼容 | 只借鉴思路，代码全部自己写 |

### 5.3 降级策略

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

*此文档定义了 AutoHySeeker 的开源集成策略。OpenViking 是最关键的引入，将在 Phase 3 Week 7 替代手写 RAG 管线。*

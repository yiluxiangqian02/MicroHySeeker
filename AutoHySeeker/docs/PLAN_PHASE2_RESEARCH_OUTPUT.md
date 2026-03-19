# Phase 2 规划：文献自动化 + 科研产出

> 版本：1.0 | 日期：2026-03-18
> 前提：Phase 1 实验闭环已完成并稳定运行。
> 目标：补全文献自动检索/下载能力，构建科研级数据分析、绘图和论文辅助写作系统。

---

## 一、Phase 2 定位

Phase 2 包含两个子目标：

- Phase 2A：文献自动化（LiteratureAgent）— 补全场景 A 的最后一环
- Phase 2B：科研产出（ResearchAnalystAgent）— 构建场景 B 的完整能力

```text
Phase 2A: 文献自动化
  检索文献 → 生成下载清单 → AI 浏览器下载 → PDF 解析 → 入库 OpenViking

Phase 2B: 科研产出
  实验数据 → 专业分析 → 科研绘图 → 文献对比 → 论文撰写辅助
```

---

## 二、新增 Agent

### 2.1 LiteratureAgent（文献自动化）

| 属性 | 值 |
| --- | --- |
| 标识 | `literature` |
| LLM | Gemini-3-Flash |
| 场景 | A（补全） |
| 依赖 | AI 浏览器（browser-use 或同类方案） |

**职责**：
1. 根据课题关键词检索文献（Google Scholar / Web of Science / PubMed）
2. 生成待下载清单（标题、DOI、相关度评分、来源）
3. 通过 AI 浏览器下载 PDF（支持学校统一身份认证）
4. 解析 PDF → 提取结构化信息（摘要、关键结论、方法、性能数据）
5. 写入 OpenViking literature/ 分区

**使用 Skill**：
- `KnowledgeArchiveSkill`（写入 literature/ 分区）— 需扩展写入权限
- `KnowledgeQuerySkill`（共享只读）— 查重，避免重复下载

**核心方法**：

```python
class LiteratureAgent(BaseAgent):
    async def search_literature(self, topic: str, sources: list[str] = None,
                                 max_results: int = 50) -> dict:
        """检索文献。

        参数:
            topic: 研究主题（如 "Fe-Co-Ni HER electrocatalyst"）
            sources: 检索源列表，默认 ["google_scholar", "web_of_science"]
            max_results: 最大结果数

        流程:
        1. LLM 生成检索关键词组合（英文 + 中文）
        2. 通过 AI 浏览器访问各检索源
        3. 提取搜索结果（标题、作者、年份、DOI、摘要）
        4. LLM 评估相关度（0~1 分）
        5. 去重（查知识库是否已有）
        6. 按相关度排序

        返回:
        {
            "query_keywords": ["Fe-Co-Ni HER", ...],
            "results": [
                {
                    "title": "...",
                    "authors": ["..."],
                    "year": 2025,
                    "doi": "10.1021/...",
                    "source": "google_scholar",
                    "abstract": "...",
                    "relevance_score": 0.92,
                    "already_in_kb": false
                }, ...
            ],
            "total_found": 50,
            "new_papers": 42  # 知识库中没有的
        }
        """

    async def download_papers(self, paper_list: list[dict],
                               auth_config: dict = None) -> dict:
        """批量下载论文 PDF。

        参数:
            paper_list: search_literature 返回的结果列表
            auth_config: 学校认证配置
                {
                    "auth_type": "university_sso",
                    "university": "xxx大学",
                    "login_url": "https://...",
                    "credentials_env": "UNI_SSO_USER/UNI_SSO_PASS"
                }

        流程:
        1. 对每篇论文：
           a. 尝试开放获取（Unpaywall / Sci-Hub 镜像）
           b. 如果需要付费 → 通过学校 SSO 认证访问出版商
           c. AI 浏览器模拟真实用户操作（点击、等待、下载）
           d. 下载 PDF 到本地 data/literature/
        2. 记录下载状态

        返回:
        {
            "downloaded": 35,
            "failed": 7,
            "details": [
                {"doi": "...", "status": "success", "path": "data/literature/xxx.pdf"},
                {"doi": "...", "status": "failed", "reason": "access_denied"},
                ...
            ]
        }
        """

    async def parse_and_ingest(self, pdf_paths: list[str]) -> dict:
        """解析 PDF 并入库。

        流程:
        1. PDF → 文本提取（PyMuPDF / pdfplumber）
        2. LLM 结构化提取：
           - 摘要
           - 关键结论（3~5 条）
           - 实验方法概述
           - 性能数据表（催化剂配比 → 过电位/电流密度/Tafel 等）
           - 关键词
        3. 写入 OpenViking literature/ 分区
        4. 建立与项目的关联

        返回:
        {
            "ingested": 35,
            "entries": [
                {
                    "doi": "...",
                    "title": "...",
                    "key_findings": ["...", "..."],
                    "performance_data": [
                        {"catalyst": "Fe0.3Co0.5Ni0.2", "overpotential_mV": 195, ...}
                    ],
                    "knowledge_entry_id": "lit_20260318_xxx"
                }, ...
            ]
        }
        """

    async def generate_download_list(self, topic: str) -> dict:
        """一键生成待下载清单（search + 去重 + 排序）。
        用户可以审核清单后再调用 download_papers。
        """
```

**AI 浏览器方案**：

```text
推荐方案: browser-use（或类似的 AI 浏览器库）

优势:
- LLM 驱动，能处理动态页面和非标准 UI
- 自适应学校 SSO 认证流程（不同学校流程不同）
- 模拟真实用户行为，不易被反爬检测
- 支持自然语言指令控制浏览器

架构:
  LiteratureAgent
      │
      ▼
  BrowserTool（封装 browser-use）
      │
      ├── search_scholar(keywords) → 搜索结果
      ├── download_pdf(doi, auth) → PDF 文件
      └── authenticate_sso(config) → 登录会话

配置 (configs/literature.toml):
  [browser]
  engine = "browser-use"          # 或 "playwright" 作为降级方案
  headless = true                 # 无头模式
  timeout_s = 30                  # 单页超时
  max_concurrent = 3              # 最大并发下载数
  download_dir = "data/literature/"

  [browser.auth]
  type = "university_sso"
  login_url = "https://..."
  # 凭据从环境变量读取，不写入配置文件
```

**手动导入支持**（Phase 1 即可使用）：

```text
在 Phase 1 中，用户可以手动将 PDF 放入 data/literature/ 目录，
然后调用 parse_and_ingest() 解析入库。

API 路由:
  POST /api/literature/ingest   → 解析指定目录下的 PDF 并入库
  GET  /api/literature/list     → 查看已入库文献列表
```

---

### 2.2 ResearchAnalystAgent（科研产出）

| 属性 | 值 |
| --- | --- |
| 标识 | `research_analyst` |
| LLM | 强推理大模型（Claude / GPT-4 级别） |
| 场景 | B（科研产出） |
| 依赖 | matplotlib + 绘图模板 |

**职责**：
1. 论文级深度数据分析
2. 数据缺口识别与补充建议
3. 按期刊风格科研绘图
4. 文献对比分析
5. 论文段落撰写辅助

**使用 Skill**：
- `KnowledgeQuerySkill`（共享只读）— 查询文献和实验数据
- `ResearchPlottingSkill`（专属）— 科研绘图
- `WritingAssistSkill`（专属）— 论文撰写辅助

**核心方法**：

```python
class ResearchAnalystAgent(BaseAgent):

    # ========== 深度数据分析 ==========

    async def deep_analysis(self, experiment_ids: list[str] = None,
                             project_id: str = None) -> dict:
        """论文级深度数据分析。

        与 Phase 1 的 DataAnalysisSkill 区别：
        - DataAnalysisSkill: 在线、快速、确定性逻辑、单次实验
        - deep_analysis: 离线、深度、LLM 推理、多实验综合

        分析内容:
        1. 性能解读（不只是数字，而是意义）
           "过电位 182mV 在同类 Fe-Co-Ni 催化剂中处于前 10%"
        2. 机理推断
           "Tafel 斜率 68mV/dec 接近 Volmer-Heyrovsky 机理"
        3. 配比-性能关系建模
           "Co 含量与过电位呈 U 型关系，最优区间 40-55%"
        4. 异常实验识别与解释
           "第 3 轮数据偏离趋势，可能因泵校准偏差"
        5. 统计显著性评估
           "最优配比与次优配比差异在 95% 置信区间内显著"

        返回:
        {
            "summary": "综合分析摘要...",
            "performance_ranking": [...],
            "composition_effect": {...},
            "mechanism_insights": "...",
            "anomalies": [...],
            "statistical_tests": {...}
        }
        """

    async def identify_data_gaps(self, project_id: str) -> dict:
        """识别数据缺口，建议补充实验。

        返回:
        {
            "gaps": [
                {
                    "type": "missing_characterization",
                    "description": "缺少 EIS 数据，无法证明电荷转移电阻",
                    "priority": "high",
                    "suggestion": "对最优 3 个样品补做 EIS 测试"
                },
                {
                    "type": "insufficient_stability",
                    "description": "未做长期稳定性测试",
                    "priority": "high",
                    "suggestion": "对最优样品做 1000 圈 ADT + 12h 计时电流"
                },
                {
                    "type": "sparse_region",
                    "description": "Co 45-55% 区间数据点不足",
                    "priority": "medium",
                    "suggestion": "在该区间补充 3-5 个实验点"
                }
            ],
            "completeness_score": 0.65  # 数据完整度评分
        }
        """

    # ========== 科研绘图 ==========

    async def generate_figures(self, project_id: str,
                                figure_types: list[str] = None,
                                journal_style: str = "nature_energy") -> dict:
        """按期刊风格生成科研图表。

        figure_types 可选:
        - "lsv_polarization"    : LSV 极化曲线（多样品叠加）
        - "tafel_plot"          : Tafel 图
        - "eis_nyquist"         : EIS Nyquist 图
        - "eis_bode"            : EIS Bode 图
        - "optimization_curve"  : 优化过程收敛图
        - "composition_heatmap" : 元素配比-性能热力图
        - "comparison_bar"      : 与文献对比柱状图
        - "stability_test"      : 稳定性测试图

        journal_style 可选:
        - "nature_energy"       : Nature Energy 风格
        - "acs_catalysis"       : ACS Catalysis 风格
        - "jacs"                : JACS 风格
        - "angew_chem"          : Angew. Chem. 风格
        - "custom"              : 自定义（读取 configs/plot_styles/custom.toml）

        返回:
        {
            "figures": [
                {
                    "type": "lsv_polarization",
                    "path_svg": "output/figures/lsv_polarization.svg",
                    "path_png": "output/figures/lsv_polarization.png",
                    "caption": "Fig. 1. LSV polarization curves of Fe-Co-Ni..."
                }, ...
            ],
            "style_applied": "nature_energy"
        }
        """

    # ========== 文献对比 ==========

    async def literature_comparison(self, project_id: str) -> dict:
        """与文献数据对比分析。

        流程:
        1. 从知识库 literature/ 提取同类催化剂性能数据
        2. 构建对比表格（我们的结果 vs 文献报道）
        3. LLM 分析优势和不足
        4. 生成对比图表

        返回:
        {
            "comparison_table": [
                {
                    "catalyst": "本工作 Fe0.3Co0.5Ni0.2",
                    "overpotential_mV": 182,
                    "tafel_mV_dec": 68,
                    "source": "this_work"
                },
                {
                    "catalyst": "Fe-Co-Ni (Ref. 12)",
                    "overpotential_mV": 210,
                    "tafel_mV_dec": 78,
                    "source": "doi:10.1021/..."
                }, ...
            ],
            "advantages": ["过电位低于大部分文献报道...", ...],
            "limitations": ["缺少 XPS 表征数据...", ...],
            "figure_path": "output/figures/literature_comparison.svg"
        }
        """

    # ========== 论文撰写辅助 ==========

    async def draft_section(self, project_id: str,
                             section: str,
                             language: str = "english") -> dict:
        """生成论文段落草稿。

        section 可选:
        - "results_discussion"  : Results and Discussion
        - "experimental"        : Experimental Section
        - "introduction_snippet": Introduction 中的相关工作段落
        - "figure_captions"     : 所有图表的 caption
        - "abstract"            : 摘要草稿

        language: "english" | "chinese"

        返回:
        {
            "section": "results_discussion",
            "draft": "The optimized Fe0.3Co0.5Ni0.2 catalyst exhibited...",
            "references_used": ["doi:...", "doi:..."],
            "word_count": 850,
            "notes": "建议补充 XPS 数据后再完善电子结构讨论部分"
        }
        """

    async def compile_references(self, project_id: str,
                                  format: str = "acs") -> dict:
        """整理参考文献列表。

        format: "acs" | "nature" | "rsc" | "bibtex" | "endnote"

        返回:
        {
            "references": [...],
            "format": "acs",
            "output_path": "output/references.bib"
        }
        """
```

---

## 三、新增 Skill（Phase 2）

### 3.1 ResearchPlottingSkill（科研绘图，ResearchAnalyst 专属）

```python
class ResearchPlottingSkill:
    """科研绘图引擎。

    基于 matplotlib，预定义期刊风格模板。
    ResearchAnalystAgent 专属。
    """

    def __init__(self, style: str = "nature_energy"):
        self.style_config = self._load_style(style)

    def plot_lsv(self, datasets: list[dict], **kwargs) -> str:
        """绘制 LSV 极化曲线。"""

    def plot_tafel(self, datasets: list[dict], **kwargs) -> str:
        """绘制 Tafel 图。"""

    def plot_eis_nyquist(self, datasets: list[dict], **kwargs) -> str:
        """绘制 EIS Nyquist 图。"""

    def plot_composition_heatmap(self, data: dict, **kwargs) -> str:
        """绘制元素配比-性能热力图（三元相图）。"""

    def plot_optimization_curve(self, history: list[dict], **kwargs) -> str:
        """绘制优化过程收敛图。"""

    def plot_comparison_bar(self, our_data: dict,
                             literature_data: list[dict], **kwargs) -> str:
        """绘制与文献对比柱状图。"""

    def _load_style(self, style: str) -> dict:
        """加载期刊风格配置。
        从 configs/plot_styles/{style}.toml 读取：
        - 字体（family, size）
        - 颜色方案
        - 线宽、标记大小
        - 图表尺寸（单栏/双栏）
        - DPI
        """
```

**期刊风格配置示例** (`configs/plot_styles/nature_energy.toml`)：

```toml
[style]
name = "Nature Energy"

[font]
family = "Arial"
title_size = 10
label_size = 9
tick_size = 8
legend_size = 8

[figure]
single_column_width_inch = 3.5
double_column_width_inch = 7.0
dpi = 300
format = ["svg", "png", "pdf"]

[colors]
palette = ["#E64B35", "#4DBBD5", "#00A087", "#3C5488",
           "#F39B7F", "#8491B4", "#91D1C2", "#DC0000"]

[line]
width = 1.5
marker_size = 6

[axes]
linewidth = 1.0
tick_direction = "in"
tick_length = 4
```

### 3.2 WritingAssistSkill（论文撰写辅助，ResearchAnalyst 专属）

```python
class WritingAssistSkill:
    """论文撰写辅助。

    提供模板化的论文段落生成能力。
    ResearchAnalystAgent 专属。
    """

    async def generate_results_discussion(self, analysis: dict,
                                           figures: list[dict],
                                           literature: list[dict],
                                           language: str) -> str:
        """生成 Results and Discussion 段落。

        输入:
        - analysis: deep_analysis 的结果
        - figures: 已生成的图表信息
        - literature: 相关文献数据
        - language: 输出语言

        LLM prompt 策略:
        - 按照"观察→解释→对比→意义"的逻辑组织
        - 每个图表对应一段讨论
        - 引用文献时标注 DOI
        - 使用学术英语/中文
        """

    async def generate_figure_caption(self, figure_info: dict) -> str:
        """生成单个图表的 caption。"""

    async def generate_abstract(self, full_analysis: dict,
                                 key_figures: list[dict]) -> str:
        """生成摘要草稿。"""
```

---

## 四、Phase 2 文件结构（增量）

```text
AutoHySeeker/
├── src/
│   ├── agents/
│   │   ├── literature_agent.py          # 新增：文献自动化
│   │   └── research_analyst.py          # 新增：科研产出
│   │
│   ├── skills/
│   │   ├── research_plotting_skill.py   # 新增：科研绘图
│   │   └── writing_assist_skill.py      # 新增：论文撰写辅助
│   │
│   ├── browser/                          # 新增目录
│   │   ├── __init__.py
│   │   ├── browser_tool.py              # AI 浏览器封装
│   │   └── auth_handlers.py             # 学校 SSO 认证处理
│   │
│   ├── api/routes/
│   │   ├── literature.py                # 新增：文献管理路由
│   │   └── research.py                  # 新增：科研产出路由
│   │
│   └── tools/
│       └── pdf_parser.py                # 新增：PDF 解析工具
│
├── configs/
│   ├── literature.toml                  # 新增：文献检索配置
│   ├── research_analyst.toml            # 新增：科研分析配置
│   └── plot_styles/                     # 新增目录
│       ├── nature_energy.toml
│       ├── acs_catalysis.toml
│       ├── jacs.toml
│       ├── angew_chem.toml
│       └── custom.toml
│
├── data/
│   └── literature/                      # PDF 存储目录
│
└── output/                              # 新增目录
    ├── figures/                          # 生成的图表
    ├── drafts/                           # 论文草稿
    └── references/                       # 参考文献
```

---

## 五、Phase 2 API 路由

```text
# 文献管理（Phase 2A）
POST /api/literature/search       → LiteratureAgent.search_literature()
POST /api/literature/download     → LiteratureAgent.download_papers()
POST /api/literature/ingest       → LiteratureAgent.parse_and_ingest()
GET  /api/literature/list         → 查看已入库文献
GET  /api/literature/download-list → 获取待下载清单

# 科研产出（Phase 2B）
POST /api/research/deep-analysis  → ResearchAnalyst.deep_analysis()
POST /api/research/data-gaps      → ResearchAnalyst.identify_data_gaps()
POST /api/research/figures        → ResearchAnalyst.generate_figures()
POST /api/research/comparison     → ResearchAnalyst.literature_comparison()
POST /api/research/draft          → ResearchAnalyst.draft_section()
POST /api/research/references     → ResearchAnalyst.compile_references()
```

---

## 六、Phase 2 实施步骤

### Phase 2A：文献自动化

1. 创建 `tools/pdf_parser.py` — PDF 文本提取
2. 创建 `browser/browser_tool.py` — AI 浏览器封装
3. 创建 `browser/auth_handlers.py` — 学校 SSO 认证
4. 创建 `agents/literature_agent.py` — LiteratureAgent
5. 扩展 `KnowledgeArchiveSkill` — 支持 literature/ 分区写入
6. 创建 `api/routes/literature.py` — 文献管理路由
7. 创建 `configs/literature.toml` — 文献检索配置

### Phase 2B：科研产出

8. 创建期刊风格配置 `configs/plot_styles/*.toml`
9. 创建 `skills/research_plotting_skill.py` — 科研绘图引擎
10. 创建 `skills/writing_assist_skill.py` — 论文撰写辅助
11. 创建 `agents/research_analyst.py` — ResearchAnalystAgent
12. 创建 `api/routes/research.py` — 科研产出路由
13. 创建 `configs/research_analyst.toml` — 科研分析配置

---

## 七、Phase 2 Agent 完整清单（含 Phase 1）

| # | Agent | 标识 | Phase | 职责 |
| --- | --- | --- | --- | --- |
| 1 | OrchestratorAgent | `orchestrator` | 1 | 调度中心 + 决策 |
| 2 | ExperimentDesignerAgent | `exp_designer` | 1 | 参数生成 |
| 3 | ExperimentExecutorAgent | `exp_executor` | 1 | 执行 + 监控 |
| 4 | DiagnosticsExpertAgent | `diagnostics` | 1 | 故障诊断 |
| 5 | ChatAgent | `chat` | 1 | 综合问答 |
| 6 | LiteratureAgent | `literature` | 2A | 文献自动化 |
| 7 | ResearchAnalystAgent | `research_analyst` | 2B | 科研产出 |

## 八、Phase 2 Skill 完整清单（含 Phase 1）

| Skill | 归属 | 共享/专属 | Phase |
| --- | --- | --- | --- |
| DataAnalysisSkill | Orchestrator | 专属 | 1 |
| KnowledgeArchiveSkill | Orchestrator + Literature | 受限共享 | 1+2A |
| KnowledgeQuerySkill | 公共 | 共享 | 1 |
| RealtimeMonitorSkill | Executor | 专属 | 1 |
| HeartbeatInspectorSkill | Executor | 专属 | 1 |
| ResearchPlottingSkill | ResearchAnalyst | 专属 | 2B |
| WritingAssistSkill | ResearchAnalyst | 专属 | 2B |

---

> 本文档定义了 Phase 2 的完整技术方案。Phase 2A 和 2B 可以并行开发，但 2B 的文献对比功能依赖 2A 的文献入库能力。实现时应严格按照本文档的 Agent 职责、Skill 归属和 API 路由进行开发。

# 文献自动获取与知识沉淀 — 规划与技术路线

> 2026-02-23 | 状态：**规划阶段，暂不实施**
> 对应需求域：① 文献与知识获取 + ⑨ 研究策略
> 核心需求：自动下载文献 → 结构化提取 → 摘要生成 → 充实RAG知识库

---

## 一、需求理解

### 1.1 你的核心诉求

```
论文PDF获取（含闭源/需登录的）
         │
         ▼
    自动下载到本地
         │
         ▼
    AI 结构化提取（方法、参数、结果、结论）
         │
         ▼
    生成摘要 + 入RAG库
         │
         ▼
    后续实验设计/分析时可检索引用
```

### 1.2 子需求分解

| 编号 | 子需求 | 描述 | 难点 |
|------|--------|------|------|
| **L1** | 文献发现 | 根据关键词/主题自动搜索相关论文 | API 限制、相关性排序 |
| **L2** | 自动下载 | 从出版商网站下载 PDF（含登录、CAPTCHA） | 反爬、人机验证、版权 |
| **L3** | PDF 解析 | 提取纯文本、表格、图片、公式 | 排版多样、扫描件OCR |
| **L4** | 结构化提取 | 提取方法参数、实验条件、关键结果 | 需要领域理解 |
| **L5** | 摘要生成 | 生成结构化摘要（目的/方法/结果/结论） | LLM 长文本 |
| **L6** | 知识入库 | 分块 + Embedding → 入 RAG 向量库 | 分块策略、元数据 |
| **L7** | 定期更新 | 监控新文献 → 自动触发 L1-L6 | 定时任务 |
| **L8** | 文献对比表 | 多篇论文自动生成方法/结果对比表 | LLM 多文档推理 |

---

## 二、技术路线

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                   Literature Agent Pipeline                      │
│                                                                  │
│  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌───────────────┐  │
│  │ L1 搜索  │──▶│ L2 下载  │──▶│ L3 解析   │──▶│ L4-L5 提取+摘要│ │
│  │ Scholar  │   │ VL+浏览器│   │ pymupdf  │   │ LLM 结构化    │  │
│  │ API      │   │ 自动化   │   │ marker   │   │               │  │
│  └─────────┘   └─────────┘   └──────────┘   └───────┬───────┘  │
│                                                       │          │
│                                                ┌──────▼───────┐  │
│                                                │ L6 RAG 入库   │  │
│                                                │ ChromaDB     │  │
│                                                └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 L1 — 文献发现

**方案**：

| 数据源 | 接入方式 | 优缺点 |
|--------|----------|--------|
| **Semantic Scholar API** | REST API（免费，无需登录） | 英文为主，速度快，有引用图 |
| **PubMed / Entrez API** | Biopython `Entrez`（免费） | 生物医学为主 |
| **CrossRef API** | REST API（免费） | DOI 元数据全，但无全文 |
| **Google Scholar** | `scholarly` 库（非官方） | 最全，但容易被封 |
| **arXiv API** | REST（免费） | 预印本，开放获取 |
| **知网 / 万方** | 无公开 API，需爬虫或 VL 模型 | 中文文献 |

**推荐组合**：Semantic Scholar（主力） + PubMed（补充） + arXiv（预印本）

**实现**：
```python
# tools/literature_search.py
async def search_semantic_scholar(query: str, year_range?: tuple, limit?: int) -> List[PaperMeta]
async def search_pubmed(query: str, limit?: int) -> List[PaperMeta]  
async def search_arxiv(query: str, limit?: int) -> List[PaperMeta]
async def search_all(query: str, sources?: List[str]) -> List[PaperMeta]

@dataclass
class PaperMeta:
    title: str
    authors: List[str]
    year: int
    doi: str
    abstract: str
    source: str          # "semantic_scholar" | "pubmed" | "arxiv"
    pdf_url: str | None  # 开放获取的PDF链接
    venue: str           # 期刊/会议
    citations: int
    is_open_access: bool
```

**依赖**：`httpx`, `scholarly`(可选), `biopython`(可选)

### 2.3 L2 — 自动下载（核心难点）

#### 2.3.1 开放获取（简单路径）

很多论文有 Open Access PDF，直接下载即可：
- Semantic Scholar / Unpaywall API → 获取 OA PDF URL → `httpx` 下载
- arXiv → 全部开放

```python
async def download_open_access(doi: str) -> Path | None:
    """尝试从 Unpaywall/S2 获取 OA PDF"""
    ...
```

#### 2.3.2 机构登录 + VL 模型自动化下载（复杂路径）

> **这是你提到的核心需求**：很多文献需要在出版商网站登录机构账号才能下载。

**技术方案：Browser Automation + VL Model**

```
┌───────────────┐     ┌──────────────┐     ┌────────────────┐
│  Playwright   │────▶│  截图/DOM    │────▶│  VL Model      │
│  (无头浏览器)  │     │  状态捕获    │     │  (理解页面)     │
│               │◀────│              │◀────│  → 输出动作     │
│  执行点击/输入 │     │  每步截图    │     │  click(x,y)    │
│               │     │              │     │  type("pwd")   │
└───────────────┘     └──────────────┘     └────────────────┘
```

**详细流程**：

```
1. 给定 DOI / URL → Playwright 打开出版商页面
2. VL 模型截图 → 理解当前状态：
   - "这是登录页面" → 输入凭证
   - "这是 CAPTCHA" → 通知人类介入 / 尝试 CAPTCHA solver
   - "这是下载按钮" → 点击下载
   - "需要跳转到机构" → 点击 Shibboleth/OAuth
3. 下载 PDF → 保存到本地
4. 验证 PDF 完整性
```

**VL 模型选择**：

| 模型 | 说明 | 适用场景 |
|------|------|----------|
| **GPT-4o** | 最强视觉理解 | 复杂页面、多语言 |
| **Qwen2-VL-72B** (本地) | 开源 SOTA | 隐私敏感、大量调用 |
| **Claude 3.5 Sonnet** | 优秀视觉 | 备选 |
| **CogAgent-18B** | 专为 GUI 操作设计 | 最适合 GUI 自动化 |

**关键组件**：

```python
# tools/literature_downloader.py

class BrowserAutomationDownloader:
    """VL 模型驱动的浏览器自动化下载器"""
    
    def __init__(self, vl_model: VLModel, browser: PlaywrightBrowser):
        self.vl = vl_model
        self.browser = browser
        self.credentials = load_credentials()  # 机构账号（加密存储）
    
    async def download_paper(self, doi: str, output_dir: Path) -> DownloadResult:
        """
        1. 导航到出版商页面
        2. VL 模型循环：截图 → 理解 → 决策 → 执行
        3. 处理登录、CAPTCHA、重定向
        4. 下载并验证 PDF
        """
        
    async def _vl_decide_action(self, screenshot: bytes, context: str) -> Action:
        """VL 模型看截图 → 输出下一步动作"""
        prompt = f"""
        你正在从学术出版商网站下载论文。
        当前页面截图如下。
        上下文: {context}
        
        请判断当前状态并指定下一步动作：
        - navigate(url): 跳转
        - click(selector_or_coords): 点击
        - type(selector, text): 输入文本
        - wait(seconds): 等待
        - download_ready(element): 点击下载
        - need_human(reason): 需要人工介入
        - done(file_path): 下载完成
        - failed(reason): 失败
        
        返回 JSON: {{"action": "...", "params": {{...}}, "reasoning": "..."}}
        """
        return await self.vl.analyze(screenshot, prompt)
    
    async def _handle_captcha(self, screenshot: bytes) -> bool:
        """
        CAPTCHA 处理策略：
        1. 简单文字验证码 → VL 模型识别
        2. reCAPTCHA v2 → 尝试 audio challenge
        3. 复杂交互式 → 通知用户手动完成
        """
        ...
```

#### 2.3.3 人机协作模式

不是所有下载都能全自动完成。设计一个**半自动模式**：

```
全自动路径：OA Paper → 直接下载 ✅
半自动路径：
  1. Bot 打开页面、登录、导航到下载页
  2. 遇到 CAPTCHA → 弹窗通知用户
  3. 用户手动完成验证 → Bot 继续下载
  4. 下载完成 → 自动进入解析流水线
```

**依赖**：`playwright`, `openai`(VL), `keyring`(凭证安全存储)

### 2.4 L3 — PDF 解析

| 方案 | 库 | 优势 | 劣势 |
|------|-----|------|------|
| **pymupdf (fitz)** | `pymupdf` | 快速、文本提取好 | 表格/公式弱 |
| **marker** | `marker-pdf` | 端到端 PDF→Markdown，保留结构 | 较重 |
| **Nougat** | `nougat-ocr` | Meta 出品，学术PDF专用 | 需 GPU |
| **GROBID** | Java 服务 | 学术出版物结构解析最强 | 需部署 Java |
| **VL 模型直接理解** | GPT-4o | 图表/公式都能理解 | 贵、Token多 |

**推荐**：pymupdf（基础文本） + marker（结构化）+ VL 模型（图表/公式）

```python
# rag/pdf_parser.py

class AcademicPDFParser:
    """学术 PDF 多策略解析"""
    
    async def parse(self, pdf_path: Path) -> ParsedPaper:
        # 1. pymupdf 快速提取文本
        raw_text = self._extract_with_pymupdf(pdf_path)
        
        # 2. marker 提取结构化 Markdown（保留标题/表格/引用）
        structured_md = self._extract_with_marker(pdf_path)
        
        # 3. 识别图表页 → VL 模型理解图表内容
        figures = self._extract_figures(pdf_path)
        figure_descriptions = [await self.vl.describe(fig) for fig in figures]
        
        return ParsedPaper(
            raw_text=raw_text,
            structured_markdown=structured_md,
            sections=self._split_sections(structured_md),  # 按章节分割
            figures=figure_descriptions,
            tables=self._extract_tables(pdf_path),
            references=self._extract_references(raw_text)
        )

@dataclass
class ParsedPaper:
    raw_text: str
    structured_markdown: str
    sections: Dict[str, str]     # {"Introduction": "...", "Methods": "...", ...}
    figures: List[FigureInfo]
    tables: List[TableInfo]
    references: List[Reference]
```

### 2.5 L4 — 结构化信息提取

```python
# skills/literature/extract_paper_info.py

EXTRACTION_PROMPT = """
你是电化学领域的论文分析专家。请从以下论文中提取结构化信息：

{paper_markdown}

请提取并返回 JSON:
{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "year": 2025,
  "journal": "期刊名",
  "doi": "...",
  
  "research_question": "核心研究问题",
  "hypothesis": "科学假说（如有）",
  
  "methods": {
    "electrode_material": "电极材料",
    "electrolyte": "电解液组成和浓度",
    "reference_electrode": "参比电极类型",
    "techniques_used": ["CV", "EIS", "LSV"],
    "scan_rate": "扫描速率 (mV/s)",
    "potential_range": "电位范围 (V)",
    "temperature": "温度",
    "other_conditions": {}
  },
  
  "key_results": [
    {"metric": "过电位", "value": "320 mV", "condition": "10 mA/cm²"},
    {"metric": "Tafel 斜率", "value": "65 mV/dec", "condition": ""},
    {"metric": "稳定性", "value": "1000 圈后衰减 5%", "condition": ""}
  ],
  
  "conclusions": ["结论1", "结论2"],
  "innovations": ["创新点1"],
  "limitations": ["局限1"],
  
  "relevance_to_microfluidics": "与微流体电化学的相关性分析",
  "reproducibility_info": "可重复性相关信息（如有）"
}
"""
```

### 2.6 L5 — 摘要与知识入库

```python
# skills/literature/ingest_paper.py

class PaperIngestionSkill:
    """论文全流程处理：解析 → 提取 → 摘要 → 入库"""
    
    async def execute(self, pdf_path: Path, collection: str = "literature") -> SkillResult:
        # 1. PDF 解析
        parsed = await self.pdf_parser.parse(pdf_path)
        
        # 2. 结构化提取
        paper_info = await self.llm.extract(EXTRACTION_PROMPT, parsed.structured_markdown)
        
        # 3. 生成多层摘要
        brief_summary = await self.llm.summarize(parsed.raw_text, style="brief")      # 100字
        detailed_summary = await self.llm.summarize(parsed.raw_text, style="detailed") # 500字
        
        # 4. 分块入向量库
        chunks = self.chunker.chunk(
            parsed.structured_markdown,
            metadata={
                "source": pdf_path.name,
                "doi": paper_info["doi"],
                "year": paper_info["year"],
                "techniques": paper_info["methods"]["techniques_used"],
                "summary": brief_summary
            }
        )
        
        # 5. 特殊处理：方法段单独入"方法知识库"
        if "Methods" in parsed.sections:
            self.rag.ingest_text(
                parsed.sections["Methods"],
                collection="experiment_methods",
                metadata={"doi": paper_info["doi"], "type": "method"}
            )
        
        # 6. 结构化数据入"论文元数据库"（SQLite/JSON）
        self.paper_db.save(paper_info)
        
        return SkillResult(success=True, data=paper_info, summary=brief_summary)
```

### 2.7 L7 — 定期监控与更新

```python
# scripts/literature_monitor.py

class LiteratureMonitor:
    """定期检查新文献"""
    
    def __init__(self, watch_queries: List[str], check_interval_hours: int = 24):
        self.queries = watch_queries  # 监控的搜索词列表
        # e.g. ["microfluidic electrochemistry catalyst screening",
        #        "high-throughput electrochemical measurement",
        #        "微流体 电化学 催化剂筛选"]
    
    async def check_new_papers(self):
        """检查新论文"""
        for query in self.queries:
            results = await search_semantic_scholar(query, year_range=(2025, 2026))
            new_papers = self._filter_already_ingested(results)
            
            for paper in new_papers:
                if paper.is_open_access and paper.pdf_url:
                    pdf = await download_open_access(paper.doi)
                    if pdf:
                        await paper_ingestion_skill.execute(pdf)
                else:
                    self.queue_for_manual_download(paper)
            
            # 生成新论文摘要推送
            if new_papers:
                summary = await self.llm.summarize_new_papers(new_papers)
                self.notify(summary)  # 推送给用户
```

---

## 三、关键技术挑战与应对

### 3.1 VL 模型 GUI 自动化的可靠性

| 挑战 | 应对策略 |
|------|---------|
| 页面布局多样性 | VL 模型的优势恰恰是泛化能力，不需要为每个网站写规则 |
| CAPTCHA | 分级策略：简单的 VL 识别 → 复杂的人工介入 |
| 登录状态维持 | Playwright persistent context，Cookie 持久化 |
| 出版商反爬 | 控制频率（每分钟 1-2 次）、随机延迟、使用真实浏览器指纹 |
| 下载失败重试 | 队列 + 重试机制 + 失败日志 |
| 版权合规 | 仅下载有机构授权的论文，不进行再分发 |

### 3.2 PDF 解析质量

| 挑战 | 应对策略 |
|------|---------|
| 双栏排版 | marker / Nougat 专门处理学术排版 |
| 公式提取 | VL 模型识别公式图片 → LaTeX |
| 表格提取 | pymupdf + camelot / tabula |
| 图表理解 | VL 模型描述图表内容 |
| 扫描件 PDF | OCR（Tesseract / PaddleOCR） |

### 3.3 提取准确性

| 挑战 | 应对策略 |
|------|---------|
| 数值提取错误 | LLM 提取 + 规则校验（电位不可能 > 10V 等） |
| 单位不统一 | 标准化转换模块 |
| 领域术语歧义 | Fine-tuned extraction prompt + 电化学知识 |

---

## 四、数据流与存储设计

```
Literature Pipeline 数据存储：

AutoHySeeker/data/
├── papers/                       # 下载的原始 PDF
│   ├── 2025_author_title.pdf
│   └── ...
├── parsed/                       # 解析后的结构化数据
│   ├── 2025_author_title/
│   │   ├── full_text.md          # Markdown 全文
│   │   ├── paper_info.json       # 结构化元信息
│   │   ├── sections/             # 各章节
│   │   ├── figures/              # 提取的图片
│   │   └── tables/               # 提取的表格
│   └── ...
├── paper_index.sqlite            # 论文元数据库（可检索）
└── vector_db/                    # ChromaDB（已在 RAG 共享）
    ├── literature/               # 文献全文向量
    └── experiment_methods/       # 方法段专用向量
```

---

## 五、与 AutoHySeeker 核心 Skills 的联动

```
文献系统产出的知识 → 增强其他 Skills：

Skill B1 (generate_experiment_plan)
  └─ RAG 检索文献中类似实验的参数 → 参考生成方案

Skill B3 (validate_and_review)
  └─ RAG 检索文献中的典型参数范围 → 校验参数合理性

Skill B4 (replicate_literature)
  └─ 直接从 parsed paper_info.json 获取方法参数 → 自动复现

Skill A1/A2 (实验分析)
  └─ 分析结果与文献值对比 → "你的过电位 320mV，文献报道范围 280-350mV"

Skill E2 (knowledge_qa)
  └─ "IrO₂ 在酸性 OER 中的 Tafel 斜率文献值？" → 从文献 RAG 回答
```

---

## 六、实施优先级建议

| 阶段 | 内容 | 优先级 | 依赖 |
|------|------|--------|------|
| **P1** | PDF 解析 + LLM 提取 + RAG 入库 | 🟢 高 | pymupdf, OpenAI |
| **P2** | 开放获取论文自动搜索+下载 | 🟢 高 | Semantic Scholar API |
| **P3** | 文献结构化对比表生成 | 🟡 中 | P1 完成 |
| **P4** | VL 模型驱动的浏览器自动化下载 | 🟡 中 | Playwright, VL model |
| **P5** | 定期新文献监控 | 🔴 低 | P1+P2 完成 |
| **P6** | 知网/万方中文文献 | 🔴 低 | P4 路线成熟后 |

> **建议**：先做 P1（手动放 PDF → 自动解析入库），最实用最快出效果。
> P4（VL 模型下载）作为独立模块慢慢打磨。

---

## 七、技术栈总结

| 组件 | 方案 | 备选 |
|------|------|------|
| 文献搜索 | Semantic Scholar API + PubMed | Google Scholar (scholarly) |
| OA 下载 | Unpaywall API + httpx | Sci-Hub (灰色地带) |
| 浏览器自动化 | Playwright | Selenium |
| VL 模型 | GPT-4o / Qwen2-VL | CogAgent |
| PDF 解析 | pymupdf + marker | Nougat, GROBID |
| 图表理解 | GPT-4o Vision | Qwen2-VL |
| 文本分块 | langchain_text_splitters | 自定义 |
| 向量库 | ChromaDB（与 AutoHySeeker 共享） | — |
| 元数据库 | SQLite | PostgreSQL |
| 凭证存储 | keyring | 加密配置文件 |

---

*此文档为规划文档，暂不实施。待 AutoHySeeker 核心 Skills (②③④⑤+RAG) 基本完成后，再启动文献管线开发。*

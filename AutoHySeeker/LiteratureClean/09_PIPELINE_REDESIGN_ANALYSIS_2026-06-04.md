# 预处理流水线重构 & 检索方案设计

> 日期：2026-06-07（更新）
> 状态：方案已确认，待执行
> 约束：**不修改 OpenViking 内部（MarkdownParser 等）**

---

## 0. 可行性总览

| # | 需求 | 涉及组件 | 改 MarkdownParser？ | 可行 |
|---|------|----------|---------------------|------|
| A | Paper/Section 级 abstract/overview 直接覆写 | `populate_directory_summaries()` | 否 | ✅ 已实现 |
| B | 段落原文 .md 直入主索引，不做 chunk 切分；段落节点无 abstract/overview | `import_to_openviking.py`；`semantic_processor.py` skip 扩展 | 否 | ✅ |
| C | 只按章级标题拆分 section，不细化到 1.1/1.1.1 | `clean_single_mineru_paper.py` 预处理 | 否 | ✅ |
| D | 删除 S00-S07 所有策略，仅参考 sections_by_heading | `clean_single_mineru_paper.py` 预处理 | 否 | ✅ |
| E | 三级检索 Stage（L0→L1→LLM Judge） | 新建 `qa_pipeline.py` 应用层 | 否 | ✅ |

**全部 5 条无需改动 OpenViking 内部组件。**

---

## 1. 章级标题拆分（已实现 ✅）

### 1.1 问题背景

MinerU 导出将所有标题标为 `#`（level 1），无层级区分。11 篇论文分三类：

| 类型 | 论文数 | 标题特征 | 示例 |
|------|--------|----------|------|
| A. 编号型 | 7 篇 | `1. Introduction` `2.1 Methods` `1.1.1` | 大部分期刊论文 |
| B. 全大写型 | 2 篇 | `INTRODUCTION` `RESULTS AND DISCUSSION` | ACS 期刊 |
| C. 无编号无大写 | 2 篇 | `Cathode oxidation...` `Reaction mechanism` | Nature 系列 |

### 1.2 三策略检测（按优先级）

```
Strategy A: 编号检测
  正则 ^(\d+(?:\.\d+)*)\.?\s 匹配编号
  深度=1（如 "1." "2."）        → 章级边界
  深度=2（如 "1.1" "2.3"）      → 节，归入章
  深度=3（如 "1.1.1"）           → 子节，归入章
  中文章节 （一）（二）           → 章级边界
  无深度1时：按首数字归组        → 1.x→章1, 2.x→章2

Strategy B: 全大写检测
  全大写标题（≥5个大写字母）     → 章级边界
  大小写混合标题                 → 节，归入最近的章

Strategy C: 关键词 + 内容体量
  关键词匹配：introduction, methods, results, discussion,
              conclusion, mechanism, theoretical, computation
  内容体量 > 2200 字符           → 未匹配关键词但内容充足，也作章
```

### 1.3 实现效果

| 论文 | 旧 sections | 新 sections | 策略 |
|------|------------|------------|------|
| 2017_uchino | 9 | 7 | C（关键词） |
| 2022_kim | 17 | 9 | B（全大写） |
| 2023_a_effects | 26 | 5 | A（编号） |
| 2023_uchino | 18 | 5 | A（编号） |
| 2024_jung | 15 | 4 | A（编号） |
| 2025_center | 20 | 5 | A（编号） |
| 2025_peng | 18 | 5 | A（编号） |
| 2025_sha | 26 | 8 | C（关键词+体量） |
| 2025_wang | 15 | 5 | A（编号） |
| 2026_he | 15 | 5 | A（编号） |
| 2026_unknown | 46 | 4 | A（编号+归组） |

### 1.4 段落切分规则

```
\n\n 切分 + 无长度下限
仅过滤：单独图片链接 (![](figures/...)) + 单独子图标签 (a/b/c/I/II/III)
覆盖率 ≥ 99%
```

---

## 2. 删除 S00-S07 宏分类体系

### 2.1 现状

[`clean_single_mineru_paper.py:2842`](AutoHySeeker/LiteratureClean/clean_single_mineru_paper.py#L2842) 将每个标题分类为 8 个宏标签（S00_front_matter ~ S07_back_matter），渗透到 `paragraph_index.json`、chunk YAML、`document_tree.json`、`tag_conflicts.json`。

### 2.2 改为

完全删除。section 标识直接用 `sections_by_heading/` 目录名。

```
旧：section_id  = "S05_discussion_mechanism"
    paragraph_id = "S05-P001"

新：section_id  = "003-catalysts-design-strategy"
    paragraph_id = "H03-P001"           ← heading_order + 段落序号
```

### 2.3 影响范围

| 文件 | 改动 | 规模 |
|------|------|------|
| `clean_single_mineru_paper.py` | 删除全部宏分类逻辑 | -500 行 |
| `macro_section_rules.yaml` | 删除 | -380 行 |
| `paragraph_index.json` 生成 | 字段 25→~15 | -10 字段 |
| `document_tree.json` 生成 | 删除 `macro_tags` | -5 行 |
| `tag_conflicts.json` | 删除 | 全文 |
| `quality_report.json` | 删除 macro 统计 | -5 行 |
| `import_to_openviking.py` | YAML frontmatter 字段调整 | -2 行 |

---

## 3. 段落原文 .md 直入主索引

### 3.1 现状

`build_paragraph_chunks()` 提取 `## Text` → 按字数切 chunk（<30 跳过/30-350 保持/>350 拆句）→ 生成 `.chunk.md`。

### 3.2 改为

段落 `.md` 文件不提取不切分，直接作为主索引文件。

```
sections_by_heading/{dir}/paragraphs/PRAW-000034.md
        ↓ 复制 + 改名
ov_index/sections/{dir}/H03-P002.md
        ↓
export_dir/sections/{dir}/H03-P002.md
        ↓ client.add_resource()
OpenViking 主索引
```

**段落节点不生成 abstract/overview**：扩展 `semantic_processor.py` 的 skip 条件——目录无子节点且只有 1 个 `.md` 文件时跳过。

### 3.3 影响范围

| 文件 | 改动 | 规模 |
|------|------|------|
| `import_to_openviking.py` | **删除** `build_paragraph_chunks()` | -125 行 |
| 同上 | **新增** `copy_paragraph_files()` | +40 行 |
| 同上 | `import_paper()` / `import_paper_with_backend()` 调用替换 | -6 行 |
| `semantic_processor.py` | skip 条件从「全 `.chunk.md`」→「无子节点 + 仅 1 个 `.md` 文件」 | ~5 行 |

### 3.4 导出目录结构

```
export_dir/
  paper.abstract.md
  paper.overview.md
  sections/
    003-catalysts-design-strategy/
      abstract.md           ← section 摘要
      overview.md           ← section 概述
      H03-P001.md           ← 段落原文（主索引）
      H03-P002.md
      ...
```

---

## 4. 检索 Stage 设计

> 实现位置：新建 `LiteratureClean/qa_pipeline.py`（应用层，不涉及 OpenViking 修改）

### Stage ①：混合检索 L0（语义 + 词面）

> **更新 2026-06-09**：纯向量检索对专有名词（NiCoP-Cr₂O₃）匹配弱，改为混合分数。

| 参数 | 值 |
|------|-----|
| 检索对象 | Paper L0（`.abstract.md`）+ Section L0（`.abstract.md`）混合向量库 |
| Top-k | **20** |
| 计分公式 | `L0_score = 0.55 × semantic_score + 0.45 × lexical_score` |
| semantic_score | `client.find()` 返回的 bge-m3 cosine（归一化到 [0,1]） |
| lexical_score | `0.75 × strong_match_score + 0.25 × generic_keyword_score` |
| strong_match | 材料名/化学式（NiCoP、Cr₂O₃）、专有短语（voltage increase rate）、含字母数字连字符的专有词 |
| generic_keyword | 普通关键词：voltage、degradation、stability、current、electrolysis 等 |

### Stage ②：Section 独立重打分

| 参数 | 值 |
|------|-----|
| 输入 | Stage ① 命中结果展开的 section 列表 |
| 计分公式 | `section_score = 0.55 × section_semantic + 0.45 × section_lexical` |
| section_semantic | 读 section `.abstract.md` 文本，bge-m3 本地向量化后与查询算余弦 |
| section_lexical | 对 section abstract 做同 Stage ① 的词面匹配 |
| Top-k | 5 个最相关章节 |

### Stage ③：LLM Judge（段落选择）

| 参数 | 值 |
|------|-----|
| 输入 | 命中章节 `sections/by-heading/{dir}/paragraphs/` 下所有 `Pxxx.md` 原文（编号 P001, P002...） |
| 逻辑 | LLM 阅读全部段落文本，判断哪些与查询相关 |
| 输出 | 保留段落编号列表 `[P003, P005]` |
| 返回 | 对应 `Pxxx.md` 原文 + `evidence_id` + 关联图表路径（`linked_figures`、`linked_tables`） |

### Stage 流程总图

```
用户查询
  │
  ▼
Stage ①: client.find(query, target_uri="viking://resources/literature", limit=15)
  │         → 混合命中列表 [{paper_A}, {paper_B.S03}, {paper_C.S05}, ...]
  │
  ▼
Stage ②: 遍历命中 → client.overview(uri) 读取 L1
  │         paper 级命中 → L1 导航到相关 section
  │         section 级命中 → 直接确认
  │         → Top-5 章节
  │
  ▼
Stage ③: 读取 paragraphs/*.md → LLM Judge 逐段判断相关性
  │         → 保留 {P003, P005, ...}
  │
  ▼
返回: Pxxx.md 原文 + evidence_id + linked_figures + linked_tables
```

---

## 5. OpenViking 最终目录结构

```
{paper_id}/
  .abstract.md              ← Paper L0（已覆写）
  .overview.md              ← Paper L1（已覆写）
  {truncated_id}/           ← 根文档节点
    H03-P001/               ← 段落成为独立文档节点
      H03-P001.md           ← 段落原文（无 .abstract/.overview，SemanticProcessor 已跳过）
    H03-P002/
      H03-P002.md
    ...
  sections/                 ← Section 目录节点
    003-catalysts-design-strategy/
      .abstract.md          ← Section L0（已覆写）
      .overview.md          ← Section L1（已覆写）
```

**说明**：段落文件因 OpenViking MarkdownParser 行为会被包装为独立文档节点（在 `{truncated_id}/` 下），不在 `sections/` 目录内。这是 MarkdownParser 固有行为。功能上无影响——段落可通过向量检索找到，section 归属记录在段落文件的 YAML frontmatter `section_id` 字段。

---

## 6. 综合影响汇总

### 6.1 代码量变化

| 类别 | 当前 | 改动后 |
|------|------|--------|
| 宏分类逻辑 (`clean_single_mineru_paper.py`) | ~500 行 | 0 |
| 分类规则 (`macro_section_rules.yaml`) | 380 行 | 0 |
| chunk 生成 (`build_paragraph_chunks`) | 125 行 | 0 |
| 段落复制 (`copy_paragraph_files`) | 0 | +40 行 |
| 冲突检测 (`build_tag_conflicts_report`) | ~30 行 | 0 |
| SemanticProcessor skip 扩展 | 0 | +5 行 |
| QA Pipeline (`qa_pipeline.py`) | 0 | +150 行 |
| **净变化** | — | **-840 行** |

### 6.2 数据流变化

```
改动前：
  MinerU MD → split_into_sections() → S00-S07 分类 → write_sections_dir()
                 ↓
           paragraph_index.json
                 ↓
           build_paragraph_chunks()（提取 ## Text + 拆句）
                 ↓
           .chunk.md → 主索引

改动后：
  MinerU MD → split_by_chapter() → write_sections_dir()
                 ↓
           paragraph_index.json
                 ↓
           copy_paragraph_files()（直接复制段落 .md）
                 ↓
           .md → 主索引

检索：
  query → Stage① L0 混合向量检索（Top-15）
       → Stage② L1 树检索收敛到章节（Top-5）
       → Stage③ LLM Judge 段落选择 → 原文 + evidence
```

### 6.3 `paragraph_index.json` 字段变化

```
保留（~15 字段）：
  paragraph_uid, paragraph_id, heading_id, heading_uid,
  heading_text, heading_level, heading_order, doc_heading_order,
  content_path, text_preview, evidence_id, evidence_short_id,
  linked_figures, linked_tables, keywords, token_count,
  paper_id, section_id, section_title, paragraph_order,
  page_index, inferred_type, source_pdf_path, is_research_body

删除（8 字段）：
  macro_primary, macro_secondary, macro_confidence,
  macro_reasons, macro_trace, macro_conflict,
  macro_section_id, macro_section_title, original_heading

格式变化：
  section_id:   "S05_discussion_mechanism" → "005-reaction-mechanism"
  paragraph_id: "S05-P001"                 → "H05-P001"
```

---

## 7. 执行顺序

```
Step 1: 章级拆分 + 删除 S00-S07（clean_single_mineru_paper.py）
           ↓
Step 2: 段落 .md 直入索引 + 段落节点无 abstract/overview
        （import_to_openviking.py + semantic_processor.py）
           ↓
Step 3: 重新生成所有论文的 paragraph_index.json + ov_index
           ↓
Step 4: --reindex 全量重导入
           ↓
Step 5: 新建 qa_pipeline.py 实现三级检索 Stage
```

---

## 8. 验证方案

1. 选 2 篇论文（结构简单 + 复杂），重跑 `build_package()` 生成新版 `sections_by_heading/`
2. 检查 `paragraph_index.json`：无 S00-S07 字段，section_id 为目录名
3. `--dry-run` 检查导出结构：段落文件在 section 目录下，无 chunk 文件
4. 单篇实测导入：段落节点无 `.abstract.md`/`.overview.md`
5. 全量 11 篇 `--reindex`
6. 写 Stage ①→②→③ 检索脚本，用 3 条查询验证端到端

# 当前 LiteratureClean 目录与文件说明日志

更新时间: 2026-05-30
适用范围: AutoHySeeker/LiteratureClean

## 1. 文档目的

本文档用于说明当前已经落地的 LiteratureClean 预处理产物结构，重点回答:

- 顶层目录长什么样
- 每篇文献目录应该有哪些文件
- 每个文件做什么
- 哪些属于原文事实层
- 哪些属于 macro section 标签层
- 哪些属于证据回溯层
- 哪些后续可进入 OpenViking
- 哪些不应进入 OpenViking 主索引

## 2. LiteratureClean 顶层结构

当前顶层可分为四类内容:

1. 每篇文献目录（paper_id 目录）
2. 预处理与验证脚本
3. 导入/检索脚本与日志
4. 规范文档与报告

示意:

```text
LiteratureClean/
  2025_xxx_xxx_xxxxxx/
  2024_xxx_xxx_xxxxxx/
  ...
  clean_single_mineru_paper.py
  batch_clean_mineru.py
  verify_new_structure.py
  check_plan_b_compliance.py
  check_rebuild_stability.py
  import_to_openviking.py
  batch_run_log.json
  openviking_import_log.json
  preprocessing_regression_report.md
  00_LITERATURE_CLEANING_GUIDE.md
  01_FILE_LOG.md
  ...
```

## 3. 单篇文献目录标准结构

每篇文献目录（LiteratureClean/{paper_id}/）当前标准如下:

```text
{paper_id}/
  metadata.json
  full_clean.md
  original_structure_index.json
  document_tree.json
  paragraph_index.json
  evidence_links.json
  image_manifest.json
  table_manifest.json
  quality_report.json
  tag_conflicts.json
  PROCESSING_RECORD.md
  figures/
    FIG001/
      caption.md
      image_001.png|jpg|jpeg|webp
    ...
  tables/
    TAB001/
      table.md
      caption.md
      image_001.png|jpg|jpeg|webp
    ...
  sections_by_heading/
    heading_index.json
    001-front-matter/
      heading.json
      paragraphs.md
      paragraphs/
        PRAW-000040.md
        PRAW-000041.md
    002-1-introduction/
      heading.json
      paragraphs.md
      paragraphs/
        PRAW-000001.md
        ...
    ...
```

说明:

- heading 目录名使用连续 display_order 前缀（001、002、003...），不是原始 doc_heading_order。
- 首个标题页若识别为文献标题页，会命名为 001-front-matter。

## 4. 文件职责分层

### 4.1 原文事实层（Fact Layer）

这层尽量贴近原文结构与原文段落，不先做主观重组。

- full_clean.md: 清洗后的全文（保留文献阅读顺序）
- sections_by_heading/: 按原始 heading 组织的主目录（事实主结构）
- sections_by_heading/heading_index.json: heading 总索引
- sections_by_heading/*/heading.json: 单个 heading 元信息（heading_text、doc_heading_order、display_order）
- sections_by_heading/*/paragraphs/PRAW-*.md: 单段事实文本文件
- original_structure_index.json: 原始结构追溯索引（用于重建稳定性对照）
- figures/、tables/: 原图表事实资产

### 4.2 Macro Section 标签层（Classification Layer）

这层不替代事实层目录，只给段落打标签。

- paragraph_index.json:
  - macro_section_id / macro_section_title
  - macro_primary / macro_secondary
  - macro_trace（打分与规则来源）
  - macro_conflict（冲突与复核标记）
- document_tree.json:
  - 提供文档级结构视图
  - 现在包含 heading 级 display_order，便于显示层使用
- quality_report.json:
  - 不确定项、统计与质量摘要
- tag_conflicts.json:
  - 标签冲突审计结果

### 4.3 证据回溯层（Evidence Layer）

这层保证每条可检索内容都能回到原段落与原来源。

- evidence_links.json:
  - evidence_id -> content_path 映射
  - 保留 mineru_full_md_path、mineru_content_list_v2_path 等来源链路
- paragraph_index.json:
  - evidence_id / evidence_short_id
  - linked_figures / linked_tables
  - content_path
- sections_by_heading/*/paragraphs/PRAW-*.md:
  - 页面可读的证据卡，含 Evidence ID、关键词、源文件路径

## 5. 每个关键文件的作用速查

- metadata.json: paper_id、标题、来源等基础元数据
- full_clean.md: 清洗后的全文文本
- original_structure_index.json: 原始 heading/paragraph 对照索引（稳定性基线）
- document_tree.json: 文档树视图（heading 粒度）
- paragraph_index.json: 段落总表（标签+证据+路径）
- evidence_links.json: 证据回链表
- image_manifest.json: 图像资源清单
- table_manifest.json: 表格资源清单
- quality_report.json: 质量与复核统计
- tag_conflicts.json: 标签冲突记录与规则追溯
- PROCESSING_RECORD.md: 单篇处理摘要（便于人工读）
- sections_by_heading/heading_index.json: heading 索引入口
- sections_by_heading/*/heading.json: heading 元信息
- sections_by_heading/*/paragraphs.md: 当前 heading 下段落总览
- sections_by_heading/*/paragraphs/PRAW-*.md: 段落正文证据文件

## 6. OpenViking 主索引边界

### 6.1 后续可能进入 OpenViking 主索引的内容

推荐作为主索引语料（可检索正文）:

- full_clean.md
- sections_by_heading/*/paragraphs/PRAW-*.md
- figures/*/caption.md
- tables/*/table.md
- tables/*/caption.md

说明:

- paragraph_index.json 和 metadata.json 更适合作为检索后的 hydration/回填数据，而不是向量主语料。

### 6.2 不应该进入 OpenViking 主索引的内容

以下文件主要是结构/审计/运行信息，不应作为检索正文主语料:

- metadata.json
- original_structure_index.json
- document_tree.json
- paragraph_index.json
- evidence_links.json
- image_manifest.json
- table_manifest.json
- quality_report.json
- tag_conflicts.json
- PROCESSING_RECORD.md
- sections_by_heading/heading_index.json
- sections_by_heading/*/heading.json
- 各类 *_log.json、*_report.json、progress 文档

## 7. 维护与再生成建议

- 自动生成产物请勿手改: 所有 {paper_id}/ 目录内容、batch_run_log.json、openviking_import_log.json、回归报告
- 规则配置可手改: macro_section_rules.yaml、本说明文档、00_LITERATURE_CLEANING_GUIDE.md
- 规则变更后建议执行:

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
.\.venv\Scripts\python.exe LiteratureClean\batch_clean_mineru.py --overwrite
.\.venv\Scripts\python.exe LiteratureClean\verify_new_structure.py --strict
```

## 8. 当前基线结论

当前方案已经稳定为:

- 事实主结构: sections_by_heading
- 标签附加层: paragraph_index.json（含 macro 标签）
- 证据回溯层: evidence_links.json + PRAW 段落文件
- 首标题页可识别为 front matter
- heading 目录按 display_order 连续编号

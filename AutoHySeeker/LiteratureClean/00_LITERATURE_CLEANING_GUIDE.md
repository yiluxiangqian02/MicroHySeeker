# 当前文献预处理方案说明文档

更新时间: 2026-05-30
适用范围: AutoHySeeker/LiteratureClean

## 0. 先看结论（给小白）

当前方案不是“看到 Markdown 标题就直接切 section”，也不是“拿关键词硬分桶”。

当前方案是两步:

1. 先尽可能保留原文事实结构（按原始 heading + 原始段落）
2. 再在段落上附加 macro section 标签（S00-S07）

一句话: 事实层优先，标签层附加。

## 1. 输入和输出

### 1.1 输入

来自 MinerU/output/{paper_raw_dir}，核心文件有:

- full.md
- content_list_v2.json
- layout.json
- images/

### 1.2 输出

写到 LiteratureClean/{paper_id}/，核心产物有:

- full_clean.md
- sections_by_heading/
- paragraph_index.json
- evidence_links.json
- quality_report.json
- tag_conflicts.json
- document_tree.json
- figures/、tables/

## 2. 一、当前预处理方案采用什么逻辑

### 2.1 不是两种旧思路

不是思路 A:

- 只按 Markdown 的 ## / # 去切 section，然后把目录当成事实。

不是思路 B:

- 只按关键词把段落粗暴分到“引言/方法/结果”等桶里。

### 2.2 当前真实逻辑（完整链路）

步骤 1. 读取与清洗

- 从 full.md 提取正文，生成 full_clean.md。
- 提取图表与基础元数据。

步骤 2. 建立事实层主结构

- 先按原始 heading 组织 sections_by_heading/。
- 每个 heading 目录下写 heading.json、paragraphs.md、paragraphs/PRAW-*.md。
- heading 目录使用 display_order 连续编号（001、002、003...）。
- 首页若识别为标题页，首目录会命名为 001-front-matter。

步骤 3. 在段落上附加 macro 标签

- 对每段做 S00-S07 宏分类打分与规则判定。
- 处理首页特殊内容（作者、邮箱、DOI、隐式摘要）时，允许 paragraph reroute。
- 结果写回 paragraph_index.json（而不是改写事实层目录）。

步骤 4. 生成证据回溯信息

- 给段落生成 evidence_id / evidence_short_id。
- 生成 evidence_links.json，把证据和 content_path 对齐。

步骤 5. 质量与冲突审计

- 输出 quality_report.json。
- 输出 tag_conflicts.json，记录标签冲突、原因和追溯信息。

## 3. 为什么要“事实层优先，标签层附加”

这样做有三个直接好处:

- 可解释: 任何标签都能回到原始 heading 和原始段落。
- 可回放: 规则变了可以重打标签，不破坏事实层目录。
- 可审计: 冲突和不确定项能在报告中追踪，不是黑盒结果。

## 4. 二、标签如何与段落关联

标签不是单独放在别处，而是直接写入段落相关文件里。

主要位置:

- paragraph_index.json
  - macro_section_id
  - macro_section_title
  - macro_primary / macro_secondary
  - macro_trace
  - macro_conflict
- sections_by_heading/*/paragraphs/PRAW-*.md
  - 人类可读形式展示 Paragraph ID、Evidence ID、Macro Primary、Macro Secondary

也就是说:

- 一个段落有自己的事实路径（content_path）
- 同时有自己的标签字段（macro_*）
- 两者在同一条记录中绑定

## 5. 三、能不能展示每个段落对应标签

可以。

每篇文献的 paragraph_index.json 就是“段落-标签-路径”的总表。

最小查看单位是一条 paragraph 记录，典型字段包含:

- paragraph_uid
- paragraph_id
- macro_section_id
- macro_primary
- macro_secondary
- content_path
- evidence_id

## 6. 给小白的阅读顺序

1. 先看 full_clean.md，理解这篇文献内容
2. 再看 sections_by_heading/，理解原文 heading 结构
3. 打开 paragraph_index.json，看每段被打了什么标签
4. 打开 evidence_links.json，确认证据是否可回链
5. 看 quality_report.json 和 tag_conflicts.json，判断是否需要人工复核

## 7. 常见误解澄清

误解 1:

- “S00-S07 就是主目录结构。”

澄清:

- 不是。主目录是 sections_by_heading，S00-S07 是段落标签层。

误解 2:

- “一旦打错标签，原文结构就坏了。”

澄清:

- 不会。标签可重算，事实层目录仍保留。

误解 3:

- “front matter 就是一个独立章节文件。”

澄清:

- front matter 是标签语义，事实层仍按 heading 目录存放；标题页 heading 会命名为 001-front-matter。

## 8. 当前稳定口径

- 主结构: sections_by_heading
- 连续编号: 按 display_order，不按 doc_heading_order
- 标签落点: paragraph_index.json + PRAW 段落文件
- 冲突审计: tag_conflicts.json
- 回溯主链: evidence_links.json

## 9. 推荐命令

全量重建:

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
.\.venv\Scripts\python.exe LiteratureClean\batch_clean_mineru.py --overwrite
```

严格校验:

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
.\.venv\Scripts\python.exe LiteratureClean\verify_new_structure.py --strict
```

单篇查看“段落-标签-路径”:

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
.\.venv\Scripts\python.exe -c "import json, pathlib; p=pathlib.Path(r'LiteratureClean/2025_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7/paragraph_index.json'); data=json.loads(p.read_text(encoding='utf-8')); print(data[0]['paragraph_uid'], data[0]['macro_section_id'], data[0]['content_path'])"
```

## 10. 你最需要记住的一句话

先保留事实，再附加标签；标签必须可追溯到段落，段落必须可追溯到原文来源。

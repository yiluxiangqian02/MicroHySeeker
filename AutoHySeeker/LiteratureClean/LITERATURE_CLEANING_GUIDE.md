# LiteratureClean 最终预处理指导文档

更新时间: 2026-05-28

## 1. 文档定位

本文档是 MinerU -> LiteratureClean 预处理阶段的最终执行规范。

仅覆盖以下链路:

`MinerU/output/{paper_raw_dir}`
-> 自动预处理
-> `LiteratureClean/{paper_id}/`

不覆盖后续阶段（如向量化、问答、UI、外部知识库导入等）。

---

## 2. 当前目标

将每个 MinerU 论文目录自动转换为稳定、可回溯、可批量验证的 LiteratureClean 结构包，要求:

1. 统一 paper_id 规则。
2. 统一章节组织为 `paper -> macro section -> subheading group -> paragraph`。
3. 为 paragraph / figure / table 生成稳定 evidence 标识。
4. 输出结构化索引与质量报告。
5. 不再生成旧结构（`memory_cards/`、根目录 `.abstract.md/.overview.md`、`heading_index.md`、`headings/`）。

---

## 3. 数据边界

### 3.1 输入（只读）

```text
MinerU/output/{paper_raw_dir}/
  full.md
  content_list_v2.json
  layout.json
  images/
  ...
```

约束:

- 预处理脚本不修改 MinerU 原始目录。
- 最低有效输入是 `full.md`（用于识别有效目录）。

### 3.2 输出（可重建）

```text
LiteratureClean/{paper_id}/
  metadata.json
  full_clean.md
  document_tree.json
  paragraph_index.json
  evidence_links.json
  image_manifest.json
  table_manifest.json
  quality_report.json
  PROCESSING_RECORD.md
  figures/
    FIGxxx/
      caption.md
      image_001.*
  tables/
    TABxxx/
      table.md
      caption.md
      image_001.*
  sections/
    Sxx_.../
      subheading_index.json
      paragraphs.md
      paragraphs/
        P001.md
        P002.md
        ...
```

---

## 4. 生效的宏章节模型

当前宏章节目录 ID 采用稳定历史 slug，显示标题可迭代优化。

已生效的章节 ID:

- `S00_front_matter`
- `S01_abstract`
- `S02_introduction`
- `S03_methods`
- `S04_results`
- `S05_mechanism`
- `S06_conclusion`
- `S07_supplementary`

当前显示标题（示例）:

- `S04_results` -> `Result`
- `S05_mechanism` -> `Mechanism`

说明:

- 目录只为非空章节创建，不强制补齐所有 S00-S07。
- 下游必须以 `document_tree.json` 为准，不应假设每篇都有完整章节集合。

### 4.1 关键词评分方法（strong/normal/preview/negative/position）

本项目当前的宏章节归并采用“标题优先 + 正文预览补充”的打分策略，核心逻辑在 `clean_single_mineru_paper.py` 的 `_build_macro_section_score_breakdown()`。

判定规则如下:

1. `strong`（默认 +5）
  - 条件: 章节关键词命中原始标题，且该关键词属于 `domain_dictionary.strong_keywords`。
  - 典型场景: 标题包含 `mechanism`、`reverse current`、`stability`、`overpotential` 等领域强特征词。

2. `normal`（默认 +2）
  - 条件: 章节关键词命中原始标题，但该词不在 `strong_keywords` 列表中。
  - 典型场景: 标题包含 `introduction`、`method`、`discussion` 这类通用词。

3. `preview`（默认 +1）
  - 条件: 关键词未命中标题，但命中该段正文预览文本（preview text）。
  - 作用: 让“标题不标准但正文内容明显”的段落仍能得到弱证据归类。

4. `position`（默认 +1）
  - 条件满足任一即加分:
    - 标题与章节标准标题完全相等；
    - 标题以前缀形式匹配章节标准标题；
    - 标题与该章节某个关键词完全相等。
  - 作用: 提供轻量“位置/格式”偏置，帮助标准标题稳定落到预期章节。

5. `negative`（默认 -4）
  - 当前状态: 配置项已存在并可读入，但当前 `_build_macro_section_score_breakdown()` 尚未使用该项做实际扣分。
  - 结论: 目前有效评分项是 `strong/normal/preview/position`，`negative` 处于“预留未启用”。

补充说明:

- 最终是否采用 top1 打分结果，还受 `uncertain` 门槛控制:
  - `min_top_score`（默认 4）
  - `min_score_gap`（默认 2）
- 若 top1 分数过低或与第二名差距不足，则回退到规则分类（`uncertain_fallback`）。

### 4.2 如何判断“关键词是否够用”

建议按以下口径判断，而不是只看单条命中:

1. 看 `quality_report.json` 中 `needs_manual_review` 是否持续偏高。
2. 看 `subheading_index.json` 中 `is_uncertain=true` 比例是否超过可接受阈值（例如 >10%）。
3. 抽查 `score_breakdown`:
  - 若大量条目只靠 `preview` 得分，说明标题关键词覆盖不足；
  - 若大量条目 top1 与 second 分差很小，说明关键词区分度不够；
  - 若误把机制段落分到结果段，可补充 S05 专属词（如腐蚀路径、价态变化、原位表征术语）。
4. 回归后比较同一批论文的三项指标趋势:
  - `uncertain` 数量
  - 人工复核数量
  - 章节误分样本数

实操建议:

- 优先补“高区分度词”，少补泛词。
- 强相关领域词放入 `domain_dictionary.strong_keywords`，让其命中标题时直接按 `strong` 计分。
- 每次改词后必须跑一轮 batch + verify，再看报告趋势，不要只凭单篇观感判断。

---

## 5. 关键字段与索引

### 5.1 段落层核心字段

在 `paragraph_index.json` 与 `sections/*/paragraphs/Pxxx.md` 中应能追踪:

- `paper_id`
- `section_id` / `section_title`
- `macro_section_id` / `macro_section_title`
- `original_heading`
- `paragraph_id`
- `evidence_id`
- `evidence_short_id`
- `linked_figures`
- `linked_tables`

### 5.2 subheading 归并解释字段

在 `sections/*/subheading_index.json` 中应包含:

- `original_heading`
- `assigned_section_id`
- `assigned_section_title`
- `assigned_by`
- `score_breakdown`
- `is_uncertain`
- `uncertain_reasons`

### 5.3 evidence 命名规则

稳定主键:

- Paragraph: `EV-{paper_short}-Sxx-Pxxx`
- Figure: `EV-{paper_short}-FIGxxx`
- Table: `EV-{paper_short}-TABxxx`

短别名:

- `E-{paper_short}-{nnn}`

---

## 6. 当前主脚本与职责

### 6.1 `clean_single_mineru_paper.py`

单篇预处理主引擎，负责:

1. 读取 MinerU 输入。
2. 清洗文本为 `full_clean.md`。
3. 解析 figure/table。
4. 构建 macro section + subheading + paragraph。
5. 落盘 sections 与全部根索引。
6. 写出 `quality_report.json` 与 `PROCESSING_RECORD.md`。

### 6.2 `batch_clean_mineru.py`

批量入口，负责:

1. 扫描 MinerU 输出目录。
2. 按 paper_id 去重。
3. 调用单篇主引擎。
4. 写 `batch_run_log.json`。
5. 处理完成后自动刷新回归报告。

### 6.3 `watch_mineru.py`

监听入口，负责:

1. 轮询新 MinerU 目录。
2. 调用批处理同源的 `process_one_paper()`。
3. 写 `watch_log.json` 与 `batch_run_log.json`。
4. 每次处理后自动刷新回归报告。

### 6.4 `verify_new_structure.py`

结构验收脚本，负责:

- 检查必需根文件。
- 检查 sections / subheading_index / paragraphs 目录。
- 检查 evidence 与 content_path 可回溯性。
- 检查 `quality_report.json` 的 `uncertain_items` 字段。
- 检查旧结构残留（`memory_cards`、`.abstract.md`、`.overview.md`、`heading_index.md`、`headings/`）。

### 6.5 `generate_preprocessing_regression_report.py`

回归总报告生成器，负责:

- 汇总每篇文献统计指标。
- 汇总失败原因。
- 汇总需要人工复核列表。
- 汇总旧结构残留检查。
- 输出 `preprocessing_regression_report.md`。

---

## 7. 标准执行方式

### 7.1 单篇重建

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
.\.venv\Scripts\python.exe LiteratureClean\batch_clean_mineru.py --overwrite --paper "10,000-h-stable"
```

### 7.2 全量重建

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
.\.venv\Scripts\python.exe LiteratureClean\batch_clean_mineru.py --overwrite
```

### 7.3 结构验证

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
.\.venv\Scripts\python.exe LiteratureClean\verify_new_structure.py
```

### 7.4 监听新目录

```powershell
cd D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker
.\.venv\Scripts\python.exe LiteratureClean\watch_mineru.py
```

或仅扫描一次:

```powershell
.\.venv\Scripts\python.exe LiteratureClean\watch_mineru.py --once
```

---

## 8. 自动更新机制（已实现）

当前回归报告实时更新规则:

- 批处理完成后自动更新:
  - `LiteratureClean/preprocessing_regression_report.md`
- 监听模式每处理一篇后自动更新:
  - `LiteratureClean/preprocessing_regression_report.md`

报告覆盖内容:

1. 总文献数
2. 成功处理数
3. 失败处理数
4. 每篇 paper_id
5. 每篇 macro section 数
6. 每篇 subheading group 数
7. 每篇 paragraph 数
8. 每篇 figure 数
9. 每篇 table 数
10. 每篇 evidence 数
11. 每篇 needs_manual_review 数
12. 失败原因
13. 需要人工复核列表
14. 是否仍有 `memory_cards`
15. 是否存在空 abstract/overview 或旧结构残留

---

## 9. 验收标准

每次回归至少满足以下条件:

1. `verify_new_structure.py` 输出 `errors=0`。
2. 无 `memory_cards/`、`.abstract.md`、`.overview.md`、`heading_index.md`、`headings/` 残留。
3. 每篇至少存在:
   - `metadata.json`
   - `full_clean.md`
   - `document_tree.json`
   - `paragraph_index.json`
   - `evidence_links.json`
   - `image_manifest.json`
   - `table_manifest.json`
   - `quality_report.json`
   - `PROCESSING_RECORD.md`
4. `sections/*` 下存在 `subheading_index.json`、`paragraphs.md` 与 `paragraphs/Pxxx.md`。
5. 回归报告自动刷新且字段齐全。

---

## 10. 常见问题与定位

### 10.1 “No valid MinerU directories found”

可能原因:

- `--mineru-output` 路径错误。
- 目录内缺少 `full.md`。

定位:

- 先用 `batch_clean_mineru.py --list` 看扫描结果。

### 10.2 paper_id 重复导致跳过

现象:

- 批处理日志出现 duplicate skip。

说明:

- 属于按 paper_id 去重的设计行为，不是错误。

### 10.3 报告统计与直觉不一致

说明:

- 成功/失败以当前有效文献目录与结构验收口径为准。
- 历史 run_log 条目可能包含旧轮次信息，必要时可清理后再重跑。

---

## 11. 非目标（本阶段不做）

以下不属于本文档约束的“最终预处理阶段”:

1. 外部知识库导入与检索配置。
2. embedding 建库与语义检索效果调优。
3. 前端 UI 展示与交互逻辑。
4. 问答链路、Agent 编排、提示词策略。

以上能力应由后续阶段文档单独管理，不应回灌到本预处理规范。

---

## 12. 最终状态摘要

截至当前版本，预处理链路已稳定在以下状态:

- 主结构统一为 sections 模型。
- 旧 memory_cards 路径已从主输出移除。
- 批量与监听入口统一调用单篇主引擎。
- 回归报告可在预处理后实时更新。
- 全量结构验证可作为固定验收门禁。

本文档即为当前最终预处理指导文档。

# MinerU → LiteratureClean 预处理进展报告

更新时间：2026-05-28

## 1. 当前目标

当前阶段的目标是：仅完成 MinerU 解析结果到新版 LiteratureClean 文献包的自动预处理，不进入 OpenViking、embedding、UI、问答或后续摘要生成阶段。

目标产物应满足以下要求：

1. 每篇文献生成一个独立的 `LiteratureClean/{paper_id}/` 目录。
2. 目录结构采用 `paper -> macro section -> subheading group -> paragraph`。
3. 保留原始小标题 `original_heading`，同时支持归并到标准化 macro section。
4. 生成统一索引文件，包括：
   - `document_tree.json`
   - `paragraph_index.json`
   - `evidence_links.json`
   - `image_manifest.json`
   - `table_manifest.json`
   - `quality_report.json`
5. section 目录下生成：
   - `subheading_index.json`
   - `paragraphs.md`
   - `paragraphs/Pxxx.md`
6. 不再生成旧版 `memory_cards/`、根目录 `.abstract.md/.overview.md`、`heading_index.md` 等旧结构。

## 2. 已完成工作

根据当前脚本、配置、样例产物目录和最近一次批量验证结果，以下工作已经完成：

### 2.1 已取消 memory_cards 输出

当前主构建链已经停用 `memory_cards` 生成。

- 在主构建逻辑中，`clean_single_mineru_paper.py` 的 `build_package()` 已明确注释掉：
  - `write_standard_memory_cards(...)`
  - `write_figure_cards(...)`
  - `write_table_memory_cards(...)`
- 当前样例输出目录中未发现以下旧产物：
  - `memory_cards/`
  - `.abstract.md`
  - `.overview.md`
  - `heading_index.md`

### 2.2 已改为 paper -> macro section -> subheading group -> paragraph 结构

当前新版结构已经落地。

- 根目录使用 paper 级目录。
- `sections/` 下按 macro section 存放内容。
- 每个 section 内使用 `subheading_index.json` 保留 subheading group。
- 每个段落落盘为 `paragraphs/Pxxx.md`。
- `document_tree.json` 当前记录的是论文到 macro section 再到 paragraph 的结构树。

### 2.3 已支持 macro section 归并

当前已经支持从原始 heading 向 macro section 的规则归并，并保留可解释的分配信息。

- 已有 `macro_section_rules.yaml`。
- `subheading_index.json` 中可见：
  - `original_heading`
  - `assigned_section_id`
  - `assigned_section_title`
  - `assigned_by`
  - `score_breakdown`
  - `is_uncertain`
  - `uncertain_reasons`
- `quality_report.json` 已汇总低置信或低分差的归并项。

### 2.4 已生成 subheading_index.json

已确认样例 paper 的 section 目录中存在 `subheading_index.json`，且内容包含：

- subheading 数量
- `original_heading`
- 归并目标 section
- 归并打分细节
- paragraph 映射路径
- linked figures / linked tables

### 2.5 已生成 paragraphs.md

已确认样例 paper 的每个非空 section 目录中存在 `paragraphs.md`。

### 2.6 已生成 paragraphs/Pxxx.md

已确认样例 paper 的 section 目录中存在 `paragraphs/P001.md` 等段落文件，并且单段文件中已包含：

- Paper ID
- Section / Section ID
- Macro Section ID / Title
- Original Heading
- Paragraph ID
- Evidence ID / Evidence Short ID
- Linked Figures / Linked Tables
- Keywords
- Source 路径

### 2.7 已生成根索引文件

当前样例 paper 根目录已存在以下文件：

- `document_tree.json`
- `paragraph_index.json`
- `evidence_links.json`
- `image_manifest.json`
- `table_manifest.json`
- `quality_report.json`
- `metadata.json`
- `full_clean.md`
- `PROCESSING_RECORD.md`

### 2.8 已保留 original_heading

`original_heading` 当前已明确保留在以下位置：

- `subheading_index.json`
- `paragraph_index.json`
- `paragraphs/Pxxx.md`

这说明新版结构没有丢弃论文原始标题层，而是在“归并到 macro section”的同时保留了原始语义锚点。

### 2.9 当前输出目录中未发现空文件、旧版结构产物

对当前 LiteratureClean 论文输出目录的递归检查结果显示：

- 未发现零字节空文件。
- 未发现根目录 `.abstract.md/.overview.md`。
- 未发现 `memory_cards/`。
- 未发现 `heading_index.md`。

说明当前主产物目录已经基本摆脱旧结构残留。

## 3. 修改过的主要文件

本次预处理链路相关、且当前仍作为主依据的主要文件包括：

1. `clean_single_mineru_paper.py`
   - 当前单篇预处理主引擎。
   - 负责从 MinerU 输出构建新版 LiteratureClean。
   - 负责 section 归并、段落落盘、索引生成、质量报告生成。

2. `macro_section_rules.yaml`
   - macro section 规则配置文件。
   - 决定标题匹配、关键词打分、uncertain 策略。

3. `batch_clean_mineru.py`
   - 当前批量入口。
   - 现在 `process_one_paper()` 已直接调用 `clean_single_mineru_paper.build_package()`。

4. `watch_mineru.py`
   - 当前轮询监听入口。
   - 通过 `batch_clean_mineru.process_one_paper()` 调用相同主链。

5. `verify_new_structure.py`
   - 当前新版结构校验脚本。
   - 会检查根索引、section 目录、paragraph 文件、legacy artifact 是否存在等。

6. `LITERATURE_CLEANING_GUIDE.md`
   - 当前人工规范文档。
   - 已与新版 sections 结构基本对齐。

## 4. 当前 LiteratureClean 输出目录结构

当前新版输出结构可概括为：

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

当前 section 命名已经是泛化后的版本，例如：

- `S04_results` 的显示标题为 `Results`
- `S05_discussion` 的显示标题为 `Discussion and Analysis`

注意：section 目录名保留了历史 ID slug，但显示标题已更新为更通用的名称。

## 5. 自动预处理链路是否已打通

结论：当前 MinerU → LiteratureClean 新版预处理链路已经打通。

依据如下：

1. 单篇主脚本 `clean_single_mineru_paper.py` 已直接输出新版结构。
2. 批量脚本 `batch_clean_mineru.py` 的 `process_one_paper()` 当前统一走 `build_package()`。
3. 监听脚本 `watch_mineru.py` 当前通过 batch 入口复用同一主链。
4. 最近一次批量运行结果显示：
   - Processed: 11
   - Failed: 0
5. 最近一次结构验证结果显示：
   - papers = 11
   - errors = 0
   - warnings = 0

因此，从自动化链路角度看，当前已经可以从 MinerU 解析结果自动生成新版 LiteratureClean。

## 6. 单篇测试结果

### 6.1 代表性样例：2025 Sha 论文

样例目录：

- `2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c`

核查结果：

- 根目录索引文件齐全。
- `sections/` 存在，且包含：
  - `S00_front_matter`
  - `S01_abstract`
  - `S03_methods`
  - `S04_results`
  - `S05_discussion`
  - `S07_supplementary`
- `S04_results/` 下存在：
  - `subheading_index.json`
  - `paragraphs.md`
  - `paragraphs/P001.md` 至 `P007.md`
- `document_tree.json` 显示：
  - section_count = 6
  - paragraph_count = 63
- `quality_report.json` 已包含：
  - generated_files
  - section_count / paragraph_count / figure_count / table_count
  - uncertain_items

### 6.2 代表性样例：2024 Jung 论文

样例目录：

- `2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9`

核查结果：

- 成功生成 5 个 section。
- `S04` 显示标题为 `Results`。
- `S05` 显示标题为 `Discussion and Analysis`。
- 说明新的 section 命名与结构不只适用于 Sha 论文，也已用于其他论文样例。

## 7. 是否还能从 MinerU 解析结果自动生成新版 LiteratureClean

结论：可以。

当前证据链如下：

1. `clean_single_mineru_paper.py` 中 `build_package()` 已明确输出新版 sections 结构与根索引。
2. memory_cards 输出在主链中已注释禁用。
3. `batch_clean_mineru.py` 现行处理入口已统一指向新版主脚本。
4. `watch_mineru.py` 复用 batch 入口。
5. 当前样例产物目录与 `verify_new_structure.py` 的检查项一致。
6. 最近一次批量重建与结构校验均通过。

因此，当前已经不是“目标结构设计中”，而是“可以自动产出新版 LiteratureClean 的已落地状态”。

## 8. 发现的问题和风险

虽然主链已经打通，但仍存在一些需要记录的风险和历史残留。

### 8.1 旧 memory_cards 辅助函数仍保留在代码中

在 `clean_single_mineru_paper.py` 中，以下旧函数仍保留：

- `write_root_docs()`
- `write_memory_card()`
- `write_standard_memory_cards()`
- `write_figure_cards()`
- `write_table_memory_cards()`

当前这些函数已不在主构建链调用路径中，但仍然留在文件内。风险是：

- 后续维护者可能误以为这些逻辑仍是有效输出的一部分；
- 某些辅助脚本如果误走旧路径，可能重新引入 `memory_cards/`；
- 文档和代码阅读成本会上升。

### 8.2 batch_clean_mineru.py 中仍保留旧 generic 辅助逻辑

虽然当前 `process_one_paper()` 已统一走新版主链，但 `batch_clean_mineru.py` 文件内部仍存在大量旧 memory_cards / generic 说明和函数残留。

这说明：

- 当前“执行路径”已经统一；
- 但“文件内容”仍未彻底清理；
- 后续仍建议做一次代码层面的旧逻辑剥离或归档。

### 8.3 历史 run log 仍保留旧 pipeline 记录

`batch_run_log.json` 中仍可见旧记录，例如：

- `pipeline = "generic (batch_clean_mineru)"`
- 某些旧条目使用 `unknown_year_*` 的历史 paper_id

这不影响当前主产物，但会带来两个问题：

1. 历史记录中混杂旧版与新版状态，容易误判当前进展；
2. 旧 paper_id 与新版 paper_id 并存时，可能影响人工审核和统计。

### 8.4 仓库内仍有旧文档/旧辅助脚本引用 memory_cards

例如：

- `_rebuild_guide.py`
- `search_hydrate.py`
- 部分非当前主链说明文档

这些内容不代表当前主输出仍在生成 memory_cards，但代表仓库层面的“旧概念清理”尚未彻底完成。

### 8.5 section 目录按非空生成，不会强制补空 section

当前结构是“只有有内容的 macro section 才会生成目录”。

这不是 bug，而是当前设计选择。但需要注意：

- 如果后续某些下游程序假定 `S00-S07` 必定齐全，则会出错；
- 下游读取逻辑应基于 `document_tree.json` 和真实存在的 `sections/*`，而不是硬编码 section 数量。

### 8.6 仍需人工关注 uncertain 归并项

`quality_report.json` 中已记录 `uncertain_items`，说明当前归并虽然可用，但不是所有标题都高置信。

这意味着：

- 当前链路可自动跑通；
- 但个别 heading 的 section 归并仍建议人工抽查；
- 特别是方法-结果-机理边界模糊的小标题，需要持续优化规则。

## 9. 是否建议进行全量回归验证

结论：建议，而且当前已经做过一轮通过的全量回归验证。

当前状态下的判断是：

1. 由于 section 命名、归并规则、front matter 识别、uncertain 策略都已经改过多轮，因此每次规则调整后都应进行全量回归验证。
2. 当前最近一次全量回归结果是通过的：
   - 批量重建 11 篇文献成功
   - `verify_new_structure.py` 检查 11 篇文献无错误、无警告

因此，现阶段不是“是否要第一次做全量回归”的问题，而是：

- 当前版本已经具备“规则改动后立即全量回归”的基础；
- 后续每次再改 section 规则、front matter 规则、表格/图片关联规则时，都应重复执行。

## 10. 下一步建议

### 10.1 建议优先做的事

1. 清理主脚本和 batch 脚本中未使用的旧 `memory_cards` 函数与说明。
2. 清理或归档仍引用旧结构的辅助脚本和文档，避免误导后续开发。
3. 统一整理 `batch_run_log.json`，移除或标记旧 generic/unknown_year 历史记录。
4. 保留 `verify_new_structure.py` 作为每次规则修改后的固定回归入口。

### 10.2 若继续推进预处理阶段，建议关注的重点

1. 继续优化 front matter 识别，减少作者信息误落入 abstract 的风险。
2. 继续优化 macro section 归并规则，减少 `uncertain_items`。
3. 针对表格较多、图注较复杂的论文增加专项抽查样例。
4. 如果未来需要给下游使用，建议明确“以 `document_tree.json` 为唯一结构真相源”。

## 11. 当前结论

截至本次检查，MinerU → LiteratureClean 预处理工作的整体状态可以概括为：

- 主链已经打通。
- 新版 sections 结构已经实际产出。
- `memory_cards` 已从主输出中移除。
- `subheading_index.json`、`paragraphs.md`、`paragraphs/Pxxx.md`、根索引文件均已生成。
- `original_heading` 已保留。
- 当前样例产物未发现空文件和旧结构产物。
- 最近一次批量重建与结构验证已经通过。

但同时也需要明确：

- 代码仓库内部仍有旧 memory_cards 相关函数、辅助脚本和说明残留；
- 历史日志中仍保留旧 generic pipeline 记录；
- 规则层面仍存在少量 uncertain heading 归并项，需要持续人工抽查和规则微调。

整体判断：当前已经可以把“MinerU 解析结果自动生成新版 LiteratureClean”视为已完成并可用的预处理阶段成果；剩余工作主要是历史残留清理、规则稳健性提升和持续回归验证。
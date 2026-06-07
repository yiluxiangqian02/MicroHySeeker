# OpenViking 准确度优先改造：完整执行计划（2026-06-02）

> 本文档是本轮所有确认决策、评分方案、索引架构、检索流程与 Todo 清单的单一执行参考文档。
> 后续按照本文档逐项执行，不再需要查阅多份散落文档。

---

## 目录

1. [当前系统状态](#1-当前系统状态)
2. [关键路径与文件地图](#2-关键路径与文件地图)
3. [评分体系（已落地，仅参考）](#3-评分体系已落地仅参考)
4. [索引架构（已确认）](#4-索引架构已确认)
5. [检索流程（已确认）](#5-检索流程已确认)
6. [段落 Chunk 口径（已确认）](#6-段落-chunk-口径已确认)
7. [答案展示模板（已确认）](#7-答案展示模板已确认)
8. [待执行 Todo 清单（H1-H6）](#8-待执行-todo-清单h1-h6)
9. [执行顺序与依赖关系](#9-执行顺序与依赖关系)
10. [验收标准汇总](#10-验收标准汇总)
11. [常用命令速查](#11-常用命令速查)
12. [当前已完成里程碑（仅记录，不执行）](#12-当前已完成里程碑仅记录不执行)

---

## 1. 当前系统状态

### 1.1 已完成项（✅ 不需再执行）

| 编号     | 事项                         | 结果                                                                      | 完成日期   |
| -------- | ---------------------------- | ------------------------------------------------------------------------- | ---------- |
| G2       | 全量 reindex 导入            | 11/11 成功，included_files=422，error=0                                   | 2026-06-02 |
| E1       | ov_index 结构完整性校验      | papers=11, ok=11, issue=0                                                 | 2026-06-02 |
| E2       | overview 质量校验            | pass=11/11, avg_score=92.97                                               | 2026-06-02 |
| E3       | 语义冲突分归一化改造         | high=2, medium=3, low=6, manual_review=5（原11→5）                       | 2026-06-02 |
| E4       | 回退与人工审核决策           | manual_review=5（ok=6, needs_fallback=5）                                 | 2026-06-02 |
| 资源清理 | 110 个 stub 占位文件删除     | before=110, after=0                                                       | 2026-06-02 |
| venv     | Python 3.11 专用环境创建     | `.venv_ov311` 含 pyagfs + sentence-transformers + tokenizers==0.23.0rc0 | 2026-06-02 |
| **H1**   | **修复 section 导入同名折叠** | **已修复，section 文件从 2 个 → N×2 个**                                  | **2026-06-03** |
| **H2**   | **段落证据索引层 (paragraph chunk)** | **已实现，11 篇论文生成 604 chunk**                            | **2026-06-03** |
| **H7**   | **Section 文件夹组织** | **已实现，section 子目录含 abstract + overview + chunk**                  | **2026-06-03** |
| **H8**   | **空白 auto-generated 覆写** | **已实现，populate_directory_summaries() 用预处理内容替换空白摘要**       | **2026-06-03** |
| **H9**   | **Chunk 命名 section 前缀 + SemanticProcessor skip** | **已实现，chunk 文件名为 section_dir 前缀；段落节点不生成 abstract/overview** | **2026-06-04** |
| **H10**  | **旧 chunk 清理 + AGFS 全量清理** | **已实现，reindex 前 rm 整个 paper URI**                                  | **2026-06-04** |

### 1.2 待执行项（❌ 本文档核心目标）

| 编号 | 事项                                         | 优先级               | 状态 |
| ---- | -------------------------------------------- | -------------------- | ---- |
| ~~H1~~ | ~~修复 section 导入"同名折叠"问题~~      | ~~P0~~               | ✅ |
| ~~H2~~ | ~~引入段落证据索引层（paragraph chunk）~~ | ~~P0~~               | ✅（将被 P1 替换为段落 .md 直入） |
| H3   | 图表/实验结构化证据索引层（条件触发）        | P2（按触发条件决定） | ⏸ 暂缓 |
| P1   | **流水线重构**：章级拆分 + 删除 S00-S07 + 段落 .md 直入 | P0                   | 🔧 方案已确认 |
| P2   | **三级检索 Stage**：L0 混合向量 → L1 树检索 → LLM Judge | P0                   | 🔧 方案已确认 |
| H5   | 回答展示模板固化（证据强制展示）             | P1                   | 🔧 融入 P2 |
| H6   | G3 回归验证（准确度口径）                    | P1                   | ⏳ 依赖 P1+P2 |

### 1.3 已识别但暂不处理的已知问题

- F1-F5（HTML 问答验证页）：待 H1/H2 完成后再做
- G3（回归验证）：即 H6，H4/H5 完成后触发
- E2 侧 `relevance` 信号缺失：集中在 section_overview，影响较小，后续轻量修复

---

## 2. 关键路径与文件地图

### 2.1 Python 环境

```text
主环境（OpenViking 专用）:
  D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/.venv_ov311/Scripts/python.exe

注意: OpenViking engine.pyd 绑定 python311.dll，必须使用此专用 venv，
     不可使用 MicroHySeeker/.venv 或其他 3.10/3.12 环境。
```

### 2.2 主要脚本

```text
主导入脚本（含 E1/E2/E3/E4 + H1/H2 全部逻辑）:
  AutoHySeeker/LiteratureClean/import_to_openviking.py

关键函数:
  _score_section_overview_signals()          # E2 信号分，中等扩词三组（~L293）
  validate_semantic_conflict_for_paper()     # E3 新方案，raw+normalized+penalty（~L510）
  build_semantic_conflict_report()           # E3 报告生成（~L624）
  _section_prompt()                          # 三段软模板 Claim/Evidence/Relevance（~L916）
  build_paragraph_chunks()                   # H2 段落 chunk 生成（~L1612）
  build_main_index_export_dir()              # H1/H2 拍平命名 + 三层导出（~L1717）

四阶段问答管线（H4，待实现）:
  AutoHySeeker/LiteratureClean/qa_pipeline.py    # LiteratureQA 类 + CLI 入口
```

### 2.3 数据路径

```text
LiteratureClean 源数据（唯一真相源）:
  AutoHySeeker/LiteratureClean/{paper_id}/ov_index/

OpenViking 运行数据（导入目标，不作为原始生成位置）:
  AutoHySeeker/data/openviking/viking/default/resources/literature/

OpenViking 配置文件:
  AutoHySeeker/OpenViking/.local_dev/ov.conf

OpenViking 服务日志:
  AutoHySeeker/logs/
```

### 2.4 ov_index 目录结构（每篇论文）

```text
LiteratureClean/{paper_id}/ov_index/
  paper.abstract.md              # 论文层摘要（已生成）
  paper.overview.md              # 论文层综述（已生成）
  generation_status.json         # 生成状态元数据（fresh/stale/missing）
  sections/
    S00_front_matter/
      abstract.md                # Section 摘要
      overview.md                # Section 综述
    S01_abstract/
      abstract.md
      overview.md
    S02_introduction/
      abstract.md
      overview.md
    ...（按实际 section 数量）
```

### 2.5 generation_status.json 关键字段

```json
{
  "generated_at": "2026-06-02T...",
  "based_on_preprocess_version": "...",
  "source_checksum": "sha256:...",
  "llm_model": "...",
  "status": "fresh"  // fresh | stale | missing
}
```

### 2.6 当前 11 篇论文 paper_id（全量）

```text
2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9
2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201
2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb
2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e
2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9
2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6
2025_peng_strategies_and_countermeasures_against_reverse_current_f_803838
2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c
2025_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7
2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e
2026_unknown_2026_2d8d75
```

---

## 3. 评分体系（已落地，仅参考）

> 以下为当前已运行落地的评分逻辑，无需修改，作为下阶段 H6 验收基准。

### 3.1 E1：结构完整性（Validation）

评估对象：每篇论文的 `ov_index` 产物和状态链。

检查项：

- 必需文件是否存在（`paper.abstract.md` / `paper.overview.md` / `sections/*`）
- 是否为占位内容或空内容
- `sections/` 目录是否与 `sections_by_heading/` 对齐
- `generation_status.json` 是否存在且有效

判定：`issue_count = 0` → ok；`issue_count > 0` → issue

**当前结果：papers=11, ok=11, issue=0**

---

### 3.2 E2：overview 质量分

#### 3.2.1 长度分（Length Score）

| 对象             | 目标区间   |
| ---------------- | ---------- |
| paper_overview   | 180-320 词 |
| section_overview | 120-220 词 |

规则：区间内=100；区间外按 gap 线性扣分（最多扣70）；最终 [0,100]

#### 3.2.2 结构分（仅 paper_overview）

命中关键词：`background`、`method`、`results`、`practical implications`

公式：`structure_score = round((命中项数 / 4) * 100)`

#### 3.2.3 信号分（仅 section_overview）

三组信号（中等扩展，中英混合）：

- **claim 组**：claim, conclusion, demonstrate, show, reveal, argue, propose, suggest, find, indicate（及中文对应）
- **evidence 组**：experiment, measurement, data, result, test, analysis, observation, study, trial, measure（及中文对应）
- **relevance 组**：relevant, impact, implication, significance, application, influence, relation, connection, effect（及中文对应）

公式：`signal_score = round((命中组数 / 3) * 100)`

避免过宽词（如 `for`、`show` 等单独无上下文词）

#### 3.2.4 综合分与等级

```
paper_overview_score = length_score * 0.6 + structure_score * 0.4
section_overview_score = length_score * 0.7 + signal_score * 0.3
paper_avg_score = 各 item 分数算术平均
```

等级：`pass >= 85`；`warn >= 70`；`fail < 70`

生成侧约束（软模板）：

- 固定结构：`## Claim` / `## Evidence` / `## Relevance`
- 每段 1-2 句，必须锚定原文，不新增原文没有的断言

**当前结果：pass=11/11, avg_score=92.97**

---

### 3.3 E3：语义冲突分（已落地新方案）

#### 3.3.1 语义本体分（raw_conflict）

```
h = high_tag_conflicts 数量
m = medium_tag_conflicts 数量
l = low_tag_conflicts 数量

raw_conflict = h * 10 + m * 2 + l * 0.5
```

#### 3.3.2 归一化主分

```
s = section_count = max(1, section_targets_count)
normalized_conflict = min(100, raw_conflict / s * 2.0)
```

#### 3.3.3 流程惩罚分（单列，不并入 raw_conflict）

| 条件                         | 惩罚分 |
| ---------------------------- | ------ |
| generation_status != fresh   | +10    |
| evidence_links.json 缺失     | +5     |
| tag_conflicts.json 缺失/无效 | +8     |
| tag_conflicts.items 缺失     | +8     |
| paper abstract/overview 缺失 | +10    |
| section targets 缺失         | +10    |

#### 3.3.4 最终分与等级

```
conflict_score = min(100, normalized_conflict + process_penalty)
```

等级：`high >= 40`；`medium >= 20 且 < 40`；`low <= 19`

**当前结果：high=2, medium=3, low=6, avg=21.52，manual_review=5**

---

### 3.4 E4：回退动作与人工审核

触发规则：

- E3 为 high 或 medium → `manual_review_only`
- E1 issue 或 E2 warn/fail 也会触发人工介入路径

**当前结果：ok=6, needs_fallback=5, manual_review=5**

需人工审核的 5 篇：

- `2023_a_effects_...` (E3=high)
- `2023_uchino_dependence_...` (E3=medium)
- `2024_jung_reverse_current_...` (E3=high)
- `2025_center_reverse_current_...` (E3=medium)
- `2025_peng_strategies_...` (E3=medium)

---

## 4. 索引架构（已实现 H1/H2）

### 4.1 四层索引设计

本阶段从"摘要最小集"升级为"三层可追溯索引"（图表层条件触发）：

```
Layer 1: 论文层（粗召回）
  ├── paper.abstract.md       → paper-level abstract
  └── paper.overview.md       → paper-level overview

Layer 2: 小节层（主题定位）
  ├── {section_dir}.abstract.md  → 每个 section 的 abstract
  └── {section_dir}.overview.md  → 每个 section 的 overview

Layer 3: 段落证据层（精召回，H2 已实现）
  └── {section_dir}.{paragraph_id}.chunk.md  → 原文段落 chunk

Layer 4: 图表/实验结构化证据层（条件触发，H3 暂缓）
  └── figure/table structured evidence（按触发条件决定是否引入）
```

### 4.1.1 关键设计决策：拍平命名 + 后缀体系

**问题**：H1 修复前，section 文件保留了目录结构 `sections/{id}/abstract.md`，OpenViking 的 MarkdownParser 用文件 stem 作为文档名，所有 section 的 `abstract` stem 碰撞导致同名折叠。

**决策**：所有索引文件拍平到导出根目录，用**文件名后缀**区分层级。每条文件名全局唯一 → stem 唯一 → 不再折叠。

**后缀体系统一管理**（`MAIN_INDEX_SUFFIXES` + `EXCLUDE_FROM_INDEX`）：

| 后缀 | 层级 | 用途 |
|------|------|------|
| `.abstract.md` | Paper + Section | 粗召回：论文/小节摘要 |
| `.overview.md` | Paper + Section | 主题定位：论文/小节综述 |
| `.chunk.md` | Paragraph | 精召回：原文段落证据 |

### 4.2 白名单规则（进入 OpenViking 主索引）

进入主索引（可被向量检索）：

1. `paper-level .abstract.md`
2. `paper-level .overview.md`
3. `section-level .abstract.md`（**需修复 H1 折叠问题后才生效**）
4. `section-level .overview.md`（**需修复 H1 折叠问题后才生效**）
5. **段落原文 chunk**（H2 实施后新增）
6. 图表/实验结构化证据（H3 触发后新增）

不进入主索引（仅回填/追溯）：

- `metadata.json`、`full_clean.md`、`document_tree.json`
- `original_structure_index.json`、`paragraph_index.json`
- `evidence_links.json`、`image_manifest.json`、`table_manifest.json`
- `quality_report.json`、`tag_conflicts.json`

### 4.3 分层存储约束（强约束，不可违反）

```
LiteratureClean 层（唯一真相源）:
  → 负责预处理、LLM 生成、状态校验
  → 所有 abstract/overview/paragraph 先在此层生成与落盘
  → 禁止在 OpenViking 运行目录直接生成并替代此层源文件

OpenViking 层（运行态）:
  → 负责导入、向量索引、检索服务
  → 内部可产生运行态缓存/索引文件（与源文件分离）

跨层方向: LiteratureClean 产物 → OpenViking 导入（单向）
```

---

## 5. 检索流程（已更新 2026-06-07）

### 5.1 三级检索 Stage 架构

> **已替换旧四阶段方案。** 新方案利用 L0/L1 双层摘要体系，不再需要 Python 侧重排。

```
Stage ①: 全局向量检索 L0（混合粒度）
  检索对象: Paper L0 + Section L0（.abstract.md）混合向量库
  检索方式: client.find(query, target_uri="viking://resources/literature", limit=15)
  输出: 混合粒度命中列表（论文A、论文B.S03、论文C.S05...）

    ↓

Stage ②: 树检索 L1（收敛到章节级）
  检索对象: Stage ① 命中结果的 .overview.md
  逻辑: 命中论文级 → 通过 L1 导航到相关章节；命中章节级 → 直接确认
  Top-k: 5 个最相关章节

    ↓

Stage ③: LLM Judge（段落选择）
  输入: 命中章节 paragraphs/ 目录下所有 Pxxx.md 原文（编号 P001, P002...）
  逻辑: LLM 阅读全部段落文本，判断哪些与查询相关
  输出: 保留段落编号 + evidence_id + linked_figures + linked_tables

    ↓

Stage ③ 返回: 原文 + evidence_id + 关联图表路径
  ├── 禁止: 引用未入选证据
  ├── 禁止: 无出处总结（必须可追溯到 paragraph_id）
  └── 输出: 见第 7 节答案展示模板
```

### 5.2 日志可观测性要求

检索/推理日志必须可区分四个阶段：

- `[stage1]` 候选召回记录（paper_id, section_id, 召回数量）
- `[stage2]` 重排后候选记录（重排分、命中类型）
- `[stage2.5]` LLM 选段结果（paragraph_id 列表 + 选择理由）
- `[stage3]` 最终答案（仅引用 stage2.5 入选证据 ID）

---

## 6. 段落 Chunk 口径（H2 已实现）

### 6.1 实现方案

**数据来源**：`paragraph_index.json`（主注册表） + `sections_by_heading/{dir}/paragraphs/PRAW-*.md`（原文文本）

**section_dir 映射**：从 `content_path` 提取——`sections_by_heading/001-front-matter/paragraphs/...` → section_dir = `001-front-matter`（与 ov_index section 目录名一致）

**输出位置**：`ov_index/paragraph_chunks/{section_dir}.{paragraph_id}[-split].chunk.md`

### 6.2 长度规整规则（实际实现）

| 情况 | 处理方式 | 阈值 |
|------|---------|------|
| 过短（DOI/URL/作者信息） | **跳过**（无证据价值） | < 30 词 |
| 正常段落 | 直接使用，一个 chunk | 30–350 词 |
| 过长段落 | 按句边界拆分（`-a`, `-b`, `-c` 后缀），子 chunk 目标 150-200 词 | > 350 词 |

> **与原始设计差异**：短段落不合并而是跳过。分析实际数据后发现 <30 词段落均为 DOI/URL/作者行，合并没有意义。

### 6.3 实际元数据（YAML frontmatter）

```yaml
---
paper_id: "2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c"
section_id: "S05_discussion_mechanism"
paragraph_id: "S05-P001"
evidence_id: "EV-sha2025-333f5c-S05-P001"
chunk_index: 0
---
```

### 6.4 单篇示例（2025_sha）

| 指标 | 值 |
|------|-----|
| 总段落 | 63 |
| 跳过（<30词） | 16 |
| 直接使用（30-350词） | 42 |
| 拆分（>350词） | 5 → ~13 子 chunk |
| **预计 chunk 总数** | **~55** |
  "text": "原文段落文本..."
}
```

### 6.4 图表信息读取边界（当前阶段）

可稳定使用（不需要 VLM）：

- 图注（figure caption）
- 表注（table caption）
- 正文中的图表引用文字
- `image_manifest.json` / `table_manifest.json` 结构化链接字段

不作为当前主链路（VLM/OCR 仅后续增强）：

- 直接图像像素理解
- 表格数值的 OCR 提取

---

## 7. 答案展示模板（已确认）

### 7.1 输出结构（固定格式）

```markdown
## 结论

[1-2 句核心结论，必须有出处]

## 证据条目

| # | paper_id | section_id | paragraph_id | 命中分 | 原文片段 |
|---|----------|------------|--------------|--------|---------|
| 1 | 2024_jung_... | S03_experimental | P007 | 0.92 | "..." |
| 2 | 2025_center_... | S02_results | P003 | 0.87 | "..." |
| ... | | | | | |

## LLM 选段列表（Stage 2.5 输出）

- paragraph_id: P007（来自 2024_jung_...，S03_experimental）
  理由: 包含目标实验条件下的电流密度测量值
- paragraph_id: P003（来自 2025_center_...，S02_results）
  理由: 直接对比了 Ni-Ru 电极降解速率

## 不确定性说明

[如有冲突证据或数据缺口，在此列出。若无则写"无明显冲突证据"。]
```

### 7.2 实验设计问题附加展示

对于"实验参数/实验设计"类问题，需额外并列展示：

```markdown
## 可复用实验参数（跨论文汇总）

| 参数名 | 数值 | 单位 | 来源 paper_id | paragraph_id |
|--------|------|------|---------------|--------------|
| 电流密度 | 500 | mA/cm² | 2024_jung_... | P007 |
| 温度 | 60 | °C | 2025_sha_... | P012 |

## 冲突证据

[如不同论文同一参数有冲突，在此对比列出]
```

---

## 8. 待执行 Todo 清单

> **重要更新 (2026-06-07)**：流水线方案已重新设计，详见 [`09_PIPELINE_REDESIGN_ANALYSIS_2026-06-04.md`](09_PIPELINE_REDESIGN_ANALYSIS_2026-06-04.md)。
> 核心变更：章级拆分 + 删除 S00-S07 + 段落 .md 直入主索引 + 三级检索 Stage。

---

### P1. 流水线重构（章级拆分 + 删除 S00-S07 + 段落 .md 直入）

**status: 方案已确认，待实现 | priority: P0**

**改动 1：章级标题拆分**（`clean_single_mineru_paper.py`）
- `split_into_sections()` 改为只识别章级标题（`#` 或 Introduction/Methods/Results/Discussion/Conclusion 级别的 `##`）
- 不再细化到 1.1/1.1.1 等子标题
- `sections_by_heading/` 目录数从 20-30 降到 5-10

**改动 2：删除 S00-S07**（`clean_single_mineru_paper.py`）
- 删除 ~500 行宏分类逻辑
- 删除 `macro_section_rules.yaml`（380 行）
- `paragraph_id` 从 `S05-P001` → `H{order}-P{order}`；`section_id` 从 `S05_discussion_mechanism` → heading 目录名
- 删除 `tag_conflicts.json` 生成；`document_tree.json` 删除 `macro_tags`
- `paragraph_index.json` 字段从 25+ 减到 ~15

**改动 3：段落 .md 直入主索引**（`import_to_openviking.py`）
- 删除 `build_paragraph_chunks()`（125 行）
- 新增 `copy_paragraph_files()`：从 `paragraph_index.json` 读路径，复制段落 .md 到 `ov_index/sections/{dir}/`
- 段落文件命名：`{paragraph_id}.md`（如 `H03-P002.md`）
- `semantic_processor.py` skip 条件扩展：无子节点 + 仅 1 个 .md 文件 → 跳过

**影响范围**：`clean_single_mineru_paper.py`(-880 行) + `import_to_openviking.py`(-85 行) + `semantic_processor.py`(+5 行)

---

### P2. 三级检索 Stage（L0 → L1 → LLM Judge）

**status: 方案已确认，待实现 | priority: P0**

新建 `LiteratureClean/qa_pipeline.py`（独立模块，不改 OpenViking）。

| Stage | 检索对象 | 方式 | Top-k | 输出 |
|-------|---------|------|-------|------|
| ① L0 混合向量 | Paper L0 + Section L0（`.abstract.md`） | `client.find()` 语义向量 | 15 | 混合粒度命中列表 |
| ② L1 树检索 | 命中结果的 `.overview.md` | `client.overview()` 导航 | 5 | 最相关章节 URI |
| ③ LLM Judge | 章节下 `paragraphs/*.md` 原文 | LLM 逐段判断相关性 | — | 段落编号列表 + evidence_id + 图表 |

```
query → ① client.find(limit=15) → ② overview 导航 → ③ LLM Judge
                                                              ↓
                                          原文 + evidence_id + linked_figures
```

---

### H3. 图表/实验结构化证据索引层（条件触发）

**status: 暂缓 | priority: P2**

---

### H6. G3 回归验证（准确度口径）

**status: 依赖 P1+P2 | priority: P1**

前置条件：P1 + P2 全部完成。

---

## 9. 执行顺序与依赖关系

```
P1 流水线重构（P0）
  ├── Step 1: 章级拆分 + 删除 S00-S07（clean_single_mineru_paper.py）
  ├── Step 2: 段落 .md 直入索引（import_to_openviking.py）
  ├── Step 3: SemanticProcessor skip 扩展（semantic_processor.py）
  ├── Step 4: 重新生成所有论文 paragraph_index.json + ov_index
  └── Step 5: --reindex 全量重导入

        ↓ P1 完成后

P2 三级检索 Stage（P0）
  └── Step 6: 新建 qa_pipeline.py

        ↓ P2 完成后

H6 G3 回归验证（P1）
  └── 端到端准确度测试

H6（P1）
  → G3 回归验证
  → 依赖 H1 + H2 + H4 + H5

H3（P2，条件触发）
  → 暂缓，按触发条件决定
```
```

**推荐执行顺序：H1 → H2 → H4 → H5 → H6（H3 按触发条件决定）**

---

## 10. 验收标准汇总

| Todo | 核心验收条件                                                           |
| ---- | ---------------------------------------------------------------------- |
| H1   | 单篇导入后 section 文件数量与 `ov_index/sections` 一致，无同名折叠   |
| H2   | 检索可返回 paragraph_id + 原文片段 + paper/section/paragraph 元数据    |
| H3   | （条件触发）可按图表/实验条件检索，返回带单位和条件字段的证据片段      |
| H4   | 日志可区分 stage1/stage2/stage2.5/stage3；最终答案仅引用 stage2.5 证据 |
| H5   | 输出固定包含结论+证据表+LLM选段列表+不确定性说明；无引用总结被拦截     |
| H6   | 段落层命中 > 50%；答案可追溯率 100%；产出 G3 报告                      |

---

## 11. 常用命令速查

### 11.1 环境设置

```powershell
# 激活 OpenViking 专用 Python 3.11 环境
$env:OPENVIKING_CONFIG_FILE = "D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/OpenViking/.local_dev/ov.conf"
cd D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker
& .venv_ov311/Scripts/python.exe --version  # 应输出 Python 3.11.x
```

### 11.2 现有已验证命令（可随时复用）

```powershell
# 检查生成状态
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py --check-generation-status

# 结构完整性校验（E1）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py --validate-ov-index

# overview 质量校验（E2）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py --validate-overview-quality

# 语义冲突校验（E3）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py --validate-semantic-conflicts

# 回退报告（E4）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py --build-fallback-report

# 全量重建索引（正式，谨慎使用）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py --reindex --import-backend resource

# dry-run 预检（无副作用，可随时运行）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py --dry-run --overwrite --import-backend resource
```

### 11.3 备份命令（重建索引前必须执行）

```powershell
# 备份 OpenViking 数据目录（重建前必须做）
robocopy `
  "D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/data/openviking" `
  "D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/data/openviking_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')" `
  /E /COPYALL
```

### 11.4 H1/H2 执行时的推荐流程

```powershell
# Step 1: 备份（必须）
# （见 11.3）

# Step 2: 修改 import_to_openviking.py（实施 H1/H2 代码改动）

# Step 3: 语法检查
& .venv_ov311/Scripts/python.exe -m py_compile LiteratureClean/import_to_openviking.py
echo $LASTEXITCODE  # 应输出 0

# Step 4: dry-run 验证（单篇）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py `
  --dry-run --overwrite `
  --paper-id "2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9"

# Step 5: dry-run 验证（全量）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py `
  --dry-run --overwrite --import-backend resource

# Step 6: 正式重建（确认 dry-run 无误后）
& .venv_ov311/Scripts/python.exe LiteratureClean/import_to_openviking.py `
  --reindex --import-backend resource

# Step 7: 验收
# 检查 resources/literature/{paper_id}/ 下 section 文件是否完整
Get-ChildItem `
  "D:/AI4S/MicroHySeeker/MicroHySeeker/AutoHySeeker/data/openviking/viking/default/resources/literature" `
  -Recurse | Where-Object { $_.Name -match "\.abstract\.md|\.overview\.md" } | Select-Object FullName
```

### 11.5 H4 四阶段问答（qa_pipeline.py，待实现）

```powershell
# 完整四阶段问答
& .venv_ov311/Scripts/python.exe LiteratureClean/qa_pipeline.py "NiCoP催化剂的电流密度是多少？"

# 带分阶段日志
& .venv_ov311/Scripts/python.exe LiteratureClean/qa_pipeline.py "问题" --verbose

# 仅 Stage 1 检索（不调用 LLM）
& .venv_ov311/Scripts/python.exe LiteratureClean/qa_pipeline.py "问题" --dry-run
```

---

## 12. 当前已完成里程碑（仅记录，不执行）

### 12.1 Phase A-G 已完成概览

| Phase | 事项                   | 状态 | 关键结果                                                                                          |
| ----- | ---------------------- | ---- | ------------------------------------------------------------------------------------------------- |
| A0    | 文本 LLM 前置配置      | ✅   | `[chat]` 段配置可读，连通性验证通过                                                             |
| A1-A3 | 方案固化与门禁设计     | ✅   | 白名单规则、stale 状态机、导入门禁落地                                                            |
| B1-B3 | 视图层生成             | ✅   | ov_index 目录骨架生成，checksum 可复现，generation_status.json 全量写入 fresh=11                  |
| C1-C3 | LLM 可控生成链路       | ✅   | generate_missing/refresh_stale/regenerate_all CLI 全部落地                                        |
| D1-D4 | 导入脚本改造           | ✅   | build_ov_index_views → gate_check → import 拆分，白名单过滤，stale 门禁，resource/ovpack 双后端 |
| E1    | 结构校验               | ✅   | `--validate-ov-index`，papers=11, ok=11                                                         |
| E2    | 质量校验               | ✅   | `--validate-overview-quality`，pass=11/11, avg=92.97                                            |
| E3    | 语义冲突校验（新方案） | ✅   | 归一化+process_penalty，manual_review 11→5                                                       |
| E4    | 回退报告               | ✅   | `--build-fallback-report`，manual_review=5                                                      |
| G0    | 备份与回滚点           | ✅   | robocopy 备份，预检失败不 wipe 安全机制                                                           |
| G1    | 小样本试运行           | ✅   | 3 篇 dry-run + overwrite 通过                                                                     |
| G2    | 全量 reindex 导入      | ✅   | 11/11, included_files=422, error=0                                                                |
| **H1** | **修复 section 同名折叠** | ✅ | 拍平命名为 `{section_dir}.{abstract|overview}.md`，后缀体系统一                                |
| **H2** | **段落证据索引层**        | ✅ | `build_paragraph_chunks()`，<30跳过/30-350直接/>350拆分，YAML frontmatter chunk               |

### 12.2 venv 配置记录（供环境重建参考）

`.venv_ov311` 关键依赖：

- Python 3.11（绑定 `python311.dll`，与 OpenViking `engine.pyd` ABI 匹配）
- `pyagfs`（OpenViking 运行时核心依赖）
- `sentence-transformers`（本地 embedding 模型）
- `transformers`（与 `tokenizers` 版本配对）
- `tokenizers==0.23.0rc0`（当前约束，满足 transformers 兼容性要求）
- `volcengine-python-sdk[ark]`（可选，VLM provider 备用）

本地 embedding 配置（`ov.conf`）：

- provider: `sentence_transformers`
- model: `BAAI/bge-large-zh-v1.5`
- 不依赖 API key

### 12.3 已识别但暂缓的工作

| 项目                  | 原因                    | 当前决策                              |
| --------------------- | ----------------------- | ------------------------------------- |
| F1-F5（HTML 验证页）  | 依赖 H1/H2 完成         | 待 H2 后启动                          |
| VLM 能力              | 当前仅文本 LLM          | 后续增强，不在本阶段                  |
| ovpack 后端实跑       | 当前生产路径为 resource | 待环境稳定后补充验证                  |
| E2 relevance 缺失修复 | 影响较小（pass=11/11）  | 后续轻量修复（补 1-2 句，不重写全文） |

---

*文档版本: 2026-06-02 | 基于本轮全部已确认决策汇总*
*执行前请先阅读第 9 节（执行顺序）和第 11.4 节（H1/H2 执行流程）*

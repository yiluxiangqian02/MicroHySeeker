# LiteratureClean → OpenViking Embedding 文件结构说明

> 本文档描述每篇文献经预处理后导入 OpenViking 向量索引的文件布局，
> 以及在 `data/openviking/viking/` 文件系统中的最终存储结构。

---

## 一、整体流程

```
LiteratureClean/{paper_id}/          ← 预处理源目录
         ↓  import_to_openviking.py
[临时导出目录 (tmp_*)]               ← 重命名点文件 + 生成 combined 文件
         ↓  OpenViking add_resource()
data/openviking/viking/.../          ← viking 文件系统（原始文件镜像）
data/openviking/vectordb/            ← 向量索引（embedding + 标量索引）
```

---

## 二、LiteratureClean 源目录结构

```
LiteratureClean/{paper_id}/
├── .abstract.md          ← L0: 论文级摘要 (paper level, L0 type=paper)
├── .overview.md          ← L1: 论文概览
├── full_clean.md         ← 全文清洁版 (完整章节文本)
├── structured.json       ← 结构化数据
├── evidence_links.json   ← 证据链接 (evidence_id → figure/title/images)
├── metadata.json         ← 元数据 (title, doi, year, journal, raw_paths…)
├── image_manifest.json   ← 图片清单
├── table_manifest.json   ← 表格清单
├── PROCESSING_RECORD.md  ← 处理记录
├── figures/              ← 图片文件
│   ├── FIG001_01.jpg
│   ├── FIG001_02.jpg
│   └── ...
├── tables/               ← 表格数据 (Markdown 格式)
│   ├── TAB001.md
│   └── ...
└── memory_cards/         ← 记忆卡片 (per-figure / per-table / other)
    ├── figures/
    │   ├── FIG001/
    │   │   ├── .abstract.md    ← FIG001 L0 摘要
    │   │   ├── .overview.md    ← FIG001 L1 概览
    │   │   ├── figure.card.md  ← 图 ID、标题、evidence ID、检索标签
    │   │   ├── caption.md      ← 图注原文
    │   │   └── image_ref.md    ← 图片文件路径列表
    │   ├── FIG002/
    │   │   └── ...
    │   └── FIG00N/
    ├── tables/
    │   ├── TAB001/
    │   │   ├── .abstract.md    ← TAB001 L0 摘要
    │   │   ├── .overview.md    ← TAB001 L1 概览
    │   │   └── table.card.md   ← 表 ID、标题、evidence ID、检索标签
    │   └── TABxxx/
    └── (other card types)/     ← methods, results, conditions, metrics, etc.
        ├── .abstract.md
        ├── .overview.md
        └── *.card.md
```

---

## 三、导出到 OpenViking 的文件清单

`import_to_openviking.py` 的 `build_export_dir()` 从源目录选择并生成以下文件：

### 3.1 根目录文件（直接复制）

| 文件 | 来源 | 说明 |
|------|------|------|
| `abstract.md` | `.abstract.md`（重命名） | 论文级 L0 摘要（去掉前缀点） |
| `overview.md` | `.overview.md`（重命名） | 论文级 L1 概览 |
| `full_clean.md` | `full_clean.md` | 全文清洁版（会被 OpenViking 按章节分块） |
| `structured.json` | `structured.json` | 结构化数据 |
| `evidence_links.json` | `evidence_links.json` | 证据链接索引 |

### 3.2 子目录文件（glob 模式复制）

| 模式 | 说明 |
|------|------|
| `tables/TAB*.md` | 每张表格的完整 Markdown 数据 |
| `figures/*.jpg` / `*.png` / `*.jpeg` | 图片文件（用于 VLM 检索，非文本 embedding） |

### 3.3 memory_cards 其他类型（非 figures/tables）

仅复制方法卡、结果卡、条件卡等目录（不含 figures/tables，它们由步骤 3.4-3.5 处理）：

| 文件名（重命名后） | 来源 | 说明 |
|------|------|------|
| `abstract.md` | `.abstract.md` | 该卡片 L0 摘要 |
| `overview.md` | `.overview.md` | 该卡片 L1 概览 |

### 3.4 生成的图片 combined 文件（步骤 5，唯一命名）

**关键设计**：OpenViking 以文件名/标题作为 viking 目录名，相同文件名会覆盖。
为避免 FIG001-FIG00N 所有 `figure_combined.md` 覆盖为同一路径，使用唯一命名：

| 生成文件 | 存放位置（导出目录内） | 内容 |
|---------|------|------|
| `figure_combined_FIG001.md` | `memory_cards/figures/` | FIG001: `.abstract.md` + `figure.card.md` + `caption.md` |
| `figure_combined_FIG002.md` | `memory_cards/figures/` | FIG002: 同上 |
| `figure_combined_FIGxxx.md` | `memory_cards/figures/` | 每图独立文件 |

### 3.5 生成的表格 combined 文件（步骤 6，唯一命名）

| 生成文件 | 存放位置（导出目录内） | 内容 |
|---------|------|------|
| `table_combined_TAB001.md` | `memory_cards/tables/` | TAB001: `.abstract.md` + `table.card.md` + `tables/TAB001.md`（实际表格数据） |
| `table_combined_TABxxx.md` | `memory_cards/tables/` | 每表独立文件 |

---

## 四、Viking 文件系统中的目录结构

OpenViking 导入后，每篇论文在 viking 中存储为：

```
data/openviking/viking/default/resources/literature/
└── {paper_id}/
    └── {inner_dir}/          ← 截断版 paper_id（OpenViking 自动生成）
        ├── .abstract.md      ← OpenViking 自动生成的目录摘要（stub，~18B）
        ├── .overview.md      ← OpenViking 自动生成的目录概览（stub）
        ├── abstract/
        │   ├── .abstract.md  ← stub
        │   └── abstract.md   ← 论文 L0 摘要内容
        ├── overview/
        │   └── overview.md   ← 论文 L1 概览内容
        ├── evidence_links.json
        ├── structured.json
        │
        ├── figure_combined_FIG001/   ← 每个图片一个独立目录
        │   └── figure_combined_FIG001.md  ← FIG001 完整嵌入内容
        ├── figure_combined_FIG002/
        │   └── figure_combined_FIG002.md
        ├── figure_combined_FIGxxx/
        │   └── figure_combined_FIGxxx.md
        │
        ├── table_combined_TAB001/    ← 每个表格一个独立目录
        │   └── table_combined_TAB001.md   ← TAB001 完整嵌入内容（卡片+原始表格）
        ├── table_combined_TABxxx/
        │   └── table_combined_TABxxx.md
        │
        ├── full_clean/               ← OpenViking 按章节分块后的目录
        │   ├── .abstract.md          ← stub
        │   ├── INTRODUCTION.md       ← 章节内容
        │   ├── RESULTS_AND_DISCUSSION.md   ← 章节标题 stub（仅 heading）
        │   ├── 2_RESULTS_AND_DISCUSSION/   ← 含子节的章节变为子目录
        │   │   ├── subsection_1.md
        │   │   └── ...
        │   └── REFERENCES.md
        │
        └── (other memory card types)/
            └── abstract/abstract.md  ← methods/results 等卡片的 L0
```

### 注：关于 `full_clean/` 中的 stub 文件

OpenViking 的 Markdown 解析器（v5.0）将 `full_clean.md` 按标题分块：
- 小文档（< 1024 tokens）→ 保存为单一文件
- 大文档 → 按 `#`/`##` 标题拆分为多个 section 文件
- 含子标题的 section → 变为**子目录**，仅在目录下留 stub（标题文本，~26B）
- 小 section（< 512 tokens）→ 与相邻 section 合并（如 `CONCLUSIONS_8more.md`）

这些 stub 文件（如 `RESULTS_AND_DISCUSSION.md` 26B）属于**正常的 OpenViking 目录占位**，不是错误。

---

## 五、Viking 路径 → card_type 映射（search_hydrate.py）

`_detect_card(rel_parts)` 解析 viking URI 中的相对路径并返回卡片类型：

| Viking 路径模式 | card_type | card_id |
|------|------|------|
| `figure_combined_FIG001/figure_combined_FIG001.md` | `figure` | `FIG001` |
| `figure_combined_FIG002/figure_combined_FIG002.md` | `figure` | `FIG002` |
| `table_combined_TAB001/table_combined_TAB001.md` | `tables` | `TAB001` |
| `abstract/abstract.md` | `paper_summary` | — |
| `overview/overview.md` | `paper_summary` | — |
| `full_clean/INTRODUCTION.md` | `paper_section` | — |
| `full_clean/2_RESULTS_AND.../subsection.md` | `paper_section` | — |
| `memory_cards/figures/FIG001/...` | `figure` | `FIG001` |
| `memory_cards/tables/TAB001/...` | `tables` | `TAB001` |
| `memory_cards/methods/...` | `methods` | — |

---

## 六、向量数据库存储位置

```
data/openviking/vectordb/literature/index/store/
└── default/
    ├── collection_meta.json     ← 集合元数据
    └── versions/
        ├── {timestamp_A}/
        │   ├── scalar_index/
        │   │   └── scalar_index.data   ← 标量索引（URI + 元数据映射，~740KB）
        │   └── vector_index/
        │       └── index_flat.data     ← FAISS flat 向量索引（1024-dim，~2.1MB）
        └── {timestamp_B}/              ← 最新版本（--overwrite 后更新）
            ├── scalar_index.data
            └── index_flat.data
```

| 文件 | 内容 |
|------|------|
| `index_flat.data` | 所有文档块的 1024-dim float32 embedding（BAAI/bge-large-zh-v1.5） |
| `scalar_index.data` | 每条向量对应的 URI、相对路径、元数据 |
| `LevelDB store/*.ldb` | URI ↔ 向量 ID 的 KV 映射（LevelDB） |

---

## 七、关键设计决策记录

| 问题 | 根因 | 解决方案 |
|------|------|------|
| FIG001-FIG00N 只有最后一个 figure 被嵌入 | OpenViking 用文件 stem 作为目录名，同名覆盖 | 改为唯一命名 `figure_combined_FIG001.md` |
| `figurecard/figurecard.md` 只保留最后一图 | 同上 | 移除冗余组件文件（figure.card.md, caption.md, image_ref.md）从导出列表 |
| `paper_section` 标签错误标记 figure/table | 旧 _detect_card 仅检查 memory_cards 路径 | 加入正则 + 文件名匹配 (Priority 2/3) |
| `RESULTS_AND_DISCUSSION.md` 26B "空白" | OpenViking 分块时章节 heading 变成 stub | 正常行为，不是 bug |
| `.abstract.md` 18B "空白" | OpenViking 自动生成目录级 stub | 正常行为，不是 bug |

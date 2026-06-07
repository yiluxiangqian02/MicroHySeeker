"""Rebuild LITERATURE_CLEANING_GUIDE.md from known content."""
from pathlib import Path

GUIDE = Path(__file__).parent / "LITERATURE_CLEANING_GUIDE.md"

CONTENT_PARTS = []

CONTENT_PARTS.append("""\
# LiteratureClean 半自动文献清洗与重组规范

## 1. 目标

将 MinerU 解析后的原始论文输出，整理为结构化、可检索、可直接导入 OpenViking 的标准化文献包。

每篇文献清洗后输出到 `LiteratureClean/{paper_id}/`，包含：

- 清洗后的完整 Markdown 全文
- 结构化 JSON（方法、结果、材料、实验条件等）
- 证据链索引
- 有效科研图和表格
- 分层 memory card（L0 快速召回 / L1 详细导览）

---

## 2. 数据边界

### 2.1 原始数据（不修改）

```
MinerU/output/{uuid}/
  {filename}.md          — MinerU 生成的原始 Markdown
  {filename}_content_list.json   — 结构化内容列表
  content_list_v2.json   — v2 格式（双栏 PDF 图注来源）
  images/                — 所有提取出的图片
```

原始输出目录**只读**，清洗脚本不修改任何原始文件。

### 2.2 清洗后数据

```
LiteratureClean/{paper_id}/
  .abstract.md           — L0：短摘要，首行为 paper_id
  .overview.md           — L1：详细导览，包含结构索引
  full_clean.md          — 去噪后的完整正文 Markdown
  metadata.json          — 基础元数据（标题、作者、DOI 等）
  structured.json        — 结构化提取（方法/结果/材料/实验/表格）
  evidence_links.json    — evidence_id → 文本位置映射
  image_manifest.json    — 所有图片的原始路径和状态
  table_manifest.json    — 所有表格的提取信息
  PROCESSING_RECORD.md   — 处理记录（自动生成，供人工审查）
  figures/               — 有效科研图（复制自 MinerU images/）
  tables/                — 提取到的表格（Markdown 格式）
  memory_cards/          — 分层 memory card
```

---

## 3. 目录结构说明

### 3.1 L0 / L1 文件约定

| 文件 | 层级 | 用途 |
|------|------|------|
| `.abstract.md` | L0 | OpenViking 快速召回（简短，≤200字） |
| `.overview.md` | L1 | 详细导览，包含内容索引和链接 |

L0 文件名以 `.` 开头，OpenViking 目录扫描器需要特殊处理（见第 17 节）。

### 3.2 根目录 L0 / L1

`LiteratureClean/{paper_id}/.abstract.md` — 该文献的 L0 入口

示例格式：
```markdown
# {paper_id}

L0 type: paper
Title: {title}
Authors: {authors}
Year: {year}
DOI: {doi}
Key topic: {main topic in one sentence}

L1 entry: `.overview.md`
```

`LiteratureClean/{paper_id}/.overview.md` — 该文献的 L1 导览

示例格式：
```markdown
# {title}

## Paper Identity
- paper_id: {paper_id}
- Authors: {authors}
- Year: {year}
- DOI: {doi}
- Journal: {journal}

## What This Paper Answers

## Key Findings

## Methods Summary

## Evidence Structure
- Total evidence entries: N
- Key claims: see memory_cards/key_claims/

## File Index
- Full text: full_clean.md
- Structured data: structured.json
- Evidence index: evidence_links.json
- Figures: figures/ (N items)
- Tables: tables/ (N items)
- Memory cards: memory_cards/
```

### 3.3 memory_cards L0 / L1

每个 memory card 目录下有：
- `.abstract.md` — L0，供 OpenViking 快速召回
- `.overview.md` — L1，详细信息

### 3.4 memory_cards 类别

```
memory_cards/
  figures/FIGxxx/        — 每张有效科研图
    .abstract.md
    .overview.md
    fig.card.md          — 可人工补充的图注解释卡
  tables/TABxxx/         — 每张提取到的表格
    .abstract.md
    .overview.md
    table.card.md
  key_claims/            — 关键 claim（需人工填写）
  methods/               — 方法 memory card
  results/               — 结果 memory card
  materials/             — 材料 memory card
  conditions/            — 实验条件
  mechanisms/            — 机制解释
  metrics/               — 指标定义
```
""")

CONTENT_PARTS.append("""\
### 3.5 表格 memory card

**已正式实现。** 每张提取到的表格均自动生成：

```text
memory_cards/tables/TABxxx/
  .abstract.md      — L0：短摘要，供 OpenViking 快速召回
  .overview.md      — L1：详细导览，包含路径、caption、evidence_id、相关文件
  table.card.md     — 可人工补充的解释卡，预写好结构但留空需手动填写
```

**`.abstract.md` 格式：**

```markdown
# TABxxx: {title}

L0 type: table
Table number: Table X
Evidence ID: EVID_TABxxx
Paper: {paper_id}

{caption前300字}

L1 entry: `.overview.md`
Table content: `../../tables/TABxxx.md`
```

**`.overview.md` 格式：**

```markdown
# TABxxx: {title}

## What This Card Answers

## Caption

## Evidence

## Table Content
Full table (Markdown): `../../tables/TABxxx.md`

## Related Files
- structured.json — structured.tables 数组
- evidence_links.json — 证据索引
```

**`table.card.md`** 预写好表格基本信息，留空 "Key Observations" 供人工补充。

实际表格数据保存在 `tables/TABxxx.md`，`memory_cards/tables/` 只保存引用路径，不重复复制表格内容。

---

## 4. paper_id 规则

`paper_id` 格式：`{year}_{first_author_lastname}_{title_slug}_{hash6}`

- `year`：出版年份，未知时用 `unknown_year`
- `first_author_lastname`：第一作者姓氏（小写，ASCII）
- `title_slug`：标题前5-6个有效词（小写，下划线连接，去除停用词）
- `hash6`：MinerU uuid 或 MD5 前6位

示例：
```
2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e
2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c
unknown_year_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9
```

---

## 5. 优先文件

### 5.1 主要文件（必须生成）

| 文件 | 说明 |
|------|------|
| `.abstract.md` | L0 快速召回入口 |
| `.overview.md` | L1 详细导览 |
| `full_clean.md` | 清洗后完整正文 |
| `metadata.json` | 基础元数据 |
| `structured.json` | 结构化提取结果 |
| `evidence_links.json` | 证据链索引 |
| `memory_cards/figures/FIGxxx/` | 每张有效图 |

### 5.2 辅助文件（自动生成，供审查）

| 文件 | 说明 |
|------|------|
| `image_manifest.json` | 所有图片状态 |
| `table_manifest.json` | 所有表格信息 |
| `PROCESSING_RECORD.md` | 处理记录 |
| `figures/` | 有效科研图（从 MinerU 复制） |
| `tables/` | 表格 Markdown |

---

## 6. 文本清洗规则

### 6.1 保留内容

- 标题、摘要、引言、方法、结果、讨论、结论
- 图注（Figure X. ...）
- 表注（Table X. ...）
- 公式（保留原格式）
- 关键数据（百分比、电压、电流密度等）
- 正文中引用标记（[1], [2] 等）

### 6.2 删除内容

- 页眉、页脚（期刊名、页码、ISSN 等）
- 版权声明（© xxx, All rights reserved 等）
- 编辑流程信息（Received, Revised, Accepted 等）
- 下载来源、二维码、DOI 横幅
- 过多空行（超过2行的连续空行合并为2行）
- 纯分隔线（---、=== 等，若不是 Markdown 结构一部分）

### 6.3 参考文献

- **不进入 `full_clean.md`**：完整 References/Bibliography 列表
- **保留**：正文中的引用标记 [1]、(Smith et al., 2023) 等
- 原因：References 列表通常很长，影响检索质量；可通过 DOI 单独获取

---

## 7. evidence_id 规则

每个 evidence 条目有唯一 ID，格式：`EVID_{category}_{serial}`

常见类别：
- `EVID_KEY_CLAIM_001` — 关键 claim
- `EVID_METHOD_001` — 方法描述
- `EVID_RESULT_001` — 实验结果
- `EVID_MATERIAL_001` — 材料信息
- `EVID_CONDITION_001` — 实验条件
- `EVID_MECHANISM_001` — 机制解释
- `EVID_METRIC_001` — 指标定义
- `EVID_FIG001` — 图的 evidence（与 FIG001 对应）
- `EVID_TAB001` — 表格的 evidence（与 TAB001 对应）

`evidence_links.json` 结构：
```json
{
  "EVID_KEY_CLAIM_001": {
    "text": "...",
    "page": 1,
    "line": 45,
    "context": "...",
    "category": "key_claim"
  }
}
```

---

## 8. 图片清洗

### 8.1 判断是否为有效科研图

有效科研图需满足：
- 有图注（Figure X. ...）
- 图注内容与科研内容相关（非纯装饰、二维码、论文格式图）
- 文件存在于 MinerU `images/` 目录

### 8.2 复制规则

- 从 `MinerU/output/{uuid}/images/` 复制到 `LiteratureClean/{paper_id}/figures/`
- 重命名为 `FIG{serial:03d}.{ext}`（序号从 001 开始）
- 原始文件名保存在 `image_manifest.json` 中

### 8.3 image_manifest.json 结构

```json
{
  "FIG001": {
    "clean_path": "figures/FIG001.jpg",
    "raw_path": "MinerU/output/{uuid}/images/xxx.jpg",
    "caption": "Figure 1. ...",
    "evidence_id": "EVID_FIG001",
    "status": "copied"
  }
}
```
""")

CONTENT_PARTS.append("""\
---

## 9. metadata.json

标准字段：

```json
{
  "paper_id": "2023_uchino_...",
  "title": "Dependence of the reverse current...",
  "authors": ["Uchino Y.", "..."],
  "year": 2023,
  "doi": "10.1149/...",
  "journal": "Journal of The Electrochemical Society",
  "volume": "170",
  "issue": "4",
  "pages": "044503",
  "keywords": ["alkaline electrolysis", "reverse current", "..."],
  "raw_path": "MinerU/output/{uuid}/",
  "clean_path": "LiteratureClean/2023_uchino_.../",
  "processing_date": "2026-05-xx"
}
```

---

## 10. structured.json

### 10.1 顶层结构

```json
{
  "paper_id": "...",
  "core": {},
  "methods": [],
  "results": [],
  "materials": [],
  "conditions": [],
  "mechanisms": [],
  "metrics": [],
  "figures": [],
  "tables": [],
  "key_claims": []
}
```

### 10.2 核心字段（core）

```json
{
  "main_topic": "...",
  "research_question": "...",
  "main_conclusion": "...",
  "novelty": "...",
  "limitations": "..."
}
```

### 10.3 通用字段说明

所有数组条目均包含 `evidence_id`，指向 `evidence_links.json` 中的对应条目。

---

## 11. OpenViking 标签

在 `.abstract.md` 和 `.overview.md` 中可使用以下标签供 OpenViking 分类检索：

```
domain: electrochemistry / alkaline_electrolysis / reverse_current
material: Ni / NiRu / NiFe / RuO2
method: chronoamperometry / CV / EIS / XPS
result_type: degradation / protection / mechanism
year: 2023
```

---

## 12. L0/L1 检索层级

### 12.1 层级定义

| 层级 | 文件 | 内容 | 用途 |
|------|------|------|------|
| L0 | `.abstract.md` | ≤200字，关键词优先 | OpenViking 快速召回 |
| L1 | `.overview.md` | 完整导览，含索引 | 深度阅读入口 |
| L2 | `full_clean.md` | 完整正文 | 全文检索 |
| L3 | `structured.json` | 结构化数据 | 精确查询 |

### 12.2 根目录层级

- `{paper_id}/.abstract.md` — 论文 L0
- `{paper_id}/.overview.md` — 论文 L1

### 12.3 图 memory card 层级

- `memory_cards/figures/FIGxxx/.abstract.md` — 图 L0
- `memory_cards/figures/FIGxxx/.overview.md` — 图 L1

### 12.4 表格 memory card 层级

- `memory_cards/tables/TABxxx/.abstract.md` — 表格 L0
- `memory_cards/tables/TABxxx/.overview.md` — 表格 L1

### 12.5 主题 memory card 层级

- `memory_cards/key_claims/{claim_id}/.abstract.md`
- `memory_cards/methods/{method_id}/.abstract.md`
- `memory_cards/results/{result_id}/.abstract.md`

### 12.6 检索路径

OpenViking 检索示例：
```python
client.find("reverse current degradation", target_uri="viking://resources/literature/")
client.abstract("viking://resources/literature/2023_uchino_.../")
client.overview("viking://resources/literature/2023_uchino_.../")
```
""")

CONTENT_PARTS.append("""\
---

## 13. 半自动流程

### 13.1 单篇流程（clean_single_mineru_paper.py）

1. 确认 MinerU 输出目录存在
2. 读取原始 Markdown
3. 分页（按 Markdown 标题或分隔符）
4. 提取图注（Markdown 正则 + content_list_v2.json fallback）
5. 提取表格（content_list_v2.json + HTML 解析）
6. 从正文删除 References 列表
7. 删除页眉页脚噪声
8. 生成 `full_clean.md`
9. 构建 evidence 列表（方法/结果/材料/条件/机制）
10. 生成 `evidence_links.json`
11. 填写 `metadata.json`（DOI/作者等需人工核对）
12. 生成 `structured.json`
13. 复制有效科研图到 `figures/`
14. 生成 `image_manifest.json`
15. 复制表格图片到 `tables/`（若有）
16. 生成 `table_manifest.json`
17. 生成 `tables/TABxxx.md`（Markdown 表格）
18. 生成根目录 `.abstract.md` 和 `.overview.md`
19. 为有效科研图生成 `memory_cards/figures/FIGxxx/`
20. 为每张提取到的表格生成 `memory_cards/tables/TABxxx/`（含 `.abstract.md`、`.overview.md`、`table.card.md`）
21. 人工抽检 evidence、图片、表格、memory card 和关键字段

### 13.2 人工审查重点

- DOI 和作者是否从正文正确提取
- `metadata.json` 是否包含原始路径
- 关键实验条件是否有 evidence_id
- 关键结果和 claim 是否可回溯
- 有效科研图是否复制到 `figures/`
- 坏图是否正确标记
- `structured.json` 是否采用正确领域扩展层
- `.abstract.md` 是否简洁
- `.overview.md` 是否适合作为 OpenViking L1 导览
- memory card 是否覆盖关键方法、结果、claim、指标、条件、机制、图表
- 每个 memory card 的 `.abstract.md` 是否短且可检索
- 每个 memory card 的 `.overview.md` 是否能直接支持问答
- References 是否已从正文删除
- 不包含明显页眉页脚、版权、下载来源、二维码等噪声

---

## 14. 初版质量标准

单篇文献进入 OpenViking 前必须满足：

- `metadata.json` 存在且包含原始路径
- `.abstract.md` 存在
- `.overview.md` 存在
- `full_clean.md` 存在且保留完整清洁章节
- `structured.json` 存在且包含通用核心层
- `evidence_links.json` 中每个 evidence_id 可回溯
- `image_manifest.json` 记录所有原始图片状态
- `figures/` 只包含有效科研图
- `memory_cards/` 存在
- 每个 `memory_cards/**/.abstract.md` 都有同目录 `.overview.md`
- 关键方法、结果、claim、指标、条件、机制和有效图应有细粒度 L0 入口
- 若有提取到表格，`memory_cards/tables/TABxxx/` 必须存在，每张表有 `.abstract.md` 和 `.overview.md`
- 完整 References 列表不进入 `full_clean.md`
- 不包含明显页眉页脚、版权、下载来源、二维码等噪声

---

## 15. 已实现工具清单

以下工具已在 `AutoHySeeker/LiteratureClean/` 中实现：

| 脚本 | 说明 |
|------|------|
| `clean_single_mineru_paper.py` | 单篇论文清洗核心库（Sha 2025 专用 + 通用工具函数） |
| `batch_clean_mineru.py` | 批量清洗器，扫描 `MinerU/output`，自动处理所有论文 |
| `watch_mineru.py` | 自动监控守护脚本，轮询新到达的 MinerU 论文并自动处理 |
| `import_to_openviking.py` | 将 LiteratureClean 数据导入 OpenViking 知识库 |

**尚未实现：**

- 跨文献主题索引
- 跨文献知识图谱
- 自动问答 UI（通过 AutoHySeeker 前端实现）
- LLM 自动填充 `memory_cards/key_claims/`、`metrics/`、`conditions/`、`mechanisms/`（当前需手动）
""")

CONTENT_PARTS.append("""\
---

## 16. 双栏 PDF 处理说明

部分期刊（如 J. Electrochem. Soc.）采用双栏排版。MinerU 在解析这类 PDF 时，`full.md` 中的图注可能被打散嵌入正文流中，例如：

```
...as a function of logarithm of Figure 4.current density...
```

图注中的 "Figure 4." 与后续正文词汇混排，导致 Markdown 图注正则无法匹配。

### 16.1 解决方案

`parse_figures()` 在 Markdown 正则匹配后，启用 **JSON fallback 机制**：

1. 加载 `content_list_v2.json`（MinerU 结构化输出，双栏图注在此文件中保持正确结构）
2. 从 `image` 类型条目的 `image_caption` 数组提取图注
3. 用 `_infer_fig_num_from_caption()` 从标准前缀或乱码中段恢复图编号
4. 将 JSON 提取结果与 Markdown 结果合并，去重

### 16.2 适用范围

- 触发条件：Markdown 正则未匹配到任何图，但目录中存在 `content_list_v2.json`
- 对正常单栏 PDF 无影响（JSON 结果会因已被 Markdown 覆盖而被跳过）

### 16.3 验证

Uchino 2023（Dependence of the reverse current...）为典型双栏案例。
清洗后 `figures/` 应包含 FIG004–FIG008 共 5 张图；`tables/` 包含 TAB001–TAB005 共 5 张表。

---

## 17. 工具使用说明

### 17.1 批量清洗（batch_clean_mineru.py）

```powershell
# 在 AutoHySeeker/ 下
.venv\\Scripts\\python LiteratureClean\\batch_clean_mineru.py
# --overwrite : 强制覆盖已有输出
# --paper-filter <keyword> : 仅处理文件夹名包含关键词的论文
# --dry-run : 预览不执行
```

输出：
- `LiteratureClean/{paper_id}/` 完整清洗包
- `LiteratureClean/batch_run_log.json` 运行记录

### 17.2 自动监控（watch_mineru.py）

```powershell
.venv\\Scripts\\python LiteratureClean\\watch_mineru.py            # 每30s轮询
.venv\\Scripts\\python LiteratureClean\\watch_mineru.py --interval 60
.venv\\Scripts\\python LiteratureClean\\watch_mineru.py --once     # 单次扫描后退出
```

输出：`LiteratureClean/watch_log.json`

### 17.3 导入 OpenViking（import_to_openviking.py）

```powershell
.venv\\Scripts\\python LiteratureClean\\import_to_openviking.py
.venv\\Scripts\\python LiteratureClean\\import_to_openviking.py --paper-id 2023_uchino_...
.venv\\Scripts\\python LiteratureClean\\import_to_openviking.py --list
```

配置文件：`OpenViking/.local_dev/ov.conf`（本地 embedded 模式）

输出：`LiteratureClean/openviking_import_log.json`

**技术说明**：OpenViking 目录扫描器跳过以 `.` 开头的文件（如 `.abstract.md`）。
导入脚本会自动将 `.abstract.md` → `abstract.md`、`.overview.md` → `overview.md`
重命名到临时导出目录后再调用 `add_resource`，保留所有预写好的 L0/L1 内容。

### 17.4 推荐工作流

```
MinerU 解析 PDF
    ↓
watch_mineru.py（自动触发）或 batch_clean_mineru.py（手动批量）
    ↓
LiteratureClean/{paper_id}/ 完整清洗包
    ↓
人工审核（DOI、作者、图片、memory cards）
    ↓
import_to_openviking.py
    ↓
OpenViking 检索库（viking://resources/literature/）
```

---

## Related Files

- `LiteratureClean/clean_single_mineru_paper.py` — 核心清洗库
- `LiteratureClean/batch_clean_mineru.py` — 批量处理器
- `LiteratureClean/watch_mineru.py` — 自动监控
- `LiteratureClean/import_to_openviking.py` — OpenViking 导入
- `OpenViking/.local_dev/ov.conf` — OpenViking 本地配置
- `LiteratureClean/batch_run_log.json` — 运行日志
- `LiteratureClean/openviking_import_log.json` — 导入日志
""")

content = "\n".join(CONTENT_PARTS)
GUIDE.write_text(content, encoding='utf-8')
lines = content.split('\n')
print(f"GUIDE rebuilt: {len(lines)} lines, {len(content)} bytes")
sections = [l for l in lines if l.startswith('## ')]
print("Sections:")
for s in sections:
    print(" ", s)


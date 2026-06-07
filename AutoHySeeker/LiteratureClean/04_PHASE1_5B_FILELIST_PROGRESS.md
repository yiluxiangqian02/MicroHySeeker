# Phase 1.5B 预处理文件清单与进展

<!-- markdownlint-disable MD032 MD060 -->

> 说明：该文档为阶段性版本。全流程清单请以 `05_PLAN_B_FULL_TODO_PROGRESS.md` 为准。

## 范围说明

本文件仅跟踪预处理阶段（不含前端）向方案B迁移的进展：
- 事实层作为主结构（按原文标题树组织）
- 标签层作为附加信息（每段保留 S00-S07 标签）
- 标签记录状态统一使用：未完成 | 已完成

## 每篇文献目标产物清单（方案B）

### 1）根级元信息与处理记录

| 项目 | 状态 |
|---|---|
| metadata.json | 已完成 |
| PROCESSING_RECORD.md | 已完成 |
| quality_report.json | 已完成 |

### 2）事实层主索引（原文标题结构）

| 项目 | 状态 |
|---|---|
| original_structure_index.json | 已完成 |

heading 级必备字段：
- heading_uid
- heading_text
- heading_level
- doc_heading_order
- page_index
- block_order
- paragraph_uid_list
- inferred_type

### 3）段落地址簿与标签层元信息

| 项目 | 状态 |
|---|---|
| paragraph_index.json | 已完成 |

paragraph 级必备字段：
- paragraph_uid
- heading_uid
- heading_text
- heading_level
- doc_heading_order
- page_index
- block_order
- inferred_type
- macro_primary
- macro_secondary (S00-S07)
- macro_confidence
- macro_reasons

### 4）文档树与全文

| 项目 | 状态 |
|---|---|
| document_tree.json | 已完成 |
| full_clean.md | 已完成 |

### 5）证据与图表索引

| 项目 | 状态 |
|---|---|
| evidence_links.json | 已完成 |
| image_manifest.json | 已完成 |
| table_manifest.json | 已完成 |
| figures/ | 已完成 |
| tables/ | 已完成 |

## 6）主内容目录（历史阶段记录，以 05 为准）

| 项目 | 状态 |
|---|---|
| sections_by_heading/ | 已完成 |

说明：
- 主目录按原文标题树组织，事实层主结构已切换到 `sections_by_heading/NNN-title-slug/`。
- S00-S07 仅作为 metadata/tags，不再作为主目录名。

## 方案B明确弃用项

| 项目 | 状态 |
|---|---|
| sections/S00_... 到 sections/S07_... 作为主目录组织 | 已弃用（仅留历史兼容/回收检查） |
| section_abstract.md | 已完成（不生成） |
| section_overview.md | 已完成（不生成） |

## 迁移差距（现状 vs 目标）

当前样本文献仍存在：

结论：本阶段文档仅保留历史演进痕迹，现阶段已切换到标题树主目录。
- 已完成：original_structure_index.json、paragraph_index.json 已输出。
- 已完成：主目录切换为 `sections_by_heading/`。
- 已完成：旧 `sections/Sxx_...` 主目录不再作为新产物的主组织方式。

## 预处理验收标准（仅后处理/划分）

| 验收项 | 状态 |
|---|---|
| 每篇文献主目录采用标题树组织 | 已完成 |
| 不再使用 S00-S07 作为主目录层级 | 已完成 |
| paragraph_index.json 每段可唯一映射到 original_structure_index.json 某个 heading | 已完成（由 strict 校验覆盖） |
| S00-S07 仅出现于标签字段并附带置信度与原因 | 已完成（字段已写出，待全量复核） |
| 不生成 section_abstract.md / section_overview.md | 已完成 |

## 标签记录状态定义

| 标签 | 含义 |
|---|---|
| 未完成 | 任务或校验项未达到目标态 |
| 已完成 | 任务或校验项已满足目标态 |

## 实时进展日志

- 2026-05-29 09:58：创建本跟踪文档。（已完成）
- 2026-05-29 09:58：确认方案B每篇文献目标产物清单。（已完成）
- 2026-05-29 09:58：确认样本仍为 sections/S00-S07 主目录结构，识别出迁移缺口。（已完成）
- 2026-05-29 09:58：确认 original_structure_index.json 与 paragraph_index.json 已产出。（已完成）
- 2026-05-29 10:07：文档中文化并引入状态标记“未完成|已完成”。（已完成）

## 下一步（仅预处理）

| 任务 | 状态 |
|---|---|
| 将主内容输出从 sections/S00-S07 切换为 sections_by_heading/ | 已完成 |
| 保留 S00-S07 仅作为段落标签字段 | 已完成 |
| 重建至少 1 篇样本并核对清单合规 | 已完成 |
| 批量重建并生成合规汇总 | 已完成 |

## 收口说明

- 本文档已停止作为活跃任务清单使用，仅保留阶段历史。
- 当前活跃清单以 `05_PLAN_B_FULL_TODO_PROGRESS.md` 为准。

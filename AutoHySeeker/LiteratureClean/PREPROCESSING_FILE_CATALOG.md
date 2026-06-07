# LiteratureClean 预处理文件清单（属性与作用）

更新时间: 2026-05-28
适用范围: `AutoHySeeker/LiteratureClean/` 预处理阶段（MinerU -> LiteratureClean）

## 1. 文档目的

本清单用于帮助新成员快速理解 `LiteratureClean` 目录中每类文件的:

- 属性（手工维护/自动生成、是否可删除重建）
- 作用（负责什么）
- 生产者（由哪个脚本产出）
- 主要使用方（验证、检索、后续导入等）

---

## 2. 顶层目录结构（当前）

`LiteratureClean/` 当前包含三类内容:

1. 论文预处理产物目录（每篇一个 `paper_id/` 目录）
2. 预处理核心脚本、验证脚本、导入脚本
3. 运行日志、回归报告与说明文档

示例论文目录（已存在）:

- `2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9/`
- `2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201/`
- `2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb/`
- `2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e/`
- `2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9/`
- `2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6/`
- `2025_peng_strategies_and_countermeasures_against_reverse_current_f_803838/`
- `2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c/`
- `2025_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7/`
- `2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e/`
- `2026_unknown_2026_2d8d75/`

---

## 3. 顶层文件说明

### 3.1 核心预处理脚本

- `clean_single_mineru_paper.py`
  - 属性: 源代码，手工维护
  - 作用: 单篇预处理主引擎（构建 sections、索引、evidence、质量报告）
  - 生产者/修改者: 开发者
  - 使用方: `batch_clean_mineru.py`、`watch_mineru.py`

- `batch_clean_mineru.py`
  - 属性: 源代码，手工维护
  - 作用: 扫描 MinerU 输出并批量执行单篇预处理
  - 附加行为: 结束后自动刷新 `preprocessing_regression_report.md`

- `watch_mineru.py`
  - 属性: 源代码，手工维护
  - 作用: 轮询监听新 MinerU 目录并触发处理
  - 附加行为: 每次处理后自动刷新 `preprocessing_regression_report.md`

- `macro_section_rules.yaml`
  - 属性: 规则配置，手工维护
  - 作用: 宏章节顺序、标题、关键词打分规则
  - 当前关键 section:
    - `S04_results` -> `Result`
    - `S05_mechanism` -> `Mechanism`

### 3.2 验证与报告

- `verify_new_structure.py`
  - 属性: 源代码，手工维护
  - 作用: 验收预处理输出结构完整性与旧结构残留

- `generate_preprocessing_regression_report.py`
  - 属性: 源代码，手工维护
  - 作用: 汇总全量预处理统计，产出回归报告

- `preprocessing_regression_report.md`
  - 属性: 自动生成（可重建）
  - 作用: 全量成功/失败、每篇统计、人工复核清单
  - 触发: batch/watch 自动更新

- `preprocessing_progress_report.md`
  - 属性: 文档（人工维护）
  - 作用: 阶段性进展记录、问题和治理说明

### 3.3 导入与检索相关（预处理后使用）

- `import_to_openviking.py`
  - 属性: 源代码，手工维护
  - 作用: 将预处理产物导入 OpenViking

- `test_semantic_search.py`
  - 属性: 源代码，手工维护
  - 作用: 检索质量冒烟测试

- `search_hydrate.py`
  - 属性: 源代码，手工维护
  - 作用: 检索结果补水/展示辅助（按当前实现）

- `embedding_index_meta.json`
  - 属性: 数据文件（自动更新）
  - 作用: embedding/检索侧的索引元信息

- `openviking_import_log.json`
  - 属性: 运行日志（自动更新）
  - 作用: 记录导入执行结果

### 3.4 运行日志

- `batch_run_log.json`
  - 属性: 运行日志（自动更新）
  - 作用: 批处理每次运行与每篇状态记录

- `watch_log.json`
  - 属性: 运行日志（自动更新）
  - 作用: 监听模式处理记录

### 3.5 说明文档

- `LITERATURE_CLEANING_GUIDE.md`
  - 属性: 规范文档（手工维护）
  - 作用: 最终预处理执行规范

- `EMBEDDING_STRUCTURE.md`
  - 属性: 说明文档（手工维护）
  - 作用: embedding 结构/约定说明

### 3.6 调试与临时脚本（下划线前缀）

示例:

- `_check_collections.py`
- `_inspect_vectordb.py`
- `_inspect_structure.py`
- `_explore_ov.py`
- `_find_guide.py`
- `_fix_guide.py`
- `_rebuild_guide.py`
- `_test_ov_init.py`
- `_test_ov_init.log`

属性:

- 多为调试/修复辅助，不属于稳定主链
- 建议在发布前统一标注用途或迁移到 `tools/`/`scripts/`

---

## 4. 单篇 paper_id 目录文件清单

以任一 `LiteratureClean/{paper_id}/` 为单位，标准包含:

### 4.1 根文件（结构索引层）

- `metadata.json`
  - 作用: 论文基础元数据（paper_id、标题、来源等）

- `full_clean.md`
  - 作用: 清洗后的全文主文本

- `document_tree.json`
  - 作用: section 级结构树（section_id/title/order/paragraph_ids）

- `paragraph_index.json`
  - 作用: 段落级总索引（paragraph -> section/evidence/link）

- `evidence_links.json`
  - 作用: evidence 到内容文件路径的回链映射

- `image_manifest.json`
  - 作用: 图片资产与使用状态清单

- `table_manifest.json`
  - 作用: 表格资产清单

- `quality_report.json`
  - 作用: 质量检查结果与 `uncertain_items`

- `PROCESSING_RECORD.md`
  - 作用: 本篇处理过程与产物摘要（可读说明）

### 4.2 资源目录

- `figures/FIGxxx/`
  - 常见文件: `caption.md`, `image_001.*`
  - 作用: 图像资产与说明

- `tables/TABxxx/`
  - 常见文件: `table.md`, `caption.md`, `image_001.*`
  - 作用: 表格内容与渲染图

### 4.3 sections 目录（核心）

- `sections/Sxx_.../`
  - 例如: `S04_results/`, `S05_mechanism/`

每个 section 下标准文件:

- `subheading_index.json`
  - 作用: 原始 heading 归并结果（含 `assigned_by`、`score_breakdown`）

- `paragraphs.md`
  - 作用: 本 section 的可读段落总览

- `paragraphs/Pxxx.md`
  - 作用: 单段正文、证据、关联 figure/table、关键词

---

## 5. 文件生命周期与变更策略

### 5.1 可重建文件（不要手工改）

- 所有 `paper_id/` 目录内 json/md 产物
- `batch_run_log.json`
- `watch_log.json`
- `preprocessing_regression_report.md`
- `openviking_import_log.json`

原则:

- 这类文件由脚本生成，手改会在下次运行被覆盖

### 5.2 手工维护文件（允许编辑）

- `macro_section_rules.yaml`
- `LITERATURE_CLEANING_GUIDE.md`
- `preprocessing_progress_report.md`
- 本文件 `PREPROCESSING_FILE_CATALOG.md`

原则:

- 修改后建议执行一次 `batch_clean_mineru.py --overwrite` + `verify_new_structure.py`

---

## 6. 建议的新人上手顺序

1. 先读 `LITERATURE_CLEANING_GUIDE.md`
2. 再读本文件 `PREPROCESSING_FILE_CATALOG.md`
3. 看 `macro_section_rules.yaml` 理解 section/关键词策略
4. 看 `clean_single_mineru_paper.py` 的 section 归并与索引写出逻辑
5. 运行 `verify_new_structure.py` 验证当前产物
6. 查 `preprocessing_regression_report.md` 了解全量状态

---

## 7. 当前命名基线（本次确认）

- Section ID:
  - `S04_results`
  - `S05_mechanism`

- Section Title:
  - `S04_results` -> `Result`
  - `S05_mechanism` -> `Mechanism`

此命名已作为当前预处理主链标准。

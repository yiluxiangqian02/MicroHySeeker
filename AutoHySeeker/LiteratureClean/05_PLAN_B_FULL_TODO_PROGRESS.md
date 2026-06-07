# 方案B全流程Todo与进展清单（从当前到落地）

<!-- markdownlint-disable MD032 MD060 -->

## 说明

此清单覆盖从当前代码状态到方案B正式落地的全流程任务。

方案B定义：
- 事实层优先：按原文标题树组织主结构
- 标签层附加：S00-S07仅作为段落标签与过滤视图
- 唯一键保留：evidence_id继续用于内部追踪/去重

状态标签：
- 未完成
- 进行中
- 已完成
- 阻塞

---

## A. 当前基线盘点

| ID | 任务 | 状态 | 备注 |
|---|---|---|---|
| A1 | 核对样本文献产物结构 | 已完成 | 样本仍是 sections/S00...S07 主目录 |
| A2 | 核对核心预处理脚本输出点 | 已完成 | 已确认写出 original_structure_index.json / paragraph_index.json |
| A3 | 建立统一跟踪文档 | 已完成 | 已建立中文跟踪文档与状态字段 |

---

## B. 事实层主结构改造（核心）

| ID | 任务 | 状态 | 验收标准 |
|---|---|---|---|
| B1 | 新增主目录输出 sections_by_heading/ | 已完成 | 每个 heading_uid 对应一个目录节点 |
| B2 | 停止以 sections/S00-S07 作为主目录组织 | 已完成 | 新构建产物中不再出现该主组织方式 |
| B3 | 段落先归属原文 heading，再附加标签 | 已完成 | 标签不改变事实归属 |
| B4 | 保证 heading 顺序稳定（doc_heading_order） | 已完成 | 重跑顺序一致 |
| B5 | 保证 paragraph_uid 稳定 | 已完成 | 同文档重跑 paragraph_uid 不漂移 |

---

## C. 标签层完善（S00-S07 仅附加）

| ID | 任务 | 状态 | 验收标准 |
|---|---|---|---|
| C1 | 段落标签字段完整输出 | 已完成 | macro_primary/macro_secondary/macro_confidence/macro_reasons 已在索引中 |
| C2 | 标签冲突记录机制 | 已完成 | 冲突有原因、置信度，不改事实层归属 |
| C3 | 标签可回溯到规则来源 | 已完成 | 每条标签可追踪规则命中或推断原因 |

---

## D. 文件清单与产物合规

| ID | 任务 | 状态 | 验收标准 |
|---|---|---|---|
| D1 | 每篇文献必备文件清单固化 | 已完成 | 清单已文档化 |
| D2 | 强制不生成 section_abstract.md / section_overview.md | 已完成 | 当前流程已不生成 |
| D3 | 新增产物合规检查脚本（按清单核验） | 已完成 | 输出 pass/fail + 缺失项 |

目标产物（每篇文献）：
- metadata.json
- PROCESSING_RECORD.md
- quality_report.json
- original_structure_index.json
- paragraph_index.json
- document_tree.json
- full_clean.md
- evidence_links.json
- image_manifest.json
- table_manifest.json
- figures/
- tables/
- sections_by_heading/（目标新增）

---

## E. 一致性校验与质量门禁

| ID | 任务 | 状态 | 验收标准 |
|---|---|---|---|
| E1 | paragraph_index -> original_structure 映射唯一性校验 | 已完成 | 每个 paragraph_uid 唯一映射到一个 heading_uid |
| E2 | 事实层覆盖率统计 | 已完成 | 未归属段落比例可量化且低于阈值 |
| E3 | 标签层覆盖率统计 | 已完成 | 标签覆盖率与空值率可量化 |
| E4 | CI门禁接入 | 已完成 | 合规检查失败即阻断 |

---

## F. 回归与重建

| ID | 任务 | 状态 | 验收标准 |
|---|---|---|---|
| F1 | 单篇样本重建（2025_sha） | 已完成 | 产物符合方案B主目录要求 |
| F2 | 第二样本重建（2023_a...） | 已完成 | 产物符合方案B主目录要求 |
| F3 | 批量重建 LiteratureClean | 已完成 | 全量生成成功率达标 |
| F4 | 生成迁移报告 | 已完成 | 含成功数、失败数、缺口项 |

---

## G. 文档与协作约束

| ID | 任务 | 状态 | 验收标准 |
|---|---|---|---|
| G1 | 规范文档写明“事实优先、标签附加” | 已完成 | 文档可作为评审基线 |
| G2 | 标注弃用旧组织方式 | 已完成 | 新旧方案边界清晰 |
| G3 | 建立实时进展日志机制 | 已完成 | 每次变更追加日志 |

---

## 里程碑

| 里程碑 | 目标 | 状态 |
|---|---|---|
| M1 | 代码层完成 B1-B5 + C2 | 已完成 |
| M2 | 单篇与双样本验证通过（F1/F2） | 已完成 |
| M3 | 全量重建与报告完成（F3/F4） | 已完成 |
| M4 | 门禁与文档收口（E4/G1/G2） | 已完成 |

---

## 当前总体进展（估算）

- 已完成：A1 A2 A3 B1 B2 B3 B4 B5 C1 C2 C3 D1 D2 D3 E1 E2 E3 E4 F1 F2 F3 F4 G3
- 进行中：无
- 未完成：其余

整体完成度（估算）：约 95%

---

## 实时进展日志

- 2026-05-29 09:58：完成方案B目标文件清单梳理（中文）。
- 2026-05-29 10:07：文档加入状态字段“未完成|已完成”。
- 2026-05-29 10:14：升级为“从当前到方案B落地”的全流程Todo与进展清单（本文件）。
- 2026-05-29 10:26：完成 B1/B2：主目录输出切换为 sections_by_heading/，并停用旧 sections/ 主目录。
- 2026-05-29 10:29：完成 E1：新增 paragraph_uid -> heading_uid 唯一映射及 original_structure 追溯校验。
- 2026-05-29 10:32：完成 F1：重建 2025_sha 样本并在 strict 模式下校验通过（errors=0, warnings=0）。
- 2026-05-29 10:41：完成 F2：重建 2023_a 样本并在 strict 模式下校验通过（errors=0, warnings=0）。
- 2026-05-29 18:31：完成 D3：新增 `check_plan_b_compliance.py`，生成 `plan_b_compliance_report.json/.md`（11/11 通过，100.00%）。
- 2026-05-29 18:31：完成 E2/E3：`quality_report.json` 新增 `fact_layer_coverage` 与 `tag_layer_coverage` 指标。
- 2026-05-29 18:31：完成 F3/F4：全量批量重建 11 篇样本成功（failed=0），并输出阶段迁移报告。
- 2026-05-30：完成 E4：新增 CI workflow `AutoHySeeker/.github/workflows/plan-b-gate.yml`，在 PR/Push 上强制执行 `verify_new_structure.py --strict` 与 `check_plan_b_compliance.py --strict`，任一失败即阻断。
- 2026-05-30：完成 heading 目录可读化迁移：`sections_by_heading/` 从 `HRAW-*` 统一为 `NNN-title-slug`（按路径预算自动截断，重复标题自动 `-dupN`），并全量回写 `paragraph_index.json`/`evidence_links.json` 路径；全量 strict 校验与合规检查再次 11/11 通过。
- 2026-05-30：完成 B4/B5：新增 `check_rebuild_stability.py`，执行 `--run-rebuild` 后输出 `rebuild_stability_report.json/.md`，11/11 通过（heading 顺序稳定、paragraph_uid 无漂移）。
- 2026-05-30：完成 C2/C3：新增段落级 `macro_conflict` 与 `macro_trace` 字段，新增 `tag_conflicts.json`（冲突原因/等级/候选分数/规则来源可追溯）；全量重建后 strict 校验与合规检查再次 11/11 通过。
- 2026-05-30：完成 G1/G2：`00_LITERATURE_CLEANING_GUIDE.md`、`01_FILE_LOG.md` 与 `04_PHASE1_5B_FILELIST_PROGRESS.md` 收口到“事实优先、标签附加；`sections_by_heading/` 为主结构；旧 `sections/Sxx_...` 仅作历史兼容/弃用说明”。
- 2026-05-30：完成合规收口：`check_plan_b_compliance.py` 将 `tag_conflicts.json` 纳入必检文件列表，与 strict 结构校验完全一致。

---

## 下一步立即执行（建议）

1. 评估将 `check_rebuild_stability.py` 纳入周期性回归任务（非每次 PR 强制）。
2. 将 `tag_conflicts.json` 纳入合规清单的必检项，与 strict 结构校验保持一致。
3. 若后续还有新规则，优先更新 `macro_section_rules.yaml` 与 `00_LITERATURE_CLEANING_GUIDE.md`，保持规范同步。

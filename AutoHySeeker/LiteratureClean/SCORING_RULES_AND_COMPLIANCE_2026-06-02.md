# 评分规则与合规结果说明（2026-06-02，已更新）

## 0. 文档目的

本文档用于统一说明 LiteratureClean -> OpenViking 流程中的评分口径、人工审核触发规则，以及当前批次（11 篇）的最新结果。

适用范围：

- E1：ov_index 结构完整性
- E2：overview 文本质量
- E3：语义冲突风险
- E4：回退与人工审核决策

---

## 1. 评分标准（按模块）

## 1.1 E1：结构完整性（Validation）

评估对象：每篇论文的 ov_index 产物和状态链。

主要检查项：

- 必需文件是否存在（paper.abstract.md / paper.overview.md / sections/*）
- 是否为占位内容或空内容
- sections 目录是否与 sections_by_heading 对齐
- generation_status.json 是否存在且有效

输出字段：

- status: ok / issue
- issue_count: 结构问题总数

判定逻辑：

- issue_count = 0 -> ok
- issue_count > 0 -> issue

---

## 1.2 E2：overview 质量分

E2 分为两类对象：

- paper_overview
- section_overview

### 1.2.1 长度分（Length Score）

规则：

- 在目标区间内 -> 100
- 低于下限或高于上限 -> 按 gap 线性扣分，最多扣 70
- 最终范围 [0, 100]

阈值：

- paper_overview: 180-320 词
- section_overview: 120-220 词

### 1.2.2 结构分（Structure Score，仅 paper_overview）

关键词命中项：

- background
- method
- results
- practical implications

公式：

- structure_score = round((命中项数 / 4) * 100)

### 1.2.3 信号分（Signal Score，仅 section_overview）

三组信号：

- claim
- evidence
- relevance

当前词表策略：中等扩展（中英混合），避免过宽泛词（例如 for）。

公式：

- signal_score = round((命中组数 / 3) * 100)

### 1.2.4 E2 综合分与等级

公式：

- paper_overview_score = length_score * 0.6 + structure_score * 0.4
- section_overview_score = length_score * 0.7 + signal_score * 0.3
- paper_avg_score = 各 item 分数算术平均

等级：

- pass: >= 85
- warn: >= 70 且 < 85
- fail: < 70

补充：

- 若文件为空或占位内容，记为 placeholder_or_empty，score=0

---

## 1.3 E3：语义冲突分（最新已落地方案）

E3 采用分层计分：

- 语义本体分（raw_conflict）
- 归一化主分（normalized_conflict）
- 流程惩罚分（process_penalty）

### 1.3.1 语义本体分

记：

- h = high_tag_conflicts 数量
- m = medium_tag_conflicts 数量
- l = low_tag_conflicts 数量

公式：

- raw_conflict = h * 10 + m * 2 + l * 0.5

### 1.3.2 归一化主分

记：

- s = section_count = max(1, section_targets_count)

公式：

- normalized_conflict = min(100, raw_conflict / s * 2.0)

### 1.3.3 流程惩罚分

单列惩罚项（不并入 raw_conflict）：

- generation_status != fresh: +10
- evidence_links.json 缺失: +5
- tag_conflicts.json 缺失/无效: +8
- tag_conflicts.items 缺失: +8
- paper abstract/overview 缺失: +10
- section targets 缺失: +10

### 1.3.4 E3 最终分与等级

公式：

- conflict_score = min(100, normalized_conflict + process_penalty)

等级：

- high: >= 40
- medium: >= 20 且 < 40
- low: <= 19

---

## 1.4 E4：回退动作与人工审核

E4 综合 E1/E2/E3 生成决策：

- fallback_action: none / generate_missing / refresh_stale / manual_review_only（可组合）
- manual_review: 是否进入人工审核

当前审核触发规则：

- E3 为 high 或 medium -> manual_review_only
- E1 issue 或 E2 warn/fail 也会触发人工介入路径

---

## 2. 生成侧约束（避免模板化降质）

section overview 使用软模板：

- 固定结构：## Claim / ## Evidence / ## Relevance
- 要求：每段 1-2 句，必须锚定原文，不新增原文没有的断言
- 目标：提升信号命中稳定性，同时控制内容失真风险

---

## 3. 当前结果（本轮最新实测）

数据来源：

- overview_quality_report.json
- semantic_conflict_report.json
- fallback_review_report.json

### 3.1 汇总结果

- E2（overview 质量）：papers=11, pass=11, warn=0, fail=0, avg_score=92.97
- E3（语义冲突）：papers=11, high=2, medium=3, low=6, avg_conflict_score=21.52
- E4（回退与审核）：papers=11, ok=6, needs_fallback=5, manual_review=5

### 3.2 改造收益（核心）

- 人工审核数量：11 -> 5
- 说明：本轮主要收益来自 E3 归一化计分，而非单纯扩词

---

## 4. 逐篇结果（当前）

| paper_id | E2_avg | E2_warn | E2_fail | E2_issue_items | E3_score | E3_level | manual_review |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9 | 93.78 | 1 | 0 | 4 | 19.00 | low | False |
| 2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201 | 92.08 | 0 | 0 | 12 | 10.00 | low | False |
| 2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb | 93.10 | 1 | 0 | 15 | 40.86 | high | True |
| 2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e | 92.57 | 0 | 0 | 12 | 22.20 | medium | True |
| 2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9 | 92.06 | 1 | 0 | 11 | 44.86 | high | True |
| 2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6 | 95.05 | 0 | 0 | 9 | 29.53 | medium | True |
| 2025_peng_strategies_and_countermeasures_against_reverse_current_f_803838 | 93.72 | 2 | 0 | 10 | 31.78 | medium | True |
| 2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c | 94.29 | 0 | 0 | 15 | 14.24 | low | False |
| 2025_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7 | 91.40 | 1 | 0 | 12 | 5.07 | low | False |
| 2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e | 92.91 | 1 | 0 | 9 | 4.31 | low | False |
| 2026_unknown_2026_2d8d75 | 91.66 | 5 | 1 | 27 | 14.85 | low | False |

---

## 5. 当前不合规重点

### 5.1 E2 侧（信号缺失）

当前 issue 仍主要集中在 missing_signals:relevance。

现状解读：

- E2 总体平均分高，但 section 粒度仍有较多信号缺失条目
- 质量改进重点应放在 relevance 句型覆盖与生成后轻量修复

### 5.2 E3 侧（仍需人工审核的 5 篇）

当前 manual_review=True 的论文对应 E3 level 为 high/medium：

- 2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb (high)
- 2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e (medium)
- 2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9 (high)
- 2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6 (medium)
- 2025_peng_strategies_and_countermeasures_against_reverse_current_f_803838 (medium)

---

## 6. 建议的下一步

1. 继续保持 E3 分层计分口径（raw + 归一化 + process_penalty）。
2. 对 E3=medium 的样本做人工抽检，确认是否可进一步降低审核阈值。
3. 对 relevance 缺失 section 增加轻量后处理（仅补 1-2 句，不重写全文）。
4. 每次参数调整后固定输出改前/改后对比：manual_review、E3分布、E2缺失分布。

---

## 7. 结论

当前评分体系已从“绝对计数导致高分堆积”转为“归一化主分 + 流程惩罚分离”的可解释方案。

在不牺牲流程安全门禁的前提下，本轮已实现人工审核数量显著下降（11 -> 5），且结果可复核、可追踪。

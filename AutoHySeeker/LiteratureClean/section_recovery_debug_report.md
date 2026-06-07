# Section Recovery Debug Report

## Scope

- 本轮只重建两篇目标文献，未做全量。
- 未运行 OpenViking、embedding、LLM。
- 重建前已清理两篇的 sections 目录。

## Rule Fixes Applied

- 增加 Abstract recovery：支持 Abstract/ABSTRACT/Abstract:/摘要/摘要：、加粗 Abstract、摘要常见起始句（This study / In this work / Herein / We investigate / 本文 / 本研究）。
- 增加 Front matter detector：DOI/URL、article info、author/affiliation、journal/publisher、received/accepted/available online 等优先归 S00。
- 增加 Back matter detector：References、CRediT、Data availability、Declaration of competing interest、Acknowledgements 等优先归 S07。
- 增加 Conclusion direct rule：标题或段落起始命中 Conclusion/Conclusions/Summary/结论/总结/结论与展望 直达 S06。
- 增加结构辅助恢复：使用 MinerU content_list_v2 的 block type + page/order 生成 recovery hints，并记录 layout.json 可用性。

## Preprocessing Strategy Summary

当前预处理采用“heading 级初判 + paragraph 级恢复”的两层策略：

1. 先做 heading 级分类
- 先命中 direct_rules（高确定性标题直达）。
- 未命中时走关键词打分（score_breakdown）。

2. 再做 paragraph 级 section recovery（用于修复无标题/混排场景）
- front_matter_detector: DOI/URL/作者/单位/ARTICLEINFO/received/accepted/published 等 -> S00。
- abstract_leading_detector: Abstract/摘要及其连续摘要段、Keywords -> S01。
- conclusion_start_detector: 段首命中 Conclusion/Conclusions/Summary/结论/总结/结论与展望 -> S06。
- back_matter_detector: References/CRediT/Data availability/Acknowledgements 等 -> S07。

3. 冲突处理优先级
- 若同段同时命中多类规则，优先级为:
	1) front matter
	2) conclusion
	3) abstract
	4) back matter
	5) 保持原 section

4. 结构辅助信号
- content_list_v2 的块类型、页序与文本顺序用于生成恢复 hints。
- layout.json 当前作为可用性标记与后续扩展入口，不直接覆盖分类决策。

## 2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9

### Section Directories After Rebuild

- S00_front_matter
- S01_abstract
- S02_introduction
- S03_methods_and_setup
- S04_results
- S06_conclusion
- S07_back_matter_or_supplementary

### Recovery Hint Summary

- content_list front hints: 1
- content_list abstract hints: 2
- content_list back hints: 2
- layout.json available: True

### Misclassified Paragraphs Before -> Now

- 原 S00/P003 (Abstract...) -> S01-P001 (S01_abstract)
- 原 S00/P004 (摘要续段) -> S01-P002 (S01_abstract)
- 原 S00/P005 (Keywords...) -> S01-P003 (S01_abstract)

### Abstract Recovery Hits

- sections/S01_abstract/paragraphs/P001.md
- sections/S01_abstract/paragraphs/P002.md
- sections/S01_abstract/paragraphs/P003.md

### Front Matter Detector Hits

- sections/S00_front_matter/paragraphs/P001.md

### Back Matter Detector Hits

- sections/S07_back_matter_or_supplementary/paragraphs/P001.md

### Contamination Check in S03/S04/S05

- 摘要混入: none
- 作者/URL/DOI 等 front matter 混入: none
- References/CRediT/Data availability 混入: none

### Conclusion Section Check

- S06_conclusion exists: True

## 2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c

### Section Directories After Rebuild

- S00_front_matter
- S01_abstract
- S03_methods_and_setup
- S04_results
- S05_discussion_mechanism
- S07_back_matter_or_supplementary

### Recovery Hint Summary

- content_list front hints: 7
- content_list abstract hints: 2
- content_list back hints: 17
- layout.json available: True

### Misclassified Paragraphs Before -> Now

- 原 S04/P001 (URL/DOI) -> S00-P001 (S00_front_matter)
- 原 S04/P002 (author list) -> S00-P002 (S00_front_matter)
- 原 S04/P003 (abstract) -> S01-P001 (S01_abstract)

### Abstract Recovery Hits

- sections/S01_abstract/paragraphs/P001.md
- sections/S01_abstract/paragraphs/P002.md
- sections/S01_abstract/paragraphs/P003.md

### Front Matter Detector Hits

- sections/S00_front_matter/paragraphs/P001.md
- sections/S00_front_matter/paragraphs/P002.md

### Back Matter Detector Hits (sample)

- sections/S07_back_matter_or_supplementary/paragraphs/P001.md
- sections/S07_back_matter_or_supplementary/paragraphs/P002.md
- sections/S07_back_matter_or_supplementary/paragraphs/P003.md
- sections/S07_back_matter_or_supplementary/paragraphs/P004.md
- sections/S07_back_matter_or_supplementary/paragraphs/P005.md

### Contamination Check in S03/S04/S05

- 摘要混入: none
- 作者/URL/DOI 等 front matter 混入: none
- References/CRediT/Data availability 混入: none

### Conclusion Section Check

- S06_conclusion exists: False (该样本当前未识别到明确结论段标题/起始语)

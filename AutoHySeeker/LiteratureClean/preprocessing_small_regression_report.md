# Preprocessing Small Regression Report

Date: 2026-05-28
Scope: Small regression only (3 papers), no full-batch run, no OpenViking

## Sample Selection

1. Standard English journal paper:
- 2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9

2. English paper containing CRediT / Data availability / References in source text:
- 2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c
- Source-text check in full_clean.md: credit=True, data availability=True, references/bibliography=True

3. Chinese or non-standard report style:
- 2026_unknown_2026_2d8d75

## Execution Protocol

For each paper:
1. Deleted old sections directory under the paper_id path.
2. Rebuilt using LiteratureClean/clean_single_mineru_paper.py with --overwrite.
3. Ran structural and content checks listed below.

## Check Matrix

Checks:
- A. memory_cards residual
- B. S00_front_matter generated
- C. S06_conclusion generated
- D. References routed to S07_back_matter_or_supplementary
- E. CRediT / Author contribution / Data availability routed to S07
- F. Title/author/affiliation/ARTICLEINFO routed to S00
- G. Legacy section dirs exist (S05_mechanism, S07_supplementary, etc.)
- H. paragraph_index.json uses new section naming
- I. document_tree.json uses new section naming
- J. evidence_links.json uses new section naming
- K. paragraph_index content_path points to real files
- L. image_manifest linked_paragraphs available

### 1) 2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9

- Sections generated:
  - S00_front_matter
  - S02_introduction
  - S03_methods_and_setup
  - S04_results
  - S06_conclusion
- A memory_cards residual: PASS (none)
- B S00 generated: PASS
- C S06 generated: PASS
- D References -> S07: N/A (no references heading detected in structured headings)
- E CRediT/Author contribution/Data availability -> S07: N/A (none detected)
- F Title/author/affiliation/ARTICLEINFO -> S00: PARTIAL (S00 exists; explicit ARTICLEINFO heading not detected)
- G Legacy dirs: PASS (none)
- H paragraph_index naming: PASS
- I document_tree naming: PASS
- J evidence_links naming: PASS
- K content_path existence: PASS
- L image_manifest linkage: PASS (11 images with linked_paragraphs)

### 2) 2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c

- Sections generated:
  - S03_methods_and_setup
  - S04_results
  - S05_discussion_mechanism
  - S07_back_matter_or_supplementary
- A memory_cards residual: PASS (none)
- B S00 generated: FAIL (not generated)
- C S06 generated: FAIL (not generated)
- D References -> S07: PARTIAL (no structured references heading detected; source text contains references)
- E CRediT/Author contribution/Data availability -> S07: PARTIAL
  - Data availability heading detected and routed to S07 (PASS)
  - CRediT/Author contribution heading not detected in structured headings in this rebuild
- F Title/author/affiliation/ARTICLEINFO -> S00: FAIL (S00 missing)
- G Legacy dirs: PASS (none)
- H paragraph_index naming: PASS
- I document_tree naming: PASS
- J evidence_links naming: PASS
- K content_path existence: PASS
- L image_manifest linkage: PASS (13 images with linked_paragraphs)

### 3) 2026_unknown_2026_2d8d75

- Sections generated:
  - S02_introduction
  - S03_methods_and_setup
  - S04_results
  - S05_discussion_mechanism
  - S07_back_matter_or_supplementary
- A memory_cards residual: PASS (none)
- B S00 generated: FAIL (not generated)
- C S06 generated: FAIL (not generated)
- D References -> S07: PASS
  - Heading hit: 主要参考文献 -> S07_back_matter_or_supplementary (direct_rule)
- E CRediT/Author contribution/Data availability -> S07: N/A (not present as structured headings)
- F Title/author/affiliation/ARTICLEINFO -> S00: FAIL (S00 missing)
- G Legacy dirs: PASS (none)
- H paragraph_index naming: PASS
- I document_tree naming: PASS
- J evidence_links naming: PASS
- K content_path existence: PASS
- L image_manifest linkage: PASS (5 images with linked_paragraphs)

## Chinese Heading Hits Verified This Round

From 2026_unknown_2026_2d8d75:
- 1.1 抗反向电流研究的背景与意义 -> S02_introduction (direct_rule)
- 1.2 国内外研究现状及发展动态分析 -> S02_introduction (direct_rule)
- 1.4创新性及研究意义 -> S02_introduction (direct_rule)
- 主要参考文献 -> S07_back_matter_or_supplementary (direct_rule)

## Summary

- No memory_cards residual found in all 3 papers.
- New naming is consistently propagated in paragraph_index.json, document_tree.json, evidence_links.json.
- No legacy section directories remained after rebuild.
- content_path integrity and image_manifest-to-paragraph linking are healthy on all 3 samples.
- Remaining gaps are concentrated in front-matter/conclusion detection for some paper styles (notably 2025_sha and 2026_unknown in this run).

## Notes

This report is intentionally limited to small-scope regression.
No full-batch run and no OpenViking operations were performed.

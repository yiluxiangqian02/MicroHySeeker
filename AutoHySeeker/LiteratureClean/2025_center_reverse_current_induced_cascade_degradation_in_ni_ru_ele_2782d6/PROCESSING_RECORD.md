# LiteratureClean Processing Record

Paper ID: `2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Reverse‐Current Induced Cascade Degradation in Ni Ru Electrodes  Tracin_9f7209bf
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6
```

## Scope

This run processes one MinerU output folder into one LiteratureClean preprocessing package. It does not perform batch import, OpenViking ingestion, L0/L1 summary generation, vectorization, or UI integration.

## Processing Steps

1. Read MinerU `full.md`, `content_list_v2.json`, `layout.json`, source PDF path, and `images/`.
2. Generate a stable `paper_id` from year, first author, title slug, and DOI hash.
3. Parse figures and tables from Markdown and `content_list_v2.json`.
4. Clean `full.md` into `full_clean.md` by removing obvious publication noise, references list, publisher note, and raw affiliation/footer noise.
5. Split the paper into `macro section -> subheading group -> paragraph` and assign stable paragraph / figure / table evidence IDs.
6. Write `sections_by_heading/NNN-title-slug/heading.json`, `paragraphs.md`, and `paragraphs/PRAW-*.md`.
7. Copy figure assets into `figures/FIGxxx/` and table assets into `tables/TABxxx/`.
8. Generate root metadata and indexes: `metadata.json`, `document_tree.json`, `paragraph_index.json`, `evidence_links.json`, `image_manifest.json`, `table_manifest.json`, and `quality_report.json`.

## Output Summary

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Reverse‐Current Induced Cascade Degradation in Ni Ru Electrodes  Tracin_9f7209bf\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 17
- Used image count: 15
- Uncertain image count: 17
- Table directory count: 1

## Generated Main Files

- Clean full text: `full_clean.md`
- Metadata: `metadata.json`
- Document tree: `document_tree.json`
- Paragraph index: `paragraph_index.json`
- Evidence index: `evidence_links.json`
- Image manifest: `image_manifest.json`
- Table manifest: `table_manifest.json`
- Tag conflicts report: `tag_conflicts.json`
- Quality report: `quality_report.json`
- Heading root: `sections_by_heading/`
- Figures root: `figures/`
- Tables root: `tables/`

## Heading Directories Generated

- `001-front-matter`
- `002-abstract`
- `003-1-introduction`
- `004-2-1-degradation-assessment`
- `005-2-2-electrochemical-behavior-and-morphology-evolu`
- `006-2-3-solution-and-interface-evolutions`
- `007-2-4-degradation-mechanism-and-pathway-analysis`
- `008-2-5-sensitivity-on-the-rc-amplitude`
- `009-3-conclusions`
- `010-4-1-electrode-preparation`
- `011-4-2-ast-setup-and-electrochemical-measurement`
- `012-4-3-configuration-of-the-electrolyzer-validation`
- `013-4-4-physical-characterization`
- `014-4-5-dynamic-dissolution-deposition-and-osterwalde`
- `015-acknowledgements`
- `016-conflicts-of-interest`
- `017-data-availability-statement`

## Figures Generated

- FIG001: Fig. 1 | Schematic description of RC formation after the rapid shut-down operation. | images: 1
- FIG002: Fig. 2 | Applied input profile and electrode degradation | images: 3
- FIG003: Fig. 3 | Performance changes and morphology features in different degradation stage | images: 3
- FIG004: Fig. 4 | Metal ion concentration in testing solution, elemental composition and electrode cross-section elemental distribution... | images: 2
- FIG005: Fig. 5 | Degradation mechanism illustrated by scheme and simulation results | images: 3
- FIG006: Fig. 6 | Performance and morphology changes under different AST profiles | images: 3

## Tables Generated

- `TAB001`

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

# LiteratureClean Processing Record

Paper ID: `2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Relationship between the redox reactions on a bipolar plate and reverse_9bed6a7a
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Relationship between the redox reactions on a bipolar plate and reverse_9bed6a7a\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2017_uchino_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 7
- Used image count: 11
- Uncertain image count: 15
- Table directory count: 0

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

- `001-relationship-between-the-redox-reactions-on-a-bipolar-plate-and`
- `002-introduction`
- `003-experiment-method-and-analytical-model`
- `004-experiment-method`
- `005-potential-profile-model`
- `006-results-and-discussion`
- `007-conclusions`

## Figures Generated

- FIG001: Fig. 1 | Schematic drawing of the experimental system | images: 1
- FIG002: Fig. 2 | One-dimensional potential profile of a bipolar electrolyzer after electrolysis without (a) and with (b) ionic conduct... | images: 2
- FIG003: Fig. 3 | Simplified experimental system (a) and model of the equivalent circuit of the experimental system (b) | images: 2
- FIG004: Fig. 4 | Relationship between loading current density and cell voltages: $U _ { 1 }$ (circles) and $U _ { 2 }$ (triangles) | images: 2
- FIG005: Fig. 5 | High-frequency intercept on real axis in Cole-Cole plot of the cells at 1.8 V (circles), 2.0 V (triangles), and 2.3 V... | images: 1
- FIG006: Fig. 6 | Reverse current of measured (solid line) and calculated (dashed line) with Eq | images: 1
- FIG007: Fig. 7 | Electric charge of the reverse current as a function of the current density during 60 min electrolysis | images: 1
- FIG008: Fig. 8 | Diagram of the $E ^ { \circ } \mathbf { s }$ of the candidate reactions of the electromotive force: $U _ { 0 }$ is th... | images: 1
- FIG009: Fig. 9 | One-dimensional profile of a bipolar electrolyzer when the reverse current stops | images: 2

## Tables Generated

- No table directories generated.

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

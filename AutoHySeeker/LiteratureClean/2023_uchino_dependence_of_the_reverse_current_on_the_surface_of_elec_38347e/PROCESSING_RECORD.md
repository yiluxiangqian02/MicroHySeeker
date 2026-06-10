# LiteratureClean Processing Record

Paper ID: `2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Dependence of the reverse current on the surface of electrode placed on_9ebe8347
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Dependence of the reverse current on the surface of electrode placed on_9ebe8347\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 5
- Used image count: 5
- Uncertain image count: 14
- Table directory count: 5

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

- `001-dependence-of-the-reverse-current-on-the-surface-of-electrode-pl`
- `002-1-introduction`
- `003-2-experimental`
- `004-3-results-and-discussion`
- `005-4-conclusions`

## Figures Generated

- FIG004: Fig. 4 | Measured cell voltage as a function of logarithm of Figure 4.current in low current density region. | images: 1
- FIG005: Fig. 5 | Leak current (circles) and the ratio to applied current Figure 5.(triangle) (A) and cell voltages for U _ { 1 } (circ... | images: 1
- FIG006: Fig. 6 | Reverse current of non-replacement (solid line) and Figure 6.replacement (dashed line) (A) and cell voltages (B) as a... | images: 1
- FIG007: Fig. 7 | Electric charge of the reverse current as a function of Figure 7.electrolysis duration time; non-replacement (circles... | images: 1
- FIG008: Fig. 8 | (B) Relationship of measured potential and redox couples at Figure 8.the initial, middle and final time for the non-r... | images: 1

## Tables Generated

- `TAB001`
- `TAB002`
- `TAB003`
- `TAB004`
- `TAB005`

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

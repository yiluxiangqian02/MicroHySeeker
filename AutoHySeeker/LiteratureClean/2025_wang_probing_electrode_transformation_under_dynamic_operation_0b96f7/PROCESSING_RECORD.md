# LiteratureClean Processing Record

Paper ID: `2025_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Probing Electrode Transformation under Dynamic Operation for Alkaline W_4ff0d6af
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Probing Electrode Transformation under Dynamic Operation for Alkaline W_4ff0d6af\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 5
- Used image count: 13
- Uncertain image count: 28
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

- `001-probing-electrode-transformation-under-dynamic-operation-for-alk`
- `002-1-introduction`
- `003-2-results-and-discussion`
- `004-3-conclusion`
- `005-4-experimental-section`

## Figures Generated

- FIG001: Fig. 1 | Schematic illustration of the current flow during normal and shutdown operation of AWEs | images: 1
- FIG002: Fig. 2 | Three electrode MEA setup and electrochemical behaviors of Ni electrodes under reverse current process | images: 2
- FIG003: Fig. 3 | Full cell electrochemical performance under repetitive startup/shutdown process for AWEs | images: 3
- FIG004: Fig. 4 | Tracking anode and cathode electrochemical performance for OER and HER, respectively during RC ASTs | images: 2
- FIG005: Fig. 5 | Anode Ni electrode transformation mechanism under continuous RC AST cycles | images: 2
- FIG006: Fig. 6 | Cathode Ni electrode degradation mechanism under continuous RC AST cycles | images: 3

## Tables Generated

- No table directories generated.

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

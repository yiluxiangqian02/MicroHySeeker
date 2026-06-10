# LiteratureClean Processing Record

Paper ID: `2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Effects of operation and shutdown parameters and electrode materials on_99bf4606
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Effects of operation and shutdown parameters and electrode materials on_99bf4606\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 5
- Used image count: 18
- Uncertain image count: 13
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

- `001-effects-of-operation-and-shutdown-parameters-and-electrode-mater`
- `002-1-introduction`
- `003-2-experimental`
- `004-3-results-and-discussion`
- `005-4-conclusion`

## Figures Generated

- FIG001: Fig. 1 | Schematic diagram of the utilized 4-cell stack bipolar plate alkaline water electrolysis system. | images: 1
- FIG002: Fig. 2 | a) A schematic diagram of the 4-cell stack alkaline water electrolyzer and the attached manifold assembly | images: 2
- FIG003: Fig. 3 | For the two set of electrodes AN-1//CA-1 and AN-2//CA-1, the cell voltage against the current density of a single-cel... | images: 2
- FIG004: Fig. 4 | For the electrode system with AN-2 anodes after electrolysis under condition of $0.6\mathrm{Acm}^{-2}$ at $30^{\circ}... | images: 3
- FIG005: Fig. 5 | For experiments conducted with and without $\mathbf{N}_2$ bubbling a) The average reverse current of BP-1 and BP-3 ve... | images: 2
- FIG006: Fig. 6 | For experiments conducted with (Pumps ON) and without (Pumps OFF) electrolyte circulation a) The average reverse curr... | images: 2
- FIG007: Fig. 7 | For water electrolysis condition of $0.4\mathrm{Acm}^{-2}$ at $30^{\circ}\mathrm{C},$ $0.6\mathrm{Acm}^{-2}$ at $30^{... | images: 3
- FIG008: Fig. 8 | For the electrode systems with AN-1 and AN-2 anodes operated under water electrolysis condition of $0.6\mathrm{Acm}^{... | images: 3

## Tables Generated

- No table directories generated.

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

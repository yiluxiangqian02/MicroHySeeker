# LiteratureClean Processing Record

Paper ID: `2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\heterointerface-enabled-anti-reverse-current-electrodes-for-alkaline-wa_4250254b
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\heterointerface-enabled-anti-reverse-current-electrodes-for-alkaline-wa_4250254b\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 13
- Used image count: 17
- Uncertain image count: 33
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

- `001-front-matter`
- `002-1-introduction`
- `003-2-results-and-discussion`
- `004-3-conclusions`
- `005-4-experimental-section`
- `006-supporting-information`
- `007-corresponding-authors`
- `008-authors`
- `009-author-contributions`
- `010-notes`
- `011-acknowledgments`
- `012-references`
- `013-note-added-after-asap-publication`

## Figures Generated

- FIG001: Fig. 1 | Reverse current effect and electrode degradation under startup/shutdown cycles | images: 3
- FIG002: Fig. 2 | Chemical stability and in situ reconstruction of $\mathrm{Ni}_3\mathrm{S}_2$ (a) IL-TEM images of $\mathrm{Ni@Ni_3S_2... | images: 3
- FIG003: Fig. 3 | Structure and stability characterization of $\mathrm{Ni}_3\mathrm{S}_2 / \mathrm{NM}$ I | images: 3
- FIG004: Fig. 4 | ADT and structural stability characterization of $\mathrm{Ni}_3\mathrm{S}_2 / \mathrm{NM}$ I | images: 2
- FIG005: Fig. 5 | Theoretical insights into structural stability | images: 3
- FIG006: Fig. 6 | Alkaline water electrolyzer performance | images: 3

## Tables Generated

- No table directories generated.

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

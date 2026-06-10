# LiteratureClean Processing Record

Paper ID: `2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\97258947-9fe4-41e1-af38-7ebc8f559868_origin
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\97258947-9fe4-41e1-af38-7ebc8f559868_origin\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 8
- Used image count: 13
- Uncertain image count: 49
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

- `001-10-000-h-stable-intermittent-alkaline-seawater-electrolysis`
- `002-cathode-oxidation-during-start-shutdown-water-splitting-cycles`
- `003-activity-and-stability-of-nicop-mathbf-c-r-2-0-3-cathode-in-inte`
- `004-reaction-mechanism`
- `005-theoretical-insight`
- `006-discussion`
- `007-methods`
- `008-computational-methods`

## Figures Generated

- FIG001: Fig. 1 | Cathode oxidation and corrosion under start–shutdown water electrolysis cycles | images: 3
- FIG002: Fig. 2 | HER performance and intermittent electrolysis stability | images: 3
- FIG003: Fig. 3 | Reaction mechanism | images: 3
- FIG004: Fig. 4 | Structural evolution during intermittent electrolysis | images: 2
- FIG005: Fig. 5 | Theoretical calculation | images: 2

## Tables Generated

- No table directories generated.

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

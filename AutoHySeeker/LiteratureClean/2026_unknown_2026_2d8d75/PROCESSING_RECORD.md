# LiteratureClean Processing Record

Paper ID: `2026_unknown_2026_2d8d75`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\76ec4365-1c6d-4a2f-ae16-12acf100a2df_origin
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2026_unknown_2026_2d8d75
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\76ec4365-1c6d-4a2f-ae16-12acf100a2df_origin\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2026_unknown_2026_2d8d75\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2026_unknown_2026_2d8d75\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 41
- Used image count: 5
- Uncertain image count: 93
- Table directory count: 3

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
- `002-1-1`
- `003-1-2`
- `004-1-2-1`
- `005-1-2-2`
- `006-1-2-3`
- `007-1-3`
- `008-1-4`
- `009-untitled`
- `010-untitled`
- `011-2-1`
- `012-2-2`
- `013-untitled`
- `014-untitled`
- `015-untitled`
- `016-untitled`
- `017-nixmy-her`
- `018-untitled`
- `019-2-4`
- `020-untitled`
- `021-untitled`
- `022-untitled`
- `023-2-5`
- `024-2-6`
- `025-iii`
- `026-iv-dft`
- `027-untitled`
- `028-untitled`
- `029-2-7`
- `030-untitled`
- `031-untitled`
- `032-untitled`
- `033-2-8`
- `034-untitled`
- `035-3-1`
- `036-1`
- `037-2`
- `038-3-ni`
- `039-4`
- `040-5`
- `041-3-2`

## Figures Generated

- FIG001: Fig. 1 | -1（a-b）双极板式ALK 电解槽结构示意图; （c） 反向电流失效示意[7] | images: 3
- FIG002: Fig. 2 | -1 研究内容、关键科学问题及研究目标的关系 | images: 1
- FIG003: Fig. 3 | -1 阴极催化剂开发及动力学优化 | images: 1

## Tables Generated

- `TAB001`
- `TAB002`
- `TAB003`

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

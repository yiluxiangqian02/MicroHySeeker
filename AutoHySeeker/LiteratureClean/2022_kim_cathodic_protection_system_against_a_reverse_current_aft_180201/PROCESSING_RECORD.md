# LiteratureClean Processing Record

Paper ID: `2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\cathodic-protection-system-against-a-reverse-current-after-shut-down-in_9f543e97
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\cathodic-protection-system-against-a-reverse-current-after-shut-down-in_9f543e97\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 9
- Used image count: 19
- Uncertain image count: 10
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

- `001-cathodic-protection-system-against-a-reverse-current-after-shutd`
- `002-introduction`
- `003-results-and-discussion`
- `004-conclusions`
- `005-associated-content`
- `006-author-information`
- `007-acknowledgments`
- `008-references`
- `009-cas-biofinder-helps-you-find-your-next-breakthrough-faster`

## Figures Generated

- FIG001: Fig. 1 | Ni electrode degradation by reverse-current flow after shut-down of the alkaline electrolyzer | images: 3
- FIG002: Fig. 2 | Reverse-current simulation model using OCV measurement | images: 3
- FIG003: Fig. 3 | Cathodic protection system for the Ni cathode | images: 3
- FIG004: Fig. 4 | Electrochemical measurement of Ni with sacrificial anodes | images: 3
- FIG005: Fig. 5 | Ni 2p XPS spectra for (a) Ni before RC, (b) Ni after RC, and (c) Ni w/Pb after RC. | images: 3
- FIG006: Fig. 6 | Comparison of the RCSF; the RCSF for Ni and Ni w/M $(\mathrm{M} = \mathrm{Al}, \mathrm{Zn}, \mathrm{Pb},$ and Sn) ele... | images: 1
- FIG007: Fig. 7 | Effect of the Zn cathodic protection system on the performance of an AWE stack during repeated SU/SD | images: 3

## Tables Generated

- No table directories generated.

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

# LiteratureClean Processing Record

Paper ID: `2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9`

Source MinerU directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Reverse‐Current Tolerance for Hydrogen Evolution Reaction Activity of L_66c3dfa7
```

Clean output directory:

```text
D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9
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

- Raw MinerU images remain untouched in `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output\Reverse‐Current Tolerance for Hydrogen Evolution Reaction Activity of L_66c3dfa7\images`.
- Clean figure copies are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9\figures` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean\2024_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9\tables` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: 14
- Used image count: 15
- Uncertain image count: 8
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
- `003-2-1-degradation-tolerance-of-the-pb-ni-electrocatal`
- `004-2-2-origin-of-the-reverse-current-tolerance-and-imp`
- `005-2-3-material-characterization-of-rc-tolerant-pb-ni`
- `006-2-4-water-activation-effect-of-rc-tolerant-pb-ni-ca`
- `007-2-5-ligand-effect-in-rc-tolerant-pb-ni-catalyst-pro`
- `008-2-6-reverse-current-tolerance-of-the-pb-ni-catalyst`
- `009-3-conclusion`
- `010-supporting-information`
- `011-acknowledgements`
- `012-conflict-of-interest`
- `013-data-availability-statement`
- `014-keywords`

## Figures Generated

- FIG001: Fig. 1 | Ni electrode degradation by reverse-current flow after the shutdown of the alkaline electrolyzer | images: 2
- FIG002: Fig. 2 | Measurement of the Ni and Pb/Ni catalysts under RC conditions | images: 2
- FIG003: Fig. 3 | Origin of the improved HER activity of the $\mathrm{Pb / Ni}$ catalyst during the RC cycles | images: 3
- FIG004: Fig. 4 | Water activation Effect of RC tolerant Pb/Ni catalyst: improving water-dissociation ability | images: 3
- FIG005: Fig. 5 | Ligand Effect in RC tolerant Pb/Ni catalyst: promoting proton desorption | images: 3
- FIG006: Fig. 6 | Alkaline water-electrolyzer stack cell | images: 2

## Tables Generated

- No table directories generated.

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.

# Literature Import Summary — OpenViking

## Overview

This document describes how LiteratureClean papers are imported into OpenViking
and how to query them after import.

- **Source**: `AutoHySeeker/LiteratureClean/{paper_id}/`
- **Target base URI**: `viking://resources/literature/`
- **Config**: `OpenViking/.local_dev/ov.conf` (embedded local mode)
- **Import script**: `LiteratureClean/import_to_openviking.py`
- **Import log**: `LiteratureClean/openviking_import_log.json`

---

## Papers Available for Import (10 papers)

| paper_id | Figs | Tables | Status |
|----------|------|--------|--------|
| `2017_yosuke_relationship_between_the_redox_reactions_on_a_bipolar_pl_eb3da9` | 11 | 0 | ready |
| `2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201` | 19 | 0 | ready |
| `2023_a_effects_of_operation_and_shutdown_parameters_and_electro_86a3bb` | 18 | 0 | ready |
| `2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e` | 5 | 5 | ready |
| `2025_center_reverse_current_induced_cascade_degradation_in_ni_ru_ele_2782d6` | 15 | 1 | ready |
| `2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c` | 13 | 0 | ready |
| `2026_he_heterointerface_enabled_anti_reverse_current_electrodes_43767e` | 17 | 0 | ready |
| `unknown_year_jung_reverse_current_tolerance_for_hydrogen_evolution_reactio_4a4ad9` | 15 | 0 | ready |
| `unknown_year_peng_strategies_and_countermeasures_against_reverse_current_f_803838` | 25 | 0 | ready |
| `unknown_year_wang_probing_electrode_transformation_under_dynamic_operation_0b96f7` | 13 | 0 | ready |

**Not imported (permissions issue):**
- `2026_unknown_2026_2d8d75` — `[Errno 13] Permission denied` on MinerU images directory

---

## URI Structure

After import, each paper is addressable as:

```
viking://resources/literature/{paper_id}/
```

Sub-resources:
```
viking://resources/literature/{paper_id}/abstract.md          ← L0 paper entry
viking://resources/literature/{paper_id}/overview.md          ← L1 paper entry
viking://resources/literature/{paper_id}/full_clean.md        ← full text
viking://resources/literature/{paper_id}/structured.json      ← structured data
viking://resources/literature/{paper_id}/evidence_links.json  ← evidence index
viking://resources/literature/{paper_id}/figures/FIG001.jpg   ← figure
viking://resources/literature/{paper_id}/tables/TAB001.md     ← table
viking://resources/literature/{paper_id}/memory_cards/figures/FIG001/abstract.md
viking://resources/literature/{paper_id}/memory_cards/tables/TAB001/abstract.md
```

---

## File Structure Mapping

| LiteratureClean file | OpenViking file (after import) | Notes |
|---------------------|-------------------------------|-------|
| `.abstract.md` | `abstract.md` | Renamed: dotfiles skipped by OV scanner |
| `.overview.md` | `overview.md` | Renamed |
| `full_clean.md` | `full_clean.md` | As-is |
| `metadata.json` | `metadata.json` | As-is |
| `structured.json` | `structured.json` | As-is |
| `evidence_links.json` | `evidence_links.json` | As-is |
| `figures/FIG*.jpg` | `figures/FIG*.jpg` | As-is |
| `tables/TAB*.md` | `tables/TAB*.md` | As-is |
| `memory_cards/**/.abstract.md` | `memory_cards/**/abstract.md` | Renamed |
| `memory_cards/**/.overview.md` | `memory_cards/**/overview.md` | Renamed |
| `memory_cards/**/fig.card.md` | `memory_cards/**/fig.card.md` | As-is |
| `memory_cards/**/table.card.md` | `memory_cards/**/table.card.md` | As-is |
| `image_manifest.json` | *(not imported)* | Internal use only |
| `table_manifest.json` | *(not imported)* | Internal use only |
| `PROCESSING_RECORD.md` | *(not imported)* | Internal use only |

---

## How to Import

### Prerequisites

1. Fill in `OpenViking/.local_dev/ov.conf` with your embedding model API key:
   ```json
   {
     "embedding": {
       "dense": {
         "model": "your-model",
         "api_key": "your-key",
         "api_base": "https://your-api-endpoint/v1",
         "dimension": 1024,
         "provider": "openai"
       }
     }
   }
   ```

2. Ensure the `openviking` package is installed:
   ```powershell
   .venv\Scripts\pip install openviking
   ```

### Run Import

```powershell
# In AutoHySeeker/
.venv\Scripts\python LiteratureClean\import_to_openviking.py --list      # preview
.venv\Scripts\python LiteratureClean\import_to_openviking.py --dry-run   # dry run
.venv\Scripts\python LiteratureClean\import_to_openviking.py             # import all
.venv\Scripts\python LiteratureClean\import_to_openviking.py --paper-id 2023_uchino_...
.venv\Scripts\python LiteratureClean\import_to_openviking.py --overwrite # re-import
```

---

## How to Query

```python
import os
from pathlib import Path
os.environ["OPENVIKING_CONFIG_FILE"] = str(
    Path("AutoHySeeker/OpenViking/.local_dev/ov.conf").resolve()
)
from openviking.sync_client import SyncOpenViking

client = SyncOpenViking(path="AutoHySeeker/data/openviking")
client.initialize()

# Search across all imported literature
results = client.find(
    "reverse current degradation mechanism",
    target_uri="viking://resources/literature/",
    limit=10
)

# Get L0 abstract for one paper
abstract = client.abstract(
    "viking://resources/literature/2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e/"
)

# Get L1 overview
overview = client.overview(
    "viking://resources/literature/2023_uchino_dependence_of_the_reverse_current_on_the_surface_of_elec_38347e/"
)

# Semantic search scoped to one paper
results = client.search(
    "cathodic protection",
    target_uri="viking://resources/literature/2022_kim_cathodic_protection_system_against_a_reverse_current_aft_180201/"
)
```

---

## Known Issues

1. **Dotfile renaming**: OpenViking skips `.abstract.md` / `.overview.md` during directory
   scan. The import script handles this by copying to a temp dir with renamed files.

2. **`2026_unknown_2026_2d8d75` skipped**: Windows permission error on the MinerU images
   directory during cleaning. Excluded from import until resolved.

3. **Embedding model required**: `ov.conf` currently has placeholder values for
   `model`, `api_key`, `api_base`. Fill these in before running a real import.

---

## Related Files

- `LiteratureClean/import_to_openviking.py` — import script
- `LiteratureClean/LITERATURE_CLEANING_GUIDE.md` — full pipeline spec
- `OpenViking/.local_dev/ov.conf` — OpenViking config (fill in API key)
- `LiteratureClean/openviking_import_log.json` — import log (created after first run)
- `LiteratureClean/batch_run_log.json` — batch cleaning log

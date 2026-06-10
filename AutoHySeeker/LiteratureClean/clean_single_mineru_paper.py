"""Build one LiteratureClean package from one MinerU output directory.

This is intentionally a single-paper, semi-automatic cleaner. It does not scan
batch folders, import into OpenViking, or touch the AutoHySeeker UI.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_module
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None


DEFAULT_MINERU_DIR = Path(
    r"D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\MinerU\output"
    r"\10,000-h-stable intermittent alkaline seawater electrolysis"
)
DEFAULT_CLEAN_ROOT = Path(
    r"D:\AI4S\MicroHySeeker\MicroHySeeker\AutoHySeeker\LiteratureClean"
)


@dataclass
class Evidence:
    evidence_id: str
    kind: str
    title: str
    source_line_start: int | None
    source_line_end: int | None
    source_excerpt: str
    page_estimate: int | None = None
    related_figures: list[str] = field(default_factory=list)
    related_tables: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class Figure:
    figure_id: str
    figure_number: str
    title: str
    caption: str
    source_line_start: int
    raw_images: list[str]
    clean_images: list[str] = field(default_factory=list)
    evidence_id: str = ""


@dataclass
class Table:
    table_id: str
    table_number: str
    title: str
    caption: str
    html_content: str          # raw HTML from MinerU (may be empty)
    raw_images: list[str]      # rendered table image(s) from MinerU
    source_line_start: int = 0
    evidence_id: str = ""


KEY_EVIDENCE_PATTERNS: list[dict[str, Any]] = [
    {
        "id": "EVID001",
        "title": "Intermittent seawater electrolysis causes cathode degradation",
        "contains": ["unveil dynamic evolution and degradation", "intermittent electrolysis"],
        "tags": ["problem", "intermittent_electrolysis", "cathode_degradation"],
    },
    {
        "id": "EVID002",
        "title": "NiCoP-Cr2O3 forms phosphate passivation layer",
        "contains": ["phosphate passivation layer", "NiCoP"],
        "tags": ["material", "passivation_layer", "NiCoP-Cr2O3"],
    },
    {
        "id": "EVID003",
        "title": "10,000 h intermittent alkaline seawater electrolysis stability",
        "contains": ["10,000", "0 . 5", "khr"],
        "tags": ["metric", "stability", "seawater_electrolysis"],
    },
    {
        "id": "EVID004",
        "title": "Shutdown causes cathodic discharge and oxidative damage",
        "contains": ["cathode voltage sharply reversed", "1.30"],
        "tags": ["mechanism", "shutdown", "oxidation"],
    },
    {
        "id": "EVID005",
        "title": "Catalyst design uses phosphorus and Cr2O3 to resist oxidation",
        "contains": ["Phosphorus has a wide range of oxidation states", "passivation layer"],
        "tags": ["design_strategy", "phosphorus", "Cr2O3"],
    },
    {
        "id": "EVID006",
        "title": "AEM electrolyser reaches high current density with low cell voltage",
        "contains": ["AEM electrolyser", "1.74 and 1.99"],
        "tags": ["AEM", "cell_voltage", "metric"],
    },
    {
        "id": "EVID007",
        "title": "NiCoP-Cr2O3 requires 275 mV overpotential at 4 A cm-2",
        "contains": ["overpotential of only", "4 A cm"],
        "tags": ["HER", "overpotential", "metric"],
    },
    {
        "id": "EVID008",
        "title": "Full cell runs 10,000 h at 0.5 A cm-2 in alkaline seawater",
        "contains": ["stably operate", "10,000", "0 . 5"],
        "tags": ["stability", "condition", "full_cell"],
    },
    {
        "id": "EVID009",
        "title": "High-frequency and high-current intermittent operation",
        "contains": ["10-min start", "4,500"],
        "tags": ["condition", "high_frequency", "stability"],
    },
    {
        "id": "EVID010",
        "title": "TOF-SIMS and XPS reveal stratified passivation",
        "contains": ["after a 24-h shutdown period", "phosphate layer"],
        "tags": ["mechanism", "TOF-SIMS", "XPS"],
    },
    {
        "id": "EVID011",
        "title": "Operando Raman shows dynamic phosphate recovery",
        "contains": ["operando Raman", "dynamic recovery"],
        "tags": ["mechanism", "operando_Raman", "phosphate"],
    },
    {
        "id": "EVID012",
        "title": "HAADF-STEM shows structural evolution after shutdown",
        "contains": ["HAADF-STEM", "passivation layers"],
        "tags": ["characterization", "HAADF-STEM", "passivation"],
    },
    {
        "id": "EVID013",
        "title": "DFT explains oxygen migration barriers through passivation layers",
        "contains": ["energy barrier", "3.41"],
        "tags": ["DFT", "oxygen_migration", "mechanism"],
    },
    {
        "id": "EVID014",
        "title": "Discussion states passivation strategy mitigates shutdown deactivation",
        "contains": ["deactivation of cathode during shutdown periods", "greatly attenuated"],
        "tags": ["claim", "discussion", "passivation_strategy"],
    },
]


CLAIMS = [
    {
        "id": "CLAIM001",
        "title": "Intermittent operation creates a previously overlooked cathode problem.",
        "summary": (
            "The paper claims that renewable-electricity-driven start-shutdown cycles "
            "cause cathodic discharge, oxidation, halide adsorption, and corrosion at the HER cathode."
        ),
        "evidence_ids": ["EVID001", "EVID004", "EVID_FIG001"],
        "tags": ["claim", "intermittent_electrolysis", "cathode_degradation"],
        # --- L1 enrichment fields ---
        "claim_type": "problem identification / motivation",
        "related_figures": ["FIG001"],
        "related_tables": [],
        "source_section": "Introduction / Abstract",
        "page_estimate": "estimated (p.1\u20132)",
        "structured_field_path": "structured.json > key_claims[0]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID001]` or `[EVID: EVID004]`",
        "manual_review_notes": (
            "This claim is the paper\u2019s core motivation. "
            "Verify whether the cathodic discharge mechanism is quantified or only qualitatively claimed. "
            "Halide adsorption evidence source (IC? XPS?) needs cross-check."
        ),
    },
    {
        "id": "CLAIM002",
        "title": "NiCoP-Cr2O3 protects the cathode through an in situ passivation layer.",
        "summary": (
            "The proposed NiCoP-Cr2O3 cathode forms phosphate/oxide passivation that protects active "
            "metal sites during shutdown and can recover under HER operation."
        ),
        "evidence_ids": ["EVID002", "EVID005", "EVID010", "EVID011", "EVID012"],
        "tags": ["claim", "NiCoP-Cr2O3", "passivation_layer"],
        # --- L1 enrichment fields ---
        "claim_type": "solution / material design claim",
        "related_figures": ["FIG003", "FIG004"],
        "related_tables": [],
        "source_section": "Abstract / Results \u2014 passivation characterization",
        "page_estimate": "estimated (p.1\u20135)",
        "structured_field_path": "structured.json > key_claims[1]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID002]` or `[EVID: EVID010]`",
        "manual_review_notes": (
            "Passivation layer reversibility (recovery under HER) needs quantitative support. "
            "Whether Cr2O3 is pre-formed or in situ is critical \u2014 verify in text. "
            "XPS/TOF-SIMS data interpretation needs manual review."
        ),
    },
    {
        "id": "CLAIM003",
        "title": "The catalyst sustains long-term intermittent alkaline seawater electrolysis.",
        "summary": (
            "The optimized electrodes withstand 10,000 h operation at 0.5 A cm-2 in alkaline seawater "
            "with low voltage increase, and also endure higher-current or higher-frequency cycling."
        ),
        "evidence_ids": ["EVID003", "EVID008", "EVID009", "EVID_FIG002"],
        "tags": ["claim", "stability", "alkaline_seawater"],
        # --- L1 enrichment fields ---
        "claim_type": "performance / stability claim",
        "related_figures": ["FIG002"],
        "related_tables": [],
        "source_section": "Abstract / Results \u2014 stability tests",
        "page_estimate": "estimated (p.1\u20134)",
        "structured_field_path": "structured.json > key_claims[2]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID003]` or `[EVID: EVID008]`",
        "manual_review_notes": (
            "10,000 h is a headline claim \u2014 verify exact figure in main text vs SI. "
            "Voltage increase rate must be cross-checked. "
            "Whether electrode composition changed post-10,000 h was measured needs confirmation."
        ),
    },
    {
        "id": "CLAIM004",
        "title": "Phosphate formation suppresses chloride adsorption during shutdown.",
        "summary": (
            "The paper argues that phosphate species generated during shutdown repel chloride ions and "
            "thereby reduce seawater-induced poisoning/corrosion at the cathode."
        ),
        "evidence_ids": ["EVID011", "EVID013"],
        "tags": ["claim", "chloride_resistance", "phosphate"],
        # --- L1 enrichment fields ---
        "claim_type": "mechanistic claim",
        "related_figures": ["FIG005"],
        "related_tables": [],
        "source_section": "Results/Discussion \u2014 chloride resistance mechanism",
        "page_estimate": "estimated (p.5\u20136)",
        "structured_field_path": "structured.json > key_claims[3]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID011]` or `[EVID: EVID013]`",
        "manual_review_notes": (
            "Chloride repulsion is supported by DFT but needs experimental IC or direct XPS Cl\u207b detection. "
            "Whether this claim is proven experimentally or is primarily computational needs disambiguation."
        ),
    },
]


METRICS = [
    {
        "id": "METRIC001",
        "title": "10,000 h at 0.5 A cm-2",
        "summary": "Full cell intermittent alkaline seawater electrolysis at 0.5 A cm-2 for 10,000 h.",
        "value": "10,000 h; 0.5 A cm-2; voltage increase rate about 0.5% khr-1",
        "evidence_ids": ["EVID003", "EVID008"],
        "tags": ["metric", "stability", "0.5_A_cm-2"],
        # --- L1 enrichment fields ---
        "unit": "hours; A cm\u207b\u00b2; % khr\u207b\u00b9",
        "measurement_method": "chronopotentiometry / cell voltage monitoring",
        "condition_ids": ["CONDITION001"],
        "related_figures": ["FIG002"],
        "related_tables": [],
        "source_section": "Results \u2014 long-term stability test",
        "page_estimate": "estimated (p.3\u20134)",
        "structured_field_path": "structured.json > results > metrics[0]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID003]` or `[EVID: EVID008]`",
        "manual_review_notes": (
            "Voltage increase rate ~0.5% khr\u207b\u00b9 needs exact citation in text. "
            "Verify whether stated as end-of-test or average rate. "
            "Confirm electrolyte composition (1 M NaOH vs 20 wt% NaOH) used for this specific run."
        ),
    },
    {
        "id": "METRIC002",
        "title": "4,500 h high-frequency cycling at 1 A cm-2",
        "summary": "10-min start-shutdown cycles at 1 A cm-2 in alkaline seawater for 4,500 h.",
        "value": "4,500 h; 1 A cm-2; 10-min start-shutdown cycle",
        "evidence_ids": ["EVID009"],
        "tags": ["metric", "high_frequency", "1_A_cm-2"],
        # --- L1 enrichment fields ---
        "unit": "hours; A cm\u207b\u00b2; minutes per cycle",
        "measurement_method": "chronopotentiometry with programmed start-shutdown cycling",
        "condition_ids": ["CONDITION002"],
        "related_figures": ["FIG002"],
        "related_tables": [],
        "source_section": "Results \u2014 high-frequency cycling test",
        "page_estimate": "estimated (p.4\u20135)",
        "structured_field_path": "structured.json > results > metrics[1]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID009]`",
        "manual_review_notes": (
            "Voltage degradation rate for this condition not explicitly extracted. "
            "Cross-check 4,500 h and 10-min cycle claim in main text. "
            "Electrode area (geometric vs BET) not specified."
        ),
    },
    {
        "id": "METRIC003",
        "title": "275 mV overpotential at 4 A cm-2",
        "summary": "HER overpotential for NiCoP-Cr2O3 in 20 wt% NaOH + seawater.",
        "value": "275 mV at 4 A cm-2",
        "evidence_ids": ["EVID007", "EVID_FIG002"],
        "tags": ["metric", "HER", "overpotential"],
        # --- L1 enrichment fields ---
        "unit": "mV overpotential; A cm\u207b\u00b2",
        "measurement_method": "linear sweep voltammetry (LSV) in three-electrode setup",
        "condition_ids": [],
        "related_figures": ["FIG002"],
        "related_tables": [],
        "source_section": "Results \u2014 HER half-cell performance",
        "page_estimate": "estimated (p.2\u20133)",
        "structured_field_path": "structured.json > results > metrics[2]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID007]`",
        "manual_review_notes": (
            "Electrolyte for this measurement is 20 wt% NaOH + seawater \u2014 different from full-cell 1 M NaOH. "
            "iR-correction status not confirmed. "
            "Reference electrode type not extracted."
        ),
    },
    {
        "id": "METRIC004",
        "title": "AEM electrolyser voltage at 1 and 4 A cm-2",
        "summary": "AEM electrolyser reaches 1 and 4 A cm-2 in 1 M KOH at 80 C.",
        "value": "1.74 V at 1 A cm-2; 1.99 V at 4 A cm-2",
        "evidence_ids": ["EVID006"],
        "tags": ["metric", "AEM", "cell_voltage"],
        # --- L1 enrichment fields ---
        "unit": "V (cell voltage); A cm\u207b\u00b2",
        "measurement_method": "AEM electrolyser polarisation curve",
        "condition_ids": ["CONDITION003"],
        "related_figures": ["FIG002"],
        "related_tables": [],
        "source_section": "Results \u2014 AEM electrolyser validation",
        "page_estimate": "estimated (p.4\u20135)",
        "structured_field_path": "structured.json > results > metrics[3]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID006]`",
        "manual_review_notes": (
            "Temperature stated as 80\u00b0C \u2014 verify in Methods. "
            "AEM membrane brand/type not extracted. "
            "Faradaic efficiency not stated."
        ),
    },
    {
        "id": "METRIC005",
        "title": "Oxygen migration energy barriers",
        "summary": "DFT-calculated barriers explain passivation blocking oxygen migration.",
        "value": "0.31 eV; 3.41 eV; 1.79 eV",
        "evidence_ids": ["EVID013", "EVID_FIG005"],
        "tags": ["metric", "DFT", "oxygen_migration"],
        # --- L1 enrichment fields ---
        "unit": "eV (energy barrier)",
        "measurement_method": "DFT + CI-NEB calculations (VASP)",
        "condition_ids": [],
        "related_figures": ["FIG005"],
        "related_tables": [],
        "source_section": "Results/Discussion \u2014 DFT mechanism analysis",
        "page_estimate": "estimated (p.5\u20136)",
        "structured_field_path": "structured.json > results > metrics[4]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID013]`",
        "manual_review_notes": (
            "Three barrier values (0.31, 3.41, 1.79 eV) correspond to different migration paths \u2014 "
            "needs manual verification of which path each value belongs to. "
            "DFT functional (GGA-PBE?) and U-correction not confirmed."
        ),
    },
]


CONDITIONS = [
    {
        "id": "CONDITION001",
        "title": "Baseline intermittent alkaline seawater operation",
        "summary": "Full water electrolysis cell operated in 1 M NaOH + seawater with 12-h start-shutdown intervals.",
        "evidence_ids": ["EVID008", "EVID_FIG002"],
        "tags": ["condition", "1M_NaOH_seawater", "12h_cycle"],
        # --- L1 enrichment fields ---
        "parameters": {
            "electrolyte": "1 M NaOH + seawater",
            "current_density": "0.5 A cm\u207b\u00b2",
            "cycle": "12-h start-shutdown intervals",
            "duration": "10,000 h",
            "temperature": "not found",
            "pressure": "not found",
        },
        "system": "full water electrolysis cell (two-electrode)",
        "supports_result": "10,000 h intermittent stability at 0.5 A cm\u207b\u00b2 with ~0.5% khr\u207b\u00b9 voltage increase (METRIC001)",
        "related_figures": ["FIG002"],
        "related_tables": [],
        "source_section": "Results \u2014 long-term stability test",
        "page_estimate": "estimated (p.3\u20134 based on MinerU grouping)",
        "structured_field_path": "structured.json > experiments_or_cases > items[0]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID008]`",
        "manual_review_notes": (
            "12-h cycle interval needs confirmation against Methods or SI. "
            "Electrolyte temperature not stated in main text. "
            "Verify whether 0.5 A cm\u207b\u00b2 applies to projected or geometric area."
        ),
    },
    {
        "id": "CONDITION002",
        "title": "High-frequency intermittent operation",
        "summary": "1 A cm-2 operation in 1 M NaOH + seawater with 10-min start-shutdown cycles.",
        "evidence_ids": ["EVID009", "EVID_FIG002"],
        "tags": ["condition", "10min_cycle", "1_A_cm-2"],
        # --- L1 enrichment fields ---
        "parameters": {
            "electrolyte": "1 M NaOH + seawater",
            "current_density": "1 A cm\u207b\u00b2",
            "cycle": "10-min start-shutdown intervals",
            "duration": "4,500 h",
            "temperature": "not found",
            "pressure": "not found",
        },
        "system": "full water electrolysis cell (two-electrode)",
        "supports_result": "4,500 h high-frequency cycling stability at 1 A cm\u207b\u00b2 (METRIC002)",
        "related_figures": ["FIG002"],
        "related_tables": [],
        "source_section": "Results \u2014 high-frequency cycling test",
        "page_estimate": "estimated (p.3\u20135 based on MinerU grouping)",
        "structured_field_path": "structured.json > experiments_or_cases > items[1]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID009]`",
        "manual_review_notes": (
            "10-min cycle and 4,500 h duration need cross-check with main text. "
            "Estimated total cycles ~27,000 (4,500 h \u00d7 6 cycles/h) \u2014 verify. "
            "Voltage degradation rate under this condition not extracted; needs manual review."
        ),
    },
    {
        "id": "CONDITION003",
        "title": "AEM electrolyser configuration",
        "summary": "AEM electrolyser uses NiCoP-Cr2O3 cathode with NiFe-LDH/NiFeP-type anodes under alkaline electrolyte.",
        "evidence_ids": ["EVID006", "EVID009"],
        "tags": ["condition", "AEM", "electrolyser"],
        # --- L1 enrichment fields ---
        "parameters": {
            "electrolyte": "1 M KOH",
            "current_density": "1 A cm\u207b\u00b2 and 4 A cm\u207b\u00b2",
            "cycle": "not found",
            "duration": "not found",
            "temperature": "80\u00b0C",
            "pressure": "not found",
        },
        "system": "AEM (Anion Exchange Membrane) electrolyser",
        "supports_result": "Cell voltages 1.74 V at 1 A cm\u207b\u00b2 and 1.99 V at 4 A cm\u207b\u00b2 (METRIC004)",
        "related_figures": ["FIG002"],
        "related_tables": [],
        "source_section": "Results \u2014 AEM electrolyser validation",
        "page_estimate": "estimated (p.4\u20135 based on MinerU grouping)",
        "structured_field_path": "structured.json > experiments_or_cases > items[2]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID006]`",
        "manual_review_notes": (
            "AEM membrane type not specified in main text. "
            "Temperature 80\u00b0C needs verification against Methods. "
            "Anode material (NiFe-LDH/NiFeP) needs cross-check."
        ),
    },
]


MECHANISMS = [
    {
        "id": "MECHANISM001",
        "title": "Shutdown-induced stratified passivation",
        "summary": (
            "During shutdown, Co and P redistribute and oxidize to form layered CoO/Cr2O3, phosphate-rich, "
            "and Ni-rich regions that shield Ni active sites."
        ),
        "evidence_ids": ["EVID010", "EVID012", "EVID_FIG003", "EVID_FIG004"],
        "tags": ["mechanism", "passivation", "shutdown"],
        # --- L1 enrichment fields ---
        "description_detail": (
            "Upon shutdown, the NiCoP-Cr2O3 cathode undergoes oxidative transformation: "
            "Co and P species migrate to form a stratified passivation shell consisting of "
            "(1) an outer CoO/Cr2O3 layer, (2) a phosphate-rich intermediate layer, and "
            "(3) a Ni-rich inner region. This stratification protects Ni active sites from "
            "oxidation and halide attack during the open-circuit/idle phase."
        ),
        "key_species": ["CoO", "Cr2O3", "phosphate", "Ni"],
        "related_figures": ["FIG003", "FIG004"],
        "related_tables": [],
        "characterization_methods": ["TOF-SIMS", "XPS", "HAADF-STEM"],
        "source_section": "Results/Discussion \u2014 shutdown passivation mechanism",
        "page_estimate": "estimated (p.4\u20135)",
        "structured_field_path": "structured.json > domain_specific > electrocatalysis > protection_strategies[0]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID010]` or `[EVID: EVID012]`",
        "manual_review_notes": (
            "Layer ordering (outer CoO/Cr2O3 vs inner Ni-rich) needs verification against TOF-SIMS depth profile. "
            "Thickness of each sublayer not extracted. "
            "Whether this passivation is fully reversible upon restart needs confirmation."
        ),
    },
    {
        "id": "MECHANISM002",
        "title": "Dynamic phosphate recovery and chloride resistance",
        "summary": (
            "P/phosphate undergoes reversible redox during start-shutdown cycles; phosphate species help repel "
            "chloride ions and reduce poisoning/corrosion."
        ),
        "evidence_ids": ["EVID011", "EVID013", "EVID_FIG005"],
        "tags": ["mechanism", "phosphate", "chloride_resistance"],
        # --- L1 enrichment fields ---
        "description_detail": (
            "During the start phase (HER operation), phosphate species formed during shutdown partially reduce "
            "back to phosphide/phosphorus states, creating a dynamic P redox cycle. "
            "The phosphate-rich surface has high negative charge density that electrostatically repels Cl\u207b "
            "ions, suppressing chloride adsorption/corrosion. "
            "DFT shows the energy barrier for O migration through the phosphate layer is 3.41 eV vs 0.31 eV "
            "through bare Ni, confirming the passivation protective effect."
        ),
        "key_species": ["phosphate", "phosphide", "Cl\u207b", "P"],
        "related_figures": ["FIG005"],
        "related_tables": [],
        "characterization_methods": ["operando Raman", "DFT CI-NEB", "ATR-SEIRAS"],
        "source_section": "Results/Discussion \u2014 dynamic phosphate recovery and DFT",
        "page_estimate": "estimated (p.5\u20136)",
        "structured_field_path": "structured.json > domain_specific > electrocatalysis > protection_strategies[1]",
        "full_clean_backlink": "Search `full_clean.md` for `[EVID: EVID011]` or `[EVID: EVID013]`",
        "manual_review_notes": (
            "Operando Raman signal assignment to specific P/phosphate species needs manual check. "
            "Whether chloride repulsion is directly demonstrated or inferred from DFT charge density. "
            "IC data for Cl\u207b concentration near cathode not confirmed in main text."
        ),
    },
]


# ---------------------------------------------------------------------------
# L1 overview template helpers
# ---------------------------------------------------------------------------

def _build_evid_lookup(evidence: "list[Evidence]") -> "dict[str, Evidence]":
    """Return a dict mapping evidence_id -> Evidence object."""
    return {e.evidence_id: e for e in evidence}


def _evidence_excerpt_block(evid_ids: "list[str]", evid_lookup: "dict[str, Evidence]") -> str:
    """Build a Markdown block quoting the relevant excerpt for each evidence ID."""
    parts: list[str] = []
    for eid in evid_ids:
        ev = evid_lookup.get(eid)
        if ev and ev.kind == "text" and ev.source_excerpt:
            page = ev.page_estimate or "null"
            excerpt = ev.source_excerpt[:500].replace("\n", " ")
            parts.append(
                f"**[{eid}]** line {ev.source_line_start}, p.{page}:\n\n> {excerpt}"
            )
        else:
            parts.append(f"**[{eid}]** — figure reference or not found in extracted text")
    return "\n\n".join(parts) if parts else "not found"


def _fmt_list(items: "list[str]") -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- null"


def _condition_l1_sections(
    condition: "dict[str, Any]",
    evid_lookup: "dict[str, Evidence]",
    metadata: "dict[str, Any]",
) -> "dict[str, str]":
    params = condition.get("parameters", {})
    param_md = "\n".join(f"- **{k}**: {v}" for k, v in params.items()) or "not found"
    return {
        "What This Card Answers": (
            f"What were the specific operating conditions for `{condition['id']}`"
            f" ({condition['title']})?"
        ),
        "Summary": condition["summary"],
        "System / Experiment": condition.get("system", "not found"),
        "Specific Parameters": param_md,
        "Supports Result or Conclusion": condition.get("supports_result", "needs manual review"),
        "Cleaned Evidence": _evidence_excerpt_block(condition["evidence_ids"], evid_lookup),
        "Evidence IDs": ", ".join(condition["evidence_ids"]),
        "Source Section": condition.get("source_section", "needs manual review"),
        "Page Number": condition.get("page_estimate", "estimated"),
        "Related Figures": _fmt_list(condition.get("related_figures", [])),
        "Related Tables": _fmt_list(condition.get("related_tables", [])),
        "Structured Fields": condition.get("structured_field_path", "needs manual review"),
        "Full Text Backlink": condition.get("full_clean_backlink", "Search `full_clean.md` for evidence IDs above"),
        "Raw Source Paths": (
            f"- `full_clean.md`\n"
            f"- `structured.json`\n"
            f"- `evidence_links.json`\n"
            f"- raw MinerU: `{metadata.get('raw_paths', {}).get('full_md', 'not found')}`"
        ),
        "Tags": ", ".join(condition["tags"]),
        "Manual Review Notes": condition.get("manual_review_notes", "needs manual review"),
    }


def _metric_l1_sections(
    metric: "dict[str, Any]",
    evid_lookup: "dict[str, Evidence]",
    metadata: "dict[str, Any]",
) -> "dict[str, str]":
    return {
        "What This Card Answers": (
            f"What is the quantitative value for `{metric['id']}` ({metric['title']})?"
        ),
        "Summary": metric["summary"],
        "Value": metric["value"],
        "Unit": metric.get("unit", "not found"),
        "Measurement Method": metric.get("measurement_method", "not found"),
        "Condition Reference": ", ".join(metric.get("condition_ids", [])) or "not found",
        "Cleaned Evidence": _evidence_excerpt_block(metric["evidence_ids"], evid_lookup),
        "Evidence IDs": ", ".join(metric["evidence_ids"]),
        "Source Section": metric.get("source_section", "needs manual review"),
        "Page Number": metric.get("page_estimate", "estimated"),
        "Related Figures": _fmt_list(metric.get("related_figures", [])),
        "Related Tables": _fmt_list(metric.get("related_tables", [])),
        "Structured Fields": metric.get("structured_field_path", "needs manual review"),
        "Full Text Backlink": metric.get("full_clean_backlink", "Search `full_clean.md` for evidence IDs above"),
        "Raw Source Paths": (
            f"- `full_clean.md`\n"
            f"- `structured.json`\n"
            f"- `evidence_links.json`\n"
            f"- raw MinerU: `{metadata.get('raw_paths', {}).get('full_md', 'not found')}`"
        ),
        "Tags": ", ".join(metric["tags"]),
        "Manual Review Notes": metric.get("manual_review_notes", "needs manual review"),
    }


def _mechanism_l1_sections(
    mechanism: "dict[str, Any]",
    evid_lookup: "dict[str, Evidence]",
    metadata: "dict[str, Any]",
) -> "dict[str, str]":
    methods = mechanism.get("characterization_methods", [])
    species = mechanism.get("key_species", [])
    return {
        "What This Card Answers": (
            f"How does `{mechanism['id']}` ({mechanism['title']}) work mechanistically?"
        ),
        "Summary": mechanism["summary"],
        "Detailed Description": mechanism.get("description_detail", "not found"),
        "Key Species Involved": _fmt_list(species),
        "Characterization Methods": _fmt_list(methods),
        "Cleaned Evidence": _evidence_excerpt_block(mechanism["evidence_ids"], evid_lookup),
        "Evidence IDs": ", ".join(mechanism["evidence_ids"]),
        "Source Section": mechanism.get("source_section", "needs manual review"),
        "Page Number": mechanism.get("page_estimate", "estimated"),
        "Related Figures": _fmt_list(mechanism.get("related_figures", [])),
        "Related Tables": _fmt_list(mechanism.get("related_tables", [])),
        "Structured Fields": mechanism.get("structured_field_path", "needs manual review"),
        "Full Text Backlink": mechanism.get("full_clean_backlink", "Search `full_clean.md` for evidence IDs above"),
        "Raw Source Paths": (
            f"- `full_clean.md`\n"
            f"- `structured.json`\n"
            f"- `evidence_links.json`\n"
            f"- raw MinerU: `{metadata.get('raw_paths', {}).get('full_md', 'not found')}`"
        ),
        "Tags": ", ".join(mechanism["tags"]),
        "Manual Review Notes": mechanism.get("manual_review_notes", "needs manual review"),
    }


def _claim_l1_sections(
    claim: "dict[str, Any]",
    evid_lookup: "dict[str, Evidence]",
    metadata: "dict[str, Any]",
) -> "dict[str, str]":
    return {
        "What This Card Answers": (
            f"What does `{claim['id']}` assert and what evidence supports it?"
        ),
        "Claim Type": claim.get("claim_type", "not found"),
        "Summary": claim["summary"],
        "Cleaned Evidence": _evidence_excerpt_block(claim["evidence_ids"], evid_lookup),
        "Evidence IDs": ", ".join(claim["evidence_ids"]),
        "Source Section": claim.get("source_section", "needs manual review"),
        "Page Number": claim.get("page_estimate", "estimated"),
        "Related Figures": _fmt_list(claim.get("related_figures", [])),
        "Related Tables": _fmt_list(claim.get("related_tables", [])),
        "Structured Fields": claim.get("structured_field_path", "needs manual review"),
        "Full Text Backlink": claim.get("full_clean_backlink", "Search `full_clean.md` for evidence IDs above"),
        "Raw Source Paths": (
            f"- `full_clean.md`\n"
            f"- `structured.json`\n"
            f"- `evidence_links.json`\n"
            f"- raw MinerU: `{metadata.get('raw_paths', {}).get('full_md', 'not found')}`"
        ),
        "Tags": ", ".join(claim["tags"]),
        "Manual Review Notes": claim.get("manual_review_notes", "needs manual review"),
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(value: str, max_len: int = 64) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value[:max_len].strip("_")


def _heading_slugify(value: str, max_len: int = 64) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    if not value:
        value = "untitled"
    return value[:max_len].strip("-") or "untitled"


def _normalize_heading_match(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _looks_like_document_title_heading(title: str, paper_title: str) -> bool:
    normalized_title = _normalize_heading_match(title)
    normalized_paper_title = _normalize_heading_match(paper_title)
    if not normalized_title or not normalized_paper_title:
        return False
    return normalized_title == normalized_paper_title or normalized_title.startswith(normalized_paper_title)


def _build_heading_dirname(
    doc_heading_order: int,
    heading_text: str,
    used_names: set[str],
    max_len: int = 80,
) -> str:
    prefix = f"{int(doc_heading_order):03d}-"
    base_limit = max(8, max_len - len(prefix))
    base_slug = _heading_slugify(heading_text, max_len=base_limit)
    candidate = f"{prefix}{base_slug}"[:max_len].rstrip("-")
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    dup_idx = 2
    while True:
        suffix = f"-dup{dup_idx}"
        slug_limit = max(8, max_len - len(prefix) - len(suffix))
        slug = _heading_slugify(heading_text, max_len=slug_limit)
        candidate = f"{prefix}{slug}{suffix}"[:max_len].rstrip("-")
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        dup_idx += 1


def _safe_heading_dirname_max_len(clean_dir: Path, default_max: int = 80) -> int:
    """Return safe heading dirname max length under Windows path limit.

    We keep 80 as the upper bound requested by users, but shrink dynamically
    to avoid MAX_PATH issues in deep paper directories.
    """
    max_path_budget = 240
    reserve_tail = len("\\sections_by_heading\\") + len("\\paragraphs\\PRAW-000000.md")
    budget = max_path_budget - len(str(clean_dir.resolve())) - reserve_tail
    return max(24, min(default_max, budget))


def _paper_short(paper_id: str) -> str:
    """Return a readable, stable short paper token for evidence IDs."""
    m = re.match(
        r"(?P<year>\d{4}|unknown_year)_(?P<author>[a-z0-9]+)_.+_(?P<hash>[0-9a-f]{6})$",
        paper_id,
        re.IGNORECASE,
    )
    if m:
        year_raw = m.group("year").lower()
        author = slugify(m.group("author"), 12) or "paper"
        year_token = year_raw if re.fullmatch(r"\d{4}", year_raw) else "unk"
        hash_token = m.group("hash").lower()
        return f"{author}{year_token}-{hash_token}"

    fallback_hash = hashlib.md5(paper_id.encode("utf-8")).hexdigest()[:6]
    fallback_slug = slugify(paper_id, 12) or "paper"
    return f"{fallback_slug}-{fallback_hash}"


def _make_evidence_id(paper_id: str, locator: str) -> str:
    """Build stable evidence IDs like EV-333f5c-S04-P001."""
    return f"EV-{_paper_short(paper_id)}-{locator}"


def _paragraph_evidence_id(paper_id: str, paragraph_id: str) -> str:
    return _make_evidence_id(paper_id, paragraph_id)


def _figure_evidence_id(paper_id: str, figure_id: str) -> str:
    return _make_evidence_id(paper_id, figure_id)


def _table_evidence_id(paper_id: str, table_id: str) -> str:
    return _make_evidence_id(paper_id, table_id)


def _table_clean_image_relpaths(table: Table) -> list[str]:
    relpaths: list[str] = []
    for idx, raw_rel in enumerate(table.raw_images, start=1):
        ext = Path(raw_rel).suffix.lower() or ".jpg"
        relpaths.append(f"tables/{table.table_id}/image_{idx:03d}{ext}")
    return relpaths


def _assign_runtime_evidence_ids(paper_id: str, figures: "list[Figure]", tables: "list[Table]") -> None:
    """Normalize figure/table evidence IDs after paper_id is known."""
    for figure in figures:
        figure.evidence_id = _figure_evidence_id(paper_id, figure.figure_id)
    for table in tables:
        table.evidence_id = _table_evidence_id(paper_id, table.table_id)


def _build_evidence_short_id_map(
    paper_id: str,
    sections: "list[dict[str, Any]]",
    figures: "list[Figure]",
    tables: "list[Table]",
) -> "dict[str, str]":
    short_prefix = _paper_short(paper_id)
    ordered_ids: list[str] = []

    for sec in sections:
        for paragraph in sec.get("paragraphs", []):
            ordered_ids.append(_paragraph_evidence_id(paper_id, paragraph["paragraph_id"]))

    for figure in figures:
        ordered_ids.append(figure.evidence_id or _figure_evidence_id(paper_id, figure.figure_id))

    for table in tables:
        ordered_ids.append(table.evidence_id or _table_evidence_id(paper_id, table.table_id))

    short_ids: dict[str, str] = {}
    for index, evidence_id in enumerate(ordered_ids, start=1):
        if evidence_id not in short_ids:
            short_ids[evidence_id] = f"E-{short_prefix}-{index:03d}"
    return short_ids


def compact_text(value: str) -> str:
    value = value.replace("\u00a0", " ").replace("\u2009", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _extract_doi(text: str) -> str:
    m = re.search(r"https://doi\.org/([^\s\)>\"]+)", text)
    if m:
        return m.group(1).rstrip(".,;")
    return ""


def _extract_published_online(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("Published online:"):
            return line.split(":", 1)[1].strip()
    return ""


def _extract_year(text: str, published_online: str) -> str:
    m = re.search(r"\b(20\d{2}|19\d{2})\b", published_online or text[:3000])
    return m.group(1) if m else "unknown_year"


def _extract_author_line(lines: list[str]) -> str:
    title_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("## "):
            title_idx = i
            break
    if title_idx < 0:
        return ""

    for line in lines[title_idx + 1:title_idx + 30]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("http", "DOI", "doi", "Published", "Received", "Accepted", "Check", "©", "†", "*")):
            continue
        if re.match(r"^\d", stripped):
            continue
        if "," in stripped and len(stripped) < 400:
            words = re.split(r"[,\s]+", stripped)
            cap_words = [w for w in words if w and w[0].isupper() and len(w) > 1]
            if len(cap_words) >= 2:
                return stripped
    return ""


def _infer_first_author(lines: list[str]) -> str:
    """Best-effort first-author surname extraction from MinerU full.md lines."""
    author_line = _extract_author_line(lines)
    if not author_line:
        return "unknown"

    first_seg = author_line.split(",")[0].strip()
    name_words: list[str] = []
    for raw_word in first_seg.split():
        cleaned = re.sub(r"[^A-Za-z\-]+$", "", raw_word)
        cleaned = re.sub(r"^[^A-Za-z]+", "", cleaned)
        if re.match(r"^[A-Za-z\-]+$", cleaned):
            name_words.append(cleaned)
    if name_words:
        return slugify(name_words[-1])[:20] or "unknown"
    return "unknown"


def _infer_journal(doi: str) -> str:
    if not doi:
        return ""
    doi_l = doi.lower()
    mapping = [
        ("s41586", "Nature"),
        ("s41560", "Nature Energy"),
        ("s41929", "Nature Catalysis"),
        ("s41467", "Nature Communications"),
        ("s41557", "Nature Chemistry"),
        ("jacs", "JACS"),
        ("acsenergylett", "ACS Energy Letters"),
        ("acsnano", "ACS Nano"),
        ("acsami", "ACS Applied Materials & Interfaces"),
        ("adfm", "Advanced Functional Materials"),
        ("adma", "Advanced Materials"),
        ("aenm", "Advanced Energy Materials"),
        ("anie", "Angewandte Chemie"),
        ("smtd", "Small Methods"),
        ("smll", "Small"),
        ("joule", "Joule"),
        ("ees", "Energy & Environmental Science"),
        ("jmatchemа", "Journal of Materials Chemistry A"),
        ("chemrev", "Chemical Reviews"),
        ("chemmat", "Chemistry of Materials"),
    ]
    for key, journal in mapping:
        if key in doi_l:
            return journal
    return ""


def extract_metadata(text: str, mineru_dir: Path) -> dict[str, Any]:
    lines = [line.strip() for line in text.splitlines()]
    title = next((line[2:].strip() for line in lines if line.startswith("# ") and not line.startswith("## ")), mineru_dir.name)
    doi = _extract_doi(text)
    published = _extract_published_online(lines)
    year = _extract_year(text, published)
    author_line = _extract_author_line(lines)
    first_author = _infer_first_author(lines)
    short_title = slugify(title.replace("10,000-h", "10000h"), 56)
    hash6 = hashlib.sha1(f"{title}|{doi}".encode("utf-8")).hexdigest()[:6]
    paper_id = f"{year}_{first_author}_{short_title}_{hash6}"

    origin_pdf = next(mineru_dir.glob("*_origin.pdf"), None)
    full_md = mineru_dir / "full.md"
    return {
        "paper_id": paper_id,
        "title": title,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}" if doi else "",
        "year": year,
        "published_online": published,
        "first_author": first_author,
        "authors_raw": author_line,
        "journal": _infer_journal(doi),
        "document_type": "research_article",
        "raw_paths": {
            "mineru_output_dir": str(mineru_dir),
            "full_md": str(full_md),
            "content_list_v2_json": str(mineru_dir / "content_list_v2.json"),
            "layout_json": str(mineru_dir / "layout.json"),
            "origin_pdf": str(origin_pdf) if origin_pdf else "",
            "images_dir": str(mineru_dir / "images"),
        },
    }


def load_content_pages(mineru_dir: Path) -> list[str]:
    path = mineru_dir / "content_list_v2.json"
    if not path.exists():
        return []
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError:
        return []
    pages: list[str] = []
    if not isinstance(data, list):
        return pages
    for page in data:
        chunks: list[str] = []
        if isinstance(page, list):
            for item in page:
                if isinstance(item, dict):
                    content = item.get("content")
                    if isinstance(content, str):
                        chunks.append(compact_text(content))
        pages.append(" ".join(chunks))
    return pages


def estimate_page(excerpt: str, pages: list[str]) -> int | None:
    if not pages or not excerpt:
        return None
    needle = compact_text(re.sub(r"\$[^$]+\$", "", excerpt))[:80]
    if len(needle) < 30:
        needle = compact_text(excerpt)[:80]
    for index, page_text in enumerate(pages, start=1):
        if needle and needle in page_text:
            return index
    return None


def line_span_for_text(lines: list[str], text: str) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    target = compact_text(text)[:80]
    for idx, line in enumerate(lines, start=1):
        if target and target in compact_text(line):
            return idx, idx
    return None, None


def paragraph_at_line(lines: list[str], start_index: int) -> tuple[int, int, str]:
    left = start_index
    while left > 0 and lines[left - 1].strip():
        left -= 1
    right = start_index
    while right + 1 < len(lines) and lines[right + 1].strip():
        right += 1
    return left + 1, right + 1, compact_text(" ".join(lines[left : right + 1]))


def find_key_evidence(lines: list[str], pages: list[str]) -> list[Evidence]:
    evidence: list[Evidence] = []
    used_lines: set[int] = set()
    for spec in KEY_EVIDENCE_PATTERNS:
        found: tuple[int, int, int, str] | None = None
        for idx, line in enumerate(lines):
            line_norm = compact_text(line).lower()
            if idx in used_lines:
                continue
            if line_norm.startswith("# "):
                continue
            if all(piece.lower() in line_norm for piece in spec["contains"]):
                start, end, excerpt = paragraph_at_line(lines, idx)
                found = (idx + 1, start, end, excerpt)
                used_lines.add(idx)
                break
        if not found:
            for idx, line in enumerate(lines):
                line_norm = compact_text(line).lower()
                if line_norm.startswith("# "):
                    continue
                matched_parts = sum(1 for piece in spec["contains"] if piece.lower() in line_norm)
                if matched_parts >= max(2, len(spec["contains"]) - 1):
                    start, end, excerpt = paragraph_at_line(lines, idx)
                    found = (idx + 1, start, end, excerpt)
                    break
        if found:
            match_line, start, end, excerpt = found
            evidence.append(
                Evidence(
                    evidence_id=spec["id"],
                    kind="text",
                    title=spec["title"],
                    source_line_start=match_line,
                    source_line_end=end,
                    source_excerpt=excerpt[:1200],
                    page_estimate=estimate_page(excerpt, pages),
                    tags=spec["tags"],
                )
            )
    return evidence


# ---------------------------------------------------------------------------
# HTML → plain text / Markdown helper
# ---------------------------------------------------------------------------

class _TableHTMLParser(HTMLParser):
    """Minimal HTML parser that converts MinerU <table> HTML to Markdown."""

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("tr",):
            self._current_row = []
        elif tag in ("td", "th"):
            self._current_cell = []
            self._in_cell = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            self._current_row.append("".join(self._current_cell).strip())
            self._in_cell = False
        elif tag == "tr":
            if self._current_row:
                self._rows.append(self._current_row)

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)

    def to_markdown(self) -> str:
        if not self._rows:
            return ""
        lines: list[str] = []
        header = self._rows[0]
        lines.append("| " + " | ".join(html_module.unescape(c) for c in header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in self._rows[1:]:
            # Pad short rows
            padded = row + [""] * (len(header) - len(row))
            lines.append("| " + " | ".join(html_module.unescape(c) for c in padded) + " |")
        return "\n".join(lines)


def html_table_to_markdown(html: str) -> str:
    """Convert an HTML table string (from MinerU) to a Markdown table."""
    parser = _TableHTMLParser()
    try:
        parser.feed(html)
        md = parser.to_markdown()
        return md if md else html  # fallback: return raw HTML
    except Exception:
        return html


# ---------------------------------------------------------------------------
# content_list_v2.json loader
# ---------------------------------------------------------------------------

def load_content_list(mineru_dir: Path) -> list[dict[str, Any]]:
    """Load and flatten content_list_v2.json.

    MinerU's content_list_v2.json is a list-of-pages (each page is a list of
    content items).  Returns a single flat list of all items with their type
    normalised to lowercase string.
    """
    json_path = mineru_dir / "content_list_v2.json"
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    flat: list[dict[str, Any]] = []
    if isinstance(data, list):
        for page_index, page_or_item in enumerate(data, start=1):
            if isinstance(page_or_item, list):
                # List of pages: each page is a list of items
                for item in page_or_item:
                    if isinstance(item, dict):
                        item = dict(item)
                        if isinstance(item.get("type"), list):
                            item["type"] = item["type"][0] if item["type"] else ""
                        item["type"] = str(item.get("type", "")).lower()
                        item["_page_index"] = page_index
                        flat.append(item)
            elif isinstance(page_or_item, dict):
                item = dict(page_or_item)
                if isinstance(item.get("type"), list):
                    item["type"] = item["type"][0] if item["type"] else ""
                item["type"] = str(item.get("type", "")).lower()
                item["_page_index"] = page_index
                flat.append(item)
    return flat


def _content_item_text(item: dict[str, Any]) -> str:
    """Extract plain text payload from one content_list item."""
    content = item.get("content")
    if isinstance(content, str):
        return compact_text(content)
    if not isinstance(content, dict):
        return ""

    parts: list[str] = []
    for key in ("title_content", "paragraph_content", "text", "caption"):
        val = content.get(key)
        if isinstance(val, list):
            for cell in val:
                if isinstance(cell, dict):
                    txt = str(cell.get("content", "")).strip()
                    if txt:
                        parts.append(txt)
                elif isinstance(cell, str):
                    if cell.strip():
                        parts.append(cell.strip())
        elif isinstance(val, str) and val.strip():
            parts.append(val.strip())
    return compact_text(" ".join(parts))


def build_section_recovery_hints(mineru_dir: Path, content_items: list[dict[str, Any]]) -> dict[str, Any]:
    """Build lightweight recovery hints from MinerU structured blocks.

    Uses content_list_v2 block type + page order to stabilize early front/abstract routing
    when full.md heading structure is noisy (e.g. two-column first page).

    Note: hints are auxiliary only. Final routing is still decided by
    paragraph-level detectors in ``build_sections_data``.
    """
    front_snippets: list[str] = []
    abstract_snippets: list[str] = []
    back_snippets: list[str] = []

    def _push(bucket: list[str], text: str) -> None:
        t = compact_text(text).lower()
        if len(t) < 16:
            return
        t = t[:120]
        if t and t not in bucket:
            bucket.append(t)

    for item in content_items:
        item_type = str(item.get("type", "")).lower()
        page_idx = int(item.get("_page_index") or 0)
        txt = _content_item_text(item)
        if not txt:
            continue
        low = txt.lower()

        if page_idx <= 1 and item_type in {"paragraph", "title"}:
            if "abstract" in txt.lower() or "摘要" in txt:
                _push(abstract_snippets, txt)

        if item_type in {"paragraph", "title"} and page_idx >= max(0, len(content_items) - 5):
            _push(back_snippets, txt)

        # Guard for inline abstract label inside a long paragraph block.
        if page_idx <= 1 and ("abstract" in low or "摘要" in low):
            _push(abstract_snippets, txt)

    layout_path = mineru_dir / "layout.json"
    layout_available = layout_path.exists()

    return {
        "front_snippets": front_snippets,
        "abstract_snippets": abstract_snippets,
        "back_snippets": back_snippets,
        "layout_available": layout_available,
    }


def _matches_recovery_snippets(text: str, snippets: list[str]) -> bool:
    low = compact_text(text).lower()
    if not low:
        return False
    for snippet in snippets:
        if not snippet:
            continue
        if snippet in low or low.startswith(snippet[:40]):
            return True
    return False


def _join_caption_parts(parts: list[dict[str, Any]]) -> str:
    """Join caption parts from content_list_v2 into a single clean string."""
    segments: list[str] = []
    for part in parts:
        if isinstance(part, dict):
            segments.append(str(part.get("content", "")).strip())
        elif isinstance(part, str):
            segments.append(part.strip())
    return compact_text(" ".join(segments))


def _infer_fig_num_from_caption(caption: str) -> str | None:
    """Try to extract a figure number from a caption string.

    Handles:
      - Clean prefixes: "Fig. 1 | ...", "Figure 1. ..."
      - Garbled mid-sentence: "...as a function of Figure 4.current..."
      - Journal-style: "Fig 3 Schematic..."
    """
    # Clean prefix patterns first (most reliable)
    clean_prefix = re.match(
        r"^(?:Fig\.?\s*|Figure\s+)(\d+)[\s|.,]", caption, re.IGNORECASE
    )
    if clean_prefix:
        return clean_prefix.group(1)
    # Embedded figure number (double-column layout artefact): "...Figure 4.current..."
    embedded = re.search(r"\bFigure\s+(\d+)\.", caption, re.IGNORECASE)
    if embedded:
        return embedded.group(1)
    return None


# ---------------------------------------------------------------------------
# Parse figures (Markdown + content_list_v2 fallback)
# ---------------------------------------------------------------------------

def parse_figures_from_content_list(
    content_items: list[dict[str, Any]],
) -> list[Figure]:
    """Extract figures from content_list_v2 items.

    Handles double-column PDFs where MinerU stores proper captions in the JSON
    even when the Markdown output scrambles the layout.
    """
    figures: list[Figure] = []
    seen: set[str] = set()
    fig_counter = 0

    for item in content_items:
        if item.get("type") != "image":
            continue
        content = item.get("content", {})
        if not isinstance(content, dict):
            continue

        img_path: str = content.get("image_source", {}).get("path", "")
        caption_parts: list = content.get("image_caption", [])
        caption_text = _join_caption_parts(caption_parts).strip()

        if not caption_text or not img_path:
            continue

        fig_num_str = _infer_fig_num_from_caption(caption_text)
        if fig_num_str:
            try:
                fig_num = int(fig_num_str)
            except ValueError:
                continue
        else:
            # No figure number found — skip (it's likely a noise image or sub-panel)
            continue

        fig_id = f"FIG{fig_num:03d}"
        if fig_id in seen:
            continue  # already captured

        seen.add(fig_id)
        fig_counter += 1

        # Clean caption: strip garbled figure-number suffix artefacts
        clean_caption = re.sub(r"\bFigure\s+\d+\.", f"Figure {fig_num}.", caption_text)
        # Extract short title
        title_body = re.sub(
            r"^(?:Fig\.?\s*\d+\s*[|.]?\s*|Figure\s+\d+\s*[.|]\s*)", "",
            clean_caption, flags=re.IGNORECASE
        ).strip()
        period_pos = title_body.find(". ")
        if 0 < period_pos < 120:
            title = title_body[:period_pos].strip()
        else:
            title = title_body[:117].strip() + ("..." if len(title_body) > 117 else "")
        if not title:
            title = f"Figure {fig_num}"

        figures.append(Figure(
            figure_id=fig_id,
            figure_number=str(fig_num),
            title=title,
            caption=clean_caption,
            source_line_start=0,
            raw_images=[img_path] if img_path else [],
            evidence_id=f"EVID_FIG{fig_num:03d}",
        ))

    # Sort by figure number
    figures.sort(key=lambda f: int(f.figure_number))
    return figures


def parse_figures(lines: list[str], pages: list[str], mineru_dir: Path | None = None) -> list[Figure]:
    """Parse figure captions from MinerU full.md.

    Supports multiple journal caption formats:
    - Nature:    'Fig. 1 | caption'
    - ACS/JACS:  'Figure 1. caption'  also '[Figure 1. caption]' (bracket-wrapped)
    - Wiley/etc: 'Figure 1. caption'  or 'Figure 1 | caption'
    - Elsevier:  'Fig. 1. caption'
    - J.Electrochem.Soc.: 'Fig. 1 caption' (no punctuation)
    - Chinese:   '图1. caption' / '图 1 caption'

    Falls back to content_list_v2.json for double-column PDFs where the
    Markdown layout scrambles figure number / caption associations.
    Uses a sliding window (MAX_LOOKBACK lines) to associate images with their
    nearest preceding caption, avoiding noise images at the document header
    (journal logos, "Read Online" buttons, etc.).
    """
    figures: list[Figure] = []
    seen_fig_nums: set[int] = set()
    image_re = re.compile(r"!\[\]\((images/[^)]+)\)")

    # Caption patterns ordered by precedence (most specific first)
    caption_patterns = [
        # Nature: 'Fig. 1 | caption'
        re.compile(r"^Fig\.\s*(\d+)\s*\|(.+)", re.IGNORECASE),
        # ACS / JACS / Wiley: 'Figure 1. caption' or 'Figure 1 | caption'
        re.compile(r"^Figure\s+(\d+)\s*[.|]\s*(.+)", re.IGNORECASE),
        # Elsevier (J. Power Sources etc.): 'Fig. 1. caption' (period after number)
        re.compile(r"^Fig\.\s+(\d+)\.\s+(.+)", re.IGNORECASE),
        # J. Electrochem. Soc. etc.: 'Fig. 1 Title text' (space after number, no period)
        # Exclude common in-text verb patterns to avoid false positives.
        re.compile(
            r"^Fig\.\s+(\d+)\s+(?!shows?\b|is\b|are\b|illustrates?\b|depicts?\b|presents?\b|displays?\b)(.{4,})",
        ),
        # Chinese: '图1. caption' or '图 1 caption'
        re.compile(r"^图\s*(\d+)\s*[.。|]?\s*(.+)"),
    ]

    # Prefix patterns for stripping "Fig. X |", "Figure X.", "Fig. X " from title
    prefix_strip_re = re.compile(
        r"^(?:"
        r"Fig\.\s*\d+\s*[|.]\s*"   # Fig. 1 | or Fig. 1.
        r"|\[?Figure\s+\d+\s*[.|]\s*"  # Figure 1. or [Figure 1.
        r"|Fig\.\s+\d+\s+"          # Fig. 1 (bare space, no punctuation)
        r"|图\s*\d+\s*[.。|]?\s*"   # Chinese
        r")",
        re.IGNORECASE,
    )

    # Build per-line image lists for sliding-window lookups
    line_images: dict[int, list[str]] = {}
    for ln, line in enumerate(lines, start=1):
        imgs = [m.group(1) for m in image_re.finditer(line)]
        if imgs:
            line_images[ln] = imgs

    MAX_LOOKBACK = 6  # lines above the caption to scan for associated images

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Unwrap bracket-wrapped captions: '[Figure 1. ...]' → 'Figure 1. ...'
        if stripped.startswith("[Figure ") or stripped.startswith("[Fig."):
            stripped_clean = stripped[1:]
            if stripped_clean.endswith("]"):
                stripped_clean = stripped_clean[:-1]
        else:
            stripped_clean = stripped

        fig_num: int | None = None
        caption: str | None = None

        for pat in caption_patterns:
            m = pat.match(stripped_clean)
            if m:
                try:
                    fig_num = int(m.group(1))
                    caption = compact_text(stripped_clean)
                    break
                except (ValueError, IndexError):
                    pass

        if fig_num is None or fig_num in seen_fig_nums:
            continue

        # Extract a short title (first sentence / before first '. ')
        title_body = prefix_strip_re.sub("", caption).strip()
        period_pos = title_body.find(". ")
        if 0 < period_pos < 120:
            title = title_body[:period_pos].strip()
        elif len(title_body) > 120:
            title = title_body[:117].strip() + "..."
        else:
            title = title_body
        if not title:
            title = f"Figure {fig_num}"

        # Collect images from the preceding MAX_LOOKBACK lines (sliding window)
        recent_images: list[str] = []
        for look_back in range(MAX_LOOKBACK, 0, -1):
            prev_ln = line_no - look_back
            if prev_ln in line_images:
                recent_images.extend(line_images[prev_ln])
        # Also include images on the same caption line (rare but possible)
        if line_no in line_images:
            recent_images.extend(line_images[line_no])

        figure = Figure(
            figure_id=f"FIG{fig_num:03d}",
            figure_number=str(fig_num),
            title=title,
            caption=caption,
            source_line_start=line_no,
            raw_images=recent_images,
            evidence_id=f"EVID_FIG{fig_num:03d}",
        )
        figures.append(figure)
        seen_fig_nums.add(fig_num)

    for figure in figures:
        figure.caption = compact_text(figure.caption)

    # ── JSON fallback for double-column / non-standard layouts ───────────────
    # If markdown parsing found fewer than expected figures, supplement with
    # entries from content_list_v2.json (which has reliable structured captions
    # even when the Markdown layout scrambles the text).
    if mineru_dir is not None:
        content_items = load_content_list(mineru_dir)
        json_figures = parse_figures_from_content_list(content_items)
        existing_ids = {f.figure_id for f in figures}
        for jf in json_figures:
            if jf.figure_id not in existing_ids:
                figures.append(jf)
                existing_ids.add(jf.figure_id)
        figures.sort(key=lambda f: int(f.figure_number))

    return figures


def copy_used_figure_images(figures: list[Figure], mineru_dir: Path, clean_dir: Path) -> dict[str, str]:
    raw_to_clean: dict[str, str] = {}
    figures_dir = clean_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    for figure in figures:
        figure_dir = figures_dir / figure.figure_id
        figure_dir.mkdir(parents=True, exist_ok=True)
        write_text(figure_dir / "caption.md", f"# Caption\n\n{figure.caption}\n")
        for index, raw_rel in enumerate(figure.raw_images, start=1):
            raw_path = mineru_dir / raw_rel
            if not raw_path.exists():
                continue
            ext = raw_path.suffix.lower() or ".jpg"
            clean_name = f"image_{index:03d}{ext}"
            clean_rel = f"figures/{figure.figure_id}/{clean_name}"
            if raw_rel not in raw_to_clean:
                shutil.copy2(raw_path, clean_dir / clean_rel)
                raw_to_clean[raw_rel] = clean_rel
            figure.clean_images.append(raw_to_clean[raw_rel])
    return raw_to_clean


def build_image_manifest(mineru_dir: Path, raw_to_clean: dict[str, str], figures: list[Figure]) -> list[dict[str, Any]]:
    figure_by_raw: dict[str, str] = {}
    figure_caption_path: dict[str, str] = {}
    for figure in figures:
        figure_caption_path[figure.figure_id] = f"figures/{figure.figure_id}/caption.md"
        for raw_rel in figure.raw_images:
            figure_by_raw[raw_rel] = figure.figure_id
    manifest: list[dict[str, Any]] = []
    for image_path in sorted((mineru_dir / "images").glob("*")):
        raw_rel = f"images/{image_path.name}"
        status = "used" if raw_rel in raw_to_clean else "uncertain"
        figure_id = figure_by_raw.get(raw_rel)
        manifest.append(
            {
                "raw_path": str(image_path),
                "raw_relative_path": raw_rel,
                "status": status,
                "figure_id": figure_id,
                "clean_path": raw_to_clean.get(raw_rel),
                "caption_path": figure_caption_path.get(figure_id),
                "note": (
                    "Copied into figures/FIGxxx/ and paired with caption.md."
                    if status == "used"
                    else "Not associated with an automatically detected main-text figure; keep raw path for manual review."
                ),
            }
        )
    return manifest


def build_figure_evidence(figures: list[Figure], lines: list[str], pages: list[str]) -> list[Evidence]:
    items: list[Evidence] = []
    for figure in figures:
        page = estimate_page(figure.caption, pages)
        if page is None:
            page = max(1, min(11, figure.source_line_start // 35 + 1))
        items.append(
            Evidence(
                evidence_id=figure.evidence_id,
                kind="figure",
                title=figure.title,
                source_line_start=figure.source_line_start,
                source_line_end=figure.source_line_start,
                source_excerpt=figure.caption,
                page_estimate=page,
                related_figures=[figure.figure_id],
                tags=["figure", "scientific_image", "electrocatalysis"],
            )
        )
    return items


def clean_full_markdown(lines: list[str], raw_to_clean: dict[str, str], evidence: list[Evidence]) -> str:
    evidence_by_line: dict[int, str] = {
        item.source_line_start: item.evidence_id
        for item in evidence
        if item.kind == "text" and item.source_line_start is not None
    }
    output: list[str] = []
    in_references = False
    image_re = re.compile(r"!\[\]\((images/[^)]+)\)")

    for line_no, original in enumerate(lines, start=1):
        line = original.rstrip()
        stripped = line.strip()

        if re.match(r"^\d+\.\s+", stripped):
            in_references = True
            continue
        if in_references:
            if stripped in {"# Article", "# Methods"}:
                in_references = False
                if stripped == "# Methods":
                    output.append(stripped)
                continue
            continue

        if stripped == "# Article":
            continue
        if stripped.startswith("Publisher") or "exclusive rights to this article" in stripped:
            continue
        if "The Author(s), under exclusive licence" in stripped:
            continue
        if "State Key Laboratory" in stripped and "e-mail:" in stripped:
            continue
        if stripped in {"Check for updates"}:
            continue

        def replace_image(match: re.Match[str]) -> str:
            raw_rel = match.group(1)
            clean_rel = raw_to_clean.get(raw_rel)
            if not clean_rel:
                return ""
            return f"![]({clean_rel})"

        line = image_re.sub(replace_image, line)

        fig_match = re.match(r"^(Fig\.\s*(\d+)\s*\|.*)", stripped)
        if fig_match and f"[EVID:" not in line:
            line = f"{line} [EVID: EVID_FIG{int(fig_match.group(2)):03d}]"
        elif line_no in evidence_by_line and "[EVID:" not in line:
            line = f"{line} [EVID: {evidence_by_line[line_no]}]"

        output.append(line)

    text = "\n".join(output)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def markdown_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def write_root_docs(clean_dir: Path, metadata: dict[str, Any]) -> None:
    write_text(
        clean_dir / ".abstract.md",
        f"""# {metadata['title']}

L0 type: paper
Paper ID: {metadata['paper_id']}
Domain: electrocatalysis; hydrogen_energy; materials_science
Document type: research_article

This paper studies intermittent alkaline seawater electrolysis driven by fluctuating renewable electricity. It identifies shutdown-induced HER cathode oxidation/corrosion as a key degradation problem and proposes NiCoP-Cr2O3 with an in situ phosphate/oxide passivation layer to protect Ni active sites and repel halide adsorption. The main experimental value is a long-term stability case: 10,000 h at 0.5 A cm-2 in alkaline seawater with low voltage increase.

L1 entry: .overview.md
Full evidence body: full_clean.md
""",
    )

    write_text(
        clean_dir / ".overview.md",
        f"""# Paper Overview

Paper ID: `{metadata['paper_id']}`

Title: {metadata['title']}

DOI: {metadata['doi_url']}

Publication: {metadata['journal']} ({metadata['year']})

## OpenViking L0/L1 Entries

- Paper-level L0: `.abstract.md`
- Paper-level L1: `.overview.md`
- Methods card: `memory_cards/methods/.abstract.md`
- Results card: `memory_cards/results/.abstract.md`
- Claims: `memory_cards/key_claims/CLAIMxxx/.abstract.md`
- Metrics: `memory_cards/metrics/METRICxxx/.abstract.md`
- Conditions: `memory_cards/conditions/CONDITIONxxx/.abstract.md`
- Mechanisms: `memory_cards/mechanisms/MECHANISMxxx/.abstract.md`
- Figure cards: `memory_cards/figures/FIGxxx/.abstract.md`

## Evidence and Traceability

- Clean full text: `full_clean.md`
- Evidence index: `evidence_links.json`
- Structured extraction: `structured.json`
- Image manifest: `image_manifest.json`
- Table manifest: `table_manifest.json`
- Raw MinerU path: `{metadata['raw_paths']['mineru_output_dir']}`
- Source PDF: `{metadata['raw_paths']['origin_pdf']}`

## Retrieval Tags

domain: electrocatalysis, hydrogen_energy, materials_science

document_type: research_article

method_type: electrochemical_measurement, AEM_electrolyser_test, operando_Raman, TOF-SIMS, HAADF-STEM, DFT

object_type: NiCoP-Cr2O3 cathode, alkaline seawater electrolyser, HER catalyst

result_type: stability, overpotential, passivation_mechanism, chloride_resistance
""",
    )


def write_memory_card(card_dir: Path, title: str, l0: str, l1_sections: dict[str, str]) -> None:
    write_text(card_dir / ".abstract.md", f"# {title}\n\n{l0}\n\nL1 entry: `.overview.md`")
    sections = [f"# {title}"]
    for heading, body in l1_sections.items():
        sections.append(f"## {heading}\n\n{body}")
    write_text(card_dir / ".overview.md", "\n\n".join(sections))


def write_standard_memory_cards(
    clean_dir: Path,
    evidence: "list[Evidence] | None" = None,
    metadata: "dict[str, Any] | None" = None,
) -> None:
    evidence = evidence or []
    metadata = metadata or {}
    evid_lookup = _build_evid_lookup(evidence)

    # ── methods card ────────────────────────────────────────────────────────
    raw_full_md = metadata.get("raw_paths", {}).get("full_md", "not found")
    raw_mineru = metadata.get("raw_paths", {}).get("mineru_output_dir", "not found")
    write_memory_card(
        clean_dir / "memory_cards" / "methods",
        "Methods Card",
        (
            "L0 type: methods. "
            "The paper combines catalyst synthesis, electrochemical testing, AEM electrolyser "
            "validation, in situ/operando characterization, microscopy, TOF-SIMS and DFT to "
            "explain intermittent seawater electrolysis stability.\n\n"
            "Tags: methods, synthesis, electrochemical, operando, DFT\n"
            "Evidence IDs: EVID005, EVID006, EVID011, EVID012, EVID013"
        ),
        {
            "What This Card Answers": (
                "What experimental and computational methods were used in this paper?"
            ),
            "Summary": (
                "Methods include NiCo-LDH/NiCoP/NiCoP-Cr2O3 synthesis, electrochemical HER "
                "testing, AEM electrolyser testing, operando Raman, ATR-SEIRAS, "
                "SEM/XRD/XPS/IC, HAADF-STEM, TOF-SIMS, and VASP DFT/CI-NEB calculations."
            ),
            "Method List": (
                "- **Catalyst synthesis**: NiCo-LDH \u2192 NiCoP \u2192 NiCoP-Cr2O3 (sequential)\n"
                "- **Electrochemical HER testing**: three-electrode cell, LSV, chronopotentiometry\n"
                "- **Full-cell stability**: two-electrode cell, chronoamperometry\n"
                "- **AEM electrolyser**: 1 M KOH, 80\u00b0C, polarisation curve\n"
                "- **operando Raman**: dynamic P/phosphate redox monitoring\n"
                "- **ATR-SEIRAS**: surface species detection\n"
                "- **SEM / XRD / XPS / IC**: bulk and surface characterization\n"
                "- **HAADF-STEM**: atomic-resolution structural imaging\n"
                "- **TOF-SIMS**: depth-profiling passivation layer composition\n"
                "- **DFT + CI-NEB (VASP)**: energy barrier calculations for O migration"
            ),
            "Key Evidence": (
                _evidence_excerpt_block(["EVID005", "EVID011", "EVID012", "EVID013"], evid_lookup)
            ),
            "Evidence IDs": "EVID005, EVID006, EVID011, EVID012, EVID013",
            "Source Section": "Methods (dedicated section in paper)",
            "Page Number": "estimated (p.6\u20138 typically in Nature format)",
            "Related Figures": "- null",
            "Related Tables": "- null",
            "Structured Fields": "structured.json > methods > items",
            "Full Text Backlink": (
                "Search `full_clean.md` for `# Methods` section or "
                "`[EVID: EVID005]` / `[EVID: EVID011]`"
            ),
            "Raw Source Paths": (
                f"- `full_clean.md`\n"
                f"- `structured.json`\n"
                f"- `evidence_links.json`\n"
                f"- raw MinerU: `{raw_full_md}`"
            ),
            "Tags": "methods, synthesis, electrochemical, operando, DFT, HAADF-STEM, TOF-SIMS",
            "Manual Review Notes": (
                "Methods section may contain SI-only details not captured here. "
                "DFT functional (GGA-PBE + U?) and U values not confirmed from main text. "
                "Electrode geometric area and loading not extracted."
            ),
        },
    )

    # ── results card ────────────────────────────────────────────────────────
    write_memory_card(
        clean_dir / "memory_cards" / "results",
        "Results Card",
        (
            "L0 type: results. "
            "The paper reports long-term intermittent alkaline seawater electrolysis stability, "
            "low HER overpotential, AEM performance, and mechanistic evidence for dynamic passivation.\n\n"
            "Tags: results, stability, overpotential, AEM, passivation\n"
            "Evidence IDs: EVID003, EVID007, EVID008, EVID009, EVID_FIG002"
        ),
        {
            "What This Card Answers": (
                "What are the main quantitative and qualitative results of this paper?"
            ),
            "Summary": (
                "NiCoP-Cr2O3 achieves 10,000 h intermittent operation at 0.5 A cm\u207b\u00b2, "
                "4,500 h at 1 A cm\u207b\u00b2 under 10-min cycling, and 275 mV overpotential "
                "at 4 A cm\u207b\u00b2 in 20 wt% NaOH + seawater."
            ),
            "Main Results": (
                "- 10,000 h at 0.5 A cm\u207b\u00b2 in 1 M NaOH + seawater (12-h cycle) \u2014 METRIC001\n"
                "- 4,500 h at 1 A cm\u207b\u00b2 (10-min cycle) \u2014 METRIC002\n"
                "- 275 mV overpotential at 4 A cm\u207b\u00b2 (HER half-cell) \u2014 METRIC003\n"
                "- AEM: 1.74 V at 1 A cm\u207b\u00b2; 1.99 V at 4 A cm\u207b\u00b2 \u2014 METRIC004\n"
                "- DFT O-migration barriers 0.31 / 3.41 / 1.79 eV \u2014 METRIC005"
            ),
            "Cleaned Evidence": (
                _evidence_excerpt_block(["EVID003", "EVID007", "EVID008", "EVID009"], evid_lookup)
            ),
            "Evidence IDs": "EVID003, EVID007, EVID008, EVID009, EVID_FIG002",
            "Source Section": "Results (main text)",
            "Page Number": "estimated (p.2\u20135)",
            "Related Figures": "- FIG002\n- FIG003\n- FIG004\n- FIG005",
            "Related Tables": "- null",
            "Structured Fields": "structured.json > results\nstructured.json > results > metrics",
            "Full Text Backlink": (
                "Search `full_clean.md` for `[EVID: EVID003]`, `[EVID: EVID007]`, "
                "`[EVID: EVID008]`, `[EVID: EVID009]`\n"
                "Also see `memory_cards/metrics/` for per-metric detail cards."
            ),
            "Raw Source Paths": (
                f"- `full_clean.md`\n"
                f"- `structured.json`\n"
                f"- `memory_cards/metrics/`\n"
                f"- `figures/`\n"
                f"- raw MinerU: `{raw_full_md}`"
            ),
            "Tags": "results, stability, overpotential, AEM, passivation_mechanism, chloride_resistance",
            "Manual Review Notes": (
                "Voltage increase rate ~0.5% khr\u207b\u00b9 needs exact text citation. "
                "Figure 2 is the primary evidence figure \u2014 verify panel assignments. "
                "Whether SI results supplement main-text values was not checked."
            ),
        },
    )

    # ── key_claims cards ─────────────────────────────────────────────────────
    for claim in CLAIMS:
        write_memory_card(
            clean_dir / "memory_cards" / "key_claims" / claim["id"],
            f"{claim['id']}: {claim['title']}",
            (
                f"L0 type: key_claim. {claim['summary']}\n\n"
                f"Tags: {', '.join(claim['tags'])}\n"
                f"Evidence IDs: {', '.join(claim['evidence_ids'])}"
            ),
            _claim_l1_sections(claim, evid_lookup, metadata),
        )

    # ── metrics cards ────────────────────────────────────────────────────────
    for metric in METRICS:
        write_memory_card(
            clean_dir / "memory_cards" / "metrics" / metric["id"],
            f"{metric['id']}: {metric['title']}",
            (
                f"L0 type: metric. {metric['summary']} Value: {metric['value']}.\n\n"
                f"Tags: {', '.join(metric['tags'])}\n"
                f"Evidence IDs: {', '.join(metric['evidence_ids'])}"
            ),
            _metric_l1_sections(metric, evid_lookup, metadata),
        )

    # ── conditions cards ─────────────────────────────────────────────────────
    for condition in CONDITIONS:
        write_memory_card(
            clean_dir / "memory_cards" / "conditions" / condition["id"],
            f"{condition['id']}: {condition['title']}",
            (
                f"L0 type: condition. {condition['summary']}\n\n"
                f"Tags: {', '.join(condition['tags'])}\n"
                f"Evidence IDs: {', '.join(condition['evidence_ids'])}"
            ),
            _condition_l1_sections(condition, evid_lookup, metadata),
        )

    # ── mechanisms cards ─────────────────────────────────────────────────────
    for mechanism in MECHANISMS:
        write_memory_card(
            clean_dir / "memory_cards" / "mechanisms" / mechanism["id"],
            f"{mechanism['id']}: {mechanism['title']}",
            (
                f"L0 type: mechanism. {mechanism['summary']}\n\n"
                f"Tags: {', '.join(mechanism['tags'])}\n"
                f"Evidence IDs: {', '.join(mechanism['evidence_ids'])}"
            ),
            _mechanism_l1_sections(mechanism, evid_lookup, metadata),
        )


def write_figure_cards(clean_dir: Path, figures: list[Figure]) -> None:
    for figure in figures:
        card_dir = clean_dir / "memory_cards" / "figures" / figure.figure_id
        image_lines = [f"- `{path}`" for path in figure.clean_images]
        write_text(
            card_dir / ".abstract.md",
            f"""# {figure.figure_id}: {figure.title}

L0 type: figure
Figure number: Fig. {figure.figure_number}
Evidence ID: {figure.evidence_id}

This figure is a scientific figure from the paper and is useful for retrieving visual evidence about `{figure.title}`.

L1 entry: `.overview.md`
Image references: `image_ref.md`
""",
        )
        write_text(
            card_dir / ".overview.md",
            f"""# {figure.figure_id}: {figure.title}

## Caption

{figure.caption}

## Evidence

Evidence ID: `{figure.evidence_id}`

Source clean text: `full_clean.md`

Source raw figure line: {figure.source_line_start}

## Image Storage Rule

This card does not contain duplicated image files. Actual clean image files are stored once in root `figures/`.

## Clean Image Paths

{markdown_list([f'`{path}`' for path in figure.clean_images]) if figure.clean_images else '- No clean image copied; check `image_manifest.json`.'}
""",
        )
        write_text(card_dir / "caption.md", f"# Caption\n\n{figure.caption}")
        write_text(
            card_dir / "figure.card.md",
            f"""# Figure Card

Figure ID: `{figure.figure_id}`

Figure number: Fig. {figure.figure_number}

Title: {figure.title}

Evidence ID: `{figure.evidence_id}`

Retrieval tags: figure, scientific_image, electrocatalysis, hydrogen_energy

Purpose: Use this card when the question needs visual evidence from Fig. {figure.figure_number}, especially catalyst degradation, HER performance, passivation mechanism, structural evolution or DFT mechanism depending on the figure title.
""",
        )
        write_text(
            card_dir / "image_ref.md",
            "# Image References\n\n"
            "Actual images are stored once in root `figures/`; they are not duplicated in this card.\n\n"
            + ("\n".join(image_lines) if image_lines else "- No image reference."),
        )


def build_structured_json(metadata: dict[str, Any], figures: list[Figure], evidence: list[Evidence]) -> dict[str, Any]:
    return {
        "paper_metadata": {
            "paper_id": metadata["paper_id"],
            "title": metadata["title"],
            "doi": metadata["doi"],
            "doi_url": metadata["doi_url"],
            "year": metadata["year"],
            "journal": metadata["journal"],
            "authors_raw": metadata["authors_raw"],
            "raw_paths": metadata["raw_paths"],
        },
        "study_summary": {
            "problem": "Intermittent renewable electricity causes start-shutdown cycles that degrade seawater electrolysis cathodes.",
            "solution": "NiCoP-Cr2O3 cathode with in situ phosphate/oxide passivation layer.",
            "main_result": "10,000 h intermittent alkaline seawater electrolysis at 0.5 A cm-2 with low voltage increase.",
            "evidence_ids": ["EVID001", "EVID002", "EVID003", "EVID008"],
        },
        "domain_classification": {
            "primary_domain": "electrocatalysis",
            "secondary_domains": ["hydrogen_energy", "materials_science"],
            "openviking_tags": {
                "domain": ["electrocatalysis", "hydrogen_energy", "materials_science"],
                "document_type": ["research_article"],
                "method_type": ["electrochemical_measurement", "operando_Raman", "TOF-SIMS", "HAADF-STEM", "DFT"],
                "object_type": ["NiCoP-Cr2O3 cathode", "alkaline seawater electrolyser"],
                "result_type": ["stability", "overpotential", "passivation_mechanism"],
                "domain_tags": ["HER", "alkaline_seawater", "passivation_layer", "chloride_resistance"],
            },
        },
        "content_structure": {
            "clean_full_text": "full_clean.md",
            "paper_l0": ".abstract.md",
            "paper_l1": ".overview.md",
            "memory_cards_root": "memory_cards/",
            "evidence_index": "evidence_links.json",
        },
        "methods": {
            "items": [
                {"name": "electrochemical measurement", "evidence_ids": ["EVID006", "EVID007"]},
                {"name": "AEM electrolyser measurement", "evidence_ids": ["EVID006", "EVID009"]},
                {"name": "operando Raman", "evidence_ids": ["EVID011"]},
                {"name": "TOF-SIMS/XPS/HAADF-STEM", "evidence_ids": ["EVID010", "EVID012"]},
                {"name": "DFT and CI-NEB", "evidence_ids": ["EVID013"]},
            ]
        },
        "objects_or_systems": {
            "items": [
                {"name": "NiCoP-Cr2O3 cathode", "role": "HER cathode", "evidence_ids": ["EVID002", "EVID005"]},
                {"name": "alkaline seawater electrolyser", "role": "test system", "evidence_ids": ["EVID008", "EVID009"]},
                {"name": "AEM electrolyser", "role": "device validation", "evidence_ids": ["EVID006"]},
            ]
        },
        "experiments_or_cases": {
            "items": CONDITIONS,
        },
        "results": {
            "metrics": METRICS,
            "main_evidence_ids": ["EVID003", "EVID007", "EVID008", "EVID009"],
        },
        "key_claims": CLAIMS,
        "figures": [
            {
                "figure_id": figure.figure_id,
                "figure_number": figure.figure_number,
                "title": figure.title,
                "caption": figure.caption,
                "clean_images": figure.clean_images,
                "evidence_id": figure.evidence_id,
            }
            for figure in figures
        ],
        "tables": [],
        "evidence_links": "evidence_links.json",
        "domain_specific": {
            "electrocatalysis": {
                "materials": [
                    {"name": "NiCoP-Cr2O3", "role": "HER cathode", "evidence_ids": ["EVID002", "EVID005"]},
                    {"name": "NiCoFeP/NiFeP", "role": "anode-related materials", "evidence_ids": ["EVID006", "EVID009"]},
                ],
                "electrochemical_system": {
                    "electrolyte": ["1 M NaOH + seawater", "20 wt% NaOH + seawater", "1 M KOH"],
                    "cell_types": ["three-electrode HER test", "full water electrolysis cell", "AEM electrolyser"],
                    "evidence_ids": ["EVID006", "EVID008", "EVID009"],
                },
                "operating_conditions": CONDITIONS,
                "electrochemical_metrics": METRICS,
                "degradation_mechanisms": [
                    {"name": "shutdown cathodic discharge and oxidation", "evidence_ids": ["EVID004"]},
                    {"name": "halide adsorption/corrosion during shutdown", "evidence_ids": ["EVID001", "EVID011"]},
                ],
                "protection_strategies": [
                    {"name": "in situ phosphate/oxide passivation layer", "evidence_ids": ["EVID002", "EVID010", "EVID011"]},
                    {"name": "Cr2O3-assisted outer passivation", "evidence_ids": ["EVID005", "EVID012"]},
                ],
            }
        },
        "extraction_quality": {
            "mode": "semi_automatic",
            "review_required": True,
            "known_limitations": [
                "Page numbers are estimated from MinerU page grouping and should be manually verified against the PDF.",
                "Formula OCR artifacts from MinerU are preserved in full_clean.md for traceability.",
                "Figure panels are copied once to root figures/; figure cards reference them rather than duplicating images.",
            ],
        },
    }


def evidence_to_json(evidence: list[Evidence], metadata: dict[str, Any], figures: list[Figure]) -> list[dict[str, Any]]:
    figure_by_id = {figure.figure_id: figure for figure in figures}
    items: list[dict[str, Any]] = []
    for item in evidence:
        record = {
            "evidence_id": item.evidence_id,
            "kind": item.kind,
            "title": item.title,
            "source_path": metadata["raw_paths"]["full_md"],
            "source_pdf": metadata["raw_paths"]["origin_pdf"],
            "source_line_start": item.source_line_start,
            "source_line_end": item.source_line_end,
            "page_estimate": item.page_estimate,
            "source_excerpt": item.source_excerpt,
            "related_figures": item.related_figures,
            "related_tables": item.related_tables,
            "tags": item.tags,
        }
        if item.related_figures:
            figure = figure_by_id.get(item.related_figures[0])
            if figure:
                record["clean_image_paths"] = figure.clean_images
                record["raw_image_paths"] = figure.raw_images
        items.append(record)
    return items


def parse_tables(mineru_dir: Path, lines: list[str]) -> list[Table]:
    """Extract tables from a MinerU output directory.

    Two sources (merged, deduped by table number):
    1. content_list_v2.json – has ``table_caption`` and ``html`` for each table
       item; also supplies a rendered image path.
    2. full.md HTML blocks – ``<table>…</table>`` found inline in the Markdown.

    Returns a list of Table dataclass instances ordered by table number.
    """
    tables: list[Table] = []
    seen: set[str] = set()

    # ── Source 1: content_list_v2.json ───────────────────────────────────────
    content_items = load_content_list(mineru_dir)
    tab_counter_json = 0
    for item in content_items:
        if item.get("type") != "table":
            continue
        content = item.get("content", {})
        if not isinstance(content, dict):
            continue

        img_path: str = content.get("image_source", {}).get("path", "")
        caption_parts: list = content.get("table_caption", [])
        caption_text = _join_caption_parts(caption_parts).strip()
        html_content: str = content.get("html", "")

        # Try to infer table number from caption
        num_match = re.search(r"\bTable\s+(\d+)", caption_text, re.IGNORECASE)
        if num_match:
            tab_num = int(num_match.group(1))
        else:
            tab_counter_json += 1
            tab_num = tab_counter_json

        tab_id = f"TAB{tab_num:03d}"
        if tab_id in seen:
            continue
        seen.add(tab_id)

        # Clean caption: remove embedded number artefacts
        clean_caption = re.sub(r"\bTable\s+\d+\.", f"Table {tab_num}.", caption_text)
        # Short title
        title_body = re.sub(
            r"^Table\s+\d+\.?\s*", "", clean_caption, flags=re.IGNORECASE
        ).strip()
        title = title_body[:120].strip() if title_body else f"Table {tab_num}"

        tables.append(Table(
            table_id=tab_id,
            table_number=str(tab_num),
            title=title,
            caption=clean_caption,
            html_content=html_content,
            raw_images=[img_path] if img_path else [],
            evidence_id=f"EVID_TAB{tab_num:03d}",
        ))

    # ── Source 2: HTML <table> blocks in full.md ──────────────────────────────
    html_block_re = re.compile(r"<table[\s>].*?</table>", re.DOTALL | re.IGNORECASE)
    tab_caption_re = re.compile(
        r"(?:^|\n)\s*(?:Table|Tab\.)\s+(\d+)[\s.|:](.+?)(?=\n|$)", re.IGNORECASE
    )
    full_text = "\n".join(lines)
    tab_counter_html = len(tables)
    for m in html_block_re.finditer(full_text):
        html_str = m.group(0)
        # Look for a caption in the 2 lines before this HTML block
        start_pos = max(0, m.start() - 300)
        context_before = full_text[start_pos: m.start()]
        cap_m = tab_caption_re.search(context_before)
        if cap_m:
            tab_num = int(cap_m.group(1))
            caption_text = compact_text(f"Table {tab_num}. {cap_m.group(2).strip()}")
        else:
            # Also look just after the closing </table>
            context_after = full_text[m.end(): m.end() + 300]
            cap_m2 = re.search(
                r"(?:Table|Tab\.)\s+(\d+)[\s.|:](.+?)(?=\n|$)",
                context_after, re.IGNORECASE
            )
            if cap_m2:
                tab_num = int(cap_m2.group(1))
                caption_text = compact_text(
                    f"Table {tab_num}. {cap_m2.group(2).strip()}"
                )
            else:
                tab_counter_html += 1
                tab_num = tab_counter_html
                caption_text = f"Table {tab_num}"

        tab_id = f"TAB{tab_num:03d}"
        if tab_id in seen:
            # Already captured from JSON; enrich with HTML if missing
            for t in tables:
                if t.table_id == tab_id and not t.html_content:
                    t.html_content = html_str
            continue
        seen.add(tab_id)

        title = re.sub(r"^Table\s+\d+\.?\s*", "", caption_text, flags=re.IGNORECASE).strip()
        tables.append(Table(
            table_id=tab_id,
            table_number=str(tab_num),
            title=title[:120],
            caption=caption_text,
            html_content=html_str,
            raw_images=[],
            source_line_start=full_text[:m.start()].count("\n") + 1,
            evidence_id=f"EVID_TAB{tab_num:03d}",
        ))

    tables.sort(key=lambda t: int(t.table_number))
    return tables


def copy_table_images(tables: list[Table], mineru_dir: Path, clean_dir: Path) -> None:
    """Copy rendered table images (from MinerU) into tables/."""
    tables_dir = clean_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    for table in tables:
        table_dir = tables_dir / table.table_id
        table_dir.mkdir(parents=True, exist_ok=True)
        for raw_rel, clean_rel in zip(table.raw_images, _table_clean_image_relpaths(table)):
            src = mineru_dir / raw_rel
            if not src.exists() or not src.is_file():
                continue
            dst = clean_dir / clean_rel
            if not dst.exists():
                shutil.copy2(src, dst)


def write_table_manifest(clean_dir: Path, tables: list[Table] | None = None) -> None:
    """Write tables/ content and table_manifest.json.

    Each Table is saved as:
            tables/TABxxx/table.md   – Markdown table body
            tables/TABxxx/caption.md – Caption text
            tables/TABxxx/image_XXX  – Rendered image(s) if provided by MinerU
    """
    tables_dir = clean_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    if not tables:
        write_json(
            clean_dir / "table_manifest.json",
            {
                "status": "no_tables_detected",
                "tables": [],
                "note": (
                    "No tables were detected in this MinerU output. "
                    "MinerU may have rendered tables as images only, or the paper "
                    "contains no main-text tables. Check image_manifest.json for "
                    "entries with table-related file names."
                ),
            },
        )
        return

    manifest_entries: list[dict[str, Any]] = []
    for table in tables:
        table_dir = tables_dir / table.table_id
        table_dir.mkdir(parents=True, exist_ok=True)
        clean_image_paths = _table_clean_image_relpaths(table)

        # Write Markdown file
        md_lines = [f"# {table.table_id}: {table.title}", ""]
        if table.html_content:
            md_table = html_table_to_markdown(table.html_content)
            md_lines.append(md_table)
        else:
            md_lines.append("*(Table content not extracted — see rendered image)*")

        if clean_image_paths:
            md_lines += ["", "**Rendered images:**"]
            for img in clean_image_paths:
                md_lines.append(f"- `{img}`")

        write_text(table_dir / "table.md", "\n".join(md_lines))
        write_text(table_dir / "caption.md", f"# Caption\n\n{table.caption}\n")

        manifest_entries.append({
            "table_id": table.table_id,
            "table_number": table.table_number,
            "title": table.title,
            "caption": table.caption,
            "evidence_id": table.evidence_id,
            "table_dir": f"tables/{table.table_id}/",
            "markdown_path": f"tables/{table.table_id}/table.md",
            "caption_path": f"tables/{table.table_id}/caption.md",
            "clean_image_paths": clean_image_paths,
            "raw_images": table.raw_images,
            "has_html": bool(table.html_content),
        })

    write_json(
        clean_dir / "table_manifest.json",
        {
            "status": "extracted",
            "table_count": len(tables),
            "tables": manifest_entries,
        },
    )


def write_table_memory_cards(
    clean_dir: Path,
    tables: list[Table],
    paper_id: str,
) -> None:
    """Write memory_cards/tables/TABxxx/ for each extracted table.

    Each table gets four files:
      .abstract.md  — L0 quick-recall card for OpenViking search
      .overview.md  — L1 detailed card with paths, caption, evidence_id
      table.card.md — Human-editable interpretation & evidence notes
    """
    for table in tables:
        card_dir = clean_dir / "memory_cards" / "tables" / table.table_id
        card_dir.mkdir(parents=True, exist_ok=True)

        # ── .abstract.md (L0) ─────────────────────────────────────────────
        write_text(
            card_dir / ".abstract.md",
            f"""# {table.table_id}: {table.title}

L0 type: table
Table number: Table {table.table_number}
Evidence ID: {table.evidence_id}
Paper: {paper_id}

{table.caption[:300]}{"..." if len(table.caption) > 300 else ""}

L1 entry: `.overview.md`
Table content: `../../tables/{table.table_id}.md`
""",
        )

        # ── .overview.md (L1) ─────────────────────────────────────────────
        img_refs = ""
        if table.raw_images:
            img_refs = "\n## Rendered Images\n\n" + "\n".join(
                f"- `../../tables/{table.table_id}_{i:02d}{Path(img).suffix or '.jpg'}`"
                for i, img in enumerate(table.raw_images, start=1)
            )

        write_text(
            card_dir / ".overview.md",
            f"""# {table.table_id}: {table.title}

## What This Card Answers

This card provides structured access to **Table {table.table_number}** from the parent paper.
Query this card for tabular data, numerical comparisons, experimental parameters, or referenced values.

## Caption

{table.caption}

## Evidence

Evidence ID: `{table.evidence_id}`

Source paper: `{paper_id}`

Source clean text: `../../full_clean.md`

## Table Content

Full table (Markdown): `../../tables/{table.table_id}.md`
{img_refs}
## Image Storage Rule

Rendered table images are stored once in `tables/`. This card references them only.

## Related Files

- `../../structured.json` — structured.tables array
- `../../evidence_links.json` — evidence index
- `../../table_manifest.json` — table registry
""",
        )

        # ── table.card.md (human-editable enrichment) ─────────────────────
        has_html_note = (
            "Table HTML was extracted from MinerU and converted to Markdown."
            if table.html_content
            else "Table was captured as rendered image only; no HTML available."
        )
        write_text(
            card_dir / "table.card.md",
            f"""# Table Card: {table.table_id}

**Title:** {table.title}

**Caption:** {table.caption}

**Evidence ID:** `{table.evidence_id}`

**Paper:** `{paper_id}`

## Content Reference

See full table: `../../tables/{table.table_id}.md`

## Extraction Notes

{has_html_note}

## Key Observations

*(Manual enrichment: add key rows, column meanings, comparison insights, and links to related figures here.)*

## Retrieval Tags

table, tabular-data, {table.table_id}
""",
        )


# ============================================================================
# NEW PIPELINE: sections/ structure, document_tree, paragraph_index
# (replaces memory_cards/ generation from the old pipeline)


def split_into_sections(clean_text: str) -> "list[dict[str, Any]]":
    """Split clean markdown text at chapter-level headings only.

    Uses three strategies in order:
      A. Numbered headings (1., 1.1, 1.1.1) → depth=1 is chapter
      B. ALL-CAPS headings → chapter; mixed-case → sub-section
      C. Keyword matching (Introduction, Methods, Results, Discussion,
         Conclusion, Experimental, Background)

    Sub-section headings are kept in the chapter text as paragraphs,
    not split into separate sections.
    """
    import re

    heading_re = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_re.finditer(clean_text))

    if len(matches) < 2:
        return [{"heading_text": "Full Text", "text": clean_text,
                 "level": 1, "heading_order": 1}]

    titles = [m.group(2).strip() for m in matches]

    # ── Strategy A: numbered headings ──────────────────────────────
    _NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s")
    _CN_NUM_RE = re.compile(r"^（([一二三四五六七八九十]+)）")
    numbered = [_NUM_RE.match(t) for t in titles]
    cn_numbered = [_CN_NUM_RE.match(t) for t in titles]

    if sum(1 for n in numbered if n) >= 2:
        # Depth = number of dot-separated parts
        depths = [len(n.group(1).split(".")) if n else 99 for n in numbered]
        chapter_indices = [i for i, d in enumerate(depths) if d == 1]
        if not chapter_indices:
            # No depth-1: group by first-level number (1.x→1, 2.x→2)
            group_nums = {}
            for i, n in enumerate(numbered):
                if n:
                    first = n.group(1).split(".")[0]
                    if first not in group_nums:
                        group_nums[first] = i
            chapter_indices = sorted(group_nums.values())
        return _build_sections(clean_text, matches, chapter_indices)

    if sum(1 for c in cn_numbered if c) >= 2:
        chapter_indices = [i for i, c in enumerate(cn_numbered) if c]
        return _build_sections(clean_text, matches, chapter_indices)

    # ── Strategy B: ALL-CAPS detection ─────────────────────────────
    _CAPS_RE = re.compile(r"^[A-Z][A-Z\s\-/]{4,}$")
    caps = [_CAPS_RE.match(t) for t in titles]
    if sum(1 for c in caps if c) >= 2:
        chapter_indices = [i for i, c in enumerate(caps) if c]
        return _build_sections(clean_text, matches, chapter_indices)

    # ── Strategy C: keyword matching + content volume ──────────────
    _CHAPTER_KW = [
        "introduction", "intro", "background",
        "experimental", "method", "methods",
        "result", "results", "results and discussion",
        "discussion", "discussions",
        "conclusion", "conclusions", "summary",
        "mechanism", "activity and stability",
        "theoretical", "computation",
    ]
    chapter_indices = []
    for i, t in enumerate(titles):
        low = re.sub(r"^\d+(?:\.\d+)*\s*", "", t.strip().lower())
        if any(kw in low for kw in _CHAPTER_KW):
            chapter_indices.append(i)
            continue
        # Fallback: heading with large content (>2200 chars) is likely a chapter
        if i > 0:  # skip paper title
            start = matches[i].start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(clean_text)
            if end - start > 2200:
                chapter_indices.append(i)

    if len(chapter_indices) >= 2:
        return _build_sections(clean_text, matches, chapter_indices)

    # ── Fallback: use all headings ─────────────────────────────────
    chapter_indices = list(range(1, len(matches)))
    return _build_sections(clean_text, matches, chapter_indices)


def _build_sections(
    clean_text: str,
    matches: "list[re.Match]",
    chapter_indices: "list[int]",
) -> "list[dict[str, Any]]":
    """Build section dicts from heading match indices."""
    import re

    chapters = [c for c in chapter_indices if c > 0]  # skip index 0 (paper title)
    # Pre-content before first chapter heading
    first_chapter = chapters[0] if chapters else 1
    pre_text = clean_text[:matches[first_chapter].start()].strip()

    sections = []
    heading_order = 0

    # Front-matter (title page info)
    if pre_text:
        heading_order += 1
        sections.append({
            "heading_text": matches[0].group(2).strip(),
            "text": pre_text,
            "level": len(matches[0].group(1)),
            "heading_order": heading_order,
        })

    for ci in chapters:
        heading_order += 1
        heading_text = matches[ci].group(2).strip()
        start_pos = matches[ci].start()

        # End position: next chapter heading, or end of text
        end_pos = len(clean_text)
        for ni in chapters:
            if ni > ci:
                end_pos = matches[ni].start()
                break

        section_text = clean_text[start_pos:end_pos].strip()
        if section_text:
            # Strip the heading line itself from section text
            heading_line_end = section_text.find("\n")
            if heading_line_end > 0:
                section_text = section_text[heading_line_end:].strip()

        if section_text:
            sections.append({
                "heading_text": heading_text,
                "text": section_text,
                "level": len(matches[ci].group(1)),
                "heading_order": heading_order,
            })

    return sections
def split_section_paragraphs(
    section_text: str,
    section_id: str,
    paper_id: str,
    pages: "list[str]",
    original_heading: str,
    macro_section_title: str,
    macro_keywords: "list[str]",
    start_order: int = 0,
) -> "list[dict[str, Any]]":
    """Split section body text into natural paragraphs.

    Returns list of dicts with keys:
      paragraph_id, order, text, page_estimate, linked_figures, linked_tables
    """
    raw_blocks = re.split(r"\n{2,}", section_text)
    valid: "list[dict[str, Any]]" = []
    order = start_order
    para_in_heading = 0
    sec_prefix = section_id.split("_")[0]  # e.g. "S04"

    for block in raw_blocks:
        block = block.strip()
        if not block or len(block) < 40:
            continue
        # Skip heading-only lines (no body)
        if re.match(r"^#{1,6}\s+\S[^\n]*$", block):
            continue
        # Skip noise patterns
        skip = any(pat.match(block) for pat in _PARA_NOISE_RES)
        if skip:
            continue

        order += 1
        para_in_heading += 1
        para_id = f"{sec_prefix}-P{order:03d}"
        linked_figs = _detect_linked_figures(block)
        linked_tabs = _detect_linked_tables(block)
        page = estimate_page(block[:200], pages)

        valid.append({
            "paragraph_id": para_id,
            "order": order,
            "text": block,
            "page_estimate": page,
            "macro_section_id": section_id,
            "macro_section_title": macro_section_title,
            "original_heading": original_heading,
            "linked_figures": linked_figs,
            "linked_tables": linked_tabs,
            "keywords": _extract_paragraph_keywords(block, original_heading, macro_keywords),
            "paragraph_in_heading": para_in_heading,
            "token_count": len(re.findall(r"\S+", block)),
        })

    return valid



def build_sections_data(
    clean_text: str,
    paper_id: str,
    pages: "list[str]",
    recovery_hints: "dict[str, Any] | None" = None,
) -> "list[dict[str, Any]]":
    """Split into chapter-level sections and process paragraphs.

    No macro classification, no S00-S07, no detector-based recovery.
    Paragraphs stay in their original chapter section.
    """
    sections = split_into_sections(clean_text)
    paragraph_uid_seq = 0

    for sec in sections:
        heading_order = sec.get("heading_order", 1)
        heading_text = sec.get("heading_text", "")
        heading_level = sec.get("level", 2)
        heading_uid_seed = f"{heading_order}:{heading_text}"
        heading_uid = f"HRAW-{heading_order:03d}-{hashlib.sha1(heading_uid_seed.encode('utf-8')).hexdigest()[:8]}"

        paras_all = []
        para_order = 0

        # Split section text into paragraphs (double-newline boundaries)
        para_texts = [t.strip() for t in sec.get("text", "").split("\n\n") if t.strip()]
        for pt in para_texts:
            # Skip noise: isolated image links, sub-figure labels (a/b/c/I/II/III)
            stripped = pt.strip()
            if re.match(r"^!\[\]\([^)]+\)$", stripped):
                continue
            if re.match(r"^[a-fA-F]?\s*(I|II|III|IV|V|VI|VII|VIII|IX|X)\s*$", stripped):
                continue
            if re.match(r"^[a-fA-F]\s*$", stripped):
                continue
            para_order += 1
            paragraph_uid_seq += 1
            page_estimate = estimate_page(pt, pages) if pages else None

            para = {
                "section_id": f"S{heading_order:02d}",
                "section_title": heading_text,
                "heading_id": f"H{heading_order:02d}",
                "heading_order": heading_order,
                "heading_uid": heading_uid,
                "heading_text": heading_text,
                "heading_level": heading_level,
                "doc_heading_order": heading_order,
                "paragraph_id": f"S{heading_order:02d}-P{para_order:03d}",
                "paragraph_uid": f"PRAW-{paragraph_uid_seq:06d}",
                "paragraph_in_heading": para_order,
                "paragraph_order": para_order,
                "text": pt,
                "text_preview": pt[:200],
                "inferred_type": "none",
                "page_estimate": page_estimate,
                "source_heading_uid": heading_uid,
                "source_heading_display_order": heading_order,
                "source_heading_text": heading_text,
                "source_heading_level": heading_level,
                "source_doc_heading_order": heading_order,
                "source_block_order": para_order,
                "source_section_id": heading_text,
                "source_section_title": heading_text,
                "keywords": [],
                "linked_figures": [],
                "linked_tables": [],
                "token_count": len(pt.split()),
                "paper_id": paper_id,
                "page_index": page_estimate,
            }
            paras_all.append(para)

        sec["paragraphs"] = paras_all
        sec["heading_uid"] = heading_uid
        sec["heading_id"] = f"H{heading_order:02d}"
        sec["section_id"] = f"S{heading_order:02d}"
        sec["section_title"] = heading_text

    return sections


# ===========================================================================
# 2. _build_heading_dirname (unchanged from original)
# ===========================================================================
# This is defined elsewhere in the file, not replaced here


# ===========================================================================
# 3. write_sections_dir (simplified: no detectors)
# ===========================================================================
def write_sections_dir(
    clean_dir: "Path",
    paper_id: str,
    sections: "list[dict[str, Any]]",
    metadata: "dict[str, Any]",
    clean_doi: str = "",
    evidence_short_ids: "dict[str, str] | None" = None,
) -> None:
    """Write sections_by_heading/ directory tree (chapter-level only).

    Each section gets a directory with:
      - heading.json
      - paragraphs.md (index)
      - paragraphs/{paragraph_uid}.md (individual paragraph files)
    """
    import json
    from pathlib import Path

    sbh_root = clean_dir / "sections_by_heading"
    sbh_root.mkdir(parents=True, exist_ok=True)

    heading_index_entries = []
    evidence_lookup: dict[str, str] = {}

    for sec in sections:
        # Build directory name from heading text
        heading_text = sec.get("heading_text", "Untitled")
        heading_order = sec.get("heading_order", 1)
        slug = _heading_slugify(heading_text)
        dirname = f"{heading_order:03d}-{slug}"
        sec_dir = sbh_root / dirname
        sec_dir.mkdir(parents=True, exist_ok=True)

        # heading.json
        hinfo = {
            "paper_id": paper_id,
            "heading_uid": sec.get("heading_uid", ""),
            "heading_id": sec.get("heading_id", f"H{heading_order:02d}"),
            "heading_text": heading_text,
            "heading_level": sec.get("level", 2),
            "heading_order": heading_order,
        }
        write_json(sec_dir / "heading.json", hinfo)

        # paragraphs/
        paras = sec.get("paragraphs", [])
        paras_dir = sec_dir / "paragraphs"
        paras_dir.mkdir(parents=True, exist_ok=True)

        para_index_lines = [f"# Section: {heading_text}\n"]
        for p in paras:
            puid = p.get("paragraph_uid", "")
            pid = p.get("paragraph_id", "")
            ev_id = p.get("evidence_id", _paragraph_evidence_id(paper_id, pid))
            p["evidence_id"] = ev_id
            evidence_lookup[pid] = ev_id

            # Write individual paragraph file
            para_path = paras_dir / f"{puid}.md"
            para_content = _format_paragraph_md(p, paper_id)
            write_text(para_path, para_content)
            p["content_path"] = str(para_path.relative_to(clean_dir))

            # Index line
            text_preview = p.get("text_preview", p.get("text", "")[:120])
            para_index_lines.append(f"- **{pid}** ({puid}): {text_preview}")

        # paragraphs.md index file
        write_text(sec_dir / "paragraphs.md", "\n".join(para_index_lines))

        heading_index_entries.append({
            "dirname": dirname,
            "heading_uid": sec.get("heading_uid", ""),
            "heading_text": heading_text,
            "heading_order": heading_order,
            "paragraph_count": len(paras),
        })

    # heading_index.json
    write_json(sbh_root / "heading_index.json", heading_index_entries)


# ===========================================================================
# 4. build_document_tree (simplified: no macro_tags)
# ===========================================================================
def build_document_tree(
    paper_id: str,
    metadata: "dict[str, Any]",
    sections: "list[dict[str, Any]]",
) -> dict[str, Any]:
    """Build document tree from chapter-level sections (no macro_tags)."""
    tree = {
        "paper_id": paper_id,
        "sections": [],
    }
    for sec in sections:
        heading_order = sec.get("heading_order", 0)
        tree["sections"].append({
            "heading_uid": sec.get("heading_uid", ""),
            "heading_id": sec.get("heading_id", f"H{heading_order:02d}"),
            "heading_text": sec.get("heading_text", ""),
            "heading_order": heading_order,
            "paragraph_count": len(sec.get("paragraphs", [])),
            "paragraph_ids": [p.get("paragraph_id", "") for p in sec.get("paragraphs", [])],
        })
    return tree


# ===========================================================================
# 5. build_paragraph_index (simplified: no macro fields)
# ===========================================================================
def build_paragraph_index(
    paper_id: str,
    sections: "list[dict[str, Any]]",
    metadata: "dict[str, Any]",
    evidence_short_ids: "dict[str, str] | None" = None,
) -> list[dict[str, Any]]:
    """Build flat paragraph index from chapter-level sections.

    paragraph_id format: H{heading_order:02d}-P{paragraph_order:03d}
    section_id: heading text
    No macro_primary/macro_secondary/macro_confidence/macro_trace/macro_conflict.
    """
    index = []
    for sec in sections:
        heading_order = sec.get("heading_order", 0)
        heading_text = sec.get("heading_text", "")
        heading_uid = sec.get("heading_uid", "")

        for p in sec.get("paragraphs", []):
            pid = p.get("paragraph_id", "")
            ev_id = p.get("evidence_id", _paragraph_evidence_id(paper_id, pid))
            p["evidence_id"] = ev_id

            index.append({
                "paper_id": paper_id,
                "section_id": sec.get("section_id", f"S{heading_order:02d}"),
                "section_title": heading_text,
                "heading_id": f"H{heading_order:02d}",
                "heading_uid": heading_uid,
                "heading_text": heading_text,
                "heading_level": sec.get("level", 2),
                "heading_order": heading_order,
                "doc_heading_order": heading_order,
                "paragraph_id": pid,
                "paragraph_uid": p.get("paragraph_uid", ""),
                "paragraph_order": p.get("paragraph_order", 0),
                "content_path": p.get("content_path", ""),
                "text_preview": p.get("text_preview", ""),
                "evidence_id": ev_id,
                "evidence_short_id": "",
                "linked_figures": p.get("linked_figures", []),
                "linked_tables": p.get("linked_tables", []),
                "keywords": p.get("keywords", []),
                "token_count": p.get("token_count", 0),
                "inferred_type": p.get("inferred_type", "none"),
                "page_index": p.get("page_estimate"),
                "page_number": p.get("page_estimate"),
                "source_pdf_path": metadata.get("raw_paths", {}).get("source_pdf", ""),
            })

    return index


# ===========================================================================
# 6. Helper: format paragraph markdown
# ===========================================================================
def _format_paragraph_md(p: dict[str, Any], paper_id: str) -> str:
    """Format a paragraph as a .md file for sections_by_heading."""
    lines = [
        f"# Paragraph {p.get('paragraph_uid', '')}",
        "",
        f"Paper ID: {paper_id}",
        f"Heading UID: {p.get('heading_uid', '')}",
        f"Heading Text: {p.get('heading_text', '')}",
        f"Heading Level: {p.get('heading_level', 0)}",
        f"Doc Heading Order: {p.get('doc_heading_order', 0)}",
        f"Paragraph ID: {p.get('paragraph_id', '')}",
        f"Paragraph UID: {p.get('paragraph_uid', '')}",
        f"Page: {p.get('page_estimate', 'unknown')}",
        f"Evidence ID: {p.get('evidence_id', '')}",
        "",
        "## Text",
        "",
        p.get("text", ""),
        "",
        "## Linked Figures",
        "",
        "\n".join(f"- {fid}" for fid in p.get("linked_figures", [])) or "- none",
        "",
        "## Linked Tables",
        "",
        "\n".join(f"- {tid}" for tid in p.get("linked_tables", [])) or "- none",
        "",
        "## Keywords",
        "",
        ", ".join(p.get("keywords", [])),
        "",
        "## Source",
        "",
        "- source_pdf:",
        "- mineru_full_md:",
        "- mineru_content_list_v2:",
    ]
    return "\n".join(lines)


def build_original_structure_index(
    paper_id: str,
    sections: "list[dict[str, Any]]",
) -> "dict[str, Any]":
    """Build fact-layer heading/paragraph index in original reading order."""
    all_paras: list[dict[str, Any]] = []
    for sec in sections:
        for p in sec.get("paragraphs", []):
            all_paras.append(p)

    def _sort_key(p: dict[str, Any]) -> tuple[int, int, str]:
        return (
            int(p.get("source_doc_heading_order", 999999) or 999999),
            int(p.get("source_block_order", 999999) or 999999),
            str(p.get("paragraph_uid") or ""),
        )

    all_paras = sorted(all_paras, key=_sort_key)

    heading_map: dict[str, dict[str, Any]] = {}
    heading_seq: list[str] = []

    for p in all_paras:
        hid = str(p.get("source_heading_uid") or "")
        if not hid:
            continue
        if hid not in heading_map:
            heading_map[hid] = {
                "heading_uid": hid,
                "heading_text": p.get("source_heading_text") or p.get("original_heading") or "",
                "heading_level": p.get("source_heading_level"),
                "doc_heading_order": p.get("source_doc_heading_order"),
                "page_index": p.get("page_estimate"),
                "block_order": p.get("source_block_order"),
                "paragraph_uid_list": [],
                "inferred_type": "none",
            }
            heading_seq.append(hid)

        heading_map[hid]["paragraph_uid_list"].append(p.get("paragraph_uid"))

        if heading_map[hid].get("page_index") is None and p.get("page_estimate") is not None:
            heading_map[hid]["page_index"] = p.get("page_estimate")

        current = str(heading_map[hid].get("inferred_type") or "none")
        incoming = str(p.get("inferred_type") or "none")
        if current == "none" and incoming != "none":
            heading_map[hid]["inferred_type"] = incoming

    headings = [heading_map[hid] for hid in heading_seq]
    return {
        "paper_id": paper_id,
        "heading_count": len(headings),
        "paragraph_count": len(all_paras),
        "headings": headings,
    }



def _classify_evidence_type(section_id: str, linked_figures: list, linked_tables: list) -> str:
    """Classify evidence type based on linked figures/tables (no S00-S07 dependency)."""
    if linked_figures and linked_tables:
        return "figure_and_table"
    if linked_figures:
        return "figure"
    if linked_tables:
        return "table"
    return "paragraph"

def build_evidence_links_sections(
    paper_id: str,
    sections: "list[dict[str, Any]]",
    figures: "list[Figure]",
    tables: "list[Table]",
    metadata: "dict[str, Any]",
    evidence_short_ids: "dict[str, str] | None" = None,
) -> "list[dict[str, Any]]":
    """Build evidence_links.json (new paragraph-level + figure/table format)."""
    raw_paths = metadata.get("raw_paths", {})
    source_pdf = raw_paths.get("source_pdf", "")
    mineru_dir_s = raw_paths.get("mineru_output_dir", "")
    mineru_full_md = str(Path(mineru_dir_s) / "full.md") if mineru_dir_s else ""
    mineru_cl_v2 = str(Path(mineru_dir_s) / "content_list_v2.json") if mineru_dir_s else ""

    entries: "list[dict[str, Any]]" = []

    # Paragraph evidence entries
    for sec in sections:
        sid = sec["section_id"]
        title = sec["section_title"]
        for p in sec.get("paragraphs", []):
            pid = p["paragraph_id"]
            short_pid = pid.split("-", 1)[1]
            ev_id = _paragraph_evidence_id(paper_id, pid)
            ev_type = _classify_evidence_type(sid, p["linked_figures"], p["linked_tables"])
            entries.append({
                "evidence_id": ev_id,
                "evidence_short_id": evidence_short_ids.get(ev_id) if evidence_short_ids else None,
                "paper_id": paper_id,
                "section_id": sid,
                "section_title": title,
                "paragraph_id": pid,
                "page_number": p["page_estimate"],
                "content_path": f"sections_by_heading/{p.get('source_heading_dirname') or p.get('source_heading_uid')}/paragraphs/{p.get('paragraph_uid')}.md",
                "clean_text": p["text"][:1000],
                "evidence_type": ev_type,
                "linked_figures": p["linked_figures"],
                "linked_tables": p["linked_tables"],
                "source_pdf_path": source_pdf,
                "mineru_full_md_path": mineru_full_md,
                "mineru_content_list_v2_path": mineru_cl_v2,
            })

    # Figure evidence entries (retain EVID_FIG001 style)
    for fig in figures:
        ev_id = fig.evidence_id or _figure_evidence_id(paper_id, fig.figure_id)
        entries.append({
            "evidence_id": ev_id,
            "evidence_short_id": evidence_short_ids.get(ev_id) if evidence_short_ids else None,
            "paper_id": paper_id,
            "section_id": None,
            "paragraph_id": None,
            "page_number": None,
            "content_path": f"figures/{fig.figure_id}/",
            "clean_text": fig.caption[:500],
            "evidence_type": "figure",
            "figure_id": fig.figure_id,
            "figure_number": fig.figure_number,
            "caption": fig.caption,
            "linked_figures": [fig.figure_id],
            "linked_tables": [],
            "clean_images": fig.clean_images,
            "source_pdf_path": source_pdf,
            "mineru_full_md_path": mineru_full_md,
            "mineru_content_list_v2_path": mineru_cl_v2,
        })

    # Table evidence entries
    for tab in tables:
        ev_id = tab.evidence_id or _table_evidence_id(paper_id, tab.table_id)
        entries.append({
            "evidence_id": ev_id,
            "evidence_short_id": evidence_short_ids.get(ev_id) if evidence_short_ids else None,
            "paper_id": paper_id,
            "section_id": None,
            "paragraph_id": None,
            "page_number": None,
            "content_path": f"tables/{tab.table_id}/table.md",
            "clean_text": tab.caption[:500],
            "evidence_type": "table",
            "table_id": tab.table_id,
            "table_number": tab.table_number,
            "caption": tab.caption,
            "linked_figures": [],
            "linked_tables": [tab.table_id],
            "source_pdf_path": source_pdf,
            "mineru_full_md_path": mineru_full_md,
            "mineru_content_list_v2_path": mineru_cl_v2,
        })

    return entries


def enrich_image_manifest_with_paragraphs(
    image_manifest: "list[dict[str, Any]]",
    sections: "list[dict[str, Any]]",
) -> "list[dict[str, Any]]":
    """Add linked_paragraphs to each image_manifest entry by scanning paragraph figure refs."""
    fig_to_paras: "dict[str, list[str]]" = {}
    for sec in sections:
        for p in sec.get("paragraphs", []):
            for fid in p["linked_figures"]:
                fig_to_paras.setdefault(fid, []).append(p["paragraph_id"])
    return [{**e, "linked_paragraphs": fig_to_paras.get(e.get("figure_id", ""), [])} for e in image_manifest]


def build_quality_report(
    clean_dir: Path,
    paper_id: str,
    sections: "list[dict[str, Any]]",
    figures: "list[Figure]",
    tables: "list[Table]",
    metadata: "dict[str, Any]",
) -> "dict[str, Any]":
    """Generate quality_report.json."""
    all_paras = [p for s in sections for p in s.get("paragraphs", [])]
    total_paras = len(all_paras)

    def _ratio(count: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return round(count / total, 4)

    with_heading_uid = sum(1 for p in all_paras if p.get("source_heading_uid"))
    with_heading_text = sum(1 for p in all_paras if p.get("source_heading_text"))
    with_doc_heading_order = sum(1 for p in all_paras if p.get("source_doc_heading_order") is not None)
    with_page_index = sum(1 for p in all_paras if p.get("page_estimate") is not None)
    with_block_order = sum(1 for p in all_paras if p.get("source_block_order") is not None)
    with_paragraph_uid = sum(1 for p in all_paras if p.get("paragraph_uid"))

    reference_paragraph_count = sum(1 for p in all_paras if len(p.get("text", "").split()) < 20)
    generated = [f for f in [
        "metadata.json", "full_clean.md", "document_tree.json",
        "paragraph_index.json", "evidence_links.json",
        "image_manifest.json", "table_manifest.json",
    ] if (clean_dir / f).exists()]
    heading_root = clean_dir / "sections_by_heading"
    if heading_root.exists() and heading_root.is_dir():
        generated.append("sections_by_heading/")

    warnings: "list[str]" = []
    soft_uncertain_items: "list[dict[str, Any]]" = []
    needs_manual_review_items: "list[dict[str, Any]]" = []
    if not sections:
        warnings.append("No sections detected in full_clean.md")
    if not figures:
        warnings.append("No figures detected")
    if not all_paras:
        warnings.append("No paragraphs extracted")

    return {
        "paper_id": paper_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_files": generated,
        "section_count": len(sections),
        "paragraph_count": len(all_paras),
        "figure_count": len(figures),
        "table_count": len(tables),
        "evidence_count": len(all_paras) + len(figures) + len(tables),
        "reference_paragraph_count": reference_paragraph_count,
        "sections_summary": [
            {"section_id": s["section_id"], "section_title": s["section_title"],
             "paragraph_count": len(s.get("paragraphs", []))}
            for s in sections
        ],
        "warnings": warnings,
        "fact_layer_coverage": {
            "total_paragraphs": total_paras,
            "with_paragraph_uid": with_paragraph_uid,
            "paragraph_uid_coverage": _ratio(with_paragraph_uid, total_paras),
            "with_heading_uid": with_heading_uid,
            "heading_uid_coverage": _ratio(with_heading_uid, total_paras),
            "with_heading_text": with_heading_text,
            "heading_text_coverage": _ratio(with_heading_text, total_paras),
            "with_doc_heading_order": with_doc_heading_order,
            "doc_heading_order_coverage": _ratio(with_doc_heading_order, total_paras),
            "with_page_index": with_page_index,
            "page_index_coverage": _ratio(with_page_index, total_paras),
            "with_block_order": with_block_order,
            "block_order_coverage": _ratio(with_block_order, total_paras),
        },
        "removed_noise_summary": "Filtered: empty blocks, <40 chars, heading-only, page numbers, noise patterns",
        "next_review_items": [
            "Verify page number estimates against source PDF",
            "Check figure-paragraph links (linked_figures in paragraph_index.json)",
            "Review section title mappings in document_tree.json",
            "Confirm no important paragraphs were filtered as noise",
        ],
        "missing_input_files": [],
    }


def write_processing_record(clean_dir: Path, metadata: dict[str, Any], figures: list[Figure], image_manifest: list[dict[str, Any]]) -> None:
    used_count = sum(1 for item in image_manifest if item["status"] == "used")
    uncertain_count = sum(1 for item in image_manifest if item["status"] == "uncertain")
    heading_root = clean_dir / "sections_by_heading"
    heading_dirs = sorted(d.name for d in heading_root.iterdir() if d.is_dir()) if heading_root.exists() else []
    tables_dir = clean_dir / "tables"
    table_dirs = sorted(d.name for d in tables_dir.iterdir() if d.is_dir()) if tables_dir.exists() else []
    write_text(
        clean_dir / "PROCESSING_RECORD.md",
        f"""# LiteratureClean Processing Record

Paper ID: `{metadata['paper_id']}`

Source MinerU directory:

```text
{metadata['raw_paths']['mineru_output_dir']}
```

Clean output directory:

```text
{clean_dir}
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

- Raw MinerU images remain untouched in `{metadata['raw_paths']['images_dir']}`.
- Clean figure copies are stored under `{clean_dir / 'figures'}` as `FIGxxx/image_XXX.*`.
- Clean table files are stored under `{clean_dir / 'tables'}` as `TABxxx/table.md`, `caption.md`, and optional rendered images.
- Heading directories generated: {len(heading_dirs)}
- Used image count: {used_count}
- Uncertain image count: {uncertain_count}
- Table directory count: {len(table_dirs)}

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

{markdown_list([f"`{heading_id}`" for heading_id in heading_dirs]) if heading_dirs else '- No heading directories generated.'}

## Figures Generated

{markdown_list([f"{figure.figure_id}: Fig. {figure.figure_number} | {figure.title} | images: {len(figure.clean_images)}" for figure in figures]) if figures else '- No figures extracted.'}

## Tables Generated

{markdown_list([f"`{table_id}`" for table_id in table_dirs]) if table_dirs else '- No table directories generated.'}

## Manual Review Items

- Verify estimated page numbers against the PDF.
- Check MinerU OCR artifacts in chemical formulas and units.
- Review whether all panel images assigned to each figure are correct.
- Check `subheading_index.json` grouping against original headings.
- Confirm figure/table links in `paragraph_index.json` and `evidence_links.json`.
""",
    )


def build_package(mineru_dir: Path, clean_root: Path, overwrite: bool = False) -> Path:
    mineru_dir = mineru_dir.resolve()
    clean_root = clean_root.resolve()
    full_md = mineru_dir / "full.md"
    if not full_md.exists():
        raise FileNotFoundError(f"Missing MinerU full.md: {full_md}")

    text = read_text(full_md)
    lines = text.splitlines()
    pages = load_content_pages(mineru_dir)
    content_items = load_content_list(mineru_dir)
    section_recovery_hints = build_section_recovery_hints(mineru_dir, content_items)
    metadata = extract_metadata(text, mineru_dir)
    paper_id = metadata["paper_id"]
    metadata["paper_short"] = _paper_short(paper_id)
    clean_dir = clean_root / paper_id

    if clean_dir.exists():
        if not overwrite:
            raise FileExistsError(f"Output directory already exists. Use --overwrite to rebuild: {clean_dir}")
        # Long-path-safe deletion: remove ov_index chunks first, then rmtree
        ov = clean_dir / "ov_index"
        if ov.exists():
            for f in ov.rglob("*"):
                if f.is_file():
                    try:
                        sp = str(f.resolve())
                        if sys.platform == "win32" and len(sp) > 259:
                            sp = "\\\\?\\" + sp
                        os.unlink(sp)
                    except OSError:
                        pass
            for d in sorted(ov.rglob("*"), reverse=True):
                if d.is_dir():
                    try:
                        sp = str(d.resolve())
                        if sys.platform == "win32" and len(sp) > 259:
                            sp = "\\\\?\\" + sp
                        os.rmdir(sp)
                    except OSError:
                        pass
            try:
                os.rmdir(str(ov.resolve()))
            except OSError:
                pass
        shutil.rmtree(clean_dir, ignore_errors=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    figures = parse_figures(lines, pages, mineru_dir)
    tables = parse_tables(mineru_dir, lines)
    _assign_runtime_evidence_ids(paper_id, figures, tables)
    raw_to_clean = copy_used_figure_images(figures, mineru_dir, clean_dir)
    image_manifest = build_image_manifest(mineru_dir, raw_to_clean, figures)
    copy_table_images(tables, mineru_dir, clean_dir)

    text_evidence = find_key_evidence(lines, pages)
    figure_evidence = build_figure_evidence(figures, lines, pages)
    evidence = text_evidence + figure_evidence

    metadata["clean_paths"] = {
        "clean_dir": str(clean_dir),
        "full_clean": str(clean_dir / "full_clean.md"),
        "figures_dir": str(clean_dir / "figures"),
        "tables_dir": str(clean_dir / "tables"),
        "sections_by_heading_dir": str(clean_dir / "sections_by_heading"),
        # Legacy paths kept for compatibility (no longer generated):
        # "paper_abstract": str(clean_dir / ".abstract.md"),
        # "paper_overview": str(clean_dir / ".overview.md"),
        # "memory_cards_dir": str(clean_dir / "memory_cards"),
    }
    metadata["processing"] = {
        "mode": "single_paper_semi_automatic",
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "script": str(Path(__file__).resolve()),
        "openviking_ingested": False,
        "batch_import": False,
        "section_recovery": {
            "content_list_hints": {
                "front_count": len(section_recovery_hints.get("front_snippets", [])),
                "abstract_count": len(section_recovery_hints.get("abstract_snippets", [])),
                "back_count": len(section_recovery_hints.get("back_snippets", [])),
            },
            "layout_json_available": bool(section_recovery_hints.get("layout_available", False)),
        },
    }

    clean_text = clean_full_markdown(lines, raw_to_clean, evidence)
    write_text(clean_dir / "full_clean.md", clean_text)

    # ── New sections pipeline ────────────────────────────────────────────────
    sections_data = build_sections_data(clean_text, paper_id, pages, recovery_hints=section_recovery_hints)
    evidence_short_ids = _build_evidence_short_id_map(paper_id, sections_data, figures, tables)
    write_sections_dir(clean_dir, paper_id, sections_data, metadata, evidence_short_ids=evidence_short_ids)
    image_manifest = enrich_image_manifest_with_paragraphs(image_manifest, sections_data)

    # NOTE: memory_cards generation disabled — replaced by sections/ pipeline
    # write_standard_memory_cards(clean_dir, evidence, metadata)
    # write_figure_cards(clean_dir, figures)
    # write_table_memory_cards(clean_dir, tables, paper_id)

    write_json(clean_dir / "metadata.json", metadata)
    write_json(clean_dir / "document_tree.json", build_document_tree(paper_id, metadata, sections_data))
    write_json(clean_dir / "paragraph_index.json", build_paragraph_index(paper_id, sections_data, metadata, evidence_short_ids=evidence_short_ids))
    write_json(clean_dir / "original_structure_index.json", build_original_structure_index(paper_id, sections_data))
    write_json(clean_dir / "evidence_links.json", build_evidence_links_sections(paper_id, sections_data, figures, tables, metadata, evidence_short_ids=evidence_short_ids))
    write_json(clean_dir / "image_manifest.json", image_manifest)
    write_table_manifest(clean_dir, tables)
    write_json(clean_dir / "quality_report.json", build_quality_report(clean_dir, paper_id, sections_data, figures, tables, metadata))
    write_processing_record(clean_dir, metadata, figures, image_manifest)

    return clean_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean one MinerU output into LiteratureClean L0/L1 structure.")
    parser.add_argument("--mineru-dir", type=Path, default=DEFAULT_MINERU_DIR)
    parser.add_argument("--clean-root", type=Path, default=DEFAULT_CLEAN_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clean_dir = build_package(args.mineru_dir, args.clean_root, overwrite=args.overwrite)
    print(f"LiteratureClean package created: {clean_dir}")


if __name__ == "__main__":
    main()

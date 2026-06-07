"""Build one LiteratureClean package from one MinerU output directory.

This is intentionally a single-paper, semi-automatic cleaner. It does not scan
batch folders, import into OpenViking, or touch the AutoHySeeker UI.
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_module
import json
import re
import shutil
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
            if _is_front_matter_paragraph(txt, ""):
                _push(front_snippets, txt)
            if _is_abstract_like_paragraph(txt):
                _push(abstract_snippets, txt)

        if item_type in {"paragraph", "title"} and _is_back_matter_paragraph(txt, ""):
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
# ============================================================================

# -- Macro section rules (keyword merge + preserve original heading) --------
_MACRO_SECTION_META: "dict[str, dict[str, Any]]" = {
    "S00_front_matter": {
        "title": "Front Matter",
        "keywords": [
            "title", "highlights", "graphical abstract", "author", "authors",
            "affiliation", "affiliations", "corresponding author", "institute",
            "university", "department", "received", "accepted", "published",
            "article history", "email", "e-mail", "作者信息", "通讯作者",
        ],
    },
    "S01_abstract": {
        "title": "Abstract",
        "keywords": ["abstract", "summary"],
    },
    "S02_introduction": {
        "title": "Introduction",
        "keywords": [
            "introduction", "background", "related", "motivation",
            "引言", "绪论", "研究背景", "研究背景与意义", "背景与意义", "研究意义", "国内外研究现状", "研究现状", "问题提出",
        ],
    },
    "S03_methods_and_setup": {
        "title": "Methods And Setup",
        "keywords": [
            "method", "experimental", "synthesis", "preparation", "fabrication",
            "characterization", "measurement", "electrochemical measurement", "material",
            "computation", "dft", "protocol", "cell assembly", "setup",
            "system construction", "stack and manifold", "实验方法", "材料与方法", "实验部分", "材料制备", "合成", "制备",
            "表征", "测试方法", "电化学测试", "计算方法", "模型设置", "实验条件", "工况设置",
        ],
    },
    "S04_results": {
        "title": "Result",
        "keywords": [
            "result", "performance", "activity", "her", "oer", "water electrolysis",
            "seawater electrolysis", "stability", "durability", "10000 h", "intermittent",
            "start-shutdown", "cycling", "current density", "cell voltage", "overpotential",
            "tafel", "lsv", "eis", "faradaic efficiency", "结果", "结果与分析", "性能", "电化学性能", "稳定性",
            "耐久性", "活性", "电解性能", "对比分析", "测试结果",
        ],
    },
    "S05_discussion_mechanism": {
        "title": "Discussion Mechanism",
        "keywords": [
            "mechanism", "reaction mechanism", "mechanism discussion", "insight", "structural evolution",
            "corrosion", "oxidation", "reverse current", "reverse-current", "degradation",
            "protection mechanism", "in situ", "operando", "xps", "xrd", "tem", "sem",
            "raman", "theoretical calculation", "charge redistribution", "讨论", "机理", "机制", "失效机制", "反向电流",
            "阴极氧化", "腐蚀", "衰减", "降解", "结构演化", "保护机制", "理论分析", "机理分析",
        ],
    },
    "S06_conclusion": {
        "title": "Conclusion",
        "keywords": ["conclusion", "summary", "outlook", "perspective", "结论", "总结", "结论与展望", "总结与展望", "展望"],
    },
    "S07_back_matter_or_supplementary": {
        "title": "Back Matter Or Supplementary",
        "keywords": [
            "supporting information", "supplementary information", "supplementary data",
            "appendix", "appendices", "references", "bibliography", "acknowledgments",
            "acknowledgement", "author contributions", "corresponding author",
            "conflict of interest", "competing interests", "declaration of competing interest",
            "data availability", "code availability", "notes", "additional information",
            "credit authorship",
            "主要参考文献",
            "参考文献",
            "致谢", "作者贡献", "通讯作者", "作者信息", "利益冲突", "数据可得性", "代码可得性", "补充信息", "附录", "声明",
        ],
    },
}

_MACRO_SECTION_ORDER = [
    "S00_front_matter",
    "S01_abstract",
    "S02_introduction",
    "S03_methods_and_setup",
    "S04_results",
    "S05_discussion_mechanism",
    "S06_conclusion",
    "S07_back_matter_or_supplementary",
]

_INTRO_KEYS = [
    "introduction", "background", "related", "motivation", "引言", "绪论", "研究背景", "研究背景与意义", "背景与意义", "研究意义", "国内外研究现状", "研究现状", "问题提出",
]
_METHOD_KEYS = [
    "method", "experimental", "synthesis", "preparation", "fabrication", "characterization",
    "measurement", "electrochemical measurement", "material", "computation", "dft", "protocol",
    "cell assembly", "setup", "system construction", "stack and manifold", "实验方法", "材料与方法", "实验部分", "材料制备", "合成", "制备", "表征", "测试方法", "电化学测试", "计算方法", "模型设置", "实验条件", "工况设置",
]
_RESULT_KEYS = [
    "result", "performance", "activity", "her", "oer", "water electrolysis", "seawater electrolysis",
    "stability", "durability", "10000 h", "intermittent", "start-shutdown", "cycling",
    "current density", "cell voltage", "overpotential", "tafel", "lsv", "eis", "faradaic efficiency", "结果", "结果与分析", "性能", "电化学性能", "稳定性", "耐久性", "活性", "电解性能", "对比分析", "测试结果",
]
_MECH_KEYS = [
    "mechanism", "reaction mechanism", "mechanism discussion", "insight", "structural evolution", "corrosion",
    "oxidation", "reverse current", "reverse-current", "degradation", "protection mechanism",
    "in situ", "operando", "xps", "xrd", "tem", "sem", "raman", "theoretical calculation",
    "charge redistribution", "讨论", "机理", "机制", "失效机制", "反向电流", "阴极氧化", "腐蚀", "衰减", "降解", "结构演化", "保护机制", "理论分析", "机理分析",
]
_CONCLUSION_KEYS = ["conclusion", "summary", "outlook", "perspective", "结论", "总结", "结论与展望", "总结与展望", "展望"]
_NON_RESEARCH_KEYS = [
    "supporting information", "supplementary information", "supplementary data",
    "appendix", "appendices", "references", "bibliography", "acknowledgments",
    "acknowledgement", "author contributions", "corresponding author",
    "conflict of interest", "competing interests", "declaration of competing interest",
    "data availability", "code availability", "notes", "additional information",
    "credit authorship", "参考文献", "主要参考文献", "致谢", "作者贡献", "通讯作者", "作者信息", "利益冲突", "数据可得性", "代码可得性", "补充信息", "附录", "声明",
]
_FRONT_MATTER_PATTERNS = [
    r"\bhighlights\b",
    r"\bgraphical abstract\b",
    r"\barticle history\b",
    r"https?://",
    r"doi\.org/10\.",
    r"\bdoi\b",
    r"\breceived\b",
    r"\baccepted\b",
    r"\bpublished\b",
    r"\bcorresponding author\b",
    r"\bdata availability\b",
    r"\bcode availability\b",
    r"\be-?mail\b",
    r"\baffiliation\b",
    r"\buniversity\b",
    r"\bdepartment\b",
    r"\binstitute\b",
]
_FRONT_MATTER_RES = [re.compile(pattern, re.IGNORECASE) for pattern in _FRONT_MATTER_PATTERNS]
_MACRO_SECTION_RULES_SOURCE = "defaults"
_MACRO_SCORING: dict[str, int] = {
    "strong": 5,
    "normal": 2,
    "preview": 1,
    "negative": -4,
    "position": 1,
}
_UNCERTAIN_POLICY: dict[str, int] = {
    "min_top_score": 4,
    "min_score_gap": 2,
}
_DOMAIN_DICTIONARY: dict[str, list[str]] = {
    "strong_keywords": [
        "electrochemical hydrogen evolution",
        "seawater electrolysis",
        "reverse current",
        "start-shutdown",
        "stability",
        "her",
        "oer",
        "current density",
        "cell voltage",
        "overpotential",
        "corrosion",
        "oxidation",
        "structural evolution",
        "mechanism",
    ],
    "characterization_keywords": ["xps", "xrd", "tem", "sem", "raman", "ftir", "eds", "mapping"],
}
_DIRECT_RULES: dict[str, list[str]] = {
    "S00_front_matter": ["articleinfo", "highlights", "graphical abstract", "article history", "author information", "affiliations", "作者信息", "通讯作者"],
    "S02_introduction": ["introduction", "1. introduction", "引言", "绪论", "研究背景", "研究背景与意义", "背景与意义", "研究意义", "国内外研究现状", "研究现状", "问题提出"],
    "S06_conclusion": ["conclusion", "conclusions", "summary", "结论", "总结", "结论与展望", "总结与展望", "展望"],
    "S07_back_matter_or_supplementary": [
        "supporting information", "supplementary information", "supplementary data",
        "appendix", "references", "bibliography", "acknowledgments", "acknowledgement",
        "author contributions", "corresponding author", "conflict of interest",
        "competing interests", "declaration of competing interest", "data availability",
        "code availability", "notes", "additional information", "credit authorship",
        "credit authorship contribution statement", "主要参考文献", "参考文献", "致谢", "作者贡献", "通讯作者", "作者信息", "利益冲突", "数据可得性", "代码可得性", "补充信息", "附录", "声明",
    ],
}
_BODY_SECTION_IDS: set[str] = {
    "S01_abstract", "S02_introduction", "S03_methods_and_setup", "S04_results", "S05_discussion_mechanism", "S06_conclusion"
}
_NON_RESEARCH_SECTION_IDS: set[str] = {"S00_front_matter", "S07_back_matter_or_supplementary"}


def _apply_macro_section_rules_from_yaml() -> None:
    """Optionally override default macro-section rules from macro_section_rules.yaml."""
    global _MACRO_SECTION_META
    global _MACRO_SECTION_ORDER
    global _INTRO_KEYS, _METHOD_KEYS, _RESULT_KEYS, _MECH_KEYS, _CONCLUSION_KEYS, _NON_RESEARCH_KEYS
    global _FRONT_MATTER_PATTERNS, _FRONT_MATTER_RES, _MACRO_SECTION_RULES_SOURCE
    global _MACRO_SCORING, _UNCERTAIN_POLICY, _DOMAIN_DICTIONARY
    global _DIRECT_RULES, _BODY_SECTION_IDS, _NON_RESEARCH_SECTION_IDS

    config_path = Path(__file__).with_name("macro_section_rules.yaml")
    if yaml is None or not config_path.exists():
        return

    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        sections_payload = payload.get("sections") or []
        loaded_meta: dict[str, dict[str, Any]] = {}
        for item in sections_payload:
            sid = str(item.get("id", "")).strip()
            title = str(item.get("title", "")).strip()
            keywords = [
                str(keyword).strip().lower()
                for keyword in item.get("keywords", [])
                if str(keyword).strip()
            ]
            if sid and title:
                loaded_meta[sid] = {"title": title, "keywords": keywords}

        if not loaded_meta:
            return

        requested_order = [sid for sid in payload.get("order", []) if sid in loaded_meta]
        merged_order = requested_order or [sid for sid in _MACRO_SECTION_ORDER if sid in loaded_meta]
        merged_order += [sid for sid in loaded_meta if sid not in merged_order]

        front_matter_patterns = payload.get("front_matter_patterns") or _FRONT_MATTER_PATTERNS
        scoring_payload = payload.get("scoring") or {}
        uncertain_payload = payload.get("uncertain") or {}
        domain_dictionary_payload = payload.get("domain_dictionary") or {}
        direct_rules_payload = payload.get("direct_rules") or {}
        manual_review_policy_payload = payload.get("manual_review_policy") or {}

        _MACRO_SECTION_META = loaded_meta
        _MACRO_SECTION_ORDER = merged_order
        _INTRO_KEYS = list(_MACRO_SECTION_META.get("S02_introduction", {}).get("keywords", []))
        _METHOD_KEYS = list(
            (_MACRO_SECTION_META.get("S03_methods_and_setup") or _MACRO_SECTION_META.get("S03_methods") or {}).get("keywords", [])
        )
        _RESULT_KEYS = list(_MACRO_SECTION_META.get("S04_results", {}).get("keywords", []))
        _MECH_KEYS = list(
            (_MACRO_SECTION_META.get("S05_discussion_mechanism") or _MACRO_SECTION_META.get("S05_mechanism_discussion") or _MACRO_SECTION_META.get("S05_mechanism") or {}).get("keywords", [])
        )
        _CONCLUSION_KEYS = list(_MACRO_SECTION_META.get("S06_conclusion", {}).get("keywords", []))
        _NON_RESEARCH_KEYS = list(
            (_MACRO_SECTION_META.get("S07_back_matter_or_supplementary") or _MACRO_SECTION_META.get("S07_non_research_or_supplementary") or _MACRO_SECTION_META.get("S07_supplementary") or {}).get("keywords", [])
        )
        _FRONT_MATTER_PATTERNS = [str(pattern) for pattern in front_matter_patterns if str(pattern).strip()]
        _FRONT_MATTER_RES = [re.compile(pattern, re.IGNORECASE) for pattern in _FRONT_MATTER_PATTERNS]
        _MACRO_SCORING = {
            "strong": int(scoring_payload.get("strong", _MACRO_SCORING["strong"])),
            "normal": int(scoring_payload.get("normal", _MACRO_SCORING["normal"])),
            "preview": int(scoring_payload.get("preview", _MACRO_SCORING["preview"])),
            "negative": int(scoring_payload.get("negative", _MACRO_SCORING["negative"])),
            "position": int(scoring_payload.get("position", _MACRO_SCORING["position"])),
        }
        _UNCERTAIN_POLICY = {
            "min_top_score": int(uncertain_payload.get("min_top_score", _UNCERTAIN_POLICY["min_top_score"])),
            "min_score_gap": int(uncertain_payload.get("min_score_gap", _UNCERTAIN_POLICY["min_score_gap"])),
        }
        _DOMAIN_DICTIONARY = {
            "strong_keywords": [
                str(item).strip().lower()
                for item in domain_dictionary_payload.get("strong_keywords", _DOMAIN_DICTIONARY["strong_keywords"])
                if str(item).strip()
            ],
            "characterization_keywords": [
                str(item).strip().lower()
                for item in domain_dictionary_payload.get("characterization_keywords", _DOMAIN_DICTIONARY["characterization_keywords"])
                if str(item).strip()
            ],
        }
        loaded_direct_rules: dict[str, list[str]] = {}
        for sid, terms in direct_rules_payload.items():
            sid_s = str(sid).strip()
            if not sid_s:
                continue
            loaded_direct_rules[sid_s] = [str(term).strip().lower() for term in (terms or []) if str(term).strip()]
        if loaded_direct_rules:
            _DIRECT_RULES = loaded_direct_rules

        body_sections = {str(item).strip() for item in manual_review_policy_payload.get("body_sections", []) if str(item).strip()}
        non_research_sections = {str(item).strip() for item in manual_review_policy_payload.get("non_research_sections", []) if str(item).strip()}
        if body_sections:
            _BODY_SECTION_IDS = body_sections
        if non_research_sections:
            _NON_RESEARCH_SECTION_IDS = non_research_sections
        _MACRO_SECTION_RULES_SOURCE = "yaml"
    except Exception:
        return


_apply_macro_section_rules_from_yaml()

_FIG_REF_RE = re.compile(r"\bFig(?:ure|s?)\.?\s*(\d+)\w*", re.IGNORECASE)
_TAB_REF_RE = re.compile(r"\bTable\s+(\d+)\w*", re.IGNORECASE)
_CONCLUSION_HEADING_RE = re.compile(r"^(?:\d+(?:\.\d+)*\s*[\.)-]?\s*)?(?:conclusion|conclusions|summary|结论|总结)\b", re.IGNORECASE)
_BACK_MATTER_HEADING_RE = re.compile(
    r"(?:^|\b)(references?|bibliography|credit authorship contribution statement|credit authorship|"
    r"author contributions?|conflict of interest|declaration of competing interest|data availability|"
    r"code availability|acknowledg?ements?|supporting information|supplementary information|"
    r"supplementary data|appendix|appendices|notes?|主要参考文献|参考文献)(?:\b|$)",
    re.IGNORECASE,
)
_REFERENCE_LIST_ITEM_RE = re.compile(r"^\s*(?:\[\d{1,4}\]|\d{1,4}[\.)])\s+[A-Z]", re.IGNORECASE | re.MULTILINE)
_REFERENCE_CUE_RE = re.compile(
    r"doi\.org/10\.|https?://|\bet\s+al\.\b|\b(?:int\.|j\.|chem\.|energy|science|electrochimica|appl\.)\b|"
    r"\(19\d{2}\)|\(20\d{2}\)",
    re.IGNORECASE,
)
_ABSTRACT_START_RE = re.compile(r"^\s*(?:\*\*)?\s*(?:abstract|摘要)\s*:?(?:\*\*)?\s*", re.IGNORECASE)
_ABSTRACT_LEAD_CUE_RE = re.compile(
    r"(?:\bthis study\b|\bin this work\b|\bherein\b|\bwe investigate\b|\bwe report\b|\bwe demonstrate\b|"
    r"\bwe propose\b|\bwe present\b|\bwe reveal\b|\bwe develop\b|\bwe explore\b|"
    r"本文|本研究|本工作|本文提出|本文研究|我们研究|我们提出)",
    re.IGNORECASE,
)
_CONCLUSION_START_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s*[\.)-]?\s*)?(?:conclusion|conclusions|summary|结论|总结|结论与展望)\b",
    re.IGNORECASE,
)
_BACK_MATTER_CUE_RE = re.compile(
    r"(?:credit authorship contribution statement|credit authorship|author contributions?|"
    r"declaration of competing interest|competing interests?|data availability|code availability|"
    r"acknowledg?ements?|参考文献|主要参考文献|作者贡献|利益冲突|数据可得性|代码可得性|致谢)",
    re.IGNORECASE,
)


def _is_numbered_heading(title: str) -> bool:
    return bool(re.match(r"^\s*\d+(?:\.\d+)*\s*[\.)-]?\s+", title))


def _looks_like_front_matter_heading(title: str, section_text: str) -> bool:
    normalized_title = re.sub(r"\s+", " ", title.strip())
    title_word_count = len(re.findall(r"[A-Za-z0-9\-]+", normalized_title))
    if _is_numbered_heading(normalized_title) or title_word_count < 8:
        return False

    probe = f"{normalized_title}\n{section_text[:1200]}".lower()
    author_name_hits = len(re.findall(r"\b[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+\b", f"{title}\n{section_text[:500]}"))
    affiliation_terms = ["university", "department", "institute", "affiliation", "school", "laboratory", "corresponding author"]
    if author_name_hits >= 3 and any(term in probe for term in affiliation_terms):
        return True
    if any(p.search(probe) for p in _FRONT_MATTER_RES):
        return True
    if "e-mail" in probe or "email" in probe or "@" in probe:
        return True
    return False


def _is_reference_paragraph(text: str) -> bool:
    probe = text.strip()
    if not probe:
        return False

    # Narrative body paragraphs often contain a few citations but are not references.
    # Guard against false positives by requiring strong bibliography density.
    low = probe.lower()
    citation_markers = len(re.findall(r"\[\d{1,4}\]", probe))
    year_markers = len(re.findall(r"\((?:19|20)\d{2}\)", probe))
    doi_markers = len(re.findall(r"doi\.org/10\.|\bdoi\b", probe, flags=re.IGNORECASE))
    url_markers = len(re.findall(r"https?://", probe, flags=re.IGNORECASE))
    line_count = len([ln for ln in probe.splitlines() if ln.strip()])
    list_item_lines = len(re.findall(r"^\s*(?:\[\d{1,4}\]|\d{1,4}[\.)])\s+", probe, flags=re.MULTILINE))

    if "fig." in low or "figure" in low:
        if doi_markers == 0 and list_item_lines == 0:
            return False

    if _REFERENCE_LIST_ITEM_RE.search(probe):
        return True
    if doi_markers >= 1 and citation_markers >= 1:
        return True
    if list_item_lines >= 2:
        return True
    if citation_markers >= 6 and year_markers >= 3:
        return True
    if line_count >= 4 and citation_markers >= 4 and (doi_markers + url_markers) >= 1:
        return True
    if year_markers >= 4 and citation_markers >= 4 and re.search(r"\bet\s+al\.\b", probe, flags=re.IGNORECASE):
        return True
    return False


def _looks_like_research_body_paragraph(text: str) -> bool:
    """Guard against moving narrative mechanism/result paragraphs into references."""
    low = text.lower()
    body_cues = [
        "reverse current", "electrolysis", "electrode", "anode", "cathode",
        "redox", "oxidation", "degradation", "temperature", "current density",
        "shutdown", "fig.", "figure", "as shown in fig", "this means", "it can be concluded",
    ]
    cue_hits = sum(1 for cue in body_cues if cue in low)
    has_equation_or_units = bool(re.search(r"\b\d+\s*(?:ma|a|v|mv|cm\^-2|oc|°c)\b", low))
    if cue_hits >= 3:
        return True
    if cue_hits >= 2 and has_equation_or_units:
        return True
    return False


def _classify_macro_section_id(title: str) -> str:
    """Classify an original heading into one macro section by keyword heuristics."""
    normalized = re.sub(r"\s+", " ", title.lower().strip())

    if _CONCLUSION_HEADING_RE.search(normalized):
        return "S06_conclusion"
    if _BACK_MATTER_HEADING_RE.search(normalized):
        return "S07_back_matter_or_supplementary"
    if "主要参考文献" in normalized:
        return "S07_back_matter_or_supplementary"
    if "研究背景与意义" in normalized:
        return "S02_introduction"

    # Boundary rules: default to methods unless explicit mechanism cues appear.
    mechanism_cues = ("corrosion", "oxidation", "mechanism", "degradation", "redox", "失效", "机理")
    if "characterization" in normalized:
        return "S05_discussion_mechanism" if any(cue in normalized for cue in mechanism_cues) else "S03_methods_and_setup"
    if "theoretical calculation" in normalized:
        return "S03_methods_and_setup"
    if "equivalent circuit model" in normalized:
        return "S05_discussion_mechanism" if any(cue in normalized for cue in mechanism_cues) else "S03_methods_and_setup"
    if "electrolysis and shutdown conditions" in normalized:
        return "S03_methods_and_setup"

    if any(k in normalized for k in _NON_RESEARCH_KEYS):
        return "S07_back_matter_or_supplementary"
    if any(k in normalized for k in _CONCLUSION_KEYS if k != "summary") or "conclusion" in normalized:
        return "S06_conclusion"
    if "abstract" in normalized or normalized in {"summary", "abstract"}:
        return "S01_abstract"
    if any(k in normalized for k in _INTRO_KEYS):
        return "S02_introduction"
    if any(k in normalized for k in _METHOD_KEYS):
        return "S03_methods_and_setup"
    if any(k in normalized for k in _RESULT_KEYS):
        return "S04_results"
    if any(k in normalized for k in _MECH_KEYS):
        return "S05_discussion_mechanism"

    # Default for unknown technical headings: merge into methods to avoid fragment dirs.
    return "S03_methods_and_setup"


def _match_direct_section_rule(title: str) -> str | None:
    """Direct whitelist mapping from heading title to section id."""
    normalized = re.sub(r"\s+", " ", title.lower().strip())
    for sid, terms in _DIRECT_RULES.items():
        for term in terms:
            if not term:
                continue
            if normalized == term or normalized.startswith(f"{term} ") or term in normalized:
                return sid
    return None


def _build_macro_section_score_breakdown(original_heading: str, preview_text: str) -> dict[str, Any]:
    """Score all macro sections for one original heading and keep a reviewable breakdown."""
    normalized_heading = re.sub(r"\s+", " ", original_heading.lower().strip())
    normalized_preview = re.sub(r"\s+", " ", preview_text.lower().strip())
    preview_excerpt = preview_text[:240].replace("\n", " ").strip()
    if len(preview_text) > 240:
        preview_excerpt += "..."

    strong_terms = set(_DOMAIN_DICTIONARY.get("strong_keywords", []))
    section_scores: list[dict[str, Any]] = []

    for sid in _MACRO_SECTION_ORDER:
        meta = _MACRO_SECTION_META.get(sid)
        if not meta:
            continue
        score = 0
        heading_hits: list[dict[str, Any]] = []
        preview_hits: list[dict[str, Any]] = []
        position_hits: list[dict[str, Any]] = []

        for keyword in meta.get("keywords", []):
            if keyword in normalized_heading:
                weight = _MACRO_SCORING["strong"] if keyword in strong_terms else _MACRO_SCORING["normal"]
                score += weight
                heading_hits.append({"term": keyword, "weight": weight})
            elif keyword in normalized_preview:
                weight = _MACRO_SCORING["preview"]
                score += weight
                preview_hits.append({"term": keyword, "weight": weight})

        canonical_title = meta.get("title", "").lower()
        if canonical_title and (
            normalized_heading == canonical_title
            or normalized_heading.startswith(canonical_title)
            or any(normalized_heading == keyword for keyword in meta.get("keywords", []))
        ):
            score += _MACRO_SCORING["position"]
            position_hits.append({"term": canonical_title, "weight": _MACRO_SCORING["position"]})

        section_scores.append({
            "section_id": sid,
            "section_title": meta.get("title", sid),
            "score": score,
            "heading_hits": heading_hits,
            "preview_hits": preview_hits,
            "position_hits": position_hits,
        })

    ranked_scores = sorted(section_scores, key=lambda item: (-item["score"], _MACRO_SECTION_ORDER.index(item["section_id"])))
    top = ranked_scores[0] if ranked_scores else None
    second = ranked_scores[1] if len(ranked_scores) > 1 else None
    return {
        "rule_source": _MACRO_SECTION_RULES_SOURCE,
        "scoring": dict(_MACRO_SCORING),
        "uncertain_policy": dict(_UNCERTAIN_POLICY),
        "heading": original_heading,
        "preview_excerpt": preview_excerpt,
        "top_section_id": top["section_id"] if top else None,
        "top_score": top["score"] if top else 0,
        "second_section_id": second["section_id"] if second else None,
        "second_score": second["score"] if second else 0,
        "score_gap": (top["score"] - second["score"]) if top and second else None,
        "section_scores": ranked_scores,
    }


def _resolve_macro_section_assignment(
    rule_section_id: str,
    score_breakdown: dict[str, Any],
) -> tuple[str, str, bool, list[str], str, bool]:
    """Choose assigned macro section from score top1 when confident, otherwise fall back."""
    top_section_id = str(score_breakdown.get("top_section_id") or "")
    top_score = int(score_breakdown.get("top_score") or 0)
    score_gap = score_breakdown.get("score_gap")
    gap_value = int(score_gap) if isinstance(score_gap, int) else 0

    uncertain_reasons: list[str] = []
    if not top_section_id:
        uncertain_reasons.append("missing_top_section")
    if top_score < _UNCERTAIN_POLICY["min_top_score"]:
        uncertain_reasons.append("low_top_score")
    if score_gap is not None and gap_value < _UNCERTAIN_POLICY["min_score_gap"]:
        uncertain_reasons.append("low_score_gap")

    if uncertain_reasons:
        if rule_section_id in _NON_RESEARCH_SECTION_IDS:
            # Non-research/supplementary headings should not inflate manual review queue.
            return rule_section_id, "uncertain_fallback", True, uncertain_reasons, "soft_uncertain", False
        return rule_section_id, "uncertain_fallback", True, uncertain_reasons, "needs_manual_review", True

    return top_section_id, "score_breakdown", False, [], "auto_accept", False


def _is_front_matter_paragraph(text: str, original_heading: str) -> bool:
    """Heuristic splitter: metadata-like blocks should go to S00_front_matter."""
    probe = f"{original_heading}\n{text}".strip()
    low = probe.lower()
    if any(p.search(probe) for p in _FRONT_MATTER_RES):
        return True
    if "doi:" in low or "doi.org/" in low or "orcid" in low:
        return True
    if "e-mail" in low or "email" in low:
        return True
    # Title-page author blocks often look like a comma-separated list of names,
    # optionally followed by affiliations or symbols, without sentence punctuation.
    if len(text) <= 320 and text.count(",") >= 3:
        author_tokens = re.findall(r"\b[A-Z][A-Za-z\-\.]+(?:\s+[A-Z][A-Za-z\-\.]+)+\*?", text)
        if len(author_tokens) >= 3:
            return True
    # Author lines often have many comma-separated names with affiliation digits.
    name_pairs = re.findall(r"\b[A-Z][a-zA-Z\-]+\s+[A-Z][a-zA-Z\-]+\d*(?:,\d+)*", text)
    if len(name_pairs) >= 3 and text.count(",") >= 2 and re.search(r"\d", text):
        return True
    if "check for updates" in low or "these authors contributed equally" in low or "e-mail:" in low:
        return True
    # Affiliation footnotes are usually numbered and institution-heavy.
    if re.match(r"^\d+\s", text.strip()) and re.search(
        r"university|department|laboratory|institute|college|school|china|hong kong|state key",
        low,
    ):
        return True
    if "articleinfo" in low or "article info" in low or "publisher" in low or "journal" in low:
        return True
    # Metadata blocks are often short and contain many separators.
    if len(low) <= 220 and (low.count(":") >= 2 or low.count(";") >= 2):
        return True
    return False


def _is_abstract_like_paragraph(text: str) -> bool:
    probe = text.strip()
    if not probe:
        return False
    low = probe.lower()
    if _ABSTRACT_START_RE.search(probe):
        return True
    if low.startswith("keywords") or low.startswith("keyword") or low.startswith("关键词"):
        return True
    if _ABSTRACT_LEAD_CUE_RE.search(probe):
        return True
    return False


def _is_back_matter_paragraph(text: str, original_heading: str) -> bool:
    probe = f"{original_heading}\n{text}".strip()
    if not probe:
        return False
    if _BACK_MATTER_HEADING_RE.search(probe):
        return True
    if _BACK_MATTER_CUE_RE.search(probe):
        return True
    return _is_reference_paragraph(text)


def _is_leading_abstract_paragraph(
    text: str,
    heading_order: int,
    paragraph_in_heading: int,
    leading_front_matter_count: int,
    abstract_started: bool,
    doc_heading_order: int,
    page_estimate: int | None,
) -> bool:
    """Infer abstract-like paragraph in the first heading after metadata lines."""
    if doc_heading_order != 1:
        return False
    if paragraph_in_heading > 8:
        return False
    if leading_front_matter_count <= 0:
        return False
    if page_estimate is not None and page_estimate > 1:
        return False

    low = text.strip().lower()
    if not low:
        return False
    if _is_abstract_like_paragraph(text):
        return True

    if abstract_started and not _is_reference_paragraph(text):
        return True

    # Typical leading abstract block: long narrative paragraph right after title/authors.
    token_count = len(re.findall(r"\S+", text))
    if token_count >= 70 and not _is_reference_paragraph(text):
        return True
    return False


def _renumber_section_paragraphs(
    paragraphs: "list[dict[str, Any]]",
    section_id: str,
    macro_section_title: str,
) -> "list[dict[str, Any]]":
    """Reassign paragraph IDs after section-level post processing."""
    sec_prefix = section_id.split("_")[0]
    for idx, p in enumerate(paragraphs, start=1):
        p["order"] = idx
        p["paragraph_id"] = f"{sec_prefix}-P{idx:03d}"
        p["macro_section_id"] = section_id
        p["macro_section_title"] = macro_section_title
        p["paragraph_in_heading"] = p.get("paragraph_in_heading") or idx
    return paragraphs


def _extract_paragraph_keywords(text: str, original_heading: str, macro_keywords: "list[str]") -> "list[str]":
    """Extract lightweight retrieval keywords without LLM."""
    source_low = f"{original_heading}\n{text[:500]}".lower()
    out: "list[str]" = []

    def _push(term: str) -> None:
        t = term.strip()
        if t and t not in out:
            out.append(t)

    # Keep macro-specific terms when they actually occur in heading/paragraph preview.
    for k in macro_keywords:
        if k in source_low:
            _push(k)

    # Capture standard scientific acronyms.
    acronyms = re.findall(r"\b[A-Z]{2,8}\b", f"{original_heading}\n{text}")
    for a in acronyms:
        _push(a)

    # Add salient lexical tokens as fallback.
    stop = {
        "the", "and", "with", "from", "that", "this", "were", "have", "which", "using",
        "into", "their", "than", "also", "for", "our", "can", "will", "was", "are", "been",
    }
    for tok in re.findall(r"\b[a-z][a-z0-9\-]{3,}\b", source_low):
        if tok in stop:
            continue
        _push(tok)
        if len(out) >= 12:
            break

    return out[:12]


def _macro_top_candidates(score_breakdown: dict[str, Any], top_n: int = 2) -> list[dict[str, Any]]:
    section_scores = score_breakdown.get("section_scores") if isinstance(score_breakdown, dict) else None
    if not isinstance(section_scores, list):
        return []
    out: list[dict[str, Any]] = []
    for item in section_scores[:max(1, top_n)]:
        out.append(
            {
                "section_id": item.get("section_id"),
                "section_title": item.get("section_title"),
                "score": item.get("score"),
                "heading_hits": item.get("heading_hits") or [],
                "preview_hits": item.get("preview_hits") or [],
                "position_hits": item.get("position_hits") or [],
            }
        )
    return out


def _build_macro_trace_from_paragraph(p: dict[str, Any]) -> dict[str, Any]:
    score_breakdown = p.get("heading_score_breakdown") or {}
    return {
        "rule_source": score_breakdown.get("rule_source"),
        "decision": score_breakdown.get("decision") or p.get("heading_assigned_by"),
        "assigned_section_id": score_breakdown.get("assigned_section_id") or p.get("macro_section_id"),
        "top_section_id": score_breakdown.get("top_section_id"),
        "second_section_id": score_breakdown.get("second_section_id"),
        "top_score": score_breakdown.get("top_score"),
        "second_score": score_breakdown.get("second_score"),
        "score_gap": score_breakdown.get("score_gap"),
        "confidence_level": score_breakdown.get("confidence_level"),
        "is_uncertain": bool(score_breakdown.get("is_uncertain")),
        "needs_manual_review": bool(score_breakdown.get("needs_manual_review")),
        "uncertain_reasons": score_breakdown.get("uncertain_reasons") or [],
        "top_candidates": _macro_top_candidates(score_breakdown, top_n=2),
    }


def _build_macro_conflict_from_paragraph(p: dict[str, Any]) -> dict[str, Any] | None:
    trace = _build_macro_trace_from_paragraph(p)
    reasons: list[str] = []
    if trace.get("is_uncertain"):
        reasons.extend([str(r) for r in trace.get("uncertain_reasons") or []])

    macro_secondary = p.get("macro_secondary")
    if macro_secondary:
        reasons.append("paragraph_rerouted")

    second_score = int(trace.get("second_score") or 0)
    if second_score > 0 and trace.get("top_section_id") != trace.get("assigned_section_id"):
        reasons.append("top_candidate_mismatch")

    if not reasons:
        return None

    confidence = str(trace.get("confidence_level") or "")
    if bool(trace.get("needs_manual_review")):
        level = "high"
    elif confidence == "soft_uncertain" or "paragraph_rerouted" in reasons:
        level = "medium"
    else:
        level = "low"

    return {
        "conflict_level": level,
        "conflict_reasons": sorted(set(reasons)),
        "primary_section_id": p.get("macro_section_id"),
        "secondary_section_id": macro_secondary,
        "top_candidate_section_id": trace.get("top_section_id"),
        "second_candidate_section_id": trace.get("second_section_id"),
        "score_gap": trace.get("score_gap"),
        "confidence_level": trace.get("confidence_level"),
        "needs_manual_review": bool(trace.get("needs_manual_review")),
    }


def build_tag_conflicts_report(paper_id: str, sections: "list[dict[str, Any]]") -> dict[str, Any]:
    """Build tag_conflicts.json for audit-friendly conflict tracing (C2/C3)."""
    items: list[dict[str, Any]] = []
    for sec in sections:
        for p in sec.get("paragraphs", []):
            conflict = _build_macro_conflict_from_paragraph(p)
            if not conflict:
                continue
            items.append(
                {
                    "paper_id": paper_id,
                    "paragraph_uid": p.get("paragraph_uid"),
                    "paragraph_id": p.get("paragraph_id"),
                    "heading_uid": p.get("source_heading_uid"),
                    "heading_text": p.get("source_heading_text") or p.get("original_heading"),
                    "doc_heading_order": p.get("source_doc_heading_order"),
                    "macro_trace": _build_macro_trace_from_paragraph(p),
                    "macro_conflict": conflict,
                    "text_preview": (p.get("text") or "")[:220].replace("\n", " ").strip(),
                }
            )

    high = sum(1 for i in items if (i.get("macro_conflict") or {}).get("conflict_level") == "high")
    medium = sum(1 for i in items if (i.get("macro_conflict") or {}).get("conflict_level") == "medium")
    low = sum(1 for i in items if (i.get("macro_conflict") or {}).get("conflict_level") == "low")
    return {
        "paper_id": paper_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_conflicts": len(items),
        "high_conflicts": high,
        "medium_conflicts": medium,
        "low_conflicts": low,
        "items": items,
    }


def _detect_linked_figures(text: str) -> "list[str]":
    """Extract figure refs like 'Fig. 2' → ['FIG002']."""
    seen: "list[str]" = []
    for m in _FIG_REF_RE.finditer(text):
        fid = f"FIG{int(m.group(1)):03d}"
        if fid not in seen:
            seen.append(fid)
    return seen


def _detect_linked_tables(text: str) -> "list[str]":
    """Extract table refs like 'Table 1' → ['TAB001']."""
    seen: "list[str]" = []
    for m in _TAB_REF_RE.finditer(text):
        tid = f"TAB{int(m.group(1)):03d}"
        if tid not in seen:
            seen.append(tid)
    return seen


def _classify_evidence_type(section_id: str, linked_figs: "list[str]", linked_tabs: "list[str]") -> str:
    """Infer evidence_type from context."""
    sid = section_id.lower()
    if "s00_front_matter" in sid or "s07_back_matter_or_supplementary" in sid:
        return "non_research"
    if linked_figs:
        return "figure_reference"
    if linked_tabs:
        return "table_reference"
    if "method" in sid or "experimental" in sid or "s03" in sid:
        return "method"
    if "result" in sid or "s04" in sid:
        return "result"
    if "mechanism" in sid or "discussion" in sid or "s05" in sid:
        return "mechanism_discussion"
    if "abstract" in sid or "s01" in sid:
        return "abstract"
    return "paragraph"


def split_into_sections(clean_text: str) -> "list[dict[str, Any]]":
    """Parse full_clean.md into a list of section dicts.

        Returns macro-section list where each entry merges multiple original headings.
        Each section dict includes:
            section_title, section_id, order, text, subsections[]
    """
    lines_raw = clean_text.splitlines()

    # Collect all headings with their level and line index
    all_headings: "list[tuple[int, int, str]]" = []  # (line_idx, level, title)
    for i, line in enumerate(lines_raw):
        m = re.match(r"^(#{1,4})\s+(.+)", line)
        if m:
            all_headings.append((i, len(m.group(1)), m.group(2).strip()))

    # Choose dominant section level: prefer ## (2), fall back to # (1)
    level_counts: "dict[int, int]" = {}
    for _, lvl, _ in all_headings:
        level_counts[lvl] = level_counts.get(lvl, 0) + 1

    section_level = 2
    if level_counts.get(2, 0) >= 2:
        section_level = 2
    elif level_counts.get(1, 0) >= 2:
        section_level = 1

    section_headings = [(i, title) for i, lvl, title in all_headings if lvl == section_level]

    if not section_headings:
        return [{
            "section_title": _MACRO_SECTION_META["S01_abstract"]["title"],
            "section_id": "S01_abstract",
            "macro_section_title": _MACRO_SECTION_META["S01_abstract"]["title"],
            "order": 1,
            "text": clean_text,
            "subsections": [{"original_heading": "Full Text", "text": clean_text}],
            "macro_keywords": _MACRO_SECTION_META["S01_abstract"]["keywords"],
        }]

    grouped: "dict[str, dict[str, Any]]" = {}

    # Preamble before first section heading is treated as front matter.
    first_heading_idx = section_headings[0][0]
    preamble_text = "\n".join(lines_raw[:first_heading_idx]).strip()
    if len(re.sub(r"\s+", " ", preamble_text)) >= 80:
        sid = "S00_front_matter"
        meta = _MACRO_SECTION_META[sid]
        score_breakdown = _build_macro_section_score_breakdown("Front Matter (inferred)", preamble_text)
        score_breakdown["decision"] = "preamble_inference"
        score_breakdown["is_uncertain"] = False
        score_breakdown["uncertain_reasons"] = []
        score_breakdown["confidence_level"] = "auto_accept"
        score_breakdown["needs_manual_review"] = False
        score_breakdown["assigned_section_id"] = sid
        score_breakdown["assigned_section_title"] = meta["title"]
        score_breakdown["matches_assigned_section"] = score_breakdown.get("top_section_id") == sid
        grouped[sid] = {
            "section_title": meta["title"],
            "macro_section_title": meta["title"],
            "section_id": sid,
            "subsections": [{
                "original_heading": "Front Matter (inferred)",
                "text": preamble_text,
                "assigned_by": "preamble_inference",
                "doc_heading_order": 0,
                "heading_level": 0,
                "score_breakdown": score_breakdown,
            }],
            "macro_keywords": meta["keywords"],
        }

    for i, (heading_line_idx, title) in enumerate(section_headings):
        if i + 1 < len(section_headings):
            next_line = section_headings[i + 1][0]
        else:
            next_line = len(lines_raw)

        section_text = "\n".join(lines_raw[heading_line_idx + 1:next_line]).strip()
        if not section_text:
            continue

        sid = _classify_macro_section_id(title)
        score_breakdown = _build_macro_section_score_breakdown(title, section_text)
        direct_sid = _match_direct_section_rule(title)
        if direct_sid:
            sid = direct_sid
            assigned_by = "direct_rule"
            is_uncertain = False
            uncertain_reasons = []
            confidence_level = "auto_accept"
            needs_manual_review = False
        else:
            sid, assigned_by, is_uncertain, uncertain_reasons, confidence_level, needs_manual_review = _resolve_macro_section_assignment(sid, score_breakdown)
        # Hard rule: first long unnumbered heading with author/affiliation cues must be front matter.
        if i == 0 and _looks_like_front_matter_heading(title, section_text):
            sid = "S00_front_matter"
            assigned_by = "front_matter_hard_rule"
            is_uncertain = False
            uncertain_reasons = []
            confidence_level = "auto_accept"
            needs_manual_review = False
        meta = _MACRO_SECTION_META[sid]
        score_breakdown["decision"] = assigned_by
        score_breakdown["is_uncertain"] = is_uncertain
        score_breakdown["uncertain_reasons"] = list(uncertain_reasons)
        score_breakdown["confidence_level"] = confidence_level
        score_breakdown["needs_manual_review"] = needs_manual_review
        score_breakdown["assigned_section_id"] = sid
        score_breakdown["assigned_section_title"] = meta["title"]
        score_breakdown["matches_assigned_section"] = score_breakdown.get("top_section_id") == sid
        if sid not in grouped:
            grouped[sid] = {
                "section_title": meta["title"],
                "macro_section_title": meta["title"],
                "section_id": sid,
                "subsections": [],
                "macro_keywords": meta["keywords"],
            }
        grouped[sid]["subsections"].append({
            "original_heading": title,
            "text": section_text,
            "doc_heading_order": i + 1,
            "heading_level": section_level,
            "assigned_by": assigned_by,
            "is_uncertain": is_uncertain,
            "uncertain_reasons": list(uncertain_reasons),
            "confidence_level": confidence_level,
            "needs_manual_review": needs_manual_review,
            "score_breakdown": score_breakdown,
        })

    sections: "list[dict[str, Any]]" = []
    order = 0
    for sid in _MACRO_SECTION_ORDER:
        sec = grouped.get(sid)
        if not sec:
            continue
        order += 1
        merged_parts: "list[str]" = []
        for sub in sec["subsections"]:
            merged_parts.append(f"## {sub['original_heading']}\n{sub['text']}")
        sec["text"] = "\n\n".join(merged_parts).strip()
        sec["order"] = order
        sections.append(sec)

    return sections


# Noise patterns to filter out from paragraphs
_PARA_NOISE_RES = [
    re.compile(r"^Downloaded from", re.IGNORECASE),
    re.compile(r"^Copyright\b", re.IGNORECASE),
    re.compile(r"^Published by\b", re.IGNORECASE),
    re.compile(r"^[©]\s*\d{4}"),
    re.compile(r"^Received:\s+\d", re.IGNORECASE),
    re.compile(r"^Accepted:\s+\d", re.IGNORECASE),
    re.compile(r"^doi:\s+10\.", re.IGNORECASE),
    re.compile(r"^\[\d+\]\s+[A-Z]"),          # numbered reference list item
    re.compile(r"^\d+\s*$"),                   # bare page number
    re.compile(r"^\d+\s+of\s+\d+", re.IGNORECASE),  # "5 of 12"
]


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
    """Split into sections, then apply paragraph-level section recovery.

    Recovery precedence for one paragraph:
    1) front_matter_detector -> S00
    2) conclusion_start_detector -> S06
    3) abstract_leading_detector -> S01
    4) back_matter_detector -> S07
    5) keep original heading-level section
    """
    sections = split_into_sections(clean_text)
    hints = recovery_hints or {}
    hint_front = [str(item) for item in hints.get("front_snippets", []) if str(item).strip()]
    hint_abstract = [str(item) for item in hints.get("abstract_snippets", []) if str(item).strip()]
    hint_back = [str(item) for item in hints.get("back_snippets", []) if str(item).strip()]
    paragraph_uid_seq = 0
    front_matter_bucket: "list[dict[str, Any]]" = []
    abstract_bucket: "list[dict[str, Any]]" = []
    reference_bucket: "list[dict[str, Any]]" = []
    conclusion_bucket: "list[dict[str, Any]]" = []

    for sec in sections:
        paras_all: "list[dict[str, Any]]" = []
        para_order = 0
        for heading_order, sub in enumerate(sec.get("subsections", []), start=1):
            sec_prefix = sec["section_id"].split("_")[0]
            heading_id = f"{sec_prefix}-H{heading_order:03d}"
            paras = split_section_paragraphs(
                sub.get("text", ""),
                sec["section_id"],
                paper_id,
                pages,
                sub.get("original_heading", sec["section_title"]),
                sec.get("macro_section_title", sec["section_title"]),
                sec.get("macro_keywords", []),
                start_order=para_order,
            )
            for p in paras:
                paragraph_uid_seq += 1
                source_doc_heading_order = int(sub.get("doc_heading_order", heading_order) or heading_order)
                source_heading_text = str(sub.get("original_heading", sec["section_title"]))
                heading_uid_seed = f"{source_doc_heading_order}:{source_heading_text}"
                source_heading_uid = f"HRAW-{source_doc_heading_order:03d}-{hashlib.sha1(heading_uid_seed.encode('utf-8')).hexdigest()[:8]}"
                p["heading_id"] = heading_id
                p["heading_order"] = heading_order
                p["doc_heading_order"] = source_doc_heading_order
                p["heading_assigned_by"] = sub.get("assigned_by")
                p["heading_score_breakdown"] = sub.get("score_breakdown")
                p["paragraph_uid"] = f"PRAW-{paragraph_uid_seq:06d}"
                p["source_heading_uid"] = source_heading_uid
                p["source_heading_display_order"] = int(source_doc_heading_order or 0)
                p["source_heading_text"] = source_heading_text
                p["source_heading_level"] = int(sub.get("heading_level", 0) or 0)
                p["source_doc_heading_order"] = source_doc_heading_order
                p["source_block_order"] = int(p.get("paragraph_in_heading", 0) or 0)
                p["source_section_id"] = sec["section_id"]
                p["source_section_title"] = sec["section_title"]
            para_order += len(paras)

            keep_paras: "list[dict[str, Any]]" = []
            leading_front_matter_count = 0
            leading_abstract_started = False
            for p in paras:
                is_front = _is_front_matter_paragraph(p["text"], p["original_heading"])
                hinted_front = _matches_recovery_snippets(p["text"], hint_front)
                hinted_abstract = _matches_recovery_snippets(p["text"], hint_abstract)
                hinted_back = _matches_recovery_snippets(p["text"], hint_back)
                is_leading_zone = p.get("doc_heading_order", 99) <= 2 and p.get("paragraph_in_heading", 99) <= 8
                on_first_page = p.get("page_estimate") in (None, 1)
                if (is_front or hinted_front) and is_leading_zone and on_first_page:
                    p["inferred_type"] = "none"
                    front_matter_bucket.append(p)
                    leading_front_matter_count += 1
                    continue

                if _CONCLUSION_START_RE.search(p["text"].strip()):
                    p["inferred_type"] = "conclusion"
                    conclusion_bucket.append(p)
                    continue

                if _is_leading_abstract_paragraph(
                    p["text"],
                    p.get("heading_order", heading_order),
                    p.get("paragraph_in_heading", 99),
                    leading_front_matter_count,
                    leading_abstract_started,
                    p.get("doc_heading_order", heading_order),
                    p.get("page_estimate"),
                ) or (hinted_abstract and p.get("doc_heading_order", 99) <= 2):
                    p["inferred_type"] = "abstract"
                    abstract_bucket.append(p)
                    leading_abstract_started = True
                    continue

                if (
                    sec["section_id"] != "S07_back_matter_or_supplementary"
                    and (_is_back_matter_paragraph(p["text"], p.get("original_heading", "")) or hinted_back)
                    and not _looks_like_research_body_paragraph(p["text"])
                ):
                    p["inferred_type"] = "back_matter"
                    reference_bucket.append(p)
                    continue

                if sec["section_id"] in {"S00_front_matter", "S03_methods_and_setup", "S04_results", "S05_discussion_mechanism"} and _is_abstract_like_paragraph(p["text"]):
                    p["inferred_type"] = "abstract"
                    abstract_bucket.append(p)
                    leading_abstract_started = True
                    continue

                p["inferred_type"] = "none"

                keep_paras.append(p)
            paras_all.extend(keep_paras)

        sec["paragraphs"] = _renumber_section_paragraphs(
            paras_all,
            sec["section_id"],
            sec.get("macro_section_title", sec["section_title"]),
        )

    if front_matter_bucket:
        fm_id = "S00_front_matter"
        fm_meta = _MACRO_SECTION_META[fm_id]
        fm_sec = next((s for s in sections if s["section_id"] == fm_id), None)
        if not fm_sec:
            fm_sec = {
                "section_title": fm_meta["title"],
                "macro_section_title": fm_meta["title"],
                "section_id": fm_id,
                "subsections": [{"original_heading": "Front Matter (inferred)", "text": ""}],
                "macro_keywords": fm_meta["keywords"],
                "paragraphs": [],
                "order": 0,
            }
            sections.append(fm_sec)

        for p in front_matter_bucket:
            p["heading_id"] = "S00-H001"
            p["heading_order"] = 1
            p["heading_assigned_by"] = "front_matter_detector"
            p["macro_section_id"] = fm_id
            p["macro_section_title"] = fm_meta["title"]
            if p.get("source_section_id") and p["source_section_id"] != fm_id:
                p["macro_secondary"] = p["source_section_id"]
        fm_sec["paragraphs"] = _renumber_section_paragraphs(
            fm_sec.get("paragraphs", []) + front_matter_bucket,
            fm_id,
            fm_meta["title"],
        )

    if abstract_bucket:
        abs_id = "S01_abstract"
        abs_meta = _MACRO_SECTION_META[abs_id]
        abs_sec = next((s for s in sections if s["section_id"] == abs_id), None)
        if not abs_sec:
            abs_sec = {
                "section_title": abs_meta["title"],
                "macro_section_title": abs_meta["title"],
                "section_id": abs_id,
                "subsections": [{"original_heading": "Abstract (inferred)", "text": ""}],
                "macro_keywords": abs_meta["keywords"],
                "paragraphs": [],
                "order": 0,
            }
            sections.append(abs_sec)

        for p in abstract_bucket:
            p["heading_id"] = "S01-H001"
            p["heading_order"] = 1
            p["heading_assigned_by"] = "abstract_leading_detector"
            p["macro_section_id"] = abs_id
            p["macro_section_title"] = abs_meta["title"]
            if p.get("source_section_id") and p["source_section_id"] != abs_id:
                p["macro_secondary"] = p["source_section_id"]

        abs_sec["paragraphs"] = _renumber_section_paragraphs(
            abs_sec.get("paragraphs", []) + abstract_bucket,
            abs_id,
            abs_meta["title"],
        )

    if reference_bucket:
        back_id = "S07_back_matter_or_supplementary"
        back_meta = _MACRO_SECTION_META[back_id]
        back_sec = next((s for s in sections if s["section_id"] == back_id), None)
        if not back_sec:
            back_sec = {
                "section_title": back_meta["title"],
                "macro_section_title": back_meta["title"],
                "section_id": back_id,
                "subsections": [{"original_heading": "References (inferred)", "text": ""}],
                "macro_keywords": back_meta["keywords"],
                "paragraphs": [],
                "order": 0,
            }
            sections.append(back_sec)

        for p in reference_bucket:
            p["heading_id"] = "S07-H900"
            p["heading_order"] = 900
            p["heading_assigned_by"] = "back_matter_detector"
            p["macro_section_id"] = back_id
            p["macro_section_title"] = back_meta["title"]
            p["original_heading"] = "References (inferred)"
            if p.get("source_section_id") and p["source_section_id"] != back_id:
                p["macro_secondary"] = p["source_section_id"]

        back_sec["paragraphs"] = _renumber_section_paragraphs(
            back_sec.get("paragraphs", []) + reference_bucket,
            back_id,
            back_meta["title"],
        )

    if conclusion_bucket:
        con_id = "S06_conclusion"
        con_meta = _MACRO_SECTION_META[con_id]
        con_sec = next((s for s in sections if s["section_id"] == con_id), None)
        if not con_sec:
            con_sec = {
                "section_title": con_meta["title"],
                "macro_section_title": con_meta["title"],
                "section_id": con_id,
                "subsections": [{"original_heading": "Conclusion (inferred)", "text": ""}],
                "macro_keywords": con_meta["keywords"],
                "paragraphs": [],
                "order": 0,
            }
            sections.append(con_sec)

        for p in conclusion_bucket:
            p["heading_id"] = "S06-H001"
            p["heading_order"] = 1
            p["heading_assigned_by"] = "conclusion_start_detector"
            p["macro_section_id"] = con_id
            p["macro_section_title"] = con_meta["title"]
            if p.get("source_section_id") and p["source_section_id"] != con_id:
                p["macro_secondary"] = p["source_section_id"]

        con_sec["paragraphs"] = _renumber_section_paragraphs(
            con_sec.get("paragraphs", []) + conclusion_bucket,
            con_id,
            con_meta["title"],
        )

    ordered: "list[dict[str, Any]]" = []
    for sid in _MACRO_SECTION_ORDER:
        for sec in sections:
            if sec["section_id"] == sid and sec not in ordered:
                ordered.append(sec)
    for i, sec in enumerate(ordered, start=1):
        sec["order"] = i
    return ordered


def write_sections_dir(
    clean_dir: Path,
    paper_id: str,
    sections: "list[dict[str, Any]]",
    metadata: "dict[str, Any]",
    evidence_short_ids: "dict[str, str] | None" = None,
) -> None:
    """Write sections_by_heading/ tree (fact layer primary structure)."""
    heading_root = clean_dir / "sections_by_heading"
    heading_root.mkdir(exist_ok=True)

    # Remove legacy macro-section root to prevent S00-S07 from being treated as primary structure.
    legacy_sections = clean_dir / "sections"
    if legacy_sections.exists() and legacy_sections.is_dir():
        shutil.rmtree(legacy_sections, ignore_errors=True)

    raw_paths = metadata.get("raw_paths", {})
    source_pdf = raw_paths.get("source_pdf", "")
    mineru_dir_s = raw_paths.get("mineru_output_dir", "")
    mineru_full_md = str(Path(mineru_dir_s) / "full.md") if mineru_dir_s else ""
    mineru_cl_v2 = str(Path(mineru_dir_s) / "content_list_v2.json") if mineru_dir_s else ""

    heading_map: "dict[str, dict[str, Any]]" = {}
    heading_seq: "list[str]" = []
    heading_dirname_map: dict[str, str] = {}
    display_order_map: dict[str, int] = {}

    for sec in sections:
        for p in sec.get("paragraphs", []):
            heading_uid = str(p.get("source_heading_uid") or "")
            if not heading_uid:
                continue
            if heading_uid not in heading_map:
                heading_map[heading_uid] = {
                    "heading_uid": heading_uid,
                    "heading_text": p.get("source_heading_text") or p.get("original_heading") or "",
                    "heading_level": p.get("source_heading_level"),
                    "doc_heading_order": p.get("source_doc_heading_order", 999999),
                    "page_index": p.get("page_estimate"),
                    "block_order": p.get("source_block_order", p.get("paragraph_in_heading")),
                    "paragraphs": [],
                }
                heading_seq.append(heading_uid)
            heading_map[heading_uid]["paragraphs"].append(p)

    heading_seq.sort(
        key=lambda hid: (
            int(heading_map[hid].get("doc_heading_order") or 999999),
            int(heading_map[hid].get("block_order") or 999999),
            hid,
        )
    )

    used_dirnames: set[str] = set()
    heading_dir_max_len = _safe_heading_dirname_max_len(clean_dir, default_max=80)
    paper_title = str(metadata.get("title") or "")
    display_order = 0
    for heading_uid in heading_seq:
        item = heading_map[heading_uid]
        display_order += 1
        display_order_map[heading_uid] = display_order
        item["display_order"] = display_order
        item["is_title_page_heading"] = bool(
            display_order == 1
            and int(item.get("doc_heading_order") or 0) == 1
            and _looks_like_document_title_heading(str(item.get("heading_text") or ""), paper_title)
        )
        if item["is_title_page_heading"]:
            heading_dirname_map[heading_uid] = f"{display_order:03d}-front-matter"
            used_dirnames.add(heading_dirname_map[heading_uid])
        else:
            heading_dirname_map[heading_uid] = _build_heading_dirname(
                display_order,
                str(item.get("heading_text") or ""),
                used_names=used_dirnames,
                max_len=heading_dir_max_len,
            )

    index_items: "list[dict[str, Any]]" = []

    for heading_uid in heading_seq:
        item = heading_map[heading_uid]
        heading_dirname = heading_dirname_map[heading_uid]
        heading_dir = heading_root / heading_dirname
        heading_dir.mkdir(exist_ok=True)
        paras_dir = heading_dir / "paragraphs"
        paras_dir.mkdir(exist_ok=True)

        paras = sorted(
            item["paragraphs"],
            key=lambda p: (
                int(p.get("source_block_order", p.get("paragraph_in_heading", 999999)) or 999999),
                str(p.get("paragraph_uid") or ""),
            ),
        )

        paragraph_ids = [str(p.get("paragraph_id") or "") for p in paras]
        paragraph_uids = [str(p.get("paragraph_uid") or "") for p in paras]
        paragraph_paths = [f"paragraphs/{uid}.md" for uid in paragraph_uids if uid]
        linked_figures = sorted({f for p in paras for f in p.get("linked_figures", [])})
        linked_tables = sorted({t for p in paras for t in p.get("linked_tables", [])})

        write_json(
            heading_dir / "heading.json",
            {
                "paper_id": paper_id,
                "heading_uid": heading_uid,
                "heading_dirname": heading_dirname,
                "heading_text": item.get("heading_text", ""),
                "heading_level": item.get("heading_level"),
                "doc_heading_order": item.get("doc_heading_order"),
                "display_order": item.get("display_order"),
                "is_title_page_heading": item.get("is_title_page_heading", False),
                "page_index": item.get("page_index"),
                "block_order": item.get("block_order"),
                "paragraph_count": len(paragraph_uids),
                "paragraph_ids": paragraph_ids,
                "paragraph_uids": paragraph_uids,
                "paragraph_paths": paragraph_paths,
                "linked_figures": linked_figures,
                "linked_tables": linked_tables,
            },
        )

        toc_lines = [f"# Heading {heading_uid}", "", f"Heading: {item.get('heading_text', '')}", ""]
        for p in paras:
            pid = str(p.get("paragraph_id") or "")
            puid = str(p.get("paragraph_uid") or "")
            p["source_heading_dirname"] = heading_dirname
            preview = p.get("text", "")[:150].replace("\n", " ").strip()
            if len(p.get("text", "")) > 150:
                preview += "..."
            ev_id = _paragraph_evidence_id(paper_id, pid)
            ev_short = evidence_short_ids.get(ev_id, "") if evidence_short_ids else ""
            toc_lines += [
                f"## {puid or pid}",
                f"Paragraph ID: {pid}",
                f"Paragraph UID: {puid}",
                f"Macro Primary: {p.get('macro_section_id')}",
                f"Macro Secondary: {p.get('macro_secondary') or 'none'}",
                f"Preview: {preview}",
                f"Path: paragraphs/{puid}.md" if puid else "Path: paragraphs/unknown.md",
                f"Evidence ID: {ev_id}",
                f"Evidence Short ID: {ev_short or 'none'}",
                "",
            ]
        write_text(heading_dir / "paragraphs.md", "\n".join(toc_lines))

        for p in paras:
            pid = str(p.get("paragraph_id") or "")
            puid = str(p.get("paragraph_uid") or "")
            if not puid:
                continue
            page_str = str(p.get("page_estimate")) if p.get("page_estimate") is not None else "unknown"
            figs_str = "\n".join(f"- {f}" for f in p.get("linked_figures", [])) or "- none"
            tabs_str = "\n".join(f"- {t}" for t in p.get("linked_tables", [])) or "- none"
            ev_id = _paragraph_evidence_id(paper_id, pid)
            ev_short = evidence_short_ids.get(ev_id, "") if evidence_short_ids else ""
            content = f"""# Paragraph {puid}

Paper ID: {paper_id}
Heading UID: {heading_uid}
Heading Text: {item.get('heading_text', '')}
Heading Level: {item.get('heading_level')}
Doc Heading Order: {item.get('doc_heading_order')}
Paragraph ID: {pid}
Paragraph UID: {puid}
Macro Primary: {p.get('macro_section_id')}
Macro Secondary: {p.get('macro_secondary') or 'none'}
Page: {page_str}
Evidence ID: {ev_id}
Evidence Short ID: {ev_short or 'none'}

## Text

{p.get('text', '')}

## Linked Figures

{figs_str}

## Linked Tables

{tabs_str}

## Keywords

{', '.join(p.get('keywords', [])) or 'none'}

## Source

- source_pdf: {source_pdf}
- mineru_full_md: {mineru_full_md}
- mineru_content_list_v2: {mineru_cl_v2}
"""
            write_text(paras_dir / f"{puid}.md", content)

        index_items.append(
            {
                "heading_uid": heading_uid,
                "heading_dirname": heading_dirname,
                "heading_text": item.get("heading_text", ""),
                "heading_level": item.get("heading_level"),
                "doc_heading_order": item.get("doc_heading_order"),
                "display_order": item.get("display_order"),
                "paragraph_count": len(paragraph_uids),
                "paragraph_uids": paragraph_uids,
                "path": f"sections_by_heading/{heading_dirname}/",
            }
        )

    write_json(
        heading_root / "heading_index.json",
        {
            "paper_id": paper_id,
            "heading_count": len(index_items),
            "headings": index_items,
        },
    )


def build_document_tree(
    paper_id: str,
    metadata: "dict[str, Any]",
    sections: "list[dict[str, Any]]",
) -> "dict[str, Any]":
    """Build document_tree.json (paper → heading tree primary map)."""
    all_paras = [p for s in sections for p in s.get("paragraphs", [])]
    heading_map: dict[str, dict[str, Any]] = {}
    for p in all_paras:
        heading_uid = str(p.get("source_heading_uid") or "")
        if not heading_uid:
            continue
        item = heading_map.setdefault(
            heading_uid,
            {
                "heading_uid": heading_uid,
                "heading_text": p.get("source_heading_text") or p.get("original_heading") or "",
                "heading_level": p.get("source_heading_level"),
                "doc_heading_order": p.get("source_doc_heading_order"),
                "display_order": p.get("source_heading_display_order"),
                "page_index": p.get("page_estimate"),
                "paragraph_count": 0,
                "paragraph_uids": [],
                "macro_tags": set(),
            },
        )
        item["paragraph_count"] += 1
        if p.get("paragraph_uid"):
            item["paragraph_uids"].append(p.get("paragraph_uid"))
        if p.get("macro_section_id"):
            item["macro_tags"].add(p.get("macro_section_id"))

    headings = sorted(
        heading_map.values(),
        key=lambda x: (int(x.get("display_order") or x.get("doc_heading_order") or 999999), str(x.get("heading_uid") or "")),
    )
    for item in headings:
        item["macro_tags"] = sorted(item.get("macro_tags") or [])

    return {
        "paper_id": paper_id,
        "title": metadata.get("title", ""),
        "heading_count": len(headings),
        "paragraph_count": len(all_paras),
        "headings": headings,
    }


def build_paragraph_index(
    paper_id: str,
    sections: "list[dict[str, Any]]",
    metadata: "dict[str, Any]",
    evidence_short_ids: "dict[str, str] | None" = None,
) -> "list[dict[str, Any]]":
    """Build paragraph_index.json — address book for all paragraphs."""
    source_pdf = metadata.get("raw_paths", {}).get("source_pdf", "")
    entries: "list[dict[str, Any]]" = []
    for sec in sections:
        sid = sec["section_id"]
        title = sec["section_title"]
        for p in sec.get("paragraphs", []):
            pid = p["paragraph_id"]
            short_pid = pid.split("-", 1)[1]
            preview = p["text"][:200].replace("\n", " ").strip()
            ev_id = _paragraph_evidence_id(paper_id, pid)
            entries.append({
                "paragraph_uid": p.get("paragraph_uid"),
                "macro_section_id": p["macro_section_id"],
                "macro_section_title": p["macro_section_title"],
                "macro_primary": sid,
                "macro_secondary": p.get("macro_secondary"),
                "macro_confidence": (p.get("heading_score_breakdown") or {}).get("confidence_level"),
                "macro_reasons": (p.get("heading_score_breakdown") or {}).get("uncertain_reasons") or [],
                "macro_trace": _build_macro_trace_from_paragraph(p),
                "macro_conflict": _build_macro_conflict_from_paragraph(p),
                "original_heading": p["original_heading"],
                "heading_id": p.get("heading_id"),
                "heading_order": p.get("heading_order"),
                "heading_uid": p.get("source_heading_uid"),
                "heading_text": p.get("source_heading_text") or p.get("original_heading"),
                "heading_level": p.get("source_heading_level"),
                "doc_heading_order": p.get("source_doc_heading_order", p.get("heading_order")),
                "page_index": p.get("page_estimate"),
                "block_order": p.get("source_block_order", p.get("paragraph_in_heading")),
                "paragraph_in_heading": p.get("paragraph_in_heading"),
                "inferred_type": p.get("inferred_type", "none"),
                "paragraph_id": pid,
                "content_path": f"sections_by_heading/{p.get('source_heading_dirname') or p.get('source_heading_uid')}/paragraphs/{p.get('paragraph_uid')}.md",
                "text_preview": preview,
                "evidence_id": ev_id,
                "evidence_short_id": evidence_short_ids.get(ev_id) if evidence_short_ids else None,
                "linked_figures": p["linked_figures"],
                "linked_tables": p["linked_tables"],
                "keywords": p.get("keywords", []),
                "token_count": p.get("token_count"),
                "paper_id": paper_id,
                "section_id": sid,
                "section_title": title,
                "paragraph_order": p["order"],
                "page_number": p["page_estimate"],
                "source_pdf_path": source_pdf,
                "is_research_body": sid in _BODY_SECTION_IDS,
            })
    return entries


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
    with_heading_text = sum(1 for p in all_paras if p.get("source_heading_text") or p.get("original_heading"))
    with_doc_heading_order = sum(1 for p in all_paras if p.get("source_doc_heading_order") is not None)
    with_page_index = sum(1 for p in all_paras if p.get("page_estimate") is not None)
    with_block_order = sum(1 for p in all_paras if p.get("source_block_order") is not None)
    with_paragraph_uid = sum(1 for p in all_paras if p.get("paragraph_uid"))

    with_macro_primary = sum(1 for p in all_paras if p.get("macro_section_id"))
    with_macro_secondary = sum(1 for p in all_paras if p.get("macro_secondary"))
    with_macro_confidence = sum(
        1 for p in all_paras if (p.get("heading_score_breakdown") or {}).get("confidence_level")
    )
    with_macro_reasons = sum(
        1 for p in all_paras if (p.get("heading_score_breakdown") or {}).get("uncertain_reasons")
    )
    tag_conflicts = [_build_macro_conflict_from_paragraph(p) for p in all_paras]
    tag_conflicts = [c for c in tag_conflicts if c]
    tag_conflicts_high = sum(1 for c in tag_conflicts if c.get("conflict_level") == "high")
    tag_conflicts_medium = sum(1 for c in tag_conflicts if c.get("conflict_level") == "medium")
    tag_conflicts_low = sum(1 for c in tag_conflicts if c.get("conflict_level") == "low")

    front_matter_count = sum(len(s.get("paragraphs", [])) for s in sections if s.get("section_id") == "S00_front_matter")
    back_matter_count = sum(len(s.get("paragraphs", [])) for s in sections if s.get("section_id") == "S07_back_matter_or_supplementary")
    reference_paragraph_count = sum(1 for p in all_paras if _is_reference_paragraph(p.get("text", "")))
    conclusion_detected = any(s.get("section_id") == "S06_conclusion" and len(s.get("paragraphs", [])) > 0 for s in sections)
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

    for sec in sections:
        for sub in sec.get("subsections", []):
            score_breakdown = sub.get("score_breakdown") or {}
            if not score_breakdown.get("is_uncertain"):
                continue
            item = {
                "section_id": sec.get("section_id"),
                "section_title": sec.get("section_title"),
                "original_heading": sub.get("original_heading", ""),
                "assigned_section_id": score_breakdown.get("assigned_section_id"),
                "top_section_id": score_breakdown.get("top_section_id"),
                "top_score": score_breakdown.get("top_score"),
                "second_score": score_breakdown.get("second_score"),
                "score_gap": score_breakdown.get("score_gap"),
                "uncertain_reasons": score_breakdown.get("uncertain_reasons", []),
                "confidence_level": score_breakdown.get("confidence_level", "soft_uncertain"),
                "needs_manual_review": bool(score_breakdown.get("needs_manual_review", False)),
            }
            if item["needs_manual_review"]:
                needs_manual_review_items.append(item)
            else:
                soft_uncertain_items.append(item)

    return {
        "paper_id": paper_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_files": generated,
        "section_count": len(sections),
        "paragraph_count": len(all_paras),
        "figure_count": len(figures),
        "table_count": len(tables),
        "evidence_count": len(all_paras) + len(figures) + len(tables),
        "front_matter_count": front_matter_count,
        "back_matter_count": back_matter_count,
        "reference_paragraph_count": reference_paragraph_count,
        "conclusion_detected": conclusion_detected,
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
        "tag_layer_coverage": {
            "total_paragraphs": total_paras,
            "with_macro_primary": with_macro_primary,
            "macro_primary_coverage": _ratio(with_macro_primary, total_paras),
            "with_macro_secondary": with_macro_secondary,
            "macro_secondary_coverage": _ratio(with_macro_secondary, total_paras),
            "with_macro_confidence": with_macro_confidence,
            "macro_confidence_coverage": _ratio(with_macro_confidence, total_paras),
            "with_macro_reasons": with_macro_reasons,
            "macro_reasons_coverage": _ratio(with_macro_reasons, total_paras),
            "tag_conflict_count": len(tag_conflicts),
            "tag_conflict_ratio": _ratio(len(tag_conflicts), total_paras),
            "tag_conflict_high": tag_conflicts_high,
            "tag_conflict_medium": tag_conflicts_medium,
            "tag_conflict_low": tag_conflicts_low,
        },
        "removed_noise_summary": "Filtered: empty blocks, <40 chars, heading-only, page numbers, noise patterns",
        "next_review_items": [
            "Verify page number estimates against source PDF",
            "Check figure-paragraph links (linked_figures in paragraph_index.json)",
            "Review section title mappings in document_tree.json",
            "Confirm no important paragraphs were filtered as noise",
        ],
        "missing_input_files": [],
        "uncertainty_summary": {
            "soft_uncertain_count": len(soft_uncertain_items),
            "needs_manual_review_count": len(needs_manual_review_items),
            "total_uncertain_count": len(soft_uncertain_items) + len(needs_manual_review_items),
        },
        "soft_uncertain_items": soft_uncertain_items,
        "needs_manual_review_items": needs_manual_review_items,
        # Backward compatibility: keep uncertain_items but only as true manual review queue.
        "uncertain_items": needs_manual_review_items,
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
        shutil.rmtree(clean_dir)
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
    write_json(clean_dir / "tag_conflicts.json", build_tag_conflicts_report(paper_id, sections_data))
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

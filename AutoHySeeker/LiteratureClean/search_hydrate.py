"""Hydration layer: maps OpenViking MatchedContext URIs back to LiteratureClean files.

Viking URI format:
  viking://resources/literature/{paper_id}/{inner_dir}/{rel_path...}
  - parts[4] = paper_id
  - parts[5] = inner_dir (truncated paper_id, skip it)
  - parts[6:] = relative path within paper_dir  ← maps to LiteratureClean/{paper_id}/{rel_path}

Card type detection (from rel_path):
  memory_cards/figures/FIG###/...  → figure
  memory_cards/methods/...         → methods
  memory_cards/results/...         → results
  memory_cards/conditions/...      → conditions
  memory_cards/metrics/...         → metrics
  memory_cards/key_claims/...      → key_claims
  memory_cards/mechanisms/...      → mechanisms
  memory_cards/tables/...          → tables
  (anything else)                  → paper_section
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class HydratedResult:
    rank: int
    score: float

    # Paper identity
    paper_id: str
    paper_title: str = ""
    paper_doi: str = ""
    paper_year: str = ""
    paper_journal: str = ""
    source_pdf_path: str = ""

    # Match location
    matched_file: str = ""            # just filename
    matched_uri: str = ""             # full viking URI of matched file
    relative_path: str = ""           # rel path within paper (joined rel_parts)
    card_type: str = "paper_section"   # figure / tables / methods / paper_section / paper_summary ...
    card_id: str = ""                  # e.g. FIG001
    memory_card_path: str = ""         # abs path to memory_card dir

    # Content paths (in LiteratureClean)
    l0_path: str = ""                  # .abstract.md path
    l1_path: str = ""                  # .overview.md path

    # Content previews
    l0_content: str = ""               # first ~400 chars
    overview_preview: str = ""         # first ~400 chars

    # Evidence & figures
    evidence_ids: List[str] = field(default_factory=list)
    evidence_titles: dict = field(default_factory=dict)   # evidence_id -> title
    evidence_images: List[str] = field(default_factory=list)  # clean_image_paths for first few evidences
    figure_images: List[str] = field(default_factory=list)
    figure_card_path: str = ""      # abs path to figure.card.md
    figure_caption: str = ""        # caption text
    # Table card fields
    table_card_path: str = ""       # abs path to table.card.md
    table_caption: str = ""         # table caption / title
    table_content_preview: str = "" # first ~300 chars of actual table data


# ------------------------------------------------------------------
# URI parsing
# ------------------------------------------------------------------

def _parse_uri(uri: str):
    """Return (paper_id, rel_parts) from a viking://resources/literature/... URI."""
    # Remove scheme
    path = uri.replace("viking://", "")
    parts = [p for p in path.split("/") if p]
    # parts: ['resources', 'literature', paper_id, inner_dir, *rel_parts]
    if len(parts) < 4:
        return "", []
    paper_id = parts[2]
    rel_parts = parts[4:]   # skip inner_dir (parts[3])
    return paper_id, rel_parts


# Regex patterns for uniquely-named combined files (new format after import fix)
_FIGURE_COMBINED_RE = re.compile(r"^figure_combined_(FIG\d+)\.md$")
_TABLE_COMBINED_RE = re.compile(r"^table_combined_(TAB\d+)\.md$")

# Regex patterns for MC card unique names (collision-free flat export since naming fix)
# e.g. CONDITION001_overview.md, CLAIM001_abstract.md, methods_overview.md
_MC_NAMED_CARD_RE = re.compile(
    r'^(CONDITION|CLAIM|MECHANISM|METRIC)(\d+)_(abstract|overview)\.md$', re.I
)
_MC_TYPE_CARD_RE = re.compile(
    r'^(methods|results|conditions|metrics|mechanisms|key_claims)_(abstract|overview)\.md$', re.I
)
_MC_PREFIX_TO_TYPE: dict = {
    "CONDITION": "conditions",
    "CLAIM": "key_claims",
    "MECHANISM": "mechanisms",
    "METRIC": "metrics",
}


def _detect_card(rel_parts: List[str]):
    """Return (card_type, card_id) from rel_path segments."""
    CARD_TYPES = {
        "figures": "figure",
        "methods": "methods",
        "results": "results",
        "conditions": "conditions",
        "metrics": "metrics",
        "key_claims": "key_claims",
        "mechanisms": "mechanisms",
        "tables": "tables",
    }
    # Priority 1: memory_cards path (full hierarchy preserved)
    if "memory_cards" in rel_parts:
        mc_idx = rel_parts.index("memory_cards")
        after = rel_parts[mc_idx + 1:]
        if after:
            cat = after[0]
            card_type = CARD_TYPES.get(cat, cat)
            card_id = after[1] if len(after) > 1 else ""
            return card_type, card_id
        return "memory_card", ""

    if rel_parts:
        fname = rel_parts[-1]
        parent = rel_parts[-2] if len(rel_parts) >= 2 else ""

        # Priority 2: uniquely-named combined files (e.g. figure_combined_FIG001.md)
        m = _FIGURE_COMBINED_RE.match(fname)
        if m:
            return "figure", m.group(1)
        m = _TABLE_COMBINED_RE.match(fname)
        if m:
            return "tables", m.group(1)
        # Also check parent-dir name (viking stores as figure_combined_FIG001/figure_combined_FIG001.md)
        m = _FIGURE_COMBINED_RE.match(parent + ".md") if parent else None
        if m:
            return "figure", m.group(1)
        m = _TABLE_COMBINED_RE.match(parent + ".md") if parent else None
        if m:
            return "tables", m.group(1)

        # Priority 2b: MC card unique names (new flat format since collision fix)
        # e.g. CONDITION001_overview.md, CLAIM001_abstract.md, methods_overview.md
        # Also matches when viking hoists: parent="CONDITION001_overview", fname=same
        for _check in ([fname] + ([parent + ".md"] if parent else [])):
            _m = _MC_NAMED_CARD_RE.match(_check)
            if _m:
                prefix = _m.group(1).upper()
                num = _m.group(2)
                ctype = _MC_PREFIX_TO_TYPE.get(prefix, prefix.lower() + "s")
                return ctype, f"{prefix}{num}"
            _m = _MC_TYPE_CARD_RE.match(_check)
            if _m:
                return _m.group(1).lower(), ""

        # Priority 3: filename-based detection (legacy/flattened viking paths)
        FNAME_MAP = {
            "figure_combined.md": "figure",
            "figure.card.md":     "figure",
            "caption.md":         "figure",
            "image_ref.md":       "figure",
            "table_combined.md":  "tables",
            "table.card.md":      "tables",
        }
        PARENT_DIR_MAP = {
            "figure_combined": "figure",
            "figurecard":      "figure",
            "table_combined":  "tables",
            "tablecard":       "tables",
        }
        SECTION_FNAMES = {"abstract.md", ".abstract.md", ".overview.md", "overview.md"}

        card_id_candidate = parent if (parent.startswith("FIG") or parent.startswith("TAB")) else ""

        if fname in FNAME_MAP:
            return FNAME_MAP[fname], card_id_candidate
        if parent in PARENT_DIR_MAP:
            return PARENT_DIR_MAP[parent], card_id_candidate
        if fname in SECTION_FNAMES:
            return "paper_summary", ""

    return "paper_section", ""


# ------------------------------------------------------------------
# File readers (safe)
# ------------------------------------------------------------------

def _read(path: Path, max_chars=500) -> str:
    try:
        text = path.read_text(encoding="utf-8")
        return text[:max_chars].strip()
    except Exception:
        return ""


def _parse_evidence_ids(text: str) -> List[str]:
    """Extract EVID_xxx / EVIDxxx patterns from any text."""
    found = re.findall(r"EVID[_-]?\w+", text)
    return list(dict.fromkeys(found))  # dedup, preserve order


def _read_evidence_links(paper_dir: Path) -> List[str]:
    """Extract all evidence_id values from evidence_links.json."""
    ev_file = paper_dir / "evidence_links.json"
    if not ev_file.exists():
        return []
    try:
        data = json.loads(ev_file.read_text(encoding="utf-8"))
        ids: List[str] = []
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("evidence_id", "evidence_ids", "related_evidence", "evidence_links"):
                val = item.get(key)
                if isinstance(val, str) and val:
                    ids.append(val)
                elif isinstance(val, list):
                    ids.extend(str(v) for v in val if v)
        return list(dict.fromkeys(ids))  # dedup preserving order
    except Exception:
        return []


def _read_evidence_links_full(paper_dir: Path) -> List[dict]:
    """Return raw evidence link items (list of dicts with evidence_id, title, clean_image_paths)."""
    ev_file = paper_dir / "evidence_links.json"
    if not ev_file.exists():
        return []
    try:
        data = json.loads(ev_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _read_metadata(paper_dir: Path) -> dict:
    meta_file = paper_dir / "metadata.json"
    if meta_file.exists():
        try:
            return json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _find_figure_images(paper_dir: Path, card_id: str) -> List[str]:
    """Return image file paths for a figure card (from image_ref.md or figures/ dir)."""
    # Try image_ref.md in memory_cards/figures/{card_id}/
    image_ref = paper_dir / "memory_cards" / "figures" / card_id / "image_ref.md"
    if image_ref.exists():
        content = image_ref.read_text(encoding="utf-8")
        # Extract image paths or filenames mentioned
        paths = re.findall(r"`([^`]+\.(jpg|png|jpeg|gif|webp))`", content, re.I)
        if paths:
            return [p[0] for p in paths]

    # Fallback: glob figures/ dir for card_id pattern
    figures_dir = paper_dir / "figures"
    if figures_dir.exists() and card_id:
        matches = sorted(figures_dir.glob(f"{card_id}_*.jpg")) + sorted(figures_dir.glob(f"{card_id}_*.png"))
        return [str(p) for p in matches]
    return []


# ------------------------------------------------------------------
# Main hydration function
# ------------------------------------------------------------------

def hydrate(matched_ctx, clean_root: Path, rank: int) -> HydratedResult:
    """Hydrate a MatchedContext object with LiteratureClean filesystem data."""
    uri = matched_ctx.uri
    score = getattr(matched_ctx, "score", 0.0) or 0.0

    paper_id, rel_parts = _parse_uri(uri)
    matched_file = rel_parts[-1] if rel_parts else ""
    card_type, card_id = _detect_card(rel_parts)
    relative_path = "/".join(rel_parts) if rel_parts else ""

    result = HydratedResult(
        rank=rank,
        score=score,
        paper_id=paper_id,
        matched_file=matched_file,
        matched_uri=uri,
        relative_path=relative_path,
        card_type=card_type,
        card_id=card_id,
    )

    if not paper_id:
        return result

    paper_dir = clean_root / paper_id
    if not paper_dir.exists():
        return result

    # --- Paper metadata ---
    meta = _read_metadata(paper_dir)
    result.paper_title = meta.get("title", "")
    result.paper_doi = meta.get("doi_url") or meta.get("doi", "")
    result.paper_year = str(meta.get("year", ""))
    result.paper_journal = meta.get("journal", "")
    raw_paths = meta.get("raw_paths") or {}
    result.source_pdf_path = (
        raw_paths.get("origin_pdf")
        or raw_paths.get("source_pdf")
        or raw_paths.get("pdf_path")
        or ""
    )

    # --- L0 / L1 paths: determine which dir to look in ---
    if card_type in ("figure", "methods", "results", "conditions",
                     "metrics", "key_claims", "mechanisms", "tables") and card_id:
        card_dir = paper_dir / "memory_cards" / ("figures" if card_type == "figure" else card_type) / card_id
        if not card_dir.exists():
            # card without specific id (e.g. methods/ directly)
            card_dir = paper_dir / "memory_cards" / card_type
        result.memory_card_path = str(card_dir)
        l0 = card_dir / ".abstract.md"
        l1 = card_dir / ".overview.md"
    elif card_type in ("methods", "results") and not card_id:
        card_dir = paper_dir / "memory_cards" / card_type
        result.memory_card_path = str(card_dir)
        l0 = card_dir / ".abstract.md"
        l1 = card_dir / ".overview.md"
    else:
        # paper-level or section
        l0 = paper_dir / ".abstract.md"
        l1 = paper_dir / ".overview.md"

    result.l0_path = str(l0) if l0.exists() else ""
    result.l1_path = str(l1) if l1.exists() else ""
    result.l0_content = _read(l0, 500) if l0.exists() else ""
    result.overview_preview = _read(l1, 500) if l1.exists() else ""

    # --- Evidence IDs ---
    if card_type == "figure" and card_id:
        # Figure-specific: read from figure.card.md first
        fig_card = paper_dir / "memory_cards" / "figures" / card_id / "figure.card.md"
        if fig_card.exists():
            result.figure_card_path = str(fig_card)
            card_text = fig_card.read_text(encoding="utf-8")
            result.evidence_ids = _parse_evidence_ids(card_text)
        if not result.evidence_ids:
            result.evidence_ids = _parse_evidence_ids(result.l0_content)
        # Caption
        cap = paper_dir / "memory_cards" / "figures" / card_id / "caption.md"
        if cap.exists():
            result.figure_caption = _read(cap, 300)
        # Images
        result.figure_images = _find_figure_images(paper_dir, card_id)
    elif card_type == "figure" and not card_id:
        # figure_combined.md or aggregated figurecard — extract EVIDs from the matched combined file
        # Try to read evidence from the content of the matched file via paper_dir/memory_cards/figures
        figs_mc = paper_dir / "memory_cards" / "figures"
        if figs_mc.exists():
            for fig_dir in sorted(figs_mc.iterdir()):
                if not fig_dir.is_dir():
                    continue
                fc = fig_dir / "figure.card.md"
                if fc.exists():
                    evids = _parse_evidence_ids(fc.read_text(encoding="utf-8", errors="replace"))
                    result.evidence_ids.extend(e for e in evids if e not in result.evidence_ids)
        result.evidence_ids = result.evidence_ids[:6]  # cap to avoid flooding
    elif card_type == "tables" and card_id:
        # Table-specific: read from table.card.md
        tab_card = paper_dir / "memory_cards" / "tables" / card_id / "table.card.md"
        if tab_card.exists():
            result.table_card_path = str(tab_card)
            card_text = tab_card.read_text(encoding="utf-8", errors="replace")
            result.evidence_ids = _parse_evidence_ids(card_text)
            for line in card_text.splitlines():
                if line.startswith("**Caption:**") or line.startswith("**Title:**"):
                    result.table_caption = line.split(":**", 1)[-1].strip().strip("*")
                    break
        if not result.evidence_ids:
            result.evidence_ids = _parse_evidence_ids(result.l0_content)
        # Actual table data preview
        tab_data = paper_dir / "tables" / f"{card_id}.md"
        if tab_data.exists():
            result.table_content_preview = _read(tab_data, 400)
    elif card_type == "tables" and not card_id:
        # table_combined.md or aggregated — extract from table cards
        tabs_mc = paper_dir / "memory_cards" / "tables"
        if tabs_mc.exists():
            for tab_dir in sorted(tabs_mc.iterdir()):
                if not tab_dir.is_dir():
                    continue
                tc = tab_dir / "table.card.md"
                if tc.exists():
                    evids = _parse_evidence_ids(tc.read_text(encoding="utf-8", errors="replace"))
                    result.evidence_ids.extend(e for e in evids if e not in result.evidence_ids)
        result.evidence_ids = result.evidence_ids[:6]
    elif card_type == "paper_summary":
        # Paper-level abstract/overview — return condensed paper-level evidence summary (max 6)
        from_links = _read_evidence_links(paper_dir)
        result.evidence_ids = from_links[:6]
        ev_full = _read_evidence_links_full(paper_dir)
        for ev in ev_full[:6]:
            eid = ev.get("evidence_id", "")
            if eid:
                title = ev.get("title", "")
                if title:
                    result.evidence_titles[eid] = title
    else:
        # Paper section (chapter, results, etc.) — gather from evidence_links + L0 scan
        from_links = _read_evidence_links(paper_dir)
        from_text = _parse_evidence_ids(result.l0_content)
        combined = list(dict.fromkeys(from_links + from_text))
        result.evidence_ids = combined[:12]  # cap at 12
        # Populate titles and sample images from evidence_links.json
        ev_full = _read_evidence_links_full(paper_dir)
        for ev in ev_full:
            eid = ev.get("evidence_id", "")
            if eid:
                title = ev.get("title", "")
                if title:
                    result.evidence_titles[eid] = title
                if len(result.evidence_images) < 6:
                    for img in ev.get("clean_image_paths", [])[:2]:
                        result.evidence_images.append(img)

    return result


# ------------------------------------------------------------------
# Pretty-print helper
# ------------------------------------------------------------------

def print_hydrated(h: HydratedResult, verbose: bool = False) -> None:
    """Print a HydratedResult in a readable format."""
    print(f"[{h.rank}] {h.paper_id}")
    print(f"    Score      : {h.score:.4f}")
    if h.paper_title:
        title = h.paper_title[:90] + ("..." if len(h.paper_title) > 90 else "")
        print(f"    Title      : {title}")
    if h.paper_year or h.paper_journal:
        print(f"    Published  : {h.paper_year} | {h.paper_journal}")
    if h.paper_doi:
        print(f"    DOI        : {h.paper_doi}")
    # Card type + matched info
    card_label = h.card_type + (f" / {h.card_id}" if h.card_id else "")
    print(f"    Card type  : {card_label}")
    print(f"    Matched    : {h.matched_file}")
    if verbose and h.relative_path and h.relative_path != h.matched_file:
        print(f"    Rel path   : {h.relative_path}")
    if verbose and h.matched_uri:
        print(f"    URI        : {h.matched_uri}")
    if h.memory_card_path:
        print(f"    Card path  : {h.memory_card_path}")
    if h.evidence_ids:
        if h.evidence_titles:
            ev_parts = []
            for eid in h.evidence_ids:
                title = h.evidence_titles.get(eid, "")
                if title:
                    short_title = title[:55] + "..." if len(title) > 55 else title
                    ev_parts.append(f"{eid} ({short_title})")
                else:
                    ev_parts.append(eid)
            ev_line = ", ".join(ev_parts[:6])
            if len(h.evidence_ids) > 6:
                ev_line += f", ... (+{len(h.evidence_ids)-6} more)"
        else:
            ev_line = ", ".join(h.evidence_ids)
        print(f"    Evidence   : {ev_line}")
    if h.figure_card_path:
        print(f"    Fig card   : {h.figure_card_path}")
    if h.figure_caption:
        cap_short = h.figure_caption.splitlines()[0][:120] if h.figure_caption else ""
        print(f"    Caption    : {cap_short}")
    if h.figure_images:
        for img in h.figure_images[:3]:
            print(f"    Figure     : {img}")
    if verbose and h.evidence_images:
        print(f"    Sample imgs:")
        for img in h.evidence_images[:6]:
            print(f"      {img}")
    if h.table_card_path:
        print(f"    Table card : {h.table_card_path}")
    if h.table_caption:
        print(f"    Table title: {h.table_caption[:120]}")
    if verbose and h.table_content_preview:
        print(f"    --- Table data preview ---")
        for line in h.table_content_preview.splitlines()[:8]:
            print(f"    {line}")
    if h.source_pdf_path:
        print(f"    Source PDF : {h.source_pdf_path}")
    if h.l0_path:
        print(f"    L0 path    : {h.l0_path}")
    if verbose and h.l0_content:
        print(f"    --- L0 abstract ---")
        for line in h.l0_content.splitlines()[:8]:
            print(f"    {line}")
    if h.l1_path:
        print(f"    L1 path    : {h.l1_path}")
    if verbose and h.overview_preview:
        print(f"    --- L1 overview preview ---")
        for line in h.overview_preview.splitlines()[:6]:
            print(f"    {line}")

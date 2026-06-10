"""Three-stage retrieval + generation pipeline for literature QA.

Stage ①: Mixed L0 vector search (paper + section .abstract.md)
Stage ②: L1 navigation via .overview.md → Top-5 sections
Stage ③: LLM Judge selects relevant paragraphs → evidence output

Usage:
    python qa_pipeline.py "What materials resist reverse current degradation?"
    python qa_pipeline.py --limit 10 --top-sections 3 "query string"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent.resolve()
AUTOHYSEEKER = HERE.parent.resolve()
AGENT_MODELS_PATH = AUTOHYSEEKER / "configs" / "agent_models.toml"
OV_DATA_PATH = AUTOHYSEEKER / "data" / "openviking_v2"
OV_CONFIG_PATH = AUTOHYSEEKER / "OpenViking" / ".local_dev" / "ov.conf"

# ── LLM Judge Prompt (from 10_Abstract+overview Prompt.md) ────────────
JUDGE_SYSTEM = (
    "You are a scientific paragraph selector. "
    "Output a strict JSON array, nothing else."
)

JUDGE_USER = """User query:
{query}

Below are paragraphs from a scientific paper section. Each has an ID.

{section_content}

Read all paragraphs and select those directly relevant to the query.

Criteria:
- Does the paragraph contain information matching the query (causal relationships, parameter ranges, method descriptions, experimental conditions, performance comparisons)?
- The paragraph's topic does not need to exactly match the query — retain it if it contains useful information.
- If no paragraphs are relevant, output [].

Output format (strict JSON array only, no other text):
["P003", "P005"]"""


# ── Helpers ────────────────────────────────────────────────────────────

def _ensure_openviking_imports() -> None:
    p = AUTOHYSEEKER / "OpenViking"
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))
    pp = p / "openviking"
    if pp.exists() and str(pp) not in sys.path:
        sys.path.insert(0, str(pp))
    agfs = p / "third_party" / "agfs" / "agfs-sdk" / "python"
    if agfs.exists() and str(agfs) not in sys.path:
        sys.path.insert(0, str(agfs))


def load_chat_llm_config() -> dict[str, Any]:
    with AGENT_MODELS_PATH.open("rb") as fh:
        raw = tomllib.load(fh)
    chat = raw.get("chat", {})
    if not isinstance(chat, dict):
        raise RuntimeError("agent_models.toml [chat] section missing")
    return {
        "model": chat["model"],
        "base_url": chat["base_url"],
        "api_key": os.path.expandvars(chat["api_key"]),
        "temperature": chat.get("temperature", 0.3),
        "max_tokens": chat.get("max_tokens", 2000),
    }


def init_client():
    _ensure_openviking_imports()
    os.environ.setdefault(
        "OPENVIKING_CONFIG_FILE", str(OV_CONFIG_PATH)
    )
    from openviking.sync_client import SyncOpenViking

    client = SyncOpenViking(path=str(OV_DATA_PATH))
    client.initialize()
    return client


def load_paper_index() -> dict[str, Path]:
    """Map paper_id → paper_dir for all LiteratureClean papers."""
    index: dict[str, Path] = {}
    for d in sorted(HERE.iterdir()):
        if d.is_dir() and (d / "metadata.json").exists() and (d / "paragraph_index.json").exists():
            index[d.name] = d
    return index


def load_paragraph_map(paper_dirs: dict[str, Path]) -> dict[str, list[dict]]:
    """Build a map of section_identifier → paragraph entries.

    The key is "paper_id/section_id" (e.g. "2025_sha.../S03").
    Each value is a list of paragraph entries from paragraph_index.json.
    """
    pmap: dict[str, list[dict]] = {}
    for paper_id, paper_dir in paper_dirs.items():
        pi_file = paper_dir / "paragraph_index.json"
        if not pi_file.exists():
            continue
        paragraphs = json.loads(pi_file.read_text(encoding="utf-8"))
        for p in paragraphs:
            sid = p.get("section_id", "")
            key = f"{paper_id}/{sid}"
            pmap.setdefault(key, []).append(p)
    return pmap


# ── Lexical Scoring Helpers ──────────────────────────────────────────

# Strong-match patterns: material names, chemical formulas, specialized phrases
_STRONG_PATTERN = re.compile(
    r"[A-Z][a-z]?[A-Z][a-z]?[\dA-Za-z\-]*"          # NiCoP, Cr2O3, NiFe-LDH
    r"|\b[A-Z]{2,}\b"                                  # HER, TOF-SIMS, AEM
    r"|\b[a-z]+-[a-z]+(?:-[a-z]+)+\b"                  # reverse-current, start-up
    r"|\$\\.*?\$"                                      # LaTeX math
)

_STRONG_WORDS: set[str] = set()  # Built from query below


# Common English stop words to exclude from lexical matching
_STOP_WORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "about", "what", "which", "who", "whom",
    "this", "that", "these", "those", "and", "but", "or", "if", "while",
    "although", "however", "therefore", "thus", "also", "well", "et", "al",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenizer."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _compute_lexical_score(query: str, abstract: str) -> float:
    """Compute lexical match score between query and abstract text.

    strong_match (0.75 weight): non-stopword tokens from query that
      appear in the abstract (material names, chemical formulas,
      specialized terms, numeric-containing tokens).
    generic_keyword (0.25 weight): remaining alphanumeric tokens.
    """
    if not abstract:
        return 0.0
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0
    abs_tokens = set(_tokenize(abstract))

    # Split into strong (non-stop) and generic (stop words)
    strong = [t for t in query_tokens if t not in _STOP_WORDS]
    generic = [t for t in query_tokens if t in _STOP_WORDS]

    if not strong:
        return 0.0

    strong_match = sum(1 for t in strong if t in abs_tokens) / len(strong)
    generic_match = sum(1 for t in generic if t in abs_tokens) / len(generic) if generic else 0.0

    return 0.75 * strong_match + 0.25 * generic_match


# ── Stage ①: Hybrid L0 Search (semantic + lexical) ──────────────────

def search_l0(
    query: str,
    client,
    limit: int = 20,
    target_uri: str = "viking://resources/literature",
) -> list[dict[str, Any]]:
    """Stage ①: hybrid search — semantic (bge-m3) + lexical (keyword).

    Returns Top-20 hits, each scored as:
      L0_score = 0.55 * semantic_score + 0.45 * lexical_score
    """
    results = client.find(query, target_uri=target_uri, limit=max(limit * 2, 50))
    hits = []
    max_sem = 0.0
    raw_hits = []
    paper_abstracts: dict[str, str] = {}

    for r in results:
        uri = getattr(r, "uri", "")
        score = getattr(r, "score", 0.0)
        uri = uri.rstrip("/")
        paper_id = _extract_paper_id(uri)

        # Read paper-level .abstract.md once for lexical scoring
        if paper_id and paper_id not in paper_abstracts:
            try:
                pa = client.read(f"viking://resources/literature/{paper_id}/.abstract.md")
                paper_abstracts[paper_id] = pa
            except Exception:
                paper_abstracts[paper_id] = ""
        abstract = paper_abstracts.get(paper_id, "")

        max_sem = max(max_sem, score)
        raw_hits.append({
            "uri": uri,
            "semantic_score": score,
            "abstract": abstract[:800],
            "paper_id": paper_id,
        })

    # Normalize semantic scores to [0,1] and merge with lexical
    for h in raw_hits:
        sem_norm = h["semantic_score"] / max_sem if max_sem > 0 else 0.0
        lex = _compute_lexical_score(query, h["abstract"])
        h["score"] = round(0.55 * sem_norm + 0.45 * lex, 4)
        h["semantic_score"] = round(sem_norm, 4)
        h["lexical_score"] = round(lex, 4)

    # Sort by hybrid score, deduplicate by paper_id, take top-k
    seen: set[str] = set()
    hits = []
    for h in sorted(raw_hits, key=lambda x: x["score"], reverse=True):
        if h["paper_id"] not in seen:
            seen.add(h["paper_id"])
            hits.append(h)
        if len(hits) >= limit:
            break

    return hits


# ── Stage ②: Section Re-scoring ─────────────────────────────────────

def _read_section_abstract(client, paper_id: str, section_dir: str) -> str:
    """Read a section's .abstract.md from OpenViking."""
    try:
        uri = f"viking://resources/literature/{paper_id}/sections/{section_dir}"
        return client.read(f"{uri}/.abstract.md")
    except Exception:
        return ""


def _local_semantic_score(query: str, abstract: str) -> float:
    """Compute cosine similarity using local bge-m3 embedding."""
    if not abstract:
        return 0.0
    try:
        from sentence_transformers import SentenceTransformer
        _model = _get_local_model()
        q_emb = _model.encode([query], normalize_embeddings=True)[0]
        a_emb = _model.encode([abstract], normalize_embeddings=True)[0]
        return float(q_emb @ a_emb)
    except Exception:
        return 0.0


_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer("BAAI/bge-m3")
    return _local_model


def navigate_l1(
    hits: list[dict[str, Any]],
    client,
    query: str = "",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Stage ②: re-score all sections with hybrid formula.

    For each L0 paper hit, reads the overview and expands to sections.
    Each section gets its own section_score:
      section_score = 0.55 * section_semantic + 0.45 * section_lexical
    """
    candidates: list[dict[str, Any]] = []
    # Cache for query embedding (computed once)
    query_emb = None

    for hit in hits:
        paper_id = hit["paper_id"]
        paper_uri = f"viking://resources/literature/{paper_id}"

        try:
            overview = client.overview(paper_uri)
        except Exception:
            overview = ""

        if not overview or len(overview) < 30:
            continue

        # Direct section hit
        if "/sections/" in hit["uri"]:
            parts = hit["uri"].split("/")
            section_dir = ""
            for j, p in enumerate(parts):
                if p == "sections" and j + 1 < len(parts):
                    section_dir = parts[j + 1]
                    break
            if section_dir:
                sec_abs = _read_section_abstract(client, paper_id, section_dir)
                sec_sem = _local_semantic_score(query, sec_abs) if query else hit.get("semantic_score", hit["score"])
                sec_lex = _compute_lexical_score(query, sec_abs)
                sec_score = 0.55 * sec_sem + 0.45 * sec_lex
                candidates.append({
                    "paper_id": paper_id,
                    "section_dir": section_dir,
                    "score": sec_score,
                    "source": "direct_section",
                })

        # Parse paper overview for all sections, re-score each
        parsed = _parse_sections_from_overview(overview, paper_id, hit["score"])
        for psec in parsed:
            sec_abs = _read_section_abstract(client, paper_id, psec["section_dir"])
            sec_sem = _local_semantic_score(query, sec_abs) if query else psec["score"]
            sec_lex = _compute_lexical_score(query, sec_abs)
            psec["score"] = 0.55 * sec_sem + 0.45 * sec_lex
        candidates.extend(parsed)

    seen: set[str] = set()
    ranked: list[dict] = []
    for c in sorted(candidates, key=lambda x: x["score"], reverse=True):
        key = f"{c['paper_id']}/{c['section_dir']}"
        if key not in seen:
            seen.add(key)
            ranked.append(c)

    return ranked[:top_k]


def _extract_paper_id(uri: str) -> str:
    """Extract paper_id from a viking URI."""
    # viking://resources/literature/{paper_id}/...
    prefix = "viking://resources/literature/"
    rest = uri[len(prefix):] if uri.startswith(prefix) else uri
    return rest.split("/")[0]


def _parse_sections_from_overview(
    overview: str, paper_id: str, base_score: float
) -> list[dict[str, Any]]:
    """Parse paper overview to extract section entries.

    Matches the Section Index format from English/Chinese overviews:
      Section Index: / 章节索引：
        001-xxx: description / S01: description
        002-xxx: description / S02: description
    """
    sections = []
    # Match section entries after "Section Index:" or "章节索引："
    # Lines like: "  001-cathode-oxidation-...: description"
    # or: "  S01: description"
    section_re = re.compile(
        r"^\s*(?:(\d{3})-[\w-]+|S(\d{2}))\s*[:：]\s*(.+)", re.MULTILINE
    )
    for m in section_re.finditer(overview):
        num_prefix = m.group(1)  # e.g. "001"
        s_prefix = m.group(2)   # e.g. "01"
        desc = m.group(3).strip()
        if num_prefix:
            section_dir = m.group(0).split(":")[0].strip().split("：")[0].strip()
            sections.append({
                "paper_id": paper_id,
                "section_dir": section_dir,
                "score": base_score,
                "source": "paper_navigation",
            })
        elif s_prefix:
            sections.append({
                "paper_id": paper_id,
                "section_dir": s_prefix,
                "score": base_score,
                "source": "paper_navigation",
            })
    return sections


def _resolve_section_id(
    paper_id: str,
    section_dir: str,
    para_map: dict[str, list[dict]],
) -> str | None:
    """Resolve a section_dir (e.g. '001-introduction') to section_id (e.g. 'S01').

    Uses the directory prefix number: '001' → section with that ordering.
    """
    # Extract numeric prefix from section_dir
    m = re.match(r"^(\d+)", section_dir)
    if not m:
        return None
    order = int(m.group(1))
    target_sid = f"S{order:02d}"

    # Find all section_ids for this paper
    paper_keys = [k for k in para_map if k.startswith(f"{paper_id}/")]
    # Sort by section_id
    sids = sorted(set(k.split("/")[1] for k in paper_keys))
    if target_sid in sids:
        return target_sid
    # Try index-based lookup
    if 1 <= order <= len(sids):
        return sids[order - 1]
    return None


# ── Stage ③: LLM Judge ───────────────────────────────────────────────

def judge_paragraphs(
    section_candidates: list[dict[str, Any]],
    query: str,
    paper_dirs: dict[str, Path],
    llm_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    """Stage ③: LLM reads section paragraphs, selects relevant ones.

    Returns list of dicts with: paragraph_id, text, evidence_id, linked_figures,
    linked_tables, paper_id, section_id.
    """
    results = []
    para_map = load_paragraph_map(paper_dirs)

    for sec in section_candidates:
        paper_id = sec["paper_id"]
        section_dir = sec.get("section_dir", "")

        # Build key: "paper_id/S01" format from paragraph_index
        # section_dir is like "001-cathode-oxidation-..." from overview
        # we need to match it to section_id in paragraph index (e.g. "S01")
        section_id = _resolve_section_id(paper_id, section_dir, para_map)
        if not section_id:
            continue

        key = f"{paper_id}/{section_id}"

        paragraphs = para_map[key]
        if not paragraphs:
            continue

        # Build section content for LLM
        content_parts = []
        for p in paragraphs:
            pid = p.get("paragraph_id", "?")
            text = p.get("text_preview", "")
            # Try to read full text from the paragraph file
            cp = p.get("content_path", "")
            if cp:
                pp = paper_dirs.get(paper_id, HERE) / cp
                if pp.exists():
                    full = pp.read_text(encoding="utf-8", errors="replace")
                    m = re.search(
                        r"## Text\s*\n\s*\n(.+?)(?=\n## |\Z)", full, re.DOTALL
                    )
                    if m:
                        text = m.group(1).strip()
            if text:
                content_parts.append(f"=== {pid} ===\n{text}")

        section_content = "\n\n".join(content_parts)
        if not section_content:
            continue

        # Call LLM Judge
        user_prompt = JUDGE_USER.format(query=query, section_content=section_content)
        try:
            raw = _call_llm(JUDGE_SYSTEM, user_prompt, llm_cfg)
            selected_ids = json.loads(raw)
        except Exception:
            continue

        if not isinstance(selected_ids, list):
            continue

        # Collect selected paragraphs
        for para in paragraphs:
            if para["paragraph_id"] in selected_ids:
                results.append({
                    "paragraph_id": para["paragraph_id"],
                    "paper_id": paper_id,
                    "section_id": section_id,
                    "text": para.get("text_preview", ""),
                    "evidence_id": para.get("evidence_id", ""),
                    "linked_figures": para.get("linked_figures", []),
                    "linked_tables": para.get("linked_tables", []),
                    "content_path": para.get("content_path", ""),
                })

    return results


def _call_llm(system: str, user: str, cfg: dict[str, Any]) -> str:
    from openai import OpenAI

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    completion = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=cfg.get("max_tokens", 2000),
        stream=False,
    )
    if not completion.choices:
        return "[]"
    return (completion.choices[0].message.content or "[]").strip()


# ── Main Entry ────────────────────────────────────────────────────────

def query(
    query_str: str,
    client=None,
    paper_dirs: dict[str, Path] | None = None,
    llm_cfg: dict[str, Any] | None = None,
    *,
    limit: int = 15,
    top_sections: int = 5,
) -> dict[str, Any]:
    """Run the full three-stage pipeline."""
    if client is None:
        client = init_client()
    if paper_dirs is None:
        paper_dirs = load_paper_index()
    if llm_cfg is None:
        llm_cfg = load_chat_llm_config()

    # Stage ①
    l0_hits = search_l0(query_str, client, limit=limit)
    if not l0_hits:
        return {"query": query_str, "l0_hits": 0, "sections": 0, "results": []}

    # Stage ②
    sections = navigate_l1(l0_hits, client, query=query_str, top_k=top_sections)
    if not sections:
        return {"query": query_str, "l0_hits": len(l0_hits), "sections": 0, "results": []}

    # Stage ③
    results = judge_paragraphs(sections, query_str, paper_dirs, llm_cfg)

    return {
        "query": query_str,
        "l0_hits": len(l0_hits),
        "sections": len(sections),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Three-stage literature QA pipeline"
    )
    parser.add_argument(
        "query", type=str, nargs="?", default=None,
        help="Query string (if not provided, enters interactive mode)"
    )
    parser.add_argument(
        "--limit", type=int, default=15,
        help="Stage ① Top-k (default: 15)"
    )
    parser.add_argument(
        "--top-sections", type=int, default=5,
        help="Stage ② Top-k sections (default: 5)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON"
    )
    args = parser.parse_args()

    client = init_client()
    paper_dirs = load_paper_index()
    llm_cfg = load_chat_llm_config()

    print(f"Papers indexed: {len(paper_dirs)}")
    print(f"LLM: {llm_cfg['model']} @ {llm_cfg['base_url']}")

    if args.query:
        queries = [args.query]
    else:
        print("\nEnter queries (empty line to exit):")
        queries = []
        while True:
            try:
                q = input("> ").strip()
                if not q:
                    break
                queries.append(q)
            except (EOFError, KeyboardInterrupt):
                break

    for q in queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print(f"{'='*60}")

        result = query(
            q, client, paper_dirs, llm_cfg,
            limit=args.limit, top_sections=args.top_sections,
        )

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            continue

        print(f"\nStage ①: {result['l0_hits']} L0 hits")
        print(f"Stage ②: {result['sections']} sections")
        print(f"Stage ③: {len(result['results'])} paragraphs selected\n")

        if not result["results"]:
            print("(no relevant paragraphs found)")
            continue

        for i, p in enumerate(result["results"], 1):
            print(f"[{i}] {p['paper_id'][:40]} / {p['section_id']} / {p['paragraph_id']}")
            print(f"    evidence_id: {p['evidence_id']}")
            if p["linked_figures"]:
                print(f"    figures: {', '.join(p['linked_figures'])}")
            if p["linked_tables"]:
                print(f"    tables: {', '.join(p['linked_tables'])}")
            print(f"    text: {p['text'][:300]}")
            print()


if __name__ == "__main__":
    main()

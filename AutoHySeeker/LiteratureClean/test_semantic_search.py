"""Quick semantic search test against the local OpenViking index.

Usage:
    python LiteratureClean/test_semantic_search.py
    python LiteratureClean/test_semantic_search.py --query "electrode degradation"
    python LiteratureClean/test_semantic_search.py --query "reverse current" --limit 5
    python LiteratureClean/test_semantic_search.py --query "reverse current" --limit 5 --verbose
    python LiteratureClean/test_semantic_search.py --query "reverse current" --limit 5 --raw
    python LiteratureClean/test_semantic_search.py --query "reverse current" --target viking://resources/literature
"""
import argparse
import os
import sys
from pathlib import Path
from typing import List

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent  # AutoHySeeker/
OV_CONF_PATH = REPO_ROOT / "OpenViking" / ".local_dev" / "ov.conf"
OV_DATA_PATH = REPO_ROOT / "data" / "openviking"

sys.path.insert(0, str(REPO_ROOT / "OpenViking"))


# ------------------------------------------------------------------
# Diversity / dedup helpers
# ------------------------------------------------------------------

def _diversify(hydrated, limit: int):
    """Deduplicate and diversify hydrated results.

    Strategy:
      1. Keep highest-score per (paper_id, matched_file) — dedup exact file hits.
      2. Among survivors, prefer different paper_ids first pass, then fill remainder.
      Returns at most `limit` results.
    """
    from search_hydrate import HydratedResult  # type: ignore

    # Step 1: dedup by exact (paper_id, matched_file)
    seen: dict = {}
    for h in hydrated:
        key = (h.paper_id, h.matched_file)
        if key not in seen or h.score > seen[key].score:
            seen[key] = h
    candidates = sorted(seen.values(), key=lambda h: h.score, reverse=True)

    # Step 2: prefer one result per paper_id first
    diversified: List[HydratedResult] = []
    seen_paper: set = set()
    remainder: List[HydratedResult] = []
    for h in candidates:
        if h.paper_id not in seen_paper:
            diversified.append(h)
            seen_paper.add(h.paper_id)
        else:
            remainder.append(h)

    diversified.extend(remainder)
    return diversified[:limit]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="reverse current", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Max results")
    parser.add_argument("--score", type=float, default=None, help="Min score threshold")
    parser.add_argument("--target", default="viking://resources/literature", help="Viking URI prefix")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show L0/L1 content preview")
    parser.add_argument("--raw", action="store_true", help="Skip dedup/diversify, show raw results")
    args = parser.parse_args()

    if not OV_CONF_PATH.exists():
        print(f"ERROR: Config not found: {OV_CONF_PATH}")
        sys.exit(1)

    os.environ["OPENVIKING_CONFIG_FILE"] = str(OV_CONF_PATH)

    try:
        from openviking.sync_client import SyncOpenViking  # type: ignore
    except ImportError:
        print("ERROR: openviking package not found. Activate the venv.")
        sys.exit(1)

    # Import hydration
    sys.path.insert(0, str(HERE))
    from search_hydrate import hydrate, print_hydrated  # type: ignore

    print(f"Connecting to OpenViking at {OV_DATA_PATH} ...")
    client = SyncOpenViking(path=str(OV_DATA_PATH))
    client.initialize()
    print("Connected.\n")

    print(f"Query : {args.query!r}")
    print(f"Limit : {args.limit}  |  Score threshold: {args.score}  |  Target: {args.target}")
    if not args.raw:
        print(f"Mode  : diversified (fetch x4, dedup + diversify by paper)")
    print("=" * 70)

    # Fetch more candidates when diversifying
    fetch_limit = args.limit if args.raw else args.limit * 4

    results = client.find(
        query=args.query,
        target_uri=args.target,
        limit=fetch_limit,
        score_threshold=args.score,
    )

    # FindResult dataclass
    items = getattr(results, "resources", None)
    if items is None:
        items = results if isinstance(results, list) else []

    if not items:
        print("No results returned.")
        return

    # Hydrate all
    clean_root = HERE  # LiteratureClean/
    hydrated = []
    for item in items:
        if hasattr(item, "uri"):
            hydrated.append(hydrate(item, clean_root, rank=0))

    # Diversify (or keep raw)
    if args.raw:
        display = hydrated[:args.limit]
    else:
        display = _diversify(hydrated, args.limit)

    # Post-diversify score filter
    if args.score is not None:
        before = len(display)
        display = [h for h in display if h.score >= args.score]
        filtered = before - len(display)
        filter_note = f"  (filtered {filtered} below score {args.score})" if filtered else ""
    else:
        filter_note = ""

    if args.raw:
        print(f"Found {len(items)} raw result(s) (showing {len(display)}){filter_note}:\n")
    else:
        print(f"Found {len(items)} raw → {len(display)} diversified result(s){filter_note}:\n")

    for i, h in enumerate(display, 1):
        h.rank = i
        print_hydrated(h, verbose=args.verbose)
        print()



if __name__ == "__main__":
    main()

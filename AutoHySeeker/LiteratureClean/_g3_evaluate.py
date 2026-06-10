"""G3 evaluation: run all 18 queries and compute Recall/MRR/Precision."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from qa_pipeline import init_client, load_paper_index, load_chat_llm_config, search_l0

HERE = Path(__file__).parent
GT_FILE = HERE / "g3_ground_truth.json"
RESULTS_FILE = HERE / "g3_results.json"


def compute_recall_at_k(hit_papers: set, expected_papers: set, k: int) -> float:
    if not expected_papers:
        return 1.0  # negative sample: empty expected = perfect
    hits = set(list(hit_papers)[:k])
    return len(hits & expected_papers) / len(expected_papers)


def compute_mrr(hit_papers: list, expected_papers: set) -> float:
    if not expected_papers:
        return 1.0
    for i, h in enumerate(hit_papers, 1):
        if h in expected_papers:
            return 1.0 / i
    return 0.0


def main():
    print("Loading models...")
    client = init_client()
    paper_dirs = load_paper_index()
    llm_cfg = load_chat_llm_config()
    print(f"LLM: {llm_cfg['model']}")

    # Load ground truth
    gt = json.loads(GT_FILE.read_text(encoding="utf-8"))

    # Run all queries
    results = []
    for item in gt["queries"]:
        qid = item["id"]
        query_str = item["query"]
        level = item["level"]
        expected = item["expected"]
        expected_keys = set(f"{e['paper']}/{e['section']}" for e in expected)

        print(f"\n[{qid}] {query_str[:80]}...")

        # Stage 1: get L0 hits
        l0_hits = search_l0(query_str, client, limit=15)

        # Extract paper_ids from hits (deduplicated, keeping order)
        hit_keys = []
        seen = set()
        hit_papers = []
        for h in l0_hits:
            pid = h.get("paper_id", "")
            if pid and pid not in seen:
                seen.add(pid)
                hit_papers.append(pid)

        # Also check section-level hits
        for h in l0_hits:
            uri = h.get("uri", "")
            if "/sections/" in uri:
                # Extract section info from URI
                parts = uri.split("/")
                sections_idx = -1
                for j, p in enumerate(parts):
                    if p == "sections":
                        sections_idx = j
                        break
                if sections_idx >= 0 and sections_idx + 1 < len(parts):
                    pid = parts[sections_idx - 1] if sections_idx > 0 else ""
                    if pid:
                        key = f"{pid}/{parts[sections_idx + 1]}"
                        if key not in seen:
                            seen.add(key)
                            hit_keys.append(key)

        # Stage 1 metrics
        recall5 = compute_recall_at_k(set(hit_papers), set(e["paper"] for e in expected), 5)
        recall10 = compute_recall_at_k(set(hit_papers), set(e["paper"] for e in expected), 10)
        mrr = compute_mrr(hit_papers, set(e["paper"] for e in expected))

        # Stage 3: full pipeline
        from qa_pipeline import query as full_query
        full_result = full_query(query_str, client, paper_dirs, llm_cfg, limit=15, top_sections=3)

        r = {
            "id": qid,
            "query": query_str,
            "level": level,
            "l0_hits": len(l0_hits),
            "l0_papers": hit_papers[:10],
            "l0_section_keys": hit_keys[:10],
            "expected_keys": list(expected_keys),
            "recall5": round(recall5, 3),
            "recall10": round(recall10, 3),
            "mrr": round(mrr, 3),
            "stage2_sections": full_result["sections"],
            "stage3_paragraphs": len(full_result["results"]),
            "stage3_paragraph_ids": [
                f"{p['paper_id'][:30]}/{p['section_id']}/{p['paragraph_id']}"
                for p in full_result["results"]
            ],
        }
        results.append(r)
        print(f"  R@5={recall5:.2f} R@10={recall10:.2f} MRR={mrr:.2f} "
              f"S2_sections={full_result['sections']} S3_paras={len(full_result['results'])}")

    # Aggregate by level
    levels = {}
    for r in results:
        lv = r["level"]
        if lv not in levels:
            levels[lv] = {"recall5": [], "recall10": [], "mrr": [], "count": 0}
        levels[lv]["recall5"].append(r["recall5"])
        levels[lv]["recall10"].append(r["recall10"])
        levels[lv]["mrr"].append(r["mrr"])
        levels[lv]["count"] += 1

    print("\n" + "=" * 60)
    print("SUMMARY BY LEVEL")
    print("=" * 60)
    for lv, metrics in sorted(levels.items()):
        n = metrics["count"]
        avg_r5 = sum(metrics["recall5"]) / n
        avg_r10 = sum(metrics["recall10"]) / n
        avg_mrr = sum(metrics["mrr"]) / n
        print(f"  {lv:15s} (n={n}): R@5={avg_r5:.2f}  R@10={avg_r10:.2f}  MRR={avg_mrr:.2f}")

    # Negative sample check
    neg_results = [r for r in results if r["level"] == "negative"]
    neg_ok = all(r["stage3_paragraphs"] == 0 for r in neg_results)
    print(f"\nNegative accuracy: {'PASS' if neg_ok else 'FAIL'} "
          f"({sum(1 for r in neg_results if r['stage3_paragraphs']==0)}/{len(neg_results)} empty)")

    # Save
    RESULTS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResults saved to {RESULTS_FILE}")

    client.close()


if __name__ == "__main__":
    main()

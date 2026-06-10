"""Import LiteratureClean papers into OpenViking (embedded local mode).

Usage:
    python import_to_openviking.py               # import all unimported papers
    python import_to_openviking.py --paper-id 2023_uchino_...
    python import_to_openviking.py --list        # list importable papers & embedding info
    python import_to_openviking.py --dry-run     # preview without importing
    python import_to_openviking.py --overwrite   # re-import already-imported papers
    python import_to_openviking.py --reindex     # wipe vector index & re-import all papers

Embedding separation model
--------------------------
LiteratureClean/ (preprocessing)  <->  data/openviking/ (vector index) are separate.
To switch embedding model:
    1. Update ov.conf: change embedding.dense.{provider,model,dimension}
    2. Run: python import_to_openviking.py --reindex
Embedding metadata is tracked in embedding_index_meta.json.

Technical notes
---------------
OpenViking's directory_scan._should_skip_file() skips any file whose name starts
with '.'. Our entire L0/L1 system uses .abstract.md and .overview.md.

This script works around the limitation by:
1. Creating a temporary export directory per paper
2. Copying all relevant files, renaming .abstract.md → abstract.md and
   .overview.md → overview.md (recursively through memory_cards/)
3. Calling client.add_resource(path=tmp_dir, target=..., wait=True)
4. Cleaning up the temp directory

Import target URI: literature/{paper_id}
  → viking://resources/literature/{paper_id}/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERE = Path(__file__).parent.resolve()                      # LiteratureClean/
AUTOHYSEEKER = HERE.parent.resolve()                        # AutoHySeeker/
OV_DATA_PATH = AUTOHYSEEKER / "data" / "openviking_v2"
OV_CONF_PATH = AUTOHYSEEKER / "OpenViking" / ".local_dev" / "ov.conf"
OPENVIKING_SRC_PATH = AUTOHYSEEKER / "OpenViking"
AGENT_MODELS_PATH = AUTOHYSEEKER / "configs" / "agent_models.toml"
CLEAN_ROOT = HERE
IMPORT_LOG = CLEAN_ROOT / "openviking_import_log.json"
EMBEDDING_META = CLEAN_ROOT / "embedding_index_meta.json"
VALIDATION_REPORT_JSON = CLEAN_ROOT / "validation_report.json"
OVERVIEW_QUALITY_REPORT_JSON = CLEAN_ROOT / "overview_quality_report.json"
SEMANTIC_CONFLICT_REPORT_JSON = CLEAN_ROOT / "semantic_conflict_report.json"
FALLBACK_REVIEW_REPORT_JSON = CLEAN_ROOT / "fallback_review_report.json"
ENGINE_PYD_PATH = OPENVIKING_SRC_PATH / "openviking" / "storage" / "vectordb" / "engine.pyd"

# Exit codes for text LLM fail-fast gate
EXIT_LLM_CFG_READ_ERR = 20
EXIT_LLM_CFG_INVALID = 21
EXIT_STALE_BLOCKED = 22

GEN_STATUS_FILENAME = "generation_status.json"
OV_INDEX_DIRNAME = "ov_index"
STATUS_SOURCE_INPUTS = [
    "paragraph_index.json",
    "document_tree.json",
    "image_manifest.json",
    "table_manifest.json",
    "full_clean.md",
]


def _safe_read_json(path: Path) -> Any | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _detect_engine_python_dll() -> str | None:
    """Best-effort detect required CPython DLL name from engine.pyd bytes."""
    if not ENGINE_PYD_PATH.exists() or not ENGINE_PYD_PATH.is_file():
        return None
    try:
        blob = ENGINE_PYD_PATH.read_bytes()
        m = re.search(rb"python3\d\d\.dll", blob)
        if not m:
            return None
        return m.group(0).decode("ascii", errors="ignore")
    except Exception:
        return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_source_checksum(paper_dir: Path) -> tuple[str, list[str]]:
    """Compute deterministic checksum for generation inputs per paper."""
    entries: list[str] = []
    for rel in STATUS_SOURCE_INPUTS:
        p = paper_dir / rel
        if p.exists() and p.is_file():
            entries.append(f"{rel}:{_sha256_file(p)}")

    if not entries:
        return "", []

    blob = "\n".join(sorted(entries)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest(), sorted(entries)


def detect_generated_targets(paper_dir: Path) -> tuple[bool, int]:
    """Return (paper_targets_ok, section_targets_count)."""
    ov_index = paper_dir / OV_INDEX_DIRNAME
    paper_targets_ok = (ov_index / "paper.abstract.md").exists() and (ov_index / "paper.overview.md").exists()

    section_targets_count = 0
    sections_root = ov_index / "sections"
    if sections_root.exists():
        for section_dir in sections_root.iterdir():
            if not section_dir.is_dir():
                continue
            if (section_dir / "abstract.md").exists() and (section_dir / "overview.md").exists():
                section_targets_count += 1

    return paper_targets_ok, section_targets_count


def validate_ov_index_for_paper(paper_dir: Path) -> dict[str, Any]:
    """E1: validate ov_index structure, section paths, and status chain for one paper."""
    ov_index = paper_dir / OV_INDEX_DIRNAME
    sections_dir = ov_index / "sections"
    status_file = ov_index / GEN_STATUS_FILENAME

    missing_files: list[str] = []
    placeholder_files: list[str] = []
    path_mismatch: list[str] = []
    index_chain_issues: list[str] = []

    required_paper_targets = [
        "paper.abstract.md",
        "paper.overview.md",
    ]
    for rel in required_paper_targets:
        p = ov_index / rel
        if not p.exists():
            missing_files.append(rel)
            continue
        if _is_missing_generation_file(p):
            placeholder_files.append(rel)

    expected_sections: set[str] = set()
    sbh_root = paper_dir / "sections_by_heading"
    if sbh_root.exists():
        for d in sorted(sbh_root.iterdir()):
            if not d.is_dir() or d.name == "_debug":
                continue
            expected_sections.add(d.name)

    actual_sections: set[str] = set()
    if sections_dir.exists():
        for d in sorted(sections_dir.iterdir()):
            if d.is_dir():
                actual_sections.add(d.name)

    for slug in sorted(expected_sections):
        for rel in [f"sections/{slug}/abstract.md", f"sections/{slug}/overview.md"]:
            p = ov_index / rel
            if not p.exists():
                missing_files.append(rel)
                continue
            if _is_missing_generation_file(p):
                placeholder_files.append(rel)

    extra_sections = sorted(actual_sections - expected_sections)
    if extra_sections:
        path_mismatch.extend([f"extra_section:{s}" for s in extra_sections])

    missing_sections = sorted(expected_sections - actual_sections)
    if missing_sections:
        path_mismatch.extend([f"missing_section_dir:{s}" for s in missing_sections])

    if not status_file.exists():
        index_chain_issues.append("missing_generation_status_json")
        status_payload = {}
    else:
        status_payload = read_generation_status(paper_dir)
        if not status_payload:
            index_chain_issues.append("invalid_generation_status_json")

    if status_payload:
        if not status_payload.get("source_checksum"):
            index_chain_issues.append("empty_source_checksum")
        status = str(status_payload.get("status", ""))
        if status not in {"fresh", "stale", "missing"}:
            index_chain_issues.append(f"invalid_status:{status}")

    issue_count = len(missing_files) + len(placeholder_files) + len(path_mismatch) + len(index_chain_issues)
    return {
        "paper_id": paper_dir.name,
        "status": "ok" if issue_count == 0 else "issue",
        "issue_count": issue_count,
        "missing_files": missing_files,
        "placeholder_files": placeholder_files,
        "path_mismatch": path_mismatch,
        "index_chain_issues": index_chain_issues,
        "expected_sections": len(expected_sections),
        "actual_sections": len(actual_sections),
        "checked_at": datetime.now().isoformat(),
    }


def build_validation_report(papers: list[Path]) -> dict[str, Any]:
    """E1: build batch validation report for ov_index health."""
    details: list[dict[str, Any]] = []
    summary = {
        "papers": len(papers),
        "ok": 0,
        "issue": 0,
        "missing_files": 0,
        "placeholder_files": 0,
        "path_mismatch": 0,
        "index_chain_issues": 0,
    }

    for paper_dir in papers:
        item = validate_ov_index_for_paper(paper_dir)
        details.append(item)
        state = str(item.get("status", "issue"))
        if state == "ok":
            summary["ok"] += 1
        else:
            summary["issue"] += 1
        summary["missing_files"] += len(item.get("missing_files", []))
        summary["placeholder_files"] += len(item.get("placeholder_files", []))
        summary["path_mismatch"] += len(item.get("path_mismatch", []))
        summary["index_chain_issues"] += len(item.get("index_chain_issues", []))

    return {
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "details": details,
    }


def _overview_word_count(text: str) -> int:
    return len((text or "").split())


def _score_length(word_count: int, min_words: int, max_words: int) -> tuple[int, str]:
    if min_words <= word_count <= max_words:
        return 100, "ok"
    if word_count < min_words:
        gap = min_words - word_count
        penalty = min(70, gap)
        return max(0, 100 - penalty), f"too_short:{word_count}<{min_words}"
    gap = word_count - max_words
    penalty = min(70, gap)
    return max(0, 100 - penalty), f"too_long:{word_count}>{max_words}"


def _score_paper_overview_structure(text: str) -> tuple[int, list[str]]:
    required = [
        "background",
        "method",
        "results",
        "practical implications",
    ]
    normalized = (text or "").lower()
    hit = [h for h in required if h in normalized]
    missing = [h for h in required if h not in normalized]
    score = int(round((len(hit) / len(required)) * 100)) if required else 100
    return score, missing


def _score_section_overview_signals(text: str) -> tuple[int, list[str]]:
    # E2 heuristic: check for claim/evidence/relevance style signals.
    signal_groups = {
        "claim": [
            "claim",
            "conclusion",
            "finding",
            "we show",
            "we demonstrate",
            "our findings",
            "结论",
            "观点",
            "本文提出",
            "本文表明",
            "研究发现",
        ],
        "evidence": [
            "evidence",
            "data",
            "experiment",
            "observed",
            "measurement",
            "measured",
            "test results",
            "figure",
            "table",
            "结果",
            "证据",
            "实验结果",
            "测试结果",
            "测量结果",
        ],
        "relevance": [
            "relevance",
            "impact",
            "implication",
            "practical application",
            "engineering application",
            "industrial application",
            "意义",
            "相关",
            "应用价值",
            "工程应用",
            "工业应用",
            "实用价值",
            "可用于",
        ],
    }
    normalized = (text or "").lower()
    hit: list[str] = []
    missing: list[str] = []
    for k, words in signal_groups.items():
        if any(w in normalized for w in words):
            hit.append(k)
        else:
            missing.append(k)
    score = int(round((len(hit) / len(signal_groups)) * 100)) if signal_groups else 100
    return score, missing


def _quality_grade(score: float) -> str:
    if score >= 85:
        return "pass"
    if score >= 70:
        return "warn"
    return "fail"


def validate_overview_quality_for_paper(paper_dir: Path) -> dict[str, Any]:
    """E2: validate paper/section overview quality with length and structure rules."""
    ov_index = paper_dir / OV_INDEX_DIRNAME
    paper_overview = ov_index / "paper.overview.md"

    items: list[dict[str, Any]] = []
    score_sum = 0.0

    if not paper_overview.exists():
        items.append(
            {
                "kind": "paper_overview",
                "path": str(paper_overview.relative_to(paper_dir)).replace("\\", "/"),
                "score": 0,
                "grade": "fail",
                "issues": ["missing_file"],
            }
        )
    else:
        text = paper_overview.read_text(encoding="utf-8", errors="replace")
        wc = _overview_word_count(text)
        len_score, len_issue = _score_length(wc, 180, 320)
        struct_score, missing_heads = _score_paper_overview_structure(text)
        score = round(len_score * 0.6 + struct_score * 0.4, 2)
        issues: list[str] = []
        if len_issue != "ok":
            issues.append(len_issue)
        if missing_heads:
            issues.append("missing_headings:" + ",".join(missing_heads))
        if _is_missing_generation_file(paper_overview):
            issues.append("placeholder_or_empty")
            score = 0
        items.append(
            {
                "kind": "paper_overview",
                "path": str(paper_overview.relative_to(paper_dir)).replace("\\", "/"),
                "word_count": wc,
                "length_score": len_score,
                "structure_score": struct_score,
                "score": score,
                "grade": _quality_grade(score),
                "issues": issues,
            }
        )
        score_sum += score

    sections_root = ov_index / "sections"
    if sections_root.exists():
        for section_dir in sorted(sections_root.iterdir()):
            if not section_dir.is_dir():
                continue
            section_overview = section_dir / "overview.md"
            rel_path = str(section_overview.relative_to(paper_dir)).replace("\\", "/")
            if not section_overview.exists():
                items.append(
                    {
                        "kind": "section_overview",
                        "section": section_dir.name,
                        "path": rel_path,
                        "score": 0,
                        "grade": "fail",
                        "issues": ["missing_file"],
                    }
                )
                continue
            text = section_overview.read_text(encoding="utf-8", errors="replace")
            wc = _overview_word_count(text)
            len_score, len_issue = _score_length(wc, 120, 220)
            signal_score, missing_signals = _score_section_overview_signals(text)
            score = round(len_score * 0.7 + signal_score * 0.3, 2)
            issues = []
            if len_issue != "ok":
                issues.append(len_issue)
            if missing_signals:
                issues.append("missing_signals:" + ",".join(missing_signals))
            if _is_missing_generation_file(section_overview):
                issues.append("placeholder_or_empty")
                score = 0
            items.append(
                {
                    "kind": "section_overview",
                    "section": section_dir.name,
                    "path": rel_path,
                    "word_count": wc,
                    "length_score": len_score,
                    "signal_score": signal_score,
                    "score": score,
                    "grade": _quality_grade(score),
                    "issues": issues,
                }
            )
            score_sum += score

    count = len(items)
    avg_score = round((score_sum / count), 2) if count else 0.0
    grade = _quality_grade(avg_score)
    fail_count = sum(1 for x in items if x.get("grade") == "fail")
    warn_count = sum(1 for x in items if x.get("grade") == "warn")
    pass_count = sum(1 for x in items if x.get("grade") == "pass")

    return {
        "paper_id": paper_dir.name,
        "grade": grade,
        "avg_score": avg_score,
        "items_count": count,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "items": items,
        "checked_at": datetime.now().isoformat(),
    }


def build_overview_quality_report(papers: list[Path]) -> dict[str, Any]:
    """E2: batch overview quality report with thresholds and summary."""
    details: list[dict[str, Any]] = []
    summary = {
        "papers": len(papers),
        "pass": 0,
        "warn": 0,
        "fail": 0,
        "avg_score": 0.0,
    }

    total_score = 0.0
    for paper_dir in papers:
        row = validate_overview_quality_for_paper(paper_dir)
        details.append(row)
        g = str(row.get("grade", "fail"))
        if g in summary:
            summary[g] += 1
        total_score += float(row.get("avg_score", 0.0))

    if papers:
        summary["avg_score"] = round(total_score / len(papers), 2)

    return {
        "generated_at": datetime.now().isoformat(),
        "thresholds": {
            "pass_min": 85,
            "warn_min": 70,
            "paper_overview_word_range": [180, 320],
            "section_overview_word_range": [120, 220],
        },
        "summary": summary,
        "details": details,
    }


def validate_semantic_conflict_for_paper(paper_dir: Path) -> dict[str, Any]:
    """E3: estimate semantic conflict risk using status + tag_conflicts + evidence links."""
    raw_conflict = 0.0
    process_penalty = 0.0
    triggers: list[str] = []

    status_payload = read_generation_status(paper_dir)
    status = str(status_payload.get("status", "missing")) if status_payload else "missing"
    if status != "fresh":
        triggers.append(f"generation_status:{status}")
        process_penalty += 10

    evidence_links = _safe_read_json(paper_dir / "evidence_links.json")
    if evidence_links is None:
        triggers.append("missing_evidence_links")
        process_penalty += 5

    tag_conflicts = _safe_read_json(paper_dir / "tag_conflicts.json")
    high = 0
    medium = 0
    low = 0
    if not isinstance(tag_conflicts, dict):
        triggers.append("missing_or_invalid_tag_conflicts")
        process_penalty += 8
    else:
        items = tag_conflicts.get("items")
        if not isinstance(items, list):
            triggers.append("tag_conflicts_items_missing")
            process_penalty += 8
        else:
            for row in items:
                if not isinstance(row, dict):
                    continue
                mc = row.get("macro_conflict") if isinstance(row.get("macro_conflict"), dict) else {}
                level = str(mc.get("conflict_level") or row.get("conflict_level") or "").lower()
                if level == "high":
                    high += 1
                elif level == "medium":
                    medium += 1
                elif level == "low":
                    low += 1
            if high > 0:
                triggers.append(f"high_tag_conflicts:{high}")
            if medium > 0:
                triggers.append(f"medium_tag_conflicts:{medium}")
            if low > 0:
                triggers.append(f"low_tag_conflicts:{low}")
            raw_conflict += high * 10 + medium * 2 + low * 0.5

    paper_targets_ok, section_targets_count = detect_generated_targets(paper_dir)
    if not paper_targets_ok:
        triggers.append("paper_overview_or_abstract_missing")
        process_penalty += 10
    if section_targets_count <= 0:
        triggers.append("section_targets_missing")
        process_penalty += 10

    section_count = max(1, section_targets_count)
    normalized_conflict = min(100.0, (raw_conflict / section_count) * 2.0)
    score = min(100.0, normalized_conflict + process_penalty)
    level = "low"
    if score >= 40:
        level = "high"
    elif score >= 20:
        level = "medium"

    return {
        "paper_id": paper_dir.name,
        "conflict_score": round(score, 2),
        "conflict_level": level,
        "status": status,
        "raw_conflict_score": round(raw_conflict, 2),
        "normalized_conflict_score": round(normalized_conflict, 2),
        "process_penalty_score": round(process_penalty, 2),
        "section_count": section_count,
        "tag_conflict_counts": {
            "high": high,
            "medium": medium,
            "low": low,
        },
        "trigger_conditions": triggers,
        "checked_at": datetime.now().isoformat(),
    }


def build_semantic_conflict_report(papers: list[Path]) -> dict[str, Any]:
    """E3: batch semantic conflict report with per-paper conflict_score."""
    details: list[dict[str, Any]] = []
    summary = {
        "papers": len(papers),
        "high": 0,
        "medium": 0,
        "low": 0,
        "avg_conflict_score": 0.0,
    }

    total = 0.0
    for p in papers:
        row = validate_semantic_conflict_for_paper(p)
        details.append(row)
        lv = str(row.get("conflict_level", "low"))
        if lv in summary:
            summary[lv] += 1
        total += float(row.get("conflict_score", 0))

    if papers:
        summary["avg_conflict_score"] = round(total / len(papers), 2)

    return {
        "generated_at": datetime.now().isoformat(),
        "thresholds": {
            "high_min": 40,
            "medium_min": 20,
            "low_max": 19,
            "semantic_weights": {
                "high": 10,
                "medium": 2,
                "low": 0.5,
            },
            "normalization": {
                "section_count_source": "detect_generated_targets.section_targets_count",
                "multiplier": 2.0,
            },
            "process_penalty": {
                "generation_status_not_fresh": 10,
                "missing_evidence_links": 5,
                "missing_or_invalid_tag_conflicts": 8,
                "tag_conflicts_items_missing": 8,
                "paper_overview_or_abstract_missing": 10,
                "section_targets_missing": 10,
            },
        },
        "summary": summary,
        "details": details,
    }


def build_fallback_review_report(papers: list[Path]) -> dict[str, Any]:
    """E4: build fallback strategy report with manual-review markers.

    This report combines A2/E1/E2/E3 checks and emits per-paper fallback actions,
    so operators can run a safe degrade path when quality gates are not met.
    """
    details: list[dict[str, Any]] = []
    summary = {
        "papers": len(papers),
        "ok": 0,
        "needs_fallback": 0,
        "manual_review": 0,
        "actions": {
            "none": 0,
            "generate_missing": 0,
            "refresh_stale": 0,
            "manual_review_only": 0,
        },
    }

    for p in papers:
        status_payload = evaluate_generation_status(p)
        e1 = validate_ov_index_for_paper(p)
        e2 = validate_overview_quality_for_paper(p)
        e3 = validate_semantic_conflict_for_paper(p)

        triggers: list[str] = []
        actions: list[str] = []

        gen_status = str(status_payload.get("status", "missing"))
        if gen_status == "missing":
            triggers.append("generation_missing")
            actions.append("generate_missing")
        elif gen_status == "stale":
            triggers.append("generation_stale")
            actions.append("refresh_stale")

        if int(e1.get("issue_count", 0)) > 0:
            triggers.append("ov_index_structure_issue")
            actions.append("manual_review_only")

        e2_status = str(e2.get("grade", "warn"))
        if e2_status in {"warn", "fail"}:
            triggers.append(f"overview_quality_{e2_status}")
            actions.append("manual_review_only")

        conflict_level = str(e3.get("conflict_level", "high"))
        if conflict_level in {"high", "medium"}:
            triggers.append(f"semantic_conflict_{conflict_level}")
            actions.append("manual_review_only")

        # Keep deterministic action order and de-duplicate.
        uniq_actions = [a for a in ["generate_missing", "refresh_stale", "manual_review_only"] if a in actions]
        final_action = "none" if not uniq_actions else "+".join(uniq_actions)
        needs_fallback = final_action != "none"
        manual_review = "manual_review_only" in uniq_actions

        row = {
            "paper_id": p.name,
            "needs_fallback": needs_fallback,
            "manual_review": manual_review,
            "fallback_action": final_action,
            "triggers": triggers,
            "generation_status": gen_status,
            "e1_status": str(e1.get("status", "issue")),
            "e1_issue_count": int(e1.get("issue_count", 0)),
            "e2_status": e2_status,
            "e2_score": round(float(e2.get("avg_score", 0.0)), 2),
            "e3_conflict_level": conflict_level,
            "e3_conflict_score": int(e3.get("conflict_score", 0)),
        }
        details.append(row)

        if needs_fallback:
            summary["needs_fallback"] += 1
        else:
            summary["ok"] += 1
        if manual_review:
            summary["manual_review"] += 1

        if final_action == "none":
            summary["actions"]["none"] += 1
        else:
            if "generate_missing" in uniq_actions:
                summary["actions"]["generate_missing"] += 1
            if "refresh_stale" in uniq_actions:
                summary["actions"]["refresh_stale"] += 1
            if "manual_review_only" in uniq_actions:
                summary["actions"]["manual_review_only"] += 1

    return {
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "details": details,
        "guidance": {
            "generate_missing": "Run --generate-missing then re-check status.",
            "refresh_stale": "Run --refresh-stale then re-check status.",
            "manual_review_only": "Keep evidence for human triage before import/reindex.",
        },
    }


def _ensure_openviking_path() -> None:
    """Ensure local OpenViking source path is available for imports."""
    p = str(OPENVIKING_SRC_PATH)
    if OPENVIKING_SRC_PATH.exists() and p not in sys.path:
        sys.path.insert(0, p)


def read_generation_status(paper_dir: Path) -> dict[str, Any]:
    p = paper_dir / OV_INDEX_DIRNAME / GEN_STATUS_FILENAME
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_generation_status(paper_dir: Path, payload: dict[str, Any]) -> Path:
    out_dir = paper_dir / OV_INDEX_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / GEN_STATUS_FILENAME
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def evaluate_generation_status(paper_dir: Path) -> dict[str, Any]:
    """Evaluate missing/stale/fresh state from checksum and generated targets."""
    source_checksum, source_items = compute_source_checksum(paper_dir)
    paper_targets_ok, section_targets_count = detect_generated_targets(paper_dir)
    prev = read_generation_status(paper_dir)

    has_targets = paper_targets_ok or section_targets_count > 0
    prev_checksum = str(prev.get("source_checksum", "")) if isinstance(prev, dict) else ""

    if not has_targets:
        status = "missing"
    elif prev_checksum and source_checksum and prev_checksum != source_checksum:
        status = "stale"
    else:
        status = "fresh"

    llm_cfg = {}
    try:
        llm_cfg = load_chat_llm_config()
    except Exception:
        llm_cfg = {}

    return {
        "status": status,
        "generated_at": prev.get("generated_at") if isinstance(prev, dict) else None,
        "source_checksum": source_checksum,
        "source_items": source_items,
        "based_on_preprocess_version": prev.get("based_on_preprocess_version") if isinstance(prev, dict) else None,
        "llm_model": llm_cfg.get("model"),
        "llm_provider": llm_cfg.get("provider"),
        "llm_base_url": llm_cfg.get("base_url"),
        "targets": {
            "paper_targets_ok": paper_targets_ok,
            "section_targets_count": section_targets_count,
        },
        "evaluated_at": datetime.now().isoformat(),
    }


def enforce_stale_gate_or_exit(papers: list[Path], *, allow_stale_import: bool) -> None:
    """A3 gate: block stale papers by default during overwrite/reindex imports."""
    stale_papers: list[str] = []
    missing_papers: list[str] = []

    for paper_dir in papers:
        status_payload = evaluate_generation_status(paper_dir)
        # Keep status file up-to-date for traceability and repeatability.
        write_generation_status(paper_dir, status_payload)
        status = str(status_payload.get("status", "missing"))
        if status == "stale":
            stale_papers.append(paper_dir.name)
        elif status == "missing":
            missing_papers.append(paper_dir.name)

    if missing_papers:
        print(
            f"[A3][WARN] {len(missing_papers)} paper(s) are missing generated summaries; "
            "import may proceed but quality can be degraded."
        )

    if stale_papers and not allow_stale_import:
        print(
            f"[A3][ERR] stale generation status detected for {len(stale_papers)} paper(s); "
            "import blocked by default."
        )
        for name in stale_papers[:10]:
            print(f"  - {name}")
        if len(stale_papers) > 10:
            print(f"  ... and {len(stale_papers) - 10} more")
        print("Hint: refresh stale summaries first, or pass --allow-stale-import to override.")
        sys.exit(EXIT_STALE_BLOCKED)

    if stale_papers:
        print(
            f"[A3][WARN] proceeding with --allow-stale-import; "
            f"{len(stale_papers)} stale paper(s) are being imported."
        )


def _read_text_limited(path: Path, limit: int = 12000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit]


def _is_missing_generation_file(path: Path) -> bool:
    if not path.exists():
        return True
    content = path.read_text(encoding="utf-8", errors="replace").strip()
    if not content:
        return True
    return "[TBD by C1 text LLM generation]" in content


def _call_text_llm(prompt: str, cfg: dict[str, Any]) -> str:
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("openai package is not installed") from exc

    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])
    completion = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {
                "role": "system",
                "content": "You are a scientific writing assistant. Output concise, factual markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        top_p=0.7,
        stream=False,
    )
    if not completion.choices:
        return ""
    return (completion.choices[0].message.content or "").strip()


def _paper_prompt(paper_dir: Path, kind: str) -> str:
    title = _read_metadata_title(paper_dir)
    full_clean = _read_text_limited(paper_dir / "full_clean.md")
    tree = _read_text_limited(paper_dir / "document_tree.json")
    if kind == "abstract":
        instr = (
            "Write a concise paper abstract in markdown (120-200 words). "
            "Include objective, method, key findings, and conclusion."
        )
    else:
        instr = (
            "Write a structured paper overview in markdown with sections: "
            "Background, Method, Results, Practical Implications (180-320 words)."
        )
    return (
        f"{instr}\n\n"
        f"Title: {title}\n\n"
        f"Document tree (json excerpt):\n{tree}\n\n"
        f"Full text excerpt:\n{full_clean}"
    )


def _section_prompt(paper_dir: Path, section_slug: str, kind: str) -> str:
    section_root = paper_dir / "sections_by_heading" / section_slug
    heading = _read_text_limited(section_root / "heading.json")
    paragraphs = _read_text_limited(section_root / "paragraphs.md")
    if kind == "abstract":
        instr = (
            "Write a concise section abstract in markdown (80-150 words). "
            "Focus on the core technical point and evidence."
        )
    else:
        instr = (
            "Write a section overview in markdown (120-220 words) using EXACTLY these headings: "
            "## Claim, ## Evidence, ## Relevance. "
            "Keep all statements grounded in the provided section text, and do not invent new facts. "
            "In each heading, provide 1-2 concise sentences anchored to the source content."
        )
    return (
        f"{instr}\n\n"
        f"Section slug: {section_slug}\n\n"
        f"Heading metadata:\n{heading}\n\n"
        f"Section paragraphs:\n{paragraphs}"
    )


def generate_missing_summaries(
    paper_dir: Path,
    *,
    max_files: int = 0,
) -> dict[str, Any]:
    """C1: generate missing abstract/overview files using text LLM."""
    cfg = load_chat_llm_config()
    errs = validate_chat_llm_config(cfg)
    if errs:
        raise RuntimeError("invalid chat LLM config: " + "; ".join(errs))

    ov_index = paper_dir / OV_INDEX_DIRNAME
    sections_root = ov_index / "sections"
    ov_index.mkdir(parents=True, exist_ok=True)
    sections_root.mkdir(parents=True, exist_ok=True)

    tasks: list[tuple[Path, str]] = []
    tasks.append((ov_index / "paper.abstract.md", _paper_prompt(paper_dir, "abstract")))
    tasks.append((ov_index / "paper.overview.md", _paper_prompt(paper_dir, "overview")))

    sbh_root = paper_dir / "sections_by_heading"
    if sbh_root.exists():
        for section_dir in sorted(sbh_root.iterdir()):
            if not section_dir.is_dir() or section_dir.name == "_debug":
                continue
            slug = section_dir.name
            tasks.append((sections_root / slug / "abstract.md", _section_prompt(paper_dir, slug, "abstract")))
            tasks.append((sections_root / slug / "overview.md", _section_prompt(paper_dir, slug, "overview")))

    generated = 0
    skipped = 0
    errors: list[str] = []

    for target, prompt in tasks:
        if not _is_missing_generation_file(target):
            skipped += 1
            continue
        if max_files > 0 and generated >= max_files:
            skipped += 1
            continue
        try:
            content = _call_text_llm(prompt, cfg)
            if not content:
                raise RuntimeError("empty completion")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content + "\n", encoding="utf-8")
            generated += 1
            print(f"  [C1][OK] {target}")
        except Exception as exc:
            err = f"{target}: {exc}"
            errors.append(err)
            print(f"  [C1][ERR] {err}")

    status_payload = evaluate_generation_status(paper_dir)
    status_payload["generated_at"] = datetime.now().isoformat()
    write_generation_status(paper_dir, status_payload)

    return {
        "paper_id": paper_dir.name,
        "generated": generated,
        "skipped": skipped,
        "errors": errors,
        "status": status_payload.get("status"),
    }


def _collect_generation_tasks(paper_dir: Path) -> list[tuple[Path, str]]:
    """Collect all generation targets and prompts for a paper."""
    ov_index = paper_dir / OV_INDEX_DIRNAME
    sections_root = ov_index / "sections"

    tasks: list[tuple[Path, str]] = []
    tasks.append((ov_index / "paper.abstract.md", _paper_prompt(paper_dir, "abstract")))
    tasks.append((ov_index / "paper.overview.md", _paper_prompt(paper_dir, "overview")))

    sbh_root = paper_dir / "sections_by_heading"
    if sbh_root.exists():
        for section_dir in sorted(sbh_root.iterdir()):
            if not section_dir.is_dir() or section_dir.name == "_debug":
                continue
            slug = section_dir.name
            tasks.append((sections_root / slug / "abstract.md", _section_prompt(paper_dir, slug, "abstract")))
            tasks.append((sections_root / slug / "overview.md", _section_prompt(paper_dir, slug, "overview")))

    return tasks


def generate_summaries(
    paper_dir: Path,
    *,
    mode: str,
    max_files: int = 0,
) -> dict[str, Any]:
    """Generate summaries in one of modes: missing | refresh_stale | regenerate_all."""
    if mode not in {"missing", "refresh_stale", "regenerate_all"}:
        raise RuntimeError(f"unsupported generate mode: {mode}")

    cfg = load_chat_llm_config()
    errs = validate_chat_llm_config(cfg)
    if errs:
        raise RuntimeError("invalid chat LLM config: " + "; ".join(errs))

    status_payload_before = evaluate_generation_status(paper_dir)
    status_before = str(status_payload_before.get("status", "missing"))

    # C2 only runs on stale papers by explicit command.
    if mode == "refresh_stale" and status_before != "stale":
        return {
            "paper_id": paper_dir.name,
            "generated": 0,
            "skipped": 0,
            "errors": [],
            "status": status_before,
            "note": "not_stale_skip",
        }

    ov_index = paper_dir / OV_INDEX_DIRNAME
    ov_index.mkdir(parents=True, exist_ok=True)
    (ov_index / "sections").mkdir(parents=True, exist_ok=True)

    tasks = _collect_generation_tasks(paper_dir)
    generated = 0
    skipped = 0
    errors: list[str] = []

    for target, prompt in tasks:
        should_generate = False
        if mode == "missing":
            should_generate = _is_missing_generation_file(target)
        elif mode == "refresh_stale":
            should_generate = True
        elif mode == "regenerate_all":
            should_generate = True

        if not should_generate:
            skipped += 1
            continue

        if max_files > 0 and generated >= max_files:
            skipped += 1
            continue

        try:
            content = _call_text_llm(prompt, cfg)
            if not content:
                raise RuntimeError("empty completion")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content + "\n", encoding="utf-8")
            generated += 1
            print(f"  [GEN][{mode}][OK] {target}")
        except Exception as exc:
            err = f"{target}: {exc}"
            errors.append(err)
            print(f"  [GEN][{mode}][ERR] {err}")

    status_payload_after = evaluate_generation_status(paper_dir)
    status_payload_after["generated_at"] = datetime.now().isoformat()
    write_generation_status(paper_dir, status_payload_after)

    return {
        "paper_id": paper_dir.name,
        "generated": generated,
        "skipped": skipped,
        "errors": errors,
        "status": status_payload_after.get("status"),
        "status_before": status_before,
    }


def refresh_stale_summaries(
    paper_dir: Path,
    *,
    max_files: int = 0,
) -> dict[str, Any]:
    """C2: refresh summaries only when generation status is stale."""
    return generate_summaries(paper_dir, mode="refresh_stale", max_files=max_files)


def regenerate_all_summaries(
    paper_dir: Path,
    *,
    max_files: int = 0,
) -> dict[str, Any]:
    """C3: force regenerate all summaries regardless of current status."""
    return generate_summaries(paper_dir, mode="regenerate_all", max_files=max_files)

# ---------------------------------------------------------------------------
# OpenViking main index policy (A1 baseline)
# ---------------------------------------------------------------------------
# The main vector index should only accept compact navigation/summary views.
# Full-text and structure/trace JSON files stay outside the main index and are
# used later for hydration, verification, or provenance lookup.
# Files entering the main index are identified by suffix (flat unique naming).
# Layer 1 (paper): paper.abstract.md / paper.overview.md
# Layer 2 (section): sections/{section_dir}/abstract.md / overview.md
# Layer 3 (paragraph): sections/{section_dir}/{paragraph_id}.md
MAIN_INDEX_SUFFIXES = (".abstract.md", ".overview.md", ".chunk.md", ".md")

# Section directory files that use plain names (no dot prefix)
SECTION_INDEX_NAMES = frozenset({"abstract.md", "overview.md"})

# Files explicitly excluded from the main index (structure/trace/metadata only).
EXCLUDE_FROM_INDEX = frozenset({
    "metadata.json",
    "full_clean.md",
    "document_tree.json",
    "original_structure_index.json",
    "paragraph_index.json",
    "evidence_links.json",
    "image_manifest.json",
    "table_manifest.json",
    "quality_report.json",
    "tag_conflicts.json",
})


def is_main_index_candidate(rel_path: str) -> bool:
    """Return True when rel_path is allowed into the OpenViking main index."""
    name = rel_path.replace("\\", "/").split("/")[-1]
    if name in EXCLUDE_FROM_INDEX:
        return False
    return name.endswith(MAIN_INDEX_SUFFIXES)

# ---------------------------------------------------------------------------
# Files to include in the export (root-level, non-dot)
# NOTE: metadata.json is intentionally excluded from the vector index;
#       it is read directly by search_hydrate.py for hydration only.
# ---------------------------------------------------------------------------
ROOT_INCLUDE = [
    "full_clean.md",
    "structured.json",
    "evidence_links.json",
]

# Sub-dir glob patterns to include
# NOTE: tables/TAB*.md removed — content is included in table_combined_TABxxx.md (step 6)
SUBDIR_GLOBS = [
    "figures/*.jpg",
    "figures/*.png",
    "figures/*.jpeg",
]

# ---------------------------------------------------------------------------
# Stub / low-quality file filter
# ---------------------------------------------------------------------------
_MIN_INDEX_WORDS = 50    # files below this word count are skipped

# Patterns that identify stub/placeholder content (whole-content match)
_STUB_RES = [
    re.compile(r"^Directory overview\s*$", re.I),
    re.compile(r"^#[^\n]*\n\s*(?:Directory overview)?\s*$", re.I | re.S),
    re.compile(r"^#{1,6}\s*\S[^\n]*\n?\s*$", re.S),  # heading-only (no body)
]

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _expand_env(value: str) -> str:
    """Expand ${VAR} / ${VAR:-default} syntax in strings."""

    def _sub(match: re.Match[str]) -> str:
        expr = match.group(1)
        if ":-" in expr:
            var, default = expr.split(":-", 1)
            return os.environ.get(var, default)
        return os.environ.get(expr, "")

    return _ENV_PATTERN.sub(_sub, value)


def _expand_value(value: Any) -> Any:
    if isinstance(value, str):
        return _expand_env(value)
    if isinstance(value, list):
        return [_expand_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _expand_value(v) for k, v in value.items()}
    return value


def load_chat_llm_config() -> dict[str, Any]:
    """Load text LLM config from configs/agent_models.toml [chat] section."""
    if not AGENT_MODELS_PATH.exists():
        raise RuntimeError(f"Config not found: {AGENT_MODELS_PATH}")

    with AGENT_MODELS_PATH.open("rb") as fh:
        raw = tomllib.load(fh)

    defaults = raw.get("defaults", {})
    chat = raw.get("chat", {})
    if not isinstance(defaults, dict):
        defaults = {}
    if not isinstance(chat, dict):
        raise RuntimeError("[chat] section missing in configs/agent_models.toml")

    defaults = _expand_value(defaults)
    chat = _expand_value(chat)

    return {
        "provider": str(chat.get("provider", defaults.get("provider", "openai"))),
        "model": str(chat.get("model", defaults.get("model", ""))),
        "base_url": str(chat.get("base_url", defaults.get("base_url", ""))),
        "api_key": str(chat.get("api_key", defaults.get("api_key", ""))),
        "enabled": bool(chat.get("enabled", True)),
    }


def validate_chat_llm_config(cfg: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if not cfg.get("enabled", True):
        errs.append("[chat].enabled=false")
    if not cfg.get("provider"):
        errs.append("provider is empty")
    if not cfg.get("model"):
        errs.append("model is empty")
    if not cfg.get("base_url"):
        errs.append("base_url is empty")
    if not cfg.get("api_key"):
        errs.append("api_key is empty after env expansion")
    return errs


def ensure_text_llm_ready_or_exit() -> None:
    """A0.3 gate: fail fast when text LLM is not configured correctly."""
    try:
        cfg = load_chat_llm_config()
    except Exception as exc:
        print(f"[A0][ERR] cannot read chat LLM config: {exc}")
        print("Hint: check configs/agent_models.toml and [chat] section")
        sys.exit(EXIT_LLM_CFG_READ_ERR)

    errs = validate_chat_llm_config(cfg)
    if errs:
        print("[A0][ERR] chat LLM config invalid:")
        for err in errs:
            print(f"  - {err}")
        print("Hint: set [chat] provider/model/base_url/api_key correctly")
        sys.exit(EXIT_LLM_CFG_INVALID)

    print("[A0][OK] text LLM gate passed (source: configs/agent_models.toml [chat])")


def _is_stub(content: str) -> tuple[bool, str]:
    """Return (is_stub, reason). Used to exclude low-quality files before import."""
    s = content.strip()
    if not s:
        return True, "empty"
    for pat in _STUB_RES:
        if pat.match(s):
            return True, "stub_pattern"
    wc = len(s.split())
    if wc < _MIN_INDEX_WORDS:
        return True, f"short({wc}w<{_MIN_INDEX_WORDS})"
    return False, ""

# memory_cards: recursively include these filenames (after rename)
# NOTE: per-figure and per-table subdirs (memory_cards/figures/FIG*/,
# memory_cards/tables/TAB*/) are SKIPPED in step 4 and handled in
# steps 5 & 6 which generate unique-named files (figure_combined_FIG001.md etc.)
# to avoid all figures collapsing to the same path in the viking filesystem.
MC_INCLUDE_NAMES = {
    "abstract.md", "overview.md",   # for methods/results/other card dirs
    # figure.card.md, caption.md, image_ref.md, table.card.md are REMOVED:
    # they are all covered by figure_combined_FIGxxx.md / table_combined_TABxxx.md
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_import_log() -> dict:
    if IMPORT_LOG.exists():
        return json.loads(IMPORT_LOG.read_text(encoding="utf-8"))
    return {}


def save_import_log(log: dict) -> None:
    IMPORT_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def load_embedding_meta() -> dict:
    if EMBEDDING_META.exists():
        return json.loads(EMBEDDING_META.read_text(encoding="utf-8"))
    return {}


def save_embedding_meta(meta: dict) -> None:
    EMBEDDING_META.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def read_ov_embedding_config() -> dict:
    """Read embedding config from ov.conf. Returns provider/model/dim dict."""
    if not OV_CONF_PATH.exists():
        return {}
    try:
        conf = json.loads(OV_CONF_PATH.read_text(encoding="utf-8"))
        dense = conf.get("embedding", {}).get("dense", {})
        return {
            "embedding_provider": dense.get("provider", "unknown"),
            "embedding_model": dense.get("model", "unknown"),
            "embedding_dim": dense.get("dimension", 0),
        }
    except Exception:
        return {}


def find_clean_papers() -> list[Path]:
    """Return importable paper directories.

    Prefer the ov_index view layer (paper.abstract.md + paper.overview.md), and
    keep legacy .abstract/.overview compatibility for older datasets.
    """
    papers = []
    for d in sorted(CLEAN_ROOT.iterdir()):
        if not d.is_dir() or not (d / "metadata.json").exists():
            continue

        has_ov_index_targets = (
            (d / OV_INDEX_DIRNAME / "paper.abstract.md").exists()
            and (d / OV_INDEX_DIRNAME / "paper.overview.md").exists()
        )
        has_legacy_targets = (d / ".abstract.md").exists() and (d / ".overview.md").exists()
        if has_ov_index_targets or has_legacy_targets:
            papers.append(d)
    return papers


def find_status_target_papers() -> list[Path]:
    """Return paper directories for A2 status checks.

    A2 should work even before summary files are generated, so we only require
    metadata.json to identify a paper root.
    """
    papers = []
    for d in sorted(CLEAN_ROOT.iterdir()):
        if d.is_dir() and (d / "metadata.json").exists():
            papers.append(d)
    return papers


def normalize_paper_id_arg(paper_id_arg: str | None) -> str | None:
    if not paper_id_arg:
        return None
    text = paper_id_arg.strip().rstrip("\\/")
    if not text:
        return None
    return Path(text).name


def _read_metadata_title(paper_dir: Path) -> str:
    meta_path = paper_dir / "metadata.json"
    if not meta_path.exists():
        return paper_dir.name
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        title = data.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
    except Exception:
        pass
    return paper_dir.name


def build_ov_index_skeleton(paper_dir: Path, *, overwrite: bool = False) -> dict[str, Any]:
    """B1: build ov_index skeleton without calling any LLM."""
    ov_index = paper_dir / OV_INDEX_DIRNAME
    sections_root = ov_index / "sections"
    ov_index.mkdir(parents=True, exist_ok=True)
    sections_root.mkdir(parents=True, exist_ok=True)

    title = _read_metadata_title(paper_dir)
    created_files = 0
    skipped_files = 0

    def _write_if_needed(path: Path, content: str) -> None:
        nonlocal created_files, skipped_files
        if path.exists() and not overwrite:
            skipped_files += 1
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created_files += 1

    _write_if_needed(
        ov_index / "paper.abstract.md",
        f"# Paper Abstract\n\nTitle: {title}\n\n[TBD by C1 text LLM generation]\n",
    )
    _write_if_needed(
        ov_index / "paper.overview.md",
        f"# Paper Overview\n\nTitle: {title}\n\n[TBD by C1 text LLM generation]\n",
    )

    section_count = 0
    sbh_root = paper_dir / "sections_by_heading"
    if sbh_root.exists():
        for section_dir in sorted(sbh_root.iterdir()):
            if not section_dir.is_dir():
                continue
            if section_dir.name == "_debug":
                continue
            target_dir = sections_root / section_dir.name
            _write_if_needed(
                target_dir / "abstract.md",
                f"# Section Abstract\n\nSection: {section_dir.name}\n\n[TBD by C1 text LLM generation]\n",
            )
            _write_if_needed(
                target_dir / "overview.md",
                f"# Section Overview\n\nSection: {section_dir.name}\n\n[TBD by C1 text LLM generation]\n",
            )
            section_count += 1

    return {
        "paper_id": paper_dir.name,
        "ov_index": str(ov_index),
        "sections": section_count,
        "created_files": created_files,
        "skipped_files": skipped_files,
    }


def _copy_dotfile_renamed(src: Path, dst: Path) -> None:
    """Copy src to dst, creating parent directories."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_export_dir(paper_dir: Path, tmp_root: Path) -> Path:
    """
    Copy paper contents to a temp directory, renaming dotfiles.

    .abstract.md  → abstract.md
    .overview.md  → overview.md
    """
    export_dir = tmp_root / paper_dir.name
    export_dir.mkdir(parents=True, exist_ok=True)

    # 1. Root .abstract.md / .overview.md
    for dot_name, plain_name in [(".abstract.md", "abstract.md"), (".overview.md", "overview.md")]:
        src = paper_dir / dot_name
        if src.exists():
            _copy_dotfile_renamed(src, export_dir / plain_name)

    # 2. Root files
    for fname in ROOT_INCLUDE:
        src = paper_dir / fname
        if src.exists():
            _copy_dotfile_renamed(src, export_dir / fname)

    # 3. Sub-dir globs
    for pattern in SUBDIR_GLOBS:
        for src in paper_dir.glob(pattern):
            rel = src.relative_to(paper_dir)
            _copy_dotfile_renamed(src, export_dir / rel)

    # 4. memory_cards — recursive, rename dotfiles
    # SKIP per-figure and per-table sub-dirs (handled by steps 5 & 6)
    mc_root = paper_dir / "memory_cards"
    if mc_root.exists():
        for src in mc_root.rglob("*"):
            if not src.is_file():
                continue
            # Skip files inside per-figure / per-table leaf dirs
            rel_to_mc = src.relative_to(mc_root)
            if rel_to_mc.parts and rel_to_mc.parts[0] in ("figures", "tables"):
                continue
            name = src.name
            # Rename dotfiles
            if name.startswith("."):
                plain = name.lstrip(".")
            else:
                plain = name
            if plain not in MC_INCLUDE_NAMES:
                continue
            # Generate unique flat name to prevent viking hoisting collision:
            # conditions/CONDITION001/overview.md → CONDITION001_overview.md
            # methods/overview.md → methods_overview.md
            parts_mc = rel_to_mc.parts  # e.g. ("conditions", "CONDITION001", ".overview.md")
            if len(parts_mc) >= 3:
                # card_type/CARD_ID/filename → CARD_ID_filename
                fname_unique = f"{parts_mc[1]}_{plain}"
            elif len(parts_mc) >= 2:
                # card_type/filename → card_type_filename
                fname_unique = f"{parts_mc[0]}_{plain}"
            else:
                fname_unique = plain
            # Place at export root with unique name (avoids subdirectory hoisting confusion)
            _copy_dotfile_renamed(src, export_dir / fname_unique)

    # 5. Create figure_combined_{fig_id}.md per figure (unique name avoids viking path collision)
    # Files placed inside export_dir/figures/ (alongside images) so OpenViking keeps them
    # grouped under the figures/ directory:
    #   figures/figure_combined_FIG001/figure_combined_FIG001.md
    #   figures/figure_combined_FIG002/figure_combined_FIG002.md  ... etc.
    figs_src = paper_dir / "memory_cards" / "figures"
    if figs_src.exists():
        for fig_dir in sorted(figs_src.iterdir()):
            if not fig_dir.is_dir():
                continue
            fig_id = fig_dir.name          # e.g. FIG001
            parts: list[str] = []
            abstract_src = fig_dir / ".abstract.md"
            if abstract_src.exists():
                parts.append(abstract_src.read_text(encoding="utf-8", errors="replace").strip())
            card_src = fig_dir / "figure.card.md"
            if card_src.exists():
                parts.append(card_src.read_text(encoding="utf-8", errors="replace").strip())
            cap_src = fig_dir / "caption.md"
            if cap_src.exists():
                parts.append(cap_src.read_text(encoding="utf-8", errors="replace").strip())
            if parts:
                combined = "\n\n---\n\n".join(parts)
                fname = f"figure_combined_{fig_id}.md"
                # Place inside figures/ directory (with images) for grouped viking layout
                dst = export_dir / "figures" / fname
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(combined, encoding="utf-8")

    # 6. Create table_combined_{tab_id}.md per table (unique name avoids viking path collision)
    # Files placed inside export_dir/tables/ for grouped viking layout.
    # NOTE: raw tables/TABxxx.md is included in the combined content — no need to export separately.
    tabs_src = paper_dir / "memory_cards" / "tables"
    if tabs_src.exists():
        for tab_dir in sorted(tabs_src.iterdir()):
            if not tab_dir.is_dir():
                continue
            tab_id = tab_dir.name          # e.g. TAB001
            parts: list[str] = []
            abstract_src = tab_dir / ".abstract.md"
            if abstract_src.exists():
                parts.append(abstract_src.read_text(encoding="utf-8", errors="replace").strip())
            card_src = tab_dir / "table.card.md"
            if card_src.exists():
                parts.append(card_src.read_text(encoding="utf-8", errors="replace").strip())
            # Include actual table markdown data (tables/TABxxx.md)
            tab_data_src = paper_dir / "tables" / f"{tab_id}.md"
            if tab_data_src.exists():
                parts.append(tab_data_src.read_text(encoding="utf-8", errors="replace").strip())
            if parts:
                combined = "\n\n---\n\n".join(parts)
                fname = f"table_combined_{tab_id}.md"
                dst = export_dir / "tables" / fname
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(combined, encoding="utf-8")

    # 7. Stub filter — remove low-quality .md files before import so they do NOT
    #    enter the vector index.  OpenViking-generated .abstract.md/.overview.md
    #    stubs are handled separately (they start with '.' and are already skipped
    #    by OpenViking's own scanner).  This step targets our exported .md files.
    stats = {"skipped_empty": 0, "skipped_stub": 0, "indexed": 0}
    for md_file in list(export_dir.rglob("*.md")):
        try:
            txt = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        stub, reason = _is_stub(txt)
        if stub:
            md_file.unlink(missing_ok=True)
            if "empty" in reason:
                stats["skipped_empty"] += 1
            else:
                stats["skipped_stub"] += 1
        else:
            stats["indexed"] += 1
    # Remove empty directories left after stub removal
    for d in sorted(export_dir.rglob("*"), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()   # only succeeds if directory is empty
            except OSError:
                pass

    return export_dir, stats


def copy_paragraph_files(paper_dir: Path) -> int:
    """Copy paragraph .md files into ov_index/sections for direct indexing.

    Reads paragraph_index.json, copies each paragraph's .md file from
    sections_by_heading/{dir}/paragraphs/ to ov_index/sections/{dir}/,
    renaming to {paragraph_id}.md (e.g. S01-P001.md).

    No chunk splitting — the full paragraph .md goes into the main index.
    Returns the number of paragraph files copied.
    """
    para_index = paper_dir / "paragraph_index.json"
    if not para_index.is_file():
        return 0

    with open(para_index, "r", encoding="utf-8") as fh:
        paragraphs = json.load(fh)

    sections_root = paper_dir / OV_INDEX_DIRNAME / "sections"
    copied = 0

    # Group paragraphs by section_dir (derived from content_path)
    section_map: dict[str, list[dict]] = {}
    for entry in paragraphs:
        content_rel = entry.get("content_path", "")
        parts = content_rel.replace(chr(92), chr(47)).split(chr(47))
        section_dir = parts[1] if len(parts) >= 2 else ""
        if not section_dir:
            continue
        section_map.setdefault(section_dir, []).append(entry)

    for section_dir, entries in section_map.items():
        dest_dir = sections_root / section_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Clean old chunk files from previous runs
        for old in sorted(dest_dir.glob("*.chunk.md")):
            try:
                old.unlink()
            except OSError:
                pass

        for entry in entries:
            content_rel = entry.get("content_path", "")
            paragraph_id = entry.get("paragraph_id", "")
            if not paragraph_id:
                continue

            src = paper_dir / content_rel
            if not src.is_file():
                continue

            fname = f"{paragraph_id}.md"
            shutil.copy2(src, dest_dir / fname)
            copied += 1

    return copied



def build_main_index_export_dir(paper_dir: Path, tmp_root: Path) -> tuple[Path, dict[str, int]]:
    """D2: build export directory with whitelist-only main index files from ov_index."""
    export_dir = tmp_root / paper_dir.name
    export_dir.mkdir(parents=True, exist_ok=True)

    ov_index = paper_dir / OV_INDEX_DIRNAME
    stats = {
        "included": 0,
        "skipped_non_whitelist": 0,
        "missing_required": 0,
    }

    if not ov_index.exists():
        return export_dir, stats

    # Paper-level .abstract.md / .overview.md are written directly to the
    # OpenViking paper root by populate_directory_summaries() after import.
    # We no longer export them as separate files — doing so creates
    # redundant document nodes (paperabstract/, paperoverview/).

    sections_root = ov_index / "sections"
    if sections_root.exists():
        for section_dir in sorted(sections_root.iterdir()):
            if not section_dir.is_dir():
                continue
            section_id = section_dir.name
            dest_dir = export_dir / "sections" / section_id
            for src in sorted(section_dir.glob("*")):
                if not src.is_file():
                    continue
                name = src.name
                # Only export paragraph files (S01-P001.md etc.).
                # Section abstract.md / overview.md are written directly
                # to OpenViking by populate_directory_summaries().
                if name in SECTION_INDEX_NAMES:
                    continue
                if not name.endswith(MAIN_INDEX_SUFFIXES):
                    continue
                _copy_dotfile_renamed(src, dest_dir / name)
                stats["included"] += 1

    return export_dir, stats


def populate_directory_summaries(client, paper_dir: Path, paper_id: str) -> dict[str, int]:
    """H8: overwrite auto-generated .abstract.md/.overview.md with pre-processed content.

    OpenViking's SemanticProcessor generates blank placeholder summaries
    ("Directory overview", 18 bytes) at every directory level when VLM is
    not configured.  This function replaces them with the content already
    prepared inside ov_index/.

    Returns {"written": N, "skipped": N}.
    """
    ov_index = paper_dir / OV_INDEX_DIRNAME
    base_uri = f"viking://resources/literature/{paper_id}"
    written = 0
    skipped = 0
    dotfiles = (".abstract.md", ".overview.md")

    # --- Paper level ---
    for dotfile in dotfiles:
        src = ov_index / f"paper{dotfile}"
        if src.is_file():
            client.write_file(f"{base_uri}/{dotfile}", src.read_text(encoding="utf-8"))
            written += 1
        else:
            skipped += 1

    # --- Section level ---
    sections_root = ov_index / "sections"
    if sections_root.is_dir():
        for section_dir in sorted(sections_root.iterdir()):
            if not section_dir.is_dir():
                continue
            section_id = section_dir.name
            section_uri = f"{base_uri}/sections/{section_id}"
            for dotfile in dotfiles:
                plain = dotfile.lstrip(".")
                src = section_dir / plain
                if src.is_file():
                    client.write_file(f"{section_uri}/{dotfile}", src.read_text(encoding="utf-8"))
                    written += 1
                else:
                    skipped += 1

    return {"written": written, "skipped": skipped}


def import_paper(paper_dir: Path, client, dry_run: bool = False) -> dict:
    """
    Import one paper to OpenViking.

    Returns a result dict with keys: paper_id, status, uri, error, timestamp.
    """
    paper_id = paper_dir.name
    target = f"literature/{paper_id}"
    result = {
        "paper_id": paper_id,
        "target": target,
        "timestamp": datetime.now().isoformat(),
        "status": "unknown",
        "uri": None,
        "error": None,
    }

    # Copy paragraph .md files for direct indexing (no chunk splitting)
    para_count = copy_paragraph_files(paper_dir)
    if para_count:
        print(f"  paragraph files: {para_count} copied")

    if dry_run:
        with tempfile.TemporaryDirectory(prefix="ov_export_") as tmp_root:
            export_dir, stats = build_main_index_export_dir(paper_dir, Path(tmp_root))
            file_count = sum(1 for f in export_dir.rglob("*") if f.is_file())
            forbidden = []
            for bad in EXCLUDE_FROM_INDEX:
                if (export_dir / bad).exists():
                    forbidden.append(bad)
            result["status"] = "dry_run"
            result["stats"] = stats
            print(f"  [dry-run] would import {paper_id!r} → {target!r}")
            print(
                f"  [dry-run] export files={file_count} included={stats['included']} "
                f"skipped_non_whitelist={stats['skipped_non_whitelist']} "
                f"missing_required={stats['missing_required']}"
            )
            if forbidden:
                print(f"  [dry-run][ERR] found blacklisted files in export: {forbidden}")
                result["status"] = "error"
                result["error"] = "blacklisted file leaked into export"
        return result

    try:
        with tempfile.TemporaryDirectory(prefix="ov_export_") as tmp_root:
            export_dir, stats = build_main_index_export_dir(paper_dir, Path(tmp_root))
            file_count = sum(1 for f in export_dir.rglob("*") if f.is_file())
            print(
                f"  exporting {paper_id!r}: {file_count} files "
                f"(included={stats['included']} "
                f"skipped_non_whitelist={stats['skipped_non_whitelist']} "
                f"missing_required={stats['missing_required']}) → {export_dir}"
            )

            res = client.add_resource(path=str(export_dir), target=target, wait=True)
            uri = getattr(res, "uri", None) or (res.get("uri") if isinstance(res, dict) else None)
            result["status"] = "ok"
            result["uri"] = str(uri) if uri else f"viking://resources/{target}/"
            result["stats"] = stats
            print(f"  [OK] imported -> {result['uri']}")

            pop_result = populate_directory_summaries(client, paper_dir, paper_id)
            result["populate"] = pop_result
            if pop_result["written"]:
                print(f"  populate summaries: {pop_result['written']} written, {pop_result['skipped']} skipped")

    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        print(f"  [ERR] {paper_id}: {exc}")

    return result


def import_paper_with_backend(
    paper_dir: Path,
    client,
    *,
    backend: str,
    dry_run: bool = False,
    ovpack_force: bool = False,
    ovpack_vectorize: bool = True,
) -> dict:
    """D4: import one paper via selected backend (resource | ovpack)."""
    if backend == "resource":
        return import_paper(paper_dir, client, dry_run=dry_run)

    if backend != "ovpack":
        raise RuntimeError(f"unsupported import backend: {backend}")

    # Copy paragraph .md files for direct indexing (no chunk splitting)
    para_count = copy_paragraph_files(paper_dir)
    if para_count:
        print(f"  paragraph files: {para_count} copied")

    paper_id = paper_dir.name
    target = f"literature/{paper_id}"
    result = {
        "paper_id": paper_id,
        "target": target,
        "timestamp": datetime.now().isoformat(),
        "status": "unknown",
        "uri": None,
        "error": None,
    }

    if dry_run:
        with tempfile.TemporaryDirectory(prefix="ov_export_") as tmp_root:
            export_dir, stats = build_main_index_export_dir(paper_dir, Path(tmp_root))
            file_count = sum(1 for f in export_dir.rglob("*") if f.is_file())
            result["status"] = "dry_run"
            result["stats"] = stats
            print(f"  [dry-run][ovpack] would import {paper_id!r} → {target!r}")
            print(
                f"  [dry-run][ovpack] export files={file_count} included={stats['included']} "
                f"skipped_non_whitelist={stats['skipped_non_whitelist']} "
                f"missing_required={stats['missing_required']}"
            )
        return result

    try:
        with tempfile.TemporaryDirectory(prefix="ov_export_") as tmp_root:
            export_dir, stats = build_main_index_export_dir(paper_dir, Path(tmp_root))
            file_count = sum(1 for f in export_dir.rglob("*") if f.is_file())
            print(
                f"  [ovpack] staging {paper_id!r}: {file_count} files "
                f"(included={stats['included']} "
                f"skipped_non_whitelist={stats['skipped_non_whitelist']} "
                f"missing_required={stats['missing_required']}) → {export_dir}"
            )

            staging_target = f"_ovpack_staging/{paper_id}"
            stage_res = client.add_resource(path=str(export_dir), target=staging_target, wait=True)
            staging_uri = getattr(stage_res, "uri", None) or (
                stage_res.get("uri") if isinstance(stage_res, dict) else None
            )
            if not staging_uri:
                staging_uri = f"viking://resources/{staging_target}/"
            staging_uri = str(staging_uri)

            ovpack_path = Path(tmp_root) / f"{paper_id}.ovpack"
            exported_path = client.export_ovpack(staging_uri.rstrip("/"), str(ovpack_path))
            exported_path = str(exported_path or ovpack_path)

            # Remove temporary staging resource before final import.
            try:
                client.rm(staging_uri.rstrip("/"), recursive=True)
            except Exception as exc:
                print(f"  [ovpack][WARN] cleanup staging resource failed: {exc}")

            parent_uri = "viking://resources/literature/"
            imported_uri = client.import_ovpack(
                exported_path,
                parent_uri,
                force=ovpack_force,
                vectorize=ovpack_vectorize,
            )

            result["status"] = "ok"
            result["uri"] = str(imported_uri) if imported_uri else f"viking://resources/{target}/"
            result["stats"] = stats
            print(f"  [OK][ovpack] imported -> {result['uri']}")

            pop_result = populate_directory_summaries(client, paper_dir, paper_id)
            result["populate"] = pop_result
            if pop_result["written"]:
                print(f"  populate summaries: {pop_result['written']} written, {pop_result['skipped']} skipped")

    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        print(f"  [ERR][ovpack] {paper_id}: {exc}")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Import LiteratureClean papers to OpenViking")
    parser.add_argument("--paper-id", metavar="ID", help="Import only this paper_id")
    parser.add_argument("--list", action="store_true", help="List importable papers and exit")
    parser.add_argument("--dry-run", action="store_true", help="Preview without actually importing")
    parser.add_argument("--overwrite", action="store_true", help="Re-import already-imported papers")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Wipe vector index (data/openviking/) and re-import all papers with current ov.conf embedding",
    )
    parser.add_argument(
        "--require-text-llm",
        action="store_true",
        help="A0 gate: fail-fast if text LLM config in configs/agent_models.toml [chat] is invalid",
    )
    parser.add_argument(
        "--check-generation-status",
        action="store_true",
        help="A2: evaluate generation status (missing/stale/fresh) for papers",
    )
    parser.add_argument(
        "--write-generation-status",
        action="store_true",
        help="A2: write evaluated status to ov_index/generation_status.json",
    )
    parser.add_argument(
        "--allow-stale-import",
        action="store_true",
        help="A3 override: allow import even when generation status is stale",
    )
    parser.add_argument(
        "--build-ov-index-skeleton",
        action="store_true",
        help="B1: create ov_index skeleton files (paper/section abstract+overview placeholders)",
    )
    parser.add_argument(
        "--overwrite-skeleton",
        action="store_true",
        help="B1: overwrite existing skeleton files when building ov_index",
    )
    parser.add_argument(
        "--generate-missing",
        action="store_true",
        help="C1: generate missing abstract/overview files using text LLM",
    )
    parser.add_argument(
        "--refresh-stale",
        action="store_true",
        help="C2: refresh stale abstract/overview files (explicit trigger)",
    )
    parser.add_argument(
        "--regenerate-all",
        action="store_true",
        help="C3: force regenerate all abstract/overview files (explicit trigger)",
    )
    parser.add_argument(
        "--max-generate-files",
        type=int,
        default=0,
        help="C1/C2/C3: max files to generate per paper (0 means no limit)",
    )
    parser.add_argument(
        "--validate-ov-index",
        action="store_true",
        help="E1: validate ov_index structure and generate validation_report.json",
    )
    parser.add_argument(
        "--validate-overview-quality",
        action="store_true",
        help="E2: validate overview quality and generate overview_quality_report.json",
    )
    parser.add_argument(
        "--validate-semantic-conflicts",
        action="store_true",
        help="E3: validate semantic conflicts and generate semantic_conflict_report.json",
    )
    parser.add_argument(
        "--build-fallback-report",
        action="store_true",
        help="E4: build fallback_review_report.json with degrade actions and manual-review markers",
    )
    parser.add_argument(
        "--import-backend",
        choices=["resource", "ovpack"],
        default="resource",
        help="D4: choose import backend (resource=add_resource, ovpack=export/import ovpack)",
    )
    parser.add_argument(
        "--ovpack-force",
        action="store_true",
        help="D4 ovpack: force overwrite when importing ovpack",
    )
    parser.add_argument(
        "--ovpack-no-vectorize",
        action="store_true",
        help="D4 ovpack: disable vectorize during ovpack import",
    )
    args = parser.parse_args()
    if args.reindex:
        args.overwrite = True  # reindex implies overwrite

    action_flags = [
        args.generate_missing,
        args.refresh_stale,
        args.regenerate_all,
    ]
    if sum(1 for f in action_flags if f) > 1:
        print("ERROR: --generate-missing/--refresh-stale/--regenerate-all are mutually exclusive")
        sys.exit(2)

    if args.require_text_llm:
        ensure_text_llm_ready_or_exit()

    if args.write_generation_status and not args.check_generation_status:
        print("ERROR: --write-generation-status requires --check-generation-status")
        sys.exit(2)

    paper_id_filter = normalize_paper_id_arg(args.paper_id)

    papers = (
        find_status_target_papers()
        if (
            args.check_generation_status
            or args.validate_ov_index
            or args.validate_overview_quality
            or args.validate_semantic_conflicts
            or args.build_fallback_report
            or args.build_ov_index_skeleton
            or args.generate_missing
            or args.refresh_stale
            or args.regenerate_all
        )
        else find_clean_papers()
    )
    if not papers:
        print("No cleaned papers found in", CLEAN_ROOT)
        sys.exit(0)

    if args.build_ov_index_skeleton:
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        total_created = 0
        total_skipped = 0
        for paper_dir in papers:
            result = build_ov_index_skeleton(paper_dir, overwrite=args.overwrite_skeleton)
            total_created += int(result["created_files"])
            total_skipped += int(result["skipped_files"])
            print(
                f"[{result['paper_id']}] sections={result['sections']} "
                f"created={result['created_files']} skipped={result['skipped_files']} "
                f"ov_index={result['ov_index']}"
            )

        print(
            f"\nB1 summary: papers={len(papers)} created_files={total_created} skipped_files={total_skipped}"
        )
        return

    if args.generate_missing:
        ensure_text_llm_ready_or_exit()
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        total_generated = 0
        total_skipped = 0
        total_errors = 0
        for paper_dir in papers:
            print(f"[C1][{paper_dir.name}] generating missing summaries...")
            result = generate_missing_summaries(paper_dir, max_files=max(0, int(args.max_generate_files)))
            total_generated += int(result["generated"])
            total_skipped += int(result["skipped"])
            total_errors += len(result["errors"])
            print(
                f"  [C1][summary] generated={result['generated']} skipped={result['skipped']} "
                f"errors={len(result['errors'])} status={result['status']}"
            )

        print(
            f"\nC1 summary: papers={len(papers)} generated={total_generated} "
            f"skipped={total_skipped} errors={total_errors}"
        )
        if total_errors:
            sys.exit(1)
        return

    if args.refresh_stale:
        ensure_text_llm_ready_or_exit()
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        total_generated = 0
        total_skipped = 0
        total_errors = 0
        stale_skipped = 0
        for paper_dir in papers:
            print(f"[C2][{paper_dir.name}] refreshing stale summaries...")
            result = refresh_stale_summaries(paper_dir, max_files=max(0, int(args.max_generate_files)))
            total_generated += int(result["generated"])
            total_skipped += int(result["skipped"])
            total_errors += len(result["errors"])
            if result.get("note") == "not_stale_skip":
                stale_skipped += 1
                print(f"  [C2][skip] status={result['status']} (not stale)")
            else:
                print(
                    f"  [C2][summary] generated={result['generated']} skipped={result['skipped']} "
                    f"errors={len(result['errors'])} status={result['status']}"
                )

        print(
            f"\nC2 summary: papers={len(papers)} generated={total_generated} "
            f"skipped={total_skipped} not_stale={stale_skipped} errors={total_errors}"
        )
        if total_errors:
            sys.exit(1)
        return

    if args.regenerate_all:
        ensure_text_llm_ready_or_exit()
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        total_generated = 0
        total_skipped = 0
        total_errors = 0
        for paper_dir in papers:
            print(f"[C3][{paper_dir.name}] force regenerating all summaries...")
            result = regenerate_all_summaries(paper_dir, max_files=max(0, int(args.max_generate_files)))
            total_generated += int(result["generated"])
            total_skipped += int(result["skipped"])
            total_errors += len(result["errors"])
            print(
                f"  [C3][summary] generated={result['generated']} skipped={result['skipped']} "
                f"errors={len(result['errors'])} status={result['status']}"
            )

        print(
            f"\nC3 summary: papers={len(papers)} generated={total_generated} "
            f"skipped={total_skipped} errors={total_errors}"
        )
        if total_errors:
            sys.exit(1)
        return

    if args.check_generation_status:
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        counts = {"fresh": 0, "stale": 0, "missing": 0}
        for paper_dir in papers:
            status_payload = evaluate_generation_status(paper_dir)
            status = str(status_payload.get("status", "missing"))
            counts[status] = counts.get(status, 0) + 1
            print(
                f"[{paper_dir.name}] status={status} "
                f"paper_targets_ok={status_payload['targets']['paper_targets_ok']} "
                f"section_targets={status_payload['targets']['section_targets_count']}"
            )
            if args.write_generation_status:
                out = write_generation_status(paper_dir, status_payload)
                print(f"  [write] {out}")

        print(
            "\nGeneration status summary: "
            f"fresh={counts.get('fresh', 0)} "
            f"stale={counts.get('stale', 0)} "
            f"missing={counts.get('missing', 0)}"
        )
        return

    if args.validate_ov_index:
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        report = build_validation_report(papers)
        VALIDATION_REPORT_JSON.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = report["summary"]
        print(
            "Validation summary: "
            f"papers={summary['papers']} ok={summary['ok']} issue={summary['issue']} "
            f"missing_files={summary['missing_files']} "
            f"placeholder_files={summary['placeholder_files']} "
            f"path_mismatch={summary['path_mismatch']} "
            f"index_chain_issues={summary['index_chain_issues']}"
        )
        print(f"Validation report written: {VALIDATION_REPORT_JSON}")
        return

    if args.validate_overview_quality:
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        report = build_overview_quality_report(papers)
        OVERVIEW_QUALITY_REPORT_JSON.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = report["summary"]
        print(
            "Overview quality summary: "
            f"papers={summary['papers']} pass={summary['pass']} warn={summary['warn']} fail={summary['fail']} "
            f"avg_score={summary['avg_score']}"
        )
        print(f"Overview quality report written: {OVERVIEW_QUALITY_REPORT_JSON}")
        return

    if args.validate_semantic_conflicts:
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        report = build_semantic_conflict_report(papers)
        SEMANTIC_CONFLICT_REPORT_JSON.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = report["summary"]
        print(
            "Semantic conflict summary: "
            f"papers={summary['papers']} high={summary['high']} "
            f"medium={summary['medium']} low={summary['low']} "
            f"avg_conflict_score={summary['avg_conflict_score']}"
        )
        print(f"Semantic conflict report written: {SEMANTIC_CONFLICT_REPORT_JSON}")
        return

    if args.build_fallback_report:
        if paper_id_filter:
            papers = [p for p in papers if p.name == paper_id_filter]
            if not papers:
                print(f"Paper not found: {paper_id_filter!r}")
                sys.exit(1)

        report = build_fallback_review_report(papers)
        FALLBACK_REVIEW_REPORT_JSON.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary = report["summary"]
        print(
            "Fallback review summary: "
            f"papers={summary['papers']} ok={summary['ok']} "
            f"needs_fallback={summary['needs_fallback']} "
            f"manual_review={summary['manual_review']}"
        )
        print(f"Fallback review report written: {FALLBACK_REVIEW_REPORT_JSON}")
        return

    if args.list:
        log = load_import_log()
        meta = load_embedding_meta()
        current_cfg = read_ov_embedding_config()
        print(f"Found {len(papers)} importable papers:\n")
        for p in papers:
            status = log.get(p.name, {}).get("status", "not imported")
            print(f"  {p.name}  [{status}]")
        # Show embedding index info
        if meta:
            print(f"\nCurrent index embedding: {meta.get('embedding_provider')}/{meta.get('embedding_model')} dim={meta.get('embedding_dim')}")
            print(f"  Last indexed: {meta.get('indexed_at')}")
            # Check if config changed
            if current_cfg and (
                current_cfg.get("embedding_model") != meta.get("embedding_model")
                or current_cfg.get("embedding_dim") != meta.get("embedding_dim")
            ):
                print(f"  ⚠ ov.conf changed → {current_cfg.get('embedding_provider')}/{current_cfg.get('embedding_model')} dim={current_cfg.get('embedding_dim')}")
                print("    Run --reindex to rebuild the vector index with the new embedding.")
        elif current_cfg:
            print(f"\nConfigured embedding (not yet indexed): {current_cfg.get('embedding_provider')}/{current_cfg.get('embedding_model')} dim={current_cfg.get('embedding_dim')}")
        return

    # Filter by --paper-id
    if paper_id_filter:
        papers = [p for p in papers if p.name == paper_id_filter]
        if not papers:
            print(f"Paper not found: {paper_id_filter!r}")
            sys.exit(1)

    # Skip already-imported unless --overwrite
    log = load_import_log()
    if not args.overwrite and not args.dry_run:
        papers = [p for p in papers if log.get(p.name, {}).get("status") != "ok"]
        if not papers:
            print("All papers already imported. Use --overwrite to re-import.")
            sys.exit(0)

    # ----------------------------------------------------------------
    # Set up OpenViking client
    # ----------------------------------------------------------------
    embedding_cfg = read_ov_embedding_config()
    if not args.dry_run:
        if not OV_CONF_PATH.exists():
            print(f"ERROR: Config not found: {OV_CONF_PATH}")
            print("Create it from the template in OpenViking/.local_dev/ov.conf")
            sys.exit(1)

        # Tell OpenViking where to find config and source path before runtime checks.
        os.environ["OPENVIKING_CONFIG_FILE"] = str(OV_CONF_PATH)
        _ensure_openviking_path()

        try:
            from openviking.sync_client import SyncOpenViking  # type: ignore
        except ImportError as exc:
            print("ERROR: failed to import openviking runtime.")
            print(f"Detail: {exc}")
            required_py_dll = _detect_engine_python_dll()
            if required_py_dll:
                current_tag = f"python{sys.version_info.major}{sys.version_info.minor}.dll"
                print(
                    "Hint: vectordb engine ABI check: "
                    f"engine expects {required_py_dll}, current interpreter provides {current_tag}."
                )
            print(
                "Hint: ensure OpenViking runtime dependencies are installed "
                f"and source path is available: {OPENVIKING_SRC_PATH}"
            )
            sys.exit(1)

        # Safety gate: for reindex, verify runtime can initialize before wiping data.
        if args.reindex:
            try:
                preflight_client = SyncOpenViking(path=str(OV_DATA_PATH))
                preflight_client.initialize()
                try:
                    preflight_client.close()
                except Exception:
                    pass
            except Exception as exc:
                print("[--reindex][ERR] runtime preflight failed before wipe; aborting to protect index.")
                print(f"Detail: {exc}")
                sys.exit(1)

        # --reindex: wipe vector index before re-importing
        if args.reindex and OV_DATA_PATH.exists():
            print(f"[--reindex] Wiping vector index at {OV_DATA_PATH} ...")
            # Use extended-length path prefix to avoid Windows MAX_PATH issues
            ov_long = Path("\\\\?\\" + str(OV_DATA_PATH.resolve()))
            try:
                shutil.rmtree(ov_long)
                print("  Vector index cleared.")
            except Exception as e:
                # Fallback: PowerShell Remove-Item (handles deep paths)
                import subprocess
                r = subprocess.run(
                    ["powershell", "-Command",
                     f"Remove-Item -LiteralPath '{OV_DATA_PATH}' -Recurse -Force"],
                    capture_output=True
                )
                if r.returncode == 0:
                    print("  Vector index cleared (via PowerShell).")
                else:
                    print(f"  [WARN] Could not fully wipe index (files may be locked by another process).")
                    print(f"  [WARN] Proceeding — new embeddings will overwrite existing ones.")
                    print(f"  [WARN] To fully reset: stop all OpenViking clients and re-run --reindex.")

        OV_DATA_PATH.mkdir(parents=True, exist_ok=True)
        client = SyncOpenViking(path=str(OV_DATA_PATH))
        client.initialize()
        print(f"OpenViking client initialized at {OV_DATA_PATH}")
        if embedding_cfg:
            print(f"Embedding: {embedding_cfg['embedding_provider']}/{embedding_cfg['embedding_model']} dim={embedding_cfg['embedding_dim']}")
    else:
        client = None

    # ----------------------------------------------------------------
    # D1 pipeline: build_ov_index_views -> gate_check -> import
    # ----------------------------------------------------------------

    def build_ov_index_views(import_papers: list[Path]) -> None:
        """D1 step 1: make sure ov_index status snapshots are materialized."""
        for p in import_papers:
            status_payload = evaluate_generation_status(p)
            write_generation_status(p, status_payload)

    def gate_check(import_papers: list[Path]) -> None:
        """D1 step 2: apply generation status gate rules before import."""
        if args.overwrite or args.reindex:
                enforce_stale_gate_or_exit(import_papers, allow_stale_import=args.allow_stale_import)

    build_ov_index_views(papers)
    gate_check(papers)

    # ----------------------------------------------------------------
    # Import loop (D1 step 3)
    # ----------------------------------------------------------------
    print(f"\nImporting {len(papers)} paper(s)...\n")
    results = []
    for paper_dir in papers:
        print(f"[{paper_dir.name}]")

        # On --overwrite: remove the entire paper resource (including all
        # nested document nodes, chunk directories, and auto-generated files)
        # so the fresh import starts from a clean slate.
        if args.overwrite and client is not None:
            paper_uri = f"viking://resources/literature/{paper_dir.name}"
            try:
                client.rm(paper_uri.rstrip("/"), recursive=True)
                print(f"  [clean] removed {paper_uri}/")
            except Exception as e:
                print(f"  [warn ] could not remove {paper_uri}/: {e}")

        result = import_paper_with_backend(
            paper_dir,
            client,
            backend=args.import_backend,
            dry_run=args.dry_run,
            ovpack_force=args.ovpack_force,
            ovpack_vectorize=not args.ovpack_no_vectorize,
        )
        results.append(result)

    # ----------------------------------------------------------------
    # Update log and embedding metadata
    # ----------------------------------------------------------------
    if not args.dry_run:
        for r in results:
            log[r["paper_id"]] = r
        save_import_log(log)
        print(f"\nImport log saved to {IMPORT_LOG}")

        # Update embedding metadata
        ok_papers = [r for r in results if r["status"] == "ok"]
        if ok_papers and embedding_cfg:
            meta = load_embedding_meta()
            meta.update(embedding_cfg)
            meta["indexed_at"] = datetime.now().isoformat()
            # Per-paper indexing timestamps
            if "papers" not in meta:
                meta["papers"] = {}
            for r in ok_papers:
                meta["papers"][r["paper_id"]] = r["timestamp"]
            save_embedding_meta(meta)
            print(f"Embedding metadata saved to {EMBEDDING_META}")

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")
    dry = sum(1 for r in results if r["status"] == "dry_run")
    total_included = sum(r.get("stats", {}).get("included", 0) for r in results)
    total_non_whitelist = sum(r.get("stats", {}).get("skipped_non_whitelist", 0) for r in results)
    total_missing_required = sum(r.get("stats", {}).get("missing_required", 0) for r in results)
    print(f"\nSummary: {ok} ok, {err} error, {dry} dry-run out of {len(results)} papers")
    if ok or dry:
        print(
            f"  included_files={total_included}  "
            f"skipped_non_whitelist_files={total_non_whitelist}  "
            f"missing_required_files={total_missing_required}"
        )
    if err:
        sys.exit(1)


if __name__ == "__main__":
    main()

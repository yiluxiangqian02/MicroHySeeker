"""Migrate sections_by_heading directory names to readable slug format.

Naming rule:
- 3-digit doc_heading_order prefix
- lowercase title slug with hyphens
- max length 80 chars
- duplicate fallback suffix: -dupN

Usage:
    python migrate_heading_dir_names.py
    python migrate_heading_dir_names.py --paper 2023_xxx
    python migrate_heading_dir_names.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_CLEAN_ROOT = HERE


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def candidate_papers(clean_root: Path) -> list[Path]:
    return sorted(
        [d for d in clean_root.iterdir() if d.is_dir() and (d / "metadata.json").exists()],
        key=lambda item: item.name,
    )


def heading_slugify(value: str, max_len: int = 64) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    if not value:
        value = "untitled"
    return value[:max_len].strip("-") or "untitled"


def normalize_heading_match(value: str) -> str:
    value = (value or "").lower().strip()
    return re.sub(r"\s+", " ", value)


def looks_like_document_title_heading(title: str, paper_title: str) -> bool:
    normalized_title = normalize_heading_match(title)
    normalized_paper_title = normalize_heading_match(paper_title)
    if not normalized_title or not normalized_paper_title:
        return False
    return normalized_title == normalized_paper_title or normalized_title.startswith(normalized_paper_title)


def build_heading_dirname(
    doc_heading_order: int,
    heading_text: str,
    used_names: set[str],
    max_len: int = 80,
) -> str:
    prefix = f"{int(doc_heading_order):03d}-"
    base_limit = max(8, max_len - len(prefix))
    base_slug = heading_slugify(heading_text, max_len=base_limit)
    candidate = f"{prefix}{base_slug}"[:max_len].rstrip("-")
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    dup_idx = 2
    while True:
        suffix = f"-dup{dup_idx}"
        slug_limit = max(8, max_len - len(prefix) - len(suffix))
        slug = heading_slugify(heading_text, max_len=slug_limit)
        candidate = f"{prefix}{slug}{suffix}"[:max_len].rstrip("-")
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        dup_idx += 1


def safe_heading_dirname_max_len(paper_dir: Path, default_max: int = 80) -> int:
    max_path_budget = 240
    reserve_tail = len("\\sections_by_heading\\") + len("\\paragraphs\\PRAW-000000.md")
    budget = max_path_budget - len(str(paper_dir.resolve())) - reserve_tail
    return max(24, min(default_max, budget))


def _extract_dirname_from_path(path_value: str) -> str:
    if path_value.startswith("sections_by_heading/") and path_value.endswith("/"):
        return path_value[len("sections_by_heading/") : -1]
    return ""


def migrate_one_paper(paper_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    heading_root = paper_dir / "sections_by_heading"
    if not heading_root.exists() or not heading_root.is_dir():
        return {
            "paper_id": paper_dir.name,
            "status": "skip",
            "reason": "missing sections_by_heading",
            "renamed_count": 0,
            "updated_paragraph_paths": 0,
            "updated_evidence_paths": 0,
            "mapping": [],
        }

    heading_index_path = heading_root / "heading_index.json"
    heading_index = load_json(heading_index_path) if heading_index_path.exists() else {"headings": []}

    records: list[dict[str, Any]] = []
    dir_entries = sorted([d for d in heading_root.iterdir() if d.is_dir()], key=lambda item: item.name)
    uid_to_old_dir: dict[str, str] = {}
    paper_title = str((load_json(paper_dir / "metadata.json") if (paper_dir / "metadata.json").exists() else {}).get("title") or "")

    for d in dir_entries:
        heading_json_path = d / "heading.json"
        if not heading_json_path.exists():
            continue
        heading_obj = load_json(heading_json_path)
        heading_uid = str(heading_obj.get("heading_uid") or "")
        if not heading_uid:
            continue
        uid_to_old_dir[heading_uid] = d.name
        records.append(
            {
                "heading_uid": heading_uid,
                "heading_text": str(heading_obj.get("heading_text") or ""),
                "doc_heading_order": int(heading_obj.get("doc_heading_order") or 999),
                "display_order": int(heading_obj.get("display_order") or heading_obj.get("doc_heading_order") or 999),
                "is_title_page_heading": bool(heading_obj.get("is_title_page_heading", False)),
                "old_dirname": d.name,
            }
        )

    if not records:
        return {
            "paper_id": paper_dir.name,
            "status": "skip",
            "reason": "no heading records",
            "renamed_count": 0,
            "updated_paragraph_paths": 0,
            "updated_evidence_paths": 0,
            "mapping": [],
        }

    records.sort(key=lambda x: (x["display_order"], x["heading_uid"]))

    used_names: set[str] = set()
    heading_dir_max_len = safe_heading_dirname_max_len(paper_dir, default_max=80)
    for rec in records:
        if rec.get("is_title_page_heading") or (
            rec["display_order"] == 1 and looks_like_document_title_heading(rec["heading_text"], paper_title)
        ):
            rec["new_dirname"] = f"{int(rec['display_order']):03d}-front-matter"
            used_names.add(rec["new_dirname"])
            continue
        rec["new_dirname"] = build_heading_dirname(
            rec["display_order"],
            rec["heading_text"],
            used_names,
            max_len=heading_dir_max_len,
        )

    mapping = [
        {
            "heading_uid": rec["heading_uid"],
            "doc_heading_order": rec["doc_heading_order"],
            "old_dirname": rec["old_dirname"],
            "new_dirname": rec["new_dirname"],
        }
        for rec in records
    ]

    rename_ops = [m for m in mapping if m["old_dirname"] != m["new_dirname"]]
    renamed_count = 0

    if not dry_run:
        temp_map: list[tuple[Path, Path, Path]] = []
        for op in rename_ops:
            old_path = heading_root / op["old_dirname"]
            new_path = heading_root / op["new_dirname"]
            if not old_path.exists():
                continue
            if new_path.exists() and new_path != old_path:
                raise RuntimeError(f"target heading dir already exists: {new_path}")
            tmp_suffix = hashlib.sha1(f"{old_path.name}->{new_path.name}".encode("utf-8")).hexdigest()[:8]
            tmp_path = heading_root / f"__tmp_{old_path.name}_{tmp_suffix}"
            if tmp_path.exists():
                raise RuntimeError(f"temporary path already exists: {tmp_path}")
            old_path.rename(tmp_path)
            temp_map.append((tmp_path, old_path, new_path))

        for tmp_path, _old_path, new_path in temp_map:
            tmp_path.rename(new_path)
            renamed_count += 1

    uid_to_new_dir = {m["heading_uid"]: m["new_dirname"] for m in mapping}

    # Update heading.json in each heading directory.
    if not dry_run:
        for heading_uid, dirname in uid_to_new_dir.items():
            heading_json_path = heading_root / dirname / "heading.json"
            if not heading_json_path.exists():
                continue
            heading_obj = load_json(heading_json_path)
            heading_obj["heading_dirname"] = dirname
            write_json(heading_json_path, heading_obj)

    # Update heading_index paths.
    if isinstance(heading_index, dict):
        for item in heading_index.get("headings") or []:
            heading_uid = str(item.get("heading_uid") or "")
            if not heading_uid:
                continue
            dirname = uid_to_new_dir.get(heading_uid)
            if not dirname:
                continue
            item["heading_dirname"] = dirname
            item["path"] = f"sections_by_heading/{dirname}/"
        if not dry_run:
            write_json(heading_index_path, heading_index)

    paragraph_index_path = paper_dir / "paragraph_index.json"
    evidence_links_path = paper_dir / "evidence_links.json"

    updated_paragraph_paths = 0
    updated_evidence_paths = 0
    evidence_id_to_path: dict[str, str] = {}

    if paragraph_index_path.exists():
        paragraph_index = load_json(paragraph_index_path)
        if isinstance(paragraph_index, list):
            for item in paragraph_index:
                heading_uid = str(item.get("heading_uid") or "")
                paragraph_uid = str(item.get("paragraph_uid") or "")
                if not heading_uid or not paragraph_uid:
                    continue
                dirname = uid_to_new_dir.get(heading_uid)
                if not dirname:
                    continue
                new_path = f"sections_by_heading/{dirname}/paragraphs/{paragraph_uid}.md"
                if item.get("content_path") != new_path:
                    item["content_path"] = new_path
                    updated_paragraph_paths += 1
                evidence_id = str(item.get("evidence_id") or "")
                if evidence_id:
                    evidence_id_to_path[evidence_id] = new_path
        if not dry_run:
            write_json(paragraph_index_path, paragraph_index)

    if evidence_links_path.exists():
        evidence_links = load_json(evidence_links_path)
        if isinstance(evidence_links, list):
            for item in evidence_links:
                evidence_id = str(item.get("evidence_id") or "")
                if not evidence_id:
                    continue
                new_path = evidence_id_to_path.get(evidence_id)
                if not new_path:
                    continue
                if item.get("content_path") != new_path:
                    item["content_path"] = new_path
                    updated_evidence_paths += 1
        if not dry_run:
            write_json(evidence_links_path, evidence_links)

    report = {
        "paper_id": paper_dir.name,
        "status": "ok",
        "renamed_count": renamed_count if not dry_run else len(rename_ops),
        "updated_paragraph_paths": updated_paragraph_paths,
        "updated_evidence_paths": updated_evidence_paths,
        "mapping": mapping,
    }

    if not dry_run:
        report_path = paper_dir / "heading_dir_rename_map.json"
        write_json(
            report_path,
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "paper_id": paper_dir.name,
                "mapping": mapping,
            },
        )

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate sections_by_heading directory names to readable slug format.")
    parser.add_argument("--clean-root", type=Path, default=DEFAULT_CLEAN_ROOT)
    parser.add_argument("--paper", type=str, default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clean_root = args.clean_root.resolve()
    papers = candidate_papers(clean_root)
    if args.paper:
        papers = [p for p in papers if p.name == args.paper]

    if not papers:
        print(f"[migrate] no paper directories found in {clean_root}")
        raise SystemExit(1)

    reports = [migrate_one_paper(p, dry_run=args.dry_run) for p in papers]

    renamed_total = sum(int(r.get("renamed_count") or 0) for r in reports)
    paragraph_updates = sum(int(r.get("updated_paragraph_paths") or 0) for r in reports)
    evidence_updates = sum(int(r.get("updated_evidence_paths") or 0) for r in reports)

    for r in reports:
        print(
            f"[migrate] {r['paper_id']} status={r['status']} "
            f"renamed={r.get('renamed_count', 0)} "
            f"paragraph_paths={r.get('updated_paragraph_paths', 0)} "
            f"evidence_paths={r.get('updated_evidence_paths', 0)}"
        )

    print(
        f"[migrate] papers={len(reports)} renamed_total={renamed_total} "
        f"paragraph_updates={paragraph_updates} evidence_updates={evidence_updates} dry_run={args.dry_run}"
    )


if __name__ == "__main__":
    main()

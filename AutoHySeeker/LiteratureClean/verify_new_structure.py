"""Validate the current LiteratureClean Plan-B heading-based package structure.

Usage
-----
    python verify_new_structure.py
    python verify_new_structure.py --paper 2025_sha_10000h_stable_intermittent_alkaline_seawater_electrolysi_333f5c
    python verify_new_structure.py --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_CLEAN_ROOT = HERE
REQUIRED_ROOT_FILES = [
    "metadata.json",
    "full_clean.md",
    "document_tree.json",
    "paragraph_index.json",
    "evidence_links.json",
    "image_manifest.json",
    "table_manifest.json",
    "tag_conflicts.json",
    "quality_report.json",
    "PROCESSING_RECORD.md",
]
LEGACY_ROOT_DISALLOWED = [
    ".abstract.md",
    ".overview.md",
    "memory_cards",
]
HEADING_DIR_PATTERN = re.compile(r"^\d{3}-[a-z0-9-]+(?:-dup\d+)?$")


def _heading_slugify(value: str, max_len: int = 64) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    if not value:
        value = "untitled"
    return value[:max_len].strip("-") or "untitled"


def _normalize_heading_match(value: str) -> str:
    value = (value or "").lower().strip()
    return re.sub(r"\s+", " ", value)


def _looks_like_document_title_heading(title: str, paper_title: str) -> bool:
    normalized_title = _normalize_heading_match(title)
    normalized_paper_title = _normalize_heading_match(paper_title)
    if not normalized_title or not normalized_paper_title:
        return False
    return normalized_title == normalized_paper_title or normalized_title.startswith(normalized_paper_title)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_papers(clean_root: Path) -> list[Path]:
    return sorted(
        [d for d in clean_root.iterdir() if d.is_dir() and (d / "metadata.json").exists()],
        key=lambda item: item.name,
    )


def _first_existing_image(directory: Path) -> bool:
    return any(child.is_file() and child.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} for child in directory.iterdir())


def validate_paper_dir(paper_dir: Path, strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for filename in REQUIRED_ROOT_FILES:
        if not (paper_dir / filename).exists():
            errors.append(f"missing root file: {filename}")

    for legacy_name in LEGACY_ROOT_DISALLOWED:
        if (paper_dir / legacy_name).exists():
            errors.append(f"legacy root artifact still present: {legacy_name}")

    metadata = load_json(paper_dir / "metadata.json") if (paper_dir / "metadata.json").exists() else {}
    document_tree = load_json(paper_dir / "document_tree.json") if (paper_dir / "document_tree.json").exists() else {}
    paragraph_index = load_json(paper_dir / "paragraph_index.json") if (paper_dir / "paragraph_index.json").exists() else []
    evidence_links = load_json(paper_dir / "evidence_links.json") if (paper_dir / "evidence_links.json").exists() else []
    tag_conflicts = load_json(paper_dir / "tag_conflicts.json") if (paper_dir / "tag_conflicts.json").exists() else {}
    quality_report = load_json(paper_dir / "quality_report.json") if (paper_dir / "quality_report.json").exists() else {}

    paper_short = metadata.get("paper_short")
    if not paper_short:
        errors.append("metadata.json missing paper_short")

    heading_root = paper_dir / "sections_by_heading"
    if not heading_root.exists() or not heading_root.is_dir():
        errors.append("missing sections_by_heading/ directory")
        return errors, warnings

    if (paper_dir / "sections").exists():
        errors.append("legacy sections/ directory still present")

    heading_dirs = sorted([d for d in heading_root.iterdir() if d.is_dir()], key=lambda item: item.name)
    if not heading_dirs:
        errors.append("sections_by_heading/ has no heading directories")

    heading_index_path = heading_root / "heading_index.json"
    heading_index: dict[str, Any] = {}
    if not heading_index_path.exists():
        errors.append("missing sections_by_heading/heading_index.json")
    else:
        heading_index = load_json(heading_index_path)
        for item in heading_index.get("headings") or []:
            if not item.get("heading_uid"):
                errors.append("heading_index entry missing heading_uid")
            if not item.get("path"):
                errors.append(f"heading_index entry missing path: {item.get('heading_uid')}")
            if "display_order" not in item:
                errors.append(f"heading_index entry missing display_order: {item.get('heading_uid')}")

    for heading_dir in heading_dirs:
        heading_json = heading_dir / "heading.json"
        paragraphs_md = heading_dir / "paragraphs.md"
        paragraphs_dir = heading_dir / "paragraphs"
        if not HEADING_DIR_PATTERN.match(heading_dir.name):
            errors.append(f"invalid heading directory name: {heading_dir.name}")
        if not heading_json.exists():
            errors.append(f"missing heading.json: {heading_dir.name}")
            continue
        if not paragraphs_md.exists():
            errors.append(f"missing paragraphs.md: {heading_dir.name}")
        if not paragraphs_dir.exists():
            errors.append(f"missing paragraphs/ dir: {heading_dir.name}")
            continue

        heading_obj = load_json(heading_json)
        for key in [
            "heading_uid",
            "heading_text",
            "heading_level",
            "doc_heading_order",
            "display_order",
            "paragraph_uids",
            "paragraph_paths",
        ]:
            if key not in heading_obj:
                errors.append(f"heading.json missing {key}: {heading_dir.name}")

        heading_dirname = str(heading_obj.get("heading_dirname") or "")
        if heading_dirname and heading_dirname != heading_dir.name:
            errors.append(
                f"heading.json heading_dirname mismatch: {heading_dir.name} != {heading_dirname}"
            )

        display_order = int(heading_obj.get("display_order") or heading_obj.get("doc_heading_order") or 999)
        expected_prefix = f"{display_order:03d}-"
        if not heading_dir.name.startswith(expected_prefix):
            errors.append(
                f"heading directory does not start with display_order prefix: {heading_dir.name}"
            )
        else:
            if heading_obj.get("is_title_page_heading"):
                if not heading_dir.name.endswith("front-matter"):
                    errors.append(f"title-page heading must use front-matter dirname: {heading_dir.name}")
            else:
                slug_expected = _heading_slugify(str(heading_obj.get("heading_text") or ""), max_len=64)
                dirname_body = heading_dir.name[len(expected_prefix):]
                dirname_body_no_dup = re.sub(r"-dup\d+$", "", dirname_body)
                # Allow truncation: generated dirname may be a prefix of the full slug.
                if slug_expected and not slug_expected.startswith(dirname_body_no_dup):
                    warnings.append(
                        f"heading directory slug may not reflect heading_text: {heading_dir.name}"
                    )

        paragraph_files = sorted(paragraphs_dir.glob("PRAW-*.md"))
        if strict and not paragraph_files:
            errors.append(f"no paragraph markdown files found: {heading_dir.name}")

    if isinstance(heading_index, dict):
        for item in heading_index.get("headings") or []:
            path_s = str(item.get("path") or "")
            if path_s.startswith("sections_by_heading/") and path_s.endswith("/"):
                dir_name = path_s[len("sections_by_heading/") : -1]
                if not (heading_root / dir_name).exists():
                    errors.append(f"heading_index path not found: {path_s}")
            elif path_s:
                errors.append(f"heading_index path format invalid: {path_s}")

    if isinstance(document_tree, dict):
        if document_tree.get("heading_count") != len(heading_dirs):
            warnings.append(
                f"document_tree heading_count mismatch: {document_tree.get('heading_count')} vs {len(heading_dirs)}"
            )

    paragraph_ids = set()
    paragraph_uid_to_heading_uid: dict[str, str] = {}
    original_structure = load_json(paper_dir / "original_structure_index.json") if (paper_dir / "original_structure_index.json").exists() else {}
    known_heading_uids = {str(h.get("heading_uid")) for h in (original_structure.get("headings") or []) if h.get("heading_uid")}
    paragraph_uid_set_from_original = {
        str(uid)
        for h in (original_structure.get("headings") or [])
        for uid in (h.get("paragraph_uid_list") or [])
        if uid
    }

    for item in paragraph_index if isinstance(paragraph_index, list) else []:
        paragraph_id = item.get("paragraph_id")
        paragraph_uid = item.get("paragraph_uid")
        heading_uid = item.get("heading_uid")
        evidence_id = item.get("evidence_id")
        evidence_short_id = item.get("evidence_short_id")
        content_path = item.get("content_path")
        if not paragraph_id:
            errors.append("paragraph_index entry missing paragraph_id")
            continue
        paragraph_ids.add(paragraph_id)
        if not paragraph_uid:
            errors.append(f"paragraph_index missing paragraph_uid: {paragraph_id}")
        if not heading_uid:
            errors.append(f"paragraph_index missing heading_uid: {paragraph_id}")
        if paragraph_uid and heading_uid:
            existing = paragraph_uid_to_heading_uid.get(str(paragraph_uid))
            if existing and existing != str(heading_uid):
                errors.append(
                    f"paragraph_uid maps to multiple heading_uid: {paragraph_uid} -> {existing}, {heading_uid}"
                )
            paragraph_uid_to_heading_uid[str(paragraph_uid)] = str(heading_uid)
            if known_heading_uids and str(heading_uid) not in known_heading_uids:
                errors.append(f"paragraph_index heading_uid not found in original_structure_index: {heading_uid}")
            if paragraph_uid_set_from_original and str(paragraph_uid) not in paragraph_uid_set_from_original:
                errors.append(f"paragraph_uid not found in original_structure_index: {paragraph_uid}")
        if not evidence_id:
            errors.append(f"paragraph_index missing evidence_id: {paragraph_id}")
        if not evidence_short_id:
            errors.append(f"paragraph_index missing evidence_short_id: {paragraph_id}")
        if "macro_trace" not in item:
            errors.append(f"paragraph_index missing macro_trace: {paragraph_id}")
        if "macro_conflict" not in item:
            errors.append(f"paragraph_index missing macro_conflict: {paragraph_id}")
        if content_path and not (paper_dir / content_path).exists():
            errors.append(f"paragraph_index content_path missing: {content_path}")

    for entry in evidence_links if isinstance(evidence_links, list) else []:
        evidence_id = entry.get("evidence_id")
        content_path = entry.get("content_path")
        if not evidence_id:
            errors.append("evidence_links entry missing evidence_id")
            continue
        if not entry.get("evidence_short_id"):
            errors.append(f"evidence_links missing evidence_short_id: {evidence_id}")
        if content_path and not (paper_dir / content_path).exists():
            errors.append(f"evidence_links content_path missing: {content_path}")

    figures_dir = paper_dir / "figures"
    if figures_dir.exists():
        for figure_dir in sorted([d for d in figures_dir.iterdir() if d.is_dir()], key=lambda item: item.name):
            if not (figure_dir / "caption.md").exists():
                errors.append(f"figure missing caption.md: {figure_dir.name}")
            if strict and not _first_existing_image(figure_dir):
                errors.append(f"figure has no image asset: {figure_dir.name}")

    tables_dir = paper_dir / "tables"
    if tables_dir.exists():
        for table_dir in sorted([d for d in tables_dir.iterdir() if d.is_dir()], key=lambda item: item.name):
            if not (table_dir / "table.md").exists():
                errors.append(f"table missing table.md: {table_dir.name}")
            if not (table_dir / "caption.md").exists():
                errors.append(f"table missing caption.md: {table_dir.name}")

    uncertain_items = quality_report.get("uncertain_items") if isinstance(quality_report, dict) else None
    if uncertain_items is None:
        errors.append("quality_report missing uncertain_items")
    elif not isinstance(uncertain_items, list):
        errors.append("quality_report uncertain_items must be a list")

    if not isinstance(tag_conflicts, dict):
        errors.append("tag_conflicts.json must be an object")
    else:
        if "items" not in tag_conflicts or not isinstance(tag_conflicts.get("items"), list):
            errors.append("tag_conflicts.json missing items list")
        for row in tag_conflicts.get("items") or []:
            if not row.get("paragraph_uid"):
                errors.append("tag_conflicts item missing paragraph_uid")
            if not isinstance(row.get("macro_trace"), dict):
                errors.append("tag_conflicts item missing macro_trace object")
            if not isinstance(row.get("macro_conflict"), dict):
                errors.append("tag_conflicts item missing macro_conflict object")

    return errors, warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify LiteratureClean Plan-B heading-based package structure.")
    parser.add_argument("--clean-root", type=Path, default=DEFAULT_CLEAN_ROOT)
    parser.add_argument("--paper", type=str, default="", help="Only verify one paper directory by exact folder name.")
    parser.add_argument("--strict", action="store_true", help="Treat missing figure image assets and empty paragraph dirs as errors.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clean_root = args.clean_root.resolve()
    papers = candidate_papers(clean_root)
    if args.paper:
        papers = [d for d in papers if d.name == args.paper]

    if not papers:
        print(f"[verify] No paper packages found under: {clean_root}")
        raise SystemExit(1)

    total_errors = 0
    total_warnings = 0
    for paper_dir in papers:
        errors, warnings = validate_paper_dir(paper_dir, strict=args.strict)
        total_errors += len(errors)
        total_warnings += len(warnings)
        status = "OK" if not errors else "FAIL"
        print(f"[{status}] {paper_dir.name}")
        for item in errors:
            print(f"  ERROR: {item}")
        for item in warnings:
            print(f"  WARN : {item}")

    print(
        f"[verify] papers={len(papers)} errors={total_errors} warnings={total_warnings} strict={args.strict}"
    )
    raise SystemExit(1 if total_errors else 0)


if __name__ == "__main__":
    main()

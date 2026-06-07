"""check_plan_b_compliance.py

Generate Plan-B file-list compliance summary for all LiteratureClean paper packages.

Usage:
    python check_plan_b_compliance.py
    python check_plan_b_compliance.py --paper 2025_sha_xxx
    python check_plan_b_compliance.py --strict
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_CLEAN_ROOT = HERE
DEFAULT_JSON_REPORT = HERE / "plan_b_compliance_report.json"
DEFAULT_MD_REPORT = HERE / "plan_b_compliance_report.md"

REQUIRED_FILES = [
    "metadata.json",
    "PROCESSING_RECORD.md",
    "quality_report.json",
    "tag_conflicts.json",
    "original_structure_index.json",
    "paragraph_index.json",
    "document_tree.json",
    "full_clean.md",
    "evidence_links.json",
    "image_manifest.json",
    "table_manifest.json",
]

REQUIRED_DIRS = [
    "figures",
    "tables",
    "sections_by_heading",
]

DISALLOWED_LEGACY = [
    "sections",
    "section_abstract.md",
    "section_overview.md",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_papers(clean_root: Path) -> list[Path]:
    return sorted(
        [d for d in clean_root.iterdir() if d.is_dir() and (d / "metadata.json").exists()],
        key=lambda item: item.name,
    )


def check_one(paper_dir: Path, strict: bool = False) -> dict[str, Any]:
    missing_files = [name for name in REQUIRED_FILES if not (paper_dir / name).exists()]
    missing_dirs = [name for name in REQUIRED_DIRS if not (paper_dir / name).is_dir()]
    legacy_present = [name for name in DISALLOWED_LEGACY if (paper_dir / name).exists()]

    heading_root = paper_dir / "sections_by_heading"
    heading_count = 0
    heading_index_ok = False
    paragraph_path_missing = 0
    original_heading_missing = 0

    if heading_root.exists() and heading_root.is_dir():
        heading_count = sum(1 for d in heading_root.iterdir() if d.is_dir())
        heading_index = heading_root / "heading_index.json"
        heading_index_ok = heading_index.exists()

    paragraph_index_path = paper_dir / "paragraph_index.json"
    if paragraph_index_path.exists():
        paragraph_items = load_json(paragraph_index_path)
        if isinstance(paragraph_items, list):
            for item in paragraph_items:
                content_path = item.get("content_path")
                if content_path and not (paper_dir / str(content_path)).exists():
                    paragraph_path_missing += 1
                if not item.get("heading_uid"):
                    original_heading_missing += 1

    errors: list[str] = []
    if missing_files:
        errors.append(f"missing_files={len(missing_files)}")
    if missing_dirs:
        errors.append(f"missing_dirs={len(missing_dirs)}")
    if legacy_present:
        errors.append(f"legacy_present={len(legacy_present)}")
    if not heading_index_ok:
        errors.append("missing heading_index.json")
    if strict and heading_count <= 0:
        errors.append("no heading directories")
    if strict and paragraph_path_missing > 0:
        errors.append(f"paragraph_path_missing={paragraph_path_missing}")
    if strict and original_heading_missing > 0:
        errors.append(f"heading_uid_missing={original_heading_missing}")

    return {
        "paper_id": paper_dir.name,
        "status": "pass" if not errors else "fail",
        "missing_files": missing_files,
        "missing_dirs": missing_dirs,
        "legacy_present": legacy_present,
        "heading_count": heading_count,
        "heading_index_ok": heading_index_ok,
        "paragraph_path_missing": paragraph_path_missing,
        "heading_uid_missing": original_heading_missing,
        "errors": errors,
    }


def make_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Plan B 合规检查报告")
    lines.append("")
    lines.append(f"生成时间: {summary['generated_at']}")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 样本总数: {summary['paper_count']}")
    lines.append(f"- 通过数: {summary['pass_count']}")
    lines.append(f"- 失败数: {summary['fail_count']}")
    lines.append(f"- 通过率: {summary['pass_rate']}")
    lines.append("")
    lines.append("## 明细")
    lines.append("")
    lines.append("| paper_id | 状态 | heading_count | 缺失文件 | 缺失目录 | legacy残留 |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for item in summary["papers"]:
        lines.append(
            f"| {item['paper_id']} | {item['status']} | {item['heading_count']} | "
            f"{len(item['missing_files'])} | {len(item['missing_dirs'])} | {len(item['legacy_present'])} |"
        )

    fail_items = [item for item in summary["papers"] if item["status"] == "fail"]
    if fail_items:
        lines.append("")
        lines.append("## 失败项错误摘要")
        lines.append("")
        for item in fail_items:
            lines.append(f"- {item['paper_id']}: {', '.join(item['errors'])}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Plan-B file-list compliance for LiteratureClean packages.")
    parser.add_argument("--clean-root", type=Path, default=DEFAULT_CLEAN_ROOT)
    parser.add_argument("--paper", type=str, default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clean_root = args.clean_root.resolve()
    papers = candidate_papers(clean_root)
    if args.paper:
        papers = [p for p in papers if p.name == args.paper]

    if not papers:
        print(f"[compliance] no paper directories found in {clean_root}")
        raise SystemExit(1)

    results = [check_one(p, strict=args.strict) for p in papers]
    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = len(results) - pass_count
    pass_rate = f"{(pass_count / len(results) * 100):.2f}%"

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "clean_root": str(clean_root),
        "strict": bool(args.strict),
        "paper_count": len(results),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": pass_rate,
        "papers": results,
    }

    args.json_report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_report.write_text(make_markdown(summary), encoding="utf-8")

    print(f"[compliance] papers={len(results)} pass={pass_count} fail={fail_count} pass_rate={pass_rate}")
    print(f"[compliance] json={args.json_report}")
    print(f"[compliance] md={args.md_report}")

    raise SystemExit(1 if fail_count else 0)


if __name__ == "__main__":
    main()

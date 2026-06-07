"""batch_clean_mineru.py

Batch processor for the unified LiteratureClean sections pipeline.

This module only scans MinerU output folders, deduplicates by paper_id,
and dispatches each paper to clean_single_mineru_paper.build_package().
It does not generate legacy memory_cards output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
AUTOHY_ROOT = HERE.parent
DEFAULT_MINERU_OUTPUT = AUTOHY_ROOT / "MinerU" / "output"
DEFAULT_CLEAN_ROOT = HERE
RUN_LOG_PATH = HERE / "batch_run_log.json"

sys.path.insert(0, str(HERE))

import clean_single_mineru_paper as _cleaner  # noqa: E402
from generate_preprocessing_regression_report import generate_preprocessing_regression_report  # noqa: E402


def load_run_log(log_path: Path) -> dict[str, Any]:
    if log_path.exists():
        try:
            return json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": "1", "updated_at": "", "entries": {}}


def save_run_log(log_path: Path, log: dict[str, Any]) -> None:
    log["updated_at"] = datetime.now().isoformat(timespec="seconds")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_valid_mineru_dir(path: Path) -> bool:
    return path.is_dir() and (path / "full.md").exists()


def scan_mineru_output(output_dir: Path) -> list[Path]:
    if not output_dir.is_dir():
        return []
    return sorted([d for d in output_dir.iterdir() if is_valid_mineru_dir(d)], key=lambda item: item.name)


def fast_paper_id(mineru_dir: Path) -> tuple[str, str]:
    full_md = mineru_dir / "full.md"
    if not full_md.exists():
        return "", ""
    try:
        text = _cleaner.read_text(full_md)
        meta = _cleaner.extract_metadata(text, mineru_dir)
        return str(meta.get("paper_id", "")), str(meta.get("doi", ""))
    except Exception:
        return "", ""


def process_one_paper(mineru_dir: Path, clean_root: Path, overwrite: bool) -> dict[str, Any]:
    try:
        clean_dir = _cleaner.build_package(mineru_dir, clean_root, overwrite=overwrite)
        return {
            "status": "success",
            "clean_dir": str(clean_dir),
            "pipeline": "unified_sections_pipeline (clean_single_mineru_paper)",
        }
    except FileExistsError as exc:
        return {"status": "skipped", "reason": "already_exists", "detail": str(exc)}
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "traceback": traceback.format_exc()}


def _record_result(entries: dict[str, Any], paper_id: str, result: dict[str, Any], mineru_dir: Path) -> None:
    entries[paper_id] = {
        "status": result.get("status"),
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "folder": mineru_dir.name,
        "clean_dir": result.get("clean_dir", ""),
        "pipeline": result.get("pipeline", ""),
        "error": result.get("error", ""),
    }


def run_batch(
    mineru_output: Path = DEFAULT_MINERU_OUTPUT,
    clean_root: Path = DEFAULT_CLEAN_ROOT,
    overwrite: bool = False,
    overwrite_failed: bool = False,
    dry_run: bool = False,
    paper_filter: str | None = None,
) -> list[dict[str, Any]]:
    all_dirs = scan_mineru_output(mineru_output)
    if paper_filter:
        all_dirs = [d for d in all_dirs if paper_filter.lower() in d.name.lower()]
    if not all_dirs:
        print(f"[batch] No valid MinerU directories found in: {mineru_output}")
        return []

    run_log = load_run_log(RUN_LOG_PATH)
    entries = run_log.setdefault("entries", {})
    seen_ids: dict[str, Path] = {}
    deduped: list[tuple[Path, str, str]] = []

    for mineru_dir in all_dirs:
        paper_id, doi = fast_paper_id(mineru_dir)
        if not paper_id:
            deduped.append((mineru_dir, "", ""))
            continue
        if paper_id in seen_ids:
            print(f"[batch] SKIP duplicate  {mineru_dir.name}\n        same paper_id as {seen_ids[paper_id].name}  ({paper_id})")
            entries[f"{paper_id}_dup_{mineru_dir.name[:20]}"] = {
                "status": "skipped",
                "reason": "duplicate_folder",
                "duplicate_of": str(seen_ids[paper_id]),
                "mineru_dir": str(mineru_dir),
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            }
            continue
        seen_ids[paper_id] = mineru_dir
        deduped.append((mineru_dir, paper_id, doi))

    results: list[dict[str, Any]] = []

    for mineru_dir, paper_id, doi in deduped:
        if not paper_id:
            paper_id, doi = fast_paper_id(mineru_dir)
        prev = entries.get(paper_id, {})
        prev_status = str(prev.get("status", ""))

        should_process = True
        if overwrite:
            should_process = True
        elif overwrite_failed and prev_status == "failed":
            should_process = True
        elif prev_status in {"success", "skipped"}:
            should_process = False

        if dry_run:
            should_process = False

        if not should_process:
            results.append({"paper_id": paper_id, "status": "skipped", "reason": "already_done", "mineru_dir": str(mineru_dir), "doi": doi})
            continue

        if dry_run:
            print(f"[batch] WOULD PROCESS  {mineru_dir.name[:60]} ... -> {paper_id}")
            results.append({"paper_id": paper_id, "status": "dry_run", "mineru_dir": str(mineru_dir), "doi": doi})
            continue

        print(f"[batch] PROCESS  {mineru_dir.name[:60]} ...")
        result = process_one_paper(mineru_dir, clean_root, overwrite=overwrite)
        _record_result(entries, paper_id, result, mineru_dir)
        results.append({"paper_id": paper_id, "doi": doi, **result})
        if result.get("status") == "success":
            print(f"[batch] OK       {paper_id}")
        elif result.get("status") == "skipped":
            print(f"[batch] SKIP     {paper_id}")
        else:
            print(f"[batch] FAIL     {paper_id}")

    save_run_log(RUN_LOG_PATH, run_log)
    print("Batch run summary")
    print(f"  Processed : {sum(1 for item in results if item.get('status') == 'success')}")
    print(f"  Skipped   : {sum(1 for item in results if item.get('status') == 'skipped') + sum(1 for item in results if item.get('status') == 'dry_run')}")
    print(f"  Failed    : {sum(1 for item in results if item.get('status') == 'failed')}")
    print(f"  Run log   : {RUN_LOG_PATH}")

    if not dry_run:
        summary = generate_preprocessing_regression_report(clean_root=clean_root, run_log_path=RUN_LOG_PATH)
        print(f"  Regression report updated : {summary['report_path']}")

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch process MinerU output into LiteratureClean sections packages.")
    parser.add_argument("--mineru-output", type=Path, default=DEFAULT_MINERU_OUTPUT)
    parser.add_argument("--clean-root", type=Path, default=DEFAULT_CLEAN_ROOT)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--overwrite-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--paper", type=str, default=None)
    parser.add_argument("--list", action="store_true", help="List detected MinerU folders and exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for folder in scan_mineru_output(args.mineru_output):
            paper_id, doi = fast_paper_id(folder)
            print(f"{folder.name}\t{paper_id}\t{doi}")
        return
    run_batch(
        mineru_output=args.mineru_output,
        clean_root=args.clean_root,
        overwrite=args.overwrite,
        overwrite_failed=args.overwrite_failed,
        dry_run=args.dry_run,
        paper_filter=args.paper,
    )


if __name__ == "__main__":
    main()
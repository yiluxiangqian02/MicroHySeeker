"""Remove experiment record directories whose echem folder is empty.

By default this script runs in dry-run mode and only prints the directories
that would be removed. Pass --execute to delete them.
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def default_data_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def is_empty_directory(path: Path) -> bool:
    if not path.is_dir():
        return False

    try:
        next(path.iterdir())
    except StopIteration:
        return True
    return False


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def find_records_with_empty_echem(data_root: Path, date: str | None = None) -> list[Path]:
    data_root = data_root.resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Data root does not exist or is not a directory: {data_root}")

    date_dirs = [data_root / date] if date else sorted(data_root.iterdir())
    records: list[Path] = []

    for date_dir in date_dirs:
        if not date_dir.is_dir() or not DATE_DIR_RE.match(date_dir.name):
            continue

        for record_dir in sorted(date_dir.iterdir()):
            if not record_dir.is_dir():
                continue

            echem_dir = record_dir / "echem"
            if echem_dir.is_dir() and is_empty_directory(echem_dir):
                records.append(record_dir.resolve())

    return records


def delete_records(records: list[Path], data_root: Path) -> tuple[list[Path], list[tuple[Path, str]]]:
    data_root = data_root.resolve()
    deleted: list[Path] = []
    failed: list[tuple[Path, str]] = []

    for record_dir in records:
        record_dir = record_dir.resolve()
        parent = record_dir.parent.resolve()

        if not is_relative_to(record_dir, data_root):
            failed.append((record_dir, "refusing to delete a path outside data root"))
            continue
        if not DATE_DIR_RE.match(parent.name) or parent.parent.resolve() != data_root:
            failed.append((record_dir, "refusing to delete a directory outside data/YYYY-MM-DD"))
            continue
        if not is_empty_directory(record_dir / "echem"):
            failed.append((record_dir, "echem is no longer empty"))
            continue

        try:
            shutil.rmtree(record_dir)
        except OSError as exc:
            failed.append((record_dir, str(exc)))
        else:
            deleted.append(record_dir)

    return deleted, failed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete experiment record directories when their echem folder is empty."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=default_data_root(),
        help="Path to the data directory. Defaults to the repository data directory.",
    )
    parser.add_argument(
        "--date",
        help="Only scan one date directory, for example 2026-04-13.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete matching experiment record directories. Without this, only dry-run.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print the summary, not every matching directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_root = args.data_root.resolve()

    records = find_records_with_empty_echem(data_root, args.date)

    mode = "DELETE" if args.execute else "DRY-RUN"
    print(f"[{mode}] data root: {data_root}")
    print(f"[{mode}] matched records: {len(records)}")

    if records and not args.quiet:
        for record_dir in records:
            print(record_dir)

    if not args.execute:
        print("No files were deleted. Re-run with --execute to delete these records.")
        return 0

    deleted, failed = delete_records(records, data_root)
    print(f"Deleted records: {len(deleted)}")
    print(f"Failed records: {len(failed)}")

    for record_dir, reason in failed:
        print(f"FAILED: {record_dir} ({reason})")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

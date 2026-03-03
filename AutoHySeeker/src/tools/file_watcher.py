"""Polling-based data directory watcher."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Generator

from src.common.config import DATA_ROOT


def _snapshot_run_dirs(root: Path) -> set[Path]:
    run_dirs: set[Path] = set()
    if not root.exists():
        return run_dirs
    for day_dir in root.iterdir():
        if not day_dir.is_dir():
            continue
        for run_dir in day_dir.iterdir():
            if run_dir.is_dir():
                run_dirs.add(run_dir.resolve())
    return run_dirs


def watch_data_dir(
    data_root: str | None = None,
    poll_interval: float = 2.0,
    max_polls: int | None = None,
) -> Generator[str, None, None]:
    """Yield newly created run directories in data root."""
    root = Path(data_root).resolve() if data_root else DATA_ROOT
    seen = _snapshot_run_dirs(root)
    polls = 0

    while max_polls is None or polls < max_polls:
        time.sleep(poll_interval)
        current = _snapshot_run_dirs(root)
        for run_dir in sorted(current - seen):
            yield str(run_dir)
        seen = current
        polls += 1


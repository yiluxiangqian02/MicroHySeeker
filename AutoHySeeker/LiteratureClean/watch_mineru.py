"""watch_mineru.py

Watches AutoHySeeker/MinerU/output for new MinerU paper folders and
automatically runs the LiteratureClean pipeline on each new arrival.

Modes
-----
  python watch_mineru.py              # poll every 30s (no extra deps)
  python watch_mineru.py --interval 60
  python watch_mineru.py --once       # one scan then exit (cron-safe)

How it works
------------
1. On startup: scans MinerU/output and processes any folders whose paper_id
   does not yet exist in LiteratureClean (not already in batch_run_log.json).
2. Then polls every --interval seconds for new subfolders containing full.md.
3. Duplicate detection: paper_id already in batch_run_log.json → skip.
4. A watch log is written to LiteratureClean/watch_log.json.

Stopping: Ctrl-C or SIGTERM.

Dependencies
------------
Pure Python stdlib — no additional packages required.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent          # .../LiteratureClean/
AUTOHY_ROOT = HERE.parent                        # .../AutoHySeeker/
DEFAULT_MINERU_OUTPUT = AUTOHY_ROOT / "MinerU" / "output"
DEFAULT_CLEAN_ROOT = HERE
WATCH_LOG_PATH = HERE / "watch_log.json"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [watch] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import batch pipeline
# ---------------------------------------------------------------------------

sys.path.insert(0, str(HERE))

from batch_clean_mineru import (   # noqa: E402
    process_one_paper,
    scan_mineru_output,
    fast_paper_id,
    load_run_log,
    save_run_log,
    RUN_LOG_PATH,
)
from generate_preprocessing_regression_report import generate_preprocessing_regression_report  # noqa: E402

# ---------------------------------------------------------------------------
# Watch log helpers
# ---------------------------------------------------------------------------

def load_watch_log() -> dict:
    if WATCH_LOG_PATH.exists():
        try:
            return json.loads(WATCH_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"processed": [], "errors": [], "last_scan": None}


def save_watch_log(wlog: dict) -> None:
    WATCH_LOG_PATH.write_text(
        json.dumps(wlog, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _done_paper_ids(clean_root: Path) -> set[str]:
    """Return paper_ids already processed (by dir or run_log)."""
    run_log = load_run_log(RUN_LOG_PATH)
    from_log: set[str] = {
        k for k, v in run_log.get("entries", {}).items()
        if v.get("status") in ("success", "skipped")
    }
    from_dirs: set[str] = {d.name for d in clean_root.iterdir() if d.is_dir()} if clean_root.exists() else set()
    return from_log | from_dirs


def _process(
    mineru_dir: Path,
    clean_root: Path,
    wlog: dict,
) -> None:
    """Process one folder, update run_log and watch_log."""
    paper_id, _ = fast_paper_id(mineru_dir)
    if not paper_id:
        log.warning("Cannot determine paper_id for %s — skipping.", mineru_dir.name)
        return

    if (clean_root / paper_id).exists():
        log.info("SKIP (already exists): %s", paper_id)
        return

    log.info("PROCESS: %s → %s ...", mineru_dir.name[:60], paper_id)
    result = process_one_paper(mineru_dir, clean_root, overwrite=False)
    ts = datetime.now().isoformat(timespec="seconds")

    # Update batch_run_log.json
    run_log = load_run_log(RUN_LOG_PATH)
    entries = run_log.setdefault("entries", {})
    entries[paper_id] = {
        "status": result.get("status"),
        "processed_at": ts,
        "folder": mineru_dir.name,
        "clean_dir": result.get("clean_dir", ""),
        "pipeline": result.get("pipeline", ""),
        "error": result.get("error", ""),
    }
    save_run_log(RUN_LOG_PATH, run_log)

    if result.get("status") == "success":
        log.info("OK: %s", paper_id)
        wlog["processed"].append({"folder": mineru_dir.name, "paper_id": paper_id, "processed_at": ts})
    else:
        err = result.get("error") or result.get("reason") or "unknown"
        log.error("FAILED: %s — %s", mineru_dir.name, err)
        wlog["errors"].append({"folder": mineru_dir.name, "error": err, "at": ts})

    summary = generate_preprocessing_regression_report(clean_root=clean_root, run_log_path=RUN_LOG_PATH)
    log.info("Regression report updated: %s", summary["report_path"])

    save_watch_log(wlog)


# ---------------------------------------------------------------------------
# Core watcher class
# ---------------------------------------------------------------------------

class MinerUWatcher:
    def __init__(
        self,
        mineru_output: Path,
        clean_root: Path,
        interval: int = 30,
    ) -> None:
        self.mineru_output = mineru_output
        self.clean_root = clean_root
        self.interval = interval
        self._known_folders: set[str] = set()   # folder names already dispatched
        self._running = False

    def _scan_new(self, wlog: dict) -> None:
        """Find and process folders not yet seen this session."""
        dirs = scan_mineru_output(self.mineru_output)
        done_ids = _done_paper_ids(self.clean_root)
        for d in dirs:
            if d.name in self._known_folders:
                continue
            self._known_folders.add(d.name)
            pid, _ = fast_paper_id(d)
            if pid and pid in done_ids:
                continue
            _process(d, self.clean_root, wlog)

    def start(self) -> None:
        """Start polling loop (blocking until stopped)."""
        wlog = load_watch_log()

        # Initial pass
        log.info("Initial scan of %s ...", self.mineru_output)
        self._scan_new(wlog)

        log.info(
            "Watching %s every %ds. Press Ctrl-C to stop.",
            self.mineru_output,
            self.interval,
        )
        self._running = True
        while self._running:
            time.sleep(self.interval)
            wlog["last_scan"] = datetime.now().isoformat(timespec="seconds")
            self._scan_new(wlog)
            save_watch_log(wlog)

    def stop(self) -> None:
        self._running = False


# ---------------------------------------------------------------------------
# Signal handler
# ---------------------------------------------------------------------------

_watcher: MinerUWatcher | None = None


def _handle_signal(signum: int, frame: object) -> None:
    log.info("Received signal %d — stopping watcher.", signum)
    if _watcher:
        _watcher.stop()
    sys.exit(0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Watch MinerU output and auto-process new papers into LiteratureClean."
    )
    p.add_argument(
        "--mineru-output",
        type=Path,
        default=DEFAULT_MINERU_OUTPUT,
        help="Path to MinerU/output directory (default: %(default)s)",
    )
    p.add_argument(
        "--clean-root",
        type=Path,
        default=DEFAULT_CLEAN_ROOT,
        help="Path to LiteratureClean root (default: %(default)s)",
    )
    p.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: %(default)s)",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run one scan then exit (useful for cron / task scheduler).",
    )
    return p.parse_args()


def main() -> None:
    global _watcher
    args = parse_args()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    log.info("MinerU output : %s", args.mineru_output)
    log.info("LiteratureClean: %s", args.clean_root)

    if args.once:
        log.info("--once mode: single scan then exit.")
        wlog = load_watch_log()
        dirs = scan_mineru_output(args.mineru_output)
        done_ids = _done_paper_ids(args.clean_root)
        processed = 0
        for d in dirs:
            pid, _ = fast_paper_id(d)
            if pid and pid in done_ids:
                continue
            _process(d, args.clean_root, wlog)
            processed += 1
        save_watch_log(wlog)
        log.info("Done. Processed %d new paper(s).", processed)
        return

    _watcher = MinerUWatcher(args.mineru_output, args.clean_root, interval=args.interval)
    _watcher.start()


if __name__ == "__main__":
    main()



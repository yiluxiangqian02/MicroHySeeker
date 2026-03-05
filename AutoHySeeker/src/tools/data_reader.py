"""Data reader tools for AutoHySeeker — load and summarise experiment data.

This module extends :mod:`src.tools.echem_reader` with higher-level helpers
that batch-load data files and expose them through the global tool registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.types import EchemData


# ── helpers ───────────────────────────────────────────────────────────────────

def _read_csv_fallback(path: Path, **kwargs: Any) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, errors="replace", **kwargs)


def _load_json_safe(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _technique_from_filename(name: str) -> str:
    lower = name.lower()
    for tag in ("cv", "lsv", "eis", "ca", "cp", "dpv", "swv"):
        if tag in lower:
            return tag
    return "unknown"


# ── public API ────────────────────────────────────────────────────────────────

def load_echem_file(file_path: str) -> EchemData:
    """Load a single electrochemical CSV file into an :class:`EchemData` object.

    Args:
        file_path: Absolute or relative path to the CSV file.

    Returns:
        :class:`~src.common.types.EchemData` with ``data`` set to a
        :class:`~pandas.DataFrame`.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be parsed as CSV.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Echem file not found: {path}")

    technique = _technique_from_filename(path.stem)
    try:
        df = _read_csv_fallback(path, comment="#")
    except Exception as exc:
        raise ValueError(f"Cannot parse CSV '{path}': {exc}") from exc

    # Collect comment-line metadata (lines starting with '#')
    metadata: dict[str, Any] = {"source_file": str(path)}
    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        for line in raw_text.splitlines():
            line = line.strip()
            if not line.startswith("#"):
                break
            content = line.lstrip("#").strip()
            if ":" in content:
                k, _, v = content.partition(":")
                metadata[k.strip()] = v.strip()
    except Exception:
        pass

    return EchemData(
        technique=technique,
        data=df,
        file_path=str(path),
        points=len(df),
        metadata=metadata,
    )


def load_run_echem_files(run_dir: str) -> list[EchemData]:
    """Load all electrochemical CSV files from a run directory.

    Searches recursively for ``*.csv`` files and loads each as an
    :class:`EchemData`.  Files that fail to parse are silently skipped.

    Args:
        run_dir: Path to the experiment run directory.

    Returns:
        List of :class:`~src.common.types.EchemData` objects (may be empty).

    Raises:
        FileNotFoundError: If the run directory does not exist.
    """
    run_path = Path(run_dir).resolve()
    if not run_path.exists():
        raise FileNotFoundError(f"Run directory not found: {run_path}")

    results: list[EchemData] = []
    for csv_file in sorted(run_path.rglob("*.csv")):
        try:
            results.append(load_echem_file(str(csv_file)))
        except Exception:
            continue
    return results


def read_run_metadata(run_dir: str) -> dict[str, Any]:
    """Read all JSON metadata files from a run directory.

    Looks for ``run_summary.json``, ``experiment.json``, and ``params.json``.

    Args:
        run_dir: Path to the experiment run directory.

    Returns:
        Dict with keys ``run_summary``, ``experiment``, ``params``, ``run_dir``.

    Raises:
        FileNotFoundError: If the run directory does not exist.
    """
    run_path = Path(run_dir).resolve()
    if not run_path.exists():
        raise FileNotFoundError(f"Run directory not found: {run_path}")

    return {
        "run_dir": str(run_path),
        "run_summary": _load_json_safe(run_path / "run_summary.json"),
        "experiment": _load_json_safe(run_path / "experiment.json"),
        "params": _load_json_safe(run_path / "params.json"),
    }


def list_run_files(run_dir: str) -> dict[str, list[str]]:
    """List all files in a run directory grouped by extension.

    Args:
        run_dir: Path to the experiment run directory.

    Returns:
        Dict mapping lowercase extension (without dot) → sorted list of paths.

    Raises:
        FileNotFoundError: If the run directory does not exist.
    """
    run_path = Path(run_dir).resolve()
    if not run_path.exists():
        raise FileNotFoundError(f"Run directory not found: {run_path}")

    grouped: dict[str, list[str]] = {}
    for f in sorted(run_path.rglob("*")):
        if f.is_file():
            ext = f.suffix.lstrip(".").lower() or "no_ext"
            grouped.setdefault(ext, []).append(str(f))
    return grouped


# ── register with global registry on import ──────────────────────────────────

def _register() -> None:
    try:
        from src.common.tool_registry import registry

        registry.register(
            "load_echem_file",
            load_echem_file,
            "Load a single electrochemical CSV file into an EchemData object",
            {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to CSV file"},
                },
                "required": ["file_path"],
            },
        )
        registry.register(
            "load_run_echem_files",
            load_run_echem_files,
            "Load all electrochemical CSV files from a run directory",
            {
                "type": "object",
                "properties": {
                    "run_dir": {"type": "string", "description": "Path to run directory"},
                },
                "required": ["run_dir"],
            },
        )
        registry.register(
            "read_run_metadata",
            read_run_metadata,
            "Read all JSON metadata files (run_summary, experiment, params) from a run directory",
            {
                "type": "object",
                "properties": {
                    "run_dir": {"type": "string", "description": "Path to run directory"},
                },
                "required": ["run_dir"],
            },
        )
        registry.register(
            "list_run_files",
            list_run_files,
            "List all files in a run directory grouped by extension",
            {
                "type": "object",
                "properties": {
                    "run_dir": {"type": "string", "description": "Path to run directory"},
                },
                "required": ["run_dir"],
            },
        )
    except Exception:
        pass


_register()

"""Electrochemistry data readers for MicroHySeeker output layout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.config import DATA_ROOT

CV_REQUIRED_COLUMNS = {"Potential(V)", "Current(A)"}
CV_COLUMN_ALIASES = {
    "Potential(V)": ["Potential(V)", "Potential", "Potential/V", "Ewe/V"],
    "Current(A)": ["Current(A)", "Current", "Current/A", "I/A"],
}


def _read_csv_with_fallback(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def _resolve_run_dir(run_dir: str) -> Path:
    input_path = Path(run_dir)
    if input_path.is_absolute():
        return input_path

    data_relative = (DATA_ROOT / input_path).resolve()
    if data_relative.exists():
        return data_relative

    return input_path.resolve()


def _normalize_cv_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for target, aliases in CV_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                rename_map[alias] = target
                break
    return df.rename(columns=rename_map)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def read_cv_csv(path: str) -> pd.DataFrame:
    """Read a CV csv file and normalize expected columns."""
    csv_path = Path(path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"CV file not found: {csv_path}")

    df = _normalize_cv_columns(_read_csv_with_fallback(csv_path))
    missing = CV_REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CV csv missing required columns: {sorted(missing)}")
    return df


def read_eis_csv(path: str) -> pd.DataFrame:
    """Read an EIS csv file."""
    csv_path = Path(path).resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"EIS file not found: {csv_path}")
    return _read_csv_with_fallback(csv_path)


def read_experiment_dir(run_dir: str) -> dict[str, Any]:
    """Read experiment metadata and discovered data files for a run directory."""
    run_path = _resolve_run_dir(run_dir)
    if not run_path.exists():
        raise FileNotFoundError(f"run directory not found: {run_path}")
    if not run_path.is_dir():
        raise NotADirectoryError(f"run directory is not a directory: {run_path}")

    csv_files = sorted(run_path.rglob("*.csv"))
    cv_files = [file for file in csv_files if "cv" in file.name.lower()]
    eis_files = [file for file in csv_files if "eis" in file.name.lower()]

    experiment_meta = _load_json(run_path / "experiment.json")
    run_summary = _load_json(run_path / "run_summary.json")

    return {
        "run_dir": str(run_path),
        "metadata": {
            "experiment": experiment_meta,
            "run_summary": run_summary,
        },
        "files": {
            "csv": [str(file) for file in csv_files],
            "cv": [str(file) for file in cv_files],
            "eis": [str(file) for file in eis_files],
        },
        "counts": {
            "csv": len(csv_files),
            "cv": len(cv_files),
            "eis": len(eis_files),
        },
    }


def list_recent_experiments(n: int = 10) -> list[dict[str, Any]]:
    """List recent run directories under data/YYYY-MM-DD/YYYY-MM-DD_HH-MM-SS_*."""
    if n <= 0:
        return []
    if not DATA_ROOT.exists():
        return []

    runs: list[Path] = []
    for day_dir in DATA_ROOT.iterdir():
        if not day_dir.is_dir():
            continue
        for run_dir in day_dir.iterdir():
            if run_dir.is_dir():
                runs.append(run_dir)

    runs.sort(key=lambda path: path.name, reverse=True)

    results: list[dict[str, Any]] = []
    for run_dir in runs[:n]:
        csv_count = sum(1 for _ in run_dir.rglob("*.csv"))
        results.append(
            {
                "run_dir": str(run_dir),
                "day": run_dir.parent.name,
                "name": run_dir.name,
                "has_echem_dir": (run_dir / "echem").exists(),
                "csv_count": csv_count,
            }
        )
    return results


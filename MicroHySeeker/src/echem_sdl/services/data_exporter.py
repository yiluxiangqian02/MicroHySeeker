"""CSV/Excel export helper with optional async execution."""

from __future__ import annotations

import csv
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from .logger import LoggerService


class DataExporter:
    def __init__(
        self,
        export_dir: Path,
        logger: LoggerService | None = None,
        async_mode: bool = False,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self.export_dir = export_dir
        self._logger = logger
        self.async_mode = async_mode
        self.executor = executor

    def ensure_dir(self) -> None:
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_csv(self, data: list[tuple[float, float]], filename: str) -> Path:
        self.ensure_dir()
        path = self.export_dir / filename
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["x", "y"])
            for x, y in data:
                writer.writerow([x, y])
        if self._logger:
            self._logger.info(f"exported CSV: {path}")
        return path

    def export_excel(self, data: list[tuple[float, float]], filename: str) -> Path:
        try:
            import pandas as pd  # type: ignore
        except Exception:
            if self._logger:
                self._logger.warning("pandas not available, falling back to CSV")
            return self.export_csv(data, filename.replace(".xlsx", ".csv"))
        self.ensure_dir()
        path = self.export_dir / filename
        df = pd.DataFrame(data, columns=["x", "y"])
        df.to_excel(path, index=False)
        if self._logger:
            self._logger.info(f"exported Excel: {path}")
        return path

    def export_dict_list(self, rows: list[dict], filename: str) -> Path:
        self.ensure_dir()
        path = self.export_dir / filename
        headers = list(rows[0].keys()) if rows else []
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        if self._logger:
            self._logger.info(f"exported rows: {path}")
        return path

    def run_async(self, func: Callable[..., Path], *args, **kwargs) -> Future | Path:
        if not self.async_mode:
            return func(*args, **kwargs)
        if self.executor is None:
            self.executor = ThreadPoolExecutor(max_workers=2)
        return self.executor.submit(func, *args, **kwargs)

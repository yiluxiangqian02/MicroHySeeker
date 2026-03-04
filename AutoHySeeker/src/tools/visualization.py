"""Visualization tools for AutoHySeeker experiment data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.family"] = ["SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


def _save_and_close(fig: Any, save_path: str) -> str:
    """Save figure to PNG and close it."""
    out = Path(save_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(out), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out)


def plot_cv_curve(cv_data: pd.DataFrame, title: str, save_path: str) -> str:
    """Plot a CV curve (Potential vs Current) and save as PNG."""
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(
        cv_data["Potential(V)"],
        cv_data["Current(A)"] * 1e3,  # convert to mA
        color="steelblue",
        linewidth=1.5,
    )
    ax.set_xlabel("电位 / V")
    ax.set_ylabel("电流 / mA")
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.5)
    return _save_and_close(fig, save_path)


def plot_step_timeline(timeline: list[dict], save_path: str) -> str:
    """Plot step timeline as a horizontal Gantt chart and save as PNG."""
    # Collect start/end pairs keyed by source
    spans: dict[str, dict] = {}
    for event in timeline:
        src = event.get("source", "unknown")
        if event.get("event") == "start":
            spans.setdefault(src, {})["start"] = event.get("timestamp", "")
            spans[src]["status"] = event.get("status", "running")
        elif event.get("event") == "end":
            spans.setdefault(src, {})["end"] = event.get("timestamp", "")
            spans.setdefault(src, {})["duration_s"] = event.get("duration_s")
            spans[src]["status"] = event.get("status", "done")

    sources = list(spans.keys())
    fig, ax = plt.subplots(figsize=(10, max(3, len(sources) * 0.6 + 1)))

    for idx, src in enumerate(sources):
        info = spans[src]
        dur = info.get("duration_s") or 1.0
        color = "green" if info.get("status") == "done" else (
            "red" if info.get("status") == "failed" else "orange"
        )
        ax.barh(idx, dur, left=0, height=0.5, color=color, alpha=0.8)
        ax.text(dur + 0.1, idx, f"{dur:.1f}s", va="center", fontsize=8)

    ax.set_yticks(range(len(sources)))
    ax.set_yticklabels(sources, fontsize=8)
    ax.set_xlabel("耗时 / 秒")
    ax.set_title("实验步骤时间线")
    ax.grid(True, axis="x", linestyle="--", alpha=0.4)
    return _save_and_close(fig, save_path)


def plot_multi_cv_overlay(
    cv_files: list[str], labels: list[str], save_path: str
) -> str:
    """Overlay multiple CV curves for comparison and save as PNG."""
    if len(labels) < len(cv_files):
        labels = labels + [f"CV {i+1}" for i in range(len(labels), len(cv_files))]

    fig, ax = plt.subplots(figsize=(8, 6))
    for path, label in zip(cv_files, labels):
        try:
            from src.tools.echem_reader import read_cv_csv

            df = read_cv_csv(path)
            ax.plot(
                df["Potential(V)"],
                df["Current(A)"] * 1e3,
                label=label,
                linewidth=1.5,
            )
        except Exception as exc:
            ax.text(0.5, 0.5, f"读取失败: {exc}", transform=ax.transAxes, ha="center")

    ax.set_xlabel("电位 / V")
    ax.set_ylabel("电流 / mA")
    ax.set_title("CV 曲线叠加对比")
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, linestyle="--", alpha=0.5)
    return _save_and_close(fig, save_path)

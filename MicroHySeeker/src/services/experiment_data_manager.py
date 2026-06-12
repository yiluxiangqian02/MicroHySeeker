"""
实验数据管理服务 - ExperimentDataManager

负责：
- 按日期/实验创建目录结构
- 保存实验方案副本
- 记录运行日志（实验级）
- 保存运行结果摘要
- 保存电化学数据 (CSV)
- 保存电化学图表 (PNG)
- 记录泵操作时序
"""
import csv
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExperimentDataManager:
    """实验数据管理 — 每次实验运行一个实例"""

    PROTOCOL_VERSION = "2.0"
    SOFTWARE_VERSION = "1.0.0"

    def __init__(self, base_dir: str = "./data"):
        self._base_dir = Path(base_dir)
        self._run_dir: Optional[Path] = None
        self._run_id: Optional[str] = None
        self._log_file = None
        self._started_at: Optional[datetime] = None
        self._step_results: List[Dict[str, Any]] = []
        self._warnings: List[str] = []
        self._errors: List[str] = []
        self._warning_keys: set[str] = set()
        self._error_keys: set[str] = set()
        self._pump_ops: List[Dict[str, Any]] = []

    # ────────── 生命周期 ──────────

    def begin_run(self, exp_name: str, exp_dict: Dict[str, Any],
                  system_snapshot: Optional[Dict[str, Any]] = None,
                  operator: str = "") -> Path:
        """开始一次实验运行，创建目录结构并保存实验方案副本
        
        Args:
            exp_name: 实验名称
            exp_dict: 实验 dict（来自 Experiment.to_dict()）
            system_snapshot: 系统配置快照（可选）
            operator: 操作员
            
        Returns:
            Path: 本次运行数据目录
        """
        self._started_at = datetime.now()
        date_str = self._started_at.strftime("%Y-%m-%d")
        time_str = self._started_at.strftime("%Y-%m-%d_%H-%M-%S")

        # 清理实验名中的非法字符
        safe_name = self._safe_filename(exp_name)
        folder_name = f"{time_str}_{safe_name}"

        self._run_dir = self._base_dir / date_str / folder_name
        self._run_dir.mkdir(parents=True, exist_ok=True)
        (self._run_dir / "echem").mkdir(exist_ok=True)
        (self._run_dir / "pump").mkdir(exist_ok=True)

        self._run_id = f"run_{self._started_at.strftime('%Y%m%d_%H%M%S')}"
        self._step_results = []
        self._warnings = []
        self._errors = []
        self._warning_keys = set()
        self._error_keys = set()
        self._pump_ops = []

        # 保存实验方案副本
        exp_copy = dict(exp_dict)
        exp_copy["_protocol_version"] = self.PROTOCOL_VERSION
        exp_copy["_software_version"] = self.SOFTWARE_VERSION
        exp_copy["_created_at"] = exp_copy.get("_created_at",
                                               self._started_at.isoformat())
        self._write_json(self._run_dir / "experiment.json", exp_copy)

        # 系统快照
        self._system_snapshot = system_snapshot or {}
        self._operator = operator

        # 打开运行日志文件
        log_path = self._run_dir / "run_log.log"
        self._log_file = open(log_path, "w", encoding="utf-8")
        self._comm_log_path = None
        try:
            from src.services.app_logger import attach_run_comm_log
            self._comm_log_path = attach_run_comm_log(self._run_dir)
        except Exception as e:
            self._comm_log_path = None
            self._log("WARNING", "SYSTEM", f"通信日志绑定失败: {e}")
        self._log("INFO", "SYSTEM", f"实验开始: {exp_name}")
        self._log("INFO", "SYSTEM", f"运行目录: {self._run_dir}")

        return self._run_dir

    def end_run(self, success: bool) -> Path:
        """结束实验运行，写入 run_summary.json
        
        Returns:
            Path: run_summary.json 路径
        """
        finished_at = datetime.now()
        elapsed = (finished_at - self._started_at).total_seconds() if self._started_at else 0

        self._log("INFO", "SYSTEM",
                  f"实验{'成功完成' if success else '失败/中断'}, 耗时 {elapsed:.1f}s")

        # 写 run_summary
        summary = {
            "run_id": self._run_id,
            "exp_id": "",
            "exp_name": "",
            "started_at": self._started_at.isoformat() if self._started_at else "",
            "finished_at": finished_at.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "success": success,
            "operator": self._operator,
            "step_results": self._step_results,
            "system_snapshot": self._system_snapshot,
            "errors": self._errors,
            "warnings": self._warnings,
            "communication_log": "comm_log.log" if getattr(self, "_comm_log_path", None) else "",
        }

        # 从 experiment.json 补充 exp_id / exp_name
        exp_json_path = self._run_dir / "experiment.json"
        if exp_json_path.exists():
            try:
                exp_data = json.loads(exp_json_path.read_text(encoding="utf-8"))
                summary["exp_id"] = exp_data.get("exp_id", "")
                summary["exp_name"] = exp_data.get("exp_name", "")
            except Exception:
                pass

        summary_path = self._run_dir / "run_summary.json"
        self._write_json(summary_path, summary)

        # 保存泵操作记录
        if self._pump_ops:
            self._save_pump_ops()

        # 关闭日志文件
        try:
            from src.services.app_logger import detach_run_comm_log
            detach_run_comm_log()
        except Exception:
            pass
        if self._log_file:
            self._log_file.close()
            self._log_file = None

        return summary_path

    # ────────── 步骤记录 ──────────

    def step_started(self, step_index: int, step_id: str, step_type: str,
                     details: str = ""):
        """记录步骤开始"""
        self._log("INFO", "RUNNER", f"步骤{step_index} [{step_type}] 开始: {details}")
        self._step_results.append({
            "step_index": step_index,
            "step_id": step_id,
            "step_type": step_type,
            "started_at": datetime.now().isoformat(),
            "finished_at": "",
            "success": False,
            "details": details,
        })

    def step_finished(self, step_index: int, success: bool, details: str = "",
                      data_file: str = "", data_points_count: int = 0):
        """记录步骤结束"""
        result_text = "成功" if success else "失败"
        self._log("INFO", "RUNNER",
                  f"步骤{step_index} {result_text}" +
                  (f": {details}" if details else ""))

        # 更新对应的 step_result
        for sr in self._step_results:
            if sr["step_index"] == step_index:
                sr["finished_at"] = datetime.now().isoformat()
                sr["success"] = success
                if details:
                    sr["details"] = details
                if data_file:
                    sr["data_file"] = data_file
                if data_points_count > 0:
                    sr["data_points_count"] = data_points_count
                break

    # ────────── 日志 ──────────

    def log(self, level: str, source: str, message: str):
        """写入运行日志（外部调用入口）"""
        normalized = (level or "INFO").upper()
        self._log(normalized, source, message)
        if normalized == "WARNING":
            self._remember_issue(self._warnings, self._warning_keys, message)
        elif normalized in {"ERROR", "CRITICAL"}:
            self._remember_issue(self._errors, self._error_keys, message)

    def log_warning(self, message: str):
        """记录警告并追加到 warnings 列表"""
        self.log("WARNING", "RUNNER", message)

    def log_error(self, message: str):
        """记录错误并追加到 errors 列表"""
        self.log("ERROR", "RUNNER", message)

    @staticmethod
    def _remember_issue(bucket: List[str], dedup: set[str], message: str):
        if message not in dedup:
            dedup.add(message)
            bucket.append(message)

    def _log(self, level: str, source: str, message: str):
        """内部日志写入"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.") + \
             f"{datetime.now().microsecond // 1000:03d}"
        line = f"[{ts}] [{level}] [{source}] {message}"
        if self._log_file:
            self._log_file.write(line + "\n")
            self._log_file.flush()

    # ────────── 电化学数据 ──────────

    def save_echem_csv(self, step_index: int, technique: str,
                       data_points: List, headers: List[str],
                       ec_params: Optional[Dict[str, Any]] = None) -> str:
        """保存电化学原始数据为 CSV（含元数据注释头）
        
        Args:
            step_index: 步骤索引
            technique: 电化学技术 (CV/LSV/i-t/OCPT/EIS 等)
            data_points: 数据点列表
            headers: 列头
            ec_params: 电化学参数 dict（可选，写入 CSV 注释头）
            
        Returns:
            str: 相对路径 (如 "echem/step_3_CV.csv")
        """
        if not self._run_dir:
            return ""
        filename = f"step_{step_index}_{technique}.csv"
        filepath = self._run_dir / "echem" / filename

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                # 写入元数据注释头（# 前缀，AI 和 pandas 都可解析）
                f.write(f"# technique: {technique}\n")
                f.write(f"# step_index: {step_index}\n")
                f.write(f"# timestamp: {datetime.now().isoformat()}\n")
                f.write(f"# data_points: {len(data_points)}\n")
                if str(technique).upper() == "ADT":
                    f.write("# phase: 0=cathodic CP constant-current segment, "
                            "1=anodic CA constant-potential segment\n")
                if ec_params:
                    for key, val in ec_params.items():
                        if val is not None:
                            f.write(f"# param_{key}: {val}\n")
                
                writer = csv.writer(f)
                if headers:
                    writer.writerow(headers)
                for row in data_points:
                    if isinstance(row, (list, tuple)):
                        writer.writerow(row)
                    else:
                        writer.writerow([row])
            self._log("INFO", "DATA", f"电化学数据已保存: {filename} ({len(data_points)}点)")
            self._save_standard_echem_chart(step_index, technique, data_points, headers)
            if str(technique).upper() == "ADT":
                self._save_adt_charts(step_index, technique, data_points)
            self._save_pre_post_adt_comparisons()
            return f"echem/{filename}"
        except Exception as e:
            self._log("ERROR", "DATA", f"保存电化学数据失败: {e}")
            return ""

    def _save_standard_echem_chart(self, step_index: int, technique: str,
                                   data_points: List,
                                   headers: Optional[List[str]] = None) -> None:
        """Save Nature-style single-technique charts from numeric CSV data."""
        if not self._run_dir or not data_points:
            return

        try:
            import matplotlib
            matplotlib.use("Agg")
            import numpy as np
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg

            tech = self._normalize_tech_name(technique)
            if tech not in ("CV", "LSV", "I-T"):
                return

            arr = np.array(data_points, dtype=float)
            if arr.ndim != 2 or arr.shape[1] < 2:
                return

            series = self._standard_series_from_array(tech, arr, headers)
            if series is None:
                return
            x, y, xlabel, ylabel, title = series

            fig = Figure(figsize=(3.45, 2.75), dpi=300, facecolor="white")
            canvas = FigureCanvasAgg(fig)
            ax = fig.add_subplot(111)
            self._plot_nature_single_axis(ax, x, y, xlabel, ylabel, title)
            fig.tight_layout(pad=0.35)
            canvas.draw()
            out_path = self._run_dir / "echem" / f"step_{step_index}_{technique}.png"
            fig.savefig(out_path, facecolor="white", bbox_inches="tight")
            fig.clear()
        except Exception as e:
            self._log("WARNING", "DATA", f"标准电化学图生成失败: {e}")

    def _save_pre_post_adt_comparisons(self) -> None:
        """Generate CV/LSV/i-t comparison plots before and after each ADT."""
        if not self._run_dir:
            return
        echem_dir = self._run_dir / "echem"
        if not echem_dir.exists():
            return

        try:
            files = []
            pattern = re.compile(r"^step_(\d+)_(.+)\.csv$")
            for path in echem_dir.glob("step_*_*.csv"):
                match = pattern.match(path.name)
                if not match:
                    continue
                step_idx = int(match.group(1))
                tech = match.group(2)
                files.append((step_idx, self._normalize_tech_name(tech), path))

            adt_steps = sorted(idx for idx, tech, _ in files if tech == "ADT")
            if not adt_steps:
                return

            comparable = ("CV", "LSV", "I-T")
            for adt_idx in adt_steps:
                for tech in comparable:
                    before = [
                        (idx, path) for idx, t, path in files
                        if t == tech and idx < adt_idx
                    ]
                    after = [
                        (idx, path) for idx, t, path in files
                        if t == tech and idx > adt_idx
                    ]
                    if not before or not after:
                        continue

                    pre_idx, pre_path = max(before, key=lambda item: item[0])
                    post_idx, post_path = min(after, key=lambda item: item[0])
                    out_path = echem_dir / (
                        f"compare_{tech.replace('-', '')}_pre_step_{pre_idx}"
                        f"_post_step_{post_idx}_around_ADT_step_{adt_idx}.png"
                    )
                    self._save_single_comparison_chart(
                        tech, pre_idx, pre_path, post_idx, post_path,
                        adt_idx, out_path,
                    )
                self._save_summary_comparison_chart(adt_idx, files, echem_dir)
        except Exception as e:
            self._log("WARNING", "DATA", f"ADT 前后对比图生成失败: {e}")

    @staticmethod
    def _normalize_tech_name(technique: str) -> str:
        tech = str(technique).strip().upper()
        if tech in ("IT", "I_T", "I-T"):
            return "I-T"
        return tech

    def _save_single_comparison_chart(self, tech: str,
                                      pre_idx: int, pre_path: Path,
                                      post_idx: int, post_path: Path,
                                      adt_idx: int, out_path: Path) -> None:
        import matplotlib
        matplotlib.use("Agg")
        import numpy as np
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        series = self._comparison_series(tech, pre_path, post_path)
        if series is None:
            return
        x_pre, y_pre, x_post, y_post, xlabel, ylabel, title = series

        fig = Figure(figsize=(3.45, 2.75), dpi=300, facecolor="white")
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        self._plot_nature_comparison_axis(
            ax, x_pre, y_pre, x_post, y_post,
            xlabel, ylabel, title,
            f"Before ADT (step {pre_idx})",
            f"After ADT (step {post_idx})",
        )
        fig.tight_layout(pad=0.35)
        canvas.draw()
        fig.savefig(out_path, facecolor="white", bbox_inches="tight")
        fig.clear()

    def _save_summary_comparison_chart(self, adt_idx: int, files: List,
                                       echem_dir: Path) -> None:
        """Save a wide CV/LSV/i-t comparison summary around one ADT step."""
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        panels = []
        for tech in ("CV", "LSV", "I-T"):
            before = [
                (idx, path) for idx, t, path in files
                if t == tech and idx < adt_idx
            ]
            after = [
                (idx, path) for idx, t, path in files
                if t == tech and idx > adt_idx
            ]
            if not before or not after:
                continue

            pre_idx, pre_path = max(before, key=lambda item: item[0])
            post_idx, post_path = min(after, key=lambda item: item[0])
            series = self._comparison_series(tech, pre_path, post_path)
            if series is not None:
                panels.append((series, pre_idx, post_idx))

        if not panels:
            return

        fig = Figure(figsize=(10.6, 3.15), dpi=300, facecolor="white",
                     constrained_layout=True)
        canvas = FigureCanvasAgg(fig)
        axes = fig.subplots(1, len(panels), squeeze=False)[0]
        for ax, (series, pre_idx, post_idx) in zip(axes, panels):
            x_pre, y_pre, x_post, y_post, xlabel, ylabel, title = series
            self._plot_nature_comparison_axis(
                ax, x_pre, y_pre, x_post, y_post,
                xlabel, ylabel, title,
                f"Before ADT (step {pre_idx})",
                f"After ADT (step {post_idx})",
                show_legend=(title == "CV"),
            )

        canvas.draw()
        out_path = echem_dir / f"compare_summary_around_ADT_step_{adt_idx}.png"
        fig.savefig(out_path, facecolor="white")
        fig.clear()

    def _comparison_series(self, tech: str, pre_path: Path, post_path: Path):
        import numpy as np

        pre_headers, pre_data = self._read_echem_csv_numeric(pre_path)
        post_headers, post_data = self._read_echem_csv_numeric(post_path)
        if not pre_data or not post_data:
            return None

        pre = np.array(pre_data, dtype=float)
        post = np.array(post_data, dtype=float)
        if pre.ndim != 2 or post.ndim != 2 or pre.shape[1] < 2 or post.shape[1] < 2:
            return None

        pre_series = self._standard_series_from_array(tech, pre, pre_headers)
        post_series = self._standard_series_from_array(tech, post, post_headers)
        if pre_series is None or post_series is None:
            return None

        x_pre, y_pre, xlabel, ylabel, title = pre_series
        x_post, y_post, _, _, _ = post_series
        return x_pre, y_pre, x_post, y_post, xlabel, ylabel, title

    @staticmethod
    def _standard_series_from_array(tech: str, arr, headers: Optional[List[str]] = None):
        """Return x/y data using headers when available, with legacy fallbacks."""
        import numpy as np

        def _find_col(candidates):
            if not headers:
                return None
            lowered = [str(h).strip().lower() for h in headers]
            for idx, name in enumerate(lowered):
                if any(token in name for token in candidates):
                    return idx
            return None

        current_col = _find_col(("current", "i/"))
        if tech in ("CV", "LSV"):
            x_col = _find_col(("potential", "e/"))
            if x_col is None or current_col is None:
                if arr.shape[1] >= 3:
                    x_col, current_col = 1, 2
                else:
                    x_col, current_col = 0, 1
            title = tech
            xlabel = "Potential (V)"
        elif tech == "I-T":
            x_col = _find_col(("time", "t/"))
            if x_col is None or current_col is None:
                if arr.shape[1] >= 3:
                    x_col, current_col = 0, 2
                else:
                    x_col, current_col = 0, 1
            title = "i-t"
            xlabel = "Time (s)"
        else:
            return None

        if x_col >= arr.shape[1] or current_col >= arr.shape[1]:
            return None
        x = arr[:, x_col]
        y = arr[:, current_col] * 1000.0
        finite = np.isfinite(x) & np.isfinite(y)
        if not finite.any():
            return None
        return x[finite], y[finite], xlabel, "Current (mA)", title

    @staticmethod
    def _plot_nature_comparison_axis(ax, x_pre, y_pre, x_post, y_post,
                                     xlabel: str, ylabel: str, title: str,
                                     pre_label: str, post_label: str,
                                     show_legend: bool = True,
                                     panel_label: Optional[str] = None) -> None:
        import numpy as np

        blue = "#7DB7D6"
        red = "#D96B63"
        dark = "#222222"

        def markevery(x):
            return max(1, len(x) // 28)

        ax.plot(
            x_pre, y_pre,
            color=blue, linewidth=0.9,
            marker="o", markevery=markevery(x_pre), markersize=2.6,
            markerfacecolor="white", markeredgewidth=0.65,
            label=pre_label,
        )
        ax.plot(
            x_post, y_post,
            color=red, linewidth=0.9,
            marker="o", markevery=markevery(x_post), markersize=2.6,
            markerfacecolor="white", markeredgewidth=0.65,
            label=post_label,
        )

        ax.set_title(title, fontsize=7.5, pad=3.0)
        ax.set_xlabel(xlabel, fontsize=7.0, labelpad=2.0)
        ax.set_ylabel(ylabel, fontsize=7.0, labelpad=2.0)
        ax.tick_params(axis="both", which="major", labelsize=6.2,
                       width=0.6, length=2.8, direction="out", pad=1.5)
        ax.tick_params(axis="both", which="minor", width=0.45,
                       length=1.6, direction="out")
        ax.minorticks_on()
        ax.grid(False)

        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_linewidth(0.7)
            ax.spines[side].set_color(dark)

        if show_legend:
            ax.legend(
                frameon=False, fontsize=5.9, loc="best",
                handlelength=1.4, borderaxespad=0.2, labelspacing=0.3,
            )

        if panel_label:
            ax.text(
                -0.23, 1.10, panel_label,
                transform=ax.transAxes, fontsize=9.0,
                fontweight="bold", va="top", ha="left",
            )

        all_y = np.concatenate([np.asarray(y_pre), np.asarray(y_post)])
        finite_y = all_y[np.isfinite(all_y)]
        if finite_y.size:
            y_min, y_max = float(np.min(finite_y)), float(np.max(finite_y))
            pad = max(abs(y_max - y_min) * 0.08, 0.5)
            ax.set_ylim(y_min - pad, y_max + pad)

    @staticmethod
    def _plot_nature_single_axis(ax, x, y, xlabel: str,
                                 ylabel: str, title: str) -> None:
        import numpy as np

        blue = "#7DB7D6"
        dark = "#222222"

        mark_step = max(1, len(x) // 34)
        ax.plot(
            x, y,
            color=blue, linewidth=0.9,
            marker="o", markevery=mark_step, markersize=2.5,
            markerfacecolor="white", markeredgewidth=0.65,
        )

        ax.set_title(title, fontsize=7.5, pad=3.0)
        ax.set_xlabel(xlabel, fontsize=7.0, labelpad=2.0)
        ax.set_ylabel(ylabel, fontsize=7.0, labelpad=2.0)
        ax.tick_params(axis="both", which="major", labelsize=6.2,
                       width=0.6, length=2.8, direction="out", pad=1.5)
        ax.tick_params(axis="both", which="minor", width=0.45,
                       length=1.6, direction="out")
        ax.minorticks_on()
        ax.grid(False)

        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_linewidth(0.7)
            ax.spines[side].set_color(dark)

        finite_y = np.asarray(y)[np.isfinite(y)]
        if finite_y.size:
            y_min, y_max = float(np.min(finite_y)), float(np.max(finite_y))
            pad = max(abs(y_max - y_min) * 0.08, 0.5)
            ax.set_ylim(y_min - pad, y_max + pad)

    @staticmethod
    def _read_echem_csv_numeric(path: Path) -> tuple[List[str], List[List[float]]]:
        headers: List[str] = []
        rows: List[List[float]] = []
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(line for line in f if line.strip() and not line.startswith("#"))
            for row in reader:
                if not headers:
                    headers = [cell.strip() for cell in row]
                    continue
                try:
                    rows.append([float(cell) for cell in row if cell != ""])
                except ValueError:
                    continue
        return headers, rows

    def _save_adt_charts(self, step_index: int, technique: str,
                         data_points: List) -> None:
        """Save ADT programmed-waveform and measured-response charts."""
        if not self._run_dir or not data_points:
            return

        try:
            import matplotlib
            matplotlib.use("Agg")
            import numpy as np

            arr = np.array(data_points, dtype=float)
            if arr.ndim != 2 or arr.shape[1] < 4:
                return

            t = arr[:, 0]
            potential = arr[:, 1]
            current = arr[:, 2]
            if arr.shape[1] >= 5:
                phase = arr[:, 4]
                cp_mask = phase == 0
                ca_mask = phase == 1
            else:
                cp_mask = np.abs(current) == np.nanmax(np.abs(current))
                ca_mask = ~cp_mask

            if arr.shape[1] >= 7:
                set_current = arr[:, 5]
                set_potential = arr[:, 6]
            else:
                set_current = np.where(cp_mask, current, np.nan)
                set_potential = np.where(ca_mask, potential, np.nan)

            out_dir = self._run_dir / "echem"
            self._save_adt_program_chart(
                out_dir / f"step_{step_index}_{technique}_program.png",
                t, set_current, set_potential,
            )
            self._save_adt_response_chart(
                out_dir / f"step_{step_index}_{technique}.png",
                t, potential, current, cp_mask, ca_mask,
            )
            self._save_adt_response_chart(
                out_dir / f"step_{step_index}_{technique}_response.png",
                t, potential, current, cp_mask, ca_mask,
            )
        except Exception as e:
            self._log("WARNING", "DATA", f"ADT chart generation failed: {e}")

    def _save_adt_program_chart(self, path: Path, t, set_current,
                                set_potential) -> None:
        import numpy as np
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        red = "#D96B63"
        blue = "#7DB7D6"
        dark = "#222222"

        fig = Figure(figsize=(8.2, 2.7), dpi=300, facecolor="white")
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)

        def _plot_finite_segments(ax, x, y, **kwargs):
            finite = np.isfinite(y)
            start = None
            for idx, ok in enumerate(finite):
                if ok and start is None:
                    start = idx
                if start is not None and (not ok or idx == len(finite) - 1):
                    end = idx if not ok else idx + 1
                    if end - start > 0:
                        ax.plot(x[start:end], y[start:end], **kwargs)
                    start = None

        current_level = np.where(np.isfinite(set_current), -1.0, np.nan)
        potential_level = np.where(np.isfinite(set_potential), 1.0, np.nan)
        _plot_finite_segments(
            ax, t, current_level,
            color=red, linewidth=0.95, drawstyle="steps-post",
        )
        _plot_finite_segments(
            ax, t, potential_level,
            color=blue, linewidth=0.95, drawstyle="steps-post",
        )
        ax.axhline(0, color=dark, linewidth=0.65, alpha=0.65)
        ax.set_title("ADT program", fontsize=7.8, pad=3.0)
        ax.set_xlabel("Time (s)", fontsize=7.0, labelpad=2.0)
        ax.set_ylim(-1.35, 1.35)
        current_label = "CP current"
        potential_label = "CA potential"
        if np.isfinite(set_current).any():
            current_mA = float(np.nanmedian(set_current[np.isfinite(set_current)]) * 1000.0)
            current_label = f"{current_mA:g} mA CP"
        if np.isfinite(set_potential).any():
            potential_v = float(np.nanmedian(set_potential[np.isfinite(set_potential)]))
            potential_label = f"{potential_v:g} V CA"
        ax.set_yticks([-1, 0, 1])
        ax.set_yticklabels([current_label, "0", potential_label])
        ax.tick_params(axis="both", which="major", labelsize=6.2,
                       width=0.6, length=2.8, direction="out", pad=1.5)
        ax.grid(False)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_linewidth(0.7)
            ax.spines[side].set_color(dark)
        fig.tight_layout(pad=0.35)
        canvas.draw()
        fig.savefig(path, facecolor="white", bbox_inches="tight")
        fig.clear()

    def _save_adt_response_chart(self, path: Path, t, potential, current,
                                 cp_mask, ca_mask) -> None:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        red = "#D96B63"
        blue = "#7DB7D6"
        dark = "#222222"

        fig = Figure(figsize=(8.2, 2.7), dpi=300, facecolor="white")
        canvas = FigureCanvasAgg(fig)
        ax_i = fig.add_subplot(111)
        ax_e = ax_i.twinx()

        def _plot_masked_segments(ax, x, y, mask, **kwargs):
            start = None
            for idx, ok in enumerate(mask):
                if ok and start is None:
                    start = idx
                if start is not None and (not ok or idx == len(mask) - 1):
                    end = idx if not ok else idx + 1
                    if end - start > 1:
                        ax.plot(x[start:end], y[start:end], **kwargs)
                    elif end - start == 1:
                        ax.scatter(x[start:end], y[start:end], s=8,
                                   color=kwargs.get("color"))
                    start = None

        _plot_masked_segments(
            ax_i, t, current * 1000.0, ca_mask,
            color=red, linewidth=0.75,
        )
        _plot_masked_segments(
            ax_e, t, potential, cp_mask,
            color=blue, linewidth=0.75,
        )

        ax_i.axhline(0, color=dark, linewidth=0.65, alpha=0.65)
        ax_i.set_title("ADT response", fontsize=7.8, pad=3.0)
        ax_i.set_xlabel("Time (s)", fontsize=7.0, labelpad=2.0)
        ax_i.set_ylabel("Current (mA)", color=red, fontsize=7.0, labelpad=2.0)
        ax_e.set_ylabel("Potential (V)", color=blue, fontsize=7.0, labelpad=2.0)
        ax_i.tick_params(axis="both", which="major", labelsize=6.2,
                         width=0.6, length=2.8, direction="out", pad=1.5)
        ax_e.tick_params(axis="y", which="major", labelsize=6.2,
                         width=0.6, length=2.8, direction="out", pad=1.5)
        ax_i.tick_params(axis="y", colors=red)
        ax_e.tick_params(axis="y", colors=blue)
        ax_i.grid(False)
        ax_i.spines["top"].set_visible(False)
        ax_e.spines["top"].set_visible(False)
        ax_i.spines["left"].set_color(red)
        ax_e.spines["right"].set_color(blue)
        ax_i.spines["bottom"].set_color(dark)
        ax_i.spines["left"].set_linewidth(0.7)
        ax_i.spines["bottom"].set_linewidth(0.7)
        ax_e.spines["right"].set_linewidth(0.7)
        self._align_twin_zero(ax_i, ax_e)

        fig.tight_layout(pad=0.35)
        canvas.draw()
        fig.savefig(path, facecolor="white", bbox_inches="tight")
        fig.clear()

    def _align_twin_zero(self, ax_left, ax_right) -> None:
        """Force 0 on twin y axes to share the same screen position."""
        left_min, left_max = ax_left.get_ylim()
        right_min, right_max = ax_right.get_ylim()

        left_span = max(abs(left_min), abs(left_max), 1e-12)
        right_span = max(abs(right_min), abs(right_max), 1e-12)

        ax_left.set_ylim(-left_span, left_span)
        ax_right.set_ylim(-right_span, right_span)

    def save_echem_chart(self, step_index: int, technique: str,
                         pixmap) -> str:
        """保存电化学图表为 PNG
        
        Args:
            pixmap: QPixmap 对象
            
        Returns:
            str: 相对路径
        """
        if not self._run_dir or pixmap is None:
            return ""
        filename = f"step_{step_index}_{technique}.png"
        filepath = self._run_dir / "echem" / filename
        if filepath.exists() and self._normalize_tech_name(technique) in ("CV", "LSV", "I-T", "ADT"):
            return f"echem/{filename}"
        
        try:
            pixmap.save(str(filepath), "PNG")
            self._log("INFO", "DATA", f"电化学图表已保存: {filename}")
            return f"echem/{filename}"
        except Exception as e:
            self._log("ERROR", "DATA", f"保存电化学图表失败: {e}")
            return ""

    # ────────── 泵操作记录 ──────────

    def save_prep_sol_result(self, step_index: int,
                              total_volume_ul: float,
                              volumes: Dict[str, float],
                              concentrations: Dict[str, float],
                              injection_order: List[str],
                              solvent_flags: Optional[Dict[str, bool]] = None) -> str:
        """保存配液结果为 JSON（目标浓度、实际注入体积、计算过程）
        
        Args:
            step_index: 步骤索引
            total_volume_ul: 总体积 (μL)
            volumes: {溶液名: 注入体积(μL)}
            concentrations: {溶液名: 目标浓度(M)}
            injection_order: 注入顺序
            solvent_flags: {溶液名: 是否为溶剂}
            
        Returns:
            str: 相对路径
        """
        if not self._run_dir:
            return ""
        filename = f"step_{step_index}_prep_sol.json"
        filepath = self._run_dir / filename

        result = {
            "step_index": step_index,
            "timestamp": datetime.now().isoformat(),
            "total_volume_ul": round(total_volume_ul, 2),
            "injection_order": injection_order,
            "solutions": {},
        }
        for sol_name in injection_order:
            vol = volumes.get(sol_name, 0)
            conc = concentrations.get(sol_name, 0)
            is_solvent = (solvent_flags or {}).get(sol_name, False)
            if vol > 0:
                result["solutions"][sol_name] = {
                    "volume_ul": round(vol, 2),
                    "target_concentration_M": round(conc, 6) if not is_solvent else None,
                    "is_solvent": is_solvent,
                    "volume_fraction": round(vol / total_volume_ul, 4) if total_volume_ul > 0 else 0,
                }

        try:
            self._write_json(filepath, result)
            self._log("INFO", "DATA", f"配液结果已保存: {filename}")
            return filename
        except Exception as e:
            self._log("ERROR", "DATA", f"保存配液结果失败: {e}")
            return ""

    def record_pump_op(self, pump_addr: int, operation: str,
                       direction: str = "", rpm: int = 0,
                       volume_ul: float = 0, duration_s: float = 0,
                       mode: str = "speed", encoder_counts: int = 0):
        """记录一次泵操作"""
        self._pump_ops.append({
            "timestamp": datetime.now().isoformat(),
            "pump_addr": pump_addr,
            "operation": operation,  # start / stop / position_move
            "direction": direction,
            "rpm": rpm,
            "volume_ul": round(volume_ul, 2),
            "duration_s": round(duration_s, 2),
            "mode": mode,
            "encoder_counts": encoder_counts,
        })

    def _save_pump_ops(self):
        """保存泵操作记录为 CSV"""
        if not self._run_dir or not self._pump_ops:
            return
        filepath = self._run_dir / "pump" / "pump_operations.csv"
        try:
            fields = ["timestamp", "pump_addr", "operation", "direction",
                      "rpm", "volume_ul", "duration_s", "mode", "encoder_counts"]
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(self._pump_ops)
            self._log("INFO", "DATA",
                      f"泵操作记录已保存: {len(self._pump_ops)} 条")
        except Exception as e:
            self._log("ERROR", "DATA", f"保存泵操作记录失败: {e}")

    # ────────── 工具方法 ──────────

    @property
    def run_dir(self) -> Optional[Path]:
        return self._run_dir

    @staticmethod
    def _safe_filename(name: str, max_len: int = 40) -> str:
        """清理文件名中的非法字符"""
        import re
        safe = re.sub(r'[<>:"/\\|?*]', '_', name)
        safe = safe.strip('. ')
        return safe[:max_len] if safe else "unnamed"

    @staticmethod
    def _write_json(path: Path, data: dict):
        """写入 JSON 文件"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def list_runs(base_dir: str = "./data",
                  date_filter: str = "") -> List[Dict[str, Any]]:
        """列出所有实验运行记录
        
        Args:
            base_dir: 数据根目录
            date_filter: 日期过滤 (如 "2026-02-13")，空字符串不过滤
            
        Returns:
            List[dict]: 每项包含 run_dir, exp_name, started_at, success 等
        """
        base = Path(base_dir)
        if not base.exists():
            return []

        runs = []
        date_dirs = sorted(base.iterdir()) if not date_filter else [base / date_filter]

        for date_dir in date_dirs:
            if not date_dir.is_dir():
                continue
            for run_dir in sorted(date_dir.iterdir()):
                if not run_dir.is_dir():
                    continue
                summary_file = run_dir / "run_summary.json"
                if summary_file.exists():
                    try:
                        summary = json.loads(summary_file.read_text(encoding="utf-8"))
                        runs.append({
                            "run_dir": str(run_dir),
                            "exp_name": summary.get("exp_name", ""),
                            "started_at": summary.get("started_at", ""),
                            "elapsed_seconds": summary.get("elapsed_seconds", 0),
                            "success": summary.get("success", False),
                            "step_count": len(summary.get("step_results", [])),
                            "errors": summary.get("errors", []),
                        })
                    except Exception:
                        runs.append({
                            "run_dir": str(run_dir),
                            "exp_name": run_dir.name,
                            "started_at": "",
                            "success": None,
                        })
                else:
                    # 没有 summary 表示运行中或异常中断
                    runs.append({
                        "run_dir": str(run_dir),
                        "exp_name": run_dir.name,
                        "started_at": "",
                        "success": None,
                    })

        return runs

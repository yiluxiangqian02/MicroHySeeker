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
        self._log(level, source, message)

    def log_warning(self, message: str):
        """记录警告并追加到 warnings 列表"""
        self._log("WARNING", "RUNNER", message)
        self._warnings.append(message)

    def log_error(self, message: str):
        """记录错误并追加到 errors 列表"""
        self._log("ERROR", "RUNNER", message)
        self._errors.append(message)

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
            return f"echem/{filename}"
        except Exception as e:
            self._log("ERROR", "DATA", f"保存电化学数据失败: {e}")
            return ""

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

"""
实验数据浏览器 — 查看、管理、分析已完成的实验运行数据

功能：
- 按日期/名称/状态浏览所有实验运行记录
- 查看运行摘要、步骤结果、日志
- 打开电化学数据 CSV / 图表 PNG
- 打开实验数据目录
- 删除/导出运行记录
"""
import csv
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QPushButton, QLabel, QComboBox,
    QGroupBox, QGridLayout, QMessageBox, QFileDialog,
    QTabWidget, QWidget, QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPixmap

from src.services.experiment_data_manager import ExperimentDataManager

FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)


class DataBrowserDialog(QDialog):
    """实验数据浏览器对话框"""
    
    def __init__(self, data_dir: str = "./data", parent=None):
        super().__init__(parent)
        self.data_dir = data_dir
        self._runs: List[Dict[str, Any]] = []
        self._current_run: Optional[Dict[str, Any]] = None
        
        self.setWindowTitle("实验数据浏览器")
        self.setGeometry(100, 60, 1400, 800)
        self.setFont(FONT_NORMAL)
        self._init_ui()
        self._refresh_runs()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # ── 顶部工具栏 ──
        toolbar = QHBoxLayout()
        
        toolbar.addWidget(QLabel("日期筛选:"))
        self.date_filter = QComboBox()
        self.date_filter.setFont(FONT_NORMAL)
        self.date_filter.setMinimumWidth(150)
        self.date_filter.addItem("全部日期", "")
        self.date_filter.currentIndexChanged.connect(self._refresh_runs)
        toolbar.addWidget(self.date_filter)
        
        toolbar.addWidget(QLabel("状态:"))
        self.status_filter = QComboBox()
        self.status_filter.setFont(FONT_NORMAL)
        self.status_filter.addItems(["全部", "成功", "失败", "中断"])
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        toolbar.addWidget(self.status_filter)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_runs)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # ── 主分栏 ──
        splitter = QSplitter(Qt.Horizontal)
        
        # 左：运行记录列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = QLabel("实验运行记录")
        list_label.setFont(FONT_TITLE)
        left_layout.addWidget(list_label)
        
        self.run_table = QTableWidget()
        self.run_table.setFont(FONT_NORMAL)
        self.run_table.setColumnCount(5)
        self.run_table.setHorizontalHeaderLabels(
            ["时间", "实验名称", "状态", "耗时", "步骤数"]
        )
        self.run_table.horizontalHeader().setStretchLastSection(True)
        self.run_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.run_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.run_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.run_table.setSelectionMode(QTableWidget.SingleSelection)
        self.run_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.run_table.setAlternatingRowColors(True)
        self.run_table.currentCellChanged.connect(self._on_run_selected)
        left_layout.addWidget(self.run_table)
        
        # 列表按钮
        list_btn_layout = QHBoxLayout()
        
        open_dir_btn = QPushButton("打开目录")
        open_dir_btn.clicked.connect(self._on_open_dir)
        list_btn_layout.addWidget(open_dir_btn)
        
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._on_export)
        list_btn_layout.addWidget(export_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("color: #f44336;")
        delete_btn.clicked.connect(self._on_delete)
        list_btn_layout.addWidget(delete_btn)
        
        list_btn_layout.addStretch()
        left_layout.addLayout(list_btn_layout)
        
        splitter.addWidget(left_widget)
        
        # 右：详情面板（Tab页）
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setFont(FONT_NORMAL)
        
        # Tab1: 运行摘要
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(FONT_NORMAL)
        self.detail_tabs.addTab(self.summary_text, "运行摘要")
        
        # Tab2: 运行日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.detail_tabs.addTab(self.log_text, "运行日志")
        
        # Tab3: 电化学数据
        self.echem_widget = QWidget()
        echem_layout = QVBoxLayout(self.echem_widget)
        
        self.echem_files_label = QLabel("电化学数据文件:")
        echem_layout.addWidget(self.echem_files_label)
        
        self.echem_table = QTableWidget()
        self.echem_table.setFont(FONT_NORMAL)
        self.echem_table.setColumnCount(4)
        self.echem_table.setHorizontalHeaderLabels(["文件", "技术", "数据点数", "操作"])
        self.echem_table.horizontalHeader().setStretchLastSection(True)
        self.echem_table.setEditTriggers(QTableWidget.NoEditTriggers)
        echem_layout.addWidget(self.echem_table)
        
        self.echem_preview = QLabel()
        self.echem_preview.setAlignment(Qt.AlignCenter)
        self.echem_preview.setMinimumHeight(200)
        self.echem_preview.setStyleSheet("border: 1px solid #ddd; background: white;")
        echem_layout.addWidget(self.echem_preview)
        
        self.detail_tabs.addTab(self.echem_widget, "电化学数据")
        
        # Tab4: 实验方案
        self.experiment_text = QTextEdit()
        self.experiment_text.setReadOnly(True)
        self.experiment_text.setFont(QFont("Consolas", 10))
        self.detail_tabs.addTab(self.experiment_text, "实验方案")
        
        splitter.addWidget(self.detail_tabs)
        splitter.setSizes([500, 900])
        
        layout.addWidget(splitter)
        
        # ── 底部状态栏 ──
        self.status_label = QLabel("就绪")
        self.status_label.setFont(FONT_NORMAL)
        layout.addWidget(self.status_label)
    
    def _refresh_runs(self):
        """刷新运行记录列表"""
        # 更新日期筛选器
        date_filter_value = self.date_filter.currentData() or ""
        
        # 枚举所有日期目录
        base = Path(self.data_dir)
        if base.exists():
            dates = sorted(
                [d.name for d in base.iterdir() if d.is_dir()],
                reverse=True
            )
            # 更新下拉但保持选中
            current_text = self.date_filter.currentText()
            self.date_filter.blockSignals(True)
            self.date_filter.clear()
            self.date_filter.addItem("全部日期", "")
            for d in dates:
                self.date_filter.addItem(d, d)
            # 恢复选中
            idx = self.date_filter.findText(current_text)
            if idx >= 0:
                self.date_filter.setCurrentIndex(idx)
            self.date_filter.blockSignals(False)
            date_filter_value = self.date_filter.currentData() or ""
        
        self._runs = ExperimentDataManager.list_runs(
            self.data_dir, date_filter=date_filter_value
        )
        self._apply_filter()
    
    def _apply_filter(self):
        """应用状态筛选"""
        status_text = self.status_filter.currentText()
        
        filtered = []
        for run in self._runs:
            success = run.get("success")
            if status_text == "成功" and success is not True:
                continue
            if status_text == "失败" and success is not False:
                continue
            if status_text == "中断" and success is not None:
                continue
            filtered.append(run)
        
        self._populate_table(filtered)
        self.status_label.setText(f"共 {len(filtered)} 条记录（总计 {len(self._runs)} 条）")
    
    def _populate_table(self, runs: List[Dict]):
        """填充表格"""
        self.run_table.setRowCount(len(runs))
        
        for i, run in enumerate(runs):
            # 时间
            started = run.get("started_at", "")
            if started:
                try:
                    dt = datetime.fromisoformat(started)
                    time_str = dt.strftime("%m-%d %H:%M:%S")
                except Exception:
                    time_str = started[:19]
            else:
                time_str = "—"
            
            time_item = QTableWidgetItem(time_str)
            time_item.setData(Qt.UserRole, run)  # 存储完整数据
            self.run_table.setItem(i, 0, time_item)
            
            # 实验名称
            self.run_table.setItem(i, 1, QTableWidgetItem(
                run.get("exp_name", "—")
            ))
            
            # 状态
            success = run.get("success")
            if success is True:
                status_item = QTableWidgetItem("✅ 成功")
                status_item.setForeground(QColor("#4CAF50"))
            elif success is False:
                status_item = QTableWidgetItem("❌ 失败")
                status_item.setForeground(QColor("#f44336"))
            else:
                status_item = QTableWidgetItem("⚠ 中断")
                status_item.setForeground(QColor("#FF9800"))
            self.run_table.setItem(i, 2, status_item)
            
            # 耗时
            elapsed = run.get("elapsed_seconds", 0)
            if elapsed > 0:
                if elapsed < 60:
                    elapsed_str = f"{elapsed:.1f}s"
                elif elapsed < 3600:
                    elapsed_str = f"{elapsed/60:.1f}min"
                else:
                    elapsed_str = f"{elapsed/3600:.1f}hr"
            else:
                elapsed_str = "—"
            self.run_table.setItem(i, 3, QTableWidgetItem(elapsed_str))
            
            # 步骤数
            self.run_table.setItem(i, 4, QTableWidgetItem(
                str(run.get("step_count", "—"))
            ))
    
    def _on_run_selected(self, row: int, col: int, prev_row: int, prev_col: int):
        """选中某条运行记录"""
        if row < 0:
            return
        item = self.run_table.item(row, 0)
        if not item:
            return
        run = item.data(Qt.UserRole)
        if not run:
            return
        
        self._current_run = run
        run_dir = Path(run["run_dir"])
        
        # ── 加载摘要 ──
        summary_file = run_dir / "run_summary.json"
        if summary_file.exists():
            try:
                summary = json.loads(summary_file.read_text(encoding="utf-8"))
                self._display_summary(summary)
            except Exception as e:
                self.summary_text.setPlainText(f"读取摘要失败: {e}")
        else:
            self.summary_text.setPlainText("无运行摘要（实验可能正在运行或异常中断）")
        
        # ── 加载日志 ──
        log_file = run_dir / "run_log.log"
        if log_file.exists():
            try:
                content = log_file.read_text(encoding="utf-8")
                self.log_text.setPlainText(content)
            except Exception:
                self.log_text.setPlainText("读取日志失败")
        else:
            self.log_text.setPlainText("无运行日志")
        
        # ── 加载电化学数据 ──
        self._load_echem_files(run_dir)
        
        # ── 加载实验方案 ──
        exp_file = run_dir / "experiment.json"
        if exp_file.exists():
            try:
                content = exp_file.read_text(encoding="utf-8")
                # 格式化显示
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                self.experiment_text.setPlainText(formatted)
            except Exception:
                self.experiment_text.setPlainText("读取实验方案失败")
        else:
            self.experiment_text.setPlainText("无实验方案文件")
    
    def _display_summary(self, summary: dict):
        """格式化显示运行摘要"""
        lines = []
        
        lines.append(f"═══ 实验运行摘要 ═══")
        lines.append(f"")
        lines.append(f"运行ID:   {summary.get('run_id', '—')}")
        lines.append(f"实验名称: {summary.get('exp_name', '—')}")
        lines.append(f"操作员:   {summary.get('operator', '—')}")
        lines.append(f"")
        lines.append(f"开始时间: {summary.get('started_at', '—')}")
        lines.append(f"结束时间: {summary.get('finished_at', '—')}")
        
        elapsed = summary.get("elapsed_seconds", 0)
        if elapsed > 60:
            lines.append(f"总耗时:   {elapsed:.1f}s ({elapsed/60:.1f}min)")
        else:
            lines.append(f"总耗时:   {elapsed:.1f}s")
        
        status = "✅ 成功" if summary.get("success") else "❌ 失败"
        lines.append(f"结果:     {status}")
        
        # 步骤结果
        steps = summary.get("step_results", [])
        if steps:
            lines.append(f"")
            lines.append(f"═══ 步骤结果 ({len(steps)} 步) ═══")
            for sr in steps:
                idx = sr.get("step_index", "?")
                stype = sr.get("step_type", "?")
                ok = "✅" if sr.get("success") else "❌"
                details = sr.get("details", "")
                data_file = sr.get("data_file", "")
                pts = sr.get("data_points_count", 0)
                
                line = f"  步骤{idx} [{stype}] {ok}"
                if details:
                    line += f" — {details}"
                if data_file:
                    line += f"  📄 {data_file}"
                if pts > 0:
                    line += f" ({pts}点)"
                lines.append(line)
        
        # 错误
        errors = summary.get("errors", [])
        if errors:
            lines.append(f"")
            lines.append(f"═══ 错误 ({len(errors)}) ═══")
            for e in errors:
                lines.append(f"  ❌ {e}")
        
        # 警告
        warnings = summary.get("warnings", [])
        if warnings:
            lines.append(f"")
            lines.append(f"═══ 警告 ({len(warnings)}) ═══")
            for w in warnings:
                lines.append(f"  ⚠ {w}")
        
        self.summary_text.setPlainText("\n".join(lines))
    
    def _load_echem_files(self, run_dir: Path):
        """加载电化学数据文件列表"""
        echem_dir = run_dir / "echem"
        self.echem_table.setRowCount(0)
        self.echem_preview.clear()
        self.echem_preview.setText("选择一个文件预览")
        
        if not echem_dir.exists():
            self.echem_files_label.setText("电化学数据文件: 无")
            return
        
        files = sorted(echem_dir.iterdir())
        csv_files = [f for f in files if f.suffix == ".csv"]
        png_files = [f for f in files if f.suffix == ".png"]
        
        self.echem_files_label.setText(
            f"电化学数据文件: {len(csv_files)} CSV, {len(png_files)} PNG"
        )
        
        row = 0
        for csv_f in csv_files:
            self.echem_table.insertRow(row)
            
            # 文件名
            self.echem_table.setItem(row, 0, QTableWidgetItem(csv_f.name))
            
            # 技术类型（从文件名提取）
            parts = csv_f.stem.split("_")
            technique = parts[-1] if len(parts) > 1 else "?"
            self.echem_table.setItem(row, 1, QTableWidgetItem(technique))
            
            # 数据点数
            try:
                with open(csv_f, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    line_count = sum(1 for _ in reader) - 1  # 减去表头
                self.echem_table.setItem(row, 2, QTableWidgetItem(str(line_count)))
            except Exception:
                self.echem_table.setItem(row, 2, QTableWidgetItem("?"))
            
            # 操作列
            item = QTableWidgetItem("双击预览")
            item.setData(Qt.UserRole, str(csv_f))
            self.echem_table.setItem(row, 3, item)
            
            # 检查是否有对应 PNG
            png_path = csv_f.with_suffix(".png")
            if png_path.exists():
                item.setData(Qt.UserRole + 1, str(png_path))
            
            row += 1
        
        # 双击预览图表
        self.echem_table.cellDoubleClicked.connect(self._on_echem_preview)
    
    def _on_echem_preview(self, row: int, col: int):
        """预览电化学图表"""
        item = self.echem_table.item(row, 3)
        if not item:
            return
        
        png_path = item.data(Qt.UserRole + 1)
        if png_path and Path(png_path).exists():
            pixmap = QPixmap(png_path)
            scaled = pixmap.scaled(
                self.echem_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.echem_preview.setPixmap(scaled)
        else:
            csv_path = item.data(Qt.UserRole)
            if csv_path:
                self.echem_preview.setText(f"无图表预览\nCSV: {Path(csv_path).name}")
    
    def _on_open_dir(self):
        """在文件管理器中打开运行目录"""
        if not self._current_run:
            return
        run_dir = self._current_run.get("run_dir", "")
        if run_dir and Path(run_dir).exists():
            os.startfile(run_dir)
    
    def _on_export(self):
        """导出选中的运行记录到指定目录"""
        if not self._current_run:
            QMessageBox.warning(self, "提示", "请先选择一条运行记录")
            return
        
        run_dir = Path(self._current_run["run_dir"])
        if not run_dir.exists():
            QMessageBox.warning(self, "提示", "运行目录不存在")
            return
        
        dest_dir = QFileDialog.getExistingDirectory(self, "选择导出目标目录")
        if dest_dir:
            try:
                dest = Path(dest_dir) / run_dir.name
                shutil.copytree(str(run_dir), str(dest))
                QMessageBox.information(self, "导出成功", f"已导出到:\n{dest}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", str(e))
    
    def _on_delete(self):
        """删除选中的运行记录"""
        if not self._current_run:
            QMessageBox.warning(self, "提示", "请先选择一条运行记录")
            return
        
        run_dir = Path(self._current_run["run_dir"])
        exp_name = self._current_run.get("exp_name", run_dir.name)
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要永久删除以下实验运行数据？\n\n"
            f"名称: {exp_name}\n"
            f"目录: {run_dir}\n\n"
            f"此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(str(run_dir))
                self._refresh_runs()
                self.summary_text.clear()
                self.log_text.clear()
                self.status_label.setText(f"已删除: {exp_name}")
            except Exception as e:
                QMessageBox.critical(self, "删除失败", str(e))

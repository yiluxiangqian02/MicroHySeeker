"""AutoHySeeker Agent Dashboard Widget.

A compact status panel embedded in the MicroHySeeker main window that:
- Shows AutoHySeeker API connectivity status
- Displays current optimization round / best result
- Allows starting/stopping the optimization loop from the hardware UI
- Polls the AutoHySeeker API every 5 seconds when visible
"""

from __future__ import annotations

import json
import logging
from typing import Any

from PySide6.QtCore import QTimer, Qt, Slot, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

_logger = logging.getLogger("MicroHySeeker.agent_dashboard")

_AUTOHYSEEKER_BASE = "http://localhost:8200"   # AutoHySeeker default port
_POLL_INTERVAL_MS = 5_000                       # 5 seconds

# ── Fonts ─────────────────────────────────────────────────────────────────────
_FONT_TITLE = QFont("Microsoft YaHei", 10, QFont.Bold)
_FONT_NORMAL = QFont("Microsoft YaHei", 9)
_FONT_SMALL = QFont("Microsoft YaHei", 8)
_FONT_MONO = QFont("Consolas", 9)


class _StatusFetcher(QThread):
    """Background thread to fetch optimization status without blocking UI."""

    status_received = Signal(dict)
    error_received = Signal(str)

    def run(self) -> None:
        if not _HTTPX_AVAILABLE:
            self.error_received.emit("httpx not installed")
            return
        try:
            resp = httpx.get(
                f"{_AUTOHYSEEKER_BASE}/api/optimization/status",
                timeout=3.0,
            )
            resp.raise_for_status()
            self.status_received.emit(resp.json())
        except Exception as exc:
            self.error_received.emit(str(exc))


class AgentDashboardWidget(QGroupBox):
    """Compact panel showing AutoHySeeker optimization status.

    Add to any Qt layout::

        dashboard = AgentDashboardWidget()
        some_layout.addWidget(dashboard)
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("🤖 AutoHySeeker Agent 状态", parent)
        self.setFont(_FONT_TITLE)
        self._connected = False
        self._running = False
        self._last_status: dict[str, Any] = {}

        self._build_ui()
        self._setup_timer()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(4)
        root.setContentsMargins(6, 4, 6, 4)

        # ── Row 1: Connection status + control buttons ─────────────────────
        top_row = QHBoxLayout()

        self._conn_dot = QLabel("●")
        self._conn_dot.setFont(QFont("Arial", 14))
        self._conn_dot.setStyleSheet("color: #9CA3AF;")  # grey = disconnected
        self._conn_dot.setFixedWidth(20)
        top_row.addWidget(self._conn_dot)

        self._conn_label = QLabel("未连接")
        self._conn_label.setFont(_FONT_SMALL)
        self._conn_label.setStyleSheet("color: #6B7280;")
        top_row.addWidget(self._conn_label)

        top_row.addStretch()

        self._btn_start = QPushButton("▶ 启动优化")
        self._btn_start.setFont(_FONT_SMALL)
        self._btn_start.setFixedHeight(24)
        self._btn_start.setEnabled(False)
        self._btn_start.setStyleSheet(
            "QPushButton { background:#10B981; color:white; border-radius:3px; padding:2px 8px; }"
            "QPushButton:disabled { background:#D1FAE5; color:#6EE7B7; }"
            "QPushButton:hover { background:#059669; }"
        )
        self._btn_start.clicked.connect(self._on_start_clicked)
        top_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton("■ 停止")
        self._btn_stop.setFont(_FONT_SMALL)
        self._btn_stop.setFixedHeight(24)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet(
            "QPushButton { background:#EF4444; color:white; border-radius:3px; padding:2px 8px; }"
            "QPushButton:disabled { background:#FEE2E2; color:#FCA5A5; }"
            "QPushButton:hover { background:#DC2626; }"
        )
        self._btn_stop.clicked.connect(self._on_stop_clicked)
        top_row.addWidget(self._btn_stop)

        root.addLayout(top_row)

        # ── Row 2: Progress bar (rounds) ───────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 10)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat("第 0 / 0 轮")
        self._progress.setFixedHeight(16)
        self._progress.setFont(_FONT_SMALL)
        self._progress.setStyleSheet(
            "QProgressBar { border:1px solid #D1D5DB; border-radius:3px; "
            "background:#F3F4F6; text-align:center; }"
            "QProgressBar::chunk { background:#3B82F6; border-radius:2px; }"
        )
        root.addWidget(self._progress)

        # ── Row 3: Best result grid ────────────────────────────────────────
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background:#F9FAFB; border-radius:4px; border:1px solid #E5E7EB;")
        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(6, 3, 6, 3)
        grid.setSpacing(2)

        def _kv(key: str, val_widget: QLabel) -> tuple[QLabel, QLabel]:
            k = QLabel(key)
            k.setFont(_FONT_SMALL)
            k.setStyleSheet("color:#6B7280; border:none;")
            val_widget.setFont(_FONT_MONO)
            val_widget.setStyleSheet("color:#111827; border:none;")
            return k, val_widget

        self._lbl_metric = QLabel("—")
        self._lbl_params = QLabel("—")
        self._lbl_status = QLabel("空闲")
        self._lbl_status.setStyleSheet("color:#6B7280; border:none;")

        k1, v1 = _kv("最优指标:", self._lbl_metric)
        k2, v2 = _kv("最优配比:", self._lbl_params)
        k3, v3 = _kv("当前状态:", self._lbl_status)

        grid.addWidget(k1, 0, 0)
        grid.addWidget(v1, 0, 1)
        grid.addWidget(k2, 1, 0)
        grid.addWidget(v2, 1, 1)
        grid.addWidget(k3, 2, 0)
        grid.addWidget(v3, 2, 1)
        grid.setColumnStretch(1, 1)

        root.addWidget(grid_frame)

        # ── Minimize size ──────────────────────────────────────────────────
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

    # ── Timer & polling ───────────────────────────────────────────────────────

    def _setup_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.setInterval(_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll_status)
        self._timer.start()
        # Initial fetch immediately
        QTimer.singleShot(500, self._poll_status)

    def _poll_status(self) -> None:
        """Spawn a background thread to fetch status."""
        fetcher = _StatusFetcher(self)
        fetcher.status_received.connect(self._on_status_received)
        fetcher.error_received.connect(self._on_status_error)
        fetcher.start()

    # ── Slots ─────────────────────────────────────────────────────────────────

    @Slot(dict)
    def _on_status_received(self, data: dict[str, Any]) -> None:
        self._last_status = data
        self._connected = True
        self._running = data.get("running", False)
        self._refresh_ui()

    @Slot(str)
    def _on_status_error(self, error: str) -> None:
        self._connected = False
        self._running = False
        self._conn_dot.setStyleSheet("color: #EF4444;")   # red = error
        self._conn_label.setText("AutoHySeeker 未启动")
        self._conn_label.setStyleSheet("color: #EF4444;")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(False)
        self._progress.setFormat("— / —")
        self._lbl_status.setText("未连接")
        self._lbl_status.setStyleSheet("color:#EF4444; border:none;")

    def _refresh_ui(self) -> None:
        data = self._last_status

        # Connection dot
        self._conn_dot.setStyleSheet("color: #10B981;")   # green = connected
        self._conn_label.setText("已连接")
        self._conn_label.setStyleSheet("color: #10B981;")

        # Progress
        current = data.get("current_round", 0)
        max_r = data.get("max_rounds", 10)
        self._progress.setRange(0, max(max_r, 1))
        self._progress.setValue(current)
        self._progress.setFormat(f"第 {current} / {max_r} 轮")

        # Status label
        status_map = {
            "idle": ("空闲", "#6B7280"),
            "running": ("运行中", "#3B82F6"),
            "designing": ("设计参数…", "#8B5CF6"),
            "executing": ("执行实验…", "#F59E0B"),
            "analyzing": ("分析数据…", "#10B981"),
            "evaluating": ("评估结果…", "#6366F1"),
            "completed": ("已完成", "#059669"),
            "error": ("错误", "#EF4444"),
            "emergency_stopped": ("紧急停止", "#DC2626"),
        }
        raw_status = data.get("status", "idle")
        label_text, label_color = status_map.get(raw_status, (raw_status, "#374151"))
        self._lbl_status.setText(label_text)
        self._lbl_status.setStyleSheet(f"color:{label_color}; border:none; font-weight:bold;")

        # Best result
        best = data.get("best_result")
        if best:
            metrics = best.get("metrics", {})
            # Show primary metric (first one)
            if metrics:
                key, val = next(iter(metrics.items()))
                self._lbl_metric.setText(f"{key}: {val:.2f}" if isinstance(val, float) else f"{key}: {val}")
            params = best.get("params", {})
            if params:
                parts = [f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                         for k, v in params.items()]
                self._lbl_params.setText("  ".join(parts[:3]))
        else:
            self._lbl_metric.setText("—")
            self._lbl_params.setText("—")

        # Buttons
        self._btn_start.setEnabled(self._connected and not self._running)
        self._btn_stop.setEnabled(self._connected and self._running)

    @Slot()
    def _on_start_clicked(self) -> None:
        """Send start request to AutoHySeeker API."""
        if not _HTTPX_AVAILABLE:
            return
        try:
            resp = httpx.post(
                f"{_AUTOHYSEEKER_BASE}/api/optimization/start",
                json={
                    "goal": "最小化 Fe-Co-Ni 三元合金 HER 过电位",
                    "max_rounds": 20,
                    "target_metric": "overpotential_mV",
                    "direction": "minimize",
                    "template_id": "tpl_her_standard",
                    "dry_run": False,
                },
                timeout=5.0,
            )
            resp.raise_for_status()
            _logger.info("Optimization loop started via dashboard")
            self._poll_status()
        except Exception as exc:
            _logger.warning("Failed to start optimization: %s", exc)

    @Slot()
    def _on_stop_clicked(self) -> None:
        """Send stop request to AutoHySeeker API."""
        if not _HTTPX_AVAILABLE:
            return
        try:
            resp = httpx.post(
                f"{_AUTOHYSEEKER_BASE}/api/optimization/stop",
                timeout=5.0,
            )
            resp.raise_for_status()
            _logger.info("Optimization loop stop requested via dashboard")
            self._poll_status()
        except Exception as exc:
            _logger.warning("Failed to stop optimization: %s", exc)

from __future__ import annotations

import datetime
import threading
from typing import Optional

import serial.tools.list_ports
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from echem_sdl.hardware import PumpManager, PumpState

from .widgets import create_pump_table


class _Signals(QObject):
    log = Signal(str)
    state = Signal(object)  # PumpState


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("泵通讯测试（MicroHySeeker/tools）")
        self.resize(1100, 700)

        self._signals = _Signals()
        self._signals.log.connect(self._append_log)
        self._signals.state.connect(self._on_state)

        self.pm = PumpManager()
        self.pm.on_state(lambda s: self._signals.state.emit(s))

        self._scan_active = False
        self._build_ui()
        self._refresh_ports()
        self.pump_table.selectRow(0)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self.pm.disconnect()
        except Exception:
            pass
        super().closeEvent(event)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        top_layout = QHBoxLayout()
        layout.addLayout(top_layout)

        top_layout.addWidget(self._build_connection_group(), 1)
        top_layout.addWidget(self._build_pump_group(), 2)
        top_layout.addWidget(self._build_control_group(), 1)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(180)
        layout.addWidget(self.log_view)

        self.setCentralWidget(root)

    def _build_connection_group(self) -> QGroupBox:
        group = QGroupBox("连接")
        layout = QVBoxLayout(group)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("端口"))
        self.port_combo = QComboBox()
        port_row.addWidget(self.port_combo)
        self.port_scan_button = QPushButton("扫描")
        self.port_scan_button.clicked.connect(self._refresh_ports)
        port_row.addWidget(self.port_scan_button)
        layout.addLayout(port_row)

        baud_row = QHBoxLayout()
        baud_row.addWidget(QLabel("波特率"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "25000", "38400", "57600", "115200", "256000"])
        self.baud_combo.setCurrentText("38400")
        baud_row.addWidget(self.baud_combo)
        layout.addLayout(baud_row)

        btn_row = QHBoxLayout()
        self.connect_button = QPushButton("连接")
        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button = QPushButton("断开")
        self.disconnect_button.clicked.connect(self._disconnect)
        self.disconnect_button.setEnabled(False)
        btn_row.addWidget(self.connect_button)
        btn_row.addWidget(self.disconnect_button)
        layout.addLayout(btn_row)

        self.connection_state = QLabel("未连接")
        self.connection_state.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.connection_state)

        return group

    def _build_pump_group(self) -> QGroupBox:
        group = QGroupBox("泵 1-12")
        layout = QVBoxLayout(group)

        self.scan_button = QPushButton("扫描 1-12（轮询）")
        self.scan_button.clicked.connect(self._toggle_scan)
        layout.addWidget(self.scan_button)

        self.pump_table = create_pump_table()
        self.pump_table.itemSelectionChanged.connect(self._update_selected_address)
        layout.addWidget(self.pump_table)
        return group

    def _build_control_group(self) -> QGroupBox:
        group = QGroupBox("选中泵")
        layout = QVBoxLayout(group)

        row = QHBoxLayout()
        row.addWidget(QLabel("地址"))
        self.selected_address = QLabel("0x01")
        row.addWidget(self.selected_address)
        row.addStretch()
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        self.read_button = QPushButton("读取状态")
        self.read_button.clicked.connect(self._read_selected)
        btn_row.addWidget(self.read_button)
        layout.addLayout(btn_row)

        enable_row = QHBoxLayout()
        self.enable_button = QPushButton("启用")
        self.enable_button.clicked.connect(lambda: self._set_enable(True))
        self.disable_button = QPushButton("禁用")
        self.disable_button.clicked.connect(lambda: self._set_enable(False))
        enable_row.addWidget(self.enable_button)
        enable_row.addWidget(self.disable_button)
        layout.addLayout(enable_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("转速"))
        self.speed_input = QLineEdit("100")
        speed_row.addWidget(self.speed_input)
        self.forward_check = QCheckBox("正转")
        self.forward_check.setChecked(True)
        speed_row.addWidget(self.forward_check)
        layout.addLayout(speed_row)

        run_row = QHBoxLayout()
        self.start_button = QPushButton("启动")
        self.start_button.clicked.connect(self._send_start)
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self._send_stop)
        run_row.addWidget(self.start_button)
        run_row.addWidget(self.stop_button)
        layout.addLayout(run_row)

        layout.addStretch()
        return group

    def _refresh_ports(self) -> None:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        current = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current and current in ports:
            self.port_combo.setCurrentText(current)

    def _connect(self) -> None:
        port = self.port_combo.currentText().strip()
        if not port:
            self._append_log("请选择端口")
            return
        try:
            baud = int(self.baud_combo.currentText())
        except ValueError:
            self._append_log("波特率无效")
            return
        try:
            self.pm.connect(port=port, baudrate=baud)
        except Exception as exc:
            self._append_log(f"连接失败: {exc}")
            return

        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.connection_state.setText("已连接")
        self._append_log(f"已连接 {port} @ {baud}")

    def _disconnect(self) -> None:
        self._stop_scan()
        try:
            self.pm.disconnect()
        except Exception:
            pass
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.connection_state.setText("未连接")
        self._append_log("已断开")

    def _toggle_scan(self) -> None:
        if self._scan_active:
            self._stop_scan()
        else:
            self._start_scan()

    def _start_scan(self) -> None:
        if not self.pm.driver.is_open():
            self._append_log("请先连接再扫描")
            return
        for row in range(self.pump_table.rowCount()):
            self.pump_table.item(row, 1).setText("离线")
            self.pump_table.item(row, 2).setText("-")
            self.pump_table.item(row, 3).setText("-")
            self.pump_table.item(row, 4).setText("-")
            self.pump_table.item(row, 5).setText("-")
            self.pump_table.item(row, 6).setText("")
        self._scan_active = True
        self.scan_button.setText("停止扫描")
        self.pm.start_scan()
        self._append_log("开始扫描（后台轮询）")

    def _stop_scan(self) -> None:
        if not self._scan_active:
            return
        self._scan_active = False
        self.scan_button.setText("扫描 1-12（轮询）")
        try:
            self.pm.stop_scan()
        except Exception:
            pass
        self._append_log("停止扫描")

    def _read_selected(self) -> None:
        if not self.pm.driver.is_open():
            self._append_log("请先连接")
            return
        self._stop_scan()
        addr = self._selected_address()

        def worker() -> None:
            try:
                self.pm.read_enable(addr)
                self.pm.read_speed(addr)
                self.pm.read_fault(addr)
                self._signals.log.emit(f"读取完成: 0x{addr:02X}")
            except Exception as exc:
                self._signals.log.emit(f"读取失败: 0x{addr:02X} - {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _set_enable(self, enable: bool) -> None:
        if not self.pm.driver.is_open():
            self._append_log("请先连接")
            return
        self._stop_scan()
        addr = self._selected_address()

        def worker() -> None:
            try:
                self.pm.set_enable(addr, enable)
                self._signals.log.emit(f"{'启用' if enable else '禁用'}: 0x{addr:02X}")
            except Exception as exc:
                self._signals.log.emit(f"设置使能失败: 0x{addr:02X} - {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _send_start(self) -> None:
        if not self.pm.driver.is_open():
            self._append_log("请先连接")
            return
        self._stop_scan()
        addr = self._selected_address()
        try:
            rpm = int(self.speed_input.text())
        except ValueError:
            self._append_log("转速必须是数字")
            return
        if rpm < 1 or rpm > 3000:
            self._append_log("转速范围 1-3000")
            return
        direction = "forward" if self.forward_check.isChecked() else "reverse"

        def worker() -> None:
            try:
                self.pm.set_speed(addr, rpm=rpm, direction=direction)
                self._signals.log.emit(f"启动: 0x{addr:02X} rpm={rpm} dir={direction}")
            except Exception as exc:
                self._signals.log.emit(f"启动失败: 0x{addr:02X} - {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _send_stop(self) -> None:
        if not self.pm.driver.is_open():
            self._append_log("请先连接")
            return
        self._stop_scan()
        addr = self._selected_address()

        def worker() -> None:
            try:
                self.pm.set_speed(addr, rpm=0)
                self._signals.log.emit(f"停止: 0x{addr:02X}")
            except Exception as exc:
                self._signals.log.emit(f"停止失败: 0x{addr:02X} - {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def _update_selected_address(self) -> None:
        addr = self._selected_address()
        self.selected_address.setText(f"0x{addr:02X}")

    def _selected_address(self) -> int:
        items = self.pump_table.selectedItems()
        if not items:
            return 1
        return items[0].row() + 1

    def _append_log(self, message: str) -> None:
        self.log_view.append(f"{self._now_text()} {message}")

    @staticmethod
    def _now_text() -> str:
        return datetime.datetime.now().strftime("%H:%M:%S")

    def _on_state(self, state_obj: object) -> None:
        if not isinstance(state_obj, PumpState):
            return
        addr = state_obj.address
        if addr < 1 or addr > 12:
            return
        row = addr - 1
        self.pump_table.item(row, 1).setText("在线" if state_obj.online else "离线")
        self.pump_table.item(row, 2).setText(
            "启用" if state_obj.enabled is True else ("禁用" if state_obj.enabled is False else "-")
        )
        self.pump_table.item(row, 3).setText(str(state_obj.speed) if state_obj.speed is not None else "-")
        if state_obj.fault is None:
            fault_text = "-"
        elif state_obj.fault == 0x00:
            fault_text = "正常"
        elif state_obj.fault == 0x01:
            fault_text = "堵转"
        else:
            fault_text = f"0x{state_obj.fault:02X}"
        self.pump_table.item(row, 4).setText(fault_text)
        self.pump_table.item(row, 5).setText(self._now_text() if state_obj.last_seen else "-")
        self.pump_table.item(row, 6).setText(state_obj.note or "")


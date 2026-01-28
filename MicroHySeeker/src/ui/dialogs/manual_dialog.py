"""Manual control dialog with syringe and RS485 peristaltic pumps."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QSpinBox,
    QDoubleSpinBox, QComboBox, QCheckBox, QTextEdit, QGroupBox, QFormLayout,
    QTabWidget, QListWidget, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt, Signal


class ManualDialog(QDialog):
    """手动控制对话框（注射泵 + RS485 蠕动泵）。"""
    
    command_sent = Signal(str)
    
    def __init__(self, pump_manager=None, rs485_driver=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("手动控制")
        self.setGeometry(100, 100, 1000, 700)
        self.pump_manager = pump_manager
        self.rs485_driver = rs485_driver
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """创建控件。"""
        layout = QVBoxLayout(self)
        
        # 选项卡
        self.tabs = QTabWidget()
        
        # 注射泵选项卡
        self._create_syringe_tab()
        
        # RS485 蠕动泵选项卡
        self._create_peristaltic_tab()
        
        # 命令日志选项卡
        self._create_log_tab()
        
        layout.addWidget(self.tabs)
        
        # 底部控制按钮
        bottom_layout = QHBoxLayout()
        
        self.btn_emergency_stop = QPushButton("🛑 紧急停止")
        self.btn_emergency_stop.setStyleSheet("QPushButton { background-color: #FF6B6B; color: white; }")
        self.btn_emergency_stop.clicked.connect(self._emergency_stop)
        
        bottom_layout.addWidget(self.btn_emergency_stop)
        bottom_layout.addStretch()
        
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(self.btn_close)
        
        layout.addLayout(bottom_layout)
    
    def _create_syringe_tab(self) -> None:
        """创建注射泵控制选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 泵选择
        pump_group = QGroupBox("泵选择")
        pump_form = QFormLayout(pump_group)
        
        self.syringe_combo = QComboBox()
        self.syringe_combo.addItems(["泵 1", "泵 2", "泵 3"])
        pump_form.addRow("选择注射泵", self.syringe_combo)
        
        layout.addWidget(pump_group)
        
        # 控制参数
        ctrl_group = QGroupBox("控制参数")
        ctrl_form = QFormLayout(ctrl_group)
        
        self.syringe_speed = QDoubleSpinBox()
        self.syringe_speed.setMinimum(0.1)
        self.syringe_speed.setMaximum(100.0)
        self.syringe_speed.setValue(10.0)
        ctrl_form.addRow("转速 (mL/min)", self.syringe_speed)
        
        self.syringe_volume = QDoubleSpinBox()
        self.syringe_volume.setMinimum(0.0)
        self.syringe_volume.setMaximum(10.0)
        self.syringe_volume.setValue(1.0)
        ctrl_form.addRow("体积 (mL)", self.syringe_volume)
        
        self.syringe_direction = QComboBox()
        self.syringe_direction.addItems(["吸入", "推出"])
        ctrl_form.addRow("方向", self.syringe_direction)
        
        layout.addWidget(ctrl_group)
        
        # 操作按钮
        op_group = QGroupBox("操作")
        op_layout = QVBoxLayout(op_group)
        
        btn_layout1 = QHBoxLayout()
        btn_start = QPushButton("启动")
        btn_stop = QPushButton("停止")
        btn_step = QPushButton("步进")
        btn_start.clicked.connect(lambda: self._syringe_command("start"))
        btn_stop.clicked.connect(lambda: self._syringe_command("stop"))
        btn_step.clicked.connect(lambda: self._syringe_command("step"))
        btn_layout1.addWidget(btn_start)
        btn_layout1.addWidget(btn_stop)
        btn_layout1.addWidget(btn_step)
        op_layout.addLayout(btn_layout1)
        
        btn_layout2 = QHBoxLayout()
        btn_move = QPushButton("移动指定体积")
        btn_home = QPushButton("复位")
        btn_move.clicked.connect(lambda: self._syringe_command("move"))
        btn_home.clicked.connect(lambda: self._syringe_command("home"))
        btn_layout2.addWidget(btn_move)
        btn_layout2.addWidget(btn_home)
        op_layout.addLayout(btn_layout2)
        
        layout.addWidget(op_group)
        
        # 状态显示
        status_group = QGroupBox("状态")
        status_form = QFormLayout(status_group)
        
        self.syringe_status = QLabel("就绪")
        self.syringe_position = QLabel("0.0 mL")
        status_form.addRow("状态", self.syringe_status)
        status_form.addRow("当前位置", self.syringe_position)
        
        layout.addWidget(status_group)
        layout.addStretch()
        
        self.tabs.addTab(widget, "注射泵")
    
    def _create_peristaltic_tab(self) -> None:
        """创建 RS485 蠕动泵控制选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 端口和设备选择
        device_group = QGroupBox("设备选择")
        device_form = QFormLayout(device_group)
        
        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4"])
        self.port_combo.currentTextChanged.connect(self._refresh_peristaltic_devices)
        device_form.addRow("通讯端口", self.port_combo)
        
        self.device_addr_combo = QComboBox()
        self.device_addr_combo.addItems(["设备 1", "设备 2", "设备 3", "设备 4", "设备 5"])
        device_form.addRow("设备地址", self.device_addr_combo)
        
        layout.addWidget(device_group)
        
        # 控制参数
        ctrl_group = QGroupBox("控制参数")
        ctrl_form = QFormLayout(ctrl_group)
        
        self.peristaltic_speed = QDoubleSpinBox()
        self.peristaltic_speed.setMinimum(0.0)
        self.peristaltic_speed.setMaximum(500.0)
        self.peristaltic_speed.setValue(100.0)
        ctrl_form.addRow("转速 (RPM)", self.peristaltic_speed)
        
        self.peristaltic_direction = QComboBox()
        self.peristaltic_direction.addItems(["正向", "反向"])
        ctrl_form.addRow("方向", self.peristaltic_direction)
        
        self.peristaltic_volume = QDoubleSpinBox()
        self.peristaltic_volume.setMinimum(0.0)
        self.peristaltic_volume.setMaximum(100.0)
        self.peristaltic_volume.setValue(10.0)
        ctrl_form.addRow("体积 (mL)", self.peristaltic_volume)
        
        self.peristaltic_cycle_time = QDoubleSpinBox()
        self.peristaltic_cycle_time.setMinimum(0.1)
        self.peristaltic_cycle_time.setMaximum(60.0)
        self.peristaltic_cycle_time.setValue(1.0)
        ctrl_form.addRow("周期 (s)", self.peristaltic_cycle_time)
        
        layout.addWidget(ctrl_group)
        
        # 操作按钮
        op_group = QGroupBox("操作")
        op_layout = QVBoxLayout(op_group)
        
        btn_layout = QHBoxLayout()
        btn_start = QPushButton("启动")
        btn_stop = QPushButton("停止")
        btn_pulse = QPushButton("脉冲")
        btn_start.clicked.connect(lambda: self._peristaltic_command("start"))
        btn_stop.clicked.connect(lambda: self._peristaltic_command("stop"))
        btn_pulse.clicked.connect(lambda: self._peristaltic_command("pulse"))
        btn_layout.addWidget(btn_start)
        btn_layout.addWidget(btn_stop)
        btn_layout.addWidget(btn_pulse)
        op_layout.addLayout(btn_layout)
        
        layout.addWidget(op_group)
        layout.addStretch()
        
        self.tabs.addTab(widget, "RS485 蠕动泵")
    
    def _create_log_tab(self) -> None:
        """创建命令日志选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("命令日志："))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        btn_clear = QPushButton("清空日志")
        btn_clear.clicked.connect(lambda: self.log_text.clear())
        layout.addWidget(btn_clear)
        
        self.tabs.addTab(widget, "日志")
    
    def _syringe_command(self, command: str) -> None:
        """执行注射泵命令。"""
        pump_index = self.syringe_combo.currentIndex() + 1
        speed = self.syringe_speed.value()
        volume = self.syringe_volume.value()
        direction = self.syringe_direction.currentText()
        
        msg = f"[SyringePump {pump_index}] {command.upper()}"
        if command == "move":
            msg += f" {volume} mL"
        elif command == "step":
            msg += f" at {speed} mL/min"
        
        self.log_text.append(msg)
        self.command_sent.emit(msg)
        print(msg)
    
    def _peristaltic_command(self, command: str) -> None:
        """执行蠕动泵命令。"""
        port = self.port_combo.currentText()
        addr = self.device_addr_combo.currentText()
        speed = self.peristaltic_speed.value()
        direction = self.peristaltic_direction.currentText()
        
        msg = f"[RS485 {port} {addr}] {command.upper()}"
        if command == "start":
            msg += f" at {speed} RPM, direction: {direction}"
        elif command == "pulse":
            msg += f" with volume {self.peristaltic_volume.value()} mL"
        
        self.log_text.append(msg)
        self.command_sent.emit(msg)
        print(msg)
    
    def _refresh_peristaltic_devices(self) -> None:
        """刷新 RS485 设备列表。"""
        if self.rs485_driver:
            devices = self.rs485_driver.scan_devices()
            self.device_addr_combo.clear()
            self.device_addr_combo.addItems([f"设备 {d}" for d in devices])
            self.log_text.append(f"已刷新设备列表: {devices}")
    
    def _emergency_stop(self) -> None:
        """紧急停止所有设备。"""
        msg = "[EMERGENCY] ALL PUMPS STOPPED!"
        self.log_text.append(msg)
        self.command_sent.emit(msg)
        self.syringe_status.setText("紧急停止")
        QMessageBox.warning(self, "紧急停止", "所有泵已停止运行")

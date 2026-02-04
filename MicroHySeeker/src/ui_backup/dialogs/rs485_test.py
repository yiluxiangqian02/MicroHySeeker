"""RS485 test dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
    QComboBox, QSpinBox, QGroupBox, QFormLayout, QMessageBox, QCheckBox
)


class RS485TestDialog(QDialog):
    """RS485 测试对话框。"""
    
    def __init__(self, rs485_driver=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RS485 测试")
        self.setGeometry(100, 100, 800, 600)
        self.rs485_driver = rs485_driver
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """创建控件。"""
        layout = QVBoxLayout(self)
        
        # 连接设置
        conn_group = QGroupBox("连接设置")
        conn_form = QFormLayout(conn_group)
        
        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4"])
        conn_form.addRow("端口", self.port_combo)
        
        self.baudrate_spin = QSpinBox()
        self.baudrate_spin.setValue(9600)
        conn_form.addRow("波特率", self.baudrate_spin)
        
        btn_connect = QPushButton("连接")
        btn_disconnect = QPushButton("断开")
        btn_connect.clicked.connect(self._connect)
        btn_disconnect.clicked.connect(self._disconnect)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_connect)
        btn_layout.addWidget(btn_disconnect)
        conn_form.addRow("操作", btn_layout)
        
        layout.addWidget(conn_group)
        
        # 命令发送
        cmd_group = QGroupBox("命令发送")
        cmd_form = QFormLayout(cmd_group)
        
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("输入十六进制命令，如: 01 03 00 00 00 0A...")
        cmd_form.addRow("命令", self.cmd_input)
        
        btn_send = QPushButton("发送")
        btn_send.clicked.connect(self._send_command)
        cmd_form.addRow("", btn_send)
        
        layout.addWidget(cmd_group)
        
        # 设备扫描
        scan_group = QGroupBox("设备扫描")
        scan_form = QFormLayout(scan_group)
        
        btn_scan = QPushButton("扫描 RS485 设备")
        btn_scan.clicked.connect(self._scan_devices)
        scan_form.addRow("", btn_scan)
        
        self.scan_result = QTextEdit()
        self.scan_result.setReadOnly(True)
        self.scan_result.setMaximumHeight(80)
        scan_form.addRow("结果", self.scan_result)
        
        layout.addWidget(scan_group)
        
        # 数据显示
        display_group = QGroupBox("数据显示")
        display_form = QFormLayout(display_group)
        
        self.hex_checkbox = QCheckBox("十六进制显示")
        self.hex_checkbox.setChecked(True)
        display_form.addRow("格式", self.hex_checkbox)
        
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        display_form.addRow("接收数据", self.data_display)
        
        layout.addWidget(display_group)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
    
    def _connect(self) -> None:
        """连接 RS485。"""
        if self.rs485_driver:
            self.rs485_driver.connect()
        QMessageBox.information(self, "成功", "已连接")
    
    def _disconnect(self) -> None:
        """断开 RS485。"""
        if self.rs485_driver:
            self.rs485_driver.disconnect()
        QMessageBox.information(self, "成功", "已断开")
    
    def _send_command(self) -> None:
        """发送命令。"""
        cmd_str = self.cmd_input.text()
        try:
            data = bytes.fromhex(cmd_str.replace(" ", ""))
            if self.rs485_driver:
                self.rs485_driver.send(data)
            self.data_display.append(f"[SENT] {data.hex().upper()}")
            
            # 模拟接收
            response = self.rs485_driver.read() if self.rs485_driver else b'\x01\x03\x00\x00'
            if response:
                self.data_display.append(f"[RECV] {response.hex().upper()}")
        except ValueError:
            QMessageBox.critical(self, "错误", "命令格式不正确")
    
    def _scan_devices(self) -> None:
        """扫描设备。"""
        if self.rs485_driver:
            devices = self.rs485_driver.scan_devices()
            self.scan_result.setText(f"找到设备: {devices}")
        else:
            self.scan_result.setText("找到设备: [1, 2, 3, 4, 5] (Mock)")

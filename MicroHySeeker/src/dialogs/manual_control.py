"""
手动控制对话 - 单台泵控制与测试
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QSpinBox, QTextEdit, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal, QThread, Slot
import time

from src.services.rs485_wrapper import get_rs485_instance


class ManualControlDialog(QDialog):
    """手动控制对话框"""
    
    def __init__(self, pump_addresses: list, parent=None):
        super().__init__(parent)
        self.pump_addresses = pump_addresses or list(range(1, 13))
        self.rs485 = get_rs485_instance()
        self.setWindowTitle("手动控制")
        self.setGeometry(200, 200, 600, 500)
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 泵选择
        pump_layout = QHBoxLayout()
        pump_layout.addWidget(QLabel("泵地址:"))
        self.pump_combo = QComboBox()
        self.pump_combo.addItems([str(addr) for addr in self.pump_addresses])
        pump_layout.addWidget(self.pump_combo)
        layout.addLayout(pump_layout)
        
        # 转速设置
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("转速(RPM):"))
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(0, 1000)
        self.speed_spin.setValue(100)
        speed_layout.addWidget(self.speed_spin)
        layout.addLayout(speed_layout)
        
        # 控制按钮组
        ctrl_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("运行")
        self.run_btn.clicked.connect(self._on_run)
        ctrl_layout.addWidget(self.run_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._on_stop)
        ctrl_layout.addWidget(self.stop_btn)
        
        self.fw_btn = QPushButton("正转")
        self.fw_btn.clicked.connect(self._on_forward)
        ctrl_layout.addWidget(self.fw_btn)
        
        self.rev_btn = QPushButton("反转")
        self.rev_btn.clicked.connect(self._on_reverse)
        ctrl_layout.addWidget(self.rev_btn)
        
        layout.addLayout(ctrl_layout)
        
        # 日志
        log_label = QLabel("命令日志:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def _get_pump_address(self) -> int:
        """获取当前选中的泵地址"""
        return int(self.pump_combo.currentText())
    
    def _log(self, msg: str):
        """添加日志"""
        self.log_text.append(msg)
    
    def _on_run(self):
        """启动泵"""
        addr = self._get_pump_address()
        rpm = self.speed_spin.value()
        if self.rs485.start_pump(addr, "FWD", rpm):
            self._log(f"[泵{addr}] 启动 FWD {rpm}RPM")
        else:
            self._log(f"[泵{addr}] 启动失败")
    
    def _on_stop(self):
        """停止泵"""
        addr = self._get_pump_address()
        if self.rs485.stop_pump(addr):
            self._log(f"[泵{addr}] 已停止")
        else:
            self._log(f"[泵{addr}] 停止失败")
    
    def _on_forward(self):
        """正转"""
        addr = self._get_pump_address()
        rpm = self.speed_spin.value()
        if self.rs485.start_pump(addr, "FWD", rpm):
            self._log(f"[泵{addr}] 正转 {rpm}RPM")
        else:
            self._log(f"[泵{addr}] 正转失败")
    
    def _on_reverse(self):
        """反转"""
        addr = self._get_pump_address()
        rpm = self.speed_spin.value()
        if self.rs485.start_pump(addr, "REV", rpm):
            self._log(f"[泵{addr}] 反转 {rpm}RPM")
        else:
            self._log(f"[泵{addr}] 反转失败")

"""
校准对话 - 泵流量标定
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QDoubleSpinBox, QSpinBox, QTextEdit, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal
import time

from src.models import SystemConfig
from src.services.rs485_wrapper import get_rs485_instance


class CalibrateDialog(QDialog):
    """校准对话框"""
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.rs485 = get_rs485_instance()
        self.start_time = None
        self.run_duration = 0.0
        
        self.setWindowTitle("泵流量校准")
        self.setGeometry(250, 250, 600, 500)
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 泵选择
        pump_layout = QHBoxLayout()
        pump_layout.addWidget(QLabel("泵地址:"))
        self.pump_combo = QComboBox()
        self.pump_combo.addItems([str(p.address) for p in self.config.pumps])
        pump_layout.addWidget(self.pump_combo)
        layout.addLayout(pump_layout)
        
        # 目标体积
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(QLabel("目标体积 (uL):"))
        self.target_volume = QDoubleSpinBox()
        self.target_volume.setRange(0, 10000)
        self.target_volume.setValue(1000)
        vol_layout.addWidget(self.target_volume)
        layout.addLayout(vol_layout)
        
        # 转速
        rpm_layout = QHBoxLayout()
        rpm_layout.addWidget(QLabel("转速 (RPM):"))
        self.rpm_spin = QSpinBox()
        self.rpm_spin.setRange(1, 1000)
        self.rpm_spin.setValue(100)
        rpm_layout.addWidget(self.rpm_spin)
        layout.addLayout(rpm_layout)
        
        # 控制按钮
        ctrl_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self._on_start)
        ctrl_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        ctrl_layout.addWidget(self.stop_btn)
        
        layout.addLayout(ctrl_layout)
        
        # 实际体积输入
        actual_vol_layout = QHBoxLayout()
        actual_vol_layout.addWidget(QLabel("实际体积 (uL):"))
        self.actual_volume = QDoubleSpinBox()
        self.actual_volume.setRange(0, 10000)
        actual_vol_layout.addWidget(self.actual_volume)
        layout.addLayout(actual_vol_layout)
        
        # 计算与保存
        calc_layout = QHBoxLayout()
        
        calc_btn = QPushButton("计算标定因子")
        calc_btn.clicked.connect(self._on_calculate)
        calc_layout.addWidget(calc_btn)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        calc_layout.addWidget(save_btn)
        
        layout.addLayout(calc_layout)
        
        # 结果显示
        result_label = QLabel("计算结果:")
        layout.addWidget(result_label)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        # 关闭
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def _get_pump_address(self) -> int:
        """获取泵地址"""
        return int(self.pump_combo.currentText())
    
    def _on_start(self):
        """开始运行"""
        addr = self._get_pump_address()
        rpm = self.rpm_spin.value()
        
        if not self.rs485.is_connected():
            QMessageBox.warning(self, "警告", "串口未连接")
            return
        
        if self.rs485.start_pump(addr, "FWD", rpm):
            self.start_time = time.time()
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.result_text.setText(f"泵 {addr} 已启动，请等待...")
        else:
            QMessageBox.critical(self, "错误", f"启动泵 {addr} 失败")
    
    def _on_stop(self):
        """停止运行"""
        addr = self._get_pump_address()
        
        if self.rs485.stop_pump(addr):
            self.run_duration = time.time() - self.start_time if self.start_time else 0
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.result_text.setText(f"泵已停止，运行时长: {self.run_duration:.2f}s")
        else:
            QMessageBox.critical(self, "错误", f"停止泵 {addr} 失败")
    
    def _on_calculate(self):
        """计算标定因子"""
        actual_vol = self.actual_volume.value()
        target_vol = self.target_volume.value()
        
        if self.run_duration <= 0:
            QMessageBox.warning(self, "警告", "请先运行泵并停止")
            return
        
        if actual_vol <= 0:
            QMessageBox.warning(self, "警告", "请输入实际体积")
            return
        
        ul_per_sec = actual_vol / self.run_duration
        ul_per_rpm = actual_vol / (self.rpm_spin.value() * self.run_duration)
        
        result = (
            f"运行时长: {self.run_duration:.2f}s\n"
            f"实际体积: {actual_vol:.2f} uL\n"
            f"流量: {ul_per_sec:.4f} uL/s\n"
            f"流量: {ul_per_rpm:.4f} uL/RPM"
        )
        self.result_text.setText(result)
        
        # 保存到配置
        self._ul_per_sec = ul_per_sec
        self._ul_per_rpm = ul_per_rpm
    
    def _on_save(self):
        """保存标定因子"""
        if not hasattr(self, '_ul_per_sec'):
            QMessageBox.warning(self, "警告", "请先计算标定因子")
            return
        
        addr = self._get_pump_address()
        self.config.calibration_data[addr] = {
            "ul_per_sec": self._ul_per_sec,
            "ul_per_rpm": self._ul_per_rpm
        }
        
        QMessageBox.information(self, "成功", f"泵 {addr} 的标定因子已保存")

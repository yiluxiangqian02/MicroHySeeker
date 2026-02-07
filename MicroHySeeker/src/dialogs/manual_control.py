"""
手动控制对话框 - 12 台蠕动泵手动控制
参照 C# ManMotorsOnRS485
- 统一更大字体
- 支持速度模式和位置模式(SR_VFOC)控制
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QPushButton, QSpinBox, QDoubleSpinBox, QTextEdit, QMessageBox, QGroupBox, QFrame,
    QWidget, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont

from src.models import SystemConfig, PumpConfig
from src.services.rs485_wrapper import get_rs485_instance

# 编码器常量
ENCODER_DIVISIONS_PER_REV = 16384

# 全局字体
FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)
FONT_PUMP_TITLE = QFont("Microsoft YaHei", 12, QFont.Bold)


class PumpControlWidget(QFrame):
    """单台泵控制控件"""
    
    def __init__(self, pump_address: int, pump_name: str, rs485, parent=None):
        super().__init__(parent)
        self.pump_address = pump_address
        self.pump_name = pump_name
        self.rs485 = rs485
        self.is_running = False
        
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            PumpControlWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        
        # 标题
        title = QLabel(f"泵 {self.pump_address}")
        title.setFont(FONT_PUMP_TITLE)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 名称
        name_label = QLabel(self.pump_name)
        name_label.setFont(FONT_NORMAL)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #666;")
        layout.addWidget(name_label)
        
        # 状态指示灯
        self.status_indicator = QLabel("●")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet("color: gray; font-size: 20px;")
        layout.addWidget(self.status_indicator)
        
        # 转速设置
        speed_layout = QHBoxLayout()
        speed_label = QLabel("转速:")
        speed_label.setFont(FONT_NORMAL)
        speed_layout.addWidget(speed_label)
        self.speed_spin = QSpinBox()
        self.speed_spin.setFont(FONT_NORMAL)
        self.speed_spin.setRange(0, 1000)
        self.speed_spin.setValue(100)
        speed_layout.addWidget(self.speed_spin)
        layout.addLayout(speed_layout)
        
        # 方向选择
        self.dir_combo = QComboBox()
        self.dir_combo.setFont(FONT_NORMAL)
        self.dir_combo.addItems(["正向", "反向"])
        layout.addWidget(self.dir_combo)
        
        # === 位置控制（转几圈）===
        pos_layout = QHBoxLayout()
        pos_label = QLabel("圈数:")
        pos_label.setFont(FONT_NORMAL)
        pos_layout.addWidget(pos_label)
        self.revolutions_spin = QDoubleSpinBox()
        self.revolutions_spin.setFont(FONT_NORMAL)
        self.revolutions_spin.setRange(0.1, 100.0)
        self.revolutions_spin.setValue(1.0)
        self.revolutions_spin.setDecimals(2)
        self.revolutions_spin.setSingleStep(0.5)
        pos_layout.addWidget(self.revolutions_spin)
        layout.addLayout(pos_layout)
        
        # 控制按钮
        btn_layout = QGridLayout()
        
        self.run_btn = QPushButton("运行")
        self.run_btn.setFont(FONT_NORMAL)
        self.run_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.run_btn.clicked.connect(self._on_run)
        btn_layout.addWidget(self.run_btn, 0, 0)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setFont(FONT_NORMAL)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_btn, 0, 1)
        
        # 位置模式按钮
        self.pos_run_btn = QPushButton("位移运行")
        self.pos_run_btn.setFont(FONT_NORMAL)
        self.pos_run_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.pos_run_btn.setToolTip("使用位置模式(SR_VFOC)精确转动指定圈数")
        self.pos_run_btn.clicked.connect(self._on_position_run)
        btn_layout.addWidget(self.pos_run_btn, 1, 0, 1, 2)
        
        layout.addLayout(btn_layout)
    
    def _on_run(self):
        """启动泵 - 后端接口调用点"""
        # 检查RS485连接
        if not self.rs485.is_connected():
            QMessageBox.critical(
                self, "RS485 未连接",
                f"无法启动泵 {self.pump_address}：RS485 端口未连接。\n\n"
                f"请先在“系统配置”中连接串口，或启用 Mock 模式。"
            )
            return
        
        direction = "FWD" if self.dir_combo.currentText() == "正向" else "REV"
        rpm = self.speed_spin.value()
        
        # === 后端接口 ===
        success = self.rs485.start_pump(self.pump_address, direction, rpm)
        
        if success:
            self.is_running = True
            self.status_indicator.setStyleSheet("color: #4CAF50; font-size: 20px;")
        else:
            QMessageBox.warning(self, "错误", f"泵 {self.pump_address} 启动失败，请检查硬件连接")
    
    def _on_stop(self):
        """停止泵 - 后端接口调用点"""
        # === 后端接口 ===
        success = self.rs485.stop_pump(self.pump_address)
        
        if success:
            self.is_running = False
            self.status_indicator.setStyleSheet("color: gray; font-size: 20px;")
        else:
            QMessageBox.warning(self, "错误", f"泵 {self.pump_address} 停止失败")
    
    def force_stop(self):
        """强制停止（不等待响应，用于快速关闭）"""
        # 使用fire_and_forget模式，不等待响应
        self.rs485.stop_pump_fast(self.pump_address)
        self.is_running = False
        self.status_indicator.setStyleSheet("color: gray; font-size: 20px;")
    
    def _on_position_run(self):
        """位置模式运行 - 使用SR_VFOC编码器精确控制"""
        # 检查RS485连接
        if not self.rs485.is_connected():
            QMessageBox.critical(
                self, "RS485 未连接",
                f"无法启动泵 {self.pump_address}：RS485 端口未连接。\n\n"
                f"请先在“系统配置”中连接串口，或启用 Mock 模式。"
            )
            return
        
        direction = "FWD" if self.dir_combo.currentText() == "正向" else "REV"
        rpm = self.speed_spin.value()
        revolutions = self.revolutions_spin.value()
        
        # 计算编码器位移
        encoder_counts = int(revolutions * ENCODER_DIVISIONS_PER_REV)
        if direction == "REV":
            encoder_counts = -encoder_counts
        
        # 更新状态
        self.is_running = True
        self.status_indicator.setStyleSheet("color: #2196F3; font-size: 20px;")  # 蓝色表示位置模式
        self.pos_run_btn.setEnabled(False)
        self.pos_run_btn.setText(f"运行中...")
        
        # === 后端接口: 位置模式运行 ===
        try:
            success = self.rs485.run_position_rel(
                self.pump_address, 
                encoder_counts, 
                rpm, 
                acceleration=2  # 平滑加速
            )
            
            if success:
                # 启动定时器检查完成（估算时间）
                estimated_time_ms = int((revolutions / (rpm / 60.0) + 1.0) * 1000)
                QTimer.singleShot(estimated_time_ms, self._on_position_complete)
            else:
                self._on_position_complete()
                QMessageBox.warning(self, "错误", f"泵 {self.pump_address} 位置命令失败")
        except AttributeError:
            # rs485_wrapper可能没有这个方法
            self._on_position_complete()
            QMessageBox.warning(self, "提示", "位置模式需要升级RS485驱动")
        except Exception as e:
            self._on_position_complete()
            QMessageBox.warning(self, "错误", f"位置命令异常: {e}")
    
    def _on_position_complete(self):
        """位置运动完成"""
        self.is_running = False
        self.status_indicator.setStyleSheet("color: gray; font-size: 20px;")
        self.pos_run_btn.setEnabled(True)
        self.pos_run_btn.setText("位移运行")


class ManualControlDialog(QDialog):
    """
    手动控制对话框 - 12 台泵统一控制
    
    === 后端接口 ===
    1. RS485Wrapper.start_pump(addr, dir, rpm) -> bool
    2. RS485Wrapper.stop_pump(addr) -> bool
    3. RS485Wrapper.stop_all() -> bool
    """
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.rs485 = get_rs485_instance()
        self.pump_widgets = []
        
        self.setWindowTitle("手动控制 - 12 台蠕动泵")
        self.setGeometry(150, 150, 900, 600)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 连接状态
        conn_layout = QHBoxLayout()
        self.conn_label = QLabel("RS485 状态: 未连接")
        self.conn_label.setFont(FONT_NORMAL)
        self.conn_label.setStyleSheet("color: #f44336;")
        conn_layout.addWidget(self.conn_label)
        conn_layout.addStretch()
        
        # 全局控制
        self.stop_all_btn = QPushButton("全部停止")
        self.stop_all_btn.setFont(FONT_TITLE)
        self.stop_all_btn.setStyleSheet(
            "background-color: #f44336; color: white; padding: 10px 30px; font-weight: bold;"
        )
        self.stop_all_btn.clicked.connect(self._on_stop_all)
        conn_layout.addWidget(self.stop_all_btn)
        
        layout.addLayout(conn_layout)
        
        # 泵控制网格（4 行 x 3 列 = 12 台泵）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        pumps_widget = QWidget()
        pumps_layout = QGridLayout(pumps_widget)
        pumps_layout.setSpacing(10)
        
        for i in range(12):
            row = i // 3
            col = i % 3
            
            # 获取泵配置
            pump_addr = i + 1
            pump_name = f"泵_{pump_addr}"
            if self.config.pumps and i < len(self.config.pumps):
                pump_name = self.config.pumps[i].name
            
            pump_widget = PumpControlWidget(pump_addr, pump_name, self.rs485)
            self.pump_widgets.append(pump_widget)
            pumps_layout.addWidget(pump_widget, row, col)
        
        scroll.setWidget(pumps_widget)
        layout.addWidget(scroll)
        
        # 日志区
        log_group = QGroupBox("通讯日志")
        log_group.setFont(FONT_TITLE)
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(80)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                font-family: "Microsoft YaHei", Consolas, monospace;
                font-size: 10px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFont(FONT_NORMAL)
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
        
        # 更新连接状态
        self._update_connection_status()
    
    def _update_connection_status(self):
        """更新连接状态"""
        if self.rs485.is_connected():
            self.conn_label.setText("RS485 状态: 已连接")
            self.conn_label.setStyleSheet("color: #4CAF50;")
        else:
            self.conn_label.setText("RS485 状态: 未连接")
            self.conn_label.setStyleSheet("color: #f44336;")
    
    def _on_stop_all(self):
        """停止所有泵 - 后端接口调用点"""
        # === 后端接口 ===
        self.rs485.stop_all()
        
        for pw in self.pump_widgets:
            pw.force_stop()
        
        self._log("已发送全部停止命令")
    
    def _log(self, msg: str):
        """添加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.append(f"[{timestamp}] {msg}")
    
    def _on_close(self):
        """关闭对话框"""
        # 确保所有泵停止
        running_count = sum(1 for pw in self.pump_widgets if pw.is_running)
        if running_count > 0:
            reply = QMessageBox.question(
                self, "确认", f"还有 {running_count} 台泵正在运行，是否全部停止后关闭？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self._on_stop_all()
            elif reply == QMessageBox.Cancel:
                return
        
        self.accept()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 只停止正在运行的泵，使用快速模式
        running_addrs = [pw.pump_address for pw in self.pump_widgets if pw.is_running]
        if running_addrs:
            self.rs485.stop_pumps_fast(running_addrs)
            for pw in self.pump_widgets:
                if pw.is_running:
                    pw.is_running = False
                    pw.status_indicator.setStyleSheet("color: gray; font-size: 20px;")
        event.accept()

"""
冲洗对话框 - Flusher Dialog

提供冲洗功能的图形界面：
1. 显示系统配置中的冲洗通道（只读，配置在系统设置中修改）
2. 设置冲洗参数（循环数）
3. 执行冲洗循环
4. 单独执行排空或移液
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
    QProgressBar, QTextEdit, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont

from src.models import SystemConfig, FlushChannel


class FlusherDialog(QDialog):
    """冲洗对话框"""
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        
        # 获取 RS485 实例
        from src.services.rs485_wrapper import get_rs485_instance
        self.rs485 = get_rs485_instance()
        
        # 解析冲洗通道配置
        self._inlet_channel = None
        self._transfer_channel = None
        self._outlet_channel = None
        self._parse_flush_channels()
        
        self._init_ui()
        self._load_config()
        
        # 状态更新定时器
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
    
    def _parse_flush_channels(self):
        """解析系统配置中的冲洗通道"""
        for ch in self.config.flush_channels:
            work_type = getattr(ch, 'work_type', '').lower()
            if work_type == 'inlet':
                self._inlet_channel = ch
            elif work_type == 'transfer':
                self._transfer_channel = ch
            elif work_type == 'outlet':
                self._outlet_channel = ch
    
    def _check_config_complete(self) -> bool:
        """检查冲洗配置是否完整"""
        return all([self._inlet_channel, self._transfer_channel, self._outlet_channel])
    
    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("冲洗控制")
        self.setMinimumSize(600, 700)
        
        layout = QVBoxLayout(self)
        
        # 配置状态提示
        if not self._check_config_complete():
            warning_label = QLabel("⚠️ 冲洗通道配置不完整！请在 [系统配置] 中添加 Inlet、Transfer、Outlet 三个冲洗通道。")
            warning_label.setStyleSheet("color: #f44336; font-weight: bold; padding: 10px; background-color: #ffebee; border-radius: 5px;")
            warning_label.setWordWrap(True)
            layout.addWidget(warning_label)
        
        # 冲洗通道配置 (只读显示)
        config_group = QGroupBox("冲洗通道配置 (在系统配置中修改)")
        config_layout = QGridLayout(config_group)
        
        # 表头
        config_layout.addWidget(QLabel("<b>类型</b>"), 0, 0)
        config_layout.addWidget(QLabel("<b>泵地址</b>"), 0, 1)
        config_layout.addWidget(QLabel("<b>方向</b>"), 0, 2)
        config_layout.addWidget(QLabel("<b>转速</b>"), 0, 3)
        config_layout.addWidget(QLabel("<b>时长(秒)</b>"), 0, 4)
        
        # Inlet
        config_layout.addWidget(QLabel("进水泵 (Inlet):"), 1, 0)
        self.inlet_addr_label = QLabel(self._get_channel_display(self._inlet_channel, 'address'))
        config_layout.addWidget(self.inlet_addr_label, 1, 1)
        self.inlet_dir_label = QLabel(self._get_channel_display(self._inlet_channel, 'direction'))
        config_layout.addWidget(self.inlet_dir_label, 1, 2)
        self.inlet_rpm_label = QLabel(self._get_channel_display(self._inlet_channel, 'rpm'))
        config_layout.addWidget(self.inlet_rpm_label, 1, 3)
        self.inlet_duration_label = QLabel(self._get_channel_display(self._inlet_channel, 'duration'))
        config_layout.addWidget(self.inlet_duration_label, 1, 4)
        
        # Transfer
        config_layout.addWidget(QLabel("移液泵 (Transfer):"), 2, 0)
        self.transfer_addr_label = QLabel(self._get_channel_display(self._transfer_channel, 'address'))
        config_layout.addWidget(self.transfer_addr_label, 2, 1)
        self.transfer_dir_label = QLabel(self._get_channel_display(self._transfer_channel, 'direction'))
        config_layout.addWidget(self.transfer_dir_label, 2, 2)
        self.transfer_rpm_label = QLabel(self._get_channel_display(self._transfer_channel, 'rpm'))
        config_layout.addWidget(self.transfer_rpm_label, 2, 3)
        self.transfer_duration_label = QLabel(self._get_channel_display(self._transfer_channel, 'duration'))
        config_layout.addWidget(self.transfer_duration_label, 2, 4)
        
        # Outlet
        config_layout.addWidget(QLabel("出水泵 (Outlet):"), 3, 0)
        self.outlet_addr_label = QLabel(self._get_channel_display(self._outlet_channel, 'address'))
        config_layout.addWidget(self.outlet_addr_label, 3, 1)
        self.outlet_dir_label = QLabel(self._get_channel_display(self._outlet_channel, 'direction'))
        config_layout.addWidget(self.outlet_dir_label, 3, 2)
        self.outlet_rpm_label = QLabel(self._get_channel_display(self._outlet_channel, 'rpm'))
        config_layout.addWidget(self.outlet_rpm_label, 3, 3)
        self.outlet_duration_label = QLabel(self._get_channel_display(self._outlet_channel, 'duration'))
        config_layout.addWidget(self.outlet_duration_label, 3, 4)
        
        layout.addWidget(config_group)
        
        # 冲洗参数
        params_group = QGroupBox("冲洗参数")
        params_layout = QHBoxLayout(params_group)
        
        params_layout.addWidget(QLabel("循环次数:"))
        self.cycles_spin = QSpinBox()
        self.cycles_spin.setRange(1, 99)
        self.cycles_spin.setValue(3)
        params_layout.addWidget(self.cycles_spin)
        
        params_layout.addStretch()
        
        # 刷新配置按钮
        self.refresh_config_btn = QPushButton("🔄 刷新配置")
        self.refresh_config_btn.setToolTip("从系统配置重新加载冲洗通道")
        self.refresh_config_btn.clicked.connect(self._refresh_config)
        params_layout.addWidget(self.refresh_config_btn)
        
        layout.addWidget(params_group)
        
        # 状态显示
        status_group = QGroupBox("冲洗状态")
        status_layout = QVBoxLayout(status_group)
        
        # 状态标签
        status_labels_layout = QHBoxLayout()
        self.state_label = QLabel("状态: 空闲")
        self.state_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        status_labels_layout.addWidget(self.state_label)
        
        self.phase_label = QLabel("阶段: -")
        status_labels_layout.addWidget(self.phase_label)
        
        self.cycle_label = QLabel("循环: 0/0")
        status_labels_layout.addWidget(self.cycle_label)
        
        status_layout.addLayout(status_labels_layout)
        
        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("总进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        status_layout.addLayout(progress_layout)
        
        phase_progress_layout = QHBoxLayout()
        phase_progress_layout.addWidget(QLabel("阶段进度:"))
        self.phase_progress_bar = QProgressBar()
        self.phase_progress_bar.setRange(0, 100)
        self.phase_progress_bar.setValue(0)
        phase_progress_layout.addWidget(self.phase_progress_bar)
        status_layout.addLayout(phase_progress_layout)
        
        layout.addWidget(status_group)
        
        # 控制按钮
        control_group = QGroupBox("冲洗控制")
        control_layout = QHBoxLayout(control_group)
        
        self.start_btn = QPushButton("开始冲洗")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.start_btn.clicked.connect(self._start_flush)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止冲洗")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
        self.stop_btn.clicked.connect(self._stop_flush)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        control_layout.addWidget(self._create_separator())
        
        self.evacuate_btn = QPushButton("排空")
        self.evacuate_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 10px;")
        self.evacuate_btn.clicked.connect(self._start_evacuate)
        control_layout.addWidget(self.evacuate_btn)
        
        self.transfer_btn = QPushButton("移液")
        self.transfer_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px;")
        self.transfer_btn.clicked.connect(self._start_transfer)
        control_layout.addWidget(self.transfer_btn)
        
        layout.addWidget(control_group)
        
        # 日志区域
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # 关闭按钮
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)
    
    def _create_separator(self):
        """创建分隔线"""
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        return line
    
    def _get_channel_display(self, channel: FlushChannel, field: str) -> str:
        """获取通道显示文本"""
        if channel is None:
            return "<未配置>"
        if field == 'address':
            return f"泵 {channel.pump_address}"
        elif field == 'direction':
            return "正向" if channel.direction == "FWD" else "反向"
        elif field == 'rpm':
            return str(channel.rpm)
        elif field == 'duration':
            return f"{channel.cycle_duration_s:.1f}"
        return "-"
    
    def _refresh_config(self):
        """从系统配置刷新冲洗通道"""
        self._parse_flush_channels()
        self._update_display()
        self._apply_config_to_backend()
        self._log("配置已刷新")
    
    def _update_display(self):
        """更新显示"""
        # 更新 Inlet
        self.inlet_addr_label.setText(self._get_channel_display(self._inlet_channel, 'address'))
        self.inlet_dir_label.setText(self._get_channel_display(self._inlet_channel, 'direction'))
        self.inlet_rpm_label.setText(self._get_channel_display(self._inlet_channel, 'rpm'))
        self.inlet_duration_label.setText(self._get_channel_display(self._inlet_channel, 'duration'))
        
        # 更新 Transfer
        self.transfer_addr_label.setText(self._get_channel_display(self._transfer_channel, 'address'))
        self.transfer_dir_label.setText(self._get_channel_display(self._transfer_channel, 'direction'))
        self.transfer_rpm_label.setText(self._get_channel_display(self._transfer_channel, 'rpm'))
        self.transfer_duration_label.setText(self._get_channel_display(self._transfer_channel, 'duration'))
        
        # 更新 Outlet
        self.outlet_addr_label.setText(self._get_channel_display(self._outlet_channel, 'address'))
        self.outlet_dir_label.setText(self._get_channel_display(self._outlet_channel, 'direction'))
        self.outlet_rpm_label.setText(self._get_channel_display(self._outlet_channel, 'rpm'))
        self.outlet_duration_label.setText(self._get_channel_display(self._outlet_channel, 'duration'))
        
        # 更新按钮状态
        config_complete = self._check_config_complete()
        self.start_btn.setEnabled(config_complete)
        self.evacuate_btn.setEnabled(config_complete)
        self.transfer_btn.setEnabled(config_complete)
    
    def _load_config(self):
        """从配置加载冲洗通道并应用到后端"""
        self._apply_config_to_backend()
        if self._check_config_complete():
            self._log("冲洗配置已加载")
        else:
            missing = []
            if not self._inlet_channel:
                missing.append("Inlet")
            if not self._transfer_channel:
                missing.append("Transfer")
            if not self._outlet_channel:
                missing.append("Outlet")
            self._log(f"⚠️ 缺少冲洗通道配置: {', '.join(missing)}")
    
    def _apply_config_to_backend(self):
        """应用当前配置到后端"""
        if not self._check_config_complete():
            return False
        
        result = self.rs485.configure_flush_channels(
            inlet_address=self._inlet_channel.pump_address,
            transfer_address=self._transfer_channel.pump_address,
            outlet_address=self._outlet_channel.pump_address,
            inlet_rpm=self._inlet_channel.rpm,
            transfer_rpm=self._transfer_channel.rpm,
            outlet_rpm=self._outlet_channel.rpm,
            inlet_duration_s=self._inlet_channel.cycle_duration_s,
            transfer_duration_s=self._transfer_channel.cycle_duration_s,
            outlet_duration_s=self._outlet_channel.cycle_duration_s,
            default_cycles=self.cycles_spin.value()
        )
        return result
    
    def _start_flush(self):
        """开始冲洗"""
        if not self._check_config_complete():
            QMessageBox.warning(self, "配置不完整", 
                "请先在 [系统配置] 中添加完整的冲洗通道配置（Inlet、Transfer、Outlet）")
            return
        
        # 确保已配置
        if not self.rs485.get_flush_status():
            self._apply_config_to_backend()
        
        cycles = self.cycles_spin.value()
        
        self._log(f"开始冲洗: {cycles}个循环")
        
        result = self.rs485.start_flush(
            cycles=cycles,
            on_phase_change=self._on_phase_change,
            on_cycle_complete=self._on_cycle_complete,
            on_complete=self._on_complete,
            on_error=self._on_error
        )
        
        if result:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.evacuate_btn.setEnabled(False)
            self.transfer_btn.setEnabled(False)
            self.refresh_config_btn.setEnabled(False)
            
            # 启动状态更新定时器
            self._status_timer.start(100)  # 每100ms更新
        else:
            self._log("❌ 启动冲洗失败")
            QMessageBox.critical(self, "错误", "启动冲洗失败")
    
    def _stop_flush(self):
        """停止冲洗"""
        self._log("停止冲洗...")
        self.rs485.stop_flush()
        self._reset_ui()
    
    def _start_evacuate(self):
        """开始排空"""
        if not self._check_config_complete():
            QMessageBox.warning(self, "配置不完整", 
                "请先在 [系统配置] 中添加完整的冲洗通道配置")
            return
        
        # 确保已配置
        if not self.rs485.get_flush_status():
            self._apply_config_to_backend()
        
        duration = self._outlet_channel.cycle_duration_s if self._outlet_channel else 10.0
        self._log(f"开始排空: {duration}秒")
        
        result = self.rs485.start_evacuate(
            duration_s=duration,
            on_complete=self._on_evacuate_complete
        )
        
        if result:
            self._set_running_state(True)
            self.state_label.setText("状态: 排空中")
            self.phase_label.setText("阶段: Outlet")
            self._status_timer.start(100)
        else:
            self._log("❌ 启动排空失败")
    
    def _start_transfer(self):
        """开始移液"""
        if not self._check_config_complete():
            QMessageBox.warning(self, "配置不完整", 
                "请先在 [系统配置] 中添加完整的冲洗通道配置")
            return
        
        # 确保已配置
        if not self.rs485.get_flush_status():
            self._apply_config_to_backend()
        
        duration = self._transfer_channel.cycle_duration_s if self._transfer_channel else 10.0
        self._log(f"开始移液: {duration}秒")
        
        result = self.rs485.start_transfer(
            duration_s=duration,
            forward=True,
            on_complete=self._on_transfer_complete
        )
        
        if result:
            self._set_running_state(True)
            self.state_label.setText("状态: 移液中")
            self.phase_label.setText("阶段: Transfer")
            self._status_timer.start(100)
        else:
            self._log("❌ 启动移液失败")
    
    def _set_running_state(self, running: bool):
        """设置运行状态UI"""
        config_complete = self._check_config_complete()
        self.start_btn.setEnabled(not running and config_complete)
        self.stop_btn.setEnabled(running)
        self.evacuate_btn.setEnabled(not running and config_complete)
        self.transfer_btn.setEnabled(not running and config_complete)
        self.refresh_config_btn.setEnabled(not running)
    
    def _reset_ui(self):
        """重置UI状态"""
        self._status_timer.stop()
        self._set_running_state(False)
        self.state_label.setText("状态: 空闲")
        self.phase_label.setText("阶段: -")
        self.progress_bar.setValue(0)
        self.phase_progress_bar.setValue(0)
    
    @Slot()
    def _update_status(self):
        """更新状态显示"""
        status = self.rs485.get_flush_status()
        if status:
            self.state_label.setText(f"状态: {self._translate_state(status['state'])}")
            self.phase_label.setText(f"阶段: {self._translate_phase(status['phase'])}")
            self.cycle_label.setText(f"循环: {status['current_cycle']}/{status['total_cycles']}")
            self.progress_bar.setValue(int(status['progress'] * 100))
            self.phase_progress_bar.setValue(int(status['phase_progress'] * 100))
    
    def _translate_state(self, state: str) -> str:
        """翻译状态"""
        translations = {
            'idle': '空闲',
            'running': '运行中',
            'paused': '已暂停',
            'error': '错误'
        }
        return translations.get(state, state)
    
    def _translate_phase(self, phase: str) -> str:
        """翻译阶段"""
        translations = {
            'idle': '-',
            'inlet': '进水',
            'transfer': '移液',
            'outlet': '出水',
            'completed': '完成'
        }
        return translations.get(phase, phase)
    
    def _on_phase_change(self, phase):
        """阶段变化回调"""
        phase_name = phase.value if hasattr(phase, 'value') else str(phase)
        self._log(f"阶段变化: {self._translate_phase(phase_name)}")
    
    def _on_cycle_complete(self, cycle_num):
        """循环完成回调"""
        self._log(f"循环 {cycle_num} 完成")
    
    def _on_complete(self):
        """冲洗完成回调"""
        self._log("✅ 冲洗全部完成!")
        self._reset_ui()
        QMessageBox.information(self, "完成", "冲洗已完成!")
    
    def _on_evacuate_complete(self):
        """排空完成回调"""
        self._log("✅ 排空完成!")
        self._reset_ui()
    
    def _on_transfer_complete(self):
        """移液完成回调"""
        self._log("✅ 移液完成!")
        self._reset_ui()
    
    def _on_error(self, error):
        """错误回调"""
        self._log(f"❌ 错误: {error}")
        self._reset_ui()
        QMessageBox.critical(self, "错误", f"冲洗出错: {error}")
    
    def _log(self, message: str):
        """添加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def closeEvent(self, event):
        """关闭时停止冲洗"""
        if self.rs485.is_flushing():
            reply = QMessageBox.question(
                self, "确认", 
                "冲洗正在进行中，是否停止并关闭？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.rs485.stop_flush()
                event.accept()
            else:
                event.ignore()
        else:
            self._status_timer.stop()
            event.accept()

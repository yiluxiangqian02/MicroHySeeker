"""
配置对话框 - 系统设置、泵配置、通道管理
- 配液通道：原浓度（非储备浓度）、泵地址下拉、方向下拉
- 冲洗通道：增加工作类型（Inlet/Transfer/Outlet）
- 通道ID改为通道，自动按顺序写入1,2,3...
- 添加通道时，已输入的参数不变
- 所有小数保留两位
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QColorDialog,
    QMessageBox, QSpinBox, QDoubleSpinBox, QHeaderView, QLineEdit,
    QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from src.models import SystemConfig, DilutionChannel, FlushChannel
from src.services.rs485_wrapper import get_rs485_instance


# 全局字体设置
FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)


class ConfigDialog(QDialog):
    """
    配置对话框
    
    === 后端接口 ===
    1. RS485Wrapper.open_port(port: str, baudrate: int) -> bool
    2. RS485Wrapper.close_port() -> None
    3. RS485Wrapper.is_connected() -> bool
    4. RS485Wrapper.scan_pumps() -> List[int]
    """
    config_saved = Signal(SystemConfig)
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.rs485 = get_rs485_instance()
        self.setWindowTitle("系统配置")
        self.setGeometry(150, 100, 1100, 650)
        self.setFont(FONT_NORMAL)
        self._init_ui()
        self._load_config()
    
    def _get_pump_addresses(self):
        """获取可用泵地址列表"""
        return [str(i) for i in range(1, 13)]
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # RS485 连接区
        conn_group = QGroupBox("RS485 连接")
        conn_group.setFont(FONT_TITLE)
        conn_layout = QHBoxLayout(conn_group)
        conn_layout.addWidget(QLabel("端口:"))
        self.port_combo = QComboBox()
        self.port_combo.addItems(['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8'])
        conn_layout.addWidget(self.port_combo)
        
        conn_layout.addWidget(QLabel("波特率:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        conn_layout.addWidget(self.baud_combo)
        
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self._on_connect)
        conn_layout.addWidget(self.connect_btn)
        
        self.scan_btn = QPushButton("扫描泵")
        self.scan_btn.clicked.connect(self._on_scan)
        self.scan_btn.setEnabled(False)
        conn_layout.addWidget(self.scan_btn)
        
        conn_layout.addStretch()
        layout.addWidget(conn_group)
        
        # Tab 页
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(FONT_NORMAL)
        
        # 配液通道 Tab
        self.dilution_tab = self._create_dilution_tab()
        self.tab_widget.addTab(self.dilution_tab, "配液通道")
        
        # 冲洗通道 Tab
        self.flush_tab = self._create_flush_tab()
        self.tab_widget.addTab(self.flush_tab, "冲洗通道")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("保存配置")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 25px; font-size: 12px;")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("padding: 10px 25px; font-size: 12px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_dilution_tab(self) -> QWidget:
        """创建配液通道表格 - 原浓度改名, 通道ID改为通道序号"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 输入区 - 先输入参数再添加
        input_group = QGroupBox("新通道参数")
        input_layout = QFormLayout(input_group)
        
        self.dil_name_input = QLineEdit()
        self.dil_name_input.setPlaceholderText("输入溶液名称")
        input_layout.addRow("溶液名称:", self.dil_name_input)
        
        self.dil_conc_input = QDoubleSpinBox()
        self.dil_conc_input.setRange(0, 1000)
        self.dil_conc_input.setDecimals(2)
        self.dil_conc_input.setValue(1.00)
        input_layout.addRow("原浓度(mol/L):", self.dil_conc_input)
        
        self.dil_addr_input = QComboBox()
        self.dil_addr_input.addItems(self._get_pump_addresses())
        input_layout.addRow("泵地址:", self.dil_addr_input)
        
        self.dil_dir_input = QComboBox()
        self.dil_dir_input.addItems(["正向", "反向"])
        input_layout.addRow("方向:", self.dil_dir_input)
        
        self.dil_rpm_input = QSpinBox()
        self.dil_rpm_input.setRange(0, 1000)
        self.dil_rpm_input.setValue(120)
        input_layout.addRow("转速(RPM):", self.dil_rpm_input)
        
        self.dil_color_btn = QPushButton()
        self.dil_color_btn.setStyleSheet("background-color: #00FF00; border: 1px solid #ccc;")
        self.dil_color_btn.setFixedSize(80, 25)
        self.dil_color_btn.clicked.connect(self._on_select_dil_color)
        self.dil_current_color = "#00FF00"
        input_layout.addRow("颜色:", self.dil_color_btn)
        
        layout.addWidget(input_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加通道")
        add_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 16px;")
        add_btn.clicked.connect(self._add_dilution_channel)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("删除选中")
        del_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px;")
        del_btn.clicked.connect(self._delete_dilution_channel)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 表格列：通道(序号), 溶液名称, 原浓度(mol/L), 泵地址, 方向, 转速(RPM), 颜色
        self.dilution_table = QTableWidget()
        self.dilution_table.setColumnCount(7)
        self.dilution_table.setHorizontalHeaderLabels([
            "通道", "溶液名称", "原浓度(mol/L)", "泵地址", "方向", "转速(RPM)", "颜色"
        ])
        self.dilution_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dilution_table.setFont(FONT_NORMAL)
        layout.addWidget(self.dilution_table)
        
        return widget
    
    def _create_flush_tab(self) -> QWidget:
        """创建冲洗通道表格 - 增加工作类型列"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 输入区
        input_group = QGroupBox("新通道参数")
        input_layout = QFormLayout(input_group)
        
        self.flush_addr_input = QComboBox()
        self.flush_addr_input.addItems(self._get_pump_addresses())
        input_layout.addRow("泵地址:", self.flush_addr_input)
        
        self.flush_dir_input = QComboBox()
        self.flush_dir_input.addItems(["正向", "反向"])
        input_layout.addRow("方向:", self.flush_dir_input)
        
        self.flush_type_input = QComboBox()
        self.flush_type_input.addItems(["Inlet", "Transfer", "Outlet"])
        input_layout.addRow("工作类型:", self.flush_type_input)
        
        self.flush_rpm_input = QSpinBox()
        self.flush_rpm_input.setRange(0, 1000)
        self.flush_rpm_input.setValue(100)
        input_layout.addRow("转速(RPM):", self.flush_rpm_input)
        
        self.flush_duration_input = QDoubleSpinBox()
        self.flush_duration_input.setRange(0, 1000)
        self.flush_duration_input.setDecimals(2)
        self.flush_duration_input.setValue(30.00)
        input_layout.addRow("循环时长(秒):", self.flush_duration_input)
        
        layout.addWidget(input_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加通道")
        add_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 16px;")
        add_btn.clicked.connect(self._add_flush_channel)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("删除选中")
        del_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px;")
        del_btn.clicked.connect(self._delete_flush_channel)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 表格列：通道, 泵地址, 方向, 工作类型, 转速(RPM), 循环时长(s)
        self.flush_table = QTableWidget()
        self.flush_table.setColumnCount(6)
        self.flush_table.setHorizontalHeaderLabels([
            "通道", "泵地址", "方向", "工作类型", "转速(RPM)", "循环时长(s)"
        ])
        self.flush_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.flush_table.setFont(FONT_NORMAL)
        layout.addWidget(self.flush_table)
        
        return widget
    
    def _on_select_dil_color(self):
        """选择配液通道颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.dil_current_color = color.name()
            self.dil_color_btn.setStyleSheet(f"background-color: {self.dil_current_color}; border: 1px solid #ccc;")
    
    def _load_config(self):
        """加载配置到 UI"""
        self.port_combo.setCurrentText(self.config.rs485_port)
        self.baud_combo.setCurrentText(str(self.config.rs485_baudrate))
        self._refresh_dilution_table()
        self._refresh_flush_table()
    
    def _refresh_dilution_table(self):
        """刷新配液通道表格 - 参数可编辑"""
        self.dilution_table.setRowCount(len(self.config.dilution_channels))
        
        for row, channel in enumerate(self.config.dilution_channels):
            # 通道序号 (只读)
            seq_item = QTableWidgetItem(str(row + 1))
            seq_item.setFlags(seq_item.flags() & ~Qt.ItemIsEditable)
            seq_item.setTextAlignment(Qt.AlignCenter)
            self.dilution_table.setItem(row, 0, seq_item)
            
            # 溶液名称 (可编辑)
            name_item = QTableWidgetItem(channel.solution_name)
            name_item.setTextAlignment(Qt.AlignCenter)
            self.dilution_table.setItem(row, 1, name_item)
            
            # 原浓度 (可编辑)
            conc_spin = QDoubleSpinBox()
            conc_spin.setRange(0, 1000)
            conc_spin.setDecimals(2)
            conc_spin.setValue(channel.stock_concentration)
            conc_spin.valueChanged.connect(lambda val, r=row: self._on_dilution_param_changed(r, 'stock_concentration', val))
            self.dilution_table.setCellWidget(row, 2, conc_spin)
            
            # 泵地址 (可编辑下拉)
            addr_combo = QComboBox()
            addr_combo.addItems(self._get_pump_addresses())
            addr_combo.setCurrentText(str(channel.pump_address))
            addr_combo.currentTextChanged.connect(lambda val, r=row: self._on_dilution_param_changed(r, 'pump_address', int(val)))
            self.dilution_table.setCellWidget(row, 3, addr_combo)
            
            # 方向 (可编辑下拉)
            dir_combo = QComboBox()
            dir_combo.addItems(["正向", "反向"])
            dir_combo.setCurrentText("正向" if channel.direction == "FWD" else "反向")
            dir_combo.currentTextChanged.connect(lambda val, r=row: self._on_dilution_param_changed(r, 'direction', "FWD" if val == "正向" else "REV"))
            self.dilution_table.setCellWidget(row, 4, dir_combo)
            
            # 转速 (可编辑)
            rpm_spin = QSpinBox()
            rpm_spin.setRange(0, 1000)
            rpm_spin.setValue(channel.default_rpm)
            rpm_spin.valueChanged.connect(lambda val, r=row: self._on_dilution_param_changed(r, 'default_rpm', val))
            self.dilution_table.setCellWidget(row, 5, rpm_spin)
            
            # 颜色按钮
            color_btn = QPushButton()
            color_btn.setStyleSheet(f"background-color: {channel.color}; border: none;")
            color_btn.setFixedSize(60, 25)
            self.dilution_table.setCellWidget(row, 6, color_btn)
    
    def _on_dilution_param_changed(self, row: int, field: str, value):
        """配液通道参数变更"""
        if 0 <= row < len(self.config.dilution_channels):
            setattr(self.config.dilution_channels[row], field, value)
    
    def _refresh_flush_table(self):
        """刷新冲洗通道表格 - 参数可编辑"""
        self.flush_table.setRowCount(len(self.config.flush_channels))
        
        for row, channel in enumerate(self.config.flush_channels):
            # 通道序号 (只读)
            seq_item = QTableWidgetItem(str(row + 1))
            seq_item.setFlags(seq_item.flags() & ~Qt.ItemIsEditable)
            seq_item.setTextAlignment(Qt.AlignCenter)
            self.flush_table.setItem(row, 0, seq_item)
            
            # 泵地址 (可编辑下拉)
            addr_combo = QComboBox()
            addr_combo.addItems(self._get_pump_addresses())
            addr_combo.setCurrentText(str(channel.pump_address))
            addr_combo.currentTextChanged.connect(lambda val, r=row: self._on_flush_param_changed(r, 'pump_address', int(val)))
            self.flush_table.setCellWidget(row, 1, addr_combo)
            
            # 方向 (可编辑下拉)
            dir_combo = QComboBox()
            dir_combo.addItems(["正向", "反向"])
            dir_combo.setCurrentText("正向" if channel.direction == "FWD" else "反向")
            dir_combo.currentTextChanged.connect(lambda val, r=row: self._on_flush_param_changed(r, 'direction', "FWD" if val == "正向" else "REV"))
            self.flush_table.setCellWidget(row, 2, dir_combo)
            
            # 工作类型 (可编辑下拉)
            work_type = getattr(channel, 'work_type', 'Transfer')
            type_combo = QComboBox()
            type_combo.addItems(["Inlet", "Transfer", "Outlet"])
            type_combo.setCurrentText(work_type)
            type_combo.currentTextChanged.connect(lambda val, r=row: self._on_flush_param_changed(r, 'work_type', val))
            self.flush_table.setCellWidget(row, 3, type_combo)
            
            # 转速 (可编辑)
            rpm_spin = QSpinBox()
            rpm_spin.setRange(0, 1000)
            rpm_spin.setValue(channel.rpm)
            rpm_spin.valueChanged.connect(lambda val, r=row: self._on_flush_param_changed(r, 'rpm', val))
            self.flush_table.setCellWidget(row, 4, rpm_spin)
            
            # 循环时长 (可编辑)
            dur_spin = QDoubleSpinBox()
            dur_spin.setRange(0, 1000)
            dur_spin.setDecimals(2)
            dur_spin.setValue(channel.cycle_duration_s)
            dur_spin.valueChanged.connect(lambda val, r=row: self._on_flush_param_changed(r, 'cycle_duration_s', val))
            self.flush_table.setCellWidget(row, 5, dur_spin)
    
    def _on_flush_param_changed(self, row: int, field: str, value):
        """冲洗通道参数变更"""
        if 0 <= row < len(self.config.flush_channels):
            setattr(self.config.flush_channels[row], field, value)
    
    def _add_dilution_channel(self):
        """添加配液通道 - 使用输入框的值"""
        name = self.dil_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入溶液名称")
            return
        
        new_channel = DilutionChannel(
            channel_id=str(len(self.config.dilution_channels) + 1),
            solution_name=name,
            stock_concentration=round(self.dil_conc_input.value(), 2),
            pump_address=int(self.dil_addr_input.currentText()),
            direction="FWD" if self.dil_dir_input.currentText() == "正向" else "REV",
            default_rpm=self.dil_rpm_input.value(),
            color=self.dil_current_color
        )
        self.config.dilution_channels.append(new_channel)
        self._refresh_dilution_table()
        
        # 清空输入
        self.dil_name_input.clear()
    
    def _delete_dilution_channel(self):
        """删除配液通道"""
        row = self.dilution_table.currentRow()
        if row >= 0 and row < len(self.config.dilution_channels):
            del self.config.dilution_channels[row]
            self._refresh_dilution_table()
    
    def _add_flush_channel(self):
        """添加冲洗通道 - 使用输入框的值"""
        new_channel = FlushChannel(
            channel_id=str(len(self.config.flush_channels) + 1),
            pump_name=f"冲洗泵{len(self.config.flush_channels) + 1}",
            pump_address=int(self.flush_addr_input.currentText()),
            direction="FWD" if self.flush_dir_input.currentText() == "正向" else "REV",
            work_type=self.flush_type_input.currentText(),
            rpm=self.flush_rpm_input.value(),
            cycle_duration_s=round(self.flush_duration_input.value(), 2)
        )
        self.config.flush_channels.append(new_channel)
        self._refresh_flush_table()
    
    def _delete_flush_channel(self):
        """删除冲洗通道"""
        row = self.flush_table.currentRow()
        if row >= 0 and row < len(self.config.flush_channels):
            del self.config.flush_channels[row]
            self._refresh_flush_table()
    
    def _on_connect(self):
        """连接/断开 RS485 - 后端接口调用点"""
        if self.rs485.is_connected():
            self.rs485.close_port()
            self.connect_btn.setText("连接")
            self.scan_btn.setEnabled(False)
        else:
            port = self.port_combo.currentText()
            baud = int(self.baud_combo.currentText())
            if self.rs485.open_port(port, baud):
                self.connect_btn.setText("断开")
                self.scan_btn.setEnabled(True)
                QMessageBox.information(self, "成功", f"已连接到 {port}")
            else:
                QMessageBox.critical(self, "错误", f"无法连接到 {port}")
    
    def _on_scan(self):
        """扫描泵 - 后端接口调用点"""
        if not self.rs485.is_connected():
            QMessageBox.warning(self, "警告", "串口未连接")
            return
        
        available = self.rs485.scan_pumps()
        msg = f"扫描完成，找到泵地址: {available}" if available else "未找到任何泵"
        QMessageBox.information(self, "扫描结果", msg)
    
    def _on_save(self):
        """保存配置"""
        self.config.rs485_port = self.port_combo.currentText()
        self.config.rs485_baudrate = int(self.baud_combo.currentText())
        
        # 保存到文件
        self.config.save_to_file("./config/system.json")
        self.config_saved.emit(self.config)
        QMessageBox.information(self, "成功", "配置已保存")
        self.accept()

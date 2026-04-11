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
    QGroupBox, QFormLayout, QCheckBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QCursor

from src.models import SystemConfig, DilutionChannel, FlushChannel
from src.services.rs485_wrapper import get_rs485_instance
from src.services.i18n import tr, get_lang, set_lang


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
    
    def showEvent(self, event):
        """对话框显示时更新UI状态"""
        super().showEvent(event)
        # 更新连接按钮状态
        if self.rs485.is_connected():
            self.connect_btn.setText("断开")
            self.scan_btn.setEnabled(True)
        else:
            self.connect_btn.setText("连接")
            self.scan_btn.setEnabled(False)
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # RS485 连接区
        conn_group = QGroupBox("RS485 连接")
        conn_group.setFont(FONT_TITLE)
        conn_layout = QHBoxLayout(conn_group)
        conn_layout.addWidget(QLabel("端口:"))
        self.port_combo = QComboBox()
        
        # 加载实际检测到的串口（带超时保护，避免USB异常时卡死）
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.rs485.list_available_ports)
                available_ports = future.result(timeout=3)
        except Exception:
            available_ports = []
        if available_ports:
            self.port_combo.addItems(available_ports)
        else:
            # 如果检测失败/超时，提供默认选项
            self.port_combo.addItems(['COM1', 'COM2', 'COM3', 'COM4', 'COM5'])
        
        conn_layout.addWidget(self.port_combo)
        
        # 刷新端口按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setMaximumWidth(40)
        refresh_btn.setToolTip("刷新端口列表")
        refresh_btn.clicked.connect(self._on_refresh_ports)
        conn_layout.addWidget(refresh_btn)
        
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
        
        # Mock模式开关
        self.mock_checkbox = QCheckBox("Mock模式 (开发测试)")
        self.mock_checkbox.setFont(FONT_NORMAL)
        self.mock_checkbox.setChecked(True)  # 默认开启Mock
        self.mock_checkbox.setToolTip("勾选=模拟硬件(测试)\n取消勾选=真实硬件")
        self.mock_checkbox.stateChanged.connect(self._on_mock_mode_changed)
        conn_layout.addWidget(self.mock_checkbox)
        
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
        
        # 语言设置
        lang_group = QGroupBox(tr("language"))
        lang_group.setFont(FONT_TITLE)
        lang_layout = QHBoxLayout(lang_group)
        lang_layout.addWidget(QLabel(tr("language") + ":"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("简体中文", "zh")
        self.lang_combo.addItem("English", "en")
        cur = get_lang()
        self.lang_combo.setCurrentIndex(0 if cur == "zh" else 1)
        self.lang_combo.setFixedWidth(160)
        lang_layout.addWidget(self.lang_combo)
        lang_layout.addStretch()
        layout.addWidget(lang_group)
        
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
        self.dil_rpm_input.setRange(0, 300)
        self.dil_rpm_input.setValue(120)
        input_layout.addRow("转速(RPM):", self.dil_rpm_input)
        
        self.dil_tube_input = QDoubleSpinBox()
        self.dil_tube_input.setRange(0.1, 10.0)
        self.dil_tube_input.setDecimals(2)
        self.dil_tube_input.setSingleStep(0.1)
        self.dil_tube_input.setValue(1.0)
        input_layout.addRow("管道内径(mm):", self.dil_tube_input)
        
        self.dil_color_btn = QPushButton()
        self.dil_color_btn.setStyleSheet("background-color: #00FF00; border: 1px solid #ccc;")
        self.dil_color_btn.setFixedSize(80, 25)
        self.dil_color_btn.clicked.connect(self._on_select_dil_color)
        self.dil_current_color = "#00FF00"
        input_layout.addRow("颜色:", self.dil_color_btn)
        
        self.dil_volume_input = QDoubleSpinBox()
        self.dil_volume_input.setRange(0, 10000)
        self.dil_volume_input.setDecimals(1)
        self.dil_volume_input.setSingleStep(1.0)
        self.dil_volume_input.setValue(50.0)
        self.dil_volume_input.setSuffix(" mL")
        input_layout.addRow("原液总量(mL):", self.dil_volume_input)
        
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
        
        # 表格列：通道(序号), 溶液名称, 原浓度(mol/L), 泵地址, 方向, 转速(RPM), 管道内径(mm), 原液总量(mL), 颜色
        self.dilution_table = QTableWidget()
        self.dilution_table.setColumnCount(9)
        self.dilution_table.setHorizontalHeaderLabels([
            "通道", "溶液名称", "原浓度(mol/L)", "泵地址", "方向", "转速(RPM)", "管道内径(mm)", "原液总量(mL)", "颜色"
        ])
        self.dilution_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dilution_table.setFont(FONT_NORMAL)
        self.dilution_table.setMinimumHeight(200)  # 预留约5行通道高度
        self.dilution_table.itemChanged.connect(self._on_dilution_item_changed)
        layout.addWidget(self.dilution_table, 1)  # stretch=1 让表格占据剩余空间
        
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
        self.flush_rpm_input.setRange(0, 300)
        self.flush_rpm_input.setValue(100)
        input_layout.addRow("转速(RPM):", self.flush_rpm_input)
        
        self.flush_volume_input = QLineEdit()
        self.flush_volume_input.setPlaceholderText("输入数字或 inf")
        self.flush_volume_input.setText("inf")
        input_layout.addRow("原液总量(mL):", self.flush_volume_input)
        
        self.flush_tube_input = QDoubleSpinBox()
        self.flush_tube_input.setRange(0.1, 10.0)
        self.flush_tube_input.setDecimals(2)
        self.flush_tube_input.setSingleStep(0.1)
        self.flush_tube_input.setValue(1.0)
        input_layout.addRow("管道内径(mm):", self.flush_tube_input)
        
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
        
        # 表格列：通道, 泵地址, 方向, 工作类型, 转速(RPM), 原液总量(mL), 管道内径(mm)
        self.flush_table = QTableWidget()
        self.flush_table.setColumnCount(7)
        self.flush_table.setHorizontalHeaderLabels([
            "通道", "泵地址", "方向", "工作类型", "转速(RPM)", "原液总量(mL)", "管道内径(mm)"
        ])
        self.flush_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.flush_table.setFont(FONT_NORMAL)
        self.flush_table.setMinimumHeight(160)
        layout.addWidget(self.flush_table, 1)
        
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
        
        # 加载Mock模式状态 - 阻止signal触发避免重复操作导致卡顿
        self.mock_checkbox.blockSignals(True)
        self.mock_checkbox.setChecked(self.config.mock_mode)
        self.mock_checkbox.blockSignals(False)
        
        self._refresh_dilution_table()
        self._refresh_flush_table()
        
        # 更新连接状态显示
        if self.rs485.is_connected():
            self.connect_btn.setText("断开")
            self.scan_btn.setEnabled(True)
        else:
            self.connect_btn.setText("连接")
            self.scan_btn.setEnabled(False)
    
    def _refresh_dilution_table(self):
        """刷新配液通道表格 - 参数可编辑"""
        self.dilution_table.blockSignals(True)
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
            rpm_spin.setRange(0, 300)
            rpm_spin.setValue(channel.default_rpm)
            rpm_spin.valueChanged.connect(lambda val, r=row: self._on_dilution_param_changed(r, 'default_rpm', val))
            self.dilution_table.setCellWidget(row, 5, rpm_spin)
            
            # 管道内径 (可编辑)
            tube_spin = QDoubleSpinBox()
            tube_spin.setRange(0.1, 10.0)
            tube_spin.setDecimals(2)
            tube_spin.setSingleStep(0.1)
            tube_spin.setValue(channel.tube_diameter_mm)
            tube_spin.valueChanged.connect(lambda val, r=row: self._on_dilution_param_changed(r, 'tube_diameter_mm', val))
            self.dilution_table.setCellWidget(row, 6, tube_spin)
            
            # 原液总量 (可编辑)
            vol_spin = QDoubleSpinBox()
            vol_spin.setRange(0, 10000)
            vol_spin.setDecimals(1)
            vol_spin.setSingleStep(1.0)
            vol_spin.setSuffix(" mL")
            vol_spin.setValue(channel.total_volume_ml)
            vol_spin.valueChanged.connect(lambda val, r=row: self._on_volume_changed(r, val))
            self.dilution_table.setCellWidget(row, 7, vol_spin)
            
            # 颜色按钮
            color_btn = QPushButton()
            color_btn.setStyleSheet(f"background-color: {channel.color}; border: none;")
            color_btn.setFixedSize(60, 25)
            self.dilution_table.setCellWidget(row, 8, color_btn)
        
        self.dilution_table.blockSignals(False)
    
    def _on_dilution_item_changed(self, item: QTableWidgetItem):
        """配液通道表格单元格编辑回调 - 用于溶液名称列"""
        if item.column() == 1:  # 溶液名称列
            row = item.row()
            if 0 <= row < len(self.config.dilution_channels):
                self.config.dilution_channels[row].solution_name = item.text()
    
    def _on_dilution_param_changed(self, row: int, field: str, value):
        """配液通道参数变更"""
        if 0 <= row < len(self.config.dilution_channels):
            # 泵地址变更时检查冲突
            if field == 'pump_address':
                new_addr = value
                # 检查配液通道中是否有冲突（排除当前行）
                for i, ch in enumerate(self.config.dilution_channels):
                    if i != row and ch.pump_address == new_addr:
                        QMessageBox.warning(
                            self, "泵地址冲突",
                            f"泵地址 {new_addr} 已被配液通道 '{ch.solution_name}' 使用！\n"
                            f"请选择其他地址。"
                        )
                        # 恢复原来的值
                        old_addr = self.config.dilution_channels[row].pump_address
                        combo = self.dilution_table.cellWidget(row, 3)
                        if combo:
                            combo.blockSignals(True)
                            combo.setCurrentText(str(old_addr))
                            combo.blockSignals(False)
                        return
                # 检查冲洗通道中是否有冲突
                for ch in self.config.flush_channels:
                    if ch.pump_address == new_addr:
                        work_type = getattr(ch, 'work_type', '')
                        QMessageBox.warning(
                            self, "泵地址冲突",
                            f"泵地址 {new_addr} 已被冲洗通道 ({work_type}) 使用！\n"
                            f"请选择其他地址。"
                        )
                        old_addr = self.config.dilution_channels[row].pump_address
                        combo = self.dilution_table.cellWidget(row, 3)
                        if combo:
                            combo.blockSignals(True)
                            combo.setCurrentText(str(old_addr))
                            combo.blockSignals(False)
                        return
            setattr(self.config.dilution_channels[row], field, value)
    
    def _on_volume_changed(self, row: int, value: float):
        """配液通道原液总量变更 - 同时更新剩余量"""
        if 0 <= row < len(self.config.dilution_channels):
            ch = self.config.dilution_channels[row]
            old_total = ch.total_volume_ml
            ch.total_volume_ml = value
            # 如果原来没配置总量(0)或者是增大总量，同步更新剩余量
            if old_total == 0 or ch.remaining_volume_ml <= 0:
                ch.remaining_volume_ml = value
            elif value > old_total:
                # 增大总量：剩余量也增加同样的差值
                ch.remaining_volume_ml += (value - old_total)
            elif value < ch.remaining_volume_ml:
                # 缩小总量：剩余量不能超过总量
                ch.remaining_volume_ml = value
    
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
            rpm_spin.setRange(0, 300)
            rpm_spin.setValue(channel.rpm)
            rpm_spin.valueChanged.connect(lambda val, r=row: self._on_flush_param_changed(r, 'rpm', val))
            self.flush_table.setCellWidget(row, 4, rpm_spin)
            
            # 原液总量 (可编辑, 支持 inf)
            vol_edit = QLineEdit()
            vol_val = getattr(channel, 'total_volume_ml', float('inf'))
            vol_edit.setText("inf" if vol_val == float('inf') else f"{vol_val:.2f}")
            vol_edit.setAlignment(Qt.AlignCenter)
            vol_edit.editingFinished.connect(
                lambda r=row, le=vol_edit: self._on_flush_volume_changed(r, le)
            )
            self.flush_table.setCellWidget(row, 5, vol_edit)
            
            # 管道内径 (可编辑)
            tube_spin = QDoubleSpinBox()
            tube_spin.setRange(0.1, 10.0)
            tube_spin.setDecimals(2)
            tube_spin.setSingleStep(0.1)
            tube_spin.setValue(channel.tube_diameter_mm)
            tube_spin.valueChanged.connect(lambda val, r=row: self._on_flush_param_changed(r, 'tube_diameter_mm', val))
            self.flush_table.setCellWidget(row, 6, tube_spin)
    
    def _on_flush_param_changed(self, row: int, field: str, value):
        """冲洗通道参数变更"""
        if 0 <= row < len(self.config.flush_channels):
            # 泵地址变更时检查冲突
            if field == 'pump_address':
                new_addr = value
                # 检查冲洗通道中是否有冲突（排除当前行）
                for i, ch in enumerate(self.config.flush_channels):
                    if i != row and ch.pump_address == new_addr:
                        work_type = getattr(ch, 'work_type', '')
                        QMessageBox.warning(
                            self, "泵地址冲突",
                            f"泵地址 {new_addr} 已被冲洗通道 ({work_type}) 使用！\n"
                            f"请选择其他地址。"
                        )
                        old_addr = self.config.flush_channels[row].pump_address
                        combo = self.flush_table.cellWidget(row, 1)
                        if combo:
                            combo.blockSignals(True)
                            combo.setCurrentText(str(old_addr))
                            combo.blockSignals(False)
                        return
                # 检查配液通道中是否有冲突
                for ch in self.config.dilution_channels:
                    if ch.pump_address == new_addr:
                        QMessageBox.warning(
                            self, "泵地址冲突",
                            f"泵地址 {new_addr} 已被配液通道 '{ch.solution_name}' 使用！\n"
                            f"请选择其他地址。"
                        )
                        old_addr = self.config.flush_channels[row].pump_address
                        combo = self.flush_table.cellWidget(row, 1)
                        if combo:
                            combo.blockSignals(True)
                            combo.setCurrentText(str(old_addr))
                            combo.blockSignals(False)
                        return
            # 工作类型变更时检查重复
            if field == 'work_type':
                for i, ch in enumerate(self.config.flush_channels):
                    if i != row and getattr(ch, 'work_type', '') == value:
                        QMessageBox.warning(
                            self, "工作类型冲突",
                            f"工作类型 '{value}' 已被其他冲洗通道使用！\n"
                            f"每种工作类型只能配置一次。"
                        )
                        old_type = getattr(self.config.flush_channels[row], 'work_type', 'Transfer')
                        combo = self.flush_table.cellWidget(row, 3)
                        if combo:
                            combo.blockSignals(True)
                            combo.setCurrentText(old_type)
                            combo.blockSignals(False)
                        return
            setattr(self.config.flush_channels[row], field, value)
    
    def _on_flush_volume_changed(self, row: int, line_edit: QLineEdit):
        """冲洗通道原液总量变更 — 支持 inf"""
        if 0 <= row < len(self.config.flush_channels):
            ch = self.config.flush_channels[row]
            text = line_edit.text().strip().lower()
            if text in ('inf', '∞', ''):
                ch.total_volume_ml = float('inf')
                ch.remaining_volume_ml = 0.0
                line_edit.setText("inf")
            else:
                try:
                    val = float(text)
                    if val < 0:
                        QMessageBox.warning(self, "警告", "原液总量不能为负数")
                        old = ch.total_volume_ml
                        line_edit.setText("inf" if old == float('inf') else f"{old:.2f}")
                        return
                    old_total = ch.total_volume_ml
                    ch.total_volume_ml = val
                    # 同步 remaining_volume_ml（首次设置或增大容量时自动补齐）
                    if old_total in (0, float('inf')) or ch.remaining_volume_ml <= 0:
                        ch.remaining_volume_ml = val
                    elif val > old_total:
                        ch.remaining_volume_ml += (val - old_total)
                    elif val < ch.remaining_volume_ml:
                        ch.remaining_volume_ml = val
                except ValueError:
                    QMessageBox.warning(self, "警告", "请输入有效数字或 inf")
                    old = ch.total_volume_ml
                    line_edit.setText("inf" if old == float('inf') else f"{old:.2f}")
    
    def _get_used_pump_addresses(self) -> set:
        """获取所有已被配置的泵地址（配液+冲洗）"""
        used = set()
        for ch in self.config.dilution_channels:
            used.add(ch.pump_address)
        for ch in self.config.flush_channels:
            used.add(ch.pump_address)
        return used
    
    def _get_used_flush_work_types(self) -> set:
        """获取所有已被配置的冲洗工作类型"""
        used = set()
        for ch in self.config.flush_channels:
            used.add(ch.work_type)
        return used
    
    def _add_dilution_channel(self):
        """添加配液通道 - 使用输入框的值"""
        name = self.dil_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入溶液名称")
            return
        
        # 检查泵地址是否已被使用
        pump_addr = int(self.dil_addr_input.currentText())
        used_addrs = self._get_used_pump_addresses()
        if pump_addr in used_addrs:
            QMessageBox.warning(self, "警告", f"泵地址 {pump_addr} 已被配置，请选择其他地址")
            return
        
        new_channel = DilutionChannel(
            channel_id=str(len(self.config.dilution_channels) + 1),
            solution_name=name,
            stock_concentration=round(self.dil_conc_input.value(), 2),
            pump_address=pump_addr,
            direction="FWD" if self.dil_dir_input.currentText() == "正向" else "REV",
            default_rpm=self.dil_rpm_input.value(),
            color=self.dil_current_color,
            tube_diameter_mm=round(self.dil_tube_input.value(), 2),
            total_volume_ml=round(self.dil_volume_input.value(), 1),
            remaining_volume_ml=round(self.dil_volume_input.value(), 1),
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
        # 检查泵地址是否已被使用
        pump_addr = int(self.flush_addr_input.currentText())
        used_addrs = self._get_used_pump_addresses()
        if pump_addr in used_addrs:
            QMessageBox.warning(self, "警告", f"泵地址 {pump_addr} 已被配置，请选择其他地址")
            return
        
        # 检查工作类型是否已被配置
        work_type = self.flush_type_input.currentText()
        used_types = self._get_used_flush_work_types()
        if work_type in used_types:
            QMessageBox.warning(self, "警告", f"工作类型 '{work_type}' 已被配置，每种类型只能配置一次")
            return
        
        # 解析原液总量
        vol_text = self.flush_volume_input.text().strip().lower()
        if vol_text in ('inf', '', '∞'):
            total_volume_ml = float('inf')
        else:
            try:
                total_volume_ml = float(vol_text)
                if total_volume_ml < 0:
                    QMessageBox.warning(self, "警告", "原液总量不能为负数")
                    return
            except ValueError:
                QMessageBox.warning(self, "警告", "请输入有效数字或 inf")
                return
        
        new_channel = FlushChannel(
            channel_id=str(len(self.config.flush_channels) + 1),
            pump_name=f"冲洗泵{len(self.config.flush_channels) + 1}",
            pump_address=pump_addr,
            direction="FWD" if self.flush_dir_input.currentText() == "正向" else "REV",
            work_type=work_type,
            rpm=self.flush_rpm_input.value(),
            total_volume_ml=total_volume_ml,
            tube_diameter_mm=round(self.flush_tube_input.value(), 2)
        )
        self.config.flush_channels.append(new_channel)
        self._refresh_flush_table()
    
    def _delete_flush_channel(self):
        """删除冲洗通道"""
        row = self.flush_table.currentRow()
        if row >= 0 and row < len(self.config.flush_channels):
            del self.config.flush_channels[row]
            self._refresh_flush_table()
    
    def _on_refresh_ports(self):
        """刷新端口列表"""
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.rs485.list_available_ports)
                available_ports = future.result(timeout=3)
        except Exception:
            available_ports = []
        
        if available_ports:
            self.port_combo.addItems(available_ports)
            # 尝试恢复之前选择的端口
            index = self.port_combo.findText(current_port)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
            print(f"✅ 刷新端口列表: {available_ports}")
        else:
            self.port_combo.addItems(['COM1', 'COM2', 'COM3'])
            QMessageBox.warning(self, "警告", "未检测到可用串口")
    
    def _on_connect(self):
        """连接/断开 RS485 - 后端接口调用点"""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
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
        except Exception as e:
            QMessageBox.critical(self, "错误", f"RS485 操作异常: {e}")
        finally:
            QApplication.restoreOverrideCursor()
    
    def _on_scan(self):
        """扫描泵 - 后端接口调用点"""
        if not self.rs485.is_connected():
            QMessageBox.warning(self, "警告", "串口未连接")
            return
        
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            available = self.rs485.scan_pumps()
            msg = f"扫描完成，找到泵地址: {available}" if available else "未找到任何泵"
        except Exception as e:
            msg = f"扫描异常: {e}"
        finally:
            QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "扫描结果", msg)
    
    def _on_mock_mode_changed(self, state):
        """Mock模式切换"""
        is_mock = (state == 2)  # Qt.Checked = 2
        
        # 记住当前连接状态
        was_connected = self.rs485.is_connected()
        port = self.port_combo.currentText()
        baud = int(self.baud_combo.currentText())
        
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            # 先断开旧连接（避免在set_mock_mode内部触发）
            if was_connected:
                try:
                    self.rs485.close_port()
                except Exception:
                    pass
            
            # 设置新模式
            self.rs485.set_mock_mode(is_mock)
            
            # 如果之前已连接，需要用新模式重新连接
            if was_connected:
                if self.rs485.open_port(port, baud):
                    mode_str = "Mock模式 (模拟)" if is_mock else "真实硬件模式"
                    print(f"✅ 已切换到 {mode_str}")
                    self.connect_btn.setText("断开")
                    self.scan_btn.setEnabled(True)
                else:
                    self.connect_btn.setText("连接")
                    self.scan_btn.setEnabled(False)
                    mode_str = "Mock模式 (模拟)" if is_mock else "真实硬件模式"
                    QMessageBox.warning(self, "警告", f"切换到{mode_str}后重连失败")
        except Exception as e:
            print(f"❌ Mock模式切换异常: {e}")
        finally:
            QApplication.restoreOverrideCursor()
    
    def _on_save(self):
        """保存配置"""
        self.config.rs485_port = self.port_combo.currentText()
        self.config.rs485_baudrate = int(self.baud_combo.currentText())
        self.config.mock_mode = self.mock_checkbox.isChecked()
        
        # 整体校验泵地址冲突
        all_addrs = {}
        for i, ch in enumerate(self.config.dilution_channels):
            addr = ch.pump_address
            label = f"配液通道 '{ch.solution_name}'"
            if addr in all_addrs:
                QMessageBox.critical(
                    self, "泵地址冲突",
                    f"泵地址 {addr} 同时被 {all_addrs[addr]} 和 {label} 使用！\n"
                    f"请修正后再保存。"
                )
                return
            all_addrs[addr] = label
        for i, ch in enumerate(self.config.flush_channels):
            addr = ch.pump_address
            work_type = getattr(ch, 'work_type', '')
            label = f"冲洗通道 ({work_type})"
            if addr in all_addrs:
                QMessageBox.critical(
                    self, "泵地址冲突",
                    f"泵地址 {addr} 同时被 {all_addrs[addr]} 和 {label} 使用！\n"
                    f"请修正后再保存。"
                )
                return
            all_addrs[addr] = label
        
        # 保存到文件
        self.config.save()
        
        # 保存语言设置
        new_lang = self.lang_combo.currentData()
        old_lang = get_lang()
        if new_lang != old_lang:
            set_lang(new_lang)
        
        self.config_saved.emit(self.config)
        QMessageBox.information(self, "成功", "配置已保存")
        self.accept()

"""Configuration dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QSpinBox,
    QDoubleSpinBox, QFormLayout, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt


class ConfigDialog(QDialog):
    """配置对话框（General/Channel/Flush/Display）。"""
    
    def __init__(self, settings_service=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置")
        self.setGeometry(100, 100, 900, 600)
        self.settings_service = settings_service
        self._create_widgets()
        self._load_settings()
    
    def _create_widgets(self) -> None:
        """创建控件。"""
        layout = QVBoxLayout(self)
        
        # 选项卡
        self.tabs = QTabWidget()
        
        # General 选项卡
        self._create_general_tab()
        
        # Channel 选项卡
        self._create_channel_tab()
        
        # Flush 选项卡
        self._create_flush_tab()
        
        # Display 选项卡
        self._create_display_tab()
        
        layout.addWidget(self.tabs)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("应用")
        self.btn_ok = QPushButton("确定")
        self.btn_cancel = QPushButton("取消")
        
        self.btn_apply.clicked.connect(self._apply_settings)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
    
    def _create_general_tab(self) -> None:
        """创建 General 选项卡。"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # 语言选择
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文 (ZH-CN)", "English (EN-US)"])
        layout.addRow("语言", self.language_combo)
        
        # RS485 端口选择
        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4"])
        self.port_combo.currentTextChanged.connect(self._on_port_changed)
        layout.addRow("RS485 端口", self.port_combo)
        
        # 波特率
        self.baudrate_spin = QSpinBox()
        self.baudrate_spin.setMinimum(9600)
        self.baudrate_spin.setMaximum(115200)
        self.baudrate_spin.setValue(9600)
        layout.addRow("波特率", self.baudrate_spin)
        
        # 数据路径
        self.data_path_edit = QLineEdit()
        self.data_path_edit.setText("./data")
        layout.addRow("数据路径", self.data_path_edit)
        
        # 错误时停止
        self.stop_on_error_checkbox = QCheckBox("错误时停止实验")
        layout.addRow("选项", self.stop_on_error_checkbox)
        
        self.tabs.addTab(widget, "常规")
    
    def _create_channel_tab(self) -> None:
        """创建 Channel 选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 通道表
        self.channel_table = QTableWidget()
        self.channel_table.setColumnCount(6)
        self.channel_table.setHorizontalHeaderLabels([
            "通道名称", "浓度 (M)", "泵转速 (RPM)", "地址", "颜色", "删除"
        ])
        self.channel_table.setRowCount(3)
        
        # 添加示例行
        for row in range(3):
            self.channel_table.setItem(row, 0, QTableWidgetItem(f"通道 {row+1}"))
            self.channel_table.setItem(row, 1, QTableWidgetItem("1.0"))
            self.channel_table.setItem(row, 2, QTableWidgetItem("100"))
            self.channel_table.setItem(row, 3, QTableWidgetItem(str(row+1)))
            self.channel_table.setItem(row, 4, QTableWidgetItem("■"))
            
            btn_del = QPushButton("删除")
            self.channel_table.setCellWidget(row, 5, btn_del)
        
        layout.addWidget(self.channel_table)
        
        # 添加按钮
        btn_add_channel = QPushButton("添加通道")
        layout.addWidget(btn_add_channel)
        
        self.tabs.addTab(widget, "通道")
    
    def _create_flush_tab(self) -> None:
        """创建 Flush 选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 冲洗设置表
        self.flush_table = QTableWidget()
        self.flush_table.setColumnCount(6)
        self.flush_table.setHorizontalHeaderLabels([
            "泵角色", "RPM", "方向", "地址", "周期 (s)", "删除"
        ])
        self.flush_table.setRowCount(2)
        
        # 添加示例行
        for row in range(2):
            self.flush_table.setItem(row, 0, QTableWidgetItem(f"冲洗泵 {row+1}"))
            self.flush_table.setItem(row, 1, QTableWidgetItem("200"))
            self.flush_table.setItem(row, 2, QTableWidgetItem("正向"))
            self.flush_table.setItem(row, 3, QTableWidgetItem(str(row+10)))
            self.flush_table.setItem(row, 4, QTableWidgetItem("10"))
            
            btn_del = QPushButton("删除")
            self.flush_table.setCellWidget(row, 5, btn_del)
        
        layout.addWidget(self.flush_table)
        
        self.tabs.addTab(widget, "冲洗")
    
    def _create_display_tab(self) -> None:
        """创建 Display 选项卡。"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("颜色映射设置"))
        
        # 颜色选择表
        color_table = QTableWidget()
        color_table.setColumnCount(2)
        color_table.setHorizontalHeaderLabels(["溶液类型", "颜色"])
        color_table.setRowCount(3)
        
        solutions = ["溶液A", "溶液B", "溶液C"]
        colors = ["红色", "绿色", "蓝色"]
        
        for row, (sol, color) in enumerate(zip(solutions, colors)):
            color_table.setItem(row, 0, QTableWidgetItem(sol))
            color_table.setItem(row, 1, QTableWidgetItem(color))
        
        layout.addWidget(color_table)
        
        self.tabs.addTab(widget, "显示")
    
    def _on_port_changed(self) -> None:
        """端口改变时刷新通道地址列表。"""
        port = self.port_combo.currentText()
        print(f"[ConfigDialog] Port changed to {port}, refreshing address list...")
        # 这里可以触发扫描或更新地址列表
    
    def _load_settings(self) -> None:
        """从 SettingsService 加载设置。"""
        if not self.settings_service:
            return
        
        lang = self.settings_service.get("language", "zh_CN")
        self.language_combo.setCurrentIndex(0 if lang == "zh_CN" else 1)
        
        port = self.settings_service.get("rs485_port", "COM1")
        self.port_combo.setCurrentText(port)
        
        baudrate = self.settings_service.get("rs485_baudrate", 9600)
        self.baudrate_spin.setValue(baudrate)
        
        data_path = self.settings_service.get("data_path", "./data")
        self.data_path_edit.setText(data_path)
        
        stop_on_error = self.settings_service.get("stop_on_error", False)
        self.stop_on_error_checkbox.setChecked(stop_on_error)
    
    def _apply_settings(self) -> None:
        """应用设置。"""
        if not self.settings_service:
            return
        
        lang = "zh_CN" if self.language_combo.currentIndex() == 0 else "en_US"
        self.settings_service.set("language", lang)
        self.settings_service.set("rs485_port", self.port_combo.currentText())
        self.settings_service.set("rs485_baudrate", self.baudrate_spin.value())
        self.settings_service.set("data_path", self.data_path_edit.text())
        self.settings_service.set("stop_on_error", self.stop_on_error_checkbox.isChecked())
        
        QMessageBox.information(self, "成功", "设置已应用")

"""
配置对话 - 系统设置、泵配置、通道管理
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QWidget, QColorDialog,
    QMessageBox, QSpinBox, QDoubleSpinBox, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from src.models import SystemConfig, DilutionChannel, FlushChannel
from src.services.rs485_wrapper import get_rs485_instance
import time


class ConfigDialog(QDialog):
    """配置对话框"""
    config_saved = Signal(SystemConfig)
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.rs485 = get_rs485_instance()
        self.setWindowTitle("系统配置")
        self.setGeometry(100, 100, 1000, 600)
        self._init_ui()
        self._load_config()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # RS485 连接区
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("RS485 端口:"))
        self.port_combo = QComboBox()
        self.port_combo.addItems(['COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6'])
        conn_layout.addWidget(self.port_combo)
        
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self._on_connect)
        conn_layout.addWidget(self.connect_btn)
        
        self.scan_btn = QPushButton("扫描泵")
        self.scan_btn.clicked.connect(self._on_scan)
        self.scan_btn.setEnabled(False)
        conn_layout.addWidget(self.scan_btn)
        
        layout.addLayout(conn_layout)
        
        # Tab 页
        self.tab_widget = QTabWidget()
        
        # 配液通道 Tab
        self.dilution_tab = self._create_dilution_tab()
        self.tab_widget.addTab(self.dilution_tab, "配液通道")
        
        # 冲洗通道 Tab
        self.flush_tab = self._create_flush_tab()
        self.tab_widget.addTab(self.flush_tab, "冲洗通道")
        
        layout.addWidget(self.tab_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _create_dilution_tab(self) -> QWidget:
        """创建配液通道表格"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.dilution_table = QTableWidget()
        self.dilution_table.setColumnCount(7)
        self.dilution_table.setHorizontalHeaderLabels([
            "通道ID", "溶液名", "浓度(mol/L)", "泵地址", "方向", "默认转速(RPM)", "颜色"
        ])
        self.dilution_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 添加按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加通道")
        add_btn.clicked.connect(self._add_dilution_channel)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("删除选中行")
        del_btn.clicked.connect(self._delete_dilution_channel)
        btn_layout.addWidget(del_btn)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.dilution_table)
        widget.setLayout(layout)
        return widget
    
    def _create_flush_tab(self) -> QWidget:
        """创建冲洗通道表格"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.flush_table = QTableWidget()
        self.flush_table.setColumnCount(6)
        self.flush_table.setHorizontalHeaderLabels([
            "通道ID", "泵名", "泵地址", "方向", "转速(RPM)", "循环时长(s)"
        ])
        self.flush_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加通道")
        add_btn.clicked.connect(self._add_flush_channel)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("删除选中行")
        del_btn.clicked.connect(self._delete_flush_channel)
        btn_layout.addWidget(del_btn)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.flush_table)
        widget.setLayout(layout)
        return widget
    
    def _load_config(self):
        """加载配置到 UI"""
        self.port_combo.setCurrentText(self.config.rs485_port)
        
        # 填充配液通道
        self._refresh_dilution_table()
        
        # 填充冲洗通道
        self._refresh_flush_table()
    
    def _refresh_dilution_table(self):
        """刷新配液通道表格"""
        self.dilution_table.setRowCount(len(self.config.dilution_channels))
        for row, channel in enumerate(self.config.dilution_channels):
            self.dilution_table.setItem(row, 0, QTableWidgetItem(channel.channel_id))
            self.dilution_table.setItem(row, 1, QTableWidgetItem(channel.solution_name))
            self.dilution_table.setItem(row, 2, QTableWidgetItem(str(channel.stock_concentration)))
            
            addr_item = QTableWidgetItem(str(channel.pump_address))
            self.dilution_table.setItem(row, 3, addr_item)
            
            dir_item = QTableWidgetItem(channel.direction)
            self.dilution_table.setItem(row, 4, dir_item)
            
            rpm_item = QTableWidgetItem(str(channel.default_rpm))
            self.dilution_table.setItem(row, 5, rpm_item)
            
            color_btn = QPushButton()
            color_btn.setStyleSheet(f"background-color: {channel.color}")
            color_btn.clicked.connect(lambda checked, r=row: self._select_color(r, True))
            self.dilution_table.setCellWidget(row, 6, color_btn)
    
    def _refresh_flush_table(self):
        """刷新冲洗通道表格"""
        self.flush_table.setRowCount(len(self.config.flush_channels))
        for row, channel in enumerate(self.config.flush_channels):
            self.flush_table.setItem(row, 0, QTableWidgetItem(channel.channel_id))
            self.flush_table.setItem(row, 1, QTableWidgetItem(channel.pump_name))
            self.flush_table.setItem(row, 2, QTableWidgetItem(str(channel.pump_address)))
            self.flush_table.setItem(row, 3, QTableWidgetItem(channel.direction))
            self.flush_table.setItem(row, 4, QTableWidgetItem(str(channel.rpm)))
            self.flush_table.setItem(row, 5, QTableWidgetItem(str(channel.cycle_duration_s)))
    
    def _add_dilution_channel(self):
        """添加配液通道"""
        ch_id = f"Dilution_{len(self.config.dilution_channels) + 1}"
        new_channel = DilutionChannel(
            channel_id=ch_id,
            solution_name="NewSolution",
            stock_concentration=0.1,
            pump_address=1,
            direction="FWD",
            default_rpm=120,
            color="#00FF00"
        )
        self.config.dilution_channels.append(new_channel)
        self._refresh_dilution_table()
    
    def _delete_dilution_channel(self):
        """删除配液通道"""
        row = self.dilution_table.currentRow()
        if row >= 0:
            del self.config.dilution_channels[row]
            self._refresh_dilution_table()
    
    def _add_flush_channel(self):
        """添加冲洗通道"""
        ch_id = f"Flush_{len(self.config.flush_channels) + 1}"
        new_channel = FlushChannel(
            channel_id=ch_id,
            pump_name="FlusePump",
            pump_address=2,
            direction="FWD",
            rpm=100,
            cycle_duration_s=30.0
        )
        self.config.flush_channels.append(new_channel)
        self._refresh_flush_table()
    
    def _delete_flush_channel(self):
        """删除冲洗通道"""
        row = self.flush_table.currentRow()
        if row >= 0:
            del self.config.flush_channels[row]
            self._refresh_flush_table()
    
    def _select_color(self, row: int, is_dilution: bool):
        """选择颜色"""
        color = QColorDialog.getColor()
        if color.isValid():
            if is_dilution:
                self.config.dilution_channels[row].color = color.name()
                self._refresh_dilution_table()
            else:
                self._refresh_flush_table()
    
    def _on_connect(self):
        """连接/断开 RS485"""
        if self.rs485.is_connected():
            self.rs485.close_port()
            self.connect_btn.setText("连接")
            self.scan_btn.setEnabled(False)
        else:
            port = self.port_combo.currentText()
            if self.rs485.open_port(port, 9600):
                self.connect_btn.setText("断开")
                self.scan_btn.setEnabled(True)
                QMessageBox.information(self, "成功", f"连接到 {port} 成功")
            else:
                QMessageBox.critical(self, "错误", f"无法连接到 {port}")
    
    def _on_scan(self):
        """扫描泵"""
        if not self.rs485.is_connected():
            QMessageBox.warning(self, "警告", "串口未连接")
            return
        
        available = self.rs485.scan_pumps()
        msg = f"扫描完成，找到泵: {available}"
        QMessageBox.information(self, "扫描结果", msg)
    
    def _on_save(self):
        """保存配置"""
        # 从表格读取数据
        for row in range(self.dilution_table.rowCount()):
            if row < len(self.config.dilution_channels):
                ch = self.config.dilution_channels[row]
                ch.solution_name = self.dilution_table.item(row, 1).text()
                ch.stock_concentration = float(self.dilution_table.item(row, 2).text())
                ch.pump_address = int(self.dilution_table.item(row, 3).text())
                ch.direction = self.dilution_table.item(row, 4).text()
                ch.default_rpm = int(self.dilution_table.item(row, 5).text())
        
        for row in range(self.flush_table.rowCount()):
            if row < len(self.config.flush_channels):
                ch = self.config.flush_channels[row]
                ch.pump_name = self.flush_table.item(row, 1).text()
                ch.pump_address = int(self.flush_table.item(row, 2).text())
                ch.direction = self.flush_table.item(row, 3).text()
                ch.rpm = int(self.flush_table.item(row, 4).text())
                ch.cycle_duration_s = float(self.flush_table.item(row, 5).text())
        
        self.config.rs485_port = self.port_combo.currentText()
        self.config_saved.emit(self.config)
        QMessageBox.information(self, "成功", "配置已保存")
        self.accept()

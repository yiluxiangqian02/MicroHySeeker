"""EChem (Electrochemistry) view dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QWidget, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt


class EChemView(QDialog):
    """电化学数据实时显示视图。"""
    
    def __init__(self, chi_driver=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("电化学实验数据")
        self.setGeometry(100, 100, 1000, 600)
        self.chi_driver = chi_driver
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """创建控件。"""
        layout = QVBoxLayout(self)
        
        # 图表区（占位符）
        chart_label = QLabel("曲线图表（使用 pyqtgraph 实现）")
        chart_label.setStyleSheet("QLabel { border: 1px solid gray; padding: 40px; }")
        chart_label.setMinimumHeight(300)
        layout.addWidget(chart_label)
        
        # 数据表
        layout.addWidget(QLabel("测量数据表："))
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(["时间 (s)", "电位 (V)", "电流 (mA)", "状态"])
        
        # 添加示例数据
        sample_data = [
            ("0.0", "0.000", "0.000", "启动"),
            ("1.0", "0.100", "0.001", "测量中"),
            ("2.0", "0.200", "0.002", "测量中"),
        ]
        
        self.data_table.setRowCount(len(sample_data))
        for row, (time, potential, current, status) in enumerate(sample_data):
            self.data_table.setItem(row, 0, QTableWidgetItem(time))
            self.data_table.setItem(row, 1, QTableWidgetItem(potential))
            self.data_table.setItem(row, 2, QTableWidgetItem(current))
            self.data_table.setItem(row, 3, QTableWidgetItem(status))
        
        self.data_table.setMaximumHeight(150)
        layout.addWidget(self.data_table)
        
        # 控制面板
        ctrl_group = QGroupBox("控制")
        ctrl_form = QFormLayout(ctrl_group)
        
        btn_start = QPushButton("启动测量")
        btn_stop = QPushButton("停止测量")
        btn_export = QPushButton("导出数据")
        
        btn_start.clicked.connect(self._start_measurement)
        btn_stop.clicked.connect(self._stop_measurement)
        btn_export.clicked.connect(self._export_data)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(btn_start)
        btn_layout.addWidget(btn_stop)
        btn_layout.addWidget(btn_export)
        ctrl_form.addRow("操作", btn_layout)
        
        layout.addWidget(ctrl_group)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        bottom_layout.addStretch()
        bottom_layout.addWidget(btn_close)
        layout.addLayout(bottom_layout)
    
    def _start_measurement(self) -> None:
        """启动测量。"""
        if self.chi_driver:
            self.chi_driver.start_measurement(60)
        print("[EChem] Measurement started")
    
    def _stop_measurement(self) -> None:
        """停止测量。"""
        if self.chi_driver:
            self.chi_driver.stop_measurement()
        print("[EChem] Measurement stopped")
    
    def _export_data(self) -> None:
        """导出数据。"""
        print("[EChem] Data exported")

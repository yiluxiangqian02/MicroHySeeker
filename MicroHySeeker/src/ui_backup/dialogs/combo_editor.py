"""Combo experiment editor dialog."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QWidget,
    QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal


class ComboEditorDialog(QDialog):
    """组合实验编辑器（与 C# ComboExpEditor 对应）。"""
    
    combo_saved = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("组合实验编辑器")
        self.setGeometry(100, 100, 1000, 700)
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """创建控件。"""
        layout = QVBoxLayout(self)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # 左侧：步骤列表
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("步骤列表："))
        self.step_list = QListWidget()
        left_layout.addWidget(self.step_list)
        
        # 左侧按钮
        left_btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("添加")
        self.btn_delete = QPushButton("删除")
        self.btn_up = QPushButton("↑")
        self.btn_down = QPushButton("↓")
        left_btn_layout.addWidget(self.btn_add)
        left_btn_layout.addWidget(self.btn_delete)
        left_btn_layout.addWidget(self.btn_up)
        left_btn_layout.addWidget(self.btn_down)
        left_layout.addLayout(left_btn_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget, 1)
        
        # 右侧：参数编辑区
        right_layout = QVBoxLayout()
        
        param_group = QGroupBox("参数编辑")
        param_form = QFormLayout(param_group)
        
        self.step_name_edit = QLineEdit()
        param_form.addRow("步骤名称", self.step_name_edit)
        
        self.msg_box = QTextEdit()
        self.msg_box.setReadOnly(True)
        param_form.addRow("信息", self.msg_box)
        
        self.info_label = QLabel("选择步骤以编辑")
        param_form.addRow("状态", self.info_label)
        
        right_layout.addWidget(param_group)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, 1)
        
        layout.addLayout(main_layout)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        self.btn_display_matrix = QPushButton("显示矩阵")
        self.btn_save = QPushButton("保存修改")
        self.btn_save_run = QPushButton("保存并运行")
        self.btn_close = QPushButton("关闭")
        
        self.btn_display_matrix.clicked.connect(self._display_matrix)
        self.btn_save.clicked.connect(self._save_changes)
        self.btn_save_run.clicked.connect(self._save_and_run)
        self.btn_close.clicked.connect(self.accept)
        
        bottom_layout.addWidget(self.btn_display_matrix)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_save)
        bottom_layout.addWidget(self.btn_save_run)
        bottom_layout.addWidget(self.btn_close)
        layout.addLayout(bottom_layout)
    
    def _display_matrix(self) -> None:
        """显示组合矩阵。"""
        QMessageBox.information(self, "矩阵", "组合实验矩阵显示功能")
    
    def _save_changes(self) -> None:
        """保存修改。"""
        QMessageBox.information(self, "保存", "修改已保存")
        self.combo_saved.emit()
    
    def _save_and_run(self) -> None:
        """保存并运行。"""
        QMessageBox.information(self, "运行", "组合实验已启动")
        self.combo_saved.emit()

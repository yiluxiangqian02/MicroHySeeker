"""About dialog."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtGui import QFont


class AboutDialog(QDialog):
    """关于对话框。"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setGeometry(100, 100, 500, 400)
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """创建控件。"""
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("MicroHySeeker")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 版本
        version = QLabel("Version 1.0.0")
        layout.addWidget(version)
        
        # 信息
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setText("""
MicroHySeeker 是一个功能强大的微流体和电化学实验控制平台。

功能特性：
- 支持多种实验步骤编辑（配液、电化学、冲洗、移液、空白）
- RS485 设备控制和通讯
- 注射泵和蠕动泵手动控制
- 电化学实验数据实时采集与可视化
- OCPT 开路电位测量
- 程序导入/导出和 JSON 格式支持

开发者: AI4S Team
许可证: MIT License
        """)
        layout.addWidget(info_text)
        
        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

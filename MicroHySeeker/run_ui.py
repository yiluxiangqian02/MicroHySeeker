#!/usr/bin/env python
"""
运行 MicroHySeeker 界面应用
"""
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()













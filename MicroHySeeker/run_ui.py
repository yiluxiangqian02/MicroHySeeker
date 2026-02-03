#!/usr/bin/env python
"""
运行 MicroHySeeker 界面应用
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 设置环境变量
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.plugin=false"

try:
    from PySide6.QtWidgets import QApplication
    from src.ui.main_window import MainWindow
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保已安装所有依赖:")
    print("  conda activate MicroHySeeker")
    print("  pip install PySide6 pyqtgraph pyserial jsonschema pydantic")
    sys.exit(1)


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

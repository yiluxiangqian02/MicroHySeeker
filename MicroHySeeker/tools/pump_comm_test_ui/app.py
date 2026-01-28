from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def _ensure_src_on_path() -> None:
    # tools/pump_comm_test_ui/app.py -> MicroHySeeker/src and MicroHySeeker/tools
    base_dir = Path(__file__).resolve().parents[2]
    src_dir = base_dir / "src"
    tools_dir = base_dir / "tools"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))


def main() -> None:
    _ensure_src_on_path()

    from pump_comm_test_ui.main_window import MainWindow

    app = QApplication([])
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(245, 245, 245))
    palette.setColor(QPalette.WindowText, QColor(20, 20, 20))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(20, 20, 20))
    palette.setColor(QPalette.Text, QColor(20, 20, 20))
    palette.setColor(QPalette.Button, QColor(245, 245, 245))
    palette.setColor(QPalette.ButtonText, QColor(20, 20, 20))
    palette.setColor(QPalette.BrightText, QColor(200, 0, 0))
    palette.setColor(QPalette.Link, QColor(0, 92, 170))
    palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

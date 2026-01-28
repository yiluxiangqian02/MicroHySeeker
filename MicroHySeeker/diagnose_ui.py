#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import traceback
from pathlib import Path

# 修复路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(Path("f:\\BaiduSyncdisk\\micro1229\\485test\\通讯")))

print("[Step 1] Testing PySide6 import...")
try:
    from PySide6.QtWidgets import QApplication
    print("  ✓ PySide6.QtWidgets OK")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

print("[Step 2] Testing config import...")
try:
    from src.models import SystemConfig
    print("  ✓ SystemConfig OK")
except Exception as e:
    print(f"  ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[Step 3] Testing dialogs import...")
try:
    from src.dialogs.config_dialog import ConfigDialog
    from src.dialogs.manual_control import ManualControlDialog
    from src.dialogs.calibrate_dialog import CalibrateDialog
    from src.dialogs.program_editor import ProgramEditorDialog
    print("  ✓ All dialogs OK")
except Exception as e:
    print(f"  ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[Step 4] Testing runner import...")
try:
    from src.engine.runner import ExperimentRunner
    print("  ✓ ExperimentRunner OK")
except Exception as e:
    print(f"  ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[Step 5] Testing MainWindow import...")
try:
    from src.ui.main_window import MainWindow
    print("  ✓ MainWindow OK")
except Exception as e:
    print(f"  ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[Step 6] Creating application...")
try:
    app = QApplication(sys.argv)
    print("  ✓ QApplication created")
except Exception as e:
    print(f"  ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[Step 7] Creating MainWindow...")
try:
    window = MainWindow()
    print("  ✓ MainWindow created")
except Exception as e:
    print(f"  ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("[Step 8] Showing window...")
try:
    window.show()
    print("  ✓ Window shown")
except Exception as e:
    print(f"  ✗ Error: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n[SUCCESS] Starting event loop...\n")
sys.exit(app.exec())

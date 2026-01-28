#!/usr/bin/env python
"""Check all imports in the project."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

errors = []

# Test core imports
try:
    from core import ExpProgram, ProgStep, PROG_STEP_SCHEMA, EXP_PROGRAM_SCHEMA
    print("✓ Core imports OK")
except Exception as e:
    print(f"✗ Core import failed: {e}")
    errors.append(str(e))

# Test services imports
try:
    from services import SettingsService, LoggerService, TranslatorService
    print("✓ Services imports OK")
except Exception as e:
    print(f"✗ Services import failed: {e}")
    errors.append(str(e))

# Test hardware imports
try:
    from hardware import PumpManager, RS485Driver, CHIDriver, FlusherDriver
    print("✓ Hardware imports OK")
except Exception as e:
    print(f"✗ Hardware import failed: {e}")
    errors.append(str(e))

# Test UI imports
try:
    from ui import MainWindow, ProgramEditorDialog, ConfigDialog, ManualDialog
    print("✓ UI imports OK")
except Exception as e:
    print(f"✗ UI import failed: {e}")
    errors.append(str(e))

# Test individual dialogs
try:
    from ui.dialogs.rs485_test import RS485TestDialog
    from ui.dialogs.echem_view import EChemView
    from ui.dialogs.about_dialog import AboutDialog
    from ui.dialogs.combo_editor import ComboEditorDialog
    print("✓ All dialogs imports OK")
except Exception as e:
    print(f"✗ Dialogs import failed: {e}")
    errors.append(str(e))

if errors:
    print(f"\n❌ Total errors: {len(errors)}")
    for i, err in enumerate(errors, 1):
        print(f"  {i}. {err}")
    sys.exit(1)
else:
    print("\n✅ All imports successful!")
    sys.exit(0)

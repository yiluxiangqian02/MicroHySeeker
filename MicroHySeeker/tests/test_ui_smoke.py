"""Smoke test for UI without displaying windows."""

import sys
from pathlib import Path

# Add src to path
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PySide6.QtWidgets import QApplication
from services import SettingsService, LoggerService, TranslatorService
from hardware import PumpManager, RS485Driver, CHIDriver
from ui import MainWindow, ProgramEditorDialog, ConfigDialog, ManualDialog
from core import ExpProgram


def test_ui_creation():
    """Test that all UI components can be created without errors."""
    app = QApplication.instance() or QApplication([])
    
    # Initialize services
    settings = SettingsService("test_config.json")
    logger = LoggerService("test_logs")
    translator = TranslatorService("zh_CN")
    
    # Initialize hardware
    pump_mgr = PumpManager()
    rs485 = RS485Driver(use_mock=True)
    chi = CHIDriver()
    
    pump_mgr.add_syringe_pump(1)
    pump_mgr.add_peristaltic_pump(1)
    rs485.connect()
    
    services = {"settings": settings, "logger": logger, "translator": translator}
    hardware = {"pump_manager": pump_mgr, "rs485": rs485, "chi": chi}
    
    # Test main window
    print("Creating MainWindow...")
    main_window = MainWindow(services=services)
    assert main_window is not None
    print("✓ MainWindow created successfully")
    
    # Test ProgramEditorDialog (without showing)
    print("Creating ProgramEditorDialog...")
    program = ExpProgram(program_id="test", program_name="Test")
    prog_editor = ProgramEditorDialog(program, settings)
    assert prog_editor is not None
    print("✓ ProgramEditorDialog created successfully")
    
    # Test ConfigDialog
    print("Creating ConfigDialog...")
    config_dialog = ConfigDialog(settings)
    assert config_dialog is not None
    print("✓ ConfigDialog created successfully")
    
    # Test ManualDialog
    print("Creating ManualDialog...")
    manual_dialog = ManualDialog(pump_mgr, rs485)
    assert manual_dialog is not None
    print("✓ ManualDialog created successfully")
    
    print("\n✓ All UI components created successfully!")
    return True


if __name__ == "__main__":
    try:
        success = test_ui_creation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ UI Creation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

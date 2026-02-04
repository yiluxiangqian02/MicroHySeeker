"""Dialogs module initialization."""

from .program_editor import ProgramEditorDialog
from .combo_editor import ComboEditorDialog
from .config_dialog import ConfigDialog
from .manual_dialog import ManualDialog
from .rs485_test import RS485TestDialog
from .echem_view import EChemView
from .about_dialog import AboutDialog

__all__ = [
    "ProgramEditorDialog",
    "ComboEditorDialog",
    "ConfigDialog",
    "ManualDialog",
    "RS485TestDialog",
    "EChemView",
    "AboutDialog",
]

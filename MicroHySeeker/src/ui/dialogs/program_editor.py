"""Program editor dialog with five operation types."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QWidget,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QGroupBox, QFormLayout, QMessageBox, QFileDialog, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import json
from jsonschema import validate, ValidationError
from typing import Dict, Optional, List
import sys
from pathlib import Path

# Add src to path for imports
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core import ExpProgram, ProgStep, PROG_STEP_SCHEMA, EXP_PROGRAM_SCHEMA


class ProgramEditorDialog(QDialog):
    """程序编辑对话框 - 五类操作类型：配液/电化学/冲洗/移液/空白。"""
    
    program_saved = Signal(ExpProgram)
    
    OPERATION_TYPES = {
        "配液": {"icon": "🧪", "color": "#E8F4F8"},
        "电化学": {"icon": "⚡", "color": "#FFF8E8"},
        "冲洗": {"icon": "💧", "color": "#E8F8E8"},
        "移液": {"icon": "🔬", "color": "#F8E8F8"},
        "空白": {"icon": "⏱️", "color": "#F0F0F0"}
    }
    
    def __init__(self, program: ExpProgram = None, settings_service=None):
        super().__init__()
        self.setWindowTitle("程序编辑器")
        self.setGeometry(100, 100, 1000, 700)
        self.program = program or ExpProgram(program_id="prog_001", program_name="New Program")
        self.settings_service = settings_service
        self.step_id_counter = len(self.program.steps) + 1
        
        self._create_widgets()
        self._load_program()
    
    def _create_widgets(self) -> None:
        """创建控件。"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel(f"编辑程序: {self.program.program_name}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # OCPT 开关
        ocpt_layout = QHBoxLayout()
        self.ocpt_checkbox = QCheckBox("启用 OCPT 开路电位测量")
        self.ocpt_checkbox.setChecked(self.program.ocpt_enabled)
        self.ocpt_checkbox.stateChanged.connect(self._on_ocpt_changed)
        ocpt_layout.addWidget(self.ocpt_checkbox)
        ocpt_layout.addStretch()
        layout.addLayout(ocpt_layout)
        
        # 步骤列表与编辑区
        main_layout = QHBoxLayout()
        
        # 左侧：步骤列表
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("步骤列表："))
        self.step_list = QListWidget()
        self.step_list.itemSelectionChanged.connect(self._on_step_selected)
        left_layout.addWidget(self.step_list)
        
        # 左侧操作按钮
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("添加")
        self.btn_delete = QPushButton("删除")
        self.btn_up = QPushButton("↑ 上移")
        self.btn_down = QPushButton("↓ 下移")
        self.btn_add.clicked.connect(self._show_add_step_menu)
        self.btn_delete.clicked.connect(self._delete_step)
        self.btn_up.clicked.connect(self._move_step_up)
        self.btn_down.clicked.connect(self._move_step_down)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_up)
        btn_layout.addWidget(self.btn_down)
        left_layout.addLayout(btn_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget, 1)
        
        # 右侧：操作类型选择与参数编辑区
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("操作类型选择："))
        
        # 操作类型小标题
        type_button_layout = QHBoxLayout()
        self.type_buttons: Dict[str, QPushButton] = {}
        for op_type, info in self.OPERATION_TYPES.items():
            btn = QPushButton(f"{info['icon']} {op_type}")
            btn.setMaximumWidth(100)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=op_type: self._on_type_selected(t))
            self.type_buttons[op_type] = btn
            type_button_layout.addWidget(btn)
        right_layout.addLayout(type_button_layout)
        
        # 参数编辑区（滚动）
        self.param_scroll = QScrollArea()
        self.param_scroll.setWidgetResizable(True)
        self.param_widget = QWidget()
        self.param_layout = QFormLayout(self.param_widget)
        self.param_scroll.setWidget(self.param_widget)
        right_layout.addWidget(self.param_scroll)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, 1)
        
        layout.addLayout(main_layout)
        
        # 底部操作按钮
        bottom_layout = QHBoxLayout()
        self.btn_import = QPushButton("导入 JSON")
        self.btn_export = QPushButton("导出 JSON")
        self.btn_run = QPushButton("运行")
        self.btn_save = QPushButton("保存")
        self.btn_close = QPushButton("关闭")
        
        self.btn_import.clicked.connect(self._import_json)
        self.btn_export.clicked.connect(self._export_json)
        self.btn_run.clicked.connect(self._run_program)
        self.btn_save.clicked.connect(self._save_program)
        self.btn_close.clicked.connect(self.accept)
        
        bottom_layout.addWidget(self.btn_import)
        bottom_layout.addWidget(self.btn_export)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_run)
        bottom_layout.addWidget(self.btn_save)
        bottom_layout.addWidget(self.btn_close)
        layout.addLayout(bottom_layout)
    
    def _load_program(self) -> None:
        """加载程序到列表。"""
        for step in self.program.steps:
            item = QListWidgetItem(f"{step.step_type} - {step.step_name}")
            item.setData(Qt.UserRole, step.step_id)
            self.step_list.addItem(item)
    
    def _show_add_step_menu(self) -> None:
        """显示添加步骤菜单。"""
        menu_dialog = QDialog(self)
        menu_dialog.setWindowTitle("选择操作类型")
        layout = QVBoxLayout(menu_dialog)
        
        layout.addWidget(QLabel("选择要添加的操作类型："))
        type_layout = QVBoxLayout()
        for op_type in self.OPERATION_TYPES.keys():
            btn = QPushButton(op_type)
            btn.clicked.connect(lambda checked, t=op_type: self._add_step(t, menu_dialog))
            type_layout.addWidget(btn)
        layout.addLayout(type_layout)
        
        menu_dialog.exec()
    
    def _add_step(self, step_type: str, dialog: QDialog) -> None:
        """添加新步骤。"""
        step = ProgStep(
            step_id=self.step_id_counter,
            step_type=step_type,
            step_name=f"新 {step_type} 步骤"
        )
        self.step_id_counter += 1
        self.program.add_step(step)
        
        item = QListWidgetItem(f"{step_type} - {step.step_name}")
        item.setData(Qt.UserRole, step.step_id)
        self.step_list.addItem(item)
        self.step_list.setCurrentItem(item)
        
        dialog.close()
    
    def _delete_step(self) -> None:
        """删除选中的步骤。"""
        current_item = self.step_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请选择要删除的步骤")
            return
        
        step_id = current_item.data(Qt.UserRole)
        self.program.remove_step(step_id)
        row = self.step_list.row(current_item)
        self.step_list.takeItem(row)
    
    def _move_step_up(self) -> None:
        """上移步骤。"""
        current_row = self.step_list.currentRow()
        if current_row <= 0:
            return
        
        self.program.steps[current_row], self.program.steps[current_row - 1] = \
            self.program.steps[current_row - 1], self.program.steps[current_row]
        
        self._reload_step_list()
        self.step_list.setCurrentRow(current_row - 1)
    
    def _move_step_down(self) -> None:
        """下移步骤。"""
        current_row = self.step_list.currentRow()
        if current_row >= len(self.program.steps) - 1:
            return
        
        self.program.steps[current_row], self.program.steps[current_row + 1] = \
            self.program.steps[current_row + 1], self.program.steps[current_row]
        
        self._reload_step_list()
        self.step_list.setCurrentRow(current_row + 1)
    
    def _reload_step_list(self) -> None:
        """重新加载步骤列表。"""
        self.step_list.clear()
        self._load_program()
    
    def _on_step_selected(self) -> None:
        """步骤选中事件。"""
        current_item = self.step_list.currentItem()
        if not current_item:
            return
        
        step_id = current_item.data(Qt.UserRole)
        step = self.program.get_step(step_id)
        if step:
            self._show_param_panel(step)
    
    def _on_type_selected(self, step_type: str) -> None:
        """操作类型选中事件。"""
        # 更新按钮样式
        for btn_type, btn in self.type_buttons.items():
            btn.setChecked(btn_type == step_type)
        
        # 创建新步骤或更新当前步骤的类型
        current_item = self.step_list.currentItem()
        if current_item:
            step_id = current_item.data(Qt.UserRole)
            step = self.program.get_step(step_id)
            if step:
                step.step_type = step_type
                current_item.setText(f"{step_type} - {step.step_name}")
                self._show_param_panel(step)
    
    def _show_param_panel(self, step: ProgStep) -> None:
        """显示参数编辑面板。"""
        # 清除旧控件
        while self.param_layout.count():
            self.param_layout.takeAt(0).widget().deleteLater()
        
        # 根据步骤类型创建参数控件
        if step.step_type == "配液":
            self._create_solution_params(step)
        elif step.step_type == "电化学":
            self._create_echem_params(step)
        elif step.step_type == "冲洗":
            self._create_flush_params(step)
        elif step.step_type == "移液":
            self._create_pipette_params(step)
        elif step.step_type == "空白":
            self._create_blank_params(step)
        
        # 更新按钮状态
        for btn_type, btn in self.type_buttons.items():
            btn.setChecked(btn_type == step.step_type)
    
    def _create_solution_params(self, step: ProgStep) -> None:
        """配液参数面板。"""
        self.solution_type_combo = QComboBox()
        self.solution_type_combo.addItems(["溶液A", "溶液B", "溶液C"])
        self.solution_type_combo.setCurrentText(step.solution_type or "溶液A")
        self.param_layout.addRow("溶液种类", self.solution_type_combo)
        
        self.conc_spin = QDoubleSpinBox()
        self.conc_spin.setValue(step.high_concentration or 1.0)
        self.param_layout.addRow("浓缩液浓度 (M)", self.conc_spin)
        
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setValue(step.target_volume or 10.0)
        self.param_layout.addRow("目标体积 (mL)", self.volume_spin)
        
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["mL", "µL", "nL"])
        self.unit_combo.setCurrentText(step.volume_unit or "mL")
        self.param_layout.addRow("单位", self.unit_combo)
        
        self.pump_addr_spin = QSpinBox()
        self.pump_addr_spin.setValue(step.pump_address or 1)
        self.param_layout.addRow("泵地址", self.pump_addr_spin)
        
        self.pump_speed_spin = QDoubleSpinBox()
        self.pump_speed_spin.setValue(step.pump_speed or 10.0)
        self.param_layout.addRow("泵转速 (RPM)", self.pump_speed_spin)
    
    def _create_echem_params(self, step: ProgStep) -> None:
        """电化学参数面板。"""
        self.potential_spin = QDoubleSpinBox()
        self.potential_spin.setMinimum(-2.0)
        self.potential_spin.setMaximum(2.0)
        self.potential_spin.setValue(step.potential or 0.0)
        self.param_layout.addRow("电位 (V)", self.potential_spin)
        
        self.current_limit_spin = QDoubleSpinBox()
        self.current_limit_spin.setValue(step.current_limit or 0.1)
        self.param_layout.addRow("电流限制 (mA)", self.current_limit_spin)
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setValue(step.duration or 60.0)
        self.param_layout.addRow("时间 (s)", self.duration_spin)
        
        self.ocpt_step_checkbox = QCheckBox("启用此步骤的 OCPT")
        self.ocpt_step_checkbox.setChecked(step.ocpt_enabled)
        self.param_layout.addRow("OCPT", self.ocpt_step_checkbox)
    
    def _create_flush_params(self, step: ProgStep) -> None:
        """冲洗参数面板。"""
        self.flush_pump_combo = QComboBox()
        self.flush_pump_combo.addItems(["泵 1", "泵 2", "泵 3"])
        self.param_layout.addRow("泵选择", self.flush_pump_combo)
        
        self.flush_volume_spin = QDoubleSpinBox()
        self.flush_volume_spin.setValue(step.flush_volume or 5.0)
        self.param_layout.addRow("冲洗体积 (mL)", self.flush_volume_spin)
        
        self.flush_cycles_spin = QSpinBox()
        self.flush_cycles_spin.setValue(step.flush_cycles or 3)
        self.param_layout.addRow("冲洗循环数", self.flush_cycles_spin)
        
        self.flush_dir_combo = QComboBox()
        self.flush_dir_combo.addItems(["正向", "反向"])
        self.param_layout.addRow("方向", self.flush_dir_combo)
    
    def _create_pipette_params(self, step: ProgStep) -> None:
        """移液参数面板。"""
        self.source_edit = QLineEdit()
        self.source_edit.setText(step.source_well or "A1")
        self.param_layout.addRow("源位置", self.source_edit)
        
        self.target_edit = QLineEdit()
        self.target_edit.setText(step.target_well or "A2")
        self.param_layout.addRow("目标位置", self.target_edit)
        
        self.transfer_volume_spin = QDoubleSpinBox()
        self.transfer_volume_spin.setValue(step.transfer_volume or 100.0)
        self.param_layout.addRow("移液体积 (µL)", self.transfer_volume_spin)
        
        self.transfer_speed_spin = QDoubleSpinBox()
        self.transfer_speed_spin.setValue(step.transfer_speed or 50.0)
        self.param_layout.addRow("移液速度 (µL/s)", self.transfer_speed_spin)
    
    def _create_blank_params(self, step: ProgStep) -> None:
        """空白参数面板。"""
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setValue(step.delay_time or 5.0)
        self.param_layout.addRow("延时时间 (s)", self.delay_spin)
    
    def _on_ocpt_changed(self) -> None:
        """OCPT 开关改变。"""
        self.program.ocpt_enabled = self.ocpt_checkbox.isChecked()
        if self.settings_service:
            self.settings_service.set("ocpt_enabled", self.program.ocpt_enabled)
    
    def _import_json(self) -> None:
        """导入 JSON 程序。"""
        filepath, _ = QFileDialog.getOpenFileName(self, "打开程序", "", "JSON Files (*.json)")
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证 JSON schema
            validate(instance=data, schema=EXP_PROGRAM_SCHEMA)
            
            self.program = ExpProgram.from_dict(data)
            self.step_id_counter = max([s.step_id for s in self.program.steps], default=0) + 1
            self._reload_step_list()
            QMessageBox.information(self, "成功", f"已加载程序: {self.program.program_name}")
        except ValidationError as e:
            QMessageBox.critical(self, "错误", f"JSON 格式不正确: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载失败: {str(e)}")
    
    def _export_json(self) -> None:
        """导出 JSON 程序。"""
        filepath, _ = QFileDialog.getSaveFileName(self, "保存程序", "", "JSON Files (*.json)")
        if not filepath:
            return
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.program.to_json())
            QMessageBox.information(self, "成功", f"程序已保存: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def _run_program(self) -> None:
        """运行程序。"""
        if not self.program.steps:
            QMessageBox.warning(self, "警告", "程序中没有步骤")
            return
        
        QMessageBox.information(self, "提示", f"运行程序: {self.program.program_name}\n共 {len(self.program.steps)} 个步骤\nOCPT: {'启用' if self.program.ocpt_enabled else '禁用'}")
    
    def _save_program(self) -> None:
        """保存程序。"""
        self.program_saved.emit(self.program)
        QMessageBox.information(self, "成功", "程序已保存")

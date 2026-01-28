"""
程序编辑器 - 实验步骤编辑与管理
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTextEdit, QMessageBox, QGroupBox, QFormLayout,
    QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal
from typing import Optional

from src.models import (
    ProgStep, Experiment, ProgramStepType, ECTechnique, ECSettings,
    PrepSolStep, OCPTAction, SystemConfig
)


class ProgramEditorDialog(QDialog):
    """程序编辑对话框"""
    program_saved = Signal(Experiment)
    
    def __init__(self, config: SystemConfig, experiment: Optional[Experiment] = None, parent=None):
        super().__init__(parent)
        self.config = config
        self.experiment = experiment or Experiment(exp_id="exp_001", exp_name="实验_001")
        self.current_step: Optional[ProgStep] = None
        
        self.setWindowTitle("程序编辑")
        self.setGeometry(100, 100, 1200, 700)
        self._init_ui()
        self._refresh_step_list()
    
    def _init_ui(self):
        """初始化 UI"""
        main_layout = QHBoxLayout(self)
        
        # 左侧：步骤列表
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("步骤列表:"))
        
        self.step_list = QListWidget()
        self.step_list.itemClicked.connect(self._on_step_selected)
        left_layout.addWidget(self.step_list)
        
        # 步骤管理按钮
        step_btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._on_add_step)
        step_btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._on_delete_step)
        step_btn_layout.addWidget(del_btn)
        
        up_btn = QPushButton("上移")
        up_btn.clicked.connect(self._on_move_up)
        step_btn_layout.addWidget(up_btn)
        
        down_btn = QPushButton("下移")
        down_btn.clicked.connect(self._on_move_down)
        step_btn_layout.addWidget(down_btn)
        
        left_layout.addLayout(step_btn_layout)
        
        main_layout.addLayout(left_layout, 1)
        
        # 右侧：步骤编辑区
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("步骤编辑:"))
        
        # 滚动区域用于动态内容
        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_widget = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_widget)
        self.editor_scroll.setWidget(self.editor_widget)
        right_layout.addWidget(self.editor_scroll)
        
        # 保存按钮
        save_layout = QHBoxLayout()
        save_btn = QPushButton("保存程序")
        save_btn.clicked.connect(self._on_save_program)
        save_layout.addWidget(save_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        save_layout.addWidget(close_btn)
        
        right_layout.addLayout(save_layout)
        
        main_layout.addLayout(right_layout, 1)
        self.setLayout(main_layout)
    
    def _refresh_step_list(self):
        """刷新步骤列表"""
        self.step_list.clear()
        for i, step in enumerate(self.experiment.steps):
            item = QListWidgetItem(f"[{i}] {step.step_type.value} - {step.step_id}")
            self.step_list.addItem(item)
    
    def _on_step_selected(self, item: QListWidgetItem):
        """选中步骤时编辑"""
        index = self.step_list.row(item)
        if 0 <= index < len(self.experiment.steps):
            self.current_step = self.experiment.steps[index]
            self._show_step_editor()
    
    def _show_step_editor(self):
        """显示步骤编辑面板"""
        # 清空编辑区
        while self.editor_layout.count():
            self.editor_layout.takeAt(0).widget().deleteLater()
        
        if not self.current_step:
            return
        
        step = self.current_step
        
        # 步骤类型选择
        type_layout = QFormLayout()
        self.type_combo = QComboBox()
        for stype in ProgramStepType:
            self.type_combo.addItem(stype.value, stype)
        self.type_combo.setCurrentText(step.step_type.value)
        self.type_combo.currentIndexChanged.connect(self._on_step_type_changed)
        type_layout.addRow("步骤类型:", self.type_combo)
        
        step_group = QGroupBox("基本信息")
        step_group.setLayout(type_layout)
        self.editor_layout.addWidget(step_group)
        
        # 根据类型显示对应编辑器
        if step.step_type == ProgramStepType.TRANSFER:
            self._show_transfer_editor(step)
        elif step.step_type == ProgramStepType.PREP_SOL:
            self._show_prep_sol_editor(step)
        elif step.step_type == ProgramStepType.FLUSH:
            self._show_flush_editor(step)
        elif step.step_type == ProgramStepType.EChem:
            self._show_echem_editor(step)
        elif step.step_type == ProgramStepType.BLANK:
            self._show_blank_editor(step)
        
        self.editor_layout.addStretch()
    
    def _show_transfer_editor(self, step: ProgStep):
        """显示 Transfer 编辑器"""
        group = QGroupBox("移液设置")
        layout = QFormLayout()
        
        pump_combo = QComboBox()
        pump_combo.addItems([str(p.address) for p in self.config.pumps])
        if step.pump_address:
            pump_combo.setCurrentText(str(step.pump_address))
        layout.addRow("泵地址:", pump_combo)
        
        dir_combo = QComboBox()
        dir_combo.addItems(["FWD", "REV"])
        if step.pump_direction:
            dir_combo.setCurrentText(step.pump_direction)
        layout.addRow("方向:", dir_combo)
        
        rpm_spin = QSpinBox()
        rpm_spin.setRange(0, 1000)
        rpm_spin.setValue(step.pump_rpm or 100)
        layout.addRow("转速(RPM):", rpm_spin)
        
        vol_spin = QDoubleSpinBox()
        vol_spin.setRange(0, 10000)
        vol_spin.setValue(step.volume_ul or 100)
        layout.addRow("体积(uL):", vol_spin)
        
        group.setLayout(layout)
        self.editor_layout.addWidget(group)
        
        # 保存回调
        def save_transfer():
            step.pump_address = int(pump_combo.currentText())
            step.pump_direction = dir_combo.currentText()
            step.pump_rpm = rpm_spin.value()
            step.volume_ul = vol_spin.value()
        
        step._save_func = save_transfer
    
    def _show_prep_sol_editor(self, step: ProgStep):
        """显示 PrepSol 编辑器"""
        group = QGroupBox("配液设置")
        layout = QFormLayout()
        
        if not step.prep_sol_params:
            step.prep_sol_params = PrepSolStep()
        
        params = step.prep_sol_params
        
        target_conc = QDoubleSpinBox()
        target_conc.setRange(0, 1000)
        target_conc.setValue(params.target_concentration)
        layout.addRow("目标浓度(mol/L):", target_conc)
        
        is_solvent = QCheckBox()
        is_solvent.setChecked(params.is_solvent)
        layout.addRow("是否溶剂:", is_solvent)
        
        order_text = QTextEdit()
        order_text.setPlainText("\n".join(params.injection_order))
        order_text.setMaximumHeight(100)
        layout.addRow("注液顺序(每行一个):", order_text)
        
        total_vol = QDoubleSpinBox()
        total_vol.setRange(0, 10000)
        total_vol.setValue(params.total_volume_ul)
        layout.addRow("总体积(uL):", total_vol)
        
        group.setLayout(layout)
        self.editor_layout.addWidget(group)
        
        def save_prep_sol():
            step.prep_sol_params.target_concentration = target_conc.value()
            step.prep_sol_params.is_solvent = is_solvent.isChecked()
            step.prep_sol_params.injection_order = order_text.toPlainText().strip().split('\n')
            step.prep_sol_params.total_volume_ul = total_vol.value()
        
        step._save_func = save_prep_sol
    
    def _show_flush_editor(self, step: ProgStep):
        """显示 Flush 编辑器"""
        group = QGroupBox("冲洗设置")
        layout = QFormLayout()
        
        pump_combo = QComboBox()
        pump_combo.addItems([str(p.address) for p in self.config.pumps])
        if step.pump_address:
            pump_combo.setCurrentText(str(step.pump_address))
        layout.addRow("泵地址:", pump_combo)
        
        rpm_spin = QSpinBox()
        rpm_spin.setRange(0, 1000)
        rpm_spin.setValue(step.flush_rpm or 100)
        layout.addRow("转速(RPM):", rpm_spin)
        
        duration_spin = QDoubleSpinBox()
        duration_spin.setRange(0, 1000)
        duration_spin.setValue(step.flush_cycle_duration_s or 30)
        layout.addRow("循环时长(s):", duration_spin)
        
        cycles_spin = QSpinBox()
        cycles_spin.setRange(1, 100)
        cycles_spin.setValue(step.flush_cycles or 1)
        layout.addRow("循环次数:", cycles_spin)
        
        group.setLayout(layout)
        self.editor_layout.addWidget(group)
        
        def save_flush():
            step.pump_address = int(pump_combo.currentText())
            step.flush_rpm = rpm_spin.value()
            step.flush_cycle_duration_s = duration_spin.value()
            step.flush_cycles = cycles_spin.value()
        
        step._save_func = save_flush
    
    def _show_echem_editor(self, step: ProgStep):
        """显示 EChem 编辑器"""
        if not step.ec_settings:
            step.ec_settings = ECSettings()
        
        ec = step.ec_settings
        
        group = QGroupBox("电化学设置")
        layout = QFormLayout()
        
        # 技术选择
        tech_combo = QComboBox()
        for tech in ECTechnique:
            tech_combo.addItem(tech.value, tech)
        tech_combo.setCurrentText(ec.technique.value)
        layout.addRow("技术:", tech_combo)
        
        # 电位设置（CV/LSV 时显示）
        e0_spin = QDoubleSpinBox()
        e0_spin.setRange(-2, 2)
        e0_spin.setValue(ec.e0 or 0)
        layout.addRow("E0(V):", e0_spin)
        
        eh_spin = QDoubleSpinBox()
        eh_spin.setRange(-2, 2)
        eh_spin.setValue(ec.eh or 0.5)
        layout.addRow("EH(V):", eh_spin)
        
        el_spin = QDoubleSpinBox()
        el_spin.setRange(-2, 2)
        el_spin.setValue(ec.el or -0.5)
        layout.addRow("EL(V):", el_spin)
        
        # 扫描速率
        sr_spin = QDoubleSpinBox()
        sr_spin.setRange(0, 100)
        sr_spin.setValue(ec.scan_rate or 0.05)
        layout.addRow("扫描速率(V/s):", sr_spin)
        
        # 采样间隔
        si_spin = QSpinBox()
        si_spin.setRange(1, 10000)
        si_spin.setValue(ec.sample_interval_ms)
        layout.addRow("采样间隔(ms):", si_spin)
        
        # 运行时间
        rt_spin = QDoubleSpinBox()
        rt_spin.setRange(0, 10000)
        rt_spin.setValue(ec.run_time_s or 60)
        layout.addRow("运行时间(s):", rt_spin)
        
        # OCPT 设置
        ocpt_check = QCheckBox("启用 OCPT 反向电流检测")
        ocpt_check.setChecked(ec.ocpt_enabled)
        layout.addRow("OCPT:", ocpt_check)
        
        ocpt_threshold = QDoubleSpinBox()
        ocpt_threshold.setRange(-1000, 0)
        ocpt_threshold.setValue(ec.ocpt_threshold_uA)
        layout.addRow("OCPT 阈值(μA):", ocpt_threshold)
        
        ocpt_action = QComboBox()
        for action in OCPTAction:
            ocpt_action.addItem(action.value, action)
        ocpt_action.setCurrentText(ec.ocpt_action.value)
        layout.addRow("OCPT 动作:", ocpt_action)
        
        group.setLayout(layout)
        self.editor_layout.addWidget(group)
        
        def save_echem():
            step.ec_settings.technique = ECTechnique(tech_combo.currentText())
            step.ec_settings.e0 = e0_spin.value()
            step.ec_settings.eh = eh_spin.value()
            step.ec_settings.el = el_spin.value()
            step.ec_settings.scan_rate = sr_spin.value()
            step.ec_settings.sample_interval_ms = si_spin.value()
            step.ec_settings.run_time_s = rt_spin.value()
            step.ec_settings.ocpt_enabled = ocpt_check.isChecked()
            step.ec_settings.ocpt_threshold_uA = ocpt_threshold.value()
            step.ec_settings.ocpt_action = OCPTAction(ocpt_action.currentText())
        
        step._save_func = save_echem
    
    def _show_blank_editor(self, step: ProgStep):
        """显示 Blank 编辑器"""
        group = QGroupBox("空白步骤")
        layout = QFormLayout()
        
        notes = QTextEdit()
        notes.setPlainText(step.notes)
        notes.setMaximumHeight(80)
        layout.addRow("备注:", notes)
        
        group.setLayout(layout)
        self.editor_layout.addWidget(group)
        
        def save_blank():
            step.notes = notes.toPlainText()
        
        step._save_func = save_blank
    
    def _on_step_type_changed(self):
        """步骤类型变更"""
        if self.current_step:
            new_type = self.type_combo.currentData()
            self.current_step.step_type = new_type
            self._show_step_editor()
    
    def _on_add_step(self):
        """添加步骤"""
        new_step = ProgStep(
            step_id=f"step_{len(self.experiment.steps) + 1}",
            step_type=ProgramStepType.TRANSFER
        )
        self.experiment.steps.append(new_step)
        self._refresh_step_list()
        self.current_step = new_step
        self._show_step_editor()
    
    def _on_delete_step(self):
        """删除步骤"""
        index = self.step_list.currentRow()
        if 0 <= index < len(self.experiment.steps):
            del self.experiment.steps[index]
            self._refresh_step_list()
    
    def _on_move_up(self):
        """上移步骤"""
        index = self.step_list.currentRow()
        if index > 0:
            self.experiment.steps[index], self.experiment.steps[index - 1] = \
                self.experiment.steps[index - 1], self.experiment.steps[index]
            self._refresh_step_list()
            self.step_list.setCurrentRow(index - 1)
    
    def _on_move_down(self):
        """下移步骤"""
        index = self.step_list.currentRow()
        if 0 <= index < len(self.experiment.steps) - 1:
            self.experiment.steps[index], self.experiment.steps[index + 1] = \
                self.experiment.steps[index + 1], self.experiment.steps[index]
            self._refresh_step_list()
            self.step_list.setCurrentRow(index + 1)
    
    def _on_save_program(self):
        """保存程序"""
        # 保存当前步骤
        if self.current_step and hasattr(self.current_step, '_save_func'):
            self.current_step._save_func()
        
        self.program_saved.emit(self.experiment)
        QMessageBox.information(self, "成功", "程序已保存")
        self.accept()

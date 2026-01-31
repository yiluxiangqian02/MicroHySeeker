"""
程序编辑器 - 单次实验步骤编辑
- 配液操作：显示溶液配方（溶液名称、原浓度、泵端口），目标浓度，是否溶剂，注液顺序
- 注液顺序在溶液配方表格中作为单独一列，可输入1,2,3...
- 电化学技术类型选择和参数放一个框内，删掉OCPT下拉选项
- OCPT反向电流检测单独列一个框，加持续时间
- CV/LSV/i-t不同技术对应参数变化
- 总体积单位改成mL
- 所有小数保留两位
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTextEdit, QMessageBox, QGroupBox, QFormLayout,
    QScrollArea, QWidget, QStackedWidget, QFrame, QTableWidget,
    QTableWidgetItem, QHeaderView, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import Optional, List

from src.models import (
    ProgStep, Experiment, ProgramStepType, ECTechnique, ECSettings,
    PrepSolStep, OCPTAction, SystemConfig, DilutionChannel
)


# 全局字体
FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)

# 步骤类型中文映射
STEP_TYPE_NAMES = {
    ProgramStepType.TRANSFER: "移液",
    ProgramStepType.PREP_SOL: "配液",
    ProgramStepType.FLUSH: "冲洗",
    ProgramStepType.EChem: "电化学",
    ProgramStepType.BLANK: "空白",
    ProgramStepType.EVACUATE: "排空",
}


class ProgramEditorDialog(QDialog):
    """
    单次实验程序编辑器
    
    === 后端接口 ===
    1. 移液: RS485Wrapper.start_pump(addr, dir, rpm), stop_pump(addr)
    2. 配液: 多泵协调配液，计算注液量
    3. 冲洗: RS485Wrapper.start_pump(addr, dir, rpm)
    4. 电化学: CHIWrapper.run_cv/lsv/it(params)
    5. 空白: 延时等待
    """
    program_saved = Signal(Experiment)
    
    def __init__(self, config: SystemConfig, experiment: Optional[Experiment] = None, parent=None):
        super().__init__(parent)
        self.config = config
        self.experiment = experiment or Experiment(exp_id="exp_001", exp_name="新实验")
        self.current_step: Optional[ProgStep] = None
        self.current_step_index = -1
        
        self.setWindowTitle("单次实验编辑")
        self.setGeometry(150, 100, 1200, 700)
        self.setFont(FONT_NORMAL)
        self._init_ui()
        self._refresh_step_list()
    
    def _init_ui(self):
        """初始化 UI"""
        main_layout = QHBoxLayout(self)
        
        # === 左侧：步骤列表 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        title_label = QLabel("步骤列表")
        title_label.setFont(FONT_TITLE)
        left_layout.addWidget(title_label)
        
        self.step_list = QListWidget()
        self.step_list.setFont(FONT_NORMAL)
        self.step_list.itemClicked.connect(self._on_step_selected)
        left_layout.addWidget(self.step_list)
        
        # 步骤管理按钮
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._on_add_step)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._on_delete_step)
        btn_layout.addWidget(del_btn)
        
        up_btn = QPushButton("上移")
        up_btn.clicked.connect(self._on_move_up)
        btn_layout.addWidget(up_btn)
        
        down_btn = QPushButton("下移")
        down_btn.clicked.connect(self._on_move_down)
        btn_layout.addWidget(down_btn)
        
        left_layout.addLayout(btn_layout)
        left_widget.setFixedWidth(300)
        main_layout.addWidget(left_widget)
        
        # === 右侧：步骤编辑区 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 步骤类型选择
        type_frame = QGroupBox("操作类型")
        type_frame.setFont(FONT_TITLE)
        type_layout = QHBoxLayout(type_frame)
        type_layout.addWidget(QLabel("类型:"))
        
        self.type_combo = QComboBox()
        self.type_combo.setFont(FONT_NORMAL)
        self.type_combo.addItem("移液", ProgramStepType.TRANSFER)
        self.type_combo.addItem("配液", ProgramStepType.PREP_SOL)
        self.type_combo.addItem("冲洗", ProgramStepType.FLUSH)
        self.type_combo.addItem("电化学", ProgramStepType.EChem)
        self.type_combo.addItem("空白", ProgramStepType.BLANK)
        self.type_combo.addItem("排空", ProgramStepType.EVACUATE)
        self.type_combo.currentIndexChanged.connect(self._on_step_type_changed)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        
        right_layout.addWidget(type_frame)
        
        # 参数编辑区（使用 QStackedWidget）
        self.params_stack = QStackedWidget()
        
        self.transfer_panel = self._create_transfer_panel()
        self.prep_sol_panel = self._create_prep_sol_panel()
        self.flush_panel = self._create_flush_panel()
        self.echem_panel = self._create_echem_panel()
        self.blank_panel = self._create_blank_panel()
        self.evacuate_panel = self._create_evacuate_panel()
        
        self.params_stack.addWidget(self.transfer_panel)   # index 0
        self.params_stack.addWidget(self.prep_sol_panel)   # index 1
        self.params_stack.addWidget(self.flush_panel)      # index 2
        self.params_stack.addWidget(self.echem_panel)      # index 3
        self.params_stack.addWidget(self.blank_panel)      # index 4
        self.params_stack.addWidget(self.evacuate_panel)   # index 5
        
        right_layout.addWidget(self.params_stack)
        
        # 保存按钮
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        save_btn = QPushButton("保存程序")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 25px; font-size: 12px;")
        save_btn.clicked.connect(self._on_save_program)
        save_layout.addWidget(save_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("padding: 10px 25px; font-size: 12px;")
        close_btn.clicked.connect(self.accept)
        save_layout.addWidget(close_btn)
        
        right_layout.addLayout(save_layout)
        main_layout.addWidget(right_widget)
    
    def _get_pump_addresses(self) -> List[str]:
        """获取泵地址列表"""
        return [str(i) for i in range(1, 13)]
    
    # === 创建各类型编辑面板 ===
    
    def _create_transfer_panel(self) -> QWidget:
        """移液参数面板 - 使用持续时间+单位"""
        panel = QGroupBox("移液参数")
        panel.setFont(FONT_TITLE)
        layout = QFormLayout(panel)
        
        self.tf_pump_combo = QComboBox()
        self.tf_pump_combo.addItems(self._get_pump_addresses())
        layout.addRow("泵地址:", self.tf_pump_combo)
        
        self.tf_dir_combo = QComboBox()
        self.tf_dir_combo.addItems(["正向", "反向"])
        layout.addRow("方向:", self.tf_dir_combo)
        
        self.tf_rpm_spin = QSpinBox()
        self.tf_rpm_spin.setRange(0, 1000)
        self.tf_rpm_spin.setValue(100)
        layout.addRow("转速(RPM):", self.tf_rpm_spin)
        
        # 持续时间 + 单位下拉
        duration_widget = QWidget()
        duration_layout = QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tf_duration_spin = QDoubleSpinBox()
        self.tf_duration_spin.setRange(0, 100000)
        self.tf_duration_spin.setDecimals(2)
        self.tf_duration_spin.setValue(10.00)
        duration_layout.addWidget(self.tf_duration_spin)
        
        self.tf_duration_unit = QComboBox()
        self.tf_duration_unit.addItems(["ms", "s", "min", "hr", "cycle"])
        self.tf_duration_unit.setCurrentText("s")
        duration_layout.addWidget(self.tf_duration_unit)
        
        layout.addRow("持续时间:", duration_widget)
        
        return panel
    
    def _create_prep_sol_panel(self) -> QWidget:
        """配液参数面板 - 表格中包含目标浓度列"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 溶液配方表格（从配液通道加载）
        recipe_group = QGroupBox("溶液配方")
        recipe_group.setFont(FONT_TITLE)
        recipe_layout = QVBoxLayout(recipe_group)
        
        # 表格列: 选择, 溶液名称, 原浓度(mol/L), 泵端口, 目标浓度(mol/L), 是否溶剂, 注液顺序
        self.recipe_table = QTableWidget()
        self.recipe_table.setColumnCount(7)
        self.recipe_table.setHorizontalHeaderLabels([
            "选择", "溶液名称", "原浓度(mol/L)", "泵端口", "目标浓度(mol/L)", "是否溶剂", "注液顺序"
        ])
        self.recipe_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recipe_table.setFont(FONT_NORMAL)
        self._refresh_recipe_table()
        recipe_layout.addWidget(self.recipe_table)
        
        layout.addWidget(recipe_group)
        
        # 配液参数
        param_group = QGroupBox("配液参数")
        param_group.setFont(FONT_TITLE)
        param_layout = QFormLayout(param_group)
        
        self.ps_vol_spin = QDoubleSpinBox()
        self.ps_vol_spin.setRange(0, 1000)
        self.ps_vol_spin.setDecimals(2)
        self.ps_vol_spin.setValue(5.00)
        param_layout.addRow("总体积(mL):", self.ps_vol_spin)
        
        layout.addWidget(param_group)
        layout.addStretch()
        
        return panel
    
    def _refresh_recipe_table(self):
        """刷新溶液配方表格 - 包含目标浓度列"""
        channels = self.config.dilution_channels
        self.recipe_table.setRowCount(len(channels))
        
        for row, ch in enumerate(channels):
            # 选择复选框
            check = QCheckBox()
            check.setChecked(True)
            check_widget = QWidget()
            check_layout = QHBoxLayout(check_widget)
            check_layout.addWidget(check)
            check_layout.setAlignment(Qt.AlignCenter)
            check_layout.setContentsMargins(0, 0, 0, 0)
            self.recipe_table.setCellWidget(row, 0, check_widget)
            
            # 溶液名称 (只读)
            name_item = QTableWidgetItem(ch.solution_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.recipe_table.setItem(row, 1, name_item)
            
            # 原浓度 (只读, 保留两位小数)
            conc_item = QTableWidgetItem(f"{ch.stock_concentration:.2f}")
            conc_item.setFlags(conc_item.flags() & ~Qt.ItemIsEditable)
            conc_item.setTextAlignment(Qt.AlignCenter)
            self.recipe_table.setItem(row, 2, conc_item)
            
            # 泵端口 (只读)
            port_item = QTableWidgetItem(str(ch.pump_address))
            port_item.setFlags(port_item.flags() & ~Qt.ItemIsEditable)
            port_item.setTextAlignment(Qt.AlignCenter)
            self.recipe_table.setItem(row, 3, port_item)
            
            # 目标浓度 (可编辑)
            target_spin = QDoubleSpinBox()
            target_spin.setRange(0, 1000)
            target_spin.setDecimals(2)
            target_spin.setValue(0.01)
            self.recipe_table.setCellWidget(row, 4, target_spin)
            
            # 是否溶剂
            solvent_check = QCheckBox()
            solvent_widget = QWidget()
            solvent_layout = QHBoxLayout(solvent_widget)
            solvent_layout.addWidget(solvent_check)
            solvent_layout.setAlignment(Qt.AlignCenter)
            solvent_layout.setContentsMargins(0, 0, 0, 0)
            self.recipe_table.setCellWidget(row, 5, solvent_widget)
            
            # 注液顺序 (可编辑)
            order_spin = QSpinBox()
            order_spin.setRange(1, 20)
            order_spin.setValue(row + 1)
            self.recipe_table.setCellWidget(row, 6, order_spin)
    
    def _create_flush_panel(self) -> QWidget:
        """冲洗参数面板"""
        panel = QGroupBox("冲洗参数")
        panel.setFont(FONT_TITLE)
        layout = QFormLayout(panel)
        
        self.fl_pump_combo = QComboBox()
        self.fl_pump_combo.addItems(self._get_pump_addresses())
        layout.addRow("泵地址:", self.fl_pump_combo)
        
        self.fl_dir_combo = QComboBox()
        self.fl_dir_combo.addItems(["正向", "反向"])
        layout.addRow("方向:", self.fl_dir_combo)
        
        self.fl_rpm_spin = QSpinBox()
        self.fl_rpm_spin.setRange(0, 1000)
        self.fl_rpm_spin.setValue(100)
        layout.addRow("转速(RPM):", self.fl_rpm_spin)
        
        self.fl_duration_spin = QDoubleSpinBox()
        self.fl_duration_spin.setRange(0, 1000)
        self.fl_duration_spin.setDecimals(2)
        self.fl_duration_spin.setValue(30.00)
        layout.addRow("循环时长(s):", self.fl_duration_spin)
        
        self.fl_cycles_spin = QSpinBox()
        self.fl_cycles_spin.setRange(1, 100)
        self.fl_cycles_spin.setValue(1)
        layout.addRow("循环次数:", self.fl_cycles_spin)
        
        return panel
    
    def _create_echem_panel(self) -> QWidget:
        """电化学参数面板 - 技术和参数在一个框内，OCPT检测单独框"""
        panel = QWidget()
        main_layout = QVBoxLayout(panel)
        
        # === 电化学技术参数 (一个框内) ===
        tech_group = QGroupBox("电化学技术")
        tech_group.setFont(FONT_TITLE)
        tech_layout = QVBoxLayout(tech_group)
        
        # 技术类型选择
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("技术类型:"))
        self.ec_tech_combo = QComboBox()
        self.ec_tech_combo.addItem("循环伏安法 (CV)", ECTechnique.CV)
        self.ec_tech_combo.addItem("线性扫描伏安法 (LSV)", ECTechnique.LSV)
        self.ec_tech_combo.addItem("计时电流法 (i-t)", ECTechnique.I_T)
        # 不包含OCPT
        self.ec_tech_combo.currentIndexChanged.connect(self._on_ec_tech_changed)
        type_row.addWidget(self.ec_tech_combo)
        type_row.addStretch()
        tech_layout.addLayout(type_row)
        
        # 参数区 (使用Grid布局)
        params_widget = QWidget()
        params_layout = QGridLayout(params_widget)
        params_layout.setSpacing(10)
        
        # 第一行: 初始电位, 上限电位
        params_layout.addWidget(QLabel("初始电位(V):"), 0, 0)
        self.ec_e0_spin = QDoubleSpinBox()
        self.ec_e0_spin.setRange(-10, 10)
        self.ec_e0_spin.setDecimals(2)
        params_layout.addWidget(self.ec_e0_spin, 0, 1)
        
        params_layout.addWidget(QLabel("上限电位(V):"), 0, 2)
        self.ec_eh_spin = QDoubleSpinBox()
        self.ec_eh_spin.setRange(-10, 10)
        self.ec_eh_spin.setDecimals(2)
        self.ec_eh_spin.setValue(0.80)
        params_layout.addWidget(self.ec_eh_spin, 0, 3)
        
        # 第二行: 下限电位, 终止电位
        params_layout.addWidget(QLabel("下限电位(V):"), 1, 0)
        self.ec_el_spin = QDoubleSpinBox()
        self.ec_el_spin.setRange(-10, 10)
        self.ec_el_spin.setDecimals(2)
        self.ec_el_spin.setValue(-0.20)
        params_layout.addWidget(self.ec_el_spin, 1, 1)
        
        params_layout.addWidget(QLabel("终止电位(V):"), 1, 2)
        self.ec_ef_spin = QDoubleSpinBox()
        self.ec_ef_spin.setRange(-10, 10)
        self.ec_ef_spin.setDecimals(2)
        params_layout.addWidget(self.ec_ef_spin, 1, 3)
        
        # 第三行: 扫速, 扫描方向
        params_layout.addWidget(QLabel("扫描速率(V/s):"), 2, 0)
        self.ec_scanrate_spin = QDoubleSpinBox()
        self.ec_scanrate_spin.setRange(0.0001, 10)
        self.ec_scanrate_spin.setDecimals(4)
        self.ec_scanrate_spin.setValue(0.05)
        params_layout.addWidget(self.ec_scanrate_spin, 2, 1)
        
        params_layout.addWidget(QLabel("扫描方向:"), 2, 2)
        self.ec_scandir_combo = QComboBox()
        self.ec_scandir_combo.addItems(["正向", "反向"])
        params_layout.addWidget(self.ec_scandir_combo, 2, 3)
        
        # 第四行: 扫描段数, 灵敏度
        params_layout.addWidget(QLabel("扫描段数:"), 3, 0)
        self.ec_segments_spin = QSpinBox()
        self.ec_segments_spin.setRange(1, 100)
        self.ec_segments_spin.setValue(2)
        params_layout.addWidget(self.ec_segments_spin, 3, 1)
        
        params_layout.addWidget(QLabel("灵敏度(V):"), 3, 2)
        self.ec_sensitivity_spin = QDoubleSpinBox()
        self.ec_sensitivity_spin.setRange(0.001, 100)
        self.ec_sensitivity_spin.setDecimals(3)
        self.ec_sensitivity_spin.setValue(1.00)
        params_layout.addWidget(self.ec_sensitivity_spin, 3, 3)
        
        # 第五行: 记录间隔, 自动灵敏度
        params_layout.addWidget(QLabel("记录间隔(mV):"), 4, 0)
        self.ec_interval_spin = QDoubleSpinBox()
        self.ec_interval_spin.setRange(0.1, 100)
        self.ec_interval_spin.setDecimals(2)
        self.ec_interval_spin.setValue(1.00)
        params_layout.addWidget(self.ec_interval_spin, 4, 1)
        
        self.ec_autosens_check = QCheckBox("自动灵敏度")
        self.ec_autosens_check.setToolTip("仅在扫速低于10mV/s时有效")
        params_layout.addWidget(self.ec_autosens_check, 4, 2, 1, 2)
        
        # 第六行: 静置时间, 运行时间(i-t用)
        params_layout.addWidget(QLabel("静置时间(秒):"), 5, 0)
        self.ec_quiettime_spin = QDoubleSpinBox()
        self.ec_quiettime_spin.setRange(0, 1000)
        self.ec_quiettime_spin.setDecimals(2)
        self.ec_quiettime_spin.setValue(2.00)
        params_layout.addWidget(self.ec_quiettime_spin, 5, 1)
        
        params_layout.addWidget(QLabel("运行时间(秒):"), 5, 2)
        self.ec_runtime_spin = QDoubleSpinBox()
        self.ec_runtime_spin.setRange(0, 10000)
        self.ec_runtime_spin.setDecimals(2)
        self.ec_runtime_spin.setValue(60.00)
        params_layout.addWidget(self.ec_runtime_spin, 5, 3)
        
        tech_layout.addWidget(params_widget)
        main_layout.addWidget(tech_group)
        
        # === OCPT 反向电流检测 (单独框) ===
        ocpt_group = QGroupBox("OCPT 反向电流检测")
        ocpt_group.setFont(FONT_TITLE)
        ocpt_layout = QFormLayout(ocpt_group)
        
        self.ec_ocpt_enable = QCheckBox("启用 OCPT 检测")
        ocpt_layout.addRow("", self.ec_ocpt_enable)
        
        self.ec_ocpt_threshold = QDoubleSpinBox()
        self.ec_ocpt_threshold.setRange(-1000, 0)
        self.ec_ocpt_threshold.setDecimals(2)
        self.ec_ocpt_threshold.setValue(-50.00)
        ocpt_layout.addRow("阈值电流(μA):", self.ec_ocpt_threshold)
        
        self.ec_ocpt_duration = QDoubleSpinBox()
        self.ec_ocpt_duration.setRange(0, 10000)
        self.ec_ocpt_duration.setDecimals(2)
        self.ec_ocpt_duration.setValue(5.00)
        ocpt_layout.addRow("持续时间(秒):", self.ec_ocpt_duration)
        
        self.ec_ocpt_action = QComboBox()
        self.ec_ocpt_action.addItem("仅记录", OCPTAction.LOG)
        self.ec_ocpt_action.addItem("暂停实验", OCPTAction.PAUSE)
        self.ec_ocpt_action.addItem("终止实验", OCPTAction.ABORT)
        ocpt_layout.addRow("触发动作:", self.ec_ocpt_action)
        
        main_layout.addWidget(ocpt_group)
        main_layout.addStretch()
        
        # 初始化时更新参数可用性
        self._on_ec_tech_changed(0)
        
        return panel
    
    def _on_ec_tech_changed(self, index: int):
        """电化学技术类型改变时更新参数可用性"""
        tech = self.ec_tech_combo.currentData()
        
        # CV: 所有参数可用
        # LSV: 上限电位、下限电位、扫描方向、扫描段数变灰
        # i-t: 上限电位、下限电位、扫描方向、扫描段数、终止电位、扫速、自动灵敏度变灰
        
        # 先全部启用
        self.ec_e0_spin.setEnabled(True)
        self.ec_eh_spin.setEnabled(True)
        self.ec_el_spin.setEnabled(True)
        self.ec_ef_spin.setEnabled(True)
        self.ec_scanrate_spin.setEnabled(True)
        self.ec_scandir_combo.setEnabled(True)
        self.ec_segments_spin.setEnabled(True)
        self.ec_autosens_check.setEnabled(True)
        self.ec_runtime_spin.setEnabled(True)
        
        if tech == ECTechnique.LSV:
            # LSV: 上限电位、下限电位、扫描方向、扫描段数变灰
            self.ec_eh_spin.setEnabled(False)
            self.ec_el_spin.setEnabled(False)
            self.ec_scandir_combo.setEnabled(False)
            self.ec_segments_spin.setEnabled(False)
        elif tech == ECTechnique.I_T:
            # i-t: 上限电位、下限电位、扫描方向、扫描段数、终止电位、扫速、自动灵敏度变灰
            self.ec_eh_spin.setEnabled(False)
            self.ec_el_spin.setEnabled(False)
            self.ec_scandir_combo.setEnabled(False)
            self.ec_segments_spin.setEnabled(False)
            self.ec_ef_spin.setEnabled(False)
            self.ec_scanrate_spin.setEnabled(False)
            self.ec_autosens_check.setEnabled(False)
    
    def _create_blank_panel(self) -> QWidget:
        """空白步骤面板"""
        panel = QGroupBox("空白步骤")
        panel.setFont(FONT_TITLE)
        layout = QFormLayout(panel)
        
        self.bl_duration_spin = QDoubleSpinBox()
        self.bl_duration_spin.setRange(0, 10000)
        self.bl_duration_spin.setDecimals(2)
        layout.addRow("持续时间(s):", self.bl_duration_spin)
        
        self.bl_notes_text = QTextEdit()
        self.bl_notes_text.setMaximumHeight(100)
        self.bl_notes_text.setPlaceholderText("输入备注信息...")
        layout.addRow("备注:", self.bl_notes_text)
        
        return panel
    
    def _create_evacuate_panel(self) -> QWidget:
        """排空参数面板 - Flusher的Outlet阶段"""
        panel = QGroupBox("排空参数")
        panel.setFont(FONT_TITLE)
        layout = QFormLayout(panel)
        
        self.ev_pump_combo = QComboBox()
        self.ev_pump_combo.addItems(self._get_pump_addresses())
        layout.addRow("Outlet泵地址:", self.ev_pump_combo)
        
        self.ev_dir_combo = QComboBox()
        self.ev_dir_combo.addItems(["正向", "反向"])
        layout.addRow("方向:", self.ev_dir_combo)
        
        self.ev_rpm_spin = QSpinBox()
        self.ev_rpm_spin.setRange(0, 1000)
        self.ev_rpm_spin.setValue(100)
        layout.addRow("转速(RPM):", self.ev_rpm_spin)
        
        # 持续时间 + 单位
        duration_widget = QWidget()
        duration_layout = QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ev_duration_spin = QDoubleSpinBox()
        self.ev_duration_spin.setRange(0, 10000)
        self.ev_duration_spin.setDecimals(2)
        self.ev_duration_spin.setValue(30.00)
        duration_layout.addWidget(self.ev_duration_spin)
        
        self.ev_duration_unit = QComboBox()
        self.ev_duration_unit.addItems(["ms", "s", "min", "hr", "cycle"])
        self.ev_duration_unit.setCurrentText("s")
        duration_layout.addWidget(self.ev_duration_unit)
        
        layout.addRow("持续时间:", duration_widget)
        
        self.ev_cycles_spin = QSpinBox()
        self.ev_cycles_spin.setRange(1, 100)
        self.ev_cycles_spin.setValue(1)
        layout.addRow("循环次数:", self.ev_cycles_spin)
        
        return panel
    
    # === 事件处理 ===
    
    def _refresh_step_list(self):
        """刷新步骤列表 - 使用中文"""
        self.step_list.clear()
        for i, step in enumerate(self.experiment.steps):
            type_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
            item = QListWidgetItem(f"[{i+1}] {type_name}")
            self.step_list.addItem(item)
    
    def _on_step_selected(self, item: QListWidgetItem):
        """选中步骤"""
        self._save_current_step()
        
        index = self.step_list.row(item)
        if 0 <= index < len(self.experiment.steps):
            self.current_step_index = index
            self.current_step = self.experiment.steps[index]
            self._load_step_to_ui()
    
    def _load_step_to_ui(self):
        """将步骤数据加载到 UI"""
        if not self.current_step:
            return
        
        step = self.current_step
        
        # 规范化 step_type
        if isinstance(step.step_type, str):
            try:
                step.step_type = ProgramStepType(step.step_type)
            except:
                for st in ProgramStepType:
                    if st.value == step.step_type:
                        step.step_type = st
                        break
        
        # 设置类型下拉框
        type_index = {
            ProgramStepType.TRANSFER: 0,
            ProgramStepType.PREP_SOL: 1,
            ProgramStepType.FLUSH: 2,
            ProgramStepType.EChem: 3,
            ProgramStepType.BLANK: 4,
            ProgramStepType.EVACUATE: 5,
        }.get(step.step_type, 0)
        
        self.type_combo.blockSignals(True)
        self.type_combo.setCurrentIndex(type_index)
        self.type_combo.blockSignals(False)
        self.params_stack.setCurrentIndex(type_index)
        
        # 加载参数
        if step.step_type == ProgramStepType.TRANSFER:
            self._load_transfer(step)
        elif step.step_type == ProgramStepType.PREP_SOL:
            self._load_prep_sol(step)
        elif step.step_type == ProgramStepType.FLUSH:
            self._load_flush(step)
        elif step.step_type == ProgramStepType.EChem:
            self._load_echem(step)
        elif step.step_type == ProgramStepType.BLANK:
            self._load_blank(step)
        elif step.step_type == ProgramStepType.EVACUATE:
            self._load_evacuate(step)
    
    def _load_transfer(self, step: ProgStep):
        if step.pump_address:
            self.tf_pump_combo.setCurrentText(str(step.pump_address))
        self.tf_dir_combo.setCurrentText("正向" if step.pump_direction == "FWD" else "反向")
        self.tf_rpm_spin.setValue(step.pump_rpm or 100)
        # 加载持续时间
        self.tf_duration_spin.setValue(step.transfer_duration or 10.0)
        self.tf_duration_unit.setCurrentText(step.transfer_duration_unit or "s")
    
    def _load_prep_sol(self, step: ProgStep):
        """加载配液参数"""
        self._refresh_recipe_table()
        
        if step.prep_sol_params:
            # 体积从μL转换为mL
            vol_ml = step.prep_sol_params.total_volume_ul / 1000.0
            self.ps_vol_spin.setValue(round(vol_ml, 2))
    
    def _load_flush(self, step: ProgStep):
        if step.pump_address:
            self.fl_pump_combo.setCurrentText(str(step.pump_address))
        self.fl_dir_combo.setCurrentText("正向" if step.pump_direction == "FWD" else "反向")
        self.fl_rpm_spin.setValue(step.flush_rpm or 100)
        self.fl_duration_spin.setValue(round(step.flush_cycle_duration_s or 30, 2))
        self.fl_cycles_spin.setValue(step.flush_cycles or 1)
    
    def _load_echem(self, step: ProgStep):
        if step.ec_settings:
            ec = step.ec_settings
            # 技术类型 (不含OCPT)
            tech_idx = {
                ECTechnique.CV: 0, ECTechnique.LSV: 1, ECTechnique.I_T: 2
            }.get(ec.technique, 0)
            self.ec_tech_combo.setCurrentIndex(tech_idx)
            self._on_ec_tech_changed(tech_idx)
            
            self.ec_e0_spin.setValue(round(ec.e0 or 0, 2))
            self.ec_eh_spin.setValue(round(ec.eh or 0.8, 2))
            self.ec_el_spin.setValue(round(ec.el or -0.2, 2))
            self.ec_ef_spin.setValue(round(ec.ef or 0, 2))
            self.ec_scanrate_spin.setValue(ec.scan_rate or 0.05)
            self.ec_segments_spin.setValue(ec.seg_num)
            self.ec_quiettime_spin.setValue(round(ec.quiet_time_s, 2))
            self.ec_runtime_spin.setValue(round(ec.run_time_s or 60, 2))
            self.ec_autosens_check.setChecked(ec.autosensitivity)
            self.ec_ocpt_enable.setChecked(ec.ocpt_enabled)
            self.ec_ocpt_threshold.setValue(round(ec.ocpt_threshold_uA, 2))
            
            action_idx = {OCPTAction.LOG: 0, OCPTAction.PAUSE: 1, OCPTAction.ABORT: 2}.get(ec.ocpt_action, 0)
            self.ec_ocpt_action.setCurrentIndex(action_idx)
    
    def _load_blank(self, step: ProgStep):
        self.bl_duration_spin.setValue(round(step.duration_s or 0, 2))
        self.bl_notes_text.setPlainText(step.notes or "")
    
    def _load_evacuate(self, step: ProgStep):
        """加载排空参数"""
        if step.pump_address:
            self.ev_pump_combo.setCurrentText(str(step.pump_address))
        self.ev_dir_combo.setCurrentText("正向" if step.pump_direction == "FWD" else "反向")
        self.ev_rpm_spin.setValue(step.pump_rpm or 100)
        self.ev_duration_spin.setValue(step.transfer_duration or 30.0)
        self.ev_duration_unit.setCurrentText(step.transfer_duration_unit or "s")
        self.ev_cycles_spin.setValue(step.flush_cycles or 1)
    
    def _save_current_step(self):
        """保存当前步骤"""
        if not self.current_step:
            return
        
        step = self.current_step
        step.step_type = self.type_combo.currentData()
        
        if step.step_type == ProgramStepType.TRANSFER:
            step.pump_address = int(self.tf_pump_combo.currentText())
            step.pump_direction = "FWD" if self.tf_dir_combo.currentText() == "正向" else "REV"
            step.pump_rpm = self.tf_rpm_spin.value()
            # 保存持续时间和单位
            step.transfer_duration = round(self.tf_duration_spin.value(), 2)
            step.transfer_duration_unit = self.tf_duration_unit.currentText()
            
        elif step.step_type == ProgramStepType.PREP_SOL:
            if not step.prep_sol_params:
                step.prep_sol_params = PrepSolStep(target_concentration=0.01)
            # 体积从mL转换为μL
            step.prep_sol_params.total_volume_ul = round(self.ps_vol_spin.value() * 1000, 2)
            
            # 保存选中的溶液、目标浓度和注液顺序
            injection_order = []
            order_data = []
            target_concs = {}
            for row in range(self.recipe_table.rowCount()):
                check_widget = self.recipe_table.cellWidget(row, 0)
                if check_widget:
                    check = check_widget.findChild(QCheckBox)
                    if check and check.isChecked():
                        name = self.recipe_table.item(row, 1).text()
                        # 获取目标浓度 (第4列)
                        target_spin = self.recipe_table.cellWidget(row, 4)
                        if target_spin:
                            target_concs[name] = target_spin.value()
                        # 获取注液顺序 (第6列)
                        order_spin = self.recipe_table.cellWidget(row, 6)
                        order = order_spin.value() if order_spin else row + 1
                        order_data.append((order, name))
            
            # 按注液顺序排序
            order_data.sort(key=lambda x: x[0])
            step.prep_sol_params.injection_order = [x[1] for x in order_data]
            
            # 检查溶剂标记 (第5列)
            step.prep_sol_params.is_solvent = False
            for row in range(self.recipe_table.rowCount()):
                solvent_widget = self.recipe_table.cellWidget(row, 5)
                if solvent_widget:
                    solvent_check = solvent_widget.findChild(QCheckBox)
                    if solvent_check and solvent_check.isChecked():
                        step.prep_sol_params.is_solvent = True
                        break
            
        elif step.step_type == ProgramStepType.FLUSH:
            step.pump_address = int(self.fl_pump_combo.currentText())
            step.pump_direction = "FWD" if self.fl_dir_combo.currentText() == "正向" else "REV"
            step.flush_rpm = self.fl_rpm_spin.value()
            step.flush_cycle_duration_s = round(self.fl_duration_spin.value(), 2)
            step.flush_cycles = self.fl_cycles_spin.value()
            
        elif step.step_type == ProgramStepType.EChem:
            if not step.ec_settings:
                step.ec_settings = ECSettings()
            ec = step.ec_settings
            ec.technique = self.ec_tech_combo.currentData()
            ec.e0 = round(self.ec_e0_spin.value(), 2)
            ec.eh = round(self.ec_eh_spin.value(), 2)
            ec.el = round(self.ec_el_spin.value(), 2)
            ec.ef = round(self.ec_ef_spin.value(), 2)
            ec.scan_rate = self.ec_scanrate_spin.value()
            ec.seg_num = self.ec_segments_spin.value()
            ec.quiet_time_s = round(self.ec_quiettime_spin.value(), 2)
            ec.run_time_s = round(self.ec_runtime_spin.value(), 2)
            ec.autosensitivity = self.ec_autosens_check.isChecked()
            ec.ocpt_enabled = self.ec_ocpt_enable.isChecked()
            ec.ocpt_threshold_uA = round(self.ec_ocpt_threshold.value(), 2)
            ec.ocpt_action = self.ec_ocpt_action.currentData()
            
        elif step.step_type == ProgramStepType.BLANK:
            step.duration_s = round(self.bl_duration_spin.value(), 2)
            step.notes = self.bl_notes_text.toPlainText()
        
        elif step.step_type == ProgramStepType.EVACUATE:
            step.pump_address = int(self.ev_pump_combo.currentText())
            step.pump_direction = "FWD" if self.ev_dir_combo.currentText() == "正向" else "REV"
            step.pump_rpm = self.ev_rpm_spin.value()
            step.transfer_duration = round(self.ev_duration_spin.value(), 2)
            step.transfer_duration_unit = self.ev_duration_unit.currentText()
            step.flush_cycles = self.ev_cycles_spin.value()
    
    def _on_step_type_changed(self, index: int):
        """步骤类型切换 - 只在有选中步骤时更新"""
        self.params_stack.setCurrentIndex(index)
        
        # 只有在有选中步骤时才更新步骤类型
        if self.current_step and self.current_step_index >= 0:
            self.current_step.step_type = self.type_combo.currentData()
            self._refresh_step_list()
            # 保持选中状态
            self.step_list.setCurrentRow(self.current_step_index)
            
        # 如果切换到配液，刷新溶液配方
        if index == 1:
            self._refresh_recipe_table()
    
    def _on_add_step(self):
        """添加步骤 - 使用当前选中的类型"""
        # 先保存当前步骤
        self._save_current_step()
        
        # 获取当前选中的类型
        selected_type = self.type_combo.currentData()
        
        new_step = ProgStep(
            step_id=f"step_{len(self.experiment.steps) + 1}",
            step_type=selected_type
        )
        self.experiment.steps.append(new_step)
        self._refresh_step_list()
        
        # 清除当前选中状态，光标不停留在新增步骤上
        self.step_list.clearSelection()
        self.current_step = None
        self.current_step_index = -1
    
    def _on_delete_step(self):
        """删除步骤"""
        index = self.step_list.currentRow()
        if 0 <= index < len(self.experiment.steps):
            del self.experiment.steps[index]
            self.current_step = None
            self.current_step_index = -1
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
        self._save_current_step()
        self.program_saved.emit(self.experiment)
        QMessageBox.information(self, "成功", "程序已保存")
        self.accept()

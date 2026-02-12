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
    QTableWidgetItem, QHeaderView, QGridLayout, QButtonGroup, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QBrush, QColor
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
    ProgramStepType.ECHEM: "电化学",
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
        
        # 初始化时填充默认泵信息（移液/Transfer）
        self._apply_pump_defaults_for_type(ProgramStepType.TRANSFER)
    
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
        self.step_list.setWordWrap(True)
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
        
        # 步骤类型选择 - 使用横向按钮组
        type_frame = QGroupBox("操作类型")
        type_frame.setFont(FONT_TITLE)
        type_layout = QHBoxLayout(type_frame)
        type_layout.setSpacing(5)
        
        # 创建按钮组
        self.type_button_group = QButtonGroup(self)
        self.type_buttons = {}
        
        # 定义按钮样式 - 去除焦点虚线框
        button_style_normal = """
            QPushButton {
                padding: 8px 16px;
                border: 2px solid #ccc;
                border-radius: 5px;
                background-color: #f5f5f5;
                font-size: 11px;
                min-width: 60px;
                outline: none;
            }
            QPushButton:hover {
                border-color: #4CAF50;
                background-color: #e8f5e9;
            }
            QPushButton:focus {
                outline: none;
            }
        """
        button_style_checked = """
            QPushButton {
                padding: 8px 16px;
                border: 2px solid #4CAF50;
                border-radius: 5px;
                background-color: #4CAF50;
                color: white;
                font-size: 11px;
                font-weight: bold;
                min-width: 60px;
                outline: none;
            }
            QPushButton:focus {
                outline: none;
            }
        """
        
        # 创建各类型按钮
        type_buttons_data = [
            ("移液", ProgramStepType.TRANSFER, 0),
            ("配液", ProgramStepType.PREP_SOL, 1),
            ("冲洗", ProgramStepType.FLUSH, 2),
            ("电化学", ProgramStepType.ECHEM, 3),
            ("空白", ProgramStepType.BLANK, 4),
            ("排空", ProgramStepType.EVACUATE, 5),
        ]
        
        for name, step_type, idx in type_buttons_data:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet(button_style_normal)
            btn.setProperty("step_type", step_type)
            btn.setProperty("panel_index", idx)
            btn.setProperty("style_normal", button_style_normal)
            btn.setProperty("style_checked", button_style_checked)
            btn.clicked.connect(lambda checked, b=btn: self._on_type_button_clicked(b))
            self.type_button_group.addButton(btn, idx)
            self.type_buttons[step_type] = btn
            type_layout.addWidget(btn)
        
        type_layout.addStretch()
        right_layout.addWidget(type_frame)
        
        # 默认选中第一个按钮
        first_btn = self.type_buttons[ProgramStepType.TRANSFER]
        first_btn.setChecked(True)
        first_btn.setStyleSheet(first_btn.property("style_checked"))
        # 取消按钮焦点策略，防止虚线框
        for btn in self.type_buttons.values():
            btn.setFocusPolicy(Qt.NoFocus)
        
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
        """移液参数面板 - 泵地址和方向只读显示"""
        panel = QGroupBox("移液参数")
        panel.setFont(FONT_TITLE)
        layout = QFormLayout(panel)
        
        # 泵地址（只读显示）
        self.tf_pump_label = QLineEdit()
        self.tf_pump_label.setReadOnly(True)
        self.tf_pump_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout.addRow("Transfer泵地址:", self.tf_pump_label)
        
        # 方向（只读显示）
        self.tf_dir_label = QLineEdit()
        self.tf_dir_label.setReadOnly(True)
        self.tf_dir_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout.addRow("方向:", self.tf_dir_label)
        
        self.tf_rpm_spin = QSpinBox()
        self.tf_rpm_spin.setRange(0, 1000)
        self.tf_rpm_spin.setValue(100)
        layout.addRow("转速(RPM):", self.tf_rpm_spin)
        
        self.tf_duration_spin = QDoubleSpinBox()
        self.tf_duration_spin.setRange(0, 100000)
        self.tf_duration_spin.setDecimals(2)
        self.tf_duration_spin.setValue(10.00)
        layout.addRow("持续时间(s):", self.tf_duration_spin)
        
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
        self.ps_vol_spin.setValue(100.00)  # 默认100mL
        param_layout.addRow("总体积(mL):", self.ps_vol_spin)
        
        layout.addWidget(param_group)
        layout.addStretch()
        
        return panel
    
    def _get_inlet_pump_info(self):
        """获取 Inlet 泵信息（用作溶剂/H2O泵）"""
        for ch in self.config.flush_channels:
            if ch.work_type == "Inlet":
                return {"address": ch.pump_address, "direction": ch.direction, "name": ch.pump_name}
        return None
    
    def _refresh_recipe_table(self):
        """刷新溶液配方表格 - 包含目标浓度列
        
        自动追加 H2O 行：使用 Inlet 泵作为溶剂泵，泵地址实时同步，
        溶剂标记默认勾选且不可取消，目标浓度不可设置。
        """
        channels = self.config.dilution_channels
        inlet_info = self._get_inlet_pump_info()
        
        # 行数 = 配液通道 + 1 (H2O溶剂行)
        total_rows = len(channels) + (1 if inlet_info else 0)
        self.recipe_table.setRowCount(total_rows)
        
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
            
            # 溶剂勾选后禁用目标浓度
            _target = target_spin  # capture for lambda
            solvent_check.toggled.connect(
                lambda checked, ts=_target: self._on_solvent_toggled(checked, ts)
            )
            
            # 注液顺序 (可编辑, 允许相同编号表示同时注液)
            order_spin = QSpinBox()
            order_spin.setRange(1, 20)
            order_spin.setValue(row + 1)
            self.recipe_table.setCellWidget(row, 6, order_spin)
        
        # === H2O 溶剂行 (Inlet泵) ===
        if inlet_info:
            h2o_row = len(channels)
            
            # 选择复选框 - 默认选中
            check = QCheckBox()
            check.setChecked(True)
            check_widget = QWidget()
            check_layout = QHBoxLayout(check_widget)
            check_layout.addWidget(check)
            check_layout.setAlignment(Qt.AlignCenter)
            check_layout.setContentsMargins(0, 0, 0, 0)
            self.recipe_table.setCellWidget(h2o_row, 0, check_widget)
            
            # 溶液名称 - H2O (只读, 蓝色底色)
            name_item = QTableWidgetItem("H2O")
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setBackground(QBrush(QColor("#E3F2FD")))
            self.recipe_table.setItem(h2o_row, 1, name_item)
            
            # 原浓度 - 0 (溶剂无浓度)
            conc_item = QTableWidgetItem("溶剂")
            conc_item.setFlags(conc_item.flags() & ~Qt.ItemIsEditable)
            conc_item.setTextAlignment(Qt.AlignCenter)
            conc_item.setBackground(QBrush(QColor("#E3F2FD")))
            self.recipe_table.setItem(h2o_row, 2, conc_item)
            
            # 泵端口 - 实时从 Inlet 同步
            port_item = QTableWidgetItem(str(inlet_info["address"]))
            port_item.setFlags(port_item.flags() & ~Qt.ItemIsEditable)
            port_item.setTextAlignment(Qt.AlignCenter)
            port_item.setBackground(QBrush(QColor("#E3F2FD")))
            self.recipe_table.setItem(h2o_row, 3, port_item)
            
            # 目标浓度 - 不可设置 (溶剂自动补足)
            target_spin = QDoubleSpinBox()
            target_spin.setRange(0, 0)
            target_spin.setDecimals(2)
            target_spin.setValue(0.0)
            target_spin.setEnabled(False)
            target_spin.setStyleSheet("background-color: #E3F2FD;")
            self.recipe_table.setCellWidget(h2o_row, 4, target_spin)
            
            # 是否溶剂 - 强制勾选, 不可取消
            solvent_check = QCheckBox()
            solvent_check.setChecked(True)
            solvent_check.setEnabled(False)  # 不可取消
            solvent_widget = QWidget()
            solvent_layout = QHBoxLayout(solvent_widget)
            solvent_layout.addWidget(solvent_check)
            solvent_layout.setAlignment(Qt.AlignCenter)
            solvent_layout.setContentsMargins(0, 0, 0, 0)
            solvent_widget.setStyleSheet("background-color: #E3F2FD;")
            self.recipe_table.setCellWidget(h2o_row, 5, solvent_widget)
            
            # 注液顺序 - 默认最后
            order_spin = QSpinBox()
            order_spin.setRange(1, 20)
            order_spin.setValue(total_rows)
            self.recipe_table.setCellWidget(h2o_row, 6, order_spin)
    
    def _on_solvent_toggled(self, checked: bool, target_spin: QDoubleSpinBox):
        """溶剂勾选后禁用目标浓度输入（溶剂自动补充到总体积）"""
        target_spin.setEnabled(not checked)
        if checked:
            target_spin.setValue(0.0)
    
    def _create_flush_panel(self) -> QWidget:
        """冲洗参数面板 - 泵地址和方向只读显示"""
        panel = QGroupBox("冲洗参数")
        panel.setFont(FONT_TITLE)
        layout = QFormLayout(panel)
        
        # 泵地址（只读显示）
        self.fl_pump_label = QLineEdit()
        self.fl_pump_label.setReadOnly(True)
        self.fl_pump_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout.addRow("Inlet泵地址:", self.fl_pump_label)
        
        # 方向（只读显示）
        self.fl_dir_label = QLineEdit()
        self.fl_dir_label.setReadOnly(True)
        self.fl_dir_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout.addRow("方向:", self.fl_dir_label)
        
        self.fl_rpm_spin = QSpinBox()
        self.fl_rpm_spin.setRange(0, 1000)
        self.fl_rpm_spin.setValue(100)
        layout.addRow("转速(RPM):", self.fl_rpm_spin)
        
        self.fl_duration_spin = QDoubleSpinBox()
        self.fl_duration_spin.setRange(0, 1000)
        self.fl_duration_spin.setDecimals(2)
        self.fl_duration_spin.setValue(30.00)
        layout.addRow("单次时长(s):", self.fl_duration_spin)
        
        self.fl_cycles_spin = QSpinBox()
        self.fl_cycles_spin.setRange(1, 100)
        self.fl_cycles_spin.setValue(1)
        layout.addRow("循环次数:", self.fl_cycles_spin)
        
        return panel
    
    def _create_echem_panel(self) -> QWidget:
        """电化学参数面板 - 5个技术类型按钮直接切换，参数随技术变化"""
        panel = QWidget()
        main_layout = QVBoxLayout(panel)
        main_layout.setSpacing(6)
        
        # === 技术类型按钮行 ===
        tech_group = QGroupBox("电化学技术")
        tech_group.setFont(FONT_TITLE)
        tech_outer = QVBoxLayout(tech_group)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self._ec_tech_buttons: dict = {}   # ECTechnique -> QPushButton
        self._ec_current_tech: ECTechnique = ECTechnique.CV
        
        TECH_LABELS = [
            (ECTechnique.CV,   "CV\n循环伏安"),
            (ECTechnique.LSV,  "LSV\n线性扫描"),
            (ECTechnique.I_T,  "i-t\n计时电流"),
            (ECTechnique.EIS,  "EIS\n交流阻抗"),
            (ECTechnique.OCPT, "OCPT\n开路电位"),
        ]
        
        _ACTIVE_STYLE = (
            "QPushButton{background:#1976D2;color:white;font-weight:bold;"
            "border:2px solid #0D47A1;border-radius:6px;padding:8px 4px;}"
        )
        _IDLE_STYLE = (
            "QPushButton{background:#F5F5F5;color:#333;border:1px solid #BDBDBD;"
            "border-radius:6px;padding:8px 4px;}"
            "QPushButton:hover{background:#E0E0E0;}"
        )
        
        for tech, label in TECH_LABELS:
            btn = QPushButton(label)
            btn.setFont(QFont("Microsoft YaHei", 9))
            btn.setMinimumHeight(44)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_IDLE_STYLE)
            btn.clicked.connect(lambda checked=False, t=tech: self._on_ec_tech_btn_clicked(t))
            btn_row.addWidget(btn)
            self._ec_tech_buttons[tech] = btn
        
        self._ec_active_style = _ACTIVE_STYLE
        self._ec_idle_style = _IDLE_STYLE
        tech_outer.addLayout(btn_row)
        
        # 保留兼容: ec_tech_combo (hidden) 用于 save/load
        self.ec_tech_combo = QComboBox()
        self.ec_tech_combo.addItem("CV", ECTechnique.CV)
        self.ec_tech_combo.addItem("LSV", ECTechnique.LSV)
        self.ec_tech_combo.addItem("I_T", ECTechnique.I_T)
        self.ec_tech_combo.addItem("EIS", ECTechnique.EIS)
        self.ec_tech_combo.addItem("OCPT", ECTechnique.OCPT)
        self.ec_tech_combo.hide()
        tech_outer.addWidget(self.ec_tech_combo)
        
        # ---- 各技术参数区 (使用 QStackedWidget) ----
        self._ec_params_stack = QStackedWidget()
        
        # --- CV 参数页 (index 0) ---
        cv_page = QWidget()
        cv_lay = QGridLayout(cv_page); cv_lay.setSpacing(8)
        cv_lay.addWidget(QLabel("初始电位 E0(V):"), 0, 0)
        self.ec_e0_spin = QDoubleSpinBox(); self.ec_e0_spin.setRange(-10,10); self.ec_e0_spin.setDecimals(3)
        cv_lay.addWidget(self.ec_e0_spin, 0, 1)
        cv_lay.addWidget(QLabel("上限电位 Eh(V):"), 0, 2)
        self.ec_eh_spin = QDoubleSpinBox(); self.ec_eh_spin.setRange(-10,10); self.ec_eh_spin.setDecimals(3); self.ec_eh_spin.setValue(0.8)
        cv_lay.addWidget(self.ec_eh_spin, 0, 3)
        cv_lay.addWidget(QLabel("下限电位 El(V):"), 1, 0)
        self.ec_el_spin = QDoubleSpinBox(); self.ec_el_spin.setRange(-10,10); self.ec_el_spin.setDecimals(3); self.ec_el_spin.setValue(-0.2)
        cv_lay.addWidget(self.ec_el_spin, 1, 1)
        cv_lay.addWidget(QLabel("终止电位 Ef(V):"), 1, 2)
        self.ec_ef_spin = QDoubleSpinBox(); self.ec_ef_spin.setRange(-10,10); self.ec_ef_spin.setDecimals(3)
        cv_lay.addWidget(self.ec_ef_spin, 1, 3)
        cv_lay.addWidget(QLabel("扫描速率(V/s):"), 2, 0)
        self.ec_scanrate_spin = QDoubleSpinBox(); self.ec_scanrate_spin.setRange(0.0001,10); self.ec_scanrate_spin.setDecimals(4); self.ec_scanrate_spin.setValue(0.05)
        cv_lay.addWidget(self.ec_scanrate_spin, 2, 1)
        cv_lay.addWidget(QLabel("扫描方向:"), 2, 2)
        self.ec_scandir_combo = QComboBox(); self.ec_scandir_combo.addItems(["正向","反向"])
        cv_lay.addWidget(self.ec_scandir_combo, 2, 3)
        cv_lay.addWidget(QLabel("扫描段数:"), 3, 0)
        self.ec_segments_spin = QSpinBox(); self.ec_segments_spin.setRange(1,100); self.ec_segments_spin.setValue(2)
        cv_lay.addWidget(self.ec_segments_spin, 3, 1)
        cv_lay.addWidget(QLabel("灵敏度(A/V):"), 3, 2)
        self.ec_sensitivity_edit = QLineEdit("1e-1")
        self.ec_sensitivity_edit.setToolTip("科学计数法，如 1e-1, 1e-3, 1e-6")
        self.ec_sensitivity_edit.setPlaceholderText("如 1e-1")
        cv_lay.addWidget(self.ec_sensitivity_edit, 3, 3)
        cv_lay.addWidget(QLabel("记录间隔(mV):"), 4, 0)
        self.ec_interval_spin = QDoubleSpinBox(); self.ec_interval_spin.setRange(0.1,100); self.ec_interval_spin.setDecimals(2); self.ec_interval_spin.setValue(1.0)
        cv_lay.addWidget(self.ec_interval_spin, 4, 1)
        cv_lay.addWidget(QLabel("静置时间(s):"), 4, 2)
        self.ec_quiettime_spin = QDoubleSpinBox(); self.ec_quiettime_spin.setRange(0,1000); self.ec_quiettime_spin.setDecimals(2); self.ec_quiettime_spin.setValue(2.0)
        cv_lay.addWidget(self.ec_quiettime_spin, 4, 3)
        self._ec_params_stack.addWidget(cv_page)  # index 0
        
        # --- LSV 参数页 (index 1) ---
        lsv_page = QWidget()
        lsv_lay = QGridLayout(lsv_page); lsv_lay.setSpacing(8)
        lsv_lay.addWidget(QLabel("初始电位 E0(V):"), 0, 0)
        self._lsv_e0 = QDoubleSpinBox(); self._lsv_e0.setRange(-10,10); self._lsv_e0.setDecimals(3)
        lsv_lay.addWidget(self._lsv_e0, 0, 1)
        lsv_lay.addWidget(QLabel("终止电位 Ef(V):"), 0, 2)
        self._lsv_ef = QDoubleSpinBox(); self._lsv_ef.setRange(-10,10); self._lsv_ef.setDecimals(3); self._lsv_ef.setValue(1.0)
        lsv_lay.addWidget(self._lsv_ef, 0, 3)
        lsv_lay.addWidget(QLabel("扫描速率(V/s):"), 1, 0)
        self._lsv_scanrate = QDoubleSpinBox(); self._lsv_scanrate.setRange(0.0001,10); self._lsv_scanrate.setDecimals(4); self._lsv_scanrate.setValue(0.05)
        lsv_lay.addWidget(self._lsv_scanrate, 1, 1)
        lsv_lay.addWidget(QLabel("灵敏度(A/V):"), 1, 2)
        self._lsv_sensitivity = QLineEdit("1e-1")
        self._lsv_sensitivity.setPlaceholderText("如 1e-1")
        lsv_lay.addWidget(self._lsv_sensitivity, 1, 3)
        lsv_lay.addWidget(QLabel("记录间隔(mV):"), 2, 0)
        self._lsv_interval = QDoubleSpinBox(); self._lsv_interval.setRange(0.1,100); self._lsv_interval.setDecimals(2); self._lsv_interval.setValue(1.0)
        lsv_lay.addWidget(self._lsv_interval, 2, 1)
        lsv_lay.addWidget(QLabel("静置时间(s):"), 2, 2)
        self._lsv_quiettime = QDoubleSpinBox(); self._lsv_quiettime.setRange(0,1000); self._lsv_quiettime.setDecimals(2); self._lsv_quiettime.setValue(2.0)
        lsv_lay.addWidget(self._lsv_quiettime, 2, 3)
        self._ec_params_stack.addWidget(lsv_page)  # index 1
        
        # --- i-t 参数页 (index 2) ---
        it_page = QWidget()
        it_lay = QGridLayout(it_page); it_lay.setSpacing(8)
        it_lay.addWidget(QLabel("恒电位 E0(V):"), 0, 0)
        self._it_e0 = QDoubleSpinBox(); self._it_e0.setRange(-10,10); self._it_e0.setDecimals(3); self._it_e0.setValue(0.2)
        it_lay.addWidget(self._it_e0, 0, 1)
        it_lay.addWidget(QLabel("运行时间(s):"), 0, 2)
        self.ec_runtime_spin = QDoubleSpinBox(); self.ec_runtime_spin.setRange(0,100000); self.ec_runtime_spin.setDecimals(2); self.ec_runtime_spin.setValue(60.0)
        it_lay.addWidget(self.ec_runtime_spin, 0, 3)
        it_lay.addWidget(QLabel("采样间隔(ms):"), 1, 0)
        self._it_interval = QDoubleSpinBox(); self._it_interval.setRange(0.1,10000); self._it_interval.setDecimals(2); self._it_interval.setValue(100.0)
        it_lay.addWidget(self._it_interval, 1, 1)
        it_lay.addWidget(QLabel("灵敏度(A/V):"), 1, 2)
        self._it_sensitivity = QLineEdit("1e-4")
        self._it_sensitivity.setPlaceholderText("如 1e-4")
        it_lay.addWidget(self._it_sensitivity, 1, 3)
        it_lay.addWidget(QLabel("静置时间(s):"), 2, 0)
        self._it_quiettime = QDoubleSpinBox(); self._it_quiettime.setRange(0,1000); self._it_quiettime.setDecimals(2); self._it_quiettime.setValue(2.0)
        it_lay.addWidget(self._it_quiettime, 2, 1)
        self._ec_params_stack.addWidget(it_page)  # index 2
        
        # --- EIS 参数页 (index 3) ---
        eis_page = QWidget()
        eis_lay = QGridLayout(eis_page); eis_lay.setSpacing(8)
        eis_lay.addWidget(QLabel("偏置电位 E0(V):"), 0, 0)
        self._eis_e0 = QDoubleSpinBox(); self._eis_e0.setRange(-10,10); self._eis_e0.setDecimals(3)
        eis_lay.addWidget(self._eis_e0, 0, 1)
        eis_lay.addWidget(QLabel("高频率(Hz):"), 0, 2)
        self.ec_freqhigh_spin = QDoubleSpinBox(); self.ec_freqhigh_spin.setRange(0.0001,3000000); self.ec_freqhigh_spin.setDecimals(1); self.ec_freqhigh_spin.setValue(100000.0)
        eis_lay.addWidget(self.ec_freqhigh_spin, 0, 3)
        eis_lay.addWidget(QLabel("低频率(Hz):"), 1, 0)
        self.ec_freqlow_spin = QDoubleSpinBox(); self.ec_freqlow_spin.setRange(0.00001,100000); self.ec_freqlow_spin.setDecimals(4); self.ec_freqlow_spin.setValue(1.0)
        eis_lay.addWidget(self.ec_freqlow_spin, 1, 1)
        eis_lay.addWidget(QLabel("AC振幅(V):"), 1, 2)
        self.ec_amplitude_spin = QDoubleSpinBox(); self.ec_amplitude_spin.setRange(0.001,0.7); self.ec_amplitude_spin.setDecimals(4); self.ec_amplitude_spin.setValue(0.005)
        eis_lay.addWidget(self.ec_amplitude_spin, 1, 3)
        eis_lay.addWidget(QLabel("偏置模式:"), 2, 0)
        self.ec_bias_combo = QComboBox(); self.ec_bias_combo.addItem("vs Eref",0); self.ec_bias_combo.addItem("vs Eoc",1)
        eis_lay.addWidget(self.ec_bias_combo, 2, 1)
        eis_lay.addWidget(QLabel("灵敏度(A/V):"), 2, 2)
        self._eis_sensitivity = QLineEdit("1e-3")
        self._eis_sensitivity.setPlaceholderText("如 1e-3")
        eis_lay.addWidget(self._eis_sensitivity, 2, 3)
        eis_lay.addWidget(QLabel("静置时间(s):"), 3, 0)
        self._eis_quiettime = QDoubleSpinBox(); self._eis_quiettime.setRange(0,1000); self._eis_quiettime.setDecimals(2); self._eis_quiettime.setValue(2.0)
        eis_lay.addWidget(self._eis_quiettime, 3, 1)
        self._ec_params_stack.addWidget(eis_page)  # index 3
        
        # --- OCPT 参数页 (index 4) ---
        ocpt_page = QWidget()
        ocpt_lay = QGridLayout(ocpt_page); ocpt_lay.setSpacing(8)
        ocpt_lay.addWidget(QLabel("运行时间(s):"), 0, 0)
        self._ocpt_runtime = QDoubleSpinBox(); self._ocpt_runtime.setRange(0,100000); self._ocpt_runtime.setDecimals(2); self._ocpt_runtime.setValue(60.0)
        ocpt_lay.addWidget(self._ocpt_runtime, 0, 1)
        ocpt_lay.addWidget(QLabel("采样间隔(ms):"), 0, 2)
        self._ocpt_interval = QDoubleSpinBox(); self._ocpt_interval.setRange(0.1,10000); self._ocpt_interval.setDecimals(2); self._ocpt_interval.setValue(1000.0)
        ocpt_lay.addWidget(self._ocpt_interval, 0, 3)
        ocpt_lay.addWidget(QLabel("上限电位 Eh(V):"), 1, 0)
        self._ocpt_eh = QDoubleSpinBox(); self._ocpt_eh.setRange(-10,10); self._ocpt_eh.setDecimals(3); self._ocpt_eh.setValue(10.0)
        ocpt_lay.addWidget(self._ocpt_eh, 1, 1)
        ocpt_lay.addWidget(QLabel("下限电位 El(V):"), 1, 2)
        self._ocpt_el = QDoubleSpinBox(); self._ocpt_el.setRange(-10,10); self._ocpt_el.setDecimals(3); self._ocpt_el.setValue(-10.0)
        ocpt_lay.addWidget(self._ocpt_el, 1, 3)
        self._ec_params_stack.addWidget(ocpt_page)  # index 4
        
        tech_outer.addWidget(self._ec_params_stack)
        
        # Dummy Cell 模式选项
        dummy_row = QHBoxLayout()
        self.ec_dummy_cell = QCheckBox("使用 Dummy Cell (内置模拟电极，用于测试)")
        self.ec_dummy_cell.setChecked(True)
        self.ec_dummy_cell.setToolTip("勾选：使用 CHI 内置模拟电极进行测试\n取消勾选：连接真实电化学电极进行测量")
        dummy_row.addWidget(self.ec_dummy_cell)
        dummy_row.addStretch()
        tech_outer.addLayout(dummy_row)
        
        main_layout.addWidget(tech_group)
        
        # 隐藏的 OCPT 反向电流检测控件 (保留兼容性, 默认值)
        self.ec_ocpt_enable = QCheckBox(); self.ec_ocpt_enable.hide()
        self.ec_ocpt_threshold = QDoubleSpinBox(); self.ec_ocpt_threshold.setValue(-50.0); self.ec_ocpt_threshold.hide()
        self.ec_ocpt_duration = QDoubleSpinBox(); self.ec_ocpt_duration.setValue(5.0); self.ec_ocpt_duration.hide()
        self.ec_ocpt_action = QComboBox()
        self.ec_ocpt_action.addItem("仅记录", OCPTAction.LOG)
        self.ec_ocpt_action.addItem("暂停实验", OCPTAction.PAUSE)
        self.ec_ocpt_action.addItem("终止实验", OCPTAction.ABORT)
        self.ec_ocpt_action.hide()
        
        main_layout.addStretch()
        
        # 初始化: 选中 CV
        self._on_ec_tech_btn_clicked(ECTechnique.CV)
        
        return panel
    
    def _on_ec_tech_btn_clicked(self, tech: ECTechnique):
        """技术按钮点击 — 切换参数页 & 高亮"""
        self._ec_current_tech = tech
        
        # 更新按钮样式
        for t, btn in self._ec_tech_buttons.items():
            btn.setStyleSheet(self._ec_active_style if t == tech else self._ec_idle_style)
        
        # 切换 stacked widget
        idx_map = {ECTechnique.CV: 0, ECTechnique.LSV: 1, ECTechnique.I_T: 2, ECTechnique.EIS: 3, ECTechnique.OCPT: 4}
        self._ec_params_stack.setCurrentIndex(idx_map.get(tech, 0))
        
        # 同步 hidden combo (用于 save/load)
        combo_idx = {ECTechnique.CV: 0, ECTechnique.LSV: 1, ECTechnique.I_T: 2, ECTechnique.EIS: 3, ECTechnique.OCPT: 4}
        self.ec_tech_combo.setCurrentIndex(combo_idx.get(tech, 0))
    
    def _on_ec_tech_changed(self, index: int):
        """兼容: combo index 变化时同步按钮 (load 时调用)"""
        tech = self.ec_tech_combo.currentData()
        if tech:
            self._on_ec_tech_btn_clicked(tech)
    
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
        """排空参数面板 - 泵地址和方向只读显示"""
        panel = QGroupBox("排空参数")
        panel.setFont(FONT_TITLE)
        layout = QFormLayout(panel)
        
        # 泵地址（只读显示）
        self.ev_pump_label = QLineEdit()
        self.ev_pump_label.setReadOnly(True)
        self.ev_pump_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout.addRow("Outlet泵地址:", self.ev_pump_label)
        
        # 方向（只读显示）
        self.ev_dir_label = QLineEdit()
        self.ev_dir_label.setReadOnly(True)
        self.ev_dir_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        layout.addRow("方向:", self.ev_dir_label)
        
        self.ev_rpm_spin = QSpinBox()
        self.ev_rpm_spin.setRange(0, 1000)
        self.ev_rpm_spin.setValue(100)
        layout.addRow("转速(RPM):", self.ev_rpm_spin)
        
        self.ev_duration_spin = QDoubleSpinBox()
        self.ev_duration_spin.setRange(0, 10000)
        self.ev_duration_spin.setDecimals(2)
        self.ev_duration_spin.setValue(30.00)
        layout.addRow("单次时长(s):", self.ev_duration_spin)
        
        self.ev_cycles_spin = QSpinBox()
        self.ev_cycles_spin.setRange(1, 100)
        self.ev_cycles_spin.setValue(1)
        layout.addRow("循环次数:", self.ev_cycles_spin)
        
        return panel
    
    # === 事件处理 ===
    
    def _refresh_step_list(self):
        """刷新步骤列表 - 显示详细参数"""
        self.step_list.clear()
        for i, step in enumerate(self.experiment.steps):
            type_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
            detail = self._get_step_detail(step)
            if detail:
                item = QListWidgetItem(f"[{i+1}] {type_name}: {detail}")
            else:
                item = QListWidgetItem(f"[{i+1}] {type_name}")
            self.step_list.addItem(item)
    
    def _get_step_detail(self, step: ProgStep) -> str:
        """获取步骤的详细描述"""
        if step.step_type == ProgramStepType.TRANSFER:
            duration = step.transfer_duration or 0
            rpm = step.pump_rpm or 0
            return f"{duration:.1f}s, {rpm}RPM"
        
        elif step.step_type == ProgramStepType.PREP_SOL:
            if step.prep_sol_params:
                return step.prep_sol_params.get_summary()
            return ""
        
        elif step.step_type == ProgramStepType.FLUSH:
            duration = step.flush_cycle_duration_s or 0
            cycles = step.flush_cycles or 1
            return f"{duration:.1f}s×{cycles}"
        
        elif step.step_type == ProgramStepType.ECHEM:
            if step.ec_settings:
                ec = step.ec_settings
                t = ec.technique
                if isinstance(t, ECTechnique):
                    tech = t.value
                elif isinstance(t, str):
                    tech = t
                else:
                    tech = "?"
                tv = tech.upper()
                parts = [tv]
                if tv in ("CV", "LSV"):
                    parts.append(f"E0={ec.e0 or 0:.2f}V")
                    if ec.eh is not None:
                        parts.append(f"Eh={ec.eh:.2f}V")
                    if ec.el is not None:
                        parts.append(f"El={ec.el:.2f}V")
                    parts.append(f"扫速={ec.scan_rate or 0.05}V/s")
                    if tv == "CV" and ec.seg_num:
                        parts.append(f"段数={ec.seg_num}")
                elif tv in ("I-T", "IT"):
                    parts.append(f"E0={ec.e0 or 0:.2f}V")
                    parts.append(f"时间={ec.run_time_s or 60}s")
                elif tv == "OCPT":
                    parts.append(f"时间={ec.run_time_s or 60}s")
                elif tv == "EIS":
                    parts.append(f"频率={ec.freq_low}-{ec.freq_high}Hz")
                    parts.append(f"幅值={ec.amplitude}V")
                if ec.sensitivity is not None and not ec.autosensitivity:
                    parts.append(f"灵敏度={ec.sensitivity:g}")
                if getattr(ec, 'use_dummy_cell', False):
                    parts.append("Dummy")
                return ", ".join(parts)
            return ""
        
        elif step.step_type == ProgramStepType.BLANK:
            duration = step.duration_s or 0
            return f"{duration:.1f}s"
        
        elif step.step_type == ProgramStepType.EVACUATE:
            duration = step.transfer_duration or 0
            cycles = step.flush_cycles or 1
            return f"{duration:.1f}s×{cycles}"
        
        return ""
    
    def _on_step_selected(self, item: QListWidgetItem):
        """选中步骤 - 在右侧面板查看参数（只读展示，不可修改回步骤）"""
        index = self.step_list.row(item)
        if 0 <= index < len(self.experiment.steps):
            step = self.experiment.steps[index]
            # 临时设置 current_step 以便 _load_step_to_ui 正常工作
            self.current_step = step
            self.current_step_index = index
            self._load_step_to_ui()
            # 立即清除，防止 UI 修改被保存回步骤
            self.current_step = None
            self.current_step_index = -1
    
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
        
        # 设置类型按钮组
        type_index = {
            ProgramStepType.TRANSFER: 0,
            ProgramStepType.PREP_SOL: 1,
            ProgramStepType.FLUSH: 2,
            ProgramStepType.ECHEM: 3,
            ProgramStepType.BLANK: 4,
            ProgramStepType.EVACUATE: 5,
        }.get(step.step_type, 0)
        
        # 更新按钮选中状态
        self._select_type_button(step.step_type)
        self.params_stack.setCurrentIndex(type_index)
        
        # 加载参数
        if step.step_type == ProgramStepType.TRANSFER:
            self._load_transfer(step)
        elif step.step_type == ProgramStepType.PREP_SOL:
            self._load_prep_sol(step)
        elif step.step_type == ProgramStepType.FLUSH:
            self._load_flush(step)
        elif step.step_type == ProgramStepType.ECHEM:
            self._load_echem(step)
        elif step.step_type == ProgramStepType.BLANK:
            self._load_blank(step)
        elif step.step_type == ProgramStepType.EVACUATE:
            self._load_evacuate(step)
    
    def _load_transfer(self, step: ProgStep):
        # 从配置加载Transfer泵信息（只读）
        self._apply_pump_defaults_for_type(ProgramStepType.TRANSFER)
        # 加载可配置参数
        self.tf_rpm_spin.setValue(step.pump_rpm or 100)
        self.tf_duration_spin.setValue(step.transfer_duration or 10.0)
    
    def _load_prep_sol(self, step: ProgStep):
        """加载配液参数到UI"""
        # 先刷新表格基础结构
        self._refresh_recipe_table()
        
        if step.prep_sol_params:
            params = step.prep_sol_params
            # 体积从μL转换为mL
            vol_ml = params.total_volume_ul / 1000.0
            self.ps_vol_spin.setValue(round(vol_ml, 2))
            
            # 加载每行溶液的配置（按溶液名称匹配）
            for row in range(self.recipe_table.rowCount()):
                name_item = self.recipe_table.item(row, 1)
                if not name_item:
                    continue
                sol_name = name_item.text()
                
                # 加载选中状态
                check_widget = self.recipe_table.cellWidget(row, 0)
                if check_widget:
                    check = check_widget.findChild(QCheckBox)
                    if check:
                        selected = params.selected_solutions.get(sol_name, True)
                        check.setChecked(selected)
                
                # 加载目标浓度
                target_spin = self.recipe_table.cellWidget(row, 4)
                if target_spin and target_spin.isEnabled():
                    target_conc = params.target_concentrations.get(sol_name, 0.0)
                    target_spin.setValue(target_conc)
                
                # 加载溶剂标记 (H2O 行始终勾选且不可改)
                solvent_widget = self.recipe_table.cellWidget(row, 5)
                if solvent_widget:
                    solvent_check = solvent_widget.findChild(QCheckBox)
                    if solvent_check and solvent_check.isEnabled():
                        is_solvent = params.solvent_flags.get(sol_name, False)
                        solvent_check.setChecked(is_solvent)
                
                # 加载注液顺序 (优先用 injection_order_numbers)
                order_spin = self.recipe_table.cellWidget(row, 6)
                if order_spin:
                    if params.injection_order_numbers and sol_name in params.injection_order_numbers:
                        order_spin.setValue(params.injection_order_numbers[sol_name])
                    elif sol_name in params.injection_order:
                        order_idx = params.injection_order.index(sol_name) + 1
                        order_spin.setValue(order_idx)
                
                # 溶剂勾选后禁用目标浓度
                if target_spin and solvent_widget:
                    solvent_check_2 = solvent_widget.findChild(QCheckBox)
                    if solvent_check_2 and solvent_check_2.isChecked():
                        target_spin.setEnabled(False)
                        target_spin.setValue(0.0)
        else:
            # 没有配液参数时使用默认值
            self.ps_vol_spin.setValue(100.00)
    
    def _load_flush(self, step: ProgStep):
        # 从配置加载Inlet泵信息（只读）
        self._apply_pump_defaults_for_type(ProgramStepType.FLUSH)
        # 加载可配置参数
        self.fl_rpm_spin.setValue(step.flush_rpm or 100)
        self.fl_duration_spin.setValue(round(step.flush_cycle_duration_s or 30, 2))
        self.fl_cycles_spin.setValue(step.flush_cycles or 1)
    
    def _load_echem(self, step: ProgStep):
        if step.ec_settings:
            ec = step.ec_settings
            # 技术类型映射
            tech_idx = {
                ECTechnique.CV: 0, ECTechnique.LSV: 1,
                ECTechnique.I_T: 2, ECTechnique.EIS: 3, ECTechnique.OCPT: 4,
            }.get(ec.technique, 0)
            self.ec_tech_combo.setCurrentIndex(tech_idx)
            self._on_ec_tech_changed(tech_idx)
            
            tech = ec.technique
            
            if tech == ECTechnique.CV:
                self.ec_e0_spin.setValue(round(ec.e0 or 0, 3))
                self.ec_eh_spin.setValue(round(ec.eh or 0.8, 3))
                self.ec_el_spin.setValue(round(ec.el or -0.2, 3))
                self.ec_ef_spin.setValue(round(ec.ef or 0, 3))
                self.ec_scanrate_spin.setValue(ec.scan_rate or 0.05)
                self.ec_segments_spin.setValue(ec.seg_num)
                if ec.sensitivity is not None:
                    self.ec_sensitivity_edit.setText(str(ec.sensitivity))
                self.ec_interval_spin.setValue(ec.sample_interval_ms if ec.sample_interval_ms else 1.0)
                self.ec_quiettime_spin.setValue(round(ec.quiet_time_s, 2))
                
            elif tech == ECTechnique.LSV:
                self._lsv_e0.setValue(round(ec.e0 or 0, 3))
                self._lsv_ef.setValue(round(ec.ef or 1.0, 3))
                self._lsv_scanrate.setValue(ec.scan_rate or 0.05)
                if ec.sensitivity is not None:
                    self._lsv_sensitivity.setText(str(ec.sensitivity))
                self._lsv_interval.setValue(ec.sample_interval_ms if ec.sample_interval_ms else 1.0)
                self._lsv_quiettime.setValue(round(ec.quiet_time_s, 2))
                
            elif tech == ECTechnique.I_T:
                self._it_e0.setValue(round(ec.e0 or 0.2, 3))
                self.ec_runtime_spin.setValue(round(ec.run_time_s or 60, 2))
                self._it_interval.setValue(ec.sample_interval_ms if ec.sample_interval_ms else 100.0)
                if ec.sensitivity is not None:
                    self._it_sensitivity.setText(str(ec.sensitivity))
                self._it_quiettime.setValue(round(ec.quiet_time_s, 2))
                
            elif tech == ECTechnique.EIS:
                self._eis_e0.setValue(round(ec.e0 or 0, 3))
                self.ec_freqhigh_spin.setValue(ec.freq_high or 100000.0)
                self.ec_freqlow_spin.setValue(ec.freq_low or 1.0)
                self.ec_amplitude_spin.setValue(ec.amplitude or 0.005)
                bias_idx = {0: 0, 1: 1}.get(ec.bias_mode, 0)
                self.ec_bias_combo.setCurrentIndex(bias_idx)
                if ec.sensitivity is not None:
                    self._eis_sensitivity.setText(str(ec.sensitivity))
                self._eis_quiettime.setValue(round(ec.quiet_time_s, 2))
                
            elif tech == ECTechnique.OCPT:
                self._ocpt_runtime.setValue(round(ec.run_time_s or 60, 2))
                self._ocpt_interval.setValue(ec.sample_interval_ms if ec.sample_interval_ms else 1000.0)
                self._ocpt_eh.setValue(round(ec.eh or 10, 3))
                self._ocpt_el.setValue(round(ec.el or -10, 3))
            
            # Dummy Cell
            self.ec_dummy_cell.setChecked(getattr(ec, 'use_dummy_cell', True))
            # OCPT检测 (隐藏兼容)
            self.ec_ocpt_enable.setChecked(ec.ocpt_enabled)
            self.ec_ocpt_threshold.setValue(round(ec.ocpt_threshold_uA, 2))
            action_idx = {OCPTAction.LOG: 0, OCPTAction.PAUSE: 1, OCPTAction.ABORT: 2}.get(ec.ocpt_action, 0)
            self.ec_ocpt_action.setCurrentIndex(action_idx)
    
    def _load_blank(self, step: ProgStep):
        self.bl_duration_spin.setValue(round(step.duration_s or 0, 2))
        self.bl_notes_text.setPlainText(step.notes or "")
    
    def _load_evacuate(self, step: ProgStep):
        """加载排空参数"""
        # 从配置加载Outlet泵信息（只读）
        self._apply_pump_defaults_for_type(ProgramStepType.EVACUATE)
        # 加载可配置参数
        self.ev_rpm_spin.setValue(step.pump_rpm or 100)
        self.ev_duration_spin.setValue(step.transfer_duration or 30.0)
        self.ev_cycles_spin.setValue(step.flush_cycles or 1)
    
    def _save_current_step(self):
        """保存当前步骤"""
        if not self.current_step:
            return
        
        step = self.current_step
        step.step_type = self._get_selected_step_type()
        
        if step.step_type == ProgramStepType.TRANSFER:
            # 从配置获取Transfer泵地址和方向
            pump_info = self._get_pump_info_for_type("Transfer")
            step.pump_address = pump_info["address"]
            step.pump_direction = pump_info["direction"]
            step.pump_rpm = self.tf_rpm_spin.value()
            step.transfer_duration = round(self.tf_duration_spin.value(), 2)
            step.transfer_duration_unit = "s"
            
        elif step.step_type == ProgramStepType.PREP_SOL:
            if not step.prep_sol_params:
                step.prep_sol_params = PrepSolStep()
            params = step.prep_sol_params
            
            # 体积从mL转换为μL
            params.total_volume_ul = round(self.ps_vol_spin.value() * 1000, 2)
            
            # 保存每行溶液的完整数据
            selected_solutions = {}
            target_concentrations = {}
            solvent_flags = {}
            order_data = []
            
            for row in range(self.recipe_table.rowCount()):
                # 获取溶液名称
                name_item = self.recipe_table.item(row, 1)
                if not name_item:
                    continue
                sol_name = name_item.text()
                
                # 获取选中状态 (第0列)
                check_widget = self.recipe_table.cellWidget(row, 0)
                if check_widget:
                    check = check_widget.findChild(QCheckBox)
                    is_selected = check.isChecked() if check else False
                    selected_solutions[sol_name] = is_selected
                
                # 获取目标浓度 (第4列)
                target_spin = self.recipe_table.cellWidget(row, 4)
                if target_spin:
                    target_concentrations[sol_name] = target_spin.value()
                
                # 获取溶剂标记 (第5列)
                solvent_widget = self.recipe_table.cellWidget(row, 5)
                if solvent_widget:
                    solvent_check = solvent_widget.findChild(QCheckBox)
                    is_solvent = solvent_check.isChecked() if solvent_check else False
                    solvent_flags[sol_name] = is_solvent
                
                # 获取注液顺序 (第6列) - 只保存选中的溶液
                if selected_solutions.get(sol_name, False):
                    order_spin = self.recipe_table.cellWidget(row, 6)
                    order = order_spin.value() if order_spin else row + 1
                    order_data.append((order, sol_name))
            
            # 保存到 params
            params.selected_solutions = selected_solutions
            params.target_concentrations = target_concentrations
            params.solvent_flags = solvent_flags
            
            # 保存注液顺序编号 (允许相同编号 = 同时注液)
            order_numbers = {}
            for order_num, sol_name in order_data:
                order_numbers[sol_name] = order_num
            params.injection_order_numbers = order_numbers
            
            # 按注液顺序排序
            order_data.sort(key=lambda x: x[0])
            params.injection_order = [x[1] for x in order_data]
            
            # 兼容性：保留 is_solvent 字段 (有任何一个溶剂则为True)
            params.is_solvent = any(solvent_flags.values())
            
        elif step.step_type == ProgramStepType.FLUSH:
            # 从配置获取Inlet泵地址和方向
            pump_info = self._get_pump_info_for_type("Inlet")
            step.pump_address = pump_info["address"]
            step.pump_direction = pump_info["direction"]
            step.flush_rpm = self.fl_rpm_spin.value()
            step.flush_cycle_duration_s = round(self.fl_duration_spin.value(), 2)
            step.flush_cycles = self.fl_cycles_spin.value()
            
        elif step.step_type == ProgramStepType.ECHEM:
            if not step.ec_settings:
                step.ec_settings = ECSettings()
            ec = step.ec_settings
            tech = self.ec_tech_combo.currentData()
            ec.technique = tech
            ec.autosensitivity = False
            
            if tech == ECTechnique.CV:
                ec.e0 = round(self.ec_e0_spin.value(), 3)
                ec.eh = round(self.ec_eh_spin.value(), 3)
                ec.el = round(self.ec_el_spin.value(), 3)
                ec.ef = round(self.ec_ef_spin.value(), 3)
                ec.scan_rate = self.ec_scanrate_spin.value()
                ec.seg_num = self.ec_segments_spin.value()
                ec.quiet_time_s = round(self.ec_quiettime_spin.value(), 2)
                ec.sample_interval_ms = int(self.ec_interval_spin.value())
                try:
                    ec.sensitivity = float(self.ec_sensitivity_edit.text())
                except ValueError:
                    ec.sensitivity = 0.1
                    
            elif tech == ECTechnique.LSV:
                ec.e0 = round(self._lsv_e0.value(), 3)
                ec.ef = round(self._lsv_ef.value(), 3)
                ec.scan_rate = self._lsv_scanrate.value()
                ec.quiet_time_s = round(self._lsv_quiettime.value(), 2)
                ec.sample_interval_ms = int(self._lsv_interval.value())
                try:
                    ec.sensitivity = float(self._lsv_sensitivity.text())
                except ValueError:
                    ec.sensitivity = 0.1
                    
            elif tech == ECTechnique.I_T:
                ec.e0 = round(self._it_e0.value(), 3)
                ec.run_time_s = round(self.ec_runtime_spin.value(), 2)
                ec.sample_interval_ms = int(self._it_interval.value())
                ec.quiet_time_s = round(self._it_quiettime.value(), 2)
                try:
                    ec.sensitivity = float(self._it_sensitivity.text())
                except ValueError:
                    ec.sensitivity = 1e-4
                    
            elif tech == ECTechnique.EIS:
                ec.e0 = round(self._eis_e0.value(), 3)
                ec.freq_high = self.ec_freqhigh_spin.value()
                ec.freq_low = self.ec_freqlow_spin.value()
                ec.amplitude = self.ec_amplitude_spin.value()
                ec.bias_mode = self.ec_bias_combo.currentData() or 0
                ec.quiet_time_s = round(self._eis_quiettime.value(), 2)
                try:
                    ec.sensitivity = float(self._eis_sensitivity.text())
                except ValueError:
                    ec.sensitivity = 1e-3
                    
            elif tech == ECTechnique.OCPT:
                ec.run_time_s = round(self._ocpt_runtime.value(), 2)
                ec.sample_interval_ms = int(self._ocpt_interval.value())
                ec.eh = round(self._ocpt_eh.value(), 3)
                ec.el = round(self._ocpt_el.value(), 3)
            
            # OCPT 检测 (兼容)
            ec.ocpt_enabled = self.ec_ocpt_enable.isChecked()
            ec.ocpt_threshold_uA = round(self.ec_ocpt_threshold.value(), 2)
            ec.ocpt_action = self.ec_ocpt_action.currentData()
            # Dummy Cell
            ec.use_dummy_cell = self.ec_dummy_cell.isChecked()
            
        elif step.step_type == ProgramStepType.BLANK:
            step.duration_s = round(self.bl_duration_spin.value(), 2)
            step.notes = self.bl_notes_text.toPlainText()
        
        elif step.step_type == ProgramStepType.EVACUATE:
            # 从配置获取Outlet泵地址和方向
            pump_info = self._get_pump_info_for_type("Outlet")
            step.pump_address = pump_info["address"]
            step.pump_direction = pump_info["direction"]
            step.pump_rpm = self.ev_rpm_spin.value()
            step.transfer_duration = round(self.ev_duration_spin.value(), 2)
            step.transfer_duration_unit = "s"
            step.flush_cycles = self.ev_cycles_spin.value()
    
    def _on_type_button_clicked(self, button: QPushButton):
        """操作类型按钮点击处理 - 仅切换参数面板"""
        # 更新所有按钮样式
        for btn in self.type_buttons.values():
            if btn == button:
                btn.setStyleSheet(btn.property("style_checked"))
            else:
                btn.setChecked(False)
                btn.setStyleSheet(btn.property("style_normal"))
        
        # 获取按钮对应的面板索引和步骤类型
        panel_index = button.property("panel_index")
        step_type = button.property("step_type")
        
        # 切换参数面板
        self.params_stack.setCurrentIndex(panel_index)
        
        # 根据操作类型自动设置对应的泵地址和方向
        self._apply_pump_defaults_for_type(step_type)
        
        # 清除步骤列表选中状态（表示当前在配置新步骤）
        self.step_list.clearSelection()
        
        # 如果切换到配液，刷新溶液配方
        if panel_index == 1:
            self._refresh_recipe_table()
    
    def _apply_pump_defaults_for_type(self, step_type: ProgramStepType):
        """根据操作类型自动设置对应的泵地址和方向
        
        - 移液(TRANSFER): 使用 work_type="Transfer" 的泵
        - 冲洗(FLUSH): 使用 work_type="Inlet" 的泵
        - 排空(EVACUATE): 使用 work_type="Outlet" 的泵
        """
        # 从配置中查找对应工作类型的泵
        work_type_map = {
            ProgramStepType.TRANSFER: "Transfer",
            ProgramStepType.FLUSH: "Inlet",
            ProgramStepType.EVACUATE: "Outlet",
        }
        
        target_work_type = work_type_map.get(step_type)
        if not target_work_type:
            return
        
        # 在 flush_channels 中查找对应工作类型的泵
        pump_address = None
        pump_direction = "FWD"
        pump_rpm = 100
        
        for ch in self.config.flush_channels:
            if ch.work_type == target_work_type:
                pump_address = ch.pump_address
                pump_direction = ch.direction
                pump_rpm = ch.rpm
                break
        
        if pump_address is None:
            return
        
        direction_text = "正向" if pump_direction == "FWD" else "反向"
        
        # 设置对应面板的泵地址和方向（只读标签）
        if step_type == ProgramStepType.TRANSFER:
            # 设置移液面板
            self.tf_pump_label.setText(str(pump_address))
            self.tf_dir_label.setText(direction_text)
            self.tf_rpm_spin.setValue(pump_rpm)
        elif step_type == ProgramStepType.FLUSH:
            # 设置冲洗面板
            self.fl_pump_label.setText(str(pump_address))
            self.fl_dir_label.setText(direction_text)
            self.fl_rpm_spin.setValue(pump_rpm)
        elif step_type == ProgramStepType.EVACUATE:
            # 设置排空面板
            self.ev_pump_label.setText(str(pump_address))
            self.ev_dir_label.setText(direction_text)
            self.ev_rpm_spin.setValue(pump_rpm)
    
    def _get_pump_info_for_type(self, work_type: str) -> dict:
        """获取指定工作类型的泵信息
        
        Args:
            work_type: 工作类型 (Transfer/Inlet/Outlet)
            
        Returns:
            dict: {"address": int, "direction": str, "rpm": int}
        """
        for ch in self.config.flush_channels:
            if ch.work_type == work_type:
                return {
                    "address": ch.pump_address,
                    "direction": ch.direction,
                    "rpm": ch.rpm
                }
        # 默认值
        return {"address": 1, "direction": "FWD", "rpm": 100}
    
    def _select_type_button(self, step_type: ProgramStepType):
        """选中指定类型的按钮"""
        for stype, btn in self.type_buttons.items():
            if stype == step_type:
                btn.setChecked(True)
                btn.setStyleSheet(btn.property("style_checked"))
            else:
                btn.setChecked(False)
                btn.setStyleSheet(btn.property("style_normal"))
    
    def _get_selected_step_type(self) -> ProgramStepType:
        """获取当前选中的步骤类型"""
        for step_type, btn in self.type_buttons.items():
            if btn.isChecked():
                return step_type
        return ProgramStepType.TRANSFER  # 默认
    
    def _on_add_step(self):
        """添加步骤 - 从右侧面板当前配置创建新步骤
        
        工作流程：用户先在右侧配置参数，然后点击"添加"将步骤
        加入列表。步骤一旦添加到列表即为最终状态，不可修改。
        """
        # 获取当前选中的类型
        selected_type = self._get_selected_step_type()
        
        new_step = ProgStep(
            step_id=f"step_{len(self.experiment.steps) + 1}",
            step_type=selected_type
        )
        
        # 根据步骤类型预设泵地址和方向
        if selected_type == ProgramStepType.TRANSFER:
            pump_info = self._get_pump_info_for_type("Transfer")
            new_step.pump_address = pump_info["address"]
            new_step.pump_direction = pump_info["direction"]
            new_step.pump_rpm = pump_info["rpm"]
            new_step.transfer_duration = 10.0
        elif selected_type == ProgramStepType.FLUSH:
            pump_info = self._get_pump_info_for_type("Inlet")
            new_step.pump_address = pump_info["address"]
            new_step.pump_direction = pump_info["direction"]
            new_step.flush_rpm = pump_info["rpm"]
            new_step.flush_cycle_duration_s = 30.0
            new_step.flush_cycles = 1
        elif selected_type == ProgramStepType.EVACUATE:
            pump_info = self._get_pump_info_for_type("Outlet")
            new_step.pump_address = pump_info["address"]
            new_step.pump_direction = pump_info["direction"]
            new_step.pump_rpm = pump_info["rpm"]
            new_step.transfer_duration = 30.0
            new_step.flush_cycles = 1
        elif selected_type == ProgramStepType.ECHEM:
            new_step.ec_settings = ECSettings()
        elif selected_type == ProgramStepType.BLANK:
            new_step.duration_s = 5.0
        
        # 临时设置 current_step，然后从 UI 读取参数填充到 new_step
        self.current_step = new_step
        self._save_current_step()
        
        # 添加到步骤列表
        self.experiment.steps.append(new_step)
        self._refresh_step_list()
        
        # 清除 current_step（步骤已最终确定）
        self.current_step = None
        self.current_step_index = -1
        self.step_list.clearSelection()
    
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
        """保存程序 - 所有步骤在添加时已最终确定"""
        # 收集所有验证错误
        errors = []
        warnings = []
        
        if not self.experiment.steps:
            QMessageBox.warning(self, "警告", "实验没有任何步骤，无法保存")
            return
        
        # 获取配液通道信息
        dilution_channels = {}
        if hasattr(self, 'config') and self.config:
            for ch in self.config.dilution_channels:
                dilution_channels[ch.solution_name] = ch
        
        for i, step in enumerate(self.experiment.steps):
            step_num = i + 1
            step_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
            
            # 泵操作步骤检查
            if step.step_type in [ProgramStepType.TRANSFER, ProgramStepType.FLUSH, ProgramStepType.EVACUATE]:
                if not step.pump_address:
                    errors.append(f"步骤 {step_num} [{step_name}]: 缺少泵地址")
                elif step.pump_address < 1 or step.pump_address > 12:
                    errors.append(f"步骤 {step_num} [{step_name}]: 泵地址 {step.pump_address} 超出有效范围 (1-12)")
                
                if step.step_type == ProgramStepType.TRANSFER:
                    if not step.transfer_duration or step.transfer_duration <= 0:
                        errors.append(f"步骤 {step_num} [移液]: 持续时间必须大于 0")
                elif step.step_type == ProgramStepType.FLUSH:
                    if not step.flush_cycle_duration_s or step.flush_cycle_duration_s <= 0:
                        errors.append(f"步骤 {step_num} [冲洗]: 冲洗时长必须大于 0")
                    if not step.flush_cycles or step.flush_cycles <= 0:
                        errors.append(f"步骤 {step_num} [冲洗]: 循环次数必须大于 0")
            
            # 配液步骤检查
            elif step.step_type == ProgramStepType.PREP_SOL:
                if not step.prep_sol_params:
                    errors.append(f"步骤 {step_num} [配液]: 缺少配液参数")
                else:
                    params = step.prep_sol_params
                    if params.total_volume_ul <= 0:
                        errors.append(f"步骤 {step_num} [配液]: 总体积必须大于 0")
                    
                    has_selected = False
                    total_solute_vol = 0
                    
                    for sol_name in params.injection_order:
                        if not params.selected_solutions.get(sol_name, False):
                            continue
                        has_selected = True
                        is_solvent = params.solvent_flags.get(sol_name, False)
                        
                        if not is_solvent:
                            target_conc = params.target_concentrations.get(sol_name, 0)
                            ch = dilution_channels.get(sol_name)
                            stock_conc = ch.stock_concentration if ch else 0
                            
                            if target_conc > 0 and stock_conc > 0:
                                if target_conc > stock_conc:
                                    errors.append(
                                        f"步骤 {step_num} [配液]: {sol_name} 目标浓度 "
                                        f"({target_conc}M) 超过母液浓度 ({stock_conc}M)"
                                    )
                                else:
                                    vol = (target_conc * params.total_volume_ul) / stock_conc
                                    total_solute_vol += vol
                    
                    if not has_selected:
                        errors.append(f"步骤 {step_num} [配液]: 没有选择任何溶液")
                    elif total_solute_vol > params.total_volume_ul:
                        errors.append(
                            f"步骤 {step_num} [配液]: 溶质总体积 ({total_solute_vol:,.0f}μL) "
                            f"超过总体积 ({params.total_volume_ul:,.0f}μL)"
                        )
            
            # 电化学步骤检查
            elif step.step_type == ProgramStepType.ECHEM:
                if not step.ec_settings:
                    errors.append(f"步骤 {step_num} [电化学]: 缺少电化学参数")
        
        # 有错误时显示汇总并阻止保存
        if errors:
            error_text = "\n".join(f"• {e}" for e in errors)
            QMessageBox.critical(
                self, "验证失败",
                f"发现 {len(errors)} 个问题，请修正后再保存：\n\n{error_text}"
            )
            return
        
        self.program_saved.emit(self.experiment)
        QMessageBox.information(self, "成功", "程序已保存")
        self.accept()

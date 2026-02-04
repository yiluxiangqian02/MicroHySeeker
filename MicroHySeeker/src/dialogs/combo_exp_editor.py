"""
组合实验编辑器 - 参照 C# ComboExpEditor 和 BACKEND_API_INTERFACES.md
- 单一表格显示所有步骤的所有变量（变量写全）
- 步骤列合并同一步骤只显示一次
- 字体放大便于阅读
- 计算按钮独立
- 所有 SpinBox 步长 0.01
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QWidget,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QSplitter, QTextEdit, QSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from typing import List, Optional

from src.models import (
    Experiment, ProgStep, ProgramStepType, ECTechnique, SystemConfig
)


# 字体设置 - 放大
FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TABLE = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)
FONT_STEP = QFont("Microsoft YaHei", 11)

# 步骤类型中文映射
STEP_TYPE_NAMES = {
    ProgramStepType.TRANSFER: "移液",
    ProgramStepType.PREP_SOL: "配液",
    ProgramStepType.FLUSH: "冲洗",
    ProgramStepType.EChem: "电化学",
    ProgramStepType.BLANK: "空白",
    ProgramStepType.EVACUATE: "排空",
}


class ComboExpEditorDialog(QDialog):
    """
    组合实验编辑器
    
    设计特点：
    - 左侧：步骤列表（放大字体）
    - 右侧：参数表格，同一步骤合并显示，变量写全
    - 底部：计算按钮独立，组合预览
    
    === 后端接口 ===
    combo_saved 信号发射组合参数列表
    """
    combo_saved = Signal(list)
    
    def __init__(self, experiment: Experiment, config: SystemConfig = None, parent=None):
        super().__init__(parent)
        self.experiment = experiment
        self.config = config
        self.param_rows = []  # 存储参数行引用
        
        self.setWindowTitle("组合实验编辑")
        self.setGeometry(80, 40, 1050, 700)
        self.setFont(FONT_NORMAL)
        self._init_ui()
        self._load_all_params()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 标题区
        title_layout = QHBoxLayout()
        title_label = QLabel("组合实验参数编辑")
        title_label.setFont(FONT_TITLE)
        title_layout.addWidget(title_label)
        
        info_label = QLabel("修改终值和间隔，点击计算查看组合数")
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        title_layout.addWidget(info_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # 使用分割器：左侧步骤列表 + 右侧参数表格
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：步骤列表
        left_group = QGroupBox("步骤列表")
        left_group.setFont(FONT_TITLE)
        left_layout = QVBoxLayout(left_group)
        left_layout.setContentsMargins(6, 6, 6, 6)
        
        self.step_list = QTextEdit()
        self.step_list.setReadOnly(True)
        self.step_list.setFont(FONT_STEP)
        self.step_list.setMinimumWidth(200)
        self.step_list.setMaximumWidth(280)
        self.step_list.setStyleSheet("font-size: 11pt; line-height: 1.3;")
        left_layout.addWidget(self.step_list)
        splitter.addWidget(left_group)
        
        # 右侧：参数表格
        right_group = QGroupBox("参数设置")
        right_group.setFont(FONT_TITLE)
        right_layout = QVBoxLayout(right_group)
        right_layout.setContentsMargins(6, 6, 6, 6)
        
        # 表格：步骤、变量、初值、终值、间隔
        self.param_table = QTableWidget()
        self.param_table.setFont(FONT_TABLE)
        self.param_table.setColumnCount(5)
        self.param_table.setHorizontalHeaderLabels(["步骤", "变量", "初值", "终值", "间隔"])
        self.param_table.horizontalHeader().setFont(FONT_TABLE)
        self.param_table.verticalHeader().setVisible(False)
        self.param_table.verticalHeader().setDefaultSectionSize(28)
        self.param_table.setStyleSheet("""
            QTableWidget { font-size: 10pt; }
            QTableWidget::item { padding: 2px; }
            QHeaderView::section { font-size: 10pt; padding: 4px; font-weight: bold; }
            QDoubleSpinBox { font-size: 10pt; }
        """)
        
        # 列宽设置
        header = self.param_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.param_table.setColumnWidth(0, 90)
        self.param_table.setColumnWidth(2, 80)
        self.param_table.setColumnWidth(3, 80)
        self.param_table.setColumnWidth(4, 80)
        
        right_layout.addWidget(self.param_table)
        splitter.addWidget(right_group)
        
        # 设置分割器比例
        splitter.setSizes([220, 700])
        layout.addWidget(splitter, 1)
        
        # 底部：计算按钮 + 预览 + 保存按钮
        bottom_layout = QHBoxLayout()
        
        # 计算按钮 - 独立显眼
        calc_btn = QPushButton("计算组合数")
        calc_btn.setFont(FONT_TITLE)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800; 
                color: white; 
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        calc_btn.clicked.connect(self._calculate_combos)
        bottom_layout.addWidget(calc_btn)
        
        # 组合预览
        self.preview_label = QLabel("组合数: 0")
        self.preview_label.setFont(FONT_TITLE)
        self.preview_label.setStyleSheet("color: #1976D2; padding: 0 20px;")
        bottom_layout.addWidget(self.preview_label)
        
        bottom_layout.addStretch()
        
        # 保存按钮
        save_btn = QPushButton("保存组合实验")
        save_btn.setFont(FONT_NORMAL)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white; 
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFont(FONT_NORMAL)
        cancel_btn.setStyleSheet("padding: 8px 20px;")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)
        
        layout.addLayout(bottom_layout)
    
    def _load_all_params(self):
        """加载所有步骤的所有参数到单一表格，同一步骤合并显示"""
        # 填充步骤列表
        step_text = ""
        all_params = []
        
        for i, step in enumerate(self.experiment.steps):
            type_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
            desc = self._get_step_short_desc(step)
            step_text += f"{i+1:02d}. [{type_name}] {desc}\n"
            
            # 获取该步骤的所有参数（完整版）
            params = self._get_step_params_full(step)
            first_param = True
            for param in params:
                all_params.append({
                    'step_index': i,
                    'step_type': type_name,
                    'param_info': param,
                    'show_step': first_param  # 只有第一个参数显示步骤
                })
                first_param = False
        
        self.step_list.setText(step_text)
        
        # 填充参数表格
        self.param_table.setRowCount(len(all_params))
        
        # 用于合并同一步骤的单元格
        current_step_idx = -1
        step_start_row = 0
        
        for row, param_data in enumerate(all_params):
            step_idx = param_data['step_index']
            step_type = param_data['step_type']
            param_info = param_data['param_info']
            show_step = param_data['show_step']
            
            # 解析参数信息
            if len(param_info) == 3:
                # 配液: (溶液类型, 参数名, 初始值)
                sol_type, param_name, init_val = param_info
                display_name = f"{sol_type}/{param_name}"
            else:
                # 其他: (参数名, 初始值)
                param_name, init_val = param_info
                display_name = param_name
                sol_type = None
            
            # 步骤列 - 只在第一个参数时显示，其他留空
            if show_step:
                step_item = QTableWidgetItem(f"{step_idx+1:02d}:{step_type}")
                step_item.setFlags(step_item.flags() & ~Qt.ItemIsEditable)
                step_item.setBackground(QColor("#e3f2fd"))
                step_item.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
                self.param_table.setItem(row, 0, step_item)
            else:
                empty_item = QTableWidgetItem("")
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
                empty_item.setBackground(QColor("#f5f5f5"))
                self.param_table.setItem(row, 0, empty_item)
            
            # 变量名 (只读)
            name_item = QTableWidgetItem(display_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.param_table.setItem(row, 1, name_item)
            
            # 初值 (只读)
            init_item = QTableWidgetItem(f"{init_val:.2f}")
            init_item.setFlags(init_item.flags() & ~Qt.ItemIsEditable)
            init_item.setTextAlignment(Qt.AlignCenter)
            self.param_table.setItem(row, 2, init_item)
            
            # 终值 (可编辑) - 步长0.01
            end_spin = QDoubleSpinBox()
            end_spin.setRange(-10000, 10000)
            end_spin.setDecimals(2)
            end_spin.setSingleStep(0.01)  # 步长0.01
            end_spin.setValue(init_val)
            end_spin.setFont(FONT_TABLE)
            self.param_table.setCellWidget(row, 3, end_spin)
            
            # 间隔 (可编辑) - 步长0.01
            interval_spin = QDoubleSpinBox()
            interval_spin.setRange(0, 10000)
            interval_spin.setDecimals(2)
            interval_spin.setSingleStep(0.01)  # 步长0.01
            interval_spin.setValue(0)
            interval_spin.setFont(FONT_TABLE)
            self.param_table.setCellWidget(row, 4, interval_spin)
            
            # 保存引用
            self.param_rows.append({
                'step_index': step_idx,
                'param_name': param_name,
                'solution_type': sol_type,
                'init_val': init_val,
                'end_spin': end_spin,
                'interval_spin': interval_spin
            })
    
    def _get_step_short_desc(self, step: ProgStep) -> str:
        """获取步骤短描述"""
        if step.step_type == ProgramStepType.PREP_SOL:
            if step.prep_sol_params:
                vol_ml = (step.prep_sol_params.total_volume_ul or 5000) / 1000
                return f"{vol_ml:.1f}mL"
            return "配液"
        
        elif step.step_type == ProgramStepType.EChem:
            if step.ec_settings:
                tech = step.ec_settings.technique
                if tech == ECTechnique.CV:
                    return "CV"
                elif tech == ECTechnique.LSV:
                    return "LSV"
                elif tech == ECTechnique.I_T:
                    return "i-t"
            return "电化学"
        
        elif step.step_type == ProgramStepType.TRANSFER:
            pump = step.pump_address or 1
            return f"泵{pump}"
        
        elif step.step_type == ProgramStepType.FLUSH:
            pump = step.pump_address or 1
            return f"泵{pump}"
        
        elif step.step_type == ProgramStepType.EVACUATE:
            pump = step.pump_address or 1
            return f"泵{pump}"
        
        elif step.step_type == ProgramStepType.BLANK:
            dur = step.duration_s or 0
            return f"{dur:.0f}s"
        
        return ""
    
    def _get_step_params_full(self, step: ProgStep) -> List[tuple]:
        """获取步骤的完整可变参数列表（参照 BACKEND_API_INTERFACES.md）
        
        配液返回: (溶液类型, 参数名, 值)
        其他返回: (参数名, 值)
        """
        params = []
        
        if step.step_type == ProgramStepType.BLANK:
            # BLANK: duration_s, notes
            params.append(("持续时间(s)", step.duration_s or 0))
            
        elif step.step_type == ProgramStepType.FLUSH:
            # FLUSH: pump_address, pump_direction, flush_rpm, flush_cycle_duration_s, flush_cycles
            # 注：冲洗模块含"仅排空"选项，由 evacuate_only 标志控制
            params.append(("转速(RPM)", step.flush_rpm or 100))
            params.append(("循环时长(s)", step.flush_cycle_duration_s or 30))
            params.append(("循环次数", step.flush_cycles or 1))
            
        elif step.step_type == ProgramStepType.PREP_SOL:
            # PREP_SOL: total_volume_ul, target_concentration, injection_order
            if self.config and self.config.dilution_channels:
                for ch in self.config.dilution_channels:
                    params.append((ch.solution_name, "浓度(mol/L)", 0.01))
            # 总体积
            if step.prep_sol_params:
                vol_ml = (step.prep_sol_params.total_volume_ul or 5000) / 1000.0
                conc = step.prep_sol_params.target_concentration or 0.01
            else:
                vol_ml = 5.00
                conc = 0.01
            params.append(("配液", "目标浓度(mol/L)", conc))
            params.append(("配液", "总体积(mL)", vol_ml))
            
        elif step.step_type == ProgramStepType.TRANSFER:
            # TRANSFER: pump_address, pump_direction, pump_rpm, transfer_duration, transfer_duration_unit
            params.append(("转速(RPM)", step.pump_rpm or 100))
            params.append(("持续时间(s)", step.transfer_duration or 10))
            
        elif step.step_type == ProgramStepType.EChem:
            # 电化学根据技术类型显示不同参数（完整版）
            if step.ec_settings:
                ec = step.ec_settings
                params.append(("静置时间(s)", ec.quiet_time_s or 2))
                params.append(("E0 初始电位(V)", ec.e0 or 0))
                
                if ec.technique == ECTechnique.CV:
                    # CV: 静置时间、起始电位、上限电位、下限电位、终止电位、扫速
                    params.append(("EH 上限电位(V)", ec.eh or 0.8))
                    params.append(("EL 下限电位(V)", ec.el or -0.2))
                    params.append(("EF 终止电位(V)", ec.ef or 0))
                    params.append(("扫描速率(V/s)", ec.scan_rate or 0.05))
                    
                elif ec.technique == ECTechnique.LSV:
                    # LSV: 静置时间、起始电位、终止电位、扫速
                    params.append(("EF 终止电位(V)", ec.ef or 0.8))
                    params.append(("扫描速率(V/s)", ec.scan_rate or 0.05))
                    
                elif ec.technique == ECTechnique.I_T:
                    # i-t: 静置时间、起始电位、运行时间
                    params.append(("运行时间(s)", ec.run_time_s or 60))
                
                # OCPT 检测参数（如果启用）
                if ec.ocpt_enabled:
                    params.append(("OCPT阈值电流(μA)", ec.ocpt_threshold_uA or 10))
                    params.append(("OCPT持续时间(s)", ec.ocpt_duration_s or 5))
            else:
                params.append(("静置时间(s)", 2.0))
                params.append(("E0 初始电位(V)", 0))
        
        return params
    
    def _calculate_combos(self):
        """计算组合数"""
        total = 1
        changed_params = []
        
        for param_data in self.param_rows:
            init_val = param_data['init_val']
            end_val = param_data['end_spin'].value()
            interval = param_data['interval_spin'].value()
            
            if interval > 0.001 and abs(end_val - init_val) > 0.001:
                count = int(abs(end_val - init_val) / interval) + 1
                total *= count
                changed_params.append(count)
        
        if changed_params:
            detail = " × ".join([str(c) for c in changed_params])
            self.preview_label.setText(f"组合数: {total}  ({detail})")
        else:
            self.preview_label.setText("组合数: 1 (无变化)")
    
    def _generate_combo_params(self) -> List[dict]:
        """生成组合参数列表"""
        combo_list = [{}]
        
        for param_data in self.param_rows:
            step_idx = param_data['step_index']
            param_name = param_data['param_name']
            sol_type = param_data.get('solution_type')
            init_val = param_data['init_val']
            end_val = param_data['end_spin'].value()
            interval = param_data['interval_spin'].value()
            
            if sol_type:
                key = f"step_{step_idx}_{sol_type}_{param_name}"
            else:
                key = f"step_{step_idx}_{param_name}"
            
            if interval > 0.001 and abs(end_val - init_val) > 0.001:
                # 生成该参数的所有值
                values = []
                val = init_val
                step = interval if end_val > init_val else -interval
                
                while (step > 0 and val <= end_val + 0.001) or (step < 0 and val >= end_val - 0.001):
                    values.append(round(val, 2))
                    val += step
                
                # 扩展组合列表
                new_combo_list = []
                for combo in combo_list:
                    for v in values:
                        new_combo = combo.copy()
                        new_combo[key] = v
                        new_combo_list.append(new_combo)
                combo_list = new_combo_list
            else:
                # 固定值
                for combo in combo_list:
                    combo[key] = round(init_val, 2)
        
        return combo_list
    
    def _on_save(self):
        """保存组合实验"""
        combo_params = self._generate_combo_params()
        if not combo_params:
            QMessageBox.warning(self, "警告", "没有生成任何组合")
            return
        
        self.combo_saved.emit(combo_params)
        QMessageBox.information(self, "成功", f"已生成 {len(combo_params)} 个组合实验")
        self.accept()

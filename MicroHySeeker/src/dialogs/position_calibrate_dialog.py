"""
位置模式校准对话框 - SR_VFOC泵位置模式校准

使用多点线性回归：10, 20, 30, 40, 50, 60, 70, 80, 90, 100 圈
对12个泵进行测试，通过线性回归得到：
- 斜率 k (μL/圈)
- 截距 b (μL)
- 公式: Volume = k * revolutions + b
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QSpinBox, QMessageBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QWidget, QRadioButton, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QBrush
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from src.models import SystemConfig
from src.services.rs485_wrapper import get_rs485_instance


# 字体设置
FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)
FONT_SMALL = QFont("Microsoft YaHei", 9)

# 编码器常量
ENCODER_DIVISIONS_PER_REV = 16384

# 测试圈数序列
TEST_REVOLUTIONS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


@dataclass
class PumpCalibrationData:
    """单个泵的校准数据"""
    pump_address: int
    pump_name: str
    
    # 10个测试点的体积数据 (μL)
    test_volumes: List[float] = field(default_factory=lambda: [0.0] * len(TEST_REVOLUTIONS))
    
    # 线性回归结果: Volume = k * revolutions + b
    slope_k: float = 0.0           # 斜率 k (μL/圈)
    intercept_b: float = 0.0       # 截距 b (μL)
    r_squared: float = 0.0         # R² 拟合度
    
    # 转换为编码器单位的系数
    ul_per_encoder_count: float = 0.0  # μL/count (= k / ENCODER_DIVISIONS_PER_REV)
    
    is_selected: bool = False      # 是否被选中进行校准
    is_calibrated: bool = False    # 是否已完成校准


class PositionCalibrateDialog(QDialog):
    """SR_VFOC位置模式校准对话框
    
    使用多点线性回归校准：
    - 10个固定测试点: 10, 20, 30, ... 100 圈
    - 12个泵同时显示
    - 通过回归得到 Volume = k * revolutions + b
    """
    
    calibration_saved = Signal(int, float)  # pump_address, ul_per_encoder_count
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.rs485 = get_rs485_instance()
        
        # 12个泵的校准数据
        self.pump_data: Dict[int, PumpCalibrationData] = {}
        self._init_pump_data()
        
        # 当前选中的泵
        self.selected_pump: Optional[int] = None
        
        # 测试状态
        self.is_testing = False
        self.current_test_rev_index = -1  # 当前测试的圈数索引
        
        self.setWindowTitle("泵校准 - 多点线性回归 (SR_VFOC位置模式)")
        self.setMinimumSize(1200, 750)
        self.setFont(FONT_NORMAL)
        self._init_ui()
        self._refresh_table()
    
    def _init_pump_data(self):
        """初始化12个泵的校准数据"""
        for i in range(1, 13):
            # 查找泵名称 - 未配置的泵显示"未配置"
            pump_name = "未配置"
            for ch in self.config.dilution_channels:
                if ch.pump_address == i:
                    pump_name = ch.solution_name
                    break
            
            self.pump_data[i] = PumpCalibrationData(
                pump_address=i,
                pump_name=pump_name
            )
            
            # 加载已有的校准数据
            if i in self.config.calibration_data:
                cal = self.config.calibration_data[i]
                if 'slope_k' in cal:
                    self.pump_data[i].slope_k = cal['slope_k']
                    self.pump_data[i].intercept_b = cal.get('intercept_b', 0.0)
                    self.pump_data[i].r_squared = cal.get('r_squared', 0.0)
                    self.pump_data[i].ul_per_encoder_count = cal.get('ul_per_encoder_count', 0.0)
                    self.pump_data[i].is_calibrated = True
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 顶部：参数设置
        top_group = QGroupBox("测试参数")
        top_group.setFont(FONT_TITLE)
        top_layout = QHBoxLayout(top_group)
        
        # 测试速度
        speed_label = QLabel("测试速度:")
        speed_label.setFont(FONT_NORMAL)
        top_layout.addWidget(speed_label)
        
        self.speed_spin = QSpinBox()
        self.speed_spin.setFont(FONT_NORMAL)
        self.speed_spin.setRange(50, 500)
        self.speed_spin.setValue(100)
        self.speed_spin.setSuffix(" RPM")
        top_layout.addWidget(self.speed_spin)
        
        top_layout.addSpacing(20)
        
        # 测试圈数提示
        rev_hint = QLabel(f"测试点: {', '.join(str(r) for r in TEST_REVOLUTIONS)} 圈")
        rev_hint.setFont(FONT_NORMAL)
        rev_hint.setStyleSheet("color: #666;")
        top_layout.addWidget(rev_hint)
        
        top_layout.addStretch()
        
        # 公式说明
        formula_label = QLabel("校准公式: Volume(μL) = k × 圈数 + b")
        formula_label.setFont(FONT_NORMAL)
        formula_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        top_layout.addWidget(formula_label)
        
        layout.addWidget(top_group)
        
        # 中部：泵校准表格
        table_group = QGroupBox("泵校准数据 (点击选择按钮选择要校准的泵)")
        table_group.setFont(FONT_TITLE)
        table_layout = QVBoxLayout(table_group)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 校准表格
        self.cal_table = QTableWidget()
        # 列: 选择 + 泵地址 + 泵名称 + 10个圈数 + k + b + R²
        col_count = 3 + len(TEST_REVOLUTIONS) + 3
        self.cal_table.setColumnCount(col_count)
        
        # 设置表头
        headers = ["选择", "泵地址", "泵名称"]
        for rev in TEST_REVOLUTIONS:
            headers.append(f"{rev}圈(μL)")
        headers.extend(["k (μL/圈)", "b (μL)", "R²"])
        self.cal_table.setHorizontalHeaderLabels(headers)
        
        # 设置列宽
        self.cal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.cal_table.horizontalHeader().setMinimumSectionSize(60)
        
        # 固定前3列和后3列的宽度
        self.cal_table.setColumnWidth(0, 50)   # 选择
        self.cal_table.setColumnWidth(1, 60)   # 泵地址
        self.cal_table.setColumnWidth(2, 80)   # 泵名称
        for i in range(len(TEST_REVOLUTIONS)):
            self.cal_table.setColumnWidth(3 + i, 75)  # 圈数列
        self.cal_table.setColumnWidth(col_count - 3, 85)  # k
        self.cal_table.setColumnWidth(col_count - 2, 70)  # b
        self.cal_table.setColumnWidth(col_count - 1, 60)  # R²
        
        self.cal_table.setFont(FONT_SMALL)
        self.cal_table.setRowCount(12)
        self.cal_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        scroll.setWidget(self.cal_table)
        table_layout.addWidget(scroll)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("▶ 运行选中圈数测试")
        self.run_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 16px; font-weight: bold;")
        self.run_btn.setToolTip("运行选中泵的当前圈数测试")
        self.run_btn.clicked.connect(self._on_run_test)
        btn_layout.addWidget(self.run_btn)
        
        # 圈数选择
        self.rev_combo_label = QLabel("测试圈数:")
        self.rev_combo_label.setFont(FONT_NORMAL)
        btn_layout.addWidget(self.rev_combo_label)
        
        self.rev_spin = QSpinBox()
        self.rev_spin.setFont(FONT_NORMAL)
        self.rev_spin.setRange(10, 100)
        self.rev_spin.setValue(10)
        self.rev_spin.setSingleStep(10)
        self.rev_spin.setSuffix(" 圈")
        btn_layout.addWidget(self.rev_spin)
        
        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px;")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addSpacing(20)
        
        self.calc_btn = QPushButton("📊 计算回归系数")
        self.calc_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 8px 16px;")
        self.calc_btn.setToolTip("对选中泵进行线性回归计算")
        self.calc_btn.clicked.connect(self._on_calculate)
        btn_layout.addWidget(self.calc_btn)
        
        btn_layout.addStretch()
        
        self.reset_btn = QPushButton("重置选中")
        self.reset_btn.clicked.connect(self._on_reset_selected)
        btn_layout.addWidget(self.reset_btn)
        
        self.reset_all_btn = QPushButton("全部重置")
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        btn_layout.addWidget(self.reset_all_btn)
        
        table_layout.addLayout(btn_layout)
        layout.addWidget(table_group)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 保存所有校准")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 25px; font-weight: bold;")
        save_btn.clicked.connect(self._on_save_all)
        bottom_layout.addWidget(save_btn)
        
        bottom_layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("就绪 - 请选择泵并输入各圈数对应的实际体积")
        self.status_label.setFont(FONT_NORMAL)
        self.status_label.setStyleSheet("color: #666;")
        bottom_layout.addWidget(self.status_label)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("padding: 10px 25px;")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def _refresh_table(self):
        """刷新表格"""
        for row, addr in enumerate(range(1, 13)):
            data = self.pump_data[addr]
            
            # 选择列 - 使用单选按钮
            radio = QRadioButton()
            radio.setChecked(data.is_selected)
            radio.toggled.connect(lambda checked, a=addr: self._on_pump_selected(a, checked))
            
            radio_widget = QWidget()
            radio_layout = QHBoxLayout(radio_widget)
            radio_layout.addWidget(radio)
            radio_layout.setAlignment(Qt.AlignCenter)
            radio_layout.setContentsMargins(0, 0, 0, 0)
            self.cal_table.setCellWidget(row, 0, radio_widget)
            
            # 泵地址
            addr_item = QTableWidgetItem(str(addr))
            addr_item.setFlags(addr_item.flags() & ~Qt.ItemIsEditable)
            addr_item.setTextAlignment(Qt.AlignCenter)
            self.cal_table.setItem(row, 1, addr_item)
            
            # 泵名称
            name_item = QTableWidgetItem(data.pump_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            name_item.setTextAlignment(Qt.AlignCenter)
            self.cal_table.setItem(row, 2, name_item)
            
            # 10个圈数的体积输入
            for i, rev in enumerate(TEST_REVOLUTIONS):
                vol_spin = QDoubleSpinBox()
                vol_spin.setFont(FONT_SMALL)
                vol_spin.setRange(0, 100000)
                vol_spin.setDecimals(1)
                vol_spin.setValue(data.test_volumes[i])
                vol_spin.valueChanged.connect(
                    lambda val, a=addr, idx=i: self._on_volume_changed(a, idx, val)
                )
                self.cal_table.setCellWidget(row, 3 + i, vol_spin)
            
            # k (斜率)
            k_item = QTableWidgetItem(f"{data.slope_k:.2f}" if data.slope_k != 0 else "-")
            k_item.setFlags(k_item.flags() & ~Qt.ItemIsEditable)
            k_item.setTextAlignment(Qt.AlignCenter)
            if data.is_calibrated:
                k_item.setForeground(QBrush(QColor(0, 128, 0)))  # 绿色
            self.cal_table.setItem(row, 3 + len(TEST_REVOLUTIONS), k_item)
            
            # b (截距)
            b_item = QTableWidgetItem(f"{data.intercept_b:.2f}" if data.intercept_b != 0 or data.is_calibrated else "-")
            b_item.setFlags(b_item.flags() & ~Qt.ItemIsEditable)
            b_item.setTextAlignment(Qt.AlignCenter)
            if data.is_calibrated:
                b_item.setForeground(QBrush(QColor(0, 128, 0)))
            self.cal_table.setItem(row, 3 + len(TEST_REVOLUTIONS) + 1, b_item)
            
            # R²
            r2_item = QTableWidgetItem(f"{data.r_squared:.4f}" if data.r_squared > 0 else "-")
            r2_item.setFlags(r2_item.flags() & ~Qt.ItemIsEditable)
            r2_item.setTextAlignment(Qt.AlignCenter)
            if data.r_squared >= 0.99:
                r2_item.setForeground(QBrush(QColor(0, 128, 0)))  # 绿色 - 很好
            elif data.r_squared >= 0.95:
                r2_item.setForeground(QBrush(QColor(255, 165, 0)))  # 橙色 - 一般
            elif data.r_squared > 0:
                r2_item.setForeground(QBrush(QColor(255, 0, 0)))  # 红色 - 差
            self.cal_table.setItem(row, 3 + len(TEST_REVOLUTIONS) + 2, r2_item)
            
            # 更新行背景色
            self._update_row_style(row, data.is_selected, data.is_calibrated)
    
    def _update_row_style(self, row: int, is_selected: bool, is_calibrated: bool):
        """更新行样式"""
        if is_selected:
            bg_color = QColor(200, 220, 255)  # 蓝色 - 选中
        elif is_calibrated:
            bg_color = QColor(220, 255, 220)  # 绿色 - 已校准
        else:
            bg_color = QColor(255, 255, 255)  # 白色
        
        for col in [1, 2, 3 + len(TEST_REVOLUTIONS), 3 + len(TEST_REVOLUTIONS) + 1, 3 + len(TEST_REVOLUTIONS) + 2]:
            item = self.cal_table.item(row, col)
            if item:
                item.setBackground(QBrush(bg_color))
    
    def _on_pump_selected(self, pump_addr: int, checked: bool):
        """泵选择变更"""
        if checked:
            for addr, data in self.pump_data.items():
                data.is_selected = (addr == pump_addr)
            self.selected_pump = pump_addr
            self.status_label.setText(f"已选择: 泵{pump_addr} ({self.pump_data[pump_addr].pump_name})")
        else:
            self.pump_data[pump_addr].is_selected = False
            if self.selected_pump == pump_addr:
                self.selected_pump = None
                self.status_label.setText("就绪")
        self._refresh_table()
    
    def _on_volume_changed(self, pump_addr: int, test_index: int, value: float):
        """测试体积输入变更"""
        self.pump_data[pump_addr].test_volumes[test_index] = value
    
    def _on_run_test(self):
        """运行测试"""
        if self.selected_pump is None:
            QMessageBox.warning(self, "警告", "请先选择要校准的泵")
            return
        
        if not self.rs485.is_connected():
            QMessageBox.warning(self, "警告", "请先连接RS485")
            return
        
        addr = self.selected_pump
        revolutions = self.rev_spin.value()
        encoder_counts = int(revolutions * ENCODER_DIVISIONS_PER_REV)
        speed = self.speed_spin.value()
        
        self.is_testing = True
        self._update_ui_testing(True)
        self.status_label.setText(f"正在运行: 泵{addr} - {revolutions}圈...")
        
        try:
            result = self.rs485.run_position_rel(addr, encoder_counts, speed, acceleration=2)
            if result:
                estimated_seconds = (revolutions / (speed / 60.0)) + 2.0
                QTimer.singleShot(int(estimated_seconds * 1000), self._on_test_complete)
            else:
                QMessageBox.warning(self, "警告", "发送位置命令失败")
                self._on_test_complete()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"执行失败: {e}")
            self._on_test_complete()
    
    def _on_test_complete(self):
        """测试完成"""
        self.is_testing = False
        self._update_ui_testing(False)
        
        rev = self.rev_spin.value()
        if self.selected_pump:
            self.status_label.setText(f"测试完成! 请称量并输入 {rev}圈 对应的实际体积")
            QMessageBox.information(
                self, "测试完成",
                f"泵{self.selected_pump} - {rev}圈 测试完成!\n"
                f"请称量液体体积，填入对应的列中。"
            )
        else:
            self.status_label.setText("就绪")
    
    def _update_ui_testing(self, testing: bool):
        """更新UI测试状态"""
        self.run_btn.setEnabled(not testing)
        self.stop_btn.setEnabled(testing)
        self.calc_btn.setEnabled(not testing)
        self.rev_spin.setEnabled(not testing)
        self.speed_spin.setEnabled(not testing)
    
    def _on_stop(self):
        """停止测试"""
        if self.selected_pump:
            try:
                self.rs485.stop_pump(self.selected_pump)
            except:
                pass
        self.is_testing = False
        self._update_ui_testing(False)
        self.status_label.setText("测试已停止")
    
    def _on_calculate(self):
        """计算选中泵的回归系数"""
        if self.selected_pump is None:
            QMessageBox.warning(self, "警告", "请先选择要校准的泵")
            return
        
        addr = self.selected_pump
        data = self.pump_data[addr]
        
        # 收集有效数据点 (x=圈数, y=体积)
        valid_points = []
        for i, rev in enumerate(TEST_REVOLUTIONS):
            vol = data.test_volumes[i]
            if vol > 0:
                valid_points.append((float(rev), vol))
        
        if len(valid_points) < 2:
            QMessageBox.warning(self, "警告", f"需要至少2个有效数据点\n当前有效: {len(valid_points)}个")
            return
        
        # 线性回归: y = kx + b
        n = len(valid_points)
        x_data = [p[0] for p in valid_points]
        y_data = [p[1] for p in valid_points]
        
        sum_x = sum(x_data)
        sum_y = sum(y_data)
        sum_xy = sum(x * y for x, y in zip(x_data, y_data))
        sum_x2 = sum(x * x for x in x_data)
        
        # k = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x^2)
        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 1e-10:
            QMessageBox.warning(self, "错误", "数据点共线，无法计算回归")
            return
        
        k = (n * sum_xy - sum_x * sum_y) / denominator
        b = (sum_y - k * sum_x) / n
        
        # 计算 R²
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_data)
        ss_res = sum((y - (k * x + b)) ** 2 for x, y in zip(x_data, y_data))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
        # 保存结果
        data.slope_k = k
        data.intercept_b = b
        data.r_squared = r_squared
        data.ul_per_encoder_count = k / ENCODER_DIVISIONS_PER_REV
        data.is_calibrated = True
        
        self._refresh_table()
        
        self.status_label.setText(f"泵{addr} 校准完成: k={k:.2f}, b={b:.2f}, R²={r_squared:.4f}")
        
        QMessageBox.information(
            self, "校准完成",
            f"泵{addr} ({data.pump_name}) 线性回归结果:\n\n"
            f"公式: Volume = {k:.2f} × 圈数 + {b:.2f}\n\n"
            f"斜率 k = {k:.2f} μL/圈\n"
            f"截距 b = {b:.2f} μL\n"
            f"R² = {r_squared:.4f}\n\n"
            f"有效数据点: {n}个"
        )
        
        if r_squared < 0.95:
            QMessageBox.warning(self, "警告", f"R² = {r_squared:.4f} 较低，建议检查数据或增加测试点")
    
    def _on_reset_selected(self):
        """重置选中泵"""
        if self.selected_pump is None:
            QMessageBox.warning(self, "警告", "请先选择泵")
            return
        
        reply = QMessageBox.question(self, "确认", f"重置泵{self.selected_pump}的数据？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            data = self.pump_data[self.selected_pump]
            data.test_volumes = [0.0] * len(TEST_REVOLUTIONS)
            data.slope_k = 0.0
            data.intercept_b = 0.0
            data.r_squared = 0.0
            data.ul_per_encoder_count = 0.0
            data.is_calibrated = False
            self._refresh_table()
            self.status_label.setText(f"泵{self.selected_pump} 已重置")
    
    def _on_reset_all(self):
        """重置所有"""
        reply = QMessageBox.question(self, "确认", "重置所有泵的数据？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for data in self.pump_data.values():
                data.test_volumes = [0.0] * len(TEST_REVOLUTIONS)
                data.slope_k = 0.0
                data.intercept_b = 0.0
                data.r_squared = 0.0
                data.ul_per_encoder_count = 0.0
                data.is_calibrated = False
                data.is_selected = False
            self.selected_pump = None
            self._refresh_table()
            self.status_label.setText("所有数据已重置")
    
    def _on_save_all(self):
        """保存所有已校准泵"""
        saved_count = 0
        
        for addr, data in self.pump_data.items():
            if data.is_calibrated and data.slope_k > 0:
                if addr not in self.config.calibration_data:
                    self.config.calibration_data[addr] = {}
                
                self.config.calibration_data[addr]["slope_k"] = data.slope_k
                self.config.calibration_data[addr]["intercept_b"] = data.intercept_b
                self.config.calibration_data[addr]["r_squared"] = data.r_squared
                self.config.calibration_data[addr]["ul_per_encoder_count"] = data.ul_per_encoder_count
                self.config.calibration_data[addr]["calibration_method"] = "linear_regression"
                
                self.calibration_saved.emit(addr, data.ul_per_encoder_count)
                saved_count += 1
        
        if saved_count > 0:
            QMessageBox.information(self, "保存成功", f"已保存 {saved_count} 个泵的校准数据!")
        else:
            QMessageBox.warning(self, "提示", "没有已校准的泵数据可保存")

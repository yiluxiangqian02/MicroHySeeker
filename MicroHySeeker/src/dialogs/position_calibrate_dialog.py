"""
位置模式校准对话框 - SR_VFOC泵位置模式校准

支持多点位移测试和线性回归拟合。
用户可以测试不同的编码器位移量，记录实际液体体积，
然后通过回归分析得到准确的 ul_per_encoder_count 校准系数。
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QDoubleSpinBox, QSpinBox, QTextEdit, QMessageBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFormLayout, QWidget, QSplitter
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont
import time
import math
from dataclasses import dataclass, field
from typing import List, Optional

from src.models import SystemConfig
from src.services.rs485_wrapper import get_rs485_instance


# 字体设置
FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)


@dataclass
class CalibrationPoint:
    """校准测试点"""
    encoder_counts: int          # 编码器计数
    revolutions: float           # 对应圈数
    actual_volume_ul: float = 0.0  # 实际测量体积 (μL)
    completed: bool = False      # 是否已完成测试


class PositionCalibrateDialog(QDialog):
    """SR_VFOC位置模式校准对话框
    
    工作流程:
    1. 选择要校准的泵
    2. 设置测试参数（速度、圈数列表）
    3. 逐个执行测试点
    4. 输入每个测试点的实际液体体积
    5. 执行线性回归计算校准系数
    6. 保存校准结果
    """
    
    calibration_saved = Signal(int, float)  # pump_address, ul_per_encoder_count
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.rs485 = get_rs485_instance()
        
        # 校准数据
        self.calibration_points: List[CalibrationPoint] = []
        self.current_test_index = -1
        self.is_testing = False
        
        # 结果
        self.ul_per_encoder_count = 0.0
        self.r_squared = 0.0
        
        self.setWindowTitle("SR_VFOC位置模式校准")
        self.setMinimumSize(800, 600)
        self.setFont(FONT_NORMAL)
        self._init_ui()
        self._init_test_points()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 顶部：泵选择和参数设置
        top_group = QGroupBox("校准设置")
        top_group.setFont(FONT_TITLE)
        top_layout = QFormLayout(top_group)
        
        # 泵选择
        self.pump_combo = QComboBox()
        for ch in self.config.dilution_channels:
            self.pump_combo.addItem(
                f"通道{ch.channel_id} - {ch.solution_name} (地址{ch.pump_address})",
                ch.pump_address
            )
        if not self.config.dilution_channels:
            # 如果没有配液通道，使用泵地址
            for i in range(1, 13):
                self.pump_combo.addItem(f"泵 {i}", i)
        top_layout.addRow("选择泵:", self.pump_combo)
        
        # 速度设置
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(50, 500)
        self.speed_spin.setValue(100)
        self.speed_spin.setSuffix(" RPM")
        top_layout.addRow("测试速度:", self.speed_spin)
        
        # 加速度设置
        self.accel_spin = QSpinBox()
        self.accel_spin.setRange(1, 255)
        self.accel_spin.setValue(2)
        top_layout.addRow("加速度:", self.accel_spin)
        
        layout.addWidget(top_group)
        
        # 中部：测试点表格
        table_group = QGroupBox("测试点")
        table_group.setFont(FONT_TITLE)
        table_layout = QVBoxLayout(table_group)
        
        # 测试点表格
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(5)
        self.points_table.setHorizontalHeaderLabels([
            "序号", "编码器计数", "圈数", "实际体积(μL)", "状态"
        ])
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.points_table.setFont(FONT_NORMAL)
        table_layout.addWidget(self.points_table)
        
        # 测试控制按钮
        btn_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("▶ 测试选中点")
        self.test_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px 16px;")
        self.test_btn.clicked.connect(self._on_test_selected)
        btn_layout.addWidget(self.test_btn)
        
        self.test_all_btn = QPushButton("▶▶ 依次测试全部")
        self.test_all_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 16px;")
        self.test_all_btn.clicked.connect(self._on_test_all)
        btn_layout.addWidget(self.test_all_btn)
        
        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px 16px;")
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addStretch()
        
        self.reset_btn = QPushButton("重置数据")
        self.reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.reset_btn)
        
        table_layout.addLayout(btn_layout)
        layout.addWidget(table_group)
        
        # 底部：结果区域
        result_group = QGroupBox("校准结果")
        result_group.setFont(FONT_TITLE)
        result_layout = QVBoxLayout(result_group)
        
        # 计算按钮
        calc_btn = QPushButton("📊 计算校准系数 (线性回归)")
        calc_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 10px 20px;")
        calc_btn.clicked.connect(self._on_calculate)
        result_layout.addWidget(calc_btn)
        
        # 结果显示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)
        self.result_text.setFont(FONT_NORMAL)
        result_layout.addWidget(self.result_text)
        
        layout.addWidget(result_group)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 保存校准")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 25px;")
        save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(save_btn)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("padding: 10px 25px;")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def _init_test_points(self):
        """初始化测试点列表"""
        # 默认测试点：0.5圈、1圈、2圈、3圈、5圈
        default_revolutions = [0.5, 1.0, 2.0, 3.0, 5.0]
        
        self.calibration_points = []
        encoder_per_rev = 16384  # ENCODER_DIVISIONS_PER_REV
        
        for rev in default_revolutions:
            counts = int(rev * encoder_per_rev)
            self.calibration_points.append(CalibrationPoint(
                encoder_counts=counts,
                revolutions=rev
            ))
        
        self._refresh_table()
    
    def _refresh_table(self):
        """刷新测试点表格"""
        self.points_table.setRowCount(len(self.calibration_points))
        
        for row, point in enumerate(self.calibration_points):
            # 序号
            seq_item = QTableWidgetItem(str(row + 1))
            seq_item.setFlags(seq_item.flags() & ~Qt.ItemIsEditable)
            seq_item.setTextAlignment(Qt.AlignCenter)
            self.points_table.setItem(row, 0, seq_item)
            
            # 编码器计数
            counts_item = QTableWidgetItem(str(point.encoder_counts))
            counts_item.setFlags(counts_item.flags() & ~Qt.ItemIsEditable)
            counts_item.setTextAlignment(Qt.AlignCenter)
            self.points_table.setItem(row, 1, counts_item)
            
            # 圈数
            rev_item = QTableWidgetItem(f"{point.revolutions:.2f}")
            rev_item.setFlags(rev_item.flags() & ~Qt.ItemIsEditable)
            rev_item.setTextAlignment(Qt.AlignCenter)
            self.points_table.setItem(row, 2, rev_item)
            
            # 实际体积 (可编辑)
            vol_spin = QDoubleSpinBox()
            vol_spin.setRange(0, 10000)
            vol_spin.setDecimals(2)
            vol_spin.setValue(point.actual_volume_ul)
            vol_spin.valueChanged.connect(
                lambda val, r=row: self._on_volume_changed(r, val)
            )
            self.points_table.setCellWidget(row, 3, vol_spin)
            
            # 状态
            if point.completed:
                status = "✅ 已完成"
            elif self.is_testing and row == self.current_test_index:
                status = "🔄 测试中..."
            else:
                status = "⏳ 待测试"
            
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.points_table.setItem(row, 4, status_item)
    
    def _on_volume_changed(self, row: int, value: float):
        """实际体积输入变更"""
        if 0 <= row < len(self.calibration_points):
            self.calibration_points[row].actual_volume_ul = value
            if value > 0:
                self.calibration_points[row].completed = True
                self._refresh_table()
    
    def _get_pump_address(self) -> int:
        """获取当前选中的泵地址"""
        return self.pump_combo.currentData()
    
    def _on_test_selected(self):
        """测试选中的测试点"""
        row = self.points_table.currentRow()
        if row < 0 or row >= len(self.calibration_points):
            QMessageBox.warning(self, "警告", "请先选择一个测试点")
            return
        
        if not self.rs485.is_connected():
            QMessageBox.warning(self, "警告", "请先连接RS485")
            return
        
        self._run_single_test(row)
    
    def _on_test_all(self):
        """依次测试所有点"""
        if not self.rs485.is_connected():
            QMessageBox.warning(self, "警告", "请先连接RS485")
            return
        
        # 从第一个未完成的点开始
        start_index = 0
        for i, point in enumerate(self.calibration_points):
            if not point.completed:
                start_index = i
                break
        
        self._run_sequential_tests(start_index)
    
    def _run_single_test(self, index: int):
        """运行单个测试点"""
        point = self.calibration_points[index]
        addr = self._get_pump_address()
        speed = self.speed_spin.value()
        accel = self.accel_spin.value()
        
        self.is_testing = True
        self.current_test_index = index
        self._update_ui_testing(True)
        self._refresh_table()
        
        # 发送位置命令
        try:
            result = self.rs485.run_position_rel(
                addr, 
                point.encoder_counts, 
                speed, 
                accel
            )
            
            if result:
                # 启动定时器检查完成状态
                self._start_completion_check()
            else:
                QMessageBox.warning(self, "警告", f"发送位置命令失败")
                self._complete_test(False)
                
        except AttributeError:
            # rs485_wrapper可能没有这个方法，使用备选方案
            try:
                # 直接使用泵管理器
                from src.echem_sdl.hardware import get_pump_manager
                pm = get_pump_manager()
                if pm:
                    pm.move_position_rel(
                        addr, 
                        point.encoder_counts, 
                        speed, 
                        accel,
                        fire_and_forget=True
                    )
                    self._start_completion_check()
                else:
                    QMessageBox.warning(self, "警告", "泵管理器不可用")
                    self._complete_test(False)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"执行失败: {e}")
                self._complete_test(False)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"执行失败: {e}")
            self._complete_test(False)
    
    def _start_completion_check(self):
        """启动完成检查定时器"""
        # 根据圈数估算完成时间
        point = self.calibration_points[self.current_test_index]
        speed = self.speed_spin.value()
        
        # 估算时间 = 圈数 / (RPM / 60)
        estimated_seconds = (point.revolutions / (speed / 60.0)) + 1.0  # 加1秒余量
        
        # 设置定时器在预估时间后检查
        QTimer.singleShot(int(estimated_seconds * 1000), self._check_completion)
    
    def _check_completion(self):
        """检查测试是否完成"""
        if not self.is_testing:
            return
        
        # 假设已完成（实际应该读取运行状态）
        self._complete_test(True)
    
    def _complete_test(self, success: bool):
        """完成测试"""
        self.is_testing = False
        
        if success and self.current_test_index >= 0:
            # 弹出输入实际体积对话框
            QMessageBox.information(
                self, 
                "测试完成", 
                f"测试点 {self.current_test_index + 1} 已完成!\n"
                f"请称量液体，输入实际体积。"
            )
        
        self.current_test_index = -1
        self._update_ui_testing(False)
        self._refresh_table()
    
    def _run_sequential_tests(self, start_index: int):
        """依次运行测试"""
        # TODO: 实现连续测试模式
        # 目前简化为逐个手动测试
        self._run_single_test(start_index)
    
    def _update_ui_testing(self, testing: bool):
        """更新UI测试状态"""
        self.test_btn.setEnabled(not testing)
        self.test_all_btn.setEnabled(not testing)
        self.stop_btn.setEnabled(testing)
        self.pump_combo.setEnabled(not testing)
        self.speed_spin.setEnabled(not testing)
    
    def _on_stop(self):
        """停止测试"""
        addr = self._get_pump_address()
        
        try:
            self.rs485.stop_pump(addr)
        except:
            pass
        
        self.is_testing = False
        self.current_test_index = -1
        self._update_ui_testing(False)
        self._refresh_table()
        
        QMessageBox.information(self, "提示", "测试已停止")
    
    def _on_reset(self):
        """重置所有测试数据"""
        reply = QMessageBox.question(
            self, 
            "确认", 
            "确定要重置所有测试数据吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._init_test_points()
            self.result_text.clear()
            self.ul_per_encoder_count = 0.0
            self.r_squared = 0.0
    
    def _on_calculate(self):
        """计算校准系数 - 线性回归"""
        # 收集有效数据点
        valid_points = [
            (p.encoder_counts, p.actual_volume_ul)
            for p in self.calibration_points
            if p.completed and p.actual_volume_ul > 0
        ]
        
        if len(valid_points) < 2:
            QMessageBox.warning(
                self, 
                "警告", 
                "至少需要2个有效测试点进行回归计算"
            )
            return
        
        # 线性回归: volume = k * encoder_counts
        # 最小二乘法: k = sum(x*y) / sum(x^2)
        x_data = [p[0] for p in valid_points]  # encoder_counts
        y_data = [p[1] for p in valid_points]  # actual_volume
        
        # 计算斜率 (强制过原点)
        sum_xy = sum(x * y for x, y in zip(x_data, y_data))
        sum_x2 = sum(x * x for x in x_data)
        
        if sum_x2 == 0:
            QMessageBox.warning(self, "错误", "无效的测试数据")
            return
        
        k = sum_xy / sum_x2  # ul_per_encoder_count
        
        # 计算 R²
        y_mean = sum(y_data) / len(y_data)
        ss_tot = sum((y - y_mean) ** 2 for y in y_data)
        ss_res = sum((y - k * x) ** 2 for x, y in zip(x_data, y_data))
        
        if ss_tot > 0:
            r_squared = 1 - (ss_res / ss_tot)
        else:
            r_squared = 0.0
        
        self.ul_per_encoder_count = k
        self.r_squared = r_squared
        
        # 计算每圈体积
        encoder_per_rev = 16384
        ul_per_rev = k * encoder_per_rev
        
        # 显示结果
        result_text = (
            f"═══════════════════════════════════════\n"
            f"  线性回归结果 (过原点拟合)\n"
            f"═══════════════════════════════════════\n"
            f"  校准系数: {k:.8f} μL/count\n"
            f"  每圈体积: {ul_per_rev:.2f} μL/圈\n"
            f"  R² 拟合度: {r_squared:.4f}\n"
            f"───────────────────────────────────────\n"
            f"  测试点数: {len(valid_points)}\n"
        )
        
        # 显示各点误差
        result_text += f"───────────────────────────────────────\n"
        result_text += f"  各点预测误差:\n"
        for i, (x, y) in enumerate(valid_points):
            predicted = k * x
            error = y - predicted
            error_pct = (error / y * 100) if y > 0 else 0
            result_text += f"    点{i+1}: 实际{y:.2f}μL, 预测{predicted:.2f}μL, 误差{error_pct:+.1f}%\n"
        
        self.result_text.setText(result_text)
        
        # 如果R²太低，给出警告
        if r_squared < 0.95:
            QMessageBox.warning(
                self, 
                "警告", 
                f"R² = {r_squared:.4f} 较低，可能存在测量误差或非线性。\n"
                f"建议检查测试数据或增加测试点。"
            )
    
    def _on_save(self):
        """保存校准结果"""
        if self.ul_per_encoder_count <= 0:
            QMessageBox.warning(self, "警告", "请先计算校准系数")
            return
        
        addr = self._get_pump_address()
        
        # 保存到配置
        if addr not in self.config.calibration_data:
            self.config.calibration_data[addr] = {}
        
        self.config.calibration_data[addr]["ul_per_encoder_count"] = self.ul_per_encoder_count
        self.config.calibration_data[addr]["r_squared"] = self.r_squared
        self.config.calibration_data[addr]["calibration_method"] = "position_mode"
        
        # 发出信号
        self.calibration_saved.emit(addr, self.ul_per_encoder_count)
        
        QMessageBox.information(
            self, 
            "成功", 
            f"泵 {addr} 的位置模式校准已保存!\n"
            f"校准系数: {self.ul_per_encoder_count:.8f} μL/count"
        )

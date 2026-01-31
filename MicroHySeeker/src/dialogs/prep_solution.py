"""
配制溶液对话框 - 参照 C# PrepSolution
选择溶液配方，设置目标浓度，执行配液
- 总体积单位改为mL
- 所有小数保留两位
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDoubleSpinBox,
    QCheckBox, QMessageBox, QGroupBox, QFormLayout, QProgressBar, QWidget
)
from PySide6.QtCore import Qt, Signal, QThread, Slot
from PySide6.QtGui import QFont
from typing import List

from src.models import SystemConfig, DilutionChannel
from src.services.rs485_wrapper import get_rs485_instance


# 全局字体
FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)


class PrepSolutionWorker(QThread):
    """配液执行线程"""
    progress = Signal(int, str)  # (进度百分比, 消息)
    finished = Signal(bool)  # 是否成功
    
    def __init__(self, channels: List[DilutionChannel], target_concs: List[float], 
                 is_solvents: List[bool], total_volume: float, rs485):
        super().__init__()
        self.channels = channels
        self.target_concs = target_concs
        self.is_solvents = is_solvents
        self.total_volume = total_volume
        self.rs485 = rs485
        self._abort = False
    
    def abort(self):
        self._abort = True
    
    def run(self):
        """执行配液 - 后端接口调用点"""
        try:
            # 计算各溶液注入量
            volumes = self._calculate_volumes()
            
            total_steps = len([v for v in volumes if v > 0])
            current_step = 0
            
            for i, (ch, vol) in enumerate(zip(self.channels, volumes)):
                if self._abort:
                    self.progress.emit(0, "配液已取消")
                    self.finished.emit(False)
                    return
                
                if vol <= 0:
                    continue
                
                current_step += 1
                progress = int(current_step / total_steps * 100)
                self.progress.emit(progress, f"正在注入 {ch.solution_name}: {vol:.2f} μL")
                
                # === 后端接口调用 ===
                # self.rs485.start_pump(ch.pump_address, ch.direction, ch.default_rpm)
                # 计算注入时间（基于校准参数）
                # time.sleep(inject_time)
                # self.rs485.stop_pump(ch.pump_address)
                
                # 模拟延时
                self.msleep(500)
            
            self.progress.emit(100, "配液完成")
            self.finished.emit(True)
            
        except Exception as e:
            self.progress.emit(0, f"配液失败: {e}")
            self.finished.emit(False)
    
    def _calculate_volumes(self) -> List[float]:
        """计算各溶液注入量"""
        volumes = []
        solvent_idx = -1
        non_solvent_total = 0
        
        for i, (ch, target, is_solvent) in enumerate(zip(
            self.channels, self.target_concs, self.is_solvents
        )):
            if is_solvent:
                solvent_idx = i
                volumes.append(0)  # 先占位
            else:
                if target > 0 and ch.stock_concentration > 0:
                    # V = C_target * V_total / C_stock
                    vol = target * self.total_volume / ch.stock_concentration
                    volumes.append(vol)
                    non_solvent_total += vol
                else:
                    volumes.append(0)
        
        # 溶剂填充剩余体积
        if solvent_idx >= 0:
            volumes[solvent_idx] = max(0, self.total_volume - non_solvent_total)
        
        return volumes


class PrepSolutionDialog(QDialog):
    """
    配制溶液对话框
    
    === 后端接口 ===
    1. RS485Wrapper.start_pump(addr, dir, rpm) -> bool
    2. RS485Wrapper.stop_pump(addr) -> bool
    3. 泵校准参数用于计算注入时间
    """
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.rs485 = get_rs485_instance()
        self.worker = None
        
        self.setWindowTitle("配制溶液")
        self.setGeometry(200, 150, 800, 500)
        self._init_ui()
        self._load_channels()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 溶液配方表格
        recipe_group = QGroupBox("溶液配方")
        recipe_group.setFont(FONT_TITLE)
        recipe_layout = QVBoxLayout(recipe_group)
        
        self.recipe_table = QTableWidget()
        self.recipe_table.setFont(FONT_NORMAL)
        self.recipe_table.setColumnCount(5)
        self.recipe_table.setHorizontalHeaderLabels([
            "溶液名称", "原浓度(mol/L)", "泵端口", "目标浓度(mol/L)", "是否溶剂"
        ])
        self.recipe_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        recipe_layout.addWidget(self.recipe_table)
        
        layout.addWidget(recipe_group)
        
        # 总体积设置
        vol_layout = QHBoxLayout()
        vol_label = QLabel("总体积 (mL):")
        vol_label.setFont(FONT_NORMAL)
        vol_layout.addWidget(vol_label)
        self.total_vol_spin = QDoubleSpinBox()
        self.total_vol_spin.setFont(FONT_NORMAL)
        self.total_vol_spin.setRange(0, 100000)
        self.total_vol_spin.setDecimals(2)
        self.total_vol_spin.setValue(1.00)
        vol_layout.addWidget(self.total_vol_spin)
        vol_layout.addStretch()
        layout.addLayout(vol_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(FONT_NORMAL)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        self.status_label.setFont(FONT_NORMAL)
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.start_btn = QPushButton("开始配制")
        self.start_btn.setFont(FONT_NORMAL)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 20px;")
        self.start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self.start_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFont(FONT_NORMAL)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_channels(self):
        """加载配液通道"""
        channels = self.config.dilution_channels
        self.recipe_table.setRowCount(len(channels))
        
        for row, ch in enumerate(channels):
            # 溶液名称（只读）
            name_item = QTableWidgetItem(ch.solution_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.recipe_table.setItem(row, 0, name_item)
            
            # 原浓度（只读）
            conc_item = QTableWidgetItem(str(ch.stock_concentration))
            conc_item.setFlags(conc_item.flags() & ~Qt.ItemIsEditable)
            self.recipe_table.setItem(row, 1, conc_item)
            
            # 泵端口（只读）
            port_item = QTableWidgetItem(str(ch.pump_address))
            port_item.setFlags(port_item.flags() & ~Qt.ItemIsEditable)
            self.recipe_table.setItem(row, 2, port_item)
            
            # 目标浓度（可编辑）
            target_spin = QDoubleSpinBox()
            target_spin.setFont(FONT_NORMAL)
            target_spin.setRange(0, 1000)
            target_spin.setDecimals(2)
            target_spin.setValue(0)
            self.recipe_table.setCellWidget(row, 3, target_spin)
            
            # 是否溶剂
            solvent_check = QCheckBox()
            self.recipe_table.setCellWidget(row, 4, solvent_check)
    
    def _on_start(self):
        """开始配制"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "配液正在进行中")
            return
        
        # 收集参数
        channels = []
        target_concs = []
        is_solvents = []
        
        for row in range(self.recipe_table.rowCount()):
            if row < len(self.config.dilution_channels):
                ch = self.config.dilution_channels[row]
                channels.append(ch)
                
                target_spin = self.recipe_table.cellWidget(row, 3)
                target_concs.append(target_spin.value())
                
                solvent_check = self.recipe_table.cellWidget(row, 4)
                is_solvents.append(solvent_check.isChecked())
        
        # 验证
        if not any(c > 0 for c in target_concs) and not any(is_solvents):
            QMessageBox.warning(self, "警告", "请至少设置一个目标浓度或选择溶剂")
            return
        
        # 启动工作线程
        self.worker = PrepSolutionWorker(
            channels, target_concs, is_solvents,
            self.total_vol_spin.value(), self.rs485
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
        
        self.start_btn.setEnabled(False)
        self.status_label.setText("正在配制...")
    
    def _on_cancel(self):
        """取消"""
        if self.worker and self.worker.isRunning():
            self.worker.abort()
            self.worker.wait(2000)
        self.reject()
    
    @Slot(int, str)
    def _on_progress(self, percent: int, msg: str):
        """进度更新"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(msg)
    
    @Slot(bool)
    def _on_finished(self, success: bool):
        """配液完成"""
        self.start_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "完成", "配液完成！")
        else:
            QMessageBox.warning(self, "警告", "配液未完成")

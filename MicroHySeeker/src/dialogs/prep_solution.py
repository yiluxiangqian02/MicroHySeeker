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
            # 1. 先配置配液通道
            if not self.rs485.is_connected():
                self.progress.emit(0, "错误：RS485未连接")
                self.finished.emit(False)
                return
            
            self.progress.emit(5, "配置配液通道...")
            success = self.rs485.configure_dilution_channels(self.channels)
            if not success:
                self.progress.emit(0, "错误：配置通道失败")
                self.finished.emit(False)
                return
            
            # 2. 计算各溶液注入量
            volumes = self._calculate_volumes()
            
            total_steps = len([v for v in volumes if v > 0])
            if total_steps == 0:
                self.progress.emit(0, "错误：没有需要注入的溶液")
                self.finished.emit(False)
                return
            
            current_step = 0
            
            # 3. 依次执行配液
            for i, (ch, vol, target, is_solvent) in enumerate(zip(
                self.channels, volumes, self.target_concs, self.is_solvents
            )):
                if self._abort:
                    self.progress.emit(0, "配液已取消")
                    self.finished.emit(False)
                    return
                
                if vol <= 0:
                    continue
                
                current_step += 1
                base_progress = int(((current_step - 1) / total_steps) * 90) + 10
                
                # 准备配液
                channel_id = ch.pump_address
                self.progress.emit(
                    base_progress, 
                    f"准备通道 {channel_id} ({ch.solution_name}): {vol:.2f} μL"
                )
                
                # 使用准备方法计算体积（如果不是溶剂）
                if not is_solvent:
                    calc_vol = self.rs485.prepare_dilution(
                        channel_id, 
                        target, 
                        self.total_volume
                    )
                    if abs(calc_vol - vol) > 1.0:  # 允许1μL误差
                        print(f"⚠️ 体积计算差异: 预期{vol:.2f}μL, 实际{calc_vol:.2f}μL")
                        vol = calc_vol
                
                # 开始配液
                self.progress.emit(
                    base_progress + 2,
                    f"注入 {ch.solution_name}: {vol:.2f} μL"
                )
                
                success = self.rs485.start_dilution(channel_id, vol)
                if not success:
                    self.progress.emit(0, f"错误：启动通道 {channel_id} 失败")
                    self.finished.emit(False)
                    return
                
                # 等待配液完成
                import time
                from echem_sdl.hardware.diluter import Diluter
                duration = Diluter.calculate_duration(vol, ch.default_rpm)
                max_wait = duration + 5.0  # 最多等待额外5秒
                start_time = time.time()
                
                while True:
                    if self._abort:
                        self.rs485.stop_dilution(channel_id)
                        self.progress.emit(0, "配液已取消")
                        self.finished.emit(False)
                        return
                    
                    # 查询进度
                    progress_info = self.rs485.get_dilution_progress(channel_id)
                    state = progress_info.get('state', 'unknown')
                    percent = progress_info.get('progress', 0)
                    
                    # 更新显示
                    step_progress = base_progress + int(percent * 0.8)  # 每步最多80%进度
                    self.progress.emit(
                        step_progress,
                        f"注入 {ch.solution_name}: {percent:.1f}%"
                    )
                    
                    if state == 'completed':
                        break
                    elif state == 'error':
                        self.progress.emit(0, f"错误：通道 {channel_id} 配液失败")
                        self.finished.emit(False)
                        return
                    
                    # 超时检查
                    if time.time() - start_time > max_wait:
                        self.progress.emit(0, f"错误：通道 {channel_id} 配液超时")
                        self.finished.emit(False)
                        return
                    
                    self.msleep(200)  # 每200ms查询一次
                
                self.progress.emit(
                    base_progress + 8,
                    f"通道 {channel_id} ({ch.solution_name}) 完成"
                )
            
            self.progress.emit(100, "配液完成")
            self.finished.emit(True)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
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
        
        # 将mL转换为μL（UI显示mL，后端使用μL）
        total_volume_ul = self.total_vol_spin.value() * 1000.0
        
        # 启动工作线程
        self.worker = PrepSolutionWorker(
            channels, target_concs, is_solvents,
            total_volume_ul, self.rs485
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

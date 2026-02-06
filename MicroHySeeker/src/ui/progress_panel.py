"""
实验进度面板 - 显示实验执行状态和进度

提供：
1. 总体进度条和时间显示
2. 当前步骤状态和进度
3. 批次注入状态（配液用）
4. 步骤列表状态预览
"""
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGroupBox, QListWidget, QListWidgetItem, QFrame, QGridLayout,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor

from src.core.step_state import StepState, EngineState
from src.engine.engine_v2 import ExperimentProgress


# 样式常量
FONT_NORMAL = QFont("Microsoft YaHei", 10)
FONT_TITLE = QFont("Microsoft YaHei", 11, QFont.Bold)
FONT_LARGE = QFont("Microsoft YaHei", 14, QFont.Bold)

# 状态颜色
STATE_COLORS = {
    EngineState.IDLE: "#9E9E9E",      # 灰色
    EngineState.LOADING: "#2196F3",   # 蓝色
    EngineState.READY: "#4CAF50",     # 绿色
    EngineState.RUNNING: "#FF9800",   # 橙色
    EngineState.PAUSED: "#FFC107",    # 黄色
    EngineState.STOPPING: "#FF5722",  # 深橙
    EngineState.COMPLETED: "#4CAF50", # 绿色
    EngineState.ERROR: "#F44336",     # 红色
}

STATE_NAMES = {
    EngineState.IDLE: "空闲",
    EngineState.LOADING: "加载中",
    EngineState.READY: "就绪",
    EngineState.RUNNING: "运行中",
    EngineState.PAUSED: "已暂停",
    EngineState.STOPPING: "停止中",
    EngineState.COMPLETED: "已完成",
    EngineState.ERROR: "错误",
}

STEP_STATE_ICONS = {
    StepState.IDLE: "⏸️",
    StepState.BUSY: "▶️",
    StepState.END: "✅",
    StepState.FAILED: "❌",
    StepState.PAUSED: "⏸️",
}


class StepStatusIndicator(QWidget):
    """步骤状态指示器"""
    
    def __init__(self, index: int, name: str, parent=None):
        super().__init__(parent)
        self.index = index
        self.name = name
        self._state = "pending"  # pending, running, completed, failed
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        # 序号
        self.index_label = QLabel(f"{self.index + 1}.")
        self.index_label.setFixedWidth(25)
        self.index_label.setFont(FONT_NORMAL)
        layout.addWidget(self.index_label)
        
        # 状态图标
        self.icon_label = QLabel("⬜")
        self.icon_label.setFixedWidth(20)
        layout.addWidget(self.icon_label)
        
        # 名称
        self.name_label = QLabel(self.name)
        self.name_label.setFont(FONT_NORMAL)
        layout.addWidget(self.name_label, 1)
        
        # 进度
        self.progress_label = QLabel("")
        self.progress_label.setFixedWidth(60)
        self.progress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.progress_label)
    
    def set_state(self, state: str, progress: float = 0.0):
        """设置状态
        
        Args:
            state: pending, running, completed, failed
            progress: 进度 (0-1)
        """
        self._state = state
        
        icons = {
            "pending": "⬜",
            "running": "▶️",
            "completed": "✅",
            "failed": "❌",
        }
        self.icon_label.setText(icons.get(state, "⬜"))
        
        if state == "running":
            self.progress_label.setText(f"{progress*100:.0f}%")
            self.setStyleSheet("background-color: #FFF3E0;")  # 浅橙色背景
        elif state == "completed":
            self.progress_label.setText("完成")
            self.setStyleSheet("background-color: #E8F5E9;")  # 浅绿色背景
        elif state == "failed":
            self.progress_label.setText("失败")
            self.setStyleSheet("background-color: #FFEBEE;")  # 浅红色背景
        else:
            self.progress_label.setText("")
            self.setStyleSheet("")


class ExperimentProgressPanel(QWidget):
    """实验进度面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._step_indicators: List[StepStatusIndicator] = []
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === 总体状态 ===
        status_group = QGroupBox("实验状态")
        status_group.setFont(FONT_TITLE)
        status_layout = QVBoxLayout(status_group)
        
        # 状态行
        status_row = QHBoxLayout()
        
        self.state_label = QLabel("空闲")
        self.state_label.setFont(FONT_LARGE)
        self.state_label.setStyleSheet(f"color: {STATE_COLORS[EngineState.IDLE]};")
        status_row.addWidget(self.state_label)
        
        status_row.addStretch()
        
        self.time_label = QLabel("--:--")
        self.time_label.setFont(FONT_TITLE)
        status_row.addWidget(self.time_label)
        
        status_layout.addLayout(status_row)
        
        # 总体进度条
        progress_row = QHBoxLayout()
        progress_row.addWidget(QLabel("总体进度:"))
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        progress_row.addWidget(self.overall_progress, 1)
        
        status_layout.addLayout(progress_row)
        layout.addWidget(status_group)
        
        # === 当前步骤 ===
        step_group = QGroupBox("当前步骤")
        step_group.setFont(FONT_TITLE)
        step_layout = QGridLayout(step_group)
        
        step_layout.addWidget(QLabel("步骤:"), 0, 0)
        self.current_step_label = QLabel("--")
        self.current_step_label.setFont(FONT_TITLE)
        step_layout.addWidget(self.current_step_label, 0, 1)
        
        step_layout.addWidget(QLabel("状态:"), 0, 2)
        self.step_state_label = QLabel("--")
        step_layout.addWidget(self.step_state_label, 0, 3)
        
        step_layout.addWidget(QLabel("进度:"), 1, 0)
        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 100)
        self.step_progress.setValue(0)
        self.step_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                height: 16px;
            }
            QProgressBar::chunk {
                background-color: #FF9800;
                border-radius: 2px;
            }
        """)
        step_layout.addWidget(self.step_progress, 1, 1, 1, 3)
        
        step_layout.addWidget(QLabel("消息:"), 2, 0)
        self.step_message_label = QLabel("--")
        self.step_message_label.setWordWrap(True)
        step_layout.addWidget(self.step_message_label, 2, 1, 1, 3)
        
        layout.addWidget(step_group)
        
        # === 批次信息（配液用）===
        self.batch_group = QGroupBox("批次注入")
        self.batch_group.setFont(FONT_TITLE)
        self.batch_group.setVisible(False)  # 默认隐藏
        batch_layout = QGridLayout(self.batch_group)
        
        batch_layout.addWidget(QLabel("当前批次:"), 0, 0)
        self.batch_label = QLabel("--/--")
        batch_layout.addWidget(self.batch_label, 0, 1)
        
        batch_layout.addWidget(QLabel("正在注入:"), 1, 0)
        self.infusing_label = QLabel("--")
        self.infusing_label.setStyleSheet("color: #FF9800;")
        batch_layout.addWidget(self.infusing_label, 1, 1)
        
        batch_layout.addWidget(QLabel("已完成:"), 2, 0)
        self.completed_label = QLabel("--")
        self.completed_label.setStyleSheet("color: #4CAF50;")
        batch_layout.addWidget(self.completed_label, 2, 1)
        
        layout.addWidget(self.batch_group)
        
        # === 步骤列表预览 ===
        steps_group = QGroupBox("步骤列表")
        steps_group.setFont(FONT_TITLE)
        steps_layout = QVBoxLayout(steps_group)
        
        self.steps_scroll = QScrollArea()
        self.steps_scroll.setWidgetResizable(True)
        self.steps_scroll.setMaximumHeight(200)
        
        self.steps_container = QWidget()
        self.steps_container_layout = QVBoxLayout(self.steps_container)
        self.steps_container_layout.setSpacing(2)
        self.steps_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.steps_scroll.setWidget(self.steps_container)
        steps_layout.addWidget(self.steps_scroll)
        
        layout.addWidget(steps_group)
        layout.addStretch()
    
    def set_steps(self, step_names: List[str]):
        """设置步骤列表"""
        # 清空现有指示器
        for indicator in self._step_indicators:
            indicator.deleteLater()
        self._step_indicators.clear()
        
        # 创建新指示器
        for i, name in enumerate(step_names):
            indicator = StepStatusIndicator(i, name)
            self.steps_container_layout.addWidget(indicator)
            self._step_indicators.append(indicator)
        
        self.steps_container_layout.addStretch()
    
    @Slot(ExperimentProgress)
    def update_progress(self, progress: ExperimentProgress):
        """更新进度显示"""
        # 更新状态
        state_name = STATE_NAMES.get(progress.state, "未知")
        state_color = STATE_COLORS.get(progress.state, "#9E9E9E")
        self.state_label.setText(state_name)
        self.state_label.setStyleSheet(f"color: {state_color};")
        
        # 更新时间
        elapsed = progress.elapsed_seconds
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
        
        # 更新总体进度
        self.overall_progress.setValue(int(progress.overall_progress * 100))
        
        # 更新当前步骤
        if progress.current_step_index >= 0:
            step_num = f"{progress.current_step_index + 1}/{progress.total_steps}"
            step_name = progress.current_step_name or "--"
            self.current_step_label.setText(f"{step_num} {step_name}")
        else:
            self.current_step_label.setText("--")
        
        # 更新步骤状态
        step_state = progress.current_step_state
        if step_state.is_running():
            self.step_state_label.setText("执行中")
            self.step_state_label.setStyleSheet("color: #FF9800;")
        elif step_state.is_completed():
            if step_state.is_success():
                self.step_state_label.setText("完成")
                self.step_state_label.setStyleSheet("color: #4CAF50;")
            else:
                self.step_state_label.setText("失败")
                self.step_state_label.setStyleSheet("color: #F44336;")
        else:
            self.step_state_label.setText("等待")
            self.step_state_label.setStyleSheet("color: #9E9E9E;")
        
        # 更新步骤进度
        self.step_progress.setValue(int(progress.step_progress * 100))
        self.step_message_label.setText(progress.step_message or "--")
        
        # 更新批次信息
        if progress.total_batches > 0:
            self.batch_group.setVisible(True)
            self.batch_label.setText(f"{progress.current_batch}/{progress.total_batches}")
        else:
            self.batch_group.setVisible(False)
        
        # 更新步骤列表指示器
        for i, indicator in enumerate(self._step_indicators):
            if i < progress.current_step_index:
                indicator.set_state("completed")
            elif i == progress.current_step_index:
                indicator.set_state("running", progress.step_progress)
            else:
                indicator.set_state("pending")
    
    def set_batch_info(self, current: int, total: int, 
                       infusing: List[str], completed: List[str]):
        """设置批次信息"""
        self.batch_group.setVisible(total > 0)
        self.batch_label.setText(f"{current}/{total}")
        self.infusing_label.setText(", ".join(infusing) if infusing else "--")
        self.completed_label.setText(", ".join(completed) if completed else "--")
    
    def reset(self):
        """重置面板"""
        self.state_label.setText("空闲")
        self.state_label.setStyleSheet(f"color: {STATE_COLORS[EngineState.IDLE]};")
        self.time_label.setText("--:--")
        self.overall_progress.setValue(0)
        self.current_step_label.setText("--")
        self.step_state_label.setText("--")
        self.step_progress.setValue(0)
        self.step_message_label.setText("--")
        self.batch_group.setVisible(False)
        
        for indicator in self._step_indicators:
            indicator.set_state("pending")

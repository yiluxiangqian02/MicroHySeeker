"""
主窗口 - MicroHySeeker 自动化实验平台
- 12 台泵模型（实际泵形状，显示完整编号，标注溶液类型、原浓度、泵地址）
- 实验过程区域：绘制Inlet/Transfer/Outlet三个泵（实际泵形状），标注泵地址
- 烧杯1改成反应池，烧杯2改成电化学池，显示液体高度变化
- 右上角组合实验进程指示
- 日志和步骤进度不同操作类型显示不同颜色
- 字体统一放大
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QTextEdit, QPushButton, QLabel, QToolBar, QStatusBar,
    QMenuBar, QMenu, QMessageBox, QFileDialog, QFrame, QSpinBox,
    QGroupBox, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt, Slot, QSize, QRectF
from PySide6.QtGui import QAction, QIcon, QFont, QColor, QPainter, QPen, QBrush, QLinearGradient, QPainterPath
from pathlib import Path

from src.models import SystemConfig, Experiment, ProgStep, ProgramStepType
from src.engine.runner import ExperimentRunner


# 全局字体设置
FONT_NORMAL = QFont("Microsoft YaHei", 11)
FONT_TITLE = QFont("Microsoft YaHei", 12, QFont.Bold)
FONT_SMALL = QFont("Microsoft YaHei", 9)

# 操作类型颜色映射
STEP_TYPE_COLORS = {
    ProgramStepType.TRANSFER: "#2196F3",   # 蓝色 - 移液
    ProgramStepType.PREP_SOL: "#4CAF50",   # 绿色 - 配液
    ProgramStepType.FLUSH: "#FF9800",      # 橙色 - 冲洗
    ProgramStepType.ECHEM: "#9C27B0",      # 紫色 - 电化学
    ProgramStepType.BLANK: "#607D8B",      # 灰色 - 空白
    ProgramStepType.EVACUATE: "#795548",   # 棕色 - 排空
}

STEP_TYPE_NAMES = {
    ProgramStepType.TRANSFER: "移液",
    ProgramStepType.PREP_SOL: "配液",
    ProgramStepType.FLUSH: "冲洗",
    ProgramStepType.ECHEM: "电化学",
    ProgramStepType.BLANK: "空白",
    ProgramStepType.EVACUATE: "排空",
}


class PumpDiagramWidget(QFrame):
    """泵状态指示 - 1行6个共2行布局，12个泵完整显示"""
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.pump_states = [False] * 12  # 泵运行状态
        self.setMinimumSize(600, 150)
        self.setMaximumHeight(180)
    
    def update_config(self, config: SystemConfig):
        self.config = config
        self.update()
    
    def set_pump_running(self, pump_id: int, running: bool):
        if 1 <= pump_id <= 12:
            self.pump_states[pump_id - 1] = running
            self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        pump_w, pump_h = 80, 35
        spacing_x = 10
        spacing_y = 15
        start_x = 10
        start_y = 10
        
        # 绘制1行6个共2行布局的泵
        for i in range(12):
            row = i // 6
            col = i % 6
            
            x = start_x + col * (pump_w + spacing_x)
            y = start_y + row * (pump_h + 30 + spacing_y)
            
            self._draw_pump(painter, x, y, pump_w, pump_h, i + 1)
    
    def _draw_pump(self, painter: QPainter, x: int, y: int, w: int, h: int, pump_id: int):
        """绘制单个泵 - 紧凑形状，信息在下方"""
        is_running = self.pump_states[pump_id - 1]
        
        # 泵主体
        body_rect = QRectF(x, y, w, h)
        
        # 渐变背景
        gradient = QLinearGradient(x, y, x, y + h)
        if is_running:
            gradient.setColorAt(0, QColor("#81C784"))
            gradient.setColorAt(1, QColor("#4CAF50"))
        else:
            gradient.setColorAt(0, QColor("#E0E0E0"))
            gradient.setColorAt(1, QColor("#BDBDBD"))
        
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(body_rect, 4, 4)
        
        # 泵滚轮 (圆形)
        roller_x = x + w // 2
        roller_y = y + h // 2
        roller_r = 8
        painter.setBrush(QBrush(QColor("#757575")))
        painter.drawEllipse(roller_x - roller_r, roller_y - roller_r, roller_r * 2, roller_r * 2)
        
        # 泵编号 (在泵主体内)
        painter.setPen(Qt.white)
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.drawText(body_rect, Qt.AlignCenter, str(pump_id))
        
        # 获取泵配置信息
        solution_name = ""
        for ch in self.config.dilution_channels:
            if ch.pump_address == pump_id:
                solution_name = ch.solution_name[:6]  # 限制长度
                break
        
        # 在泵下方显示信息
        painter.setPen(Qt.black)
        painter.setFont(QFont("Microsoft YaHei", 8))
        
        info_y = y + h + 3
        if solution_name:
            painter.drawText(x, info_y, w, 15, Qt.AlignCenter, solution_name)
        else:
            painter.drawText(x, info_y, w, 15, Qt.AlignCenter, f"泵{pump_id}")


class ExperimentProcessWidget(QFrame):
    """实验过程区域 - 绘制Inlet/Transfer/Outlet泵、反应池、电化学池，液体高度"""
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.inlet_pump = 0
        self.transfer_pump = 0
        self.outlet_pump = 0
        self.inlet_active = False
        self.transfer_active = False
        self.outlet_active = False
        self.tank1_level = 0.3  # 反应池液位 (0-1)
        self.tank2_level = 0.5  # 电化学池液位 (0-1)
        self.combo_progress = "0/0"  # 组合实验进程
        self.setMinimumSize(600, 200)
        self.setMaximumHeight(220)
    
    def update_config(self, config: SystemConfig):
        self.config = config
        self._update_pump_ids()
        self.update()
    
    def _update_pump_ids(self):
        """从配置更新泵ID"""
        self.inlet_pump = 0
        self.transfer_pump = 0
        self.outlet_pump = 0
        for ch in self.config.flush_channels:
            work_type = getattr(ch, 'work_type', 'Transfer')
            if work_type == 'Inlet':
                self.inlet_pump = ch.pump_address
            elif work_type == 'Transfer':
                self.transfer_pump = ch.pump_address
            elif work_type == 'Outlet':
                self.outlet_pump = ch.pump_address
    
    def set_pump_states(self, inlet_active: bool, transfer_active: bool, outlet_active: bool):
        self.inlet_active = inlet_active
        self.transfer_active = transfer_active
        self.outlet_active = outlet_active
        self.update()
    
    def set_tank_levels(self, tank1: float, tank2: float):
        self.tank1_level = max(0, min(1, tank1))
        self.tank2_level = max(0, min(1, tank2))
        self.update()
    
    def set_combo_progress(self, current: int, total: int):
        self.combo_progress = f"{current}/{total}"
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # 组合实验进程指示 (右上角)
        painter.setPen(Qt.black)
        painter.setFont(FONT_TITLE)
        painter.drawText(w - 180, 5, 170, 20, Qt.AlignRight, f"组合进程: {self.combo_progress}")
        
        # === 绘制Inlet泵 ===
        inlet_x, inlet_y = 20, 70
        self._draw_pump_shape(painter, inlet_x, inlet_y, 55, 35, "Inlet", 
                              self.inlet_pump, self.inlet_active)
        
        # === 绘制反应池 ===
        tank1_x, tank1_y = 120, 50
        tank_w, tank_h = 80, 110
        self._draw_tank(painter, tank1_x, tank1_y, tank_w, tank_h, "反应池", 
                        self.tank1_level, QColor("#BBDEFB"))
        
        # Inlet到反应池的管道
        pipe_color = QColor("#4CAF50") if self.inlet_active else QColor("#9E9E9E")
        painter.setPen(QPen(pipe_color, 3))
        painter.drawLine(inlet_x + 55, inlet_y + 17, tank1_x, tank1_y + 25)
        
        # === 绘制Transfer泵 ===
        transfer_x, transfer_y = 240, 70
        self._draw_pump_shape(painter, transfer_x, transfer_y, 55, 35, "Transfer",
                              self.transfer_pump, self.transfer_active)
        
        # 反应池到Transfer泵的管道
        pipe_color = QColor("#2196F3") if self.transfer_active else QColor("#9E9E9E")
        painter.setPen(QPen(pipe_color, 3))
        painter.drawLine(tank1_x + tank_w, tank1_y + 55, transfer_x, transfer_y + 17)
        
        # === 绘制电化学池 ===
        tank2_x, tank2_y = 340, 50
        self._draw_tank(painter, tank2_x, tank2_y, tank_w, tank_h, "电化学池",
                        self.tank2_level, QColor("#E1BEE7"))
        
        # Transfer泵到电化学池的管道
        painter.setPen(QPen(pipe_color, 3))
        painter.drawLine(transfer_x + 55, transfer_y + 17, tank2_x, tank2_y + 25)
        
        # === 绘制Outlet泵 ===
        outlet_x, outlet_y = 460, 70
        self._draw_pump_shape(painter, outlet_x, outlet_y, 55, 35, "Outlet",
                              self.outlet_pump, self.outlet_active)
        
        # 电化学池到Outlet泵的管道
        pipe_color = QColor("#FF9800") if self.outlet_active else QColor("#9E9E9E")
        painter.setPen(QPen(pipe_color, 3))
        painter.drawLine(tank2_x + tank_w, tank2_y + 55, outlet_x, outlet_y + 17)
        
        # Outlet到废液的管道
        painter.drawLine(outlet_x + 55, outlet_y + 17, outlet_x + 85, outlet_y + 17)
        
        # 废液标识
        painter.setFont(FONT_SMALL)
        painter.setPen(Qt.black)
        painter.drawText(outlet_x + 55, outlet_y + 35, "废液")
    
    def _draw_pump_shape(self, painter: QPainter, x: int, y: int, w: int, h: int,
                         name: str, pump_id: int, is_active: bool):
        """绘制泵的实际形状"""
        # 泵主体
        gradient = QLinearGradient(x, y, x, y + h)
        if is_active:
            gradient.setColorAt(0, QColor("#81C784"))
            gradient.setColorAt(1, QColor("#4CAF50"))
        else:
            gradient.setColorAt(0, QColor("#E0E0E0"))
            gradient.setColorAt(1, QColor("#BDBDBD"))
        
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(QRectF(x, y, w, h), 4, 4)
        
        # 滚轮
        roller_x = x + w // 2
        roller_y = y + h // 2
        painter.setBrush(QBrush(QColor("#757575")))
        painter.drawEllipse(roller_x - 6, roller_y - 6, 12, 12)
        
        # 名称和泵地址
        painter.setPen(Qt.black)
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.drawText(x, y - 12, w, 12, Qt.AlignCenter, name)
        if pump_id > 0:
            painter.drawText(x, y + h + 2, w, 12, Qt.AlignCenter, f"泵{pump_id}")
    
    def _draw_tank(self, painter: QPainter, x: int, y: int, w: int, h: int,
                   name: str, level: float, liquid_color: QColor):
        """绘制烧杯/池子，带液位"""
        # 容器轮廓 (梯形)
        path = QPainterPath()
        path.moveTo(x + 10, y)
        path.lineTo(x + w - 10, y)
        path.lineTo(x + w, y + h)
        path.lineTo(x, y + h)
        path.closeSubpath()
        
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(QBrush(QColor("#FAFAFA")))
        painter.drawPath(path)
        
        # 液体 (根据液位)
        if level > 0:
            liquid_h = int(h * level)
            liquid_y = y + h - liquid_h
            
            liquid_path = QPainterPath()
            # 计算液位处的宽度
            ratio = liquid_h / h
            left_offset = 10 * (1 - ratio)
            right_offset = 10 * (1 - ratio)
            
            liquid_path.moveTo(x + left_offset, liquid_y)
            liquid_path.lineTo(x + w - right_offset, liquid_y)
            liquid_path.lineTo(x + w, y + h)
            liquid_path.lineTo(x, y + h)
            liquid_path.closeSubpath()
            
            painter.setBrush(QBrush(liquid_color))
            painter.drawPath(liquid_path)
        
        # 容器名称
        painter.setPen(Qt.black)
        painter.setFont(FONT_SMALL)
        painter.drawText(x, y + h + 5, w, 20, Qt.AlignCenter, name)


class MainWindow(QMainWindow):
    """
    主窗口
    
    === 后端接口 ===
    1. RS485Wrapper: start_pump, stop_pump, stop_all
    2. CHIWrapper: run_cv, run_lsv, run_it, get_data, stop
    3. ExperimentRunner: run_experiment, stop, pause, resume
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MicroHySeeker - 自动化实验平台")
        self.setGeometry(100, 100, 1550, 1000)
        self.setFont(FONT_NORMAL)
        
        # 加载配置
        self.config_file = Path("./config/system.json")
        self.config = SystemConfig.load_from_file(str(self.config_file))
        self.config.initialize_default_pumps()
        
        # 当前实验
        self.single_experiment: Experiment = None
        self.combo_experiments: list = []
        self.combo_params: list = []
        self.current_combo_index = 0
        self.total_combo_count = 0
        
        # 运行引擎
        self.runner = ExperimentRunner()
        self.runner.step_started.connect(self._on_step_started)
        self.runner.step_finished.connect(self._on_step_finished)
        self.runner.log_message.connect(self._on_log_message)
        self.runner.experiment_finished.connect(self._on_experiment_finished)
        
        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()
        
        self.log_message("系统已启动，欢迎使用 MicroHySeeker", "info")
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        menubar.setFont(FONT_NORMAL)
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        single_action = QAction("单次实验(&S)", self)
        single_action.triggered.connect(self._on_single_exp)
        file_menu.addAction(single_action)
        
        combo_action = QAction("组合实验(&C)", self)
        combo_action.triggered.connect(self._on_combo_exp)
        file_menu.addAction(combo_action)
        
        file_menu.addSeparator()
        
        load_action = QAction("载入实验(&L)", self)
        load_action.triggered.connect(self._on_load_exp)
        file_menu.addAction(load_action)
        
        save_action = QAction("保存实验(&V)", self)
        save_action.triggered.connect(self._on_save_exp)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        
        config_action = QAction("系统配置(&S)", self)
        config_action.triggered.connect(self._on_config)
        tools_menu.addAction(config_action)
        
        manual_action = QAction("手动控制(&M)", self)
        manual_action.triggered.connect(self._on_manual)
        tools_menu.addAction(manual_action)
        
        calibrate_action = QAction("泵校准(&C)", self)
        calibrate_action.triggered.connect(self._on_calibrate)
        tools_menu.addAction(calibrate_action)
        
        tools_menu.addSeparator()
        
        prep_action = QAction("配制溶液(&P)", self)
        prep_action.triggered.connect(self._on_prep_solution)
        tools_menu.addAction(prep_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(28, 28))
        toolbar.setFont(FONT_NORMAL)
        self.addToolBar(toolbar)
        
        single_btn = QAction("单次实验", self)
        single_btn.triggered.connect(self._on_single_exp)
        toolbar.addAction(single_btn)
        
        combo_btn = QAction("组合实验", self)
        combo_btn.triggered.connect(self._on_combo_exp)
        toolbar.addAction(combo_btn)
        
        toolbar.addSeparator()
        
        load_btn = QAction("载入实验", self)
        load_btn.triggered.connect(self._on_load_exp)
        toolbar.addAction(load_btn)
        
        save_btn = QAction("保存实验", self)
        save_btn.triggered.connect(self._on_save_exp)
        toolbar.addAction(save_btn)
        
        toolbar.addSeparator()
        
        prep_btn = QAction("配制溶液", self)
        prep_btn.triggered.connect(self._on_prep_solution)
        toolbar.addAction(prep_btn)
        
        config_btn = QAction("系统设置", self)
        config_btn.triggered.connect(self._on_config)
        toolbar.addAction(config_btn)
        
        calibrate_btn = QAction("泵校准", self)
        calibrate_btn.triggered.connect(self._on_calibrate)
        toolbar.addAction(calibrate_btn)
        
        manual_btn = QAction("手动控制", self)
        manual_btn.triggered.connect(self._on_manual)
        toolbar.addAction(manual_btn)
    
    def _create_central_widget(self):
        """创建中央区域"""
        central = QWidget()
        main_layout = QVBoxLayout(central)
        
        # 上部分割器
        top_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：泵装填栏 + 实验过程
        left_frame = QFrame()
        left_frame.setFrameStyle(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_frame)
        
        # 泵状态指示
        pumps_group = QGroupBox("泵状态指示")
        pumps_group.setFont(FONT_TITLE)
        pumps_layout = QVBoxLayout(pumps_group)
        self.pump_diagram = PumpDiagramWidget(self.config)
        pumps_layout.addWidget(self.pump_diagram)
        left_layout.addWidget(pumps_group)
        
        # 实验过程
        process_group = QGroupBox("实验过程")
        process_group.setFont(FONT_TITLE)
        process_layout = QVBoxLayout(process_group)
        self.process_widget = ExperimentProcessWidget(self.config)
        process_layout.addWidget(self.process_widget)
        left_layout.addWidget(process_group)
        
        top_splitter.addWidget(left_frame)
        
        # 右侧：步骤进度 + 日志
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 步骤进度
        step_group = QGroupBox("步骤进度")
        step_group.setFont(FONT_TITLE)
        step_layout = QVBoxLayout(step_group)
        self.step_list = QListWidget()
        self.step_list.setFont(FONT_NORMAL)
        self.step_list.setMaximumHeight(220)
        step_layout.addWidget(self.step_list)
        right_layout.addWidget(step_group)
        
        # 运行日志 - 白色背景
        log_group = QGroupBox("运行日志")
        log_group.setFont(FONT_TITLE)
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
            }
        """)
        log_layout.addWidget(self.log_text)
        right_layout.addWidget(log_group)
        
        top_splitter.addWidget(right_widget)
        top_splitter.setSizes([850, 450])
        
        main_layout.addWidget(top_splitter, stretch=1)
        
        # 下部：控制按钮
        self._create_control_buttons(main_layout)
        
        self.setCentralWidget(central)
    
    def _create_control_buttons(self, parent_layout):
        """创建控制按钮区"""
        btn_frame = QGroupBox("实验控制")
        btn_frame.setFont(FONT_TITLE)
        btn_layout = QHBoxLayout(btn_frame)
        
        # 单次实验
        single_group = QGroupBox("单次实验")
        single_layout = QHBoxLayout(single_group)
        
        self.btn_run_single = QPushButton("开始单次实验")
        self.btn_run_single.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 18px; font-size: 12px;")
        self.btn_run_single.clicked.connect(self._on_run_single)
        single_layout.addWidget(self.btn_run_single)
        
        btn_layout.addWidget(single_group)
        
        # 组合实验
        combo_group = QGroupBox("组合实验")
        combo_layout = QHBoxLayout(combo_group)
        
        self.btn_run_combo = QPushButton("开始组合实验")
        self.btn_run_combo.setStyleSheet("background-color: #2196F3; color: white; padding: 10px 18px; font-size: 12px;")
        self.btn_run_combo.clicked.connect(self._on_run_combo)
        combo_layout.addWidget(self.btn_run_combo)
        
        self.btn_prev = QPushButton("上一个")
        self.btn_prev.clicked.connect(self._on_prev_combo)
        combo_layout.addWidget(self.btn_prev)
        
        self.btn_next = QPushButton("下一个")
        self.btn_next.clicked.connect(self._on_next_combo)
        combo_layout.addWidget(self.btn_next)
        
        combo_layout.addWidget(QLabel("跳至:"))
        self.jump_spin = QSpinBox()
        self.jump_spin.setRange(1, 1000)
        self.jump_spin.setFont(FONT_NORMAL)
        combo_layout.addWidget(self.jump_spin)
        
        self.btn_jump = QPushButton("跳转")
        self.btn_jump.clicked.connect(self._on_jump_combo)
        combo_layout.addWidget(self.btn_jump)
        
        # 复位组合实验
        self.btn_reset_combo = QPushButton("复位组合实验进程")
        self.btn_reset_combo.setStyleSheet("padding: 10px 12px; font-size: 11px;")
        self.btn_reset_combo.clicked.connect(self._on_reset_combo)
        combo_layout.addWidget(self.btn_reset_combo)
        
        # 列出参数
        self.btn_list_params = QPushButton("列出参数")
        self.btn_list_params.setStyleSheet("padding: 10px 12px; font-size: 11px;")
        self.btn_list_params.clicked.connect(self._on_list_params)
        combo_layout.addWidget(self.btn_list_params)
        
        btn_layout.addWidget(combo_group)
        
        # 停止按钮
        self.btn_stop = QPushButton("停止实验")
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; padding: 10px 18px; font-size: 12px;")
        self.btn_stop.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.btn_stop)
        
        parent_layout.addWidget(btn_frame)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.status_bar.setFont(FONT_NORMAL)
        self.setStatusBar(self.status_bar)
        
        self.status_rs485 = QLabel("RS485: 未连接")
        self.status_chi = QLabel("电化学仪: 未连接")
        self.status_exp = QLabel("状态: 就绪")
        
        self.status_bar.addWidget(self.status_rs485)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addWidget(self.status_chi)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addPermanentWidget(self.status_exp)
    
    # === 菜单事件 ===
    
    def _on_single_exp(self):
        """编辑单次实验"""
        from src.dialogs.program_editor import ProgramEditorDialog
        
        if not self.single_experiment:
            self.single_experiment = Experiment(exp_id="single_001", exp_name="单次实验")
        
        dialog = ProgramEditorDialog(self.config, self.single_experiment, self)
        dialog.program_saved.connect(self._on_program_saved)
        dialog.exec()
    
    def _on_combo_exp(self):
        """编辑组合实验"""
        if not self.single_experiment or not self.single_experiment.steps:
            QMessageBox.warning(self, "警告", "请先编辑单次实验程序")
            return
        
        from src.dialogs.combo_exp_editor import ComboExpEditorDialog
        dialog = ComboExpEditorDialog(self.single_experiment, self.config, self)
        dialog.combo_saved.connect(self._on_combo_saved)
        dialog.exec()
    
    def _on_load_exp(self):
        """载入实验"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "载入实验", "./experiments", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.single_experiment = Experiment.from_json_str(f.read())
                self._refresh_step_list()
                self.log_message(f"已载入实验: {file_path}", "info")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"载入失败: {e}")
    
    def _on_save_exp(self):
        """保存实验"""
        if not self.single_experiment:
            QMessageBox.warning(self, "警告", "没有可保存的实验")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存实验", "./experiments", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.single_experiment.to_json_str())
                self.log_message(f"实验已保存: {file_path}", "info")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")
    
    def _on_config(self):
        """系统配置"""
        from src.dialogs.config_dialog import ConfigDialog
        dialog = ConfigDialog(self.config, self)
        dialog.config_saved.connect(self._on_config_saved)
        dialog.exec()
    
    def _on_manual(self):
        """手动控制"""
        from src.dialogs.manual_control import ManualControlDialog
        dialog = ManualControlDialog(self.config, self)
        dialog.exec()
    
    def _on_calibrate(self):
        """泵校准"""
        from src.dialogs.calibrate_dialog import CalibrateDialog
        dialog = CalibrateDialog(self.config, self)
        dialog.exec()
    
    def _on_prep_solution(self):
        """配制溶液"""
        from src.dialogs.prep_solution import PrepSolutionDialog
        dialog = PrepSolutionDialog(self.config, self)
        dialog.exec()
    
    def _on_about(self):
        """关于"""
        QMessageBox.about(
            self, "关于 MicroHySeeker",
            "MicroHySeeker 自动化实验平台\n\n"
            "版本: 1.0.0\n"
            "用于高通量电化学实验的自动化控制\n\n"
            "© 2024-2026"
        )
    
    # === 实验控制 ===
    
    def _on_run_single(self):
        """运行单次实验"""
        if not self.single_experiment or not self.single_experiment.steps:
            QMessageBox.warning(self, "警告", "请先编辑单次实验程序")
            return
        
        self._refresh_step_list()
        self.runner.run_experiment(self.single_experiment)
        self.status_exp.setText("状态: 运行中")
        self.log_message("开始运行单次实验...", "info")
    
    def _on_run_combo(self):
        """运行组合实验"""
        if not self.combo_params:
            QMessageBox.warning(self, "警告", "请先编辑组合实验程序")
            return
        
        self.current_combo_index = 0
        self.total_combo_count = len(self.combo_params)
        self.process_widget.set_combo_progress(1, self.total_combo_count)
        self.log_message(f"开始运行组合实验，共 {self.total_combo_count} 组", "info")
    
    def _on_stop(self):
        """停止实验"""
        self.runner.stop()
        self.status_exp.setText("状态: 已停止")
        self.log_message("实验已停止", "warning")
        
        # 重置泵状态
        for i in range(12):
            self.pump_diagram.set_pump_running(i + 1, False)
        self.process_widget.set_pump_states(False, False, False)
    
    def _on_prev_combo(self):
        """上一个组合实验"""
        if self.current_combo_index > 0:
            self.current_combo_index -= 1
            self.process_widget.set_combo_progress(self.current_combo_index + 1, self.total_combo_count)
            self.log_message(f"切换到组合实验 {self.current_combo_index + 1}", "info")
    
    def _on_next_combo(self):
        """下一个组合实验"""
        if self.current_combo_index < len(self.combo_params) - 1:
            self.current_combo_index += 1
            self.process_widget.set_combo_progress(self.current_combo_index + 1, self.total_combo_count)
            self.log_message(f"切换到组合实验 {self.current_combo_index + 1}", "info")
    
    def _on_jump_combo(self):
        """跳转到指定组合实验"""
        target = self.jump_spin.value() - 1
        if 0 <= target < len(self.combo_params):
            self.current_combo_index = target
            self.process_widget.set_combo_progress(target + 1, self.total_combo_count)
            self.log_message(f"跳转到组合实验 {target + 1}", "info")
    
    def _on_reset_combo(self):
        """复位组合实验进程"""
        self.current_combo_index = 0
        self.process_widget.set_combo_progress(1, self.total_combo_count)
        self.log_message("组合实验进程已复位到第 1 组", "info")
    
    def _on_list_params(self):
        """列出当前参数"""
        if not self.combo_params:
            QMessageBox.information(self, "参数列表", "没有组合实验参数")
            return
        
        if self.current_combo_index < len(self.combo_params):
            params = self.combo_params[self.current_combo_index]
            param_str = "\n".join([f"{k}: {v}" for k, v in params.items()])
            QMessageBox.information(
                self, f"组合实验 {self.current_combo_index + 1} 参数",
                param_str if param_str else "无参数"
            )
    
    # === 回调 ===
    
    def _on_program_saved(self, experiment: Experiment):
        """程序保存回调"""
        self.single_experiment = experiment
        self._refresh_step_list()
        self.log_message(f"程序已更新: {experiment.exp_name}", "info")
    
    def _on_combo_saved(self, combo_params: list):
        """组合实验保存回调"""
        self.combo_params = combo_params
        self.total_combo_count = len(combo_params)
        self.process_widget.set_combo_progress(1, self.total_combo_count)
        self.log_message(f"已生成 {len(combo_params)} 组组合实验", "info")
    
    def _on_config_saved(self, config: SystemConfig):
        """配置保存回调"""
        self.config = config
        self.pump_diagram.update_config(config)
        self.process_widget.update_config(config)
        self.log_message("系统配置已更新", "info")
    
    def _refresh_step_list(self):
        """刷新步骤列表 - 中文显示，不同类型不同颜色"""
        self.step_list.clear()
        if self.single_experiment:
            for i, step in enumerate(self.single_experiment.steps):
                type_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
                color = STEP_TYPE_COLORS.get(step.step_type, "#000000")
                
                item = QListWidgetItem(f"[{i+1}] {type_name} - {step.step_id}")
                item.setForeground(QColor(color))
                self.step_list.addItem(item)
    
    def log_message(self, msg: str, msg_type: str = "info"):
        """添加日志 - 不同类型不同颜色"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 根据类型设置颜色
        color_map = {
            "info": "#000000",      # 黑色
            "success": "#4CAF50",   # 绿色
            "warning": "#FF9800",   # 橙色
            "error": "#f44336",     # 红色
            "transfer": "#2196F3",  # 蓝色 - 移液
            "prep_sol": "#4CAF50",  # 绿色 - 配液
            "flush": "#FF9800",     # 橙色 - 冲洗
            "echem": "#9C27B0",     # 紫色 - 电化学
            "blank": "#607D8B",     # 灰色 - 空白
        }
        color = color_map.get(msg_type, "#000000")
        
        self.log_text.append(f'<span style="color:{color}; font-size:11px;">[{timestamp}] {msg}</span>')
    
    @Slot(str)
    def _on_log_message(self, msg: str):
        """接收引擎日志"""
        self.log_message(msg, "info")
    
    @Slot(int, str)
    def _on_step_started(self, index: int, step_id: str):
        """步骤开始"""
        if index < self.step_list.count():
            self.step_list.setCurrentRow(index)
        
        # 确定步骤类型并显示对应颜色
        if self.single_experiment and index < len(self.single_experiment.steps):
            step = self.single_experiment.steps[index]
            type_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
            msg_type = step.step_type.value if hasattr(step.step_type, 'value') else "info"
            self.log_message(f"步骤 {index+1} 开始: [{type_name}] {step_id}", msg_type)
    
    @Slot(int, str, bool)
    def _on_step_finished(self, index: int, step_id: str, success: bool):
        """步骤完成"""
        status = "成功" if success else "失败"
        msg_type = "success" if success else "error"
        self.log_message(f"步骤 {index+1} {status}: {step_id}", msg_type)
    
    @Slot(bool)
    def _on_experiment_finished(self, success: bool):
        """实验完成"""
        status = "成功完成" if success else "异常结束"
        self.status_exp.setText(f"状态: {status}")
        msg_type = "success" if success else "error"
        self.log_message(f"实验{status}", msg_type)
        
        # 重置泵状态
        for i in range(12):
            self.pump_diagram.set_pump_running(i + 1, False)
        self.process_widget.set_pump_states(False, False, False)

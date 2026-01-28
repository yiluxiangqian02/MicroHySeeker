"""
主窗口 - 实验平台主界面
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QTextEdit, QMenuBar,
    QMenu, QMessageBox, QFileDialog, QSplitter, QStatusBar
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QAction, QColor, QFont
from pathlib import Path

import pyqtgraph as pg

from src.models import SystemConfig, Experiment, ProgStep
from src.dialogs.config_dialog import ConfigDialog
from src.dialogs.manual_control import ManualControlDialog
from src.dialogs.calibrate_dialog import CalibrateDialog
from src.dialogs.program_editor import ProgramEditorDialog
from src.engine.runner import ExperimentRunner


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MicroHySeeker - 自动化实验平台")
        self.setGeometry(0, 0, 1600, 900)
        
        # 加载配置
        self.config_file = Path("./config/system.json")
        self.config = SystemConfig.load_from_file(str(self.config_file))
        self.config.initialize_default_pumps()
        
        # 当前实验
        self.current_experiment: Experiment = None
        
        # 运行引擎
        self.runner = ExperimentRunner()
        self.runner.step_started.connect(self._on_step_started)
        self.runner.step_finished.connect(self._on_step_finished)
        self.runner.log_message.connect(self._on_log_message)
        self.runner.experiment_finished.connect(self._on_experiment_finished)
        
        self._init_ui()
        self._create_menu()
    
    def _init_ui(self):
        """初始化主 UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧：步骤列表
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("实验步骤:"))
        
        self.step_list = QListWidget()
        left_layout.addWidget(self.step_list)
        
        # 步骤控制按钮
        step_ctrl_layout = QHBoxLayout()
        
        run_single_btn = QPushButton("运行")
        run_single_btn.clicked.connect(self._on_run_single)
        step_ctrl_layout.addWidget(run_single_btn)
        
        stop_btn = QPushButton("停止")
        stop_btn.clicked.connect(self._on_stop)
        step_ctrl_layout.addWidget(stop_btn)
        
        left_layout.addLayout(step_ctrl_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        
        # 右侧：日志 + 绘图区（上下分割）
        right_splitter = QSplitter(Qt.Vertical)
        
        # 绘图区
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', '电流', units='μA')
        self.plot_widget.setLabel('bottom', '时间', units='s')
        self.plot_widget.setTitle('电化学数据 (CHIData)')
        self.plot_item = self.plot_widget.plot(pen='g')
        right_splitter.addWidget(self.plot_widget)
        
        # 日志区
        log_label = QLabel("执行日志:")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        # 设置日志字体颜色
        self.log_text.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #00FF00; font-family: 'Courier New'; }"
        )
        
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_text)
        
        right_splitter.addWidget(log_widget)
        right_splitter.setSizes([400, 300])
        
        # 主分割
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([300, 1300])
        
        main_layout.addWidget(main_splitter)
        central_widget.setLayout(main_layout)
    
    def _create_menu(self):
        """创建菜单"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_exp_action = QAction("新建实验", self)
        new_exp_action.triggered.connect(self._on_new_experiment)
        file_menu.addAction(new_exp_action)
        
        open_exp_action = QAction("打开实验", self)
        open_exp_action.triggered.connect(self._on_open_experiment)
        file_menu.addAction(open_exp_action)
        
        save_exp_action = QAction("保存实验", self)
        save_exp_action.triggered.connect(self._on_save_experiment)
        file_menu.addAction(save_exp_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tool_menu = menubar.addMenu("工具")
        
        config_action = QAction("系统配置", self)
        config_action.triggered.connect(self._on_config)
        tool_menu.addAction(config_action)
        
        manual_action = QAction("手动控制", self)
        manual_action.triggered.connect(self._on_manual_control)
        tool_menu.addAction(manual_action)
        
        calibrate_action = QAction("泵校准", self)
        calibrate_action.triggered.connect(self._on_calibrate)
        tool_menu.addAction(calibrate_action)
        
        # 实验菜单
        exp_menu = menubar.addMenu("实验")
        
        edit_action = QAction("编辑程序", self)
        edit_action.triggered.connect(self._on_edit_program)
        exp_menu.addAction(edit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.status_label = QLabel("就绪")
        self.statusBar.addWidget(self.status_label)
    
    def log_message(self, msg: str):
        """添加日志"""
        self.log_text.append(msg)
    
    @Slot(str)
    def _on_log_message(self, msg: str):
        """接收引擎日志"""
        self.log_message(msg)
    
    @Slot(int, str)
    def _on_step_started(self, index: int, step_id: str):
        """步骤开始"""
        self.step_list.setCurrentRow(index)
    
    @Slot(int, str, bool)
    def _on_step_finished(self, index: int, step_id: str, success: bool):
        """步骤完成"""
        pass
    
    @Slot(bool)
    def _on_experiment_finished(self, success: bool):
        """实验完成"""
        self.status_label.setText("实验完成" if success else "实验失败")
    
    def _refresh_step_list(self):
        """刷新步骤列表"""
        self.step_list.clear()
        if self.current_experiment:
            for i, step in enumerate(self.current_experiment.steps):
                item = QListWidgetItem(f"[{i}] {step.step_type.value}")
                self.step_list.addItem(item)
    
    def _on_new_experiment(self):
        """新建实验"""
        self.current_experiment = Experiment(exp_id="exp_001", exp_name="新实验")
        self._refresh_step_list()
        self.log_message("[实验] 新建实验")
    
    def _on_open_experiment(self):
        """打开实验"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开实验", "./experiments", "JSON (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    exp_data = Experiment.from_json_str(f.read())
                self.current_experiment = exp_data
                self._refresh_step_list()
                self.log_message(f"[实验] 已打开: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开文件失败: {e}")
    
    def _on_save_experiment(self):
        """保存实验"""
        if not self.current_experiment:
            QMessageBox.warning(self, "警告", "没有要保存的实验")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存实验", "./experiments", "JSON (*.json)"
        )
        if file_path:
            try:
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.current_experiment.to_json_str())
                self.log_message(f"[实验] 已保存: {file_path}")
                QMessageBox.information(self, "成功", "实验已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")
    
    def _on_config(self):
        """系统配置"""
        dialog = ConfigDialog(self.config, self)
        if dialog.exec() == dialog.Accepted:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config.save_to_file(str(self.config_file))
            self.log_message("[配置] 系统配置已保存")
    
    def _on_manual_control(self):
        """手动控制"""
        pump_addrs = [p.address for p in self.config.pumps]
        dialog = ManualControlDialog(pump_addrs, self)
        dialog.exec()
    
    def _on_calibrate(self):
        """校准"""
        dialog = CalibrateDialog(self.config, self)
        if dialog.exec() == dialog.Accepted:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config.save_to_file(str(self.config_file))
            self.log_message("[校准] 校准数据已保存")
    
    def _on_edit_program(self):
        """编辑程序"""
        if not self.current_experiment:
            self.current_experiment = Experiment(exp_id="exp_001", exp_name="实验_001")
        
        dialog = ProgramEditorDialog(self.config, self.current_experiment, self)
        if dialog.exec() == dialog.Accepted:
            self._refresh_step_list()
            self.log_message("[程序] 程序已编辑")
    
    def _on_run_single(self):
        """运行单个实验"""
        if not self.current_experiment or not self.current_experiment.steps:
            QMessageBox.warning(self, "警告", "没有步骤可运行")
            return
        
        self.status_label.setText("运行中...")
        self.log_message(f"[运行] 开始执行实验: {self.current_experiment.exp_name}")
        self.runner.run_experiment(self.current_experiment)
    
    def _on_stop(self):
        """停止运行"""
        self.runner.stop()
        self.status_label.setText("已停止")
        self.log_message("[运行] 实验已停止")
    
    def _on_about(self):
        """关于"""
        QMessageBox.information(
            self, 
            "关于",
            "MicroHySeeker v1.0\n自动化实验平台\n基于 PySide6 和 pyqtgraph"
        )
    
    def closeEvent(self, event):
        """关闭事件"""
        self.runner.stop()
        event.accept()

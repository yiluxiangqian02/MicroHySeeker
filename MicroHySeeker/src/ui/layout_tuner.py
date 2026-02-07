"""
布局微调器 - 实时调节实验过程图中每个形状和管道的位置/尺寸
右键点击"实验过程"区域即可打开
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDoubleSpinBox, QSpinBox, QLabel, QComboBox,
    QPushButton, QWidget, QScrollArea, QApplication,
    QTabWidget, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# ── 参数分组与中文标签 ──
# 每个 entry: (参数key, 中文标签, 类型hint)
# 类型: "int", "float", "mode" (管道模式下拉框)

GROUPS = [
    ("🌐 全局", [
        ("margin_x",           "水平边距 (px)",       "int"),
        ("margin_y",           "垂直边距 (px)",       "int"),
        ("col_count",          "网格列数",            "int"),
        ("def_pump_w_ratio",   "泵默认宽度比例",      "float"),
        ("def_pump_hw_ratio",  "泵默认高宽比",        "float"),
        ("def_tank_w_ratio",   "烧杯默认宽度比例",    "float"),
        ("def_tank_hw_ratio",  "烧杯默认高宽比",      "float"),
        ("def_ws_w_ratio",     "工作站默认宽度比例",   "float"),
        ("tank_btm_margin",    "烧杯底部留白 (px)",   "int"),
    ]),
    ("🔵 Inlet泵", [
        ("inlet_col",  "所在列 (可小数)",  "float"),
        ("inlet_dx",   "水平偏移 (px)",    "int"),
        ("inlet_dy",   "垂直偏移 (px)",    "int"),
        ("inlet_w",    "宽度 (0=自动)",    "int"),
        ("inlet_h",    "高度 (0=自动)",    "int"),
    ]),
    ("🟢 Transfer泵", [
        ("trans_col",  "所在列",   "float"),
        ("trans_dx",   "水平偏移", "int"),
        ("trans_dy",   "垂直偏移", "int"),
        ("trans_w",    "宽度",     "int"),
        ("trans_h",    "高度",     "int"),
    ]),
    ("🔴 Outlet泵", [
        ("outlet_col", "所在列",   "float"),
        ("outlet_dx",  "水平偏移", "int"),
        ("outlet_dy",  "垂直偏移", "int"),
        ("outlet_w",   "宽度",     "int"),
        ("outlet_h",   "高度",     "int"),
    ]),
    ("🧪 混合烧杯", [
        ("tank1_col",  "所在列",   "float"),
        ("tank1_dx",   "水平偏移", "int"),
        ("tank1_dy",   "垂直偏移", "int"),
        ("tank1_w",    "宽度",     "int"),
        ("tank1_h",    "高度",     "int"),
    ]),
    ("🧫 反应烧杯", [
        ("tank2_col",  "所在列",   "float"),
        ("tank2_dx",   "水平偏移", "int"),
        ("tank2_dy",   "垂直偏移", "int"),
        ("tank2_w",    "宽度",     "int"),
        ("tank2_h",    "高度",     "int"),
    ]),
    ("📟 工作站", [
        ("ws_col",  "所在列",   "float"),
        ("ws_dx",   "水平偏移", "int"),
        ("ws_dy",   "垂直偏移", "int"),
        ("ws_w",    "宽度",     "int"),
        ("ws_h",    "高度",     "int"),
    ]),
    ("🔧 管道1 Inlet→混合", [
        ("pipe1_sx",     "起点X偏移",  "int"),
        ("pipe1_sy",     "起点Y偏移",  "int"),
        ("pipe1_ex",     "终点X偏移",  "int"),
        ("pipe1_ey",     "终点Y偏移",  "int"),
        ("pipe1_mode",   "走线模式",   "mode"),
        ("pipe1_radius", "圆角半径",   "int"),
    ]),
    ("🔧 管道2 混合→Trans", [
        ("pipe2_sx",     "起点X偏移",  "int"),
        ("pipe2_sy",     "起点Y偏移",  "int"),
        ("pipe2_ex",     "终点X偏移",  "int"),
        ("pipe2_ey",     "终点Y偏移",  "int"),
        ("pipe2_mode",   "走线模式",   "mode"),
        ("pipe2_radius", "圆角半径",   "int"),
    ]),
    ("🔧 管道3 Trans→反应", [
        ("pipe3_sx",     "起点X偏移",  "int"),
        ("pipe3_sy",     "起点Y偏移",  "int"),
        ("pipe3_ex",     "终点X偏移",  "int"),
        ("pipe3_ey",     "终点Y偏移",  "int"),
        ("pipe3_mode",   "走线模式",   "mode"),
        ("pipe3_radius", "圆角半径",   "int"),
    ]),
    ("🔧 管道4 反应→Outlet", [
        ("pipe4_sx",     "起点X偏移",  "int"),
        ("pipe4_sy",     "起点Y偏移",  "int"),
        ("pipe4_ex",     "终点X偏移",  "int"),
        ("pipe4_ey",     "终点Y偏移",  "int"),
        ("pipe4_mode",   "走线模式",   "mode"),
        ("pipe4_radius", "圆角半径",   "int"),
    ]),
    ("🔧 管道5+电极线", [
        ("pipe5_len",       "废液管长度 (px)",     "int"),
        ("wire_bridge_dy",  "电极飞线Y偏移 (px)",  "int"),
    ]),
]


class LayoutTunerDialog(QDialog):
    """实时布局参数微调器 - 分Tab显示形状与管道参数"""

    def __init__(self, target_widget, parent=None):
        super().__init__(parent)
        self.target = target_widget
        self.setWindowTitle("🛠️ 布局微调器")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(420, 620)
        
        # 保存初始值
        self._initial_params = {}
        if hasattr(self.target, 'layout_params'):
            self._initial_params = dict(self.target.layout_params)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)
        
        # 标题
        tip = QLabel("调整数值实时预览 | 右键实验过程区域可再次打开")
        tip.setFont(QFont("Microsoft YaHei", 8))
        tip.setStyleSheet("color: #888;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)
        
        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.West)
        self.tabs.setStyleSheet(
            "QTabBar::tab { min-width: 28px; padding: 4px 6px; font-size: 11px; }"
        )
        self.inputs = {}
        
        params = self.target.layout_params if hasattr(self.target, 'layout_params') else {}
        
        for group_name, fields in GROUPS:
            page = QWidget()
            form = QFormLayout(page)
            form.setSpacing(5)
            form.setContentsMargins(8, 8, 8, 8)
            
            for key, label, typ in fields:
                value = params.get(key, 0)
                widget = self._make_editor(key, value, typ)
                form.addRow(label, widget)
                self.inputs[key] = widget
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            
            self.tabs.addTab(scroll, group_name)
        
        main_layout.addWidget(self.tabs, 1)
        
        # 按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        btn_reset = QPushButton("↩ 重置")
        btn_reset.setToolTip("恢复到打开时的参数")
        btn_reset.clicked.connect(self._reset_params)
        btn_layout.addWidget(btn_reset)
        
        btn_default = QPushButton("🔄 默认值")
        btn_default.setToolTip("恢复到程序出厂默认参数")
        btn_default.clicked.connect(self._load_defaults)
        btn_layout.addWidget(btn_default)
        
        btn_copy = QPushButton("📋 复制")
        btn_copy.setToolTip("复制当前参数到剪贴板")
        btn_copy.clicked.connect(self._copy_params)
        btn_layout.addWidget(btn_copy)
        
        btn_print = QPushButton("🖨 打印")
        btn_print.clicked.connect(self._print_params)
        btn_layout.addWidget(btn_print)
        
        main_layout.addLayout(btn_layout)

    def _make_editor(self, key, value, typ):
        """根据类型创建编辑控件"""
        if typ == "mode":
            combo = QComboBox()
            combo.addItems(["V_H (先竖后横)", "H_V (先横后竖)", "Direct (直线)"])
            combo.setCurrentIndex(int(value) % 3)
            combo.currentIndexChanged.connect(
                lambda idx, k=key: self._on_param_changed(k, idx)
            )
            return combo
        elif typ == "float":
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setSingleStep(0.05)
            spin.setRange(-500.0, 500.0)
            spin.setValue(float(value))
            spin.setMinimumWidth(90)
            spin.valueChanged.connect(lambda v, k=key: self._on_param_changed(k, v))
            return spin
        else:  # int
            spin = QSpinBox()
            spin.setSingleStep(1)
            spin.setRange(-2000, 2000)
            spin.setValue(int(value))
            spin.setMinimumWidth(90)
            spin.valueChanged.connect(lambda v, k=key: self._on_param_changed(k, v))
            return spin

    def _on_param_changed(self, key, value):
        """参数变更 → 实时刷新"""
        try:
            self.target.layout_params[key] = value
            self.target.update()
        except Exception as e:
            print(f"[LayoutTuner] Error updating {key}: {e}")

    def _reset_params(self):
        """重置为打开时的值"""
        self._apply_params(self._initial_params)

    def _load_defaults(self):
        """加载出厂默认值"""
        defaults = self.target._default_layout_params()
        self._apply_params(defaults)

    def _apply_params(self, params_dict):
        """批量应用参数并刷新UI控件"""
        for key, value in params_dict.items():
            self.target.layout_params[key] = value
            if key in self.inputs:
                widget = self.inputs[key]
                widget.blockSignals(True)
                if isinstance(widget, QComboBox):
                    widget.setCurrentIndex(int(value) % 3)
                else:
                    widget.setValue(value)
                widget.blockSignals(False)
        self.target.update()

    def _copy_params(self):
        """复制参数字典到剪贴板"""
        lines = ["self.layout_params = {"]
        for key, value in self.target.layout_params.items():
            if isinstance(value, float):
                lines.append(f'    "{key}": {value:.2f},')
            else:
                lines.append(f'    "{key}": {value},')
        lines.append("}")
        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            QMessageBox.information(
                self, "已复制",
                "参数已复制到剪贴板！\n可直接粘贴到代码中替换 _default_layout_params。"
            )

    def _print_params(self):
        """打印到终端"""
        print("=" * 60)
        print("Current Layout Params:")
        print("=" * 60)
        for group_name, fields in GROUPS:
            print(f"\n  ── {group_name} ──")
            for key, label, _ in fields:
                val = self.target.layout_params.get(key, "?")
                print(f"    {label:20s} ({key}) = {val}")
        print("=" * 60)

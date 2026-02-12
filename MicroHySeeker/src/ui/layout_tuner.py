"""
布局微调器 - 实时调节实验过程图中每个形状和管道的位置/尺寸
右键点击"实验过程"区域即可打开
"""
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDoubleSpinBox, QSpinBox, QLabel, QComboBox,
    QPushButton, QWidget, QScrollArea, QApplication,
    QTabWidget, QGroupBox, QMessageBox, QFileDialog,
    QLineEdit, QColorDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

# 默认保存路径
LAYOUT_PARAMS_FILE = Path(__file__).parent.parent.parent / "config" / "layout_params.json"

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
        ("tank1_col",      "所在列",           "float"),
        ("tank1_dx",       "水平偏移",         "int"),
        ("tank1_dy",       "垂直偏移",         "int"),
        ("tank1_w",        "宽度",             "int"),
        ("tank1_h",        "高度",             "int"),
    ]),
    ("🧫 反应烧杯", [
        ("tank2_col",      "所在列",           "float"),
        ("tank2_dx",       "水平偏移",         "int"),
        ("tank2_dy",       "垂直偏移",         "int"),
        ("tank2_w",        "宽度",             "int"),
        ("tank2_h",        "高度",             "int"),
    ]),
    ("📏 烧杯水位线", [
        ("tank1_critical", "混合烧杯临界线(0~1)", "ratio"),
        ("tank2_critical", "反应烧杯临界线(0~1)", "ratio"),
    ]),
    ("📟 工作站", [
        ("ws_col",  "所在列",   "float"),
        ("ws_dx",   "水平偏移", "int"),
        ("ws_dy",   "垂直偏移", "int"),
        ("ws_w",    "宽度",     "int"),
        ("ws_h",    "高度",     "int"),
    ]),
    ("🟢 电极线1", [
        ("wire1_color", "线颜色",             "color"),
        ("wire1_sx",    "起点X偏移(工作站)", "int"),
        ("wire1_sy",    "起点Y偏移(工作站)", "int"),
        ("wire1_ex",    "终点X偏移(烧杯)",   "int"),
        ("wire1_ey",    "终点Y偏移(烧杯)",   "int"),
        ("wire1_bend",  "拐弯次数(0或1)",     "bend"),
        ("wire1_bh",    "拐弯横向偏移",       "int"),
        ("wire1_bv",    "拐弯纵向偏移",       "int"),
    ]),
    ("🔵 电极线2", [
        ("wire2_color", "线颜色",             "color"),
        ("wire2_sx",    "起点X偏移(工作站)", "int"),
        ("wire2_sy",    "起点Y偏移(工作站)", "int"),
        ("wire2_ex",    "终点X偏移(烧杯)",   "int"),
        ("wire2_ey",    "终点Y偏移(烧杯)",   "int"),
        ("wire2_bend",  "拐弯次数(0或1)",     "bend"),
        ("wire2_bh",    "拐弯横向偏移",       "int"),
        ("wire2_bv",    "拐弯纵向偏移",       "int"),
    ]),
    ("🔴 电极线3", [
        ("wire3_color", "线颜色",             "color"),
        ("wire3_sx",    "起点X偏移(工作站)", "int"),
        ("wire3_sy",    "起点Y偏移(工作站)", "int"),
        ("wire3_ex",    "终点X偏移(烧杯)",   "int"),
        ("wire3_ey",    "终点Y偏移(烧杯)",   "int"),
        ("wire3_bend",  "拐弯次数(0或1)",     "bend"),
        ("wire3_bh",    "拐弯横向偏移",       "int"),
        ("wire3_bv",    "拐弯纵向偏移",       "int"),
    ]),
    ("⚪ 泵色·空闲", [
        ("pump_idle_bg",        "背景色",   "color"),
        ("pump_idle_border",    "边框色(空=无)", "color"),
        ("pump_idle_indicator", "指示灯色", "color"),
    ]),
    ("🟢 泵色·运行", [
        ("pump_run_bg",        "背景色",   "color"),
        ("pump_run_border",    "边框色(空=无)", "color"),
        ("pump_run_indicator", "指示灯色", "color"),
    ]),
    ("🟡 泵色·待运行", [
        ("pump_pend_bg",        "背景色",   "color"),
        ("pump_pend_border",    "边框色(空=无)", "color"),
        ("pump_pend_indicator", "指示灯色", "color"),
    ]),
    ("🔤 标签字体", [
        ("label_font_size",     "标签基础字号(pt)",    "int"),
        ("label_color",         "标签文字颜色",        "color"),
        ("uncfg_color",         "未配置文字颜色",      "color"),
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
        
        # 保存/加载按钮行
        io_layout = QHBoxLayout()
        io_layout.setSpacing(4)
        
        btn_save = QPushButton("💾 保存到文件")
        btn_save.setToolTip(f"保存参数到 {LAYOUT_PARAMS_FILE}")
        btn_save.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "font-weight: bold; padding: 4px 8px; border-radius: 3px; }"
            "QPushButton:hover { background-color: #388E3C; }"
        )
        btn_save.clicked.connect(self._save_to_file)
        io_layout.addWidget(btn_save)
        
        btn_load = QPushButton("📂 从文件加载")
        btn_load.setToolTip("从文件加载布局参数")
        btn_load.clicked.connect(self._load_from_file)
        io_layout.addWidget(btn_load)
        
        main_layout.addLayout(io_layout)

    def _make_editor(self, key, value, typ):
        """根据类型创建编辑控件"""
        if typ == "color":
            return self._make_color_editor(key, str(value) if value else "#888888")
        elif typ == "ratio":
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            spin.setSingleStep(0.05)
            spin.setRange(0.0, 1.0)
            spin.setValue(float(value))
            spin.setMinimumWidth(90)
            spin.valueChanged.connect(lambda v, k=key: self._on_param_changed(k, v))
            return spin
        elif typ == "mode":
            combo = QComboBox()
            combo.addItems(["V_H (先竖后横)", "H_V (先横后竖)", "Direct (直线)"])
            combo.setCurrentIndex(int(value) % 3)
            combo.currentIndexChanged.connect(
                lambda idx, k=key: self._on_param_changed(k, idx)
            )
            return combo
        elif typ == "bend":
            combo = QComboBox()
            combo.addItems(["0 - 直线", "1 - 拐一次弯(L型)"])
            combo.setCurrentIndex(int(value) % 2)
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

    def _make_color_editor(self, key, hex_val):
        """创建颜色编辑器: 输入框 + 颜色预览按钮 + 调色盘按钮"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # hex 输入框
        line = QLineEdit(hex_val)
        line.setFixedWidth(80)
        line.setPlaceholderText("#RRGGBB")
        layout.addWidget(line)

        # 颜色预览色块
        preview = QPushButton("")
        preview.setFixedSize(24, 24)
        preview.setStyleSheet(
            f"background-color: {hex_val}; border: 1px solid #999; border-radius: 3px;"
        )
        layout.addWidget(preview)

        # 调色盘按钮
        pick_btn = QPushButton("🎨")
        pick_btn.setFixedSize(28, 24)
        pick_btn.setToolTip("打开调色盘")
        layout.addWidget(pick_btn)

        def _on_text_changed(text):
            text = text.strip()
            c = QColor(text)
            if c.isValid():
                preview.setStyleSheet(
                    f"background-color: {text}; border: 1px solid #999; border-radius: 3px;"
                )
                self._on_param_changed(key, text)

        def _on_pick():
            initial = QColor(line.text().strip())
            if not initial.isValid():
                initial = QColor("#888888")
            c = QColorDialog.getColor(initial, self, "选择颜色")
            if c.isValid():
                hex_str = c.name()  # e.g. "#4caf50"
                line.setText(hex_str)
                # _on_text_changed will be triggered

        line.textChanged.connect(_on_text_changed)
        pick_btn.clicked.connect(_on_pick)

        # 存一个引用以便 _apply_params 可以回写
        container._line_edit = line
        container._preview = preview
        return container

    def _on_param_changed(self, key, value):
        """参数变更 → 实时刷新"""
        try:
            self.target.layout_params[key] = value
            self.target.update()
            # 泵颜色参数变更时，同步刷新 PumpDiagramWidget
            if key.startswith("pump_"):
                main_win = self.target.window()
                if hasattr(main_win, 'pump_diagram'):
                    main_win.pump_diagram.update()
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
                if hasattr(widget, '_line_edit'):
                    # 颜色编辑器
                    widget._line_edit.setText(str(value))
                    c = QColor(str(value))
                    if c.isValid():
                        widget._preview.setStyleSheet(
                            f"background-color: {value}; border: 1px solid #999; border-radius: 3px;"
                        )
                elif isinstance(widget, QComboBox):
                    max_idx = widget.count()
                    widget.setCurrentIndex(int(value) % max_idx)
                else:
                    widget.setValue(value)
                widget.blockSignals(False)
        self.target.update()

    def _copy_params(self):
        """复制参数字典到剪贴板"""
        lines = ["self.layout_params = {"]
        for key, value in self.target.layout_params.items():
            if isinstance(value, str):
                lines.append(f'    "{key}": "{value}",')
            elif isinstance(value, float):
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

    def _save_to_file(self):
        """保存当前参数到JSON文件"""
        try:
            params = dict(self.target.layout_params)
            # 确保目录存在
            LAYOUT_PARAMS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LAYOUT_PARAMS_FILE, "w", encoding="utf-8") as f:
                json.dump(params, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
                self, "保存成功",
                f"布局参数已保存到:\n{LAYOUT_PARAMS_FILE}"
            )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存失败: {e}")

    def _load_from_file(self):
        """从JSON文件加载参数"""
        try:
            fpath, _ = QFileDialog.getOpenFileName(
                self, "选择布局参数文件",
                str(LAYOUT_PARAMS_FILE.parent),
                "JSON 文件 (*.json)"
            )
            if not fpath:
                return
            with open(fpath, "r", encoding="utf-8") as f:
                params = json.load(f)
            self._apply_params(params)
            QMessageBox.information(self, "加载成功", f"已从文件加载参数:\n{fpath}")
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载失败: {e}")


def load_saved_layout_params() -> dict | None:
    """加载已保存的布局参数（供 ExperimentProcessWidget 启动时调用）
    
    Returns:
        dict: 参数字典，如果文件不存在或读取失败则返回 None
    """
    try:
        if LAYOUT_PARAMS_FILE.exists():
            with open(LAYOUT_PARAMS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[LayoutTuner] 加载保存的布局参数失败: {e}")
    return None

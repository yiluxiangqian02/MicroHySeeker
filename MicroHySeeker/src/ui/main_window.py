"""
主窗口 - MicroHySeeker 自动化实验平台
- 12 台泵模型（实际泵形状，显示完整编号，标注溶液类型、原浓度、泵地址）
- 实验过程区域：绘制Inlet/Transfer/Outlet三个泵（实际泵形状），标注泵地址
- 烧杯1为混合烧杯，烧杯2为反应烧杯，显示液体高度变化
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
from PySide6.QtCore import Qt, Slot, QSize, QRectF, QTimer, QPointF
from PySide6.QtGui import QAction, QIcon, QFont, QColor, QPainter, QPen, QBrush, QLinearGradient, QPainterPath, QPolygonF
from pathlib import Path

from src.models import SystemConfig, Experiment, ProgStep, ProgramStepType, ECSettings
from src.engine.runner import ExperimentRunner
from src.services.i18n import tr, get_lang, set_lang


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

def _step_type_names():
    """动态获取步骤类型名称 (支持i18n)"""
    return {
        ProgramStepType.TRANSFER: tr("step_transfer"),
        ProgramStepType.PREP_SOL: tr("step_prep_sol"),
        ProgramStepType.FLUSH: tr("step_flush"),
        ProgramStepType.ECHEM: tr("step_echem"),
        ProgramStepType.BLANK: tr("step_blank"),
        ProgramStepType.EVACUATE: tr("step_evacuate"),
    }

# 向后兼容 - 旧代码引用 STEP_TYPE_NAMES 的地方不用全改
STEP_TYPE_NAMES = _step_type_names()

# ── 泵颜色辅助函数 (从 layout_params 读取) ──
_PUMP_STYLE_DEFAULTS = {
    0: {"bg": "#E5E7EB", "border": "", "indicator": "#9CA3AF"},
    1: {"bg": "#BBF7D0", "border": "", "indicator": "#22C55E"},
    2: {"bg": "#FDE68A", "border": "", "indicator": "#EAB308"},
}
_PUMP_STATE_PREFIX = {0: "pump_idle", 1: "pump_run", 2: "pump_pend"}

def _pump_style(state: int, params: dict = None) -> dict:
    """Return {bg, border, indicator} QColor-ready strings for a pump state."""
    prefix = _PUMP_STATE_PREFIX.get(state, "pump_idle")
    defaults = _PUMP_STYLE_DEFAULTS.get(state, _PUMP_STYLE_DEFAULTS[0])
    if params:
        return {
            "bg":        params.get(f"{prefix}_bg", defaults["bg"]),
            "border":    params.get(f"{prefix}_border", defaults["border"]),
            "indicator": params.get(f"{prefix}_indicator", defaults["indicator"]),
        }
    return dict(defaults)


class PumpDiagramWidget(QFrame):
    """泵状态指示 - 1行6个共2行布局，12个泵完整显示
    - 配置好的通道显示溶液名/工作类型
    - 运行中亮绿灯，待运行亮黄灯
    - 自适应填满可用空间
    """
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.pump_states = [0] * 12  # 0=空闲, 1=运行中(绿), 2=待运行(黄)
        self.setMinimumSize(600, 200)
        # 加载泵颜色参数
        from src.ui.layout_tuner import load_saved_layout_params
        self._color_params = load_saved_layout_params() or {}
    
    def update_config(self, config: SystemConfig):
        self.config = config
        self.update()
    
    def update_pump_colors(self, params: dict):
        """Update pump color params (called when layout tuner saves)."""
        self._color_params = params
        self.update()
    
    def set_pump_running(self, pump_id: int, running: bool):
        if 1 <= pump_id <= 12:
            self.pump_states[pump_id - 1] = 1 if running else 0
            self.update()
    
    def set_pump_state(self, pump_id: int, state: int):
        """设置泵状态: 0=空闲, 1=运行中(绿), 2=待运行(黄)"""
        if 1 <= pump_id <= 12:
            self.pump_states[pump_id - 1] = state
            self.update()
    
    def _get_pump_label(self, pump_id: int) -> str:
        """获取泵的显示标签（溶液名 / 工作类型）"""
        for ch in self.config.dilution_channels:
            if ch.pump_address == pump_id:
                return ch.solution_name[:8]
        for ch in self.config.flush_channels:
            if ch.pump_address == pump_id:
                wt = getattr(ch, 'work_type', 'Flush')
                return wt
        return ""
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # 自适应计算泵尺寸 (6列2行)
        margin = 8
        cols, rows = 6, 2
        avail_w = w - margin * 2
        avail_h = h - margin * 2
        cell_w = avail_w // cols
        cell_h = avail_h // rows
        pump_w = int(cell_w * 0.85)
        pump_h = int(cell_h * 0.45)
        
        # 字体缩放系数 (基准: cell_w=100, cell_h=100)
        self._fs = max(0.6, min(2.0, min(cell_w / 100, cell_h / 100)))
        
        for i in range(12):
            row = i // cols
            col = i % cols
            
            cx = margin + col * cell_w + cell_w // 2  # 中心x
            cy = margin + row * cell_h + cell_h // 2  # 中心y
            
            px = cx - pump_w // 2
            py = cy - pump_h // 2 - 8  # 往上偏一点留空间给标签
            
            self._draw_pump(painter, px, py, pump_w, pump_h, i + 1)
    
    def _draw_pump(self, painter: QPainter, x: int, y: int, w: int, h: int, pump_id: int):
        """绘制单个泵 - Win11 扁平风格"""
        state = self.pump_states[pump_id - 1]
        label = self._get_pump_label(pump_id)
        style = _pump_style(state, self._color_params)
        
        body_rect = QRectF(x, y, w, h)
        bg_color = QColor(style["bg"])
        indicator_color = QColor(style["indicator"])
        border_val = style["border"].strip() if style["border"] else ""
        
        # 泵主体
        if border_val:
            painter.setPen(QPen(QColor(border_val), 1.5))
        else:
            painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(body_rect, 8, 8)
        
        # 中心指示灯
        indicator_r = min(w, h) // 5
        cx = x + w // 2
        cy = y + h // 2
        painter.setBrush(QBrush(indicator_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - indicator_r, cy - indicator_r, indicator_r * 2, indicator_r * 2)
        
        # 泵编号
        fs = getattr(self, '_fs', 1.0)
        painter.setPen(Qt.white)
        painter.setFont(QFont("Microsoft YaHei", max(8, int(9 * fs)), QFont.Bold))
        painter.drawText(cx - indicator_r, cy - indicator_r, indicator_r * 2, indicator_r * 2,
                         Qt.AlignCenter, str(pump_id))
        
        # 从布局参数获取统一字号和颜色
        base_sz = int(self._color_params.get("label_font_size", 10))
        lbl_color = str(self._color_params.get("label_color", "#374151"))
        
        # 下方标签: 溶液名/工作类型 + 泵地址在同一行
        if label:
            label_text = f"{label} ({tr('pump_n', n=pump_id)})"
        else:
            label_text = tr("pump_n", n=pump_id)
        painter.setPen(QColor(lbl_color))
        painter.setFont(QFont("Microsoft YaHei", max(7, int(base_sz * fs))))
        painter.drawText(x - 5, y + h + 2, w + 10, int(20 * fs), Qt.AlignCenter, label_text)


class ExperimentProcessWidget(QFrame):
    """实验过程区域 - Inlet/Transfer/Outlet泵 + 混合烧杯/反应烧杯 + 液位 + 指示灯"""
    
    def __init__(self, config: SystemConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.inlet_pump = 0
        self.transfer_pump = 0
        self.outlet_pump = 0
        self.inlet_active = False
        self.transfer_active = False
        self.outlet_active = False
        self.tank1_level = 0.0  # 混合烧杯液位 (0-1)
        self.tank2_level = 0.0  # 反应烧杯液位 (0-1)
        self.combo_progress = "0/0"
        self.setMinimumSize(600, 300)
        
        # ======== 工作站状态 ========
        # "disconnected" | "connected" | "failed"
        self.ws_connection_status = "disconnected"
        # "" | "即将开始CV测量" | "CV测量中..." | "测量完成" 等
        self.ws_measurement_status = ""
        
        # ======== 电化学结果图像 ========
        self._echem_pixmap = None  # QPixmap, 由 set_echem_result 生成
        
        # ======== 布局参数（每个形状独立 dx/dy/w/h, 每条管道独立偏移） ========
        self.layout_params = self._default_layout_params()
        # 尝试从文件加载已保存的参数
        self._load_saved_layout_params()
        
        # 波形数据 (模拟)
        self.curve_data = [0] * 50
        # 更新定时器 - 用于波形动画
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(100)

    def _load_saved_layout_params(self):
        """尝试从配置文件加载布局参数"""
        try:
            from src.ui.layout_tuner import load_saved_layout_params
            saved = load_saved_layout_params()
            if saved:
                # 用保存的值覆盖默认值（保留默认值中有但保存文件中没有的键）
                self.layout_params.update(saved)
                print("[ExperimentProcess] 已从文件加载布局参数")
        except Exception as e:
            print(f"[ExperimentProcess] 加载布局参数失败: {e}")

    @staticmethod
    def _default_layout_params():
        """所有可调参数的默认值"""
        return {
            # ── 全局 ──
            "margin_x": 20,
            "margin_y": 20,
            "col_count": 6,          # 网格列数
            
            # ── Inlet 泵 (Col 0) ──
            "inlet_col": 0.0,        # 所在列(可小数)
            "inlet_dx": 0,           # 额外水平偏移 px
            "inlet_dy": 0,           # 额外垂直偏移 px
            "inlet_w": 0,            # 宽度覆盖 (0=自动)
            "inlet_h": 0,            # 高度覆盖 (0=自动)
            
            # ── Transfer 泵 (Col 2) ──
            "trans_col": 2.0,
            "trans_dx": 0,
            "trans_dy": 0,
            "trans_w": 0,
            "trans_h": 0,
            
            # ── Outlet 泵 (Col 4) ──
            "outlet_col": 4.0,
            "outlet_dx": 0,
            "outlet_dy": 0,
            "outlet_w": 0,
            "outlet_h": 0,
            
            # ── 混合烧杯 (Col 1) ──
            "tank1_col": 1.0,
            "tank1_dx": 0,
            "tank1_dy": 0,
            "tank1_w": 0,
            "tank1_h": 0,
            
            # ── 反应烧杯 (Col 3) ──
            "tank2_col": 3.0,
            "tank2_dx": 0,
            "tank2_dy": 0,
            "tank2_w": 0,
            "tank2_h": 0,
            
            # ── 工作站 (Col 5) ──
            "ws_col": 5.0,
            "ws_dx": 0,
            "ws_dy": 0,
            "ws_w": 0,
            "ws_h": 0,
            
            # ── 默认尺寸比例 (当 w/h=0 时使用) ──
            "def_pump_w_ratio": 0.85,   # 泵宽 = col_w * ratio
            "def_pump_hw_ratio": 0.60,  # 泵高 = pump_w * ratio
            "def_tank_w_ratio": 0.80,
            "def_tank_hw_ratio": 1.00,
            "def_ws_w_ratio": 0.90,
            "tank_btm_margin": 20,      # 烧杯底部留白
            
            # ── 烧杯临界线高度 (0.0~1.0) ──
            "tank1_critical": 0.80,  # 混合烧杯临界线位置
            "tank2_critical": 0.80,  # 反应烧杯临界线位置
            
            # ── 电极线 1 (绿色) ──
            "wire1_color": "#4CAF50",  # 线颜色
            "wire1_sx": 10,   # 起点X偏移(相对工作站左上)
            "wire1_sy": 10,   # 起点Y偏移(相对工作站左上)
            "wire1_ex": -5,   # 终点X偏移(相对烧杯中心)
            "wire1_ey": 20,   # 终点Y偏移(相对烧杯顶部)
            "wire1_bend": 1,  # 拐弯次数 0=直线, 1=L型拐一次弯
            "wire1_bh": 0,    # 拐弯横向偏移(相对起点X)
            "wire1_bv": 0,    # 拐弯纵向偏移(相对终点Y)
            
            # ── 电极线 2 (蓝色) ──
            "wire2_color": "#2196F3",
            "wire2_sx": 15,
            "wire2_sy": 10,
            "wire2_ex": 0,
            "wire2_ey": 20,
            "wire2_bend": 1,
            "wire2_bh": 0,
            "wire2_bv": 0,
            
            # ── 电极线 3 (红色) ──
            "wire3_color": "#F44336",
            "wire3_sx": 20,
            "wire3_sy": 10,
            "wire3_ex": 5,
            "wire3_ey": 20,
            "wire3_bend": 1,
            "wire3_bh": 0,
            "wire3_bv": 0,
            
            # ── 泵颜色 · 空闲 ──
            "pump_idle_bg":        "#E5E7EB",
            "pump_idle_border":    "",          # 空=无边框
            "pump_idle_indicator": "#9CA3AF",
            # ── 泵颜色 · 运行中 ──
            "pump_run_bg":        "#BBF7D0",
            "pump_run_border":    "",
            "pump_run_indicator": "#22C55E",
            # ── 泵颜色 · 待运行 ──
            "pump_pend_bg":        "#FDE68A",
            "pump_pend_border":    "",
            "pump_pend_indicator": "#EAB308",
            
            # ── 标签字体 ──
            "label_font_size":     10,          # 标签基础字号 (px)
            "label_color":         "#374151",   # 标签文字颜色 (统一)
            "uncfg_color":         "#DC2626",   # 未配置文字颜色
        }

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        action = menu.addAction("🛠️ 调节布局参数 (Tuner)")
        action.triggered.connect(self.open_tuner)
        if hasattr(menu, 'exec'):
            menu.exec(event.globalPos())
        else:
            menu.exec_(event.globalPos())

    def open_tuner(self):
        """打开布局微调对话框"""
        try:
            from src.ui.layout_tuner import LayoutTunerDialog
            self._tuner_dlg = LayoutTunerDialog(self, self)
            self._tuner_dlg.show()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Failed to open tuner: {e}")
    
    def update_config(self, config: SystemConfig):
        self.config = config
        self._update_pump_ids()
        self.update()
    
    def _update_pump_ids(self):
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
    
    def set_ws_connection_status(self, status: str):
        """设置工作站连接状态: 'disconnected' | 'connected' | 'failed'"""
        self.ws_connection_status = status
        self.update()
    
    def set_ws_measurement_status(self, text: str):
        """设置工作站测量状态文字，如 '即将开始CV测量' / 'CV测量中...' / ''"""
        self.ws_measurement_status = text
        self.update()
    
    def set_echem_result(self, technique: str, data_points: list, headers: list):
        """接收电化学结果数据，使用 matplotlib 生成白底红线图像并显示在工作站屏幕区域"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            import numpy as np
            
            if not data_points:
                return
            
            arr = np.array(data_points)
            fig = Figure(figsize=(6, 4.5), dpi=200, facecolor='white')
            canvas = FigureCanvasAgg(fig)
            ax = fig.add_subplot(111)
            ax.set_facecolor('white')
            
            line_color = '#D32F2F'  # 红线
            lw = 1.8  # 线宽
            tech_upper = technique.upper()
            if tech_upper == "CV" and arr.shape[1] >= 3:
                ax.plot(arr[:, 1], arr[:, 2], color=line_color, linewidth=lw)
                ax.set_xlabel('E / V', fontsize=15, fontweight='bold')
                ax.set_ylabel('I / A', fontsize=15, fontweight='bold')
                ax.set_title('Cyclic Voltammetry (CV)', fontsize=16, fontweight='bold')
            elif tech_upper == "LSV" and arr.shape[1] >= 3:
                ax.plot(arr[:, 1], arr[:, 2], color=line_color, linewidth=lw)
                ax.set_xlabel('E / V', fontsize=15, fontweight='bold')
                ax.set_ylabel('I / A', fontsize=15, fontweight='bold')
                ax.set_title('Linear Sweep Voltammetry (LSV)', fontsize=16, fontweight='bold')
            elif tech_upper in ("I-T", "IT") and arr.shape[1] >= 3:
                ax.plot(arr[:, 0], arr[:, 2], color=line_color, linewidth=lw)
                ax.set_xlabel('t / s', fontsize=15, fontweight='bold')
                ax.set_ylabel('I / A', fontsize=15, fontweight='bold')
                ax.set_title('Amperometric i-t Curve', fontsize=16, fontweight='bold')
            elif tech_upper == "OCPT" and arr.shape[1] >= 2:
                ax.plot(arr[:, 0], arr[:, 1], color='#1565C0', linewidth=lw)
                ax.set_xlabel('t / s', fontsize=15, fontweight='bold')
                ax.set_ylabel('E / V', fontsize=15, fontweight='bold')
                ax.set_title('Open Circuit Potential (OCPT)', fontsize=16, fontweight='bold')
            elif tech_upper == "EIS" and arr.shape[1] >= 2:
                ax.plot(arr[:, 0], -arr[:, 1], color=line_color, linewidth=lw, marker='o', markersize=3)
                ax.set_xlabel("Z' / Ω", fontsize=15, fontweight='bold')
                ax.set_ylabel("-Z'' / Ω", fontsize=15, fontweight='bold')
                ax.set_title('Nyquist Plot (EIS)', fontsize=16, fontweight='bold')
            else:
                ax.plot(arr[:, 0], arr[:, 1] if arr.shape[1] >= 2 else arr[:, 0],
                        color=line_color, linewidth=lw)
                ax.set_title(tech_upper, fontsize=16, fontweight='bold')
            
            ax.tick_params(labelsize=12, width=1.5)
            ax.grid(True, alpha=0.3, color='#CCCCCC')
            for spine in ax.spines.values():
                spine.set_linewidth(1.5)
            fig.tight_layout(pad=1.0)
            
            canvas.draw()
            buf = canvas.buffer_rgba()
            w, h = canvas.get_width_height()
            
            from PySide6.QtGui import QImage, QPixmap
            qimg = QImage(bytes(buf), w, h, QImage.Format_RGBA8888)
            self._echem_pixmap = QPixmap.fromImage(qimg)
            plt.close(fig)
            
            self.ws_measurement_status = tr("ws_done", tech=tech_upper)
            self.update()
        except Exception as e:
            print(f"[ExperimentProcess] 生成电化学图像失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_animation(self):
        # 简单的随机游走波形
        import random
        last = self.curve_data[-1]
        new_val = last + (random.random() - 0.5) * 0.1
        new_val = max(-1.0, min(1.0, new_val))
        self.curve_data.pop(0)
        self.curve_data.append(new_val)
        self.update()
    
    def set_combo_progress(self, current: int, total: int):
        self.combo_progress = f"{current}/{total}"
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # 字体缩放系数 (基准: 600x300)
        self._fs = max(0.65, min(2.2, min(w / 600, h / 300)))
        
        p = self.layout_params  # 简写
        
        mx = int(p["margin_x"])
        my = int(p["margin_y"])
        ncol = max(1, int(p["col_count"]))
        col_w = (w - mx * 2) / ncol
        
        # ── 辅助函数: 计算形状的实际矩形 ──
        def _auto_pump_size():
            pw = int(col_w * p["def_pump_w_ratio"])
            ph = int(pw * p["def_pump_hw_ratio"])
            return pw, ph
        
        def _auto_tank_size():
            tw = int(col_w * p["def_tank_w_ratio"])
            th = int(tw * p["def_tank_hw_ratio"])
            return tw, th
        
        def _auto_ws_size():
            ws_w = int(col_w * p["def_ws_w_ratio"])
            return ws_w
        
        def _shape_rect(prefix, default_w, default_h, is_bottom=False):
            """根据参数计算形状的 (x, y, w, h)"""
            col = p.get(f"{prefix}_col", 0)
            dx = int(p.get(f"{prefix}_dx", 0))
            dy = int(p.get(f"{prefix}_dy", 0))
            sw = int(p.get(f"{prefix}_w", 0))
            sh = int(p.get(f"{prefix}_h", 0))
            if sw <= 0: sw = default_w
            if sh <= 0: sh = default_h
            cx = int(mx + col * col_w + col_w / 2) + dx
            if is_bottom:
                sy = h - my - sh - int(p["tank_btm_margin"]) + dy
            else:
                sy = my + dy
            sx = cx - sw // 2
            return sx, sy, sw, sh
        
        # ── 计算默认尺寸 ──
        auto_pw, auto_ph = _auto_pump_size()
        auto_tw, auto_th = _auto_tank_size()
        auto_ws_w = _auto_ws_size()
        
        # ── 各形状实际矩形 ──
        ix, iy, iw, ih = _shape_rect("inlet",  auto_pw, auto_ph)
        tx, ty, tw_, th = _shape_rect("trans",  auto_pw, auto_ph)
        ox, oy, ow, oh = _shape_rect("outlet", auto_pw, auto_ph)
        t1x, t1y, t1w, t1h = _shape_rect("tank1", auto_tw, auto_th, is_bottom=True)
        t2x, t2y, t2w, t2h = _shape_rect("tank2", auto_tw, auto_th, is_bottom=True)
        
        # 工作站特殊处理: 高度默认从泵顶到烧杯底
        ws_dw = int(p.get("ws_w", 0))
        ws_dh = int(p.get("ws_h", 0))
        ws_auto_w = auto_ws_w if ws_dw <= 0 else ws_dw
        ws_col = p.get("ws_col", 5.0)
        ws_dx = int(p.get("ws_dx", 0))
        ws_dy = int(p.get("ws_dy", 0))
        ws_cx = int(mx + ws_col * col_w + col_w / 2) + ws_dx
        ws_x = ws_cx - ws_auto_w // 2
        ws_y = my + ws_dy
        ws_auto_h = (t2y + t2h) - ws_y if ws_dh <= 0 else ws_dh
        
        # ── 绘制组件 ──
        t1_crit = float(p.get("tank1_critical", 0.80))
        t2_crit = float(p.get("tank2_critical", 0.80))
        self._draw_beaker(painter, t1x, t1y, t1w, t1h,
                          tr("mix_beaker"), self.tank1_level, QColor("#90CAF9"), QColor("#42A5F5"), t1_crit)
        self._draw_beaker(painter, t2x, t2y, t2w, t2h,
                          tr("react_beaker"), self.tank2_level, QColor("#CE93D8"), QColor("#AB47BC"), t2_crit)
        self._draw_workstation(painter, ws_x, ws_y, ws_auto_w, ws_auto_h)
        
        self._draw_pump_like_status(painter, ix, iy, iw, ih,
                                    "Inlet", self.inlet_pump, self.inlet_active)
        self._draw_pump_like_status(painter, tx, ty, tw_, th,
                                    "Transfer", self.transfer_pump, self.transfer_active)
        self._draw_pump_like_status(painter, ox, oy, ow, oh,
                                    "Outlet", self.outlet_pump, self.outlet_active)
        
        # ── 电极线 (颜色可配置, 工作站↔反应烧杯) ──
        wire_prefixes = ["wire1", "wire2", "wire3"]
        wire_defaults = ["#4CAF50", "#2196F3", "#F44336"]
        for prefix, def_color in zip(wire_prefixes, wire_defaults):
            color = QColor(str(p.get(f"{prefix}_color", def_color)))
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)
            # 起点: 工作站左上角 + 偏移
            sx_ = ws_x + p.get(f"{prefix}_sx", 10)
            sy_ = ws_y + p.get(f"{prefix}_sy", 10)
            # 终点: 反应烧杯中心顶部 + 偏移
            ex_ = t2x + t2w / 2 + p.get(f"{prefix}_ex", 0)
            ey_ = t2y + p.get(f"{prefix}_ey", 20)
            bend = int(p.get(f"{prefix}_bend", 1))
            path = QPainterPath()
            path.moveTo(sx_, sy_)
            if bend == 0:
                # 直线
                path.lineTo(ex_, ey_)
            else:
                # L型拐一次弯: 先竖后横
                bh = p.get(f"{prefix}_bh", 0)
                bv = p.get(f"{prefix}_bv", 0)
                corner_x = sx_ + bh
                corner_y = ey_ + bv
                path.lineTo(corner_x, corner_y)
                path.lineTo(ex_, corner_y)
                path.lineTo(ex_, ey_)
            painter.drawPath(path)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(ex_, ey_), 2, 2)
        
        # 组合进程
        fs = self._fs
        p = self.layout_params
        base_sz = int(p.get("label_font_size", 10))
        painter.setPen(QColor("#1565C0"))
        painter.setFont(QFont("Microsoft YaHei", max(7, int(base_sz * fs)), QFont.Bold))
        combo_w = int(200 * fs)
        painter.drawText(w - combo_w, 5, combo_w - 10, int(22 * fs), Qt.AlignRight, f"{tr('combo_label')}: {self.combo_progress}")

    def _draw_pump_like_status(self, painter, x, y, w, h, label, pump_id, active):
        """绘制与PumpDiagramWidget风格一致的泵 - Win11扁平风格"""
        state = 1 if active else 0
        style = _pump_style(state, self.layout_params)
        
        body_rect = QRectF(x, y, w, h)
        bg_color = QColor(style["bg"])
        indicator_color = QColor(style["indicator"])
        border_val = style["border"].strip() if style["border"] else ""
        
        if border_val:
            painter.setPen(QPen(QColor(border_val), 1.5))
        else:
            painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(body_rect, 8, 8)
        
        # 中心指示灯
        indicator_r = min(w, h) // 4
        cx = x + w // 2
        cy = y + h // 2
        painter.setBrush(QBrush(indicator_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - indicator_r, cy - indicator_r, indicator_r * 2, indicator_r * 2)
        
        # 从布局参数获取统一字号和颜色
        fs = getattr(self, '_fs', 1.0)
        p = self.layout_params
        base_sz = int(p.get("label_font_size", 10))
        lbl_color = str(p.get("label_color", "#374151"))
        uncfg_clr = str(p.get("uncfg_color", "#DC2626"))
        
        # 顶部标签 (Inlet/Transfer/Outlet)
        painter.setPen(QColor(lbl_color))
        painter.setFont(QFont("Microsoft YaHei", max(7, int(base_sz * fs))))
        painter.drawText(x, y - int(20 * fs), w, int(20 * fs), Qt.AlignCenter, label)
        
        # 底部状态
        painter.setFont(QFont("Microsoft YaHei", max(7, int(base_sz * fs))))
        if pump_id > 0:
            painter.setPen(QColor(lbl_color))
            painter.drawText(x, y + h + 2, w, int(15 * fs), Qt.AlignCenter, tr("pump_n", n=pump_id))
        else:
            painter.setPen(QColor(uncfg_clr))
            painter.drawText(x, y + h + 2, w, int(15 * fs), Qt.AlignCenter, tr("not_configured"))

    def _draw_rounded_pipe(self, painter, p1, p2, active, mode, radius):
        """画带圆角的管路"""
        color = QColor("#2E7D32") if active else QColor("#90A4AE")
        pen = QPen(color, 4 if active else 3)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        path = QPainterPath()
        path.moveTo(p1)
        
        if mode == "Direct":
            path.lineTo(p2)
            
        elif mode == "H_V": 
            # Horizontal first, then Vertical
            corner = QPointF(p2.x(), p1.y())
            dx = 1 if p2.x() > p1.x() else -1
            dy = 1 if p2.y() > p1.y() else -1
            
            if abs(p2.x() - p1.x()) > radius:
               path.lineTo(corner.x() - dx * radius, corner.y())
               path.quadTo(corner, QPointF(corner.x(), corner.y() + dy * radius))
            else:
               path.lineTo(corner)
            path.lineTo(p2)
            
        elif mode == "V_H":
            # Vertical first, then Horizontal
            corner = QPointF(p1.x(), p2.y())
            dx = 1 if p2.x() > p1.x() else -1
            dy = 1 if p2.y() > p1.y() else -1
            
            if abs(p2.y() - p1.y()) > radius:
                path.lineTo(corner.x(), corner.y() - dy * radius)
                path.quadTo(corner, QPointF(corner.x() + dx * radius, corner.y()))
            else:
                path.lineTo(corner)
            path.lineTo(p2)
            
        painter.drawPath(path)
        
        # Flow Marker
        if active:
            mid = (p1 + p2) / 2
            painter.setBrush(QBrush(color))
            painter.drawEllipse(mid, 3, 3)

    def _draw_workstation(self, painter: QPainter, x: int, y: int, w: int, h: int):
        """绘制电化学工作站 - 含连接状态和测量状态"""
        # 外壳
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(QBrush(QColor("#F5F5F5")))
        painter.drawRoundedRect(x, y, w, h, 8, 8)
        
        # 标题栏 - 使用 QPainterPath 实现仅上半部分圆角
        title_h = 25
        title_path = QPainterPath()
        title_path.moveTo(x, y + title_h)
        title_path.lineTo(x, y + 8)
        title_path.quadTo(x, y, x + 8, y)
        title_path.lineTo(x + w - 8, y)
        title_path.quadTo(x + w, y, x + w, y + 8)
        title_path.lineTo(x + w, y + title_h)
        title_path.closeSubpath()
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#E0E0E0")))
        painter.drawPath(title_path)
        # 标题栏边框
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(title_path)
        
        fs = getattr(self, '_fs', 1.0)
        p = self.layout_params
        base_sz = int(p.get("label_font_size", 10))
        lbl_color = str(p.get("label_color", "#374151"))
        painter.setPen(QColor(lbl_color))
        painter.setFont(QFont("Microsoft YaHei", max(7, int(base_sz * fs))))
        painter.drawText(x, y, w, title_h, Qt.AlignCenter, tr("ws_title"))
        
        # 屏幕区域
        screen_m = 10
        screen_x = x + screen_m
        screen_y = y + 30
        screen_w = w - screen_m * 2
        screen_h = h - 40
        
        if self._echem_pixmap:
            # 有图像时 —— 白色背景
            painter.setPen(QPen(QColor("#BDBDBD"), 2))
            painter.setBrush(QBrush(Qt.white))
            painter.drawRoundedRect(screen_x, screen_y, screen_w, screen_h, 4, 4)
            
            # 绘制电化学结果图像
            from PySide6.QtCore import QRectF
            img_margin = 4
            target_rect = QRectF(screen_x + img_margin, screen_y + img_margin,
                                 screen_w - img_margin * 2, screen_h - img_margin * 2)
            painter.drawPixmap(target_rect.toRect(), self._echem_pixmap)
        else:
            # 无图像时 —— 浅灰色背景 + 居中深灰文字
            painter.setPen(QPen(QColor("#BDBDBD"), 2))
            painter.setBrush(QBrush(QColor("#EEEEEE")))
            painter.drawRoundedRect(screen_x, screen_y, screen_w, screen_h, 4, 4)
            
            # 连接状态 + 等待文字居中显示
            status_map = {
                "disconnected": tr("ws_disconnected"),
                "connected":    tr("ws_connected"),
                "failed":       tr("ws_failed"),
            }
            status_text = status_map.get(self.ws_connection_status, tr("ws_disconnected"))
            display_text = f"{status_text} · {tr('ws_waiting')}"
            if self.ws_measurement_status:
                display_text = self.ws_measurement_status
            painter.setPen(QColor("#9E9E9E"))
            painter.setFont(QFont("Microsoft YaHei", max(8, int(10 * fs))))
            painter.drawText(screen_x, screen_y, screen_w, screen_h,
                             Qt.AlignCenter, display_text)

    def _draw_process_pump(self, painter: QPainter, x: int, y: int, w: int, h: int,
                           name: str, pump_id: int, is_active: bool):
        """绘制过程泵 - Win11扁平风格"""
        state = 1 if is_active else 0
        style = _pump_style(state, self.layout_params)
        
        bg_color = QColor(style["bg"])
        indicator_color = QColor(style["indicator"])
        border_val = style["border"].strip() if style["border"] else ""
        
        if border_val:
            painter.setPen(QPen(QColor(border_val), 1.5))
        else:
            painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(QRectF(x, y, w, h), 8, 8)
        
        # 指示灯 (中心圆)
        indicator_r = min(w, h) // 4
        cx = x + w // 2
        cy = y + h // 2
        
        painter.setBrush(QBrush(indicator_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - indicator_r, cy - indicator_r, indicator_r * 2, indicator_r * 2)
        
        # 从布局参数获取统一字号和颜色
        fs = getattr(self, '_fs', 1.0)
        p = self.layout_params
        base_sz = int(p.get("label_font_size", 10))
        lbl_color = str(p.get("label_color", "#374151"))
        uncfg_clr = str(p.get("uncfg_color", "#DC2626"))
        
        # 泵名称 (上方)
        painter.setPen(QColor(lbl_color))
        painter.setFont(QFont("Microsoft YaHei", max(7, int(base_sz * fs))))
        painter.drawText(x - 5, y - int(20 * fs), w + 10, int(18 * fs), Qt.AlignCenter, name)
        
        # 泵地址 (下方)
        painter.setFont(QFont("Microsoft YaHei", max(7, int(base_sz * fs))))
        if pump_id > 0:
            painter.setPen(QColor(lbl_color))
            painter.drawText(x - 5, y + h + 2, w + 10, int(20 * fs), Qt.AlignCenter, tr("pump_n", n=pump_id))
        else:
            painter.setPen(QColor(uncfg_clr))
            painter.drawText(x - 5, y + h + 2, w + 10, int(20 * fs), Qt.AlignCenter, tr("not_configured"))
    
    def _draw_beaker(self, painter: QPainter, x: int, y: int, w: int, h: int,
                     name: str, level: float, liquid_color: QColor, border_color: QColor,
                     critical_level: float = 0.80):
        """绘制烧杯造型 - U型容器(无上边，圆角底) + 液位 + 可调临界线"""
        r = 20  # 底部圆角半径 (加大)

        # 容器路径 (U型)
        container_path = QPainterPath()
        container_path.moveTo(x, y)                         # 左上
        container_path.lineTo(x, y + h - r)                 # 左边线
        container_path.quadTo(x, y + h, x + r, y + h)       # 左下圆角
        container_path.lineTo(x + w - r, y + h)             # 底边线
        container_path.quadTo(x + w, y + h, x + w, y + h - r) # 右下圆角
        container_path.lineTo(x + w, y)                     # 右边线
        
        # 容器背景 - 闭合路径(用于液体裁剪, 不填充白底)
        bg_path = QPainterPath(container_path)
        bg_path.closeSubpath()
        
        # 容器轮廓 - 黑色加粗 (无白色底色填充)
        painter.setPen(QPen(Qt.black, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(container_path)
        
        # 临界线 - 浅灰色虚线 (高度可配置)
        crit_level = max(0.0, min(1.0, critical_level))
        critical_y = y + h - int(h * crit_level * 0.9)
        painter.setPen(QPen(QColor(180, 180, 180, 160), 1, Qt.DashLine))
        painter.drawLine(x + 5, critical_y, x + w - 5, critical_y)
        
        # 液体
        if level > 0:
            liquid_h = int(h * level * 0.9)  # 最高90%
            liquid_y = y + h - liquid_h
            
            # 液体矩形区域
            liquid_rect_path = QPainterPath()
            liquid_rect_path.addRect(x, liquid_y, w, liquid_h)
            
            # 液体形状 = 液体矩形 Intersect 容器形状
            final_liquid_path = liquid_rect_path.intersected(bg_path)
            
            # 液体渐变
            lg = QLinearGradient(x, liquid_y, x, y + h)
            lc = QColor(liquid_color)
            lc.setAlpha(180)
            lg.setColorAt(0, lc)
            lc.setAlpha(230)
            lg.setColorAt(1, lc)
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(lg))
            painter.drawPath(final_liquid_path)
            
            # 液面波纹线 (顶部横线)
            painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
            painter.drawLine(x + 3, int(liquid_y), x + w - 3, int(liquid_y))
        
        # 容器名称
        fs = getattr(self, '_fs', 1.0)
        p = self.layout_params
        base_sz = int(p.get("label_font_size", 10))
        lbl_color = str(p.get("label_color", "#374151"))
        painter.setPen(QColor(lbl_color))
        painter.setFont(QFont("Microsoft YaHei", max(7, int(base_sz * fs))))
        painter.drawText(x - 10, y + h + 5, w + 20, int(20 * fs), Qt.AlignCenter, name)
        
        # 液位百分比
        if level > 0:
            painter.setPen(QColor("#455A64"))
            painter.setFont(QFont("Microsoft YaHei", max(7, int(9 * fs))))
            painter.drawText(x, y + h // 2, w, int(14 * fs), Qt.AlignCenter, f"{level*100:.0f}%")
    
    def _draw_pipe(self, painter: QPainter, x1: int, y1: int, x2: int, y2: int, active: bool):
        """绘制管道连接线"""
        if active:
            painter.setPen(QPen(QColor("#43A047"), 3, Qt.SolidLine))
        else:
            painter.setPen(QPen(QColor("#B0BEC5"), 2, Qt.DashLine))
        painter.drawLine(x1, y1, x2, y2)


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
        self.setWindowTitle(tr("app_title"))
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
        
        # 运行引擎 (传入系统配置)
        self.runner = ExperimentRunner(config=self.config)
        self.runner.step_started.connect(self._on_step_started)
        self.runner.step_finished.connect(self._on_step_finished)
        self.runner.log_message.connect(self._on_log_message)
        self.runner.experiment_finished.connect(self._on_experiment_finished)
        self.runner.echem_result.connect(self._on_echem_result)
        self.runner.pump_batch_update.connect(self._on_pump_batch_update)
        
        # 电化学实时截图定时器 (测量期间捕获CHI660F窗口)
        self._echem_capture_timer = QTimer(self)
        self._echem_capture_timer.timeout.connect(self._capture_chi_window)
        self._echem_capturing = False
        
        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()
        
        # EChem 连接状态轮询定时器 (每3秒检查 CHI660F 窗口是否存在)
        self._chi_status_timer = QTimer(self)
        self._chi_status_timer.timeout.connect(self._poll_chi_status)
        self._chi_status_timer.start(3000)
        
        # 加载上次保存的实验
        self._load_last_experiment()
        
        self.log_message(tr("sys_started"), "info")
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        menubar.setFont(FONT_NORMAL)
        
        # 文件菜单
        file_menu = menubar.addMenu(tr("file"))
        
        single_action = QAction(tr("single_exp"), self)
        single_action.triggered.connect(self._on_single_exp)
        file_menu.addAction(single_action)
        
        combo_action = QAction(tr("combo_exp"), self)
        combo_action.triggered.connect(self._on_combo_exp)
        file_menu.addAction(combo_action)
        
        file_menu.addSeparator()
        
        load_action = QAction(tr("load_exp"), self)
        load_action.triggered.connect(self._on_load_exp)
        file_menu.addAction(load_action)
        
        save_action = QAction(tr("save_exp"), self)
        save_action.triggered.connect(self._on_save_exp)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(tr("exit"), self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu(tr("tools"))
        
        config_action = QAction(tr("sys_config"), self)
        config_action.triggered.connect(self._on_config)
        tools_menu.addAction(config_action)
        
        manual_action = QAction(tr("manual_ctrl"), self)
        manual_action.triggered.connect(self._on_manual)
        tools_menu.addAction(manual_action)
        
        calibrate_action = QAction(tr("calibrate"), self)
        calibrate_action.triggered.connect(self._on_calibrate)
        tools_menu.addAction(calibrate_action)
        
        tools_menu.addSeparator()
        
        prep_action = QAction(tr("prep_solution"), self)
        prep_action.triggered.connect(self._on_prep_solution)
        tools_menu.addAction(prep_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu(tr("help"))
        
        about_action = QAction(tr("about"), self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(28, 28))
        toolbar.setFont(FONT_NORMAL)
        self.addToolBar(toolbar)
        
        single_btn = QAction(tr("tb_single_exp"), self)
        single_btn.triggered.connect(self._on_single_exp)
        toolbar.addAction(single_btn)
        
        combo_btn = QAction(tr("tb_combo_exp"), self)
        combo_btn.triggered.connect(self._on_combo_exp)
        toolbar.addAction(combo_btn)
        
        toolbar.addSeparator()
        
        load_btn = QAction(tr("tb_load"), self)
        load_btn.triggered.connect(self._on_load_exp)
        toolbar.addAction(load_btn)
        
        save_btn = QAction(tr("tb_save"), self)
        save_btn.triggered.connect(self._on_save_exp)
        toolbar.addAction(save_btn)
        
        toolbar.addSeparator()
        
        prep_btn = QAction(tr("tb_prep"), self)
        prep_btn.triggered.connect(self._on_prep_solution)
        toolbar.addAction(prep_btn)
        
        config_btn = QAction(tr("tb_config"), self)
        config_btn.triggered.connect(self._on_config)
        toolbar.addAction(config_btn)
        
        calibrate_btn = QAction(tr("tb_calibrate"), self)
        calibrate_btn.triggered.connect(self._on_calibrate)
        toolbar.addAction(calibrate_btn)
        
        manual_btn = QAction(tr("tb_manual"), self)
        manual_btn.triggered.connect(self._on_manual)
        toolbar.addAction(manual_btn)
        
        flush_btn = QAction(tr("tb_flush"), self)
        flush_btn.triggered.connect(self._on_flush)
        toolbar.addAction(flush_btn)
    
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
        pumps_group = QGroupBox(tr("pump_status"))
        pumps_group.setFont(FONT_TITLE)
        pumps_layout = QVBoxLayout(pumps_group)
        self.pump_diagram = PumpDiagramWidget(self.config)
        pumps_layout.addWidget(self.pump_diagram)
        left_layout.addWidget(pumps_group, 4)  # 权重 4
        
        # 实验过程
        process_group = QGroupBox(tr("exp_process"))
        process_group.setFont(FONT_TITLE)
        process_layout = QVBoxLayout(process_group)
        self.process_widget = ExperimentProcessWidget(self.config)
        process_layout.addWidget(self.process_widget)
        left_layout.addWidget(process_group, 6)  # 权重 6
        
        # 让 PumpDiagramWidget 共享 ExperimentProcessWidget 的 layout_params（同一个 dict 引用）
        self.pump_diagram._color_params = self.process_widget.layout_params
        
        top_splitter.addWidget(left_frame)
        
        # 右侧：步骤进度 + 日志
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 步骤进度
        step_group = QGroupBox(tr("step_progress"))
        step_group.setFont(FONT_TITLE)
        step_layout = QVBoxLayout(step_group)
        self.step_list = QListWidget()
        self.step_list.setFont(FONT_NORMAL)
        self.step_list.setWordWrap(True)
        step_layout.addWidget(self.step_list)
        right_layout.addWidget(step_group)
        
        # 运行日志 - 白色背景
        log_group = QGroupBox(tr("run_log"))
        log_group.setFont(FONT_TITLE)
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(FONT_NORMAL)
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
        btn_frame = QGroupBox(tr("exp_control"))
        btn_frame.setFont(FONT_TITLE)
        btn_layout = QHBoxLayout(btn_frame)
        
        # 单次实验
        single_group = QGroupBox(tr("single_exp_ctrl"))
        single_layout = QHBoxLayout(single_group)
        
        self.btn_run_single = QPushButton(tr("start_single"))
        self.btn_run_single.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px 18px; font-size: 12px;")
        self.btn_run_single.clicked.connect(self._on_run_single)
        single_layout.addWidget(self.btn_run_single)
        
        btn_layout.addWidget(single_group)
        
        # 组合实验
        combo_group = QGroupBox(tr("combo_exp_ctrl"))
        combo_layout = QHBoxLayout(combo_group)
        
        self.btn_run_combo = QPushButton(tr("start_combo"))
        self.btn_run_combo.setStyleSheet("background-color: #2196F3; color: white; padding: 10px 18px; font-size: 12px;")
        self.btn_run_combo.clicked.connect(self._on_run_combo)
        combo_layout.addWidget(self.btn_run_combo)
        
        self.btn_prev = QPushButton(tr("prev"))
        self.btn_prev.clicked.connect(self._on_prev_combo)
        combo_layout.addWidget(self.btn_prev)
        
        self.btn_next = QPushButton(tr("next"))
        self.btn_next.clicked.connect(self._on_next_combo)
        combo_layout.addWidget(self.btn_next)
        
        combo_layout.addWidget(QLabel(tr("jump_to")))
        self.jump_spin = QSpinBox()
        self.jump_spin.setRange(1, 1000)
        self.jump_spin.setFont(FONT_NORMAL)
        combo_layout.addWidget(self.jump_spin)
        
        self.btn_jump = QPushButton(tr("jump"))
        self.btn_jump.clicked.connect(self._on_jump_combo)
        combo_layout.addWidget(self.btn_jump)
        
        # 复位组合实验
        self.btn_reset_combo = QPushButton(tr("reset_combo"))
        self.btn_reset_combo.setStyleSheet("padding: 10px 12px; font-size: 11px;")
        self.btn_reset_combo.clicked.connect(self._on_reset_combo)
        combo_layout.addWidget(self.btn_reset_combo)
        
        # 列出参数
        self.btn_list_params = QPushButton(tr("list_params"))
        self.btn_list_params.setStyleSheet("padding: 10px 12px; font-size: 11px;")
        self.btn_list_params.clicked.connect(self._on_list_params)
        combo_layout.addWidget(self.btn_list_params)
        
        btn_layout.addWidget(combo_group)
        
        # 停止按钮
        self.btn_stop = QPushButton(tr("stop_exp"))
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; padding: 10px 18px; font-size: 12px;")
        self.btn_stop.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.btn_stop)
        
        parent_layout.addWidget(btn_frame)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.status_bar.setFont(FONT_NORMAL)
        self.setStatusBar(self.status_bar)
        
        self.status_rs485 = QLabel(tr("rs485_status"))
        self.status_chi = QLabel(tr("echem_status"))
        self.status_exp = QLabel(tr("status_idle"))
        
        self.status_bar.addWidget(self.status_rs485)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addWidget(self.status_chi)
        self.status_bar.addWidget(QLabel(" | "))
        self.status_bar.addPermanentWidget(self.status_exp)
    
    # === 菜单事件 ===
    
    def _switch_language(self, lang: str):
        """切换语言并刷新 UI"""
        old_lang = get_lang()
        if lang == old_lang:
            return
        set_lang(lang)
        lang_label = "English" if lang == "en" else "简体中文"
        QMessageBox.information(
            self, tr("info"),
            tr("lang_restart_hint", lang=lang_label)
        )
        # 动态刷新可直接更新的部分
        self.setWindowTitle(tr("app_title"))
        self.status_rs485.setText(tr("rs485_status"))
        self.status_chi.setText(tr("echem_status"))
        self.status_exp.setText(tr("status_idle"))
        if self.single_experiment:
            self._refresh_step_list()
        self.process_widget.update()
        self.pump_diagram.update()
    
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
            QMessageBox.warning(self, tr("warning"), tr("no_steps_warning"))
            return
        
        from src.dialogs.combo_exp_editor import ComboExpEditorDialog
        dialog = ComboExpEditorDialog(self.single_experiment, self.config, self)
        dialog.combo_saved.connect(self._on_combo_saved)
        dialog.exec()
    
    def _on_load_exp(self):
        """载入实验"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("load_exp"), "./experiments", "JSON (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.single_experiment = Experiment.from_json_str(f.read())
                self._refresh_step_list()
                self.log_message(f"已载入实验: {file_path}", "info")
            except Exception as e:
                QMessageBox.critical(self, tr("error"), f"Load failed: {e}")
    
    def _on_save_exp(self):
        """保存实验"""
        if not self.single_experiment:
            QMessageBox.warning(self, tr("warning"), tr("no_exp_to_save"))
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("save_exp"), "./experiments", "JSON (*.json)"
        )
        if file_path:
            try:
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.single_experiment.to_json_str())
                self.log_message(f"实验已保存: {file_path}", "info")
            except Exception as e:
                QMessageBox.critical(self, tr("error"), f"Save failed: {e}")
    
    def _on_config(self):
        """系统配置"""
        from src.dialogs.config_dialog import ConfigDialog
        dialog = ConfigDialog(self.config, self)
        dialog.config_saved.connect(self._on_config_saved)
        dialog.exec()
        # 对话框关闭后更新RS485状态
        self.update_rs485_status()
    
    def _on_manual(self):
        """手动控制"""
        from src.dialogs.manual_control import ManualControlDialog
        dialog = ManualControlDialog(self.config, self)
        dialog.exec()
    
    def _on_calibrate(self):
        """泵校准 - 直接打开位置模式校准对话框"""
        from src.dialogs.position_calibrate_dialog import PositionCalibrateDialog
        dialog = PositionCalibrateDialog(self.config, self)
        dialog.calibration_saved.connect(self._on_position_calibration_saved)
        dialog.exec()
    
    def _on_position_calibration_saved(self, pump_address: int, ul_per_encoder_count: float):
        """位置校准保存后回调"""
        self.log_message(f"泵 {pump_address} 位置校准已保存: {ul_per_encoder_count:.8f} μL/count")
        # 保存配置到磁盘
        try:
            self.config.save_to_file(str(self.config_file))
            self.log_message("校准数据已持久化到配置文件")
        except Exception as e:
            self.log_message(f"保存校准数据失败: {e}", "error")
    
    def _on_prep_solution(self):
        """配制溶液"""
        from src.dialogs.prep_solution import PrepSolutionDialog
        dialog = PrepSolutionDialog(self.config, self)
        dialog.exec()
    
    def _on_flush(self):
        """冲洗"""
        from src.dialogs.flusher_dialog import FlusherDialog
        dialog = FlusherDialog(self.config, self)
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
            QMessageBox.warning(self, tr("warning"), tr("no_steps_warning"))
            return
        
        # --- 运前前预检查 ---
        errors = self.runner.pre_check_experiment(self.single_experiment)
        if errors:
            error_text = "\n".join(f"• {e}" for e in errors)
            QMessageBox.critical(
                self, tr("precheck_fail"),
                f"发现 {len(errors)} 个问题，无法启动实验：\n\n{error_text}\n\n"
                f"请修正后重试。"
            )
            self.log_message(f"预检查失败: {len(errors)} 个错误", "error")
            for err in errors:
                self.log_message(f"  ✖ {err}", "error")
            return
        
        self._refresh_step_list()
        self.runner.run_experiment(self.single_experiment)
        self.status_exp.setText(tr("status_running"))
        self.log_message("开始运行单次实验...", "info")
    
    def _on_run_combo(self):
        """运行组合实验"""
        if not self.combo_params:
            QMessageBox.warning(self, tr("warning"), tr("no_steps_warning"))
            return
        
        if not self.single_experiment:
            QMessageBox.warning(self, tr("warning"), tr("no_steps_warning"))
            return
        
        # --- 运行前预检查（用基础实验做检查） ---
        errors = self.runner.pre_check_experiment(self.single_experiment)
        if errors:
            error_text = "\n".join(f"• {e}" for e in errors)
            QMessageBox.critical(
                self, "预检查失败",
                f"发现 {len(errors)} 个问题，无法启动组合实验：\n\n{error_text}\n\n"
                f"请修正后重试。"
            )
            self.log_message(f"组合实验预检查失败: {len(errors)} 个错误", "error")
            for err in errors:
                self.log_message(f"  ✖ {err}", "error")
            return
        
        self.current_combo_index = 0
        self.total_combo_count = len(self.combo_params)
        self.process_widget.set_combo_progress(1, self.total_combo_count)
        self.log_message(f"开始运行组合实验，共 {self.total_combo_count} 组", "info")
        
        # 应用第一组参数并运行
        self._apply_combo_params_and_run(0)
    
    def _apply_combo_params_and_run(self, combo_index: int):
        """应用组合参数并运行实验
        
        Args:
            combo_index: 组合参数索引
        """
        if combo_index >= len(self.combo_params):
            self.log_message("所有组合实验完成", "success")
            return
        
        params = self.combo_params[combo_index]
        self.log_message(f"应用组合 {combo_index + 1} 参数: {params}", "info")
        
        # 将参数应用到实验步骤
        import copy
        experiment_copy = copy.deepcopy(self.single_experiment)
        
        for param_key, param_value in params.items():
            # param_key 格式: "步骤序号:参数名" 或 "步骤序号:溶液/参数名"
            if ':' in param_key:
                parts = param_key.split(':', 1)
                step_idx = int(parts[0]) - 1
                param_name = parts[1]
                
                if 0 <= step_idx < len(experiment_copy.steps):
                    step = experiment_copy.steps[step_idx]
                    self._apply_param_to_step(step, param_name, param_value)
        
        # 运行实验
        self.runner.run_experiment(experiment_copy)
        self.status_exp.setText(f"状态: 运行中 (组合 {combo_index + 1}/{self.total_combo_count})")
    
    def _apply_param_to_step(self, step, param_name: str, param_value: float):
        """将参数值应用到步骤
        
        Args:
            step: 步骤对象
            param_name: 参数名
            param_value: 参数值
        """
        from src.models import ProgramStepType
        
        # 根据步骤类型和参数名设置值
        if step.step_type == ProgramStepType.TRANSFER:
            if param_name == "转速(RPM)":
                step.pump_rpm = int(param_value)
            elif param_name == "持续时间(s)":
                step.transfer_duration = param_value
        elif step.step_type == ProgramStepType.FLUSH:
            if param_name == "转速(RPM)":
                step.flush_rpm = int(param_value)
            elif param_name == "单次时长(s)":
                step.flush_cycle_duration_s = param_value
            elif param_name == "循环次数":
                step.flush_cycles = int(param_value)
        elif step.step_type == ProgramStepType.EVACUATE:
            if param_name == "转速(RPM)":
                step.pump_rpm = int(param_value)
            elif param_name == "单次时长(s)":
                step.transfer_duration = param_value
            elif param_name == "循环次数":
                step.flush_cycles = int(param_value)
        elif step.step_type == ProgramStepType.ECHEM:
            if step.ec_settings:
                if param_name == "扫描速率":
                    step.ec_settings.scan_rate = param_value
                elif param_name == "初始电位":
                    step.ec_settings.e0 = param_value
                elif param_name == "上限电位":
                    step.ec_settings.eh = param_value
                elif param_name == "下限电位":
                    step.ec_settings.el = param_value
                elif param_name == "运行时间":
                    step.ec_settings.run_time_s = param_value
        elif step.step_type == ProgramStepType.BLANK:
            if param_name == "持续时间(s)":
                step.duration_s = param_value
    
    def _on_stop(self):
        """停止实验 - 设标志 + 立即停止所有硬件泵"""
        self.runner.stop()
        
        # 立即发送硬件停止命令给所有泵
        try:
            from src.services.rs485_wrapper import get_rs485_instance
            rs485 = get_rs485_instance()
            if rs485.is_connected():
                rs485.stop_all()
                self.log_message("已发送停止命令到所有泵", "warning")
        except Exception as e:
            self.log_message(f"停止泵异常: {e}", "error")
        
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
        self._save_last_experiment()
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
        # 同步更新 runner 的配置
        self.runner.set_config(config)
        self.log_message("系统配置已更新", "info")
        # 刷新语言相关 UI
        self.setWindowTitle(tr("app_title"))
        self.status_rs485.setText(tr("rs485_status"))
        self.status_chi.setText(tr("echem_status"))
        if self.single_experiment:
            self._refresh_step_list()
        self.process_widget.update()
        self.pump_diagram.update()
    
    def _refresh_step_list(self):
        """刷新步骤列表 - 中文显示，不同类型不同颜色，带详细参数"""
        self.step_list.clear()
        names = _step_type_names()
        if self.single_experiment:
            for i, step in enumerate(self.single_experiment.steps):
                type_name = names.get(step.step_type, str(step.step_type))
                color = STEP_TYPE_COLORS.get(step.step_type, "#000000")
                detail = self._get_step_detail(step)
                
                if detail:
                    text = f"[{i+1}] {type_name}: {detail}"
                else:
                    text = f"[{i+1}] {type_name}"
                
                item = QListWidgetItem(text)
                item.setForeground(QColor(color))
                item.setToolTip(text)  # 鼠标悬停显示完整内容
                self.step_list.addItem(item)
    
    def _get_step_detail(self, step) -> str:
        """获取步骤详细描述"""
        if step.step_type == ProgramStepType.TRANSFER:
            d = step.transfer_duration or 0
            rpm = step.pump_rpm or 0
            addr = step.pump_address or '?'
            return f"泵{addr} {d:.1f}s {rpm}RPM"
        elif step.step_type == ProgramStepType.PREP_SOL:
            if step.prep_sol_params:
                return step.prep_sol_params.get_summary()
            return ""
        elif step.step_type == ProgramStepType.FLUSH:
            d = step.flush_cycle_duration_s or 0
            c = step.flush_cycles or 1
            addr = step.pump_address or '?'
            return f"泵{addr} {d:.1f}s×{c}次"
        elif step.step_type == ProgramStepType.ECHEM:
            if step.ec_settings:
                tech = step.ec_settings.technique
                tv = tech.value if hasattr(tech, 'value') else str(tech)
                tv_upper = tv.upper()
                ec = step.ec_settings
                parts = [tv_upper]
                if tv_upper in ("CV", "LSV"):
                    parts.append(f"E0={ec.e0 or 0:.2f}V")
                    if ec.eh is not None:
                        parts.append(f"Eh={ec.eh:.2f}V")
                    if ec.el is not None:
                        parts.append(f"El={ec.el:.2f}V")
                    parts.append(f"{tr('scan_rate')}={ec.scan_rate or 0.05}V/s")
                    if tv_upper == "CV":
                        parts.append(f"{tr('segments')}={ec.seg_num}")
                elif tv_upper in ("I-T", "IT"):
                    parts.append(f"E0={ec.e0 or 0:.2f}V")
                    parts.append(f"{tr('run_time')}={ec.run_time_s or 60}s")
                elif tv_upper == "OCPT":
                    parts.append(f"{tr('run_time')}={ec.run_time_s or 60}s")
                elif tv_upper == "EIS":
                    parts.append(f"{tr('freq_range')}={ec.freq_low}-{ec.freq_high}Hz")
                    parts.append(f"{tr('amplitude')}={ec.amplitude}V")
                if ec.sensitivity is not None and not ec.autosensitivity:
                    parts.append(f"{tr('sensitivity')}={ec.sensitivity:g}")
                dummy = getattr(ec, 'use_dummy_cell', None)
                if dummy:
                    parts.append("Dummy")
                return ", ".join(parts)
            return ""
        elif step.step_type == ProgramStepType.BLANK:
            d = step.duration_s or 0
            return f"等待{d:.1f}s"
        elif step.step_type == ProgramStepType.EVACUATE:
            d = step.transfer_duration or 0
            c = step.flush_cycles or 1
            addr = step.pump_address or '?'
            return f"泵{addr} {d:.1f}s×{c}次"
        return ""
    
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
        
        self.log_text.append(f'<span style="color:{color};">[{timestamp}] {msg}</span>')
    
    @Slot(str)
    def _on_log_message(self, msg: str):
        """接收引擎日志"""
        self.log_message(msg, "info")
    
    @Slot(int, str)
    def _on_step_started(self, index: int, step_id: str):
        """步骤开始 - 更新指示灯和泵状态"""
        if index < self.step_list.count():
            self.step_list.setCurrentRow(index)
            # 高亮当前步骤
            for i in range(self.step_list.count()):
                item = self.step_list.item(i)
                if i == index:
                    item.setBackground(QColor("#E8F5E9"))  # 浅绿色背景 = 当前执行
                elif i == index + 1:
                    item.setBackground(QColor("#FFF9C4"))  # 浅黄色背景 = 下一步
                else:
                    item.setBackground(QColor(Qt.transparent))
        
        if self.single_experiment and index < len(self.single_experiment.steps):
            step = self.single_experiment.steps[index]
            names = _step_type_names()
            type_name = names.get(step.step_type, str(step.step_type))
            detail = self._get_step_detail(step)
            msg_type = step.step_type.value if hasattr(step.step_type, 'value') else "info"
            self.log_message(f"▶ 步骤 {index+1} 开始: [{type_name}] {detail or step_id}", msg_type)
            
            # 电化学步骤 - 更新工作站显示状态 + 启动实时截图
            if step.step_type == ProgramStepType.ECHEM and step.ec_settings:
                tech = step.ec_settings.technique
                tv = tech.value if hasattr(tech, 'value') else str(tech)
                self.process_widget.set_ws_connection_status("connected")
                self.process_widget.set_ws_measurement_status(
                    tr("ws_measuring", tech=tv.upper())
                )
                # 启动 CHI 窗口实时截图 (每1秒捕获一次)
                self._start_echem_capture()
            
            # 更新泵指示灯 - 当前步骤绿色
            self._update_pump_indicators(step, running=True)
            
            # 下一步泵变黄色
            if index + 1 < len(self.single_experiment.steps):
                next_step = self.single_experiment.steps[index + 1]
                self._set_next_step_pump_yellow(next_step)
    
    def _set_next_step_pump_yellow(self, step):
        """将下一步涉及的泵设置为黄色(state=2)指示"""
        stype = step.step_type
        if stype == ProgramStepType.PREP_SOL:
            if step.prep_sol_params:
                for sol_name in step.prep_sol_params.injection_order:
                    if step.prep_sol_params.selected_solutions.get(sol_name, False):
                        for ch in self.config.dilution_channels:
                            if ch.solution_name == sol_name:
                                # 仅当该泵不是当前运行状态(1)时才设为黄色
                                if self.pump_diagram.pump_states[ch.pump_address - 1] != 1:
                                    self.pump_diagram.set_pump_state(ch.pump_address, 2)
        elif stype in (ProgramStepType.TRANSFER, ProgramStepType.FLUSH, ProgramStepType.EVACUATE):
            addr = step.pump_address
            if addr and self.pump_diagram.pump_states[addr - 1] != 1:
                self.pump_diagram.set_pump_state(addr, 2)
    
    def _update_pump_indicators(self, step, running: bool):
        """根据当前步骤更新泵状态指示灯和过程区域"""
        # 重置所有泵指示灯
        for i in range(12):
            self.pump_diagram.set_pump_state(i + 1, 0)
        
        stype = step.step_type
        
        if stype == ProgramStepType.PREP_SOL:
            # 配液时: 步骤开始时将所有配液泵设为黄色(等待)
            # 后续由 pump_batch_update 信号动态更新为绿色(运行中)
            if running and step.prep_sol_params:
                for sol_name in step.prep_sol_params.injection_order:
                    if step.prep_sol_params.selected_solutions.get(sol_name, False):
                        for ch in self.config.dilution_channels:
                            if ch.solution_name == sol_name:
                                self.pump_diagram.set_pump_state(ch.pump_address, 2)  # 黄色=等待
            self.process_widget.set_pump_states(False, False, False)
        
        elif stype == ProgramStepType.TRANSFER:
            addr = step.pump_address
            if addr:
                self.pump_diagram.set_pump_state(addr, 1 if running else 0)
            # 如果是Transfer泵，亮对应的过程泵指示
            if addr == self.process_widget.transfer_pump:
                self.process_widget.set_pump_states(False, running, False)
            elif addr == self.process_widget.inlet_pump:
                self.process_widget.set_pump_states(running, False, False)
            elif addr == self.process_widget.outlet_pump:
                self.process_widget.set_pump_states(False, False, running)
        
        elif stype == ProgramStepType.FLUSH:
            addr = step.pump_address
            if addr:
                self.pump_diagram.set_pump_state(addr, 1 if running else 0)
            if addr == self.process_widget.inlet_pump:
                self.process_widget.set_pump_states(running, False, False)
            elif addr == self.process_widget.transfer_pump:
                self.process_widget.set_pump_states(False, running, False)
            elif addr == self.process_widget.outlet_pump:
                self.process_widget.set_pump_states(False, False, running)
        
        elif stype == ProgramStepType.EVACUATE:
            addr = step.pump_address
            if addr:
                self.pump_diagram.set_pump_state(addr, 1 if running else 0)
            if addr == self.process_widget.outlet_pump:
                self.process_widget.set_pump_states(False, False, running)
    
    @Slot(int, str, bool)
    def _on_step_finished(self, index: int, step_id: str, success: bool):
        """步骤完成"""
        status = "✓" if success else "✗"
        msg_type = "success" if success else "error"
        
        detail = ""
        if self.single_experiment and index < len(self.single_experiment.steps):
            step = self.single_experiment.steps[index]
            type_name = _step_type_names().get(step.step_type, str(step.step_type))
            detail = f" [{type_name}]"
            # 关闭当前步骤的指示灯
            self._update_pump_indicators(step, running=False)
            # 电化学步骤完成 - 停止实时截图
            if step.step_type == ProgramStepType.ECHEM:
                self._stop_echem_capture()
        
        self.log_message(f"{status} 步骤 {index+1}{detail} {tr('completed') if success else tr('failed')}", msg_type)
    
    @Slot(list, list)
    def _on_pump_batch_update(self, running_addrs: list, waiting_addrs: list):
        """配液批次更新 - 按注入顺序号动态更新泵颜色
        
        running_addrs: 当前正在运行的泵地址列表（绿色）
        waiting_addrs: 排队等待的泵地址列表（黄色）
        """
        # 先将所有泵重置为灰色
        for i in range(12):
            self.pump_diagram.set_pump_state(i + 1, 0)
        
        # 等待中的泵 → 黄色
        for addr in waiting_addrs:
            if 1 <= addr <= 12:
                self.pump_diagram.set_pump_state(addr, 2)
        
        # 正在运行的泵 → 绿色（覆盖黄色）
        for addr in running_addrs:
            if 1 <= addr <= 12:
                self.pump_diagram.set_pump_state(addr, 1)
    
    @Slot(bool)
    def _on_experiment_finished(self, success: bool):
        """实验完成"""
        # 确保停止 CHI 截图
        self._stop_echem_capture()
        
        status = tr("exp_done_ok") if success else tr("exp_done_fail")
        self.status_exp.setText(tr("status_done") if success else tr("status_failed"))
        msg_type = "success" if success else "error"
        self.log_message(f"实验{status}", msg_type)
        
        # 重置所有泵状态和指示灯
        for i in range(12):
            self.pump_diagram.set_pump_state(i + 1, 0)
        self.process_widget.set_pump_states(False, False, False)
        
        # 清除步骤列表高亮
        for i in range(self.step_list.count()):
            self.step_list.item(i).setBackground(QColor(Qt.transparent))

    # ── 电化学实时截图 ──────────────────────────────────
    
    def _start_echem_capture(self):
        """启动 CHI660F 窗口实时截图，每1秒捕获一次"""
        if not self._echem_capturing:
            self._echem_capturing = True
            self._echem_capture_timer.start(1000)  # 每1秒
            print("[MainWindow] EChem 实时截图已启动")
    
    def _stop_echem_capture(self):
        """停止 CHI660F 窗口实时截图"""
        if self._echem_capturing:
            self._echem_capture_timer.stop()
            self._echem_capturing = False
            print("[MainWindow] EChem 实时截图已停止")
    
    def _capture_chi_window(self):
        """定时回调: 捕获 CHI660F 窗口画面并显示在工作站区域"""
        try:
            from src.utils.window_capture import capture_chi_to_qpixmap
            pixmap = capture_chi_to_qpixmap()
            if pixmap and not pixmap.isNull():
                self.process_widget._echem_pixmap = pixmap
                self.process_widget.update()
        except Exception as e:
            # 捕获失败时静默处理，不影响测量
            pass

    def _poll_chi_status(self):
        """定时轮询: 检测 CHI660F 窗口是否存在，更新状态栏"""
        try:
            from src.utils.window_capture import find_chi_window
            hwnd = find_chi_window()
            if hwnd:
                self.status_chi.setText("电化学仪: ✅ 已连接")
                self.status_chi.setStyleSheet("color: #2E7D32;")
            else:
                self.status_chi.setText("电化学仪: 未连接")
                self.status_chi.setStyleSheet("color: #757575;")
        except Exception:
            self.status_chi.setText("电化学仪: 未连接")
            self.status_chi.setStyleSheet("color: #757575;")

    def _on_echem_result(self, technique: str, data_points: list, headers: list):
        """接收电化学测量结果，在实验过程区域显示图像"""
        # 停止实时截图，切换为最终结果图
        self._stop_echem_capture()
        self.process_widget.set_echem_result(technique, data_points, headers)

    def _save_last_experiment(self):
        """保存当前实验到文件，下次启动时自动加载"""
        if not self.single_experiment:
            return
        try:
            last_exp_file = Path("./config/last_experiment.json")
            last_exp_file.parent.mkdir(parents=True, exist_ok=True)
            with open(last_exp_file, 'w', encoding='utf-8') as f:
                f.write(self.single_experiment.to_json_str())
        except Exception as e:
            print(f"⚠️ 保存上次实验失败: {e}")
    
    def _load_last_experiment(self):
        """加载上次保存的实验"""
        last_exp_file = Path("./config/last_experiment.json")
        if last_exp_file.exists():
            try:
                with open(last_exp_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if not content:
                    print("⚠️ last_experiment.json 为空，跳过加载")
                    return
                self.single_experiment = Experiment.from_json_str(content)
                self._refresh_step_list()
                self.log_message(f"已加载上次实验: {self.single_experiment.exp_name}", "info")
            except Exception as e:
                print(f"⚠️ 加载上次实验失败: {e}")
    
    def closeEvent(self, event):
        """关闭窗口时自动断开RS485连接并保存实验"""
        # 停止轮询定时器
        if hasattr(self, '_chi_status_timer'):
            self._chi_status_timer.stop()
        
        # 保存当前实验
        self._save_last_experiment()
        
        try:
            from src.services.rs485_wrapper import get_rs485_instance
            rs485 = get_rs485_instance()
            if rs485.is_connected():
                rs485.close_port()
                print("✅ 已自动断开RS485连接")
        except Exception as e:
            print(f"⚠️ 关闭RS485时出错: {e}")
        super().closeEvent(event)
    
    def update_rs485_status(self):
        """更新RS485连接状态显示"""
        try:
            from src.services.rs485_wrapper import get_rs485_instance
            rs485 = get_rs485_instance()
            if rs485.is_connected():
                port = getattr(rs485, '_current_port', '')
                self.status_rs485.setText(f"RS485: 已连接 ({port})")
                self.status_rs485.setStyleSheet("color: green;")
            else:
                self.status_rs485.setText("RS485: 未连接")
                self.status_rs485.setStyleSheet("color: red;")
        except Exception as e:
            self.status_rs485.setText("RS485: 状态未知")
            self.status_rs485.setStyleSheet("color: gray;")

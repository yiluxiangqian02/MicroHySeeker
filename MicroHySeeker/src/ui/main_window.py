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
    
    def update_config(self, config: SystemConfig):
        self.config = config
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
        
        for i in range(12):
            row = i // cols
            col = i % cols
            
            cx = margin + col * cell_w + cell_w // 2  # 中心x
            cy = margin + row * cell_h + cell_h // 2  # 中心y
            
            px = cx - pump_w // 2
            py = cy - pump_h // 2 - 8  # 往上偏一点留空间给标签
            
            self._draw_pump(painter, px, py, pump_w, pump_h, i + 1)
    
    def _draw_pump(self, painter: QPainter, x: int, y: int, w: int, h: int, pump_id: int):
        """绘制单个泵 - 更大更美观"""
        state = self.pump_states[pump_id - 1]
        label = self._get_pump_label(pump_id)
        
        # 泵主体 - 圆角矩形
        body_rect = QRectF(x, y, w, h)
        gradient = QLinearGradient(x, y, x, y + h)
        if state == 1:  # 运行中 - 绿色
            gradient.setColorAt(0, QColor("#66BB6A"))
            gradient.setColorAt(1, QColor("#388E3C"))
        elif state == 2:  # 待运行 - 黄色
            gradient.setColorAt(0, QColor("#FFD54F"))
            gradient.setColorAt(1, QColor("#FFA000"))
        else:  # 空闲 - 纯灰色系
            gradient.setColorAt(0, QColor("#D5D5D5"))
            gradient.setColorAt(1, QColor("#A0A0A0"))
        
        painter.setPen(QPen(QColor("#757575"), 1.5))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(body_rect, 6, 6)
        
        # 中心指示灯 (圆形)
        indicator_r = min(w, h) // 5
        cx = x + w // 2
        cy = y + h // 2
        
        if state == 1:  # 运行中 - 亮绿灯
            painter.setBrush(QBrush(QColor("#00E676")))
            painter.setPen(QPen(QColor("#1B5E20"), 1))
        elif state == 2:  # 待运行 - 亮黄灯
            painter.setBrush(QBrush(QColor("#FFEB3B")))
            painter.setPen(QPen(QColor("#F57F17"), 1))
        else:  # 空闲 - 暗灰
            painter.setBrush(QBrush(QColor("#888888")))
            painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawEllipse(cx - indicator_r, cy - indicator_r, indicator_r * 2, indicator_r * 2)
        
        # 泵编号 (在圆形中)
        painter.setPen(Qt.white)
        painter.setFont(QFont("Microsoft YaHei", max(9, indicator_r), QFont.Bold))
        painter.drawText(cx - indicator_r, cy - indicator_r, indicator_r * 2, indicator_r * 2, 
                         Qt.AlignCenter, str(pump_id))
        
        # 下方标签 - 字体与步骤进度列表一致 (11号)
        painter.setPen(QColor("#333333"))
        painter.setFont(QFont("Microsoft YaHei", 11))
        label_text = label if label else f"泵{pump_id}"
        painter.drawText(x - 5, y + h + 2, w + 10, 20, Qt.AlignCenter, label_text)


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
        
        # ======== 布局参数（每个形状独立 dx/dy/w/h, 每条管道独立偏移） ========
        self.layout_params = self._default_layout_params()
        
        # 波形数据 (模拟)
        self.curve_data = [0] * 50
        # 更新定时器 - 用于波形动画
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(100)

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
            
            # ── 管道 1: Inlet→混合烧杯 ──
            "pipe1_sx": 0, "pipe1_sy": 0,   # 起点偏移
            "pipe1_ex": 0, "pipe1_ey": 0,   # 终点偏移
            "pipe1_mode": 0,  # 0=V_H, 1=H_V, 2=Direct
            "pipe1_radius": 20,
            
            # ── 管道 2: 混合烧杯→Transfer ──
            "pipe2_sx": 0, "pipe2_sy": 0,
            "pipe2_ex": 0, "pipe2_ey": 0,
            "pipe2_mode": 1,
            "pipe2_radius": 20,
            
            # ── 管道 3: Transfer→反应烧杯 ──
            "pipe3_sx": 0, "pipe3_sy": 0,
            "pipe3_ex": 0, "pipe3_ey": 0,
            "pipe3_mode": 1,
            "pipe3_radius": 20,
            
            # ── 管道 4: 反应烧杯→Outlet ──
            "pipe4_sx": 0, "pipe4_sy": 0,
            "pipe4_ex": 0, "pipe4_ey": 0,
            "pipe4_mode": 1,
            "pipe4_radius": 20,
            
            # ── 管道 5: Outlet→废液 ──
            "pipe5_len": 40,
            
            # ── 电极线 ──
            "wire_bridge_dy": -10,  # 飞线顶部相对泵顶的偏移
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
    
    def _update_animation(self):
        # 简单的随机游走波形
        import random
        last = self.curve_data[-1]
        new_val = last + (random.random() - 0.5) * 0.1
        new_val = max(-1.0, min(1.0, new_val))
        self.curve_data.pop(0)
        self.curve_data.append(new_val)
        self.update()

    def set_pump_states(self, inlet: bool, transfer: bool, outlet: bool):
        self.inlet_active = inlet
        self.transfer_active = transfer
        self.outlet_active = outlet
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
        self._draw_beaker(painter, t1x, t1y, t1w, t1h,
                          "混合烧杯", self.tank1_level, QColor("#90CAF9"), QColor("#42A5F5"))
        self._draw_beaker(painter, t2x, t2y, t2w, t2h,
                          "反应烧杯", self.tank2_level, QColor("#CE93D8"), QColor("#AB47BC"))
        self._draw_workstation(painter, ws_x, ws_y, ws_auto_w, ws_auto_h)
        
        self._draw_pump_like_status(painter, ix, iy, iw, ih,
                                    "Inlet", self.inlet_pump, self.inlet_active)
        self._draw_pump_like_status(painter, tx, ty, tw_, th,
                                    "Transfer", self.transfer_pump, self.transfer_active)
        self._draw_pump_like_status(painter, ox, oy, ow, oh,
                                    "Outlet", self.outlet_pump, self.outlet_active)
        
        # ── 管道绘制 (每条管道独立可调) ──
        PIPE_MODES = ["V_H", "H_V", "Direct"]
        
        def _pipe_mode(n):
            m = int(p.get(f"pipe{n}_mode", 0))
            return PIPE_MODES[m % len(PIPE_MODES)]
        
        # Pipe 1: Inlet Bottom Center → Tank1 Left
        p1_sx = ix + iw / 2 + p["pipe1_sx"]
        p1_sy = iy + ih + p["pipe1_sy"]
        p1_ex = t1x + 5 + p["pipe1_ex"]
        p1_ey = t1y + 30 + p["pipe1_ey"]
        self._draw_rounded_pipe(painter,
                                QPointF(p1_sx, p1_sy), QPointF(p1_ex, p1_ey),
                                self.inlet_active, _pipe_mode(1), p["pipe1_radius"])
        
        # Pipe 2: Tank1 Right → Transfer Bottom
        p2_sx = t1x + t1w + p["pipe2_sx"]
        p2_sy = t1y + t1h - 40 + p["pipe2_sy"]
        p2_ex = tx + 5 + p["pipe2_ex"]
        p2_ey = ty + th + 10 + p["pipe2_ey"]
        self._draw_rounded_pipe(painter,
                                QPointF(p2_sx, p2_sy), QPointF(p2_ex, p2_ey),
                                self.transfer_active, _pipe_mode(2), p["pipe2_radius"])
        
        # Pipe 3: Transfer Right → Tank2 Top-Left
        p3_sx = tx + tw_ + p["pipe3_sx"]
        p3_sy = ty + th / 2 + p["pipe3_sy"]
        p3_ex = t2x + 20 + p["pipe3_ex"]
        p3_ey = t2y + 10 + p["pipe3_ey"]
        self._draw_rounded_pipe(painter,
                                QPointF(p3_sx, p3_sy), QPointF(p3_ex, p3_ey),
                                self.transfer_active, _pipe_mode(3), p["pipe3_radius"])
        
        # Pipe 4: Tank2 Right → Outlet Bottom
        p4_sx = t2x + t2w + p["pipe4_sx"]
        p4_sy = t2y + t2h - 40 + p["pipe4_sy"]
        p4_ex = ox + ow / 2 + p["pipe4_ex"]
        p4_ey = oy + oh + 10 + p["pipe4_ey"]
        self._draw_rounded_pipe(painter,
                                QPointF(p4_sx, p4_sy), QPointF(p4_ex, p4_ey),
                                self.outlet_active, _pipe_mode(4), p["pipe4_radius"])
        
        # Pipe 5: Outlet Right → Waste
        waste_len = int(p.get("pipe5_len", 40))
        self._draw_rounded_pipe(painter,
                                QPointF(ox + ow, oy + oh / 2),
                                QPointF(ox + ow + waste_len, oy + oh / 2),
                                self.outlet_active, "Direct", 0)
        painter.setPen(QColor("#795548"))
        painter.drawText(int(ox + ow + 5), int(oy + oh / 2 + 20), "废液")
        
        # ── 电极线 ──
        wire_y = iy + int(p.get("wire_bridge_dy", -10))
        colors = [QColor("#4CAF50"), QColor("#2196F3"), QColor("#F44336")]
        for i, color in enumerate(colors):
            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)
            path = QPainterPath()
            sx_ = ws_x + 10 + i * 5
            sy_ = ws_y + 10
            target_x = t2x + t2w / 2 + i * 5
            target_y = t2y + 20
            path.moveTo(sx_, sy_)
            path.lineTo(sx_, wire_y)
            path.lineTo(target_x, wire_y)
            path.lineTo(target_x, target_y)
            painter.drawPath(path)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(target_x, target_y), 2, 2)
        
        # 组合进程
        painter.setPen(QColor("#1565C0"))
        painter.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        painter.drawText(w - 200, 5, 190, 22, Qt.AlignRight, f"组合: {self.combo_progress}")

    def _draw_pump_like_status(self, painter, x, y, w, h, label, pump_id, active):
        """绘制与PumpDiagramWidget风格一致的泵"""
        state = 1 if active else 0
        
        # 泵主体 - 圆角矩形
        body_rect = QRectF(x, y, w, h)
        gradient = QLinearGradient(x, y, x, y + h)
        if state == 1:  # 运行中 - 绿色
            gradient.setColorAt(0, QColor("#66BB6A"))
            gradient.setColorAt(1, QColor("#388E3C"))
        else:  # 空闲 - 纯灰色系
            gradient.setColorAt(0, QColor("#D5D5D5"))
            gradient.setColorAt(1, QColor("#A0A0A0"))
        
        painter.setPen(QPen(QColor("#757575"), 1.5))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(body_rect, 6, 6)
        
        # 中心指示灯 (圆形)
        indicator_r = min(w, h) // 4 # 稍微大一点
        cx = x + w // 2
        cy = y + h // 2
        
        if state == 1:
            painter.setBrush(QBrush(QColor("#00E676")))
        else:
            painter.setBrush(QBrush(QColor("#888888")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - indicator_r, cy - indicator_r, indicator_r * 2, indicator_r * 2)
        
        # 顶部标签 (Inlet/Transfer/Outlet)
        painter.setPen(QColor("#333333"))
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.drawText(x, y - 20, w, 20, Qt.AlignCenter, label)
        
        # 底部状态 (未配置/地址)
        painter.setFont(QFont("Microsoft YaHei", 9))
        if pump_id > 0:
            painter.drawText(x, y + h + 2, w, 15, Qt.AlignCenter, f"泵{pump_id}")
        else:
            painter.setPen(QColor("#D32F2F"))
            painter.drawText(x, y + h + 2, w, 15, Qt.AlignCenter, "未配置")

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
        """绘制电化学工作站"""
        # ...existing code...
        # 外壳
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(QBrush(QColor("#F5F5F5")))
        painter.drawRoundedRect(x, y, w, h, 8, 8)
        
        # 标题栏
        painter.setBrush(QBrush(QColor("#E0E0E0")))
        painter.drawRoundedRect(x, y, w, 25, 8, 8) # 顶部圆角会被上面覆盖吗？
        # 修复顶部圆角的绘制: 单独画下半部分矩形覆盖上面的圆角
        painter.drawRect(x, y + 10, w, 15)
        
        painter.setPen(QColor("#333333"))
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        painter.drawText(x, y, w, 25, Qt.AlignCenter, "电化学工作站")
        
        # 屏幕区域
        screen_m = 10
        screen_x = x + screen_m
        screen_y = y + 30
        screen_w = w - screen_m * 2
        screen_h = h - 40
        
        painter.setPen(QPen(QColor("#424242"), 2))
        painter.setBrush(QBrush(Qt.black))
        painter.drawRoundedRect(screen_x, screen_y, screen_w, screen_h, 4, 4)
        
        # 绘制波形图
        painter.setPen(QPen(QColor("#00E676"), 1.5))
        painter.setBrush(Qt.NoBrush)
        
        if screen_w > 0 and screen_h > 0:
            path = QPainterPath()
            x_step = screen_w / (len(self.curve_data) - 1) if len(self.curve_data) > 1 else 0
            
            for i, val in enumerate(self.curve_data):
                px = screen_x + i * x_step
                # val is -1 to 1 -> map to screen_h
                py = screen_y + screen_h / 2 - val * (screen_h / 2 - 5)
                if i == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            painter.drawPath(path)

    def _draw_process_pump(self, painter: QPainter, x: int, y: int, w: int, h: int,
                           name: str, pump_id: int, is_active: bool):
        """绘制过程泵 - 带指示灯"""
        # 泵主体
        gradient = QLinearGradient(x, y, x, y + h)
        if is_active:
            gradient.setColorAt(0, QColor("#66BB6A"))
            gradient.setColorAt(1, QColor("#2E7D32"))
        else:
            gradient.setColorAt(0, QColor("#D5D5D5"))
            gradient.setColorAt(1, QColor("#A0A0A0"))
        
        painter.setPen(QPen(QColor("#757575"), 1.5))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(QRectF(x, y, w, h), 6, 6)
        
        # 指示灯 (中心圆)
        indicator_r = min(w, h) // 4
        cx = x + w // 2
        cy = y + h // 2
        
        if is_active:
            painter.setBrush(QBrush(QColor("#00E676")))
            painter.setPen(QPen(QColor("#1B5E20"), 1))
        else:
            painter.setBrush(QBrush(QColor("#888888")))
            painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawEllipse(cx - indicator_r, cy - indicator_r, indicator_r * 2, indicator_r * 2)
        
        # 泵名称 (上方) - 11号字体
        painter.setPen(QColor("#333333"))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        painter.drawText(x - 5, y - 20, w + 10, 18, Qt.AlignCenter, name)
        
        # 泵地址 (下方) - 11号字体
        if pump_id > 0:
            painter.setFont(QFont("Microsoft YaHei", 11))
            painter.drawText(x - 5, y + h + 2, w + 10, 20, Qt.AlignCenter, f"泵{pump_id}")
        else:
            painter.setPen(QColor("#E53935"))
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.drawText(x - 5, y + h + 2, w + 10, 20, Qt.AlignCenter, "未配置")
    
    def _draw_beaker(self, painter: QPainter, x: int, y: int, w: int, h: int,
                     name: str, level: float, liquid_color: QColor, border_color: QColor):
        """绘制烧杯造型 - U型容器(无上边，圆角底) + 液位"""
        r = 20  # 底部圆角半径 (加大)

        # 容器路径 (U型)
        container_path = QPainterPath()
        container_path.moveTo(x, y)                         # 左上
        container_path.lineTo(x, y + h - r)                 # 左边线
        container_path.quadTo(x, y + h, x + r, y + h)       # 左下圆角
        container_path.lineTo(x + w - r, y + h)             # 底边线
        container_path.quadTo(x + w, y + h, x + w, y + h - r) # 右下圆角
        container_path.lineTo(x + w, y)                     # 右边线
        
        # 容器背景 - 获取闭合路径用于填充
        bg_path = QPainterPath(container_path)
        bg_path.closeSubpath() # 闭合上边以进行填充
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
        painter.drawPath(bg_path)
        
        # 容器轮廓 - 黑色加粗
        painter.setPen(QPen(Qt.black, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(container_path)
        
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
        painter.setPen(QColor("#333333"))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        painter.drawText(x - 10, y + h + 5, w + 20, 20, Qt.AlignCenter, name)
        
        # 液位百分比
        if level > 0:
            painter.setPen(QColor("#455A64"))
            painter.setFont(QFont("Microsoft YaHei", 9))
            painter.drawText(x, y + h // 2, w, 14, Qt.AlignCenter, f"{level*100:.0f}%")
    
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
        
        # 运行引擎 (传入系统配置)
        self.runner = ExperimentRunner(config=self.config)
        self.runner.step_started.connect(self._on_step_started)
        self.runner.step_finished.connect(self._on_step_finished)
        self.runner.log_message.connect(self._on_log_message)
        self.runner.experiment_finished.connect(self._on_experiment_finished)
        
        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()
        
        # 加载上次保存的实验
        self._load_last_experiment()
        
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
        
        flush_btn = QAction("冲洗", self)
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
        pumps_group = QGroupBox("泵状态指示")
        pumps_group.setFont(FONT_TITLE)
        pumps_layout = QVBoxLayout(pumps_group)
        self.pump_diagram = PumpDiagramWidget(self.config)
        pumps_layout.addWidget(self.pump_diagram)
        left_layout.addWidget(pumps_group, 4)  # 权重 4
        
        # 实验过程
        process_group = QGroupBox("实验过程")
        process_group.setFont(FONT_TITLE)
        process_layout = QVBoxLayout(process_group)
        self.process_widget = ExperimentProcessWidget(self.config)
        process_layout.addWidget(self.process_widget)
        left_layout.addWidget(process_group, 6)  # 权重 6
        
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
        self.step_list.setWordWrap(True)
        step_layout.addWidget(self.step_list)
        right_layout.addWidget(step_group)
        
        # 运行日志 - 白色背景
        log_group = QGroupBox("运行日志")
        log_group.setFont(FONT_TITLE)
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Microsoft YaHei", 11))
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
        self._log(f"泵 {pump_address} 位置校准已保存: {ul_per_encoder_count:.8f} μL/count")
        # 保存配置
        self._save_config()
    
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
            QMessageBox.warning(self, "警告", "请先编辑单次实验程序")
            return
        
        # --- 运行前预检查 ---
        errors = self.runner.pre_check_experiment(self.single_experiment)
        if errors:
            error_text = "\n".join(f"• {e}" for e in errors)
            QMessageBox.critical(
                self, "预检查失败",
                f"发现 {len(errors)} 个问题，无法启动实验：\n\n{error_text}\n\n"
                f"请修正后重试。"
            )
            self.log_message(f"预检查失败: {len(errors)} 个错误", "error")
            for err in errors:
                self.log_message(f"  ✖ {err}", "error")
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
        
        if not self.single_experiment:
            QMessageBox.warning(self, "警告", "请先编辑单次实验程序")
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
    
    def _refresh_step_list(self):
        """刷新步骤列表 - 中文显示，不同类型不同颜色，带详细参数"""
        self.step_list.clear()
        if self.single_experiment:
            for i, step in enumerate(self.single_experiment.steps):
                type_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
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
                return tv.upper()
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
        
        self.log_text.append(f'<span style="color:{color}; font-size:13px;">[{timestamp}] {msg}</span>')
    
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
            type_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
            detail = self._get_step_detail(step)
            msg_type = step.step_type.value if hasattr(step.step_type, 'value') else "info"
            self.log_message(f"▶ 步骤 {index+1} 开始: [{type_name}] {detail or step_id}", msg_type)
            
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
            # 配液时: 对应的配液泵亮绿灯
            if step.prep_sol_params:
                for sol_name in step.prep_sol_params.injection_order:
                    if step.prep_sol_params.selected_solutions.get(sol_name, False):
                        for ch in self.config.dilution_channels:
                            if ch.solution_name == sol_name:
                                self.pump_diagram.set_pump_state(ch.pump_address, 1 if running else 0)
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
            type_name = STEP_TYPE_NAMES.get(step.step_type, str(step.step_type))
            detail = f" [{type_name}]"
            # 关闭当前步骤的指示灯
            self._update_pump_indicators(step, running=False)
        
        self.log_message(f"{status} 步骤 {index+1}{detail} {'完成' if success else '失败'}", msg_type)
    
    @Slot(bool)
    def _on_experiment_finished(self, success: bool):
        """实验完成"""
        status = "成功完成" if success else "异常结束"
        self.status_exp.setText(f"状态: {status}")
        msg_type = "success" if success else "error"
        self.log_message(f"实验{status}", msg_type)
        
        # 重置所有泵状态和指示灯
        for i in range(12):
            self.pump_diagram.set_pump_state(i + 1, 0)
        self.process_widget.set_pump_states(False, False, False)
        
        # 清除步骤列表高亮
        for i in range(self.step_list.count()):
            self.step_list.item(i).setBackground(QColor(Qt.transparent))

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
                    self.single_experiment = Experiment.from_json_str(f.read())
                self._refresh_step_list()
                self.log_message(f"已加载上次实验: {self.single_experiment.exp_name}", "info")
            except Exception as e:
                print(f"⚠️ 加载上次实验失败: {e}")
    
    def closeEvent(self, event):
        """关闭窗口时自动断开RS485连接并保存实验"""
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

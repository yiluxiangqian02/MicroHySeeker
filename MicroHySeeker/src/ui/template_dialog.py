"""实验模板对话框。

包含：
- SaveTemplateDialog  : 将当前实验保存为模板（填写名称/描述/标签）。
- TemplateLibraryDialog: 浏览、加载和删除已保存的模板库。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QSplitter, QWidget, QFrame,
)

from src.core.template_manager import get_template_manager


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_FONT_NORMAL = QFont("Microsoft YaHei", 10)
_FONT_TITLE = QFont("Microsoft YaHei", 12, QFont.Bold)
_FONT_SMALL = QFont("Microsoft YaHei", 9)


# ---------------------------------------------------------------------------
# SaveTemplateDialog
# ---------------------------------------------------------------------------

class SaveTemplateDialog(QDialog):
    """将当前实验程序保存为可复用模板的对话框。

    调用示例::

        steps = [s.to_dict() for s in experiment.steps]
        dlg = SaveTemplateDialog(steps, parent=self)
        if dlg.exec() == QDialog.Accepted:
            # 模板已保存到 templates/ 目录
            pass
    """

    def __init__(
        self,
        steps: List[Dict[str, Any]],
        templates_dir: str = "./templates",
        parent=None,
    ):
        super().__init__(parent)
        self._steps = steps
        self._templates_dir = templates_dir
        self.setWindowTitle("保存为模板")
        self.setFixedSize(480, 340)
        self.setFont(_FONT_NORMAL)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(20, 16, 20, 16)

        # 标题
        title = QLabel("💾  保存实验为模板")
        title.setFont(_FONT_TITLE)
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep)

        # 表单
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(8)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("模板名称（必填）")
        self._name_edit.setFont(_FONT_NORMAL)
        form.addRow("名称 *", self._name_edit)

        self._desc_edit = QTextEdit()
        self._desc_edit.setPlaceholderText("模板描述（可选）")
        self._desc_edit.setFont(_FONT_NORMAL)
        self._desc_edit.setFixedHeight(70)
        form.addRow("描述", self._desc_edit)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("标签，逗号分隔，例如：CV, 酸性, 铂电极")
        self._tags_edit.setFont(_FONT_NORMAL)
        form.addRow("标签", self._tags_edit)

        root.addLayout(form)

        # 步骤数量提示
        hint = QLabel(f"📋  共 {len(self._steps)} 个实验步骤将被包含在模板中")
        hint.setFont(_FONT_SMALL)
        hint.setStyleSheet("color: #555;")
        root.addWidget(hint)

        root.addStretch()

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.setFixedWidth(80)
        self._btn_cancel.clicked.connect(self.reject)

        self._btn_save = QPushButton("保存模板")
        self._btn_save.setFixedWidth(100)
        self._btn_save.setStyleSheet(
            "QPushButton { background-color: #1976D2; color: white; "
            "border-radius: 4px; padding: 5px 10px; } "
            "QPushButton:hover { background-color: #1565C0; }"
        )
        self._btn_save.clicked.connect(self._on_save)

        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_save)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "模板名称不能为空。")
            self._name_edit.setFocus()
            return

        description = self._desc_edit.toPlainText().strip()
        raw_tags = self._tags_edit.text()
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

        mgr = get_template_manager(self._templates_dir)
        template = mgr.save(
            name=name,
            description=description,
            tags=tags,
            steps=self._steps,
        )

        QMessageBox.information(
            self,
            "保存成功",
            f"模板「{template['name']}」已保存到 templates/ 目录。\n"
            f"ID: {template['id'][:8]}…",
        )
        self.accept()


# ---------------------------------------------------------------------------
# TemplateLibraryDialog
# ---------------------------------------------------------------------------

class TemplateLibraryDialog(QDialog):
    """实验模板库对话框 — 浏览、加载和删除已保存模板。

    当用户选择模板并点击「加载到实验」时，发出 ``template_loaded`` 信号，
    携带完整模板字典，由主窗口处理步骤导入。

    调用示例::

        dlg = TemplateLibraryDialog(parent=self)
        dlg.template_loaded.connect(self._on_template_loaded)
        dlg.exec()
    """

    template_loaded = Signal(dict)  # 传递完整模板字典

    def __init__(self, templates_dir: str = "./templates", parent=None):
        super().__init__(parent)
        self._templates_dir = templates_dir
        self._current_template: Optional[Dict[str, Any]] = None

        self.setWindowTitle("模板库")
        self.setMinimumSize(820, 540)
        self.setFont(_FONT_NORMAL)
        self._build_ui()
        self._refresh_list()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # 标题栏
        header_row = QHBoxLayout()
        title = QLabel("📚  实验模板库")
        title.setFont(_FONT_TITLE)
        header_row.addWidget(title)
        header_row.addStretch()

        self._btn_refresh = QPushButton("🔄 刷新")
        self._btn_refresh.setFont(_FONT_SMALL)
        self._btn_refresh.setFixedWidth(70)
        self._btn_refresh.clicked.connect(self._refresh_list)
        header_row.addWidget(self._btn_refresh)
        root.addLayout(header_row)

        # 主分割区
        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧：模板列表 ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.addWidget(QLabel("模板列表"))

        self._list = QListWidget()
        self._list.setFont(_FONT_NORMAL)
        self._list.currentItemChanged.connect(self._on_item_changed)
        left_layout.addWidget(self._list)
        splitter.addWidget(left)

        # ── 右侧：模板详情 ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.addWidget(QLabel("模板详情"))

        detail_group = QGroupBox()
        detail_form = QFormLayout(detail_group)
        detail_form.setLabelAlignment(Qt.AlignRight)
        detail_form.setSpacing(6)

        self._detail_name = QLabel("—")
        self._detail_name.setFont(_FONT_NORMAL)
        self._detail_name.setWordWrap(True)
        detail_form.addRow("名称：", self._detail_name)

        self._detail_tags = QLabel("—")
        self._detail_tags.setFont(_FONT_SMALL)
        self._detail_tags.setWordWrap(True)
        detail_form.addRow("标签：", self._detail_tags)

        self._detail_steps = QLabel("—")
        self._detail_steps.setFont(_FONT_NORMAL)
        detail_form.addRow("步骤数：", self._detail_steps)

        self._detail_created = QLabel("—")
        self._detail_created.setFont(_FONT_SMALL)
        detail_form.addRow("创建时间：", self._detail_created)

        self._detail_updated = QLabel("—")
        self._detail_updated.setFont(_FONT_SMALL)
        detail_form.addRow("更新时间：", self._detail_updated)

        right_layout.addWidget(detail_group)

        # 描述文本
        right_layout.addWidget(QLabel("描述："))
        self._detail_desc = QTextEdit()
        self._detail_desc.setReadOnly(True)
        self._detail_desc.setFont(_FONT_NORMAL)
        self._detail_desc.setFixedHeight(100)
        right_layout.addWidget(self._detail_desc)

        # 步骤预览
        right_layout.addWidget(QLabel("步骤预览："))
        self._steps_preview = QListWidget()
        self._steps_preview.setFont(_FONT_SMALL)
        self._steps_preview.setFixedHeight(140)
        right_layout.addWidget(self._steps_preview)

        right_layout.addStretch()
        splitter.addWidget(right)

        splitter.setSizes([280, 520])
        root.addWidget(splitter, stretch=1)

        # ── 按钮行 ──
        btn_row = QHBoxLayout()

        self._btn_delete = QPushButton("🗑 删除模板")
        self._btn_delete.setFont(_FONT_NORMAL)
        self._btn_delete.setStyleSheet(
            "QPushButton { background-color: #D32F2F; color: white; "
            "border-radius: 4px; padding: 6px 12px; } "
            "QPushButton:hover { background-color: #B71C1C; } "
            "QPushButton:disabled { background-color: #ccc; color: #888; }"
        )
        self._btn_delete.setEnabled(False)
        self._btn_delete.clicked.connect(self._on_delete)

        btn_row.addWidget(self._btn_delete)
        btn_row.addStretch()

        self._btn_close = QPushButton("关闭")
        self._btn_close.setFont(_FONT_NORMAL)
        self._btn_close.setFixedWidth(80)
        self._btn_close.clicked.connect(self.reject)

        self._btn_load = QPushButton("📥 加载到实验")
        self._btn_load.setFont(_FONT_NORMAL)
        self._btn_load.setFixedWidth(130)
        self._btn_load.setStyleSheet(
            "QPushButton { background-color: #388E3C; color: white; "
            "border-radius: 4px; padding: 6px 12px; } "
            "QPushButton:hover { background-color: #2E7D32; } "
            "QPushButton:disabled { background-color: #ccc; color: #888; }"
        )
        self._btn_load.setEnabled(False)
        self._btn_load.clicked.connect(self._on_load)

        btn_row.addWidget(self._btn_close)
        btn_row.addWidget(self._btn_load)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _refresh_list(self) -> None:
        """重新加载模板列表。"""
        self._list.clear()
        self._clear_details()
        self._current_template = None
        self._btn_delete.setEnabled(False)
        self._btn_load.setEnabled(False)

        mgr = get_template_manager(self._templates_dir)
        templates = mgr.list_templates()

        if not templates:
            placeholder = QListWidgetItem("（暂无模板）")
            placeholder.setFlags(Qt.NoItemFlags)
            placeholder.setForeground(QColor("#999"))
            self._list.addItem(placeholder)
            return

        for tpl in templates:
            tags_str = "  #" + "  #".join(tpl.get("tags", [])) if tpl.get("tags") else ""
            steps_count = len(tpl.get("steps", []))
            display = f"[{steps_count}步] {tpl['name']}{tags_str}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, tpl["id"])
            item.setFont(_FONT_NORMAL)
            self._list.addItem(item)

    def _clear_details(self) -> None:
        self._detail_name.setText("—")
        self._detail_tags.setText("—")
        self._detail_steps.setText("—")
        self._detail_created.setText("—")
        self._detail_updated.setText("—")
        self._detail_desc.clear()
        self._steps_preview.clear()

    def _on_item_changed(self, current: QListWidgetItem, _previous) -> None:
        if current is None or not current.data(Qt.UserRole):
            self._clear_details()
            self._current_template = None
            self._btn_delete.setEnabled(False)
            self._btn_load.setEnabled(False)
            return

        template_id = current.data(Qt.UserRole)
        mgr = get_template_manager(self._templates_dir)
        tpl = mgr.load(template_id)

        if tpl is None:
            self._clear_details()
            return

        self._current_template = tpl

        # 填充详情
        self._detail_name.setText(tpl.get("name", "—"))
        tags = tpl.get("tags", [])
        self._detail_tags.setText(", ".join(tags) if tags else "（无标签）")
        steps = tpl.get("steps", [])
        self._detail_steps.setText(str(len(steps)))

        def _fmt_dt(iso_str: str) -> str:
            if not iso_str:
                return "—"
            try:
                dt = datetime.fromisoformat(iso_str)
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                return iso_str

        self._detail_created.setText(_fmt_dt(tpl.get("created_at", "")))
        self._detail_updated.setText(_fmt_dt(tpl.get("updated_at", "")))
        self._detail_desc.setPlainText(tpl.get("description", ""))

        # 步骤预览
        self._steps_preview.clear()
        _STEP_TYPE_ZH = {
            "transfer": "移液",
            "prep_sol": "配液",
            "flush": "冲洗",
            "echem": "电化学",
            "blank": "空白",
            "evacuate": "排空",
        }
        for i, step in enumerate(steps, start=1):
            stype = step.get("step_type", "")
            stype_zh = _STEP_TYPE_ZH.get(stype, stype)
            notes = step.get("notes", "")
            preview = f"  {i}. [{stype_zh}]" + (f"  {notes}" if notes else "")
            self._steps_preview.addItem(preview)

        self._btn_delete.setEnabled(True)
        self._btn_load.setEnabled(True)

    def _on_delete(self) -> None:
        if self._current_template is None:
            return

        name = self._current_template.get("name", "（未命名）")
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模板「{name}」吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        mgr = get_template_manager(self._templates_dir)
        mgr.delete(self._current_template["id"])
        self._refresh_list()

    def _on_load(self) -> None:
        if self._current_template is None:
            return

        name = self._current_template.get("name", "（未命名）")
        steps_count = len(self._current_template.get("steps", []))

        reply = QMessageBox.question(
            self,
            "加载模板",
            f"将模板「{name}」（{steps_count} 步骤）加载到当前实验？\n"
            f"当前实验的所有步骤将被替换。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        self.template_loaded.emit(dict(self._current_template))
        self.accept()

from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


def create_pump_table() -> QTableWidget:
    table = QTableWidget(12, 7)
    table.setHorizontalHeaderLabels(
        [
            "地址",
            "在线",
            "使能",
            "转速",
            "故障",
            "最后响应",
            "备注",
        ]
    )
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    for row in range(12):
        addr_text = f"0x{row + 1:02X}"
        table.setItem(row, 0, QTableWidgetItem(addr_text))
        table.setItem(row, 1, QTableWidgetItem("离线"))
        table.setItem(row, 2, QTableWidgetItem("-"))
        table.setItem(row, 3, QTableWidgetItem("-"))
        table.setItem(row, 4, QTableWidgetItem("-"))
        table.setItem(row, 5, QTableWidgetItem("-"))
        table.setItem(row, 6, QTableWidgetItem(""))
    table.resizeColumnsToContents()
    return table


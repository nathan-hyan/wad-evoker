import wad_importer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QAbstractItemView, QStyledItemDelegate
)
from PyQt6.QtCore import pyqtSignal, Qt, QRect
from PyQt6.QtGui import QFont, QColor, QPen, QBrush


class WadItemDelegate(QStyledItemDelegate):
    _DEH_ROLE = Qt.ItemDataRole.UserRole + 1

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not index.data(self._DEH_ROLE):
            return
        painter.save()
        r = option.rect
        tag_w, tag_h = 44, 16
        tag_x = r.right() - tag_w - 8
        tag_y = r.center().y() - tag_h // 2
        tag_rect = QRect(tag_x, tag_y, tag_w, tag_h)
        painter.setBrush(QBrush(QColor("#2a2a2a")))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawRoundedRect(tag_rect, 3, 3)
        font = QFont("Courier New", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#aaaaaa"))
        painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, "DEH")
        painter.restore()


class WadListWidget(QWidget):
    wad_selected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setObjectName("wadListContainer")
        self._wads = []
        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("  LIBRARY")
        header.setObjectName("listHeader")
        header.setFixedHeight(32)
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("wadList")
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.currentItemChanged.connect(self._on_item_changed)
        self.list_widget.setSpacing(1)
        self.list_widget.setItemDelegate(WadItemDelegate(self.list_widget))
        layout.addWidget(self.list_widget)

    def _apply_styles(self):
        self.setStyleSheet("""
            #wadListContainer {
                background: #111;
                border-right: 1px solid #2a2a2a;
            }

            #listHeader {
                background: #0d0d0d;
                color: #666;
                font-size: 10px;
                letter-spacing: 3px;
                font-family: 'Courier New', monospace;
                border-bottom: 1px solid #2a2a2a;
                padding-left: 8px;
            }

            #wadList {
                background: #111;
                border: none;
                outline: none;
                font-family: 'Courier New', monospace;
            }

            #wadList::item {
                padding: 10px 14px;
                border-bottom: 1px solid #1c1c1c;
                color: #ccc;
                font-size: 12px;
            }

            #wadList::item:selected {
                background: #1e0000;
                color: #ff4422;
                border-left: 3px solid #cc2200;
            }

            #wadList::item:hover:!selected {
                background: #181818;
                color: #e8e0d0;
            }
        """)

    def populate(self, wads):
        self._wads = wads
        self.list_widget.clear()
        for wad in wads:
            item = QListWidgetItem()
            item.setText(wad["title"])
            item.setData(Qt.ItemDataRole.UserRole, wad)
            item.setData(WadItemDelegate._DEH_ROLE, bool(wad_importer.find_deh_files(wad.get("filepath", ""))))
            item.setToolTip(wad.get("filename", ""))
            self.list_widget.addItem(item)

    def select_wad_by_id(self, wad_id):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            wad = item.data(Qt.ItemDataRole.UserRole)
            if wad and wad["id"] == wad_id:
                self.list_widget.setCurrentItem(item)
                return

    def _on_item_changed(self, current, previous):
        if current:
            wad = current.data(Qt.ItemDataRole.UserRole)
            if wad:
                self.wad_selected.emit(wad)

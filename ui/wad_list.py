import wad_importer
import sourceport
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QAbstractItemView, QStyledItemDelegate, QMenu,
    QStyleOptionViewItem
)
from PyQt6.QtCore import pyqtSignal, Qt, QRect
from PyQt6.QtGui import QFont, QColor, QPen, QBrush, QAction


class WadItemDelegate(QStyledItemDelegate):
    _DEH_ROLE = Qt.ItemDataRole.UserRole + 1
    _MULTI_WAD_ROLE = Qt.ItemDataRole.UserRole + 2
    _FINISHED_ROLE = Qt.ItemDataRole.UserRole + 3
    _SEPARATOR_ROLE = Qt.ItemDataRole.UserRole + 4

    def paint(self, painter, option, index):
        # Separator items get special rendering
        if index.data(self._SEPARATOR_ROLE):
            painter.save()
            r = option.rect
            painter.fillRect(r, QColor("#0d0d0d"))
            font = QFont("Courier New", 9)
            font.setBold(True)
            painter.setFont(font)
            fm = painter.fontMetrics()
            text = "FINISHED"
            text_w = fm.horizontalAdvance(text)
            text_gap = 10
            mid_y = r.center().y()
            text_x = r.left() + (r.width() - text_w) // 2
            painter.setPen(QPen(QColor("#2a2a2a"), 1))
            painter.drawLine(r.left() + 14, mid_y, text_x - text_gap, mid_y)
            painter.drawLine(text_x + text_w + text_gap, mid_y, r.right() - 14, mid_y)
            painter.setPen(QColor("#555555"))
            text_rect = QRect(r.left(), r.top(), r.width(), r.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()
            return

        has_deh = index.data(self._DEH_ROLE)
        has_multi = index.data(self._MULTI_WAD_ROLE)
        is_finished = index.data(self._FINISHED_ROLE)

        tag_w, tag_h = 44, 16
        tag_spacing = 4
        chips = []
        if is_finished:
            chips.append(("DONE", QColor("#0a2a0a"), QColor("#2a6a2a"), QColor("#44aa44")))
        if has_deh:
            chips.append(("DEH", QColor("#2a2a2a"), QColor("#555555"), QColor("#aaaaaa")))
        if has_multi:
            chips.append(("+WAD", QColor("#1a2a3a"), QColor("#3a6a9a"), QColor("#6aaaee")))

        # Reserve space for chips so the default text gets elided
        chips_total_w = 0
        if chips:
            chips_total_w = len(chips) * tag_w + (len(chips) - 1) * tag_spacing + 16

        # Draw background / selection with a narrower rect so text gets elided
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.textElideMode = Qt.TextElideMode.ElideRight
        if chips_total_w:
            opt.rect = QRect(option.rect.left(), option.rect.top(),
                             option.rect.width() - chips_total_w, option.rect.height())
        style = opt.widget.style() if opt.widget else None
        if style:
            style.drawControl(style.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        else:
            super().paint(painter, opt, index)

        if not chips:
            return

        painter.save()
        r = option.rect
        cursor_x = r.right() - 8
        for label, bg, border, fg in reversed(chips):
            tag_x = cursor_x - tag_w
            tag_y = r.center().y() - tag_h // 2
            tag_rect = QRect(tag_x, tag_y, tag_w, tag_h)
            painter.setBrush(QBrush(bg))
            painter.setPen(QPen(border, 1))
            painter.drawRoundedRect(tag_rect, 3, 3)
            font = QFont("Courier New", 8)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(fg)
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, label)
            cursor_x = tag_x - tag_spacing
        painter.restore()


class WadListWidget(QWidget):
    wad_selected = pyqtSignal(dict)
    play_requested = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    finish_toggled = pyqtSignal(dict)

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
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
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

        sort_mode = sourceport.get_finished_sort_mode()
        if sort_mode in ("separator", "bottom"):
            unfinished = [w for w in wads if not w.get("finished")]
            finished = [w for w in wads if w.get("finished")]
        else:
            unfinished = wads
            finished = []

        for wad in unfinished:
            self._add_wad_item(wad)

        if finished:
            if sort_mode == "separator":
                sep = QListWidgetItem()
                sep.setData(WadItemDelegate._SEPARATOR_ROLE, True)
                sep.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list_widget.addItem(sep)
            for wad in finished:
                self._add_wad_item(wad)

    def _add_wad_item(self, wad):
        item = QListWidgetItem()
        item.setText(wad["title"])
        item.setData(Qt.ItemDataRole.UserRole, wad)
        item.setData(WadItemDelegate._DEH_ROLE, bool(wad_importer.find_deh_files(wad.get("filepath", ""))))
        item.setData(WadItemDelegate._MULTI_WAD_ROLE, bool(wad.get("extra_wads")))
        item.setData(WadItemDelegate._FINISHED_ROLE,
                     bool(wad.get("finished")) and sourceport.get_show_finished_badge())
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

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        wad = item.data(Qt.ItemDataRole.UserRole)
        if not wad:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 6px 24px;
            }
            QMenu::item:selected {
                background: #2a1a1a;
                color: #ff6644;
            }
            QMenu::separator {
                height: 1px;
                background: #2a2a2a;
                margin: 4px 8px;
            }
        """)

        act_play = menu.addAction("▶  Play")
        act_edit = menu.addAction("✎  Edit")
        menu.addSeparator()

        is_finished = bool(wad.get("finished"))
        if is_finished:
            act_finish = menu.addAction("Mark as Unfinished")
        else:
            act_finish = menu.addAction("✓  Mark as Finished")

        menu.addSeparator()
        act_delete = menu.addAction("Remove from Library")

        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if action == act_play:
            self.play_requested.emit(wad)
        elif action == act_edit:
            self.edit_requested.emit(wad)
        elif action == act_finish:
            self.finish_toggled.emit(wad)
        elif action == act_delete:
            self.delete_requested.emit(wad)

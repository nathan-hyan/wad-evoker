import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QLineEdit, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QPixmap


class MapListWidget(QWidget):
    """Compact scrollable column showing map names, optionally with MAPINFO titles."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel("MAPS")
        lbl.setObjectName("sectionLabel")
        layout.addWidget(lbl)

        self.text = QTextEdit()
        self.text.setObjectName("mapListText")
        self.text.setReadOnly(True)
        self.text.setMinimumHeight(80)
        self.text.setMaximumHeight(200)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.text)

    def set_maps(self, map_list_str):
        """map_list_str is a newline-separated string from the DB, or empty."""
        if map_list_str:
            self.text.setPlainText(map_list_str)
        else:
            self.text.setPlainText("")
        self.setVisible(bool(map_list_str))


class TagChip(QWidget):
    removed = pyqtSignal(str)

    def __init__(self, tag):
        super().__init__()
        self.tag = tag
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 4, 3)
        layout.setSpacing(4)

        lbl = QLabel(tag)
        lbl.setObjectName("chipLabel")
        layout.addWidget(lbl)

        btn = QPushButton("×")
        btn.setObjectName("chipRemove")
        btn.setFixedSize(16, 16)
        btn.clicked.connect(lambda: self.removed.emit(self.tag))
        layout.addWidget(btn)

        self.setObjectName("tagChip")
        self.setStyleSheet("""
            #tagChip {
                background: #2a0000;
                border: 1px solid #cc2200;
                border-radius: 3px;
            }
            #chipLabel {
                color: #ff6644;
                font-size: 11px;
                font-family: 'Courier New', monospace;
            }
            #chipRemove {
                background: transparent;
                border: none;
                color: #cc2200;
                font-size: 13px;
                font-weight: bold;
                padding: 0;
            }
            #chipRemove:hover { color: #ff4422; }
        """)


class TagsWidget(QWidget):
    tags_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._tags = []
        self._build_ui()

    def _build_ui(self):
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(6)

        lbl = QLabel("TAGS")
        lbl.setObjectName("sectionLabel")
        self.outer.addWidget(lbl)

        # Chips row
        self.chips_widget = QWidget()
        self.chips_layout = QHBoxLayout(self.chips_widget)
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(6)
        self.chips_layout.addStretch()
        self.outer.addWidget(self.chips_widget)

        # Input row
        row = QHBoxLayout()
        row.setSpacing(6)
        self.tag_input = QLineEdit()
        self.tag_input.setObjectName("tagInput")
        self.tag_input.setPlaceholderText("Add tag…")
        self.tag_input.setFixedHeight(28)
        self.tag_input.returnPressed.connect(self._add_tag)
        row.addWidget(self.tag_input)

        btn = QPushButton("Add")
        btn.setObjectName("btnAddTag")
        btn.setFixedHeight(28)
        btn.clicked.connect(self._add_tag)
        row.addWidget(btn)
        row.addStretch()
        self.outer.addLayout(row)

    def set_tags(self, tags):
        self._tags = list(tags)
        self._rebuild_chips()

    def _add_tag(self):
        text = self.tag_input.text().strip()
        if text and text not in self._tags:
            self._tags.append(text)
            self._rebuild_chips()
            self.tags_changed.emit(self._tags)
        self.tag_input.clear()

    def _remove_tag(self, tag):
        if tag in self._tags:
            self._tags.remove(tag)
            self._rebuild_chips()
            self.tags_changed.emit(self._tags)

    def _rebuild_chips(self):
        # Clear existing chips (leave the stretch)
        while self.chips_layout.count() > 1:
            item = self.chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for tag in self._tags:
            chip = TagChip(tag)
            chip.removed.connect(self._remove_tag)
            self.chips_layout.insertWidget(self.chips_layout.count() - 1, chip)


class WadDetailPanel(QWidget):
    launch_requested = pyqtSignal(int, str)
    edit_requested = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    tags_changed = pyqtSignal(int, list)

    def __init__(self):
        super().__init__()
        self._current_wad = None
        self._build_ui()
        self._apply_styles()
        self.clear()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll area for all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("detailScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content.setObjectName("detailContent")
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Empty state
        self.empty_label = QLabel("← Select a WAD from the library")
        self.empty_label.setObjectName("emptyLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

        # Detail content (hidden until WAD selected)
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(20)

        # Title + launch row
        title_row = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setObjectName("wadTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_row.addWidget(self.title_label, 1)

        self.btn_edit = QPushButton("✎  EDIT")
        self.btn_edit.setObjectName("btnEdit")
        self.btn_edit.setFixedSize(100, 40)
        self.btn_edit.clicked.connect(self._on_edit)
        title_row.addWidget(self.btn_edit)

        self.btn_launch = QPushButton("▶  LAUNCH")
        self.btn_launch.setObjectName("btnLaunch")
        self.btn_launch.setFixedSize(120, 40)
        self.btn_launch.clicked.connect(self._on_launch)
        title_row.addWidget(self.btn_launch)
        detail_layout.addLayout(title_row)

        # Meta grid
        self.meta_widget = QWidget()
        meta_layout = QVBoxLayout(self.meta_widget)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(4)

        self.lbl_filename = self._make_meta_row("FILE")
        self.lbl_author   = self._make_meta_row("AUTHOR")
        self.lbl_year     = self._make_meta_row("YEAR")
        self.lbl_game     = self._make_meta_row("GAME")
        self.lbl_played   = self._make_meta_row("LAST PLAYED")

        for row in [self.lbl_filename, self.lbl_author, self.lbl_year,
                    self.lbl_game, self.lbl_played]:
            meta_layout.addWidget(row)

        # Meta + map list + TITLEPIC side-by-side
        meta_and_pic = QHBoxLayout()
        meta_and_pic.setSpacing(16)
        meta_and_pic.addWidget(self.meta_widget, 1)

        self.titlepic_label = QLabel()
        self.titlepic_label.setObjectName("titlepicLabel")
        self.titlepic_label.setFixedSize(200, 125)
        self.titlepic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titlepic_label.hide()
        meta_and_pic.addWidget(self.titlepic_label, 0, Qt.AlignmentFlag.AlignTop)

        detail_layout.addLayout(meta_and_pic)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setObjectName("innerDivider")
        detail_layout.addWidget(div)

        # Description
        desc_lbl = QLabel("DESCRIPTION")
        desc_lbl.setObjectName("sectionLabel")
        detail_layout.addWidget(desc_lbl)

        self.desc_text = QTextEdit()
        self.desc_text.setObjectName("descText")
        self.desc_text.setReadOnly(True)
        self.desc_text.setMaximumHeight(140)
        detail_layout.addWidget(self.desc_text)

        self.map_list_widget = MapListWidget()
        self.map_list_widget.hide()
        detail_layout.addWidget(self.map_list_widget)

        # Tags
        self.tags_widget = TagsWidget()
        self.tags_widget.tags_changed.connect(self._on_tags_changed)
        detail_layout.addWidget(self.tags_widget)

        detail_layout.addStretch()

        # Delete button at bottom
        btn_delete = QPushButton("Remove from Library")
        btn_delete.setObjectName("btnDelete")
        btn_delete.clicked.connect(self._on_delete)
        detail_layout.addWidget(btn_delete, alignment=Qt.AlignmentFlag.AlignRight)

        self.detail_widget.hide()
        layout.addWidget(self.detail_widget)
        layout.addStretch()

        scroll.setWidget(self.content)
        root.addWidget(scroll)

    def _make_meta_row(self, key):
        row = QWidget()
        row.setObjectName("metaRow")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(12)
        key_lbl = QLabel(key)
        key_lbl.setObjectName("metaKey")
        key_lbl.setFixedWidth(90)
        val_lbl = QLabel()
        val_lbl.setObjectName("metaVal")
        val_lbl.setWordWrap(True)
        hl.addWidget(key_lbl)
        hl.addWidget(val_lbl, 1)
        row._val_label = val_lbl
        return row

    def _apply_styles(self):
        self.setStyleSheet("""
            QScrollArea, #detailContent {
                background: #141414;
                border: none;
            }

            #emptyLabel {
                color: #444;
                font-size: 14px;
                font-family: 'Courier New', monospace;
                font-style: italic;
            }

            #wadTitle {
                font-size: 22px;
                font-weight: bold;
                color: #ff4422;
                font-family: 'Courier New', monospace;
                letter-spacing: 1px;
            }

            #btnLaunch {
                background: #8b0000;
                color: #ffddcc;
                border: 2px solid #cc2200;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 13px;
                letter-spacing: 2px;
            }
            #btnLaunch:hover {
                background: #aa0000;
                border-color: #ff4422;
                color: #fff;
            }
            #btnLaunch:pressed { background: #6b0000; }

            #btnEdit {
                background: #1e1e1e;
                color: #ccc;
                border: 2px solid #3a3a3a;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 2px;
            }
            #btnEdit:hover {
                border-color: #cc2200;
                color: #ff4422;
                background: #181818;
            }
            #btnEdit:pressed { background: #111; }

            #metaKey {
                color: #666;
                font-size: 10px;
                letter-spacing: 2px;
                font-family: 'Courier New', monospace;
            }
            #metaVal {
                color: #ccc;
                font-size: 12px;
                font-family: 'Courier New', monospace;
            }

            #innerDivider { background: #2a2a2a; max-height: 1px; }

            #sectionLabel {
                color: #666;
                font-size: 10px;
                letter-spacing: 3px;
                font-family: 'Courier New', monospace;
            }

            #titlepicLabel {
                background: #0a0a0a;
                border: 1px solid #2a2a2a;
                border-radius: 3px;
            }

            #mapListText {
                background: #111;
                border: 1px solid #2a2a2a;
                border-radius: 3px;
                color: #aaa;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 6px;
            }

            #descText {
                background: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 3px;
                color: #aaa;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }

            #tagInput {
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                color: #ccc;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 3px 8px;
            }
            #tagInput:focus { border-color: #cc2200; }

            #btnAddTag {
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                color: #ccc;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 3px 12px;
            }
            #btnAddTag:hover { border-color: #cc2200; color: #ff4422; }

            #btnDelete {
                background: transparent;
                border: 1px solid #3a3a3a;
                color: #555;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 4px 10px;
            }
            #btnDelete:hover { border-color: #8b0000; color: #cc2200; }
        """)

    # ── PUBLIC ────────────────────────────────────────────────────────────────

    def show_wad(self, wad, tags):
        self._current_wad = wad
        self.empty_label.hide()
        self.detail_widget.show()

        self.title_label.setText(wad["title"])
        self.lbl_filename._val_label.setText(wad.get("filename", "—"))
        self.lbl_author._val_label.setText(wad.get("author") or "—")
        self.lbl_year._val_label.setText(wad.get("year") or "—")
        self.lbl_game._val_label.setText(wad.get("game") or "—")

        lp = wad.get("last_played")
        self.lbl_played._val_label.setText(lp[:16].replace("T", " ") if lp else "Never")

        self.desc_text.setPlainText(wad.get("description") or "No description available.")

        ml = wad.get("map_list") or ""
        self.map_list_widget.set_maps(ml)
        if ml:
            self.map_list_widget.show()
        else:
            self.map_list_widget.hide()

        self.tags_widget.set_tags(tags)

        tp = wad.get("titlepic_path")
        if tp and os.path.isfile(tp):
            px = QPixmap(tp).scaled(
                200, 125,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.titlepic_label.setPixmap(px)
            self.titlepic_label.show()
        else:
            self.titlepic_label.setPixmap(QPixmap())
            self.titlepic_label.hide()

    def clear(self):
        self._current_wad = None
        self.empty_label.show()
        self.detail_widget.hide()

    # ── SLOTS ─────────────────────────────────────────────────────────────────

    def _on_launch(self):
        if self._current_wad:
            self.launch_requested.emit(self._current_wad["id"], self._current_wad["filepath"])

    def _on_edit(self):
        if self._current_wad:
            self.edit_requested.emit(self._current_wad["id"])

    def _on_delete(self):
        if self._current_wad:
            self.delete_requested.emit(self._current_wad["id"])

    def _on_tags_changed(self, tags):
        if self._current_wad:
            self.tags_changed.emit(self._current_wad["id"], tags)

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QListWidget,
    QListWidgetItem, QAbstractItemView
)
from PyQt6.QtCore import Qt

import db


class GameplayModLaunchDialog(QDialog):
    """Modal dialog shown when launching a gameplay mod entry.

    Presents a searchable list of non-gameplay-mod WADs from the library
    so the user can pick one to play alongside the mod, or skip to launch
    with just the source port's default IWAD.
    """

    def __init__(self, mod_title, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Launch Gameplay Mod")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(420)
        self._selected_wad = None
        self._all_wads = []
        self._build_ui(mod_title)
        self._apply_styles()
        self._load_wads()

    def _build_ui(self, mod_title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        title = QLabel("LAUNCH GAMEPLAY MOD")
        title.setObjectName("dlgTitle")
        layout.addWidget(title)

        desc = QLabel(
            f'Select a WAD to play with "{mod_title}",\n'
            "or skip to launch with just the default IWAD."
        )
        desc.setObjectName("dlgDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setObjectName("dlgDivider")
        layout.addWidget(div)

        search_lbl = QLabel("SEARCH LIBRARY")
        search_lbl.setObjectName("sectionLabel")
        layout.addWidget(search_lbl)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("Filter WADs…")
        self.search_input.setFixedHeight(30)
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)

        self.wad_list = QListWidget()
        self.wad_list.setObjectName("wadPickerList")
        self.wad_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.wad_list.setMinimumHeight(200)
        layout.addWidget(self.wad_list, 1)

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setObjectName("dlgDivider")
        layout.addWidget(div2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnDlgCancel")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_skip = QPushButton("Skip (IWAD only)")
        btn_skip.setObjectName("btnDlgSkip")
        btn_skip.setFixedHeight(36)
        btn_skip.clicked.connect(self._on_skip)
        btn_row.addWidget(btn_skip)

        btn_launch = QPushButton("▶  LAUNCH")
        btn_launch.setObjectName("btnDlgLaunch")
        btn_launch.setFixedHeight(36)
        btn_launch.setDefault(True)
        btn_launch.clicked.connect(self._on_launch)
        btn_row.addWidget(btn_launch)

        layout.addLayout(btn_row)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: #141414;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
            }
            #dlgTitle {
                color: #cc2200;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 3px;
                font-family: 'Courier New', monospace;
            }
            #dlgDesc {
                color: #aaa;
                font-size: 12px;
                font-family: 'Courier New', monospace;
            }
            #dlgDivider {
                background: #2a2a2a;
                max-height: 1px;
            }
            #sectionLabel {
                color: #666;
                font-size: 10px;
                letter-spacing: 3px;
                font-family: 'Courier New', monospace;
            }
            #searchInput {
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 4px 10px;
            }
            #searchInput:focus { border-color: #cc2200; }
            #wadPickerList {
                background: #111;
                border: 1px solid #2a2a2a;
                border-radius: 3px;
                color: #ccc;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                outline: none;
            }
            #wadPickerList::item {
                padding: 8px 12px;
                border-bottom: 1px solid #1c1c1c;
            }
            #wadPickerList::item:selected {
                background: #1e0000;
                color: #ff4422;
                border-left: 3px solid #cc2200;
            }
            #wadPickerList::item:hover:!selected {
                background: #181818;
                color: #e8e0d0;
            }
            #btnDlgLaunch {
                background: #8b0000;
                color: #ffddcc;
                border: 2px solid #cc2200;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 2px;
                padding: 4px 20px;
            }
            #btnDlgLaunch:hover {
                background: #aa0000;
                border-color: #ff4422;
                color: #fff;
            }
            #btnDlgLaunch:pressed { background: #6b0000; }
            #btnDlgCancel {
                background: #1e1e1e;
                color: #ccc;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 4px 16px;
            }
            #btnDlgCancel:hover {
                border-color: #666;
                color: #e8e0d0;
            }
            #btnDlgSkip {
                background: #1e1e1e;
                color: #ccc;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 4px 16px;
            }
            #btnDlgSkip:hover {
                border-color: #8a6a2a;
                color: #ddaa44;
            }
        """)

    def _load_wads(self):
        self._all_wads = [
            w for w in db.get_all_wads()
            if not w.get("is_gameplay_mod")
        ]
        self._populate_list(self._all_wads)

    def _populate_list(self, wads):
        self.wad_list.clear()
        for wad in wads:
            item = QListWidgetItem()
            label = wad["title"]
            author = wad.get("author")
            if author:
                label += f"  ({author})"
            item.setText(label)
            item.setData(Qt.ItemDataRole.UserRole, wad)
            self.wad_list.addItem(item)

    def _on_search(self, text):
        text = text.strip().lower()
        if not text:
            self._populate_list(self._all_wads)
            return
        filtered = [
            w for w in self._all_wads
            if text in (w.get("title") or "").lower()
            or text in (w.get("author") or "").lower()
            or text in (w.get("filename") or "").lower()
        ]
        self._populate_list(filtered)

    def _on_skip(self):
        self._selected_wad = None
        self.accept()

    def _on_launch(self):
        current = self.wad_list.currentItem()
        if current:
            self._selected_wad = current.data(Qt.ItemDataRole.UserRole)
        else:
            self._selected_wad = None
        self.accept()

    def selected_wad(self):
        """Return the selected WAD dict, or None if skipped."""
        return self._selected_wad

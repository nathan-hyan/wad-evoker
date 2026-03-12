import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QLineEdit, QTextEdit, QFormLayout,
    QDialogButtonBox, QWidget, QPushButton, QFileDialog, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt

import db
import sqlite3


class WadEditDialog(QDialog):
    def __init__(self, wad_id, parent=None):
        super().__init__(parent)
        self._wad_id = wad_id
        self._wad = None
        self._sidecar_txt_path = None

        self._left_fixed_width = 560
        self._sidecar_min_width = 320

        self.setWindowTitle("Edit WAD")
        self.setModal(True)

        self._build_ui()
        self._apply_styles()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        title = QLabel("EDIT WAD")
        title.setObjectName("editTitle")
        layout.addWidget(title)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setObjectName("editDivider")
        layout.addWidget(div)

        body = QHBoxLayout()
        body.setSpacing(16)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        form_host = QWidget()
        form = QFormLayout(form_host)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setObjectName("textInput")

        self.author_input = QLineEdit()
        self.author_input.setObjectName("textInput")

        self.year_input = QLineEdit()
        self.year_input.setObjectName("textInput")

        self.game_input = QComboBox()
        self.game_input.setObjectName("comboInput")
        self.game_input.addItem("")
        self.game_input.addItem("Doom")
        self.game_input.addItem("Doom 2")
        self.game_input.addItem("Final Doom: TNT Evilution")
        self.game_input.addItem("Final Doom: The Plutonia Experiment")

        self.filepath_input = QLineEdit()
        self.filepath_input.setObjectName("textInput")
        self.filepath_input.textChanged.connect(self._on_filepath_changed)

        self.btn_browse_wad = QPushButton("Browse…")
        self.btn_browse_wad.setObjectName("btnBrowse")
        self.btn_browse_wad.clicked.connect(self._browse_wad)

        filepath_row = QWidget()
        filepath_row_layout = QHBoxLayout(filepath_row)
        filepath_row_layout.setContentsMargins(0, 0, 0, 0)
        filepath_row_layout.setSpacing(8)
        filepath_row_layout.addWidget(self.filepath_input, 1)
        filepath_row_layout.addWidget(self.btn_browse_wad)

        self.filename_input = QLineEdit()
        self.filename_input.setObjectName("textInput")
        self.filename_input.setReadOnly(True)

        form.addRow("Title", self.title_input)
        form.addRow("Author", self.author_input)
        form.addRow("Year", self.year_input)
        form.addRow("Game", self.game_input)
        form.addRow("Filename", self.filename_input)
        form.addRow("File path", filepath_row)

        left_layout.addWidget(form_host)

        # Text areas
        desc_lbl = QLabel("DESCRIPTION")
        desc_lbl.setObjectName("sectionLabel")
        left_layout.addWidget(desc_lbl)
        self.desc_text = QTextEdit()
        self.desc_text.setObjectName("editTextArea")
        self.desc_text.setAcceptRichText(False)
        self.desc_text.setMinimumHeight(120)
        left_layout.addWidget(self.desc_text, 1)

        maps_lbl = QLabel("MAP LIST")
        maps_lbl.setObjectName("sectionLabel")
        left_layout.addWidget(maps_lbl)
        self.map_list_text = QTextEdit()
        self.map_list_text.setObjectName("editTextArea")
        self.map_list_text.setAcceptRichText(False)
        self.map_list_text.setMinimumHeight(120)
        left_layout.addWidget(self.map_list_text, 1)

        left.setFixedWidth(self._left_fixed_width)
        left.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        body.addWidget(left, 0)

        # Right: sidecar txt preview (collapsible)
        self.sidecar_panel = QWidget()
        self.sidecar_panel.setObjectName("sidecarPanel")
        sidecar_layout = QVBoxLayout(self.sidecar_panel)
        sidecar_layout.setContentsMargins(0, 0, 0, 0)
        sidecar_layout.setSpacing(8)

        self.sidecar_txt = QTextEdit()
        self.sidecar_txt.setObjectName("editTextArea")
        self.sidecar_txt.setReadOnly(True)
        self.sidecar_txt.setAcceptRichText(False)
        self.sidecar_txt.setMinimumWidth(self._sidecar_min_width)
        sidecar_layout.addWidget(self.sidecar_txt, 1)

        self.sidecar_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body.addWidget(self.sidecar_panel, 1)

        layout.addLayout(body, 1)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("hintLabel")
        layout.addWidget(self.hint_label)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.btn_toggle_txt = QPushButton("Hide .txt")
        self.btn_toggle_txt.setObjectName("btnToggle")
        self.btn_toggle_txt.clicked.connect(self._toggle_sidecar)
        bottom_row.addWidget(self.btn_toggle_txt)

        self.btn_choose_txt = QPushButton("Choose .txt…")
        self.btn_choose_txt.setObjectName("btnBrowse")
        self.btn_choose_txt.clicked.connect(self._choose_sidecar_txt)
        bottom_row.addWidget(self.btn_choose_txt)

        bottom_row.addStretch()

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("btnSave")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("btnCancel")
        bottom_row.addWidget(btns)

        layout.addLayout(bottom_row)

        margins = layout.contentsMargins()
        min_w = (
            margins.left() + margins.right() +
            self._left_fixed_width +
            body.spacing() +
            self._sidecar_min_width
        )
        self.setMinimumWidth(min_w)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: #141414;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
            }

            #editTitle {
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 4px;
                color: #cc2200;
            }

            #editDivider { background: #2a2a2a; max-height: 1px; }

            QLabel { color: #888; font-size: 11px; }

            #sectionLabel {
                color: #666;
                font-size: 10px;
                letter-spacing: 3px;
                font-family: 'Courier New', monospace;
            }

            #textInput {
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 6px 10px;
            }
            #textInput:focus { border-color: #cc2200; }

            #comboInput {
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 6px 10px;
            }
            #comboInput:focus { border-color: #cc2200; }

            #editTextArea {
                background: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 3px;
                color: #aaa;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 8px;
            }

            #hintLabel { font-size: 11px; }

            #btnSave {
                background: #8b0000;
                border: none;
                color: #ffddcc;
                border-radius: 3px;
                padding: 6px 20px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
            }
            #btnSave:hover { background: #aa0000; }

            #btnCancel {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                color: #aaa;
                border-radius: 3px;
                padding: 6px 16px;
                font-family: 'Courier New', monospace;
            }
            #btnCancel:hover { border-color: #555; color: #ccc; }

            #btnBrowse {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                color: #ccc;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                padding: 6px 14px;
            }
            #btnBrowse:hover { border-color: #cc2200; color: #ff4422; }

            #btnToggle {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                color: #ccc;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                padding: 6px 14px;
            }
            #btnToggle:hover { border-color: #555; color: #e8e0d0; }

            #sidecarPanel {
                background: transparent;
            }
        """)

    def _load(self):
        self._wad = db.get_wad_by_id(self._wad_id)
        if not self._wad:
            self.hint_label.setText("WAD not found.")
            self.hint_label.setStyleSheet("color: #cc2200;")
            return

        self.title_input.setText(self._wad.get("title") or "")
        self.author_input.setText(self._wad.get("author") or "")
        self.year_input.setText(self._wad.get("year") or "")
        self._set_game(self._wad.get("game") or "")
        self.filename_input.setText(self._wad.get("filename") or "")
        self.filepath_input.setText(self._wad.get("filepath") or "")

        self.desc_text.setPlainText(self._wad.get("description") or "")
        self.map_list_text.setPlainText(self._wad.get("map_list") or "")

        txt_path = self._find_sidecar_txt(self._wad.get("filepath") or "", self._wad.get("filename") or "")
        self._load_sidecar_txt(txt_path)
        self._set_sidecar_visible(bool(txt_path))

    def _set_game(self, game):
        game = (game or "").strip()
        idx = self.game_input.findText(game)
        if idx >= 0:
            self.game_input.setCurrentIndex(idx)
        else:
            self.game_input.setCurrentIndex(0)

    def _browse_wad(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select WAD / PK3 / ZIP",
            os.path.expanduser("~"),
            "Doom files (*.wad *.pk3 *.zip);;All files (*)"
        )
        if path:
            self.filepath_input.setText(path)

    def _on_filepath_changed(self, text):
        text = (text or "").strip()
        self.filename_input.setText(os.path.basename(text) if text else "")

    def _toggle_sidecar(self):
        self._set_sidecar_visible(not self.sidecar_txt.isVisible())

    def _set_sidecar_visible(self, visible):
        self.sidecar_txt.setVisible(visible)
        self.btn_toggle_txt.setText("Hide .txt" if visible else "Show .txt")

    def _choose_sidecar_txt(self):
        start_dir = os.path.dirname(self.filepath_input.text().strip()) or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Sidecar .txt",
            start_dir,
            "Text files (*.txt);;All files (*)"
        )
        if path:
            self._load_sidecar_txt(path)
            self._set_sidecar_visible(True)

    def _load_sidecar_txt(self, txt_path):
        self._sidecar_txt_path = txt_path if txt_path else None
        if txt_path and os.path.isfile(txt_path):
            try:
                with open(txt_path, "rb") as f:
                    data = f.read()
                text = self._decode_text_best_effort(data)
                self.sidecar_txt.setPlainText(text)
                return
            except OSError:
                self.sidecar_txt.setPlainText("Could not read sidecar .txt.")
                return
        self.sidecar_txt.setPlainText("No sidecar .txt selected/found.")

    def _decode_text_best_effort(self, data: bytes) -> str:
        if not data:
            return ""

        candidates = [
            "utf-8",
            "utf-8-sig",
            "utf-16",
            "cp1252",
            "cp437",
            "latin-1",
        ]

        best_text = None
        best_score = None

        for enc in candidates:
            try:
                decoded = data.decode(enc, errors="strict")
            except Exception:
                continue

            score = self._text_sanity_score(decoded)
            if best_score is None or score > best_score:
                best_score = score
                best_text = decoded

        if best_text is not None:
            return best_text

        return data.decode("utf-8", errors="replace")

    def _text_sanity_score(self, text: str) -> float:
        if not text:
            return 0.0

        n = len(text)
        good = 0
        bad = 0

        for ch in text:
            o = ord(ch)

            if ch in "\n\r\t":
                good += 1
                continue

            # Favor typical printable ASCII and common Latin-1 punctuation.
            if 32 <= o <= 126:
                good += 1
                continue
            if 160 <= o <= 255:
                good += 1
                continue

            # Penalize replacement and control chars.
            if ch == "\ufffd" or o < 32:
                bad += 2
                continue

            # Slight penalty for other uncommon unicode.
            bad += 1

        # Normalize: prefer texts with fewer bad chars.
        return (good - bad) / max(1, n)

    def _find_sidecar_txt(self, wad_filepath, wad_filename):
        try:
            directory = os.path.dirname(wad_filepath)
            if not directory:
                return None
            base = os.path.splitext(wad_filename)[0]
            for fname in os.listdir(directory):
                if fname.lower().endswith(".txt") and fname.lower().startswith(base.lower()):
                    return os.path.join(directory, fname)
            for fname in os.listdir(directory):
                if fname.lower().endswith(".txt"):
                    return os.path.join(directory, fname)
        except OSError:
            return None
        return None

    def _save(self):
        if not self._wad:
            return

        title = self.title_input.text().strip()
        if not title:
            self.hint_label.setText("Title cannot be empty.")
            self.hint_label.setStyleSheet("color: #cc8800;")
            return

        filepath = self.filepath_input.text().strip()
        if not filepath:
            self.hint_label.setText("File path cannot be empty.")
            self.hint_label.setStyleSheet("color: #cc8800;")
            return
        if not os.path.isfile(filepath):
            self.hint_label.setText("WAD file not found at the given path.")
            self.hint_label.setStyleSheet("color: #cc8800;")
            return

        try:
            db.update_wad(
                self._wad_id,
                title=title,
                filename=os.path.basename(filepath),
                filepath=filepath,
                author=self.author_input.text().strip() or "",
                year=self.year_input.text().strip() or "",
                game=self.game_input.currentText().strip() or "",
                description=self.desc_text.toPlainText().strip() or "",
                map_list=self.map_list_text.toPlainText().strip() or "",
            )
        except sqlite3.IntegrityError:
            self.hint_label.setText("That file is already in your library.")
            self.hint_label.setStyleSheet("color: #cc2200;")
            return

        self.accept()

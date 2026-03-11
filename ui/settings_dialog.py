import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QFrame, QDialogButtonBox
)
from PyQt6.QtCore import Qt

import sourceport


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._build_ui()
        self._apply_styles()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(20)

        # Title
        title = QLabel("SETTINGS")
        title.setObjectName("settingsTitle")
        layout.addWidget(title)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setObjectName("settingsDivider")
        layout.addWidget(div)

        # ── Source Port ──────────────────────────────────────────────────────
        sp_label = QLabel("SOURCE PORT")
        sp_label.setObjectName("sectionLabel")
        layout.addWidget(sp_label)

        desc = QLabel(
            "Choose the executable for your source port.\n"
            "This can be GZDoom, DSDA-Doom, Crispy Doom, or any compatible port."
        )
        desc.setObjectName("settingsDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.binary_input = QLineEdit()
        self.binary_input.setObjectName("binaryInput")
        self.binary_input.setPlaceholderText("/usr/bin/gzdoom  or  /opt/dsda-doom/dsda-doom  …")
        row.addWidget(self.binary_input, 1)

        btn_browse = QPushButton("Browse…")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.clicked.connect(self._browse)
        row.addWidget(btn_browse)

        layout.addLayout(row)

        # Validation hint
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("hintLabel")
        layout.addWidget(self.hint_label)

        layout.addStretch()

        # Dialog buttons
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("btnSave")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("btnCancel")
        layout.addWidget(btns)

        self.binary_input.textChanged.connect(self._validate)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: #141414;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
            }

            #settingsTitle {
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 4px;
                color: #cc2200;
            }

            #settingsDivider { background: #2a2a2a; max-height: 1px; }

            #sectionLabel {
                color: #666;
                font-size: 10px;
                letter-spacing: 3px;
            }

            #settingsDesc {
                color: #888;
                font-size: 12px;
                line-height: 1.5;
            }

            #binaryInput {
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 6px 10px;
            }
            #binaryInput:focus { border-color: #cc2200; }

            #btnBrowse {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                color: #ccc;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                padding: 6px 14px;
            }
            #btnBrowse:hover { border-color: #cc2200; color: #ff4422; }

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
        """)

    def _load(self):
        current = sourceport.get_source_port()
        self.binary_input.setText(current)
        self._validate(current)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Source Port Executable",
            os.path.expanduser("~"),
            "Executables (*)"
        )
        if path:
            self.binary_input.setText(path)

    def _validate(self, text):
        text = text.strip()
        if not text:
            self.hint_label.setText("")
            self.hint_label.setStyleSheet("")
            return
        if not os.path.isfile(text):
            self.hint_label.setText("⚠  File not found.")
            self.hint_label.setStyleSheet("color: #cc8800;")
        elif not os.access(text, os.X_OK):
            self.hint_label.setText("⚠  File exists but is not executable.")
            self.hint_label.setStyleSheet("color: #cc8800;")
        else:
            name = os.path.basename(text)
            self.hint_label.setText(f"✓  {name} found and executable.")
            self.hint_label.setStyleSheet("color: #44aa44;")

    def _save(self):
        path = self.binary_input.text().strip()
        sourceport.set_source_port(path)
        self.accept()

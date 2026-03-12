import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QFrame, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer

import sourceport
from updater import UpdateCheckWorker, UpdateDownloadWorker, restart_app
from version import __version__


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
            "This can be UZDoom, DSDA-Doom, Crispy Doom, or any compatible port."
        )
        desc.setObjectName("settingsDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.binary_input = QLineEdit()
        self.binary_input.setObjectName("binaryInput")
        self.binary_input.setPlaceholderText("/usr/bin/UZDoom  or  /opt/dsda-doom/dsda-doom  …")
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

        # ── Software Update ───────────────────────────────────────────────────
        upd_div = QFrame()
        upd_div.setFrameShape(QFrame.Shape.HLine)
        upd_div.setObjectName("settingsDivider")
        layout.addWidget(upd_div)

        upd_section = QLabel("SOFTWARE UPDATE")
        upd_section.setObjectName("sectionLabel")
        layout.addWidget(upd_section)

        self.version_label = QLabel(f"Current version: v{__version__}")
        self.version_label.setObjectName("settingsDesc")
        layout.addWidget(self.version_label)

        upd_row = QHBoxLayout()
        upd_row.setSpacing(8)

        self.btn_check_updates = QPushButton("Check for Updates")
        self.btn_check_updates.setObjectName("btnCheckUpdates")
        self.btn_check_updates.clicked.connect(self._check_updates)
        upd_row.addWidget(self.btn_check_updates)

        self.btn_update_now = QPushButton("Update Now")
        self.btn_update_now.setObjectName("btnUpdateNow")
        self.btn_update_now.setVisible(False)
        self.btn_update_now.clicked.connect(self._apply_update)
        upd_row.addWidget(self.btn_update_now)

        upd_row.addStretch()
        layout.addLayout(upd_row)

        self.update_status_label = QLabel("")
        self.update_status_label.setObjectName("updateStatusLabel")
        layout.addWidget(self.update_status_label)

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

            #updateStatusLabel { font-size: 11px; }

            #btnCheckUpdates {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                color: #ccc;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                padding: 6px 14px;
            }
            #btnCheckUpdates:hover { border-color: #cc2200; color: #ff4422; }
            #btnCheckUpdates:disabled { color: #555; border-color: #2a2a2a; }

            #btnUpdateNow {
                background: #8b0000;
                border: none;
                color: #ffddcc;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                padding: 6px 14px;
            }
            #btnUpdateNow:hover { background: #aa0000; }
            #btnUpdateNow:disabled { background: #3a1010; color: #666; }

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

    def _check_updates(self):
        self.btn_check_updates.setEnabled(False)
        self.btn_check_updates.setText("Checking…")
        self.update_status_label.setText("")
        self.btn_update_now.setVisible(False)
        self._pending_zipball_url = None
        self._pending_appimage_url = ""

        self._check_worker = UpdateCheckWorker()
        self._check_worker.update_available.connect(self._on_update_available)
        self._check_worker.up_to_date.connect(self._on_up_to_date)
        self._check_worker.check_failed.connect(self._on_check_failed)
        self._check_worker.start()

    def _on_update_available(self, latest, zipball_url, html_url, appimage_url):
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText("Check for Updates")
        self.update_status_label.setText(f"v{latest} is available!")
        self.update_status_label.setStyleSheet("color: #cc2200;")
        self._pending_zipball_url = zipball_url
        self._pending_appimage_url = appimage_url
        self.btn_update_now.setVisible(True)

    def _on_up_to_date(self, version):
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText("Check for Updates")
        self.update_status_label.setText(f"Up to date (v{version})")
        self.update_status_label.setStyleSheet("color: #44aa44;")

    def _on_check_failed(self, error):
        self.btn_check_updates.setEnabled(True)
        self.btn_check_updates.setText("Check for Updates")
        self.update_status_label.setText(f"Check failed: {error}")
        self.update_status_label.setStyleSheet("color: #cc8800;")

    def _apply_update(self):
        if not self._pending_zipball_url:
            return
        self.btn_update_now.setEnabled(False)
        self.btn_update_now.setText("Downloading…")
        self.btn_check_updates.setEnabled(False)
        self.update_status_label.setText("Downloading update…")
        self.update_status_label.setStyleSheet("color: #ccc;")

        self._download_worker = UpdateDownloadWorker(self._pending_zipball_url, self._pending_appimage_url)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.failed.connect(self._on_download_failed)
        self._download_worker.start()

    def _on_download_finished(self):
        self.update_status_label.setText("Update applied! Restarting…")
        self.update_status_label.setStyleSheet("color: #44aa44;")
        QTimer.singleShot(1000, restart_app)

    def _on_download_failed(self, error):
        self.btn_update_now.setEnabled(True)
        self.btn_update_now.setText("Update Now")
        self.btn_check_updates.setEnabled(True)
        self.update_status_label.setText(f"Download failed: {error}")
        self.update_status_label.setStyleSheet("color: #cc2200;")

    def _save(self):
        path = self.binary_input.text().strip()
        sourceport.set_source_port(path)
        self.accept()

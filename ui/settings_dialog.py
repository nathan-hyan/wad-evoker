import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QFrame, QDialogButtonBox,
    QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer

import sourceport
from updater import UpdateCheckWorker, UpdateDownloadWorker, restart_app
from version import __version__


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(560)
        self.setModal(True)
        self._build_ui()
        self._apply_styles()
        self._load_profiles()

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

        # ── Source Ports ─────────────────────────────────────────────────────
        sp_label = QLabel("SOURCE PORTS")
        sp_label.setObjectName("sectionLabel")
        layout.addWidget(sp_label)

        desc = QLabel(
            "Manage your source port profiles.\n"
            "Add executables like UZDoom, DSDA-Doom, Crispy Doom, etc."
        )
        desc.setObjectName("settingsDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.setObjectName("profileList")
        self.profile_list.setMaximumHeight(140)
        self.profile_list.currentRowChanged.connect(self._on_profile_selected)
        layout.addWidget(self.profile_list)

        # Profile action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_add_profile = QPushButton("＋ Add")
        self.btn_add_profile.setObjectName("btnProfileAction")
        self.btn_add_profile.clicked.connect(self._add_profile)
        btn_row.addWidget(self.btn_add_profile)

        self.btn_edit_profile = QPushButton("✎ Edit")
        self.btn_edit_profile.setObjectName("btnProfileAction")
        self.btn_edit_profile.clicked.connect(self._edit_profile)
        self.btn_edit_profile.setEnabled(False)
        btn_row.addWidget(self.btn_edit_profile)

        self.btn_delete_profile = QPushButton("✕ Delete")
        self.btn_delete_profile.setObjectName("btnDeleteProfile")
        self.btn_delete_profile.clicked.connect(self._delete_profile)
        self.btn_delete_profile.setEnabled(False)
        btn_row.addWidget(self.btn_delete_profile)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Edit area (name + binary)
        self.edit_frame = QFrame()
        self.edit_frame.setObjectName("profileEditFrame")
        edit_layout = QVBoxLayout(self.edit_frame)
        edit_layout.setContentsMargins(0, 8, 0, 0)
        edit_layout.setSpacing(8)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_lbl = QLabel("Name:")
        name_lbl.setObjectName("fieldLabel")
        name_lbl.setFixedWidth(50)
        name_row.addWidget(name_lbl)
        self.name_input = QLineEdit()
        self.name_input.setObjectName("binaryInput")
        self.name_input.setPlaceholderText("e.g. DSDA-Doom")
        name_row.addWidget(self.name_input, 1)
        edit_layout.addLayout(name_row)

        bin_row = QHBoxLayout()
        bin_row.setSpacing(8)
        bin_lbl = QLabel("Binary:")
        bin_lbl.setObjectName("fieldLabel")
        bin_lbl.setFixedWidth(50)
        bin_row.addWidget(bin_lbl)
        self.binary_input = QLineEdit()
        self.binary_input.setObjectName("binaryInput")
        self.binary_input.setPlaceholderText("/usr/bin/dsda-doom")
        bin_row.addWidget(self.binary_input, 1)
        btn_browse = QPushButton("Browse…")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.clicked.connect(self._browse)
        bin_row.addWidget(btn_browse)
        edit_layout.addLayout(bin_row)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("hintLabel")
        edit_layout.addWidget(self.hint_label)

        save_row = QHBoxLayout()
        save_row.addStretch()
        self.btn_save_profile = QPushButton("Save Profile")
        self.btn_save_profile.setObjectName("btnSaveProfile")
        self.btn_save_profile.clicked.connect(self._save_profile)
        save_row.addWidget(self.btn_save_profile)
        self.btn_cancel_edit = QPushButton("Cancel")
        self.btn_cancel_edit.setObjectName("btnCancelEdit")
        self.btn_cancel_edit.clicked.connect(self._cancel_edit)
        save_row.addWidget(self.btn_cancel_edit)
        edit_layout.addLayout(save_row)

        self.edit_frame.setVisible(False)
        layout.addWidget(self.edit_frame)

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
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Close).setObjectName("btnCancel")
        layout.addWidget(btns)

        self.binary_input.textChanged.connect(self._validate)

    # ── Internal state for edit mode ──────────────────────────────────────────
    # _editing_profile_id: None = add mode, int = editing existing
    _editing_profile_id = None

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

            #profileList {
                background: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                padding: 4px;
            }
            #profileList::item {
                padding: 4px 8px;
                border-radius: 2px;
            }
            #profileList::item:selected {
                background: #2a1a1a;
                color: #ff6644;
            }
            #profileList::item:hover {
                background: #1e1e1e;
            }

            #btnProfileAction {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                color: #ccc;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                padding: 5px 12px;
                font-size: 11px;
            }
            #btnProfileAction:hover { border-color: #cc2200; color: #ff4422; }
            #btnProfileAction:disabled { color: #555; border-color: #2a2a2a; }

            #btnDeleteProfile {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                color: #cc4444;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                padding: 5px 12px;
                font-size: 11px;
            }
            #btnDeleteProfile:hover { border-color: #cc2200; color: #ff2222; }
            #btnDeleteProfile:disabled { color: #555; border-color: #2a2a2a; }

            #fieldLabel {
                color: #888;
                font-size: 12px;
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

            #btnSaveProfile {
                background: #8b0000;
                border: none;
                color: #ffddcc;
                border-radius: 3px;
                padding: 6px 16px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 11px;
            }
            #btnSaveProfile:hover { background: #aa0000; }

            #btnCancelEdit {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                color: #aaa;
                border-radius: 3px;
                padding: 6px 14px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
            #btnCancelEdit:hover { border-color: #555; color: #ccc; }

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

    # ── Profile management ────────────────────────────────────────────────────

    def _load_profiles(self):
        """Populate the profile list from config."""
        self.profile_list.clear()
        profiles = sourceport.get_profiles()
        active_id = sourceport.get_active_profile_id()
        for p in profiles:
            label = p["name"]
            if p["id"] == active_id:
                label = f"▸ {label}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.profile_list.addItem(item)
        has_profiles = self.profile_list.count() > 0
        self.btn_edit_profile.setEnabled(has_profiles)
        self.btn_delete_profile.setEnabled(has_profiles)
        if has_profiles:
            self.profile_list.setCurrentRow(0)

    def _on_profile_selected(self, row):
        has_selection = row >= 0
        self.btn_edit_profile.setEnabled(has_selection)
        self.btn_delete_profile.setEnabled(has_selection)

    def _add_profile(self):
        self._editing_profile_id = None
        self.name_input.clear()
        self.binary_input.clear()
        self.hint_label.setText("")
        self.edit_frame.setVisible(True)
        self.name_input.setFocus()

    def _edit_profile(self):
        item = self.profile_list.currentItem()
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        profiles = sourceport.get_profiles()
        profile = next((p for p in profiles if p["id"] == pid), None)
        if not profile:
            return
        self._editing_profile_id = pid
        self.name_input.setText(profile["name"])
        self.binary_input.setText(profile["binary"])
        self.edit_frame.setVisible(True)
        self.name_input.setFocus()

    def _save_profile(self):
        name = self.name_input.text().strip()
        binary = self.binary_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a name for the profile.")
            return
        if not binary:
            QMessageBox.warning(self, "Missing Binary", "Please select a source port executable.")
            return

        if self._editing_profile_id is not None:
            sourceport.update_profile(self._editing_profile_id, name=name, binary=binary)
        else:
            sourceport.add_profile(name, binary)

        self.edit_frame.setVisible(False)
        self._load_profiles()
        # Notify parent to refresh dropdown
        parent = self.parent()
        if parent and hasattr(parent, "refresh_source_port_dropdown"):
            parent.refresh_source_port_dropdown()

    def _cancel_edit(self):
        self.edit_frame.setVisible(False)

    def _delete_profile(self):
        item = self.profile_list.currentItem()
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        name = item.text().lstrip("▸ ")

        reply = QMessageBox.question(
            self, "Delete Profile",
            f"Delete source port profile \"{name}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        sourceport.delete_profile(pid)
        if self._editing_profile_id == pid:
            self.edit_frame.setVisible(False)
        self._load_profiles()
        # Notify parent to refresh dropdown
        parent = self.parent()
        if parent and hasattr(parent, "refresh_source_port_dropdown"):
            parent.refresh_source_port_dropdown()

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

    # ── Software Update ───────────────────────────────────────────────────────

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

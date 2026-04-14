import os
import shlex
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog,
    QMessageBox, QSplitter, QFrame, QStatusBar, QComboBox
)
from PyQt6.QtCore import Qt, QMimeData, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QIcon

import db
import maplist
import titlepic
import wad_importer
import sourceport
import updater
from updater import UpdateCheckWorker, UpdateDownloadWorker, restart_app
from version import __version__
from ui.wad_list import WadListWidget
from ui.wad_detail import WadDetailPanel
from ui.wad_edit_dialog import WadEditDialog
from ui.last_played import LastPlayedBar
from ui.settings_dialog import SettingsDialog
from ui.update_progress_dialog import UpdateProgressDialog
from ui.files_launch_dialog import FilesLaunchDialog
from ui.primary_wad_picker_dialog import PrimaryWadPickerDialog
from process_watcher import ProcessWatcher


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wad Evoker")
        self.setMinimumSize(1000, 660)
        self.resize(1200, 760)
        self.setAcceptDrops(True)
        self._active_watchers = {}  # wad_id -> ProcessWatcher
        self._build_ui()
        self._apply_styles()
        self.refresh_library()
        QTimer.singleShot(2000, self._start_update_check)

    # ── UI BUILD ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        root.addWidget(self._build_topbar())

        # Red accent line below top bar
        red_line = QFrame()
        red_line.setFrameShape(QFrame.Shape.HLine)
        red_line.setObjectName("topBarLine")
        red_line.setFixedHeight(2)
        root.addWidget(red_line)

        # Last played
        self.last_played_bar = LastPlayedBar()
        self.last_played_bar.wad_launched.connect(self._on_launch_from_recent)
        root.addWidget(self.last_played_bar)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("divider")
        root.addWidget(line)

        # Main splitter: list | detail
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("mainSplitter")
        splitter.setHandleWidth(1)

        self.wad_list = WadListWidget()
        self.wad_list.wad_selected.connect(self._on_wad_selected)
        self.wad_list.play_requested.connect(lambda wad: self._on_launch(wad["id"], wad["filepath"]))
        self.wad_list.edit_requested.connect(lambda wad: self._on_edit(wad["id"]))
        self.wad_list.delete_requested.connect(lambda wad: self._on_delete(wad["id"]))
        self.wad_list.finish_toggled.connect(self._on_finish_toggled)
        splitter.addWidget(self.wad_list)

        self.detail_panel = WadDetailPanel()
        self.detail_panel.launch_requested.connect(self._on_launch)
        self.detail_panel.edit_requested.connect(self._on_edit)
        self.detail_panel.delete_requested.connect(self._on_delete)
        self.detail_panel.tags_changed.connect(self._on_tags_changed)
        splitter.addWidget(self.detail_panel)

        splitter.setSizes([380, 620])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self.status = QStatusBar()
        self.status.setObjectName("statusBar")
        self.setStatusBar(self.status)

        # Source port dropdown in status bar (right side)
        sp_label = QLabel("Source Port:")
        sp_label.setObjectName("spLabel")
        self.sp_combo = QComboBox()
        self.sp_combo.setObjectName("spCombo")
        self.sp_combo.setMinimumWidth(160)
        self.sp_combo.currentIndexChanged.connect(self._on_source_port_changed)
        self.status.addPermanentWidget(sp_label)
        self.status.addPermanentWidget(self.sp_combo)
        self.refresh_source_port_dropdown()

    def _build_topbar(self):
        bar = QWidget()
        bar.setObjectName("topBar")
        bar.setFixedHeight(56)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        skull = QLabel("💀")
        skull.setObjectName("skullIcon")
        skull.setFont(QFont("monospace", 22))
        layout.addWidget(skull)

        title = QLabel("WAD EVOKER")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        layout.addStretch()

        # Search
        self.search_box = QLineEdit()
        self.search_box.setObjectName("searchBox")
        self.search_box.setPlaceholderText("Search WADs…")
        self.search_box.setFixedWidth(220)
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        # Add WAD
        btn_add = QPushButton("＋  Add WAD")
        btn_add.setObjectName("btnAdd")
        btn_add.clicked.connect(self._on_add_wad)
        layout.addWidget(btn_add)

        # Settings
        btn_settings = QPushButton("⚙")
        btn_settings.setObjectName("btnSettings")
        btn_settings.setToolTip("Settings")
        btn_settings.setFixedWidth(38)
        btn_settings.clicked.connect(self._on_settings)
        layout.addWidget(btn_settings)

        return bar

    # ── STYLES ────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #141414;
                color: #e8e0d0;
                font-family: 'Courier New', 'Courier', monospace;
            }

            #topBar {
                background: #0d0d0d;
            }

            #topBarLine {
                background: #b22222;
                border: none;
                max-height: 2px;
            }

            #appTitle {
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 4px;
                color: #cc2200;
                font-family: 'Courier New', monospace;
            }

            #skullIcon {
                color: #cc2200;
            }

            #searchBox {
                background: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 5px 10px;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
            }
            #searchBox:focus {
                border: 1px solid #cc2200;
            }

            #btnAdd {
                background: #8b0000;
                color: #e8e0d0;
                border: none;
                border-radius: 3px;
                padding: 7px 16px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
            }
            #btnAdd:hover { background: #a00000; }
            #btnAdd:pressed { background: #6b0000; }

            #btnSettings {
                background: #1e1e1e;
                color: #999;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                font-size: 16px;
            }
            #btnSettings:hover { background: #2a2a2a; color: #cc2200; }

            #divider { background: #2a2a2a; max-height: 1px; }

            #mainSplitter::handle { background: #2a2a2a; }

            #statusBar {
                background: #0d0d0d;
                color: #666;
                font-size: 11px;
                border-top: 1px solid #2a2a2a;
                font-family: 'Courier New', monospace;
            }

            #spLabel {
                color: #666;
                font-size: 11px;
                font-family: 'Courier New', monospace;
                padding-right: 4px;
            }

            #spCombo {
                background: #1a1a1a;
                color: #e8e0d0;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 2px 8px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                min-height: 20px;
            }
            #spCombo:hover { border-color: #cc2200; }
            #spCombo::drop-down {
                border: none;
                width: 18px;
            }
            #spCombo QAbstractItemView {
                background: #1a1a1a;
                color: #e8e0d0;
                border: 1px solid #3a3a3a;
                selection-background-color: #2a1a1a;
                selection-color: #ff6644;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }

            QScrollBar:vertical {
                background: #1a1a1a;
                width: 8px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #3a3a3a;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #cc2200; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

    # ── ACTIONS ───────────────────────────────────────────────────────────────

    def _on_add_wad(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select WAD / PK3 / ZIP",
            os.path.expanduser("~"),
            "Doom files (*.wad *.pk3 *.zip);;All files (*)"
        )
        for path in paths:
            self._import_path(path)

    def _import_path(self, path):
        results = wad_importer.import_file(path)
        imported = 0
        last_imported_id = None
        for r in results:
            if r.get("needs_primary_selection"):
                r = self._pick_primary_wad(r)
                if r is None:
                    continue
            meta = r["metadata"]
            title = meta.get("title") or wad_importer.title_from_filename(r["filename"])
            wad = db.add_wad(
                title=title,
                filename=r["filename"],
                filepath=r["filepath"],
                author=meta.get("author"),
                description=meta.get("description"),
                year=meta.get("year"),
                game=meta.get("game"),
                map_count=meta.get("map_count"),
                map_list=r.get("map_list"),
                titlepic_path=r.get("titlepic_path"),
                extra_wads=r.get("extra_wads"),
            )
            if wad:
                imported += 1
                last_imported_id = wad["id"]
        if imported:
            self.status.showMessage(f"Imported {imported} WAD(s).", 4000)
            self.detail_panel.clear()
            self.refresh_library()
            if last_imported_id:
                self.wad_list.select_wad_by_id(last_imported_id)
        else:
            self.status.showMessage("No new WADs imported (already in library or unsupported).", 4000)

    def _pick_primary_wad(self, selection_data):
        """Show PrimaryWadPickerDialog and return a finalised result dict, or None on cancel."""
        dlg = PrimaryWadPickerDialog(
            zip_base=selection_data["zip_base"],
            candidates=selection_data["candidates"],
            entry_dir=selection_data["entry_dir"],
            parent=self,
        )
        if dlg.exec() != dlg.DialogCode.Accepted:
            return None
        primary = dlg.selected_primary()
        return wad_importer.finalize_zip_primary(
            entry_dir=selection_data["entry_dir"],
            primary_path=primary,
            all_dest_paths=selection_data["candidates"],
        )

    def _on_search(self, text):
        if text.strip():
            wads = db.search_wads(text.strip())
        else:
            wads = db.get_all_wads()
        self.wad_list.populate(wads)

    def _on_wad_selected(self, wad):
        wad_id = wad["id"]
        wad = db.get_wad_by_id(wad_id)
        if not wad:
            return
        
        tags = db.get_tags(wad_id)
        if not wad.get("titlepic_path"):
            path = titlepic.extract_titlepic(wad["filepath"])
            if path:
                db.update_titlepic(wad_id, path)
                wad["titlepic_path"] = path

        ml_existing = wad.get("map_list") or ""
        map_list_needs_refresh = (not ml_existing.strip()) or ("lookup" in ml_existing.lower())
        if map_list_needs_refresh:
            maps = maplist.extract_maps(wad["filepath"])
            if maps:
                ml = maplist.format_map_list(maps)
                db.update_map_list(wad_id, ml)
                wad["map_list"] = ml
        self.detail_panel.show_wad(wad, tags)

    def _on_edit(self, wad_id):
        wad_before = db.get_wad_by_id(wad_id)
        if not wad_before:
            return

        dlg = WadEditDialog(wad_id, self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        wad_after = db.get_wad_by_id(wad_id)
        if not wad_after:
            return

        titlepic_maybe_changed = (wad_before.get("titlepic_path") != wad_after.get("titlepic_path"))
        maplist_maybe_changed = (wad_before.get("map_list") != wad_after.get("map_list"))

        if titlepic_maybe_changed and not wad_after.get("titlepic_path"):
            path = titlepic.extract_titlepic(wad_after.get("filepath"))
            if path:
                db.update_titlepic(wad_id, path)
                wad_after["titlepic_path"] = path

        if maplist_maybe_changed and not wad_after.get("map_list"):
            maps = maplist.extract_maps(wad_after.get("filepath"))
            if maps:
                ml = maplist.format_map_list(maps)
                db.update_map_list(wad_id, ml)
                wad_after["map_list"] = ml

        self.refresh_library()
        tags = db.get_tags(wad_id)
        self.detail_panel.show_wad(wad_after, tags)
        self.wad_list.select_wad_by_id(wad_id)

    def _on_launch(self, wad_id, wad_filepath):
        # Prevent re-launch while already running
        if wad_id in self._active_watchers:
            QMessageBox.information(
                self, "Already Running",
                "This WAD is already running. Wait for it to exit before launching again."
            )
            return

        extra_wads = db.get_extra_wads(wad_id)
        deh_files = wad_importer.find_deh_files(wad_filepath)
        all_extra = extra_wads + deh_files

        selected_extra = []
        if all_extra:
            wad = db.get_wad_by_id(wad_id)
            if wad and wad.get("skip_files_prompt"):
                selected_extra = all_extra
            else:
                dlg = FilesLaunchDialog(all_extra, self)
                if dlg.exec() != dlg.DialogCode.Accepted:
                    return
                selected_extra = dlg.selected_files()
                if dlg.dont_ask_again():
                    db.update_skip_files_prompt(wad_id, True)

        selected_wads = [f for f in selected_extra if os.path.splitext(f)[1].lower() in (".wad", ".pk3")]
        selected_deh = [f for f in selected_extra if f.lower().endswith(".deh")]

        # Per-WAD extra args
        raw_args = db.get_extra_args(wad_id)
        parsed_extra_args = None
        if raw_args:
            try:
                parsed_extra_args = shlex.split(raw_args)
            except ValueError:
                parsed_extra_args = raw_args.split()

        # Per-WAD source port override
        binary_override = None
        sp_profile_id = db.get_sourceport_profile_id(wad_id)
        if sp_profile_id:
            binary = sourceport.get_profile_binary(sp_profile_id)
            if binary:
                binary_override = binary
            # If profile was deleted, binary is empty — fall back to active (no override)

        ok, err, proc = sourceport.launch_wad(
            wad_filepath,
            extra_wad_files=selected_wads or None,
            deh_files=selected_deh or None,
            extra_args=parsed_extra_args,
            binary_override=binary_override,
        )
        if ok:
            self.status.showMessage("Launched!", 3000)
            watcher = ProcessWatcher(proc, wad_id, parent=self)
            watcher.finished.connect(self._on_process_finished)
            self._active_watchers[wad_id] = watcher
            watcher.start()
        else:
            QMessageBox.warning(self, "Launch Failed", err)

    def _on_process_finished(self, wad_id, elapsed_seconds):
        self._active_watchers.pop(wad_id, None)
        db.update_last_played(wad_id)
        if elapsed_seconds > 0:
            db.add_play_duration(wad_id, elapsed_seconds)
        self.last_played_bar.refresh()
        # Refresh detail panel if this WAD is currently shown
        wad = db.get_wad_by_id(wad_id)
        if wad and self.detail_panel._current_wad and self.detail_panel._current_wad["id"] == wad_id:
            tags = db.get_tags(wad_id)
            self.detail_panel.show_wad(wad, tags)

    def _on_launch_from_recent(self, wad):
        self._on_launch(wad["id"], wad["filepath"])
        # Also highlight it in the list
        self.wad_list.select_wad_by_id(wad["id"])

    def _on_delete(self, wad_id):
        wad = db.get_wad_by_id(wad_id)
        if not wad:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Remove WAD")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("What would you like to do with this WAD?")
        msg.setInformativeText(
            "You can remove it from the library, or also delete the file from disk."
        )

        btn_cancel = msg.addButton(QMessageBox.StandardButton.Cancel)
        btn_remove = msg.addButton("Remove from Library", QMessageBox.ButtonRole.AcceptRole)
        btn_delete = msg.addButton("Remove + Delete File", QMessageBox.ButtonRole.DestructiveRole)
        msg.setDefaultButton(btn_remove)

        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_cancel:
            return

        want_delete_file = (clicked == btn_delete)
        wad_path = wad.get("filepath")

        allow_file_delete = False
        if want_delete_file and wad_path:
            try:
                wad_real = os.path.realpath(os.path.abspath(wad_path))
                managed_dir = os.path.realpath(os.path.abspath(wad_importer.WAD_DIR))
                allow_file_delete = os.path.commonpath([wad_real, managed_dir]) == managed_dir
            except Exception:
                allow_file_delete = False

        if want_delete_file and not allow_file_delete:
            QMessageBox.warning(
                self,
                "Cannot Delete File",
                "For safety, Wad Evoker only deletes files inside its managed library folder:\n"
                f"{wad_importer.WAD_DIR}\n\n"
                "This entry will be removed from the library, but the file will be kept on disk."
            )
            want_delete_file = False

        db.delete_wad(wad_id)

        if want_delete_file and wad_path:
            try:
                if os.path.exists(wad_path) and os.path.isfile(wad_path):
                    os.remove(wad_path)
                    entry_dir = os.path.dirname(wad_path)
                    entry_dir_real = os.path.realpath(os.path.abspath(entry_dir))
                    managed_dir = os.path.realpath(os.path.abspath(wad_importer.WAD_DIR))
                    parent_of_entry = os.path.realpath(os.path.abspath(os.path.dirname(entry_dir)))
                    if parent_of_entry == managed_dir and not os.listdir(entry_dir):
                        os.rmdir(entry_dir)
            except OSError as e:
                QMessageBox.warning(
                    self,
                    "File Delete Failed",
                    f"Removed from library, but could not delete the file:\n{wad_path}\n\n{e}"
                )

        self.detail_panel.clear()
        self.refresh_library()
        if want_delete_file:
            self.status.showMessage("WAD removed and file deleted.", 3000)
        else:
            self.status.showMessage("WAD removed from library.", 3000)

    def _on_tags_changed(self, wad_id, tags):
        # tags is the full new list — sync with db
        existing = set(db.get_tags(wad_id))
        new_set = set(tags)
        for t in new_set - existing:
            db.add_tag(wad_id, t)
        for t in existing - new_set:
            db.remove_tag(wad_id, t)

    def _on_finish_toggled(self, wad):
        wad_id = wad["id"]
        new_state = not bool(wad.get("finished"))
        db.set_finished(wad_id, new_state)
        self.refresh_library()
        self.wad_list.select_wad_by_id(wad_id)
        # Refresh detail panel if this wad is currently shown
        updated = db.get_wad_by_id(wad_id)
        if updated:
            tags = db.get_tags(wad_id)
            self.detail_panel.show_wad(updated, tags)

    def _on_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
        self.refresh_source_port_dropdown()
        self.refresh_library()

    def refresh_source_port_dropdown(self):
        """Reload source port profiles into the status bar combo box."""
        self.sp_combo.blockSignals(True)
        self.sp_combo.clear()
        profiles = sourceport.get_profiles()
        active_id = sourceport.get_active_profile_id()
        select_idx = 0
        for i, p in enumerate(profiles):
            self.sp_combo.addItem(p["name"], p["id"])
            if p["id"] == active_id:
                select_idx = i
        if profiles:
            self.sp_combo.setCurrentIndex(select_idx)
        self.sp_combo.blockSignals(False)

    def _on_source_port_changed(self, index):
        if index < 0:
            return
        pid = self.sp_combo.currentData()
        if pid is not None:
            sourceport.set_active_profile(pid)

    def _start_update_check(self):
        self._update_worker = UpdateCheckWorker()
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.start()

    def _on_update_available(self, latest, zipball_url, html_url, appimage_url):
        msg = QMessageBox(self)
        msg.setWindowTitle("Update Available")
        msg.setText(
            f"Wad Evoker v{latest} is available (you have v{__version__}).\n\n"
            "Download and install now?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self._run_update(zipball_url, appimage_url)

    def _run_update(self, zipball_url, appimage_url=""):
        self._progress_dialog = UpdateProgressDialog(self)
        self._progress_dialog.show()
        
        self._download_worker = UpdateDownloadWorker(zipball_url, appimage_url)
        self._download_worker.progress.connect(self._on_update_progress)
        self._download_worker.status_changed.connect(self._on_update_status)
        self._download_worker.finished.connect(self._on_update_downloaded)
        self._download_worker.failed.connect(self._on_update_failed)
        self._download_worker.start()

    def _on_update_progress(self, downloaded, total):
        if hasattr(self, '_progress_dialog'):
            self._progress_dialog.set_progress(downloaded, total)
    
    def _on_update_status(self, status):
        if hasattr(self, '_progress_dialog'):
            self._progress_dialog.set_status(status)
    
    def _on_update_downloaded(self):
        if hasattr(self, '_progress_dialog'):
            self._progress_dialog.set_status("Update complete! Restarting...")
            self._progress_dialog.set_indeterminate()
        self.status.showMessage("Update applied. Restarting…")
        QTimer.singleShot(1000, restart_app)

    def _on_update_failed(self, error):
        if hasattr(self, '_progress_dialog'):
            self._progress_dialog.close()
        self.status.showMessage(f"Update failed: {error}", 6000)
        QMessageBox.warning(self, "Update Failed", f"Could not apply update:\n{error}")

    def refresh_library(self):
        wads = db.get_all_wads()
        self.wad_list.populate(wads)
        self.last_played_bar.refresh()
        count = len(wads)
        self.status.showMessage(f"{count} WAD{'s' if count != 1 else ''} in library.", 3000)

    # ── DRAG AND DROP ─────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in (".wad", ".pk3", ".zip"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in (".wad", ".pk3", ".zip"):
                self._import_path(path)
        event.acceptProposedAction()

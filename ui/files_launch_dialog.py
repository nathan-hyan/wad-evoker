import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from ui.styled_checkbox import StyledCheckBox


class FilesLaunchDialog(QDialog):
    """Modal dialog shown before launching when the entry has extra files (DEH etc.).

    Shows a checklist of available files so the user can pick which to include.
    Also offers a 'Don't ask again for this mod' option stored per-entry in the DB.
    """

    def __init__(self, extra_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multiple Files Found")
        self.setModal(True)
        self.setMinimumWidth(460)
        self._checkboxes = []
        self._dont_ask_cb = None
        self._build_ui(extra_files)
        self._apply_styles()

    def _build_ui(self, extra_files):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)
        layout.setSizeConstraint(layout.SizeConstraint.SetFixedSize)

        title = QLabel("MULTIPLE FILES FOUND")
        title.setObjectName("dlgTitle")
        layout.addWidget(title)

        desc = QLabel(
            "This mod contains multiple files that can be loaded.\n"
            "Select which files to include when launching:"
        )
        desc.setObjectName("dlgDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setObjectName("dlgDivider")
        layout.addWidget(div)

        for path in extra_files:
            cb = StyledCheckBox(os.path.basename(path))
            cb.setChecked(True)
            cb._file_path = path
            self._checkboxes.append(cb)
            layout.addWidget(cb)

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setObjectName("dlgDivider")
        layout.addWidget(div2)

        self._dont_ask_cb = StyledCheckBox("Don't ask again for this mod")
        self._dont_ask_cb.setChecked(False)
        self._dont_ask_cb.setObjectName("dontAskCheckbox")
        layout.addWidget(self._dont_ask_cb)

        layout.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnDlgCancel")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_launch = QPushButton("▶  LAUNCH")
        btn_launch.setObjectName("btnDlgLaunch")
        btn_launch.setFixedHeight(36)
        btn_launch.setDefault(True)
        btn_launch.clicked.connect(self.accept)
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
            #dontAskCheckbox {
                color: #666;
                font-size: 11px;
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
        """)

    def selected_files(self):
        """Return list of checked file paths."""
        return [cb._file_path for cb in self._checkboxes if cb.isChecked()]

    def dont_ask_again(self):
        """Return True if the user checked 'Don't ask again'."""
        return self._dont_ask_cb.isChecked()


# Keep old name as alias for backwards compatibility
DehLaunchDialog = FilesLaunchDialog

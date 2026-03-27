import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QButtonGroup, QTextEdit, QWidget
)
from PyQt6.QtCore import Qt
from ui.styled_checkbox import StyledCheckBox


def _read_txt(entry_dir):
    """Return content of the first .txt file found in entry_dir, or empty string.

    Skips macOS resource-fork / dot-files (._* and hidden files).
    """
    try:
        for fname in sorted(os.listdir(entry_dir)):
            if fname.startswith("."):
                continue
            if fname.lower().endswith(".txt"):
                path = os.path.join(entry_dir, fname)
                for enc in ("utf-8", "cp1252", "cp437", "latin-1"):
                    try:
                        with open(path, "r", encoding=enc) as f:
                            return f.read()
                    except UnicodeDecodeError:
                        continue
    except OSError:
        pass
    return ""


class PrimaryWadPickerDialog(QDialog):
    """Modal dialog asking the user to pick which WAD is the primary file.

    Shows a radio-button list of candidates on the left and the .txt sidecar
    content on the right so the user can make an informed decision.
    """

    def __init__(self, zip_base, candidates, entry_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Primary WAD")
        self.setModal(True)
        self.setMinimumSize(700, 420)
        self._candidates = candidates
        self._radio_group = QButtonGroup(self)
        self._radio_group.setExclusive(True)
        self._radios = []
        self._build_ui(zip_base, entry_dir)
        self._apply_styles()

    def _build_ui(self, zip_base, entry_dir):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left panel: picker ───────────────────────────────────────────────
        left = QWidget()
        left.setObjectName("pickerLeft")
        left.setMinimumWidth(280)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(24, 24, 24, 20)
        left_layout.setSpacing(14)

        title = QLabel("SELECT PRIMARY WAD")
        title.setObjectName("dlgTitle")
        left_layout.addWidget(title)

        desc = QLabel(
            f"The archive <b>{zip_base}.zip</b> contains multiple WAD/PK3 files.\n"
            "Select which one is the main mod file.\n"
            "The others will be loaded as extras."
        )
        desc.setObjectName("dlgDesc")
        desc.setWordWrap(True)
        left_layout.addWidget(desc)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setObjectName("dlgDivider")
        left_layout.addWidget(div)

        for i, path in enumerate(self._candidates):
            cb = StyledCheckBox(os.path.basename(path))
            cb._file_path = path
            cb.setChecked(i == 0)
            self._radios.append(cb)
            self._radio_group.addButton(cb, i)
            left_layout.addWidget(cb)

        left_layout.addStretch()

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.HLine)
        div2.setObjectName("dlgDivider")
        left_layout.addWidget(div2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnDlgCancel")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_ok = QPushButton("Confirm")
        btn_ok.setObjectName("btnDlgLaunch")
        btn_ok.setFixedHeight(36)
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_row.addWidget(btn_ok)

        left_layout.addLayout(btn_row)

        # ── Right panel: .txt preview ────────────────────────────────────────
        right = QWidget()
        right.setObjectName("pickerRight")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 24, 24, 20)
        right_layout.setSpacing(8)

        txt_label = QLabel("README / INFO")
        txt_label.setObjectName("sectionLabel")
        right_layout.addWidget(txt_label)

        self._txt_view = QTextEdit()
        self._txt_view.setObjectName("txtPreview")
        self._txt_view.setReadOnly(True)
        self._txt_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = _read_txt(entry_dir)
        self._txt_view.setPlainText(content if content else "(No readme found in this archive)")
        right_layout.addWidget(self._txt_view, 1)

        # ── Splitter-like: fixed left, expanding right ───────────────────────
        vdiv = QFrame()
        vdiv.setFrameShape(QFrame.Shape.VLine)
        vdiv.setObjectName("dlgDivider")

        root.addWidget(left)
        root.addWidget(vdiv)
        root.addWidget(right, 1)

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: #141414;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
            }
            #pickerLeft {
                background: #141414;
            }
            #pickerRight {
                background: #111111;
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
                max-width: 1px;
            }
            #sectionLabel {
                color: #666;
                font-size: 10px;
                letter-spacing: 3px;
                font-family: 'Courier New', monospace;
            }
            #txtPreview {
                background: #0d0d0d;
                border: 1px solid #2a2a2a;
                border-radius: 3px;
                color: #aaa;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
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

    def selected_primary(self):
        """Return the path of the selected primary WAD."""
        for cb in self._radios:
            if cb.isChecked():
                return cb._file_path
        return self._candidates[0] if self._candidates else None

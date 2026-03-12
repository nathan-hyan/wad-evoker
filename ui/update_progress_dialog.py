from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class UpdateProgressDialog(QDialog):
    """Modal dialog showing update download and installation progress."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating Wad Evoker")
        self.setModal(True)
        self.setFixedSize(480, 160)
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.CustomizeWindowHint | 
            Qt.WindowType.WindowTitleHint
        )
        self._build_ui()
        self._apply_styles()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        self.status_label = QLabel("Preparing update...")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setFont(QFont("Courier New", 11))
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)
        
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("detailLabel")
        self.detail_label.setFont(QFont("Courier New", 9))
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.detail_label)
        
        layout.addStretch()
    
    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: #1a1a1a;
                color: #e8e0d0;
                font-family: 'Courier New', monospace;
            }
            
            #statusLabel {
                color: #e8e0d0;
                font-weight: bold;
                font-size: 11pt;
            }
            
            #detailLabel {
                color: #999;
                font-size: 9pt;
            }
            
            #progressBar {
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                background: #0d0d0d;
                text-align: center;
                height: 28px;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                font-weight: bold;
            }
            
            #progressBar::chunk {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #8b0000,
                    stop: 1 #cc2200
                );
                border-radius: 2px;
            }
        """)
    
    def set_status(self, message):
        """Update the status message."""
        self.status_label.setText(message)
    
    def set_progress(self, downloaded, total):
        """Update progress bar based on bytes downloaded."""
        if total > 0:
            percentage = int((downloaded / total) * 100)
            self.progress_bar.setValue(percentage)
            
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.detail_label.setText(f"{downloaded_mb:.1f} MB / {total_mb:.1f} MB")
        else:
            self.progress_bar.setMaximum(0)
            self.detail_label.setText("Downloading...")
    
    def set_indeterminate(self):
        """Set progress bar to indeterminate mode."""
        self.progress_bar.setMaximum(0)
        self.detail_label.setText("")

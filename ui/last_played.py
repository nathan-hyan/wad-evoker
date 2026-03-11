import os

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QPainter, QColor, QPixmap, QPainterPath

import db


class RecentCard(QWidget):
    clicked = pyqtSignal(dict)

    def __init__(self, wad):
        super().__init__()
        self.wad = wad
        self._bg_pixmap = None
        self.setObjectName("recentCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(150, 66)

        tp = wad.get("titlepic_path")
        if tp and os.path.isfile(tp):
            px = QPixmap(tp)
            if not px.isNull():
                self._bg_pixmap = px

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        title = QLabel(wad["title"])
        title.setObjectName("recentTitle")
        title.setWordWrap(False)
        title.setMaximumWidth(130)
        # Truncate long titles
        font = QFont("Courier New", 11)
        font.setBold(True)
        title.setFont(font)
        metrics = title.fontMetrics()
        text = metrics.elidedText(wad["title"], Qt.TextElideMode.ElideRight, 130)
        title.setText(text)
        layout.addWidget(title)

        lp = wad.get("last_played", "")
        if lp:
            lp_short = lp[:10]
        else:
            lp_short = ""
        sub = QLabel(f"Played {lp_short}")
        sub.setObjectName("recentSub")
        layout.addWidget(sub)

        self._apply_style()

    def _apply_style(self):
        if self._bg_pixmap:
            bg = "transparent"
            hover_bg = "transparent"
            sub_color = "#ccbbaa"
        else:
            bg = "#1a0000"
            hover_bg = "#250000"
            sub_color = "#665555"
        self.setStyleSheet(f"""
            #recentCard {{
                background: {bg};
                border: 1px solid #3a1010;
                border-radius: 4px;
            }}
            #recentCard:hover {{
                background: {hover_bg};
                border-color: #cc2200;
            }}
            #recentTitle {{ color: #ff6644; }}
            #recentSub {{
                color: {sub_color};
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }}
        """)

    def paintEvent(self, event):
        if self._bg_pixmap:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            path = QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(), 4, 4)
            painter.setClipPath(path)

            scaled = self._bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())

            painter.fillRect(self.rect(), QColor(10, 0, 0, 172))
            painter.end()
        super().paintEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit(self.wad)


class LastPlayedBar(QWidget):
    wad_launched = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setObjectName("lastPlayedBar")
        self.setFixedHeight(96)
        self._build_ui()
        self._apply_styles()
        self.refresh()

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 0, 16, 0)
        outer.setSpacing(16)

        lbl = QLabel("RECENT")
        lbl.setObjectName("recentHeader")
        lbl.setFixedWidth(56)
        outer.addWidget(lbl)

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setObjectName("recentScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(80)

        self.cards_widget = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 7, 0, 7)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        scroll.setWidget(self.cards_widget)
        outer.addWidget(scroll, 1)

        self.empty_lbl = QLabel("No WADs played yet.")
        self.empty_lbl.setObjectName("recentEmpty")
        outer.addWidget(self.empty_lbl)

    def _apply_styles(self):
        self.setStyleSheet("""
            #lastPlayedBar {
                background: #0f0f0f;
            }
            #recentHeader {
                color: #555;
                font-size: 9px;
                letter-spacing: 3px;
                font-family: 'Courier New', monospace;
            }
            #recentScroll, QScrollArea {
                background: transparent;
                border: none;
            }
            #recentEmpty {
                color: #333;
                font-size: 12px;
                font-family: 'Courier New', monospace;
                font-style: italic;
            }
        """)

    def refresh(self):
        # Clear existing cards
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        wads = db.get_last_played(limit=8)
        if wads:
            self.empty_lbl.hide()
            for wad in wads:
                card = RecentCard(wad)
                card.clicked.connect(self.wad_launched)
                self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        else:
            self.empty_lbl.show()

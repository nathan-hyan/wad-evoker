from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont


class StyledCheckBox(QCheckBox):
    """Reusable themed checkbox matching the application's dark terminal aesthetic.

    Renders a fully custom indicator:
      - Unchecked: dark box (#1a1a1a) with gray border (#3a3a3a)
      - Checked:   blood-red box (#8b0000) with red border (#cc2200)
                   plus a centered white dash as the check mark

    Text is drawn in #e8e0d0 using Courier New 11pt.
    The widget font is also set to Courier New 11 so sizeHint() stays accurate.
    """

    _IND_SIZE = 14
    _IND_GAP  = 8

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Courier New", 11))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        sz    = self._IND_SIZE
        y_off = (self.height() - sz) // 2
        ind   = QRect(0, y_off, sz, sz)

        if self.isChecked():
            painter.setBrush(QBrush(QColor("#8b0000")))
            painter.setPen(QPen(QColor("#cc2200"), 1))
        else:
            painter.setBrush(QBrush(QColor("#1a1a1a")))
            painter.setPen(QPen(QColor("#3a3a3a"), 1))
        painter.drawRoundedRect(ind, 2, 2)

        if self.isChecked():
            painter.setPen(QPen(QColor("#e8e0d0"), 2))
            cx = ind.left() + ind.width()  // 2
            cy = ind.top()  + ind.height() // 2
            painter.drawLine(cx - 4, cy, cx + 4, cy)

        text_rect = self.rect().adjusted(sz + self._IND_GAP, 0, 0, 0)
        painter.setPen(QColor("#e8e0d0"))
        painter.setFont(self.font())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self.text())

        painter.end()

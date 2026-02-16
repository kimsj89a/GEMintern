"""Status box widget - replaces st.info/warning/success/error."""

from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt


class StatusBox(QFrame):
    """Styled status/notification box - Notion style."""

    ICONS = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
    }

    def __init__(self, message="", style="info", parent=None):
        super().__init__(parent)
        self._style = style
        self.setProperty("cssClass", style)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        icon = self.ICONS.get(style, "ℹ️")
        self._label = QLabel(f"{icon} {message}")
        self._label.setWordWrap(True)
        self._label.setStyleSheet("font-size: 14px; border: none;")
        layout.addWidget(self._label)

    def setText(self, message, style=None):
        if style:
            self._style = style
            self.setProperty("cssClass", style)
            self.setStyle(self.style())  # Force style refresh
            icon = self.ICONS.get(style, "ℹ️")
            self._label.setText(f"{icon} {message}")
        else:
            current_text = self._label.text()
            icon = current_text[:2] if len(current_text) > 2 else "ℹ️"
            self._label.setText(f"{icon} {message}")

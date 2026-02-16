"""Collapsible group box widget - replaces st.expander()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup


class CollapsibleBox(QWidget):
    """A collapsible container widget with a toggle button header."""

    def __init__(self, title="", expanded=False, parent=None):
        super().__init__(parent)
        self._is_expanded = expanded

        self.toggle_btn = QPushButton(f"{'▼' if expanded else '▶'} {title}")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(expanded)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #f8f9fa;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:checked {
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }
        """)
        self.toggle_btn.clicked.connect(self._toggle)
        self._title = title

        self.content_area = QFrame()
        self.content_area.setStyleSheet("""
            QFrame {
                border: 1px solid #dee2e6;
                border-top: none;
                border-radius: 0 0 6px 6px;
                padding: 8px;
            }
        """)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(8, 8, 8, 8)

        if not expanded:
            self.content_area.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content_area)

    def _toggle(self):
        self._is_expanded = not self._is_expanded
        self.content_area.setVisible(self._is_expanded)
        arrow = "▼" if self._is_expanded else "▶"
        self.toggle_btn.setText(f"{arrow} {self._title}")

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)

    def setExpanded(self, expanded):
        self._is_expanded = expanded
        self.content_area.setVisible(expanded)
        self.toggle_btn.setChecked(expanded)
        arrow = "▼" if expanded else "▶"
        self.toggle_btn.setText(f"{arrow} {self._title}")

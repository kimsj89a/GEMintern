"""Step indicator widget - replaces step progress bar in ui_workflow."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PyQt6.QtCore import pyqtSignal, Qt


class StepIndicator(QWidget):
    """Horizontal step progress indicator."""

    step_clicked = pyqtSignal(int)  # step number clicked

    def __init__(self, steps=None, parent=None):
        """
        steps: dict {step_num: (icon, label)} e.g. {1: ("📁", "데이터 업로드"), ...}
        """
        super().__init__(parent)
        self._steps = steps or {}
        self._current = 1
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._step_widgets = {}
        self._build()

    def _build(self):
        # Clear existing
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._step_widgets.clear()

        for step_num in sorted(self._steps.keys()):
            icon, label = self._steps[step_num]
            frame = QFrame()
            frame.setMinimumHeight(60)

            if step_num < self._current:
                # Done - clickable
                btn = QPushButton(f"✅ {label}")
                btn.setProperty("cssClass", "secondary")
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #d4edda;
                        border: 2px solid #28a745;
                        border-radius: 8px;
                        padding: 6px;
                        font-size: 12px;
                        color: #155724;
                    }
                    QPushButton:hover { background-color: #c3e6cb; }
                """)
                step = step_num
                btn.clicked.connect(lambda checked, s=step: self.step_clicked.emit(s))
                frame_layout = QHBoxLayout(frame)
                frame_layout.setContentsMargins(0, 0, 0, 0)
                frame_layout.addWidget(btn)
            elif step_num == self._current:
                frame.setProperty("cssClass", "step-active")
                frame.setStyleSheet("""
                    QFrame {
                        background-color: #cce5ff;
                        border: 2px solid #0068c9;
                        border-radius: 8px;
                        padding: 6px;
                    }
                """)
                fl = QHBoxLayout(frame)
                fl.setContentsMargins(4, 4, 4, 4)
                lbl = QLabel(f"{icon}\n{label}")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("color: #004085; font-weight: bold; font-size: 12px;")
                fl.addWidget(lbl)
            else:
                frame.setProperty("cssClass", "step-pending")
                frame.setStyleSheet("""
                    QFrame {
                        background-color: #f8f9fa;
                        border: 2px solid #dee2e6;
                        border-radius: 8px;
                        padding: 6px;
                    }
                """)
                fl = QHBoxLayout(frame)
                fl.setContentsMargins(4, 4, 4, 4)
                lbl = QLabel(f"{icon}\n{label}")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("color: #6c757d; font-size: 12px;")
                fl.addWidget(lbl)

            self._step_widgets[step_num] = frame
            self._layout.addWidget(frame)

    def set_current(self, step):
        self._current = step
        self._build()

    def set_steps(self, steps):
        self._steps = steps
        self._build()

    def current_step(self):
        return self._current

"""
GEM Intern v7.0 - PyQt6 Desktop Application
Entry point for the application.
"""

import sys
import os

# Ensure the app directory is in path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from styles import MAIN_STYLESHEET
from main_window import MainWindow


def main():
    # High DPI support
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("GEM Intern")
    app.setApplicationVersion("7.0")

    # Set default font (Notion-inspired: clean sans-serif)
    # Try to use system fonts that are similar to Notion's font stack
    font_families = [
        "Segoe UI",           # Windows default, clean and modern
        "Apple SD Gothic Neo", # macOS Korean
        "Malgun Gothic",      # Windows Korean fallback
        "sans-serif"          # Generic fallback
    ]

    for family in font_families:
        font = QFont(family, 10)
        if font.exactMatch():
            break

    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Apply global stylesheet
    app.setStyleSheet(MAIN_STYLESHEET)

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

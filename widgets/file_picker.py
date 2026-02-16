"""File picker widget - replaces st.file_uploader()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal, Qt
import os


class FilePicker(QWidget):
    """File upload widget with multi-file support."""

    files_changed = pyqtSignal(list)  # list of file paths

    def __init__(self, label="파일 선택", accept_multiple=True,
                 file_filter="All Files (*)", parent=None):
        super().__init__(parent)
        self._file_paths = []
        self._accept_multiple = accept_multiple
        self._file_filter = file_filter

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QHBoxLayout()
        self.label = QLabel(label)
        self.label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(self.label)
        header.addStretch()

        self.btn_browse = QPushButton("📁 찾아보기")
        self.btn_browse.setProperty("cssClass", "secondary")
        self.btn_browse.clicked.connect(self._browse)
        header.addWidget(self.btn_browse)

        self.btn_clear = QPushButton("✕ 초기화")
        self.btn_clear.setProperty("cssClass", "secondary")
        self.btn_clear.clicked.connect(self._clear)
        self.btn_clear.setVisible(False)
        header.addWidget(self.btn_clear)

        layout.addLayout(header)

        # File list
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(120)
        self.file_list.setVisible(False)
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 4px 8px;
            }
        """)
        layout.addWidget(self.file_list)

        # Drop zone label
        self.drop_label = QLabel("📂 파일을 선택하세요")
        self.drop_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                padding: 20px;
                color: #6c757d;
                font-size: 13px;
                text-align: center;
            }
        """)
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.drop_label)

    def _browse(self):
        if self._accept_multiple:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "파일 선택", "", self._file_filter
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "파일 선택", "", self._file_filter
            )
            paths = [path] if path else []

        if paths:
            self._file_paths = paths
            self._update_list()
            self.files_changed.emit(self._file_paths)

    def _clear(self):
        self._file_paths = []
        self._update_list()
        self.files_changed.emit(self._file_paths)

    def _update_list(self):
        self.file_list.clear()
        if self._file_paths:
            for p in self._file_paths:
                name = os.path.basename(p)
                size = os.path.getsize(p)
                size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f} MB"
                self.file_list.addItem(f"📄 {name} ({size_str})")
            self.file_list.setVisible(True)
            self.drop_label.setVisible(False)
            self.btn_clear.setVisible(True)
        else:
            self.file_list.setVisible(False)
            self.drop_label.setVisible(True)
            self.btn_clear.setVisible(False)

    def get_file_paths(self):
        return self._file_paths

    def set_file_filter(self, filter_str):
        self._file_filter = filter_str

    def setAcceptDrops(self, accept):
        super().setAcceptDrops(accept)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        if not self._accept_multiple:
            paths = paths[:1]
        self._file_paths = paths
        self._update_list()
        self.files_changed.emit(self._file_paths)

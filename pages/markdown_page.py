"""Markdown to Word page - replaces ui_markdown.render_markdown_converter_panel()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QCheckBox, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.markdown_viewer import MarkdownViewer
from widgets.status_box import StatusBox


class MarkdownPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("📝 Markdown → Word 변환")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Input method
        input_row = QHBoxLayout()
        self.radio_file = QRadioButton("파일 업로드")
        self.radio_direct = QRadioButton("직접 입력")
        self.radio_direct.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.radio_file)
        group.addButton(self.radio_direct)
        input_row.addWidget(self.radio_file)
        input_row.addWidget(self.radio_direct)
        input_row.addStretch()
        layout.addLayout(input_row)

        self.file_picker = FilePicker("Markdown 파일", accept_multiple=False,
                                       file_filter="Markdown (*.md *.txt);;All (*)")
        self.file_picker.setVisible(False)
        self.radio_file.toggled.connect(lambda c: self.file_picker.setVisible(c))
        layout.addWidget(self.file_picker)

        self.md_input = QTextEdit()
        self.md_input.setPlaceholderText("# 제목\n\n내용을 입력하세요...")
        self.md_input.setMinimumHeight(250)
        self.md_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.md_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.md_input)

        # Options
        opts = QHBoxLayout()
        opts.addWidget(QLabel("파일명:"))
        self.filename_input = QLineEdit("output.docx")
        opts.addWidget(self.filename_input)
        self.template_check = QCheckBox("템플릿 스타일 적용")
        opts.addWidget(self.template_check)
        opts.addStretch()
        layout.addLayout(opts)

        # Preview
        self.preview = MarkdownViewer()
        self.preview.setMinimumHeight(200)
        layout.addWidget(self.preview)

        # Buttons
        btn_row = QHBoxLayout()
        btn_preview = QPushButton("👁️ 미리보기")
        btn_preview.clicked.connect(self._preview)
        btn_row.addWidget(btn_preview)

        btn_convert = QPushButton("📄 Word 변환 및 저장")
        btn_convert.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        btn_convert.clicked.connect(self._convert)
        btn_row.addWidget(btn_convert)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _get_md_text(self):
        if self.radio_file.isChecked():
            paths = self.file_picker.get_file_paths()
            if paths:
                with open(paths[0], 'r', encoding='utf-8') as f:
                    return f.read()
        return self.md_input.toPlainText()

    def _preview(self):
        text = self._get_md_text()
        self.preview.setMarkdown(text)

    def _convert(self):
        text = self._get_md_text()
        if not text.strip():
            QMessageBox.warning(self, "경고", "변환할 텍스트가 없습니다.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Word 저장", self.filename_input.text(),
            "Word Documents (*.docx)"
        )
        if path:
            try:
                import utils
                docx_data = utils.create_docx(text)
                with open(path, 'wb') as f:
                    f.write(docx_data)
                QMessageBox.information(self, "완료", f"파일이 저장되었습니다:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", str(e))

    def refresh(self):
        pass

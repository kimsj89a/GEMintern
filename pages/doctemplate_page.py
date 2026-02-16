"""Document template page - replaces ui_doctemplate.render_doctemplate_panel()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QCheckBox, QLineEdit, QProgressBar,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.markdown_viewer import MarkdownViewer
from widgets.status_box import StatusBox


class DocTemplateWorker(QThread):
    finished = pyqtSignal(str, str)  # step_name, result
    error = pyqtSignal(str)

    def __init__(self, step, api_key, model, text, parent=None):
        super().__init__(parent)
        self.step = step
        self.api_key = api_key
        self.model = model
        self.text = text

    def run(self):
        try:
            from utils_doctemplate import analyze_document_format, extract_content_as_markdown, generate_final_document
            if self.step == "analyze_format":
                result = analyze_document_format(self.text, self.api_key, self.model)
                self.finished.emit("format", result)
            elif self.step == "extract_content":
                result = extract_content_as_markdown(self.text, self.api_key, self.model)
                self.finished.emit("content", result)
            elif self.step == "generate":
                # text is "format|||content"
                parts = self.text.split("|||", 1)
                result = generate_final_document(parts[0], parts[1], self.api_key, self.model)
                self.finished.emit("final", result)
        except Exception as e:
            self.error.emit(str(e))


class DocTemplatePage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("📋 문서양식 - 포맷 복제기")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(StatusBox("양식 파일의 구조를 분석하고, 새 내용을 해당 양식에 맞춰 생성합니다.", "info"))

        # Step 1: Format template
        layout.addWidget(QLabel("📐 Step 1: 양식 파일 업로드"))
        self.format_picker = FilePicker("양식 파일", accept_multiple=False,
            file_filter="Documents (*.docx *.pdf *.txt *.pptx);;All (*)")
        layout.addWidget(self.format_picker)

        self.btn_analyze = QPushButton("🔍 양식 분석")
        self.btn_analyze.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 8px; border-radius: 6px; font-weight: bold; }
        """)
        self.btn_analyze.clicked.connect(self._analyze_format)
        layout.addWidget(self.btn_analyze)

        self.format_edit = QTextEdit()
        self.format_edit.setPlaceholderText("양식 분석 결과가 여기에 표시됩니다...")
        self.format_edit.setMaximumHeight(150)
        self.format_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.format_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.format_edit)

        # Step 2: Content
        layout.addWidget(QLabel("📄 Step 2: 내용 파일 업로드"))
        self.content_picker = FilePicker("내용 파일", accept_multiple=False,
            file_filter="Documents (*.docx *.pdf *.txt *.pptx);;All (*)")
        layout.addWidget(self.content_picker)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("내용을 직접 입력할 수도 있습니다...")
        self.content_edit.setMaximumHeight(150)
        self.content_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.content_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.content_edit)

        # Step 3: Generate
        self.btn_generate = QPushButton("🤖 양식 적용 문서 생성")
        self.btn_generate.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_generate.clicked.connect(self._generate)
        layout.addWidget(self.btn_generate)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.result_viewer = MarkdownViewer()
        self.result_viewer.setMinimumHeight(300)
        layout.addWidget(self.result_viewer)

        btn_row = QHBoxLayout()
        btn_word = QPushButton("📄 Word 저장")
        btn_word.clicked.connect(self._save_word)
        btn_row.addWidget(btn_word)
        btn_md = QPushButton("📝 MD 저장")
        btn_md.clicked.connect(self._save_md)
        btn_row.addWidget(btn_md)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _analyze_format(self):
        paths = self.format_picker.get_file_paths()
        if not paths:
            QMessageBox.warning(self, "경고", "양식 파일을 선택하세요.")
            return
        settings = AppState.get("latest_settings", {})
        try:
            from utils_doctemplate import extract_text_from_file
            text = extract_text_from_file(paths[0])
            self.progress.setVisible(True)
            self._worker = DocTemplateWorker("analyze_format", settings["api_key"],
                                              settings["model_name"], text)
            self._worker.finished.connect(self._on_step_done)
            self._worker.error.connect(lambda e: (
                QMessageBox.critical(self, "오류", e),
                self.progress.setVisible(False)
            ))
            self._worker.start()
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))

    def _on_step_done(self, step_name, result):
        self.progress.setVisible(False)
        if step_name == "format":
            self.format_edit.setPlainText(result)
        elif step_name == "content":
            self.content_edit.setPlainText(result)
        elif step_name == "final":
            AppState.set("doctemplate_result", result)
            self.result_viewer.setMarkdown(result)

    def _generate(self):
        format_text = self.format_edit.toPlainText().strip()
        content_text = self.content_edit.toPlainText().strip()
        if not format_text or not content_text:
            QMessageBox.warning(self, "경고", "양식과 내용을 모두 입력해주세요.")
            return
        settings = AppState.get("latest_settings", {})
        self.progress.setVisible(True)
        self._worker = DocTemplateWorker("generate", settings["api_key"],
                                          settings["model_name"], f"{format_text}|||{content_text}")
        self._worker.finished.connect(self._on_step_done)
        self._worker.error.connect(lambda e: (
            QMessageBox.critical(self, "오류", e),
            self.progress.setVisible(False)
        ))
        self._worker.start()

    def _save_word(self):
        text = AppState.get("doctemplate_result", "")
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Word 저장", "document.docx", "Word (*.docx)")
        if path:
            from utils_markdown import markdown_to_docx
            data = markdown_to_docx(text)
            with open(path, 'wb') as f:
                f.write(data)

    def _save_md(self):
        text = AppState.get("doctemplate_result", "")
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "MD 저장", "document.md", "Markdown (*.md)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)

    def refresh(self):
        pass

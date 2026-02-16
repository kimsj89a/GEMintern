"""Text organizer page - replaces ui_text_organizer.render_text_organizer_panel()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from app_state import AppState
from widgets.markdown_viewer import MarkdownViewer


class OrganizeWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, model, text, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model = model
        self.text = text

    def run(self):
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            prompt = (
                "다음 텍스트를 읽기 쉬운 불렛 포인트 형식으로 정리해주세요.\n"
                "- 핵심 내용을 중심으로 구조화\n"
                "- 불필요한 반복, 추임새 제거\n"
                "- 마크다운 형식 사용\n\n"
                f"[원문]\n{self.text}"
            )
            resp = client.models.generate_content(model=self.model, contents=prompt)
            self.finished.emit(resp.text)
        except Exception as e:
            self.error.emit(str(e))


class TextOrganizerPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("✏️ 문장 정리기")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(QLabel("텍스트를 불렛 포인트로 정리합니다."))

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("정리할 텍스트를 입력하세요...")
        self.text_input.setMinimumHeight(200)
        self.text_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.text_input)

        opts = QHBoxLayout()
        opts.addWidget(QLabel("모델:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gemini-2.5-flash", "gemini-2.5-pro"])
        opts.addWidget(self.model_combo)
        opts.addStretch()
        layout.addLayout(opts)

        self.btn_organize = QPushButton("✏️ 정리 실행")
        self.btn_organize.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_organize.clicked.connect(self._on_organize)
        layout.addWidget(self.btn_organize)

        self.result_viewer = MarkdownViewer()
        self.result_viewer.setMinimumHeight(300)
        layout.addWidget(self.result_viewer)

        btn_row = QHBoxLayout()
        btn_txt = QPushButton("📄 TXT 저장")
        btn_txt.clicked.connect(lambda: self._save("txt"))
        btn_row.addWidget(btn_txt)
        btn_md = QPushButton("📝 MD 저장")
        btn_md.clicked.connect(lambda: self._save("md"))
        btn_row.addWidget(btn_md)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_organize(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "경고", "텍스트를 입력하세요.")
            return

        settings = AppState.get("latest_settings", {})
        if not settings.get("api_key"):
            QMessageBox.warning(self, "경고", "API Key를 설정해주세요.")
            return

        self.btn_organize.setEnabled(False)
        self._worker = OrganizeWorker(settings["api_key"], self.model_combo.currentText(), text)
        self._worker.finished.connect(lambda r: (
            AppState.set("organizer_result", r),
            self.result_viewer.setMarkdown(r),
            self.btn_organize.setEnabled(True)
        ))
        self._worker.error.connect(lambda e: (
            QMessageBox.critical(self, "오류", e),
            self.btn_organize.setEnabled(True)
        ))
        self._worker.start()

    def _save(self, fmt):
        text = AppState.get("organizer_result", "")
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "저장", f"organized.{fmt}", f"(*.{fmt})")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)

    def refresh(self):
        pass

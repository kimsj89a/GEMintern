"""Audio post-processing page - replaces ui_audio.render_audio_transcription_panel()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QRadioButton, QButtonGroup,
    QProgressBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.markdown_viewer import MarkdownViewer
from widgets.status_box import StatusBox


class AudioProcessWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)

    def __init__(self, api_key, model, text, mode, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model = model
        self.text = text
        self.mode = mode

    def run(self):
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            
            instructions = {
                "meeting_summary": "회의록 형태로 정리해주세요. 참석자, 안건, 논의 내용, 결론, Action Item을 구분하세요.",
                "summary": "핵심 내용 요약문을 작성해주세요.",
                "qa_format": "Q&A 형식으로 정리해주세요.",
                "presentation_format": "발표/보고용 문서로 정리해주세요.",
                "clean": "불필요한 반복, 추임새, 문법 오류를 제거하여 깔끔하게 정리해주세요.",
            }
            instruction = instructions.get(self.mode, instructions["clean"])
            
            # Chunk if text is large
            chunk_size = 5000
            if len(self.text) > chunk_size:
                chunks = [self.text[i:i+chunk_size] for i in range(0, len(self.text), chunk_size)]
                results = []
                for i, chunk in enumerate(chunks):
                    self.progress.emit(i + 1, len(chunks))
                    prompt = f"{instruction}\n\n[텍스트 ({i+1}/{len(chunks)})]\n{chunk}"
                    if results:
                        prompt += f"\n\n[이전 정리 결과 요약]\n{results[-1][:500]}"
                    resp = client.models.generate_content(model=self.model, contents=prompt)
                    results.append(resp.text)
                self.finished.emit("\n\n".join(results))
            else:
                prompt = f"{instruction}\n\n{self.text}"
                resp = client.models.generate_content(model=self.model, contents=prompt)
                self.finished.emit(resp.text)
        except Exception as e:
            self.error.emit(str(e))


class AudioPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("🎤 텍스트 후처리 (오디오 전사 결과)")
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

        # File picker
        self.file_picker = FilePicker("텍스트 파일", accept_multiple=False,
                                       file_filter="Text Files (*.txt *.md);;All (*)")
        self.file_picker.setVisible(False)
        self.radio_file.toggled.connect(lambda c: self.file_picker.setVisible(c))
        layout.addWidget(self.file_picker)

        # Direct input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("전사된 텍스트를 여기에 붙여넣으세요...")
        self.text_input.setMinimumHeight(150)
        self.text_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.text_input)

        # Options
        opts = QHBoxLayout()
        opts.addWidget(QLabel("처리 모드:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("회의록 정리", "meeting_summary")
        self.mode_combo.addItem("핵심 요약", "summary")
        self.mode_combo.addItem("Q&A 형식", "qa_format")
        self.mode_combo.addItem("발표용 정리", "presentation_format")
        self.mode_combo.addItem("단순 정리 (클린업)", "clean")
        opts.addWidget(self.mode_combo)

        opts.addWidget(QLabel("모델:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"])
        opts.addWidget(self.model_combo)
        opts.addStretch()
        layout.addLayout(opts)

        # Process button
        self.btn_process = QPushButton("🤖 AI 후처리 실행")
        self.btn_process.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_process.clicked.connect(self._on_process)
        layout.addWidget(self.btn_process)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Result
        self.result_viewer = MarkdownViewer()
        self.result_viewer.setMinimumHeight(300)
        layout.addWidget(self.result_viewer)

        # Save buttons
        btn_row = QHBoxLayout()
        btn_save_txt = QPushButton("📄 TXT 저장")
        btn_save_txt.clicked.connect(lambda: self._save("txt"))
        btn_row.addWidget(btn_save_txt)
        btn_save_md = QPushButton("📝 MD 저장")
        btn_save_md.clicked.connect(lambda: self._save("md"))
        btn_row.addWidget(btn_save_md)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_process(self):
        settings = AppState.get("latest_settings", {})
        api_key = settings.get("api_key", "")
        if not api_key:
            QMessageBox.warning(self, "경고", "API Key를 설정해주세요.")
            return

        if self.radio_file.isChecked():
            paths = self.file_picker.get_file_paths()
            if not paths:
                QMessageBox.warning(self, "경고", "파일을 선택해주세요.")
                return
            with open(paths[0], 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            text = self.text_input.toPlainText().strip()

        if not text:
            QMessageBox.warning(self, "경고", "텍스트를 입력해주세요.")
            return

        self.btn_process.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

        model = self.model_combo.currentText()
        mode = self.mode_combo.currentData()

        self._worker = AudioProcessWorker(api_key, model, text, mode)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(lambda c, t: (
            self.progress.setRange(0, t), self.progress.setValue(c)
        ))
        self._worker.start()

    def _on_done(self, result):
        AppState.set("audio_result", result)
        self.result_viewer.setMarkdown(result)
        self.progress.setVisible(False)
        self.btn_process.setEnabled(True)

    def _on_error(self, msg):
        QMessageBox.critical(self, "오류", msg)
        self.progress.setVisible(False)
        self.btn_process.setEnabled(True)

    def _save(self, fmt):
        text = AppState.get("audio_result", "")
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "저장", f"result.{fmt}",
                                               f"{'Text' if fmt=='txt' else 'Markdown'} (*.{fmt})")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)

    def refresh(self):
        pass

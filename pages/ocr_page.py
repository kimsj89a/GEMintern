"""OCR page - replaces ui_ocr.render_ocr_panel()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QProgressBar, QTabWidget,
    QTextEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.status_box import StatusBox


class OcrWorker(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, file_paths, engine, api_key, docai_config=None, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.engine = engine
        self.api_key = api_key
        self.docai_config = docai_config

    def run(self):
        try:
            import os
            import fitz
            results = {}
            total = len(self.file_paths)
            for i, fpath in enumerate(self.file_paths):
                self.progress.emit(i + 1, total)
                name = os.path.basename(fpath)
                if self.engine == "gemini":
                    import ocr as ocr_module
                    with fitz.open(fpath) as doc:
                        text = ocr_module.extract_pdf_with_gemini_ocr(doc, self.api_key)
                else:
                    import utils_docai
                    with open(fpath, "rb") as f:
                        file_bytes = f.read()
                    mime_type = utils_docai.get_mime_type(name)
                    cfg = self.docai_config or {}
                    result = utils_docai.process_document(
                        file_bytes=file_bytes,
                        mime_type=mime_type,
                        project_id=cfg.get("project_id", ""),
                        location=cfg.get("location", "us"),
                        processor_id=cfg.get("processor_id", ""),
                        credentials_json=cfg.get("credentials_json"),
                    )
                    text = result.get("text", "") if isinstance(result, dict) else result
                results[name] = text if text else "(OCR 결과 없음)"
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class OcrPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("👁️ 문서 OCR")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        self.file_picker = FilePicker("PDF/이미지 파일",
            file_filter="Documents (*.pdf *.png *.jpg *.jpeg *.tiff);;All (*)")
        layout.addWidget(self.file_picker)

        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("OCR 엔진:"))
        self.radio_gemini = QRadioButton("Gemini Vision (빠름)")
        self.radio_docai = QRadioButton("Document AI (고품질)")
        self.radio_gemini.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.radio_gemini)
        group.addButton(self.radio_docai)
        engine_row.addWidget(self.radio_gemini)
        engine_row.addWidget(self.radio_docai)
        engine_row.addStretch()
        layout.addLayout(engine_row)

        self.btn_ocr = QPushButton("🔍 OCR 변환 시작")
        self.btn_ocr.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_ocr.clicked.connect(self._on_ocr)
        layout.addWidget(self.btn_ocr)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.result_tabs = QTabWidget()
        self.result_tabs.setMinimumHeight(400)
        layout.addWidget(self.result_tabs)

        btn_row = QHBoxLayout()
        btn_txt = QPushButton("📄 전체 TXT 저장")
        btn_txt.clicked.connect(self._save_txt)
        btn_row.addWidget(btn_txt)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_ocr(self):
        paths = self.file_picker.get_file_paths()
        if not paths:
            QMessageBox.warning(self, "경고", "파일을 선택하세요.")
            return

        settings = AppState.get("latest_settings", {})
        api_key = settings.get("api_key", "")
        if not api_key:
            QMessageBox.warning(self, "경고", "API Key를 설정해주세요.")
            return

        engine = "gemini" if self.radio_gemini.isChecked() else "docai"
        self.btn_ocr.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, len(paths))

        self._worker = OcrWorker(paths, engine, api_key, settings.get("docai_config"))
        self._worker.finished.connect(self._on_done)
        self._worker.progress.connect(lambda c, t: self.progress.setValue(c))
        self._worker.error.connect(lambda e: (
            QMessageBox.critical(self, "오류", e),
            self.btn_ocr.setEnabled(True)
        ))
        self._worker.start()

    def _on_done(self, results):
        AppState.set("ocr_results", results)
        self.result_tabs.clear()
        for name, text in results.items():
            te = QTextEdit()
            te.setPlainText(text)
            te.setReadOnly(True)
            te.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            te.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.result_tabs.addTab(te, name)
        self.progress.setVisible(False)
        self.btn_ocr.setEnabled(True)

    def _save_txt(self):
        results = AppState.get("ocr_results", {})
        if not results:
            return
        path, _ = QFileDialog.getSaveFileName(self, "TXT 저장", "ocr_result.txt", "Text (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for name, text in results.items():
                    f.write(f"=== {name} ===\n{text}\n\n")

    def refresh(self):
        pass

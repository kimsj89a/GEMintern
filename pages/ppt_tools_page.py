"""PPT tools page - replaces ui_ppt_tools.render_ppt_tools_panel()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QProgressBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.markdown_viewer import MarkdownViewer
from widgets.status_box import StatusBox
from workers import AnalysisWorker


class PptToolsPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("📢 발표자료 (PPT) 도구")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        tabs = QTabWidget()

        # Tab 1: PPT Generation
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)

        t1_layout.addWidget(QLabel("문서를 기반으로 발표자료를 생성합니다."))

        self.ppt_file_picker = FilePicker("문서 파일",
            file_filter="Documents (*.pdf *.docx *.pptx *.txt);;All (*)")
        t1_layout.addWidget(self.ppt_file_picker)

        t1_layout.addWidget(QLabel("💬 추가 맥락"))
        self.ppt_context = QTextEdit()
        self.ppt_context.setPlaceholderText("발표 대상, 시간, 중점 사항 등")
        self.ppt_context.setMaximumHeight(80)
        self.ppt_context.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.ppt_context.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        t1_layout.addWidget(self.ppt_context)

        self.btn_gen_ppt = QPushButton("📊 PPT 생성")
        self.btn_gen_ppt.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_gen_ppt.clicked.connect(self._on_gen_ppt)
        t1_layout.addWidget(self.btn_gen_ppt)

        self.ppt_progress = QProgressBar()
        self.ppt_progress.setRange(0, 0)
        self.ppt_progress.setVisible(False)
        t1_layout.addWidget(self.ppt_progress)

        self.ppt_result = MarkdownViewer()
        self.ppt_result.setMinimumHeight(300)
        t1_layout.addWidget(self.ppt_result)

        btn_dl = QPushButton("📥 PPTX 다운로드")
        btn_dl.clicked.connect(self._save_ppt)
        t1_layout.addWidget(btn_dl)

        tabs.addTab(tab1, "📊 PPT 생성")

        # Tab 2: PPT Updater
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        t2_layout.addWidget(QLabel("기존 PPT의 투자이력 슬라이드를 업데이트합니다."))

        self.updater_picker = FilePicker("PPTX 파일", accept_multiple=False,
            file_filter="PowerPoint (*.pptx)")
        t2_layout.addWidget(self.updater_picker)

        self.btn_update = QPushButton("🔄 투자이력 업데이트")
        self.btn_update.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
        """)
        self.btn_update.clicked.connect(self._on_update_ppt)
        t2_layout.addWidget(self.btn_update)

        self.update_status = StatusBox("PPTX 파일을 업로드하세요.", "info")
        t2_layout.addWidget(self.update_status)
        t2_layout.addStretch()

        tabs.addTab(tab2, "🔄 투자이력 업데이트")
        layout.addWidget(tabs)

    def _on_gen_ppt(self):
        settings = AppState.get("latest_settings", {})
        if not settings.get("api_key"):
            QMessageBox.warning(self, "경고", "API Key를 설정해주세요.")
            return

        file_paths = self.ppt_file_picker.get_file_paths()
        context = self.ppt_context.toPlainText().strip()

        # Parse files
        file_context = ""
        if file_paths:
            import utils
            from workers import _FileWrapper
            for fpath in file_paths:
                with open(fpath, 'rb') as f:
                    wrapper = _FileWrapper(f, fpath)
                    parsed = utils.parse_uploaded_file(wrapper, api_key=settings["api_key"])
                    if parsed:
                        file_context += parsed + "\n\n"

        if not file_context.strip():
            project = AppState.get("current_project", "")
            if project:
                import core_rag
                file_context = core_rag.load_all_project_docs(project)

        if not file_context.strip():
            QMessageBox.warning(self, "경고", "파일을 업로드하거나 프로젝트를 선택하세요.")
            return

        self.btn_gen_ppt.setEnabled(False)
        self.ppt_progress.setVisible(True)

        self._worker = AnalysisWorker(
            "slide_json", settings["api_key"], settings["model_name"],
            file_context=file_context, context_text=context
        )
        self._worker.finished.connect(self._on_ppt_done)
        self._worker.error.connect(lambda e: (
            QMessageBox.critical(self, "오류", e),
            self.btn_gen_ppt.setEnabled(True),
            self.ppt_progress.setVisible(False)
        ))
        self._worker.start()

    def _on_ppt_done(self, result):
        AppState.set("ppt_slide_text", result)
        self.ppt_result.setMarkdown(result)
        self.ppt_progress.setVisible(False)
        self.btn_gen_ppt.setEnabled(True)

    def _save_ppt(self):
        text = AppState.get("ppt_slide_text", "")
        if not text:
            QMessageBox.warning(self, "경고", "생성된 내용이 없습니다.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "PPT 저장", "slides.pptx", "PowerPoint (*.pptx)")
        if path:
            import utils_ppt
            data = utils_ppt.create_ppt(text)
            with open(path, 'wb') as f:
                f.write(data)
            QMessageBox.information(self, "완료", f"파일이 저장되었습니다:\n{path}")

    def _on_update_ppt(self):
        paths = self.updater_picker.get_file_paths()
        if not paths:
            QMessageBox.warning(self, "경고", "PPTX 파일을 선택하세요.")
            return
        try:
            from core_ppt_updater import InvestmentHistoryUpdater
            updater = InvestmentHistoryUpdater(paths[0])
            data = updater.extract_data()
            updater.update_slide(data)

            save_path, _ = QFileDialog.getSaveFileName(
                self, "업데이트된 PPT 저장", "updated.pptx", "PowerPoint (*.pptx)")
            if save_path:
                updater.save(save_path)
                self.update_status.setText("업데이트 완료!", "success")
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))

    def refresh(self):
        pass

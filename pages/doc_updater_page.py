"""Document updater page — 기존 문서 업데이트."""

import os
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QRadioButton, QButtonGroup, QProgressBar,
    QFileDialog, QMessageBox, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.markdown_viewer import MarkdownViewer
from widgets.status_box import StatusBox


class DocUpdateWorker(QThread):
    finished = pyqtSignal(str, str, str)  # output_path, summary, preview
    error = pyqtSignal(str)

    def __init__(self, original_path, supplementary_paths, supplementary_text,
                 instruction, mode, api_key, model, parent=None):
        super().__init__(parent)
        self.original_path = original_path
        self.supplementary_paths = supplementary_paths
        self.supplementary_text = supplementary_text
        self.instruction = instruction
        self.mode = mode
        self.api_key = api_key
        self.model = model

    def run(self):
        try:
            from core_doc_updater import update_document
            output_path, summary, preview = update_document(
                self.original_path, self.supplementary_paths,
                self.supplementary_text, self.instruction,
                self.mode, self.api_key, self.model,
            )
            self.finished.emit(output_path, summary, preview)
        except Exception as e:
            self.error.emit(str(e))


class DocUpdaterPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._output_path = ""
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)

        # Title
        title = QLabel("📄 기존 문서 업데이트")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(StatusBox(
            "기존 문서에 추가 자료와 지시사항을 반영하여 원본 서식을 유지한 채 업데이트합니다.",
            "info"
        ))

        # Step 1: Original document
        layout.addWidget(QLabel("📎 Step 1: 기존 문서 업로드"))
        self.original_picker = FilePicker(
            "기존 문서 (1개)", accept_multiple=False,
            file_filter="Documents (*.docx *.pptx *.pdf *.txt *.md);;All (*)"
        )
        layout.addWidget(self.original_picker)

        # Step 2: Supplementary materials
        layout.addWidget(QLabel("📚 Step 2: 추가 자료 업로드 (선택)"))
        self.suppl_picker = FilePicker(
            "추가 자료 (복수 가능)", accept_multiple=True,
            file_filter="Documents (*.docx *.pdf *.pptx *.xlsx *.xls *.txt *.md *.csv);;All (*)"
        )
        layout.addWidget(self.suppl_picker)

        self.suppl_text = QTextEdit()
        self.suppl_text.setPlaceholderText("또는 추가 자료 텍스트를 직접 붙여넣기...")
        self.suppl_text.setMaximumHeight(120)
        self.suppl_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.suppl_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.suppl_text)

        # Step 3: Instruction
        layout.addWidget(QLabel("💡 Step 3: 업데이트 지시사항"))
        self.instruction_edit = QTextEdit()
        self.instruction_edit.setPlaceholderText(
            "예: 2025년 재무 데이터를 반영하고, 시장 분석 섹션을 업데이트해줘"
        )
        self.instruction_edit.setMaximumHeight(100)
        self.instruction_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.instruction_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.instruction_edit)

        # Options row
        opts = QHBoxLayout()

        opts.addWidget(QLabel("모드:"))
        self.mode_group = QButtonGroup(self)
        self.radio_partial = QRadioButton("부분 수정")
        self.radio_full = QRadioButton("전체 재생성")
        self.radio_partial.setChecked(True)
        self.mode_group.addButton(self.radio_partial)
        self.mode_group.addButton(self.radio_full)
        opts.addWidget(self.radio_partial)
        opts.addWidget(self.radio_full)

        opts.addStretch()

        opts.addWidget(QLabel("모델:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gemini-2.5-flash", "gemini-2.5-pro"])
        opts.addWidget(self.model_combo)

        layout.addLayout(opts)

        # Run button
        self.btn_update = QPushButton("🔄 문서 업데이트 실행")
        self.btn_update.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_update.clicked.connect(self._on_update)
        layout.addWidget(self.btn_update)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Status
        self.status_box = StatusBox("", "info")
        self.status_box.setVisible(False)
        layout.addWidget(self.status_box)

        # Result preview
        self.result_viewer = MarkdownViewer()
        self.result_viewer.setMinimumHeight(300)
        layout.addWidget(self.result_viewer)

        # Save buttons
        btn_row = QHBoxLayout()
        self.btn_save_original = QPushButton("📄 업데이트 파일 저장")
        self.btn_save_original.clicked.connect(self._save_updated_file)
        self.btn_save_original.setEnabled(False)
        btn_row.addWidget(self.btn_save_original)

        self.btn_save_md = QPushButton("📝 MD 저장")
        self.btn_save_md.clicked.connect(self._save_md)
        self.btn_save_md.setEnabled(False)
        btn_row.addWidget(self.btn_save_md)

        btn_row.addStretch()

        self.btn_reset = QPushButton("🔄 초기화")
        self.btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(self.btn_reset)

        layout.addLayout(btn_row)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_update(self):
        original_paths = self.original_picker.get_file_paths()
        if not original_paths:
            QMessageBox.warning(self, "경고", "기존 문서를 선택해주세요.")
            return

        instruction = self.instruction_edit.toPlainText().strip()
        if not instruction:
            QMessageBox.warning(self, "경고", "업데이트 지시사항을 입력해주세요.")
            return

        settings = AppState.get("latest_settings", {})
        api_key = settings.get("api_key", "")
        if not api_key:
            QMessageBox.warning(self, "경고", "설정에서 API Key를 입력해주세요.")
            return

        mode = "full" if self.radio_full.isChecked() else "partial"
        suppl_paths = self.suppl_picker.get_file_paths()
        suppl_text = self.suppl_text.toPlainText().strip()

        self.btn_update.setEnabled(False)
        self.progress.setVisible(True)
        self.status_box.setText("문서 분석 및 업데이트 중...", "info")
        self.status_box.setVisible(True)

        self._worker = DocUpdateWorker(
            original_paths[0], suppl_paths, suppl_text,
            instruction, mode, api_key, self.model_combo.currentText(),
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, output_path, summary, preview):
        self.progress.setVisible(False)
        self.btn_update.setEnabled(True)
        self._output_path = output_path
        self.status_box.setText(f"완료: {summary}", "success")
        self.result_viewer.setMarkdown(preview)
        self.btn_save_original.setEnabled(True)
        self.btn_save_md.setEnabled(True)
        AppState.set("doc_updater_preview", preview)

    def _on_error(self, error_msg):
        self.progress.setVisible(False)
        self.btn_update.setEnabled(True)
        self.status_box.setText(f"오류: {error_msg}", "error")
        QMessageBox.critical(self, "오류", error_msg)

    def _save_updated_file(self):
        if not self._output_path or not os.path.exists(self._output_path):
            QMessageBox.warning(self, "경고", "저장할 파일이 없습니다.")
            return
        ext = os.path.splitext(self._output_path)[1]
        name = os.path.basename(self._output_path)
        filter_map = {
            '.docx': "Word (*.docx)",
            '.pptx': "PowerPoint (*.pptx)",
            '.txt': "Text (*.txt)",
            '.md': "Markdown (*.md)",
        }
        file_filter = filter_map.get(ext, f"File (*{ext})")
        path, _ = QFileDialog.getSaveFileName(self, "업데이트 파일 저장", name, file_filter)
        if path:
            shutil.copy2(self._output_path, path)
            self.status_box.setText(f"저장 완료: {path}", "success")

    def _save_md(self):
        preview = AppState.get("doc_updater_preview", "")
        if not preview:
            return
        path, _ = QFileDialog.getSaveFileName(self, "MD 저장", "update_preview.md", "Markdown (*.md)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(preview)

    def _reset(self):
        self.result_viewer.setMarkdown("")
        self.status_box.setVisible(False)
        self.btn_save_original.setEnabled(False)
        self.btn_save_md.setEnabled(False)
        self._output_path = ""
        AppState.set("doc_updater_preview", "")

    def refresh(self):
        pass

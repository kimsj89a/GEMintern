"""LP Q&A page - replaces ui_lp_qa.render_lp_qa_panel()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QProgressBar, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QScrollArea, QFrame, QApplication
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from PyQt6.QtGui import QClipboard
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.status_box import StatusBox
from widgets.markdown_viewer import MarkdownViewer
from widgets.document_list import DocumentListWidget
import utils_markdown
import core_rag


class QaItemWidget(QFrame):
    """Single Q&A item with markdown rendering and action buttons."""

    def __init__(self, question, answer, parent=None):
        super().__init__(parent)
        self.question = question
        self.answer = answer
        self._build_ui()

    def _build_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                margin: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Question section
        q_label = QLabel("Q:")
        q_label.setStyleSheet("font-weight: bold; color: #0068c9; font-size: 13px;")
        layout.addWidget(q_label)

        question_text = QLabel(self.question)
        question_text.setWordWrap(True)
        question_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        question_text.setStyleSheet("font-size: 13px; color: #333; margin-left: 12px;")
        layout.addWidget(question_text)

        # Answer section
        a_label = QLabel("A:")
        a_label.setStyleSheet("font-weight: bold; color: #28a745; font-size: 13px; margin-top: 8px;")
        layout.addWidget(a_label)

        # Markdown viewer for answer
        self.answer_viewer = MarkdownViewer()
        self.answer_viewer.setMarkdown(self.answer)
        self.answer_viewer.setMinimumHeight(100)
        # Remove maximum height to allow full content display
        layout.addWidget(self.answer_viewer)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_copy = QPushButton("📋 복사")
        btn_copy.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5a6268; }
        """)
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(btn_copy)

        btn_word = QPushButton("📄 Word 내보내기")
        btn_word.setStyleSheet("""
            QPushButton {
                background: #2b5797;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e4277; }
        """)
        btn_word.clicked.connect(self._export_to_word)
        btn_row.addWidget(btn_word)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _copy_to_clipboard(self):
        """Copy answer to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.answer)
        QMessageBox.information(self, "복사 완료", "답변이 클립보드에 복사되었습니다.")

    def _export_to_word(self):
        """Export Q&A to Word document."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Word 저장", f"qa_{self.question[:20]}.docx", "Word (*.docx)"
        )
        if path:
            try:
                # Create markdown with question and answer
                markdown_content = f"# Q: {self.question}\n\n{self.answer}"
                docx_bytes = utils_markdown.markdown_to_docx(markdown_content, use_template=True)

                with open(path, 'wb') as f:
                    f.write(docx_bytes)

                QMessageBox.information(self, "완료", f"Word 파일이 저장되었습니다:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"Word 변환 실패: {e}")


class QaWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api_key, model, questions, file_context, rag_context="", parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model = model
        self.questions = questions
        self.file_context = file_context
        self.rag_context = rag_context

    def run(self):
        try:
            import core_logic
            results = []
            for i, q in enumerate(self.questions):
                self.progress.emit(i + 1, len(self.questions))
                answer = core_logic.generate_qa_answer(
                    self.api_key, self.model, self.file_context, q,
                    rag_context=self.rag_context
                )
                results.append({"question": q, "answer": answer})
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class LpQaPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._selected_docs = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("🙋‍♂️ LP Q&A 대응")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Check project
        self.project_status = StatusBox("프로젝트를 선택하면 문서 기반으로 답변합니다.", "info")
        layout.addWidget(self.project_status)

        # Document selection widget
        self.doc_list = DocumentListWidget()
        self.doc_list.selection_changed.connect(self._on_doc_selection_changed)
        layout.addWidget(self.doc_list)

        tabs = QTabWidget()

        # Tab 1: Direct
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        t1_layout.addWidget(QLabel("질문을 줄바꿈으로 구분하여 입력하세요"))
        self.qa_input = QTextEdit()
        self.qa_input.setPlaceholderText("질문1\n질문2\n질문3")
        self.qa_input.setMinimumHeight(150)
        self.qa_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.qa_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        t1_layout.addWidget(self.qa_input)
        tabs.addTab(tab1, "직접 입력")

        # Tab 2: Excel
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        self.excel_picker = FilePicker("Excel 파일", accept_multiple=False,
            file_filter="Excel (*.xlsx *.xls *.csv);;All (*)")
        t2_layout.addWidget(self.excel_picker)
        tabs.addTab(tab2, "Excel 업로드")

        layout.addWidget(tabs)

        self.btn_generate = QPushButton("🤖 답변 생성")
        self.btn_generate.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_generate.clicked.connect(self._on_generate)
        layout.addWidget(self.btn_generate)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Results section with scroll area
        results_label = QLabel("📊 답변 결과")
        results_label.setStyleSheet("font-size: 15px; font-weight: bold; margin-top: 16px;")
        layout.addWidget(results_label)

        # Scroll area for Q&A items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(400)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Container widget for Q&A items
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(12)
        self.results_layout.addStretch()

        self.scroll_area.setWidget(self.results_container)
        layout.addWidget(self.scroll_area)

        # Export buttons
        btn_row = QHBoxLayout()
        btn_excel = QPushButton("📥 Excel 저장 (전체)")
        btn_excel.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #218838; }
        """)
        btn_excel.clicked.connect(self._save_excel)
        btn_row.addWidget(btn_excel)

        btn_word_all = QPushButton("📄 Word 저장 (전체)")
        btn_word_all.setStyleSheet("""
            QPushButton {
                background: #2b5797;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e4277; }
        """)
        btn_word_all.clicked.connect(self._save_word_all)
        btn_row.addWidget(btn_word_all)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_generate(self):
        settings = AppState.get("latest_settings", {})
        if not settings.get("api_key"):
            QMessageBox.warning(self, "경고", "API Key를 설정해주세요.")
            return

        # Get questions
        questions = []
        text = self.qa_input.toPlainText().strip()
        if text:
            questions = [q.strip() for q in text.split('\n') if q.strip()]

        if not questions:
            # Try Excel
            paths = self.excel_picker.get_file_paths()
            if paths:
                try:
                    import pandas as pd
                    df = pd.read_excel(paths[0])
                    col = df.columns[0]
                    questions = df[col].dropna().astype(str).tolist()
                except Exception as e:
                    QMessageBox.critical(self, "오류", f"Excel 읽기 실패: {e}")
                    return

        if not questions:
            QMessageBox.warning(self, "경고", "질문을 입력하세요.")
            return

        # Get context from selected documents
        project = AppState.get("current_project", "")
        file_context = ""
        rag_context = ""
        if project and core_rag.is_indexed(project):
            if self._selected_docs:
                file_context = core_rag.load_selected_project_docs(project, self._selected_docs)
                self.project_status.setText(
                    f"프로젝트 '{project}': {len(self._selected_docs)}개 문서 기반 답변",
                    "success"
                )
            else:
                file_context = core_rag.load_all_project_docs(project)
                self.project_status.setText(f"프로젝트 '{project}': 전체 문서 기반 답변", "success")
        else:
            self.project_status.setText("프로젝트 없음 - 일반 답변", "warning")

        self.btn_generate.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, len(questions))

        self._worker = QaWorker(settings["api_key"], settings["model_name"],
                                 questions, file_context, rag_context)
        self._worker.progress.connect(lambda c, t: self.progress.setValue(c))
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(lambda e: (
            QMessageBox.critical(self, "오류", e),
            self.btn_generate.setEnabled(True)
        ))
        self._worker.start()

    def _on_done(self, results):
        AppState.set("lp_qa_results", results)

        # Clear previous results
        while self.results_layout.count() > 1:  # Keep the stretch
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new Q&A items
        for i, r in enumerate(results):
            qa_widget = QaItemWidget(r["question"], r["answer"])
            self.results_layout.insertWidget(i, qa_widget)

        self.progress.setVisible(False)
        self.btn_generate.setEnabled(True)

    def _save_excel(self):
        results = AppState.get("lp_qa_results", [])
        if not results:
            QMessageBox.warning(self, "경고", "저장할 결과가 없습니다.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Excel 저장", "lp_qa.xlsx", "Excel (*.xlsx)")
        if path:
            import pandas as pd
            df = pd.DataFrame(results)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "완료", f"파일이 저장되었습니다:\n{path}")

    def _save_word_all(self):
        """Export all Q&A results to a single Word document."""
        results = AppState.get("lp_qa_results", [])
        if not results:
            QMessageBox.warning(self, "경고", "저장할 결과가 없습니다.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Word 저장", "lp_qa_all.docx", "Word (*.docx)")
        if path:
            try:
                # Create markdown content for all Q&A
                markdown_content = "# LP Q&A 답변 모음\n\n"
                for i, r in enumerate(results, 1):
                    markdown_content += f"## Q{i}: {r['question']}\n\n"
                    markdown_content += f"{r['answer']}\n\n"
                    markdown_content += "---\n\n"

                docx_bytes = utils_markdown.markdown_to_docx(markdown_content, use_template=True)

                with open(path, 'wb') as f:
                    f.write(docx_bytes)

                QMessageBox.information(self, "완료", f"Word 파일이 저장되었습니다:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"Word 변환 실패: {e}")

    def _on_doc_selection_changed(self, selected_docs):
        """Handle document selection change."""
        self._selected_docs = selected_docs

    def _load_project_documents(self):
        """Load project documents into document list widget."""
        project = AppState.get("current_project", "")
        if not project:
            self.doc_list.clear()
            return

        doc_names = core_rag.get_indexed_doc_names(project) or []
        if doc_names:
            self.doc_list.set_documents(doc_names, check_all=True)
            self.project_status.setText(
                f"✅ 프로젝트 '{project}': {len(doc_names)}개 문서 로드됨. 참고할 문서를 선택하세요.",
                "success"
            )
        else:
            self.doc_list.clear()
            self.project_status.setText(
                f"⚠️ 프로젝트 '{project}'에 로드된 문서가 없습니다.",
                "warning"
            )

    def refresh(self):
        project = AppState.get("current_project", "")
        if project:
            self._load_project_documents()
        else:
            self.doc_list.clear()
            self.project_status.setText("프로젝트를 선택하면 문서 기반으로 답변합니다.", "info")

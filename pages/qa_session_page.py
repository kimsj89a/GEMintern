"""자료기반 Q&A 세션 페이지.
좌측: FolderTreeSelector로 소스 문서 선택 (폴더 단위)
우측: ChatWidget으로 대화형 Q&A
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QMessageBox, QProgressBar
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from app_state import AppState
from widgets.folder_tree_selector import FolderTreeSelector
from widgets.chat_widget import ChatWidget
from widgets.status_box import StatusBox
import core_rag


class QaSessionWorker(QThread):
    """Background worker for generating Q&A answers."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, model, question, context, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model = model
        self.question = question
        self.context = context

    def run(self):
        try:
            import core_logic
            answer = core_logic.generate_qa_answer(
                self.api_key, self.model, self.context, self.question
            )
            self.finished.emit(answer)
        except Exception as e:
            self.error.emit(str(e))


class QaSessionPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._selected_docs = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        # Title
        title = QLabel("자료기반 Q&A")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("프로젝트 문서를 소스로 선택하고 질문하면, AI가 문서 기반으로 답변합니다.")
        subtitle.setStyleSheet("color: #6c757d; font-size: 13px; margin-bottom: 8px;")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Status
        self.status = StatusBox("프로젝트를 선택하면 문서 목록이 표시됩니다.", "info")
        layout.addWidget(self.status)

        # Splitter: left=source selector, right=chat
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: folder tree selector
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 8, 0)

        self.folder_selector = FolderTreeSelector()
        self.folder_selector.selection_changed.connect(self._on_selection_changed)
        left_layout.addWidget(self.folder_selector)

        left_layout.addStretch()
        splitter.addWidget(left)

        # Right: chat
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        self.chat = ChatWidget("질문을 입력하세요 (예: 이 회사의 주요 매출원은?)")
        self.chat.message_sent.connect(self._on_question)
        right_layout.addWidget(self.chat)

        # Bottom buttons
        btn_row = QHBoxLayout()
        self.btn_clear = QPushButton("대화 초기화")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                color: #6c757d; border: 1px solid #dee2e6; border-radius: 4px;
                padding: 6px 16px; background: white; font-size: 12px;
            }
            QPushButton:hover { background: #f0f2f6; }
        """)
        self.btn_clear.clicked.connect(self.chat.clear_messages)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([280, 520])

        layout.addWidget(splitter)

    def _on_selection_changed(self, selected_docs):
        self._selected_docs = selected_docs
        project = AppState.get("current_project", "")
        if selected_docs:
            self.status.setText(
                f"프로젝트 '{project}': {len(selected_docs)}개 문서 선택됨",
                "success"
            )
        elif project:
            self.status.setText(
                "문서를 선택해주세요. 선택된 문서를 소스로 답변합니다.",
                "warning"
            )

    def _on_question(self, question):
        settings = AppState.get("latest_settings", {})
        if not settings.get("api_key"):
            QMessageBox.warning(self, "경고", "API Key를 설정해주세요.")
            return

        project = AppState.get("current_project", "")
        if not project:
            QMessageBox.warning(self, "경고", "프로젝트를 먼저 선택해주세요.")
            return

        if not self._selected_docs:
            QMessageBox.warning(self, "경고", "소스 문서를 선택해주세요.")
            return

        # Show user message
        self.chat.add_message("user", question)
        self.chat.set_enabled(False)

        # Load context from selected docs
        context = core_rag.load_selected_project_docs(project, self._selected_docs)

        # Start worker
        self._worker = QaSessionWorker(
            settings["api_key"],
            settings.get("model_name", "gemini-3.1-pro-preview"),
            question,
            context
        )
        self._worker.finished.connect(self._on_answer)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_answer(self, answer):
        self.chat.add_message("assistant", answer)
        self.chat.set_enabled(True)
        self._worker = None

    def _on_error(self, error_msg):
        self.chat.add_message("assistant", f"오류가 발생했습니다: {error_msg}")
        self.chat.set_enabled(True)
        self._worker = None

    def refresh(self):
        project = AppState.get("current_project", "")
        if project:
            self.folder_selector.load_project(project, check_all=True)
            doc_count = core_rag.get_indexed_count(project)
            if doc_count > 0:
                self.status.setText(
                    f"프로젝트 '{project}': {doc_count}개 문서 로드됨. 참고할 문서를 선택하세요.",
                    "success"
                )
            else:
                self.status.setText(
                    f"프로젝트 '{project}'에 로드된 문서가 없습니다.",
                    "warning"
                )
        else:
            self.folder_selector.clear()
            self.status.setText("프로젝트를 선택하면 문서 목록이 표시됩니다.", "info")

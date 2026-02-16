"""Project management page - replaces ui_project.render_project_hub()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QFrame, QMessageBox,
    QFileDialog, QProgressBar, QSplitter, QDialog, QTextEdit, QMenu
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.status_box import StatusBox
from widgets.collapsible import CollapsibleBox
import core_rag
import utils


class ProjectPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        title = QLabel("📂 프로젝트 관리 Hub")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Splitter: left=project list, right=project detail
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Project list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 16, 0)

        left_header = QLabel("프로젝트 목록")
        left_header.setStyleSheet("font-size: 15px; font-weight: bold;")
        left_layout.addWidget(left_header)

        # New project input
        new_row = QHBoxLayout()
        self.new_project_input = QLineEdit()
        self.new_project_input.setPlaceholderText("새 프로젝트 이름")
        new_row.addWidget(self.new_project_input)

        self.btn_create = QPushButton("생성")
        self.btn_create.setProperty("cssClass", "primary")
        self.btn_create.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 6px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_create.clicked.connect(self._create_project)
        new_row.addWidget(self.btn_create)
        left_layout.addLayout(new_row)

        self.project_list = QListWidget()
        self.project_list.setStyleSheet("""
            QListWidget { border: 1px solid #dee2e6; border-radius: 6px; }
            QListWidget::item { padding: 10px; }
            QListWidget::item:selected { background-color: #e6f0ff; color: #0068c9; }
        """)
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        left_layout.addWidget(self.project_list)

        self.btn_delete = QPushButton("🗑️ 프로젝트 삭제")
        self.btn_delete.setStyleSheet("""
            QPushButton { color: #dc3545; border: 1px solid #dc3545; border-radius: 4px;
                         padding: 6px 12px; background: white; }
            QPushButton:hover { background: #f8d7da; }
        """)
        self.btn_delete.clicked.connect(self._delete_project)
        left_layout.addWidget(self.btn_delete)

        splitter.addWidget(left)

        # Right panel: Project detail
        right = QWidget()
        self.right_layout = QVBoxLayout(right)
        self.right_layout.setContentsMargins(16, 0, 0, 0)

        self.detail_header = QLabel("프로젝트를 선택하세요")
        self.detail_header.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.right_layout.addWidget(self.detail_header)

        self.detail_status = StatusBox("좌측에서 프로젝트를 선택하거나 새로 생성하세요.", "info")
        self.right_layout.addWidget(self.detail_status)

        # File upload
        self.file_picker = FilePicker(
            "자료 파일 업로드",
            file_filter="Documents (*.pdf *.docx *.pptx *.xlsx *.txt *.md *.csv);;All Files (*)"
        )
        self.right_layout.addWidget(self.file_picker)

        self.btn_load = QPushButton("📥 자료 로드")
        self.btn_load.setProperty("cssClass", "primary")
        self.btn_load.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_load.clicked.connect(self._load_files)
        self.right_layout.addWidget(self.btn_load)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.right_layout.addWidget(self.progress)

        # Document list
        self.doc_list_label = QLabel("📚 로드된 문서")
        self.doc_list_label.setStyleSheet("font-weight: bold; margin-top: 12px;")
        self.right_layout.addWidget(self.doc_list_label)

        self.doc_list = QListWidget()
        self.doc_list.setStyleSheet("""
            QListWidget { border: 1px solid #dee2e6; border-radius: 6px; }
            QListWidget::item { padding: 6px; font-size: 12px; }
        """)
        self.doc_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.doc_list.customContextMenuRequested.connect(self._show_doc_context_menu)
        self.doc_list.itemDoubleClicked.connect(self._on_doc_double_click)
        self.right_layout.addWidget(self.doc_list)

        self.btn_delete_doc = QPushButton("🗑 선택 문서 삭제")
        self.btn_delete_doc.setStyleSheet("""
            QPushButton { color: #dc3545; border: 1px solid #dee2e6; border-radius: 4px;
                         padding: 4px 12px; background: white; font-size: 12px; }
        """)
        self.btn_delete_doc.clicked.connect(self._delete_doc)
        self.right_layout.addWidget(self.btn_delete_doc)

        self.right_layout.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)

    def _create_project(self):
        name = self.new_project_input.text().strip()
        if not name:
            return
        result = core_rag.create_project(name)
        if result["success"]:
            AppState.set("current_project", result["project"]["name"])
            self.new_project_input.clear()
            self.refresh()
        else:
            QMessageBox.warning(self, "오류", result.get("error", "프로젝트 생성 실패"))

    def _delete_project(self):
        current = self.project_list.currentItem()
        if not current:
            return
        name = current.text()
        reply = QMessageBox.question(
            self, "확인", f"'{name}' 프로젝트를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            core_rag.delete_project(name)
            if AppState.get("current_project") == name:
                AppState.set("current_project", "")
            self.refresh()

    def _on_project_selected(self, current, previous):
        if not current:
            return
        name = current.text()
        AppState.set("current_project", name)
        self._refresh_detail(name)

    def _refresh_detail(self, project_name):
        self.detail_header.setText(f"📂 {project_name}")
        docs = core_rag.get_indexed_doc_names(project_name) or []

        self.doc_list.clear()
        for doc in docs:
            self.doc_list.addItem(doc)

        if docs:
            self.detail_status.setText(f"{len(docs)}개 문서 로드됨", "success")
        else:
            self.detail_status.setText("파일을 업로드하고 '자료 로드' 버튼을 눌러주세요.", "info")

    def _load_files(self):
        project = AppState.get("current_project", "")
        if not project:
            QMessageBox.warning(self, "경고", "프로젝트를 먼저 선택하세요.")
            return

        file_paths = self.file_picker.get_file_paths()
        if not file_paths:
            QMessageBox.warning(self, "경고", "파일을 선택하세요.")
            return

        settings = AppState.get("latest_settings", {})
        api_key = settings.get("api_key", "")

        self.progress.setVisible(True)
        self.progress.setMaximum(len(file_paths))

        loaded = 0
        failed_files = []  # List of (filename, error_msg)

        for i, fpath in enumerate(file_paths):
            self.progress.setValue(i + 1)
            try:
                from workers import _FileWrapper
                import os
                filename = os.path.basename(fpath)

                with open(fpath, 'rb') as f:
                    wrapper = _FileWrapper(f, fpath)
                    parsed = utils.parse_uploaded_file(
                        wrapper, api_key=api_key,
                        docai_config=settings.get("docai_config")
                    )
                    if parsed:
                        core_rag.index_texts(api_key, {wrapper.name: parsed}, project)
                        loaded += 1
                    else:
                        failed_files.append((filename, "파일 파싱 결과가 없습니다."))
            except Exception as e:
                import os
                filename = os.path.basename(fpath)
                error_msg = f"{type(e).__name__}: {str(e)}"
                failed_files.append((filename, error_msg))
                print(f"Parse error for {fpath}: {e}")

        self.progress.setVisible(False)

        # Show results
        if loaded > 0 and not failed_files:
            self.detail_status.setText(f"✅ {loaded}개 파일 모두 로드 완료!", "success")
            self._refresh_detail(project)
        elif loaded > 0 and failed_files:
            # Some succeeded, some failed
            error_list = "\n".join([f"• {name}: {err}" for name, err in failed_files])
            msg = f"✅ 성공: {loaded}개\n❌ 실패: {len(failed_files)}개\n\n실패한 파일:\n{error_list}"
            QMessageBox.warning(self, "일부 파일 로드 실패", msg)
            self.detail_status.setText(f"⚠️ {loaded}개 로드 완료, {len(failed_files)}개 실패", "warning")
            self._refresh_detail(project)
        else:
            # All failed
            error_list = "\n".join([f"• {name}: {err}" for name, err in failed_files])
            msg = f"모든 파일 로드에 실패했습니다.\n\n{error_list}"
            QMessageBox.critical(self, "파일 로드 실패", msg)
            self.detail_status.setText("❌ 로드된 파일이 없습니다.", "error")

    def _delete_doc(self):
        """Delete selected document with confirmation dialog."""
        current = self.doc_list.currentItem()
        if not current:
            QMessageBox.warning(self, "경고", "삭제할 문서를 선택하세요.")
            return

        project = AppState.get("current_project", "")
        if not project:
            return

        doc_name = current.text()

        # Show confirmation dialog
        reply = QMessageBox.question(
            self, "문서 삭제 확인",
            f"'{doc_name}' 문서를 삭제하시겠습니까?\n\n"
            "문서는 휴지통으로 이동되며, 나중에 복구할 수 있습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # Default to No for safety
        )

        if reply == QMessageBox.StandardButton.Yes:
            result = core_rag.trash_document(project, doc_name)
            if result.get("success"):
                self.detail_status.setText(f"✅ '{doc_name}' 문서가 휴지통으로 이동되었습니다.", "success")
                self._refresh_detail(project)
            else:
                error_msg = result.get("error", "알 수 없는 오류")
                QMessageBox.critical(self, "삭제 실패", f"문서 삭제 중 오류가 발생했습니다:\n\n{error_msg}")
                self.detail_status.setText(f"❌ 문서 삭제 실패: {error_msg}", "error")

    def _show_doc_context_menu(self, position):
        """Show context menu for document list."""
        item = self.doc_list.itemAt(position)
        if not item:
            return

        project = AppState.get("current_project", "")
        if not project:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #e6f0ff;
                color: #0068c9;
            }
        """)

        # Preview action
        preview_action = QAction("📄 미리보기", self)
        preview_action.triggered.connect(lambda: self._on_doc_double_click(item))
        menu.addAction(preview_action)

        menu.addSeparator()

        # Delete action
        delete_action = QAction("🗑️ 삭제", self)
        delete_action.triggered.connect(lambda: self._delete_doc_from_menu(item.text()))
        menu.addAction(delete_action)

        menu.exec(self.doc_list.mapToGlobal(position))

    def _delete_doc_from_menu(self, doc_name):
        """Delete document from context menu action."""
        project = AppState.get("current_project", "")
        if not project:
            return

        # Show confirmation dialog
        reply = QMessageBox.question(
            self, "문서 삭제 확인",
            f"'{doc_name}' 문서를 삭제하시겠습니까?\n\n"
            "문서는 휴지통으로 이동되며, 나중에 복구할 수 있습니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            result = core_rag.trash_document(project, doc_name)
            if result.get("success"):
                self.detail_status.setText(f"✅ '{doc_name}' 문서가 휴지통으로 이동되었습니다.", "success")
                self._refresh_detail(project)
            else:
                error_msg = result.get("error", "알 수 없는 오류")
                QMessageBox.critical(self, "삭제 실패", f"문서 삭제 중 오류가 발생했습니다:\n\n{error_msg}")
                self.detail_status.setText(f"❌ 문서 삭제 실패: {error_msg}", "error")

    def _on_doc_double_click(self, item):
        """Show document preview dialog on double-click."""
        if not item:
            return

        project = AppState.get("current_project", "")
        if not project:
            return

        doc_name = item.text()
        content = core_rag._load_doc_file(project, doc_name)

        if not content:
            QMessageBox.warning(self, "경고", "문서 내용을 로드할 수 없습니다.")
            return

        # Create preview dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"📄 문서 미리보기: {doc_name}")
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        # Info label
        info_label = QLabel(f"프로젝트: {project} | 문서: {doc_name}")
        info_label.setStyleSheet("font-weight: bold; padding: 8px; background: #f0f2f6; border-radius: 4px;")
        layout.addWidget(info_label)

        # Content viewer
        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setMarkdown(content)
        viewer.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        viewer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        viewer.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 12px;
                font-family: 'Malgun Gothic', sans-serif;
                font-size: 11pt;
                background: white;
            }
        """)
        layout.addWidget(viewer)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_copy = QPushButton("📋 복사")
        btn_copy.clicked.connect(lambda: (
            viewer.selectAll(),
            viewer.copy(),
            viewer.moveCursor(viewer.textCursor().Start),
            QMessageBox.information(dialog, "완료", "문서 내용이 클립보드에 복사되었습니다.")
        ))
        btn_layout.addWidget(btn_copy)

        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(dialog.close)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        dialog.exec()

    def refresh(self):
        projects = core_rag.list_projects()
        self.project_list.clear()
        for p in projects:
            self.project_list.addItem(p["name"])

        current = AppState.get("current_project", "")
        if current:
            items = self.project_list.findItems(current, Qt.MatchFlag.MatchExactly)
            if items:
                self.project_list.setCurrentItem(items[0])
                self._refresh_detail(current)

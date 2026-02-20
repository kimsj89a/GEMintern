"""Project management page with folder tree view."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QFrame, QMessageBox,
    QFileDialog, QProgressBar, QSplitter, QDialog, QTextEdit, QMenu,
    QTreeWidget, QTreeWidgetItem, QInputDialog, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction, QIcon
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.status_box import StatusBox
import core_rag
import utils

# Item data role for storing metadata
ROLE_TYPE = Qt.ItemDataRole.UserRole  # "folder" or "doc"
ROLE_NAME = Qt.ItemDataRole.UserRole + 1  # actual name
ROLE_FOLDER = Qt.ItemDataRole.UserRole + 2  # parent folder name


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

        self.btn_delete = QPushButton("프로젝트 삭제")
        self.btn_delete.setStyleSheet("""
            QPushButton { color: #dc3545; border: 1px solid #dc3545; border-radius: 4px;
                         padding: 6px 12px; background: white; }
            QPushButton:hover { background: #f8d7da; }
        """)
        self.btn_delete.clicked.connect(self._delete_project)
        left_layout.addWidget(self.btn_delete)

        splitter.addWidget(left)

        # Right panel: Project detail with tree view
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

        # Upload buttons row
        upload_row = QHBoxLayout()
        self.btn_load = QPushButton("자료 로드")
        self.btn_load.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_load.clicked.connect(self._load_files)
        upload_row.addWidget(self.btn_load)
        self.right_layout.addLayout(upload_row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.right_layout.addWidget(self.progress)

        # Document tree header + folder controls
        tree_header = QHBoxLayout()
        self.doc_list_label = QLabel("문서 트리")
        self.doc_list_label.setStyleSheet("font-weight: bold; margin-top: 12px;")
        tree_header.addWidget(self.doc_list_label)
        tree_header.addStretch()

        self.btn_new_folder = QPushButton("+ 폴더")
        self.btn_new_folder.setStyleSheet("""
            QPushButton { background: #e6f0ff; color: #0068c9; border: none;
                         padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background: #cce0ff; }
        """)
        self.btn_new_folder.clicked.connect(self._create_folder)
        tree_header.addWidget(self.btn_new_folder)

        self.right_layout.addLayout(tree_header)

        # Tree widget
        self.doc_tree = QTreeWidget()
        self.doc_tree.setHeaderHidden(True)
        self.doc_tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.doc_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.doc_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 6px 4px;
                border-radius: 4px;
            }
            QTreeWidget::item:hover {
                background: #f0f2f6;
            }
            QTreeWidget::item:selected {
                background: #e6f0ff;
                color: #0068c9;
            }
            QTreeWidget::branch {
                background: white;
            }
        """)
        self.doc_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.doc_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        self.doc_tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.doc_tree.setMinimumHeight(200)
        self.right_layout.addWidget(self.doc_tree)

        # Bottom buttons
        btn_row = QHBoxLayout()
        self.btn_delete_doc = QPushButton("선택 문서 삭제")
        self.btn_delete_doc.setStyleSheet("""
            QPushButton { color: #dc3545; border: 1px solid #dee2e6; border-radius: 4px;
                         padding: 4px 12px; background: white; font-size: 12px; }
            QPushButton:hover { background: #f8d7da; }
        """)
        self.btn_delete_doc.clicked.connect(self._delete_doc)
        btn_row.addWidget(self.btn_delete_doc)
        btn_row.addStretch()
        self.right_layout.addLayout(btn_row)

        self.right_layout.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([300, 500])

        layout.addWidget(splitter)

    # ========================================
    # Project list actions
    # ========================================

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

    # ========================================
    # Tree view
    # ========================================

    def _refresh_detail(self, project_name):
        self.detail_header.setText(f"📂 {project_name}")
        folder_tree = core_rag.get_folder_tree(project_name)

        self.doc_tree.clear()
        total_docs = 0

        # Render named folders first (sorted)
        for folder_name in sorted(folder_tree.keys()):
            if folder_name == core_rag.ROOT_FOLDER:
                continue
            docs = folder_tree[folder_name]
            folder_item = QTreeWidgetItem(self.doc_tree)
            folder_item.setText(0, f"📁 {folder_name} ({len(docs)})")
            folder_item.setData(0, ROLE_TYPE, "folder")
            folder_item.setData(0, ROLE_NAME, folder_name)
            folder_item.setFlags(
                folder_item.flags() | Qt.ItemFlag.ItemIsDropEnabled
            )
            for doc in sorted(docs):
                doc_item = QTreeWidgetItem(folder_item)
                doc_item.setText(0, f"📄 {doc}")
                doc_item.setData(0, ROLE_TYPE, "doc")
                doc_item.setData(0, ROLE_NAME, doc)
                doc_item.setData(0, ROLE_FOLDER, folder_name)
            folder_item.setExpanded(True)
            total_docs += len(docs)

        # Render root (unfiled) documents
        root_docs = folder_tree.get(core_rag.ROOT_FOLDER, [])
        if root_docs:
            root_item = QTreeWidgetItem(self.doc_tree)
            root_item.setText(0, f"📁 미분류 ({len(root_docs)})")
            root_item.setData(0, ROLE_TYPE, "folder")
            root_item.setData(0, ROLE_NAME, core_rag.ROOT_FOLDER)
            root_item.setFlags(
                root_item.flags() | Qt.ItemFlag.ItemIsDropEnabled
            )
            for doc in sorted(root_docs):
                doc_item = QTreeWidgetItem(root_item)
                doc_item.setText(0, f"📄 {doc}")
                doc_item.setData(0, ROLE_TYPE, "doc")
                doc_item.setData(0, ROLE_NAME, doc)
                doc_item.setData(0, ROLE_FOLDER, core_rag.ROOT_FOLDER)
            root_item.setExpanded(True)
            total_docs += len(root_docs)

        if total_docs > 0:
            folder_count = len([k for k in folder_tree if k != core_rag.ROOT_FOLDER])
            self.detail_status.setText(
                f"{total_docs}개 문서, {folder_count}개 폴더", "success"
            )
        else:
            self.detail_status.setText("파일을 업로드하고 '자료 로드' 버튼을 눌러주세요.", "info")

    # ========================================
    # Folder management
    # ========================================

    def _create_folder(self):
        project = AppState.get("current_project", "")
        if not project:
            QMessageBox.warning(self, "경고", "프로젝트를 먼저 선택하세요.")
            return

        name, ok = QInputDialog.getText(self, "새 폴더", "폴더 이름:")
        if ok and name.strip():
            result = core_rag.create_folder(project, name.strip())
            if result["success"]:
                self._refresh_detail(project)
            else:
                QMessageBox.warning(self, "오류", result.get("error", "폴더 생성 실패"))

    # ========================================
    # Context menu
    # ========================================

    def _show_tree_context_menu(self, position):
        item = self.doc_tree.itemAt(position)
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

        if item is None:
            # Right-click on empty area
            new_folder = QAction("📁 새 폴더", self)
            new_folder.triggered.connect(self._create_folder)
            menu.addAction(new_folder)
        elif item.data(0, ROLE_TYPE) == "folder":
            folder_name = item.data(0, ROLE_NAME)

            if folder_name != core_rag.ROOT_FOLDER:
                rename_action = QAction("✏️ 이름 변경", self)
                rename_action.triggered.connect(lambda: self._rename_folder(folder_name))
                menu.addAction(rename_action)

                delete_action = QAction("🗑️ 폴더 삭제", self)
                delete_action.triggered.connect(lambda: self._delete_folder(folder_name))
                menu.addAction(delete_action)

                menu.addSeparator()

            new_folder = QAction("📁 새 폴더", self)
            new_folder.triggered.connect(self._create_folder)
            menu.addAction(new_folder)
        else:
            # Document item
            doc_name = item.data(0, ROLE_NAME)

            preview_action = QAction("📄 미리보기", self)
            preview_action.triggered.connect(lambda: self._preview_doc(doc_name))
            menu.addAction(preview_action)

            # Move to folder submenu
            folders = core_rag.list_folders(project)
            if folders:
                move_menu = menu.addMenu("📁 폴더로 이동")
                current_folder = item.data(0, ROLE_FOLDER)

                # Add root option
                if current_folder != core_rag.ROOT_FOLDER:
                    root_action = QAction("미분류", self)
                    root_action.triggered.connect(
                        lambda: self._move_doc(doc_name, core_rag.ROOT_FOLDER)
                    )
                    move_menu.addAction(root_action)

                for f in folders:
                    if f != current_folder:
                        f_action = QAction(f, self)
                        f_action.triggered.connect(
                            lambda checked, folder=f: self._move_doc(doc_name, folder)
                        )
                        move_menu.addAction(f_action)

            menu.addSeparator()

            delete_action = QAction("🗑️ 삭제", self)
            delete_action.triggered.connect(lambda: self._delete_doc_by_name(doc_name))
            menu.addAction(delete_action)

        menu.exec(self.doc_tree.mapToGlobal(position))

    def _rename_folder(self, old_name):
        project = AppState.get("current_project", "")
        if not project:
            return
        new_name, ok = QInputDialog.getText(self, "폴더 이름 변경", "새 이름:", text=old_name)
        if ok and new_name.strip():
            result = core_rag.rename_folder(project, old_name, new_name.strip())
            if result["success"]:
                self._refresh_detail(project)
            else:
                QMessageBox.warning(self, "오류", result.get("error", ""))

    def _delete_folder(self, folder_name):
        project = AppState.get("current_project", "")
        if not project:
            return
        reply = QMessageBox.question(
            self, "폴더 삭제",
            f"'{folder_name}' 폴더를 삭제하시겠습니까?\n하위 문서는 미분류로 이동됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            core_rag.delete_folder(project, folder_name)
            self._refresh_detail(project)

    def _move_doc(self, doc_name, target_folder):
        project = AppState.get("current_project", "")
        if not project:
            return
        core_rag.move_doc_to_folder(project, doc_name, target_folder)
        self._refresh_detail(project)

    # ========================================
    # Document actions
    # ========================================

    def _on_tree_double_click(self, item, column):
        if item and item.data(0, ROLE_TYPE) == "doc":
            self._preview_doc(item.data(0, ROLE_NAME))

    def _preview_doc(self, doc_name):
        project = AppState.get("current_project", "")
        if not project:
            return

        content = core_rag._load_doc_file(project, doc_name)
        if not content:
            QMessageBox.warning(self, "경고", "문서 내용을 로드할 수 없습니다.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"문서 미리보기: {doc_name}")
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(f"프로젝트: {project} | 문서: {doc_name}")
        info_label.setStyleSheet("font-weight: bold; padding: 8px; background: #f0f2f6; border-radius: 4px;")
        layout.addWidget(info_label)

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

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_copy = QPushButton("복사")
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

    def _delete_doc(self):
        """Delete selected document from tree."""
        item = self.doc_tree.currentItem()
        if not item or item.data(0, ROLE_TYPE) != "doc":
            QMessageBox.warning(self, "경고", "삭제할 문서를 선택하세요.")
            return
        self._delete_doc_by_name(item.data(0, ROLE_NAME))

    def _delete_doc_by_name(self, doc_name):
        project = AppState.get("current_project", "")
        if not project:
            return

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
                self.detail_status.setText(f"'{doc_name}' 휴지통으로 이동", "success")
                self._refresh_detail(project)
            else:
                error_msg = result.get("error", "알 수 없는 오류")
                QMessageBox.critical(self, "삭제 실패", error_msg)

    # ========================================
    # File loading
    # ========================================

    def _load_files(self):
        project = AppState.get("current_project", "")
        if not project:
            QMessageBox.warning(self, "경고", "프로젝트를 먼저 선택하세요.")
            return

        file_paths = self.file_picker.get_file_paths()
        if not file_paths:
            QMessageBox.warning(self, "경고", "파일을 선택하세요.")
            return

        # Determine target folder from current tree selection
        target_folder = core_rag.ROOT_FOLDER
        current_item = self.doc_tree.currentItem()
        if current_item:
            if current_item.data(0, ROLE_TYPE) == "folder":
                target_folder = current_item.data(0, ROLE_NAME)
            elif current_item.data(0, ROLE_FOLDER):
                target_folder = current_item.data(0, ROLE_FOLDER)

        settings = AppState.get("latest_settings", {})
        api_key = settings.get("api_key", "")

        self.progress.setVisible(True)
        self.progress.setMaximum(len(file_paths))

        loaded = 0
        failed_files = []

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
                        core_rag.index_texts_to_folder(
                            api_key, {wrapper.name: parsed}, project, target_folder
                        )
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

        if loaded > 0 and not failed_files:
            folder_label = target_folder if target_folder != core_rag.ROOT_FOLDER else "미분류"
            self.detail_status.setText(
                f"{loaded}개 파일 [{folder_label}] 폴더에 로드 완료", "success"
            )
            self._refresh_detail(project)
        elif loaded > 0 and failed_files:
            error_list = "\n".join([f"- {name}: {err}" for name, err in failed_files])
            QMessageBox.warning(self, "일부 파일 로드 실패",
                                f"성공: {loaded}개\n실패: {len(failed_files)}개\n\n{error_list}")
            self._refresh_detail(project)
        else:
            error_list = "\n".join([f"- {name}: {err}" for name, err in failed_files])
            QMessageBox.critical(self, "파일 로드 실패", f"모든 파일 로드 실패\n\n{error_list}")

    # ========================================
    # Refresh
    # ========================================

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

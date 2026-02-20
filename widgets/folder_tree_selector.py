"""
Folder tree widget with checkboxes for selecting source documents.
Supports folder-level toggling: checking a folder checks all child docs.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import pyqtSignal, Qt
import core_rag


ROLE_TYPE = Qt.ItemDataRole.UserRole
ROLE_NAME = Qt.ItemDataRole.UserRole + 1


class FolderTreeSelector(QWidget):
    """Folder tree with checkboxes. Emits selected document names.

    Signals:
        selection_changed(list): List of selected document names (stems).
    """

    selection_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        header.setSpacing(8)

        self.label = QLabel("소스 문서 선택")
        self.label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(self.label)
        header.addStretch()

        self.btn_select_all = QPushButton("전체 선택")
        self.btn_select_all.setStyleSheet("""
            QPushButton {
                background: #e6f0ff; color: #0068c9; border: none;
                padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #cce0ff; }
        """)
        self.btn_select_all.clicked.connect(self._select_all)
        header.addWidget(self.btn_select_all)

        self.btn_select_none = QPushButton("전체 해제")
        self.btn_select_none.setStyleSheet("""
            QPushButton {
                background: #f0f2f6; color: #6c757d; border: none;
                padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #e2e6ea; }
        """)
        self.btn_select_none.clicked.connect(self._select_none)
        header.addWidget(self.btn_select_none)

        layout.addLayout(header)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 4px 4px;
                border-radius: 4px;
            }
            QTreeWidget::item:hover {
                background: #f0f2f6;
            }
            QTreeWidget::branch {
                background: white;
            }
        """)
        self.tree.setMinimumHeight(150)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)

        # Info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        layout.addWidget(self.info_label)

    def load_project(self, project_name: str, check_all: bool = True):
        """Load folder tree from a project. Checks all docs by default."""
        self._updating = True
        self.tree.clear()

        if not project_name:
            self._updating = False
            self._update_info()
            return

        folder_tree = core_rag.get_folder_tree(project_name)
        check_state = Qt.CheckState.Checked if check_all else Qt.CheckState.Unchecked

        # Named folders first
        for folder_name in sorted(folder_tree.keys()):
            if folder_name == core_rag.ROOT_FOLDER:
                continue
            docs = folder_tree[folder_name]
            self._add_folder_node(folder_name, f"📁 {folder_name}", docs, check_state)

        # Root docs
        root_docs = folder_tree.get(core_rag.ROOT_FOLDER, [])
        if root_docs:
            self._add_folder_node(core_rag.ROOT_FOLDER, "📁 미분류", root_docs, check_state)

        self._updating = False
        self._update_info()
        self._emit_selection()

    def _add_folder_node(self, folder_key, display_name, docs, check_state):
        folder_item = QTreeWidgetItem(self.tree)
        folder_item.setText(0, f"{display_name} ({len(docs)})")
        folder_item.setData(0, ROLE_TYPE, "folder")
        folder_item.setData(0, ROLE_NAME, folder_key)
        folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        folder_item.setCheckState(0, check_state)

        for doc in sorted(docs):
            doc_item = QTreeWidgetItem(folder_item)
            doc_item.setText(0, f"📄 {doc}")
            doc_item.setData(0, ROLE_TYPE, "doc")
            doc_item.setData(0, ROLE_NAME, doc)
            doc_item.setFlags(doc_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            doc_item.setCheckState(0, check_state)

        folder_item.setExpanded(True)

    def get_selected_documents(self):
        """Return list of selected document names."""
        selected = []
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            for j in range(folder_item.childCount()):
                doc_item = folder_item.child(j)
                if doc_item.checkState(0) == Qt.CheckState.Checked:
                    selected.append(doc_item.data(0, ROLE_NAME))
        return selected

    def _on_item_changed(self, item, column):
        if self._updating:
            return

        item_type = item.data(0, ROLE_TYPE)
        if item_type == "folder":
            # Toggle all children to match folder state
            self._updating = True
            state = item.checkState(0)
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)
            self._updating = False
        elif item_type == "doc":
            # Update parent folder check state
            self._updating = True
            parent = item.parent()
            if parent:
                self._update_folder_check_state(parent)
            self._updating = False

        self._update_info()
        self._emit_selection()

    def _update_folder_check_state(self, folder_item):
        """Update folder checkbox based on children states."""
        total = folder_item.childCount()
        checked = sum(
            1 for i in range(total)
            if folder_item.child(i).checkState(0) == Qt.CheckState.Checked
        )
        if checked == 0:
            folder_item.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked == total:
            folder_item.setCheckState(0, Qt.CheckState.Checked)
        else:
            folder_item.setCheckState(0, Qt.CheckState.PartiallyChecked)

    def _select_all(self):
        self._updating = True
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            folder_item.setCheckState(0, Qt.CheckState.Checked)
            for j in range(folder_item.childCount()):
                folder_item.child(j).setCheckState(0, Qt.CheckState.Checked)
        self._updating = False
        self._update_info()
        self._emit_selection()

    def _select_none(self):
        self._updating = True
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            folder_item.setCheckState(0, Qt.CheckState.Unchecked)
            for j in range(folder_item.childCount()):
                folder_item.child(j).setCheckState(0, Qt.CheckState.Unchecked)
        self._updating = False
        self._update_info()
        self._emit_selection()

    def _update_info(self):
        total = 0
        selected = 0
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            for j in range(folder_item.childCount()):
                total += 1
                if folder_item.child(j).checkState(0) == Qt.CheckState.Checked:
                    selected += 1
        if total == 0:
            self.info_label.setText("프로젝트를 선택하면 문서 목록이 표시됩니다.")
        else:
            self.info_label.setText(f"선택: {selected}개 / 전체: {total}개")

    def _emit_selection(self):
        self.selection_changed.emit(self.get_selected_documents())

    def clear(self):
        self.tree.clear()
        self._update_info()

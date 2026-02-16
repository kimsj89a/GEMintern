"""
Document list widget with checkboxes for selecting which documents to include.
Updates automatically when project selection changes.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt


class DocumentListWidget(QWidget):
    """Widget displaying project documents with checkboxes for selection.

    Signals:
        selection_changed: Emitted when document selection changes (selected_docs: List[str])
    """

    selection_changed = pyqtSignal(list)  # List of selected document names

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with select all/none buttons
        header = QHBoxLayout()
        header.setSpacing(8)

        self.label = QLabel("📚 프로젝트 문서 선택")
        self.label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(self.label)

        header.addStretch()

        self.btn_select_all = QPushButton("전체 선택")
        self.btn_select_all.setStyleSheet("""
            QPushButton {
                background: #e6f0ff;
                color: #0068c9;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #cce0ff; }
        """)
        self.btn_select_all.clicked.connect(self._select_all)
        header.addWidget(self.btn_select_all)

        self.btn_select_none = QPushButton("전체 해제")
        self.btn_select_none.setStyleSheet("""
            QPushButton {
                background: #f0f2f6;
                color: #6c757d;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background: #e2e6ea; }
        """)
        self.btn_select_none.clicked.connect(self._select_none)
        header.addWidget(self.btn_select_none)

        layout.addLayout(header)

        # Document list with checkboxes
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #f0f2f6;
            }
        """)
        self.list_widget.setMinimumHeight(120)
        self.list_widget.setMaximumHeight(200)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.list_widget)

        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        layout.addWidget(self.info_label)

    def set_documents(self, doc_names, check_all=True):
        """Set the list of documents and optionally check all by default.

        Args:
            doc_names: List of document names (without .md extension)
            check_all: If True, all documents are checked by default
        """
        # Block signals while updating
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for doc_name in doc_names:
            item = QListWidgetItem(doc_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if check_all:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)

        self.list_widget.blockSignals(False)
        self._update_info_label()
        self._emit_selection()

    def get_selected_documents(self):
        """Get list of selected document names.

        Returns:
            List of document names that are checked
        """
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def _select_all(self):
        """Check all documents."""
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Checked)
        self.list_widget.blockSignals(False)
        self._update_info_label()
        self._emit_selection()

    def _select_none(self):
        """Uncheck all documents."""
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        self.list_widget.blockSignals(False)
        self._update_info_label()
        self._emit_selection()

    def _on_item_changed(self, item):
        """Handle item check state change."""
        self._update_info_label()
        self._emit_selection()

    def _update_info_label(self):
        """Update the info label with selection count."""
        total = self.list_widget.count()
        selected = len(self.get_selected_documents())
        if total == 0:
            self.info_label.setText("프로젝트를 선택하면 문서 목록이 표시됩니다.")
        else:
            self.info_label.setText(f"선택됨: {selected}개 / 전체: {total}개")

    def _emit_selection(self):
        """Emit selection changed signal."""
        self.selection_changed.emit(self.get_selected_documents())

    def clear(self):
        """Clear all documents from the list."""
        self.list_widget.clear()
        self._update_info_label()

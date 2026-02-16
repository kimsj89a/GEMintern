"""Home/Dashboard page - replaces render_dashboard() in app.py."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout
)
from PyQt6.QtCore import pyqtSignal
from app_state import AppState


class DashCard(QFrame):
    """Dashboard card widget."""
    clicked = pyqtSignal()

    def __init__(self, icon, phase_num, title, desc, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor if hasattr(Qt, 'CursorShape') else 0)
        self.setProperty("cssClass", "card-clickable")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter if hasattr(Qt, 'AlignmentFlag') else 0)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 40px; border: none;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(icon_lbl)

        phase_lbl = QLabel(phase_num)
        phase_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #2383E2; border: none;")
        phase_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        phase_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(phase_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #37352F; border: none;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 13px; color: #787774; border: none;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        desc_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(desc_lbl)

    def mousePressEvent(self, event):
        self.clicked.emit()


from PyQt6.QtCore import Qt


class HomePage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)

        # Title
        title = QLabel("🏠 GEM Intern Dashboard")
        title.setProperty("cssClass", "title")
        layout.addWidget(title)

        subtitle = QLabel("투자 분석 업무의 단계를 선택하세요.")
        subtitle.setProperty("cssClass", "subtitle")
        layout.addWidget(subtitle)

        # Investment Workflow section
        section1 = QLabel("🚀 Investment Workflow")
        section1.setProperty("cssClass", "heading2")
        layout.addWidget(section1)

        workflow_row = QHBoxLayout()
        workflow_row.setSpacing(16)
        phases = [
            ("📥", "Phase 1", "사전 정보 수집", "자료 수집, 시장 조사, 초기 검토", "phase1"),
            ("📝", "Phase 2", "투심보고서 작성", "IM 작성, Valuation, 투자심의", "phase2"),
        ]
        for icon, num, title_text, desc, page_id in phases:
            card = DashCard(icon, num, title_text, desc)
            card.clicked.connect(lambda pid=page_id: self.navigate_to.emit(pid))
            workflow_row.addWidget(card)

        layout.addLayout(workflow_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #E9E9E7; max-height: 1px; margin: 20px 0;")
        layout.addWidget(sep)

        # Tools & Project section
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(24)

        # Tools
        tools_col = QVBoxLayout()
        tools_col.setSpacing(12)
        tools_header = QLabel("🛠️ Independent Tools")
        tools_header.setProperty("cssClass", "heading2")
        tools_col.addWidget(tools_header)

        tools = [
            ("📑 IM 작성", "im"),
            ("📢 발표자료 (PPT)", "ppt_tools"),
            ("🙋‍♂️ LP Q&A 대응", "lp_qa"),
        ]
        for label, page_id in tools:
            btn = QPushButton(label)
            btn.setProperty("cssClass", "secondary")
            btn.clicked.connect(lambda checked, pid=page_id: self.navigate_to.emit(pid))
            tools_col.addWidget(btn)

        tools_col.addStretch()
        bottom_row.addLayout(tools_col)

        # Project
        proj_col = QVBoxLayout()
        proj_col.setSpacing(12)
        proj_header = QLabel("📂 Project")
        proj_header.setProperty("cssClass", "heading2")
        proj_col.addWidget(proj_header)

        btn_proj = QPushButton("📂 프로젝트 관리")
        btn_proj.setProperty("cssClass", "primary")
        btn_proj.clicked.connect(lambda: self.navigate_to.emit("project"))
        proj_col.addWidget(btn_proj)

        proj_desc = QLabel("문서 저장소 및 RAG 설정")
        proj_desc.setProperty("cssClass", "caption")
        proj_col.addWidget(proj_desc)
        proj_col.addStretch()
        bottom_row.addLayout(proj_col)

        layout.addLayout(bottom_row)
        layout.addStretch()

    def refresh(self):
        pass

"""
Workflow page - replaces ui_workflow.py.
Supports Phase 1 (tab-based), Phase 2 (step-based), and utility workflows (IM, PPT).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTextEdit, QComboBox, QCheckBox, QRadioButton,
    QButtonGroup, QProgressBar, QFrame, QFileDialog,
    QMessageBox, QSlider, QGroupBox, QFormLayout, QPlainTextEdit,
    QSplitter, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from app_state import AppState
from widgets import (
    CollapsibleBox, FilePicker, ChatWidget, StepIndicator, MarkdownViewer, StatusBox,
    DocumentListWidget
)
from workers import GenerateWorker, RefineWorker, FileParseWorker, AnalysisWorker
import core_logic
import core_rag
import core_chained
import core_im
import core_im_ppt

# ========================================
# Phase/Utility configurations
# ========================================

CONFIGS = {
    "phase1": {
        "key_prefix": "p1",
        "title": "📥 사전 정보 수집 및 접촉",
        "subtitle": "공개 자료 기반 기업/산업/인력 사전 조사 및 자료 수집 정리",
        "page_type": "collection",
        "tabs": ["📁 자료 수집", "🔍 자료 분석", "💬 자료 기반 답변", "❓ 추가 질문 정리", "📝 보고서 생성"],
        "default_template": "simple_review",
        "template_options": {
            "simple_review": "1. 약식 투자검토 (Quick Memo)",
            "free_summary": "2. 자유 구조화 (요약보고서)",
        },
    },
    "phase2": {
        "key_prefix": "p2",
        "title": "📝 투심보고서 작성 (Investment Memo)",
        "subtitle": "NDA 후 내부 정보 기반 투자 매력도 분석 및 Valuation 검토",
        "page_type": "analysis",
        "steps": {
            1: ("📁", "데이터 입력"),
            2: ("🤖", "보고서 생성"),
            3: ("💬", "수정/보완"),
            4: ("📄", "최종 결과"),
        },
        "default_template": "investment",
        "template_options": {
            "investment": "1. 투자심사보고서 (표준)",
            "management": "2. 사후관리보고서",
            "term_sheet": "3. Term Sheet 정리",
            "loi_mou": "4. LOI/MOU 초안",
            "free_summary": "5. 자유 구조화 (요약)",
            "custom": "6. 자유 구조화 (요약보고서)",
        },
    },
    "im": {
        "key_prefix": "im",
        "title": "📑 IM 작성 (Information Memorandum)",
        "subtitle": "잠재 투자자를 위한 투자제안서(IM)를 PPT 형식으로 자동 생성합니다.",
        "page_type": "im_workflow",
        "steps": {
            1: ("📁", "데이터 입력"),
            2: ("🤖", "IM 생성"),
            3: ("💬", "수정/보완"),
            4: ("📊", "PPT 생성"),
        },
        "default_template": "im_full",
        "template_options": {
            "im_full": "1. IM 전체 (PPT 자동 생성)",
            "im": "2. IM 약식 (마크다운)",
            "free_summary": "3. 자유 구조화 (요약)",
        },
    },
}


class WorkflowPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, workflow_id, parent=None):
        super().__init__(parent)
        self.workflow_id = workflow_id
        self.config = CONFIGS.get(workflow_id, {})
        self.prefix = self.config.get("key_prefix", workflow_id)
        self._worker = None
        self._init_state()
        self._build_ui()

    def _init_state(self):
        """Initialize workflow state."""
        defaults = {
            f"{self.prefix}_current_step": 1,
            f"{self.prefix}_inputs": {},
            f"{self.prefix}_generated_text": "",
            f"{self.prefix}_file_context": "",
            f"{self.prefix}_chat_history": [],
            f"{self.prefix}_generation_complete": False,
            f"{self.prefix}_active_mode": self.config.get("default_template", ""),
            f"{self.prefix}_organized_summary": "",
            f"{self.prefix}_followup_questions": "",
        }
        for key, default in defaults.items():
            AppState.setdefault(key, default)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)

        # Title
        title = QLabel(self.config.get("title", ""))
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(title)

        subtitle = QLabel(self.config.get("subtitle", ""))
        subtitle.setStyleSheet("color: #6c757d; font-size: 13px;")
        subtitle.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(subtitle)

        page_type = self.config.get("page_type", "standard")

        if page_type == "collection":
            self._build_collection_ui(layout)
        elif page_type == "analysis":
            self._build_analysis_ui(layout)
        elif page_type == "im_workflow":
            self._build_im_workflow_ui(layout)
        else:
            self._build_standard_ui(layout)

    # ========================================
    # Collection (Phase 1) - Tab-based
    # ========================================

    def _build_collection_ui(self, parent_layout):
        self.tabs = QTabWidget()
        tab_labels = self.config.get("tabs", [])

        # Tab 1: 자료 수집
        self.tab_collect = self._build_tab_collect()
        self.tabs.addTab(self.tab_collect, tab_labels[0] if len(tab_labels) > 0 else "자료 수집")

        # Tab 2: 자료 분석
        self.tab_analyze = self._build_tab_analyze()
        self.tabs.addTab(self.tab_analyze, tab_labels[1] if len(tab_labels) > 1 else "자료 분석")

        # Tab 3: Q&A
        self.tab_qa = self._build_tab_qa()
        self.tabs.addTab(self.tab_qa, tab_labels[2] if len(tab_labels) > 2 else "Q&A")

        # Tab 4: 추가 질문
        self.tab_questions = self._build_tab_questions()
        self.tabs.addTab(self.tab_questions, tab_labels[3] if len(tab_labels) > 3 else "추가 질문")

        # Tab 5: 보고서 생성
        self.tab_report = self._build_tab_report()
        self.tabs.addTab(self.tab_report, tab_labels[4] if len(tab_labels) > 4 else "보고서")

        parent_layout.addWidget(self.tabs)

    def _build_tab_collect(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Project document status
        self.collect_project_status = StatusBox("", "info")
        layout.addWidget(self.collect_project_status)
        self._update_collection_project_status()

        # Document selection widget
        self.collect_doc_list = DocumentListWidget()
        self.collect_doc_list.selection_changed.connect(self._on_collect_doc_selection_changed)
        layout.addWidget(self.collect_doc_list)

        row = QHBoxLayout()

        # Left: File upload
        left = QVBoxLayout()
        left.addWidget(QLabel("📁 추가 자료 업로드"))
        self.collect_files = FilePicker(
            "감사보고서, 산업보고서 등",
            file_filter="Documents (*.pdf *.docx *.pptx *.xlsx *.txt);;All (*)"
        )
        left.addWidget(self.collect_files)
        row.addLayout(left)

        # Right: Context
        right = QVBoxLayout()
        right.addWidget(QLabel("💬 조사 배경 / 핵심 질문"))
        self.collect_context = QTextEdit()
        self.collect_context.setPlaceholderText("예: 기업명, 투자 배경, 산업 동향 등")
        self.collect_context.setMaximumHeight(120)
        self.collect_context.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.collect_context.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right.addWidget(self.collect_context)
        row.addLayout(right)

        layout.addLayout(row)

        # Load button row
        load_row = QHBoxLayout()
        self.btn_collect_load = QPushButton("📥 자료 로드 및 파싱")
        self.btn_collect_load.setProperty("cssClass", "primary")
        self.btn_collect_load.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_collect_load.clicked.connect(self._on_collect_load)
        load_row.addWidget(self.btn_collect_load)

        self.btn_stop_collect = QPushButton("⏹ 중지")
        self.btn_stop_collect.setStyleSheet("""
            QPushButton { background: #dc3545; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #c82333; }
        """)
        self.btn_stop_collect.clicked.connect(self._on_stop_worker)
        self.btn_stop_collect.setVisible(False)
        load_row.addWidget(self.btn_stop_collect)
        layout.addLayout(load_row)

        self.collect_status = StatusBox("파일을 업로드하고 자료 로드를 실행하세요.", "info")
        layout.addWidget(self.collect_status)

        self.collect_progress = QProgressBar()
        self.collect_progress.setVisible(False)
        layout.addWidget(self.collect_progress)

        layout.addStretch()
        return widget

    def _build_tab_analyze(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.btn_analyze = QPushButton("🤖 AI 자료 분석 실행")
        self.btn_analyze.setProperty("cssClass", "primary")
        self.btn_analyze.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_analyze.clicked.connect(self._on_analyze)
        layout.addWidget(self.btn_analyze)

        self.analyze_viewer = MarkdownViewer()
        self.analyze_viewer.setMinimumHeight(400)
        layout.addWidget(self.analyze_viewer)

        # Followup analysis
        layout.addWidget(QLabel("🔎 후속 분석 요청"))
        self.analyze_input = QTextEdit()
        self.analyze_input.setPlaceholderText("추가 분석 영역을 입력하세요")
        self.analyze_input.setMaximumHeight(80)
        self.analyze_input.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.analyze_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.analyze_input)

        self.btn_followup_analyze = QPushButton("🔎 후속 분석 실행")
        self.btn_followup_analyze.setProperty("cssClass", "primary")
        self.btn_followup_analyze.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 8px; border-radius: 6px; font-weight: bold; }
        """)
        self.btn_followup_analyze.clicked.connect(self._on_followup_analyze)
        layout.addWidget(self.btn_followup_analyze)

        return widget

    def _build_tab_qa(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.qa_chat = ChatWidget("질문을 입력하세요 (예: 이 회사의 주요 매출원은?)")
        self.qa_chat.message_sent.connect(self._on_qa_question)
        layout.addWidget(self.qa_chat)

        self.btn_qa_clear = QPushButton("🗑️ Q&A 초기화")
        self.btn_qa_clear.clicked.connect(self.qa_chat.clear_messages)
        layout.addWidget(self.btn_qa_clear)

        return widget

    def _build_tab_questions(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.btn_gen_questions = QPushButton("❓ 추가 질문 생성")
        self.btn_gen_questions.setProperty("cssClass", "primary")
        self.btn_gen_questions.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_gen_questions.clicked.connect(self._on_gen_questions)
        layout.addWidget(self.btn_gen_questions)

        self.questions_viewer = MarkdownViewer()
        self.questions_viewer.setMinimumHeight(400)
        layout.addWidget(self.questions_viewer)

        return widget

    def _build_tab_report(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Left: options
        left = QVBoxLayout()
        left.addWidget(QLabel("📝 템플릿 선택"))
        self.report_template = QComboBox()
        for k, v in self.config.get("template_options", {}).items():
            self.report_template.addItem(v, k)
        left.addWidget(self.report_template)

        left.addWidget(QLabel("생성 방식"))
        self.gen_mode_group = QButtonGroup()
        self.radio_chained = QRadioButton("📊 단계별 생성 (정확도↑)")
        self.radio_single = QRadioButton("🚀 한 번에 생성 (속도↑)")
        self.radio_chained.setChecked(True)
        self.gen_mode_group.addButton(self.radio_chained)
        self.gen_mode_group.addButton(self.radio_single)
        left.addWidget(self.radio_chained)
        left.addWidget(self.radio_single)

        self.check_inc_analysis = QCheckBox("자료 분석 결과 포함")
        self.check_inc_questions = QCheckBox("추가 질문 결과 포함")
        left.addWidget(self.check_inc_analysis)
        left.addWidget(self.check_inc_questions)

        self.btn_generate = QPushButton("🤖 보고서 생성")
        self.btn_generate.setProperty("cssClass", "primary")
        self.btn_generate.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_generate.clicked.connect(self._on_generate_report)
        left.addWidget(self.btn_generate)
        left.addStretch()
        layout.addLayout(left, 1)

        # Right: result
        right = QVBoxLayout()
        self.report_viewer = MarkdownViewer()
        self.report_viewer.setMinimumHeight(400)
        right.addWidget(self.report_viewer)

        btn_row = QHBoxLayout()
        self.btn_save_word = QPushButton("📄 Word 저장")
        self.btn_save_word.clicked.connect(lambda: self._save_file("docx"))
        btn_row.addWidget(self.btn_save_word)

        self.btn_save_ppt = QPushButton("📊 PPT 저장")
        self.btn_save_ppt.clicked.connect(lambda: self._save_file("pptx"))
        btn_row.addWidget(self.btn_save_ppt)
        right.addLayout(btn_row)

        self.report_progress = QProgressBar()
        self.report_progress.setRange(0, 0)  # Indeterminate
        self.report_progress.setVisible(False)
        right.addWidget(self.report_progress)

        layout.addLayout(right, 2)
        return widget

    # ========================================
    # Analysis (Phase 2) - Step-based
    # ========================================

    def _build_analysis_ui(self, parent_layout):
        # Step indicator
        self.step_indicator = StepIndicator(self.config.get("steps", {}))
        self.step_indicator.step_clicked.connect(self._go_to_step)
        parent_layout.addWidget(self.step_indicator)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #dee2e6;")
        parent_layout.addWidget(sep)

        # Stacked pages for each step
        from PyQt6.QtWidgets import QStackedWidget
        self.step_stack = QStackedWidget()

        # Step 1: Data input
        self.step_stack.addWidget(self._build_step_upload())
        # Step 2: Generate
        self.step_stack.addWidget(self._build_step_generate())
        # Step 3: Refine
        self.step_stack.addWidget(self._build_step_refine())
        # Step 4: Output
        self.step_stack.addWidget(self._build_step_output())

        parent_layout.addWidget(self.step_stack)

    def _build_standard_ui(self, parent_layout):
        """Standard 4-step workflow (IM, etc.)."""
        self.step_indicator = StepIndicator(self.config.get("steps", {}))
        self.step_indicator.step_clicked.connect(self._go_to_step)
        parent_layout.addWidget(self.step_indicator)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        parent_layout.addWidget(sep)

        from PyQt6.QtWidgets import QStackedWidget
        self.step_stack = QStackedWidget()

        self.step_stack.addWidget(self._build_step_upload())
        self.step_stack.addWidget(self._build_step_generate())
        self.step_stack.addWidget(self._build_step_refine())
        self.step_stack.addWidget(self._build_step_output())

        parent_layout.addWidget(self.step_stack)

    def _build_step_upload(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Left: Files
        left = QVBoxLayout()

        # Project document status
        self.upload_project_status = StatusBox("", "info")
        left.addWidget(self.upload_project_status)
        self._update_project_status()

        # Document selection widget
        self.upload_doc_list = DocumentListWidget()
        self.upload_doc_list.selection_changed.connect(self._on_upload_doc_selection_changed)
        left.addWidget(self.upload_doc_list)

        self.upload_files = FilePicker(
            "📁 파일 업로드",
            file_filter="Documents (*.pdf *.docx *.pptx *.xlsx *.txt);;All (*)"
        )
        left.addWidget(self.upload_files)

        left.addWidget(QLabel("💬 투자 배경 / 맥락"))
        self.upload_context = QTextEdit()
        self.upload_context.setPlaceholderText("예: 기업명, 딜 규모, 투자 배경 등")
        self.upload_context.setMaximumHeight(120)
        self.upload_context.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.upload_context.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left.addWidget(self.upload_context)
        layout.addLayout(left)

        # Right: Template
        right = QVBoxLayout()
        right.addWidget(QLabel("📝 템플릿 선택"))
        self.upload_template = QComboBox()
        for k, v in self.config.get("template_options", {}).items():
            self.upload_template.addItem(v, k)
        right.addWidget(self.upload_template)

        # Gen mode
        right.addWidget(QLabel("생성 방식"))
        self.upload_gen_group = QButtonGroup()
        self.upload_radio_chained = QRadioButton("📊 단계별 생성")
        self.upload_radio_single = QRadioButton("🚀 한 번에 생성")
        self.upload_radio_chained.setChecked(True)
        self.upload_gen_group.addButton(self.upload_radio_chained)
        self.upload_gen_group.addButton(self.upload_radio_single)
        right.addWidget(self.upload_radio_chained)
        right.addWidget(self.upload_radio_single)

        right.addStretch()

        btn_next = QPushButton("다음 단계 >>>")
        btn_next.setProperty("cssClass", "primary")
        btn_next.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #004085; }
        """)
        btn_next.clicked.connect(self._on_upload_next)
        right.addWidget(btn_next)

        layout.addLayout(right)
        return widget

    def _build_step_checklist(self):
        """Phase 2 only: Investment checklist."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("📋 투자 매력도 체크리스트"))

        self.checklist_items = [
            ("사업안정성", "비즈니스 모델의 안정성, 매출 다변화"),
            ("경쟁력", "기술력, 브랜드, 시장 지위, 진입장벽"),
            ("수익성", "영업이익률, EBITDA 마진"),
            ("전략적 파트너 협업 가능성", "시너지 효과, 파트너 네트워크"),
            ("가치증대 가능성", "성장 잠재력, 운영 개선 여지"),
            ("리스크 관리 용이성", "주요 리스크 식별 및 대응"),
            ("투자수익 예측 타당성", "재무 추정 신뢰성"),
            ("Valuation 적정성", "밸류에이션 수준, Multiple 적정성"),
        ]
        self.checklist_sliders = {}
        self.checklist_rationales = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for name, desc in self.checklist_items:
            box = CollapsibleBox(f"{name} - {desc}")

            row_widget = QWidget()
            row = QHBoxLayout(row_widget)

            # Score slider
            score_col = QVBoxLayout()
            score_col.addWidget(QLabel("점수 (1-5)"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(1, 5)
            slider.setValue(3)
            slider.setTickInterval(1)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            self.checklist_sliders[name] = slider
            score_col.addWidget(slider)
            score_label = QLabel("3")
            slider.valueChanged.connect(lambda v, lbl=score_label: lbl.setText(str(v)))
            score_col.addWidget(score_label)
            row.addLayout(score_col, 1)

            # Rationale
            rat_col = QVBoxLayout()
            rat_col.addWidget(QLabel("평가 근거"))
            rationale = QTextEdit()
            rationale.setPlaceholderText(f"{name}에 대한 평가 근거...")
            rationale.setMaximumHeight(60)
            rationale.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            rationale.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.checklist_rationales[name] = rationale
            rat_col.addWidget(rationale)
            row.addLayout(rat_col, 3)

            box.addWidget(row_widget)
            scroll_layout.addWidget(box)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Navigation
        nav = QHBoxLayout()
        btn_prev = QPushButton("<<< 이전 단계")
        btn_prev.clicked.connect(lambda: self._go_to_step(1))
        nav.addWidget(btn_prev)
        nav.addStretch()
        btn_next = QPushButton("다음: 보고서 생성 >>>")
        btn_next.setProperty("cssClass", "primary")
        btn_next.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 8px 16px; border-radius: 6px; font-weight: bold; }
        """)
        btn_next.clicked.connect(self._on_checklist_next)
        nav.addWidget(btn_next)
        layout.addLayout(nav)

        return widget

    def _build_step_generate(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("🤖 보고서 생성"))

        self.gen_viewer = MarkdownViewer()
        self.gen_viewer.setMinimumHeight(400)
        layout.addWidget(self.gen_viewer)

        self.gen_progress = QProgressBar()
        self.gen_progress.setRange(0, 0)
        self.gen_progress.setVisible(False)
        layout.addWidget(self.gen_progress)

        self.gen_status = StatusBox("보고서를 자동 생성합니다...", "info")
        layout.addWidget(self.gen_status)

        nav = QHBoxLayout()
        btn_prev = QPushButton("<<< 이전 단계")
        btn_prev.clicked.connect(lambda: self._go_to_step(
            AppState.get(f"{self.prefix}_current_step", 1) - 1
        ))
        nav.addWidget(btn_prev)
        nav.addStretch()

        self.btn_stop_gen = QPushButton("⏹ 중지")
        self.btn_stop_gen.setStyleSheet("""
            QPushButton { background: #dc3545; color: white; border: none;
                         padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background: #c82333; }
        """)
        self.btn_stop_gen.clicked.connect(self._on_stop_worker)
        self.btn_stop_gen.setVisible(False)
        nav.addWidget(self.btn_stop_gen)

        btn_regen = QPushButton("🔄 다시 생성")
        btn_regen.clicked.connect(self._on_regenerate)
        nav.addWidget(btn_regen)

        btn_next = QPushButton("다음: 수정/보완 >>>")
        btn_next.setProperty("cssClass", "primary")
        btn_next.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 8px 16px; border-radius: 6px; font-weight: bold; }
        """)
        btn_next.clicked.connect(lambda: self._go_to_step(
            AppState.get(f"{self.prefix}_current_step", 1) + 1
        ))
        nav.addWidget(btn_next)
        layout.addLayout(nav)

        return widget

    def _build_step_refine(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Left: document view
        left = QVBoxLayout()
        left.addWidget(QLabel("📄 현재 결과물"))
        self.refine_viewer = MarkdownViewer()
        self.refine_viewer.setMinimumHeight(400)
        left.addWidget(self.refine_viewer)
        layout.addLayout(left, 6)

        # Right: chat
        right = QVBoxLayout()
        right.addWidget(QLabel("💬 수정 요청"))
        self.refine_chat = ChatWidget("수정/보완 요청을 입력하세요")
        self.refine_chat.message_sent.connect(self._on_refine_message)
        right.addWidget(self.refine_chat)

        nav = QHBoxLayout()
        btn_prev = QPushButton("<<< 이전")
        btn_prev.clicked.connect(lambda: self._go_to_step(
            AppState.get(f"{self.prefix}_current_step", 1) - 1
        ))
        nav.addWidget(btn_prev)
        btn_next = QPushButton("최종 결과 >>>")
        btn_next.setProperty("cssClass", "primary")
        btn_next.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 8px 16px; border-radius: 6px; font-weight: bold; }
        """)
        btn_next.clicked.connect(lambda: self._go_to_step(
            len(self.config.get("steps", {1: None, 2: None, 3: None, 4: None}))
        ))
        nav.addWidget(btn_next)
        right.addLayout(nav)

        layout.addLayout(right, 4)
        return widget

    def _build_step_output(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("📄 최종 결과"))

        self.output_viewer = MarkdownViewer()
        self.output_viewer.setMinimumHeight(500)
        layout.addWidget(self.output_viewer)

        btn_row = QHBoxLayout()
        btn_word = QPushButton("📄 Word 다운로드")
        btn_word.clicked.connect(lambda: self._save_file("docx"))
        btn_row.addWidget(btn_word)

        btn_ppt = QPushButton("📊 PPT 다운로드")
        btn_ppt.clicked.connect(lambda: self._save_file("pptx"))
        btn_row.addWidget(btn_ppt)

        btn_copy = QPushButton("📋 클립보드 복사")
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(btn_copy)
        layout.addLayout(btn_row)

        nav = QHBoxLayout()
        btn_prev = QPushButton("<<< 수정하러 돌아가기")
        btn_prev.clicked.connect(lambda: self._go_to_step(
            len(self.config.get("steps", {1: None, 2: None, 3: None, 4: None})) - 1
        ))
        nav.addWidget(btn_prev)
        nav.addStretch()

        btn_restart = QPushButton("🔄 처음부터 다시")
        btn_restart.clicked.connect(self._reset_workflow)
        nav.addWidget(btn_restart)
        layout.addLayout(nav)

        return widget

    # ========================================
    # Event handlers
    # ========================================

    def _go_to_step(self, step):
        if step < 1:
            step = 1
        max_step = len(self.config.get("steps", {1: None, 2: None, 3: None, 4: None}))
        if step > max_step:
            step = max_step

        AppState.set(f"{self.prefix}_current_step", step)
        self.step_indicator.set_current(step)
        self.step_stack.setCurrentIndex(step - 1)

        # Auto-start generation if moving to generate step
        gen_step = 2
        if step == gen_step and not AppState.get(f"{self.prefix}_generation_complete"):
            self._start_generation()

        # Update viewers
        text = AppState.get(f"{self.prefix}_generated_text", "")
        if hasattr(self, 'gen_viewer'):
            self.gen_viewer.setMarkdown(text)
        if hasattr(self, 'refine_viewer'):
            self.refine_viewer.setMarkdown(text)
        if hasattr(self, 'output_viewer'):
            self.output_viewer.setMarkdown(text)

    def _on_collect_load(self):
        """Parse and load files for collection tab."""
        settings = AppState.get("latest_settings", {})
        api_key = settings.get("api_key", "")
        if not api_key:
            QMessageBox.warning(self, "경고", "설정에서 API Key를 먼저 입력해주세요.")
            return

        file_paths = self.collect_files.get_file_paths()
        project = AppState.get("current_project", "")

        if not file_paths and not project:
            QMessageBox.warning(self, "경고", "파일을 업로드하거나 프로젝트를 선택해주세요.")
            return

        self.btn_collect_load.setEnabled(False)
        self.collect_progress.setVisible(True)
        self.collect_progress.setRange(0, 0)
        if hasattr(self, 'btn_stop_collect'):
            self.btn_stop_collect.setVisible(True)

        # Get selected documents
        selected_docs = AppState.get(f"{self.prefix}_selected_docs", None)

        # Parse files in background
        self._worker = FileParseWorker(
            file_paths, api_key,
            docai_config=settings.get("docai_config"),
            template_option=self.config.get("default_template", ""),
            project_name=project,
            selected_docs=selected_docs
        )
        self._worker.finished.connect(self._on_files_parsed)
        self._worker.error.connect(self._on_parse_error)
        self._worker.start()

    def _on_files_parsed(self, file_context, ocr_text, parse_results=None):
        context = self.collect_context.toPlainText().strip()
        if context:
            AppState.set(f"{self.prefix}_context_text", context)

        AppState.set(f"{self.prefix}_file_context", file_context)

        # Show parse results summary
        if parse_results:
            success_count = sum(1 for r in parse_results.values() if r["success"])
            failed_count = len(parse_results) - success_count
            failed_files = [(name, r["error"]) for name, r in parse_results.items() if not r["success"]]

            if failed_count == 0:
                self.collect_status.setText(f"✅ {success_count}개 파일 모두 로드 완료! ({len(file_context):,}자)", "success")
            elif success_count > 0:
                error_list = "\n".join([f"• {name}: {err}" for name, err in failed_files])
                msg = f"✅ 성공: {success_count}개\n❌ 실패: {failed_count}개\n\n실패한 파일:\n{error_list}"
                QMessageBox.warning(self, "일부 파일 로드 실패", msg)
                self.collect_status.setText(f"⚠️ {success_count}개 로드, {failed_count}개 실패", "warning")
            else:
                error_list = "\n".join([f"• {name}: {err}" for name, err in failed_files])
                msg = f"모든 파일 로드에 실패했습니다.\n\n{error_list}"
                QMessageBox.critical(self, "파일 로드 실패", msg)
                self.collect_status.setText("❌ 로드 실패", "error")
        else:
            self.collect_status.setText(f"자료 로드 완료! ({len(file_context):,}자)", "success")

        self._hide_stop_buttons()

    def _on_parse_error(self, error_msg):
        self._hide_stop_buttons()
        self.collect_status.setText(f"파싱 오류: {error_msg}", "error")

    def _on_analyze(self):
        file_context = self._ensure_file_context()
        if not file_context.strip():
            QMessageBox.warning(self, "경고", "먼저 자료를 로드하거나 프로젝트를 선택해주세요.")
            return

        settings = AppState.get("latest_settings", {})
        self.btn_analyze.setEnabled(False)

        self._worker = AnalysisWorker(
            "material_summary",
            settings["api_key"], settings["model_name"],
            file_context=file_context
        )
        self._worker.finished.connect(self._on_analysis_done)
        self._worker.error.connect(lambda e: (
            QMessageBox.critical(self, "오류", e),
            self.btn_analyze.setEnabled(True)
        ))
        self._worker.start()

    def _on_analysis_done(self, result):
        AppState.set(f"{self.prefix}_organized_summary", result)
        self.analyze_viewer.setMarkdown(result)
        self.btn_analyze.setEnabled(True)

    def _ensure_file_context(self):
        """프로젝트 선택 시 file_context 자동 로드"""
        file_context = AppState.get(f"{self.prefix}_file_context", "")
        if not file_context.strip():
            project = AppState.get("current_project", "")
            if project:
                selected_docs = AppState.get(f"{self.prefix}_selected_docs", None)
                if selected_docs:
                    file_context = core_rag.load_selected_project_docs(project, selected_docs)
                else:
                    file_context = core_rag.load_all_project_docs(project)
                if file_context:
                    AppState.set(f"{self.prefix}_file_context", file_context)
        return file_context

    def _on_followup_analyze(self):
        user_input = self.analyze_input.toPlainText().strip()
        if not user_input:
            return

        settings = AppState.get("latest_settings", {})
        file_context = self._ensure_file_context()
        existing = AppState.get(f"{self.prefix}_organized_summary", "")

        self._worker = AnalysisWorker(
            "followup_analysis",
            settings["api_key"], settings["model_name"],
            file_context=file_context,
            existing_analysis=existing,
            user_input=user_input
        )
        self._worker.finished.connect(lambda r: (
            AppState.set(f"{self.prefix}_organized_summary", existing + "\n\n" + r),
            self.analyze_viewer.setMarkdown(AppState.get(f"{self.prefix}_organized_summary"))
        ))
        self._worker.error.connect(lambda e: QMessageBox.critical(self, "오류", e))
        self._worker.start()

    def _on_qa_question(self, question):
        file_context = self._ensure_file_context()
        if not file_context.strip():
            QMessageBox.warning(self, "경고", "먼저 자료를 로드하거나 프로젝트를 선택해주세요.")
            return

        settings = AppState.get("latest_settings", {})
        self.qa_chat.add_message("user", question)
        self.qa_chat.set_enabled(False)

        # Build prev QA context
        msgs = self.qa_chat.get_messages()
        prev_qa = "\n".join(
            f"Q: {m['content']}" if m['role'] == 'user' else f"A: {m['content']}"
            for m in msgs[-10:]
        )

        project = AppState.get("current_project", "")
        rag_context = ""
        if project and core_rag.is_indexed(project):
            selected_docs = AppState.get(f"{self.prefix}_selected_docs", None)
            if selected_docs:
                rag_context = core_rag.load_selected_project_docs(project, selected_docs)
            else:
                rag_context = core_rag.load_all_project_docs(project)

        self._worker = AnalysisWorker(
            "qa_answer",
            settings["api_key"], settings["model_name"],
            file_context=file_context,
            question=question,
            prev_qa_context=prev_qa,
            rag_context=rag_context
        )
        self._worker.finished.connect(lambda r: (
            self.qa_chat.add_message("assistant", r),
            self.qa_chat.set_enabled(True)
        ))
        self._worker.error.connect(lambda e: (
            self.qa_chat.add_message("assistant", f"오류: {e}"),
            self.qa_chat.set_enabled(True)
        ))
        self._worker.start()

    def _on_gen_questions(self):
        file_context = self._ensure_file_context()
        if not file_context.strip():
            QMessageBox.warning(self, "경고", "먼저 자료를 로드하거나 프로젝트를 선택해주세요.")
            return

        settings = AppState.get("latest_settings", {})
        self.btn_gen_questions.setEnabled(False)

        project = AppState.get("current_project", "")
        rag_context = ""
        if project and core_rag.is_indexed(project):
            selected_docs = AppState.get(f"{self.prefix}_selected_docs", None)
            if selected_docs:
                rag_context = core_rag.load_selected_project_docs(project, selected_docs)
            else:
                rag_context = core_rag.load_all_project_docs(project)

        self._worker = AnalysisWorker(
            "followup_questions",
            settings["api_key"], settings["model_name"],
            file_context=file_context,
            rag_context=rag_context
        )
        self._worker.finished.connect(lambda r: (
            AppState.set(f"{self.prefix}_followup_questions", r),
            self.questions_viewer.setMarkdown(r),
            self.btn_gen_questions.setEnabled(True)
        ))
        self._worker.error.connect(lambda e: (
            QMessageBox.critical(self, "오류", e),
            self.btn_gen_questions.setEnabled(True)
        ))
        self._worker.start()

    def _on_generate_report(self):
        """Generate report from collection tab."""
        file_context = self._ensure_file_context()
        if not file_context.strip():
            QMessageBox.warning(self, "경고", "먼저 자료를 로드하거나 프로젝트를 선택해주세요.")
            return

        settings = AppState.get("latest_settings", {})
        if not settings.get("api_key"):
            QMessageBox.warning(self, "경고", "API Key를 설정해주세요.")
            return

        template_key = self.report_template.currentData()
        gen_mode = "chained" if self.radio_chained.isChecked() else "single"

        # Build context
        full_context = file_context
        if self.check_inc_analysis.isChecked():
            summary = AppState.get(f"{self.prefix}_organized_summary", "")
            if summary:
                full_context += f"\n\n[AI 분석 결과 요약]\n{summary}"
        if self.check_inc_questions.isChecked():
            questions = AppState.get(f"{self.prefix}_followup_questions", "")
            if questions:
                full_context += f"\n\n[추가 질문/조사 항목]\n{questions}"

        inputs = {
            "template_option": template_key,
            "structure_text": core_logic.get_default_structure(template_key),
            "uploaded_files": [],
            "context_text": AppState.get(f"{self.prefix}_context_text", ""),
            "selected_saved_files": [],
            "generation_mode": gen_mode,
            "generate_btn": True,
            "use_diagram": settings.get("use_diagram", False),
        }

        AppState.set(f"{self.prefix}_inputs", inputs)
        self._start_generation_with(settings, inputs, full_context, gen_mode)

    def _on_upload_next(self):
        """Upload step next button."""
        settings = AppState.get("latest_settings", {})
        if not settings.get("api_key"):
            QMessageBox.warning(self, "경고", "API Key를 설정해주세요.")
            return

        file_paths = self.upload_files.get_file_paths()
        project = AppState.get("current_project", "")

        if not file_paths and not project:
            QMessageBox.warning(self, "경고", "파일을 업로드하거나 프로젝트를 선택해주세요.")
            return

        template_key = self.upload_template.currentData()
        gen_mode = "chained" if self.upload_radio_chained.isChecked() else "single"

        inputs = {
            "template_option": template_key,
            "structure_text": core_logic.get_default_structure(template_key),
            "uploaded_files": file_paths,
            "context_text": self.upload_context.toPlainText().strip(),
            "selected_saved_files": [],
            "generation_mode": gen_mode,
            "generate_btn": True,
            "use_diagram": settings.get("use_diagram", False),
        }
        AppState.set(f"{self.prefix}_inputs", inputs)
        AppState.set(f"{self.prefix}_active_mode", template_key)

        # Get selected documents
        selected_docs = AppState.get(f"{self.prefix}_selected_docs", None)

        # Parse files then go to next step
        self._worker = FileParseWorker(
            file_paths, settings["api_key"],
            docai_config=settings.get("docai_config"),
            template_option=template_key,
            project_name=project,
            selected_docs=selected_docs
        )
        self._worker.finished.connect(self._on_upload_files_parsed)
        self._worker.error.connect(lambda e: QMessageBox.critical(self, "오류", e))
        self._worker.start()

    def _on_upload_files_parsed(self, file_context, ocr_text, parse_results=None):
        """Handle file parsing completion for upload step."""
        AppState.set(f"{self.prefix}_file_context", file_context)

        # Show parse results if any files failed
        if parse_results:
            failed_files = [(name, r["error"]) for name, r in parse_results.items() if not r["success"]]
            if failed_files:
                success_count = sum(1 for r in parse_results.values() if r["success"])
                error_list = "\n".join([f"• {name}: {err}" for name, err in failed_files])
                msg = f"✅ 성공: {success_count}개\n❌ 실패: {len(failed_files)}개\n\n실패한 파일:\n{error_list}"
                QMessageBox.warning(self, "일부 파일 로드 실패", msg)

        # Move to next step (generate)
        self._go_to_step(2)

    def _on_checklist_next(self):
        """Save checklist data and go to generate step."""
        checklist_context = "\n\n[투자 매력도 체크리스트 평가 결과]\n"
        for name, _ in self.checklist_items:
            score = self.checklist_sliders[name].value()
            rationale = self.checklist_rationales[name].toPlainText().strip()
            checklist_context += f"- {name}: {score}점"
            if rationale:
                checklist_context += f" / {rationale}"
            checklist_context += "\n"

        current_fc = AppState.get(f"{self.prefix}_file_context", "")
        AppState.set(f"{self.prefix}_file_context", current_fc + checklist_context)
        self._go_to_step(3)

    def _start_generation(self):
        """Start AI generation."""
        settings = AppState.get("latest_settings", {})
        inputs = AppState.get(f"{self.prefix}_inputs", {})
        file_context = AppState.get(f"{self.prefix}_file_context", "")
        gen_mode = inputs.get("generation_mode", "single")
        self._start_generation_with(settings, inputs, file_context, gen_mode)

    def _start_generation_with(self, settings, inputs, file_context, gen_mode):
        if hasattr(self, 'gen_progress'):
            self.gen_progress.setVisible(True)
        if hasattr(self, 'report_progress'):
            self.report_progress.setVisible(True)
        if hasattr(self, 'gen_status'):
            self.gen_status.setText("🤖 보고서를 생성하는 중...", "info")
        if hasattr(self, 'btn_stop_gen'):
            self.btn_stop_gen.setVisible(True)

        self._worker = GenerateWorker(
            settings["api_key"], settings["model_name"],
            inputs, settings.get("thinking_level", "MINIMAL"),
            file_context, mode=gen_mode
        )
        self._worker.chunk_received.connect(self._on_gen_chunk)
        self._worker.status_update.connect(self._on_gen_status)
        self._worker.finished.connect(self._on_gen_finished)
        self._worker.error.connect(self._on_gen_error)
        self._worker.start()

    def _on_gen_status(self, status_msg):
        if hasattr(self, 'gen_status'):
            self.gen_status.setText(status_msg, "info")

    def _on_gen_chunk(self, partial_text):
        if hasattr(self, 'gen_viewer'):
            self.gen_viewer.setMarkdown(partial_text + "▌")
        if hasattr(self, 'report_viewer'):
            self.report_viewer.setMarkdown(partial_text + "▌")

    def _on_stop_worker(self):
        """Stop the current background worker."""
        if hasattr(self, '_worker') and self._worker and self._worker.isRunning():
            self._worker.stop()
            if hasattr(self, 'gen_status'):
                self.gen_status.setText("⏹ 중지됨", "warning")
            if hasattr(self, 'collect_status'):
                self.collect_status.setText("⏹ 중지됨", "warning")
        self._hide_stop_buttons()

    def _hide_stop_buttons(self):
        for btn_name in ('btn_stop_gen', 'btn_stop_collect', 'btn_stop_upload',
                         'btn_stop_analyze', 'btn_stop_qa'):
            if hasattr(self, btn_name):
                getattr(self, btn_name).setVisible(False)
        if hasattr(self, 'gen_progress'):
            self.gen_progress.setVisible(False)
        if hasattr(self, 'report_progress'):
            self.report_progress.setVisible(False)
        if hasattr(self, 'collect_progress'):
            self.collect_progress.setVisible(False)
        if hasattr(self, 'btn_collect_load'):
            self.btn_collect_load.setEnabled(True)

    def _on_gen_finished(self, full_text):
        self._hide_stop_buttons()
        # Strip preamble
        lines = full_text.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('#') and len(line.strip()) > 1:
                if i > 0:
                    full_text = '\n'.join(lines[i:])
                break

        AppState.set(f"{self.prefix}_generated_text", full_text)
        AppState.set(f"{self.prefix}_generation_complete", True)

        if hasattr(self, 'gen_viewer'):
            self.gen_viewer.setMarkdown(full_text)
            self.gen_progress.setVisible(False)
            self.gen_status.setText("✅ 작성 완료!", "success")
        if hasattr(self, 'report_viewer'):
            self.report_viewer.setMarkdown(full_text)
            self.report_progress.setVisible(False)
        if hasattr(self, 'refine_viewer'):
            self.refine_viewer.setMarkdown(full_text)
        if hasattr(self, 'output_viewer'):
            self.output_viewer.setMarkdown(full_text)

    def _on_gen_error(self, error_msg):
        self._hide_stop_buttons()
        if hasattr(self, 'gen_status'):
            self.gen_status.setText(f"오류: {error_msg}", "error")
        QMessageBox.critical(self, "생성 오류", error_msg)

    def _on_regenerate(self):
        AppState.set(f"{self.prefix}_generation_complete", False)
        self._start_generation()

    def _on_refine_message(self, message):
        settings = AppState.get("latest_settings", {})
        current_text = AppState.get(f"{self.prefix}_generated_text", "")
        chat_history = AppState.get(f"{self.prefix}_chat_history", [])

        chat_history.append({"role": "user", "content": message})
        AppState.set(f"{self.prefix}_chat_history", chat_history)

        self.refine_chat.set_enabled(False)

        self._worker = RefineWorker(
            settings["api_key"], settings["model_name"],
            current_text, chat_history, message
        )
        self._worker.finished.connect(self._on_refine_done)
        self._worker.error.connect(lambda e: (
            self.refine_chat.add_message("assistant", f"오류: {e}"),
            self.refine_chat.set_enabled(True)
        ))
        self._worker.start()

    def _on_refine_done(self, refined_text):
        AppState.set(f"{self.prefix}_generated_text", refined_text)
        self.refine_viewer.setMarkdown(refined_text)
        self.refine_chat.add_message("assistant", "수정 사항을 반영했습니다.")
        self.refine_chat.set_enabled(True)

        chat_history = AppState.get(f"{self.prefix}_chat_history", [])
        chat_history.append({"role": "assistant", "content": "수정 사항을 반영했습니다."})
        AppState.set(f"{self.prefix}_chat_history", chat_history)

    def _extract_title_from_markdown(self, text):
        """마크다운 텍스트에서 첫 번째 헤딩을 추출하여 파일명으로 사용."""
        import re
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                title = line.lstrip('#').strip()
                # 파일명에 사용할 수 없는 문자 제거
                title = re.sub(r'[\\/*?:"<>|]', '', title).strip()
                if title:
                    # 너무 길면 50자로 자르기
                    return title[:50].rstrip()
        # 헤딩이 없으면 첫 번째 비어있지 않은 줄 사용
        for line in text.split('\n'):
            line = line.strip()
            if line:
                title = re.sub(r'[\\/*?:"<>|]', '', line).strip()
                if title:
                    return title[:50].rstrip()
        return "report"

    def _save_file(self, fmt):
        text = AppState.get(f"{self.prefix}_generated_text", "")
        if not text:
            QMessageBox.warning(self, "경고", "저장할 내용이 없습니다.")
            return

        default_name = self._extract_title_from_markdown(text)

        if fmt == "docx":
            path, _ = QFileDialog.getSaveFileName(
                self, "Word 저장", f"{default_name}.docx",
                "Word Documents (*.docx)"
            )
            if path:
                data = utils.create_docx(text)
                with open(path, 'wb') as f:
                    f.write(data)
                QMessageBox.information(self, "저장 완료", f"파일이 저장되었습니다:\n{path}")
        elif fmt == "pptx":
            path, _ = QFileDialog.getSaveFileName(
                self, "PPT 저장", f"{default_name}.pptx",
                "PowerPoint (*.pptx)"
            )
            if path:
                import utils_ppt
                data = utils_ppt.create_ppt(text)
                with open(path, 'wb') as f:
                    f.write(data)
                QMessageBox.information(self, "저장 완료", f"파일이 저장되었습니다:\n{path}")

    def _copy_to_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QMimeData
        text = AppState.get(f"{self.prefix}_generated_text", "")
        # HTML도 함께 설정하여 Word 붙여넣기 시 서식 유지
        viewer = MarkdownViewer()
        html = viewer._md_to_html(text)
        styled_html = f"""<html><body style="font-family: -apple-system, Malgun Gothic, sans-serif; font-size: 13px; line-height: 1.6;">
        <style>
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #dee2e6; padding: 6px 10px; text-align: left; }}
            th {{ background-color: #f0f2f6; font-weight: bold; }}
            blockquote {{ border-left: 4px solid #0068c9; padding-left: 12px; color: #555; }}
        </style>
        {html}</body></html>"""
        mime = QMimeData()
        mime.setText(text)
        mime.setHtml(styled_html)
        QApplication.clipboard().setMimeData(mime)
        QMessageBox.information(self, "복사 완료", "클립보드에 복사되었습니다.\n(Word에 붙여넣기 시 서식이 유지됩니다)")

    def _reset_workflow(self):
        AppState.clear_prefix(f"{self.prefix}_")
        self._init_state()
        self._go_to_step(1)

    def _update_project_status(self):
        """Update project document status display."""
        if not hasattr(self, 'upload_project_status'):
            return

        project = AppState.get("current_project", "")
        if not project:
            self.upload_project_status.setText(
                "💡 사이드바에서 프로젝트를 선택하면 해당 문서가 자동으로 분석에 포함됩니다.",
                "info"
            )
            if hasattr(self, 'upload_doc_list'):
                self.upload_doc_list.clear()
            return

        doc_count = core_rag.get_indexed_count(project)
        if doc_count > 0:
            doc_names = core_rag.get_indexed_doc_names(project)
            self.upload_project_status.setText(
                f"✅ 프로젝트 '{project}': {doc_count}개 문서 로드됨. 아래에서 참고할 문서를 선택하세요.",
                "success"
            )
            # Auto-load documents into the list
            self._load_project_documents()
        else:
            self.upload_project_status.setText(
                f"⚠️ 프로젝트 '{project}'에 로드된 문서가 없습니다. "
                f"'프로젝트' 페이지에서 자료를 먼저 로드해주세요.",
                "warning"
            )
            if hasattr(self, 'upload_doc_list'):
                self.upload_doc_list.clear()

    def _on_collect_doc_selection_changed(self, selected_docs):
        """Handle document selection change in collection tab."""
        AppState.set(f"{self.prefix}_selected_docs", selected_docs)

    def _on_upload_doc_selection_changed(self, selected_docs):
        """Handle document selection change in upload step."""
        AppState.set(f"{self.prefix}_selected_docs", selected_docs)

    def _load_project_documents(self):
        """Load project documents into document list widgets."""
        project = AppState.get("current_project", "")
        if not project:
            if hasattr(self, 'collect_doc_list'):
                self.collect_doc_list.clear()
            if hasattr(self, 'upload_doc_list'):
                self.upload_doc_list.clear()
            return

        doc_names = core_rag.get_indexed_doc_names(project) or []

        # Update collection tab document list
        if hasattr(self, 'collect_doc_list'):
            self.collect_doc_list.set_documents(doc_names, check_all=True)

        # Update upload step document list
        if hasattr(self, 'upload_doc_list'):
            self.upload_doc_list.set_documents(doc_names, check_all=True)

    def _update_collection_project_status(self):
        """Update project document status display for collection tab."""
        if not hasattr(self, 'collect_project_status'):
            return

        project = AppState.get("current_project", "")
        if not project:
            self.collect_project_status.setText(
                "💡 사이드바에서 프로젝트를 선택하면 해당 문서가 자동으로 분석에 포함됩니다.",
                "info"
            )
            if hasattr(self, 'collect_doc_list'):
                self.collect_doc_list.clear()
            return

        doc_count = core_rag.get_indexed_count(project)
        if doc_count > 0:
            doc_names = core_rag.get_indexed_doc_names(project)
            self.collect_project_status.setText(
                f"✅ 프로젝트 '{project}': {doc_count}개 문서 로드됨. 아래에서 참고할 문서를 선택하세요.",
                "success"
            )
            # Auto-load documents into the list
            self._load_project_documents()
        else:
            self.collect_project_status.setText(
                f"⚠️ 프로젝트 '{project}'에 로드된 문서가 없습니다. "
                f"'프로젝트' 페이지에서 자료를 먼저 로드해주세요.",
                "warning"
            )
            if hasattr(self, 'collect_doc_list'):
                self.collect_doc_list.clear()

    # ========================================
    # IM Workflow (im_workflow page_type)
    # ========================================

    def _build_im_workflow_ui(self, parent_layout):
        """IM 전용 4-step workflow: 데이터 입력 → IM 생성 → 수정/보완 → PPT 생성."""
        self.step_indicator = StepIndicator(self.config.get("steps", {}))
        self.step_indicator.step_clicked.connect(self._go_to_step)
        parent_layout.addWidget(self.step_indicator)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #dee2e6;")
        parent_layout.addWidget(sep)

        from PyQt6.QtWidgets import QStackedWidget
        self.step_stack = QStackedWidget()

        # Step 1: IM-specific data input (deal terms + files)
        self.step_stack.addWidget(self._build_im_step_upload())
        # Step 2: Generate (reuse standard)
        self.step_stack.addWidget(self._build_step_generate())
        # Step 3: Refine (reuse standard)
        self.step_stack.addWidget(self._build_step_refine())
        # Step 4: IM-specific PPT output
        self.step_stack.addWidget(self._build_im_step_output())

        parent_layout.addWidget(self.step_stack)

    def _build_im_step_upload(self):
        """IM Step 1: 투자 유형 + Deal Terms + 파일 업로드."""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)

        # Left: Deal Terms + Files
        left = QVBoxLayout()

        # Investment type selector
        type_group = QGroupBox("📊 투자 유형")
        type_layout = QVBoxLayout(type_group)
        self.im_type_combo = QComboBox()
        self.im_type_combo.addItems(["Growth", "Buyout", "Pre-IPO"])
        type_layout.addWidget(self.im_type_combo)
        left.addWidget(type_group)

        # Deal Terms form
        deal_group = QGroupBox("📋 Deal Terms")
        deal_layout = QFormLayout(deal_group)

        self.im_project_name = QPlainTextEdit()
        self.im_project_name.setMaximumHeight(30)
        self.im_project_name.setPlaceholderText("예: Project Alpha")
        deal_layout.addRow("프로젝트명:", self.im_project_name)

        self.im_gp_name = QPlainTextEdit()
        self.im_gp_name.setMaximumHeight(30)
        self.im_gp_name.setPlaceholderText("예: ABC캐피탈")
        deal_layout.addRow("GP명:", self.im_gp_name)

        self.im_target = QPlainTextEdit()
        self.im_target.setMaximumHeight(30)
        self.im_target.setPlaceholderText("예: (주)테크코리아")
        deal_layout.addRow("대상회사:", self.im_target)

        self.im_amount = QPlainTextEdit()
        self.im_amount.setMaximumHeight(30)
        self.im_amount.setPlaceholderText("예: 100억원")
        deal_layout.addRow("투자규모:", self.im_amount)

        self.im_valuation = QPlainTextEdit()
        self.im_valuation.setMaximumHeight(30)
        self.im_valuation.setPlaceholderText("예: Pre 500억원")
        deal_layout.addRow("Valuation:", self.im_valuation)

        self.im_vehicle = QPlainTextEdit()
        self.im_vehicle.setMaximumHeight(30)
        self.im_vehicle.setPlaceholderText("예: 신주인수, CB, 구주매입")
        deal_layout.addRow("투자형태:", self.im_vehicle)

        self.im_equity = QPlainTextEdit()
        self.im_equity.setMaximumHeight(30)
        self.im_equity.setPlaceholderText("예: 20%")
        deal_layout.addRow("지분율:", self.im_equity)

        left.addWidget(deal_group)

        # Project document status
        self.upload_project_status = StatusBox("", "info")
        left.addWidget(self.upload_project_status)
        self._update_project_status()

        # Document selection widget
        self.upload_doc_list = DocumentListWidget()
        self.upload_doc_list.selection_changed.connect(self._on_upload_doc_selection_changed)
        left.addWidget(self.upload_doc_list)

        main_layout.addLayout(left, 3)

        # Right: File upload + Template + Next
        right = QVBoxLayout()

        self.upload_files = FilePicker(
            "📁 추가 파일 업로드",
            file_filter="Documents (*.pdf *.docx *.pptx *.xlsx *.txt);;All (*)"
        )
        right.addWidget(self.upload_files)

        right.addWidget(QLabel("💬 추가 맥락/지시사항"))
        self.upload_context = QTextEdit()
        self.upload_context.setPlaceholderText("예: 특별히 강조할 부분, 참고할 사항 등")
        self.upload_context.setMaximumHeight(100)
        self.upload_context.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.upload_context.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right.addWidget(self.upload_context)

        right.addWidget(QLabel("📝 템플릿 선택"))
        self.upload_template = QComboBox()
        for k, v in self.config.get("template_options", {}).items():
            self.upload_template.addItem(v, k)
        right.addWidget(self.upload_template)

        right.addStretch()

        btn_next = QPushButton("다음: IM 생성 >>>")
        btn_next.setProperty("cssClass", "primary")
        btn_next.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #004085; }
        """)
        btn_next.clicked.connect(self._on_im_upload_next)
        right.addWidget(btn_next)

        main_layout.addLayout(right, 2)
        return widget

    def _build_im_step_output(self):
        """IM Step 4: IM PPT (16:9) + Word + 표준 PPT 다운로드."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("📊 IM 최종 결과 및 PPT 생성"))

        self.output_viewer = MarkdownViewer()
        self.output_viewer.setMinimumHeight(500)
        layout.addWidget(self.output_viewer)

        btn_row = QHBoxLayout()

        btn_im_ppt = QPushButton("📊 IM PPT 다운로드 (16:9)")
        btn_im_ppt.setStyleSheet("""
            QPushButton { background: #198754; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background: #157347; }
        """)
        btn_im_ppt.clicked.connect(self._on_im_save_ppt)
        btn_row.addWidget(btn_im_ppt)

        btn_word = QPushButton("📄 Word 다운로드")
        btn_word.clicked.connect(lambda: self._save_file("docx"))
        btn_row.addWidget(btn_word)

        btn_ppt = QPushButton("📊 표준 PPT (4:3)")
        btn_ppt.clicked.connect(lambda: self._save_file("pptx"))
        btn_row.addWidget(btn_ppt)

        btn_copy = QPushButton("📋 클립보드 복사")
        btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_row.addWidget(btn_copy)
        layout.addLayout(btn_row)

        nav = QHBoxLayout()
        btn_prev = QPushButton("<<< 수정하러 돌아가기")
        btn_prev.clicked.connect(lambda: self._go_to_step(3))
        nav.addWidget(btn_prev)
        nav.addStretch()

        btn_restart = QPushButton("🔄 처음부터 다시")
        btn_restart.clicked.connect(self._reset_workflow)
        nav.addWidget(btn_restart)
        layout.addLayout(nav)

        return widget

    def _on_im_upload_next(self):
        """IM Step 1 → Step 2: Deal Terms 수집 후 파일 파싱 → 생성."""
        settings = AppState.get("latest_settings", {})
        if not settings.get("api_key"):
            QMessageBox.warning(self, "경고", "설정에서 API Key를 먼저 입력해주세요.")
            return

        file_paths = self.upload_files.get_file_paths()
        project = AppState.get("current_project", "")

        if not file_paths and not project:
            QMessageBox.warning(self, "경고", "파일을 업로드하거나 프로젝트를 선택해주세요.")
            return

        template_key = self.upload_template.currentData()
        investment_type = self.im_type_combo.currentText()

        # Collect deal terms
        deal_terms_text = ""
        deal_fields = [
            ("프로젝트명", self.im_project_name.toPlainText().strip()),
            ("GP명", self.im_gp_name.toPlainText().strip()),
            ("대상회사", self.im_target.toPlainText().strip()),
            ("투자규모", self.im_amount.toPlainText().strip()),
            ("Valuation", self.im_valuation.toPlainText().strip()),
            ("투자형태", self.im_vehicle.toPlainText().strip()),
            ("지분율", self.im_equity.toPlainText().strip()),
        ]
        non_empty = [(k, v) for k, v in deal_fields if v]
        if non_empty:
            deal_terms_text = "\n[Deal Terms]\n" + "\n".join(
                f"- {k}: {v}" for k, v in non_empty
            )

        context_text = self.upload_context.toPlainText().strip()
        if deal_terms_text:
            context_text = deal_terms_text + "\n\n" + context_text

        # IM uses chained mode for im_full
        gen_mode = "im_chained" if template_key == "im_full" else "single"

        inputs = {
            "template_option": template_key,
            "structure_text": core_logic.get_default_structure(template_key),
            "uploaded_files": file_paths,
            "context_text": context_text,
            "selected_saved_files": [],
            "generation_mode": gen_mode,
            "generate_btn": True,
            "use_diagram": settings.get("use_diagram", False),
            "investment_type": investment_type,
            "project_name": self.im_project_name.toPlainText().strip(),
            "gp_name": self.im_gp_name.toPlainText().strip(),
        }
        AppState.set(f"{self.prefix}_inputs", inputs)
        AppState.set(f"{self.prefix}_active_mode", template_key)

        # Get selected documents
        selected_docs = AppState.get(f"{self.prefix}_selected_docs", None)

        # Parse files then go to generate step
        self._worker = FileParseWorker(
            file_paths, settings["api_key"],
            docai_config=settings.get("docai_config"),
            template_option=template_key,
            project_name=project,
            selected_docs=selected_docs
        )
        self._worker.finished.connect(self._on_upload_files_parsed)
        self._worker.error.connect(lambda e: QMessageBox.critical(self, "오류", e))
        self._worker.start()

    def _on_im_save_ppt(self):
        """Save IM PPT (16:9 format) using core_im_ppt."""
        text = AppState.get(f"{self.prefix}_generated_text", "")
        if not text:
            QMessageBox.warning(self, "경고", "저장할 내용이 없습니다.")
            return

        inputs = AppState.get(f"{self.prefix}_inputs", {})
        project_name = inputs.get("project_name", "")
        gp_name = inputs.get("gp_name", "")

        import datetime
        date_str = datetime.date.today().strftime("%Y년 %m월")

        default_name = self._extract_title_from_markdown(text)
        path, _ = QFileDialog.getSaveFileName(
            self, "IM PPT 저장 (16:9)", f"{default_name}_IM.pptx",
            "PowerPoint (*.pptx)"
        )
        if path:
            try:
                data = core_im_ppt.create_im_ppt(
                    text, project_name=project_name,
                    gp_name=gp_name, date_str=date_str
                )
                with open(path, 'wb') as f:
                    f.write(data)
                QMessageBox.information(self, "저장 완료", f"IM PPT가 저장되었습니다:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "PPT 생성 오류", f"PPT 생성 중 오류 발생:\n{e}")

    def refresh(self):
        """Refresh page state."""
        self._update_project_status()
        self._update_collection_project_status()
        text = AppState.get(f"{self.prefix}_generated_text", "")
        if text:
            if hasattr(self, 'report_viewer'):
                self.report_viewer.setMarkdown(text)
            if hasattr(self, 'gen_viewer'):
                self.gen_viewer.setMarkdown(text)
            if hasattr(self, 'output_viewer'):
                self.output_viewer.setMarkdown(text)

        summary = AppState.get(f"{self.prefix}_organized_summary", "")
        if summary and hasattr(self, 'analyze_viewer'):
            self.analyze_viewer.setMarkdown(summary)

        questions = AppState.get(f"{self.prefix}_followup_questions", "")
        if questions and hasattr(self, 'questions_viewer'):
            self.questions_viewer.setMarkdown(questions)

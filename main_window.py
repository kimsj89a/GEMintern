"""
Main window with sidebar navigation and tabbed content pages.
Supports multiple open tabs and zoom controls.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QScrollArea,
    QFrame, QComboBox, QSplitter, QMessageBox, QApplication,
    QTabWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
import os
from app_state import AppState
from workers import SyncWorker

# Import pages
from pages.home_page import HomePage
from pages.settings_page import SettingsPage
from pages.project_page import ProjectPage
from pages.workflow_page import WorkflowPage
from pages.audio_page import AudioPage
from pages.crawler_page import CrawlerPage
from pages.ocr_page import OcrPage
from pages.markdown_page import MarkdownPage
from pages.doctemplate_page import DocTemplatePage
from pages.text_organizer_page import TextOrganizerPage
from pages.ppt_tools_page import PptToolsPage
from pages.lp_qa_page import LpQaPage
from pages.qa_session_page import QaSessionPage


# Navigation structure
NAV_SECTIONS = {
    "Main": [
        ("🏠 홈", "home"),
        ("📂 프로젝트", "project"),
    ],
    "Phase Workflow": [
        ("📥 사전 정보 수집", "phase1"),
        ("📝 투심보고서 작성", "phase2"),
    ],
    "Independent Tools": [
        ("📑 IM 작성", "im"),
        ("📢 발표자료 (PPT)", "ppt_tools"),
        ("🙋‍♂️ LP Q&A 대응", "lp_qa"),
        ("💬 자료기반 Q&A", "qa_session"),
    ],
    "Utilities": [
        ("🎤 오디오 전사", "audio"),
        ("🌐 웹 크롤러", "crawler"),
        ("👁️ 문서 OCR", "ocr"),
        ("📝 MD to Word", "markdown"),
        ("📋 문서양식", "doctemplate"),
        ("✏️ 문장 정리기", "text_organizer"),
    ],
}

# page_id -> display label
PAGE_LABELS = {}
for _section, _items in NAV_SECTIONS.items():
    for _label, _pid in _items:
        PAGE_LABELS[_pid] = _label
PAGE_LABELS["settings"] = "⚙️ 설정"

# page_id -> factory (class or lambda)
PAGE_FACTORIES = {
    "home": HomePage,
    "settings": SettingsPage,
    "project": ProjectPage,
    "phase1": lambda: WorkflowPage("phase1"),
    "phase2": lambda: WorkflowPage("phase2"),
    "im": lambda: WorkflowPage("im"),
    "ppt_tools": PptToolsPage,
    "lp_qa": LpQaPage,
    "qa_session": QaSessionPage,
    "audio": AudioPage,
    "crawler": CrawlerPage,
    "ocr": OcrPage,
    "markdown": MarkdownPage,
    "doctemplate": DocTemplatePage,
    "text_organizer": TextOrganizerPage,
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("💎 GEM Intern v7.0")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        self._zoom_level = 100
        self._base_font_size = 10

        # Initialize state
        AppState.setdefault("app_started", False)
        AppState.setdefault("current_project", "")
        AppState.setdefault("selected_page", "home")

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Splitter for sidebar + content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # --- Sidebar ---
        self.sidebar = self._build_sidebar()
        splitter.addWidget(self.sidebar)

        # --- Content area ---
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Project banner
        self.project_banner = QFrame()
        self.project_banner.setProperty("cssClass", "project-banner")
        self.project_banner.setVisible(False)
        banner_layout = QHBoxLayout(self.project_banner)
        banner_layout.setContentsMargins(16, 10, 16, 10)
        self.banner_label = QLabel()
        self.banner_label.setStyleSheet("font-size: 14px; font-weight: 500; border: none; color: #2383E2;")
        self.banner_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        banner_layout.addWidget(self.banner_label)
        content_layout.addWidget(self.project_banner)

        # Tab widget for pages
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.tab_widget.setStyleSheet("""
            QTabBar::tab { max-width: 200px; }
        """)
        content_layout.addWidget(self.tab_widget)
        splitter.addWidget(content_wrapper)

        splitter.setSizes([260, 1140])

        # Track open tabs
        self._open_tabs = {}   # page_id -> scroll_widget
        self._pages = {}       # page_id -> page_widget

        # Show initial page
        if not AppState.get("app_started"):
            self._navigate_to("settings")
        else:
            self._navigate_to("home")

        # Listen for state changes
        AppState().state_changed.connect(self._on_state_changed)

    def _build_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(0)

        # Title
        title = QLabel("💎 GEM Intern v7.0")
        title.setStyleSheet("font-size: 18px; font-weight: 700; padding: 16px 20px; color: #37352F;")
        title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(title)

        # Project quick switcher
        self.project_combo = QComboBox()
        self.project_combo.setStyleSheet("margin: 4px 16px;")
        self.project_combo.setToolTip("프로젝트를 선택하면 해당 프로젝트의 문서가 자동으로 분석에 포함됩니다.")
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        layout.addWidget(self.project_combo)
        self._refresh_projects()

        layout.addSpacing(12)

        # Navigation buttons
        self._nav_buttons = {}
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        for section_name, items in NAV_SECTIONS.items():
            header = QLabel(section_name)
            header.setObjectName("sectionHeader")
            header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            nav_layout.addWidget(header)

            for label, page_id in items:
                btn = QPushButton(label)
                btn.setProperty("page_id", page_id)
                btn.clicked.connect(lambda checked, pid=page_id: self._navigate_to(pid))
                nav_layout.addWidget(btn)
                self._nav_buttons[page_id] = btn

        nav_layout.addStretch()
        scroll.setWidget(nav_widget)
        layout.addWidget(scroll)

        # --- Bottom section ---
        layout.addSpacing(8)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #E9E9E7; max-height: 1px; margin: 0 12px;")
        layout.addWidget(sep)
        layout.addSpacing(6)

        bottom = QVBoxLayout()
        bottom.setContentsMargins(8, 0, 8, 0)
        bottom.setSpacing(4)

        # Zoom controls
        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(4)

        btn_zoom_out = QPushButton("-")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.setToolTip("축소")
        btn_zoom_out.setStyleSheet(self._zoom_btn_css())
        btn_zoom_out.clicked.connect(self._zoom_out)
        zoom_row.addWidget(btn_zoom_out)

        self._zoom_label = QPushButton("100%")
        self._zoom_label.setFixedHeight(28)
        self._zoom_label.setToolTip("배율 초기화")
        self._zoom_label.setStyleSheet("""
            QPushButton {
                color: #787774; background: transparent; border: 1px solid #E9E9E7;
                border-radius: 6px; font-size: 12px; padding: 0 6px;
            }
            QPushButton:hover { background: #F7F6F3; }
        """)
        self._zoom_label.clicked.connect(self._zoom_reset)
        zoom_row.addWidget(self._zoom_label)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.setToolTip("확대")
        btn_zoom_in.setStyleSheet(self._zoom_btn_css())
        btn_zoom_in.clicked.connect(self._zoom_in)
        zoom_row.addWidget(btn_zoom_in)

        bottom.addLayout(zoom_row)

        # Sync status button
        self.sync_btn = QPushButton("🔴 클라우드 미연결")
        self.sync_btn.setToolTip("클릭하여 수동 동기화 실행")
        self.sync_btn.setStyleSheet("""
            QPushButton {
                color: #787774; background: transparent; border: 1px solid #E9E9E7;
                border-radius: 6px; padding: 6px 12px; margin: 2px 0px; font-size: 12px;
            }
            QPushButton:hover { background: #E8F3FC; border-color: #2383E2; }
        """)
        self.sync_btn.clicked.connect(self._on_sync_clicked)
        bottom.addWidget(self.sync_btn)

        # Settings + Restart
        btn_settings = QPushButton("⚙️ 설정 수정")
        btn_settings.setProperty("page_id", "settings_bottom")
        btn_settings.clicked.connect(lambda: self._navigate_to("settings"))
        bottom.addWidget(btn_settings)
        self._nav_buttons["settings_bottom"] = btn_settings

        btn_restart = QPushButton("🔄 앱 재시작")
        btn_restart.setToolTip("코드 변경 후 앱을 재시작합니다")
        btn_restart.setStyleSheet("""
            QPushButton {
                color: #787774; background: transparent; border: 1px solid #E9E9E7;
                border-radius: 6px; padding: 6px 12px; margin: 2px 0px; font-size: 13px;
            }
            QPushButton:hover { background: #FFF8E1; border-color: #FFA726; color: #E65100; }
        """)
        btn_restart.clicked.connect(self._restart_app)
        bottom.addWidget(btn_restart)

        layout.addLayout(bottom)
        return sidebar

    def _zoom_btn_css(self):
        return """
            QPushButton {
                color: #787774; background: #F7F6F3; border: 1px solid #E9E9E7;
                border-radius: 6px; font-size: 16px; font-weight: bold;
            }
            QPushButton:hover { background: #E8F3FC; color: #2383E2; border-color: #2383E2; }
        """

    # ========================================
    # Zoom
    # ========================================

    def _zoom_in(self):
        self._zoom_level = min(self._zoom_level + 10, 150)
        self._apply_zoom()

    def _zoom_out(self):
        self._zoom_level = max(self._zoom_level - 10, 70)
        self._apply_zoom()

    def _zoom_reset(self):
        self._zoom_level = 100
        self._apply_zoom()

    def _apply_zoom(self):
        import re
        from styles import MAIN_STYLESHEET

        factor = self._zoom_level / 100.0

        # Scale all font-size values in the global stylesheet
        def scale_px(match):
            original = int(match.group(1))
            return f"font-size: {max(8, int(original * factor))}px"

        scaled_css = re.sub(r'font-size:\s*(\d+)px', scale_px, MAIN_STYLESHEET)

        app = QApplication.instance()
        app.setStyleSheet(scaled_css)

        # Also scale the default app font for widgets without explicit CSS
        font = app.font()
        font.setPointSize(max(7, int(self._base_font_size * factor)))
        app.setFont(font)

        self._zoom_label.setText(f"{self._zoom_level}%")

    # ========================================
    # Tab management
    # ========================================

    def _navigate_to(self, page_id):
        """Open page as a tab, or switch to it if already open."""
        if page_id not in PAGE_FACTORIES:
            return

        # If tab already open, switch to it
        if page_id in self._open_tabs:
            scroll = self._open_tabs[page_id]
            tab_idx = self.tab_widget.indexOf(scroll)
            if tab_idx >= 0:
                self.tab_widget.setCurrentIndex(tab_idx)
                page = self._pages.get(page_id)
                if page and hasattr(page, 'refresh'):
                    page.refresh()
                return

        # Create new page
        page = self._create_page(page_id)
        if page is None:
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        scroll.setStyleSheet("border: none;")

        label = PAGE_LABELS.get(page_id, page_id)
        tab_idx = self.tab_widget.addTab(scroll, label)
        self.tab_widget.setCurrentIndex(tab_idx)

        self._open_tabs[page_id] = scroll
        self._pages[page_id] = page

        # Connect signals
        if hasattr(page, 'navigate_to'):
            page.navigate_to.connect(self._navigate_to)
        if hasattr(page, 'settings_applied'):
            page.settings_applied.connect(self._on_settings_applied)

        if hasattr(page, 'refresh'):
            page.refresh()

        AppState.set("selected_page", page_id)
        self._update_sidebar_active(page_id)
        self._update_banner(page_id)

    def _create_page(self, page_id):
        factory = PAGE_FACTORIES.get(page_id)
        if factory is None:
            return None
        if callable(factory) and not isinstance(factory, type):
            return factory()
        return factory()

    def _close_tab(self, index):
        widget = self.tab_widget.widget(index)
        # Find page_id for this tab
        pid_to_remove = None
        for pid, scroll in self._open_tabs.items():
            if scroll is widget:
                pid_to_remove = pid
                break

        # Don't allow closing the last tab
        if self.tab_widget.count() <= 1:
            return

        self.tab_widget.removeTab(index)
        if pid_to_remove:
            self._open_tabs.pop(pid_to_remove, None)
            self._pages.pop(pid_to_remove, None)

    def _on_tab_changed(self, index):
        """Update sidebar highlight when tab changes."""
        if index < 0:
            return
        widget = self.tab_widget.widget(index)
        for pid, scroll in self._open_tabs.items():
            if scroll is widget:
                AppState.set("selected_page", pid)
                self._update_sidebar_active(pid)
                self._update_banner(pid)
                break

    def _update_sidebar_active(self, page_id):
        for pid, btn in self._nav_buttons.items():
            is_active = (pid == page_id) or (pid == "settings_bottom" and page_id == "settings")
            btn.setProperty("active", "true" if is_active else "false")
            btn.setStyle(btn.style())

    def _update_banner(self, page_id):
        project = AppState.get("current_project", "")
        if project and page_id not in ("home", "settings"):
            try:
                import core_rag
                doc_names = core_rag.get_indexed_doc_names(project) or []
                self.banner_label.setText(f"📂 {project} | {len(doc_names)}건 문서")
                self.project_banner.setVisible(True)
            except Exception:
                self.project_banner.setVisible(False)
        else:
            self.project_banner.setVisible(False)

    # ========================================
    # Other handlers
    # ========================================

    def _restart_app(self):
        import sys, os, subprocess
        python = sys.executable
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        subprocess.Popen([python, script])
        QApplication.instance().quit()

    def _on_settings_applied(self):
        AppState.set("app_started", True)
        self._init_cloud_sync()
        self._navigate_to("home")

    def _on_project_changed(self, text):
        if text and text != "-- 선택하세요 --":
            AppState.set("current_project", text)
        else:
            AppState.set("current_project", "")

    def _refresh_projects(self):
        try:
            import core_rag
            projects = [p["name"] for p in core_rag.list_projects()]
        except Exception:
            projects = []

        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem("-- 선택하세요 --")
        self.project_combo.addItems(projects)

        current = AppState.get("current_project", "")
        if current in projects:
            self.project_combo.setCurrentText(current)
        self.project_combo.blockSignals(False)

    def _on_state_changed(self, key, value):
        if key == "current_project":
            self._refresh_projects()
            page_id = AppState.get("selected_page", "home")
            self._update_banner(page_id)
            # Refresh all open workflow pages
            for pid, page in self._pages.items():
                if hasattr(page, 'refresh'):
                    page.refresh()
        elif key == "cloud_sync":
            self._init_cloud_sync()

    # ========================================
    # Cloud Sync
    # ========================================

    def _init_cloud_sync(self):
        """Initialize CloudSyncManager from current settings and register with core_rag."""
        cs = AppState.get("cloud_sync", {})
        if not cs:
            return

        auto_sync = cs.get("auto_sync", True)
        onedrive_client = None
        gsheets_client = None

        # OneDrive client (token is acquired separately via OAuth flow)
        if cs.get("onedrive_enabled") and cs.get("onedrive_client_id"):
            try:
                from utils_onedrive import OneDriveClient
                onedrive_client = OneDriveClient(cs["onedrive_client_id"])
            except Exception as e:
                print(f"OneDrive init error: {e}")

        # Google Sheets client
        if cs.get("gsheets_enabled") and cs.get("gsheets_credentials_path"):
            cred_path = cs["gsheets_credentials_path"]
            if os.path.exists(cred_path):
                try:
                    from utils_gsheets import GSheetsClient
                    gsheets_client = GSheetsClient(cred_path)
                    gsheets_client.ensure_workbook(
                        spreadsheet_id=cs.get("gsheets_spreadsheet_id") or None
                    )
                    # Store the resolved spreadsheet ID back
                    if gsheets_client.spreadsheet_id:
                        cs["gsheets_spreadsheet_id"] = gsheets_client.spreadsheet_id
                except Exception as e:
                    print(f"GSheets init error: {e}")

        # Google Drive client
        gdrive_client = None
        if cs.get("gdrive_enabled") and cs.get("gdrive_client_id"):
            try:
                from utils_gdrive import GoogleDriveClient
                gdrive_client = GoogleDriveClient(
                    cs["gdrive_client_id"],
                    cs.get("gdrive_client_secret", ""),
                )
                gdrive_client.load_saved_token()
            except Exception as e:
                print(f"Google Drive init error: {e}")

        if onedrive_client or gsheets_client or gdrive_client:
            from cloud_sync import CloudSyncManager
            import core_rag
            manager = CloudSyncManager(
                onedrive_client=onedrive_client,
                gsheets_client=gsheets_client,
                gdrive_client=gdrive_client,
            )
            if auto_sync:
                core_rag.set_sync_manager(manager)
            self._sync_manager = manager
            self._update_sync_status("connected")
        else:
            self._sync_manager = None
            import core_rag
            core_rag.set_sync_manager(None)
            self._update_sync_status("disconnected")

    def _update_sync_status(self, status):
        """Update sync button appearance."""
        if status == "connected" and hasattr(self, '_sync_manager') and self._sync_manager:
            services = []
            mgr = self._sync_manager
            if mgr.onedrive_enabled:
                services.append("OneDrive")
            if mgr.gdrive_enabled:
                services.append("GDrive")
            if mgr.gsheets_enabled:
                services.append("GSheets")
            svc_text = "+".join(services) if services else "클라우드"
            self.sync_btn.setText(f"🟢 {svc_text} 연결됨")
        elif status == "syncing":
            self.sync_btn.setText("🟡 동기화 중...")
        else:
            self.sync_btn.setText("🔴 클라우드 미연결")

    def _on_sync_clicked(self):
        """Manual sync: sync current project if available."""
        if not hasattr(self, '_sync_manager') or not self._sync_manager:
            QMessageBox.information(self, "동기화", "클라우드 연결이 설정되지 않았습니다.\n설정 페이지에서 OneDrive 또는 Google Sheets를 활성화하세요.")
            return

        project = AppState.get("current_project", "")
        if not project:
            # Just sync registry
            self._run_sync("sync_registry")
        else:
            self._run_sync("full_sync", project)

    def _run_sync(self, action, project_name=None):
        """Run sync in background thread."""
        self._update_sync_status("syncing")
        self._sync_worker = SyncWorker(
            self._sync_manager, action=action, project_name=project_name
        )
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.error.connect(self._on_sync_error)
        self._sync_worker.start()

    def _on_sync_finished(self, result):
        self._update_sync_status("connected")

    def _on_sync_error(self, error_msg):
        self._update_sync_status("connected")
        print(f"Sync error: {error_msg}")

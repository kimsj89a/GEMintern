"""Settings page - replaces ui_input.render_settings() and initial setup screen."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QCheckBox, QPushButton, QGroupBox, QFormLayout,
    QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from app_state import AppState
from widgets.status_box import StatusBox
import json, os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "settings.json")


class SettingsPage(QWidget):
    navigate_to = pyqtSignal(str)
    settings_applied = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_saved()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)

        # Title
        title_row = QHBoxLayout()
        title = QLabel("💎 GEM Intern")
        title.setProperty("cssClass", "title")
        title_row.addWidget(title)

        badge = QLabel("v7.0")
        badge.setProperty("cssClass", "badge")
        title_row.addWidget(badge)
        title_row.addStretch()
        layout.addLayout(title_row)

        subtitle = QLabel("AI-Powered Investment Analysis Assistant")
        subtitle.setProperty("cssClass", "subtitle")
        layout.addWidget(subtitle)

        # Settings header
        header = QLabel("⚙️ 환경 설정 (Settings)")
        header.setProperty("cssClass", "heading1")
        layout.addWidget(header)

        info = StatusBox("업무를 시작하기 전에 필요한 설정을 완료해주세요.", "info")
        layout.addWidget(info)

        # API Settings group
        api_group = QGroupBox("🔑 API 설정")
        api_form = QFormLayout(api_group)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Google Gemini API Key를 입력하세요")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("API Key:", self.api_key_input)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gemini-3-pro-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
        ])
        api_form.addRow("모델:", self.model_combo)

        self.thinking_combo = QComboBox()
        self.thinking_combo.addItems(["MINIMAL", "LOW", "MEDIUM", "HIGH"])
        api_form.addRow("Thinking Level:", self.thinking_combo)

        layout.addWidget(api_group)

        # Generation options group
        gen_group = QGroupBox("📝 생성 옵션")
        gen_form = QFormLayout(gen_group)

        self.use_diagram_check = QCheckBox("다이어그램/차트 생성 포함")
        gen_form.addRow(self.use_diagram_check)

        layout.addWidget(gen_group)

        # OCR / Document AI group
        ocr_group = QGroupBox("👁️ OCR / Document AI 설정 (선택)")
        ocr_form = QFormLayout(ocr_group)

        self.docai_check = QCheckBox("Google Document AI 사용")
        self.docai_check.toggled.connect(self._toggle_docai)
        ocr_form.addRow(self.docai_check)

        self.docai_project = QLineEdit()
        self.docai_project.setPlaceholderText("GCP Project ID")
        self.docai_project.setEnabled(False)
        ocr_form.addRow("GCP Project:", self.docai_project)

        self.docai_location = QLineEdit()
        self.docai_location.setText("us")
        self.docai_location.setEnabled(False)
        ocr_form.addRow("Location:", self.docai_location)

        self.docai_processor = QLineEdit()
        self.docai_processor.setPlaceholderText("Processor ID")
        self.docai_processor.setEnabled(False)
        ocr_form.addRow("Processor ID:", self.docai_processor)

        layout.addWidget(ocr_group)

        # Save checkbox
        self.save_settings_check = QCheckBox("설정을 로컬에 저장 (다음 실행 시 자동 로드)")
        self.save_settings_check.setChecked(True)
        layout.addWidget(self.save_settings_check)

        layout.addSpacing(16)

        # Start button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.start_btn = QPushButton("✅ 설정 적용 및 업무 시작")
        self.start_btn.setProperty("cssClass", "primary")
        self.start_btn.setMinimumWidth(300)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._apply_settings)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _toggle_docai(self, checked):
        self.docai_project.setEnabled(checked)
        self.docai_location.setEnabled(checked)
        self.docai_processor.setEnabled(checked)

    def _apply_settings(self):
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "경고", "API Key를 입력해주세요.")
            return

        settings = {
            "api_key": api_key,
            "model_name": self.model_combo.currentText(),
            "thinking_level": self.thinking_combo.currentText(),
            "use_diagram": self.use_diagram_check.isChecked(),
            "docai_config": {},
        }

        if self.docai_check.isChecked():
            settings["docai_config"] = {
                "project_id": self.docai_project.text().strip(),
                "location": self.docai_location.text().strip(),
                "processor_id": self.docai_processor.text().strip(),
            }

        AppState.set("latest_settings", settings)
        AppState.set("api_key", api_key)
        AppState.set("model_name", settings["model_name"])
        AppState.set("thinking_level", settings["thinking_level"])
        AppState.set("use_diagram", settings["use_diagram"])
        AppState.set("docai_config", settings["docai_config"])

        if self.save_settings_check.isChecked():
            self._save_to_file(settings)

        self.settings_applied.emit()

    def _save_to_file(self, settings):
        try:
            save_data = {k: v for k, v in settings.items() if k != "api_key"}
            save_data["api_key_hint"] = settings["api_key"][:8] + "..." if len(settings["api_key"]) > 8 else ""
            save_data["api_key"] = settings["api_key"]
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Settings save error: {e}")

    def _load_saved(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("api_key"):
                    self.api_key_input.setText(data["api_key"])
                if data.get("model_name"):
                    idx = self.model_combo.findText(data["model_name"])
                    if idx >= 0:
                        self.model_combo.setCurrentIndex(idx)
                if data.get("thinking_level"):
                    idx = self.thinking_combo.findText(data["thinking_level"])
                    if idx >= 0:
                        self.thinking_combo.setCurrentIndex(idx)
                if data.get("use_diagram"):
                    self.use_diagram_check.setChecked(data["use_diagram"])
                if data.get("docai_config") and data["docai_config"].get("project_id"):
                    self.docai_check.setChecked(True)
                    self.docai_project.setText(data["docai_config"].get("project_id", ""))
                    self.docai_location.setText(data["docai_config"].get("location", "us"))
                    self.docai_processor.setText(data["docai_config"].get("processor_id", ""))
        except Exception as e:
            print(f"Settings load error: {e}")

    def get_settings(self):
        return AppState.get("latest_settings", {})

    def refresh(self):
        pass

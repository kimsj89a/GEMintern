# 기존 문서 업데이트 기능 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 기존 문서를 업로드하고, 추가 자료 + 프롬프트를 반영하여 원본 파일 포맷을 유지한 채 업데이트된 문서를 출력하는 기능

**Architecture:** core_doc_updater.py에서 원본 문서의 paragraph/shape를 인덱싱하고, AI가 JSON structured output으로 수정 지시를 반환하면, python-docx/python-pptx로 원본 파일을 직접 수정. UI는 pages/doc_updater_page.py에 PyQt6 QWidget으로 구현.

**Tech Stack:** PyQt6, Google Gemini API (genai), python-docx, python-pptx, PyMuPDF

---

### Task 1: prompts.py에 문서 업데이트 프롬프트 추가

**Files:**
- Modify: `prompts.py:1978` (파일 끝, `LOGIC_PROMPTS` dict 닫히기 전)

**Step 1: prompts.py 끝에 DOC_UPDATER_PROMPTS dict 추가**

`prompts.py` 파일 맨 끝(1978행 `}` 다음)에 새 dict를 추가:

```python
# --- Document Updater Prompts ---

DOC_UPDATER_PROMPTS = {
    'system': """당신은 문서 업데이트 전문가입니다.
기존 문서의 구조와 톤을 유지하면서, 추가 자료와 지시사항을 반영하여 문서를 업데이트합니다.

[핵심 규칙]
1. 반드시 JSON 형식으로만 응답하세요. 마크다운 코드블록이나 설명 텍스트를 포함하지 마세요.
2. 원본 문서의 구조, 문체, 톤앤매너를 최대한 유지하세요.
3. 수치, 고유명사, 날짜 등 팩트 데이터는 추가 자료에 근거해서만 변경하세요.
4. 추가 자료에 없는 내용을 임의로 만들어내지 마세요.
5. 한국어로 작성하세요.""",

    'full_update': """[작업 유형: 전체 재생성]
기존 문서의 모든 문단을 추가 자료와 지시사항을 반영하여 업데이트해주세요.

[원본 문서 구조]
{document_map}

[추가 자료]
{supplementary}

[사용자 지시사항]
{instruction}

[응답 형식 - 반드시 이 JSON 스키마를 따르세요]
{{
  "updated_paragraphs": [
    {{"index": 0, "new_text": "업데이트된 첫번째 문단 텍스트"}},
    {{"index": 1, "new_text": "업데이트된 두번째 문단 텍스트"}}
  ],
  "new_paragraphs": [
    {{"after_index": 5, "text": "새로 삽입할 문단 텍스트"}}
  ],
  "summary": "변경 사항 요약 (1-2문장)"
}}

- updated_paragraphs: 기존 문단 중 내용이 변경된 것만 포함 (변경 없는 문단은 제외)
- new_paragraphs: 새로 추가해야 할 문단 (after_index는 어떤 문단 뒤에 삽입할지)
- summary: 어떤 부분을 왜 변경했는지 요약""",

    'partial_update': """[작업 유형: 부분 수정]
기존 문서에서 추가 자료와 지시사항에 따라 변경이 필요한 부분만 식별하여 수정해주세요.
변경이 불필요한 문단은 건드리지 마세요.

[원본 문서 구조]
{document_map}

[추가 자료]
{supplementary}

[사용자 지시사항]
{instruction}

[응답 형식 - 반드시 이 JSON 스키마를 따르세요]
{{
  "updated_paragraphs": [
    {{"index": 3, "new_text": "수정된 문단 텍스트", "reason": "변경 이유"}}
  ],
  "new_paragraphs": [
    {{"after_index": 10, "text": "새로 삽입할 문단 텍스트", "reason": "삽입 이유"}}
  ],
  "summary": "변경 사항 요약 (1-2문장)"
}}

- 변경이 필요한 문단만 updated_paragraphs에 포함하세요
- 각 변경에 reason을 포함하여 변경 근거를 명시하세요""",
}
```

**Step 2: 구문 확인**

Run: `cd /c/Users/kimsj/GEMintern/GEMintern && source .venv/Scripts/activate && python -c "import prompts; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add prompts.py
git commit -m "feat: add DOC_UPDATER_PROMPTS for document update feature"
```

---

### Task 2: core_doc_updater.py 생성 — 문서 파싱 및 인덱싱

**Files:**
- Create: `core_doc_updater.py`

**Step 1: core_doc_updater.py 작성 — 문서 인덱싱 함수들**

기존 `utils_doctemplate.py`의 `extract_text_from_file`을 참고하되, **인덱스 매핑** 형태로 반환하는 함수를 만든다.

```python
"""
기존 문서 업데이트 모듈
원본 파일을 직접 수정하여 서식을 보존한 채 내용을 업데이트한다.
"""
import os
import io
import json
import copy
import shutil
from google import genai
from google.genai import types
from prompts import DOC_UPDATER_PROMPTS


# ── 1. 문서 인덱싱: paragraph index → text 매핑 ──

def index_docx(file_path: str) -> list[dict]:
    """Word 문서의 paragraph를 인덱싱하여 [{index, text, style}] 반환."""
    from docx import Document
    doc = Document(file_path)
    result = []
    for i, para in enumerate(doc.paragraphs):
        result.append({
            "index": i,
            "text": para.text,
            "style": para.style.name if para.style else "",
        })
    return result


def index_pptx(file_path: str) -> list[dict]:
    """PPT 문서의 slide/shape/paragraph를 인덱싱."""
    from pptx import Presentation
    prs = Presentation(file_path)
    result = []
    idx = 0
    for si, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for pi, para in enumerate(shape.text_frame.paragraphs):
                result.append({
                    "index": idx,
                    "text": para.text,
                    "slide": si,
                    "shape_name": shape.name,
                    "para_in_shape": pi,
                })
                idx += 1
    return result


def index_text_file(file_path: str) -> list[dict]:
    """TXT/MD 파일을 줄 단위로 인덱싱."""
    raw = open(file_path, 'rb').read()
    text = ""
    for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = raw.decode('utf-8', errors='replace')

    lines = text.split('\n')
    return [{"index": i, "text": line} for i, line in enumerate(lines)]


def index_document(file_path: str) -> tuple[str, list[dict]]:
    """파일 확장자에 따라 적절한 인덱서를 선택. (doc_type, indexed_paragraphs) 반환."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.docx':
        return 'docx', index_docx(file_path)
    elif ext == '.pptx':
        return 'pptx', index_pptx(file_path)
    elif ext in ('.txt', '.md'):
        return 'text', index_text_file(file_path)
    elif ext == '.pdf':
        # PDF는 텍스트 추출만 가능, Word로 변환 출력
        return 'pdf', _index_pdf(file_path)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {ext}")


def _index_pdf(file_path: str) -> list[dict]:
    """PDF에서 텍스트 추출하여 인덱싱."""
    import fitz
    doc = fitz.open(file_path)
    result = []
    idx = 0
    for page_num, page in enumerate(doc):
        blocks = page.get_text("blocks")
        for block in blocks:
            text = block[4].strip()
            if text:
                result.append({"index": idx, "text": text, "page": page_num})
                idx += 1
    doc.close()
    return result


def format_document_map(indexed: list[dict]) -> str:
    """인덱싱된 문서를 AI에게 전달할 문자열로 포맷."""
    lines = []
    for item in indexed:
        text_preview = item["text"][:200]
        if len(item["text"]) > 200:
            text_preview += "..."
        lines.append(f"[{item['index']}] {text_preview}")
    return "\n".join(lines)


# ── 2. 추가 자료 파싱 ──

def parse_supplementary_files(file_paths: list[str]) -> str:
    """추가 자료 파일들을 파싱하여 하나의 텍스트로 합침."""
    from utils_doctemplate import extract_text_from_file
    parts = []
    for path in file_paths:
        name = os.path.basename(path)
        text = extract_text_from_file(path)
        if text:
            parts.append(f"--- [{name}] ---\n{text}")
    return "\n\n".join(parts)


# ── 3. AI 호출 ──

def call_update_ai(document_map: str, supplementary: str, instruction: str,
                   mode: str, api_key: str, model: str) -> dict:
    """Gemini API를 호출하여 업데이트 지시 JSON을 받는다."""
    client = genai.Client(api_key=api_key)

    if mode == "full":
        user_prompt = DOC_UPDATER_PROMPTS['full_update'].format(
            document_map=document_map,
            supplementary=supplementary,
            instruction=instruction,
        )
    else:
        user_prompt = DOC_UPDATER_PROMPTS['partial_update'].format(
            document_map=document_map,
            supplementary=supplementary,
            instruction=instruction,
        )

    config = types.GenerateContentConfig(
        system_instruction=DOC_UPDATER_PROMPTS['system'],
        temperature=0.3,
        response_mime_type="application/json",
    )

    response = client.models.generate_content(
        model=model, contents=user_prompt, config=config
    )

    raw = response.text.strip()
    return json.loads(raw)


# ── 4. 원본 파일 직접 수정 ──

def apply_updates_docx(file_path: str, updates: dict, output_path: str):
    """Word 문서의 paragraph를 직접 수정하여 output_path에 저장."""
    from docx import Document
    doc = Document(file_path)

    # 기존 paragraph 텍스트 교체 (Run 서식 보존)
    for item in updates.get("updated_paragraphs", []):
        idx = item["index"]
        new_text = item["new_text"]
        if 0 <= idx < len(doc.paragraphs):
            para = doc.paragraphs[idx]
            # 첫 번째 run에 전체 텍스트를 넣고, 나머지 run은 비움
            if para.runs:
                para.runs[0].text = new_text
                for run in para.runs[1:]:
                    run.text = ""
            else:
                para.text = new_text

    # 새 paragraph 삽입 (뒤에서부터 삽입하여 인덱스 밀림 방지)
    new_paras = sorted(updates.get("new_paragraphs", []),
                       key=lambda x: x["after_index"], reverse=True)
    for item in new_paras:
        after_idx = item["after_index"]
        text = item["text"]
        if 0 <= after_idx < len(doc.paragraphs):
            ref_para = doc.paragraphs[after_idx]
            new_para = copy.deepcopy(ref_para._element)
            # 새 paragraph의 텍스트 설정
            from docx.oxml.ns import qn
            for r in new_para.findall(qn('w:r')):
                new_para.remove(r)
            from docx.oxml import OxmlElement
            r_elem = OxmlElement('w:r')
            t_elem = OxmlElement('w:t')
            t_elem.text = text
            r_elem.append(t_elem)
            new_para.append(r_elem)
            ref_para._element.addnext(new_para)

    doc.save(output_path)


def apply_updates_pptx(file_path: str, updates: dict, indexed: list[dict], output_path: str):
    """PPT 문서의 shape 텍스트를 직접 수정하여 output_path에 저장."""
    from pptx import Presentation
    prs = Presentation(file_path)

    # indexed에서 index → (slide_idx, shape_name, para_in_shape) 매핑 구축
    index_map = {}
    for item in indexed:
        index_map[item["index"]] = item

    for item in updates.get("updated_paragraphs", []):
        idx = item["index"]
        new_text = item["new_text"]
        if idx not in index_map:
            continue
        meta = index_map[idx]
        slide = prs.slides[meta["slide"]]
        for shape in slide.shapes:
            if shape.name == meta["shape_name"] and shape.has_text_frame:
                pi = meta["para_in_shape"]
                if pi < len(shape.text_frame.paragraphs):
                    para = shape.text_frame.paragraphs[pi]
                    if para.runs:
                        para.runs[0].text = new_text
                        for run in para.runs[1:]:
                            run.text = ""
                    else:
                        para.text = new_text
                break

    prs.save(output_path)


def apply_updates_text(file_path: str, updates: dict, output_path: str):
    """TXT/MD 파일의 줄을 수정하여 output_path에 저장."""
    raw = open(file_path, 'rb').read()
    text = ""
    for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr']:
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = raw.decode('utf-8', errors='replace')

    lines = text.split('\n')

    # 기존 줄 수정
    for item in updates.get("updated_paragraphs", []):
        idx = item["index"]
        if 0 <= idx < len(lines):
            lines[idx] = item["new_text"]

    # 새 줄 삽입 (뒤에서부터)
    new_items = sorted(updates.get("new_paragraphs", []),
                       key=lambda x: x["after_index"], reverse=True)
    for item in new_items:
        after_idx = item["after_index"]
        if 0 <= after_idx < len(lines):
            lines.insert(after_idx + 1, item["text"])

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def apply_updates_pdf_as_docx(file_path: str, updates: dict, indexed: list[dict], output_path: str):
    """PDF는 직접 수정 불가 → 텍스트를 Word로 변환하여 저장."""
    from docx import Document
    doc = Document()

    # indexed 텍스트를 기본으로 하되 updates 반영
    update_map = {item["index"]: item["new_text"] for item in updates.get("updated_paragraphs", [])}

    for item in indexed:
        idx = item["index"]
        text = update_map.get(idx, item["text"])
        doc.add_paragraph(text)

    # 새 paragraph는 끝에 추가 (PDF 구조 보존 불가이므로)
    for item in updates.get("new_paragraphs", []):
        doc.add_paragraph(item["text"])

    doc.save(output_path)


# ── 5. 통합 실행 함수 ──

def update_document(original_path: str, supplementary_paths: list[str],
                    supplementary_text: str, instruction: str,
                    mode: str, api_key: str, model: str) -> tuple[str, str, str]:
    """
    문서 업데이트 전체 파이프라인.
    Returns: (output_path, summary, preview_text)
    """
    # 1. 원본 인덱싱
    doc_type, indexed = index_document(original_path)
    document_map = format_document_map(indexed)

    # 2. 추가 자료 파싱
    supplementary = ""
    if supplementary_paths:
        supplementary = parse_supplementary_files(supplementary_paths)
    if supplementary_text:
        supplementary += f"\n\n--- [직접 입력 텍스트] ---\n{supplementary_text}"

    if not supplementary.strip():
        supplementary = "(추가 자료 없음 — 지시사항에 따라 기존 문서만 수정)"

    # 3. AI 호출
    updates = call_update_ai(document_map, supplementary, instruction, mode, api_key, model)

    # 4. 원본 파일 수정
    base, ext = os.path.splitext(original_path)
    if doc_type == 'pdf':
        output_path = base + "_updated.docx"
    else:
        output_path = base + "_updated" + ext

    if doc_type == 'docx':
        apply_updates_docx(original_path, updates, output_path)
    elif doc_type == 'pptx':
        apply_updates_pptx(original_path, updates, indexed, output_path)
    elif doc_type == 'text':
        apply_updates_text(original_path, updates, output_path)
    elif doc_type == 'pdf':
        apply_updates_pdf_as_docx(original_path, updates, indexed, output_path)

    # 5. 미리보기용 텍스트 생성
    summary = updates.get("summary", "업데이트 완료")
    preview_lines = [f"## 변경 사항 요약\n{summary}\n"]
    for item in updates.get("updated_paragraphs", []):
        reason = item.get("reason", "")
        preview_lines.append(f"**[{item['index']}번 문단 수정]** {reason}")
        preview_lines.append(f"> {item['new_text'][:150]}...\n")
    for item in updates.get("new_paragraphs", []):
        reason = item.get("reason", "")
        preview_lines.append(f"**[{item['after_index']}번 뒤 신규 삽입]** {reason}")
        preview_lines.append(f"> {item['text'][:150]}...\n")
    preview = "\n".join(preview_lines)

    return output_path, summary, preview
```

**Step 2: 구문 확인**

Run: `cd /c/Users/kimsj/GEMintern/GEMintern && source .venv/Scripts/activate && python -c "import core_doc_updater; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add core_doc_updater.py
git commit -m "feat: add core_doc_updater module for document update logic"
```

---

### Task 3: pages/doc_updater_page.py 생성 — UI 페이지

**Files:**
- Create: `pages/doc_updater_page.py`

**Step 1: PyQt6 UI 페이지 작성**

기존 `pages/doctemplate_page.py` 패턴을 따라 구현한다.

```python
"""Document updater page — 기존 문서 업데이트."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QRadioButton, QButtonGroup, QProgressBar,
    QFileDialog, QMessageBox, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt
from app_state import AppState
from widgets.file_picker import FilePicker
from widgets.markdown_viewer import MarkdownViewer
from widgets.status_box import StatusBox


class DocUpdateWorker(QThread):
    finished = pyqtSignal(str, str, str)  # output_path, summary, preview
    error = pyqtSignal(str)

    def __init__(self, original_path, supplementary_paths, supplementary_text,
                 instruction, mode, api_key, model, parent=None):
        super().__init__(parent)
        self.original_path = original_path
        self.supplementary_paths = supplementary_paths
        self.supplementary_text = supplementary_text
        self.instruction = instruction
        self.mode = mode
        self.api_key = api_key
        self.model = model

    def run(self):
        try:
            from core_doc_updater import update_document
            output_path, summary, preview = update_document(
                self.original_path, self.supplementary_paths,
                self.supplementary_text, self.instruction,
                self.mode, self.api_key, self.model,
            )
            self.finished.emit(output_path, summary, preview)
        except Exception as e:
            self.error.emit(str(e))


class DocUpdaterPage(QWidget):
    navigate_to = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._output_path = ""
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 24, 32, 24)

        # Title
        title = QLabel("📄 기존 문서 업데이트")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(StatusBox(
            "기존 문서에 추가 자료와 지시사항을 반영하여 원본 서식을 유지한 채 업데이트합니다.",
            "info"
        ))

        # Step 1: Original document
        layout.addWidget(QLabel("📎 Step 1: 기존 문서 업로드"))
        self.original_picker = FilePicker(
            "기존 문서 (1개)", accept_multiple=False,
            file_filter="Documents (*.docx *.pptx *.pdf *.txt *.md);;All (*)"
        )
        layout.addWidget(self.original_picker)

        # Step 2: Supplementary materials
        layout.addWidget(QLabel("📚 Step 2: 추가 자료 업로드 (선택)"))
        self.suppl_picker = FilePicker(
            "추가 자료 (복수 가능)", accept_multiple=True,
            file_filter="Documents (*.docx *.pdf *.pptx *.xlsx *.xls *.txt *.md *.csv);;All (*)"
        )
        layout.addWidget(self.suppl_picker)

        self.suppl_text = QTextEdit()
        self.suppl_text.setPlaceholderText("또는 추가 자료 텍스트를 직접 붙여넣기...")
        self.suppl_text.setMaximumHeight(120)
        self.suppl_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.suppl_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.suppl_text)

        # Step 3: Instruction
        layout.addWidget(QLabel("💡 Step 3: 업데이트 지시사항"))
        self.instruction_edit = QTextEdit()
        self.instruction_edit.setPlaceholderText(
            "예: 2025년 재무 데이터를 반영하고, 시장 분석 섹션을 업데이트해줘"
        )
        self.instruction_edit.setMaximumHeight(100)
        self.instruction_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.instruction_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.instruction_edit)

        # Options row
        opts = QHBoxLayout()

        # Update mode
        opts.addWidget(QLabel("모드:"))
        self.mode_group = QButtonGroup(self)
        self.radio_partial = QRadioButton("부분 수정")
        self.radio_full = QRadioButton("전체 재생성")
        self.radio_partial.setChecked(True)
        self.mode_group.addButton(self.radio_partial)
        self.mode_group.addButton(self.radio_full)
        opts.addWidget(self.radio_partial)
        opts.addWidget(self.radio_full)

        opts.addStretch()

        # Model
        opts.addWidget(QLabel("모델:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gemini-2.5-flash", "gemini-2.5-pro"])
        opts.addWidget(self.model_combo)

        layout.addLayout(opts)

        # Run button
        self.btn_update = QPushButton("🔄 문서 업데이트 실행")
        self.btn_update.setStyleSheet("""
            QPushButton { background: #0068c9; color: white; border: none;
                         padding: 10px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background: #004085; }
        """)
        self.btn_update.clicked.connect(self._on_update)
        layout.addWidget(self.btn_update)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Status
        self.status_box = StatusBox("", "info")
        self.status_box.setVisible(False)
        layout.addWidget(self.status_box)

        # Result preview
        self.result_viewer = MarkdownViewer()
        self.result_viewer.setMinimumHeight(300)
        layout.addWidget(self.result_viewer)

        # Save buttons
        btn_row = QHBoxLayout()
        self.btn_save_original = QPushButton("📄 업데이트 파일 저장")
        self.btn_save_original.clicked.connect(self._save_updated_file)
        self.btn_save_original.setEnabled(False)
        btn_row.addWidget(self.btn_save_original)

        self.btn_save_md = QPushButton("📝 MD 저장")
        self.btn_save_md.clicked.connect(self._save_md)
        self.btn_save_md.setEnabled(False)
        btn_row.addWidget(self.btn_save_md)

        btn_row.addStretch()

        self.btn_reset = QPushButton("🔄 초기화")
        self.btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(self.btn_reset)

        layout.addLayout(btn_row)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_update(self):
        # Validate inputs
        original_paths = self.original_picker.get_file_paths()
        if not original_paths:
            QMessageBox.warning(self, "경고", "기존 문서를 선택해주세요.")
            return

        instruction = self.instruction_edit.toPlainText().strip()
        if not instruction:
            QMessageBox.warning(self, "경고", "업데이트 지시사항을 입력해주세요.")
            return

        settings = AppState.get("latest_settings", {})
        api_key = settings.get("api_key", "")
        if not api_key:
            QMessageBox.warning(self, "경고", "설정에서 API Key를 입력해주세요.")
            return

        mode = "full" if self.radio_full.isChecked() else "partial"
        suppl_paths = self.suppl_picker.get_file_paths()
        suppl_text = self.suppl_text.toPlainText().strip()

        self.btn_update.setEnabled(False)
        self.progress.setVisible(True)
        self.status_box.setText("문서 분석 및 업데이트 중...", "info")
        self.status_box.setVisible(True)

        self._worker = DocUpdateWorker(
            original_paths[0], suppl_paths, suppl_text,
            instruction, mode, api_key, self.model_combo.currentText(),
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, output_path, summary, preview):
        self.progress.setVisible(False)
        self.btn_update.setEnabled(True)
        self._output_path = output_path
        self.status_box.setText(f"완료: {summary}", "success")
        self.result_viewer.setMarkdown(preview)
        self.btn_save_original.setEnabled(True)
        self.btn_save_md.setEnabled(True)
        AppState.set("doc_updater_preview", preview)

    def _on_error(self, error_msg):
        self.progress.setVisible(False)
        self.btn_update.setEnabled(True)
        self.status_box.setText(f"오류: {error_msg}", "error")
        QMessageBox.critical(self, "오류", error_msg)

    def _save_updated_file(self):
        if not self._output_path or not os.path.exists(self._output_path):
            QMessageBox.warning(self, "경고", "저장할 파일이 없습니다.")
            return
        import os
        ext = os.path.splitext(self._output_path)[1]
        name = os.path.basename(self._output_path)
        filter_map = {
            '.docx': "Word (*.docx)",
            '.pptx': "PowerPoint (*.pptx)",
            '.txt': "Text (*.txt)",
            '.md': "Markdown (*.md)",
        }
        file_filter = filter_map.get(ext, f"File (*{ext})")
        path, _ = QFileDialog.getSaveFileName(self, "업데이트 파일 저장", name, file_filter)
        if path:
            import shutil
            shutil.copy2(self._output_path, path)
            self.status_box.setText(f"저장 완료: {path}", "success")

    def _save_md(self):
        preview = AppState.get("doc_updater_preview", "")
        if not preview:
            return
        path, _ = QFileDialog.getSaveFileName(self, "MD 저장", "update_preview.md", "Markdown (*.md)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(preview)

    def _reset(self):
        self.result_viewer.setMarkdown("")
        self.status_box.setVisible(False)
        self.btn_save_original.setEnabled(False)
        self.btn_save_md.setEnabled(False)
        self._output_path = ""
        AppState.set("doc_updater_preview", "")

    def refresh(self):
        pass
```

참고: `import os`가 `_save_updated_file` 안에 중복되어 있으므로, 파일 상단에만 두고 메서드 내부의 import는 제거할 것.

**Step 2: 구문 확인**

Run: `cd /c/Users/kimsj/GEMintern/GEMintern && source .venv/Scripts/activate && python -c "from pages.doc_updater_page import DocUpdaterPage; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add pages/doc_updater_page.py
git commit -m "feat: add DocUpdaterPage UI for document update feature"
```

---

### Task 4: main_window.py에 네비게이션 등록

**Files:**
- Modify: `main_window.py:19-84`

**Step 1: import 추가**

`main_window.py:31` (qa_session_page import 다음)에 추가:

```python
from pages.doc_updater_page import DocUpdaterPage
```

**Step 2: NAV_SECTIONS에 메뉴 항목 추가**

`Independent Tools` 섹션(`main_window.py:44-49`)의 리스트 끝에 추가:

```python
        ("📄 문서 업데이트", "doc_updater"),
```

결과:
```python
    "Independent Tools": [
        ("📑 IM 작성", "im"),
        ("📢 발표자료 (PPT)", "ppt_tools"),
        ("🙋‍♂️ LP Q&A 대응", "lp_qa"),
        ("💬 자료기반 Q&A", "qa_session"),
        ("📄 문서 업데이트", "doc_updater"),
    ],
```

**Step 3: PAGE_FACTORIES에 등록**

`main_window.py:83` (`"text_organizer": TextOrganizerPage,` 다음)에 추가:

```python
    "doc_updater": DocUpdaterPage,
```

**Step 4: 구문 확인**

Run: `cd /c/Users/kimsj/GEMintern/GEMintern && source .venv/Scripts/activate && python -c "from main_window import MainWindow; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add main_window.py
git commit -m "feat: register doc_updater page in navigation"
```

---

### Task 5: 통합 테스트 — 앱 실행 확인

**Step 1: 앱 실행**

Run: `cd /c/Users/kimsj/GEMintern/GEMintern && source .venv/Scripts/activate && python main.py`
(백그라운드로 실행)

**Step 2: 확인 사항**
- 사이드바 "Independent Tools" 섹션에 "📄 문서 업데이트" 메뉴 표시
- 메뉴 클릭 시 DocUpdaterPage UI 렌더링
- Step 1/2/3 UI 요소 정상 표시
- FilePicker 동작 확인

**Step 3: 앱 종료 후 최종 Commit**

```bash
git add -A
git commit -m "feat: complete document updater feature integration"
```

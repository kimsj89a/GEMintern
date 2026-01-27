import io
import re
import os
import tempfile
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
from pptx import Presentation
from openai import OpenAI

# Gemini Vision OCR 지원 (google-genai 패키지 필요)
OCR_AVAILABLE = False
OCR_ERROR_MSG = ""

try:
    from google import genai
    from google.genai import types
    OCR_AVAILABLE = True
except ImportError:
    OCR_ERROR_MSG = "google-genai 패키지가 설치되지 않았습니다"

# MarkItDown 지원 확인
MARKITDOWN_AVAILABLE = False
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    pass

# Document AI OCR 지원 확인
DOCAI_AVAILABLE = False
try:
    import utils_docai
    DOCAI_AVAILABLE = True
except ImportError:
    pass

def get_ocr_status():
    """OCR 상태 확인 (UI에서 사용)"""
    if OCR_AVAILABLE:
        return True, "Gemini Vision OCR 사용 가능(API 키 필요)"
    return False, OCR_ERROR_MSG


def extract_pdf_with_gemini_ocr(doc, api_key, ocr_threshold=50):
    """
    PDF에서 텍스트 추출 (Gemini Vision OCR 대응)

    Args:
        doc: fitz.Document 객체
        api_key: Google API 키
        ocr_threshold: 페이지당 글자 수 미만이면 OCR 수행

    Returns:
        추출된 텍스트
    """
    text_content = ""
    ocr_used = False
    ocr_pages = []

    # 1단계: 일반 텍스트 추출 및 OCR 필요 페이지 표시
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()

        if len(page_text) < ocr_threshold:
            # OCR이 필요한 페이지 - 이미지로 변환
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x 이상도
            img_bytes = pix.tobytes("png")
            ocr_pages.append((page_num, img_bytes, page_text))
        else:
            text_content += f"[Page {page_num + 1}]\n{page_text}\n\n"

    # 2단계: OCR 필요 페이지가 있고 API 키가 있으면 Gemini OCR 수행
    if ocr_pages and api_key and OCR_AVAILABLE:
        try:
            client = genai.Client(api_key=api_key)

            for page_num, img_bytes, original_text in ocr_pages:
                try:
                    # Gemini Vision API 호출
                    response = client.models.generate_content(
                        model="gemini-2.0-flash-exp",
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                            "이 이미지에서 모든 텍스트를 추출해주세요. 원본 레이아웃을 최대한 유지하고, 텍스트만 반환해주세요. 추가 설명 없이 텍스트만 출력하세요."
                        ],
                        config=types.GenerateContentConfig(
                            max_output_tokens=4096,
                            temperature=0.1
                        )
                    )

                    ocr_text = response.text.strip() if response.text else ""

                    if len(ocr_text) > len(original_text):
                        text_content += f"[Page {page_num + 1} - OCR]\n{ocr_text}\n\n"
                        ocr_used = True
                    else:
                        text_content += f"[Page {page_num + 1}]\n{original_text}\n\n"

                except Exception:
                    # 개별 페이지 OCR 실패 시 원본 유지
                    text_content += f"[Page {page_num + 1}]\n{original_text}\n\n"

        except Exception:
            # API 연결 실패 시 원본 텍스트로 대체
            for page_num, _, original_text in ocr_pages:
                text_content += f"[Page {page_num + 1}]\n{original_text}\n\n"
    else:
        # OCR 불가 시 원본 텍스트 사용
        for page_num, _, original_text in ocr_pages:
            text_content += f"[Page {page_num + 1}]\n{original_text}\n\n"

    # OCR 사용 여부 표시
    if ocr_used:
        text_content = "[Gemini Vision OCR 적용됨]\n\n" + text_content

    return text_content


# 레거시 명환용 (API 키 없이 호출 시)
def extract_pdf_with_ocr(doc):
    """레거시 호환 - API 키 없이 호출 시 일반 텍스트만 추출"""
    text_content = ""
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()
        text_content += f"[Page {page_num + 1}]\n{page_text}\n\n"
    return text_content

def _docx_to_ppt_markdown(doc: Document, filename: str) -> str:
    """
    Convert a Word document into PPT-friendly Markdown.

    Mapping:
    - Heading 1 -> section cover (#)
    - Heading 2 -> slide title (##)
    - Heading 3+ -> emphasized line inside a slide (###)
    - Normal paragraphs -> bullets (-)
    """
    title = os.path.splitext(filename)[0]
    lines = [f"# {title}"]

    def has_slide_title() -> bool:
        return any(line.startswith("## ") for line in lines)

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if not text:
            continue

        style_name = ""
        try:
            style_name = (para.style.name or "").lower()
        except Exception:
            style_name = ""

        if style_name.startswith("heading"):
            level = 2
            match = re.search(r"heading\s*(\d+)", style_name)
            if match:
                try:
                    level = int(match.group(1))
                except Exception:
                    level = 2

            if level <= 1:
                lines.append(f"# {text}")
            elif level == 2:
                lines.append(f"## {text}")
            else:
                lines.append(f"### {text}")
            continue

        if not has_slide_title():
            lines.append("## Overview")

        lines.append(f"- {text}")

    return "\n".join(lines).strip() + "\n\n"


def parse_uploaded_file(uploaded_file, api_key=None, docai_config=None, template_option=None):
    """파일 형태별 텍스트 추출 (전체 시트 지원 + OCR 지원)

    Args:
        uploaded_file: Streamlit 업로드 파일 객체
        api_key: Google API 키 (PDF OCR용, 선택사항)
        docai_config: Document AI 설정 dict (선택사항)
            - project_id: GCP 프로젝트 ID
            - location: 위치 (us/eu)
            - processor_id: 프로세서 ID
            - credentials_json: 서비스 계정 JSON 문자열
    """
    if uploaded_file is None:
        return ""

    file_type = uploaded_file.name.split('.')[-1].lower()

    # [Document AI OCR] PDF/이미지 우선 처리
    if DOCAI_AVAILABLE and docai_config and file_type in utils_docai.get_supported_extensions():
        try:
            uploaded_file.seek(0)
            file_bytes = uploaded_file.read()
            mime_type = utils_docai.get_mime_type(uploaded_file.name)

            ocr_result = utils_docai.process_document(
                file_bytes=file_bytes,
                mime_type=mime_type,
                project_id=docai_config['project_id'],
                location=docai_config.get('location', 'us'),
                processor_id=docai_config['processor_id'],
                credentials_json=docai_config.get('credentials_json')
            )

            uploaded_file.seek(0)
            if ocr_result and ocr_result.get('text'):
                return f"### [파일명: {uploaded_file.name} (Document AI OCR)]\n{ocr_result['text']}\n\n"
        except Exception as e:
            uploaded_file.seek(0)
            # Document AI 실패 시 다음 방법으로 진행

    # [MarkItDown] 우선 시도
    # PPT 모드에서 Word는 별도 변환 로직을 사용한다.
    if MARKITDOWN_AVAILABLE and not (template_option == "presentation" and file_type in ["docx", "doc"]):
        try:
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                uploaded_file.seek(0)
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            uploaded_file.seek(0)

            try:
                md = MarkItDown()
                result = md.convert(tmp_path)
                if result and result.text_content:
                    return f"### [파일명: {uploaded_file.name} (MarkItDown)]\n{result.text_content}\n\n"
            finally:
                if os.path.exists(tmp_path):
                    try: os.unlink(tmp_path)
                    except: pass
        except Exception:
            uploaded_file.seek(0)

    file_type = uploaded_file.name.split('.')[-1].lower()
    text_content = ""

    try:
        # [PDF] PyMuPDF + Gemini Vision OCR
        if file_type == 'pdf':
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                if api_key:
                    text_content = extract_pdf_with_gemini_ocr(doc, api_key)
                else:
                    text_content = extract_pdf_with_ocr(doc)

        # [Word] python-docx
        elif file_type in ['docx', 'doc']:
            doc = Document(uploaded_file)
            if template_option == "presentation":
                text_content = _docx_to_ppt_markdown(doc, uploaded_file.name)
            else:
                for para in doc.paragraphs:
                    text_content += para.text + "\n"

        # [PPT] python-pptx
        elif file_type in ['pptx', 'ppt']:
            prs = Presentation(uploaded_file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text_content += shape.text + "\n"

        # [Excel] pandas (전체 시트 파싱 적용)
        elif file_type in ['xlsx', 'xls', 'csv']:
            try:
                text_content = f"### [파일명: {uploaded_file.name}]\n"

                # 1. 파일 읽기 (CSV vs Excel)
                if file_type == 'csv':
                    df = pd.read_csv(uploaded_file)
                    df = df.fillna("")
                    try:
                        table_text = df.to_markdown(index=False)
                    except ImportError:
                        table_text = df.to_string(index=False)
                    text_content += f"\n{table_text}\n"
                else:
                    # [특별 변경] sheet_name=None으로 설정하여 모든 시트를 OrderedDict로 읽어옴
                    # 명시적 openpyxl 명시적으로 사용 (안정성)
                    xls_dict = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')

                    # 모든 시트 조회
                    for sheet_name, df in xls_dict.items():
                        df = df.fillna("") # 빈값 처리

                        # 시트별 헤더 추가
                        text_content += f"\n#### [Sheet: {sheet_name}]\n"

                        # 변환 (tabulate가 없으면 to_string으로 대체)
                        try:
                            table_text = df.to_markdown(index=False)
                        except ImportError:
                            table_text = df.to_string(index=False)

                        text_content += f"{table_text}\n"

            except Exception as e:
                text_content = f"[엑셀 파싱 오류: {str(e)}]\n(Tip: 암호 걸린 파일인 아닌지, 형식에 맞는지 확인해주세요)"

        # [Text]
        elif file_type in ['txt', 'md']:
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            text_content = stringio.read()

        else:
            text_content = f"[지원하지 않는 파일 형식입니다: {uploaded_file.name}]"

    except Exception as e:
        return f"[파일 읽기 시도 중 오류: {uploaded_file.name} - {str(e)}]"

    # 파일 포인터 초기화
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)

    return f"{text_content}\n\n"

def generate_filename(uploaded_files, template_option):
    template_map = {
        "simple_review": "simple_review",
        "rfi": "RFI",
        "investment": "investment_report",
        "im": "IM",
        "management": "management_report",
        "presentation": "presentation",
        "custom": "report",
    }
    suffix = template_map.get(template_option, "report")
    project_name = "Investment_Report"
    if uploaded_files:
        first_file = uploaded_files[0].name
        base_name = os.path.splitext(first_file)[0]
        project_name = re.sub(r'[\\/*?:"<>|]', "", base_name).strip()
    return f"{project_name}_{suffix}.docx"

def add_list_paragraph(doc, content, level, is_bullet=True):
    """들여쓰기가 적용된 리스트 아이템 추가

    Args:
        doc: Document 객체
        content: 텍스트 내용
        level: 들여쓰기 레벨 (0부터 시작)
        is_bullet: True면 불릿, False면 번호
    """

    # Bullet characters by level (fallback to simple ASCII bullets)
    bullet_chars = ["-", "*", "+"]
    bullet_char = bullet_chars[level % len(bullet_chars)]

    p = doc.add_paragraph()

    # 들여쓰기 설정 (레벨당 0.1인치)
    indent = Inches(0.1 * (level + 1))
    p.paragraph_format.left_indent = indent
    p.paragraph_format.first_line_indent = Inches(-0.15)  # 불릿/번호 hanging indent

    # 불릿 문자 추가
    if is_bullet:
        p.add_run(f"{bullet_char} ")
    else:
        p.add_run(f"• ")  # 번호 리스트도 일단 불릿으로

    # 내용 추가 (볼드 처리 포함)
    parts = re.split(r'(\*\*.*?\*\*)', content)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            run = p.add_run(part[2:-2])
            run.bold = True
        else:
            p.add_run(part)

    return p

def create_docx(markdown_text):
    doc = Document()
    lines = markdown_text.split('\n')
    i = 0

    # 로마 숫자 헤더 패턴 (I., II., III., IV., V., VI., VII., VIII.)
    roman_header_pattern = re.compile(r'^(I{1,3}|IV|VI{0,3}|V|IX|X)\.\s+(.+)$')

    # 리스트 level 추적 (들여쓰기 상속)
    indent_stack = [0]  # 각 level의 들여쓰기 칸 수

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()

        # Markdown 헤더 처리 (#### 추가)
        if line.startswith('##### '):
            doc.add_heading(line.replace('##### ', ''), level=5)
            indent_stack = [0]  # 리스트 상속 리셋
            i += 1
        elif line.startswith('#### '):
            doc.add_heading(line.replace('#### ', ''), level=4)
            indent_stack = [0]
            i += 1
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=3)
            indent_stack = [0]
            i += 1
        elif line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=2)
            indent_stack = [0]
            i += 1
        elif line.startswith('# '):
            doc.add_heading(line.replace('# ', ''), level=1)
            indent_stack = [0]
            i += 1
        # 로마 숫자 헤더 처리 (I. Executive Summary 등)
        elif roman_header_pattern.match(line):
            doc.add_heading(line, level=1)
            indent_stack = [0]
            i += 1
        elif line.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            if len(table_lines) >= 2:
                headers = [c.strip() for c in table_lines[0].split('|') if c.strip()]
                data_rows = []
                for row_line in table_lines[1:]:
                    if '---' in row_line: continue
                    parts = row_line.split('|')
                    if len(parts) >= 2: data_rows.append([c.strip() for c in parts[1:-1]])
                if headers:
                    table = doc.add_table(rows=1, cols=len(headers))
                    table.style = 'Table Grid'
                    for idx, text in enumerate(headers):
                        if idx < len(table.rows[0].cells):
                            cell = table.rows[0].cells[idx]
                            cell.text = text
                            cell.paragraphs[0].runs[0].bold = True
                    for row_data in data_rows:
                        row_cells = table.add_row().cells
                        for idx, text in enumerate(row_data):
                            if idx < len(row_cells): row_cells[idx].text = text.replace('**', '')
            indent_stack = [0]
        elif re.match(r'^\s*([-*]|\d+\.)\s', raw_line):
            match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)', raw_line)
            if match:
                indent_str, marker, content = match.groups()
                spaces = indent_str.replace('\t', '    ')  # 탭을 4칸으로
                indent_len = len(spaces)

                # 들여쓰기 기반 level 계산 (시작점으로 1, 2, 3...)
                if indent_len == 0:
                    level = 0
                    indent_stack = [0]
                elif indent_len > indent_stack[-1]:
                    # 들여쓰기 증가 시 level 증가
                    level = len(indent_stack)
                    indent_stack.append(indent_len)
                else:
                    # 들여쓰기 감소 또는 유지 시 해당 level 찾기
                    while len(indent_stack) > 1 and indent_stack[-1] > indent_len:
                        indent_stack.pop()
                    level = len(indent_stack) - 1

                if level > 8: level = 8
                is_bullet = marker in ['-', '*']
                add_list_paragraph(doc, content, level, is_bullet)
            i += 1
        else:
            if line:
                p = doc.add_paragraph()
                parts = re.split(r'(\*\*.*?\*\*)', line)
                for part in parts:
                    if part.startswith('**') and part.endswith('**'):
                        run = p.add_run(part[2:-2])
                        run.bold = True
                    else: p.add_run(part)
            i += 1
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_excel(markdown_text):
    data = []
    lines = markdown_text.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('|') and '---' not in line:
            row = [c.strip().replace('**', '') for c in line.split('|')[1:-1]]
            if row: data.append(row)
    bio = io.BytesIO()
    if data:
        df = pd.DataFrame(data[1:], columns=data[0])
        with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='RFI_List')
    return bio.getvalue()

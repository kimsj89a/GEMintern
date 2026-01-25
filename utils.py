import io
import re
import os
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
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
    OCR_ERROR_MSG = "google-genai 패키지가 설치되지 않았습니다."


def get_ocr_status():
    """OCR 상태 확인 (UI에서 사용)"""
    if OCR_AVAILABLE:
        return True, "Gemini Vision OCR 사용 가능 (API 키 필요)"
    return False, OCR_ERROR_MSG


def extract_pdf_with_gemini_ocr(doc, api_key, ocr_threshold=50):
    """
    PDF에서 텍스트 추출 (Gemini Vision OCR 폴백)

    Args:
        doc: fitz.Document 객체
        api_key: Google API 키
        ocr_threshold: 페이지당 이 글자수 미만이면 OCR 실행

    Returns:
        추출된 텍스트
    """
    text_content = ""
    ocr_used = False
    ocr_pages = []

    # 1단계: 일반 텍스트 추출 및 OCR 필요 페이지 수집
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()

        if len(page_text) < ocr_threshold:
            # OCR이 필요한 페이지 - 이미지로 변환
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x 해상도
            img_bytes = pix.tobytes("png")
            ocr_pages.append((page_num, img_bytes, page_text))
        else:
            text_content += f"[Page {page_num + 1}]\n{page_text}\n\n"

    # 2단계: OCR 필요 페이지가 있고 API 키가 있으면 Gemini OCR 실행
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
        # OCR 불가능 시 원본 텍스트 사용
        for page_num, _, original_text in ocr_pages:
            text_content += f"[Page {page_num + 1}]\n{original_text}\n\n"

    # OCR 사용 여부 표시
    if ocr_used:
        text_content = "[Gemini Vision OCR 적용됨]\n\n" + text_content

    return text_content


# 레거시 호환용 (API 키 없이 호출 시)
def extract_pdf_with_ocr(doc):
    """레거시 호환 - API 키 없이 호출 시 일반 텍스트만 추출"""
    text_content = ""
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()
        text_content += f"[Page {page_num + 1}]\n{page_text}\n\n"
    return text_content

def parse_uploaded_file(uploaded_file, api_key=None):
    """파일 타입별 텍스트 추출 (전체 시트 지원 + OCR 지원)

    Args:
        uploaded_file: Streamlit 업로드 파일 객체
        api_key: Google API 키 (PDF OCR용, 선택사항)
    """
    if uploaded_file is None:
        return ""

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
                    # [핵심 변경] sheet_name=None으로 설정하여 모든 시트를 OrderedDict로 읽어옴
                    # 엔진은 openpyxl을 명시적으로 사용 (안정성)
                    xls_dict = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')
                    
                    # 모든 시트 순회
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
                text_content = f"[엑셀 파싱 오류: {str(e)}]\n(Tip: 암호 걸린 파일은 아닌지, 포맷이 맞는지 확인해주세요)"
        
        # [Text]
        elif file_type in ['txt', 'md']:
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            text_content = stringio.read()
            
        else:
            text_content = f"[지원하지 않는 파일 형식입니다: {uploaded_file.name}]"

    except Exception as e:
        return f"[파일 읽기 치명적 오류: {uploaded_file.name} - {str(e)}]"

    # 파일 포인터 초기화
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)

    return f"{text_content}\n\n"

def generate_filename(uploaded_files, template_option):
    template_map = {
        'simple_review': '약식투자검토', 'rfi': 'RFI', 'investment': '투자심사보고서',
        'im': 'IM', 'management': '사후관리보고서', 'presentation': '발표자료', 'custom': '보고서'
    }
    suffix = template_map.get(template_option, '보고서')
    project_name = "Investment_Report"
    if uploaded_files:
        first_file = uploaded_files[0].name
        base_name = os.path.splitext(first_file)[0]
        project_name = re.sub(r'[\\/*?:"<>|]', "", base_name).strip()
    return f"{project_name}_{suffix}.docx"

def set_list_level(paragraph, level):
    pPr = paragraph._p.get_or_add_pPr()
    numPr = pPr.get_or_add_numPr()
    ilvl = numPr.get_or_add_ilvl()
    ilvl.val = level
    if numPr.numId is None:
        numId = numPr.get_or_add_numId()
        numId.val = 1 

def create_docx(markdown_text):
    doc = Document()
    lines = markdown_text.split('\n')
    i = 0

    # 로마 숫자 헤더 패턴 (I., II., III., IV., V., VI., VII., VIII.)
    roman_header_pattern = re.compile(r'^(I{1,3}|IV|VI{0,3}|V|IX|X)\.\s+(.+)$')

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()

        # Markdown 헤더 처리 (#### 추가)
        if line.startswith('##### '):
            doc.add_heading(line.replace('##### ', ''), level=5)
            i += 1
        elif line.startswith('#### '):
            doc.add_heading(line.replace('#### ', ''), level=4)
            i += 1
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=3)
            i += 1
        elif line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=2)
            i += 1
        elif line.startswith('# '):
            doc.add_heading(line.replace('# ', ''), level=1)
            i += 1
        # 로마 숫자 헤더 처리 (I. Executive Summary 등)
        elif roman_header_pattern.match(line):
            match = roman_header_pattern.match(line)
            doc.add_heading(line, level=1)
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
        elif re.match(r'^\s*([-*]|\d+\.)\s', raw_line):
            match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)', raw_line)
            if match:
                indent_str, marker, content = match.groups()
                spaces = indent_str.replace('\t', '  ')
                level = len(spaces) // 2
                if level > 8: level = 8
                is_bullet = marker in ['-', '*']
                style_name = 'List Bullet' if is_bullet else 'List Number'
                try: p = doc.add_paragraph(style=style_name)
                except: p = doc.add_paragraph()
                set_list_level(p, level)
                parts = re.split(r'(\*\*.*?\*\*)', content)
                for part in parts:
                    if part.startswith('**') and part.endswith('**'):
                        run = p.add_run(part[2:-2])
                        run.bold = True
                    else: p.add_run(part)
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
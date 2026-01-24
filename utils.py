import io
import re
import os
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from pptx import Presentation
from openai import OpenAI
from PIL import Image

# OCR 지원 (pytesseract 설치 시 활성화)
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def extract_pdf_with_ocr(doc, ocr_threshold=50):
    """
    PDF에서 텍스트 추출 (OCR 폴백 지원)

    Args:
        doc: fitz.Document 객체
        ocr_threshold: 페이지당 이 글자수 미만이면 OCR 실행

    Returns:
        추출된 텍스트
    """
    text_content = ""
    ocr_used = False

    for _, page in enumerate(doc):
        # 1. 먼저 일반 텍스트 추출 시도
        page_text = page.get_text().strip()

        # 2. 텍스트가 너무 적으면 OCR 시도
        if len(page_text) < ocr_threshold and OCR_AVAILABLE:
            try:
                # PyMuPDF pixmap을 PIL Image로 변환
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x 해상도로 품질 향상
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # pytesseract로 OCR 실행 (한글+영어)
                ocr_text = pytesseract.image_to_string(img, lang='kor+eng')

                if len(ocr_text.strip()) > len(page_text):
                    page_text = ocr_text.strip()
                    ocr_used = True

            except Exception:
                # OCR 실패 시 원본 텍스트 유지
                pass

        text_content += f"{page_text}\n"

    # OCR 사용 여부 표시
    if ocr_used:
        text_content = "[OCR 적용됨]\n" + text_content

    return text_content

def parse_uploaded_file(uploaded_file):
    """파일 타입별 텍스트 추출 (전체 시트 지원 + 오류 방지)"""
    if uploaded_file is None:
        return ""
        
    file_type = uploaded_file.name.split('.')[-1].lower()
    text_content = ""

    try:
        # [PDF] PyMuPDF + OCR 폴백
        if file_type == 'pdf':
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
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
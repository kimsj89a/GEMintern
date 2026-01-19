import io
import re
import datetime
import pandas as pd
import fitz  # PyMuPDF (High-performance PDF parser)
from docx import Document
from pptx import Presentation

def parse_uploaded_file(uploaded_file):
    """
    업로드된 파일의 타입에 따라 최적의 라이브러리로 텍스트를 추출합니다.
    Performance: PyMuPDF(PDF) & Calamine(Excel) 적용
    """
    if uploaded_file is None:
        return ""
        
    file_type = uploaded_file.name.split('.')[-1].lower()
    text_content = ""

    try:
        # [PDF] PyMuPDF (fitz) - 기존 pypdf 대비 10배 이상 고속
        if file_type == 'pdf':
            # Streamlit의 UploadedFile을 bytes로 읽어서 처리
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                for page in doc:
                    text_content += page.get_text() + "\n"
        
        # [Word] python-docx (Standard)
        elif file_type in ['docx', 'doc']:
            doc = Document(uploaded_file)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        
        # [PPT] python-pptx (Standard)
        elif file_type in ['pptx', 'ppt']:
            prs = Presentation(uploaded_file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text_content += shape.text + "\n"
        
        # [Excel] pandas + calamine (Rust-based, Ultra fast)
        elif file_type in ['xlsx', 'xls', 'csv']:
            if file_type == 'csv':
                df = pd.read_csv(uploaded_file)
            else:
                try:
                    # 1순위: 고속 calamine 엔진 시도
                    df = pd.read_excel(uploaded_file, engine='calamine')
                except ImportError:
                    # 2순위: fallback (openpyxl)
                    uploaded_file.seek(0)
                    df = pd.read_excel(uploaded_file)
            
            text_content = df.to_string()
        
        # [Text]
        elif file_type in ['txt', 'md']:
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            text_content = stringio.read()
            
        else:
            text_content = f"[지원하지 않는 파일 형식입니다: {uploaded_file.name}]"

    except Exception as e:
        return f"[파일 읽기 오류: {uploaded_file.name} - {str(e)}]"

    # 포인터 초기화 (다른 로직에서 재사용 시 안전장치)
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)

    return f"=== 파일명: {uploaded_file.name} ===\n{text_content}\n\n"

def sanitize_filename(text):
    """파일명으로 사용할 수 없는 문자를 제거합니다."""
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    return text.strip()[:20]

def generate_filename_from_content(content_text, doc_type="Report"):
    """내용 기반 파일명 생성"""
    company_name = "Company"
    try:
        lines = content_text.split('\n')
        patterns = [r"대상\s*??기업\s*??[:\-\)]\s*(.*)", r"Target\s*??[:\-\)]\s*(.*)", r"Company\s*??[:\-\)]\s*(.*)"]
        found = False
        for line in lines[:20]:
            for pat in patterns:
                match = re.search(pat, line, re.IGNORECASE)
                if match:
                    extracted = match.group(1).split('(')[0].strip()
                    if extracted:
                        company_name = sanitize_filename(extracted)
                        found = True
                        break
            if found: break
        
        if not found:
            for line in lines[:10]:
                if line.startswith('# '):
                    clean = line.replace('#', '').strip()
                    if 2 < len(clean) < 20: 
                        company_name = sanitize_filename(clean)
                        break
        return f"{company_name}_{doc_type}.docx"
    except:
        return f"{company_name}_{doc_type}.docx"

def set_list_level(paragraph, level):
    pPr = paragraph._p.get_or_add_pPr()
    numPr = pPr.get_or_add_numPr()
    ilvl = numPr.get_or_add_ilvl()
    ilvl.val = level

def create_docx(markdown_text):
    """Markdown -> Word 변환 (최적화 버전)"""
    doc = Document()
    
    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        
        # 헤더
        if line.strip().startswith('# '):
            doc.add_heading(line.strip().replace('# ', ''), level=1)
            i += 1
        elif line.strip().startswith('## '):
            doc.add_heading(line.strip().replace('## ', ''), level=2)
            i += 1
        elif line.strip().startswith('### '):
            doc.add_heading(line.strip().replace('### ', ''), level=3)
            i += 1
        
        # 표
        elif line.strip().startswith('|'):
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
                    if len(parts) >= 2:
                        data_rows.append([c.strip() for c in parts[1:-1]])

                if headers:
                    table = doc.add_table(rows=1, cols=len(headers))
                    table.style = 'Table Grid'
                    for idx, text in enumerate(headers):
                        if idx < len(table.rows[0].cells):
                            table.rows[0].cells[idx].text = text
                            table.rows[0].cells[idx].paragraphs[0].runs[0].bold = True
                    for row_data in data_rows:
                        row_cells = table.add_row().cells
                        for idx, text in enumerate(row_data):
                            if idx < len(row_cells):
                                row_cells[idx].text = text.replace('**', '')

        # 목록 (List)
        elif re.match(r'^\s*([-*]|\d+\.)\s', line):
            match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)', line)
            if match:
                indent_str, marker, content = match.groups()
                level = len(indent_str) // 2
                style = 'List Bullet' if marker in ['-', '*'] else 'List Number'
                
                try:
                    p = doc.add_paragraph(style=style)
                    if level > 0: set_list_level(p, level)
                except:
                    p = doc.add_paragraph(style='List Paragraph')
                
                parts = re.split(r'(\*\*.*?\*\*)', content)
                for part in parts:
                    if part.startswith('**') and part.endswith('**'):
                        p.add_run(part[2:-2]).bold = True
                    else:
                        p.add_run(part)
            i += 1

        # 일반 텍스트
        else:
            if line.strip():
                p = doc.add_paragraph()
                parts = re.split(r'(\*\*.*?\*\*)', line.strip())
                for part in parts:
                    if part.startswith('**') and part.endswith('**'):
                        p.add_run(part[2:-2]).bold = True
                    else:
                        p.add_run(part)
            i += 1
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_excel(markdown_text):
    """RFI Excel 생성"""
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
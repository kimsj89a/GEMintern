import io
import re
import pandas as pd
from pypdf import PdfReader
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pptx import Presentation

def parse_uploaded_file(uploaded_file):
    """업로드된 파일의 타입에 따라 텍스트를 추출합니다."""
    if uploaded_file is None:
        return ""
        
    file_type = uploaded_file.name.split('.')[-1].lower()
    text_content = ""

    try:
        if file_type == 'pdf':
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content += text + "\n"
        
        elif file_type in ['docx', 'doc']:
            doc = Document(uploaded_file)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        
        elif file_type in ['pptx', 'ppt']:
            prs = Presentation(uploaded_file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text_content += shape.text + "\n"
        
        elif file_type in ['xlsx', 'xls', 'csv']:
            if file_type == 'csv':
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            text_content = df.to_string()
        
        elif file_type in ['txt', 'md']:
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            text_content = stringio.read()
            
        else:
            text_content = f"[지원하지 않는 파일 형식입니다: {uploaded_file.name}]"

    except Exception as e:
        return f"[파일 읽기 오류: {uploaded_file.name} - {str(e)}]"

    return f"=== 파일명: {uploaded_file.name} ===\n{text_content}\n\n"

def create_docx(markdown_text):
    """Markdown 텍스트를 Word 파일로 변환합니다 (표 처리 포함)."""
    doc = Document()
    
    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 1. 헤더 처리
        if line.startswith('# '):
            doc.add_heading(line.replace('# ', ''), level=1)
            i += 1
        elif line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=2)
            i += 1
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=3)
            i += 1
            
        # 2. 표(Table) 처리
        elif line.startswith('|'):
            # 표 데이터 수집
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            
            # Markdown Table 파싱
            if len(table_lines) >= 2: # 최소 헤더 + 구분선
                # 구분선 제거 (---|---)
                headers = [c.strip() for c in table_lines[0].split('|') if c.strip()]
                data_rows = []
                for row_line in table_lines[1:]:
                    if '---' in row_line: continue
                    row_data = [c.strip() for c in row_line.split('|') if c.strip() or c == ""]
                    # 빈 셀 처리 보정
                    if row_line.startswith('|') and row_line.endswith('|'):
                        row_data = [c.strip() for c in row_line.split('|')[1:-1]]
                    if row_data:
                        data_rows.append(row_data)

                if headers:
                    table = doc.add_table(rows=1, cols=len(headers))
                    table.style = 'Table Grid'
                    
                    # 헤더 입력
                    hdr_cells = table.rows[0].cells
                    for idx, text in enumerate(headers):
                        if idx < len(hdr_cells):
                            hdr_cells[idx].text = text
                            hdr_cells[idx].paragraphs[0].runs[0].bold = True
                    
                    # 데이터 입력
                    for row_data in data_rows:
                        row_cells = table.add_row().cells
                        for idx, text in enumerate(row_data):
                            if idx < len(row_cells):
                                row_cells[idx].text = text.replace('**', '') # 볼드 마크 제거
        
        # 3. 일반 텍스트 (Bold 처리)
        else:
            if line:
                p = doc.add_paragraph()
                parts = re.split(r'(\*\*.*?\*\*)', line)
                for part in parts:
                    if part.startswith('**') and part.endswith('**'):
                        run = p.add_run(part[2:-2])
                        run.bold = True
                    else:
                        p.add_run(part)
            i += 1
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def create_excel(markdown_text):
    """Markdown 표를 파싱하여 Excel 파일로 변환합니다 (RFI용)."""
    data = []
    lines = markdown_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('|') and '---' not in line:
            # | col1 | col2 | ...
            row = [c.strip().replace('**', '') for c in line.split('|')[1:-1]]
            if row:
                data.append(row)
    
    bio = io.BytesIO()
    if data:
        df = pd.DataFrame(data[1:], columns=data[0]) # 첫 줄을 헤더로
        with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='RFI_List')
    
    return bio.getvalue()
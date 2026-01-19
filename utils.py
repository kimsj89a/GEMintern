import io
import re
import datetime
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

def sanitize_filename(text):
    """파일명으로 사용할 수 없는 문자를 제거합니다."""
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    return text.strip()[:30] # 너무 길면 자름

def generate_filename_from_content(content_text, default_name="Investment_Report"):
    """
    내용을 분석하여 적절한 파일명을 생성합니다.
    예: 첫 번째 헤더(#) 내용을 가져오거나, '대상 기업:' 문구 등을 찾습니다.
    """
    try:
        lines = content_text.split('\n')
        
        # 1. '# 1. 기업명' 패턴 찾기
        for line in lines[:10]:
            if line.startswith('# '):
                # "# 1. Executive Summary" 같은 건 제외하고 기업명만 있는 경우 등 고려
                clean_header = line.replace('#', '').strip()
                # 헤더가 너무 길지 않으면 사용 (30자 이내)
                if len(clean_header) > 0 and len(clean_header) < 30:
                    return f"{sanitize_filename(clean_header)}.docx"
        
        # 2. 내용 중 '기업명', 'Target' 키워드 찾기 (단순화)
        # (구현 복잡도를 낮추기 위해 우선 헤더 기반 혹은 타임스탬프로 처리)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        return f"{default_name}_{timestamp}.docx"
    except:
        return f"{default_name}.docx"

def create_docx(markdown_text):
    """Markdown 텍스트를 Word 파일로 변환합니다 (표 및 목록 스타일 처리)."""
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
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            
            if len(table_lines) >= 2:
                headers = [c.strip() for c in table_lines[0].split('|') if c.strip()]
                data_rows = []
                for row_line in table_lines[1:]:
                    if '---' in row_line: continue
                    # 빈 셀 포함하여 파싱
                    parts = row_line.split('|')
                    if len(parts) >= 2:
                        row_data = [c.strip() for c in parts[1:-1]]
                        data_rows.append(row_data)

                if headers:
                    table = doc.add_table(rows=1, cols=len(headers))
                    table.style = 'Table Grid'
                    
                    hdr_cells = table.rows[0].cells
                    for idx, text in enumerate(headers):
                        if idx < len(hdr_cells):
                            hdr_cells[idx].text = text
                            hdr_cells[idx].paragraphs[0].runs[0].bold = True
                    
                    for row_data in data_rows:
                        row_cells = table.add_row().cells
                        for idx, text in enumerate(row_data):
                            if idx < len(row_cells):
                                # 셀 내부 텍스트 처리
                                row_cells[idx].text = text.replace('**', '')
        
        # 3. 목록(List) 처리 (요청사항 반영)
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet List 스타일 적용
            clean_text = line[2:]
            p = doc.add_paragraph(style='List Bullet')
            # 내부 Bold 처리
            parts = re.split(r'(\*\*.*?\*\*)', clean_text)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    run = p.add_run(part[2:-2])
                    run.bold = True
                else:
                    p.add_run(part)
            i += 1
            
        elif re.match(r'^\d+\.\s', line):
            # Numbered List 스타일 적용
            match = re.match(r'^\d+\.\s', line)
            clean_text = line[match.end():]
            p = doc.add_paragraph(style='List Number')
            parts = re.split(r'(\*\*.*?\*\*)', clean_text)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    run = p.add_run(part[2:-2])
                    run.bold = True
                else:
                    p.add_run(part)
            i += 1

        # 4. 일반 텍스트
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
        df = pd.DataFrame(data[1:], columns=data[0])
        with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='RFI_List')
    
    return bio.getvalue()
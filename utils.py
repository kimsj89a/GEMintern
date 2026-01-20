import io
import re
import os
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from pptx import Presentation

def parse_uploaded_file(uploaded_file):
    """파일 타입별 텍스트 추출 (고속 라이브러리 사용)"""
    if uploaded_file is None:
        return ""
        
    file_type = uploaded_file.name.split('.')[-1].lower()
    text_content = ""

    try:
        # [PDF] PyMuPDF (Fast)
        if file_type == 'pdf':
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                for page in doc:
                    text_content += page.get_text() + "\n"
        
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
        
        # [Excel] pandas + calamine
        elif file_type in ['xlsx', 'xls', 'csv']:
            if file_type == 'csv':
                df = pd.read_csv(uploaded_file)
            else:
                try:
                    df = pd.read_excel(uploaded_file, engine='calamine')
                except:
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

    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)

    return f"=== 파일명: {uploaded_file.name} ===\n{text_content}\n\n"

def generate_filename(uploaded_files, template_option):
    """[파일명]_[서식명] 규칙으로 파일명 생성"""
    template_map = {
        'simple_review': '약식투자검토',
        'rfi': 'RFI',
        'investment': '투자심사보고서',
        'im': 'IM',
        'management': '사후관리보고서',
        'presentation': '발표자료',
        'custom': '보고서'
    }
    suffix = template_map.get(template_option, '보고서')

    project_name = "Investment_Report" 
    if uploaded_files:
        first_file = uploaded_files[0].name
        base_name = os.path.splitext(first_file)[0]
        project_name = re.sub(r'[\\/*?:"<>|]', "", base_name).strip()
    
    return f"{project_name}_{suffix}.docx"

def set_list_level(paragraph, level):
    """Word 목록의 들여쓰기 수준(Level) 설정 (핵심 로직)"""
    # 1. pPr(Paragraph Properties) 가져오기
    pPr = paragraph._p.get_or_add_pPr()
    
    # 2. numPr(Numbering Properties) 설정
    numPr = pPr.get_or_add_numPr()
    
    # 3. ilvl(Indent Level) 설정 (0, 1, 2...)
    ilvl = numPr.get_or_add_ilvl()
    ilvl.val = level
    
    # 4. numId 설정 (Word의 기본 리스트 정의에 연결)
    # numId가 없으면 강제로 1번(통상 Bullet)이나 2번(Number)을 할당해야 보임
    if numPr.numId is None:
        numId = numPr.get_or_add_numId()
        # 스타일 이름에 따라 ID 배정이 다르지만, 여기선 강제로 연결 시도
        numId.val = 1 

def create_docx(markdown_text):
    """Markdown -> Word 변환 (Multilevel Bullet 적용)"""
    doc = Document()
    
    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()
        
        # 1. 헤더
        if line.startswith('# '):
            doc.add_heading(line.replace('# ', ''), level=1)
            i += 1
        elif line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=2)
            i += 1
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=3)
            i += 1
            
        # 2. 표
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
                    if len(parts) >= 2:
                        data_rows.append([c.strip() for c in parts[1:-1]])

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
                            if idx < len(row_cells):
                                row_cells[idx].text = text.replace('**', '')

        # 3. 목록 (Multilevel Bullet/Numbering)
        elif re.match(r'^\s*([-*]|\d+\.)\s', raw_line):
            match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)', raw_line)
            if match:
                indent_str, marker, content = match.groups()
                
                # 레벨 계산: 공백 2개 = 1레벨
                spaces = indent_str.replace('\t', '  ')
                level = len(spaces) // 2
                if level > 8: level = 8

                # 스타일 결정 (List Bullet / List Number)
                is_bullet = marker in ['-', '*']
                style_name = 'List Bullet' if is_bullet else 'List Number'
                
                try:
                    p = doc.add_paragraph(style=style_name)
                except:
                    # 스타일이 없을 경우 기본 스타일 사용
                    p = doc.add_paragraph()
                
                # [핵심] 다단계 들여쓰기 적용
                set_list_level(p, level)

                # 내용 작성 (Bold 처리)
                parts = re.split(r'(\*\*.*?\*\*)', content)
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
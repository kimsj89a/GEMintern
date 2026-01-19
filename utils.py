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

    # 파일 포인터 초기화
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)

    return f"=== 파일명: {uploaded_file.name} ===\n{text_content}\n\n"

def generate_filename(uploaded_files, template_option):
    """
    [파일명]_[서식명] 규칙으로 파일명을 생성합니다.
    예: 'Samsung_IR.pdf' + 'simple_review' -> 'Samsung_IR_약식투자검토.docx'
    """
    # 1. 서식명 매핑
    template_map = {
        'simple_review': '약식투자검토',
        'rfi': 'RFI',
        'investment': '투자심사보고서',
        'im': 'IM',
        'management': '사후관리보고서',
        'custom': '보고서'
    }
    suffix = template_map.get(template_option, '보고서')

    # 2. 프로젝트명 추출 (첫 번째 파일명 기준)
    project_name = "Investment_Report" # 기본값
    if uploaded_files:
        # 확장자 제거
        first_file = uploaded_files[0].name
        base_name = os.path.splitext(first_file)[0]
        # 특수문자 제거 (파일명 안전하게)
        project_name = re.sub(r'[\\/*?:"<>|]', "", base_name).strip()
    
    return f"{project_name}_{suffix}.docx"

def set_list_level(paragraph, level):
    """
    Word 목록의 들여쓰기 수준(Level)을 강제로 설정합니다.
    level 0: ●, level 1: ○, level 2: ■ ... (Word 스타일에 따름)
    """
    pPr = paragraph._p.get_or_add_pPr()
    numPr = pPr.get_or_add_numPr()
    
    # 레벨 설정 (ilvl)
    ilvl = numPr.get_or_add_ilvl()
    ilvl.val = level
    
    # numId가 없으면 추가 (워드 기본 불렛 리스트 연결 시도)
    if numPr.numId is None:
        numId = numPr.get_or_add_numId()
        numId.val = 1 

def create_docx(markdown_text):
    """Markdown -> Word 변환 (Bullet Level 완벽 지원)"""
    doc = Document()
    
    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        # 원본 라인 (들여쓰기 계산용)
        raw_line = lines[i]
        line = raw_line.strip()
        
        # 1. 헤더 (#)
        if line.startswith('# '):
            doc.add_heading(line.replace('# ', ''), level=1)
            i += 1
        elif line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=2)
            i += 1
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=3)
            i += 1
            
        # 2. 표 (|...|)
        elif line.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            
            if len(table_lines) >= 2:
                # 헤더 파싱
                headers = [c.strip() for c in table_lines[0].split('|') if c.strip()]
                data_rows = []
                for row_line in table_lines[1:]:
                    if '---' in row_line: continue
                    parts = row_line.split('|')
                    if len(parts) >= 2:
                        row_data = [c.strip() for c in parts[1:-1]]
                        data_rows.append(row_data)

                if headers:
                    table = doc.add_table(rows=1, cols=len(headers))
                    table.style = 'Table Grid'
                    
                    # 헤더 스타일
                    hdr_cells = table.rows[0].cells
                    for idx, text in enumerate(headers):
                        if idx < len(hdr_cells):
                            hdr_cells[idx].text = text
                            for run in hdr_cells[idx].paragraphs[0].runs:
                                run.bold = True
                                
                    # 데이터 입력
                    for row_data in data_rows:
                        row_cells = table.add_row().cells
                        for idx, text in enumerate(row_data):
                            if idx < len(row_cells):
                                row_cells[idx].text = text.replace('**', '')

        # 3. 목록 (Bullet/Numbering with Levels)
        # 예: "- 항목", "  - 하위항목", "1. 항목"
        elif re.match(r'^\s*([-*]|\d+\.)\s', raw_line):
            match = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)', raw_line)
            if match:
                indent_str, marker, content = match.groups()
                
                # 레벨 계산: 공백 2개당 1레벨 (탭은 2칸으로 간주)
                spaces = indent_str.replace('\t', '  ')
                level = len(spaces) // 2
                if level > 8: level = 8 

                # 스타일 선택
                is_bullet = marker in ['-', '*']
                style_name = 'List Bullet' if is_bullet else 'List Number'
                
                # 문단 추가
                try:
                    p = doc.add_paragraph(style=style_name)
                except:
                    p = doc.add_paragraph() # Fallback
                
                # 레벨 적용
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
    """Markdown 표 -> Excel 변환"""
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
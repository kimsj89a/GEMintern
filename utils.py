import io
import re
import pandas as pd
from pypdf import PdfReader
from docx import Document
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
    """
    Markdown 텍스트를 Word 파일로 변환합니다.
    Header(#) 및 Bold(**) 처리를 지원합니다.
    """
    doc = Document()
    
    # 빈 줄 제외하고 처리
    lines = [line for line in markdown_text.split('\n') if line.strip() != '']
    
    for line in lines:
        line = line.strip()
        
        # 1. 헤더 처리
        if line.startswith('# '):
            doc.add_heading(line.replace('# ', ''), level=1)
        elif line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=2)
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=3)
        
        # 2. 본문 및 Bold 처리
        else:
            p = doc.add_paragraph()
            # 정규표현식으로 **...** 패턴 분리 (캡처 그룹 사용으로 구분자도 포함됨)
            parts = re.split(r'(\*\*.*?\*\*)', line)
            
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    # 굵게 적용 (앞뒤 ** 제거)
                    text = part[2:-2]
                    run = p.add_run(text)
                    run.bold = True
                else:
                    # 일반 텍스트
                    if part: # 빈 문자열 제외
                        p.add_run(part)
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()
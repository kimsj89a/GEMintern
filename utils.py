import io
import pandas as pd
from pypdf import PdfReader
from docx import Document
from pptx import Presentation

def parse_uploaded_file(uploaded_file):
    """업로드된 파일의 타입에 따라 텍스트를 추출합니다."""
    file_type = uploaded_file.name.split('.')[-1].lower()
    text_content = ""

    try:
        if file_type == 'pdf':
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
        
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
    """생성된 텍스트를 Word 파일 바이너리로 변환합니다 (간이 버전)."""
    doc = Document()
    for line in markdown_text.split('\n'):
        if line.startswith('# '):
            doc.add_heading(line.replace('# ', ''), level=1)
        elif line.startswith('## '):
            doc.add_heading(line.replace('## ', ''), level=2)
        elif line.startswith('### '):
            doc.add_heading(line.replace('### ', ''), level=3)
        else:
            doc.add_paragraph(line)
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()
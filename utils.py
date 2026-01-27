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

# Gemini Vision OCR 吏??(google-genai ?⑦궎吏 ?꾩슂)
OCR_AVAILABLE = False
OCR_ERROR_MSG = ""

try:
    from google import genai
    from google.genai import types
    OCR_AVAILABLE = True
except ImportError:
    OCR_ERROR_MSG = "google-genai ?⑦궎吏媛 ?ㅼ튂?섏? ?딆븯?듬땲??"

# MarkItDown 吏???뺤씤
MARKITDOWN_AVAILABLE = False
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    pass

# Document AI OCR 吏???뺤씤
DOCAI_AVAILABLE = False
try:
    import utils_docai
    DOCAI_AVAILABLE = True
except ImportError:
    pass

def get_ocr_status():
    """OCR ?곹깭 ?뺤씤 (UI?먯꽌 ?ъ슜)"""
    if OCR_AVAILABLE:
        return True, "Gemini Vision OCR ?ъ슜 媛??(API ???꾩슂)"
    return False, OCR_ERROR_MSG


def extract_pdf_with_gemini_ocr(doc, api_key, ocr_threshold=50):
    """
    PDF?먯꽌 ?띿뒪??異붿텧 (Gemini Vision OCR ?대갚)

    Args:
        doc: fitz.Document 媛앹껜
        api_key: Google API ??
        ocr_threshold: ?섏씠吏????湲?먯닔 誘몃쭔?대㈃ OCR ?ㅽ뻾

    Returns:
        異붿텧???띿뒪??
    """
    text_content = ""
    ocr_used = False
    ocr_pages = []

    # 1?④퀎: ?쇰컲 ?띿뒪??異붿텧 諛?OCR ?꾩슂 ?섏씠吏 ?섏쭛
    for page_num, page in enumerate(doc):
        page_text = page.get_text().strip()

        if len(page_text) < ocr_threshold:
            # OCR???꾩슂???섏씠吏 - ?대?吏濡?蹂??
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x ?댁긽??
            img_bytes = pix.tobytes("png")
            ocr_pages.append((page_num, img_bytes, page_text))
        else:
            text_content += f"[Page {page_num + 1}]\n{page_text}\n\n"

    # 2?④퀎: OCR ?꾩슂 ?섏씠吏媛 ?덇퀬 API ?ㅺ? ?덉쑝硫?Gemini OCR ?ㅽ뻾
    if ocr_pages and api_key and OCR_AVAILABLE:
        try:
            client = genai.Client(api_key=api_key)

            for page_num, img_bytes, original_text in ocr_pages:
                try:
                    # Gemini Vision API ?몄텧
                    response = client.models.generate_content(
                        model="gemini-2.0-flash-exp",
                        contents=[
                            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                            "???대?吏?먯꽌 紐⑤뱺 ?띿뒪?몃? 異붿텧?댁＜?몄슂. ?먮낯 ?덉씠?꾩썐??理쒕????좎??섍퀬, ?띿뒪?몃쭔 諛섑솚?댁＜?몄슂. 異붽? ?ㅻ챸 ?놁씠 ?띿뒪?몃쭔 異쒕젰?섏꽭??"
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
                    # 媛쒕퀎 ?섏씠吏 OCR ?ㅽ뙣 ???먮낯 ?좎?
                    text_content += f"[Page {page_num + 1}]\n{original_text}\n\n"

        except Exception:
            # API ?곌껐 ?ㅽ뙣 ???먮낯 ?띿뒪?몃줈 ?泥?
            for page_num, _, original_text in ocr_pages:
                text_content += f"[Page {page_num + 1}]\n{original_text}\n\n"
    else:
        # OCR 遺덇??????먮낯 ?띿뒪???ъ슜
        for page_num, _, original_text in ocr_pages:
            text_content += f"[Page {page_num + 1}]\n{original_text}\n\n"

    # OCR ?ъ슜 ?щ? ?쒖떆
    if ocr_used:
        text_content = "[Gemini Vision OCR ?곸슜??\n\n" + text_content

    return text_content


# ?덇굅???명솚??(API ???놁씠 ?몄텧 ??
def extract_pdf_with_ocr(doc):
    """?덇굅???명솚 - API ???놁씠 ?몄텧 ???쇰컲 ?띿뒪?몃쭔 異붿텧"""
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
    """?뚯씪 ??낅퀎 ?띿뒪??異붿텧 (?꾩껜 ?쒗듃 吏??+ OCR 吏??

    Args:
        uploaded_file: Streamlit ?낅줈???뚯씪 媛앹껜
        api_key: Google API ??(PDF OCR?? ?좏깮?ы빆)
        docai_config: Document AI ?ㅼ젙 dict (?좏깮?ы빆)
            - project_id: GCP ?꾨줈?앺듃 ID
            - location: ?꾩튂 (us/eu)
            - processor_id: ?꾨줈?몄꽌 ID
            - credentials_json: ?쒕퉬??怨꾩젙 JSON 臾몄옄??
    """
    if uploaded_file is None:
        return ""

    file_type = uploaded_file.name.split('.')[-1].lower()

    # [Document AI OCR] PDF/?대?吏 ?곗꽑 泥섎━
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
                return f"### [?뚯씪紐? {uploaded_file.name} (Document AI OCR)]\n{ocr_result['text']}\n\n"
        except Exception as e:
            uploaded_file.seek(0)
            # Document AI ?ㅽ뙣 ???ㅼ쓬 諛⑸쾿?쇰줈 吏꾪뻾

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
                    return f"### [?뚯씪紐? {uploaded_file.name} (MarkItDown)]\n{result.text_content}\n\n"
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
        
        # [Excel] pandas (?꾩껜 ?쒗듃 ?뚯떛 ?곸슜)
        elif file_type in ['xlsx', 'xls', 'csv']:
            try:
                text_content = f"### [?뚯씪紐? {uploaded_file.name}]\n"
                
                # 1. ?뚯씪 ?쎄린 (CSV vs Excel)
                if file_type == 'csv':
                    df = pd.read_csv(uploaded_file)
                    df = df.fillna("")
                    try:
                        table_text = df.to_markdown(index=False)
                    except ImportError:
                        table_text = df.to_string(index=False)
                    text_content += f"\n{table_text}\n"
                else:
                    # [?듭떖 蹂寃? sheet_name=None?쇰줈 ?ㅼ젙?섏뿬 紐⑤뱺 ?쒗듃瑜?OrderedDict濡??쎌뼱??
                    # ?붿쭊? openpyxl??紐낆떆?곸쑝濡??ъ슜 (?덉젙??
                    xls_dict = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')
                    
                    # 紐⑤뱺 ?쒗듃 ?쒗쉶
                    for sheet_name, df in xls_dict.items():
                        df = df.fillna("") # 鍮덇컪 泥섎━
                        
                        # ?쒗듃蹂??ㅻ뜑 異붽?
                        text_content += f"\n#### [Sheet: {sheet_name}]\n"
                        
                        # 蹂??(tabulate媛 ?놁쑝硫?to_string?쇰줈 ?泥?
                        try:
                            table_text = df.to_markdown(index=False)
                        except ImportError:
                            table_text = df.to_string(index=False)
                        
                        text_content += f"{table_text}\n"

            except Exception as e:
                text_content = f"[?묒? ?뚯떛 ?ㅻ쪟: {str(e)}]\n(Tip: ?뷀샇 嫄몃┛ ?뚯씪? ?꾨땶吏, ?щ㎎??留욌뒗吏 ?뺤씤?댁＜?몄슂)"
        
        # [Text]
        elif file_type in ['txt', 'md']:
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            text_content = stringio.read()
            
        else:
            text_content = f"[吏?먰븯吏 ?딅뒗 ?뚯씪 ?뺤떇?낅땲?? {uploaded_file.name}]"

    except Exception as e:
        return f"[?뚯씪 ?쎄린 移섎챸???ㅻ쪟: {uploaded_file.name} - {str(e)}]"

    # ?뚯씪 ?ъ씤??珥덇린??
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
    """?ㅼ뿬?곌린媛 ?곸슜??由ъ뒪????ぉ 異붽?

    Args:
        doc: Document 媛앹껜
        content: ?띿뒪???댁슜
        level: ?ㅼ뿬?곌린 ?섏? (0遺???쒖옉)
        is_bullet: True硫?遺덈┸, False硫?踰덊샇
    """

    # Bullet characters by level (fallback to simple ASCII bullets)
    bullet_chars = ["-", "*", "+"]
    bullet_char = bullet_chars[level % len(bullet_chars)]

    p = doc.add_paragraph()

    # ?ㅼ뿬?곌린 ?ㅼ젙 (?섏???0.1?몄튂)
    indent = Inches(0.1 * (level + 1))
    p.paragraph_format.left_indent = indent
    p.paragraph_format.first_line_indent = Inches(-0.15)  # 遺덈┸/踰덊샇 hanging indent

    # 遺덈┸ 臾몄옄 異붽?
    if is_bullet:
        p.add_run(f"{bullet_char} ")
    else:
        p.add_run(f"??")  # 踰덊샇 由ъ뒪?몃룄 ?쇰떒 遺덈┸?쇰줈

    # ?댁슜 異붽? (蹂쇰뱶 泥섎━ ?ы븿)
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

    # 濡쒕쭏 ?レ옄 ?ㅻ뜑 ?⑦꽩 (I., II., III., IV., V., VI., VII., VIII.)
    roman_header_pattern = re.compile(r'^(I{1,3}|IV|VI{0,3}|V|IX|X)\.\s+(.+)$')

    # 由ъ뒪??level 異붿쟻 (?ㅼ뿬?곌린 ?ㅽ깮)
    indent_stack = [0]  # 媛?level???ㅼ뿬?곌린 ?????

    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()

        # Markdown ?ㅻ뜑 泥섎━ (#### 異붽?)
        if line.startswith('##### '):
            doc.add_heading(line.replace('##### ', ''), level=5)
            indent_stack = [0]  # 由ъ뒪???ㅽ깮 由ъ뀑
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
        # 濡쒕쭏 ?レ옄 ?ㅻ뜑 泥섎━ (I. Executive Summary ??
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
                spaces = indent_str.replace('\t', '    ')  # ??쓣 4移몄쑝濡?
                indent_len = len(spaces)

                # ?ㅼ뿬?곌린 湲곕컲 level 怨꾩궛 (?쒖감?곸쑝濡?1, 2, 3...)
                if indent_len == 0:
                    level = 0
                    indent_stack = [0]
                elif indent_len > indent_stack[-1]:
                    # ?ㅼ뿬?곌린 利앷? ??level 利앷?
                    level = len(indent_stack)
                    indent_stack.append(indent_len)
                else:
                    # ?ㅼ뿬?곌린 媛먯냼 ?먮뒗 ?좎? ???대떦 level 李얘린
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

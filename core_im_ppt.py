"""
IM PPT 변환 엔진
마크다운 형식의 IM 보고서를 16:9 PPT로 변환
"""

import io
import re
import datetime
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# --- 디자인 상수 (IM Theme) ---
COLOR_PRIMARY = RGBColor(30, 58, 138)      # Dark Navy
COLOR_ACCENT = RGBColor(0, 104, 201)       # Blue
COLOR_WHITE = RGBColor(255, 255, 255)
COLOR_BLACK = RGBColor(0, 0, 0)
COLOR_DARK_GREY = RGBColor(80, 80, 80)
COLOR_MID_GREY = RGBColor(128, 128, 128)
COLOR_LIGHT_GREY = RGBColor(240, 240, 240)
COLOR_TABLE_HEADER = RGBColor(30, 58, 138)
COLOR_TABLE_ALT = RGBColor(245, 247, 250)
COLOR_CHART_BG = RGBColor(230, 230, 230)

DEFAULT_FONT = "Malgun Gothic"

# 16:9 슬라이드 크기
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


def clean_text(text):
    """Markdown 문법 제거."""
    text = text.replace('**', '').replace('*', '')
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # links
    return text.strip()


def _set_font(run, size, bold=False, color=None, font_name=DEFAULT_FONT):
    """폰트 설정 헬퍼."""
    run.font.name = font_name
    run.font.size = size
    run.font.bold = bold
    if color:
        run.font.color.rgb = color


def _set_paragraph_font(paragraph, size, bold=False, color=None, font_name=DEFAULT_FONT):
    """Paragraph 레벨 폰트 설정."""
    for run in paragraph.runs:
        _set_font(run, size, bold, color, font_name)
    paragraph.font.name = font_name
    paragraph.font.size = size
    paragraph.font.bold = bold
    if color:
        paragraph.font.color.rgb = color


def _add_footer(slide, section_label="", page_num=0):
    """슬라이드 하단 footer: 'Private & Confidential' + 페이지 번호."""
    # Footer line
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.5), Inches(7.0), Inches(12.333), Emu(12700)  # 1pt line
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_MID_GREY
    line.line.fill.background()

    # Confidential text (left)
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(7.05), Inches(4), Inches(0.35))
    p = tb.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = "Private & Confidential"
    _set_font(run, Pt(8), color=COLOR_MID_GREY)

    # Page number (right)
    if page_num > 0:
        tb2 = slide.shapes.add_textbox(Inches(11.5), Inches(7.05), Inches(1.333), Inches(0.35))
        p2 = tb2.text_frame.paragraphs[0]
        p2.alignment = PP_ALIGN.RIGHT
        run2 = p2.add_run()
        run2.text = str(page_num)
        _set_font(run2, Pt(8), color=COLOR_MID_GREY)


def _add_section_label(slide, section_label):
    """슬라이드 좌상단 섹션 라벨."""
    if not section_label:
        return
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(5), Inches(0.3))
    p = tb.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = section_label
    _set_font(run, Pt(9), bold=True, color=COLOR_ACCENT)


def _create_cover_slide(prs, project_name, gp_name, date_str):
    """표지 슬라이드."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank

    # Full background
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_PRIMARY
    bg.line.fill.background()

    # Accent bar
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8), Inches(3.2), Inches(1.5), Emu(38100)  # 3pt
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_WHITE
    bar.line.fill.background()

    # Project name
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11), Inches(1.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = project_name if project_name else "Information Memorandum"
    _set_font(run, Pt(36), bold=True, color=COLOR_WHITE)

    # Subtitle
    tb2 = slide.shapes.add_textbox(Inches(0.8), Inches(3.5), Inches(11), Inches(0.6))
    p2 = tb2.text_frame.paragraphs[0]
    run2 = p2.add_run()
    run2.text = "Information Memorandum"
    _set_font(run2, Pt(20), color=RGBColor(180, 198, 231))

    # GP name
    if gp_name:
        tb3 = slide.shapes.add_textbox(Inches(0.8), Inches(5.5), Inches(11), Inches(0.5))
        p3 = tb3.text_frame.paragraphs[0]
        run3 = p3.add_run()
        run3.text = gp_name
        _set_font(run3, Pt(14), color=COLOR_WHITE)

    # Date
    if not date_str:
        date_str = datetime.date.today().strftime("%Y년 %m월")
    tb4 = slide.shapes.add_textbox(Inches(0.8), Inches(6.0), Inches(11), Inches(0.5))
    p4 = tb4.text_frame.paragraphs[0]
    run4 = p4.add_run()
    run4.text = date_str
    _set_font(run4, Pt(14), color=RGBColor(180, 198, 231))

    # Confidential
    tb5 = slide.shapes.add_textbox(Inches(0.8), Inches(6.5), Inches(11), Inches(0.4))
    p5 = tb5.text_frame.paragraphs[0]
    run5 = p5.add_run()
    run5.text = "CONFIDENTIAL"
    _set_font(run5, Pt(10), color=RGBColor(150, 170, 210))

    return slide


def _create_disclaimer_slide(prs):
    """Disclaimer 슬라이드."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = "Disclaimer"
    _set_font(run, Pt(28), bold=True, color=COLOR_PRIMARY)

    # Line
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8), Inches(1.3), Inches(11.5), Emu(19050)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_PRIMARY
    line.line.fill.background()

    # Disclaimer text
    disclaimer_text = (
        "본 자료는 정보 제공 목적으로만 작성되었으며, 투자 권유를 구성하지 않습니다.\n\n"
        "본 자료에 포함된 정보는 신뢰할 수 있다고 판단되는 자료에 기초하였으나, "
        "그 정확성이나 완전성에 대해 보증하지 않습니다.\n\n"
        "본 자료는 기밀 정보를 포함하고 있으며, 수신자의 사전 서면 동의 없이 "
        "제3자에게 공개, 복사, 배포할 수 없습니다.\n\n"
        "투자에는 원금 손실의 위험이 있으며, 과거 실적이 미래 수익을 보장하지 않습니다.\n\n"
        "본 자료에 포함된 미래 전망에 관한 진술은 현재 시점의 추정치이며, "
        "실제 결과는 다양한 요인에 의해 달라질 수 있습니다."
    )
    tb2 = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.5), Inches(5.0))
    tf = tb2.text_frame
    tf.word_wrap = True
    p2 = tf.paragraphs[0]
    run2 = p2.add_run()
    run2.text = disclaimer_text
    _set_font(run2, Pt(11), color=COLOR_DARK_GREY)
    p2.line_spacing = Pt(18)

    _add_footer(slide, "", 1)
    return slide


def _create_section_divider(prs, section_num, section_title, page_num=0):
    """섹션 간지 슬라이드."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Background
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT)
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_PRIMARY
    bg.line.fill.background()

    # Section number (large)
    if section_num:
        tb_num = slide.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11), Inches(1.0))
        p_num = tb_num.text_frame.paragraphs[0]
        run_num = p_num.add_run()
        run_num.text = section_num
        _set_font(run_num, Pt(48), bold=True, color=RGBColor(180, 198, 231))

    # Accent bar
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8), Inches(3.2), Inches(2.0), Emu(38100)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = COLOR_WHITE
    bar.line.fill.background()

    # Section title
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(3.5), Inches(11), Inches(1.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = clean_text(section_title)
    _set_font(run, Pt(32), bold=True, color=COLOR_WHITE)

    return slide


def _create_content_slide(prs, title, items, section_label="", page_num=0):
    """일반 콘텐츠 슬라이드."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Section label
    _add_section_label(slide, section_label)

    # Title bar background
    title_bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0.45), SLIDE_WIDTH, Inches(0.6)
    )
    title_bg.fill.solid()
    title_bg.fill.fore_color.rgb = COLOR_LIGHT_GREY
    title_bg.line.fill.background()

    # Title text
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = clean_text(title)
    _set_font(run, Pt(20), bold=True, color=COLOR_PRIMARY)

    # Accent line under title
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.5), Inches(1.1), Inches(12.333), Emu(19050)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_ACCENT
    line.line.fill.background()

    # Content area
    content_top = Inches(1.3)
    content_height = Inches(5.5)

    if items:
        tb2 = slide.shapes.add_textbox(
            Inches(0.5), content_top, Inches(12.333), content_height
        )
        tf = tb2.text_frame
        tf.word_wrap = True

        for i, item in enumerate(items):
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()

            cleaned = clean_text(item)

            # Sub-heading (###)
            if item.strip().startswith('### '):
                run = p.add_run()
                run.text = cleaned.replace('### ', '')
                _set_font(run, Pt(14), bold=True, color=COLOR_PRIMARY)
                p.space_before = Pt(12)
                p.space_after = Pt(4)
            elif item.strip().startswith('- ') or item.strip().startswith('* '):
                text = cleaned.lstrip('- ').lstrip('* ')
                # Check for bold prefix (key: value pattern)
                bold_match = re.match(r'^([^:]+):\s*(.+)$', text)
                if bold_match:
                    run_bold = p.add_run()
                    run_bold.text = bold_match.group(1) + ": "
                    _set_font(run_bold, Pt(11), bold=True, color=COLOR_BLACK)
                    run_normal = p.add_run()
                    run_normal.text = bold_match.group(2)
                    _set_font(run_normal, Pt(11), color=COLOR_DARK_GREY)
                else:
                    run = p.add_run()
                    run.text = "  •  " + text
                    _set_font(run, Pt(11), color=COLOR_DARK_GREY)
                p.space_before = Pt(3)
                p.space_after = Pt(3)
            else:
                run = p.add_run()
                run.text = cleaned
                _set_font(run, Pt(11), color=COLOR_DARK_GREY)
                p.space_before = Pt(2)
                p.space_after = Pt(2)

    _add_footer(slide, section_label, page_num)
    return slide


def _create_table_slide(prs, title, table_data, section_label="", page_num=0):
    """테이블 슬라이드."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    _add_section_label(slide, section_label)

    # Title
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = clean_text(title)
    _set_font(run, Pt(20), bold=True, color=COLOR_PRIMARY)

    # Line
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.5), Inches(1.1), Inches(12.333), Emu(19050)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_ACCENT
    line.line.fill.background()

    if not table_data or len(table_data) < 2:
        _add_footer(slide, section_label, page_num)
        return slide

    rows = len(table_data)
    cols = len(table_data[0])
    # Limit table size
    cols = min(cols, 8)
    rows = min(rows, 15)

    table_width = Inches(12.333)
    table_height = Inches(min(rows * 0.4, 5.5))
    table_shape = slide.shapes.add_table(
        rows, cols,
        Inches(0.5), Inches(1.3),
        table_width, table_height
    )
    table = table_shape.table

    # Set column widths proportionally
    col_width = int(table_width / cols)
    for c in range(cols):
        table.columns[c].width = col_width

    for r in range(min(rows, len(table_data))):
        for c in range(min(cols, len(table_data[r]))):
            cell = table.cell(r, c)
            cell.text = clean_text(table_data[r][c])

            # Style
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.name = DEFAULT_FONT
                paragraph.font.size = Pt(9)
                if r == 0:
                    paragraph.font.bold = True
                    paragraph.font.color.rgb = COLOR_WHITE
                else:
                    paragraph.font.color.rgb = COLOR_DARK_GREY

            # Cell background
            if r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLOR_TABLE_HEADER
            elif r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLOR_TABLE_ALT

    _add_footer(slide, section_label, page_num)
    return slide


def _create_chart_placeholder(prs, title, chart_desc, section_label="", page_num=0):
    """차트 placeholder 슬라이드."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    _add_section_label(slide, section_label)

    # Title
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = clean_text(title)
    _set_font(run, Pt(20), bold=True, color=COLOR_PRIMARY)

    # Chart placeholder box
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(1.5), Inches(1.5), Inches(10.333), Inches(4.5)
    )
    box.fill.solid()
    box.fill.fore_color.rgb = COLOR_CHART_BG
    box.line.color.rgb = COLOR_MID_GREY
    box.line.width = Pt(1)

    # Chart description text
    tb2 = slide.shapes.add_textbox(Inches(2.5), Inches(3.0), Inches(8), Inches(1.5))
    tf = tb2.text_frame
    tf.word_wrap = True
    p2 = tf.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = f"[Chart Placeholder]\n{clean_text(chart_desc)}"
    _set_font(run2, Pt(14), color=COLOR_MID_GREY)

    _add_footer(slide, section_label, page_num)
    return slide


def _parse_table(lines):
    """마크다운 테이블 라인들을 2D 배열로 파싱."""
    table_data = []
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        # Skip separator row (| --- | --- |)
        if re.match(r'^\|[\s\-:]+\|', line):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if cells:
            table_data.append(cells)
    return table_data


def _extract_section_num(title):
    """제목에서 섹션 번호 추출. 예: 'I. Executive Summary' -> 'I'"""
    match = re.match(r'^([IVX]+\.?|[0-9]+\.?)\s', title.strip())
    if match:
        return match.group(1).rstrip('.')
    return ""


def create_im_ppt(markdown_text, project_name="", gp_name="", date_str=""):
    """
    IM 마크다운을 PPT로 변환하는 메인 함수.

    Args:
        markdown_text: 마크다운 형식의 IM 텍스트
        project_name: 프로젝트명 (표지용)
        gp_name: GP사명 (표지용)
        date_str: 날짜 (표지용)

    Returns:
        bytes: PPT 파일 바이트
    """
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    # Cover slide
    _create_cover_slide(prs, project_name, gp_name, date_str)

    # Disclaimer slide
    _create_disclaimer_slide(prs)

    page_num = 2
    current_section_label = ""
    current_slide_title = ""
    current_items = []
    is_first_h1 = True

    lines = markdown_text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and horizontal rules
        if not stripped or stripped == '---':
            i += 1
            continue

        # H1: Cover (first) or Section divider (subsequent)
        if stripped.startswith('# ') and not stripped.startswith('## '):
            # Flush current slide
            if current_slide_title and current_items:
                page_num += 1
                _create_content_slide(prs, current_slide_title, current_items,
                                     current_section_label, page_num)
                current_items = []
                current_slide_title = ""

            h1_text = stripped[2:].strip()

            if is_first_h1:
                # Skip - already created cover slide
                is_first_h1 = False
            else:
                # Section divider
                section_num = _extract_section_num(h1_text)
                section_title = re.sub(r'^[IVX]+\.?\s*|^[0-9]+\.?\s*', '', h1_text).strip()
                page_num += 1
                _create_section_divider(prs, section_num, section_title or h1_text, page_num)

            current_section_label = h1_text
            i += 1
            continue

        # H2: New content slide
        if stripped.startswith('## '):
            # Flush previous slide
            if current_slide_title and current_items:
                page_num += 1
                _create_content_slide(prs, current_slide_title, current_items,
                                     current_section_label, page_num)
                current_items = []

            current_slide_title = stripped[3:].strip()
            i += 1
            continue

        # Table detection
        if stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1

            table_data = _parse_table(table_lines)
            if table_data and len(table_data) >= 2:
                # Flush any pending items as a content slide first
                if current_items:
                    page_num += 1
                    _create_content_slide(prs, current_slide_title, current_items,
                                         current_section_label, page_num)
                    current_items = []

                page_num += 1
                _create_table_slide(prs, current_slide_title, table_data,
                                   current_section_label, page_num)
                current_slide_title = ""  # Reset after table
            continue

        # Chart placeholder
        chart_match = re.match(r'\[차트:\s*(.+?)\]', stripped)
        if chart_match:
            if current_items:
                page_num += 1
                _create_content_slide(prs, current_slide_title, current_items,
                                     current_section_label, page_num)
                current_items = []

            page_num += 1
            _create_chart_placeholder(prs, current_slide_title, chart_match.group(1),
                                     current_section_label, page_num)
            i += 1
            continue

        # Regular content (bullets, sub-headings, text)
        current_items.append(stripped)
        i += 1

    # Flush last slide
    if current_slide_title and current_items:
        page_num += 1
        _create_content_slide(prs, current_slide_title, current_items,
                             current_section_label, page_num)

    # Save to bytes
    output = io.BytesIO()
    prs.save(output)
    return output.getvalue()

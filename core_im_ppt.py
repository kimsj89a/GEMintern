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
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

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


def _detect_chart_type(chart_desc):
    """차트 설명에서 차트 타입 추론."""
    desc_lower = chart_desc.lower()
    if any(k in desc_lower for k in ['pie', '파이', '비중', '구성비', '비율']):
        return 'pie'
    if any(k in desc_lower for k in ['line', '추이', '추세', '변화', '성장', 'trend', 'growth']):
        return 'line'
    return 'bar'


_CHART_TYPE_MAP = {
    'bar': XL_CHART_TYPE.COLUMN_CLUSTERED,
    'line': XL_CHART_TYPE.LINE_MARKERS,
    'pie': XL_CHART_TYPE.PIE,
}

_CHART_COLORS = [
    RGBColor(30, 58, 138), RGBColor(204, 160, 0), RGBColor(0, 104, 201),
    RGBColor(0, 128, 0), RGBColor(91, 44, 140), RGBColor(217, 119, 6),
]


def _create_chart_slide(prs, title, chart_desc, table_data=None,
                        section_label="", page_num=0):
    """차트 슬라이드 — 선행 테이블 데이터가 있으면 실제 차트, 없으면 스타일 플레이스홀더."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_section_label(slide, section_label)

    # Title
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(0.5))
    p = tb.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = clean_text(title)
    _set_font(run, Pt(20), bold=True, color=COLOR_PRIMARY)

    # Line under title
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.5), Inches(1.1), Inches(12.333), Emu(19050)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_ACCENT
    line.line.fill.background()

    chart_type = _detect_chart_type(chart_desc)

    # Try to create a real chart from preceding table data
    if table_data and len(table_data) >= 2:
        categories, series_list = _table_to_chart_data(table_data, chart_type)
        if categories and series_list:
            xl_type = _CHART_TYPE_MAP.get(chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)
            chart_data = CategoryChartData()
            chart_data.categories = categories
            for s in series_list:
                chart_data.add_series(s['name'], s['values'])

            chart_frame = slide.shapes.add_chart(
                xl_type,
                Inches(1.0), Inches(1.3), Inches(11.333), Inches(4.8),
                chart_data
            )
            chart = chart_frame.chart
            chart.has_legend = len(series_list) > 1
            if chart.has_legend:
                chart.legend.include_in_layout = False
                chart.legend.font.size = Pt(9)
                chart.legend.font.name = DEFAULT_FONT
            chart.font.name = DEFAULT_FONT
            chart.font.size = Pt(9)

            # Apply IM theme colors
            try:
                plot = chart.plots[0]
                for idx, series in enumerate(plot.series):
                    fill = series.format.fill
                    fill.solid()
                    fill.fore_color.rgb = _CHART_COLORS[idx % len(_CHART_COLORS)]
            except Exception:
                pass

            # Chart description as subtitle
            if chart_desc:
                tb2 = slide.shapes.add_textbox(
                    Inches(1.0), Inches(6.3), Inches(11.333), Inches(0.4))
                p2 = tb2.text_frame.paragraphs[0]
                run2 = p2.add_run()
                run2.text = clean_text(chart_desc)
                _set_font(run2, Pt(9), color=COLOR_MID_GREY)

            _add_footer(slide, section_label, page_num)
            return slide

    # Fallback: styled placeholder
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(1.5), Inches(1.5), Inches(10.333), Inches(4.5)
    )
    box.fill.solid()
    box.fill.fore_color.rgb = COLOR_CHART_BG
    box.line.color.rgb = COLOR_MID_GREY
    box.line.width = Pt(1)

    tb2 = slide.shapes.add_textbox(Inches(2.5), Inches(3.0), Inches(8), Inches(1.5))
    tf = tb2.text_frame
    tf.word_wrap = True
    p2 = tf.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = f"[Chart: {chart_type.upper()}]\n{clean_text(chart_desc)}"
    _set_font(run2, Pt(14), color=COLOR_MID_GREY)

    _add_footer(slide, section_label, page_num)
    return slide


def _table_to_chart_data(table_data, chart_type='bar'):
    """테이블 데이터(2D 배열)를 차트 데이터로 변환.
    첫 행=헤더, 첫 열=카테고리, 나머지=숫자 시리즈.
    """
    if not table_data or len(table_data) < 2:
        return None, None

    headers = table_data[0]
    rows = table_data[1:]

    # 숫자 컬럼 찾기
    numeric_cols = []
    for ci in range(1, len(headers)):
        numeric_count = 0
        for row in rows:
            if ci < len(row):
                val = re.sub(r'[,%원$₩억만]', '', str(row[ci]).strip())
                try:
                    float(val)
                    numeric_count += 1
                except ValueError:
                    pass
        if numeric_count >= len(rows) * 0.5:
            numeric_cols.append(ci)

    if not numeric_cols:
        return None, None

    categories = [str(row[0]).strip() for row in rows if row]

    series_list = []
    for ci in numeric_cols:
        values = []
        for row in rows:
            if ci < len(row):
                val = re.sub(r'[,%원$₩억만]', '', str(row[ci]).strip())
                try:
                    values.append(float(val))
                except ValueError:
                    values.append(0)
            else:
                values.append(0)
        series_list.append({'name': str(headers[ci]).strip(), 'values': values})

    return categories, series_list


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


def create_im_ppt(markdown_text, project_name="", gp_name="", date_str="",
                  template_path=None):
    """
    IM 마크다운을 PPT로 변환하는 메인 함수.

    Args:
        markdown_text: 마크다운 형식의 IM 텍스트
        project_name: 프로젝트명 (표지용)
        gp_name: GP사명 (표지용)
        date_str: 날짜 (표지용)
        template_path: .pptx 템플릿 파일 경로 (선택)

    Returns:
        bytes: PPT 파일 바이트
    """
    import os
    if template_path and os.path.exists(template_path):
        prs = Presentation(template_path)
    else:
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
    last_table_data = None  # 차트 생성에 사용할 직전 테이블 데이터

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
                last_table_data = table_data  # 차트 생성용으로 보관
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
            _create_chart_slide(prs, current_slide_title, chart_match.group(1),
                               table_data=last_table_data,
                               section_label=current_section_label, page_num=page_num)
            last_table_data = None  # 사용 후 초기화
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


def im_markdown_to_slide_json(markdown_text, project_name="", gp_name="", date_str=""):
    """IM 마크다운을 NP 렌더러 호환 JSON 슬라이드 배열로 변환.

    이 함수를 통해 IM 마크다운 데이터를 utils_ppt.create_deck_from_json()에
    전달하여 NP 테마로 렌더링할 수 있습니다.

    Returns:
        dict: {"slides": [...]} NP 렌더러 호환 JSON
    """
    slides = []

    # Cover slide
    slides.append({
        "slide_type": "title",
        "title": project_name or "Information Memorandum",
        "subtitle": gp_name or "Information Memorandum",
    })

    current_section_label = ""
    current_slide_title = ""
    current_items = []
    is_first_h1 = True
    section_num_counter = 0
    last_table_data = None

    def _flush_content():
        nonlocal current_items, current_slide_title
        if current_slide_title and current_items:
            slide = {
                "slide_type": "two_column",
                "title": clean_text(current_slide_title),
                "subtitle": current_section_label,
                "left": {"items": [clean_text(item) for item in current_items]},
            }
            slides.append(slide)
            current_items = []
            current_slide_title = ""

    lines = markdown_text.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped == '---':
            i += 1
            continue

        # H1: Section divider
        if stripped.startswith('# ') and not stripped.startswith('## '):
            _flush_content()
            h1_text = stripped[2:].strip()

            if is_first_h1:
                is_first_h1 = False
            else:
                section_num_counter += 1
                section_num = _extract_section_num(h1_text)
                section_title = re.sub(r'^[IVX]+\.?\s*|^[0-9]+\.?\s*', '', h1_text).strip()
                slides.append({
                    "slide_type": "divider",
                    "title": section_title or h1_text,
                    "section_number": section_num or str(section_num_counter),
                })

            current_section_label = h1_text
            i += 1
            continue

        # H2: New slide
        if stripped.startswith('## '):
            _flush_content()
            current_slide_title = stripped[3:].strip()
            i += 1
            continue

        # Table
        if stripped.startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1

            table_data = _parse_table(table_lines)
            if table_data and len(table_data) >= 2:
                _flush_content()
                headers = table_data[0]
                rows = table_data[1:]
                slides.append({
                    "slide_type": "data_table",
                    "title": clean_text(current_slide_title) if current_slide_title else "",
                    "subtitle": current_section_label,
                    "table": {"headers": headers, "rows": rows},
                })
                last_table_data = table_data
                current_slide_title = ""
            continue

        # Chart
        chart_match = re.match(r'\[차트:\s*(.+?)\]', stripped)
        if chart_match:
            _flush_content()
            chart_desc = chart_match.group(1)
            chart_type = _detect_chart_type(chart_desc)

            chart_slide = {
                "slide_type": "chart_table",
                "title": clean_text(current_slide_title) if current_slide_title else chart_desc,
                "subtitle": current_section_label,
            }

            # Use preceding table data for chart
            if last_table_data:
                categories, series_list = _table_to_chart_data(last_table_data, chart_type)
                if categories and series_list:
                    chart_slide["chart"] = {
                        "chart_type": chart_type,
                        "categories": categories,
                        "series": series_list,
                    }
                    # Also include table
                    chart_slide["table"] = {
                        "headers": last_table_data[0],
                        "rows": last_table_data[1:],
                    }
                last_table_data = None

            slides.append(chart_slide)
            i += 1
            continue

        current_items.append(stripped)
        i += 1

    _flush_content()

    return {"slides": slides}

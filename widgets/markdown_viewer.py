"""Markdown viewer widget - replaces st.markdown() for rich content display."""

from PyQt6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
import re


class MarkdownViewer(QTextBrowser):
    """Widget that renders markdown as HTML for display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QTextBrowser {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                background-color: white;
            }
        """)

    def setMarkdown(self, md_text):
        """Convert markdown to HTML and display, preserving scroll position."""
        if not md_text:
            self.setHtml("")
            return

        # 현재 스크롤 위치 저장
        scrollbar = self.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 20
        old_pos = scrollbar.value()

        html = self._md_to_html(md_text)
        self.setHtml(f"""
        <style>
            body {{ font-family: -apple-system, sans-serif; font-size: 13px; line-height: 1.6; color: #333; }}
            h1 {{ font-size: 20px; font-weight: bold; margin: 16px 0 8px 0; color: #1a1a2e; border-bottom: 2px solid #0068c9; padding-bottom: 4px; }}
            h2 {{ font-size: 17px; font-weight: bold; margin: 14px 0 6px 0; color: #1a1a2e; }}
            h3 {{ font-size: 15px; font-weight: bold; margin: 12px 0 4px 0; color: #333; }}
            h4, h5, h6 {{ font-size: 14px; font-weight: bold; margin: 10px 0 4px 0; }}
            p {{ margin: 6px 0; }}
            ul, ol {{ margin: 4px 0; padding-left: 20px; }}
            li {{ margin: 2px 0; }}
            table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
            th, td {{ border: 1px solid #dee2e6; padding: 6px 10px; text-align: left; font-size: 12px; }}
            th {{ background-color: #f0f2f6; font-weight: bold; }}
            code {{ background-color: #f0f2f6; padding: 1px 4px; border-radius: 3px; font-family: monospace; font-size: 12px; }}
            pre {{ background-color: #f0f2f6; padding: 10px; border-radius: 6px; overflow-x: auto; }}
            blockquote {{ border-left: 4px solid #0068c9; padding-left: 12px; color: #555; margin: 8px 0; }}
            hr {{ border: none; border-top: 1px solid #dee2e6; margin: 12px 0; }}
            strong {{ font-weight: bold; }}
            em {{ font-style: italic; }}
        </style>
        <body>{html}</body>
        """)

        # 스크롤 위치 복원: 끝에 있었으면 끝으로, 아니면 이전 위치 유지
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(old_pos)

    def _md_to_html(self, text):
        """Simple markdown to HTML converter."""
        lines = text.split('\n')
        html_lines = []
        in_code_block = False
        in_table = False
        in_list = False
        list_type = None

        for line in lines:
            # Code blocks
            if line.strip().startswith('```'):
                if in_code_block:
                    html_lines.append('</pre>')
                    in_code_block = False
                else:
                    html_lines.append('<pre><code>')
                    in_code_block = True
                continue

            if in_code_block:
                html_lines.append(self._escape_html(line))
                continue

            stripped = line.strip()

            # Empty line
            if not stripped:
                if in_list:
                    html_lines.append(f'</{list_type}>')
                    in_list = False
                if in_table:
                    html_lines.append('</table>')
                    in_table = False
                html_lines.append('<br>')
                continue

            # Table
            if '|' in stripped and stripped.startswith('|'):
                cells = [c.strip() for c in stripped.split('|')[1:-1]]
                if all(set(c) <= {'-', ':', ' '} for c in cells):
                    continue  # Skip separator row
                if not in_table:
                    html_lines.append('<table>')
                    in_table = True
                    tag = 'th'
                else:
                    tag = 'td'
                row = ''.join(f'<{tag}>{self._inline(c)}</{tag}>' for c in cells)
                html_lines.append(f'<tr>{row}</tr>')
                continue

            if in_table and '|' not in stripped:
                html_lines.append('</table>')
                in_table = False

            # Headers
            if stripped.startswith('#'):
                level = min(len(stripped) - len(stripped.lstrip('#')), 6)
                text_content = stripped[level:].strip()
                if in_list:
                    html_lines.append(f'</{list_type}>')
                    in_list = False
                html_lines.append(f'<h{level}>{self._inline(text_content)}</h{level}>')
                continue

            # Horizontal rule
            if stripped in ('---', '***', '___'):
                html_lines.append('<hr>')
                continue

            # Blockquote
            if stripped.startswith('>'):
                text_content = stripped[1:].strip()
                html_lines.append(f'<blockquote>{self._inline(text_content)}</blockquote>')
                continue

            # Unordered list
            if stripped.startswith('- ') or stripped.startswith('* '):
                if not in_list or list_type != 'ul':
                    if in_list:
                        html_lines.append(f'</{list_type}>')
                    html_lines.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                text_content = stripped[2:]
                html_lines.append(f'<li>{self._inline(text_content)}</li>')
                continue

            # Ordered list
            if re.match(r'^\d+\.\s', stripped):
                if not in_list or list_type != 'ol':
                    if in_list:
                        html_lines.append(f'</{list_type}>')
                    html_lines.append('<ol>')
                    in_list = True
                    list_type = 'ol'
                text_content = re.sub(r'^\d+\.\s', '', stripped)
                html_lines.append(f'<li>{self._inline(text_content)}</li>')
                continue

            # Close list if not a list item
            if in_list:
                html_lines.append(f'</{list_type}>')
                in_list = False

            # Regular paragraph
            html_lines.append(f'<p>{self._inline(stripped)}</p>')

        # Close open tags
        if in_list:
            html_lines.append(f'</{list_type}>')
        if in_table:
            html_lines.append('</table>')
        if in_code_block:
            html_lines.append('</pre>')

        return '\n'.join(html_lines)

    def _inline(self, text):
        """Process inline markdown."""
        text = self._escape_html(text)
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
        # Inline code
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        # Links
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
        return text

    def _escape_html(self, text):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

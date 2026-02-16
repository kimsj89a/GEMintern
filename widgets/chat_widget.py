"""Chat widget - replaces st.chat_message() + st.chat_input()."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QTextBrowser, QSizePolicy,
    QFileDialog, QMessageBox, QApplication
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
import re


def _escape_html(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _inline_md(text):
    """Process inline markdown to HTML."""
    text = _escape_html(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def md_to_html(text):
    """Convert markdown to HTML."""
    lines = text.split('\n')
    html_lines = []
    in_code_block = False
    in_table = False
    in_list = False
    list_type = None

    for line in lines:
        if line.strip().startswith('```'):
            if in_code_block:
                html_lines.append('</pre>')
                in_code_block = False
            else:
                html_lines.append('<pre><code>')
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(_escape_html(line))
            continue

        stripped = line.strip()

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
                continue
            if not in_table:
                html_lines.append('<table>')
                in_table = True
                tag = 'th'
            else:
                tag = 'td'
            row = ''.join(f'<{tag}>{_inline_md(c)}</{tag}>' for c in cells)
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
            html_lines.append(f'<h{level}>{_inline_md(text_content)}</h{level}>')
            continue

        if stripped in ('---', '***', '___'):
            html_lines.append('<hr>')
            continue

        if stripped.startswith('>'):
            text_content = stripped[1:].strip()
            html_lines.append(f'<blockquote>{_inline_md(text_content)}</blockquote>')
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
            html_lines.append(f'<li>{_inline_md(text_content)}</li>')
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
            html_lines.append(f'<li>{_inline_md(text_content)}</li>')
            continue

        if in_list:
            html_lines.append(f'</{list_type}>')
            in_list = False

        html_lines.append(f'<p>{_inline_md(stripped)}</p>')

    if in_list:
        html_lines.append(f'</{list_type}>')
    if in_table:
        html_lines.append('</table>')
    if in_code_block:
        html_lines.append('</pre>')

    return '\n'.join(html_lines)


BUBBLE_CSS = """
<style>
    body { font-family: 'Malgun Gothic', -apple-system, sans-serif; font-size: 13px; line-height: 1.7; color: #37352F; margin: 0; padding: 0; }
    h1 { font-size: 18px; font-weight: bold; margin: 14px 0 6px 0; color: #1a1a2e; border-bottom: 2px solid #2383E2; padding-bottom: 4px; }
    h2 { font-size: 16px; font-weight: bold; margin: 12px 0 5px 0; color: #1a1a2e; }
    h3 { font-size: 14px; font-weight: bold; margin: 10px 0 4px 0; color: #333; }
    h4, h5, h6 { font-size: 13px; font-weight: bold; margin: 8px 0 3px 0; }
    p { margin: 4px 0; }
    ul, ol { margin: 4px 0; padding-left: 20px; }
    li { margin: 2px 0; }
    table { border-collapse: collapse; width: 100%; margin: 8px 0; }
    th, td { border: 1px solid #dee2e6; padding: 5px 8px; text-align: left; font-size: 12px; }
    th { background-color: #f0f2f6; font-weight: bold; }
    tr:nth-child(even) td { background-color: #fafafa; }
    code { background-color: #f0f2f6; padding: 1px 4px; border-radius: 3px; font-family: monospace; font-size: 12px; }
    pre { background-color: #f0f2f6; padding: 10px; border-radius: 6px; overflow-x: auto; }
    blockquote { border-left: 3px solid #2383E2; padding-left: 10px; color: #555; margin: 6px 0; }
    hr { border: none; border-top: 1px solid #dee2e6; margin: 10px 0; }
    strong { font-weight: bold; }
    em { font-style: italic; }
</style>
"""


class AutoResizeBrowser(QTextBrowser):
    """QTextBrowser that auto-resizes to fit its content."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QTextBrowser {
                border: none;
                background-color: transparent;
                font-size: 13px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def setHtml(self, html):
        super().setHtml(html)
        QTimer.singleShot(10, self._adjust_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_height()

    def _adjust_height(self):
        doc = self.document()
        doc.setTextWidth(self.viewport().width())
        h = int(doc.size().height()) + 8
        if h != self.fixedHeight if hasattr(self, 'fixedHeight') else True:
            self.fixedHeight = h
            self.setFixedHeight(h)


class ChatBubble(QFrame):
    """Single chat message bubble with rendered markdown for assistant."""

    def __init__(self, role, content, parent=None):
        super().__init__(parent)
        self._raw_content = content
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        if role == "user":
            self.setStyleSheet("""
                QFrame {
                    background-color: #E8F3FC;
                    border: 1px solid #b3d1ff;
                    border-radius: 10px;
                    margin: 4px 60px 4px 4px;
                }
            """)
            header = QLabel("  질문")
            header.setStyleSheet("font-weight: bold; font-size: 11px; color: #1F6FC1; border: none; background: transparent;")
            header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(header)

            text_label = QLabel(content)
            text_label.setWordWrap(True)
            text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            text_label.setStyleSheet("font-size: 14px; color: #37352F; border: none; background: transparent; padding: 2px 0;")
            layout.addWidget(text_label)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #E9E9E7;
                    border-radius: 10px;
                    margin: 4px 4px 4px 4px;
                }
            """)
            header = QLabel("  AI 답변")
            header.setStyleSheet("font-weight: bold; font-size: 11px; color: #787774; border: none; background: transparent;")
            header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(header)

            # Render markdown as Word-like HTML (auto-resize)
            viewer = AutoResizeBrowser()
            html_content = md_to_html(content)
            viewer.setHtml(f"{BUBBLE_CSS}<body>{html_content}</body>")
            layout.addWidget(viewer)

            # Action buttons row
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 4, 0, 0)
            btn_row.addStretch()

            btn_copy = QPushButton("  복사")
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #787774; border: 1px solid #E9E9E7;
                    border-radius: 6px; padding: 4px 10px; font-size: 11px;
                }
                QPushButton:hover { background: #F7F6F3; color: #37352F; }
            """)
            btn_copy.clicked.connect(lambda: self._copy_content())
            btn_row.addWidget(btn_copy)

            btn_word = QPushButton("  Word 저장")
            btn_word.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_word.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #787774; border: 1px solid #E9E9E7;
                    border-radius: 6px; padding: 4px 10px; font-size: 11px;
                }
                QPushButton:hover { background: #E8F3FC; color: #2383E2; border-color: #2383E2; }
            """)
            btn_word.clicked.connect(lambda: self._save_word())
            btn_row.addWidget(btn_word)

            layout.addLayout(btn_row)

    def _copy_content(self):
        QApplication.clipboard().setText(self._raw_content)

    def _save_word(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Word 저장", "AI_answer.docx", "Word Documents (*.docx)"
        )
        if path:
            try:
                import utils
                data = utils.create_docx(self._raw_content)
                with open(path, 'wb') as f:
                    f.write(data)
                QMessageBox.information(self, "저장 완료", f"저장되었습니다:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "저장 실패", str(e))


class ChatWidget(QWidget):
    """Complete chat interface with input on top and messages below."""

    message_sent = pyqtSignal(str)

    def __init__(self, placeholder="메시지를 입력하세요...", parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # === Input area (TOP) ===
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: #F7F6F3;
                border: 2px solid #2383E2;
                border-radius: 10px;
                padding: 4px;
            }
        """)
        input_inner = QHBoxLayout(input_frame)
        input_inner.setContentsMargins(12, 8, 8, 8)
        input_inner.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(placeholder)
        self.input_field.returnPressed.connect(self._send)
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                font-size: 15px;
                padding: 6px 4px;
                color: #37352F;
            }
        """)
        self.input_field.setMinimumHeight(36)
        input_inner.addWidget(self.input_field)

        self.send_btn = QPushButton("전송 ↵")
        self.send_btn.clicked.connect(self._send)
        self.send_btn.setFixedSize(80, 36)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2383E2;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1F6FC1; }
            QPushButton:disabled { background-color: #B0B0B0; }
        """)
        input_inner.addWidget(self.send_btn)

        layout.addWidget(input_frame)

        # === Messages area (BELOW) ===
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: 1px solid #E9E9E7; border-radius: 8px; background-color: #FAFAF9; }
        """)

        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("background-color: #FAFAF9;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSpacing(8)
        self.messages_layout.setContentsMargins(8, 8, 8, 8)
        self.scroll_area.setWidget(self.messages_container)

        layout.addWidget(self.scroll_area)

        self._messages = []

    def _send(self):
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.message_sent.emit(text)

    def add_message(self, role, content):
        """Add a message to the chat."""
        self._messages.append({"role": role, "content": content})
        bubble = ChatBubble(role, content)
        self.messages_layout.addWidget(bubble)
        # Scroll to bottom after layout updates
        QTimer.singleShot(100, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def clear_messages(self):
        """Remove all messages."""
        self._messages.clear()
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def get_messages(self):
        return self._messages.copy()

    def set_enabled(self, enabled):
        self.input_field.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)

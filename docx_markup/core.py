"""
core.py — DOCX Tracked Changes 추출 엔진

.docx 파일의 XML을 파싱하여 삽입(w:ins), 삭제(w:del), 서식변경(w:rPrChange) 등
tracked changes를 구조화된 데이터로 추출한다.
"""

import zipfile
import copy
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from lxml import etree

# ─── OOXML 네임스페이스 ────────────────────────────────────────────
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
}


def _qn(tag: str) -> str:
    """네임스페이스 접두사를 Clark notation으로 변환. 예: 'w:ins' → '{http://...}ins'"""
    prefix, local = tag.split(":")
    return f"{{{NS[prefix]}}}{local}"


# ─── 데이터 클래스 ─────────────────────────────────────────────────
@dataclass
class TrackedChange:
    """단일 tracked change를 표현"""
    change_type: str          # 'insertion' | 'deletion' | 'format_change' | 'paragraph_insertion' | 'paragraph_deletion'
    change_id: str            # w:id
    author: str               # w:author
    date: str                 # w:date (ISO 8601)
    text: str                 # 변경된 텍스트 내용
    context_before: str = ""  # 변경 앞쪽 텍스트 (최대 80자)
    context_after: str = ""   # 변경 뒤쪽 텍스트 (최대 80자)
    paragraph_index: int = -1 # 문서 내 문단 인덱스
    xml_element: Optional[object] = field(default=None, repr=False)  # 원본 lxml element
    source_file: str = ""     # 원본 파일명

    def signature(self) -> str:
        """변경의 고유 시그니처 (중복 판별용)"""
        return f"{self.change_type}|{self.author}|{self.text[:100]}|{self.paragraph_index}"

    def to_dict(self) -> dict:
        return {
            "change_type": self.change_type,
            "change_id": self.change_id,
            "author": self.author,
            "date": self.date,
            "text": self.text,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "paragraph_index": self.paragraph_index,
            "source_file": self.source_file,
        }


@dataclass
class DocumentInfo:
    """문서 메타정보"""
    filename: str
    authors: List[str]
    change_count: int
    paragraphs_total: int


# ─── XML 파서 ──────────────────────────────────────────────────────
class DocxParser:
    """DOCX 파일에서 tracked changes를 추출하는 파서"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self._tree = None
        self._body = None
        self._load()

    def _load(self):
        """docx ZIP에서 word/document.xml 파싱"""
        with zipfile.ZipFile(self.filepath, "r") as zf:
            with zf.open("word/document.xml") as f:
                self._tree = etree.parse(f)
        self._body = self._tree.getroot().find(_qn("w:body"))
        if self._body is None:
            raise ValueError(f"word/document.xml에서 w:body를 찾을 수 없습니다: {self.filepath}")

    def get_document_xml(self) -> etree._Element:
        """전체 document.xml 루트 반환"""
        return self._tree.getroot()

    def get_body(self) -> etree._Element:
        """w:body 엘리먼트 반환"""
        return self._body

    def get_body_copy(self) -> etree._Element:
        """w:body의 deep copy 반환 (비파괴 작업용)"""
        return copy.deepcopy(self._body)

    def get_raw_zip(self) -> zipfile.ZipFile:
        """원본 ZIP 핸들 반환"""
        return zipfile.ZipFile(self.filepath, "r")

    # ── 텍스트 추출 유틸 ──
    @staticmethod
    def _collect_text(element, tag="w:t") -> str:
        """엘리먼트 하위의 모든 w:t (또는 w:delText) 텍스트를 결합"""
        texts = []
        for t in element.iter(_qn(tag)):
            if t.text:
                texts.append(t.text)
        return "".join(texts)

    @staticmethod
    def _collect_any_text(element) -> str:
        """w:t와 w:delText 모두 수집"""
        texts = []
        for t in element.iter(_qn("w:t")):
            if t.text:
                texts.append(t.text)
        for t in element.iter(_qn("w:delText")):
            if t.text:
                texts.append(t.text)
        return "".join(texts)

    def _get_paragraph_context(self, paragraph, change_elem) -> Tuple[str, str]:
        """변경 엘리먼트 앞뒤의 일반 텍스트를 문맥으로 추출"""
        before_parts = []
        after_parts = []
        found = False

        for child in paragraph:
            if child is change_elem or child.tag == change_elem.tag and child.get(_qn("w:id")) == change_elem.get(_qn("w:id")):
                found = True
                continue
            text = self._collect_any_text(child)
            if text:
                if not found:
                    before_parts.append(text)
                else:
                    after_parts.append(text)

        ctx_before = "".join(before_parts)[-80:]
        ctx_after = "".join(after_parts)[:80]
        return ctx_before, ctx_after

    # ── 메인 추출 ──
    def extract_changes(self) -> List[TrackedChange]:
        """모든 tracked changes 추출"""
        changes = []
        paragraphs = list(self._body.iter(_qn("w:p")))

        for p_idx, para in enumerate(paragraphs):
            # 단락 삽입/삭제 (w:pPr > w:rPr > w:ins/w:del)
            ppr = para.find(_qn("w:pPr"))
            if ppr is not None:
                rpr = ppr.find(_qn("w:rPr"))
                if rpr is not None:
                    for marker_tag, ctype in [("w:ins", "paragraph_mark_insertion"), ("w:del", "paragraph_mark_deletion")]:
                        marker = rpr.find(_qn(marker_tag))
                        if marker is not None:
                            changes.append(TrackedChange(
                                change_type=ctype,
                                change_id=marker.get(_qn("w:id"), ""),
                                author=marker.get(_qn("w:author"), ""),
                                date=marker.get(_qn("w:date"), ""),
                                text=self._collect_any_text(para),
                                paragraph_index=p_idx,
                                xml_element=marker,
                                source_file=self.filename,
                            ))

            # 인라인 삽입 (w:ins)
            for ins in para.iter(_qn("w:ins")):
                # pPr 내부의 것은 위에서 처리했으므로 제외
                if ins.getparent() is not None and ins.getparent().tag == _qn("w:rPr"):
                    continue
                text = self._collect_text(ins)
                ctx_b, ctx_a = self._get_paragraph_context(para, ins)
                changes.append(TrackedChange(
                    change_type="insertion",
                    change_id=ins.get(_qn("w:id"), ""),
                    author=ins.get(_qn("w:author"), ""),
                    date=ins.get(_qn("w:date"), ""),
                    text=text,
                    context_before=ctx_b,
                    context_after=ctx_a,
                    paragraph_index=p_idx,
                    xml_element=ins,
                    source_file=self.filename,
                ))

            # 인라인 삭제 (w:del)
            for dele in para.iter(_qn("w:del")):
                if dele.getparent() is not None and dele.getparent().tag == _qn("w:rPr"):
                    continue
                text = self._collect_text(dele, "w:delText")
                ctx_b, ctx_a = self._get_paragraph_context(para, dele)
                changes.append(TrackedChange(
                    change_type="deletion",
                    change_id=dele.get(_qn("w:id"), ""),
                    author=dele.get(_qn("w:author"), ""),
                    date=dele.get(_qn("w:date"), ""),
                    text=text,
                    context_before=ctx_b,
                    context_after=ctx_a,
                    paragraph_index=p_idx,
                    xml_element=dele,
                    source_file=self.filename,
                ))

            # 서식 변경 (w:rPrChange)
            for rpc in para.iter(_qn("w:rPrChange")):
                run = rpc.getparent()  # w:rPr
                if run is not None:
                    run = run.getparent()  # w:r
                run_text = self._collect_text(run) if run is not None else ""
                changes.append(TrackedChange(
                    change_type="format_change",
                    change_id=rpc.get(_qn("w:id"), ""),
                    author=rpc.get(_qn("w:author"), ""),
                    date=rpc.get(_qn("w:date"), ""),
                    text=f"[서식변경] {run_text}",
                    paragraph_index=p_idx,
                    xml_element=rpc,
                    source_file=self.filename,
                ))

        return changes

    def get_info(self) -> DocumentInfo:
        """문서 메타정보 반환"""
        changes = self.extract_changes()
        authors = list(set(c.author for c in changes if c.author))
        para_count = len(list(self._body.iter(_qn("w:p"))))
        return DocumentInfo(
            filename=self.filename,
            authors=authors,
            change_count=len(changes),
            paragraphs_total=para_count,
        )

    def get_plain_text(self) -> str:
        """문서의 최종(변경 수락 후) 플레인텍스트 추출"""
        lines = []
        for para in self._body.iter(_qn("w:p")):
            parts = []
            for elem in para.iter():
                # 삭제된 텍스트 제외
                if elem.tag == _qn("w:delText"):
                    continue
                if elem.tag == _qn("w:t") and elem.text:
                    # w:del 하위인지 확인
                    parent = elem.getparent()
                    in_del = False
                    while parent is not None:
                        if parent.tag == _qn("w:del"):
                            in_del = True
                            break
                        parent = parent.getparent()
                    if not in_del:
                        parts.append(elem.text)
            lines.append("".join(parts))
        return "\n".join(lines)


# ─── 편의 함수 ────────────────────────────────────────────────────
def extract_all_changes(filepath: str) -> List[TrackedChange]:
    """파일 경로 하나에서 모든 tracked changes 추출"""
    parser = DocxParser(filepath)
    return parser.extract_changes()


def summarize_changes(changes: List[TrackedChange]) -> Dict:
    """변경사항 요약 통계"""
    by_type = {}
    by_author = {}
    for c in changes:
        by_type[c.change_type] = by_type.get(c.change_type, 0) + 1
        by_author[c.author] = by_author.get(c.author, 0) + 1
    return {
        "total": len(changes),
        "by_type": by_type,
        "by_author": by_author,
    }

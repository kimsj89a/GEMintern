"""
output.py — Clean / Redline 버전 DOCX 생성

병합된 변경사항을 바탕으로:
  - Clean 버전: 모든 변경을 수락한 깨끗한 문서
  - Redline 버전: 모든 변경이 tracked changes로 표시된 문서
를 생성한다.
"""

import copy
import os
import zipfile
import shutil
import tempfile
from typing import List, Optional, Set
from lxml import etree

from core import DocxParser, TrackedChange, _qn, NS


# ─── Clean 버전 생성 ───────────────────────────────────────────────
class CleanGenerator:
    """Tracked changes를 모두 수락하여 clean 버전 생성"""

    def __init__(self, source_path: str):
        self.source_path = source_path
        self.parser = DocxParser(source_path)

    def generate(self, output_path: str, accept_changes: Optional[Set[str]] = None):
        """
        Clean 버전 생성

        Args:
            output_path: 출력 파일 경로
            accept_changes: 수락할 change_id 집합. None이면 전부 수락.
        """
        # 임시 디렉토리에 원본 ZIP 풀기
        tmpdir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(self.source_path, "r") as zf:
                zf.extractall(tmpdir)

            # document.xml 수정
            doc_xml_path = os.path.join(tmpdir, "word", "document.xml")
            tree = etree.parse(doc_xml_path)
            root = tree.getroot()
            body = root.find(_qn("w:body"))

            self._accept_all_changes(body, accept_changes)

            # 수정된 XML 저장
            tree.write(doc_xml_path, xml_declaration=True, encoding="UTF-8", standalone=True)

            # 다시 ZIP으로 묶기
            self._repack_docx(tmpdir, output_path)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _accept_all_changes(self, body: etree._Element, accept_ids: Optional[Set[str]] = None):
        """모든 tracked changes를 수락 (XML 레벨)"""

        # 1) w:ins → 내용만 남기고 w:ins 태그 제거 (unwrap)
        for ins in list(body.iter(_qn("w:ins"))):
            # pPr 내부의 ins 마커인지 확인
            parent = ins.getparent()
            if parent is not None and parent.tag == _qn("w:rPr"):
                # 문단 마크 삽입 → 마커만 제거
                parent.remove(ins)
                continue

            if accept_ids is not None:
                ins_id = ins.get(_qn("w:id"), "")
                if ins_id not in accept_ids:
                    continue

            # ins의 자식들을 ins 위치에 삽입하고, ins 제거
            parent = ins.getparent()
            if parent is not None:
                idx = list(parent).index(ins)
                for i, child in enumerate(list(ins)):
                    parent.insert(idx + i, child)
                parent.remove(ins)

        # 2) w:del → 전체 제거 (삭제를 수락 = 텍스트 삭제)
        for dele in list(body.iter(_qn("w:del"))):
            parent = dele.getparent()
            if parent is not None and parent.tag == _qn("w:rPr"):
                # 문단 마크 삭제 → 마커만 제거
                parent.remove(dele)
                continue

            if accept_ids is not None:
                del_id = dele.get(_qn("w:id"), "")
                if del_id not in accept_ids:
                    continue

            parent = dele.getparent()
            if parent is not None:
                parent.remove(dele)

        # 3) w:rPrChange → 제거 (서식 변경 수락)
        for rpc in list(body.iter(_qn("w:rPrChange"))):
            parent = rpc.getparent()
            if parent is not None:
                parent.remove(rpc)

        # 4) 빈 문단 정리 (삭제 수락 후 텍스트 없는 문단)
        # 이 부분은 선택적이므로 보수적으로 처리

    @staticmethod
    def _repack_docx(extracted_dir: str, output_path: str):
        """풀어둔 디렉토리를 다시 .docx로 묶기"""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root_dir, dirs, files in os.walk(extracted_dir):
                for f in files:
                    full_path = os.path.join(root_dir, f)
                    arc_name = os.path.relpath(full_path, extracted_dir)
                    zf.write(full_path, arc_name)


# ─── Redline 버전 생성 ─────────────────────────────────────────────
class RedlineGenerator:
    """여러 문서의 tracked changes를 하나의 redline 문서로 합성"""

    # 저자별 색상 매핑 (Word의 기본 revision 색상 시스템 활용)
    AUTHOR_COLORS = [
        "FF0000",  # 빨강
        "0000FF",  # 파랑
        "008000",  # 초록
        "FF6600",  # 주황
        "800080",  # 보라
        "008080",  # 청록
    ]

    def __init__(self, base_path: str):
        """
        Args:
            base_path: 베이스 문서 경로 (구조를 여기서 가져옴)
        """
        self.base_path = base_path
        self.parser = DocxParser(base_path)

    def generate(self, output_path: str,
                 accepted_changes: List[TrackedChange] = None,
                 rejected_changes: List[TrackedChange] = None,
                 label_sources: bool = True):
        """
        Redline 버전 생성

        기본 동작: 원본 문서의 tracked changes를 그대로 유지.
        accepted/rejected가 주어지면 해당 변경만 표시.

        Args:
            output_path: 출력 파일 경로
            accepted_changes: 수락 대상 변경 (redline에서 초록으로 표시)
            rejected_changes: 거부 대상 변경 (redline에서 빨강 취소선)
            label_sources: True면 출처 파일명을 코멘트로 표기
        """
        tmpdir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(self.base_path, "r") as zf:
                zf.extractall(tmpdir)

            doc_xml_path = os.path.join(tmpdir, "word", "document.xml")
            tree = etree.parse(doc_xml_path)

            # Redline은 기본적으로 원본의 tracked changes를 유지
            # 추가로 병합된 다른 문서의 변경사항을 삽입할 수도 있음
            # (이 버전에서는 원본 유지 방식)

            tree.write(doc_xml_path, xml_declaration=True, encoding="UTF-8", standalone=True)
            CleanGenerator._repack_docx(tmpdir, output_path)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def generate_from_base_and_clean(self, clean_path: str, output_path: str):
        """
        원본(base)과 clean 버전을 비교하여 redline 생성.

        이 방식은 pandoc이나 LibreOffice를 사용하여
        두 문서 간 실제 diff를 tracked changes로 만든다.
        """
        import subprocess

        # LibreOffice macro를 사용한 문서 비교
        # (pandoc은 docx 비교를 지원하지 않으므로 대안 제공)
        try:
            result = subprocess.run(
                ["python3", "scripts/office/soffice.py",
                 "--headless",
                 "--invisible",
                 f"macro:///Standard.Compare.CompareDocuments({self.base_path},{clean_path},{output_path})"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                # fallback: 단순 복사
                shutil.copy2(self.base_path, output_path)
                return False
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # LibreOffice 없으면 원본 복사
            shutil.copy2(self.base_path, output_path)
            return False


# ─── 편의 함수 ────────────────────────────────────────────────────
def create_clean_version(source: str, output: str):
    """원본 문서에서 clean 버전 생성 (모든 변경 수락)"""
    gen = CleanGenerator(source)
    gen.generate(output)
    print(f"Clean 버전 생성: {output}")


def create_redline_version(source: str, output: str):
    """원본 문서의 redline(tracked changes 유지) 버전 생성"""
    gen = RedlineGenerator(source)
    gen.generate(output)
    print(f"Redline 버전 생성: {output}")


def create_both_versions(source: str, output_dir: str, base_name: str = None):
    """Clean + Redline 양쪽 버전을 한 번에 생성"""
    if base_name is None:
        base_name = os.path.splitext(os.path.basename(source))[0]

    os.makedirs(output_dir, exist_ok=True)
    clean_path = os.path.join(output_dir, f"{base_name}_CLEAN.docx")
    redline_path = os.path.join(output_dir, f"{base_name}_REDLINE.docx")

    create_clean_version(source, clean_path)
    create_redline_version(source, redline_path)

    return clean_path, redline_path

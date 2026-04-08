"""
compare.py — 다중 문서 Markup 비교

여러 .docx 파일의 tracked changes를 비교하여
동일 변경, 충돌 변경, 고유 변경을 식별한다.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher

from core import DocxParser, TrackedChange, summarize_changes


# ─── 비교 결과 데이터 ─────────────────────────────────────────────
@dataclass
class ChangeMatch:
    """두 문서 간 매칭된 변경"""
    change_a: TrackedChange
    change_b: TrackedChange
    similarity: float          # 0.0 ~ 1.0
    match_type: str            # 'identical' | 'similar' | 'conflict'


@dataclass
class ComparisonResult:
    """두 문서 비교 결과"""
    file_a: str
    file_b: str
    matched: List[ChangeMatch]         # 동일하거나 유사한 변경
    only_in_a: List[TrackedChange]     # A에만 있는 변경
    only_in_b: List[TrackedChange]     # B에만 있는 변경
    conflicts: List[ChangeMatch]       # 같은 위치에 다른 변경


@dataclass
class MultiComparisonResult:
    """다중 문서 비교 결과"""
    files: List[str]
    pairwise: List[ComparisonResult]
    common_changes: List[TrackedChange]          # 모든 문서에 공통
    unique_per_file: Dict[str, List[TrackedChange]]  # 파일별 고유 변경
    all_conflicts: List[ChangeMatch]             # 전체 충돌


# ─── 비교 엔진 ─────────────────────────────────────────────────────
class ChangeComparer:
    """Tracked changes 비교 엔진"""

    def __init__(self, similarity_threshold: float = 0.7):
        self.threshold = similarity_threshold

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """두 텍스트의 유사도 (0~1)"""
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    def _is_same_location(self, a: TrackedChange, b: TrackedChange) -> bool:
        """같은 위치의 변경인지 판단 (문단 인덱스 + 문맥)"""
        # 문단 인덱스가 ±2 이내
        if abs(a.paragraph_index - b.paragraph_index) > 2:
            return False
        # 앞뒤 문맥 유사도
        ctx_sim = self._text_similarity(a.context_before, b.context_before)
        return ctx_sim > 0.5

    def compare_pair(self, changes_a: List[TrackedChange], changes_b: List[TrackedChange],
                     file_a: str = "A", file_b: str = "B") -> ComparisonResult:
        """두 문서의 변경사항 비교"""
        matched = []
        used_a = set()
        used_b = set()

        # 1) 텍스트+타입 완전 일치 찾기
        for i, ca in enumerate(changes_a):
            for j, cb in enumerate(changes_b):
                if j in used_b:
                    continue
                if ca.change_type == cb.change_type and ca.text == cb.text:
                    if self._is_same_location(ca, cb):
                        matched.append(ChangeMatch(ca, cb, 1.0, "identical"))
                        used_a.add(i)
                        used_b.add(j)
                        break

        # 2) 유사 변경 찾기
        for i, ca in enumerate(changes_a):
            if i in used_a:
                continue
            for j, cb in enumerate(changes_b):
                if j in used_b:
                    continue
                if ca.change_type != cb.change_type:
                    continue
                sim = self._text_similarity(ca.text, cb.text)
                if sim >= self.threshold and self._is_same_location(ca, cb):
                    matched.append(ChangeMatch(ca, cb, sim, "similar"))
                    used_a.add(i)
                    used_b.add(j)
                    break

        # 3) 충돌 찾기 (같은 위치, 다른 변경)
        conflicts = []
        for i, ca in enumerate(changes_a):
            if i in used_a:
                continue
            for j, cb in enumerate(changes_b):
                if j in used_b:
                    continue
                if self._is_same_location(ca, cb):
                    sim = self._text_similarity(ca.text, cb.text)
                    if sim < self.threshold:
                        conflicts.append(ChangeMatch(ca, cb, sim, "conflict"))
                        used_a.add(i)
                        used_b.add(j)
                        break

        # 4) 나머지 = 고유 변경
        only_a = [changes_a[i] for i in range(len(changes_a)) if i not in used_a]
        only_b = [changes_b[j] for j in range(len(changes_b)) if j not in used_b]

        return ComparisonResult(
            file_a=file_a,
            file_b=file_b,
            matched=matched,
            only_in_a=only_a,
            only_in_b=only_b,
            conflicts=conflicts,
        )

    def compare_multiple(self, file_changes: Dict[str, List[TrackedChange]]) -> MultiComparisonResult:
        """다중 문서 비교"""
        files = list(file_changes.keys())
        pairwise = []

        # 모든 쌍 비교
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                result = self.compare_pair(
                    file_changes[files[i]], file_changes[files[j]],
                    files[i], files[j]
                )
                pairwise.append(result)

        # 모든 문서에 공통인 변경 (시그니처 기반)
        if len(files) >= 2:
            sig_sets = []
            sig_to_change = {}
            for fname, changes in file_changes.items():
                sigs = set()
                for c in changes:
                    sig = c.signature()
                    sigs.add(sig)
                    sig_to_change[sig] = c
                sig_sets.append(sigs)
            common_sigs = sig_sets[0]
            for s in sig_sets[1:]:
                common_sigs &= s
            common_changes = [sig_to_change[s] for s in common_sigs]
        else:
            common_changes = list(file_changes.get(files[0], [])) if files else []

        # 파일별 고유 변경
        unique_per_file = {}
        for fname, changes in file_changes.items():
            other_sigs = set()
            for other_fname, other_changes in file_changes.items():
                if other_fname == fname:
                    continue
                for c in other_changes:
                    other_sigs.add(c.signature())
            unique_per_file[fname] = [c for c in changes if c.signature() not in other_sigs]

        # 전체 충돌 수집
        all_conflicts = []
        for pw in pairwise:
            all_conflicts.extend(pw.conflicts)

        return MultiComparisonResult(
            files=files,
            pairwise=pairwise,
            common_changes=common_changes,
            unique_per_file=unique_per_file,
            all_conflicts=all_conflicts,
        )


# ─── 리포트 생성 ──────────────────────────────────────────────────
def format_comparison_report(result: MultiComparisonResult) -> str:
    """비교 결과를 읽기 쉬운 텍스트 리포트로 변환"""
    lines = []
    lines.append("=" * 70)
    lines.append("다중 문서 Markup 비교 리포트")
    lines.append("=" * 70)
    lines.append(f"\n비교 대상 문서: {len(result.files)}개")
    for f in result.files:
        lines.append(f"  • {f}")

    lines.append(f"\n공통 변경사항: {len(result.common_changes)}건")
    lines.append(f"충돌 변경사항: {len(result.all_conflicts)}건")

    # 파일별 고유
    lines.append("\n--- 파일별 고유 변경사항 ---")
    for fname, changes in result.unique_per_file.items():
        lines.append(f"\n[{fname}] 고유 변경 {len(changes)}건:")
        for c in changes:
            marker = {"insertion": "추가", "deletion": "삭제", "format_change": "서식"}.get(c.change_type, c.change_type)
            text_preview = c.text[:80].replace("\n", " ")
            lines.append(f"  [{marker}] {text_preview}")

    # 쌍별 비교
    for pw in result.pairwise:
        lines.append(f"\n--- {pw.file_a} vs {pw.file_b} ---")
        lines.append(f"  동일/유사: {len(pw.matched)}건  |  충돌: {len(pw.conflicts)}건")
        lines.append(f"  {pw.file_a}에만: {len(pw.only_in_a)}건  |  {pw.file_b}에만: {len(pw.only_in_b)}건")

        if pw.conflicts:
            lines.append("\n  [충돌 상세]")
            for cm in pw.conflicts:
                lines.append(f"    위치: 문단 #{cm.change_a.paragraph_index}")
                lines.append(f"    A: [{cm.change_a.change_type}] {cm.change_a.text[:60]}")
                lines.append(f"    B: [{cm.change_b.change_type}] {cm.change_b.text[:60]}")
                lines.append(f"    유사도: {cm.similarity:.1%}")
                lines.append("")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)

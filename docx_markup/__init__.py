"""
docx_markup_tool — DOCX Tracked Changes 비교/병합/출력 도구

Modules:
    core     - DOCX XML 파싱 및 tracked changes 추출
    compare  - 다중 문서 markup 비교
    merge    - 변경사항 병합 + Claude API 충돌 해소
    output   - Clean / Redline 버전 DOCX 생성
    cli      - 명령줄 인터페이스
"""

from core import DocxParser, TrackedChange, extract_all_changes, summarize_changes
from compare import ChangeComparer, ComparisonResult, MultiComparisonResult
from merge import ChangeMerger, ConflictStrategy, MergeResult, ClaudeConflictResolver
from output import CleanGenerator, RedlineGenerator, create_both_versions

__version__ = "0.1.0"
__all__ = [
    "DocxParser", "TrackedChange", "extract_all_changes", "summarize_changes",
    "ChangeComparer", "ComparisonResult", "MultiComparisonResult",
    "ChangeMerger", "ConflictStrategy", "MergeResult", "ClaudeConflictResolver",
    "CleanGenerator", "RedlineGenerator", "create_both_versions",
]

"""
merge.py — 다중 문서 변경사항 병합 + Claude API 충돌 해소

여러 .docx 파일의 tracked changes를 하나의 문서로 병합한다.
충돌이 발생하면 Claude API를 호출하여 법률 문맥에 맞는 해소안을 제시한다.
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from core import DocxParser, TrackedChange
from compare import ChangeComparer, ComparisonResult, ChangeMatch

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ─── 병합 전략 ─────────────────────────────────────────────────────
class ConflictStrategy(Enum):
    KEEP_A = "keep_a"           # 문서 A의 변경 우선
    KEEP_B = "keep_b"           # 문서 B의 변경 우선
    KEEP_BOTH = "keep_both"     # 양쪽 모두 유지 (redline에 표기)
    ASK_CLAUDE = "ask_claude"   # Claude API로 최적안 결정
    MANUAL = "manual"           # 수동 결정 (placeholder 삽입)


@dataclass
class MergeDecision:
    """충돌 해소 결정"""
    conflict: ChangeMatch
    strategy: ConflictStrategy
    resolved_text: str = ""
    reasoning: str = ""


@dataclass
class MergeResult:
    """병합 결과"""
    accepted_changes: List[TrackedChange]     # 수락할 변경
    rejected_changes: List[TrackedChange]     # 거부할 변경
    conflict_decisions: List[MergeDecision]   # 충돌 해소 내역
    warnings: List[str] = field(default_factory=list)


# ─── Claude API 충돌 해소 ──────────────────────────────────────────
class ClaudeConflictResolver:
    """Claude API를 사용한 충돌 해소"""

    SYSTEM_PROMPT = """당신은 한국 PE(사모펀드) 정관 및 법률 문서의 전문 리뷰어입니다.
두 버전의 문서 변경사항이 충돌할 때, 다음 기준으로 최적의 해소안을 제시합니다:

1. LP(유한책임사원) 보호 관점에서 더 강한 보호를 제공하는 쪽 우선
2. 법적 명확성이 높은 표현 우선
3. 업계 표준 관행에 부합하는 쪽 우선
4. 양쪽을 조합하여 더 나은 안이 가능한 경우 통합안 제시

반드시 JSON 형식으로 응답하세요."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic 패키지를 설치하세요: pip install anthropic")
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def resolve_conflict(self, conflict: ChangeMatch, document_context: str = "") -> MergeDecision:
        """단일 충돌을 Claude API로 해소"""
        user_msg = self._build_prompt(conflict, document_context)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        return self._parse_response(conflict, response.content[0].text)

    def resolve_conflicts_batch(self, conflicts: List[ChangeMatch],
                                 document_context: str = "") -> List[MergeDecision]:
        """여러 충돌을 일괄 해소"""
        if not conflicts:
            return []

        user_msg = self._build_batch_prompt(conflicts, document_context)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        return self._parse_batch_response(conflicts, response.content[0].text)

    def _build_prompt(self, conflict: ChangeMatch, context: str) -> str:
        return f"""다음 문서 변경사항의 충돌을 해소해주세요.

## 문맥
{context if context else "(문맥 없음)"}

## 문서 A의 변경 (출처: {conflict.change_a.source_file})
- 유형: {conflict.change_a.change_type}
- 수정자: {conflict.change_a.author}
- 내용: {conflict.change_a.text}
- 앞 문맥: {conflict.change_a.context_before}
- 뒤 문맥: {conflict.change_a.context_after}

## 문서 B의 변경 (출처: {conflict.change_b.source_file})
- 유형: {conflict.change_b.change_type}
- 수정자: {conflict.change_b.author}
- 내용: {conflict.change_b.text}
- 앞 문맥: {conflict.change_b.context_before}
- 뒤 문맥: {conflict.change_b.context_after}

## 유사도: {conflict.similarity:.1%}

다음 JSON 형식으로 응답하세요:
```json
{{
  "decision": "keep_a" | "keep_b" | "merge",
  "resolved_text": "최종 텍스트 (merge인 경우 통합 텍스트)",
  "reasoning": "판단 근거 (한국어)"
}}
```"""

    def _build_batch_prompt(self, conflicts: List[ChangeMatch], context: str) -> str:
        parts = [f"다음 {len(conflicts)}개의 문서 변경사항 충돌을 각각 해소해주세요.\n"]
        if context:
            parts.append(f"## 전체 문맥\n{context}\n")

        for i, c in enumerate(conflicts):
            parts.append(f"""
### 충돌 #{i+1} (문단 #{c.change_a.paragraph_index})
- A ({c.change_a.source_file}, {c.change_a.author}): [{c.change_a.change_type}] {c.change_a.text[:200]}
- B ({c.change_b.source_file}, {c.change_b.author}): [{c.change_b.change_type}] {c.change_b.text[:200]}
- 유사도: {c.similarity:.1%}
""")

        parts.append("""다음 JSON 배열 형식으로 응답하세요:
```json
[
  {"index": 0, "decision": "keep_a|keep_b|merge", "resolved_text": "...", "reasoning": "..."},
  ...
]
```""")
        return "\n".join(parts)

    def _parse_response(self, conflict: ChangeMatch, response_text: str) -> MergeDecision:
        try:
            # JSON 블록 추출
            json_str = response_text
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())
            decision_map = {
                "keep_a": ConflictStrategy.KEEP_A,
                "keep_b": ConflictStrategy.KEEP_B,
                "merge": ConflictStrategy.KEEP_BOTH,
            }
            return MergeDecision(
                conflict=conflict,
                strategy=decision_map.get(data.get("decision", "keep_a"), ConflictStrategy.KEEP_A),
                resolved_text=data.get("resolved_text", ""),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError, IndexError):
            return MergeDecision(
                conflict=conflict,
                strategy=ConflictStrategy.MANUAL,
                reasoning=f"Claude 응답 파싱 실패. 원문: {response_text[:200]}",
            )

    def _parse_batch_response(self, conflicts: List[ChangeMatch], response_text: str) -> List[MergeDecision]:
        try:
            json_str = response_text
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            data_list = json.loads(json_str.strip())
            decisions = []
            decision_map = {
                "keep_a": ConflictStrategy.KEEP_A,
                "keep_b": ConflictStrategy.KEEP_B,
                "merge": ConflictStrategy.KEEP_BOTH,
            }
            for item in data_list:
                idx = item.get("index", len(decisions))
                if idx < len(conflicts):
                    decisions.append(MergeDecision(
                        conflict=conflicts[idx],
                        strategy=decision_map.get(item.get("decision", "keep_a"), ConflictStrategy.KEEP_A),
                        resolved_text=item.get("resolved_text", ""),
                        reasoning=item.get("reasoning", ""),
                    ))
            return decisions
        except (json.JSONDecodeError, KeyError):
            return [MergeDecision(conflict=c, strategy=ConflictStrategy.MANUAL,
                                  reasoning="Claude 응답 파싱 실패") for c in conflicts]


# ─── 병합 엔진 ─────────────────────────────────────────────────────
class ChangeMerger:
    """다중 문서의 tracked changes를 병합"""

    def __init__(self, conflict_strategy: ConflictStrategy = ConflictStrategy.KEEP_BOTH,
                 claude_api_key: Optional[str] = None,
                 claude_model: str = "claude-sonnet-4-20250514"):
        self.default_strategy = conflict_strategy
        self.comparer = ChangeComparer()
        self.resolver = None
        if conflict_strategy == ConflictStrategy.ASK_CLAUDE and HAS_ANTHROPIC:
            self.resolver = ClaudeConflictResolver(api_key=claude_api_key, model=claude_model)

    def merge_two(self, changes_a: List[TrackedChange], changes_b: List[TrackedChange],
                  file_a: str = "A", file_b: str = "B",
                  document_context: str = "") -> MergeResult:
        """두 문서의 변경사항 병합"""
        comparison = self.comparer.compare_pair(changes_a, changes_b, file_a, file_b)

        accepted = []
        rejected = []
        decisions = []
        warnings = []

        # 1) 동일/유사 변경 → 수락 (A쪽 사용)
        for match in comparison.matched:
            accepted.append(match.change_a)

        # 2) A에만 있는 변경 → 수락
        accepted.extend(comparison.only_in_a)

        # 3) B에만 있는 변경 → 수락
        accepted.extend(comparison.only_in_b)

        # 4) 충돌 해소
        for conflict in comparison.conflicts:
            decision = self._resolve_conflict(conflict, document_context)
            decisions.append(decision)

            if decision.strategy == ConflictStrategy.KEEP_A:
                accepted.append(conflict.change_a)
                rejected.append(conflict.change_b)
            elif decision.strategy == ConflictStrategy.KEEP_B:
                accepted.append(conflict.change_b)
                rejected.append(conflict.change_a)
            elif decision.strategy == ConflictStrategy.KEEP_BOTH:
                accepted.append(conflict.change_a)
                accepted.append(conflict.change_b)
                warnings.append(
                    f"문단 #{conflict.change_a.paragraph_index}: 양쪽 변경 모두 유지 — 수동 확인 필요"
                )
            elif decision.strategy == ConflictStrategy.MANUAL:
                warnings.append(
                    f"문단 #{conflict.change_a.paragraph_index}: 수동 해소 필요 — {decision.reasoning}"
                )

        # 문단 순서로 정렬
        accepted.sort(key=lambda c: (c.paragraph_index, c.date))

        return MergeResult(
            accepted_changes=accepted,
            rejected_changes=rejected,
            conflict_decisions=decisions,
            warnings=warnings,
        )

    def merge_multiple(self, file_changes: Dict[str, List[TrackedChange]],
                       document_context: str = "") -> MergeResult:
        """다중 문서를 순차적으로 병합 (fold-left)"""
        files = list(file_changes.keys())
        if not files:
            return MergeResult([], [], [])
        if len(files) == 1:
            return MergeResult(accepted_changes=file_changes[files[0]],
                               rejected_changes=[], conflict_decisions=[])

        # 첫 두 문서 병합
        accumulated = self.merge_two(
            file_changes[files[0]], file_changes[files[1]],
            files[0], files[1], document_context
        )

        # 나머지 문서 순차 병합
        for fname in files[2:]:
            next_result = self.merge_two(
                accumulated.accepted_changes, file_changes[fname],
                "merged", fname, document_context
            )
            accumulated = MergeResult(
                accepted_changes=next_result.accepted_changes,
                rejected_changes=accumulated.rejected_changes + next_result.rejected_changes,
                conflict_decisions=accumulated.conflict_decisions + next_result.conflict_decisions,
                warnings=accumulated.warnings + next_result.warnings,
            )

        return accumulated

    def _resolve_conflict(self, conflict: ChangeMatch, context: str) -> MergeDecision:
        """충돌 해소"""
        if self.default_strategy == ConflictStrategy.ASK_CLAUDE and self.resolver:
            return self.resolver.resolve_conflict(conflict, context)

        return MergeDecision(
            conflict=conflict,
            strategy=self.default_strategy,
            reasoning=f"기본 전략 적용: {self.default_strategy.value}",
        )


# ─── 리포트 ────────────────────────────────────────────────────────
def format_merge_report(result: MergeResult) -> str:
    """병합 결과 리포트"""
    lines = []
    lines.append("=" * 70)
    lines.append("문서 변경사항 병합 리포트")
    lines.append("=" * 70)
    lines.append(f"\n수락: {len(result.accepted_changes)}건")
    lines.append(f"거부: {len(result.rejected_changes)}건")
    lines.append(f"충돌 해소: {len(result.conflict_decisions)}건")
    lines.append(f"경고: {len(result.warnings)}건")

    if result.conflict_decisions:
        lines.append("\n--- 충돌 해소 상세 ---")
        for d in result.conflict_decisions:
            lines.append(f"\n문단 #{d.conflict.change_a.paragraph_index}:")
            lines.append(f"  전략: {d.strategy.value}")
            lines.append(f"  근거: {d.reasoning}")
            if d.resolved_text:
                lines.append(f"  결과: {d.resolved_text[:100]}")

    if result.warnings:
        lines.append("\n--- 경고 ---")
        for w in result.warnings:
            lines.append(f"  ⚠ {w}")

    return "\n".join(lines)

"""
McKinsey-style PPT builder adapter.

GEMintern 의 슬라이드 JSON(LLM 출력 형식)을 vendored mckinsey-pptx
PresentationBuilder 의 spec 으로 매핑해 .pptx 를 생성한다.

활성 조건 (둘 중 하나):
- 환경변수 USE_MCKINSEY_PPTX=true (앱 전체 기본값 전환)
- /create-pptx 호출 시 use_mckinsey=True 플래그
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


def is_enabled_globally() -> bool:
    return os.environ.get("USE_MCKINSEY_PPTX", "").lower() in ("1", "true", "yes")


# ── slide_type/type_hint → mckinsey 템플릿 이름 매핑 ──
# planner ppt_planner.type_hint 와 기존 ppt_outline.slide_type 둘 다 흡수.
# mckinsey 50종 중 PE 워크플로에서 자주 쓰는 것 위주로 매핑.
_TYPE_MAP: Dict[str, str] = {
    # 표지·구분
    "title": "cover_slide",
    "cover": "cover_slide",
    "divider": "section_divider",
    "agenda": "agenda",
    # 요약
    "executive_summary": "executive_summary_paragraph",
    "summary": "dark_navy_summary",
    "pull_quote": "quote_slide",
    "stat_hero": "stat_hero",
    # KPI / 숫자
    "kpi_dashboard": "kpi_dashboard",
    "data_table": "assessment_table",
    "chart_table": "assessment_table",
    # 비교
    "comparison": "comparison_table",
    "two_column": "two_column_compare",
    "before_after": "before_after",
    "pros_cons": "pros_cons",
    # 매트릭스 / 리스크
    "risk_matrix": "prioritization_matrix",
    "bcg_matrix": "bcg_matrix",
    # 차트
    "column_chart": "column_comparison",
    "line_chart": "line_chart",
    "bubble_chart": "bubble_chart",
    "stacked_column": "stacked_column_chart",
    "grouped_column": "grouped_column_chart",
    # 프로세스 / 타임라인
    "timeline_flow": "phases_chevron_3",
    "process_flow": "process_flow_horizontal",
    "funnel": "funnel",
    "gantt": "gantt_timeline",
    # 조직 / 팀
    "org_chart": "org_chart",
    "team_chart": "team_chart",
    "project_team": "project_team_circles",
    # 일반 박스 류 (LLM 자유 출력 → 안전한 fallback)
    "numbered_blocks": "three_trends_numbered",
    "grid_cards": "five_key_areas",
}


def _coerce_to_spec(slide: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """LLM 슬라이드 dict → mckinsey spec dict 변환.

    슬라이드 본문 JSON 형식이 매우 다양하기 때문에, 안전하게 매핑되는
    필드만 옮기고 나머지는 텍스트로 압축해서 dark_navy_summary 등의
    fallback 으로 보낸다. 매핑 실패 시 None 반환 (호출자가 skip).
    """
    raw_type = (slide.get("slide_type") or slide.get("type_hint") or slide.get("type") or "").strip()
    mapped = _TYPE_MAP.get(raw_type)
    title = slide.get("title", "") or ""
    summary = slide.get("summary") or slide.get("subtitle") or slide.get("plan") or ""

    # 표지
    if mapped == "cover_slide":
        return {"type": "cover_slide", "title": title or "GEM Intern Deck",
                "client": slide.get("client", "")}
    # 구분
    if mapped == "section_divider":
        return {"type": "section_divider",
                "section_number": slide.get("section_number", ""),
                "section_title": title}
    # Agenda — items 가 문자열 리스트여야 함
    if mapped == "agenda":
        items = slide.get("items") or [s.get("title", "") for s in slide.get("slides", []) if isinstance(s, dict)]
        items = [str(i) for i in items if i]
        if not items:
            items = ["(빈 목차)"]
        return {"type": "agenda", "title": title or "목차", "items": items}
    # Quote
    if mapped == "quote_slide":
        return {"type": "quote_slide",
                "title": title or "",
                "quote": slide.get("quote", summary or title),
                "author": slide.get("author", "")}
    # Stat hero
    if mapped == "stat_hero":
        return {"type": "stat_hero",
                "title": title or "",
                "stat": str(slide.get("stat") or slide.get("number") or ""),
                "stat_label": slide.get("stat_label") or summary or ""}
    # Pros/Cons
    if mapped == "pros_cons":
        return {"type": "pros_cons", "title": title,
                "pros": slide.get("pros", []), "cons": slide.get("cons", [])}
    # Two column compare / before-after
    if mapped in ("two_column_compare", "before_after"):
        spec = {"type": mapped, "title": title}
        if "left_items" in slide and "right_items" in slide:
            spec["left_items"] = slide["left_items"]
            spec["right_items"] = slide["right_items"]
            spec.setdefault("left_title", slide.get("left_title", ""))
            spec.setdefault("right_title", slide.get("right_title", ""))
        else:
            # blocks/columns 류에서 추출
            blocks = slide.get("blocks") or slide.get("columns") or []
            if len(blocks) >= 2:
                spec["left_title"] = blocks[0].get("title", "Before") if isinstance(blocks[0], dict) else ""
                spec["right_title"] = blocks[1].get("title", "After") if isinstance(blocks[1], dict) else ""
                spec["left_items"] = blocks[0].get("items", []) if isinstance(blocks[0], dict) else []
                spec["right_items"] = blocks[1].get("items", []) if isinstance(blocks[1], dict) else []
            else:
                return None
        return spec
    # KPI dashboard
    if mapped == "kpi_dashboard":
        kpis = slide.get("kpis") or slide.get("metrics") or []
        if not kpis:
            return None
        return {"type": "kpi_dashboard", "title": title, "kpis": kpis}
    # Comparison table
    if mapped == "comparison_table":
        opts = slide.get("options") or []
        crit = slide.get("criteria") or []
        if not (opts and crit):
            return None
        return {"type": "comparison_table", "title": title, "options": opts, "criteria": crit}
    # Assessment / data table
    if mapped == "assessment_table":
        cats = slide.get("categories") or slide.get("rows") or []
        if not cats:
            return None
        return {"type": "assessment_table", "title": title, "categories": cats}
    # Chart 류 — categories + values 필수
    if mapped in ("column_comparison", "line_chart", "stacked_column_chart", "grouped_column_chart"):
        if "categories" not in slide:
            return None
        spec = {"type": mapped, "title": title, "categories": slide["categories"]}
        if "values" in slide: spec["values"] = slide["values"]
        if "series" in slide: spec["series"] = slide["series"]
        return spec
    # Bubble
    if mapped in ("bubble_chart", "bcg_matrix"):
        if "bubbles" not in slide and "bus" not in slide:
            return None
        return {"type": mapped, "title": title,
                **{k: slide[k] for k in ("bubbles", "bus", "x_label", "y_label") if k in slide}}
    # Prioritization (risk matrix)
    if mapped == "prioritization_matrix":
        items = slide.get("items") or []
        if not items:
            return None
        return {"type": "prioritization_matrix", "title": title, "items": items}
    # Phases / process
    if mapped == "phases_chevron_3":
        phases = slide.get("phases") or slide.get("steps") or []
        if not phases:
            return None
        return {"type": "phases_chevron_3", "title": title, "phases": phases}
    if mapped == "process_flow_horizontal":
        steps = slide.get("steps") or slide.get("phases") or []
        if not steps:
            return None
        return {"type": "process_flow_horizontal", "title": title, "steps": steps}
    if mapped == "funnel":
        stages = slide.get("stages") or []
        if not stages:
            return None
        return {"type": "funnel", "title": title, "stages": stages}
    if mapped == "gantt_timeline":
        if "weeks" not in slide or "workstreams" not in slide:
            return None
        return {"type": "gantt_timeline", "title": title,
                "weeks": slide["weeks"], "workstreams": slide["workstreams"]}
    # Org / team
    if mapped == "org_chart":
        if "branches" not in slide:
            return None
        return {"type": "org_chart", "title": title, "branches": slide["branches"]}
    if mapped == "team_chart":
        if "functions" not in slide:
            return None
        return {"type": "team_chart", "title": title, "functions": slide["functions"]}
    if mapped == "project_team_circles":
        if "leader" not in slide and "members" not in slide:
            return None
        return {"type": "project_team_circles", "title": title,
                "leader": slide.get("leader", {}), "members": slide.get("members", [])}
    # Numbered / grid (자유 박스)
    if mapped in ("three_trends_numbered", "five_key_areas"):
        items = slide.get("trends") or slide.get("areas") or slide.get("items") or slide.get("blocks") or []
        if not items:
            return None
        key = "trends" if mapped == "three_trends_numbered" else "areas"
        return {"type": mapped, "title": title, key: items}
    # Executive summary paragraph
    if mapped == "executive_summary_paragraph":
        paras = slide.get("paragraphs") or ([summary] if summary else [])
        if not paras:
            return None
        return {"type": "executive_summary_paragraph", "title": title, "paragraphs": paras}
    # Dark navy summary (fallback)
    if mapped == "dark_navy_summary":
        body = slide.get("body") or summary or title
        return {"type": "dark_navy_summary", "title": title, "body": body}

    # 매핑 실패 → 짧은 텍스트면 dark_navy_summary 로 살림, 아니면 skip
    text = summary or slide.get("body") or ""
    if title and text:
        return {"type": "dark_navy_summary", "title": title, "body": text}
    return None


def build_pptx(slides: List[Dict[str, Any]], output_path: Optional[str] = None,
               *, deck_title: str = "") -> str:
    """슬라이드 리스트 → mckinsey 스타일 .pptx 생성. output_path 반환."""
    # vendor/ 를 Python path 에 명시적으로 보장
    import sys
    repo_root = os.path.dirname(os.path.abspath(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from vendor.mckinsey_pptx.builder import PresentationBuilder  # noqa

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".pptx", prefix="mckinsey_")
        os.close(fd)

    b = PresentationBuilder()
    skipped: List[int] = []
    for i, sl in enumerate(slides):
        spec = _coerce_to_spec(sl)
        if spec is None:
            skipped.append(i)
            continue
        try:
            b.add_spec(spec)
        except Exception as e:
            logger.warning(f"[mckinsey] slide {i} 건너뜀 ({spec.get('type')}): {e}")
            skipped.append(i)
    if skipped:
        logger.info(f"[mckinsey] 매핑 실패 {len(skipped)}장 skip: {skipped[:10]}")
    b.save(output_path)
    return output_path


def smoke_test() -> str:
    """3장짜리 샘플 덱 생성 — 환경 검증용."""
    slides = [
        {"slide_type": "title", "title": "Smoke Test Deck", "client": "GEM Intern"},
        {"slide_type": "executive_summary", "title": "요약",
         "paragraphs": ["mckinsey-pptx vendor 통합 테스트.", "이 슬라이드가 보이면 OK."]},
        {"slide_type": "kpi_dashboard", "title": "지표",
         "kpis": [{"label": "매출", "value": "100억"}, {"label": "EBITDA", "value": "20억"}]},
    ]
    out = build_pptx(slides, deck_title="Smoke")
    print(f"OK: {out}")
    return out


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "--smoke":
        smoke_test()

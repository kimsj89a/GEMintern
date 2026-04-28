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


def _flatten_to_text(obj, max_chars: int = 1200) -> str:
    """슬라이드 본문에서 의미 있는 모든 텍스트 추출 → bullet-style markdown.
    fallback (dark_navy_summary) 본문 생성용. 절대 빈 문자열 반환 금지.
    """
    parts: list[str] = []

    def walk(o, depth=0):
        if depth > 5:
            return
        if isinstance(o, str):
            s = o.strip()
            if s and s not in parts:
                parts.append(s)
        elif isinstance(o, (int, float)):
            parts.append(str(o))
        elif isinstance(o, dict):
            for k, v in o.items():
                if k in ("slide_type", "type", "type_hint", "color", "chart_type"):
                    continue
                walk(v, depth + 1)
        elif isinstance(o, list):
            for it in o:
                walk(it, depth + 1)

    walk(obj)
    text = "\n• " + "\n• ".join(parts) if parts else ""
    return text[:max_chars] if len(text) > max_chars else text


def _table_to_specs(t: Dict[str, Any]) -> Dict[str, Any] | None:
    """LLM table {headers, rows} → mckinsey assessment_table {categories[{rows}]} 변환."""
    if not isinstance(t, dict):
        return None
    headers = t.get("headers") or []
    rows = t.get("rows") or []
    if not rows:
        return None
    return {"headers": [str(h) for h in headers], "rows": rows}


def _coerce_to_spec(slide: Dict[str, Any]) -> Dict[str, Any]:
    """LLM 슬라이드 dict → mckinsey spec dict 변환.

    절대 None 반환 금지 — 매핑 실패 시 dark_navy_summary 로 폴백해서
    빈 PPT가 되지 않도록 보장. (이전 버전: 매핑 실패 시 슬라이드 skip 했음)
    """
    raw_type = (slide.get("slide_type") or slide.get("type_hint") or slide.get("type") or "").strip()
    mapped = _TYPE_MAP.get(raw_type)
    title = (slide.get("title") or "").strip()
    summary = slide.get("summary") or slide.get("subtitle") or slide.get("plan") or ""

    def _fallback() -> Dict[str, Any]:
        # dark_navy_summary 는 title 인자가 없음 — body 에 prefix 형태로 합침
        body = _flatten_to_text(slide) or summary or "(내용 없음)"
        if title:
            body = f"{title}\n{body}"
        return {"type": "dark_navy_summary", "body": body, "eyebrow": title or None}

    # 표지
    if mapped == "cover_slide":
        return {"type": "cover_slide", "title": title or "GEM Intern Deck",
                "client": slide.get("client", "")}
    # 구분
    if mapped == "section_divider":
        return {"type": "section_divider",
                "section_number": slide.get("section_number", ""),
                "section_title": title}
    # Agenda
    if mapped == "agenda":
        items = slide.get("items") or [s.get("title", "") for s in slide.get("slides", []) if isinstance(s, dict)]
        items = [str(i) for i in items if i]
        if not items:
            return _fallback()
        return {"type": "agenda", "title": title or "목차", "items": items}
    # Quote
    if mapped == "quote_slide":
        q = slide.get("quote") or summary or title
        if not q:
            return _fallback()
        return {"type": "quote_slide", "title": title,
                "quote": q, "author": slide.get("author", "")}
    # Stat hero
    if mapped == "stat_hero":
        stat = str(slide.get("stat") or slide.get("number") or "")
        if not stat:
            return _fallback()
        return {"type": "stat_hero", "title": title, "stat": stat,
                "stat_label": slide.get("stat_label") or summary or ""}
    # Pros/Cons
    if mapped == "pros_cons":
        pros = slide.get("pros") or []
        cons = slide.get("cons") or []
        if not (pros or cons):
            return _fallback()
        return {"type": "pros_cons", "title": title, "pros": pros, "cons": cons}
    # Two column compare / before-after — mckinsey 인자: left_label/right_label/left_items/right_items
    if mapped in ("two_column_compare", "before_after"):
        spec: Dict[str, Any] = {"type": mapped, "title": title}
        L, R = slide.get("left"), slide.get("right")
        if isinstance(L, dict) and isinstance(R, dict):
            spec["left_label"] = L.get("title", "")
            spec["right_label"] = R.get("title", "")
            spec["left_items"] = L.get("items") or [
                " | ".join(str(c) for c in r) for r in (L.get("table", {}).get("rows") or [])
            ]
            spec["right_items"] = R.get("items") or [
                " | ".join(str(c) for c in r) for r in (R.get("table", {}).get("rows") or [])
            ]
        elif "left_items" in slide and "right_items" in slide:
            spec["left_items"] = slide["left_items"]
            spec["right_items"] = slide["right_items"]
            spec["left_label"] = slide.get("left_label") or slide.get("left_title", "")
            spec["right_label"] = slide.get("right_label") or slide.get("right_title", "")
        else:
            blocks = slide.get("blocks") or slide.get("columns") or []
            if len(blocks) >= 2 and all(isinstance(b, dict) for b in blocks[:2]):
                spec["left_label"] = blocks[0].get("title", "")
                spec["right_label"] = blocks[1].get("title", "")
                spec["left_items"] = blocks[0].get("items", [])
                spec["right_items"] = blocks[1].get("items", [])
            else:
                return _fallback()
        if not (spec.get("left_items") or spec.get("right_items")):
            return _fallback()
        return spec
    # KPI dashboard — kpis 가 정확한 형식 ([{label,value,...}]) 일 때만, 아니면 fallback
    if mapped == "kpi_dashboard":
        kpis = slide.get("kpis") or slide.get("metrics") or []
        if isinstance(kpis, list) and kpis and all(isinstance(k, dict) for k in kpis):
            return {"type": "kpi_dashboard", "title": title, "kpis": kpis}
        return _fallback()
    # Comparison table — options/criteria 가 없으면 left/right 또는 table.rows 도 시도
    if mapped == "comparison_table":
        opts = slide.get("options") or []
        crit = slide.get("criteria") or []
        if opts and crit:
            return {"type": "comparison_table", "title": title, "options": opts, "criteria": crit}
        # left/right{items} 있으면 pros_cons 로 다운그레이드 매핑
        L, R = slide.get("left"), slide.get("right")
        if isinstance(L, dict) and isinstance(R, dict) and (L.get("items") or R.get("items")):
            return {"type": "pros_cons", "title": title,
                    "pros": L.get("items", []), "cons": R.get("items", [])}
        return _fallback()
    # Assessment table — mckinsey 는 KPI/target/actual/status 라는 매우 특수한 형식만 받음.
    # LLM 의 일반 table {headers, rows} 와 schema 충돌 → dark_navy_summary 로 안전하게 폴백.
    # categories 가 mckinsey 형식 그대로일 때만 직접 사용.
    if mapped == "assessment_table":
        cats = slide.get("categories")
        if (isinstance(cats, list) and cats and isinstance(cats[0], dict)
                and "rows" in cats[0] and isinstance(cats[0]["rows"], list)
                and cats[0]["rows"] and isinstance(cats[0]["rows"][0], dict)
                and "kpi" in cats[0]["rows"][0]):
            return {"type": "assessment_table", "title": title, "categories": cats}
        return _fallback()
    # Chart 류 — categories + values/series 흡수 (chart.{categories,series} 도)
    if mapped in ("column_comparison", "line_chart", "stacked_column_chart", "grouped_column_chart"):
        chart = slide.get("chart") if isinstance(slide.get("chart"), dict) else slide
        cats = chart.get("categories")
        if not cats:
            return _fallback()
        spec = {"type": mapped, "title": title, "categories": cats}
        if "values" in chart: spec["values"] = chart["values"]
        if "series" in chart: spec["series"] = chart["series"]
        return spec
    # Bubble
    if mapped in ("bubble_chart", "bcg_matrix"):
        if "bubbles" not in slide and "bus" not in slide:
            return _fallback()
        return {"type": mapped, "title": title,
                **{k: slide[k] for k in ("bubbles", "bus", "x_label", "y_label") if k in slide}}
    # Prioritization / risk matrix — risks[] 도 흡수
    if mapped == "prioritization_matrix":
        items = slide.get("items") or slide.get("risks") or []
        if not items:
            return _fallback()
        return {"type": "prioritization_matrix", "title": title, "items": items}
    # Phases / process — nodes[] 도 흡수
    if mapped == "phases_chevron_3":
        phases = slide.get("phases") or slide.get("steps") or slide.get("nodes") or []
        if not phases:
            return _fallback()
        return {"type": "phases_chevron_3", "title": title, "phases": phases}
    if mapped == "process_flow_horizontal":
        steps = slide.get("steps") or slide.get("phases") or slide.get("nodes") or []
        if not steps:
            return _fallback()
        return {"type": "process_flow_horizontal", "title": title, "steps": steps}
    if mapped == "funnel":
        stages = slide.get("stages") or []
        if not stages:
            return _fallback()
        return {"type": "funnel", "title": title, "stages": stages}
    if mapped == "gantt_timeline":
        if "weeks" not in slide or "workstreams" not in slide:
            return _fallback()
        return {"type": "gantt_timeline", "title": title,
                "weeks": slide["weeks"], "workstreams": slide["workstreams"]}
    # Org / team
    if mapped == "org_chart":
        if "branches" not in slide:
            return _fallback()
        return {"type": "org_chart", "title": title, "branches": slide["branches"]}
    if mapped == "team_chart":
        if "functions" not in slide:
            return _fallback()
        return {"type": "team_chart", "title": title, "functions": slide["functions"]}
    if mapped == "project_team_circles":
        if "leader" not in slide and "members" not in slide:
            return _fallback()
        return {"type": "project_team_circles", "title": title,
                "leader": slide.get("leader", {}), "members": slide.get("members", [])}
    # Numbered / grid — blocks[{number,title,description}] 또는 cards[]
    if mapped in ("three_trends_numbered", "five_key_areas"):
        items = (slide.get("trends") or slide.get("areas") or
                 slide.get("items") or slide.get("blocks") or slide.get("cards") or [])
        if not items:
            return _fallback()
        key = "trends" if mapped == "three_trends_numbered" else "areas"
        return {"type": mapped, "title": title, key: items}
    # Executive summary
    if mapped == "executive_summary_paragraph":
        paras = slide.get("paragraphs") or ([summary] if summary else [])
        if not paras:
            return _fallback()
        return {"type": "executive_summary_paragraph", "title": title, "paragraphs": paras}
    # Dark navy summary
    if mapped == "dark_navy_summary":
        body = slide.get("body") or summary or _flatten_to_text(slide) or title
        return {"type": "dark_navy_summary", "title": title or "Untitled", "body": body}

    # 매핑 자체가 실패 → 항상 fallback (절대 None 반환 X)
    return _fallback()


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
    rendered = 0
    for i, sl in enumerate(slides):
        spec = _coerce_to_spec(sl)  # never None now
        try:
            b.add_spec(spec)
            rendered += 1
        except Exception as e:
            # mckinsey 템플릿 자체에서 reject — 최후의 fallback (반드시 dark_navy_summary)
            logger.warning(f"[mckinsey] slide {i} ({spec.get('type')}) failed: {e} — rendering as dark_navy_summary")
            try:
                b.add_spec({"type": "dark_navy_summary",
                            "title": str(sl.get("title") or f"Slide {i+1}")[:80],
                            "body": _flatten_to_text(sl) or "(렌더링 실패)"})
                rendered += 1
            except Exception as e2:
                logger.error(f"[mckinsey] slide {i} dark_navy_summary fallback도 실패: {e2}")
    if rendered == 0:
        raise RuntimeError("렌더링된 슬라이드 0장 — mckinsey-pptx 템플릿 호출이 모두 실패했습니다.")
    b.save(output_path)
    logger.info(f"[mckinsey] {rendered}/{len(slides)} 슬라이드 빌드 완료 → {output_path}")
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

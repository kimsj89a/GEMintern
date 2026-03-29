"""
Review Workflow — 투자검토 워크플로 (RFI 추출 + 교차검증).
위키 내용을 분석하여 미비사항을 추출하고, 원본 소스와 교차검증한다.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

import prompts
from ai_client import get_client
from google.genai import types

logger = logging.getLogger(__name__)


# ── RFI Extraction ───────────────────────────────────────

def extract_rfi_from_wiki(api_key: str, model_name: str,
                          project_name: str, owner_id: int | None = None) -> dict:
    """위키 내용을 분석하여 Q&A/RFI 항목을 추출한다."""
    import core_wiki

    wiki = core_wiki.load_wiki(project_name, owner_id=owner_id)
    if not wiki or not wiki.get("sections"):
        return {"items": [], "error": "위키가 없습니다. 먼저 위키를 생성해주세요."}

    # 위키 전체 텍스트 구성
    wiki_text = ""
    for sec in wiki["sections"]:
        wiki_text += f"\n## {sec['title']}\n{sec['content']}\n"

    client = get_client(api_key)
    prompt = f"""{prompts.REVIEW_WORKFLOW_PROMPTS['extract_rfi']}

[위키 전문]
{wiki_text[:100000]}
"""

    resp = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8192,
        ),
    )

    # JSON 파싱
    items = _parse_json_array(resp.text)
    # id 부여
    for i, item in enumerate(items):
        item["id"] = f"rfi_{i+1:03d}"
        item.setdefault("status", "unresolved")

    return {"items": items}


# ── Cross-check ──────────────────────────────────────────

def crosscheck_rfi(api_key: str, model_name: str,
                   project_name: str, items: List[dict],
                   owner_id: int | None = None) -> dict:
    """RFI 항목을 원본 소스 문서와 교차검증한다."""
    from core_rag import load_project_docs_dict, _get_storage_name

    if not items:
        return {"items": []}

    storage = _get_storage_name(project_name, owner_id=owner_id)
    docs = load_project_docs_dict(storage)
    if not docs:
        return {"items": [{"id": it.get("id", ""), "question": it.get("question", ""),
                           "coverage": "gap", "explanation": "프로젝트에 소스 문서가 없습니다."}
                          for it in items]}

    # 소스 문서 컨텍스트 구성 (축약)
    doc_context = _build_doc_summary(docs, budget=150000)

    # 전체 항목을 한 번에 검증 (항목이 적으면 효율적)
    items_text = "\n".join(
        f"- [{it.get('id', '')}] {it.get('question', '')}" for it in items
    )

    client = get_client(api_key)
    prompt = f"""{prompts.REVIEW_WORKFLOW_PROMPTS['crosscheck']}

[검증 대상 항목]
{items_text}

[소스 문서]
{doc_context}
"""

    resp = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=12000,
        ),
    )

    results = _parse_json_array(resp.text)

    # 원본 항목과 매핑
    result_map = {r.get("id", ""): r for r in results}
    merged = []
    for it in items:
        rid = it.get("id", "")
        r = result_map.get(rid, {})
        merged.append({
            "id": rid,
            "question": it.get("question", ""),
            "category": it.get("category", ""),
            "priority": it.get("priority", "중"),
            "coverage": r.get("coverage", "gap"),
            "source_doc": r.get("source_doc", ""),
            "source_excerpt": r.get("source_excerpt", ""),
            "explanation": r.get("explanation", ""),
        })

    # 요약 통계
    covered = sum(1 for m in merged if m["coverage"] == "covered")
    partial = sum(1 for m in merged if m["coverage"] == "partial")
    gap = sum(1 for m in merged if m["coverage"] == "gap")

    return {
        "items": merged,
        "summary": {"total": len(merged), "covered": covered, "partial": partial, "gap": gap},
    }


# ── External RFI Document Generation ─────────────────────

def generate_external_rfi(api_key: str, model_name: str,
                          gap_items: List[dict],
                          project_name: str = "",
                          owner_id: int | None = None) -> dict:
    """미커버/부분커버 항목을 기반으로 외부 자료 요청 문서를 생성한다."""
    if not gap_items:
        return {"rfi_document": "요청할 항목이 없습니다."}

    items_text = ""
    for i, it in enumerate(gap_items, 1):
        cov = it.get("coverage", "gap")
        cov_label = "미제출" if cov == "gap" else "확인 필요"
        items_text += f"{i}. [{cov_label}] {it.get('question', '')}\n"
        if it.get("explanation"):
            items_text += f"   비고: {it['explanation']}\n"

    client = get_client(api_key)
    prompt = f"""{prompts.REVIEW_WORKFLOW_PROMPTS['external_rfi']}

[요청 대상 항목]
{items_text}
"""

    resp = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=8192,
        ),
    )

    return {"rfi_document": resp.text or ""}


# ── Helpers ──────────────────────────────────────────────

def _build_doc_summary(docs: Dict[str, str], budget: int = 150000) -> str:
    """소스 문서를 번호 매겨서 컨텍스트로 구성."""
    doc_list = list(docs.items())
    n = len(doc_list)
    per_doc = max(2000, budget // max(n, 1))
    parts = []
    for i, (name, content) in enumerate(doc_list, 1):
        truncated = content[:per_doc] if len(content) > per_doc else content
        parts.append(f"[DOC-{i}] {name}\n{truncated}")
    return "\n\n---\n\n".join(parts)


def _parse_json_array(text: str) -> list:
    """AI 응답에서 JSON 배열 추출. 여러 전략으로 시도."""
    if not text:
        return []
    # 1) markdown fence
    m = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 2) 직접 파싱
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "items" in parsed:
            return parsed["items"]
    except json.JSONDecodeError:
        pass
    # 3) 가장 바깥 [] 찾기
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return []

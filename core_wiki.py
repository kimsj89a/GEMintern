"""
Wiki generation for GEM Intern projects.
Analyzes project documents via RAG and generates structured wiki with citations.
"""
import datetime
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional

from core_rag import (
    _get_project_dir,
    _get_storage_name,
    load_project_docs_dict,
)

logger = logging.getLogger(__name__)

DEFAULT_SECTIONS = [
    {"id": "deal_overview", "title": "Deal Overview", "desc": "거래 개요, 투자 구조, 금액"},
    {"id": "market_analysis", "title": "Market Analysis", "desc": "시장 규모, 트렌드, 경쟁 환경"},
    {"id": "company_overview", "title": "Company Overview", "desc": "회사 소개, 연혁, 핵심 제품/서비스"},
    {"id": "investment_thesis", "title": "Investment Thesis", "desc": "투자 논거, 성장 전략"},
    {"id": "financial_overview", "title": "Financial Overview", "desc": "재무 현황, 매출, 수익성"},
    {"id": "risk_analysis", "title": "Risk Analysis", "desc": "리스크 요인, 완화 방안"},
    {"id": "exit_strategy", "title": "Exit Strategy", "desc": "Exit 전략, IPO/M&A 전망"},
    {"id": "deal_timeline", "title": "Deal Timeline", "desc": "주요 일정, 마일스톤"},
    {"id": "reference", "title": "Reference Materials", "desc": "참고 자료 목록"},
]

# Per-doc truncation limit when building source context
_DOC_BUDGET = 15000


def _wiki_path(project_name: str) -> str:
    return os.path.join(_get_project_dir(project_name), "_wiki.json")


# ── Load / Save ──────────────────────────────────────────

def load_wiki(project_name: str, owner_id: int | None = None) -> Optional[dict]:
    storage = _get_storage_name(project_name, owner_id=owner_id)
    path = _wiki_path(storage)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None


def save_wiki(project_name: str, wiki_data: dict, owner_id: int | None = None):
    storage = _get_storage_name(project_name, owner_id=owner_id)
    path = _wiki_path(storage)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(wiki_data, f, ensure_ascii=False, indent=2)


# ── Generation ───────────────────────────────────────────

def _build_source_context(docs: Dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    """Build numbered source text from project docs.
    Returns (formatted_text, [(doc_name, full_content), ...]).
    """
    doc_list = list(docs.items())
    parts = []
    for i, (name, content) in enumerate(doc_list, 1):
        truncated = content[:_DOC_BUDGET] if len(content) > _DOC_BUDGET else content
        parts.append(f"[DOC-{i}] {name}\n{truncated}")
    return "\n\n---\n\n".join(parts), doc_list


def generate_wiki(
    api_key: str,
    project_name: str,
    owner_id: int | None = None,
    sections: list | None = None,
) -> dict:
    """Generate full wiki from project documents using Gemini."""
    from ai_client import AIClient
    from google.genai import types

    docs = load_project_docs_dict(project_name, owner_id=owner_id)
    if not docs:
        return {"error": "프로젝트에 문서가 없습니다."}

    source_text, doc_list = _build_source_context(docs)
    section_defs = sections or DEFAULT_SECTIONS
    sections_desc = "\n".join(
        f"- {s['id']}: {s['title']} ({s.get('desc', '')})" for s in section_defs
    )

    prompt = f"""당신은 투자 분석 전문가입니다. 아래 프로젝트 자료를 분석하여 위키를 작성하세요.

## 프로젝트 자료
{source_text}

## 작성할 섹션
{sections_desc}

## 지시사항
1. 각 섹션의 내용을 자료에 기반하여 한국어로 작성하세요.
2. 모든 정보에 출처를 표기하세요. 출처는 각주 번호 [1], [2], ... 형식으로 인라인 삽입합니다.
3. 자료에 없는 내용은 절대 작성하지 마세요.
4. 해당 섹션에 관련 자료가 없으면 content를 "관련 자료 없음"으로 표시하세요.
5. citations 배열에 각 각주의 상세 정보를 반드시 포함하세요.

## 출력 (JSON만 출력)
```json
{{
  "sections": [
    {{
      "id": "section_id",
      "title": "섹션 제목",
      "content": "분석 내용 [1] 추가 내용 [2] ..."
    }}
  ],
  "citations": [
    {{
      "id": 1,
      "doc_ref": 1,
      "excerpt": "원문에서 발췌한 1-2문장"
    }}
  ]
}}
```"""

    client = AIClient(api_key)
    model = "gemini-2.5-flash-preview-05-20"
    config = types.GenerateContentConfig(temperature=0.2, max_output_tokens=16384)

    try:
        resp = client.models.generate_content(model=model, contents=prompt, config=config)
    except Exception as e:
        logger.error(f"Wiki generation API error: {e}")
        return {"error": f"AI 호출 실패: {e}"}

    raw = resp.text.strip()
    # Strip markdown code fence if present
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"Wiki JSON parse failed: {raw[:500]}")
        return {"error": "AI 응답 파싱 실패", "raw": raw[:2000]}

    # Map doc_ref (1-based index) → actual filename
    citations = []
    for c in result.get("citations", []):
        doc_idx = int(c.get("doc_ref", 0)) - 1
        source_doc = doc_list[doc_idx][0] if 0 <= doc_idx < len(doc_list) else "unknown"
        citations.append({
            "id": c["id"],
            "source_doc": source_doc,
            "page": None,
            "excerpt": c.get("excerpt", ""),
        })

    now = datetime.datetime.utcnow().isoformat() + "Z"
    wiki_data = {
        "sections": [
            {
                "id": s.get("id", f"section_{i}"),
                "title": s.get("title", f"Section {i + 1}"),
                "content": s.get("content", ""),
                "order": i,
                "auto_generated": True,
                "updated_at": now,
            }
            for i, s in enumerate(result.get("sections", []))
        ],
        "citations": citations,
        "template": "investment",
        "generated_at": now,
    }

    save_wiki(project_name, wiki_data, owner_id=owner_id)
    return wiki_data


def update_wiki(
    api_key: str,
    project_name: str,
    owner_id: int | None = None,
) -> dict:
    """Re-generate wiki incorporating any new documents."""
    existing = load_wiki(project_name, owner_id=owner_id)
    if not existing:
        return generate_wiki(api_key, project_name, owner_id=owner_id)

    # Preserve user-customized sections (auto_generated=False)
    custom_sections = [s for s in existing.get("sections", []) if not s.get("auto_generated", True)]
    section_defs = [
        {"id": s["id"], "title": s["title"], "desc": ""}
        for s in existing["sections"]
        if s.get("auto_generated", True)
    ]
    if not section_defs:
        section_defs = DEFAULT_SECTIONS

    result = generate_wiki(api_key, project_name, owner_id=owner_id, sections=section_defs)
    if "error" in result:
        return result

    # Merge: auto-generated + custom
    max_order = max((s["order"] for s in result["sections"]), default=-1)
    for cs in custom_sections:
        max_order += 1
        cs["order"] = max_order
        result["sections"].append(cs)

    save_wiki(project_name, result, owner_id=owner_id)
    return result


def suggest_sections(
    api_key: str,
    project_name: str,
    owner_id: int | None = None,
) -> list:
    """Ask Gemini to suggest wiki sections based on document content."""
    from ai_client import AIClient
    from google.genai import types

    docs = load_project_docs_dict(project_name, owner_id=owner_id)
    if not docs:
        return DEFAULT_SECTIONS

    # Brief summary of each doc
    summaries = []
    for name, content in list(docs.items())[:20]:
        summaries.append(f"- {name}: {content[:300]}...")

    prompt = f"""다음 프로젝트 자료 목록을 보고, 이 프로젝트에 적합한 위키 섹션 구조를 제안하세요.

## 자료 목록
{chr(10).join(summaries)}

## 기본 템플릿 (참고용)
{json.dumps(DEFAULT_SECTIONS, ensure_ascii=False)}

## 지시사항
- 자료 내용에 맞게 섹션을 추가/수정/제거하세요.
- id는 영문 snake_case, title은 한국어 또는 영어 혼용 가능.
- 5~12개 섹션이 적당합니다.

## 출력 (JSON 배열만)
```json
[{{"id": "...", "title": "...", "desc": "..."}}]
```"""

    client = AIClient(api_key)
    config = types.GenerateContentConfig(temperature=0.3, max_output_tokens=4096)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20", contents=prompt, config=config
        )
        raw = resp.text.strip()
        m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"suggest_sections failed: {e}")
        return DEFAULT_SECTIONS


def update_section(
    project_name: str,
    section_id: str,
    updates: dict,
    owner_id: int | None = None,
) -> dict:
    """Update a single wiki section (title, content, order)."""
    wiki = load_wiki(project_name, owner_id=owner_id)
    if not wiki:
        return {"error": "위키가 없습니다. 먼저 생성하세요."}

    for s in wiki["sections"]:
        if s["id"] == section_id:
            if "title" in updates:
                s["title"] = updates["title"]
            if "content" in updates:
                s["content"] = updates["content"]
                s["auto_generated"] = False
            if "order" in updates:
                s["order"] = updates["order"]
            s["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
            save_wiki(project_name, wiki, owner_id=owner_id)
            return wiki
    return {"error": f"섹션 '{section_id}'를 찾을 수 없습니다."}


def add_section(
    project_name: str,
    section_id: str,
    title: str,
    content: str = "",
    owner_id: int | None = None,
) -> dict:
    """Add a new section to the wiki."""
    wiki = load_wiki(project_name, owner_id=owner_id)
    if not wiki:
        return {"error": "위키가 없습니다. 먼저 생성하세요."}

    if any(s["id"] == section_id for s in wiki["sections"]):
        return {"error": f"'{section_id}' 섹션이 이미 존재합니다."}

    max_order = max((s["order"] for s in wiki["sections"]), default=-1)
    now = datetime.datetime.utcnow().isoformat() + "Z"
    wiki["sections"].append({
        "id": section_id,
        "title": title,
        "content": content,
        "order": max_order + 1,
        "auto_generated": False,
        "updated_at": now,
    })
    save_wiki(project_name, wiki, owner_id=owner_id)
    return wiki


def delete_section(
    project_name: str,
    section_id: str,
    owner_id: int | None = None,
) -> dict:
    """Remove a section from the wiki."""
    wiki = load_wiki(project_name, owner_id=owner_id)
    if not wiki:
        return {"error": "위키가 없습니다."}

    before = len(wiki["sections"])
    wiki["sections"] = [s for s in wiki["sections"] if s["id"] != section_id]
    if len(wiki["sections"]) == before:
        return {"error": f"섹션 '{section_id}'를 찾을 수 없습니다."}

    save_wiki(project_name, wiki, owner_id=owner_id)
    return wiki

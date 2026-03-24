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

# Total context budget for wiki generation (characters)
_TOTAL_BUDGET = 200_000


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
    logger.info(f"save_wiki: storage={storage}, path={path}")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(wiki_data, f, ensure_ascii=False, indent=2)
        logger.info(f"save_wiki: OK, size={os.path.getsize(path)}")
    except Exception as e:
        logger.error(f"save_wiki FAILED: {e}")
        # Fallback: try saving directly under project name
        fallback = _wiki_path(project_name)
        logger.info(f"save_wiki fallback: {fallback}")
        os.makedirs(os.path.dirname(fallback), exist_ok=True)
        with open(fallback, "w", encoding="utf-8") as f:
            json.dump(wiki_data, f, ensure_ascii=False, indent=2)


# ── Generation ───────────────────────────────────────────

def _build_source_context(docs: Dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    """Build numbered source text from project docs.
    Returns (formatted_text, [(doc_name, full_content), ...]).
    Dynamically allocates per-doc budget based on total doc count.
    """
    doc_list = list(docs.items())
    n = len(doc_list)
    per_doc = max(2000, _TOTAL_BUDGET // max(n, 1))
    parts = []
    for i, (name, content) in enumerate(doc_list, 1):
        truncated = content[:per_doc] if len(content) > per_doc else content
        parts.append(f"[DOC-{i}] {name}\n{truncated}")
    return "\n\n---\n\n".join(parts), doc_list


def _get_model() -> str:
    """Read model name from settings.json, matching the rest of the app."""
    try:
        import json as _json
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                return _json.load(f).get("model_name", "") or "gemini-2.5-flash"
    except Exception:
        pass
    return "gemini-2.5-flash"


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

## 서식 규칙 (반드시 준수)
- 취소선(~~)은 절대 사용하지 마세요.
- 재무 데이터(매출, 이익, 자산, 부채 등 숫자가 포함된 항목)는 반드시 마크다운 표(| 헤더 | ... |)로 작성하세요.
- Financial Overview 섹션은 표를 메인으로 구성하고, 표 아래에 핵심 설명을 간결하게 추가하세요. 예: 손익 요약 표 → 설명, 재무상태 요약 표 → 설명 순서.
- 각 문장/항목 사이에 빈 줄을 넣어 문단을 구분하세요. 한 문단에 너무 많은 내용을 넣지 마세요.
- 나열 항목은 불릿 리스트(- 항목) 또는 번호 리스트(1. 항목)를 사용하세요.

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
    model = _get_model()
    # 위키 생성은 thinking 끄고 빠르게
    config = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=16384,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    try:
        logger.info(f"Wiki generate: model={model}, docs={len(docs)}, prompt_len={len(prompt)}")
        resp = client.models.generate_content(model=model, contents=prompt, config=config)
        logger.info(f"Wiki generate: response received, len={len(resp.text)}")
    except Exception as e:
        logger.error(f"Wiki generation API error: {e}")
        return {"error": f"AI 호출 실패: {e}"}

    raw = resp.text.strip()
    # Try multiple extraction strategies
    result = None
    # 1) Markdown code fence
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # 2) Direct parse
    if result is None:
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            pass
    # 3) Find outermost { ... }
    if result is None:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                result = json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
    if result is None:
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

    # Post-process: strip strikethrough markers
    for s in result.get("sections", []):
        if "content" in s:
            s["content"] = re.sub(r"~~(.*?)~~", r"\1", s["content"])

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
            model=_get_model(), contents=prompt, config=config
        )
        raw = resp.text.strip()
        m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
        return json.loads(raw)
    except Exception as e:
        logger.error(f"suggest_sections failed: {e}")
        return DEFAULT_SECTIONS


def revise_section(
    api_key: str,
    project_name: str,
    section_id: str,
    instruction: str,
    owner_id: int | None = None,
) -> dict:
    """AI로 특정 섹션을 수정 지시에 따라 다시 작성."""
    from ai_client import AIClient
    from google.genai import types

    wiki = load_wiki(project_name, owner_id=owner_id)
    if not wiki:
        return {"error": "위키가 없습니다."}

    section = None
    for s in wiki["sections"]:
        if s["id"] == section_id:
            section = s
            break
    if not section:
        return {"error": f"섹션 '{section_id}'를 찾을 수 없습니다."}

    # 프로젝트 문서 로드 (출처 참조용)
    docs = load_project_docs_dict(project_name, owner_id=owner_id)
    doc_list = list(docs.items())
    n = len(doc_list)
    per_doc = max(2000, _TOTAL_BUDGET // max(n, 1))
    source_brief = "\n".join(
        f"[DOC-{i+1}] {name}\n{content[:per_doc]}"
        for i, (name, content) in enumerate(doc_list)
    )

    prompt = f"""아래 위키 섹션을 수정 지시에 따라 다시 작성하세요.

## 섹션: {section['title']}
### 현재 내용
{section['content']}

## 프로젝트 자료 (출처 참조용)
{source_brief}

## 수정 지시
{instruction}

## 규칙
- 출처 각주 [1], [2] 등을 유지하세요. 새 출처 추가 시 기존 번호 이후로 부여하세요.
- 취소선(~~)은 사용하지 마세요.
- 재무 데이터는 마크다운 표로 작성하세요.
- 항목별 줄바꿈을 해주세요.

## 출력 (JSON만)
```json
{{
  "content": "수정된 섹션 내용",
  "new_citations": [
    {{"id": 번호, "doc_ref": DOC번호, "excerpt": "발췌"}}
  ]
}}
```"""

    client = AIClient(api_key)
    model = _get_model()
    config = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=8192,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    try:
        resp = client.models.generate_content(model=model, contents=prompt, config=config)
    except Exception as e:
        return {"error": f"AI 호출 실패: {e}"}

    raw = resp.text.strip()
    result = None
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    if result is None:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                result = json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                pass
    if result is None:
        return {"error": "AI 응답 파싱 실패"}

    # 섹션 업데이트
    new_content = re.sub(r"~~(.*?)~~", r"\1", result.get("content", section["content"]))
    section["content"] = new_content
    section["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    # 새 citations 추가
    for nc in result.get("new_citations", []):
        doc_idx = int(nc.get("doc_ref", 0)) - 1
        source_doc = doc_list[doc_idx][0] if 0 <= doc_idx < len(doc_list) else "unknown"
        wiki["citations"].append({
            "id": nc["id"],
            "source_doc": source_doc,
            "page": None,
            "excerpt": nc.get("excerpt", ""),
        })

    save_wiki(project_name, wiki, owner_id=owner_id)
    return wiki


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

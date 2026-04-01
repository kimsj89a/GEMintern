"""
Contract comparison module for GEM Intern.
Compares Termsheet vs contract drafts (SSA/SHA) and generates
structured comparison report with article-level matching.
"""
import logging
from typing import Optional

from ai_client import get_client
from google.genai import types

logger = logging.getLogger(__name__)


def compare_contracts(
    api_key: str,
    model_name: str,
    project_name: str,
    owner_id: int | None = None,
    selected_docs: list | None = None,
) -> str:
    """Compare termsheet vs contract drafts using AI.

    Loads project documents, sends to AI with comparison prompt,
    returns structured markdown report.
    """
    from core_rag import load_project_docs_dict, _get_storage_name
    from core_wiki import load_wiki
    from prompts import CONTRACT_COMPARE_PROMPTS

    # Load wiki for context
    wiki_text = ""
    wiki = load_wiki(project_name, owner_id=owner_id)
    if wiki and wiki.get("sections"):
        parts = []
        for sec in wiki["sections"]:
            parts.append(f"## {sec.get('title', '')}\n{sec.get('content', '')}")
        wiki_text = "\n\n".join(parts)

    # Load source docs
    docs = load_project_docs_dict(project_name, owner_id=owner_id)
    if selected_docs:
        import os
        def _stem(name: str) -> str:
            n = name
            if n.endswith('.md'):
                n = n[:-3]
            return os.path.splitext(n)[0]
        sel_stems = {_stem(s) for s in selected_docs}
        docs = {k: v for k, v in docs.items()
                if _stem(k) in sel_stems or k in selected_docs}

    if not docs:
        raise ValueError("비교할 문서가 없습니다. 프로젝트에 텀싯과 계약서를 업로드해 주세요.")

    # Build document context with labels
    doc_budget = 200_000
    per_doc = max(5000, doc_budget // max(len(docs), 1))
    doc_parts = []
    for i, (fname, content) in enumerate(sorted(docs.items()), 1):
        display = fname.replace('.md', '').replace('.txt', '')
        truncated = content[:per_doc]
        doc_parts.append(f"[DOC-{i}] {display}\n{truncated}")
    doc_text = ("\n\n" + "=" * 60 + "\n\n").join(doc_parts)

    # Build user prompt
    wiki_section = f"[위키 요약]\n{wiki_text}\n\n" if wiki_text else ""
    user_content = f"""{wiki_section}[제공 문서 ({len(docs)}건)]

{doc_text}

위 문서들을 분석하여 신구조문 비교표를 작성하십시오.
프로젝트명: {project_name}
"""

    system_prompt = CONTRACT_COMPARE_PROMPTS["compare"]

    client = get_client(api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            max_output_tokens=16384,
        ),
    )

    result = response.text if hasattr(response, "text") else str(response)
    if not result or len(result.strip()) < 50:
        raise ValueError("AI가 비교 분석 결과를 생성하지 못했습니다.")

    return result

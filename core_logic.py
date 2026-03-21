from google.genai import types
from ai_client import AIClient, get_client
import utils
import core_rfi
import core_chained
import core_im
import core_rag
import prompts

def extract_structure(api_key, structure_file):
    try:
        client = get_client(api_key)
        file_text = utils.parse_uploaded_file(structure_file, api_key=api_key)
        prompt = f"{prompts.LOGIC_PROMPTS['structure_extraction']}\n[파일 내용]\n{file_text[:15000]}"
        resp = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return resp.text
    except Exception as e:
        return f"구조 추출 오류: {str(e)}"

def parse_all_files(uploaded_files, saved_files=None, read_content=True, api_key=None, docai_config=None, template_option=None):
    """파일 목록 파싱 및 로컬 저장/로드

    Args:
        uploaded_files: 업로드된 파일 목록
        saved_files: 로컬에 저장된 파일명 목록 (선택됨)
        read_content: 파일 내용 읽기 여부
        api_key: Google API 키 (Gemini OCR용)
        docai_config: Document AI 설정 (선택사항)
    """
    all_text = ""
    file_list_str = ""

    # 1. 새로 업로드된 파일 처리 (파싱 -> 저장 -> 텍스트 추가)
    if uploaded_files:
        for file in uploaded_files:
            file_list_str += f"- [New] {file.name}\n"
            if read_content:
                parsed = utils.parse_uploaded_file(
                    file,
                    api_key=api_key,
                    docai_config=docai_config,
                    template_option=template_option,
                )
                utils.save_to_local_storage(file.name, parsed)
                all_text += parsed

    # 2. 저장된 파일 불러오기 (로드 -> 텍스트 추가)
    if saved_files and read_content:
        for fname in saved_files:
            file_list_str += f"- [Saved] {fname}\n"
            content = utils.load_saved_doc(fname)
            all_text += f"\n\n{content}\n"

    if not read_content:
        all_text = "(RFI 모드: 내용은 읽지 않음)"

    return all_text, file_list_str


def get_rag_enriched_context(api_key, structure_text, context_text, project_name, template_option):
    """RAG를 사용하여 보고서 생성에 필요한 추가 컨텍스트를 검색합니다."""
    return core_rag.enrich_context_with_rag(
        api_key=api_key,
        structure_text=structure_text,
        context_text=context_text,
        project_name=project_name,
        template_option=template_option,
    )

def get_default_structure(template_key):
    return prompts.TEMPLATE_STRUCTURES.get(template_key, "")

def _get_system_prompt(template_opt):
    """템플릿별 시스템 프롬프트 반환"""
    prompt_map = {
        'simple_review': 'simple_review_system',
        'investment': 'investment_system',
        'im': 'im_full_system',
        'im_full': 'im_full_system',
        'management': 'management_system',
        'presentation': 'ppt_system',
        'paper_review': 'paper_review_system',
        'free_summary': 'free_summary_system',
        'context_based': 'context_based_system',
        'custom': 'custom_system',
        'teaser': 'teaser_system',
        'term_sheet': 'term_sheet_system',
        'loi_mou': 'loi_mou_system',
        'dd_report': 'dd_report_system',
    }
    prompt_key = prompt_map.get(template_opt, 'custom_system')
    return prompts.LOGIC_PROMPTS.get(prompt_key, prompts.LOGIC_PROMPTS['custom_system'])

def generate_report_stream(api_key, model_name, inputs, thinking_level, file_context):
    """Single-pass generation mode for all templates."""
    client = get_client(api_key)
    template_opt = inputs.get('template_option', 'free_summary')
    structure_text = inputs.get('structure_text', get_default_structure(template_opt))

    # [RFI Mode] - 별도 처리
    if template_opt == 'rfi':
        stream = core_rfi.generate_rfi_stream(api_key, model_name, inputs, thinking_level, file_context)
        for chunk in stream:
            yield chunk
        return

    # [IM Full Mode] - IM chained 생성
    if template_opt == 'im_full':
        for chunk in core_im.generate_im_chained_stream(
            api_key, model_name, inputs, thinking_level, file_context,
            investment_type=inputs.get('investment_type', 'Growth')
        ):
            yield chunk
        return

    # 템플릿별 시스템 프롬프트 가져오기
    system_instruction = _get_system_prompt(template_opt)

    # 도식화 옵션 추가
    if inputs.get('use_diagram'):
        system_instruction += "\n**도식화**: 필요시 {{DIAGRAM: 설명}} 태그 삽입."

    # Main prompt composition
    thinking_label = thinking_level.upper() if isinstance(thinking_level, str) else "HIGH"
    main_prompt = f"""
[System: Thinking Level {thinking_label}]
[Critical Instruction] Analyze the provided data deeply and step-by-step. Prioritize accuracy and logical consistency.
[Format Instruction] 서문, 인트로, 설명 문장 없이 바로 마크다운 본문(# 헤딩)으로 시작하세요. "~를 작성합니다", "~를 분석하여", "~를 검토합니다" 등의 도입부를 절대 쓰지 마세요. 첫 줄부터 # 제목으로 시작하세요.

[Document Structure]
{structure_text}

[User Context]
{inputs.get('context_text', '')}

[Source Data]
{file_context}
"""

    # 템플릿별 config 설정
    if template_opt == 'presentation' or template_opt == 'paper_review':
        temperature = 0.7
    elif template_opt in ('custom', 'context_based'):
        temperature = 0.7  # 자유 구조화/컨텍스트 기반 모드 - 유연한 작성을 위해 높은 temperature
    else:
        temperature = 0.3

    config = types.GenerateContentConfig(
        max_output_tokens=65536,
        temperature=temperature,
        system_instruction=system_instruction
    )

    # Generate Stream
    response_stream = client.models.generate_content_stream(
        model=model_name,
        contents=main_prompt,
        config=config
    )

    for chunk in response_stream:
        yield chunk

def generate_report_stream_chained(api_key, model_name, inputs, thinking_level, file_context):
    """Chained prompting via core_chained."""
    template_option = inputs.get('template_option', 'investment')

    # core_chained 모듈의 일반화된 함수 사용
    for chunk in core_chained.generate_chained_stream(
        api_key=api_key,
        model_name=model_name,
        inputs=inputs,
        thinking_level=thinking_level,
        file_context=file_context,
        template_option=template_option
    ):
        yield chunk


def refine_report(api_key, model_name, current_text, refine_query):
    client = get_client(api_key)
    refine_prompt = (
        f"You are a document refinement assistant.\n"
        f"Apply the user's request to the existing document without losing structure.\n"
        f"User request: \"{refine_query}\"\n"
        f"Write the updates under the heading: ## Additional Request Applied\n"
        f"Existing document (truncated): {current_text[:20000]}...\n"
    )
    resp = client.models.generate_content(model=model_name, contents=refine_prompt)
    return resp.text


def refine_report_with_context(api_key, model_name, current_text, chat_history,
                                refine_query, additional_file_context=""):
    """Chat-based refinement with history and additional file context.
    Returns the complete updated document (not just changes).
    """
    client = get_client(api_key)

    # Build conversation context from recent messages
    history_text = ""
    for msg in chat_history[-5:]:
        role = "사용자" if msg["role"] == "user" else "AI"
        history_text += f"[{role}]: {msg['content']}\n"

    additional_section = ""
    if additional_file_context:
        additional_section = f"\n[추가 제공된 자료]\n{additional_file_context}\n"

    refine_prompt = (
        f"You are a document refinement assistant.\n"
        f"Apply the user's latest request to the existing document.\n"
        f"Return the COMPLETE updated document (전체 문서를 반환하세요).\n"
        f"Do NOT return only the changed parts - return the full document with changes applied.\n"
        f"Preserve the original structure and formatting.\n"
        f"IMPORTANT: 서문, 인트로, 설명 문장 없이 바로 마크다운 본문(# 헤딩)으로 시작하세요. 도입부를 쓰지 마세요.\n\n"
        f"[이전 대화]\n{history_text}\n"
        f"[최신 요청]: \"{refine_query}\"\n"
        f"{additional_section}\n"
        f"[현재 문서]\n{current_text[:30000]}\n"
    )

    config = types.GenerateContentConfig(
        max_output_tokens=65536,
        temperature=0.3,
    )
    resp = client.models.generate_content(model=model_name, contents=refine_prompt, config=config)
    return resp.text


# ========================================
# Phase-specific helper functions
# ========================================

def generate_material_summary(api_key, model_name, file_context):
    """Phase 1: 수집 자료 심층 분석 (출처 태깅, 교차 분석, 리스크 분류)"""
    client = get_client(api_key)
    system_prompt = prompts.LOGIC_PROMPTS.get('material_summary', '')
    doc_count = file_context.count('===== 문서:')
    prompt = f"[수집된 자료 ({doc_count}건)]\n{file_context}"
    config = types.GenerateContentConfig(
        max_output_tokens=16384,
        temperature=0.3,
        system_instruction=system_prompt,
    )
    resp = client.models.generate_content(model=model_name, contents=prompt, config=config)
    return resp.text


def web_research(api_key, model_name, query, existing_context=""):
    """웹 검색 기반 리서치 — Gemini google_search grounding 활용."""
    from google import genai as _genai
    gemini_client = _genai.Client(api_key=api_key)

    context_section = ""
    if existing_context:
        context_section = f"\n[기존 프로젝트 자료 요약]\n{existing_context[:5000]}\n"

    prompt = f"""당신은 PE/VC 투자 분석 전문가이자 리서치 애널리스트입니다.
아래 주제에 대해 웹 검색을 수행하고, 투자 분석에 유용한 정보를 구조화하여 정리하십시오.
{context_section}
[리서치 주제]
{query}

[출력 규칙]
1. 서문 없이 바로 # 헤딩으로 시작
2. 모든 정보에 출처 URL 또는 출처명을 표기
3. 수치, 날짜, 고유명사는 정확히 인용
4. 투자 분석 관점에서 유의미한 정보 위주로 정리

[출력 형식]

# {{주제}} 리서치 결과

## 핵심 요약
> 3-5문장 요약

---

## 주요 발견사항
(카테고리별로 구분하여 정리. 출처 표기 필수.)

---

## 핵심 데이터

| 항목 | 수치/데이터 | 출처 |
| :--- | :--- | :--- |
| ... | ... | ... |

---

## 시사점 및 투자 관점
- ...

---

## 추가 리서치 키워드
(이 주제를 더 깊이 조사하기 위해 검색해볼 만한 키워드 3-5개)
- ...

---
*웹 검색 기반 리서치 결과 | 검색일: 오늘*
"""

    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        max_output_tokens=65536,
        temperature=0.3,
    )
    resp = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )
    return resp.text


def generate_material_summary_batch(api_key, model_name, docs_dict, on_doc_complete=None):
    """Phase 1: 각 문서별 개별 분석 (batch mode)"""
    import json
    client = get_client(api_key)
    system_prompt = prompts.LOGIC_PROMPTS.get('material_summary_single', '')
    results = []
    total = len(docs_dict)
    for i, (doc_name, content) in enumerate(docs_dict.items()):
        display_name = doc_name.replace('.txt.md', '').replace('.md', '')
        # Truncate very long docs
        truncated = content[:50000] if len(content) > 50000 else content
        prompt = f"[문서: {display_name}]\n{truncated}"
        config = types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.3,
            system_instruction=system_prompt,
        )
        resp = client.models.generate_content(model=model_name, contents=prompt, config=config)
        entry = {"filename": display_name, "result": resp.text}
        results.append(entry)
        if on_doc_complete:
            on_doc_complete(entry, i, total)
    return json.dumps(results, ensure_ascii=False)


def generate_followup_analysis(api_key, model_name, file_context, existing_analysis, user_input):
    """사용자 요청 기반 후속 분석 - 기존 분석 결과에 추가 심화 분석 수행"""
    client = get_client(api_key)
    prompt_text = f"""당신은 PE/VC 투자 분석 전문가입니다.

[원본 자료]
{file_context}

[기존 분석 결과]
{existing_analysis}

[사용자 추가 분석 요청]
{user_input}

위 사용자의 요청을 바탕으로 기존 분석을 보완하는 **후속 심화 분석**을 수행하십시오.

[출력 형식]
## 🔎 후속 분석: {user_input[:50]}

### 핵심 발견사항
- ...

### 상세 분석
(사용자 요청 영역에 대한 구체적 분석 내용. 수치, 근거, 비교 등 포함)

### 시사점 및 리스크
- ...

### 추가 확인 필요 사항
- ...
"""
    config = types.GenerateContentConfig(
        max_output_tokens=4096,
        temperature=0.3,
    )
    resp = client.models.generate_content(model=model_name, contents=prompt_text, config=config)
    return resp.text


_INSUFFICIENT_MARKERS = [
    "자료에서 직접 확인되지 않",
    "자료에서 확인되지 않",
    "자료에 언급되어 있지 않",
    "자료에 포함되어 있지 않",
    "관련 내용을 찾을 수 없",
    "해당 정보가 없",
    "확인할 수 없",
    "자료에 없",
]


def _needs_web_search(answer: str) -> bool:
    """1차 답변에서 문서 부족 신호가 있는지 감지."""
    if not answer:
        return True
    answer_lower = answer.lower()
    hit_count = sum(1 for m in _INSUFFICIENT_MARKERS if m in answer)
    # 부족 표현이 2회 이상이면 웹 검색 필요
    return hit_count >= 2


def _web_search_supplement(api_key, question, doc_answer, file_context_summary=""):
    """Gemini google_search tool로 웹 검색 보강 답변 생성."""
    from google import genai as _genai
    gemini_client = _genai.Client(api_key=api_key)

    prompt = f"""당신은 PE/VC 투자 분석 전문가입니다. 아래 질문에 대해 기존 문서 기반 답변이 부족하여 웹 검색으로 보강합니다.

[질문]
{question}

[기존 문서 기반 답변 (참고용)]
{doc_answer[:3000]}

[지침]
- 웹 검색 결과를 활용하여 기존 답변을 보강하세요
- 문서 기반 내용과 웹 검색 내용을 통합하여 완성도 높은 답변을 작성하세요
- 웹 검색으로 얻은 정보는 출처를 간략히 표기하세요 (예: "웹 검색 결과에 따르면...")
- 핵심 내용을 먼저, 부연 설명을 뒤에 배치하세요
- 관련 데이터가 있으면 표로 정리하세요
"""
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        max_output_tokens=65536,
        temperature=0.3,
    )
    resp = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )
    return resp.text


def generate_qa_answer(api_key, model_name, file_context, question, prev_qa_context="", rag_context=""):
    """자료 기반 Q&A - 로드된 자료를 참조하여 사용자 질문에 답변.
    2-pass: 문서 기반 답변 → 부족 시 Gemini 웹 검색 보강.
    """
    client = get_client(api_key)
    prev_section = f"\n[이전 Q&A 맥락]\n{prev_qa_context}\n" if prev_qa_context else ""
    rag_section = f"\n[프로젝트 문서]\n{rag_context}\n" if rag_context else ""
    prompt_text = f"""당신은 PE/VC 투자 분석 전문가입니다. 주어진 자료를 철저히 참조하여 질문에 정확하게 답변하십시오.

[참조 자료]
{file_context}
{rag_section}
{prev_section}

[질문]
{question}

[답변 지침]
- 반드시 참조 자료에 근거하여 답변하세요
- 자료에 명시된 수치, 데이터가 있으면 구체적으로 인용하세요
- 자료에서 직접 확인되지 않는 내용은 "자료에서 직접 확인되지 않음"이라고 명시하세요
- 핵심 내용을 먼저, 부연 설명을 뒤에 배치하세요
- 관련 데이터가 있으면 표로 정리하세요
"""
    config = types.GenerateContentConfig(
        max_output_tokens=65536,
        temperature=0.2,
    )
    resp = client.models.generate_content(model=model_name, contents=prompt_text, config=config)
    first_answer = resp.text

    # 2nd pass: 문서 답변이 부족하면 Gemini 웹 검색으로 보강
    if _needs_web_search(first_answer):
        try:
            web_answer = _web_search_supplement(api_key, question, first_answer)
            if web_answer and len(web_answer.strip()) > 100:
                return web_answer + "\n\n---\n*웹 검색 결과를 포함하여 보강된 답변입니다.*"
        except Exception as e:
            print(f"[qa] web search supplement failed: {e}")

    return first_answer


def generate_followup_questions(api_key, model_name, file_context, rag_context=""):
    """Phase 1: 수집 자료 기반 추가 질문 및 조사 항목 도출 (RAG 연동)"""
    client = get_client(api_key)
    template = prompts.LOGIC_PROMPTS.get('material_followup_questions', '')
    rag_section = f"\n[RAG 검색 결과 - 프로젝트 인덱스 참조]\n{rag_context}\n" if rag_context else ""
    prompt_text = template.replace('{rag_context}', rag_section).replace('{file_context}', file_context)
    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=0.3,
    )
    resp = client.models.generate_content(model=model_name, contents=prompt_text, config=config)
    return resp.text


def generate_additional_questions(api_key, model_name, file_context, existing_questions, user_input, rag_context=""):
    """사용자 입력 기반 후속 질문 생성 - 기존 질문 + 사용자 관심사를 반영하여 심화 질문 도출"""
    client = get_client(api_key)
    prompt_text = f"""당신은 PE/VC 투자 리서치 전문가입니다.

[기존 분석 자료]
{file_context}

[기존 도출된 질문/조사 항목]
{existing_questions}

{f"[프로젝트 문서 참조]{chr(10)}{rag_context}" if rag_context else ""}

[사용자 추가 요청/관심 영역]
{user_input}

위 사용자의 추가 요청/관심 영역을 바탕으로:
1. 해당 영역에 대한 심화 확인 질문 (경영진/대상기업 대상) 5~10개
2. 추가 조사가 필요한 세부 항목 (표 형태)
3. 기존 질문과의 연관성 및 우선순위 정리

[출력 형식]
## 🔎 후속 질문 (사용자 요청 기반)

### 핵심 확인 질문
1. ...
(각 질문에 배경/목적 병기)

### 추가 조사 항목
| 영역 | 조사 항목 | 목적 | 우선순위 |
| :--- | :--- | :--- | :--- |
| ... | ... | ... | ... |

### 기존 질문과의 연관성
- ...
"""
    config = types.GenerateContentConfig(
        max_output_tokens=4096,
        temperature=0.3,
    )
    resp = client.models.generate_content(model=model_name, contents=prompt_text, config=config)
    return resp.text


def evaluate_checklist_item(api_key, model_name, item_name, file_context):
    """Phase 2: 투자 매력도 체크리스트 항목별 자동 평가"""
    client = get_client(api_key)
    template = prompts.LOGIC_PROMPTS.get('checklist_evaluation', '')
    prompt = template.replace('{checklist_item}', item_name).replace('{file_context}', file_context)
    config = types.GenerateContentConfig(
        max_output_tokens=1024,
        temperature=0.3,
    )
    resp = client.models.generate_content(model=model_name, contents=prompt, config=config)
    return resp.text


def analyze_dd_issues(api_key, model_name, file_context, context_text=""):
    """Phase 3: 실사 자료에서 이슈 자동 추출 및 분류"""
    client = get_client(api_key)
    template = prompts.LOGIC_PROMPTS.get('dd_issue_analysis', '')
    prompt = template.replace('{file_context}', file_context).replace('{context_text}', context_text)
    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=0.3,
    )
    resp = client.models.generate_content(model=model_name, contents=prompt, config=config)
    return resp.text


def _safe_parse_json(text):
    """Parse JSON with repair for truncated/malformed output."""
    import json as _json, re
    if not text or not text.strip():
        return {"sections": []}
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        pass
    # Try to fix common issues: trailing commas, truncated arrays
    cleaned = text.strip()
    # Remove markdown code blocks
    cleaned = re.sub(r'^```\w*\n?', '', cleaned)
    cleaned = re.sub(r'\n?```$', '', cleaned)
    # Close unclosed brackets/braces
    open_braces = cleaned.count('{') - cleaned.count('}')
    open_brackets = cleaned.count('[') - cleaned.count(']')
    # Remove trailing comma before closing
    cleaned = re.sub(r',\s*$', '', cleaned)
    cleaned += ']' * max(0, open_brackets)
    cleaned += '}' * max(0, open_braces)
    try:
        return _json.loads(cleaned)
    except _json.JSONDecodeError:
        # Last resort: extract the largest valid JSON object
        m = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if m:
            try:
                return _json.loads(m.group())
            except _json.JSONDecodeError:
                pass
    return {"sections": []}


def generate_slide_outline(api_key, model_name, file_context="", context_text="", **_kwargs):
    """2단계 PPT 아웃라인: Quick Review → 슬라이드 JSON.
    generate_slide_json과 동일 로직이지만 on_slide 콜백 없이 dict 반환.
    """
    import json as _json
    result_json = generate_slide_json(
        api_key, model_name,
        file_context=file_context,
        context_text=context_text,
        on_slide=None,
    )
    return _safe_parse_json(result_json) if isinstance(result_json, str) else result_json


def generate_slides_from_outline(api_key, model_name, outline, file_context="",
                                  context_text="", on_slide=None):
    """Phase 2: Generate slide details from an (edited) outline.
    Takes user-edited outline and generates detailed slides for each section.
    """
    import json as _json
    client = get_client(api_key)

    sections = outline.get("sections", [])
    if not sections:
        return _json.dumps({"slides": []}, ensure_ascii=False)

    section_prompt = prompts.LOGIC_PROMPTS.get('ppt_section_detail', '')
    all_slides = []

    for sec_idx, section in enumerate(sections):
        sec_title = section.get("title", f"Section {sec_idx + 1}")
        sec_slides_plan = section.get("slides", [])

        section_user = f"""[Overall Outline]
{_json.dumps(outline, ensure_ascii=False, indent=2)}

[Current Section to Generate]
Section {sec_idx + 1}: {sec_title}
Planned slides: {_json.dumps(sec_slides_plan, ensure_ascii=False)}

[Source Material]
{file_context}

[Context/Goal]
{context_text}
"""

        if on_slide:
            sec_config = types.GenerateContentConfig(
                max_output_tokens=16384,
                temperature=0.3,
                system_instruction=section_prompt,
            )
            stream = client.models.generate_content_stream(
                model=model_name,
                contents=section_user,
                config=sec_config
            )
            offset = len(all_slides)
            section_slides = []

            def _on_section_slide(slide_obj, idx):
                section_slides.append(slide_obj)
                on_slide(slide_obj, offset + idx)

            _parse_streaming_slides(stream, _on_section_slide)
            all_slides.extend(section_slides)
        else:
            sec_config = types.GenerateContentConfig(
                max_output_tokens=16384,
                temperature=0.3,
                system_instruction=section_prompt,
                response_mime_type="application/json"
            )
            resp = client.models.generate_content(
                model=model_name,
                contents=section_user,
                config=sec_config
            )
            sec_data = _safe_parse_json(resp.text)
            sec_slides = sec_data.get("slides", sec_data if isinstance(sec_data, list) else [])
            if isinstance(sec_slides, list):
                all_slides.extend(sec_slides)

    return _json.dumps({"slides": all_slides}, ensure_ascii=False)


def generate_slide_json(api_key, model_name, file_context="", context_text="",
                        on_slide=None, **_kwargs):
    """2단계 PPT 생성: Quick Review → 슬라이드화.

    Step 1: 문서를 분석하여 구조화된 리뷰 생성 (simple_review)
    Step 2: 리뷰 결과를 DYNAMIC_PPTX_PROMPT로 좌표 기반 슬라이드 JSON 변환
    """
    import json as _json
    import logging
    logger = logging.getLogger(__name__)
    client = get_client(api_key)

    # ── Step 1: Quick Review (문서 분석) ──
    logger.info("PPT Step 1: Quick Review 분석 시작")
    review_prompt = prompts.LOGIC_PROMPTS.get('simple_review_system', '')
    review_user = (
        f"아래 자료를 분석하여 투자 검토 보고서를 작성하세요.\n"
        f"핵심 지표(매출, EBITDA, 성장률 등)를 정확한 숫자와 함께 정리하고,\n"
        f"시장 분석, 사업 모델, 재무 현황, 리스크를 구조화하세요.\n\n"
        f"[사용자 요청]\n{context_text or '투자 검토 보고서'}\n\n"
        f"[자료]\n{file_context}"
    )

    review_config = types.GenerateContentConfig(
        max_output_tokens=16384,
        temperature=0.2,
        system_instruction=review_prompt if review_prompt else None,
    )
    review_resp = client.models.generate_content(
        model=model_name, contents=review_user, config=review_config,
    )
    review_text = review_resp.text or ""
    logger.info(f"PPT Step 1 완료: {len(review_text)} chars")

    # ── Step 2: 리뷰 → 슬라이드 JSON 변환 ──
    logger.info("PPT Step 2: 슬라이드 JSON 변환 시작")
    dynamic_prompt = getattr(prompts, 'DYNAMIC_PPTX_PROMPT', '')
    if not dynamic_prompt:
        dynamic_prompt = prompts.LOGIC_PROMPTS.get('ppt_outline', '')

    # 리뷰 결과를 context로, 원래 사용자 요청을 query로
    user_content = dynamic_prompt.format(
        context=review_text,
        query=context_text or "투자 검토 보고서를 작성해주세요",
    )

    slide_config = types.GenerateContentConfig(
        max_output_tokens=65536,
        temperature=0.3,
        response_mime_type="application/json",
    )
    slide_resp = client.models.generate_content(
        model=model_name, contents=user_content, config=slide_config,
    )
    result = _safe_parse_json(slide_resp.text)
    slides = result.get("slides", [])
    logger.info(f"PPT Step 2 완료: {len(slides)} slides")

    # on_slide 콜백 호출 (WebSocket 스트리밍 호환)
    if on_slide and slides:
        for i, slide in enumerate(slides):
            on_slide(slide, i)

    return _json.dumps(result, ensure_ascii=False)


def _parse_streaming_slides(stream, on_slide):
    """Parse streaming Gemini output and emit each slide as it completes.

    Accumulates all streamed text, then after each chunk scans the full
    buffer for complete slide JSON objects using brace-depth counting.
    """
    import json as _json

    buffer = ""
    slides_found = []
    scan_pos = 0  # Where to resume scanning in the buffer

    for chunk in stream:
        text = ""
        if hasattr(chunk, "text"):
            text = chunk.text or ""
        elif isinstance(chunk, str):
            text = chunk
        if not text:
            continue

        buffer += text

        # Scan from last position for complete slide objects
        while scan_pos < len(buffer):
            # Find the start of a slides array if not yet found
            if not slides_found and scan_pos == 0:
                arr_idx = buffer.find('"slides"')
                if arr_idx < 0:
                    break  # Haven't seen "slides" key yet
                bracket = buffer.find('[', arr_idx)
                if bracket < 0:
                    break
                scan_pos = bracket + 1

            # Find next '{' from scan_pos
            obj_start = buffer.find('{', scan_pos)
            if obj_start < 0:
                break

            # Count braces to find matching '}'
            depth = 0
            in_string = False
            escape_next = False
            found_end = -1

            for i in range(obj_start, len(buffer)):
                c = buffer[i]
                if escape_next:
                    escape_next = False
                    continue
                if c == '\\' and in_string:
                    escape_next = True
                    continue
                if c == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        found_end = i
                        break

            if found_end < 0:
                break  # Incomplete object, wait for more data

            # Extract and parse the slide object
            slide_str = buffer[obj_start:found_end + 1]
            scan_pos = found_end + 1

            try:
                slide_obj = _json.loads(slide_str)
                # Only emit if it looks like a slide (has slide_type or type)
                if isinstance(slide_obj, dict) and (slide_obj.get("slide_type") or slide_obj.get("type") or slide_obj.get("title")):
                    slides_found.append(slide_obj)
                    on_slide(slide_obj, len(slides_found) - 1)
            except _json.JSONDecodeError:
                pass  # Malformed JSON, skip

    # Return final JSON
    return _json.dumps({"slides": slides_found}, ensure_ascii=False)


def regenerate_single_slide(api_key, model_name, current_slide="", prev_slide="null",
                            next_slide="null", instruction=""):
    """Regenerate a single slide based on user instruction.

    Args:
        current_slide: JSON string of the slide to edit
        prev_slide: JSON string of previous slide (or "null")
        next_slide: JSON string of next slide (or "null")
        instruction: user's edit instruction

    Returns:
        JSON string of the new slide
    """
    client = get_client(api_key)
    template = prompts.LOGIC_PROMPTS.get('ppt_slide_regenerate', '')

    system_prompt = template.replace("{current_slide}", current_slide) \
                           .replace("{prev_slide}", prev_slide) \
                           .replace("{next_slide}", next_slide) \
                           .replace("{instruction}", instruction)

    config = types.GenerateContentConfig(
        max_output_tokens=4096,
        temperature=0.3,
        system_instruction=system_prompt,
        response_mime_type="application/json"
    )

    resp = client.models.generate_content(
        model=model_name,
        contents=instruction,
        config=config
    )
    return resp.text

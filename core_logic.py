from google import genai
from google.genai import types
import utils
import core_rfi
import core_chained
import core_im
import core_rag
import prompts

def get_client(api_key):
    return genai.Client(api_key=api_key)

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
    """Phase 1: 수집 자료 요약 및 핵심 발견사항 추출"""
    client = get_client(api_key)
    system_prompt = prompts.LOGIC_PROMPTS.get('material_summary', '')
    prompt = f"{system_prompt}\n\n[수집된 자료]\n{file_context}"
    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=0.3,
        system_instruction=system_prompt,
    )
    resp = client.models.generate_content(model=model_name, contents=prompt, config=config)
    return resp.text


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


def generate_qa_answer(api_key, model_name, file_context, question, prev_qa_context="", rag_context=""):
    """자료 기반 Q&A - 로드된 자료를 참조하여 사용자 질문에 답변"""
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
    return resp.text


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


def generate_slide_json(api_key, model_name, file_context, context_text=""):
    """
    Generates structured JSON for PPT slides directly from source material.
    """
    client = get_client(api_key)
    system_prompt = prompts.LOGIC_PROMPTS.get('ppt_structure_json', '')

    user_prompt = f"""
[Context/Goal]
{context_text}

[Source Material]
{file_context}
"""
    
    # Force JSON output
    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=0.3,
        system_instruction=system_prompt,
        response_mime_type="application/json"
    )
    
    resp = client.models.generate_content(
        model=model_name, 
        contents=user_prompt, 
        config=config
    )
    return resp.text


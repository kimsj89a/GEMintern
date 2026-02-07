from google import genai
from google.genai import types
import utils
import core_rfi
import core_chained
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

def parse_all_files(uploaded_files, saved_files=None, read_content=True, api_key=None, docai_config=None, template_option=None, use_rag=False):
    """파일 목록 파싱 및 로컬 저장/로드 (RAG 지원)

    Args:
        uploaded_files: 업로드된 파일 목록
        saved_files: 로컬에 저장된 파일명 목록 (선택됨)
        read_content: 파일 내용 읽기 여부
        api_key: Google API 키 (Gemini OCR용)
        docai_config: Document AI 설정 (선택사항)
        use_rag: RAG 인덱싱 활성화 여부
    """
    all_text = ""
    file_list_str = ""
    rag_texts = {}  # RAG 인덱싱용 텍스트 수집

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
                # 로컬 스토리지에 저장 (RAG)
                utils.save_to_local_storage(file.name, parsed)
                all_text += parsed
                if use_rag:
                    rag_texts[file.name] = parsed

    # 2. 저장된 파일 불러오기 (로드 -> 텍스트 추가)
    if saved_files and read_content:
        for fname in saved_files:
            file_list_str += f"- [Saved] {fname}\n"
            content = utils.load_saved_doc(fname)
            all_text += f"\n\n{content}\n"
            if use_rag:
                rag_texts[fname] = content

    if not read_content:
        all_text = "(RFI 모드: 내용은 읽지 않음)"

    # 3. RAG 인덱싱 (활성화된 경우)
    rag_result = None
    if use_rag and rag_texts and api_key:
        try:
            rag_result = core_rag.index_texts(api_key, rag_texts)
        except Exception:
            rag_result = {"success": False, "error": "RAG indexing failed"}

    return all_text, file_list_str, rag_result


def get_rag_enriched_context(api_key, structure_text, context_text, template_option):
    """RAG를 사용하여 보고서 생성에 필요한 추가 컨텍스트를 검색합니다."""
    return core_rag.enrich_context_with_rag(
        api_key=api_key,
        structure_text=structure_text,
        context_text=context_text,
        template_option=template_option,
    )

def get_default_structure(template_key):
    return prompts.TEMPLATE_STRUCTURES.get(template_key, "")

def _get_system_prompt(template_opt):
    """템플릿별 시스템 프롬프트 반환"""
    prompt_map = {
        'simple_review': 'simple_review_system',
        'investment': 'investment_system',
        'im': 'im_system',
        'management': 'management_system',
        'presentation': 'ppt_system',
        'paper_review': 'paper_review_system',
        'free_summary': 'free_summary_system',
        'custom': 'custom_system'
    }
    prompt_key = prompt_map.get(template_opt, 'custom_system')
    return prompts.LOGIC_PROMPTS.get(prompt_key, prompts.LOGIC_PROMPTS['custom_system'])

def generate_report_stream(api_key, model_name, inputs, thinking_level, file_context):
    """Single-pass generation mode for all templates."""
    client = get_client(api_key)
    template_opt = inputs['template_option']
    structure_text = inputs['structure_text']

    # [RFI Mode] - 별도 처리
    if template_opt == 'rfi':
        stream = core_rfi.generate_rfi_stream(api_key, model_name, inputs, thinking_level, file_context)
        for chunk in stream:
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

[Document Structure]
{structure_text}

[User Context]
{inputs['context_text']}

[Source Data]
{file_context[:50000]}
"""

    # 템플릿별 config 설정
    if template_opt == 'presentation' or template_opt == 'paper_review':
        temperature = 0.7
    elif template_opt == 'custom':
        temperature = 0.7  # 자유 구조화 모드 - 창의적 구조화를 위해 높은 temperature
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

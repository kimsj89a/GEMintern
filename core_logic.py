from google import genai
from google.genai import types
import utils
import core_rfi
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

def parse_all_files(uploaded_files, read_content=True, api_key=None):
    """파일 목록 파싱 (OCR 지원)"""
    all_text = ""
    file_list_str = ""
    if uploaded_files:
        for file in uploaded_files:
            file_list_str += f"- {file.name}\n"
            if read_content:
                parsed = utils.parse_uploaded_file(file, api_key=api_key)
                all_text += parsed

    if not read_content:
        all_text = "(RFI 모드: 내용을 읽지 않음)"

    return all_text, file_list_str

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
        'custom': 'custom_system'
    }
    prompt_key = prompt_map.get(template_opt, 'custom_system')
    return prompts.LOGIC_PROMPTS.get(prompt_key, prompts.LOGIC_PROMPTS['custom_system'])

def generate_report_stream(api_key, model_name, inputs, thinking_level, file_context):
    """단일 생성 모드 - 모든 템플릿 지원"""
    client = get_client(api_key)
    template_opt = inputs['template_option']
    structure_text = inputs['structure_text']

    # [RFI Mode] - 별도 처리
    if template_opt == 'rfi':
        stream = core_rfi.generate_rfi_stream(api_key, model_name, inputs, thinking_level)
        for chunk in stream:
            yield chunk
        return

    # 템플릿별 시스템 프롬프트 가져오기
    system_instruction = _get_system_prompt(template_opt)

    # 도식화 옵션 추가
    if inputs.get('use_diagram'):
        system_instruction += "\n**도식화**: 필요시 {{DIAGRAM: 설명}} 태그 삽입."

    # 프롬프트 구성
    main_prompt = f"""
[System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
[Critical Instruction] Analyze the provided data deeply and step-by-step. Prioritize accuracy and logical consistency.

[문서 구조]
{structure_text}

[맥락]
{inputs['context_text']}

[분석 데이터]
{file_context[:50000]}
"""

    # 템플릿별 config 설정
    if template_opt == 'presentation':
        temperature = 0.7
    elif template_opt == 'custom':
        temperature = 0.5
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
    """5단계 Chained Prompting - 투자심사보고서 전용 (품질 우선)"""
    client = get_client(api_key)

    # 투자심사보고서 전용 시스템 프롬프트
    system_instruction = prompts.LOGIC_PROMPTS['investment_system']
    if inputs.get('use_diagram'):
        system_instruction += "\n**도식화**: 필요시 {{DIAGRAM: 설명}} 태그 삽입."

    # 투자심사보고서 5개 파트 정의
    parts = [
        ('investment_part1', 'Part 1/5: 투자내용', 32768),
        ('investment_part2', 'Part 2/5: 회사현황', 32768),
        ('investment_part3', 'Part 3/5: 시장분석', 32768),
        ('investment_part4', 'Part 4/5: 사업분석', 32768),
        ('investment_part5', 'Part 5/5: Valuation, Risk & 종합의견', 65536)
    ]

    accumulated_result = ""

    for part_key, part_title, max_tokens in parts:
        # 진행 상황 알림
        status_text = f"\n\n---\n\n📝 **[{part_title}] 생성 중...**\n\n"
        yield types.GenerateContentResponse(
            candidates=[types.Candidate(
                content=types.Content(parts=[types.Part(text=status_text)])
            )]
        )

        # 이전 파트 결과를 컨텍스트로 포함
        prev_context = ""
        if accumulated_result:
            prev_context = f"""
[이전 작성 내용 - 참고용, 중복 작성 금지]
{accumulated_result[-20000:]}
"""

        # 파트별 프롬프트 가져오기
        part_prompt = prompts.LOGIC_PROMPTS.get(part_key, "")

        main_prompt = f"""
[System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
[Critical Instruction] Analyze the provided data deeply and step-by-step. Prioritize accuracy and logical consistency.

{prev_context}

{part_prompt}

[맥락]
{inputs['context_text']}

[분석 데이터]
{file_context[:45000]}
"""

        tools = []
        # Part 3 (시장분석)에서 웹 검색 활성화
        if part_key == 'investment_part3':
            tools = [types.Tool(google_search=types.GoogleSearch())]

        config = types.GenerateContentConfig(
            tools=tools,
            max_output_tokens=max_tokens,
            temperature=0.3,
            system_instruction=system_instruction
        )

        part_result = ""
        response_stream = client.models.generate_content_stream(
            model=model_name,
            contents=main_prompt,
            config=config
        )

        for chunk in response_stream:
            if chunk.text:
                part_result += chunk.text
            yield chunk

        accumulated_result += part_result


def refine_report(api_key, model_name, current_text, refine_query):
    client = get_client(api_key)
    refine_prompt = f"""
    당신은 문서 수정 전문가입니다.
    사용자 요청: "{refine_query}"
    기존 내용을 바탕으로 **"## 🔄 추가 요청 반영"** 하위에 내용을 작성하세요.
    [기존 내용] {current_text[:20000]}...
    """
    resp = client.models.generate_content(model=model_name, contents=refine_prompt)
    return resp.text

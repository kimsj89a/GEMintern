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
        file_text = utils.parse_uploaded_file(structure_file)
        prompt = f"{prompts.LOGIC_PROMPTS['structure_extraction']}\n[파일 내용]\n{file_text[:15000]}"
        resp = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return resp.text
    except Exception as e:
        return f"구조 추출 오류: {str(e)}"

def parse_all_files(uploaded_files, read_content=True):
    all_text = ""
    file_list_str = ""
    if uploaded_files:
        for file in uploaded_files:
            file_list_str += f"- {file.name}\n"
            if read_content:
                parsed = utils.parse_uploaded_file(file)
                all_text += parsed
    
    if not read_content:
        all_text = "(RFI 모드: 내용을 읽지 않음)"
        
    return all_text, file_list_str

def get_default_structure(template_key):
    return prompts.TEMPLATE_STRUCTURES.get(template_key, "")

def generate_report_stream(api_key, model_name, inputs, thinking_level, file_context):
    client = get_client(api_key)
    template_opt = inputs['template_option']
    
    # [RFI Mode]
    if template_opt == 'rfi':
        stream = core_rfi.generate_rfi_stream(api_key, model_name, inputs, thinking_level)
        for chunk in stream:
            yield chunk
        return

    # [PPT Mode]
    if template_opt == 'presentation':
        system_instruction = prompts.LOGIC_PROMPTS['ppt_system']
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        [슬라이드 구조] {inputs['structure_text']}
        [맥락] {inputs['context_text']}
        [데이터] {file_context[:50000]}
        """
        config = types.GenerateContentConfig(
            max_output_tokens=65536,
            temperature=0.7,
            system_instruction=system_instruction
        )

    # [Custom Mode] - 서식 복제
    elif template_opt == 'custom':
        system_instruction = prompts.LOGIC_PROMPTS['custom_system']
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        
        [목표 문서 구조 (반드시 준수)]
        {inputs['structure_text']}
        
        [전체 맥락]
        {inputs['context_text']}
        
        [본문 채우기용 분석 데이터]
        {file_context[:50000]}
        """
        config = types.GenerateContentConfig(
            max_output_tokens=65536,
            temperature=0.5, # 구조 준수를 위해 약간 낮춤
            system_instruction=system_instruction
        )

    # [Standard Report Mode]
    else:
        system_instruction = prompts.LOGIC_PROMPTS['report_system']
        if template_opt == 'simple_review':
             system_instruction += "\n**중요: 10페이지 이내로 핵심만 요약하세요.**"
        if inputs['use_diagram']:
            system_instruction += "\n**도식화**: 필요시 {{DIAGRAM: 설명}} 태그 삽입."

        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        [Critical Instruction] Analyze the provided data deeply and step-by-step. Prioritize accuracy and logical consistency.
        [문서 구조] {inputs['structure_text']}
        [맥락] {inputs['context_text']}
        [데이터] {file_context[:50000]}
        """
        
        tools = []
        if "뉴스" in inputs['structure_text'] or "동향" in inputs['structure_text']:
            tools = [types.Tool(google_search=types.GoogleSearch())]

        config = types.GenerateContentConfig(
            tools=tools,
            max_output_tokens=8192,
            temperature=0.3,
            system_instruction=system_instruction
        )

    response_stream = client.models.generate_content_stream(
        model=model_name,
        contents=main_prompt,
        config=config
    )
    for chunk in response_stream:
        yield chunk

def generate_report_stream_chained(api_key, model_name, inputs, thinking_level, file_context):
    """3단계 Chained Prompting으로 투자심사보고서 생성 (품질 우선)"""
    client = get_client(api_key)

    # 시스템 프롬프트 (공통)
    system_instruction = prompts.LOGIC_PROMPTS['report_system_base']
    if inputs.get('use_diagram'):
        system_instruction += "\n**도식화**: 필요시 {{DIAGRAM: 설명}} 태그 삽입."

    # 3개 파트 정의 (part_key, title, max_tokens)
    parts = [
        ('report_part1', 'Part 1/3: Executive Summary & Investment Highlights', 65536),
        ('report_part2', 'Part 2/3: Target Company & Market Analysis', 65536),
        ('report_part3', 'Part 3/3: Financials, Valuation, Risk & 종합의견', 65536)
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

        main_prompt = f"""
[System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
[Critical Instruction] Analyze the provided data deeply and step-by-step. Prioritize accuracy and logical consistency.

{prev_context}

{prompts.LOGIC_PROMPTS[part_key]}

[맥락]
{inputs['context_text']}

[분석 데이터]
{file_context[:45000]}
"""

        tools = []
        # Part 2 (시장 분석)에서 웹 검색 활성화
        if part_key == 'report_part2':
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
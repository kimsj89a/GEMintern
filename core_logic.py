import re
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
    """파일 목록 파싱 (OCR 지원)

    Args:
        uploaded_files: 업로드된 파일 목록
        read_content: 내용 읽기 여부
        api_key: Google API 키 (PDF OCR용)
    """
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

def generate_report_stream(api_key, model_name, inputs, thinking_level, file_context):
    client = get_client(api_key)
    template_opt = inputs['template_option']
    structure_text = inputs['structure_text']
    
    # [RFI Mode]
    if template_opt == 'rfi':
        stream = core_rfi.generate_rfi_stream(api_key, model_name, inputs, thinking_level)
        for chunk in stream:
            yield chunk
        return
    
    # [Sequential Generation Strategy]
    # 1. Split structure into chapters to generate long, detailed reports
    # Regex splits by headers starting with # (e.g., # 1. Overview)
    sections = re.split(r'(?=^# )', structure_text, flags=re.MULTILINE)
    sections = [s for s in sections if s.strip()]
    
    # If no sections found (e.g. custom without headers), treat as one block
    if not sections:
        sections = [structure_text]

<<<<<<< HEAD
    for i, section_content in enumerate(sections):
        section_title = section_content.split('\n')[0].replace('#', '').strip()
        
        # Determine System Instruction based on Mode
        if template_opt == 'presentation':
            base_system = PROMPTS['ppt_system']
            task_instruction = f"""
            [현재 작업]
            전체 발표자료 중 **"{section_title}"** 파트만 작성하세요.
            입력된 [슬라이드 구조]의 하위 목차(##)를 슬라이드 제목으로 삼아 내용을 구성하세요.
            """
        elif template_opt == 'custom':
            base_system = PROMPTS['custom_system']
            task_instruction = f"""
            [현재 작업]
            전체 문서 중 **"{section_title}"** 챕터만 작성하세요.
            제공된 [문서 구조]를 토씨 하나 틀리지 말고 그대로 유지하며 내용을 채우십시오.
            """
        else:
            # Standard Investment Report / Simple Review / IM / Management
            base_system = PROMPTS['report_system']
            
            # Special handling for Simple Review (Summary focus)
            if template_opt == 'simple_review':
                base_system += "\n**중요: 이 보고서는 5페이지 내외의 '요약' 보고서입니다. 장황한 나열보다는 핵심 요약과 근거 위주로 명료하게 서술하세요.**"
            
            if inputs['use_diagram']:
                base_system += "\n**도식화**: 설명 중 시각화가 필요한 프로세스나 구조가 있다면 **{{DIAGRAM: 설명}}** 태그를 삽입하세요."
                
            task_instruction = f"""
            [현재 작업]
            전체 보고서 중 **"{section_title}"** 챕터만 작성하세요.
            입력된 [문서 구조]의 하위 목차를 빠짐없이 다루세요.
            """

        # Construct Prompt
=======
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
>>>>>>> b5499fc08ff2379c3bc3f5f3545d80550de1327c
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        
        [작성할 챕터 구조]
        {section_content}
        
        [전체 맥락]
        {inputs['context_text']}
        
        [분석 데이터]
        첨부된 파일 내용을 바탕으로 작성하세요. 없는 내용은 지어내지 말고, 추론이 필요하면 [추후 실사 필요]라고 명시하세요.
        {file_context[:50000]}
<<<<<<< HEAD
=======
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
>>>>>>> b5499fc08ff2379c3bc3f5f3545d80550de1327c
        
        {task_instruction}
        """

        config = types.GenerateContentConfig(
            max_output_tokens=8192,
<<<<<<< HEAD
            temperature=0.7,
            system_instruction=base_system
=======
            temperature=0.3,
            system_instruction=system_instruction
>>>>>>> b5499fc08ff2379c3bc3f5f3545d80550de1327c
        )

        # Generate Stream for this section
        response_stream = client.models.generate_content_stream(
            model=model_name,
            contents=main_prompt,
            config=config
        )
        
        for chunk in response_stream:
            yield chunk
            
        # Add separator between sections
        yield types.GenerateContentResponse(
            candidates=[types.Candidate(
                content=types.Content(parts=[types.Part(text="\n\n")])
            )]
        )

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
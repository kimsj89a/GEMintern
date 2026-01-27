"""
Chained Prompting 모듈
- 긴 보고서를 여러 파트로 나누어 순차적으로 생성
- 이전 파트 결과를 컨텍스트로 활용하여 일관성 유지
"""

from google import genai
from google.genai import types
import prompts


def get_client(api_key):
    return genai.Client(api_key=api_key)


# 템플릿별 파트 정의
CHAINED_PARTS = {
    'simple_review': [
        ('simple_review_part1', 'Part 1/3: 투자개요 및 회사현황', 32768),
        ('simple_review_part2', 'Part 2/3: 투자조건 및 투자포인트', 32768),
        ('simple_review_part3', 'Part 3/3: 리스크 및 추진일정', 32768),
    ],
    'investment': [
        ('investment_part1', 'Part 1/5: 투자내용', 32768),
        ('investment_part2', 'Part 2/5: 회사현황', 32768),
        ('investment_part3', 'Part 3/5: 시장분석', 32768),
        ('investment_part4', 'Part 4/5: 사업분석', 32768),
        ('investment_part5', 'Part 5/5: Valuation, Risk & 종합의견', 65536),
    ],
}

# 웹 검색이 필요한 파트 정의
WEB_SEARCH_PARTS = {
    'investment': ['investment_part3'],  # 시장분석 파트
    'simple_review': [],  # 약식검토는 웹 검색 불필요
}


def generate_chained_stream(api_key, model_name, inputs, thinking_level, file_context, template_option):
    """
    일반화된 Chained Prompting 생성기

    Args:
        api_key: Gemini API 키
        model_name: 사용할 모델명
        inputs: 입력 데이터 (context_text, use_diagram 등)
        thinking_level: 사고 수준
        file_context: 파일 컨텍스트
        template_option: 템플릿 종류 ('simple_review', 'investment' 등)

    Yields:
        GenerateContentResponse chunks
    """
    client = get_client(api_key)

    # 템플릿별 시스템 프롬프트 가져오기
    system_prompt_key = f"{template_option}_system"
    system_instruction = prompts.LOGIC_PROMPTS.get(system_prompt_key, prompts.LOGIC_PROMPTS['custom_system'])

    if inputs.get('use_diagram'):
        system_instruction += "\n**도식화**: 필요시 {{DIAGRAM: 설명}} 태그 삽입."

    # 템플릿별 파트 정의 가져오기
    parts = CHAINED_PARTS.get(template_option, [])
    if not parts:
        raise ValueError(f"Chained prompting not supported for template: {template_option}")

    # 웹 검색 파트 목록
    web_search_parts = WEB_SEARCH_PARTS.get(template_option, [])

    accumulated_result = ""

    for part_key, part_title, max_tokens in parts:
        # 진행 상황 알림
        status_text = f"\n\n---\n\n**[{part_title}] 생성 중...**\n\n"
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

        # 웹 검색 도구 설정
        tools = []
        if part_key in web_search_parts:
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


def is_chained_supported(template_option):
    """해당 템플릿이 chained prompting을 지원하는지 확인"""
    return template_option in CHAINED_PARTS

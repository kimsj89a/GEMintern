"""
IM (Information Memorandum) Chained Prompting 모듈
- IM을 5개 파트로 나누어 순차적으로 생성
- 이전 파트 결과를 컨텍스트로 활용하여 일관성 유지
- investment_type별 프롬프트 분기
"""

from google.genai import types
from ai_client import AIClient, make_status_chunk
import prompts


def get_client(api_key):
    return AIClient(api_key=api_key)


IM_CHAINED_PARTS = [
    ('im_full_part1', 'Part 1/5: Executive Summary', 32768),
    ('im_full_part2', 'Part 2/5: 대상회사 분석', 32768),
    ('im_full_part3', 'Part 3/5: 시장 분석', 32768),
    ('im_full_part4', 'Part 4/5: 재무 분석', 32768),
    ('im_full_part5', 'Part 5/5: Valuation & Risk', 65536),
]

IM_WEB_SEARCH_PARTS = ['im_full_part3']


def generate_im_chained_stream(api_key, model_name, inputs, thinking_level,
                                file_context, investment_type="Growth"):
    """
    IM 전용 Chained Prompting 생성기

    Args:
        api_key: Gemini API 키
        model_name: 사용할 모델명
        inputs: 입력 데이터 (context_text, deal_terms 등)
        thinking_level: 사고 수준
        file_context: 파일 컨텍스트
        investment_type: 투자 유형 (Growth/Buyout/Pre-IPO)

    Yields:
        GenerateContentResponse chunks
    """
    client = get_client(api_key)

    # IM 전용 시스템 프롬프트
    system_instruction = prompts.LOGIC_PROMPTS.get('im_full_system', '')
    system_instruction = system_instruction.replace('{investment_type}', investment_type)

    if inputs.get('use_diagram'):
        system_instruction += "\n**도식화**: 필요시 {{DIAGRAM: 설명}} 태그 삽입."

    # Deal terms 구조화 데이터
    deal_terms = _format_deal_terms(inputs)

    accumulated_result = ""

    for part_key, part_title, max_tokens in IM_CHAINED_PARTS:
        # 진행 상황 알림
        status_text = f"\n\n---\n\n**[{part_title}] 생성 중...**\n\n"
        yield make_status_chunk(status_text)

        # 이전 파트 결과를 컨텍스트로 포함 (25K chars)
        prev_context = ""
        if accumulated_result:
            prev_context = f"""
[이전 작성 내용 - 참고용, 중복 작성 금지]
{accumulated_result[-25000:]}
"""

        # 파트별 프롬프트 가져오기 & investment_type 치환
        part_prompt = prompts.LOGIC_PROMPTS.get(part_key, "")
        part_prompt = part_prompt.replace('{investment_type}', investment_type)

        # Part 1에 deal_terms 주입
        deal_terms_section = ""
        if part_key == 'im_full_part1' and deal_terms:
            deal_terms_section = f"\n[Deal Terms - 반드시 반영]\n{deal_terms}\n"

        main_prompt = f"""
[System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
[Critical Instruction] Analyze the provided data deeply and step-by-step. Prioritize accuracy and logical consistency.
[Format Instruction] 서문, 인트로, 설명 문장 없이 바로 마크다운 본문으로 시작하세요.

{prev_context}

{part_prompt}

{deal_terms_section}

[맥락]
{inputs.get('context_text', '')}

[분석 데이터]
{file_context[:45000]}
"""

        # 웹 검색 도구 설정
        tools = []
        if part_key in IM_WEB_SEARCH_PARTS:
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


def _format_deal_terms(inputs):
    """inputs에서 deal terms 정보를 구조화된 텍스트로 포맷."""
    terms = []
    field_map = {
        'project_name': 'Project Name',
        'gp_name': 'GP명',
        'target_company': '대상회사',
        'investment_amount': '투자규모',
        'valuation': 'Valuation',
        'investment_vehicle': '투자형태',
        'equity_stake': '지분율',
    }
    for key, label in field_map.items():
        value = inputs.get(key, '')
        if value:
            terms.append(f"- {label}: {value}")

    return '\n'.join(terms) if terms else ''

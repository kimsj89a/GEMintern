from google import genai
from google.genai import types
import utils
import datetime

# --- PROMPTS ---
PROMPTS = {
    'structure_extraction': """
[System: Thinking Level MINIMAL]
당신은 문서 구조 분석 전문가입니다.
제공된 파일의 내용을 분석하여 **문서의 목차(Table of Contents)**와 **핵심 구조**를 Markdown 형식으로 추출하십시오.
""",
    'rfi_system': """
당신은 회계법인 FAS팀의 M&A 실사 전문 매니저입니다.
(기존 내용 유지...)
""",
    'report_system': """
당신은 **국내 최정상급 PEF/VC 수석 심사역**입니다. 
[대상 기업]에 대한 투자를 승인받기 위해 투심위 위원들을 설득할 수 있는 **'투자심사보고서(Investment Memorandum)'**를 작성 중입니다.

[작성 원칙 - Word 모드]
1. **헤더 금지**: '수신:', '발신:', '작성일:', '대상:' 등의 보고서 개요 메타데이터를 절대 작성하지 마십시오.
2. **분석 태도**: 객관적이고 보수적인 태도로 분석하세요.
3. **서술 방식**: 논리적 연결이 있는 문장형 개조식(Bullet points)을 사용하세요.
4. **결론 작성 규칙 (중요)**: 
   - 종합 의견이나 결론 챕터 작성 시, **"[승인 권고]", "[조건부 승인]", "Recommendation:" 같은 라벨이나 말머리를 절대 붙이지 마십시오.**
   - 바로 내용을 서술하십시오. (예: "본 건 투자는 ~한 이유로 타당하다고 판단됨." 처럼 작성)
5. **표/출처**: Markdown Table 사용, 출처 명시.
""",
    'ppt_system': """
당신은 **프레젠테이션 전문가**입니다.
(기존 내용 유지...)
"""
}

TEMPLATE_STRUCTURES = {
    'simple_review': """# 1. Executive Summary
   - 대상 기업 요약
   - 주요 투자 조건

# 2. 회사 현황
   - 설립 및 연혁
   - 주요 사업 현황

# 3. 주요 동향 및 이슈
   - 최근 주요 계약
   - 최근 주요 뉴스

# 4. 재무 및 주가 분석
   - 요약 재무상태 (최근 3년 매출/이익, 자산/부채 현황)
   - (필요시) 주가 추이 및 거래량 분석

# 5. 종합 의견
   - 투자 리스크 점검
   - 최종 의견""",
    'rfi': "[RFI 모드]",
    'investment': """# 1. 투자내용 (Executive Summary)
# 2. 회사현황
# 3. 시장분석
# 4. 사업분석
# 5. 투자 타당성
# 6. 리스크 분석
# 7. 종합의견""",
    'im': "# 1. Highlights\n# 2. Company\n# 3. Market\n# 4. Product\n# 5. Financial",
    'management': "# 1. 개요\n# 2. 현황\n# 3. 이슈\n# 4. 회수",
    'presentation': """# 1. Executive Summary
## 투자 개요
## 핵심 투자 포인트
## 주요 투자 조건

# 2. Market & Business
## 시장 규모 및 성장성
## 경쟁 현황
## 비즈니스 모델
## 핵심 기술

# 3. Financials & Valuation
## 과거 재무 실적
## 추정 손익
## 가치평가 및 회수 전략

# 4. Risk & Opinion
## 주요 리스크 및 헷지 방안
## 종합 투자의견""",
    'custom': ""
}

def get_client(api_key):
    return genai.Client(api_key=api_key)

def extract_structure(api_key, structure_file):
    try:
        client = get_client(api_key)
        file_text = utils.parse_uploaded_file(structure_file)
        prompt = f"{PROMPTS['structure_extraction']}\n[파일 내용]\n{file_text[:15000]}"
        resp = client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        return resp.text
    except Exception as e:
        return f"구조 추출 오류: {str(e)}"

def parse_all_files(uploaded_files):
    all_text = ""
    file_list_str = ""
    if uploaded_files:
        for file in uploaded_files:
            parsed = utils.parse_uploaded_file(file)
            all_text += parsed
            file_list_str += f"- {file.name}\n"
    return all_text, file_list_str

def get_default_structure(template_key):
    return TEMPLATE_STRUCTURES.get(template_key, "")

def generate_report_stream(api_key, model_name, inputs, thinking_level, file_context):
    client = get_client(api_key)
    template_opt = inputs['template_option']
    
    if template_opt == 'rfi':
        system_instruction = PROMPTS['rfi_system']
        uploaded_list = [f.name for f in inputs['uploaded_files']] if inputs['uploaded_files'] else []
        file_list_str = "\n".join([f"- {name}" for name in uploaded_list])
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        # [기존 RFI] {inputs['rfi_existing']}
        # [신규 질문] {inputs['context_text']}
        [파일 목록] {file_list_str}
        [참고 내용] {file_context[:30000]}
        """
    elif template_opt == 'presentation':
        system_instruction = PROMPTS['ppt_system']
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        [슬라이드 구조] {inputs['structure_text']}
        [맥락] {inputs['context_text']}
        [데이터] {file_context[:50000]}
        """
    else:
        system_instruction = PROMPTS['report_system']
        if template_opt == 'simple_review':
             system_instruction += "\n**중요: 10페이지 이내로 핵심만 요약하세요.**"
        if inputs['use_diagram']:
            system_instruction += "\n**도식화**: 필요시 {{DIAGRAM: 설명}} 태그 삽입."

        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        [문서 구조] {inputs['structure_text']}
        [맥락] {inputs['context_text']}
        [데이터] {file_context[:50000]}
        """

    tools = []
    if template_opt != 'rfi' and ("뉴스" in inputs['structure_text'] or "동향" in inputs['structure_text']):
        tools = [types.Tool(google_search=types.GoogleSearch())]

    config = types.GenerateContentConfig(
        tools=tools,
        max_output_tokens=8192,
        temperature=0.2 if template_opt == 'rfi' else 0.7,
        system_instruction=system_instruction
    )

    response_stream = client.models.generate_content_stream(
        model=model_name,
        contents=main_prompt,
        config=config
    )
    for chunk in response_stream:
        yield chunk

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
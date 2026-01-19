from google import genai
from google.genai import types
import utils
import datetime

# --- HTML에서 추출한 프롬프트 정의 ---
PROMPTS = {
    'structure_extraction': """
[System: Thinking Level MINIMAL]
당신은 문서 구조 분석 전문가입니다.
제공된 파일의 내용을 분석하여 **문서의 목차(Table of Contents)**와 **핵심 구조**를 Markdown 형식으로 추출하십시오.

[요구사항]
1. 오직 구조(# 헤더)만 출력하십시오. 설명이나 사족을 달지 마십시오.
2. 문서의 계층 구조(#, ##, ###)를 정확히 반영하십시오.
3. 내용이 없다면 일반적인 해당 문서 유형의 표준 목차를 제안하십시오.
""",
    'rfi_system': """
당신은 회계법인 FAS(Financial Advisory Services)팀의 **M&A 실사(Due Diligence) 전문 매니저**입니다.
기업이 주장하는 내용을 맹신하지 않고, 반드시 **객관적인 근거 데이터(계약서, 원장, 신고서 등)**로 검증하는 보수적인 태도를 가집니다.
(중략... 기존 RFI 프롬프트와 동일)
# Rules (Critical)
0. **[제공 자료] 자동 생성**: 사용자가 보유한 파일 목록이 제공되면, **가장 먼저 [1. 제공 자료 현황] 표**를 작성하십시오.
1. **[기존 RFI] 우선 기재**: 사용자가 제공한 **[기존 RFI Copy & Paste]** 데이터가 있다면, 해당 내용을 분석하여 Markdown Table의 **상단에 먼저 [2. 기존 RFI 목록]**으로 정리하십시오.
2. **[신규 요청] 추가**: 사용자의 **[신규 요청/질문]**을 분석하고, [기본 실사 체크리스트] 중 누락된 필수 항목을 더해 **[3. 추가 자료 요청 목록]** 표를 작성하십시오.
3. **포맷 준수**: 아래 Markdown Table 양식을 정확히 따르십시오.
    | No. | 구분 | 요청자료 | 설명 | 요청일자 |
    | --- | --- | --- | --- | --- |
""",
    'report_system': """
당신은 **국내 최정상급 PEF/VC 수석 심사역**입니다. 
[대상 기업]에 대한 투자를 승인받기 위해 투심위 위원들을 설득할 수 있는 **'투자심사보고서(Investment Memorandum)'**를 작성 중입니다.

[작성 원칙 - Word 모드]
1. **헤더 금지 (No Metadata)**: '수신:', '발신:', '작성일:', '대상:' 등의 보고서 개요 메타데이터를 **절대 작성하지 마십시오.** 바로 **# 1. 챕터 제목**으로 시작하십시오.
2. **분석 태도 (최우선)**: 제공된 자료들은 회사나 자문사가 작성한 홍보성 자료임을 감안하여, **최대한 객관적이고 보수적인 태도**로 분석하세요. 장밋빛 전망은 배제하고, 리스크와 하방 요인을 비판적으로 검토해야 합니다.
3. **서술 방식**: 가독성을 위해 **개조식(Bullet points)**을 적극 활용하되, 단순 나열이 아닌 논리적 연결이 있는 문장형 개조식을 사용하세요.
4. **표(Table)**: 원본 데이터의 재무 수치나 비교 자료는 Markdown Table로 변환하여 삽입하세요.
5. **출처 표기**: 데이터 인용 시 바로 아래에 "Source : [문서의 실제 제목]"를 명시하세요.
""",
    # [NEW] PPT 전용 프롬프트
    'ppt_system': """
당신은 **국내 최정상급 PEF/VC 수석 심사역**이자 **프레젠테이션 전문가**입니다.
투심위에서 사용할 **[투자심의 발표자료 (Slide Deck)]**를 작성해야 합니다.

[작성 원칙 - PPT 모드]
1. **구조적 포맷팅 (매우 중요)**:
   - **# (H1)**: [섹션 간지]입니다. 챕터의 큰 주제를 적으세요. (예: # 1. 투자 하이라이트)
   - **## (H2)**: [개별 슬라이드]의 제목입니다. (예: ## 핵심 투자 포인트)
   - **- (Bullet)**: 슬라이드 본문 내용입니다.
2. **내용 작성 스타일**:
   - **절대 서술형 문장을 쓰지 마십시오.** (예: "~함.", "~임." 형태로 종결)
   - **단문 위주**: 한 줄은 50자를 넘지 않도록 핵심만 요약하십시오.
   - **슬라이드 당 분량**: 하나의 `## 제목` 아래에는 5~7개의 Bullet Point만 포함하십시오. 내용이 많으면 슬라이드를 나누세요.
3. **논리적 흐름**:
   - 결론부터 말하는 두괄식 구성을 사용하십시오.
   - 수치 데이터(매출, 이익률, 점유율 등)를 적극적으로 인용하여 신뢰도를 높이십시오.
4. **메타데이터 금지**: 작성일, 작성자 등의 정보는 포함하지 마십시오.
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
    'rfi': "[RFI 모드] 보유 자료 목록 및 추가 질문을 기반으로 RFI 테이블을 생성합니다.",
    'investment': """# 1. 투자내용 (Executive Summary)
   - 투자개요
   - 투자조건 및 구조

# 2. 회사현황 (Company Profile)
   - 회사개요
   - 재무현황

# 3. 시장분석 (Market Analysis)
   - 산업 트렌드
   - 경쟁 현황

# 4. 사업분석 (Business Analysis)
   - 비즈니스 모델
   - 핵심 경쟁력

# 5. 투자 타당성 및 리스크
   - Valuation
   - 리스크 및 대응 방안

# 6. 종합의견""",
    'im': """# 1. Investment Highlights
# 2. Company Overview
# 3. Market Opportunity
# 4. Product & Technology
# 5. Financial Plan""",
    'management': """# 1. 운용 개요
# 2. 포트폴리오 현황
# 3. 주요 이슈
# 4. 회수 계획""",
    # [NEW] PPT 전용 구조 (간지와 슬라이드 제목 분리)
    'presentation': """# 1. Executive Summary
## 투자 개요 (Deal Overview)
## 핵심 투자 포인트 (Investment Highlights)
## 주요 투자 조건 (Term Sheet)

# 2. Market & Business
## 시장 규모 및 성장성 (Market Size)
## 경쟁 현황 및 포지셔닝 (Competition)
## 비즈니스 모델 (BM)
## 핵심 기술 및 제품 (Product)

# 3. Financials & Valuation
## 과거 재무 실적 (Historical Financials)
## 추정 손익 및 근거 (Financial Projection)
## 가치평가 및 회수 전략 (Valuation & Exit)

# 4. Risk & Opinion
## 주요 리스크 및 헷지 방안 (Key Risks)
## 종합 투자의견 (Conclusion)""",
    'custom': ""
}

def get_client(api_key):
    return genai.Client(api_key=api_key)

def extract_structure(api_key, structure_file):
    try:
        client = get_client(api_key)
        file_text = utils.parse_uploaded_file(structure_file)
        
        prompt = f"""
        {PROMPTS['structure_extraction']}
        
        [파일 내용]
        {file_text[:15000]}
        """
        
        resp = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
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
    
    # 1. 프롬프트 선택 로직 분기
    if template_opt == 'rfi':
        system_instruction = PROMPTS['rfi_system']
        uploaded_list = [f.name for f in inputs['uploaded_files']] if inputs['uploaded_files'] else []
        file_list_str = "\n".join([f"- {name}" for name in uploaded_list])
        
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        # [기존 RFI Copy & Paste]
        {inputs['rfi_existing']}
        # [신규 요청/질문]
        {inputs['context_text']}
        [사용자가 보유한 파일 목록]
        {file_list_str}
        [참고 파일 내용]
        {file_context[:30000]}
        """
    
    # [NEW] PPT 모드일 경우 전용 프롬프트 사용
    elif template_opt == 'presentation':
        system_instruction = PROMPTS['ppt_system']
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        [작성할 슬라이드 구조]
        {inputs['structure_text']}
        [전체 맥락]
        {inputs['context_text']}
        [분석 데이터 활용]
        {file_context[:50000]}
        """
        
    else: # 일반 보고서 (Word)
        system_instruction = PROMPTS['report_system']
        if template_opt == 'simple_review':
             system_instruction += "\n**중요: 결과물은 절대 10페이지 분량을 넘지 않도록 핵심만 요약하세요.**"

        if inputs['use_diagram']:
            system_instruction += "\n5. **도식화(Diagram)**: 설명 중 시각화가 필요한 프로세스나 구조가 있다면 **{{DIAGRAM: 설명}}** 태그를 삽입하세요."

        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        [작성할 문서 구조]
        {inputs['structure_text']}
        [전체 맥락]
        {inputs['context_text']}
        [분석 데이터 활용]
        {file_context[:50000]}
        """

    # 2. 툴 설정
    tools = []
    if template_opt != 'rfi' and ("뉴스" in inputs['structure_text'] or "동향" in inputs['structure_text']):
        tools = [types.Tool(google_search=types.GoogleSearch())]

    # 3. API 호출
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
    당신은 문서 수정 및 보완 전문가입니다. 
    기존 문서의 내용을 전면 재작성하지 말고, 사용자가 요청한 **추가 분석, 수정 사항, 또는 보완 내용**을 
    **"## 🔄 추가 요청 반영"** 이라는 제목 하위에 작성하십시오.
    
    [기존 내용]
    {current_text[:20000]}...
    
    [수정 요청]
    {refine_query}
    """
    
    resp = client.models.generate_content(
        model=model_name, 
        contents=refine_prompt
    )
    return resp.text
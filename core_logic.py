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
    # [Step 1] Flash 모델용: 파일 매칭 및 상태 판별
    'rfi_indexing': """
당신은 자료 관리 및 인덱싱 전문가입니다.
[기존 요청 자료 목록(RFI)]과 [수령한 파일 목록]을 대조하여 제출 현황을 점검하십시오.

# Task
1. 사용자가 제출한 파일명들을 분석하여, 기존 RFI 항목 중 어느 것에 해당하는지 매칭하십시오.
2. 각 항목의 제출 상태를 아래 기준으로 판별하십시오.
   - **O (제출됨)**: 파일명으로 보아 해당 자료가 명확히 포함됨.
   - **△ (확인 필요)**: 파일명이 모호하거나, 부분적으로만 포함된 것으로 추정됨.
   - **X (미제출)**: 해당 내용을 유추할 수 있는 파일이 없음.
3. 결과는 반드시 **Markdown Table** 형식으로만 출력하십시오. 설명은 필요 없습니다.

# Output Table Format
| No. | 구분 | 기존 요청 자료 | 매칭된 파일명(없으면 -) | 상태(O/△/X) | 비고 |
| --- | --- | --- | --- | --- | --- |
""",
    # [Step 2] Main 모델용: 최종 RFI 생성
    'rfi_finalizing': """
당신은 회계법인 FAS팀의 **M&A 실사(Due Diligence) 전문 매니저**입니다.
[1차 자료 점검 결과]를 바탕으로, 부족한 자료를 파악하고 **최종 RFI(자료요청목록)**를 작성하십시오.

# Context: [기본 실사 체크리스트]
아래 필수 항목들이 누락되었다면 반드시 추가 요청해야 합니다.
1. 회사일반: 주주명부, 정관, 등기부등본, 조직도
2. 재무/회계: 최근 3개년 감사보고서, 계정별 원장, 월별 결산서
3. 영업/시장: 주요 매출처 계약서, 수주잔고, 시장 M/S 자료
4. 인사/노무: 급여대장, 퇴직금 추계액, 조직도
5. 법무: 소송 현황, 제재 내역

# Task
1. **[1. 기존 자료 제출 현황]**: 앞서 생성된 '점검 결과 표'를 다듬어서 출력하십시오. (상태가 X인 항목 강조)
2. **[2. 추가 요청 사항]**: 
   - 상태가 **X** 또는 **△**인 항목을 다시 요청 리스트에 포함하십시오.
   - [기본 실사 체크리스트] 중 아예 언급되지 않은 필수 자료를 추가하십시오.
   - 사용자의 [추가 질문/맥락]을 반영하여 구체적인 자료를 요청하십시오.

# Output Style
- 표 형식을 사용하여 깔끔하게 정리하십시오.
- 불필요한 서론/결론 없이 표와 핵심 코멘트 위주로 작성하십시오.
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
[작성 원칙 - PPT 모드]
1. **구조적 포맷팅**: # (간지), ## (슬라이드 제목), - (내용) 구조 준수.
2. **내용 작성**: 서술형 금지, 핵심 키워드 위주의 단문(개조식) 작성.
3. **분량**: 슬라이드당 5~7줄 이내.
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
    'rfi': "[RFI 모드] 자동 생성됩니다.",
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

# [New] RFI 1단계: 파일 인덱싱 및 대사 (Flash 모델 사용)
def analyze_rfi_status(api_key, existing_rfi, file_list_str):
    client = get_client(api_key)
    
    prompt = f"""
    {PROMPTS['rfi_indexing']}
    
    [기존 요청 자료 목록(RFI)]
    {existing_rfi}
    
    [수령한 파일 목록 (폴더 인덱스)]
    {file_list_str}
    """
    
    try:
        # Flash 모델로 빠르고 저렴하게 처리
        resp = client.models.generate_content(
            model="gemini-3.0-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        return resp.text
    except Exception as e:
        return f"인덱싱 오류: {str(e)}"

def generate_report_stream(api_key, model_name, inputs, thinking_level, file_context):
    client = get_client(api_key)
    template_opt = inputs['template_option']
    
    # ---------------------------------------------------------
    # [RFI Mode] 2-Step Process
    # ---------------------------------------------------------
    if template_opt == 'rfi':
        uploaded_list = [f.name for f in inputs['uploaded_files']] if inputs['uploaded_files'] else []
        file_list_str = "\n".join([f"- {name}" for name in uploaded_list])
        
        # 1. UI에 진행상황 알림 (Yield)
        yield types.GenerateContentResponse(
            candidates=[types.Candidate(
                content=types.Content(parts=[types.Part(text="📂 [Step 1] 수령 자료 인덱싱 및 대사 작업 중... (Gemini Flash)\n\n")])
            )]
        )
        
        # 2. Step 1: 상태 판별 (Blocking Call)
        # 기존 RFI가 없으면 생략 가능하지만, 빈칸이라도 체크하도록 함
        rfi_status_table = analyze_rfi_status(api_key, inputs['rfi_existing'], file_list_str)
        
        yield types.GenerateContentResponse(
            candidates=[types.Candidate(
                content=types.Content(parts=[types.Part(text=f"{rfi_status_table}\n\n---\n🧠 [Step 2] 부족 자료 분석 및 최종 RFI 작성 중... ({model_name})\n\n")])
            )]
        )

        # 3. Step 2: 최종 RFI 생성 (Streaming)
        system_instruction = PROMPTS['rfi_finalizing']
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        
        [1차 자료 점검 결과 (Flash 분석)]
        {rfi_status_table}

        [사용자 추가 질문/맥락]
        {inputs['context_text']}
        
        [참고: 파일 내용 일부]
        {file_context[:30000]}
        """
        
        config = types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.2, # 정교한 분석을 위해 낮음
            system_instruction=system_instruction
        )

    # ---------------------------------------------------------
    # [PPT Mode]
    # ---------------------------------------------------------
    elif template_opt == 'presentation':
        system_instruction = PROMPTS['ppt_system']
        main_prompt = f"""
        [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
        [슬라이드 구조] {inputs['structure_text']}
        [맥락] {inputs['context_text']}
        [데이터] {file_context[:50000]}
        """
        config = types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.7,
            system_instruction=system_instruction
        )

    # ---------------------------------------------------------
    # [Word Report Mode]
    # ---------------------------------------------------------
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
        
        # Tools setup (Search)
        tools = []
        if "뉴스" in inputs['structure_text'] or "동향" in inputs['structure_text']:
            tools = [types.Tool(google_search=types.GoogleSearch())]

        config = types.GenerateContentConfig(
            tools=tools,
            max_output_tokens=8192,
            temperature=0.7,
            system_instruction=system_instruction
        )

    # Common Generation Call
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
import os
import datetime
from google import genai
from google.genai import types

# --- RFI 전용 프롬프트 ---
PROMPTS = {
    'indexing': """
당신은 자료 관리 및 인덱싱 전문가입니다.
[기존 요청 자료 목록(RFI)]과 [수령한 파일 인덱스]를 대조하여 제출 현황을 점검하십시오.

# Task
1. 사용자가 스캔한 **파일 경로 및 메타데이터**를 분석하여, 기존 RFI 항목 중 어느 것에 해당하는지 매칭하십시오.
2. 각 항목의 제출 상태를 아래 기준으로 판별하십시오.
   - **O (제출됨)**: 파일명으로 보아 해당 자료가 명확히 포함됨.
   - **△ (확인 필요)**: 파일명이 모호하거나, 부분적으로만 포함된 것으로 추정됨.
   - **X (미제출)**: 해당 내용을 유추할 수 있는 파일이 없음.
3. 결과는 반드시 **Markdown Table** 형식으로만 출력하십시오. 설명은 필요 없습니다.

# Output Table Format
| No. | 구분 | 기존 요청 자료 | 매칭된 파일 정보(경로) | 상태(O/△/X) | 비고 |
| --- | --- | --- | --- | --- | --- |
""",
    'finalizing': """
당신은 회계법인 FAS(Financial Advisory Services)팀의 **M&A 실사(Due Diligence) 전문 매니저**입니다.
기업이 주장하는 내용을 맹신하지 않고, 반드시 **객관적인 근거 데이터(계약서, 원장, 신고서 등)**로 검증하는 보수적인 태도를 가집니다.

# Context: [기본 실사 체크리스트]
1. 회사일반: 주주명부, 정관, 등기부등본, 조직도, 이사회 의사록, 경영진 이력
2. 재무/회계: 최근 3개년 감사보고서, 계정별 원장, 월별 결산서, 우발채무, 차입금 현황
3. 영업/시장: 시장규모 및 M/S 분석 자료(외부), 주요 매출처 계약서, 수주잔고(Backlog), 단가 정책
4. 기술/생산: 특허 리스트, 생산설비 대장, 수율/가동률 데이터, 라이선스 계약
5. 인사/노무: 급여대장, 노조 현황, 퇴직금 추계액, 근속연수 분석
6. 법무: 진행 중인 소송 리스트, 제재 내역, 특수관계인 거래 내역

# Task
사용자가 입력한 **"구체적인 질문"**이나 **"우려 사항"**을 해소하기 위해 받아야 할 **RFI(자료요청목록) 테이블**을 작성하십시오.

# Rules (Critical - Update Mode)
1. **이어쓰기(Update)**: [1차 자료 점검 결과]에 있는 기존 항목들은 상태(O/X)를 유지하여 그대로 포함시키고, 사용자의 질문에서 파생된 **새로운 요청 항목**을 하단에 추가하십시오. (중복 제외, 번호 이어 매기기)
2. **질문의 RFI 변환**: 사용자가 던지는 질문(예: "성장성이 있어?")을 실사 요청 자료(예: "매출처별/제품별 3개년 매출 상세 내역")로 변환하여 기재하십시오.
3. **객관성 유지**: 단순 답변을 요구하지 말고, 판단 근거가 되는 Raw Data를 요청하세요.
4. **포맷 준수**: 아래 Markdown Table 양식을 정확히 따르십시오.
   | No. | 구분 | 요청자료 | 요청일자 | 비고 |
   | --- | --- | --- | --- | --- |
   (구분은 [회사일반/재무/영업/기술/인사/법무] 중 택 1)
   (요청일자는 오늘 날짜 기준 +5 영업일)
"""
}

def get_client(api_key):
    return genai.Client(api_key=api_key)

def analyze_rfi_status(client, existing_rfi, file_index_str):
    """Step 1: Flash 모델로 인덱싱"""
    prompt = f"""
    {PROMPTS['indexing']}
    
    [기존 요청 자료 목록(RFI)]
    {existing_rfi}
    
    [수령한 파일 인덱스 (Browser Scan)]
    {file_index_str}
    """
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash-exp", 
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        return resp.text
    except Exception as e:
        return f"인덱싱 오류: {str(e)}"

def generate_rfi_stream(api_key, model_name, inputs, thinking_level):
    """RFI 생성 메인 로직"""
    client = get_client(api_key)
    
    # UI에서 복사/붙여넣기 한 텍스트 사용
    file_index_str = inputs.get('rfi_file_list_input', '')
    if not file_index_str:
        file_index_str = "(파일 인덱스 없음 - 사용자가 입력하지 않음)"
    
    yield types.GenerateContentResponse(
        candidates=[types.Candidate(
            content=types.Content(parts=[types.Part(text="📂 [Step 1] 파일 인덱스 기반 대사(Indexing) 진행 중...\n\n")])
        )]
    )
    
    rfi_status_table = analyze_rfi_status(client, inputs['rfi_existing'], file_index_str)
    
    yield types.GenerateContentResponse(
        candidates=[types.Candidate(
            content=types.Content(parts=[types.Part(text=f"{rfi_status_table}\n\n---\n🧠 [Step 2] 부족 자료 분석 및 최종 RFI 작성 중... ({model_name})\n\n")])
        )]
    )

    main_prompt = f"""
    [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
    
    [1차 자료 점검 결과]
    {rfi_status_table}

    [사용자 추가 질문/맥락]
    {inputs['context_text']}
    """
    
    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=0.2, 
        system_instruction=PROMPTS['finalizing']
    )
    
    response_stream = client.models.generate_content_stream(
        model=model_name,
        contents=main_prompt,
        config=config
    )
    
    for chunk in response_stream:
        yield chunk
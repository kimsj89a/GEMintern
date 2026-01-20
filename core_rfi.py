from google import genai
from google.genai import types

# --- RFI 전용 프롬프트 ---
PROMPTS = {
    'indexing': """
당신은 자료 관리 및 인덱싱 전문가입니다.
[기존 요청 자료 목록(RFI)]과 [수령한 파일 목록]을 대조하여 제출 현황을 점검하십시오.

# Task
1. 사용자가 제출한 **파일명들을 분석**하여, 기존 RFI 항목 중 어느 것에 해당하는지 매칭하십시오.
2. 각 항목의 제출 상태를 아래 기준으로 판별하십시오.
   - **O (제출됨)**: 파일명으로 보아 해당 자료가 명확히 포함됨.
   - **△ (확인 필요)**: 파일명이 모호하거나, 부분적으로만 포함된 것으로 추정됨.
   - **X (미제출)**: 해당 내용을 유추할 수 있는 파일이 없음.
3. 결과는 반드시 **Markdown Table** 형식으로만 출력하십시오. 설명은 필요 없습니다.

# Output Table Format
| No. | 구분 | 기존 요청 자료 | 매칭된 파일명(없으면 -) | 상태(O/△/X) | 비고 |
| --- | --- | --- | --- | --- | --- |
""",
    'finalizing': """
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
"""
}

def get_client(api_key):
    return genai.Client(api_key=api_key)

def extract_filenames_from_objects(uploaded_files):
    """
    Streamlit UploadedFile 객체 리스트에서 이름만 추출.
    파일 내용(Bytes)은 절대 읽지 않으므로 서버 부하 없음.
    """
    if not uploaded_files:
        return "(수령한 파일이 없습니다)"
    
    # 리스트 컴프리헨션으로 이름만 빠르게 추출
    return "\n".join([f"- {f.name}" for f in uploaded_files])

def analyze_rfi_status(client, existing_rfi, file_list_str):
    """Step 1: Flash 모델로 인덱싱"""
    prompt = f"""
    {PROMPTS['indexing']}
    
    [기존 요청 자료 목록(RFI)]
    {existing_rfi}
    
    [수령한 파일 목록 (파일명 인덱스)]
    {file_list_str}
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
    """RFI 생성 메인 로직 (스트리밍)"""
    client = get_client(api_key)
    
    # 1. 파일 목록 준비 (Standard Uploader -> Name Extraction)
    file_list_str = extract_filenames_from_objects(inputs['uploaded_files'])
    
    # UI 알림
    yield types.GenerateContentResponse(
        candidates=[types.Candidate(
            content=types.Content(parts=[types.Part(text="📂 [Step 1] 업로드된 파일명 자동 대사(Indexing) 진행 중...\n\n")])
        )]
    )
    
    # 2. Step 1: 인덱싱 (Flash)
    rfi_status_table = analyze_rfi_status(client, inputs['rfi_existing'], file_list_str)
    
    yield types.GenerateContentResponse(
        candidates=[types.Candidate(
            content=types.Content(parts=[types.Part(text=f"{rfi_status_table}\n\n---\n🧠 [Step 2] 부족 자료 분석 및 최종 RFI 작성 중... ({model_name})\n\n")])
        )]
    )

    # 3. Step 2: 최종 RFI 작성 (Main Model)
    main_prompt = f"""
    [System: Thinking Level {thinking_level.upper() if isinstance(thinking_level, str) else 'HIGH'}]
    
    [1차 자료 점검 결과 (파일명 분석)]
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
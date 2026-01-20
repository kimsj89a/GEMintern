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
당신은 회계법인 FAS팀의 **M&A 실사(Due Diligence) 전문 매니저**입니다.
[1차 자료 점검 결과]를 바탕으로, 부족한 자료를 파악하고 **최종 RFI(자료요청목록)**를 작성하십시오.

# Task
1. **[1. 기존 자료 제출 현황]**: 앞서 생성된 '점검 결과 표'를 다듬어서 출력하십시오.
2. **[2. 추가 요청 사항]**: 
   - 상태가 **X** 또는 **△**인 항목을 다시 요청 리스트에 포함하십시오.
   - [기본 실사 체크리스트] 중 아예 언급되지 않은 필수 자료를 추가하십시오.

# Output Style
- 표 형식을 사용하여 깔끔하게 정리하십시오.
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
import os
import datetime
from google import genai
from google.genai import types
import prompts

def get_client(api_key):
    return genai.Client(api_key=api_key)

def analyze_rfi_status(client, existing_rfi, file_index_str):
    """Step 1: Flash 모델로 인덱싱"""
    prompt = f"""
    {prompts.RFI_PROMPTS['indexing']}
    
    [기존 요청 자료 목록(RFI)]
    {existing_rfi}
    
    [수령한 파일 인덱스 (Browser Scan)]
    {file_index_str}
    """
    try:
        resp = client.models.generate_content(
            model="gemini-3-flash-preview", 
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
        system_instruction=prompts.RFI_PROMPTS['finalizing']
    )
    
    response_stream = client.models.generate_content_stream(
        model=model_name,
        contents=main_prompt,
        config=config
    )
    
    for chunk in response_stream:
        yield chunk
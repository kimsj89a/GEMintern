from google import genai
from google.genai import types
import utils

def get_client(api_key):
    return genai.Client(api_key=api_key)

def extract_structure(api_key, structure_file):
    """업로드된 파일에서 문서 구조(목차)를 추출합니다."""
    try:
        client = get_client(api_key)
        file_text = utils.parse_uploaded_file(structure_file)
        
        prompt = f"""
        [System: Thinking Level MINIMAL]
        제공된 파일 내용을 분석하여 문서의 목차(Markdown Header #, ##)를 추출하세요.
        불필요한 본문 내용은 제외하고 구조만 잡으세요.
        
        [파일 내용]
        {file_text[:10000]}
        """
        
        resp = client.models.generate_content(
            model="gemini-2.0-flash-exp", 
            contents=prompt
        )
        return resp.text
    except Exception as e:
        return f"구조 추출 오류: {str(e)}"

def build_prompt(inputs, all_file_text, thinking_level):
    """최종 프롬프트를 구성합니다."""
    system_instruction = "당신은 전문 투자 심사역입니다. 객관적이고 보수적인 태도로 분석하세요."
    if inputs['template_option'] == 'simple_review':
        system_instruction += "\n**중요: 결과물은 절대 10페이지 분량을 넘지 않도록 핵심만 요약하세요.**"
    
    # Grounding 툴 사용 여부 힌트 (실제 툴 설정은 stream 함수에서)
    if "뉴스" in inputs['structure_text'] or "동향" in inputs['structure_text']:
         system_instruction += "\n[Google Search]: 최신 시장 동향과 뉴스는 Google 검색을 통해 팩트를 확인하고 작성하세요."

    full_prompt = f"""
    {system_instruction}
    
    [Thinking Level: {thinking_level.upper()}]
    
    [작성할 문서 구조]
    {inputs['structure_text']}
    
    [맥락 및 요청사항]
    {inputs['context_text']}
    
    [기존 RFI (RFI 모드일 경우)]
    {inputs['rfi_existing']}
    
    [참고 데이터 (업로드된 파일)]
    {all_file_text[:50000]} 
    """
    return full_prompt, system_instruction

def generate_report_stream(api_key, model_name, inputs, thinking_level):
    """Gemini API를 호출하여 리포트를 스트리밍으로 생성합니다."""
    client = get_client(api_key)
    
    # 1. 파일 내용 파싱
    all_file_text = ""
    if inputs['uploaded_files']:
        for file in inputs['uploaded_files']:
            all_file_text += utils.parse_uploaded_file(file)
            
    # 2. 프롬프트 구성
    full_prompt, _ = build_prompt(inputs, all_file_text, thinking_level)
    
    # 3. 툴 설정 (뉴스/동향 키워드가 있으면 검색 활성화)
    tools = []
    if "뉴스" in inputs['structure_text'] or "동향" in inputs['structure_text'] or inputs['template_option'] == 'simple_review':
        tools = [types.Tool(google_search=types.GoogleSearch())]

    # 4. API 호출
    config = types.GenerateContentConfig(
        tools=tools,
        max_output_tokens=8192,
        temperature=0.7
    )

    return client.models.generate_content_stream(
        model=model_name,
        contents=full_prompt,
        config=config
    )

def refine_report(api_key, model_name, current_text, refine_query):
    """기존 리포트를 사용자 요청에 따라 수정합니다."""
    client = get_client(api_key)
    
    refine_prompt = f"""
    기존 문서 내용을 바탕으로 다음 요청사항을 반영하여 수정하거나 추가 내용을 작성해줘.
    
    [기존 내용]
    {current_text[:20000]}...
    
    [수정 요청]
    {refine_query}
    
    전체 문서를 다시 쓸 필요 없이, 수정된 부분이나 추가된 챕터 내용을 출력해줘.
    """
    
    resp = client.models.generate_content(
        model=model_name, 
        contents=refine_prompt
    )
    return resp.text
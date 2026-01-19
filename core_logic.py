import streamlit as st
from google import genai
from google.genai import types
import utils
import traceback

def process_and_generate(inputs, api_key, model_name, thinking_level, response_container):
    """
    파일 처리 -> 프롬프트 구성 -> Gemini API 호출 과정을 수행합니다.
    결과는 response_container(Streamlit placeholder)에 스트리밍됩니다.
    """
    client = genai.Client(api_key=api_key)
    full_response = ""

    try:
        # 1. 파일 내용 파싱
        all_file_text = ""
        uploaded_files = inputs['uploaded_files']
        
        if uploaded_files:
            st.info(f"📂 파일 {len(uploaded_files)}개 분석 중...")
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                file_content = utils.parse_uploaded_file(file)
                all_file_text += file_content
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            st.success("파일 분석 완료!")
        
        # 2. 프롬프트 구성
        st.info("🧠 생각 정리 중...")
        system_instruction = "당신은 전문 투자 심사역입니다. 객관적이고 보수적인 태도로 분석하세요."
        
        # Google Grounding 도구 설정
        tools = []
        structure_text = inputs['structure_text']
        if "뉴스" in structure_text or "동향" in structure_text or inputs['template_key'] == 'simple_review':
            tools = [types.Tool(google_search=types.GoogleSearch())]
            st.info("🔍 Google Search 도구 활성화됨 (최신 정보 검색)")

        full_prompt = f"""
        {system_instruction}
        [Thinking Level: {thinking_level.upper()}]
        
        [작성할 문서 구조] 
        {structure_text}
        
        [맥락 및 요청사항] 
        {inputs['context_text']}
        
        [기존 RFI (해당 시)]
        {inputs['rfi_existing']}
        
        [참고 데이터 (파일 내용)] 
        {all_file_text[:60000]} 
        """ # 토큰 제한 고려 (필요시 조절)

        # 3. API 호출 및 스트리밍
        st.info(f"✨ 문서 작성 시작... ({model_name})")
        
        config = types.GenerateContentConfig(
            tools=tools,
            max_output_tokens=8192,
            temperature=0.7
        )

        response = client.models.generate_content_stream(
            model=model_name,
            contents=full_prompt,
            config=config
        )
        
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                response_container.markdown(full_response + "▌")
        
        response_container.markdown(full_response)
        return full_response

    except Exception as e:
        st.error("오류 발생!")
        st.code(traceback.format_exc())
        return None
import streamlit as st
from google import genai
from google.genai import types
import utils
import time

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="GEM Intern v5.0 (Py)", page_icon="💎")

# --- CSS 스타일 적용 (모바일 스크롤 및 가독성) ---
st.markdown("""
<style>
    .reportview-container .main .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    /* 한글 단어 단위 줄바꿈 */
    p, li, div {
        word-break: keep-all;
        overflow-wrap: break-word;
    }
    /* 모바일 가시성 확보 */
    @media (max-width: 640px) {
        .stTextArea textarea { font-size: 16px !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 상태 초기화 ---
if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 템플릿 데이터 ---
TEMPLATES = {
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
    'investment': "# 1. 투자내용\n# 2. 회사현황\n# 3. 시장분석\n# 4. 사업분석\n# 5. 투자 타당성\n# 6. 리스크 분석\n# 7. 종합의견",
    'custom': ""
}

# --- 사이드바 (설정) ---
with st.sidebar:
    st.header("⚙️ 설정 (Settings)")
    
    api_key = st.text_input("Google API Key", type="password", help="브라우저 세션에만 저장됩니다.")
    model_name = st.selectbox("Model", [
        "gemini-2.0-flash-exp", 
        "gemini-1.5-pro", 
        "gemini-1.5-flash"
    ], index=0)
    
    thinking_level = st.selectbox("Thinking Level", ["High", "Low"], index=0)
    use_diagram = st.checkbox("도식화 이미지 생성", value=False)
    
    st.info("💡 **가이드**\n\n- **약식 검토**: 5pg 내외 요약\n- **RFI**: 자료 요청 리스트\n- **Grounding**: 뉴스 챕터 작성 시 자동 검색")
    
    st.caption("Powered by Gemini 2.0 | Converted to Streamlit")

# --- 메인 레이아웃 (2단) ---
col1, col2 = st.columns([1, 1])

# === [왼쪽: 입력 패널] ===
with col1:
    st.subheader("📥 입력 (Input)")
    
    # 1. 템플릿 선택
    template_option = st.selectbox(
        "1. 문서 구조 / 템플릿", 
        list(TEMPLATES.keys()), 
        format_func=lambda x: {
            'simple_review': '1. 약식 투자검토 (요약)',
            'rfi': '2. RFI 작성 (실사 자료 요청)',
            'investment': '3. 투자심사보고서 (표준)',
            'custom': '4. 직접 입력'
        }.get(x, x)
    )
    
    # 구조 추출 기능
    uploaded_structure_file = st.file_uploader("📂 서식 파일 업로드 (구조 추출용)", type=['pdf', 'docx', 'txt', 'md'])
    
    if uploaded_structure_file:
        if st.button("구조 추출 실행"):
            if not api_key:
                st.error("API Key가 필요합니다.")
            else:
                with st.spinner("구조 분석 중..."):
                    client = genai.Client(api_key=api_key)
                    file_text = utils.parse_uploaded_file(uploaded_structure_file)
                    
                    prompt = f"""
                    [System: Thinking Level MINIMAL]
                    제공된 파일 내용을 분석하여 문서의 목차(Markdown Header #, ##)를 추출하세요.
                    
                    [파일 내용]
                    {file_text[:10000]}
                    """
                    try:
                        resp = client.models.generate_content(
                            model="gemini-2.0-flash-exp", 
                            contents=prompt
                        )
                        st.session_state['structure_input'] = resp.text
                        st.rerun() # Refresh to update text area
                    except Exception as e:
                        st.error(f"오류 발생: {e}")

    # 구조 입력창 (기본값 설정 로직 포함)
    default_structure = TEMPLATES[template_option]
    if 'structure_input' in st.session_state and template_option == 'custom':
        default_structure = st.session_state['structure_input']
        
    structure_text = st.text_area(
        "문서 구조 편집", 
        value=default_structure, 
        height=200,
        disabled=(template_option == 'rfi')
    )

    # 2. 데이터 업로드
    st.markdown("##### 2. 분석할 데이터 (Raw Data)")
    uploaded_files = st.file_uploader("IR 자료, 재무제표 등", accept_multiple_files=True)
    
    # 3. 컨텍스트
    st.markdown("##### 3. 대상 기업 및 맥락 (Context)")
    context_text = st.text_area(
        "추가 질문 및 상황 설명", 
        placeholder="예: 기업명, 핵심 제품, 주요 우려 사항 등...",
        height=100
    )

    # RFI 전용: 기존 RFI 입력
    rfi_existing = ""
    if template_option == 'rfi':
        st.markdown("##### 5. 기존 RFI 목록 (선택)")
        rfi_existing = st.text_area("기존 목록 붙여넣기", height=100)

    # 생성 버튼
    generate_btn = st.button("🚀 문서 생성 시작", use_container_width=True, type="primary")


# === [오른쪽: 결과 패널] ===
with col2:
    st.subheader("📄 결과물 (Result)")
    
    # 결과 표시 영역
    result_container = st.container(height=600, border=True)
    
    if generate_btn:
        if not api_key:
            st.error("설정 패널에서 API Key를 입력해주세요.")
        else:
            client = genai.Client(api_key=api_key)
            
            # 1. 파일 내용 파싱
            all_file_text = ""
            if uploaded_files:
                with st.spinner("파일 내용 읽는 중..."):
                    for file in uploaded_files:
                        all_file_text += utils.parse_uploaded_file(file)
            
            # 2. 프롬프트 구성
            system_instruction = "당신은 전문 투자 심사역입니다. 객관적이고 보수적인 태도로 분석하세요."
            if template_option == 'simple_review':
                system_instruction += "\n**중요: 결과물은 절대 10페이지 분량을 넘지 않도록 핵심만 요약하세요.**"
            
            # Google Grounding 설정 (뉴스 챕터 등)
            tools = []
            if "뉴스" in structure_text or "동향" in structure_text or template_option == 'simple_review':
                tools = [types.Tool(google_search=types.GoogleSearch())]
                system_instruction += "\n[Google Search]: 최신 시장 동향과 뉴스는 Google 검색을 통해 팩트를 확인하고 작성하세요."

            full_prompt = f"""
            {system_instruction}
            
            [Thinking Level: {thinking_level.upper()}]
            
            [작성할 문서 구조]
            {structure_text}
            
            [맥락 및 요청사항]
            {context_text}
            
            [기존 RFI (RFI 모드일 경우)]
            {rfi_existing}
            
            [참고 데이터 (업로드된 파일)]
            {all_file_text[:50000]} 
            """
            # Token limit note: Adjust slice based on model capability

            # 3. Gemini 호출 (Streaming)
            with result_container:
                response_placeholder = st.empty()
                full_response = ""
                
                try:
                    # Config for tools
                    config = types.GenerateContentConfig(
                        tools=tools,
                        max_output_tokens=8192, # v4.7 equivalent logic
                        temperature=0.7
                    )

                    # Generate
                    response = client.models.generate_content_stream(
                        model=model_name,
                        contents=full_prompt,
                        config=config
                    )
                    
                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            response_placeholder.markdown(full_response + "▌")
                    
                    response_placeholder.markdown(full_response)
                    st.session_state.generated_text = full_response
                    
                except Exception as e:
                    st.error(f"생성 중 오류 발생: {e}")

    # 이미 생성된 텍스트가 있으면 표시
    elif st.session_state.generated_text:
        with result_container:
            st.markdown(st.session_state.generated_text)

    # --- 수정 및 내보내기 ---
    if st.session_state.generated_text:
        st.markdown("---")
        
        # 추가 요청 (Chat Input 스타일)
        refine_query = st.chat_input("결과물 수정/보완 요청 (Enter로 전송)")
        if refine_query:
            if not api_key:
                st.error("API Key 필요")
            else:
                client = genai.Client(api_key=api_key)
                refine_prompt = f"""
                기존 문서 내용을 바탕으로 다음 요청사항을 반영하여 수정하거나 추가 내용을 작성해줘.
                
                [기존 내용]
                {st.session_state.generated_text[:20000]}...
                
                [수정 요청]
                {refine_query}
                
                전체 문서를 다시 쓸 필요 없이, 수정된 부분이나 추가된 챕터 내용을 출력해줘.
                """
                with st.spinner("수정 내용 생성 중..."):
                    try:
                        resp = client.models.generate_content(model=model_name, contents=refine_prompt)
                        st.session_state.generated_text += f"\n\n--- [추가 요청 반영] ---\n{resp.text}"
                        st.rerun()
                    except Exception as e:
                        st.error(f"수정 중 오류: {e}")

        # 다운로드 버튼
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            docx_data = utils.create_docx(st.session_state.generated_text)
            st.download_button(
                label="📄 Word로 저장",
                data=docx_data,
                file_name="investment_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        with col_d2:
            st.button("📊 PPT로 저장 (구현 예정)", disabled=True, use_container_width=True)
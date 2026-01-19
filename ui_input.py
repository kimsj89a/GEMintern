import streamlit as st
import utils
import core_logic

# 템플릿 상수 정의 (HTML 버전과 동기화)
TEMPLATES = {
    'simple_review': '1. 약식 투자검토 (요약)',
    'rfi': '2. RFI 작성 (실사 자료 요청)',
    'investment': '3. 투자심사보고서 (표준)',
    'im': '4. IM (투자제안서)',
    'management': '5. 사후관리보고서',
    'custom': '6. 직접 입력 (자동 구조화)'
}

def render_settings():
    """상단 설정 영역(Expander)을 렌더링하고 설정값을 반환합니다."""
    
    # URL 쿼리 파라미터에서 API Key 읽기
    query_params = st.query_params
    cached_key = query_params.get("api_key", "")
    if isinstance(cached_key, list): cached_key = cached_key[0]

    with st.expander("⚙️ 설정 (SETTINGS)", expanded=True):
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
        
        with c1:
            api_key = st.text_input("Google API Key", value=cached_key, type="password", placeholder="Enter Key...")
            save_to_url = st.checkbox("🔑 브라우저(URL)에 키 저장", value=bool(cached_key))
            
            if save_to_url and api_key:
                st.query_params["api_key"] = api_key
            elif not save_to_url and "api_key" in st.query_params:
                del st.query_params["api_key"]
            
        with c2:
            model_name = st.selectbox("사용할 모델 (Model)", [
                "gemini-3-pro-preview",
                "gemini-3-flash-preview",
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro"
            ], index=0)
            
        with c3:
            thinking_level = st.selectbox("사고 수준 (Thinking)", ["High (추론 깊이 극대화)", "Low (속도 우선)"], index=0)
            
        with c4:
            st.write("") 
            st.write("") 
            use_diagram = st.checkbox("🎨 도식화 생성", value=False)

        st.info("💡 **약식 검토**: 5pg 내외 요약 | **RFI**: 자료 요청 리스트 (엑셀) | **뉴스 검색**: '뉴스/동향' 챕터 작성 시 자동 검색")

    return {
        "api_key": api_key,
        "model_name": model_name,
        "thinking_level": "High" if "High" in thinking_level else "Low",
        "use_diagram": use_diagram
    }

def render_input_panel(container, settings):
    """왼쪽 입력 패널 UI"""
    with container:
        st.markdown("### 1️⃣ 입력 (Input)")
        
        # 1. 템플릿 선택
        template_option = st.selectbox(
            "문서 구조 / 템플릿 선택", 
            list(TEMPLATES.keys()), 
            format_func=lambda x: TEMPLATES[x],
            label_visibility="collapsed"
        )
        
        # 구조 추출 기능
        uploaded_structure_file = st.file_uploader("📂 서식 파일 업로드 (구조 추출용)", type=['pdf', 'docx', 'txt', 'md'])
        
        if uploaded_structure_file:
            if st.button("구조 추출 실행"):
                if not settings["api_key"]:
                    st.error("API Key가 필요합니다.")
                else:
                    with st.spinner("구조 분석 중..."):
                        extracted_structure = core_logic.extract_structure(
                            settings["api_key"], 
                            uploaded_structure_file
                        )
                        if extracted_structure:
                            st.session_state['structure_input'] = extracted_structure
                            st.rerun()

        # 기본 구조 텍스트 로드
        default_structure = core_logic.get_default_structure(template_option)
        if 'structure_input' in st.session_state and template_option == 'custom':
            default_structure = st.session_state['structure_input']
            
        # RFI 모드일 때는 구조 입력창 비활성화
        is_rfi = (template_option == 'rfi')
        
        structure_text = st.text_area(
            "문서 구조 편집" if not is_rfi else "문서 구조 (RFI 모드는 자동 설정됩니다)", 
            value=default_structure, 
            height=200 if not is_rfi else 100,
            disabled=is_rfi
        )

        # 2. 데이터 업로드
        st.markdown("##### 2. 분석할 데이터 (Raw Data)")
        uploaded_files = st.file_uploader("IR 자료, 재무제표 등", accept_multiple_files=True, label_visibility="collapsed")
        
        # 3. 컨텍스트 (RFI 모드일 경우 라벨 변경)
        context_label = "3. 대상 기업 및 맥락 (Context)" if not is_rfi else "3. 추가 질문 및 확인 사항 (Questions)"
        st.markdown(f"##### {context_label}")
        context_text = st.text_area(
            "Context Input", 
            placeholder="예: 기업명, 핵심 제품, 주요 우려 사항 등..." if not is_rfi else "예: 재고가 너무 많은 것 같은데 확인 필요, 대표이사 횡령 이슈 체크...",
            height=100,
            label_visibility="collapsed"
        )

        # RFI 전용: 기존 RFI 입력
        rfi_existing = ""
        if is_rfi:
            st.markdown("##### 5. 기존 RFI 목록 (선택)")
            rfi_existing = st.text_area("기존 목록 붙여넣기", height=100, placeholder="기존에 작성된 RFI 표가 있다면 붙여넣으세요.")

        st.markdown("---")
        generate_btn = st.button("🚀 문서 생성 시작", use_container_width=True, type="primary")

        return {
            "template_option": template_option,
            "structure_text": structure_text,
            "uploaded_files": uploaded_files,
            "context_text": context_text,
            "rfi_existing": rfi_existing,
            "generate_btn": generate_btn
        }
import streamlit as st
import utils
import core_logic

# 템플릿 상수 정의
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

def render_settings():
    """상단 설정 영역(Expander)을 렌더링하고 설정값을 반환합니다."""
    
    # URL 쿼리 파라미터에서 API Key 읽기 (브라우저 캐시)
    query_params = st.query_params
    cached_key = query_params.get("api_key", "")
    
    # 리스트로 반환될 경우 첫 번째 값 사용
    if isinstance(cached_key, list):
        cached_key = cached_key[0] if cached_key else ""

    with st.expander("⚙️ 설정 (SETTINGS)", expanded=True):
        # 4개의 컬럼으로 분할 (API Key, Model, Thinking, Diagram)
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
        
        with c1:
            # 기본값으로 캐시된 키 사용
            api_key = st.text_input("Google API Key", value=cached_key, type="password", placeholder="Enter Key...")
            
            # 브라우저(URL) 저장 옵션
            save_to_url = st.checkbox("🔑 브라우저(URL)에 키 저장", value=bool(cached_key), help="체크 시 URL에 키가 저장되어 새로고침 후에도 유지됩니다.")
            
            # 체크박스 상태에 따라 URL 업데이트
            if save_to_url and api_key:
                st.query_params["api_key"] = api_key
            elif not save_to_url:
                if "api_key" in st.query_params:
                    del st.query_params["api_key"]
            
        with c2:
            # [수정됨] 요청하신 모델 리스트로 통일
            model_name = st.selectbox("사용할 모델 (Model)", [
                "gemini-3-pro-preview",
                "gemini-3-flash-preview"
            ], index=0)
            
        with c3:
            thinking_level = st.selectbox("사고 수준 (Thinking)", ["High (추론 깊이 극대화)", "Low (속도 우선)"], index=0)
            
        with c4:
            st.write("") # 줄맞춤용 공백
            st.write("") 
            use_diagram = st.checkbox("🎨 도식화 이미지 생성", value=False)

        # 하단 가이드 배너
        st.info("💡 **약식 검토**: 5pg 내외 요약 (자동압축)  |  **RFI 작성**: 자료 요청 리스트 (엑셀)  |  **뉴스 검색**: '뉴스/동향' 작성 시 Google 검색")

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
        template_keys = list(TEMPLATES.keys())
        template_option = st.selectbox(
            "문서 구조 / 템플릿 선택", 
            template_keys, 
            format_func=lambda x: {
                'simple_review': '1. 약식 투자검토 (요약)',
                'rfi': '2. RFI 작성 (실사 자료 요청)',
                'investment': '3. 투자심사보고서 (표준)',
                'custom': '4. 직접 입력'
            }.get(x, x),
            label_visibility="collapsed"
        )
        
        # 구조 추출 기능 (옵션)
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

        # 구조 입력창
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
        uploaded_files = st.file_uploader("IR 자료, 재무제표 등", accept_multiple_files=True, label_visibility="collapsed")
        
        # 3. 컨텍스트
        st.markdown("##### 3. 대상 기업 및 맥락 (Context)")
        context_text = st.text_area(
            "추가 질문 및 상황 설명", 
            placeholder="예: 기업명, 핵심 제품, 주요 우려 사항 등...",
            height=100,
            label_visibility="collapsed"
        )

        # RFI 전용
        rfi_existing = ""
        if template_option == 'rfi':
            st.markdown("##### 5. 기존 RFI 목록 (선택)")
            rfi_existing = st.text_area("기존 목록 붙여넣기", height=100)

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
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

def render_sidebar():
    """사이드바 설정 UI를 렌더링하고 설정값을 반환합니다."""
    with st.sidebar:
        st.header("⚙️ 설정 (Settings)")
        
        api_key = st.text_input("Google API Key", type="password", help="브라우저 세션에만 저장됩니다.")
        model_name = st.selectbox("Model", [
            "gemini-2.0-flash-exp", 
            "gemini-1.5-pro", 
            "gemini-1.5-flash"
        ], index=0)
        
        thinking_level = st.selectbox("Thinking Level", ["High", "Low"], index=0)
        
        st.info("💡 **가이드**\n\n- **약식 검토**: 5pg 내외 요약\n- **RFI**: 자료 요청 리스트\n- **Grounding**: 뉴스 챕터 작성 시 자동 검색")
        st.caption("Powered by Gemini 2.0 | Converted to Streamlit")
        
        return {
            "api_key": api_key,
            "model_name": model_name,
            "thinking_level": thinking_level
        }

def render_input_panel(container, settings):
    """입력 패널 UI를 렌더링하고 사용자 입력 데이터를 반환합니다."""
    with container:
        st.subheader("📥 입력 (Input)")
        
        # 1. 템플릿 선택
        template_keys = list(TEMPLATES.keys())
        template_option = st.selectbox(
            "1. 문서 구조 / 템플릿", 
            template_keys, 
            format_func=lambda x: {
                'simple_review': '1. 약식 투자검토 (요약)',
                'rfi': '2. RFI 작성 (실사 자료 요청)',
                'investment': '3. 투자심사보고서 (표준)',
                'custom': '4. 직접 입력'
            }.get(x, x)
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

        # 구조 입력창 (기본값 vs 추출값)
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

        # RFI 전용
        rfi_existing = ""
        if template_option == 'rfi':
            st.markdown("##### 5. 기존 RFI 목록 (선택)")
            rfi_existing = st.text_area("기존 목록 붙여넣기", height=100)

        generate_btn = st.button("🚀 문서 생성 시작", use_container_width=True, type="primary")

        return {
            "template_option": template_option,
            "structure_text": structure_text,
            "uploaded_files": uploaded_files,
            "context_text": context_text,
            "rfi_existing": rfi_existing,
            "generate_btn": generate_btn
        }
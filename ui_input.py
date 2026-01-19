import streamlit as st
from google import genai

# 템플릿 정의
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

def render_input_panel(api_key):
    """좌측 입력 패널을 렌더링하고 사용자 입력을 반환합니다."""
    st.subheader("📥 입력 (Input)")
    
    # 1. 템플릿 선택
    template_key = st.selectbox(
        "1. 문서 구조", 
        list(TEMPLATES.keys()), 
        format_func=lambda x: {
            'simple_review': '1. 약식 투자검토',
            'rfi': '2. RFI 작성',
            'investment': '3. 투자심사보고서',
            'custom': '4. 직접 입력'
        }.get(x, x)
    )
    
    # 구조 추출 기능 (옵션)
    uploaded_structure_file = st.file_uploader("📂 서식 파일 (선택 - 구조 추출용)", type=['pdf', 'docx', 'txt'])
    if uploaded_structure_file:
        if st.button("구조 추출 실행"):
            # 여기서 간단한 추출 로직을 바로 실행하거나 core_logic을 호출할 수도 있음
            # 편의상 여기서는 간단한 텍스트 읽기만 수행 (복잡한 로직은 분리 가능)
            import utils
            file_text = utils.parse_uploaded_file(uploaded_structure_file)
            st.session_state['structure_input'] = f"[추출된 구조]\n{file_text[:1000]}..." # 예시
            st.rerun()

    # 구조 텍스트 에디터
    default_structure = TEMPLATES[template_key]
    if 'structure_input' in st.session_state and template_key == 'custom':
        default_structure = st.session_state['structure_input']
        
    structure_text = st.text_area("문서 구조 편집", value=default_structure, height=200)

    # 2. 데이터 업로드
    st.markdown("##### 2. 분석할 데이터")
    uploaded_files = st.file_uploader("IR 자료, 재무제표 등", accept_multiple_files=True)
    
    # 3. 컨텍스트
    st.markdown("##### 3. 맥락")
    context_text = st.text_area("추가 질문 및 상황 설명", height=100)

    # 4. RFI 전용
    rfi_existing = ""
    if template_key == 'rfi':
        rfi_existing = st.text_area("기존 목록 붙여넣기", height=100)

    # 실행 버튼
    generate_btn = st.button("🚀 문서 생성 시작", use_container_width=True, type="primary")

    # 모든 입력을 딕셔너리로 반환
    return {
        "template_key": template_key,
        "structure_text": structure_text,
        "uploaded_files": uploaded_files,
        "context_text": context_text,
        "rfi_existing": rfi_existing,
        "generate_btn": generate_btn
    }
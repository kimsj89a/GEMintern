import streamlit as st
from google import genai
import utils

def render_output_panel(api_key, model_name):
    """우측 결과 패널을 렌더링합니다."""
    st.subheader("📄 결과물 (Result)")
    
    # 결과를 보여줄 컨테이너 (고정 높이, 스크롤 가능)
    result_container = st.container(height=600, border=True)
    
    # 이미 생성된 텍스트가 있다면 표시
    if st.session_state.generated_text:
        with result_container:
            st.markdown(st.session_state.generated_text)
            
        st.markdown("---")
        
        # 1. 수정/보완 요청 (Chat Input)
        refine_query = st.chat_input("결과물 수정/보완 요청 (Enter로 전송)")
        
        if refine_query:
            if not api_key:
                st.error("API Key가 필요합니다.")
            else:
                client = genai.Client(api_key=api_key)
                refine_prompt = f"""
                다음 문서를 사용자의 요청에 맞춰 수정하거나 내용을 추가해줘.
                전체 문서를 다시 쓸 필요는 없고, 수정된 섹션이나 추가된 내용만 마크다운으로 출력해.
                
                [기존 내용]
                {st.session_state.generated_text[:20000]}...
                
                [요청 사항]
                {refine_query}
                """
                
                with st.spinner("수정 내용 생성 중..."):
                    try:
                        resp = client.models.generate_content(model=model_name, contents=refine_prompt)
                        # 기존 내용 뒤에 추가 (또는 교체 로직 구현 가능)
                        st.session_state.generated_text += f"\n\n--- [수정 요청 반영] ---\n{resp.text}"
                        st.rerun()
                    except Exception as e:
                        st.error(f"수정 중 오류: {e}")

        # 2. 다운로드 버튼
        col1, col2 = st.columns(2)
        with col1:
            # utils.py의 개선된 create_docx 사용
            docx_data = utils.create_docx(st.session_state.generated_text)
            st.download_button(
                label="📄 Word로 저장 (서식 적용됨)",
                data=docx_data,
                file_name="investment_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        with col2:
            st.button("📊 PPT로 저장 (준비중)", disabled=True, use_container_width=True)
            
    return result_container
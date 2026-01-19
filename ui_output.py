import streamlit as st
import utils
import core_logic

def render_output_panel(container, settings, inputs):
    """결과 패널을 렌더링하고 스트리밍 출력 및 다운로드 기능을 처리합니다."""
    with container:
        # 헤더 스타일 조정
        c_head1, c_head2 = st.columns([2, 1])
        with c_head1:
             st.markdown("### ®️ 결과물 (Result)")
        with c_head2:
             # 이미지의 복사/편집 버튼 흉내 (기능은 추후 구현)
             st.markdown('<div style="text-align: right; color: gray; font-size: 0.8rem;">📄 복사 | ✏️ 편집</div>', unsafe_allow_html=True)

        result_container = st.container(height=600, border=True)
        
        # 1. 생성 로직 (inputs 딕셔너리 사용)
        if inputs['generate_btn']:
            if not settings['api_key']:
                st.error("설정 패널에서 API Key를 입력해주세요.")
            else:
                with result_container:
                    response_placeholder = st.empty()
                    full_response = ""
                    
                    try:
                        with st.spinner("분석 및 보고서 작성 중..."):
                            # core_logic 호출
                            stream = core_logic.generate_report_stream(
                                settings['api_key'],
                                settings['model_name'],
                                inputs,
                                settings['thinking_level']
                            )
                            
                            for chunk in stream:
                                if chunk.text:
                                    full_response += chunk.text
                                    response_placeholder.markdown(full_response + "▌")
                            
                            response_placeholder.markdown(full_response)
                            st.session_state.generated_text = full_response
                            
                    except Exception as e:
                        st.error(f"생성 중 오류 발생: {e}")

        # 2. 결과 표시 (이미 생성된 경우)
        elif st.session_state.generated_text:
            with result_container:
                st.markdown(st.session_state.generated_text)

        # 3. 하단 액션 (수정 및 다운로드)
        if st.session_state.generated_text:
            st.markdown("---")
            
            # 수정 요청
            refine_query = st.chat_input("결과물 수정/보완 요청 (Enter로 전송)")
            if refine_query:
                if not settings['api_key']:
                    st.error("API Key 필요")
                else:
                    with st.spinner("수정 내용 생성 중..."):
                        try:
                            refined_text = core_logic.refine_report(
                                settings['api_key'],
                                settings['model_name'],
                                st.session_state.generated_text,
                                refine_query
                            )
                            st.session_state.generated_text += f"\n\n--- [추가 요청 반영] ---\n{refined_text}"
                            st.rerun()
                        except Exception as e:
                            st.error(f"수정 중 오류: {e}")

            # 다운로드 버튼
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                # utils.create_docx 사용
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
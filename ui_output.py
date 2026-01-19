import streamlit as st
import utils
import core_logic

def render_output_panel(container, settings, inputs):
    with container:
        c_head1, c_head2 = st.columns([2, 1])
        with c_head1:
             st.markdown("### ®️ 결과물 (Result)")
        with c_head2:
             st.markdown('<div style="text-align: right; color: gray; font-size: 0.8rem;">📄 복사 | ✏️ 편집</div>', unsafe_allow_html=True)

        result_container = st.container(height=600, border=True)
        
        # 생성 로직
        if inputs['generate_btn']:
            if not settings['api_key']:
                st.error("설정 패널에서 API Key를 입력해주세요.")
            else:
                with result_container:
                    response_placeholder = st.empty()
                    full_response = ""
                    
                    try:
                        with st.status("🚀 분석 작업을 시작합니다...", expanded=True) as status:
                            st.write("📂 1. 파일을 읽고 텍스트를 추출합니다...")
                            file_context, _ = core_logic.parse_all_files(inputs['uploaded_files'])
                            
                            st.write("🧠 2. AI가 전문 심사역 페르소나로 분석을 시작합니다...")
                            stream = core_logic.generate_report_stream(
                                settings['api_key'],
                                settings['model_name'],
                                inputs,
                                settings['thinking_level'],
                                file_context
                            )
                            
                            st.write("✍️ 3. 문서를 작성 중입니다 (스트리밍)...")
                            for chunk in stream:
                                if chunk.text:
                                    full_response += chunk.text
                                    response_placeholder.markdown(full_response + "▌")
                            
                            status.update(label="✅ 작성이 완료되었습니다!", state="complete", expanded=False)
                        
                        response_placeholder.markdown(full_response)
                        st.session_state.generated_text = full_response
                            
                    except Exception as e:
                        st.error(f"생성 중 오류 발생: {e}")

        elif st.session_state.generated_text:
            with result_container:
                st.markdown(st.session_state.generated_text)

        # 하단 액션
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
            is_rfi_mode = (inputs['template_option'] == 'rfi')

            with col_d1:
                if is_rfi_mode:
                    # RFI 모드: Excel 다운로드
                    excel_data = utils.create_excel(st.session_state.generated_text)
                    st.download_button(
                        label="📉 RFI 엑셀(Excel)로 저장",
                        data=excel_data,
                        file_name="RFI_List.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    # 일반 모드: Word 다운로드
                    docx_data = utils.create_docx(st.session_state.generated_text)
                    st.download_button(
                        label="📄 Word로 저장",
                        data=docx_data,
                        file_name="investment_report.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
            
            with col_d2:
                # PPT는 아직 미구현 (Placeholder)
                st.button("📊 PPT로 저장 (구현 예정)", disabled=True, use_container_width=True)
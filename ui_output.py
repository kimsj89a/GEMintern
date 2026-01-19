import streamlit as st
import streamlit.components.v1 as components
import utils
import core_logic

def render_output_panel(container, settings, inputs):
    with container:
        c_head1, c_head2 = st.columns([2, 1])
        with c_head1:
             st.markdown("### 📄 결과물 (Result)")
        with c_head2:
             st.markdown('<div style="text-align: right; color: gray; font-size: 0.8rem;">📄 복사 | ✏️ 편집</div>', unsafe_allow_html=True)

        st.markdown('<div id="result_anchor"></div>', unsafe_allow_html=True)

        # [UI 분리] 진행 상태(Status)와 결과(Result)를 물리적으로 분리
        # Status는 임시 컨테이너에 표시하고, 결과는 그 아래 영구 컨테이너에 표시
        
        # 1. 상태 표시 영역 (Progress Area)
        status_placeholder = st.empty()
        
        # 2. 결과 표시 영역 (Result Area)
        result_container = st.container(height=600, border=True)
        
        # 생성 로직
        if inputs['generate_btn']:
            components.html("""
                <script>
                    window.parent.document.getElementById('result_anchor').scrollIntoView({behavior: 'smooth'});
                </script>
            """, height=0)

            if not settings['api_key']:
                st.error("설정 패널에서 API Key를 입력해주세요.")
            else:
                try:
                    inputs['use_diagram'] = settings['use_diagram']

                    # 상태창은 status_placeholder 안에 생성
                    with status_placeholder.status("🚀 분석 작업을 시작합니다...", expanded=True) as status:
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
                        
                        # [중요] 스트리밍 결과를 result_container (하단)에 출력
                        full_response = ""
                        with result_container:
                            response_placeholder = st.empty()
                            for chunk in stream:
                                if chunk.text:
                                    full_response += chunk.text
                                    response_placeholder.markdown(full_response + "▌")
                            
                            # 스트리밍 완료 후 커서 제거
                            response_placeholder.markdown(full_response)
                        
                        # 완료 상태 업데이트
                        status.update(label="✅ 작성이 완료되었습니다!", state="complete", expanded=False)
                        st.session_state.generated_text = full_response
                        
                except Exception as e:
                    st.error(f"생성 중 오류 발생: {e}")

        elif st.session_state.generated_text:
            # 이미 생성된 텍스트가 있으면 결과 컨테이너에 표시
            with result_container:
                st.markdown(st.session_state.generated_text)

        # 하단 액션 (수정 및 다운로드)
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

            # [동적 파일명 생성]
            file_name_docx = utils.generate_filename_from_content(st.session_state.generated_text, "Investment_Report")
            file_name_xlsx = utils.generate_filename_from_content(st.session_state.generated_text, "RFI_List").replace('.docx', '.xlsx')

            with col_d1:
                if is_rfi_mode:
                    excel_data = utils.create_excel(st.session_state.generated_text)
                    st.download_button(
                        label=f"📉 RFI 엑셀 저장 ({file_name_xlsx})",
                        data=excel_data,
                        file_name=file_name_xlsx,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    docx_data = utils.create_docx(st.session_state.generated_text)
                    st.download_button(
                        label=f"📄 Word 저장 ({file_name_docx})",
                        data=docx_data,
                        file_name=file_name_docx,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
            
            with col_d2:
                st.button("📊 PPT로 저장 (구현 예정)", disabled=True, use_container_width=True)
import streamlit as st
import streamlit.components.v1 as components
import utils
import utils_ppt
import core_logic

def render_output_panel(container, settings, inputs):
    with container:
        c_head1, c_head2 = st.columns([2, 1])
        with c_head1:
             st.markdown("### 📄 결과물 (Result)")
        with c_head2:
             st.markdown('<div style="text-align: right; color: gray; font-size: 0.8rem;">📄 복사 | ✏️ 편집</div>', unsafe_allow_html=True)

        st.markdown('<div id="result_anchor"></div>', unsafe_allow_html=True)

        # UI 분리
        status_placeholder = st.empty()
        result_container = st.container(height=600, border=True)
        
        # [상태 관리] 현재 출력된 텍스트의 모드 (Word vs PPT) 추적
        if "active_mode" not in st.session_state:
            st.session_state.active_mode = inputs['template_option']

        # -------------------------------------------------------------------
        # 1. 문서 생성 로직 (Generate)
        # -------------------------------------------------------------------
        if inputs['generate_btn']:
            # 생성 시작 시 현재 입력된 모드로 초기화
            st.session_state.active_mode = inputs['template_option']
            
            # 스크롤 이동
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

                    with status_placeholder.status("🚀 분석 작업을 시작합니다...", expanded=True) as status:
                        st.write("📂 1. 파일을 읽고 텍스트를 추출합니다...")
                        file_context, _ = core_logic.parse_all_files(inputs['uploaded_files'])
                        
                        st.write(f"🧠 2. AI가 [{st.session_state.active_mode}] 페르소나로 분석을 시작합니다...")
                        stream = core_logic.generate_report_stream(
                            settings['api_key'],
                            settings['model_name'],
                            inputs,
                            settings['thinking_level'],
                            file_context
                        )
                        
                        st.write("✍️ 3. 문서를 작성 중입니다 (스트리밍)...")
                        
                        full_response = ""
                        with result_container:
                            response_placeholder = st.empty()
                            for chunk in stream:
                                if chunk.text:
                                    full_response += chunk.text
                                    response_placeholder.markdown(full_response + "▌")
                            
                            response_placeholder.markdown(full_response)
                        
                        status.update(label="✅ 작성이 완료되었습니다!", state="complete", expanded=False)
                        st.session_state.generated_text = full_response
                        
                except Exception as e:
                    st.error(f"생성 중 오류 발생: {e}")

        # -------------------------------------------------------------------
        # 2. 결과 표시 (Display)
        # -------------------------------------------------------------------
        elif st.session_state.generated_text:
            with result_container:
                st.markdown(st.session_state.generated_text)

        # -------------------------------------------------------------------
        # 3. 하단 액션 (Convert & Download)
        # -------------------------------------------------------------------
        if st.session_state.generated_text:
            st.markdown("---")
            
            # (1) PPT 변환 버튼 (현재 모드가 PPT가 아닐 때만 노출)
            # RFI 모드일 때는 굳이 PPT 변환이 필요 없으므로 제외할 수도 있음
            if st.session_state.active_mode != 'presentation' and st.session_state.active_mode != 'rfi':
                if st.button("📊 이 내용으로 발표자료(PPT) 생성하기", use_container_width=True):
                    if not settings['api_key']:
                        st.error("API Key가 필요합니다.")
                    else:
                        try:
                            # PPT 변환을 위한 가상 입력값 생성
                            ppt_inputs = inputs.copy()
                            ppt_inputs['template_option'] = 'presentation' # 모드 강제 변경
                            ppt_inputs['structure_text'] = core_logic.get_default_structure('presentation') # 구조 강제 변경
                            
                            st.session_state.active_mode = 'presentation' # 상태 업데이트

                            with status_placeholder.status("🔄 PPT 스타일로 변환 중입니다...", expanded=True) as status:
                                st.write("📂 기존 데이터를 PPT 프레임워크로 재해석합니다...")
                                file_context, _ = core_logic.parse_all_files(inputs['uploaded_files'])
                                
                                st.write("🧠 Slide Deck 전문가 페르소나(PPT System)를 로드합니다...")
                                stream = core_logic.generate_report_stream(
                                    settings['api_key'],
                                    settings['model_name'],
                                    ppt_inputs, # 수정된 입력 사용
                                    settings['thinking_level'],
                                    file_context
                                )
                                
                                st.write("✍️ 슬라이드별 핵심 요약 작성 중...")
                                full_response = ""
                                with result_container:
                                    response_placeholder = st.empty()
                                    for chunk in stream:
                                        if chunk.text:
                                            full_response += chunk.text
                                            response_placeholder.markdown(full_response + "▌")
                                    response_placeholder.markdown(full_response)
                                
                                status.update(label="✅ PPT 변환 완료! 아래에서 다운로드하세요.", state="complete", expanded=False)
                                st.session_state.generated_text = full_response
                                st.rerun() # 버튼 상태 갱신을 위해 리로드

                        except Exception as e:
                            st.error(f"PPT 변환 중 오류: {e}")

            # (2) 수정 요청 (Refine)
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

            # (3) 다운로드 버튼
            st.write("") # 간격
            col_d1, col_d2 = st.columns(2)
            
            # 현재 활성화된 모드에 따라 파일명 접미사 결정
            current_mode_option = st.session_state.get('active_mode', inputs['template_option'])
            file_name_base = utils.generate_filename(inputs['uploaded_files'], current_mode_option)
            
            file_name_docx = file_name_base
            file_name_xlsx = file_name_base.replace('.docx', '.xlsx')
            file_name_pptx = file_name_base.replace('.docx', '.pptx')

            is_rfi_mode = (current_mode_option == 'rfi')
            is_ppt_mode = (current_mode_option == 'presentation')

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
                    # PPT 모드여도 텍스트 확인용으로 Word 다운로드는 유지하거나, 
                    # 헷갈리지 않게 PPT 모드일 땐 PPT 버튼을 강조할 수 있음.
                    # 여기선 기본적으로 Word는 항상 제공
                    docx_data = utils.create_docx(st.session_state.generated_text)
                    st.download_button(
                        label=f"📄 Word 저장 ({file_name_docx})",
                        data=docx_data,
                        file_name=file_name_docx,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
            
            with col_d2:
                # PPT 저장 버튼
                # PPT 모드이거나, 일반 보고서라도 PPT 변환을 원하는 경우 (자동 변환)
                ppt_data = utils_ppt.create_ppt(st.session_state.generated_text)
                
                # 버튼 스타일: PPT 모드일 때는 Primary(강조), 아니면 Secondary
                btn_type = "primary" if is_ppt_mode else "secondary"
                
                st.download_button(
                    label=f"📊 PPT로 저장 ({file_name_pptx})", 
                    data=ppt_data,
                    file_name=file_name_pptx,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                    type=btn_type
                )
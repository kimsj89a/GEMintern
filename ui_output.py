import streamlit as st
import streamlit.components.v1 as components
import utils
import utils_ppt
import core_logic

def render_output_panel(container, settings, inputs):
    with container:
        # --------------------------------------------------------
        # 헤더 & 기능 버튼 (편집/복사)
        # --------------------------------------------------------
        c_head1, c_head2 = st.columns([1, 1])
        with c_head1:
             st.markdown("### 📄 결과물 (Result)")
        
        # [기능 구현] 편집 및 복사 버튼
        with c_head2:
            sub_c1, sub_c2, sub_c3 = st.columns([2, 1, 1])
            with sub_c2:
                # 편집 모드 토글
                if "is_editing" not in st.session_state:
                    st.session_state.is_editing = False
                
                edit_label = "✏️ 완료" if st.session_state.is_editing else "✏️ 편집"
                if st.button(edit_label, key="btn_toggle_edit", use_container_width=True):
                    st.session_state.is_editing = not st.session_state.is_editing
                    st.rerun()

            with sub_c3:
                # 복사 기능 (st.code 활용)
                if st.button("📋 복사", key="btn_copy_view", use_container_width=True):
                    st.toast("아래 코드를 클릭하여 복사하세요", icon="📋")
                    st.session_state.show_copy_code = True
                else:
                    if "show_copy_code" not in st.session_state:
                        st.session_state.show_copy_code = False

        st.markdown('<div id="result_anchor"></div>', unsafe_allow_html=True)

        # --------------------------------------------------------
        # 결과 표시 영역
        # --------------------------------------------------------
        status_placeholder = st.empty()
        result_container = st.container(height=600, border=True)
        
        # [상태 관리] 모드 추적
        if "active_mode" not in st.session_state:
            st.session_state.active_mode = inputs['template_option']

        # 1. 생성 로직
        if inputs['generate_btn']:
            st.session_state.active_mode = inputs['template_option']
            st.session_state.is_editing = False # 생성 시 편집모드 해제
            st.session_state.show_copy_code = False

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
                            settings['api_key'], settings['model_name'], inputs, settings['thinking_level'], file_context
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

        # 2. 결과 표시 (편집 모드 vs 뷰어 모드)
        elif st.session_state.generated_text:
            with result_container:
                # (A) 복사용 코드 블록 (잠깐 표시)
                if st.session_state.get("show_copy_code"):
                    st.info("우측 상단의 복사 버튼을 누르세요. (닫으려면 '복사' 버튼 다시 클릭)")
                    st.code(st.session_state.generated_text, language="markdown")
                
                # (B) 편집 모드
                if st.session_state.is_editing:
                    new_text = st.text_area(
                        "내용 편집", 
                        value=st.session_state.generated_text, 
                        height=550,
                        label_visibility="collapsed"
                    )
                    st.session_state.generated_text = new_text # 실시간 반영
                # (C) 뷰어 모드
                else:
                    st.markdown(st.session_state.generated_text)

        # 3. 하단 액션
        if st.session_state.generated_text:
            st.markdown("---")
            
            # PPT 변환 버튼
            if st.session_state.active_mode != 'presentation' and st.session_state.active_mode != 'rfi':
                if st.button("📊 이 내용으로 발표자료(PPT) 생성하기", use_container_width=True):
                    if not settings['api_key']:
                        st.error("API Key 필요")
                    else:
                        try:
                            ppt_inputs = inputs.copy()
                            ppt_inputs['template_option'] = 'presentation'
                            ppt_inputs['structure_text'] = core_logic.get_default_structure('presentation')
                            st.session_state.active_mode = 'presentation'
                            st.session_state.is_editing = False

                            with status_placeholder.status("🔄 PPT 스타일로 변환 중...", expanded=True) as status:
                                file_context, _ = core_logic.parse_all_files(inputs['uploaded_files'])
                                stream = core_logic.generate_report_stream(
                                    settings['api_key'], settings['model_name'], ppt_inputs, settings['thinking_level'], file_context
                                )
                                full_response = ""
                                with result_container:
                                    response_placeholder = st.empty()
                                    for chunk in stream:
                                        if chunk.text:
                                            full_response += chunk.text
                                            response_placeholder.markdown(full_response + "▌")
                                    response_placeholder.markdown(full_response)
                                status.update(label="✅ PPT 변환 완료!", state="complete", expanded=False)
                                st.session_state.generated_text = full_response
                                st.rerun()
                        except Exception as e:
                            st.error(f"PPT 변환 오류: {e}")

            # Refine
            refine_query = st.chat_input("결과물 수정/보완 요청")
            if refine_query:
                if not settings['api_key']: st.error("API Key 필요")
                else:
                    with st.spinner("수정 내용 생성 중..."):
                        try:
                            refined_text = core_logic.refine_report(
                                settings['api_key'], settings['model_name'], st.session_state.generated_text, refine_query
                            )
                            st.session_state.generated_text += f"\n\n--- [추가 요청 반영] ---\n{refined_text}"
                            st.rerun()
                        except Exception as e:
                            st.error(f"수정 오류: {e}")

            # Download
            st.write("")
            col_d1, col_d2 = st.columns(2)
            current_mode = st.session_state.get('active_mode', inputs['template_option'])
            fname = utils.generate_filename(inputs['uploaded_files'], current_mode)
            
            with col_d1:
                if current_mode == 'rfi':
                    st.download_button("📉 RFI 엑셀 저장", utils.create_excel(st.session_state.generated_text), fname.replace('.docx','.xlsx'), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                else:
                    st.download_button(f"📄 Word 저장 ({fname})", utils.create_docx(st.session_state.generated_text), fname, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            
            with col_d2:
                btn_type = "primary" if current_mode == 'presentation' else "secondary"
                st.download_button(f"📊 PPT 저장 ({fname.replace('.docx','.pptx')})", utils_ppt.create_ppt(st.session_state.generated_text), fname.replace('.docx','.pptx'), "application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True, type=btn_type)
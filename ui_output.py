import streamlit as st
import streamlit.components.v1 as components
import utils
import utils_ppt
import core_logic
import core_chained
import core_rag

def render_output_panel(container, settings, inputs, key_prefix="output"):
    # State keys with prefix to isolate tabs
    k_editing = f"{key_prefix}_is_editing"
    k_copy = f"{key_prefix}_show_copy_code"
    k_text = f"{key_prefix}_generated_text"
    k_mode = f"{key_prefix}_active_mode"
    k_ocr = f"{key_prefix}_ocr_text"  # OCR 추출 텍스트 저장용

    with container:
        c_head1, c_head2 = st.columns([1, 1])
        with c_head1:
             st.markdown("### 📄 결과문(Result)")

        with c_head2:
            sub_c1, sub_c2, sub_c3 = st.columns([2, 1, 1])
            with sub_c2:
                if k_editing not in st.session_state:
                    st.session_state[k_editing] = False
                is_editing = st.session_state[k_editing]
                edit_label = "✅ 편집 완료" if is_editing else "✏️ 직접 편집"
                edit_type = "primary" if is_editing else "secondary"
                if st.button(edit_label, key=f"{key_prefix}_btn_toggle_edit",
                             use_container_width=True, type=edit_type):
                    st.session_state[k_editing] = not st.session_state[k_editing]
                    st.rerun()

            with sub_c3:
                if st.button("📋 복사", key=f"{key_prefix}_btn_copy_view", use_container_width=True):
                    st.toast("아래 코드를 클릭하여 복사하세요.", icon="📋")
                    st.session_state[k_copy] = True
                else:
                    if k_copy not in st.session_state:
                        st.session_state[k_copy] = False

        anchor_id = f"{key_prefix}_result_anchor"
        st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)

        status_placeholder = st.empty()
        result_container = st.container(height=600, border=True)

        if k_mode not in st.session_state:
            st.session_state[k_mode] = inputs['template_option']

        # Initialize text state if missing
        if k_text not in st.session_state:
            st.session_state[k_text] = ""

        # 1. 생성 로직
        if inputs['generate_btn']:
            st.session_state[k_mode] = inputs['template_option']
            st.session_state[k_editing] = False
            st.session_state[k_copy] = False

            components.html(f"""
                <script>
                    window.parent.document.getElementById('{anchor_id}').scrollIntoView({{behavior: 'smooth'}});
                </script>
            """, height=0)

            if not settings['api_key']:
                st.error("설정 패널에서 API Key를 입력해주세요.")
            else:
                try:
                    inputs['use_diagram'] = settings['use_diagram']

                    # [수정] RFI 모드 여부 확인
                    is_rfi_mode = (inputs['template_option'] == 'rfi')

                    with status_placeholder.status("✅ 분석 작업이 시작됩니다..", expanded=True) as status:
                        # Document AI 설정 가져오기
                        docai_config = settings.get('docai_config')

                        use_rag = settings.get('use_rag', False) and core_rag.is_rag_available()

                        if is_rfi_mode:
                            if inputs.get('uploaded_files'):
                                st.write("📁 1. 업로드된 파일의 내용을 분석 중입니다 (OCR/Text)...")
                                file_context, _, rag_result = core_logic.parse_all_files(
                                    inputs['uploaded_files'],
                                    saved_files=inputs.get('selected_saved_files'),
                                    read_content=True,
                                    api_key=settings['api_key'],
                                    docai_config=docai_config,
                                    template_option=inputs['template_option'],
                                    use_rag=use_rag,
                                )
                            else:
                                st.write("📁 1. (Fast Mode) 파일 내용은 건너뛰고 파일명만 추출합니다..")
                                file_context, _, rag_result = core_logic.parse_all_files(
                                    inputs['uploaded_files'],
                                    saved_files=inputs.get('selected_saved_files'),
                                    read_content=False,
                                    template_option=inputs['template_option'],
                                )
                        else:
                            # OCR 방식 표시
                            if docai_config:
                                st.write("📁 1. Document AI OCR로 파일을 마크다운으로 변환 중입니다...")
                            elif utils.MARKITDOWN_AVAILABLE:
                                st.write("📁 1. MarkItDown으로 파일을 마크다운으로 변환 중입니다...")
                            else:
                                st.write("📁 1. 파일을 분석 중입니다 (텍스트 추출 + OCR)...")
                            file_context, _, rag_result = core_logic.parse_all_files(
                                inputs['uploaded_files'],
                                saved_files=inputs.get('selected_saved_files'),
                                read_content=True,
                                api_key=settings['api_key'],
                                docai_config=docai_config,
                                template_option=inputs['template_option'],
                                use_rag=use_rag,
                            )
                            # OCR 텍스트 저장 (다운로드용)
                            st.session_state[k_ocr] = file_context

                        # RAG 인덱싱 결과 표시
                        if use_rag and rag_result:
                            if rag_result.get('success'):
                                indexed = rag_result.get('indexed', [])
                                skipped = rag_result.get('skipped', [])
                                if indexed:
                                    st.write(f"🔍 1-1. RAG 인덱싱 완료: {len(indexed)}개 문서")
                                if skipped:
                                    st.write(f"🔍 1-1. RAG 이미 인덱싱됨: {len(skipped)}개 문서 (스킵)")
                            else:
                                st.write(f"⚠️ RAG 인덱싱 오류: {rag_result.get('error', 'unknown')}")

                        # RAG 컨텍스트 보강
                        if use_rag and core_rag.is_indexed() and not is_rfi_mode:
                            st.write("🔍 1-2. RAG 검색으로 관련 정보를 보강 중입니다...")
                            try:
                                rag_context = core_logic.get_rag_enriched_context(
                                    settings['api_key'],
                                    inputs.get('structure_text', ''),
                                    inputs.get('context_text', ''),
                                    inputs['template_option'],
                                )
                                if rag_context:
                                    file_context += rag_context
                                    st.write("✅ RAG 검색 결과가 컨텍스트에 추가되었습니다.")
                            except Exception as e:
                                st.write(f"⚠️ RAG 검색 오류 (생성은 계속됩니다): {e}")

                        st.write(f"🤖 2. AI가 [{st.session_state[k_mode]}] 템플릿으로 분석을 시작합니다..")

                        # 생성 모드에 따라 다른 함수 호출
                        gen_mode = inputs.get('generation_mode', 'single')
                        if gen_mode == 'chained' and core_chained.is_chained_supported(inputs['template_option']):
                            part_count = len(core_chained.CHAINED_PARTS.get(inputs['template_option'], []))
                            st.write(f"🔗 3. {part_count}단계 분할 생성 모드로 문서를 작성합니다..")
                            stream = core_logic.generate_report_stream_chained(
                                settings['api_key'], settings['model_name'], inputs, settings['thinking_level'], file_context
                            )
                        else:
                            st.write("🔗 3. 문서를 작성 중입니다 (스트리밍)...")
                            stream = core_logic.generate_report_stream(
                                settings['api_key'], settings['model_name'], inputs, settings['thinking_level'], file_context
                            )

                        full_response = ""
                        with result_container:
                            response_placeholder = st.empty()
                            for chunk in stream:
                                if chunk.text:
                                    full_response += chunk.text
                                    response_placeholder.markdown(full_response + "▌")
                            response_placeholder.markdown(full_response)

                        status.update(label="✅ 작성이 완료되었습니다", state="complete", expanded=False)
                        st.session_state[k_text] = full_response
                except Exception as e:
                    st.error(f"생성 중 오류 발생: {e}")

        # 2. 결과 표시
        elif st.session_state[k_text]:
            with result_container:
                if st.session_state.get(k_copy):
                    st.info("저장 단계에서 복사 버튼을 눌렀어요. (펼쳐진 후 '복사' 버튼 다시 클릭)")
                    st.code(st.session_state[k_text], language="markdown")

                if st.session_state[k_editing]:
                    new_text = st.text_area("내용 편집", value=st.session_state[k_text], height=550, label_visibility="collapsed", key=f"{key_prefix}_edit_area")
                    st.session_state[k_text] = new_text
                else:
                    st.markdown(st.session_state[k_text])

        # 빈 상태 UI (아직 결과가 없는 경우)
        else:
            with result_container:
                st.markdown(
                    "<div style='text-align:center;padding:80px 20px;color:var(--gem-muted);'>"
                    "<p style='font-size:2.5rem;margin-bottom:8px;'>📄</p>"
                    "<p style='font-weight:600;font-size:1.05rem;'>아직 생성된 결과가 없습니다</p>"
                    "<p style='font-size:0.85rem;'>설정을 완료하고 '생성' 버튼을 눌러주세요.</p>"
                    "</div>",
                    unsafe_allow_html=True,
                )

        # 3. 하단 액션
        if st.session_state[k_text]:
            st.markdown("---")

            # PPT 변환 버튼
            if st.session_state[k_mode] not in ['presentation', 'paper_review', 'rfi']:
                if st.button("📊 이 내용으로 발표자료(PPT) 생성하기", use_container_width=True, key=f"{key_prefix}_btn_ppt_convert"):
                    if not settings['api_key']:
                        st.error("API Key 필요")
                    else:
                        try:
                            ppt_inputs = inputs.copy()
                            ppt_inputs['template_option'] = 'presentation'
                            ppt_inputs['structure_text'] = core_logic.get_default_structure('presentation')
                            st.session_state[k_mode] = 'presentation'
                            st.session_state[k_editing] = False

                            with status_placeholder.status("📊 PPT 스타일로 변환 중..", expanded=True) as status:
                                # PPT 변환 시에도 기존 데이터를 활용함 (파일 다시 읽을 필요 X)
                                # 하지만 file_context가 필요하므로 다시 파싱 (이미 로컬 캐시되어 빠름)
                                docai_config = settings.get('docai_config')
                                file_context, _, _ = core_logic.parse_all_files(
                                    inputs['uploaded_files'],
                                    saved_files=inputs.get('selected_saved_files'),
                                    read_content=True,
                                    api_key=settings['api_key'],
                                    docai_config=docai_config,
                                    template_option=ppt_inputs['template_option'],
                                )
                                # 프로젝트 문서 병합
                                ppt_project_docs = settings.get('project_docs_text', '')
                                if ppt_project_docs:
                                    file_context = ppt_project_docs + "\n\n" + file_context
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
                                st.session_state[k_text] = full_response
                                st.rerun()
                        except Exception as e:
                            st.error(f"PPT 변환 오류: {e}")

            # Refine
            refine_query = st.chat_input("결과문 수정/보완 요청", key=f"{key_prefix}_chat_refine")
            if refine_query:
                if not settings['api_key']: st.error("API Key 필요")
                else:
                    with st.spinner("✏️ 수정 내용을 생성하는 중..."):
                        try:
                            refined_text = core_logic.refine_report(
                                settings['api_key'], settings['model_name'], st.session_state[k_text], refine_query
                            )
                            st.session_state[k_text] += f"\n\n--- [추가 요청 반영] ---\n{refined_text}"
                            st.rerun()
                        except Exception as e:
                            st.error(f"수정 오류: {e}")

            # Download
            st.write("")
            col_d1, col_d2, col_d3 = st.columns(3)
            current_mode = st.session_state.get(k_mode, inputs['template_option'])
            fname = utils.generate_filename(
                inputs['uploaded_files'], current_mode,
                generated_text=st.session_state.get(k_text, "")
            )

            with col_d1:
                if current_mode == 'rfi':
                    st.download_button(
                        "📥 RFI 엑셀 다운로드",
                        utils.create_excel(st.session_state[k_text]),
                        fname.replace(".docx", ".xlsx"),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"{key_prefix}_dl_rfi",
                    )
                else:
                    st.download_button(
                        "📄 Word 다운로드",
                        utils.create_docx(st.session_state[k_text]),
                        fname,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        key=f"{key_prefix}_dl_word",
                    )

            with col_d2:
                btn_type = "primary" if current_mode in ['presentation', 'paper_review'] else "secondary"
                st.download_button(
                    "📊 PPT 다운로드",
                    utils_ppt.create_ppt(st.session_state[k_text]),
                    fname.replace(".docx", ".pptx"),
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                    type=btn_type,
                    key=f"{key_prefix}_dl_ppt",
                )

            with col_d3:
                # OCR 텍스트 다운로드 (Document AI 사용 시)
                ocr_text = st.session_state.get(k_ocr, "")
                if ocr_text:
                    st.download_button(
                        "📝 OCR 텍스트 다운로드",
                        ocr_text,
                        fname.replace(".docx", "_ocr.txt"),
                        "text/plain",
                        use_container_width=True,
                        key=f"{key_prefix}_dl_ocr",
                    )

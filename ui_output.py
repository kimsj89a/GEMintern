import streamlit as st
import streamlit.components.v1 as components
import utils
import utils_ppt
import core_logic
import core_chained

def render_output_panel(container, settings, inputs, key_prefix="output"):
    # State keys with prefix to isolate tabs
    k_editing = f"{key_prefix}_is_editing"
    k_copy = f"{key_prefix}_show_copy_code"
    k_text = f"{key_prefix}_generated_text"
    k_mode = f"{key_prefix}_active_mode"
    k_ocr = f"{key_prefix}_ocr_text"  # OCR 異붿텧 ?띿뒪????μ슜

    with container:
        c_head1, c_head2 = st.columns([1, 1])
        with c_head1:
             st.markdown("### ?뱞 寃곌낵臾?(Result)")

        with c_head2:
            sub_c1, sub_c2, sub_c3 = st.columns([2, 1, 1])
            with sub_c2:
                if k_editing not in st.session_state:
                    st.session_state[k_editing] = False
                edit_label = "?륅툘 ?꾨즺" if st.session_state[k_editing] else "?륅툘 ?몄쭛"
                if st.button(edit_label, key=f"{key_prefix}_btn_toggle_edit", use_container_width=True):
                    st.session_state[k_editing] = not st.session_state[k_editing]
                    st.rerun()

            with sub_c3:
                if st.button("?뱥 蹂듭궗", key=f"{key_prefix}_btn_copy_view", use_container_width=True):
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

        # 1. ?앹꽦 濡쒖쭅
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
                st.error("?ㅼ젙 ?⑤꼸?먯꽌 API Key瑜??낅젰?댁＜?몄슂.")
            else:
                try:
                    inputs['use_diagram'] = settings['use_diagram']
                    
                    # [?섏젙] RFI 紐⑤뱶 ?щ? ?뺤씤
                    is_rfi_mode = (inputs['template_option'] == 'rfi')

                    with status_placeholder.status("?? 遺꾩꽍 ?묒뾽???쒖옉?⑸땲??..", expanded=True) as status:
                        # Document AI ?ㅼ젙 媛?몄삤湲?
                        docai_config = settings.get('docai_config')

                        if is_rfi_mode:
                            st.write("?뱛 1. (Fast Mode) ?뚯씪 ?댁슜??嫄대꼫?곌퀬 ?뚯씪紐낅쭔 異붿텧?⑸땲??..")
                            file_context, _ = core_logic.parse_all_files(
                                inputs['uploaded_files'],
                                read_content=False,
                                template_option=inputs['template_option'],
                            )
                        else:
                            # OCR 諛⑹떇 ?쒖떆
                            if docai_config:
                                st.write("?뱛 1. Document AI OCR濡??뚯씪??留덊겕?ㅼ슫?쇰줈 蹂??以묒엯?덈떎...")
                            elif utils.MARKITDOWN_AVAILABLE:
                                st.write("?뱛 1. MarkItDown?쇰줈 ?뚯씪??留덊겕?ㅼ슫?쇰줈 蹂??以묒엯?덈떎...")
                            else:
                                st.write("?뱛 1. ?뚯씪??遺꾩꽍 以묒엯?덈떎 (?띿뒪??異붿텧 + OCR)...")
                            file_context, _ = core_logic.parse_all_files(
                                inputs['uploaded_files'],
                                read_content=True,
                                api_key=settings['api_key'],
                                docai_config=docai_config,
                                template_option=inputs['template_option'],
                            )
                            # OCR ?띿뒪?????(?ㅼ슫濡쒕뱶??
                            st.session_state[k_ocr] = file_context

                        st.write(f"?쭬 2. AI媛 [{st.session_state[k_mode]}] ?섎Ⅴ?뚮굹濡?遺꾩꽍???쒖옉?⑸땲??..")

                        # ?앹꽦 紐⑤뱶???곕씪 ?ㅻⅨ ?⑥닔 ?몄텧
                        gen_mode = inputs.get('generation_mode', 'single')
                        if gen_mode == 'chained' and core_chained.is_chained_supported(inputs['template_option']):
                            part_count = len(core_chained.CHAINED_PARTS.get(inputs['template_option'], []))
                            st.write(f"?랃툘 3. {part_count}?④퀎 遺꾪븷 ?앹꽦 紐⑤뱶濡?臾몄꽌瑜??묒꽦?⑸땲??..")
                            stream = core_logic.generate_report_stream_chained(
                                settings['api_key'], settings['model_name'], inputs, settings['thinking_level'], file_context
                            )
                        else:
                            st.write("?랃툘 3. 臾몄꽌瑜??묒꽦 以묒엯?덈떎 (?ㅽ듃由щ컢)...")
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
                        
                        status.update(label="???묒꽦???꾨즺?섏뿀?듬땲??", state="complete", expanded=False)
                        st.session_state[k_text] = full_response
                except Exception as e:
                    st.error(f"?앹꽦 以??ㅻ쪟 諛쒖깮: {e}")

        # 2. 寃곌낵 ?쒖떆
        elif st.session_state[k_text]:
            with result_container:
                if st.session_state.get(k_copy):
                    st.info("?곗륫 ?곷떒??蹂듭궗 踰꾪듉???꾨Ⅴ?몄슂. (?レ쑝?ㅻ㈃ '蹂듭궗' 踰꾪듉 ?ㅼ떆 ?대┃)")
                    st.code(st.session_state[k_text], language="markdown")
                
                if st.session_state[k_editing]:
                    new_text = st.text_area("?댁슜 ?몄쭛", value=st.session_state[k_text], height=550, label_visibility="collapsed", key=f"{key_prefix}_edit_area")
                    st.session_state[k_text] = new_text
                else:
                    st.markdown(st.session_state[k_text])

        # 3. ?섎떒 ?≪뀡
        if st.session_state[k_text]:
            st.markdown("---")
            
            # PPT 蹂??踰꾪듉
            if st.session_state[k_mode] != 'presentation' and st.session_state[k_mode] != 'rfi':
                if st.button("?뱤 ???댁슜?쇰줈 諛쒗몴?먮즺(PPT) ?앹꽦?섍린", use_container_width=True, key=f"{key_prefix}_btn_ppt_convert"):
                    if not settings['api_key']:
                        st.error("API Key ?꾩슂")
                    else:
                        try:
                            ppt_inputs = inputs.copy()
                            ppt_inputs['template_option'] = 'presentation'
                            ppt_inputs['structure_text'] = core_logic.get_default_structure('presentation')
                            st.session_state[k_mode] = 'presentation'
                            st.session_state[k_editing] = False

                            with status_placeholder.status("?봽 PPT ?ㅽ??쇰줈 蹂??以?..", expanded=True) as status:
                                # PPT 蹂???쒖뿉??湲곗〈 ?곗씠?곕? ?ы솢??(?뚯씪 ?ㅼ떆 ?쎌쓣 ?꾩슂 X)
                                # ?섏?留?file_context媛 ?꾩슂?섎?濡??ㅼ떆 ?뚯떛 (?대? 濡쒖뺄 罹먯떆?섏뼱 鍮좊쫫)
                                docai_config = settings.get('docai_config')
                                file_context, _ = core_logic.parse_all_files(
                                    inputs['uploaded_files'],
                                    read_content=True,
                                    api_key=settings['api_key'],
                                    docai_config=docai_config,
                                    template_option=ppt_inputs['template_option'],
                                )
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
                                status.update(label="??PPT 蹂???꾨즺!", state="complete", expanded=False)
                                st.session_state[k_text] = full_response
                                st.rerun()
                        except Exception as e:
                            st.error(f"PPT 蹂???ㅻ쪟: {e}")

            # Refine
            refine_query = st.chat_input("寃곌낵臾??섏젙/蹂댁셿 ?붿껌", key=f"{key_prefix}_chat_refine")
            if refine_query:
                if not settings['api_key']: st.error("API Key ?꾩슂")
                else:
                    with st.spinner("?섏젙 ?댁슜 ?앹꽦 以?.."):
                        try:
                            refined_text = core_logic.refine_report(
                                settings['api_key'], settings['model_name'], st.session_state[k_text], refine_query
                            )
                            st.session_state[k_text] += f"\n\n--- [異붽? ?붿껌 諛섏쁺] ---\n{refined_text}"
                            st.rerun()
                        except Exception as e:
                            st.error(f"?섏젙 ?ㅻ쪟: {e}")

            # Download
            st.write("")
            col_d1, col_d2, col_d3 = st.columns(3)
            current_mode = st.session_state.get(k_mode, inputs['template_option'])
            fname = utils.generate_filename(inputs['uploaded_files'], current_mode)

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
                btn_type = "primary" if current_mode == 'presentation' else "secondary"
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
                # OCR ?띿뒪???ㅼ슫濡쒕뱶 (Document AI ?ъ슜 ??
                ocr_text = st.session_state.get(k_ocr, "")
                if ocr_text:
                    st.download_button(
                        "🧾 OCR 텍스트 다운로드",
                        ocr_text,
                        fname.replace(".docx", "_ocr.txt"),
                        "text/plain",
                        use_container_width=True,
                        key=f"{key_prefix}_dl_ocr",
                    )

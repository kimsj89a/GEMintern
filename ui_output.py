import streamlit as st
import streamlit.components.v1 as components
import utils
import utils_ppt
import core_logic

# PDF 처리용 라이브러리 임포트 시도
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pypdf
except ImportError:
    pypdf = None

def _parse_pdf_chunked(file_obj, chunk_size=15):
    """
    PDF 파일을 청크 단위로 나누어 텍스트를 추출합니다 (Searchable PDF 지원).
    15페이지 이상일 경우 chunking하여 작업 후 병합합니다.
    """
    text_content = []
    try:
        # 1순위: pdfplumber (레이아웃 보존 우수)
        if pdfplumber:
            with pdfplumber.open(file_obj) as pdf:
                total_pages = len(pdf.pages)
                for i in range(0, total_pages, chunk_size):
                    chunk = pdf.pages[i:i+chunk_size]
                    chunk_text = "\n".join([p.extract_text() or "" for p in chunk])
                    if chunk_text.strip():
                        text_content.append(chunk_text)
        # 2순위: pypdf (가벼움)
        elif pypdf:
            reader = pypdf.PdfReader(file_obj)
            total_pages = len(reader.pages)
            for i in range(0, total_pages, chunk_size):
                end = min(i + chunk_size, total_pages)
                chunk_text = "\n".join([reader.pages[p].extract_text() or "" for p in range(i, end)])
                if chunk_text.strip():
                    text_content.append(chunk_text)
    except Exception as e:
        print(f"PDF Parsing Error: {e}")
        return None
    
    return "\n\n".join(text_content) if text_content else None

def render_output_panel(container, settings, inputs, key_prefix="output"):
    # State keys with prefix to isolate tabs
    k_editing = f"{key_prefix}_is_editing"
    k_copy = f"{key_prefix}_show_copy_code"
    k_text = f"{key_prefix}_generated_text"
    k_mode = f"{key_prefix}_active_mode"

    with container:
        c_head1, c_head2 = st.columns([1, 1])
        with c_head1:
             st.markdown("### 📄 결과물 (Result)")

        with c_head2:
            sub_c1, sub_c2, sub_c3 = st.columns([2, 1, 1])
            with sub_c2:
                if k_editing not in st.session_state:
                    st.session_state[k_editing] = False
                edit_label = "✏️ 완료" if st.session_state[k_editing] else "✏️ 편집"
                if st.button(edit_label, key=f"{key_prefix}_btn_toggle_edit", use_container_width=True):
                    st.session_state[k_editing] = not st.session_state[k_editing]
                    st.rerun()

            with sub_c3:
                if st.button("📋 복사", key=f"{key_prefix}_btn_copy_view", use_container_width=True):
                    st.toast("아래 코드를 클릭하여 복사하세요", icon="📋")
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

                    with status_placeholder.status("🚀 분석 작업을 시작합니다...", expanded=True) as status:
                        if is_rfi_mode:
                            st.write("📂 1. (Fast Mode) 파일 내용을 건너뛰고 파일명만 추출합니다...")
                            file_context, _ = core_logic.parse_all_files(inputs['uploaded_files'], read_content=False)
                        elif utils.MARKITDOWN_AVAILABLE:
                            st.write("📂 1. MarkItDown을 사용하여 파일을 변환 중입니다...")
                            file_context, _ = core_logic.parse_all_files(inputs['uploaded_files'], read_content=True, api_key=settings['api_key'])
                        else:
                            # [수정] Searchable PDF 우선 처리 및 Chunking 로직 적용
                            st.write("📂 1. 파일을 분석 중입니다 (Searchable PDF & OCR)...")
                            
                            pdf_files = [f for f in inputs['uploaded_files'] if f.name.lower().endswith('.pdf')]
                            other_files = [f for f in inputs['uploaded_files'] if not f.name.lower().endswith('.pdf')]
                            
                            extracted_parts = []
                            
                            # 1. PDF 파일: Searchable Text 우선 추출 (Chunking 적용)
                            if pdf_files:
                                for pdf in pdf_files:
                                    pdf_text = _parse_pdf_chunked(pdf, chunk_size=15)
                                    if pdf_text:
                                        extracted_parts.append(f"=== File: {pdf.name} ===\n{pdf_text}")
                                    else:
                                        # 텍스트 추출 실패 시 OCR 처리를 위해 other_files로 넘김
                                        other_files.append(pdf)
                            
                            # 2. 나머지 파일 및 스캔된 PDF: 기존 OCR/Parsing 로직 사용
                            if other_files:
                                ocr_context, _ = core_logic.parse_all_files(other_files, read_content=True, api_key=settings['api_key'])
                                extracted_parts.append(ocr_context)
                            
                            file_context = "\n\n".join(extracted_parts)
                        
                        st.write(f"🧠 2. AI가 [{st.session_state[k_mode]}] 페르소나로 분석을 시작합니다...")

                        # 생성 모드에 따라 다른 함수 호출
                        gen_mode = inputs.get('generation_mode', 'single')
                        if gen_mode == 'chained' and inputs['template_option'] == 'investment':
                            st.write("✍️ 3. 3단계 분할 생성 모드로 문서를 작성합니다...")
                            stream = core_logic.generate_report_stream_chained(
                                settings['api_key'], settings['model_name'], inputs, settings['thinking_level'], file_context
                            )
                        else:
                            st.write("✍️ 3. 문서를 작성 중입니다 (스트리밍)...")
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
                        
                        status.update(label="✅ 작성이 완료되었습니다!", state="complete", expanded=False)
                        st.session_state[k_text] = full_response
                except Exception as e:
                    st.error(f"생성 중 오류 발생: {e}")

        # 2. 결과 표시
        elif st.session_state[k_text]:
            with result_container:
                if st.session_state.get(k_copy):
                    st.info("우측 상단의 복사 버튼을 누르세요. (닫으려면 '복사' 버튼 다시 클릭)")
                    st.code(st.session_state[k_text], language="markdown")
                
                if st.session_state[k_editing]:
                    new_text = st.text_area("내용 편집", value=st.session_state[k_text], height=550, label_visibility="collapsed", key=f"{key_prefix}_edit_area")
                    st.session_state[k_text] = new_text
                else:
                    st.markdown(st.session_state[k_text])

        # 3. 하단 액션
        if st.session_state[k_text]:
            st.markdown("---")
            
            # PPT 변환 버튼
            if st.session_state[k_mode] != 'presentation' and st.session_state[k_mode] != 'rfi':
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

                            with status_placeholder.status("🔄 PPT 스타일로 변환 중...", expanded=True) as status:
                                # PPT 변환 시에는 기존 데이터를 재활용 (파일 다시 읽을 필요 X)
                                # 하지만 file_context가 필요하므로 다시 파싱 (이미 로컬 캐시되어 빠름)
                                file_context, _ = core_logic.parse_all_files(inputs['uploaded_files'], read_content=True, api_key=settings['api_key'])
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
            refine_query = st.chat_input("결과물 수정/보완 요청", key=f"{key_prefix}_chat_refine")
            if refine_query:
                if not settings['api_key']: st.error("API Key 필요")
                else:
                    with st.spinner("수정 내용 생성 중..."):
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
            col_d1, col_d2 = st.columns(2)
            current_mode = st.session_state.get(k_mode, inputs['template_option'])
            fname = utils.generate_filename(inputs['uploaded_files'], current_mode)
            
            with col_d1:
                if current_mode == 'rfi':
                    st.download_button("📉 RFI 엑셀 저장", utils.create_excel(st.session_state[k_text]), fname.replace('.docx','.xlsx'), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"{key_prefix}_dl_rfi")
                else:
                    st.download_button(f"📄 Word 저장 ({fname})", utils.create_docx(st.session_state[k_text]), fname, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True, key=f"{key_prefix}_dl_word")
            
            with col_d2:
                btn_type = "primary" if current_mode == 'presentation' else "secondary"
                st.download_button(f"📊 PPT 저장 ({fname.replace('.docx','.pptx')})", utils_ppt.create_ppt(st.session_state[k_text]), fname.replace('.docx','.pptx'), "application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True, type=btn_type, key=f"{key_prefix}_dl_ppt")
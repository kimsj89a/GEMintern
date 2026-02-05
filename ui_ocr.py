import streamlit as st
import utils
import utils_docai
import io
import os

def render_ocr_panel(settings):
    """문서 OCR 및 변환 전용 패널 (다중 파일 지원)"""
    st.markdown("### 👁️ 문서 OCR 및 변환 (OCR & Converter)")
    
    st.markdown("""
        <div style='background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #0068c9;'>
        <h4 style='margin-top: 0; color: #0068c9;'>📋 기능 안내</h4>
        <b>1. Gemini Vision OCR:</b> 이미지/PDF의 텍스트를 마크다운으로 추출 (무료/빠름/API Key 필요)<br/>
        <b>2. Google Document AI:</b> 고품질 OCR 및 <b>Searchable PDF(검색 가능한 PDF)</b> 생성 (GCP 설정 필요)
        </div>
    """, unsafe_allow_html=True)

    # 1. 파일 업로드 (다중 파일 허용)
    uploaded_files = st.file_uploader(
        "파일 업로드 (PDF, 이미지) - 여러 개 선택 가능", 
        type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp'], 
        accept_multiple_files=True,
        key="ocr_files"
    )
    
    if not uploaded_files:
        st.info("파일을 업로드하면 설정 옵션이 나타납니다.")
        return

    # 2. 설정
    st.markdown("#### ⚙️ 변환 설정")
    
    col1, col2 = st.columns(2)
    with col1:
        ocr_engine = st.radio(
            "OCR 엔진 선택",
            ["Gemini Vision (기본)", "Google Document AI (고급)"],
            horizontal=True,
            key="ocr_engine_choice"
        )

    docai_config = settings.get('docai_config')
    
    if ocr_engine == "Google Document AI (고급)":
        if not docai_config:
            st.warning("⚠️ 상단 '설정(SETTINGS)' 메뉴에서 Document AI 설정을 먼저 완료해주세요.")
        else:
            st.success(f"✅ Document AI 설정됨 (Project: {docai_config.get('project_id')})")
            
    # 3. 실행
    st.markdown("---")
    if st.button(f"🚀 {len(uploaded_files)}개 파일 변환 시작", type="primary", use_container_width=True, key="btn_start_ocr"):
        # 결과 저장소 초기화
        st.session_state['ocr_results'] = {} 
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"처리 중 ({i+1}/{len(uploaded_files)}): {uploaded_file.name}")
            
            try:
                if ocr_engine == "Gemini Vision (기본)":
                    if not settings.get('api_key'):
                        st.error("⚠️ Google API Key가 필요합니다.")
                        break
                    
                    # utils.parse_uploaded_file 사용
                    text_result = utils.parse_uploaded_file(
                        uploaded_file, 
                        api_key=settings['api_key']
                    )
                    st.session_state['ocr_results'][uploaded_file.name] = {
                        'type': 'gemini',
                        'text': text_result
                    }

                else: # Document AI
                    if not docai_config:
                        st.error("Document AI 설정이 필요합니다.")
                        break
                    
                    # 파일 읽기
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    mime_type = utils_docai.get_mime_type(uploaded_file.name)
                    
                    result = utils_docai.process_document(
                        file_bytes=file_bytes,
                        mime_type=mime_type,
                        project_id=docai_config['project_id'],
                        location=docai_config.get('location', 'us'),
                        processor_id=docai_config['processor_id'],
                        credentials_json=docai_config.get('credentials_json')
                    )
                    
                    st.session_state['ocr_results'][uploaded_file.name] = {
                        'type': 'docai',
                        'text': result.get('text', ''),
                        'docai_result': result,
                        'file_bytes': file_bytes,
                        'mime_type': mime_type
                    }
            except Exception as e:
                st.error(f"{uploaded_file.name} 처리 중 오류: {e}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
            
        status_text.text("완료!")
        st.rerun()

    # 4. 결과 표시
    if st.session_state.get('ocr_results'):
        results = st.session_state['ocr_results']
        st.markdown(f"#### 📄 변환 결과 ({len(results)}개)")
        
        # 탭으로 파일 구분
        file_names = list(results.keys())
        if not file_names:
            return

        tabs = st.tabs(file_names)
        
        for idx, fname in enumerate(file_names):
            res = results[fname]
            with tabs[idx]:
                st.text_area("Extracted Text", value=res['text'], height=400, key=f"ocr_text_{idx}")
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.download_button("📥 텍스트 다운로드", res['text'], f"{fname}.txt", use_container_width=True, key=f"btn_dl_txt_{idx}")
                
                # Document AI인 경우 Searchable PDF 옵션
                if res['type'] == 'docai' and 'docai_result' in res:
                    with col_d2:
                        pdf_key = f'pdf_bytes_{fname}'
                        if st.button("Searchable PDF 생성", key=f"btn_pdf_{idx}"):
                            with st.spinner("PDF 생성 중..."):
                                try:
                                    pdf_bytes = utils_docai.create_searchable_pdf(res['file_bytes'], res['docai_result'], res['mime_type'])
                                    st.session_state[pdf_key] = pdf_bytes
                                except Exception as e:
                                    st.error(f"PDF 생성 오류: {e}")
                        
                        if st.session_state.get(pdf_key):
                            st.download_button("📥 PDF 다운로드", st.session_state[pdf_key], f"{os.path.splitext(fname)[0]}_searchable.pdf", "application/pdf", use_container_width=True, type="primary", key=f"btn_dl_pdf_{idx}")
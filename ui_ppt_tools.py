import streamlit as st
import io
import os
import json
import core_logic
import utils_ppt
import utils
import core_ppt_updater

def render_ppt_tools_panel(settings):
    """
    PPT Workspace: Consolidates Deck Generation and Slide Tools.
    """
    st.markdown("### 📢 발표자료 (PPT Workspace)")
    
    t1, t2 = st.tabs(["🏗️ 새 슬라이드 생성", "🛠️ 슬라이드 도구"])
    
    # ==========================================
    # Tab 1: New Deck Generation (Direct Mode)
    # ==========================================
    with t1:
        st.markdown("#### 📄 문서 기반 PPT 초안 생성")
        st.info("문서를 업로드하면 AI가 구조를 분석하여 **2단 컬럼 레이아웃**의 PPT 초안을 바로 생성합니다. (보고서 생성 과정 생략)")
        
        col_input, col_opt = st.columns([2, 1])
        
        with col_input:
            uploaded_file = st.file_uploader("참조 문서 업로드 (PDF, DOCX 등)", type=['pdf', 'docx', 'txt', 'md'], key="ppt_gen_file")
            context_text = st.text_area("발표 목적 및 강조 사항", height=100, placeholder="예: 시리즈 A 투자 유치를 위한 IR 자료, 10분 발표 분량, 성장성 강조...", key="ppt_gen_context")
            
        with col_opt:
            st.markdown("###### 설정")
            model_name = settings.get("model_name", "gemini-3-flash-preview")
            st.caption(f"사용 모델: {model_name}")
            
        if st.button("🚀 PPT 생성 시작", type="primary", key="ppt_gen_btn", use_container_width=True):
            if not uploaded_file:
                st.warning("문서를 업로드해주세요.")
                return
            
            api_key = settings.get("api_key")
            if not api_key:
                st.error("API Key가 설정되지 않았습니다.")
                return
                
            with st.spinner("1. 문서 분석 및 슬라이드 구조 설계 중..."):
                # 1. Parse File
                file_text = utils.parse_uploaded_file(uploaded_file, api_key=api_key)
                
                # 2. Generate JSON Structure
                json_str = core_logic.generate_slide_json(
                    api_key=api_key,
                    model_name=model_name,
                    file_context=file_text,
                    context_text=context_text
                )
                
                # Debug: Show JSON if needed
                # st.json(json_str)
                
            with st.spinner("2. PPT 파일 생성 중..."):
                # 3. Create PPTX
                ppt_bytes = utils_ppt.create_deck_from_json(json_str)
                
                if ppt_bytes:
                    st.success("✅ PPT 생성 완료!")
                    st.download_button(
                        label="📥 PPTX 다운로드",
                        data=ppt_bytes,
                        file_name=f"Presentation_{uploaded_file.name}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )
                else:
                    st.error("PPT 생성 실패: JSON 구조 오류")
                    st.text_area("Debug Info", value=json_str)

    # ==========================================
    # Tab 2: Slide Tools (Investment History, etc.)
    # ==========================================
    with t2:
        st.markdown("#### 📈 투자유치 히스토리 업데이트 (Slide 9)")
        st.info("기존 PPT 파일을 업로드하면, 타 슬라이드의 투자 정보를 수집하여 '투자유치 히스토리' 장표를 업데이트합니다.")
        
        uploaded_pptx = st.file_uploader("PPTX 파일 업로드", type=['pptx'], key="tool_ppt_update_file")
        
        if uploaded_pptx:
            if st.button("🚀 업데이트 실행", key="tool_ppt_update_btn", type="primary", use_container_width=True):
                with st.spinner("슬라이드 분석 및 업데이트 중..."):
                    try:
                        temp_input_path = f"temp_tool_{uploaded_pptx.name}"
                        with open(temp_input_path, "wb") as f:
                            f.write(uploaded_pptx.getbuffer())
                            
                        updater = core_ppt_updater.InvestmentHistoryUpdater(temp_input_path)
                        extracted_data = updater.extract_data()
                        updater.update_slide(8) # Slide 9
                        
                        output_bio = io.BytesIO()
                        updater.prs.save(output_bio)
                        output_bio.seek(0)
                        
                        if os.path.exists(temp_input_path):
                            os.remove(temp_input_path)
                            
                        st.success("✅ 업데이트 완료!")
                        
                        col_down, col_preview = st.columns([1, 1])
                        with col_down:
                            st.download_button(
                                label="📥 업데이트된 파일 다운로드",
                                data=output_bio,
                                file_name=f"updated_{uploaded_pptx.name}",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                use_container_width=True
                            )
                        with col_preview:
                            with st.expander("데이터 미리보기"):
                                st.dataframe(extracted_data)
                                
                    except Exception as e:
                        st.error(f"오류 발생: {e}")
                        if os.path.exists(temp_input_path):
                            try: os.remove(temp_input_path)
                            except: pass

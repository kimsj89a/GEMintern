import streamlit as st
import io
import os
import core_ppt_updater

def render_ppt_updater_panel(settings):
    """
    Investment History PPT Updater Panel
    """
    st.markdown("### 📈 투자유치 히스토리 업데이트 (Slide 9)")
    
    st.info("기존 PPT 파일을 업로드하면, 타 슬라이드의 투자 정보를 수집하여 '투자유치 히스토리(Slide 9)'를 자동으로 업데이트합니다.")

    # 1. File Upload
    uploaded_file = st.file_uploader(
        "PPTX 파일 업로드",
        type=['pptx'],
        key="ppt_update_file"
    )
    
    if uploaded_file:
        st.markdown("---")
        if st.button("🚀 업데이트 실행", type="primary", use_container_width=True):
            with st.spinner("슬라이드 분석 및 업데이트 중..."):
                try:
                    # Save uploaded file to a temporary location
                    temp_input_path = f"temp_input_{uploaded_file.name}"
                    with open(temp_input_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                        
                    # Process
                    updater = core_ppt_updater.InvestmentHistoryUpdater(temp_input_path)
                    
                    # Extract Data (Mock/Heuristic)
                    extracted_data = updater.extract_data()
                    
                    # Update Slide
                    updater.update_slide(8) # Slide 9 (0-indexed 8)
                    
                    # Save to BytesIO for download
                    output_bio = io.BytesIO()
                    updater.prs.save(output_bio)
                    output_bio.seek(0)
                    
                    # Cleanup temp file
                    if os.path.exists(temp_input_path):
                        os.remove(temp_input_path)
                        
                    st.success("✅ 업데이트 완료!")
                    
                    st.download_button(
                        label="📥 업데이트된 PPTX 다운로드",
                        data=output_bio,
                        file_name=f"updated_{uploaded_file.name}",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )
                    
                    # Show extracted data preview
                    with st.expander("📊 추출된 데이터 미리보기"):
                        st.dataframe(extracted_data)
                        
                except Exception as e:
                    st.error(f"오류 발생: {e}")
                    # Cleanup if failed
                    if os.path.exists(temp_input_path):
                        try:
                            os.remove(temp_input_path)
                        except:
                            pass

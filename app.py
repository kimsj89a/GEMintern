import streamlit as st
import ui_input
import ui_output
import ui_audio
import ui_crawler
import ui_ocr
import ui_markdown
import ui_doctemplate

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="GEM Intern v6.0", page_icon="💎")

# --- CSS 스타일 적용 ---
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .title-container { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .badge { background-color: #f0f2f6; color: #31333F; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500; border: 1px solid #d6d6d8; }
    .badge-blue { background-color: #e6f0ff; color: #0068c9; border: 1px solid #b3d1ff; }
    .info-box { background-color: #fff8c5; padding: 10px; border-radius: 5px; border: 1px solid #e3d5a5; font-size: 0.85rem; color: #5c4b12; margin-bottom: 15px; }
    p, li, div { word-break: keep-all; overflow-wrap: break-word; }
</style>
""", unsafe_allow_html=True)

# --- 상태 초기화 ---
# if "generated_text" not in st.session_state: st.session_state.generated_text = "" # Removed global init

if "app_started" not in st.session_state:
    st.session_state.app_started = False

def main():
    st.markdown("""
        <div class="title-container">
            <h1>💎 GEM Intern</h1>
            <span class="badge">v6.0</span>
            <span class="badge badge-blue">Cloud-Safe Indexer</span>
        </div>
        <p style='color: gray; margin-top: -10px; margin-bottom: 20px;'>AI-Powered Investment Analysis Assistant</p>
    """, unsafe_allow_html=True)

    if not st.session_state.app_started:
        # [화면 1] 설정 페이지 (메인)
        st.markdown("### ⚙️ 환경 설정 (Settings)")
        st.info("업무를 시작하기 전에 필요한 설정을 완료해주세요.")
        
        # 설정 패널 렌더링 (메인 영역)
        settings = ui_input.render_settings()
        
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ 설정 적용 및 업무 시작", type="primary", use_container_width=True):
                st.session_state.app_started = True
                st.rerun()
                
    else:
        # [화면 2] 업무 프로세스 (사이드바 레이아웃)
        with st.sidebar:
            st.header("업무 프로세스")
            
            # 네비게이션
            selected_page = st.radio(
                "단계 선택",
                [
                    "📋 초기검토",
                    "📊 예비실사",
                    "🔍 정밀실사",
                    "🖥️ PPT 생성",
                    "🎤 오디오 전사",
                    "🌐 웹 크롤러",
                    "👁️ 문서 OCR",
                    "📝 MD to Word",
                    "📋 문서양식"
                ],
                index=0
            )
            
            st.markdown("---")
            
            # 설정 수정 (사이드바 내 Expander로 이동)
            with st.expander("⚙️ 설정 수정"):
                settings = ui_input.render_settings()
                
            st.markdown("---")
            if st.button("🏠 처음으로 (설정 화면)"):
                st.session_state.app_started = False
                st.rerun()

        # 메인 콘텐츠 영역
        if selected_page == "📋 초기검토":
            st.markdown("### 📋 초기검토 (Quick Memo)")
            st.caption("약식 투자검토보고서를 빠르게 작성합니다.")
            st.markdown("---")
            inputs = ui_input.render_initial_review_panel(st.container(), settings)
            st.markdown("<br>", unsafe_allow_html=True)
            ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="init")

        elif selected_page == "📊 예비실사":
            st.markdown("### 📊 예비실사 (Preliminary DD)")
            st.caption("투자심사보고서, IM, 사후관리보고서 등을 작성합니다.")
            st.markdown("---")
            inputs = ui_input.render_preliminary_dd_panel(st.container(), settings)
            st.markdown("<br>", unsafe_allow_html=True)
            ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="prelim")

        elif selected_page == "🔍 정밀실사":
            st.markdown("### 🔍 정밀실사 (Detailed DD)")
            st.caption("RFI (자료요청목록) 작성 - FDD/LDD 유형별 지원")
            st.markdown("---")
            inputs = ui_input.render_detailed_dd_panel(st.container(), settings)
            st.markdown("<br>", unsafe_allow_html=True)
            ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="dd")

        elif selected_page == "🖥️ PPT 생성":
            st.markdown("### 🖥️ PPT 생성 (Paper2Slides)")
            st.caption("문서나 논문을 업로드하여 구조화된 발표자료(PPT)로 변환합니다.")
            st.markdown("---")
            inputs = ui_input.render_ppt_panel(st.container(), settings)
            st.markdown("<br>", unsafe_allow_html=True)
            ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="ppt")

        elif selected_page == "🎤 오디오 전사":
            ui_audio.render_audio_transcription_panel(settings)

        elif selected_page == "🌐 웹 크롤러":
            ui_crawler.render_crawler_panel(settings)

        elif selected_page == "👁️ 문서 OCR":
            ui_ocr.render_ocr_panel(settings)

        elif selected_page == "📝 MD to Word":
            ui_markdown.render_markdown_converter_panel(settings)

        elif selected_page == "📋 문서양식":
            ui_doctemplate.render_doctemplate_panel(settings)

if __name__ == "__main__":
    main()
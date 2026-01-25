import streamlit as st
import ui_input
import ui_output
import ui_audio

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="GEM Intern v5.12", page_icon="💎")

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

def main():
    st.markdown("""
        <div class="title-container">
            <h1>💎 GEM Intern</h1>
            <span class="badge">v5.12</span>
            <span class="badge badge-blue">Cloud-Safe Indexer</span>
        </div>
        <p style='color: gray; margin-top: -10px; margin-bottom: 20px;'>AI-Powered Investment Analysis Assistant</p>
    """, unsafe_allow_html=True)

    # 공통 설정 (탭 위에 고정)
    settings = ui_input.render_settings()

    # 탭 기반 UI - 4개 탭으로 분리
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 투자분석 보고서",
        "📋 RFI 작성",
        "📈 IM/PPT 생성",
        "🎤 오디오 전사"
    ])

    with tab1:
        st.markdown("### 📄 투자분석 보고서 작성")
        st.markdown("---")
        inputs = ui_input.render_investment_report_panel(st.container(), settings)
        st.markdown("<br>", unsafe_allow_html=True)
        ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="report")

    with tab2:
        st.markdown("### 📋 RFI (실사 자료 요청) 작성")
        st.markdown("---")
        inputs = ui_input.render_rfi_panel(st.container(), settings)
        st.markdown("<br>", unsafe_allow_html=True)
        ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="rfi")

    with tab3:
        st.markdown("### 📊 IM/PPT 생성")
        st.markdown("---")
        inputs = ui_input.render_im_ppt_panel(st.container(), settings)
        st.markdown("<br>", unsafe_allow_html=True)
        ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="im")

    with tab4:
        ui_audio.render_audio_transcription_panel()

if __name__ == "__main__":
    main()
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
if "generated_text" not in st.session_state: st.session_state.generated_text = ""

def main():
    st.markdown("""
        <div class="title-container">
            <h1>💎 GEM Intern</h1>
            <span class="badge">v5.12</span>
            <span class="badge badge-blue">Cloud-Safe Indexer</span>
        </div>
        <p style='color: gray; margin-top: -10px; margin-bottom: 20px;'>AI-Powered Investment Analysis Assistant</p>
    """, unsafe_allow_html=True)

    # 탭 기반 UI
    tab1, tab2 = st.tabs(["📊 투자분석 보고서", "🎤 오디오 전사"])

    with tab1:
        settings = ui_input.render_settings()
        st.markdown("---")
        inputs = ui_input.render_input_panel(st.container(), settings)
        st.markdown("<br>", unsafe_allow_html=True)
        ui_output.render_output_panel(st.container(), settings, inputs)

    with tab2:
        ui_audio.render_audio_transcription_panel()

if __name__ == "__main__":
    main()
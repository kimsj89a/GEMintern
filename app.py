import streamlit as st
import ui_input
import ui_output

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="GEM Intern v5.0 (Py)", page_icon="💎")

# --- CSS 스타일 적용 ---
st.markdown("""
<style>
    .reportview-container .main .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    p, li, div {
        word-break: keep-all;
        overflow-wrap: break-word;
    }
    @media (max-width: 640px) {
        .stTextArea textarea { font-size: 16px !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 상태 초기화 ---
if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

def main():
    # 1. 사이드바 설정 로드
    settings = ui_input.render_sidebar()
    
    # 2. 메인 레이아웃 (2단)
    col1, col2 = st.columns([1, 1])
    
    # 3. 왼쪽 패널 (입력)
    inputs = ui_input.render_input_panel(col1, settings)
    
    # 4. 오른쪽 패널 (결과)
    ui_output.render_output_panel(col2, settings, inputs)

if __name__ == "__main__":
    main()
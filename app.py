import streamlit as st
import ui_input
import ui_output

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="GEM Intern v4.8", page_icon="💎")

# --- CSS 스타일 적용 ---
st.markdown("""
<style>
    /* 전체 여백 조정 */
    .reportview-container .main .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    /* 타이틀 스타일 */
    .title-container {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }
    .badge {
        background-color: #f0f2f6;
        color: #31333F;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 500;
        border: 1px solid #d6d6d8;
    }
    .badge-blue {
        background-color: #e6f0ff;
        color: #0068c9;
        border: 1px solid #b3d1ff;
    }
    /* 텍스트 줄바꿈 */
    p, li, div {
        word-break: keep-all;
        overflow-wrap: break-word;
    }
</style>
""", unsafe_allow_html=True)

# --- 상태 초기화 ---
if "generated_text" not in st.session_state:
    st.session_state.generated_text = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

def main():
    # 1. 헤더
    st.markdown("""
        <div class="title-container">
            <h1>💎 GEM Intern</h1>
            <span class="badge">v4.8</span>
            <span class="badge badge-blue">Vertical Layout</span>
        </div>
        <p style='color: gray; margin-top: -10px; margin-bottom: 20px;'>AI-Powered Investment Analysis Assistant</p>
    """, unsafe_allow_html=True)

    # 2. 상단 설정 영역
    settings = ui_input.render_settings()
    
    st.markdown("---")

    # 3. 메인 레이아웃 (상하 배치)
    # 기존 col1, col2 = st.columns(...) 제거 -> 순차 렌더링
    
    # [입력 패널]
    inputs = ui_input.render_input_panel(st.container(), settings)
    
    st.markdown("<br>", unsafe_allow_html=True) # 간격 추가

    # [결과 패널] - 입력값(버튼 클릭 등) 전달
    ui_output.render_output_panel(st.container(), settings, inputs)

if __name__ == "__main__":
    main()
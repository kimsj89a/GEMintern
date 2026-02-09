import traceback
import streamlit as st
import ui_input
import ui_workflow
import ui_project
import ui_audio
import ui_crawler
import ui_ocr
import ui_markdown
import ui_doctemplate
import ui_text_organizer

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="GEM Intern v7.0", page_icon="💎")

# --- CSS 스타일 적용 ---
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .title-container { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
    .badge { background-color: #f0f2f6; color: #31333F; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500; border: 1px solid #d6d6d8; }
    .badge-blue { background-color: #e6f0ff; color: #0068c9; border: 1px solid #b3d1ff; }
    .info-box { background-color: #fff8c5; padding: 10px; border-radius: 5px; border: 1px solid #e3d5a5; font-size: 0.85rem; color: #5c4b12; margin-bottom: 15px; }
    p, li, div { word-break: keep-all; overflow-wrap: break-word; }

    /* 사이드바 네비게이션 버튼 스타일 (Gemini-like) */
    section[data-testid="stSidebar"] .stButton button {
        text-align: left;
        padding-left: 20px;
        border: none;
        background-color: transparent;
        font-size: 1.05rem;
        justify-content: flex-start;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background-color: #f0f2f6;
        color: #0068c9;
    }
    /* 활성화된 버튼 스타일 */
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: #e6f0ff;
        color: #0068c9;
        font-weight: 600;
        border-left: 4px solid #0068c9;
        border-radius: 0 4px 4px 0;
    }
    /* 사이드바 섹션 헤더 */
    .nav-section-header {
        color: #6c757d;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        padding: 8px 20px 4px 20px;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 상태 초기화 ---
if "app_started" not in st.session_state:
    st.session_state.app_started = False

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "📂 프로젝트"

if "current_project" not in st.session_state:
    st.session_state.current_project = None

# --- 네비게이션 구조 ---
NAV_SECTIONS = {
    "프로젝트": ["📂 프로젝트"],
    "투자 프로세스": [
        "📥 사전 정보 수집",
        "📊 예비실사",
        "🔍 정밀실사",
    ],
    "독립 도구": [
        "📑 IM 작성",
        "🖥️ PPT 생성",
    ],
    "유틸리티": [
        "🎤 오디오 전사", "🌐 웹 크롤러", "👁️ 문서 OCR",
        "📝 MD to Word", "📋 문서양식", "✏️ 문장 정리기",
    ],
}

PHASE_PAGES = ["📥 사전 정보 수집", "📊 예비실사", "🔍 정밀실사"]
UTILITY_ANALYSIS_PAGES = ["📑 IM 작성", "🖥️ PPT 생성"]


def main():
    if not st.session_state.app_started:
        st.markdown("""
            <div class="title-container">
                <h1>💎 GEM Intern</h1>
                <span class="badge">v7.0</span>
                <span class="badge badge-blue">3-Phase Workflow</span>
            </div>
            <p style='color: gray; margin-top: -10px; margin-bottom: 10px;'>AI-Powered Investment Analysis Assistant</p>
        """, unsafe_allow_html=True)

        # [화면 1] 설정 페이지 (메인)
        st.markdown("### ⚙️ 환경 설정 (Settings)")
        st.info("업무를 시작하기 전에 필요한 설정을 완료해주세요.")

        settings = ui_input.render_settings()
        st.session_state['latest_settings'] = settings

        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ 설정 적용 및 업무 시작", type="primary", use_container_width=True):
                st.session_state.app_started = True
                st.session_state.selected_page = "📂 프로젝트"
                st.rerun()

    else:
        # 설정값 불러오기
        settings = st.session_state.get('latest_settings', {
            "api_key": st.session_state.get("api_key", ""),
            "model_name": st.session_state.get("model_name", "gemini-2.0-flash-thinking-exp-1219"),
            "thinking_level": st.session_state.get("thinking_level", "MINIMAL"),
            "use_diagram": st.session_state.get("use_diagram", False),
            "docai_config": st.session_state.get("docai_config", {}),
        })

        # [화면 2] 업무 프로세스 (사이드바 레이아웃)
        with st.sidebar:
            st.markdown("### 💎 GEM Intern v7.0")
            st.markdown("<br>", unsafe_allow_html=True)

            # 현재 프로젝트 표시
            current_proj = st.session_state.get("current_project")
            if current_proj:
                st.markdown(
                    f"<div style='background:#e6f0ff;padding:8px 12px;border-radius:6px;"
                    f"border:1px solid #b3d1ff;margin-bottom:10px;'>"
                    f"<small style='color:#004085;'>현재 프로젝트</small><br>"
                    f"<b style='color:#0068c9;'>{current_proj}</b></div>",
                    unsafe_allow_html=True,
                )

            # 그룹별 네비게이션 렌더링
            for section_name, items in NAV_SECTIONS.items():
                st.markdown(
                    f"<div class='nav-section-header'>{section_name}</div>",
                    unsafe_allow_html=True,
                )
                for item in items:
                    is_active = (st.session_state.selected_page == item)
                    if st.button(item, key=f"nav_{item}", use_container_width=True,
                                 type="primary" if is_active else "secondary"):
                        st.session_state.selected_page = item
                        st.rerun()

            st.markdown("---")

            # 설정 수정 버튼
            if st.button("⚙️ 설정 수정", key="nav_settings", use_container_width=True,
                          type="primary" if st.session_state.selected_page == "SETTINGS" else "secondary"):
                st.session_state.selected_page = "SETTINGS"
                st.rerun()

            if st.button("🏠 처음으로", key="nav_home", use_container_width=True):
                st.session_state.app_started = False
                st.rerun()

        # 메인 콘텐츠 영역
        selected_page = st.session_state.selected_page

        if selected_page == "📂 프로젝트":
            ui_project.render_project_hub(settings)

        elif selected_page == "SETTINGS":
            st.markdown("### ⚙️ 환경 설정 (Settings)")
            st.info("설정을 수정한 후 하단의 '적용' 버튼을 눌러주세요.")
            updated_settings = ui_input.render_settings()
            st.session_state['latest_settings'] = updated_settings

            st.markdown("---")
            if st.button("✅ 설정 적용 및 업무 복귀", type="primary"):
                st.session_state.selected_page = "📥 사전 정보 수집"
                st.rerun()

        elif selected_page in PHASE_PAGES:
            try:
                ui_workflow.render_phase_workflow(settings, selected_page)
            except Exception as e:
                st.error(f"워크플로우 오류: {type(e).__name__}: {e}")
                st.code(traceback.format_exc())

        elif selected_page in UTILITY_ANALYSIS_PAGES:
            try:
                ui_workflow.render_standard_workflow(settings, selected_page)
            except Exception as e:
                st.error(f"워크플로우 오류: {type(e).__name__}: {e}")
                st.code(traceback.format_exc())

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

        elif selected_page == "✏️ 문장 정리기":
            ui_text_organizer.render_text_organizer_panel(settings)

if __name__ == "__main__":
    main()

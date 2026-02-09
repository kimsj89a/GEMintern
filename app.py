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
import utils
import core_logic

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

def render_project_sidebar(settings):
    """사이드바 프로젝트 관리 UI"""
    with st.sidebar:
        st.markdown("## 📁 프로젝트 자료 관리")

        # 프로젝트 선택/생성
        projects = utils.list_projects()
        project_options = ["-- 선택하세요 --"] + projects + ["➕ 새 프로젝트 만들기"]

        if "current_project" not in st.session_state:
            st.session_state["current_project"] = ""

        # 현재 프로젝트가 있으면 해당 인덱스 선택
        default_idx = 0
        if st.session_state["current_project"] in projects:
            default_idx = projects.index(st.session_state["current_project"]) + 1

        selected = st.selectbox(
            "프로젝트 선택",
            project_options,
            index=default_idx,
            key="sidebar_project_select"
        )

        # 새 프로젝트 만들기
        if selected == "➕ 새 프로젝트 만들기":
            new_name = st.text_input("새 프로젝트 이름", placeholder="예: Redvelvet", key="sidebar_new_project")
            if st.button("프로젝트 생성", key="sidebar_create_project") and new_name:
                created = utils.create_project(new_name)
                if created:
                    st.session_state["current_project"] = created
                    st.rerun()
                else:
                    st.error("유효하지 않은 프로젝트 이름입니다.")
        elif selected and selected != "-- 선택하세요 --":
            st.session_state["current_project"] = selected
        else:
            st.session_state["current_project"] = ""

        current_project = st.session_state.get("current_project", "")

        if current_project:
            st.markdown("---")

            # 파일 업로더
            uploaded_files = st.file_uploader(
                "자료 파일 업로드",
                accept_multiple_files=True,
                key="sidebar_project_files",
                help="PDF, Word, Excel, PPT, TXT 등"
            )

            if uploaded_files and st.button("📥 자료 로드", use_container_width=True, type="primary", key="sidebar_load_files"):
                api_key = settings.get("api_key", "")
                docai_config = settings.get("docai_config")
                loaded_count = 0
                with st.spinner("파일 파싱 및 저장 중..."):
                    for file in uploaded_files:
                        parsed = utils.parse_uploaded_file(file, api_key=api_key, docai_config=docai_config)
                        if parsed:
                            utils.add_doc_to_project(current_project, file.name, parsed)
                            loaded_count += 1
                if loaded_count > 0:
                    st.success(f"✅ {loaded_count}개 파일 로드 완료! (프로젝트 문서함에 저장됨)")
                    # st.rerun() 제거: 즉시 반영하여 UI 갱신
                else:
                    st.error("❌ 로드된 파일이 없습니다. (빈 파일이거나 지원되지 않는 형식)")

            # 현재 프로젝트 문서 목록
            docs = utils.list_project_docs(current_project)
            if docs:
                st.success(f"프로젝트 **{current_project}** - {len(docs)}개 문서 로드됨")
                with st.expander("📚 로드된 문서 목록", expanded=False):
                    for doc_name in docs:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.caption(doc_name)
                        with col2:
                            if st.button("🗑", key=f"del_{doc_name}", help="문서 삭제"):
                                utils.remove_doc_from_project(current_project, doc_name)
                                st.rerun()
            else:
                st.info("파일을 업로드하고 '자료 로드' 버튼을 눌러주세요.")

            # 프로젝트 삭제
            st.markdown("---")
            if st.button("🗑️ 프로젝트 삭제", key="sidebar_delete_project", type="secondary"):
                utils.delete_project(current_project)
                st.session_state["current_project"] = ""
                st.rerun()

    # 프로젝트 문서 텍스트/이름 반환
    project_docs_text = ""
    project_doc_names = []
    if current_project:
        project_doc_names = utils.list_project_docs(current_project)
        if project_doc_names:
            project_docs_text = utils.load_all_project_docs(current_project)

    return {
        "project_name": current_project,
        "project_docs_text": project_docs_text,
        "project_doc_names": project_doc_names,
    }


def main():
    st.markdown("""
        <div class="title-container">
            <h1>💎 GEM Intern</h1>
            <span class="badge">v6.0</span>
            <span class="badge badge-blue">Cloud-Safe Indexer</span>
        </div>
        <p style='color: gray; margin-top: -10px; margin-bottom: 20px;'>AI-Powered Investment Analysis Assistant</p>
    """, unsafe_allow_html=True)

if "current_project" not in st.session_state:
    st.session_state.current_project = None

    # 사이드바 프로젝트 관리
    project_info = render_project_sidebar(settings)
    settings["project_docs_text"] = project_info["project_docs_text"]
    settings["project_doc_names"] = project_info["project_doc_names"]
    settings["project_name"] = project_info["project_name"]

    # 탭 기반 UI - 프로세스 3탭 + 도구 5탭
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📋 초기검토",
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

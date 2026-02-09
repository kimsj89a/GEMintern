import streamlit as st
import ui_input
import ui_output
import ui_audio
import ui_crawler
import ui_ocr
import ui_markdown
import ui_doctemplate
import utils
import core_logic

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

    # 공통 설정 (탭 위에 고정)
    settings = ui_input.render_settings()

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
        "🎤 오디오 전사",
        "🌐 웹 크롤러",
        "👁️ 문서 OCR",
        "📝 MD to Word",
        "📋 문서양식"
    ])

    with tab1:
        st.markdown("### 📋 초기검토 (Quick Memo)")
        st.caption("약식 투자검토보고서를 빠르게 작성합니다.")
        st.markdown("---")
        inputs = ui_input.render_initial_review_panel(st.container(), settings)
        st.markdown("<br>", unsafe_allow_html=True)
        ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="init")

    with tab2:
        st.markdown("### 📊 예비실사 (Preliminary DD)")
        st.caption("투자심사보고서, IM, 발표자료, 사후관리보고서 등을 작성합니다.")
        st.markdown("---")
        inputs = ui_input.render_preliminary_dd_panel(st.container(), settings)
        st.markdown("<br>", unsafe_allow_html=True)
        ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="prelim")

    with tab3:
        st.markdown("### 🔍 정밀실사 (Detailed DD)")
        st.caption("RFI (자료요청목록) 작성 - FDD/LDD 유형별 지원")
        st.markdown("---")
        inputs = ui_input.render_detailed_dd_panel(st.container(), settings)
        st.markdown("<br>", unsafe_allow_html=True)
        ui_output.render_output_panel(st.container(), settings, inputs, key_prefix="dd")

    with tab4:
        ui_audio.render_audio_transcription_panel(settings)

    with tab5:
        ui_crawler.render_crawler_panel(settings)

    with tab6:
        ui_ocr.render_ocr_panel(settings)

    with tab7:
        ui_markdown.render_markdown_converter_panel(settings)

    with tab8:
        ui_doctemplate.render_doctemplate_panel(settings)

if __name__ == "__main__":
    main()
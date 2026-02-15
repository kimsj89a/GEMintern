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
import utils
import core_logic
import core_logic
import core_rag
import ui_ppt_tools
import ui_lp_qa

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="GEM Intern v7.0", page_icon="💎")

# --- CSS 스타일 적용 ---
st.markdown("""
<style>
    :root {
        /* Primary palette */
        --gem-primary: #0068c9;
        --gem-primary-light: #e6f0ff;
        --gem-primary-border: #b3d1ff;
        --gem-primary-dark: #004085;

        /* Step indicator */
        --gem-step-done-bg: #d4edda;
        --gem-step-done-border: #28a745;
        --gem-step-done-text: #155724;
        --gem-step-active-bg: #cce5ff;
        --gem-step-active-border: var(--gem-primary);
        --gem-step-active-text: var(--gem-primary-dark);
        --gem-step-pending-bg: #f8f9fa;
        --gem-step-pending-border: #dee2e6;
        --gem-step-pending-text: #6c757d;

        /* Surfaces & badges */
        --gem-surface: #f0f2f6;
        --gem-surface-border: #d6d6d8;
        --gem-badge-text: #31333F;
        --gem-muted: #6c757d;
        --gem-info-bg: #fff8c5;
        --gem-info-border: #e3d5a5;
        --gem-info-text: #5c4b12;

        /* Spacing */
        --gem-spacing-xs: 4px;
        --gem-spacing-sm: 8px;
        --gem-spacing-md: 16px;
        --gem-spacing-lg: 24px;

        /* Typography */
        --gem-font-xs: 0.75rem;
        --gem-font-sm: 0.85rem;
        --gem-font-md: 1rem;
        --gem-font-lg: 1.05rem;
    }

    .reportview-container .main .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    .title-container { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
    .badge { background-color: var(--gem-surface); color: var(--gem-badge-text); padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 500; border: 1px solid var(--gem-surface-border); }
    .badge-blue { background-color: var(--gem-primary-light); color: var(--gem-primary); border: 1px solid var(--gem-primary-border); }
    .info-box { background-color: var(--gem-info-bg); padding: 10px; border-radius: 5px; border: 1px solid var(--gem-info-border); font-size: var(--gem-font-sm); color: var(--gem-info-text); margin-bottom: 15px; }
    p, li, div { word-break: keep-all; overflow-wrap: break-word; }

    /* Dashboard cards */
    .dash-card {
        background: white; border: 1px solid var(--gem-step-pending-border);
        border-radius: 12px; padding: var(--gem-spacing-lg); text-align: center;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .dash-card:hover { border-color: var(--gem-primary); box-shadow: 0 4px 12px rgba(0,104,201,0.08); }
    .dash-card .phase-num { font-size: 1.6rem; font-weight: 700; color: var(--gem-primary); }
    .dash-card .phase-title { font-size: var(--gem-font-lg); font-weight: 600; margin: var(--gem-spacing-xs) 0; }
    .dash-card .phase-desc { font-size: var(--gem-font-sm); color: var(--gem-muted); }
    .dash-card-done { border-left: 4px solid var(--gem-step-done-border); }

    /* Project context banner */
    .project-banner {
        background: var(--gem-primary-light); padding: var(--gem-spacing-sm) var(--gem-spacing-md);
        border-radius: 6px; border-left: 4px solid var(--gem-primary);
        margin-bottom: var(--gem-spacing-md); display: flex; align-items: center; gap: var(--gem-spacing-sm);
    }
    .project-banner .proj-name { font-weight: 600; color: var(--gem-primary); }
    .project-banner .proj-meta { color: var(--gem-muted); font-size: var(--gem-font-sm); }

    /* Breadcrumb */
    .breadcrumb { margin-bottom: var(--gem-spacing-md); font-size: var(--gem-font-sm); }
    .breadcrumb span { color: var(--gem-muted); }
    .breadcrumb .bc-current { color: var(--gem-primary); font-weight: 600; }

    /* 사이드바 네비게이션 버튼 스타일 (Gemini-like) */
    section[data-testid="stSidebar"] .stButton button {
        text-align: left;
        padding-left: 20px;
        border: none;
        background-color: transparent;
        font-size: var(--gem-font-lg);
        justify-content: flex-start;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background-color: var(--gem-surface);
        color: var(--gem-primary);
    }
    /* 활성화된 버튼 스타일 */
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: var(--gem-primary-light);
        color: var(--gem-primary);
        font-weight: 600;
        border-left: 4px solid var(--gem-primary);
        border-radius: 0 4px 4px 0;
    }
    /* 사이드바 섹션 헤더 */
    .nav-section-header {
        color: var(--gem-muted);
        font-size: var(--gem-font-xs);
        font-weight: 600;
        text-transform: uppercase;
        padding: var(--gem-spacing-sm) 20px var(--gem-spacing-xs) 20px;
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
        projects = [p["name"] for p in core_rag.list_projects()]
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
                result = core_rag.create_project(new_name)
                if result["success"]:
                    st.session_state["current_project"] = result["project"]["name"]
                    st.rerun()
                else:
                    st.error(result["error"])
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
                            core_rag.index_texts(api_key, {file.name: parsed}, current_project)
                            loaded_count += 1
                if loaded_count > 0:
                    st.success(f"✅ {loaded_count}개 파일 로드 완료! (프로젝트 문서함에 저장됨)")
                    # st.rerun() 제거: 즉시 반영하여 UI 갱신
                else:
                    st.error("❌ 로드된 파일이 없습니다. (빈 파일이거나 지원되지 않는 형식)")

            # 현재 프로젝트 문서 목록
            docs = core_rag.get_indexed_doc_names(current_project)
            if docs:
                st.success(f"프로젝트 **{current_project}** - {len(docs)}개 문서 로드됨")
                with st.expander("📚 로드된 문서 목록", expanded=False):
                    for doc_name in docs:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.caption(doc_name)
                        with col2:
                            if st.button("🗑", key=f"del_{doc_name}", help="문서 삭제"):
                                core_rag.trash_document(current_project, doc_name)
                                st.rerun()
            else:
                st.info("파일을 업로드하고 '자료 로드' 버튼을 눌러주세요.")

            # 프로젝트 삭제 (확인 대화상자)
            st.markdown("---")
            if st.button("🗑️ 프로젝트 삭제", key="sidebar_delete_project", type="secondary"):
                st.session_state["_confirm_sidebar_delete"] = True
                st.rerun()

            if st.session_state.get("_confirm_sidebar_delete"):
                st.warning(f"'{current_project}' 프로젝트를 삭제하시겠습니까?")
                c_del1, c_del2 = st.columns(2)
                with c_del1:
                    if st.button("삭제 확인", key="sidebar_del_confirm", type="primary"):
                        core_rag.delete_project(current_project)
                        st.session_state["current_project"] = ""
                        st.session_state.pop("_confirm_sidebar_delete", None)
                        st.rerun()
                with c_del2:
                    if st.button("취소", key="sidebar_del_cancel"):
                        st.session_state.pop("_confirm_sidebar_delete", None)
                        st.rerun()

    # 프로젝트 문서 텍스트/이름 반환
    project_docs_text = ""
    project_doc_names = []
    if current_project:
        project_doc_names = core_rag.get_indexed_doc_names(current_project)
        if project_doc_names:
            project_docs_text = core_rag.load_all_project_docs(current_project)

    return {
        "project_name": current_project,
        "project_docs_text": project_docs_text,
        "project_doc_names": project_doc_names,
    }


NAV_SECTIONS = {
    "Main": ["🏠 홈", "📂 프로젝트"],
    "Phase Workflow": ["📥 사전 정보 수집", "📝 투심보고서 작성"], #, "💰 FDD (재무실사)", "⚖️ LDD (법률실사)"],
    "Independent Tools": ["📑 IM 작성", "📢 발표자료 (PPT)", "🙋‍♂️ LP Q&A 대응"],
    "Utilities": [
        "🎤 오디오 전사", "🌐 웹 크롤러", "👁️ 문서 OCR",
        "📝 MD to Word", "📋 문서양식", "✏️ 문장 정리기",
    ],
}

# FDD/LDD temporarily disabled
PHASE_PAGES = ["📥 사전 정보 수집", "📝 투심보고서 작성"] #, "💰 FDD (재무실사)", "⚖️ LDD (법률실사)"]
UTILITY_ANALYSIS_PAGES = ["📑 IM 작성"]

def render_dashboard(settings):
    """메인 대시보드 화면"""
    st.markdown("### 🏠 GEM Intern Dashboard")
    st.markdown("투자 분석 업무의 단계를 선택하세요.")

    # 1. Phase Workflow
    st.markdown("#### 🚀 Investment Workflow")

    phases = [
        {
            "num": "Phase 1", "icon": "📥", "page": "📥 사전 정보 수집",
            "title": "사전 정보 수집", "desc": "자료 수집, 시장 조사, 초기 검토",
            "prefix": "p1", "key": "dash_p1",
        },
        {
            "num": "Phase 2", "icon": "📝", "page": "📝 투심보고서 작성",
            "title": "투심보고서 작성", "desc": "IM 작성, Valuation, 투자심의",
            "prefix": "p2", "key": "dash_p2",
        },
        # {
        #     "num": "Phase 3", "icon": "💰", "page": "💰 FDD (재무실사)",
        #     "title": "FDD (재무실사)", "desc": "회계법인 대응, 재무 이슈 관리",
        #     "prefix": "p3", "key": "dash_p3",
        # },
        # {
        #     "num": "Phase 4", "icon": "⚖️", "page": "⚖️ LDD (법률실사)",
        #     "title": "LDD (법률실사)", "desc": "법무법인 대응, 법률 리스크 관리",
        #     "prefix": "p4", "key": "dash_p4",
        # },
    ]

    cols = st.columns(2) # Adjusted columns
    for col, ph in zip(cols, phases):
        with col:
            has_result = bool(st.session_state.get(f"{ph['prefix']}_generated_text", ""))
            done_cls = " dash-card-done" if has_result else ""
            badge = "<span style='color:var(--gem-step-done-border);font-size:var(--gem-font-sm);'> ✅ 결과 있음</span>" if has_result else ""
            st.markdown(
                f"<div class='dash-card{done_cls}'>"
                f"<div class='phase-num'>{ph['icon']}</div>"
                f"<div class='phase-title'>{ph['num']}: {ph['title']}{badge}</div>"
                f"<div class='phase-desc'>{ph['desc']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"{ph['icon']} {ph['title']} 시작", use_container_width=True, key=ph["key"]):
                st.session_state.selected_page = ph["page"]
                st.rerun()

    st.markdown("---")

    # 2. Tools & Project
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🛠️ Independent Tools")
        if st.button("📑 IM 작성", use_container_width=True, key="dash_im"):
            st.session_state.selected_page = "📑 IM 작성"
            st.rerun()
        if st.button("📢 발표자료 (PPT)", use_container_width=True, key="dash_ppt"):
            st.session_state.selected_page = "📢 발표자료 (PPT)"
            st.rerun()
        if st.button("🙋‍♂️ LP Q&A 대응", use_container_width=True, key="dash_lp_qa"):
            st.session_state.selected_page = "🙋‍♂️ LP Q&A 대응"
            st.rerun()

    with c2:
        st.markdown("#### 📂 Project")
        if st.button("📂 프로젝트 관리", use_container_width=True, type="primary", key="dash_proj"):
            st.session_state.selected_page = "📂 프로젝트"
            st.rerun()
        st.caption("문서 저장소 및 RAG 설정")

def _render_breadcrumb(selected_page):
    """메인 콘텐츠 상단에 현재 위치 경로 표시."""
    crumbs = ["GEM Intern"]
    for section_name, items in NAV_SECTIONS.items():
        if selected_page in items:
            crumbs.append(section_name)
            break
    if selected_page == "SETTINGS":
        crumbs.append("Settings")
    else:
        crumbs.append(selected_page)

    # Phase 스텝 정보 추가
    if selected_page in PHASE_PAGES:
        config = ui_workflow.PHASE_CONFIGS.get(selected_page, {})
        prefix = config.get("key_prefix", "")
        if config.get("page_type") != "collection":
            step = st.session_state.get(f"{prefix}_current_step", 1)
            steps = config.get("steps", {})
            if step in steps:
                _, step_label = steps[step]
                crumbs.append(f"Step {step}: {step_label}")

    parts = []
    for i, c in enumerate(crumbs):
        if i < len(crumbs) - 1:
            parts.append(f"<span>{c}</span>")
        else:
            parts.append(f"<span class='bc-current'>{c}</span>")
    st.markdown(
        f"<div class='breadcrumb'>{' &rsaquo; '.join(parts)}</div>",
        unsafe_allow_html=True,
    )


def _render_project_banner():
    """현재 선택된 프로젝트 컨텍스트 배너."""
    project = st.session_state.get("current_project", "")
    if project:
        doc_names = core_rag.get_indexed_doc_names(project) or []
        st.markdown(
            f"<div class='project-banner'>"
            f"<span style='font-size:1.1em;'>📂</span>"
            f"<span class='proj-name'>{project}</span>"
            f"<span class='proj-meta'>| {len(doc_names)}건 문서</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


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
                st.session_state.selected_page = "🏠 홈"
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

            # 프로젝트 퀵 스위처 렌더링
            render_project_sidebar(settings)

            # 그룹별 네비게이션 렌더링
            for section_name, items in NAV_SECTIONS.items():
                # Utilities 섹션은 접을 수 있게 (현재 선택 페이지가 해당 섹션에 있으면 자동 펼침)
                is_section_active = st.session_state.selected_page in items
                if section_name == "Utilities":
                    with st.expander(f"🧰 {section_name}", expanded=is_section_active):
                        for item in items:
                            is_active = (st.session_state.selected_page == item)
                            if st.button(item, key=f"nav_{item}", use_container_width=True,
                                         type="primary" if is_active else "secondary"):
                                st.session_state.selected_page = item
                                st.rerun()
                else:
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
                st.session_state.selected_page = "🏠 홈"
                st.rerun()

        # 메인 콘텐츠 영역
        selected_page = st.session_state.selected_page

        # 브레드크럼 + 프로젝트 배너 (홈 제외)
        if selected_page != "🏠 홈":
            _render_breadcrumb(selected_page)
            _render_project_banner()

        if selected_page == "🏠 홈":
            render_dashboard(settings)

        elif selected_page == "📂 프로젝트":
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
            
        elif selected_page == "📢 발표자료 (PPT)":
            ui_ppt_tools.render_ppt_tools_panel(settings)
            
        elif selected_page == "🙋‍♂️ LP Q&A 대응":
            ui_lp_qa.render_lp_qa_panel(settings)

if __name__ == "__main__":
    main()

"""
Step-based workflow UI for analysis pages.
Phase workflow: 3 custom-flow phases (사전 정보 수집, 예비실사, 정밀실사)
Standard workflow: 4-step flow for utility pages (IM 작성, PPT 생성)
"""

import streamlit as st
import streamlit.components.v1 as components
import utils
import utils_ppt
import core_logic
import core_chained
import core_rag


# ========================================
# Utility
# ========================================

def _strip_preamble(text):
    """Remove AI preamble text before the first markdown heading."""
    if not text:
        return text
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('#') and len(stripped) > 1 and stripped[1:].lstrip().strip():
            if i > 0:
                return '\n'.join(lines[i:])
            break
    return text


# ========================================
# Phase configurations (3-phase workflow)
# ========================================

PHASE_CONFIGS = {
    "📥 사전 정보 수집": {
        "phase_id": "phase1",
        "key_prefix": "p1",
        "title": "📥 사전 정보 수집 및 접촉",
        "subtitle": "공개 자료 기반 기업/산업/인력 사전 조사 및 자료 수집 정리",
        "page_type": "collection",
        "tabs": ["📁 자료 수집", "🔍 자료 분석", "❓ 추가 질문 정리", "📝 보고서 생성"],
        "default_template": "simple_review",
        "template_options": {
            "simple_review": "1. 약식 투자검토 (Quick Memo)",
            "free_summary": "2. 자유 구조화 (요약보고서)",
        },
        "show_gen_mode": True,
    },
    "📊 예비실사": {
        "phase_id": "phase2",
        "key_prefix": "p2",
        "title": "📊 예비실사 (Preliminary Due Diligence)",
        "subtitle": "NDA 후 내부 정보 기반 투자 매력도 분석 및 Valuation 검토",
        "page_type": "analysis",
        "steps": {
            1: ("📁", "데이터 입력"),
            2: ("📋", "체크리스트"),
            3: ("🤖", "보고서 생성"),
            4: ("💬", "수정/보완"),
            5: ("📄", "최종 결과"),
        },
        "default_template": "investment",
        "template_options": {
            "investment": "1. 투자심사보고서 (표준)",
            "management": "2. 사후관리보고서",
            "term_sheet": "3. Term Sheet 정리",
            "loi_mou": "4. LOI/MOU 초안",
            "free_summary": "5. 자유 구조화 (요약)",
            "custom": "6. 자유 구조화 (요약보고서)",
        },
        "show_gen_mode": True,
    },
    "🔍 정밀실사": {
        "phase_id": "phase3",
        "key_prefix": "p3",
        "title": "🔍 정밀실사 (Detailed Due Diligence)",
        "subtitle": "외부 자문사 활용 상세 실사, RFI 관리 및 실사결과 보고",
        "page_type": "dd_management",
        "steps": {
            1: ("📥", "실사 설정"),
            2: ("📋", "RFI 관리"),
            3: ("🔍", "실사 점검"),
            4: ("🤖", "보고서 생성"),
            5: ("💬", "수정/보완"),
            6: ("📄", "최종 결과"),
        },
        "default_template": "rfi",
        "template_options": {
            "rfi": "1. RFI (자료요청목록)",
            "dd_report": "2. 실사결과보고서",
        },
        "show_gen_mode": False,
    },
}

# ========================================
# Utility page configurations (legacy 4-step)
# ========================================

UTILITY_CONFIGS = {
    "📑 IM 작성": {
        "key_prefix": "im",
        "title": "📑 IM 작성 (Information Memorandum)",
        "subtitle": "잠재 투자자를 위한 투자제안서(IM)를 작성합니다.",
        "default_template": "im",
        "template_options": {
            "im": "1. IM (투자제안서)",
            "free_summary": "2. 자유 구조화 (요약)",
        },
        "show_gen_mode": False,
        "page_type": "standard",
    },
    "🖥️ PPT 생성": {
        "key_prefix": "ppt",
        "title": "🖥️ PPT 생성 (Paper2Slides)",
        "subtitle": "문서나 논문을 발표자료(PPT)로 변환합니다.",
        "default_template": "presentation",
        "template_options": {
            "presentation": "1. 투자심의 발표자료",
            "paper_review": "2. 논문/문서 발표자료 (Paper2Slides)",
        },
        "show_gen_mode": False,
        "page_type": "standard",
    },
}


# ========================================
# Main entry points
# ========================================

def render_phase_workflow(settings, selected_page):
    """Entry point for 3-phase investment workflow."""
    config = PHASE_CONFIGS.get(selected_page)
    if not config:
        st.error(f"Unknown phase page: {selected_page}")
        return

    prefix = config["key_prefix"]
    _init_phase_state(prefix, config)
    page_type = config["page_type"]

    if page_type == "collection":
        # Tab-based layout (no step indicator)
        _render_phase1_tabs(prefix, settings, config)
    else:
        _render_phase_step_indicator(prefix, config)
        current_step = st.session_state[f"{prefix}_current_step"]
        if page_type == "analysis":
            _dispatch_phase2_step(current_step, prefix, settings, config)
        elif page_type == "dd_management":
            _dispatch_phase3_step(current_step, prefix, settings, config)


def render_standard_workflow(settings, selected_page):
    """Entry point for utility pages (IM, PPT) using legacy 4-step flow."""
    config = UTILITY_CONFIGS.get(selected_page)
    if not config:
        st.error(f"Unknown utility page: {selected_page}")
        return

    prefix = config["key_prefix"]
    _init_workflow_state(prefix, config)
    _render_step_indicator(prefix)

    current_step = st.session_state[f"{prefix}_current_step"]

    if current_step == 1:
        _render_step1_upload(prefix, settings, config)
    elif current_step == 2:
        _render_step_generate(prefix, settings, config, step_number=2, total_steps=4)
    elif current_step == 3:
        _render_step_refine(prefix, settings, config, step_number=3, total_steps=4)
    elif current_step == 4:
        _render_step_output(prefix, settings, config, step_number=4, total_steps=4)


# ========================================
# Phase dispatchers
# ========================================

def _dispatch_phase2_step(step, prefix, settings, config):
    """Phase 2: 예비실사 (5-step)."""
    if step == 1:
        _render_p2_step1_input(prefix, settings, config)
    elif step == 2:
        _render_p2_step2_checklist(prefix, settings, config)
    elif step == 3:
        _render_step_generate(prefix, settings, config, step_number=3, total_steps=5)
    elif step == 4:
        _render_step_refine(prefix, settings, config, step_number=4, total_steps=5)
    elif step == 5:
        _render_step_output(prefix, settings, config, step_number=5, total_steps=5)


def _dispatch_phase3_step(step, prefix, settings, config):
    """Phase 3: 정밀실사 (6-step)."""
    if step == 1:
        _render_p3_step1_setup(prefix, settings, config)
    elif step == 2:
        _render_p3_step2_rfi(prefix, settings, config)
    elif step == 3:
        _render_p3_step3_checkpoint(prefix, settings, config)
    elif step == 4:
        _render_step_generate(prefix, settings, config, step_number=4, total_steps=6)
    elif step == 5:
        _render_step_refine(prefix, settings, config, step_number=5, total_steps=6)
    elif step == 6:
        _render_step_output(prefix, settings, config, step_number=6, total_steps=6)


# ========================================
# State management
# ========================================

def _init_workflow_state(prefix, config):
    """Initialize session state for utility (legacy 4-step) workflows."""
    defaults = {
        f"{prefix}_current_step": 1,
        f"{prefix}_inputs": {},
        f"{prefix}_generated_text": "",
        f"{prefix}_file_context": "",
        f"{prefix}_chat_history": [],
        f"{prefix}_generation_complete": False,
        f"{prefix}_ocr_text": "",
        f"{prefix}_active_mode": config.get("default_template", ""),
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _init_phase_state(prefix, config):
    """Initialize session state for phase workflows."""
    defaults = {
        f"{prefix}_current_step": 1,
        f"{prefix}_inputs": {},
        f"{prefix}_generated_text": "",
        f"{prefix}_file_context": "",
        f"{prefix}_chat_history": [],
        f"{prefix}_generation_complete": False,
        f"{prefix}_ocr_text": "",
        f"{prefix}_active_mode": config.get("default_template", ""),
    }
    page_type = config.get("page_type")
    if page_type == "collection":
        defaults[f"{prefix}_collected_files_meta"] = []
        defaults[f"{prefix}_organized_summary"] = ""
        defaults[f"{prefix}_followup_questions"] = ""
        defaults[f"{prefix}_file_categories"] = {}
        defaults[f"{prefix}_context_text"] = ""
        defaults[f"{prefix}_report_generating"] = False
    elif page_type == "analysis":
        defaults[f"{prefix}_checklist_data"] = {}
        defaults[f"{prefix}_checklist_complete"] = False
    elif page_type == "dd_management":
        defaults[f"{prefix}_dd_setup"] = {}
        defaults[f"{prefix}_rfi_generated"] = False
        defaults[f"{prefix}_rfi_text"] = ""
        defaults[f"{prefix}_rfi_tracking"] = []
        defaults[f"{prefix}_dd_issues"] = []
        defaults[f"{prefix}_dd_active_template"] = "rfi"

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _reset_workflow(prefix):
    """Clear all state for this workflow prefix."""
    keys_to_clear = [k for k in list(st.session_state.keys()) if k.startswith(f"{prefix}_")]
    for k in keys_to_clear:
        del st.session_state[k]


# ========================================
# Step indicators
# ========================================

def _render_step_indicator(prefix):
    """Render horizontal step progress bar (legacy 4-step)."""
    current = st.session_state[f"{prefix}_current_step"]
    steps = {
        1: ("📁", "데이터 업로드"),
        2: ("🤖", "보고서 생성"),
        3: ("💬", "수정/보완"),
        4: ("📄", "최종 결과"),
    }
    cols = st.columns(4)
    for i, col in enumerate(cols, 1):
        icon, label = steps[i]
        with col:
            _render_step_box(i, current, icon, label)
    st.markdown("---")


def _render_phase_step_indicator(prefix, config):
    """Render horizontal step progress bar (variable-length phases)."""
    current = st.session_state[f"{prefix}_current_step"]
    steps = config["steps"]
    num_steps = len(steps)

    # Title
    st.markdown(f"### {config['title']}")
    st.caption(config["subtitle"])

    cols = st.columns(num_steps)
    for i, col in enumerate(cols):
        step_num = i + 1
        icon, label = steps[step_num]
        with col:
            _render_step_box(step_num, current, icon, label)
    st.markdown("---")


def _render_step_box(step_num, current, icon, label):
    """Render a single step box with appropriate styling."""
    if step_num < current:
        st.markdown(
            f"<div style='text-align:center;padding:6px;background:#d4edda;"
            f"border-radius:8px;border:2px solid #28a745;'>"
            f"<span style='font-size:1.1em;'>✅</span><br>"
            f"<small style='color:#155724;'>{label}</small></div>",
            unsafe_allow_html=True,
        )
    elif step_num == current:
        st.markdown(
            f"<div style='text-align:center;padding:6px;background:#cce5ff;"
            f"border-radius:8px;border:2px solid #0068c9;'>"
            f"<span style='font-size:1.1em;'>{icon}</span><br>"
            f"<small style='color:#004085;font-weight:bold;'>{label}</small></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='text-align:center;padding:6px;background:#f8f9fa;"
            f"border-radius:8px;border:2px solid #dee2e6;'>"
            f"<span style='font-size:1.1em;'>{icon}</span><br>"
            f"<small style='color:#6c757d;'>{label}</small></div>",
            unsafe_allow_html=True,
        )


# ========================================
# Phase 1: 사전 정보 수집 - Tab-based Layout
# ========================================

def _render_phase1_tabs(prefix, settings, config):
    """Phase 1: independent tabs instead of sequential workflow."""
    st.markdown(f"### {config['title']}")
    st.caption(config["subtitle"])

    tab_labels = config["tabs"]
    tab_collect, tab_analyze, tab_questions, tab_report = st.tabs(tab_labels)

    with tab_collect:
        _render_p1_tab_collect(prefix, settings, config)
    with tab_analyze:
        _render_p1_tab_analyze(prefix, settings, config)
    with tab_questions:
        _render_p1_tab_questions(prefix, settings, config)
    with tab_report:
        _render_p1_tab_report(prefix, settings, config)


def _render_p1_tab_collect(prefix, settings, config):
    """Tab 1: 자료 수집 - 프로젝트 문서 로드 + 추가 파일 업로드."""
    current_project = st.session_state.get("current_project")
    has_rag = current_project and core_rag.is_rag_available() and core_rag.is_indexed(current_project)

    # Show current project docs
    if has_rag:
        rag_count = core_rag.get_indexed_count(current_project)
        st.success(f"프로젝트 **{current_project}** - {rag_count}개 문서 로드됨")

        docs_dict = core_rag.load_project_docs_dict(current_project)
        if docs_dict:
            with st.expander(f"📂 프로젝트 문서 ({len(docs_dict)}건)", expanded=False):
                for fname, content in docs_dict.items():
                    preview = content[:200].replace("\n", " ")
                    st.markdown(f"**{fname}** - {len(content):,}자")
                    st.caption(preview + "...")

        # Auto-load project docs into file_context
        if not st.session_state.get(f"{prefix}_file_context"):
            all_docs = core_rag.load_all_project_docs(current_project)
            if all_docs:
                st.session_state[f"{prefix}_file_context"] = f"--- [프로젝트 문서: {current_project}] ---\n{all_docs}"
    else:
        st.info("프로젝트를 선택하고 문서를 저장하면 자동으로 로드됩니다. 또는 아래에서 파일을 직접 업로드하세요.")

    st.markdown("---")

    # Additional file upload
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("#### 📁 추가 자료 업로드")
        uploaded_files = st.file_uploader(
            "감사보고서, 산업보고서, Analyst 보고서, 언론기사 등",
            accept_multiple_files=True,
            key=f"{prefix}_tab_collect_files",
        )

        # Category tagging
        file_categories = st.session_state.get(f"{prefix}_file_categories", {})
        if uploaded_files:
            st.markdown("##### 📂 자료 분류")
            category_options = ["감사보고서", "산업보고서", "Analyst 보고서", "언론기사", "기업 공시자료", "기타"]
            for f in uploaded_files:
                file_categories[f.name] = st.selectbox(
                    f.name,
                    category_options,
                    key=f"{prefix}_tab_cat_{f.name}",
                    label_visibility="collapsed",
                )
            st.session_state[f"{prefix}_file_categories"] = file_categories

    with col_right:
        st.markdown("#### 💬 조사 배경 / 핵심 질문")
        context_text = st.text_area(
            "Context",
            height=120,
            placeholder="예: 기업명, 투자 배경, 산업 동향, 핵심 확인 사항 등",
            key=f"{prefix}_tab_collect_context",
            label_visibility="collapsed",
        )

        # Project selector (if not already loaded)
        if not has_rag:
            selected_project, proj_doc_count = _render_project_doc_selector(prefix, "tab_collect")
        else:
            selected_project = current_project

    # Parse & load button
    st.markdown("")
    if st.button(
        "📥 자료 로드 및 파싱",
        type="primary",
        use_container_width=True,
        key=f"{prefix}_tab_collect_load",
    ):
        if not uploaded_files and not has_rag and not (not has_rag and selected_project):
            st.error("파일을 업로드하거나 프로젝트를 선택해주세요.")
        elif not settings.get("api_key") and uploaded_files:
            st.error("설정에서 API Key를 먼저 입력해주세요.")
        else:
            with st.spinner("자료를 파싱하고 로드 중..."):
                _parse_and_cache_files(
                    prefix, settings, uploaded_files, [],
                    config.get("default_template", "simple_review"),
                    project_name=selected_project if not has_rag else current_project,
                )
                # Collect file metadata
                meta = []
                if uploaded_files:
                    for f in uploaded_files:
                        meta.append({
                            "filename": f.name,
                            "category": file_categories.get(f.name, "기타"),
                            "size": f.size,
                        })
                st.session_state[f"{prefix}_collected_files_meta"] = meta
                if context_text:
                    st.session_state[f"{prefix}_context_text"] = context_text
            st.success("자료 로드 완료! 다른 탭에서 분석/질문/보고서 생성을 진행하세요.")

    # Show loaded data status
    file_context = st.session_state.get(f"{prefix}_file_context", "")
    if file_context:
        st.markdown("---")
        st.caption(f"현재 로드된 컨텍스트: {len(file_context):,}자")


def _render_p1_tab_analyze(prefix, settings, config):
    """Tab 2: 자료 분석 - AI 요약 + 핵심 발견사항 추출."""
    file_context = st.session_state.get(f"{prefix}_file_context", "")
    organized_summary = st.session_state.get(f"{prefix}_organized_summary", "")

    if not file_context.strip():
        st.info("먼저 '자료 수집' 탭에서 자료를 로드해주세요.")
        return

    st.caption(f"분석 대상 컨텍스트: {len(file_context):,}자")

    if st.button("🤖 AI 자료 분석 실행", type="primary", key=f"{prefix}_tab_analyze_run",
                  use_container_width=True):
        with st.spinner("자료를 분석하고 핵심 발견사항을 추출 중..."):
            try:
                summary = core_logic.generate_material_summary(
                    settings["api_key"],
                    settings["model_name"],
                    file_context,
                )
                st.session_state[f"{prefix}_organized_summary"] = summary
                organized_summary = summary
            except Exception as e:
                st.error(f"분석 오류: {e}")

    if organized_summary:
        st.markdown("##### 🔑 분석 결과")
        result_container = st.container(height=500, border=True)
        with result_container:
            st.markdown(organized_summary)
    else:
        st.info("위 버튼을 눌러 AI 분석을 실행하세요.")


def _render_p1_tab_questions(prefix, settings, config):
    """Tab 3: 추가 질문 정리 - 프로젝트 문서 참조하여 추가 질문 도출."""
    file_context = st.session_state.get(f"{prefix}_file_context", "")
    followup_questions = st.session_state.get(f"{prefix}_followup_questions", "")

    current_project = st.session_state.get("current_project")
    has_rag = (current_project and core_rag.is_rag_available()
               and core_rag.is_indexed(current_project))

    if not file_context.strip():
        st.info("먼저 '자료 수집' 탭에서 자료를 로드해주세요.")
        return

    rag_note = " (프로젝트 문서 참조)" if has_rag else ""
    st.caption(f"분석 대상 컨텍스트: {len(file_context):,}자{rag_note}")

    if st.button(f"❓ 추가 질문 생성{rag_note}", type="primary",
                  key=f"{prefix}_tab_questions_run", use_container_width=True):
        with st.spinner("추가 질문 및 조사 항목을 도출 중..."):
            try:
                project_docs_context = ""
                if has_rag:
                    project_docs_context = core_rag.load_all_project_docs(current_project)

                result = core_logic.generate_followup_questions(
                    settings["api_key"],
                    settings["model_name"],
                    file_context,
                    rag_context=project_docs_context,
                )
                st.session_state[f"{prefix}_followup_questions"] = result
                followup_questions = result
            except Exception as e:
                st.error(f"추가 질문 생성 오류: {e}")

    if followup_questions:
        st.markdown("##### ❓ 추가 질문/조사 항목")
        result_container = st.container(height=500, border=True)
        with result_container:
            st.markdown(followup_questions)
    else:
        st.info("위 버튼을 눌러 추가 질문을 생성하세요.")


def _render_p1_tab_report(prefix, settings, config):
    """Tab 4: 보고서 생성 - Quick review / 요약보고서."""
    file_context = st.session_state.get(f"{prefix}_file_context", "")
    organized_summary = st.session_state.get(f"{prefix}_organized_summary", "")
    followup_questions = st.session_state.get(f"{prefix}_followup_questions", "")
    generated_text = st.session_state.get(f"{prefix}_generated_text", "")

    if not file_context.strip():
        st.info("먼저 '자료 수집' 탭에서 자료를 로드해주세요.")
        return

    col_left, col_right = st.columns([1, 2], gap="medium")

    with col_left:
        template_options = config["template_options"]
        st.markdown("#### 📝 템플릿 선택")
        template_option = st.selectbox(
            "Template",
            list(template_options.keys()),
            format_func=lambda x: template_options[x],
            key=f"{prefix}_tab_report_template",
            label_visibility="collapsed",
        )

        default_structure = core_logic.get_default_structure(template_option)
        with st.expander("📋 문서 구조 미리보기 / 편집", expanded=False):
            structure_text = st.text_area(
                "Structure",
                value=default_structure,
                height=250,
                key=f"{prefix}_tab_report_structure",
                label_visibility="collapsed",
            )

        generation_mode = st.radio(
            "생성 방식",
            ["chained", "single"],
            format_func=lambda x: "📊 단계별 생성 (정확도↑)" if x == "chained" else "🚀 한 번에 생성 (속도↑)",
            index=0,
            horizontal=True,
            key=f"{prefix}_tab_report_gen_mode",
        )

        context_text = st.session_state.get(f"{prefix}_context_text",
                        st.session_state.get(f"{prefix}_tab_collect_context", ""))

        # Include analysis results as extra context
        include_analysis = st.checkbox(
            "자료 분석 결과 포함",
            value=bool(organized_summary),
            key=f"{prefix}_tab_report_inc_analysis",
        )
        include_questions = st.checkbox(
            "추가 질문 결과 포함",
            value=bool(followup_questions),
            key=f"{prefix}_tab_report_inc_questions",
        )

        if st.button("🤖 보고서 생성", type="primary", use_container_width=True,
                      key=f"{prefix}_tab_report_generate"):
            if not settings.get("api_key"):
                st.error("설정에서 API Key를 먼저 입력해주세요.")
            else:
                # Build full context
                full_context = file_context
                if include_analysis and organized_summary:
                    full_context += f"\n\n[AI 분석 결과 요약]\n{organized_summary}"
                if include_questions and followup_questions:
                    full_context += f"\n\n[추가 질문/조사 항목]\n{followup_questions}"

                st.session_state[f"{prefix}_file_context_for_gen"] = full_context
                st.session_state[f"{prefix}_inputs"] = {
                    "template_option": template_option,
                    "structure_text": structure_text,
                    "uploaded_files": [],
                    "context_text": context_text,
                    "selected_saved_files": [],
                    "generation_mode": generation_mode,
                    "generate_btn": True,
                    "use_diagram": settings.get("use_diagram", False),
                }
                st.session_state[f"{prefix}_active_mode"] = template_option
                st.session_state[f"{prefix}_report_generating"] = True
                st.rerun()

    with col_right:
        # Generation in progress
        if st.session_state.get(f"{prefix}_report_generating"):
            inputs = st.session_state[f"{prefix}_inputs"]
            gen_context = st.session_state.get(f"{prefix}_file_context_for_gen", file_context)

            with st.status("🤖 보고서를 생성하는 중...", expanded=True) as status:
                try:
                    gen_mode = inputs.get("generation_mode", "single")
                    if gen_mode == "chained" and core_chained.is_chained_supported(inputs.get("template_option", "")):
                        stream = core_logic.generate_report_stream_chained(
                            settings["api_key"], settings["model_name"],
                            inputs, settings["thinking_level"], gen_context,
                        )
                    else:
                        stream = core_logic.generate_report_stream(
                            settings["api_key"], settings["model_name"],
                            inputs, settings["thinking_level"], gen_context,
                        )

                    full_response = ""
                    response_placeholder = st.empty()
                    for chunk in stream:
                        if chunk.text:
                            full_response += chunk.text
                            response_placeholder.markdown(full_response + "▌")
                    response_placeholder.markdown(full_response)
                    status.update(label="✅ 작성 완료!", state="complete", expanded=False)

                    st.session_state[f"{prefix}_generated_text"] = _strip_preamble(full_response)
                    st.session_state[f"{prefix}_report_generating"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"생성 오류: {e}")
                    st.session_state[f"{prefix}_report_generating"] = False

        elif generated_text:
            st.markdown("#### 📄 생성된 보고서")
            result_container = st.container(height=500, border=True)
            with result_container:
                st.markdown(generated_text)

            # Download buttons
            st.markdown("")
            inputs = st.session_state.get(f"{prefix}_inputs", {})
            current_mode = st.session_state.get(f"{prefix}_active_mode", "")
            fname = utils.generate_filename(inputs.get("uploaded_files"), current_mode)

            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    "📄 Word 다운로드",
                    utils.create_docx(generated_text),
                    fname,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True, key=f"{prefix}_tab_dl_word",
                )
            with col_d2:
                st.download_button(
                    "📊 PPT 다운로드",
                    utils_ppt.create_ppt(generated_text),
                    fname.replace(".docx", ".pptx"),
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True, key=f"{prefix}_tab_dl_ppt",
                )
        else:
            st.info("왼쪽에서 템플릿을 선택하고 보고서를 생성하세요.")


# ========================================
# Phase 2: 예비실사 - Custom Steps
# ========================================

def _render_p2_step1_input(prefix, settings, config):
    """Phase 2 Step 1: 데이터 입력 (NDA 자료 업로드)."""
    current_project = st.session_state.get("current_project")
    has_rag = current_project and core_rag.is_rag_available() and core_rag.is_indexed(current_project)

    if has_rag:
        rag_count = core_rag.get_indexed_count(current_project)
        st.info(
            f"프로젝트 **{current_project}** (RAG {rag_count}건) 기반으로 생성합니다. "
            f"추가 파일 업로드는 선택사항입니다."
        )

    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("#### 📁 실사 자료 업로드" + (" (선택)" if has_rag else ""))
        uploaded_files = st.file_uploader(
            "NDA 체결 후 수령한 내부 자료를 업로드하세요",
            accept_multiple_files=True,
            key=f"{prefix}_s1_files",
        )

        selected_project, proj_doc_count = _render_project_doc_selector(prefix, "s1")

        st.markdown("#### 💬 투자 배경 / 맥락")
        context_text = st.text_area(
            "Context",
            height=120,
            placeholder="예: 기업명, 딜 규모, 타겟 밸류에이션, 투자 배경 등",
            key=f"{prefix}_s1_context",
            label_visibility="collapsed",
        )

    with col_right:
        template_options = config["template_options"]
        st.markdown("#### 📝 템플릿 선택")
        template_option = st.selectbox(
            "Template",
            list(template_options.keys()),
            format_func=lambda x: template_options[x],
            key=f"{prefix}_s1_template",
            label_visibility="collapsed",
        )

        default_structure = core_logic.get_default_structure(template_option)
        with st.expander("📋 문서 구조 미리보기 / 편집", expanded=False):
            structure_text = st.text_area(
                "Structure",
                value=default_structure,
                height=400,
                key=f"{prefix}_s1_structure",
                label_visibility="collapsed",
            )

        if config.get("show_gen_mode"):
            generation_mode = st.radio(
                "생성 방식",
                ["chained", "single"],
                format_func=lambda x: "📊 단계별 생성 (정확도↑)" if x == "chained" else "🚀 한 번에 생성 (속도↑)",
                index=0,
                horizontal=True,
                key=f"{prefix}_s1_gen_mode",
            )
        else:
            generation_mode = "single"

    # Navigation
    st.markdown("")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button(
            "다음: 체크리스트 평가 >>>",
            type="primary",
            use_container_width=True,
            key=f"{prefix}_s1_next",
        ):
            if not uploaded_files and not selected_project and not has_rag:
                st.error("파일을 업로드하거나 프로젝트를 선택해주세요.")
            elif not settings.get("api_key"):
                st.error("설정에서 API Key를 먼저 입력해주세요.")
            else:
                st.session_state[f"{prefix}_inputs"] = {
                    "template_option": template_option,
                    "structure_text": structure_text,
                    "uploaded_files": uploaded_files,
                    "context_text": context_text,
                    "selected_saved_files": [],
                    "generation_mode": generation_mode,
                    "generate_btn": True,
                }
                st.session_state[f"{prefix}_active_mode"] = template_option
                _parse_and_cache_files(prefix, settings, uploaded_files, [], template_option, project_name=selected_project)
                st.session_state[f"{prefix}_current_step"] = 2
                st.rerun()


def _render_p2_step2_checklist(prefix, settings, config):
    """Phase 2 Step 2: 투자 매력도 체크리스트 (8개 항목 평가)."""
    st.markdown("#### 📋 투자 매력도 체크리스트")
    st.caption("각 항목별로 1~5점 평가 및 근거를 작성하세요. AI 자동평가 버튼으로 자료 기반 제안을 받을 수 있습니다.")

    checklist_items = [
        ("사업안정성", "비즈니스 모델의 안정성, 매출 다변화, 고객 집중도"),
        ("경쟁력", "기술력, 브랜드, 시장 지위, 진입장벽"),
        ("수익성", "영업이익률, EBITDA 마진, 수익 구조의 지속성"),
        ("전략적 파트너 협업 가능성", "전략적 협업, 시너지 효과, 파트너 네트워크"),
        ("가치증대 가능성", "성장 잠재력, 운영 개선 여지, M&A 기회"),
        ("리스크 관리 용이성", "주요 리스크 식별 용이성, 대응 가능성, 규제 리스크"),
        ("투자수익 예측 타당성", "재무 추정의 신뢰성, 시장 성장률, 매출 추정 근거"),
        ("Valuation 적정성", "밸류에이션 수준, 유사 거래 대비, Multiple 적정성"),
    ]

    checklist_data = st.session_state.get(f"{prefix}_checklist_data", {})
    file_context = st.session_state.get(f"{prefix}_file_context", "")

    for item_name, item_desc in checklist_items:
        with st.expander(f"**{item_name}** - {item_desc}", expanded=False):
            col_score, col_rationale, col_ai = st.columns([1, 3, 1])

            current_data = checklist_data.get(item_name, {"score": 3, "rationale": ""})

            with col_score:
                score = st.slider(
                    "점수",
                    min_value=1, max_value=5,
                    value=current_data.get("score", 3),
                    key=f"{prefix}_cl_score_{item_name}",
                )

            with col_rationale:
                rationale = st.text_area(
                    "평가 근거",
                    value=current_data.get("rationale", ""),
                    height=80,
                    placeholder=f"{item_name}에 대한 평가 근거를 작성하세요...",
                    key=f"{prefix}_cl_rationale_{item_name}",
                    label_visibility="collapsed",
                )

            with col_ai:
                if st.button("🤖 AI 평가", key=f"{prefix}_cl_ai_{item_name}",
                              use_container_width=True):
                    if file_context.strip():
                        with st.spinner("AI 분석 중..."):
                            try:
                                result = core_logic.evaluate_checklist_item(
                                    settings["api_key"],
                                    settings["model_name"],
                                    f"{item_name} ({item_desc})",
                                    file_context,
                                )
                                st.info(result)
                            except Exception as e:
                                st.error(f"평가 오류: {e}")
                    else:
                        st.warning("분석할 자료가 없습니다.")

            checklist_data[item_name] = {"score": score, "rationale": rationale}

    st.session_state[f"{prefix}_checklist_data"] = checklist_data

    # Summary
    if checklist_data:
        scores = [v.get("score", 0) for v in checklist_data.values() if v.get("score")]
        if scores:
            avg_score = sum(scores) / len(scores)
            st.markdown(f"##### 종합 점수: **{avg_score:.1f}** / 5.0")
            st.progress(avg_score / 5.0)

    # Navigation
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("<<< 이전 단계", key=f"{prefix}_s2_prev"):
            st.session_state[f"{prefix}_current_step"] = 1
            st.rerun()
    with c3:
        if st.button("다음: 보고서 생성 >>>", type="primary", key=f"{prefix}_s2_next"):
            # Append checklist context for generation
            checklist_context = "\n\n[투자 매력도 체크리스트 평가 결과]\n"
            for item_name, data in checklist_data.items():
                checklist_context += f"- {item_name}: {data.get('score', '-')}점"
                if data.get("rationale"):
                    checklist_context += f" / {data['rationale']}"
                checklist_context += "\n"
            current_fc = st.session_state.get(f"{prefix}_file_context", "")
            st.session_state[f"{prefix}_file_context"] = current_fc + checklist_context
            st.session_state[f"{prefix}_checklist_complete"] = True
            st.session_state[f"{prefix}_current_step"] = 3
            st.session_state[f"{prefix}_generation_complete"] = False
            st.rerun()


# ========================================
# Phase 3: 정밀실사 - Custom Steps
# ========================================

def _render_p3_step1_setup(prefix, settings, config):
    """Phase 3 Step 1: 실사 설정 (DD 유형/자문사/범위)."""
    st.markdown("#### 📥 실사 설정")

    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("##### 실사 유형")
        dd_type = st.radio(
            "DD Type",
            ["general", "fdd", "ldd", "combined"],
            format_func=lambda x: {
                "general": "📋 일반 RFI (종합)",
                "fdd": "📊 FDD (재무실사)",
                "ldd": "⚖️ LDD (법률실사)",
                "combined": "🔄 FDD + LDD (통합)",
            }[x],
            horizontal=True,
            key=f"{prefix}_s1_dd_type",
            label_visibility="collapsed",
        )

        st.markdown("##### 자문사 정보")
        advisor_accounting = st.text_input("회계법인", placeholder="예: 삼일PwC", key=f"{prefix}_s1_adv_acc")
        advisor_law = st.text_input("법무법인", placeholder="예: 김앤장", key=f"{prefix}_s1_adv_law")
        advisor_industry = st.text_input("산업전문가", placeholder="예: 업종 전문 컨설턴트", key=f"{prefix}_s1_adv_ind")

    with col_right:
        st.markdown("##### 실사 범위 / 중점점검 사항")
        scope_text = st.text_area(
            "Scope",
            height=150,
            placeholder="예: 매출 인식 기준, 재고 실사, 핵심 계약서 검토, 지적재산권 현황 등",
            key=f"{prefix}_s1_scope",
            label_visibility="collapsed",
        )

        # Import from Phase 2
        st.markdown("##### 예비실사 결과 가져오기")
        p2_text = st.session_state.get("p2_generated_text", "")
        p2_checklist = st.session_state.get("p2_checklist_data", {})
        has_p2_data = bool(p2_text) or bool(p2_checklist)

        if has_p2_data:
            if st.button("📥 예비실사 결과 임포트", key=f"{prefix}_s1_import_p2",
                          type="primary", use_container_width=True):
                import_context = ""
                if p2_text:
                    import_context += f"\n[예비실사 보고서]\n{p2_text[:20000]}\n"
                if p2_checklist:
                    import_context += "\n[예비실사 체크리스트]\n"
                    for item, data in p2_checklist.items():
                        import_context += f"- {item}: {data.get('score', '-')}점"
                        if data.get("rationale"):
                            import_context += f" / {data['rationale']}"
                        import_context += "\n"
                st.session_state[f"{prefix}_file_context"] = import_context
                st.success("예비실사 결과를 가져왔습니다.")
        else:
            st.caption("예비실사 단계에서 생성된 결과가 없습니다.")

        # Template selection
        st.markdown("##### 보고서 템플릿")
        template_options = config["template_options"]
        template_option = st.selectbox(
            "Template",
            list(template_options.keys()),
            format_func=lambda x: template_options[x],
            key=f"{prefix}_s1_template",
            label_visibility="collapsed",
        )

    # Navigation
    st.markdown("")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button(
            "다음: RFI 관리 >>>",
            type="primary",
            use_container_width=True,
            key=f"{prefix}_s1_next",
        ):
            if not settings.get("api_key"):
                st.error("설정에서 API Key를 먼저 입력해주세요.")
            else:
                dd_context_prefix = {
                    "general": "",
                    "fdd": "[실사 유형: FDD (Financial Due Diligence)]\n재무실사 관점에서 재무제표, 세무, 운전자본, 순차입금, 정상화 EBITDA, 내부거래, 우발부채 등에 중점을 두어 자료를 요청하십시오.\n\n",
                    "ldd": "[실사 유형: LDD (Legal Due Diligence)]\n법률실사 관점에서 계약서, 소송/분쟁, 지적재산권, 인허가, 규제 준수, 지배구조, 주주간계약 등에 중점을 두어 자료를 요청하십시오.\n\n",
                    "combined": "[실사 유형: FDD + LDD (통합실사)]\n재무실사(FDD)와 법률실사(LDD)를 통합하여 수행합니다.\n\n",
                }
                st.session_state[f"{prefix}_dd_setup"] = {
                    "dd_type": dd_type,
                    "advisors": {
                        "accounting": advisor_accounting,
                        "law": advisor_law,
                        "industry": advisor_industry,
                    },
                    "scope": scope_text,
                }
                st.session_state[f"{prefix}_inputs"] = {
                    "template_option": template_option,
                    "structure_text": "",
                    "uploaded_files": [],
                    "context_text": dd_context_prefix.get(dd_type, "") + scope_text,
                    "rfi_existing": "",
                    "rfi_file_list_input": "",
                    "generate_btn": True,
                    "generation_mode": "single",
                    "selected_saved_files": [],
                }
                st.session_state[f"{prefix}_active_mode"] = template_option
                st.session_state[f"{prefix}_dd_active_template"] = template_option
                st.session_state[f"{prefix}_current_step"] = 2
                st.rerun()


def _render_p3_step2_rfi(prefix, settings, config):
    """Phase 3 Step 2: RFI 관리 (생성 + 추적)."""
    st.markdown("#### 📋 RFI 관리")

    tab_gen, tab_track = st.tabs(["📝 RFI 생성", "📊 RFI 추적"])

    with tab_gen:
        col_left, col_right = st.columns([1, 1], gap="medium")

        with col_left:
            st.caption("1. RFI 엑셀 파일 (Basis)")
            uploaded_rfi_file = st.file_uploader(
                "RFI 엑셀", type=["xlsx", "xls", "csv"],
                key=f"{prefix}_s2_rfi_basis", label_visibility="collapsed",
            )
            rfi_existing = ""
            if uploaded_rfi_file:
                with st.spinner("RFI 파싱..."):
                    rfi_existing = utils.parse_uploaded_file(uploaded_rfi_file)
                st.success("RFI 로드 완료")

            st.caption("2. 분석할 문서")
            uploaded_files = st.file_uploader(
                "분석 문서", accept_multiple_files=True,
                key=f"{prefix}_s2_files", label_visibility="collapsed",
            )

            selected_project, proj_doc_count = _render_project_doc_selector(prefix, "s2")

            st.caption("3. 추가 질문 및 확인 사항")
            context_text = st.text_area(
                "Context", height=100, label_visibility="collapsed",
                placeholder="예: 재고 관련 이슈 확인 필요...",
                key=f"{prefix}_s2_context",
            )

        with col_right:
            from ui_input import HTML_SCANNER
            st.markdown("##### 📂 수령 자료 스캔 (Folder Scan)")
            components.html(HTML_SCANNER, height=280)
            st.caption("파일 목록 붙여넣기 (Ctrl+V)")
            rfi_file_list_input = st.text_area(
                "File List", height=200, placeholder="- 폴더명/파일명.pdf...",
                key=f"{prefix}_s2_filelist", label_visibility="collapsed",
            )

        # Generate RFI button
        st.markdown("")
        if st.button("🤖 RFI 생성", type="primary", use_container_width=True,
                      key=f"{prefix}_s2_gen_rfi"):
            if not settings.get("api_key"):
                st.error("API Key가 필요합니다.")
            else:
                # Update inputs for RFI generation
                dd_setup = st.session_state.get(f"{prefix}_dd_setup", {})
                dd_type = dd_setup.get("dd_type", "general")
                dd_context_prefix = {
                    "general": "",
                    "fdd": "[실사 유형: FDD]\n",
                    "ldd": "[실사 유형: LDD]\n",
                    "combined": "[실사 유형: FDD + LDD]\n",
                }
                final_context = dd_context_prefix.get(dd_type, "") + context_text

                rfi_inputs = {
                    "template_option": "rfi",
                    "structure_text": "",
                    "uploaded_files": uploaded_files,
                    "rfi_file_list_input": rfi_file_list_input,
                    "context_text": final_context,
                    "rfi_existing": rfi_existing,
                    "generate_btn": True,
                    "generation_mode": "single",
                    "selected_saved_files": [],
                }
                st.session_state[f"{prefix}_inputs"] = rfi_inputs
                st.session_state[f"{prefix}_active_mode"] = "rfi"

                # Parse files
                if uploaded_files or selected_project:
                    _parse_and_cache_files(prefix, settings, uploaded_files, [], "rfi", project_name=selected_project)
                else:
                    existing_fc = st.session_state.get(f"{prefix}_file_context", "")
                    if not existing_fc:
                        st.session_state[f"{prefix}_file_context"] = "(RFI 모드: 내용은 읽지 않음)"

                # Generate
                file_context = st.session_state.get(f"{prefix}_file_context", "")
                with st.status("🤖 RFI를 생성하는 중...", expanded=True) as status:
                    try:
                        stream = core_logic.generate_report_stream(
                            settings["api_key"], settings["model_name"],
                            rfi_inputs, settings["thinking_level"], file_context,
                        )
                        full_response = ""
                        response_placeholder = st.empty()
                        for chunk in stream:
                            if chunk.text:
                                full_response += chunk.text
                                response_placeholder.markdown(full_response[:2000] + "...")
                        status.update(label="✅ RFI 생성 완료!", state="complete", expanded=False)

                        st.session_state[f"{prefix}_rfi_text"] = _strip_preamble(full_response)
                        st.session_state[f"{prefix}_generated_text"] = _strip_preamble(full_response)
                        st.session_state[f"{prefix}_rfi_generated"] = True
                        st.session_state[f"{prefix}_generation_complete"] = True
                    except Exception as e:
                        st.error(f"RFI 생성 오류: {e}")

    with tab_track:
        rfi_text = st.session_state.get(f"{prefix}_rfi_text", "")
        if rfi_text:
            st.markdown("##### 생성된 RFI")
            rfi_container = st.container(height=400, border=True)
            with rfi_container:
                st.markdown(rfi_text)
        else:
            st.info("RFI 생성 탭에서 먼저 RFI를 생성해주세요.")

    # Navigation
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("<<< 이전 단계", key=f"{prefix}_s2_prev"):
            st.session_state[f"{prefix}_current_step"] = 1
            st.rerun()
    with c3:
        if st.button("다음: 실사 점검 >>>", type="primary", key=f"{prefix}_s2_next"):
            st.session_state[f"{prefix}_current_step"] = 3
            st.rerun()


def _render_p3_step3_checkpoint(prefix, settings, config):
    """Phase 3 Step 3: 실사 점검 (이슈 로그 + 체크리스트)."""
    st.markdown("#### 🔍 실사 점검 - 이슈 관리")

    dd_issues = st.session_state.get(f"{prefix}_dd_issues", [])
    file_context = st.session_state.get(f"{prefix}_file_context", "")
    dd_setup = st.session_state.get(f"{prefix}_dd_setup", {})

    # AI Issue Analysis
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("##### 📎 실사 자료 추가 업로드")
        dd_files = st.file_uploader(
            "실사 결과 자료", accept_multiple_files=True,
            key=f"{prefix}_s3_dd_files", label_visibility="collapsed",
        )
        if dd_files:
            if st.button("파일 파싱", key=f"{prefix}_s3_parse_files"):
                with st.spinner("파일 파싱 중..."):
                    for f in dd_files:
                        parsed = utils.parse_uploaded_file(
                            f, api_key=settings.get("api_key"),
                            docai_config=settings.get("docai_config"),
                        )
                        file_context += f"\n\n{parsed}"
                    st.session_state[f"{prefix}_file_context"] = file_context
                    st.success("파일 파싱 완료")

    with col2:
        if st.button("🤖 AI 이슈 자동 분석", type="primary", key=f"{prefix}_s3_ai_issues",
                      use_container_width=True):
            if file_context.strip():
                with st.spinner("실사 자료에서 이슈를 분석하는 중..."):
                    try:
                        scope = dd_setup.get("scope", "")
                        result = core_logic.analyze_dd_issues(
                            settings["api_key"],
                            settings["model_name"],
                            file_context,
                            scope,
                        )
                        st.session_state[f"{prefix}_dd_issue_analysis"] = result
                    except Exception as e:
                        st.error(f"이슈 분석 오류: {e}")
            else:
                st.warning("분석할 자료가 없습니다. 자료를 업로드하거나 이전 단계에서 데이터를 확보해주세요.")

    # Display AI analysis result
    ai_analysis = st.session_state.get(f"{prefix}_dd_issue_analysis", "")
    if ai_analysis:
        st.markdown("##### 🤖 AI 이슈 분석 결과")
        analysis_container = st.container(height=350, border=True)
        with analysis_container:
            st.markdown(ai_analysis)

    # Manual issue log
    st.markdown("##### ✏️ 이슈 직접 추가")
    with st.expander("이슈 추가", expanded=False):
        ic1, ic2, ic3 = st.columns([1, 1, 1])
        with ic1:
            issue_cat = st.selectbox("분류", ["FDD", "LDD", "Commercial"], key=f"{prefix}_s3_issue_cat")
        with ic2:
            issue_sev = st.selectbox("심각도", ["Critical", "Major", "Minor"], key=f"{prefix}_s3_issue_sev")
        with ic3:
            issue_status = st.selectbox("상태", ["Open", "In Progress", "Resolved"], key=f"{prefix}_s3_issue_status")

        issue_desc = st.text_input("이슈 내용", key=f"{prefix}_s3_issue_desc")
        issue_impact = st.text_input("재무적 영향", key=f"{prefix}_s3_issue_impact")
        issue_response = st.text_input("대응 방안", key=f"{prefix}_s3_issue_response")

        if st.button("이슈 추가", key=f"{prefix}_s3_add_issue"):
            if issue_desc:
                dd_issues.append({
                    "category": issue_cat,
                    "severity": issue_sev,
                    "description": issue_desc,
                    "impact": issue_impact,
                    "response": issue_response,
                    "status": issue_status,
                })
                st.session_state[f"{prefix}_dd_issues"] = dd_issues
                st.success("이슈가 추가되었습니다.")
                st.rerun()

    # Display issue table
    if dd_issues:
        st.markdown("##### 📋 이슈 목록")
        table_md = "| No | 분류 | 심각도 | 이슈 내용 | 재무적 영향 | 대응 방안 | 상태 |\n"
        table_md += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for i, issue in enumerate(dd_issues, 1):
            table_md += (
                f"| {i} | {issue['category']} | {issue['severity']} | "
                f"{issue['description']} | {issue['impact']} | {issue['response']} | {issue['status']} |\n"
            )
        st.markdown(table_md)

    # Template selection for report generation
    st.markdown("---")
    st.markdown("##### 보고서 템플릿 변경")
    template_options = config["template_options"]
    template_option = st.selectbox(
        "Template",
        list(template_options.keys()),
        format_func=lambda x: template_options[x],
        key=f"{prefix}_s3_template",
        label_visibility="collapsed",
    )

    # Navigation
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("<<< 이전 단계", key=f"{prefix}_s3_prev"):
            st.session_state[f"{prefix}_current_step"] = 2
            st.rerun()
    with c3:
        if st.button("다음: 보고서 생성 >>>", type="primary", key=f"{prefix}_s3_next"):
            # Append issues context
            if dd_issues:
                issues_context = "\n\n[실사 발견 이슈]\n"
                for i, issue in enumerate(dd_issues, 1):
                    issues_context += (
                        f"{i}. [{issue['category']}] [{issue['severity']}] {issue['description']} "
                        f"(영향: {issue['impact']}, 대응: {issue['response']})\n"
                    )
                current_fc = st.session_state.get(f"{prefix}_file_context", "")
                st.session_state[f"{prefix}_file_context"] = current_fc + issues_context
            if ai_analysis:
                current_fc = st.session_state.get(f"{prefix}_file_context", "")
                st.session_state[f"{prefix}_file_context"] = current_fc + f"\n\n[AI 이슈 분석]\n{ai_analysis}"

            # Update template
            st.session_state[f"{prefix}_active_mode"] = template_option
            st.session_state[f"{prefix}_dd_active_template"] = template_option
            inputs = st.session_state.get(f"{prefix}_inputs", {})
            inputs["template_option"] = template_option
            inputs["structure_text"] = core_logic.get_default_structure(template_option)
            st.session_state[f"{prefix}_inputs"] = inputs

            st.session_state[f"{prefix}_current_step"] = 4
            st.session_state[f"{prefix}_generation_complete"] = False
            st.rerun()


# ========================================
# Legacy Step 1: Upload (for utility pages)
# ========================================

def _render_step1_upload(prefix, settings, config):
    """Step 1: File upload + template selection (utility pages)."""
    st.markdown(f"### {config['title']}")
    st.caption(config["subtitle"])
    _render_step1_standard(prefix, settings, config)


def _render_step1_standard(prefix, settings, config):
    """Standard upload step (non-RFI pages)."""
    current_project = st.session_state.get("current_project")
    has_rag = current_project and core_rag.is_rag_available() and core_rag.is_indexed(current_project)

    if has_rag:
        rag_count = core_rag.get_indexed_count(current_project)
        st.info(
            f"프로젝트 **{current_project}** (RAG {rag_count}건) 기반으로 생성합니다. "
            f"추가 파일 업로드는 선택사항입니다."
        )

    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("#### 📁 파일 업로드" + (" (선택)" if has_rag else ""))
        uploaded_files = st.file_uploader(
            "분석할 문서를 업로드하세요" if not has_rag else "추가 문서 업로드 (선택사항)",
            accept_multiple_files=True,
            key=f"{prefix}_s1_files",
        )

        selected_project, proj_doc_count = _render_project_doc_selector(prefix, "s1")

        st.markdown("#### 💬 맥락 / 요청사항")
        context_text = st.text_area(
            "Context",
            height=100,
            placeholder="예: 기업명, 투자 배경, 중점 분석 사항 등",
            key=f"{prefix}_s1_context",
            label_visibility="collapsed",
        )

    with col_right:
        template_options = config["template_options"]
        st.markdown("#### 📝 템플릿 선택")
        template_option = st.selectbox(
            "Template",
            list(template_options.keys()),
            format_func=lambda x: template_options[x],
            key=f"{prefix}_s1_template",
            label_visibility="collapsed",
        )

        default_structure = core_logic.get_default_structure(template_option)
        with st.expander("📋 문서 구조 미리보기 / 편집", expanded=False):
            structure_text = st.text_area(
                "Structure",
                value=default_structure,
                height=400,
                key=f"{prefix}_s1_structure",
                label_visibility="collapsed",
            )

        if config.get("show_gen_mode"):
            generation_mode = st.radio(
                "생성 방식",
                ["chained", "single"],
                format_func=lambda x: "📊 단계별 생성 (정확도↑)" if x == "chained" else "🚀 한 번에 생성 (속도↑)",
                index=0,
                horizontal=True,
                key=f"{prefix}_s1_gen_mode",
            )
        else:
            generation_mode = "single"

    # Navigation
    st.markdown("")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button(
            "다음: 보고서 생성 >>>",
            type="primary",
            use_container_width=True,
            key=f"{prefix}_s1_next",
        ):
            if not uploaded_files and not selected_project and not has_rag:
                st.error("파일을 업로드하거나 프로젝트를 선택해주세요.")
            elif not settings.get("api_key"):
                st.error("설정에서 API Key를 먼저 입력해주세요.")
            else:
                st.session_state[f"{prefix}_inputs"] = {
                    "template_option": template_option,
                    "structure_text": structure_text,
                    "uploaded_files": uploaded_files,
                    "context_text": context_text,
                    "selected_saved_files": [],
                    "generation_mode": generation_mode,
                    "generate_btn": True,
                }
                st.session_state[f"{prefix}_active_mode"] = template_option
                _parse_and_cache_files(prefix, settings, uploaded_files, [], template_option, project_name=selected_project)
                st.session_state[f"{prefix}_current_step"] = 2
                st.session_state[f"{prefix}_generation_complete"] = False
                st.rerun()


def _render_project_doc_selector(prefix, key_suffix="s1"):
    """Render project document selector. Returns (project_name, doc_count)."""
    projects = core_rag.list_projects()
    if not projects:
        return None, 0

    current_project = st.session_state.get("current_project")
    project_names = [p["name"] for p in projects]
    options = ["(선택 안함)"] + project_names
    default_idx = 0
    if current_project and current_project in project_names:
        default_idx = project_names.index(current_project) + 1

    selected = st.selectbox(
        "📂 프로젝트 문서 불러오기",
        options,
        index=default_idx,
        key=f"{prefix}_{key_suffix}_project_docs",
    )

    if selected and selected != "(선택 안함)":
        doc_count = core_rag.get_indexed_count(selected)
        if doc_count > 0:
            st.caption(f"'{selected}' 프로젝트의 {doc_count}개 문서가 컨텍스트에 포함됩니다.")
        else:
            st.caption(f"'{selected}' 프로젝트에 저장된 문서가 없습니다.")
        return selected, doc_count
    return None, 0


def _parse_and_cache_files(prefix, settings, uploaded_files, selected_saved, template_option, project_name=None):
    """Parse all files and cache the text in session state.
    If project_name is given, also loads all project documents as base context.
    """
    docai_config = settings.get("docai_config")

    # 프로젝트 문서 로드 (base context)
    project_context = ""
    if project_name:
        project_context = core_rag.load_all_project_docs(project_name)
        if project_context:
            project_context = f"--- [프로젝트 문서: {project_name}] ---\n{project_context}\n\n"

    # 업로드/저장된 파일 파싱
    file_context, _ = core_logic.parse_all_files(
        uploaded_files,
        saved_files=selected_saved,
        read_content=True,
        api_key=settings["api_key"],
        docai_config=docai_config,
        template_option=template_option,
    )
    # 스킵/트렁케이트된 파일 경고
    if "SKIPPED" in file_context[:5000]:
        st.warning("⚠️ 일부 파일이 크기 제한으로 스킵되었습니다. 상세 내용은 생성 결과에 표시됩니다.")
    if "TRUNCATED" in file_context[:5000]:
        st.warning("⚠️ 일부 PDF가 페이지 제한으로 잘려서 처리되었습니다.")

    combined = project_context + file_context
    st.session_state[f"{prefix}_file_context"] = combined
    st.session_state[f"{prefix}_ocr_text"] = combined


# ========================================
# Shared: Generate Step (reusable)
# ========================================

def _render_step_generate(prefix, settings, config, step_number=2, total_steps=4):
    """Reusable generation step with configurable navigation."""
    st.markdown("### 🤖 보고서 생성")

    inputs = st.session_state[f"{prefix}_inputs"]
    file_context = st.session_state[f"{prefix}_file_context"]
    template_opt = inputs.get("template_option", "")

    # If already generated, show the result
    if st.session_state[f"{prefix}_generation_complete"]:
        result_container = st.container(height=500, border=True)
        with result_container:
            st.markdown(st.session_state[f"{prefix}_generated_text"])

        st.markdown("")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("<<< 이전 단계", key=f"{prefix}_sg_prev"):
                st.session_state[f"{prefix}_current_step"] = step_number - 1
                st.rerun()
        with c2:
            if st.button("🔄 다시 생성", key=f"{prefix}_sg_regen"):
                st.session_state[f"{prefix}_generation_complete"] = False
                st.rerun()
        with c3:
            sub1, sub2 = st.columns(2)
            with sub1:
                if st.button("💬 수정하러 가기", key=f"{prefix}_sg_to_refine", type="primary"):
                    st.session_state[f"{prefix}_current_step"] = step_number + 1
                    st.rerun()
            with sub2:
                if st.button("📄 최종 결과", key=f"{prefix}_sg_to_final"):
                    st.session_state[f"{prefix}_current_step"] = total_steps
                    st.rerun()
        return

    # --- Run generation ---
    status_placeholder = st.empty()
    result_container = st.container(height=500, border=True)

    try:
        inputs["use_diagram"] = settings.get("use_diagram", False)
        is_rfi_mode = template_opt == "rfi"
        current_project = st.session_state.get("current_project")
        has_rag = current_project and core_rag.is_rag_available() and core_rag.is_indexed(current_project)

        with status_placeholder.status("🤖 분석 작업을 시작합니다...", expanded=True) as status:
            # RAG context enrichment
            if has_rag and not is_rfi_mode:
                rag_only = not file_context.strip()
                if rag_only:
                    st.write(f"📂 프로젝트 '{current_project}' RAG 데이터로 보고서를 생성합니다.")
                else:
                    st.write(f"🔍 프로젝트 '{current_project}' RAG 검색으로 관련 정보를 보강 중...")
                try:
                    rag_context = core_logic.get_rag_enriched_context(
                        settings["api_key"],
                        inputs.get("structure_text", ""),
                        inputs.get("context_text", ""),
                        current_project,
                        template_opt,
                    )
                    if rag_context:
                        file_context += rag_context
                        st.write("RAG 검색 결과가 컨텍스트에 추가되었습니다.")
                    elif rag_only:
                        st.write("⚠️ RAG 검색 결과가 비어있습니다.")
                except Exception as e:
                    st.write(f"⚠️ RAG 검색 오류: {e}")

            st.write(f"🤖 [{st.session_state[f'{prefix}_active_mode']}] 템플릿으로 생성 중...")

            gen_mode = inputs.get("generation_mode", "single")
            if gen_mode == "chained" and core_chained.is_chained_supported(template_opt):
                part_count = len(core_chained.CHAINED_PARTS.get(template_opt, []))
                st.write(f"🔗 {part_count}단계 분할 생성 모드")
                stream = core_logic.generate_report_stream_chained(
                    settings["api_key"], settings["model_name"],
                    inputs, settings["thinking_level"], file_context,
                )
            else:
                st.write("📝 문서 작성 중 (스트리밍)...")
                stream = core_logic.generate_report_stream(
                    settings["api_key"], settings["model_name"],
                    inputs, settings["thinking_level"], file_context,
                )

            full_response = ""
            with result_container:
                response_placeholder = st.empty()
                for chunk in stream:
                    if chunk.text:
                        full_response += chunk.text
                        response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)

            status.update(label="✅ 작성 완료!", state="complete", expanded=False)

        st.session_state[f"{prefix}_generated_text"] = _strip_preamble(full_response)
        st.session_state[f"{prefix}_generation_complete"] = True
        st.rerun()

    except Exception as e:
        st.error(f"생성 중 오류 발생: {e}")
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            if st.button("<<< 이전 단계", key=f"{prefix}_sg_prev_err"):
                st.session_state[f"{prefix}_current_step"] = step_number - 1
                st.rerun()


# ========================================
# Shared: Refine Step (reusable)
# ========================================

def _render_step_refine(prefix, settings, config, step_number=3, total_steps=4):
    """Reusable chat-based refinement step."""
    st.markdown("### 💬 결과 수정 / 보완")

    col_doc, col_chat = st.columns([6, 4], gap="medium")

    with col_doc:
        st.markdown("#### 📄 현재 결과물")
        is_editing = st.session_state.get(f"{prefix}_sr_editing", False)
        edit_label = "✅ 편집 완료" if is_editing else "✏️ 직접 편집"
        if st.button(edit_label, key=f"{prefix}_sr_edit_toggle"):
            st.session_state[f"{prefix}_sr_editing"] = not is_editing
            st.rerun()

        doc_container = st.container(height=500, border=True)
        with doc_container:
            current_text = st.session_state[f"{prefix}_generated_text"]
            if is_editing:
                new_text = st.text_area(
                    "편집", value=current_text, height=450,
                    label_visibility="collapsed",
                    key=f"{prefix}_sr_edit_area",
                )
                st.session_state[f"{prefix}_generated_text"] = new_text
            else:
                st.markdown(current_text)

    with col_chat:
        st.markdown("#### 💬 수정 요청")

        chat_container = st.container(height=350, border=True)
        with chat_container:
            history = st.session_state[f"{prefix}_chat_history"]
            if not history:
                st.caption("수정/보완 요청을 아래에 입력하세요.")
            for msg in history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        with st.expander("📎 추가 자료 업로드", expanded=False):
            additional_files = st.file_uploader(
                "추가 자료", accept_multiple_files=True,
                key=f"{prefix}_sr_files", label_visibility="collapsed",
            )

        refine_query = st.chat_input(
            "수정/보완 요청을 입력하세요",
            key=f"{prefix}_sr_chat",
        )
        if refine_query:
            if not settings.get("api_key"):
                st.error("API Key가 필요합니다.")
            else:
                st.session_state[f"{prefix}_chat_history"].append(
                    {"role": "user", "content": refine_query}
                )
                additional_context = ""
                if additional_files:
                    for f in additional_files:
                        additional_context += utils.parse_uploaded_file(
                            f, api_key=settings["api_key"],
                            docai_config=settings.get("docai_config"),
                        )
                with st.spinner("수정 중..."):
                    try:
                        refined = core_logic.refine_report_with_context(
                            settings["api_key"],
                            settings["model_name"],
                            st.session_state[f"{prefix}_generated_text"],
                            st.session_state[f"{prefix}_chat_history"],
                            refine_query,
                            additional_context,
                        )
                        st.session_state[f"{prefix}_generated_text"] = _strip_preamble(refined)
                        st.session_state[f"{prefix}_chat_history"].append(
                            {"role": "assistant", "content": "수정 사항을 반영했습니다."}
                        )
                    except Exception as e:
                        st.session_state[f"{prefix}_chat_history"].append(
                            {"role": "assistant", "content": f"오류 발생: {e}"}
                        )
                st.rerun()

    # Navigation
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("<<< 이전 단계", key=f"{prefix}_sr_prev"):
            st.session_state[f"{prefix}_current_step"] = step_number - 1
            st.rerun()
    with c3:
        if st.button("다음: 최종 결과 확인 >>>", type="primary", key=f"{prefix}_sr_next"):
            st.session_state[f"{prefix}_current_step"] = step_number + 1
            st.rerun()


# ========================================
# Shared: Output Step (reusable)
# ========================================

def _render_step_output(prefix, settings, config, step_number=4, total_steps=4):
    """Reusable final output step with downloads."""
    st.markdown("### 📄 최종 결과")

    current_text = st.session_state[f"{prefix}_generated_text"]
    current_mode = st.session_state.get(f"{prefix}_active_mode", "")

    # Copy / Edit buttons
    c_head1, c_head2, c_head3 = st.columns([4, 1, 1])
    with c_head2:
        is_editing = st.session_state.get(f"{prefix}_so_editing", False)
        edit_label = "✅ 완료" if is_editing else "✏️ 편집"
        if st.button(edit_label, key=f"{prefix}_so_edit_toggle", use_container_width=True):
            st.session_state[f"{prefix}_so_editing"] = not is_editing
            st.rerun()
    with c_head3:
        if st.button("📋 복사", key=f"{prefix}_so_copy", use_container_width=True):
            st.session_state[f"{prefix}_so_show_copy"] = True
            st.toast("아래 코드를 클릭하여 복사하세요.", icon="📋")

    # Result display
    result_container = st.container(height=600, border=True)
    with result_container:
        if st.session_state.get(f"{prefix}_so_show_copy"):
            st.code(current_text, language="markdown")
            st.session_state[f"{prefix}_so_show_copy"] = False

        if st.session_state.get(f"{prefix}_so_editing"):
            new_text = st.text_area(
                "편집", value=current_text, height=550,
                label_visibility="collapsed", key=f"{prefix}_so_edit_area",
            )
            st.session_state[f"{prefix}_generated_text"] = new_text
        else:
            st.markdown(current_text)

    # Downloads
    st.markdown("---")
    inputs = st.session_state.get(f"{prefix}_inputs", {})
    fname = utils.generate_filename(inputs.get("uploaded_files"), current_mode)

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        if current_mode == "rfi":
            st.download_button(
                "📥 RFI 엑셀 다운로드",
                utils.create_excel(current_text),
                fname.replace(".docx", ".xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key=f"{prefix}_so_dl_rfi",
            )
        else:
            st.download_button(
                "📄 Word 다운로드",
                utils.create_docx(current_text),
                fname,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True, key=f"{prefix}_so_dl_word",
            )

    with col_d2:
        btn_type = "primary" if current_mode in ["presentation", "paper_review"] else "secondary"
        st.download_button(
            "📊 PPT 다운로드",
            utils_ppt.create_ppt(current_text),
            fname.replace(".docx", ".pptx"),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True, type=btn_type, key=f"{prefix}_so_dl_ppt",
        )

    with col_d3:
        ocr_text = st.session_state.get(f"{prefix}_ocr_text", "")
        if ocr_text and current_mode != "rfi":
            st.download_button(
                "📝 OCR 텍스트 다운로드",
                ocr_text,
                fname.replace(".docx", "_ocr.txt"),
                "text/plain",
                use_container_width=True, key=f"{prefix}_so_dl_ocr",
            )

    # PPT conversion (for non-PPT templates)
    if current_mode not in ["presentation", "paper_review", "rfi"]:
        st.markdown("")
        if st.button(
            "📊 이 내용으로 발표자료(PPT) 생성하기",
            use_container_width=True, key=f"{prefix}_so_ppt_convert",
        ):
            if not settings.get("api_key"):
                st.error("API Key 필요")
            else:
                try:
                    ppt_inputs = inputs.copy()
                    ppt_inputs["template_option"] = "presentation"
                    ppt_inputs["structure_text"] = core_logic.get_default_structure("presentation")

                    with st.status("📊 PPT 스타일로 변환 중...", expanded=True) as ppt_status:
                        file_context = st.session_state.get(f"{prefix}_file_context", "")
                        stream = core_logic.generate_report_stream(
                            settings["api_key"], settings["model_name"],
                            ppt_inputs, settings["thinking_level"], file_context,
                        )
                        full_response = ""
                        for chunk in stream:
                            if chunk.text:
                                full_response += chunk.text
                        ppt_status.update(label="✅ PPT 변환 완료!", state="complete", expanded=False)

                    st.session_state[f"{prefix}_generated_text"] = full_response
                    st.session_state[f"{prefix}_active_mode"] = "presentation"
                    st.rerun()
                except Exception as e:
                    st.error(f"PPT 변환 오류: {e}")

    # Navigation
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("<<< 수정하러 돌아가기", key=f"{prefix}_so_to_refine"):
            st.session_state[f"{prefix}_current_step"] = step_number - 1
            st.rerun()
    with c3:
        if st.button("🔄 처음부터 다시 시작", key=f"{prefix}_so_restart"):
            _reset_workflow(prefix)
            st.rerun()

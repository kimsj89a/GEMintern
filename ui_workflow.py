"""
Step-based workflow UI for analysis pages.
4-step flow: Upload → Generate → Refine → Final Output
"""

import streamlit as st
import streamlit.components.v1 as components
import utils
import utils_ppt
import core_logic
import core_chained
import core_rag

# ========================================
# Page configurations
# ========================================

def _strip_preamble(text):
    """Remove AI preamble text before the first markdown heading.
    AI sometimes outputs explanation like '~를 분석하여 보고서를 작성합니다' before the report.
    This strips that and returns only the report body starting from the first # heading.
    """
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


PAGE_CONFIGS = {
    "📋 초기검토": {
        "key_prefix": "init",
        "title": "📋 초기검토 (Quick Memo)",
        "subtitle": "약식 투자검토보고서를 빠르게 작성합니다.",
        "default_template": "simple_review",
        "template_options": {
            "simple_review": "1. 약식 투자검토 (요약)",
            "investment": "2. 투자심사보고서 (표준)",
            "custom": "3. 자유 구조화 (요약보고서)",
        },
        "show_gen_mode": True,
        "page_type": "standard",
    },
    "📊 예비실사": {
        "key_prefix": "prelim",
        "title": "📊 예비실사 (Preliminary DD)",
        "subtitle": "투자심사보고서, 사후관리보고서 등을 작성합니다.",
        "default_template": "investment",
        "template_options": {
            "investment": "1. 투자심사보고서 (표준)",
            "im": "2. IM (투자제안서)",
            "management": "3. 사후관리보고서",
            "free_summary": "4. 자유 구조화 (요약)",
            "custom": "5. 자유 구조화 (요약보고서)",
        },
        "show_gen_mode": True,
        "page_type": "standard",
    },
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
    "🔍 정밀실사": {
        "key_prefix": "dd",
        "title": "🔍 정밀실사 (Detailed DD)",
        "subtitle": "RFI (자료요청목록) 작성 - FDD/LDD 유형별 지원",
        "default_template": "rfi",
        "template_options": {},
        "show_gen_mode": False,
        "page_type": "rfi",
    },
}


# ========================================
# Main entry point
# ========================================

def render_step_workflow(settings, selected_page):
    """Main entry for step-based analysis workflow."""
    config = PAGE_CONFIGS.get(selected_page)
    if not config:
        st.error(f"Unknown page: {selected_page}")
        return

    prefix = config["key_prefix"]
    _init_workflow_state(prefix, config)
    _render_step_indicator(prefix)

    current_step = st.session_state[f"{prefix}_current_step"]

    if current_step == 1:
        _render_step1_upload(prefix, settings, config)
    elif current_step == 2:
        _render_step2_generate(prefix, settings, config)
    elif current_step == 3:
        _render_step3_refine(prefix, settings, config)
    elif current_step == 4:
        _render_step4_output(prefix, settings, config)


# ========================================
# State management
# ========================================

def _init_workflow_state(prefix, config):
    """Initialize session state keys for this workflow."""
    defaults = {
        f"{prefix}_current_step": 1,
        f"{prefix}_inputs": {},
        f"{prefix}_generated_text": "",
        f"{prefix}_file_context": "",
        f"{prefix}_chat_history": [],
        f"{prefix}_generation_complete": False,
        f"{prefix}_ocr_text": "",
        f"{prefix}_rag_result": None,
        f"{prefix}_active_mode": config.get("default_template", ""),
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _reset_workflow(prefix):
    """Clear all state for this workflow prefix."""
    keys_to_clear = [k for k in list(st.session_state.keys()) if k.startswith(f"{prefix}_")]
    for k in keys_to_clear:
        del st.session_state[k]


# ========================================
# Step indicator
# ========================================

def _render_step_indicator(prefix):
    """Render horizontal step progress bar."""
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
            if i < current:
                st.markdown(
                    f"<div style='text-align:center;padding:6px;background:#d4edda;"
                    f"border-radius:8px;border:2px solid #28a745;'>"
                    f"<span style='font-size:1.1em;'>✅</span><br>"
                    f"<small style='color:#155724;'>{label}</small></div>",
                    unsafe_allow_html=True,
                )
            elif i == current:
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
    st.markdown("---")


# ========================================
# Step 1: Data Upload
# ========================================

def _render_step1_upload(prefix, settings, config):
    """Step 1: File upload + template selection."""
    st.markdown(f"### {config['title']}")
    st.caption(config["subtitle"])

    if config.get("page_type") == "rfi":
        _render_step1_rfi(prefix, settings, config)
    else:
        _render_step1_standard(prefix, settings, config)


def _render_step1_standard(prefix, settings, config):
    """Standard upload step (non-RFI pages)."""
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("#### 📁 파일 업로드")
        uploaded_files = st.file_uploader(
            "분석할 문서를 업로드하세요",
            accept_multiple_files=True,
            key=f"{prefix}_s1_files",
        )

        saved_docs = utils.list_saved_docs()
        selected_saved = []
        if saved_docs:
            selected_saved = st.multiselect(
                "📚 저장된 문서에서 선택",
                saved_docs,
                key=f"{prefix}_s1_saved",
            )

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
            if not uploaded_files and not selected_saved:
                st.error("파일을 업로드하거나 저장된 문서를 선택해주세요.")
            elif not settings.get("api_key"):
                st.error("설정에서 API Key를 먼저 입력해주세요.")
            else:
                # Cache inputs
                st.session_state[f"{prefix}_inputs"] = {
                    "template_option": template_option,
                    "structure_text": structure_text,
                    "uploaded_files": uploaded_files,
                    "context_text": context_text,
                    "selected_saved_files": selected_saved,
                    "generation_mode": generation_mode,
                    "generate_btn": True,
                }
                st.session_state[f"{prefix}_active_mode"] = template_option
                # Parse files now (before file_uploader disappears)
                _parse_and_cache_files(prefix, settings, uploaded_files, selected_saved, template_option)
                st.session_state[f"{prefix}_current_step"] = 2
                st.session_state[f"{prefix}_generation_complete"] = False
                st.rerun()


def _render_step1_rfi(prefix, settings, config):
    """RFI-specific upload step (정밀실사)."""
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("#### 📥 데이터 입력")

        st.caption("실사 유형 선택")
        dd_type = st.radio(
            "실사 유형",
            ["general", "fdd", "ldd"],
            format_func=lambda x: {
                "general": "📋 일반 RFI (종합)",
                "fdd": "📊 FDD (재무실사)",
                "ldd": "⚖️ LDD (법률실사)",
            }[x],
            horizontal=True,
            key=f"{prefix}_s1_dd_type",
        )

        st.caption("1. RFI 엑셀 파일 (Basis)")
        uploaded_rfi_file = st.file_uploader(
            "RFI 엑셀", type=["xlsx", "xls", "csv"],
            key=f"{prefix}_s1_rfi_basis", label_visibility="collapsed",
        )
        rfi_existing = ""
        if uploaded_rfi_file:
            with st.spinner("RFI 파싱..."):
                rfi_existing = utils.parse_uploaded_file(uploaded_rfi_file)
            st.success("RFI 로드 완료")

        st.caption("2. 분석할 문서")
        uploaded_files = st.file_uploader(
            "분석 문서", accept_multiple_files=True,
            key=f"{prefix}_s1_files", label_visibility="collapsed",
        )

        saved_docs = utils.list_saved_docs()
        selected_saved = []
        if saved_docs:
            selected_saved = st.multiselect(
                "📚 저장된 문서", saved_docs,
                key=f"{prefix}_s1_saved", label_visibility="collapsed",
            )

        st.caption("3. 추가 질문 및 확인 사항")
        context_text = st.text_area(
            "Context", height=120, label_visibility="collapsed",
            placeholder="예: 재고 관련 이슈 확인 필요...",
            key=f"{prefix}_s1_context",
        )

        dd_context_prefix = {
            "general": "",
            "fdd": "[실사 유형: FDD (Financial Due Diligence)]\n재무실사 관점에서 재무제표, 세무, 운전자본, 순차입금, 정상화 EBITDA, 내부거래, 우발부채 등에 중점을 두어 자료를 요청하십시오.\n\n",
            "ldd": "[실사 유형: LDD (Legal Due Diligence)]\n법률실사 관점에서 계약서, 소송/분쟁, 지적재산권, 인허가, 규제 준수, 지배구조, 주주간계약 등에 중점을 두어 자료를 요청하십시오.\n\n",
        }
        final_context = dd_context_prefix.get(dd_type, "") + context_text

    with col_right:
        from ui_input import HTML_SCANNER
        st.markdown("#### 📂 수령 자료 스캔 (Folder Scan)")
        components.html(HTML_SCANNER, height=280)
        st.caption("파일 목록 붙여넣기 (Ctrl+V)")
        rfi_file_list_input = st.text_area(
            "File List", height=300, placeholder="- 폴더명/파일명.pdf...",
            key=f"{prefix}_s1_filelist", label_visibility="collapsed",
        )

    # Navigation
    st.markdown("")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button(
            "다음: RFI 생성 >>>",
            type="primary",
            use_container_width=True,
            key=f"{prefix}_s1_next",
        ):
            if not settings.get("api_key"):
                st.error("설정에서 API Key를 먼저 입력해주세요.")
            else:
                st.session_state[f"{prefix}_inputs"] = {
                    "template_option": "rfi",
                    "structure_text": "",
                    "uploaded_files": uploaded_files,
                    "rfi_file_list_input": rfi_file_list_input,
                    "context_text": final_context,
                    "rfi_existing": rfi_existing,
                    "generate_btn": True,
                    "generation_mode": "single",
                    "selected_saved_files": selected_saved,
                }
                st.session_state[f"{prefix}_active_mode"] = "rfi"
                # Parse files
                if uploaded_files or selected_saved:
                    _parse_and_cache_files(prefix, settings, uploaded_files, selected_saved, "rfi")
                else:
                    st.session_state[f"{prefix}_file_context"] = "(RFI 모드: 내용은 읽지 않음)"
                st.session_state[f"{prefix}_current_step"] = 2
                st.session_state[f"{prefix}_generation_complete"] = False
                st.rerun()


def _parse_and_cache_files(prefix, settings, uploaded_files, selected_saved, template_option):
    """Parse all files and cache the text in session state."""
    use_rag = settings.get("use_rag", False) and core_rag.is_rag_available()
    docai_config = settings.get("docai_config")

    file_context, _, rag_result = core_logic.parse_all_files(
        uploaded_files,
        saved_files=selected_saved,
        read_content=True,
        api_key=settings["api_key"],
        docai_config=docai_config,
        template_option=template_option,
        use_rag=use_rag,
    )

    st.session_state[f"{prefix}_file_context"] = file_context
    st.session_state[f"{prefix}_ocr_text"] = file_context
    st.session_state[f"{prefix}_rag_result"] = rag_result


# ========================================
# Step 2: Generate
# ========================================

def _render_step2_generate(prefix, settings, config):
    """Step 2: Auto-generate report with streaming."""
    st.markdown(f"### 🤖 보고서 생성")

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
            if st.button("<<< 이전 단계", key=f"{prefix}_s2_prev"):
                st.session_state[f"{prefix}_current_step"] = 1
                st.rerun()
        with c2:
            if st.button("🔄 다시 생성", key=f"{prefix}_s2_regen"):
                st.session_state[f"{prefix}_generation_complete"] = False
                st.rerun()
        with c3:
            sub1, sub2 = st.columns(2)
            with sub1:
                if st.button("💬 수정하러 가기", key=f"{prefix}_s2_to_refine", type="primary"):
                    st.session_state[f"{prefix}_current_step"] = 3
                    st.rerun()
            with sub2:
                if st.button("📄 최종 결과", key=f"{prefix}_s2_to_final"):
                    st.session_state[f"{prefix}_current_step"] = 4
                    st.rerun()
        return

    # --- Run generation ---
    status_placeholder = st.empty()
    result_container = st.container(height=500, border=True)

    try:
        inputs["use_diagram"] = settings.get("use_diagram", False)
        is_rfi_mode = template_opt == "rfi"
        use_rag = settings.get("use_rag", False) and core_rag.is_rag_available()

        with status_placeholder.status("🤖 분석 작업을 시작합니다...", expanded=True) as status:
            # Show RAG indexing results
            rag_result = st.session_state.get(f"{prefix}_rag_result")
            if use_rag and rag_result:
                if rag_result.get("success"):
                    indexed = rag_result.get("indexed", [])
                    skipped = rag_result.get("skipped", [])
                    if indexed:
                        st.write(f"🔍 RAG 인덱싱 완료: {len(indexed)}개 문서")
                    if skipped:
                        st.write(f"🔍 RAG 이미 인덱싱됨: {len(skipped)}개 문서 (스킵)")
                else:
                    st.write(f"⚠️ RAG 인덱싱 오류: {rag_result.get('error', 'unknown')}")

            # RAG context enrichment
            if use_rag and core_rag.is_indexed() and not is_rfi_mode:
                st.write("🔍 RAG 검색으로 관련 정보를 보강 중...")
                try:
                    rag_context = core_logic.get_rag_enriched_context(
                        settings["api_key"],
                        inputs.get("structure_text", ""),
                        inputs.get("context_text", ""),
                        template_opt,
                    )
                    if rag_context:
                        file_context += rag_context
                        st.write("RAG 검색 결과가 컨텍스트에 추가되었습니다.")
                except Exception as e:
                    st.write(f"⚠️ RAG 검색 오류 (생성은 계속됩니다): {e}")

            st.write(f"🤖 [{st.session_state[f'{prefix}_active_mode']}] 템플릿으로 생성 중...")

            # Choose generation mode
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

            # Stream output
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
            if st.button("<<< 이전 단계", key=f"{prefix}_s2_prev_err"):
                st.session_state[f"{prefix}_current_step"] = 1
                st.rerun()


# ========================================
# Step 3: Refine (Chat-based)
# ========================================

def _render_step3_refine(prefix, settings, config):
    """Step 3: Chat-based refinement with side-by-side view."""
    st.markdown("### 💬 결과 수정 / 보완")

    col_doc, col_chat = st.columns([6, 4], gap="medium")

    with col_doc:
        st.markdown("#### 📄 현재 결과물")
        is_editing = st.session_state.get(f"{prefix}_s3_editing", False)
        edit_label = "✅ 편집 완료" if is_editing else "✏️ 직접 편집"
        if st.button(edit_label, key=f"{prefix}_s3_edit_toggle"):
            st.session_state[f"{prefix}_s3_editing"] = not is_editing
            st.rerun()

        doc_container = st.container(height=500, border=True)
        with doc_container:
            current_text = st.session_state[f"{prefix}_generated_text"]
            if is_editing:
                new_text = st.text_area(
                    "편집", value=current_text, height=450,
                    label_visibility="collapsed",
                    key=f"{prefix}_s3_edit_area",
                )
                st.session_state[f"{prefix}_generated_text"] = new_text
            else:
                st.markdown(current_text)

    with col_chat:
        st.markdown("#### 💬 수정 요청")

        # Chat history display
        chat_container = st.container(height=350, border=True)
        with chat_container:
            history = st.session_state[f"{prefix}_chat_history"]
            if not history:
                st.caption("수정/보완 요청을 아래에 입력하세요.")
            for msg in history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # Additional file upload
        with st.expander("📎 추가 자료 업로드", expanded=False):
            additional_files = st.file_uploader(
                "추가 자료", accept_multiple_files=True,
                key=f"{prefix}_s3_files", label_visibility="collapsed",
            )

        # Chat input
        refine_query = st.chat_input(
            "수정/보완 요청을 입력하세요",
            key=f"{prefix}_s3_chat",
        )
        if refine_query:
            if not settings.get("api_key"):
                st.error("API Key가 필요합니다.")
            else:
                # Add user message
                st.session_state[f"{prefix}_chat_history"].append(
                    {"role": "user", "content": refine_query}
                )

                # Parse additional files if any
                additional_context = ""
                if additional_files:
                    for f in additional_files:
                        additional_context += utils.parse_uploaded_file(
                            f, api_key=settings["api_key"],
                            docai_config=settings.get("docai_config"),
                        )

                # Call refinement
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
        if st.button("<<< 이전 단계", key=f"{prefix}_s3_prev"):
            st.session_state[f"{prefix}_current_step"] = 2
            st.rerun()
    with c3:
        if st.button("다음: 최종 결과 확인 >>>", type="primary", key=f"{prefix}_s3_next"):
            st.session_state[f"{prefix}_current_step"] = 4
            st.rerun()


# ========================================
# Step 4: Final Output
# ========================================

def _render_step4_output(prefix, settings, config):
    """Step 4: Final result display + downloads."""
    st.markdown("### 📄 최종 결과")

    current_text = st.session_state[f"{prefix}_generated_text"]
    current_mode = st.session_state.get(f"{prefix}_active_mode", "")

    # Copy / Edit buttons
    c_head1, c_head2, c_head3 = st.columns([4, 1, 1])
    with c_head2:
        is_editing = st.session_state.get(f"{prefix}_s4_editing", False)
        edit_label = "✅ 완료" if is_editing else "✏️ 편집"
        if st.button(edit_label, key=f"{prefix}_s4_edit_toggle", use_container_width=True):
            st.session_state[f"{prefix}_s4_editing"] = not is_editing
            st.rerun()
    with c_head3:
        if st.button("📋 복사", key=f"{prefix}_s4_copy", use_container_width=True):
            st.session_state[f"{prefix}_s4_show_copy"] = True
            st.toast("아래 코드를 클릭하여 복사하세요.", icon="📋")

    # Result display
    result_container = st.container(height=600, border=True)
    with result_container:
        if st.session_state.get(f"{prefix}_s4_show_copy"):
            st.code(current_text, language="markdown")
            st.session_state[f"{prefix}_s4_show_copy"] = False

        if st.session_state.get(f"{prefix}_s4_editing"):
            new_text = st.text_area(
                "편집", value=current_text, height=550,
                label_visibility="collapsed", key=f"{prefix}_s4_edit_area",
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
                use_container_width=True, key=f"{prefix}_s4_dl_rfi",
            )
        else:
            st.download_button(
                "📄 Word 다운로드",
                utils.create_docx(current_text),
                fname,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True, key=f"{prefix}_s4_dl_word",
            )

    with col_d2:
        btn_type = "primary" if current_mode in ["presentation", "paper_review"] else "secondary"
        st.download_button(
            "📊 PPT 다운로드",
            utils_ppt.create_ppt(current_text),
            fname.replace(".docx", ".pptx"),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True, type=btn_type, key=f"{prefix}_s4_dl_ppt",
        )

    with col_d3:
        ocr_text = st.session_state.get(f"{prefix}_ocr_text", "")
        if ocr_text and current_mode != "rfi":
            st.download_button(
                "📝 OCR 텍스트 다운로드",
                ocr_text,
                fname.replace(".docx", "_ocr.txt"),
                "text/plain",
                use_container_width=True, key=f"{prefix}_s4_dl_ocr",
            )

    # PPT conversion (for non-PPT templates)
    if current_mode not in ["presentation", "paper_review", "rfi"]:
        st.markdown("")
        if st.button(
            "📊 이 내용으로 발표자료(PPT) 생성하기",
            use_container_width=True, key=f"{prefix}_s4_ppt_convert",
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
        if st.button("<<< 수정하러 돌아가기", key=f"{prefix}_s4_to_refine"):
            st.session_state[f"{prefix}_current_step"] = 3
            st.rerun()
    with c3:
        if st.button("🔄 처음부터 다시 시작", key=f"{prefix}_s4_restart"):
            _reset_workflow(prefix)
            st.rerun()

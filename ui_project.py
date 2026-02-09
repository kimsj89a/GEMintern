"""
Project Hub UI for project-based RAG management.
Users create projects, upload documents, and build RAG indexes before analysis.
"""

import streamlit as st
import utils
import core_rag
import core_logic


def render_project_hub(settings):
    """Main entry point for the Project Hub page."""
    st.markdown("""
        <div style='display:flex;align-items:center;gap:10px;margin-bottom:5px;'>
            <h2 style='margin:0;'>Project Hub</h2>
        </div>
        <p style='color:gray;margin-top:0;'>프로젝트별 RAG 인덱스를 관리합니다. 분석 전에 프로젝트를 생성하고 문서를 인덱싱하세요.</p>
    """, unsafe_allow_html=True)

    if not core_rag.is_rag_available():
        st.warning("lightrag-hku가 설치되지 않았습니다. RAG 기능을 사용하려면 `pip install lightrag-hku`를 실행하세요.")
        return

    col_list, col_detail = st.columns([2, 3], gap="medium")

    with col_list:
        _render_project_list(settings)

    with col_detail:
        _render_project_detail(settings)


def _render_project_list(settings):
    """Left column: project creation, selection, deletion."""
    st.markdown("#### 프로젝트 목록")

    # Create new project
    with st.form("create_project_form", clear_on_submit=True):
        new_name = st.text_input(
            "새 프로젝트명",
            placeholder="예: 히든스페이스_투자검토",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("+ 프로젝트 생성", use_container_width=True)
        if submitted and new_name:
            result = core_rag.create_project(new_name)
            if result["success"]:
                st.session_state["current_project"] = result["project"]["name"]
                st.toast(f"프로젝트 '{result['project']['name']}' 생성 완료")
                st.rerun()
            else:
                st.error(result["error"])

    st.markdown("---")

    # List existing projects
    projects = core_rag.list_projects()
    if not projects:
        st.info("프로젝트가 없습니다. 위에서 새 프로젝트를 생성하세요.")
        return

    current = st.session_state.get("current_project", "")

    for p in projects:
        name = p["name"]
        doc_count = p.get("doc_count", 0)
        is_active = name == current

        col_btn, col_del = st.columns([5, 1])
        with col_btn:
            label = f"{'> ' if is_active else '  '}{name} ({doc_count}건)"
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"proj_select_{name}", use_container_width=True, type=btn_type):
                st.session_state["current_project"] = name
                st.rerun()
        with col_del:
            if st.button("X", key=f"proj_del_{name}"):
                st.session_state[f"_confirm_del_{name}"] = True
                st.rerun()

        # Delete confirmation
        if st.session_state.get(f"_confirm_del_{name}"):
            st.warning(f"'{name}' 프로젝트를 삭제하시겠습니까?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("삭제", key=f"proj_del_confirm_{name}", type="primary"):
                    core_rag.delete_project(name)
                    if current == name:
                        st.session_state.pop("current_project", None)
                    st.session_state.pop(f"_confirm_del_{name}", None)
                    st.toast(f"'{name}' 삭제 완료")
                    st.rerun()
            with c2:
                if st.button("취소", key=f"proj_del_cancel_{name}"):
                    st.session_state.pop(f"_confirm_del_{name}", None)
                    st.rerun()


def _render_project_detail(settings):
    """Right column: project detail, file upload, RAG indexing."""
    current = st.session_state.get("current_project", "")
    if not current:
        st.info("왼쪽에서 프로젝트를 선택하거나 새로 생성하세요.")
        return

    info = core_rag.get_project_info(current)
    if not info:
        st.error(f"프로젝트 '{current}'를 찾을 수 없습니다.")
        return

    doc_count = info.get("doc_count", 0)
    indexed_docs = info.get("indexed_docs", [])

    st.markdown(f"#### {current}")

    if doc_count > 0:
        st.success(f"RAG: {doc_count}개 문서 인덱싱됨")
        with st.expander("인덱싱된 문서 목록", expanded=False):
            for d in indexed_docs:
                st.text(f"  - {d}")
    else:
        st.info("인덱싱된 문서가 없습니다. 아래에서 문서를 업로드하고 RAG 인덱스를 빌드하세요.")

    st.markdown("---")

    # File upload section
    st.markdown("##### 문서 업로드 및 인덱싱")
    uploaded_files = st.file_uploader(
        "파일 업로드",
        accept_multiple_files=True,
        key=f"proj_upload_{current}",
        label_visibility="collapsed",
    )

    # Saved documents selection
    saved_docs = utils.list_saved_docs()
    selected_saved = []
    if saved_docs:
        selected_saved = st.multiselect(
            "저장된 문서에서 선택",
            saved_docs,
            key=f"proj_saved_{current}",
        )

    # Build RAG button
    has_files = bool(uploaded_files) or bool(selected_saved)
    if st.button(
        "RAG 인덱스 빌드",
        use_container_width=True,
        type="primary",
        disabled=not has_files,
        key=f"proj_build_{current}",
    ):
        api_key = settings.get("api_key", "")
        if not api_key:
            st.error("설정에서 API Key를 먼저 입력해주세요.")
        else:
            _build_rag_index(settings, current, uploaded_files, selected_saved)

    st.markdown("---")

    # Management buttons
    c1, c2 = st.columns(2)
    with c1:
        if saved_docs and st.button("저장된 문서 전체 인덱싱", use_container_width=True, key=f"proj_index_all_{current}"):
            api_key = settings.get("api_key", "")
            if not api_key:
                st.error("API Key를 먼저 입력해주세요.")
            else:
                with st.spinner("저장된 문서 전체 인덱싱 중..."):
                    result = core_rag.index_saved_documents(api_key, current)
                    if result.get("success"):
                        indexed = result.get("indexed", [])
                        st.success(f"{len(indexed)}개 문서 인덱싱 완료")
                        st.rerun()
                    else:
                        st.error(f"오류: {result.get('error', '')}")

    with c2:
        if doc_count > 0 and st.button("인덱스 초기화", use_container_width=True, key=f"proj_clear_{current}"):
            core_rag.clear_rag_index(current)
            st.toast("인덱스가 초기화되었습니다.")
            st.rerun()


def _build_rag_index(settings, project_name, uploaded_files, selected_saved):
    """Parse files and build RAG index with progress bar."""
    api_key = settings["api_key"]
    docai_config = settings.get("docai_config")
    texts = {}

    progress = st.progress(0, text="파일 파싱 중...")
    total = len(uploaded_files or []) + len(selected_saved or [])
    done = 0

    # Parse uploaded files
    skipped_files = []
    if uploaded_files:
        for f in uploaded_files:
            progress.progress(done / max(total, 1), text=f"파싱 중: {f.name}")
            try:
                parsed = utils.parse_uploaded_file(
                    f,
                    api_key=api_key,
                    docai_config=docai_config,
                )
                if parsed and "SKIPPED" in parsed[:100]:
                    skipped_files.append(f.name)
                elif parsed and len(parsed.strip()) > 50:
                    texts[f.name] = parsed
                    utils.save_to_local_storage(f.name, parsed)
            except Exception as e:
                skipped_files.append(f"{f.name} (오류: {e})")
            done += 1

    # Load saved documents
    if selected_saved:
        for fname in selected_saved:
            progress.progress(done / max(total, 1), text=f"로딩 중: {fname}")
            content = utils.load_saved_doc(fname)
            if content and len(content.strip()) > 50:
                texts[fname] = content
            done += 1

    if not texts:
        progress.empty()
        st.warning("인덱싱할 문서가 없습니다 (내용이 너무 짧음).")
        return

    # Index into RAG
    progress.progress(0.8, text="RAG 인덱싱 중...")
    try:
        result = core_rag.index_texts(api_key, texts, project_name)
        progress.progress(1.0, text="완료!")

        if result.get("success") or result.get("indexed"):
            indexed = result.get("indexed", [])
            skipped = result.get("skipped", [])
            msg_parts = []
            if indexed:
                msg_parts.append(f"{len(indexed)}개 신규 인덱싱")
            if skipped:
                msg_parts.append(f"{len(skipped)}개 이미 인덱싱됨 (스킵)")
            st.success(" / ".join(msg_parts) if msg_parts else "인덱싱 완료")
        else:
            st.error(f"인덱싱 오류: {result.get('error', 'unknown')}")

        if result.get("errors"):
            for err in result["errors"]:
                st.warning(f"오류 - {err['name']}: {err['error']}")

        if skipped_files:
            st.warning(f"⚠️ {len(skipped_files)}개 파일 스킵됨: {', '.join(skipped_files)}")

        st.rerun()

    except Exception as e:
        progress.empty()
        st.error(f"RAG 인덱싱 실패: {e}")

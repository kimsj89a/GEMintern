"""
Project Hub UI for project-based document management.
Users create projects, upload documents (parsed to markdown), and use them across all workflow steps.
"""

import streamlit as st
import utils
import core_rag
import core_logic
import ui_onedrive


def render_project_hub(settings):
    """Main entry point for the Project Hub page."""
    st.markdown("""
        <div style='display:flex;align-items:center;gap:10px;margin-bottom:5px;'>
            <h2 style='margin:0;'>Project Hub</h2>
        </div>
        <p style='color:gray;margin-top:0;'>프로젝트별 문서를 관리합니다. 프로젝트를 생성하고 문서를 업로드하면, 이후 모든 분석 단계에서 활용됩니다.</p>
    """, unsafe_allow_html=True)

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
    """Right column: project detail, file upload, document storage."""
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
        st.success(f"{doc_count}개 문서 저장됨")

        # 문서 검색 필터 (5건 이상)
        if doc_count > 5:
            doc_filter = st.text_input(
                "문서 검색", placeholder="파일명으로 검색...",
                key=f"doc_filter_{current}",
            )
        else:
            doc_filter = ""
        filtered_docs = [d for d in indexed_docs if doc_filter.lower() in d.lower()] if doc_filter else indexed_docs

        with st.expander(f"저장된 문서 목록 ({len(filtered_docs)}/{doc_count}건)", expanded=False):
            for d in filtered_docs:
                col_doc, col_trash = st.columns([5, 1])
                with col_doc:
                    st.text(f"  {d}")
                with col_trash:
                    if st.button("🗑️", key=f"trash_{current}_{d}", help="휴지통으로 이동"):
                        result = core_rag.trash_document(current, d)
                        if result["success"]:
                            st.toast(f"'{d}' 휴지통으로 이동")
                            st.rerun()
                        else:
                            st.error(result["error"])
    else:
        st.info("저장된 문서가 없습니다. 아래에서 문서를 업로드하세요.")

    # Trash section
    trash_items = core_rag.list_trash(current)
    if trash_items:
        with st.expander(f"🗑️ 휴지통 ({len(trash_items)}건)", expanded=False):
            for t in trash_items:
                col_name, col_restore, col_delete = st.columns([4, 1, 1])
                with col_name:
                    st.text(f"  {t}")
                with col_restore:
                    if st.button("♻️", key=f"restore_{current}_{t}", help="복구"):
                        result = core_rag.restore_from_trash(current, t)
                        if result["success"]:
                            st.toast(f"'{t}' 복구 완료")
                            st.rerun()
                with col_delete:
                    if st.button("❌", key=f"permdel_{current}_{t}", help="영구 삭제"):
                        core_rag.permanently_delete_from_trash(current, t)
                        st.toast(f"'{t}' 영구 삭제")
                        st.rerun()
            st.markdown("")
            if st.button("🗑️ 휴지통 비우기", key=f"empty_trash_{current}", use_container_width=True):
                core_rag.empty_trash(current)
                st.toast("휴지통 비움")
                st.rerun()

    st.markdown("---")

    # File upload section
    st.markdown("##### 문서 업로드 및 저장")
    st.caption("업로드된 파일은 마크다운으로 변환되어 프로젝트에 저장됩니다. 이후 모든 분석 단계에서 자동으로 활용됩니다.")
    uploaded_files = st.file_uploader(
        "파일 업로드",
        accept_multiple_files=True,
        key=f"proj_upload_{current}",
        label_visibility="collapsed",
    )

    # OneDrive Import
    od_file, od_name = ui_onedrive.render_onedrive_importer(settings, key_prefix="proj_od")
    if od_file and od_name:
        # Save to local storage variable to be picked up by _build_project_docs logic if we want,
        # or just treat it as a "file" object.
        # Since _build_project_docs expects UploadedFile (which has read(), name), we might need a wrapper
        # or adjust _build_project_docs.
        # Let's create a simple BytesIO wrapper.
        import io
        class VirtualFile(io.BytesIO):
             def __init__(self, content, name):
                 super().__init__(content)
                 self.name = name
                 self.size = len(content)
        
        v_file = VirtualFile(od_file, od_name)
        if not uploaded_files:
            uploaded_files = []
        uploaded_files.append(v_file)
        st.success(f"OneDrive에서 '{od_name}' 가져오기 완료! 아래 '문서 저장' 버튼을 눌러주세요.")

    # Saved documents selection
    saved_docs = utils.list_saved_docs()
    selected_saved = []
    if saved_docs:
        selected_saved = st.multiselect(
            "저장된 문서에서 선택",
            saved_docs,
            key=f"proj_saved_{current}",
        )

    # Build button
    has_files = bool(uploaded_files) or bool(selected_saved)
    if st.button(
        "문서 저장",
        use_container_width=True,
        type="primary",
        disabled=not has_files,
        key=f"proj_build_{current}",
    ):
        api_key = settings.get("api_key", "")
        if not api_key:
            st.error("설정에서 API Key를 먼저 입력해주세요.")
        else:
            _build_project_docs(settings, current, uploaded_files, selected_saved)

    st.markdown("---")

    # Management buttons
    c1, c2 = st.columns(2)
    with c1:
        if saved_docs and st.button("저장된 문서 전체 가져오기", use_container_width=True, key=f"proj_index_all_{current}"):
            api_key = settings.get("api_key", "")
            with st.spinner("저장된 문서 전체를 프로젝트에 추가 중..."):
                result = core_rag.index_saved_documents(api_key, current)
                if result.get("success"):
                    indexed = result.get("indexed", [])
                    st.success(f"{len(indexed)}개 문서 추가 완료")
                    st.rerun()
                else:
                    st.error(f"오류: {result.get('error', '')}")

    with c2:
        if doc_count > 0 and st.button("문서 초기화", use_container_width=True, key=f"proj_clear_{current}"):
            core_rag.clear_rag_index(current)
            st.toast("프로젝트 문서가 초기화되었습니다.")
            st.rerun()


def _build_project_docs(settings, project_name, uploaded_files, selected_saved):
    """Parse files and save to project document store."""
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
        st.warning("저장할 문서가 없습니다 (내용이 너무 짧음).")
        return

    # Save to project
    progress.progress(0.8, text="프로젝트에 문서 저장 중...")
    try:
        result = core_rag.index_texts(api_key, texts, project_name)
        progress.progress(1.0, text="완료!")

        if result.get("success") or result.get("indexed"):
            indexed = result.get("indexed", [])
            skipped = result.get("skipped", [])
            msg_parts = []
            if indexed:
                msg_parts.append(f"{len(indexed)}개 신규 저장")
            if skipped:
                msg_parts.append(f"{len(skipped)}개 이미 저장됨 (스킵)")
            st.success(" / ".join(msg_parts) if msg_parts else "저장 완료")
        else:
            st.error(f"저장 오류: {result.get('error', 'unknown')}")

        if result.get("errors"):
            for err in result["errors"]:
                st.warning(f"오류 - {err['name']}: {err['error']}")

        if skipped_files:
            st.warning(f"⚠️ {len(skipped_files)}개 파일 스킵됨: {', '.join(skipped_files)}")

        st.rerun()

    except Exception as e:
        progress.empty()
        st.error(f"문서 저장 실패: {e}")

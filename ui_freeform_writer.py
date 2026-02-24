"""
자유양식 작성기 (Freeform Writer)
파일을 업로드하거나 지시사항만 입력하면 AI가 자유양식으로 문서를 작성.
수정 채팅으로 후속 보완 가능.
"""
import streamlit as st
from google import genai
from google.genai import types
import utils


SYSTEM_PROMPT = (
    "당신은 전문 문서 작성자입니다. "
    "사용자가 제공한 자료와 지시사항에 따라 문서를 작성합니다.\n\n"
    "[규칙]\n"
    "1. 서문, 인트로, 설명 문장 없이 바로 마크다운 본문으로 시작하세요.\n"
    "2. 사용자가 제공한 원본 자료의 정보를 정확히 반영하세요.\n"
    "3. 마크다운 형식으로 출력하세요.\n"
    "4. 수치, 고유명사, 날짜 등 구체적 데이터는 절대 변경하지 마세요.\n"
)

LENGTH_LABELS = {"short": "짧게 (1-2페이지)", "medium": "보통 (3-5페이지)", "long": "길게 (5페이지 이상)"}
LENGTH_INSTRUCTIONS = {
    "short": "분량은 짧고 간결하게, 핵심만 1-2페이지 이내로 작성하세요.",
    "medium": "분량은 보통 수준으로, 3-5페이지 정도로 작성하세요.",
    "long": "분량은 상세하고 풍부하게, 5페이지 이상으로 작성하세요.",
}
TONE_LABELS = {"formal": "격식체", "informal": "비격식체"}
TONE_INSTRUCTIONS = {
    "formal": "격식체(합쇼체)로 작성하세요.",
    "informal": "비격식체(해요체)로 부드럽게 작성하세요.",
}

# Session state key prefix
_PFX = "freeform_"


def _build_prompt(instruction: str, file_context: str, length: str, tone: str) -> str:
    """사용자 입력 + 옵션으로 메인 프롬프트 구성."""
    parts = []
    parts.append(f"[지시사항]\n{instruction}")
    parts.append(f"[분량] {LENGTH_INSTRUCTIONS[length]}")
    parts.append(f"[어조] {TONE_INSTRUCTIONS[tone]}")
    if file_context:
        parts.append(f"[참고 자료]\n{file_context}")
    return "\n\n".join(parts)


def _generate_stream(api_key: str, model: str, prompt: str):
    """Gemini 스트리밍 생성."""
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        max_output_tokens=65536,
        temperature=0.5,
        system_instruction=SYSTEM_PROMPT,
    )
    return client.models.generate_content_stream(
        model=model, contents=prompt, config=config
    )


def _refine_stream(api_key: str, model: str, original_text: str, request: str):
    """기존 결과물 + 수정 요청으로 재생성."""
    client = genai.Client(api_key=api_key)
    system = (
        "당신은 전문 문서 편집자입니다. "
        "기존 문서와 사용자의 수정 요청을 받아 문서를 수정합니다.\n"
        "수정 요청에 해당하는 부분만 변경하고, 나머지는 최대한 유지하세요.\n"
        "마크다운 형식으로 전체 수정 결과를 출력하세요."
    )
    prompt = f"[기존 문서]\n{original_text}\n\n[수정 요청]\n{request}"
    config = types.GenerateContentConfig(
        max_output_tokens=65536,
        temperature=0.3,
        system_instruction=system,
    )
    return client.models.generate_content_stream(
        model=model, contents=prompt, config=config
    )


def render_freeform_writer_panel(settings=None):
    """자유양식 작성기 UI 패널."""
    main_api_key = settings.get("api_key", "") if settings else ""

    st.markdown("### 📝 자유양식 작성기")
    st.caption("파일을 업로드하거나 지시사항만 입력하면 AI가 자유양식으로 문서를 작성합니다.")

    # ── 1. 입력 영역 ──
    st.markdown("---")

    # 파일 업로드 (선택)
    uploaded_files = st.file_uploader(
        "📎 참고 파일 업로드 (선택)",
        accept_multiple_files=True,
        type=["pdf", "docx", "txt", "md", "xlsx", "xls", "pptx", "png", "jpg"],
        key=f"{_PFX}files",
        help="PDF, Word, Excel, PPT, 이미지 등. 없어도 지시사항만으로 작성 가능.",
    )

    # 지시사항
    instruction = st.text_area(
        "✍️ 지시사항",
        height=150,
        placeholder="예: 이 자료를 바탕으로 투자 요약문을 작성해줘\n예: 이메일 초안을 격식체로 써줘\n예: 이 계약서 내용을 정리해줘",
        key=f"{_PFX}instruction",
    )

    # 옵션
    col_len, col_tone, col_model = st.columns(3)
    with col_len:
        length = st.selectbox(
            "분량",
            options=list(LENGTH_LABELS.keys()),
            format_func=lambda k: LENGTH_LABELS[k],
            index=1,
            key=f"{_PFX}length",
        )
    with col_tone:
        tone = st.selectbox(
            "어조",
            options=list(TONE_LABELS.keys()),
            format_func=lambda k: TONE_LABELS[k],
            index=0,
            key=f"{_PFX}tone",
        )
    with col_model:
        model = st.selectbox(
            "모델",
            options=["gemini-3-flash-preview", "gemini-3-pro-preview"],
            index=0,
            key=f"{_PFX}model",
        )

    # 생성 버튼
    run_btn = st.button(
        "🚀 생성하기", use_container_width=True, type="primary", key=f"{_PFX}run"
    )

    if run_btn:
        if not instruction:
            st.warning("지시사항을 입력해주세요.")
            return
        if not main_api_key:
            st.error("⚠️ 설정에서 Google API Key를 입력해주세요.")
            return

        # 파일 파싱
        file_context = ""
        if uploaded_files:
            parsed_parts = []
            docai_config = settings.get("docai_config") if settings else None
            for f in uploaded_files:
                parsed = utils.parse_uploaded_file(f, api_key=main_api_key, docai_config=docai_config)
                if parsed:
                    parsed_parts.append(f"--- [{f.name}] ---\n{parsed}")
            file_context = "\n\n".join(parsed_parts)

        prompt = _build_prompt(instruction, file_context, length, tone)

        # 스트리밍 생성
        result_placeholder = st.empty()
        accumulated = ""
        try:
            for chunk in _generate_stream(main_api_key, model, prompt):
                if chunk.text:
                    accumulated += chunk.text
                    result_placeholder.markdown(accumulated)
            st.session_state[f"{_PFX}result"] = accumulated
            st.session_state[f"{_PFX}file_context"] = file_context
            st.rerun()
        except Exception as e:
            st.error(f"생성 오류: {str(e)}")
            return

    # ── 2. 결과 영역 ──
    result = st.session_state.get(f"{_PFX}result", "")
    if not result:
        return

    st.markdown("---")
    st.markdown("#### 📄 생성 결과")
    with st.container(border=True):
        st.markdown(result)

    # 다운로드 + 초기화 버튼
    col_dl_word, col_dl_md, col_reset = st.columns(3)
    with col_dl_word:
        try:
            docx_bytes = utils.create_docx(result)
            st.download_button(
                "📥 Word 다운로드",
                data=docx_bytes,
                file_name="freeform_document.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except Exception:
            st.download_button(
                "📥 TXT 다운로드",
                data=result,
                file_name="freeform_document.txt",
                mime="text/plain",
                use_container_width=True,
            )
    with col_dl_md:
        st.download_button(
            "📥 MD 다운로드",
            data=result,
            file_name="freeform_document.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_reset:
        if st.button("🔄 초기화", use_container_width=True, key=f"{_PFX}reset"):
            for k in list(st.session_state.keys()):
                if k.startswith(_PFX):
                    del st.session_state[k]
            st.rerun()

    # ── 3. 수정 채팅 ──
    st.markdown("---")
    st.markdown("#### 💬 수정 요청")

    # 수정 이력 표시
    refine_history = st.session_state.get(f"{_PFX}refine_history", [])
    for item in refine_history:
        st.chat_message("user").write(item["request"])
        st.chat_message("assistant").write("✅ 반영 완료")

    refine_input = st.chat_input(
        "수정할 내용을 입력하세요 (예: '결론 부분을 좀 더 자세하게 써줘')",
        key=f"{_PFX}refine_input",
    )

    if refine_input:
        if not main_api_key:
            st.error("⚠️ API Key가 없습니다.")
            return

        st.chat_message("user").write(refine_input)

        with st.chat_message("assistant"):
            result_placeholder = st.empty()
            accumulated = ""
            try:
                for chunk in _refine_stream(main_api_key, model, result, refine_input):
                    if chunk.text:
                        accumulated += chunk.text
                        result_placeholder.markdown(accumulated)

                # 결과 업데이트
                st.session_state[f"{_PFX}result"] = accumulated
                history = st.session_state.get(f"{_PFX}refine_history", [])
                history.append({"request": refine_input})
                st.session_state[f"{_PFX}refine_history"] = history
                st.rerun()
            except Exception as e:
                st.error(f"수정 오류: {str(e)}")

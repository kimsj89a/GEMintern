"""
문장 정리기 (Text Organizer)
줄글을 붙여넣으면 Gemini API를 통해 개조식(bullet point)으로 정리
"""
import streamlit as st
from google import genai


ORGANIZER_PROMPT = (
    "당신은 텍스트 구조화 전문가입니다.\n"
    "다음 줄글(서술형 텍스트)을 **개조식(bullet point)**으로 정리해주세요.\n\n"
    "[규칙]\n"
    "1. 원문의 모든 정보를 빠짐없이 포함하세요. 새로운 내용을 추가하지 마세요.\n"
    "2. 주제별로 그룹화하고, 대주제는 `##`, 소주제는 `###`으로 구분하세요.\n"
    "3. 각 항목은 `-` 불릿으로 시작하고, 한 문장 이내로 간결하게 작성하세요.\n"
    "4. 수치, 고유명사, 날짜 등 구체적 데이터는 절대 변경하지 마세요.\n"
    "5. 논리적 흐름(시간순, 중요도순 등)에 맞게 배치하세요.\n"
    "6. 마크다운 형식으로 출력하세요.\n"
)


def _organize_text(raw_text: str, api_key: str, model: str) -> str:
    """Gemini API로 줄글을 개조식으로 변환"""
    client = genai.Client(api_key=api_key)
    prompt = f"{ORGANIZER_PROMPT}\n[입력 텍스트]\n{raw_text}"
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text.strip() if response.text else ""


def render_text_organizer_panel(settings=None):
    """문장 정리기 UI 패널"""
    main_api_key = settings.get('api_key', '') if settings else ''

    st.markdown("### ✏️ 문장 정리기 (Text Organizer)")
    st.caption("줄글을 붙여넣으면 개조식(bullet point)으로 깔끔하게 정리해줍니다.")

    # 1단계: 텍스트 입력
    st.markdown("---")
    input_text = st.text_area(
        "줄글 입력",
        height=300,
        placeholder="여기에 정리할 줄글을 붙여넣으세요...",
        key="organizer_input"
    )

    if input_text:
        st.info(f"입력된 텍스트: {len(input_text):,}자")

    # 2단계: 실행
    col_btn, col_model = st.columns([2, 1])
    with col_model:
        post_model = st.selectbox(
            "모델",
            options=["gemini-3-flash-preview", "gemini-3-pro-preview"],
            index=0,
            key="organizer_model"
        )
    with col_btn:
        run_btn = st.button(
            "🚀 개조식으로 정리",
            use_container_width=True,
            type="primary",
            key="organizer_run"
        )

    if run_btn:
        if not input_text:
            st.warning("텍스트를 입력해주세요.")
        elif not main_api_key:
            st.error("⚠️ 설정에서 Google API Key를 입력해주세요.")
        else:
            with st.spinner("✏️ 개조식으로 정리하는 중..."):
                try:
                    result = _organize_text(input_text, main_api_key, post_model)
                    st.session_state['organizer_result'] = result
                    st.rerun()
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")

    # 3단계: 결과 표시
    if 'organizer_result' in st.session_state and st.session_state['organizer_result']:
        st.markdown("---")
        st.markdown("#### 결과")

        with st.container(border=True):
            st.markdown(st.session_state['organizer_result'])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "📥 TXT 다운로드",
                data=st.session_state['organizer_result'],
                file_name="organized.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col2:
            st.download_button(
                "📥 MD 다운로드",
                data=st.session_state['organizer_result'],
                file_name="organized.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col3:
            if st.button("🔄 초기화", use_container_width=True, key="organizer_reset"):
                del st.session_state['organizer_result']
                st.rerun()

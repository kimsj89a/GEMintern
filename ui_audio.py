"""
텍스트 후처리 모듈
TXT 파일 업로드 또는 직접 입력 → AI 후처리 (회의록, 요약 등)
"""
import streamlit as st
from google import genai


def _get_instruction(mode: str) -> str:
    """후처리 모드별 instruction 반환"""
    instructions = {
        "clean": (
            "다음 한국어 텍스트를 의미를 바꾸지 말고, "
            "띄어쓰기/문장부호를 자연스럽게 다듬고, 중복 표현을 최소화해 주세요. "
            "새로운 사실을 추가하지 마세요."
        ),
        "summary": (
            "다음 한국어 텍스트를 바탕으로 "
            "1) 핵심 요약(불릿 5~10개) "
            "2) 결정사항(있으면) "
            "3) 액션아이템(담당/기한이 언급되면 포함) "
            "형태로 정리해 주세요. 없는 항목은 '없음'으로 표시하세요. "
            "새로운 사실을 추가하지 마세요."
        ),
        "meeting_summary": (
            "다음은 회의 녹음의 전사 텍스트입니다.\n"
            "이 내용을 바탕으로 다음 형식의 회의록을 작성해주세요.\n\n"
            "1. 3줄 핵심 요약\n"
            "   - 전체 회의의 가장 중요한 결론이나 내용을 3가지로 요약 (개조식)\n\n"
            "2. 상세 요약\n"
            "   - 주요 주제가 바뀌는 구간을 나누어 정리\n"
            "   - 타임스탬프가 있다면 [mm:ss ~ mm:ss] 형식으로 헤더에 표시\n"
            "   - 내용은 Q&A 형식 또는 핵심 내용 서술형으로 상세히 정리\n"
            "   - 전사된 내용의 팩트를 기반으로 작성하되, 문장은 깔끔하게 다듬을 것"
        ),
        "qa_format": (
            "다음 텍스트를 Q&A 형식으로 정리해주세요.\n"
            "- 주요 질문과 답변을 추출하여 구조화\n"
            "- Q: 질문 / A: 답변 형식으로 작성\n"
            "- 관련 주제별로 그룹화"
        ),
        "presentation_format": (
            "다음 텍스트를 발표자료 형식으로 변환해주세요.\n"
            "- 슬라이드별로 구분 (## 슬라이드 1, ## 슬라이드 2...)\n"
            "- 각 슬라이드는 제목과 3-5개의 불릿포인트로 구성\n"
            "- 핵심 메시지 중심으로 간결하게 정리"
        ),
    }
    return instructions.get(mode, "다음 텍스트를 의미를 바꾸지 말고 정리해 주세요.")


def _get_chunked_instruction(mode: str) -> str:
    """Chunking 시 사용할 instruction (핵심요약 + 상세요약 분리)"""
    if mode == "meeting_summary":
        return (
            "다음은 회의 녹음의 전사 텍스트 일부입니다.\n"
            "이 내용을 바탕으로 다음 형식으로 정리해주세요.\n\n"
            "반드시 아래 두 섹션을 구분하여 작성하세요:\n\n"
            "===핵심요약===\n"
            "이 파트의 가장 중요한 내용을 2-3줄로 요약 (개조식)\n\n"
            "===상세요약===\n"
            "- 주요 주제가 바뀌는 구간을 나누어 정리\n"
            "- 타임스탬프가 있다면 [mm:ss ~ mm:ss] 형식으로 헤더에 표시\n"
            "- 내용은 Q&A 형식 또는 핵심 내용 서술형으로 상세히 정리\n"
            "- 전사된 내용의 팩트를 기반으로 작성하되, 문장은 깔끔하게 다듬을 것"
        )
    return _get_instruction(mode)


def _postprocess_with_gemini(raw_text: str, mode: str, model: str, api_key: str) -> str:
    """Gemini를 사용한 텍스트 후처리 (Chunking 적용)"""
    client = genai.Client(api_key=api_key)

    # 사용자 요청 반영: 뉘앙스, 데이터, 고유명사 유지
    additional_instruction = (
        "\n\n[중요 원칙]\n"
        "1. 원문의 뉘앙스를 최대한 유지하세요.\n"
        "2. 언급된 상세 데이터(수치 등)와 고유명사는 절대 변경하거나 생략하지 말고 그대로 기재하세요.\n"
        "3. 텍스트가 분할되어 입력될 수 있으니, 문맥이 자연스럽게 이어지도록 하세요."
    )

    # Chunking (5000자 기준 - 속도 개선)
    chunk_size = 5000
    chunks = [raw_text[i:i+chunk_size] for i in range(0, len(raw_text), chunk_size)]

    # 청크가 1개면 기존 방식 사용
    if len(chunks) == 1:
        base_instruction = _get_instruction(mode)
        full_instruction = base_instruction + additional_instruction

        prompt = f"{full_instruction}\n\n[텍스트]\n{chunks[0]}"
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text.strip() if response.text else ""
        except Exception as e:
            return f"[Error: {str(e)}]"

    # 청크가 여러 개면 핵심요약/상세요약 분리 처리
    base_instruction = _get_chunked_instruction(mode)
    full_instruction = base_instruction + additional_instruction

    executive_summaries = []
    detailed_summaries = []
    prev_context = ""

    # 진행상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_chunks = len(chunks)

    for i, chunk in enumerate(chunks):
        status_text.text(f"Processing chunk {i+1}/{total_chunks}...")

        # 문맥 연결을 위한 프롬프트 구성
        prompt = f"{full_instruction}\n"
        if prev_context:
            prompt += f"\n[이전 처리 내용 (문맥 연결용)]\n...{prev_context}\n\n(위 내용과 문맥이 자연스럽게 이어지도록 작성하세요)\n"

        prompt += f"\n[텍스트 (Part {i+1}/{total_chunks})]\n{chunk}"

        try:
            response = client.models.generate_content(model=model, contents=prompt)
            if response.text:
                result_text = response.text.strip()

                # 핵심요약과 상세요약 분리
                if "===핵심요약===" in result_text and "===상세요약===" in result_text:
                    parts = result_text.split("===상세요약===")
                    exec_part = parts[0].replace("===핵심요약===", "").strip()
                    detail_part = parts[1].strip() if len(parts) > 1 else ""

                    if exec_part:
                        executive_summaries.append(f"**[Part {i+1}]**\n{exec_part}")
                    if detail_part:
                        detailed_summaries.append(detail_part)
                        prev_context = detail_part[-500:] if len(detail_part) > 500 else detail_part
                else:
                    # 분리 실패 시 전체를 상세요약으로 처리
                    detailed_summaries.append(result_text)
                    prev_context = result_text[-500:] if len(result_text) > 500 else result_text

        except Exception as e:
            detailed_summaries.append(f"[Error in chunk {i+1}: {str(e)}]")
        progress_bar.progress((i + 1) / total_chunks)

    status_text.empty()
    progress_bar.empty()

    # 최종 결과 조합: Executive Summary + 상세 요약
    final_result = []

    if executive_summaries and mode == "meeting_summary":
        final_result.append("## 📌 Executive Summary\n")
        final_result.append("\n\n".join(executive_summaries))
        final_result.append("\n\n---\n")

    final_result.append("## 📝 상세 요약\n")
    final_result.append("\n\n".join(detailed_summaries))

    return "\n".join(final_result)


def render_audio_transcription_panel(settings=None):
    """텍스트 후처리 UI 패널

    Args:
        settings: 메인 설정 (api_key, model_name 등 포함)
    """
    # 메인 설정에서 API Key 가져오기
    main_api_key = settings.get('api_key', '') if settings else ''

    st.markdown("### 📝 텍스트 후처리 (Text Processing)")
    st.markdown("""
        <div style='background-color: #e8f4f8; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #0068c9;'>
        <h4 style='margin-top: 0; color: #0068c9;'>📋 사용 방법</h4>
        <b>1단계:</b> 텍스트 파일(TXT) 업로드 또는 직접 입력<br/>
        <b>2단계:</b> AI 후처리 방식 선택 (회의록, 요약, Q&A 등)<br/>
        <b>3단계:</b> 결과 확인 및 다운로드
        <hr style='margin: 10px 0; border: none; border-top: 1px solid #ccc;'>
        <small>✓ Gemini 지원 | ✓ 다양한 후처리 옵션 | ✓ 즉시 다운로드</small>
        </div>
    """, unsafe_allow_html=True)

    # ============================================
    # 1단계: 텍스트 입력
    # ============================================
    st.markdown("---")
    st.markdown("## 1️⃣ 텍스트 입력")

    # 입력 방식 선택
    input_method = st.radio(
        "입력 방식 선택",
        options=["📄 TXT 파일 업로드", "✏️ 직접 입력"],
        horizontal=True,
        key="text_input_method"
    )

    input_text = ""

    if input_method == "📄 TXT 파일 업로드":
        uploaded_file = st.file_uploader(
            "텍스트 파일 업로드 (TXT, MD)",
            type=['txt', 'md'],
            key="text_file_uploader"
        )

        if uploaded_file:
            try:
                # 다양한 인코딩 시도: UTF-8 → UTF-16 → CP949
                raw_bytes = uploaded_file.read()
                input_text = None

                # 1. UTF-8 (BOM 포함/미포함)
                try:
                    input_text = raw_bytes.decode('utf-8-sig')
                except UnicodeDecodeError:
                    pass

                # 2. UTF-16 (BOM 자동 감지 - 0xFE 0xFF 또는 0xFF 0xFE)
                if input_text is None:
                    try:
                        input_text = raw_bytes.decode('utf-16')
                    except UnicodeDecodeError:
                        pass

                # 3. CP949 (한국어 Windows 기본)
                if input_text is None:
                    try:
                        input_text = raw_bytes.decode('cp949')
                    except UnicodeDecodeError:
                        pass

                # 4. EUC-KR (레거시 한국어)
                if input_text is None:
                    try:
                        input_text = raw_bytes.decode('euc-kr')
                    except UnicodeDecodeError:
                        pass

                # 5. 최후 수단: errors='replace'로 UTF-8
                if input_text is None:
                    input_text = raw_bytes.decode('utf-8', errors='replace')

                st.success(f"✅ 파일 로드 완료: {uploaded_file.name} ({len(input_text):,}자)")

                with st.expander("📄 파일 내용 미리보기", expanded=False):
                    st.text(input_text[:2000] + ("..." if len(input_text) > 2000 else ""))

            except Exception as e:
                st.error(f"파일 읽기 오류: {str(e)}")
    else:
        input_text = st.text_area(
            "텍스트 직접 입력",
            height=300,
            placeholder="여기에 텍스트를 붙여넣기 하세요...",
            key="direct_text_input"
        )
        if input_text:
            st.info(f"입력된 텍스트: {len(input_text):,}자")

    # ============================================
    # 2단계: AI 후처리 설정
    # ============================================
    if input_text:
        st.markdown("---")
        st.markdown("## 2️⃣ AI 후처리 설정")

        # 후처리 모델 선택
        post_model = st.selectbox(
            "🤖 모델 선택",
            options=["gemini-3-flash-preview", "gemini-3-pro-preview", "gemini-2.5-pro"],
            index=0,
            key="text_post_model_gemini"
        )

        # API Key는 메인 설정에서 가져옴
        api_key = main_api_key
        if api_key:
            st.success("✅ 메인 설정의 API Key 사용")
        else:
            st.warning("⚠️ 상단 설정에서 Google API Key를 입력해주세요")

        # 후처리 방식 선택
        st.markdown("#### 후처리 방식")
        gpt_mode = st.selectbox(
            "변환 형식 선택",
            options=[
                ("📝 회의록 (3줄 요약 + 상세 정리)", "meeting_summary"),
                ("📊 핵심 요약 (불릿 + 결정사항 + 액션아이템)", "summary"),
                ("💬 Q&A 형식 (질의응답 구조화)", "qa_format"),
                ("📢 발표자료 형식 (슬라이드 구조)", "presentation_format"),
                ("✨ 텍스트 정리 (띄어쓰기/문장부호)", "clean")
            ],
            format_func=lambda x: x[0],
            key="text_gpt_mode"
        )

        # 후처리 실행 버튼
        st.markdown("")
        if st.button("🚀 AI 후처리 시작", use_container_width=True, type="primary", key="text_process_btn"):
            if not api_key:
                st.error("⚠️ 상단 설정에서 API Key를 입력해주세요")
            else:
                with st.spinner("🤖 AI 후처리를 수행하는 중..."):
                    try:
                        processed_text = _postprocess_with_gemini(
                            raw_text=input_text,
                            mode=gpt_mode[1],
                            model=post_model,
                            api_key=api_key
                        )

                        st.session_state['processed_result'] = processed_text
                        st.session_state['original_text'] = input_text
                        st.success("✅ 후처리 완료!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"⚠️ 후처리 중 오류 발생: {str(e)}")

    # ============================================
    # 3단계: 결과 확인 및 다운로드
    # ============================================
    if 'processed_result' in st.session_state and st.session_state['processed_result']:
        st.markdown("---")
        st.markdown("## 3️⃣ 결과 확인")

        # 결과 표시
        with st.container(border=True):
            st.markdown(st.session_state['processed_result'])

        # 다운로드 버튼
        st.markdown("#### 💾 다운로드")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button(
                label="📥 결과 (TXT)",
                data=st.session_state['processed_result'],
                file_name="processed_result.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="📥 결과 (MD)",
                data=st.session_state['processed_result'],
                file_name="processed_result.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col3:
            if st.button("🔄 초기화", use_container_width=True, type="secondary"):
                if 'processed_result' in st.session_state:
                    del st.session_state['processed_result']
                if 'original_text' in st.session_state:
                    del st.session_state['original_text']
                st.rerun()

        # 원본 텍스트 보기 옵션
        if 'original_text' in st.session_state:
            with st.expander("📄 원본 텍스트 보기"):
                st.text(st.session_state['original_text'])

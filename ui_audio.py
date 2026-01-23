"""
오디오 전사 기능 독립 모듈
Whisper API를 사용한 음성 파일 텍스트 변환
"""
import streamlit as st
import utils_audio

def render_audio_transcription_panel():
    """오디오 전사 전용 UI 패널"""
    st.markdown("### 🎤 오디오 전사 (Audio Transcription)")
    st.markdown("""
        <div style='background-color: #e8f4f8; padding: 12px; border-radius: 6px; margin-bottom: 15px;'>
        <b>🔊 음성 파일 전사 기능 (고급)</b><br/>
        ✓ Apple m4a 파일 지원 (iPhone/iPad 녹음)<br/>
        ✓ 긴 파일 자동 분할 (FFmpeg 필요)<br/>
        ✓ 타임스탬프 & 문단 정리<br/>
        ✓ GPT 후처리 (요약/정리)
        </div>
    """, unsafe_allow_html=True)

    # API 키 입력
    query_params = st.query_params
    cached_openai_key = query_params.get("openai_api_key", "")
    if isinstance(cached_openai_key, list):
        cached_openai_key = cached_openai_key[0]

    col1, col2 = st.columns([3, 1])
    with col1:
        openai_api_key = st.text_input(
            "OpenAI API Key",
            value=cached_openai_key,
            type="password",
            placeholder="sk-...",
            key="audio_openai_key"
        )
    with col2:
        st.write("")
        st.write("")
        save_key = st.checkbox("🔑 키 저장", value=bool(cached_openai_key), key="audio_save_key")

    if save_key and openai_api_key:
        st.query_params["openai_api_key"] = openai_api_key
    elif not save_key and "openai_api_key" in st.query_params:
        del st.query_params["openai_api_key"]

    # 파일 업로드
    st.markdown("##### 오디오 파일 업로드")
    uploaded_audio = st.file_uploader(
        "MP3, WAV, M4A 등 오디오 파일 선택",
        type=['mp3', 'wav', 'm4a', 'mp4', 'mpeg', 'mpga', 'webm', 'ogg', 'flac'],
        key="audio_file_uploader"
    )

    # 전사 옵션
    st.markdown("##### ⚙️ 전사 옵션")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**기본 설정**")
        include_timestamps = st.checkbox(
            "⏱️ 타임스탬프 포함 [mm:ss]",
            value=True,
            help="각 문단에 시작-종료 시간 표시",
            key="audio_timestamps"
        )

        remove_fillers = st.checkbox(
            "🧹 추임새 자동 제거",
            value=True,
            help="'아', '음', '그' 등 불필요한 표현 제거",
            key="audio_remove_fillers"
        )

        chunk_minutes = st.slider(
            "📦 긴 파일 분할 단위 (분)",
            min_value=5,
            max_value=30,
            value=10,
            step=5,
            help="FFmpeg 설치 시 자동 분할 (미설치 시 전체 처리)",
            key="audio_chunk_minutes"
        )

    with col2:
        st.markdown("**고급 설정**")

        gpt_mode = st.selectbox(
            "🤖 GPT 후처리",
            options=[
                ("없음", None),
                ("텍스트 정리", "clean"),
                ("회의록 요약", "summary"),
                ("질적코딩용", "atlas_codebook")
            ],
            format_func=lambda x: x[0],
            help="전사 후 GPT로 추가 정리 (비용 추가 발생)",
            key="audio_gpt_mode"
        )

        gpt_model = st.selectbox(
            "GPT 모델",
            options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
            index=0,
            help="후처리용 모델 선택",
            key="audio_gpt_model"
        )

        # 화자 분리 (고급 기능 - HF_TOKEN 필요)
        do_diarization = st.checkbox(
            "🎭 화자 분리 시도 (실험적)",
            value=False,
            help="HuggingFace Token 환경변수 필요 (HF_TOKEN)",
            key="audio_diarization"
        )

    # FFmpeg 설치 확인
    has_ffmpeg = utils_audio._has_ffmpeg()
    if not has_ffmpeg:
        st.warning("⚠️ FFmpeg가 설치되지 않았습니다. 긴 파일 분할 및 형식 변환이 제한됩니다.")

    # 전사 실행
    if st.button("🚀 전사 시작", use_container_width=True, type="primary", key="audio_transcribe_btn"):
        if not openai_api_key:
            st.error("⚠️ OpenAI API Key를 입력해주세요")
        elif not uploaded_audio:
            st.error("⚠️ 오디오 파일을 업로드해주세요")
        else:
            with st.spinner("🎧 오디오 전사 중... (파일 크기에 따라 수 분 소요될 수 있습니다)"):
                transcribed_text = utils_audio.transcribe_audio(
                    uploaded_file=uploaded_audio,
                    api_key=openai_api_key,
                    language="ko",
                    chunk_seconds=chunk_minutes * 60,
                    do_diarization=do_diarization,
                    include_timestamps=include_timestamps,
                    remove_fillers=remove_fillers,
                    gpt_mode=gpt_mode[1],  # tuple의 두 번째 값 (실제 mode)
                    gpt_model=gpt_model
                )

                # 결과 저장
                st.session_state['transcription_result'] = transcribed_text
                st.success("✅ 전사 완료!")

    # 결과 표시
    if 'transcription_result' in st.session_state and st.session_state['transcription_result']:
        st.markdown("---")
        st.markdown("### 📝 전사 결과")

        result_text = st.session_state['transcription_result']

        # 결과 미리보기 (마크다운 렌더링)
        with st.expander("📄 결과 미리보기", expanded=True):
            st.markdown(result_text)

        # 편집 가능한 텍스트 영역
        st.markdown("##### 편집 가능한 텍스트")
        edited_text = st.text_area(
            "전사된 텍스트 (편집 가능)",
            value=result_text,
            height=400,
            key="audio_result_text"
        )

        # 다운로드 및 초기화 버튼
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                label="📥 텍스트 파일 다운로드",
                data=edited_text,
                file_name=f"transcription_{uploaded_audio.name.split('.')[0]}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="📥 마크다운 파일 다운로드",
                data=edited_text,
                file_name=f"transcription_{uploaded_audio.name.split('.')[0]}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col3:
            if st.button("🔄 초기화", use_container_width=True):
                del st.session_state['transcription_result']
                st.rerun()

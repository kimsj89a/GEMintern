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
        <b>🔊 음성 파일 전사 기능</b><br/>
        MP3, WAV 등 오디오 파일을 업로드하면 텍스트로 변환됩니다.<br/>
        추임새("아", "음", "그" 등) 자동 제거 옵션 제공
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
    remove_fillers = st.checkbox(
        "추임새 자동 제거 ('아', '음', '그' 등)",
        value=True,
        key="audio_remove_fillers"
    )

    # 전사 실행
    if st.button("🚀 전사 시작", use_container_width=True, type="primary", key="audio_transcribe_btn"):
        if not openai_api_key:
            st.error("⚠️ OpenAI API Key를 입력해주세요")
        elif not uploaded_audio:
            st.error("⚠️ 오디오 파일을 업로드해주세요")
        else:
            with st.spinner("🎧 오디오 전사 중... (파일 크기에 따라 시간이 걸릴 수 있습니다)"):
                transcribed_text = utils_audio.transcribe_audio(
                    uploaded_audio,
                    openai_api_key
                )

                # 추임새 제거 옵션이 꺼져있으면 원본 반환
                if not remove_fillers and transcribed_text:
                    # utils_audio.transcribe_audio는 이미 추임새 제거를 하므로,
                    # 옵션을 끄려면 별도 처리 필요 (향후 개선)
                    pass

                # 결과 저장
                st.session_state['transcription_result'] = transcribed_text
                st.success("✅ 전사 완료!")

    # 결과 표시
    if 'transcription_result' in st.session_state and st.session_state['transcription_result']:
        st.markdown("---")
        st.markdown("### 📝 전사 결과")

        result_text = st.session_state['transcription_result']
        st.text_area(
            "전사된 텍스트",
            value=result_text,
            height=400,
            key="audio_result_text"
        )

        # 다운로드 버튼
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 텍스트 파일로 다운로드",
                data=result_text,
                file_name="transcription.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col2:
            if st.button("🔄 초기화", use_container_width=True):
                del st.session_state['transcription_result']
                st.rerun()

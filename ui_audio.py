"""
오디오 전사 기능 독립 모듈
Whisper API 또는 Gemini를 사용한 음성 파일 텍스트 변환
"""
import streamlit as st
import utils_audio

def render_audio_transcription_panel():
    """오디오 전사 전용 UI 패널"""
    st.markdown("### 🎤 오디오 전사 (Audio Transcription)")
    st.markdown("""
        <div style='background-color: #e8f4f8; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #0068c9;'>
        <h4 style='margin-top: 0; color: #0068c9;'>📋 워크플로우</h4>
        <b>1단계:</b> 분·문장 단위로 화자 구분하여 전사<br/>
        <b>2단계:</b> 전사 내용을 주제별로 묶어서 표시 & 편집<br/>
        <b>3단계:</b> AI 후처리 (선택) - Summary/Q&A/발표자료 형식으로 변환
        <hr style='margin: 10px 0; border: none; border-top: 1px solid #ccc;'>
        <small>✓ Whisper & Gemini 지원 | ✓ 타임스탬프 & 화자 구분 | ✓ 주제별 자동 그룹핑</small>
        </div>
    """, unsafe_allow_html=True)

    # ============================================
    # 1단계: 전사 설정 및 실행
    # ============================================
    st.markdown("---")
    st.markdown("## 1️⃣ 전사 설정")

    # 전사 엔진 선택
    col_engine1, col_engine2 = st.columns([2, 1])
    with col_engine1:
        transcription_engine = st.selectbox(
            "🤖 전사 엔진 선택",
            options=[
                ("Google Gemini", "gemini"),
                ("OpenAI Whisper", "whisper")
            ],
            format_func=lambda x: x[0],
            help="Whisper: 타임스탬프 지원, 높은 정확도 | Gemini: 빠른 처리, 다양한 형식 지원",
            key="audio_transcription_engine"
        )

    # API 키 입력 - 선택된 엔진에 따라 변경
    query_params = st.query_params

    if transcription_engine[1] == "whisper":
        cached_key = query_params.get("openai_api_key", "")
        if isinstance(cached_key, list):
            cached_key = cached_key[0]

        col1, col2 = st.columns([3, 1])
        with col1:
            api_key = st.text_input(
                "OpenAI API Key",
                value=cached_key,
                type="password",
                placeholder="sk-...",
                key="audio_openai_key"
            )
        with col2:
            st.write("")
            st.write("")
            save_key = st.checkbox("🔑 키 저장", value=bool(cached_key), key="audio_save_key")

        if save_key and api_key:
            st.query_params["openai_api_key"] = api_key
        elif not save_key and "openai_api_key" in st.query_params:
            del st.query_params["openai_api_key"]

    else:  # Gemini
        cached_key = query_params.get("gemini_api_key", "")
        if isinstance(cached_key, list):
            cached_key = cached_key[0]

        col1, col2 = st.columns([3, 1])
        with col1:
            api_key = st.text_input(
                "Gemini API Key",
                value=cached_key,
                type="password",
                placeholder="AI...",
                key="audio_gemini_key"
            )
        with col2:
            st.write("")
            st.write("")
            save_key = st.checkbox("🔑 키 저장", value=bool(cached_key), key="audio_save_gemini_key")

        if save_key and api_key:
            st.query_params["gemini_api_key"] = api_key
        elif not save_key and "gemini_api_key" in st.query_params:
            del st.query_params["gemini_api_key"]

    # 파일 업로드
    uploaded_audio = st.file_uploader(
        "🎵 오디오 파일 업로드 (MP3, WAV, M4A 등)",
        type=['mp3', 'wav', 'm4a', 'mp4', 'mpeg', 'mpga', 'webm', 'ogg', 'flac'],
        key="audio_file_uploader"
    )

    # 전사 옵션 (확장 가능한 섹션으로 변경)
    with st.expander("⚙️ 전사 옵션 (고급)", expanded=False):
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
            if transcription_engine[1] == "gemini":
                st.info("ℹ️ FFmpeg가 없어도 Gemini 엔진은 대용량 파일을 자동으로 분할 처리(Batch)합니다.")
            else:
                st.warning("⚠️ FFmpeg가 설치되지 않았습니다. 긴 파일 분할 및 형식 변환이 제한됩니다.")

    # 전사 실행 버튼
    if st.button("🚀 전사 시작", use_container_width=True, type="primary", key="audio_transcribe_btn"):
        if not api_key:
            st.error("⚠️ API Key를 입력해주세요")
        elif not uploaded_audio:
            st.error("⚠️ 오디오 파일을 업로드해주세요")
        else:
            engine_name = "Whisper" if transcription_engine[1] == "whisper" else "Gemini"
            with st.spinner(f"🎧 {engine_name}로 오디오 전사 중... (파일 크기에 따라 수 분 소요될 수 있습니다)"):
                try:
                    # 실시간 결과 표시를 위한 컨테이너
                    progress_container = st.container()
                    with progress_container:
                        st.info("🔄 순차적 처리 중... (전사 -> 요약)")
                        col_res1, col_res2 = st.columns(2)
                        with col_res1:
                            st.markdown("### 📜 실시간 전사")
                            transcription_placeholder = st.empty()
                        with col_res2:
                            st.markdown("### 📝 실시간 회의록")
                            summary_placeholder = st.empty()

                                        def _render_chunk_views(chunks):
                        transcript_parts = []
                        summary_parts = []
                        for i, c in enumerate(chunks, 1):
                            transcript_parts.append(f"#### Chunk {i}
{c.get('text','')}")
                            if c.get('summary'):
                                summary_parts.append(f"#### Chunk {i}
{c['summary']}")
                            else:
                                summary_parts.append(f"#### Chunk {i}
(Summary pending...)")
                        return "

---

".join(transcript_parts), "

---

".join(summary_parts)

                    full_transcript = ""
                    full_summary = ""
                    chunk_results = []
                    
                    # Generator를 통해 순차적으로 처리
                    for chunk_text in utils_audio.transcribe_audio(
                        uploaded_file=uploaded_audio,
                        api_key=api_key,
                        language="ko",
                        chunk_seconds=chunk_minutes * 60,
                        do_diarization=do_diarization if transcription_engine[1] == "whisper" else False,  # Gemini는 화자 분리 미지원
                        include_timestamps=include_timestamps,  # Gemini도 타임스탬프 지원하도록 변경
                        remove_fillers=remove_fillers,
                        gpt_mode=None,  # GPT 후처리 제거 (나중에 별도로 수행)
                        gpt_model=None,
                        engine=transcription_engine[1],  # whisper 또는 gemini
                        gemini_model="gemini-2.0-flash-exp"  # Gemini 모델
                    ):
                        # 1. ??? ???????? ????? (??? ????? ???)
                        chunk_results.append({"text": chunk_text, "summary": None})
                        transcript_md, summary_md = _render_chunk_views(chunk_results)
                        transcription_placeholder.markdown(transcript_md)
                        summary_placeholder.markdown(summary_md)
                        full_transcript += chunk_text + "

"

                        # 2. 해당 청크에 대한 요약 생성 (순차적 요약)
                        try:
                            auto_model = "gemini-2.0-flash-exp" if transcription_engine[1] == "gemini" else "gpt-4o-mini"
                            auto_api_type = "gemini" if transcription_engine[1] == "gemini" else "openai"
                            
                            chunk_summary = utils_audio._gpt_postprocess(
                                raw_text=chunk_text,
                                mode="meeting_summary",
                                model=auto_model,
                                api_key=api_key,
                                api_type=auto_api_type
                            )
                            chunk_results[-1]["summary"] = chunk_summary
                            transcript_md, summary_md = _render_chunk_views(chunk_results)
                            transcription_placeholder.markdown(transcript_md)
                            summary_placeholder.markdown(summary_md)
                            full_summary += chunk_summary + "

"
                        except Exception as e:
                            full_summary += f"\n[요약 실패: {e}]\n"

                    # 결과 저장
                    st.session_state['transcription_result'] = full_transcript
                    st.session_state['gpt_processed_result'] = full_summary
                    st.session_state['transcription_api_key'] = api_key  # API 키 저장 (후처리용)
                    st.session_state['transcription_engine'] = transcription_engine[1]  # 사용된 엔진 저장

                    st.success(f"✅ {engine_name} 전사 완료!")
                    st.rerun()  # 결과 표시를 위해 리런
                except Exception as e:
                    st.error(f"⚠️ 전사 중 오류 발생: {str(e)}")
                finally:
                    # 파일 객체를 명시적으로 정리 (seek을 통해 스트림 리셋)
                    try:
                        uploaded_audio.seek(0)
                    except Exception:
                        pass

    # ============================================
    # 2단계: 전사 결과 확인 & 편집
    # ============================================
    if 'transcription_result' in st.session_state and st.session_state['transcription_result']:
        st.markdown("---")
        st.markdown("## 2️⃣ 전사 결과")

        # [화자 이름 변경 UI]
        with st.expander("👥 화자 이름 일괄 변경 (Speaker Renaming)", expanded=True):
            c_find, c_replace, c_btn = st.columns([2, 2, 1])
            with c_find:
                find_text = st.text_input("찾을 텍스트 (예: 화자 1)", key="spk_find")
            with c_replace:
                replace_text = st.text_input("변경할 이름 (예: 홍길동)", key="spk_replace")
            with c_btn:
                st.write("")
                if st.button("변경 적용", use_container_width=True):
                    if find_text and replace_text:
                        st.session_state['transcription_result'] = st.session_state['transcription_result'].replace(find_text, replace_text)
                        # 회의록도 함께 업데이트
                        if 'gpt_processed_result' in st.session_state:
                            st.session_state['gpt_processed_result'] = st.session_state['gpt_processed_result'].replace(find_text, replace_text)
                        st.success("적용 완료!")
                        st.rerun()

        result_text = st.session_state['transcription_result']

        # 결과 미리보기 (탭으로 변경)
        tab_preview, tab_edit = st.tabs(["📄 미리보기", "✏️ 편집"])

        with tab_preview:
            st.markdown(result_text)

        with tab_edit:
            edited_text = st.text_area(
                "전사된 텍스트 (편집 가능)",
                value=result_text,
                height=500,
                key="audio_result_text",
                label_visibility="collapsed"
            )
            # 편집 내용 저장 버튼
            if st.button("💾 편집 내용 저장", use_container_width=True):
                st.session_state['transcription_result'] = edited_text
                st.success("✅ 편집 내용이 저장되었습니다!")
                st.rerun()

        # ============================================
        # 3단계: AI 후처리 (선택사항)
        # ============================================
        st.markdown("---")
        st.markdown("## 3️⃣ AI 후처리 (선택사항)")

        # 후처리 엔진 선택
        col_post1, col_post2 = st.columns([2, 1])

        with col_post1:
            post_engine = st.selectbox(
                "🤖 후처리 엔진 선택",
                options=[
                    ("Google Gemini", "gemini"),
                    ("OpenAI GPT", "openai")
                ],
                format_func=lambda x: x[0],
                help="텍스트 정리/요약에 사용할 AI 엔진",
                key="audio_post_engine"
            )

        with col_post2:
            if post_engine[1] == "openai":
                post_model = st.selectbox(
                    "모델 선택",
                    options=[
                        "GPT-5.2-chat-latest",
                        "GPT-5.2",
                        "GPT-5.2 Pro"
                    ],
                    index=0,
                    help="후처리용 OpenAI 모델",
                    key="audio_post_model_openai"
                )
            else:  # Gemini
                post_model = st.selectbox(
                    "모델 선택",
                    options=[
                        "gemini-3-pro-preview",
                        "gemini-3-flash-preview"
                    ],
                    index=0,
                    help="후처리용 Gemini 모델",
                    key="audio_post_model_gemini"
                )

        # 후처리 방식 선택
        gpt_mode = st.selectbox(
            "후처리 방식",
            options=[
                ("📝 회의록 (3줄 요약 + 타임라인)", "meeting_summary"),
                ("📊 Summary (핵심 요약)", "summary"),
                ("💬 Q&A 형식 (질의응답)", "qa_format"),
                ("📢 발표자료 형식 (프레젠테이션)", "presentation_format")
            ],
            format_func=lambda x: x[0],
            help="전사된 내용을 AI로 재구성 (비용 추가 발생)",
            key="audio_gpt_mode_step3"
        )

        # 후처리 API 키 입력 (전사 엔진과 다른 경우)
        post_api_key = None
        if post_engine[1] == "openai":
            # OpenAI 키가 필요
            if 'transcription_api_key' in st.session_state and st.session_state.get('transcription_engine') == 'whisper':
                # 전사에서 Whisper를 사용했으면 키 재사용
                post_api_key = st.session_state['transcription_api_key']
                st.info("ℹ️ 전사에 사용한 OpenAI API 키를 재사용합니다.")
            else:
                # 새로 입력 받기
                post_api_key = st.text_input(
                    "OpenAI API Key (후처리용)",
                    type="password",
                    placeholder="sk-...",
                    key="audio_post_openai_key"
                )
        else:  # Gemini
            # Gemini 키가 필요
            if 'transcription_api_key' in st.session_state and st.session_state.get('transcription_engine') == 'gemini':
                # 전사에서 Gemini를 사용했으면 키 재사용
                post_api_key = st.session_state['transcription_api_key']
                st.info("ℹ️ 전사에 사용한 Gemini API 키를 재사용합니다.")
            else:
                # 새로 입력 받기
                post_api_key = st.text_input(
                    "Gemini API Key (후처리용)",
                    type="password",
                    placeholder="AI...",
                    key="audio_post_gemini_key"
                )

        # 후처리 실행 버튼
        if st.button("🤖 AI 후처리 시작", use_container_width=True, type="secondary", key="audio_gpt_process_btn"):
            if not post_api_key:
                st.error("⚠️ API Key가 필요합니다")
            else:
                with st.spinner(f"🤖 {post_engine[0]} 후처리 중..."):
                    try:
                        # 현재 편집된 텍스트 가져오기
                        current_text = st.session_state.get('audio_result_text', result_text)

                        # AI 후처리 실행
                        processed_text = utils_audio._gpt_postprocess(
                            raw_text=current_text,
                            mode=gpt_mode[1],
                            model=post_model,
                            api_key=post_api_key,
                            api_type=post_engine[1]
                        )

                        # 결과를 새로운 세션 스테이트에 저장
                        st.session_state['gpt_processed_result'] = processed_text
                        st.success(f"✅ {post_engine[0]} 후처리 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ 후처리 중 오류 발생: {str(e)}")

        # GPT 후처리 결과 표시
        if 'gpt_processed_result' in st.session_state and st.session_state['gpt_processed_result']:
            st.markdown("#### 📊 GPT 후처리 결과")
            with st.container(border=True):
                st.markdown(st.session_state['gpt_processed_result'])

            # GPT 결과 다운로드
            col_gpt_download1, col_gpt_download2 = st.columns(2)
            with col_gpt_download1:
                st.download_button(
                    label="📥 후처리 결과 다운로드 (TXT)",
                    data=st.session_state['gpt_processed_result'],
                    file_name=f"processed_{uploaded_audio.name.split('.')[0] if uploaded_audio else 'result'}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with col_gpt_download2:
                st.download_button(
                    label="📥 후처리 결과 다운로드 (MD)",
                    data=st.session_state['gpt_processed_result'],
                    file_name=f"processed_{uploaded_audio.name.split('.')[0] if uploaded_audio else 'result'}.md",
                    mime="text/markdown",
                    use_container_width=True
                )

        # ============================================
        # 다운로드 & 초기화
        # ============================================
        st.markdown("---")
        st.markdown("#### 💾 파일 저장")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                label="📥 전사 결과 (TXT)",
                data=st.session_state.get('audio_result_text', result_text),
                file_name=f"transcription_{uploaded_audio.name.split('.')[0] if uploaded_audio else 'result'}.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="📥 전사 결과 (MD)",
                data=st.session_state.get('audio_result_text', result_text),
                file_name=f"transcription_{uploaded_audio.name.split('.')[0] if uploaded_audio else 'result'}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col3:
            if st.button("🔄 초기화", use_container_width=True, type="secondary"):
                # 모든 관련 세션 스테이트 초기화
                if 'transcription_result' in st.session_state:
                    del st.session_state['transcription_result']
                if 'gpt_processed_result' in st.session_state:
                    del st.session_state['gpt_processed_result']
                if 'audio_result_text' in st.session_state:
                    del st.session_state['audio_result_text']
                st.rerun()

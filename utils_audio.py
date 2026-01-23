import re
from openai import OpenAI

def transcribe_audio(uploaded_file, api_key=None):
    """
    오디오 파일을 텍스트로 전사 (Whisper API 사용)
    추임새 등 불필요한 표현 제거

    Args:
        uploaded_file: Streamlit UploadedFile 객체
        api_key: OpenAI API 키

    Returns:
        str: 전사된 텍스트 (추임새 제거됨)
    """
    if uploaded_file is None:
        return ""

    if not api_key:
        return "[오류: OpenAI API 키가 필요합니다]"

    try:
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=api_key)

        # 파일을 메모리에서 직접 전송
        uploaded_file.seek(0)

        # Streamlit UploadedFile을 OpenAI가 인식할 수 있는 형식으로 변환
        # 튜플 형식: (filename, file_content, content_type)
        file_tuple = (uploaded_file.name, uploaded_file.read(), uploaded_file.type)

        # Whisper API 호출
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=file_tuple,
            language="ko",  # 한국어 명시
            response_format="text"
        )

        # 전사 결과
        transcribed_text = transcript if isinstance(transcript, str) else transcript.text

        # 추임새 제거 (한국어 추임새 패턴)
        filler_words = [
            r'\b아+\s*', r'\b어+\s*', r'\b음+\s*', r'\b으+\s*',
            r'\b그+\s*', r'\b저+\s*', r'\b뭐+\s*',
            r'\b이제\s*', r'\b그니까\s*', r'\b그러니까\s*',
            r'\b어\.\.\.\s*', r'\b음\.\.\.\s*', r'\b아\.\.\.\s*',
            r'\b그게\s*', r'\b저기\s*', r'\b이거\s*',
            r'\b좀\s*', r'\b막\s*', r'\b약간\s*'
        ]

        cleaned_text = transcribed_text
        for pattern in filler_words:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)

        # 중복 공백 및 불필요한 줄바꿈 제거
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        # 문장 단위로 정리 (선택적)
        cleaned_text = re.sub(r'\s*\.\s*', '. ', cleaned_text)
        cleaned_text = re.sub(r'\s*,\s*', ', ', cleaned_text)

        return f"### [오디오 전사 결과: {uploaded_file.name}]\n\n{cleaned_text}\n\n"

    except Exception as e:
        return f"[오디오 전사 오류: {uploaded_file.name} - {str(e)}]"
    finally:
        # 파일 포인터 초기화
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)

def is_audio_file(filename):
    """
    파일이 오디오 파일인지 확인

    Args:
        filename: 파일명

    Returns:
        bool: 오디오 파일 여부
    """
    audio_extensions = ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm', 'ogg', 'flac']
    file_ext = filename.split('.')[-1].lower()
    return file_ext in audio_extensions

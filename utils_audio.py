import re
import io
from openai import OpenAI
from pydub import AudioSegment

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
        file_content = uploaded_file.read()

        # 파일 확장자 추출 및 검증
        original_filename = uploaded_file.name
        file_ext = original_filename.split('.')[-1].lower()

        # 지원되는 확장자 목록
        supported_formats = ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']

        if file_ext not in supported_formats:
            return f"[오류: 지원되지 않는 파일 형식입니다. 지원 형식: {', '.join(supported_formats)}]"

        # Apple 기기 m4a 파일 등 특수 코덱 처리
        # m4a 파일의 경우 mp3로 변환 시도
        if file_ext == 'm4a':
            try:
                # AudioSegment를 사용하여 m4a를 mp3로 변환
                audio = AudioSegment.from_file(io.BytesIO(file_content), format="m4a")
                mp3_buffer = io.BytesIO()
                audio.export(mp3_buffer, format="mp3")
                mp3_buffer.seek(0)
                file_content = mp3_buffer.read()
                file_ext = "mp3"
            except Exception:
                # 변환 실패 시 원본 파일 그대로 시도
                pass

        # BytesIO 객체로 변환하고 MIME type과 함께 파일명 설정
        audio_file = io.BytesIO(file_content)
        audio_file.name = f"audio.{file_ext}"  # 단순화된 파일명 사용

        # MIME type 매핑
        mime_types = {
            'mp3': 'audio/mpeg',
            'mp4': 'audio/mp4',
            'm4a': 'audio/mp4',
            'wav': 'audio/wav',
            'webm': 'audio/webm',
            'ogg': 'audio/ogg',
            'flac': 'audio/flac',
            'mpeg': 'audio/mpeg',
            'mpga': 'audio/mpeg',
            'oga': 'audio/ogg'
        }

        # Whisper API 호출 (파일을 튜플로 전달하여 MIME type 명시)
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio_file.name, audio_file, mime_types.get(file_ext, 'audio/mpeg')),
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

        return f"### [오디오 전사 결과: {original_filename}]\n\n{cleaned_text}\n\n"

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

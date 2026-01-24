import os
import re
import io
import gc
import math
import json
import shutil
import base64
import tempfile
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple, Iterator

from openai import OpenAI

# Gemini 지원을 위한 선택적 import
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# =========================
# Utilities
# =========================

SUPPORTED_FORMATS = ["flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "oga", "ogg", "wav", "webm"]

def _ext(name: str) -> str:
    return (name.split(".")[-1] if "." in name else "").lower()

def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def _run(cmd: List[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr[:2000]}")

def _safe_seek(uploaded_file) -> None:
    try:
        uploaded_file.seek(0)
    except Exception:
        pass

def _write_uploaded_to_temp(uploaded_file, suffix: str) -> str:
    """
    Streamlit의 UploadedFile을 임시 파일로 저장.
    파일 내용을 읽은 후 즉시 핸들 정리.
    """
    _safe_seek(uploaded_file)
    # 파일 내용을 메모리로 읽기
    file_content = uploaded_file.read()

    # 임시 파일에 쓰기 (핸들을 즉시 닫음)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp_file.write(file_content)
        tmp_file.flush()
        return tmp_file.name
    finally:
        tmp_file.close()  # 명시적으로 닫기

def _get_duration_seconds(path: str) -> Optional[float]:
    # Uses ffprobe via ffmpeg install; if not available, returns None
    if not _has_ffmpeg():
        return None
    # ffprobe might not exist separately; ffmpeg typically ships it, but not always.
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        return None
    try:
        return float(p.stdout.strip())
    except Exception:
        return None

def _format_timestamp(t: float) -> str:
    # mm:ss
    m = int(t // 60)
    s = int(t % 60)
    return f"{m:02d}:{s:02d}"

def _convert_to_wav_16k_mono(input_path: str) -> str:
    """
    Convert any supported audio/video container to a consistent PCM WAV 16kHz mono.
    This significantly reduces format-related edge cases.
    """
    if not _has_ffmpeg():
        # If ffmpeg isn't available, we just return the input.
        # Whisper can still handle many formats, but conversion is recommended.
        return input_path

    # 임시 파일 핸들을 즉시 닫아 Windows 파일 잠금 문제 방지
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    out_path = tmp_file.name
    tmp_file.close()

    _run([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        out_path
    ])
    return out_path

def _split_wav_by_duration(input_wav_path: str, chunk_seconds: int = 600) -> List[str]:
    """
    Split WAV into chunks using ffmpeg's segment muxer.
    chunk_seconds default: 10 minutes
    """
    if not _has_ffmpeg():
        # No safe split without ffmpeg/pydub; return as single chunk
        return [input_wav_path]

    out_dir = tempfile.mkdtemp()
    out_pattern = os.path.join(out_dir, "chunk_%03d.wav")

    _run([
        "ffmpeg", "-y",
        "-i", input_wav_path,
        "-f", "segment",
        "-segment_time", str(chunk_seconds),
        "-c", "copy",
        out_pattern
    ])

    # Collect in order
    chunks = []
    i = 0
    while True:
        p = os.path.join(out_dir, f"chunk_{i:03d}.wav")
        if not os.path.exists(p):
            break
        chunks.append(p)
        i += 1

    return chunks if chunks else [input_wav_path]


# =========================
# Whisper transcription (with timestamps)
# =========================

@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None

def _transcribe_whisper_verbose(
    client: OpenAI,
    file_path: str,
    original_filename: str,
    language: str = "ko"
) -> Dict[str, Any]:
    """
    Calls Whisper with verbose_json to get segments/timestamps.
    IMPORTANT: pass (filename, fileobj) so format detection doesn't fail.
    """
    # 파일 내용을 메모리로 읽어서 사용 (파일 핸들 누수 방지)
    with open(file_path, "rb") as f:
        file_content = f.read()

    # io.BytesIO로 파일 객체 생성하여 API 호출
    file_obj = io.BytesIO(file_content)
    resp = client.audio.transcriptions.create(
        model="whisper-1",
        file=(original_filename, file_obj),  # <-- 핵심: 파일명 포함
        language=language,
        response_format="verbose_json",
        timestamp_granularities=["segment"],
    )
    file_obj.close()  # 명시적으로 닫기

    # SDK가 dict/obj 형태로 올 수 있어 안전하게 변환
    if isinstance(resp, dict):
        return resp
    # pydantic-like object
    try:
        return resp.model_dump()
    except Exception:
        # last resort
        return json.loads(resp.model_dump_json())

def _collect_segments(verbose_json: Dict[str, Any], time_offset: float = 0.0) -> List[Segment]:
    segs = []
    for s in verbose_json.get("segments", []) or []:
        start = float(s.get("start", 0.0)) + time_offset
        end = float(s.get("end", 0.0)) + time_offset
        text = (s.get("text") or "").strip()
        if text:
            segs.append(Segment(start=start, end=end, text=text))
    return segs


def _transcribe_gemini(
    file_path: str,
    api_key: str,
    model: str = "gemini-3-flash-preview",
    language: str = "ko",
    include_timestamps: bool = False,
    start_offset_sec: float = 0.0,
    total_duration_sec: Optional[float] = None,
    batch_size_sec: int = 600,
    batch_threshold_sec: int = 900
) -> Iterator[str]:
    """
    Gemini를 사용한 오디오 전사.
    Generator function yielding text chunks.
    """
    if not GEMINI_AVAILABLE:
        raise RuntimeError("google-generativeai 패키지가 설치되지 않았습니다. pip install google-generativeai")

    # Gemini 설정
    genai.configure(api_key=api_key)

    # 파일 MIME 타입 결정
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {
        ".mp3": "audio/mp3",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".mpeg": "audio/mpeg",
        ".mpga": "audio/mpeg",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac"
    }
    mime_type = mime_types.get(ext, "audio/mpeg")

    # [변경] 대용량 파일 처리를 위해 File API 사용 (Base64 제한 해결)
    try:
        uploaded_file = genai.upload_file(file_path, mime_type=mime_type)
        
        # 처리 대기 (Audio는 보통 즉시 처리되지만 안전장치)
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai.get_file(uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            raise ValueError("Gemini File Upload Failed")
            
    except Exception as e:
        raise RuntimeError(f"Gemini 파일 업로드 실패: {str(e)}")

    # Gemini 모델 초기화
    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction="당신은 전문적인 음성 전사 전문가입니다. 오디오 내용을 정확하게 한국어로 전사하고, 화자를 명확히 구분해주세요."
    )

    # [NEW] 긴 파일 자동 배치 처리 (FFmpeg 미설치 대응)
    # 1. 재생 시간 확인 (모델에게 질의)
    total_duration = total_duration_sec or 0.0
    if total_duration <= 0.0:
        try:
            # ??? ???????????
            dur_prompt = "??????????????? ??? ?????'??seconds)' ??????????? ???????? ??? ??? ????????????? (?? 1234.5)"
            dur_resp = gemini_model.generate_content([dur_prompt, uploaded_file])
            # ??? ???
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", dur_resp.text)
            if nums:
                total_duration = float(nums[0])
        except Exception:
            pass # ??? ????? ????????

    # 2. 배치 처리 (15분(900초) 초과 시 10분 단위 논리적 분할)
        if total_duration > batch_threshold_sec:
        current_pos = 0.0
        
        while current_pos < total_duration:
            end_pos = min(current_pos + batch_size_sec, total_duration)
            
            # 시간 포맷팅
            t_start_str = _format_timestamp(current_pos)
            t_end_str = _format_timestamp(end_pos)
            
            # 타임스탬프 계산 (전체 오프셋 + 현재 청크 오프셋)
            chunk_start_time = start_offset_sec + current_pos
            chunk_start_str = _format_timestamp(chunk_start_time)
            
            # 배치 프롬프트
            batch_prompt = f"""
            오디오 파일의 **{t_start_str} 부터 {t_end_str} 까지의 구간만** 전사해주세요.
            
            요구사항:
            - 언어: {language}
            - 지정된 구간의 내용만 빠짐없이 전사 (이전/이후 내용 무시)
            - 화자 분리 (화자 1, 화자 2...)
            - 자연스러운 문단 구분
            """
            
            if include_timestamps:
                batch_prompt += f"\n- 각 문장 시작에 [MM:SS] 형식 타임스탬프 필수\n- 타임스탬프는 **{chunk_start_str}** 부터 시작하여 흐름에 맞게 작성"
            
            batch_prompt += "\n\n결과만 출력하세요."
            
            try:
                resp = gemini_model.generate_content([batch_prompt, uploaded_file])
                if resp.text:
                    yield resp.text.strip()
            except Exception as e:
                yield f"[{t_start_str}~{t_end_str} 처리 중 오류: {str(e)}]"
            
            current_pos += batch_size_sec
            time.sleep(2) # Rate limit 완화
            
        try:
            uploaded_file.delete()
        except:
            pass
            
        return

    # 타임스탬프 요청 문구
    timestamp_instruction = ""
    if include_timestamps:
        start_time_str = _format_timestamp(start_offset_sec)
        timestamp_instruction = (
            f"- 각 문장 또는 발화의 시작 부분에 [MM:SS] 형식으로 타임스탬프를 반드시 표시해주세요.\n"
            f"- 주의: 이 오디오 클립은 전체 녹음의 {start_time_str} 부터 시작됩니다. 타임스탬프를 작성할 때 {start_time_str}를 기준으로 시간을 더해서 작성해주세요. (예: 시작 직후 발화 -> [{start_time_str}] ...)"
        )

    # 프롬프트
    prompt = f"""
    제공된 오디오 파일을 분석하여 음성 내용을 정확하게 전사해주세요.

    요구사항:
    - 언어: 한국어
    - 모든 대화와 내용을 빠짐없이 전사
    - 자연스러운 문단 구분
    - 화자가 바뀔 때마다 줄바꿈을 하고, "화자 1:", "화자 2:" 등으로 명확히 구분 (가능한 경우)
    {timestamp_instruction}

    전사 결과만 출력하고, 추가 설명은 하지 마세요.
    """

    try:
        # API 호출 (파일 객체 전달)
        response = gemini_model.generate_content([prompt, uploaded_file])
        yield response.text.strip()
    finally:
        # 파일 삭제 (리소스 정리)
        try:
            uploaded_file.delete()
        except Exception:
            pass


# =========================
# (1) 문단 단위 정리: paragraphing
# =========================

def _paragraphize(
    segments: List[Segment],
    gap_threshold: float = 1.2,
    max_chars: int = 140
) -> List[List[Segment]]:
    """
    그룹 기준:
      - 이전 세그먼트 종료~다음 시작 gap이 크면 문단 분리
      - 문단 누적 글자수가 max_chars 넘어가면 문단 분리
    """
    paras: List[List[Segment]] = []
    cur: List[Segment] = []
    cur_chars = 0

    for i, seg in enumerate(segments):
        if not cur:
            cur = [seg]
            cur_chars = len(seg.text)
            continue

        gap = seg.start - cur[-1].end
        if gap >= gap_threshold or cur_chars + len(seg.text) > max_chars:
            paras.append(cur)
            cur = [seg]
            cur_chars = len(seg.text)
        else:
            cur.append(seg)
            cur_chars += len(seg.text) + 1

    if cur:
        paras.append(cur)
    return paras

def _render_paragraphs(paras: List[List[Segment]], include_timestamps: bool = True) -> str:
    lines = []
    for para in paras:
        start = para[0].start
        end = para[-1].end
        text = " ".join(s.text.strip() for s in para).strip()
        if include_timestamps:
            lines.append(f"[{_format_timestamp(start)}–{_format_timestamp(end)}] {text}")
        else:
            lines.append(text)
    return "\n\n".join(lines).strip()


# =========================
# (2) 화자 분리(가능한 선까지): optional diarization
# =========================
"""
Whisper 자체는 "진짜" 화자분리를 제공하지 않습니다.
아래는 선택 기능입니다.

옵션 A (권장): pyannote.audio + HuggingFace 토큰으로 diarization 수행 후 세그먼트에 speaker 라벨 정렬
- 환경에 pyannote.audio 설치 + HF_TOKEN 필요

옵션 B (기본): diarization 불가 → 단일 화자(또는 미표기)
"""

def _try_diarize_with_pyannote(wav_path: str) -> Optional[List[Tuple[float, float, str]]]:
    """
    Returns list of (start, end, speaker_label).
    Requires:
      pip install pyannote.audio
      export HF_TOKEN=...
    """
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        return None

    try:
        from pyannote.audio import Pipeline  # type: ignore
    except Exception:
        return None

    try:
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=hf_token)
        diar = pipeline(wav_path)
        turns = []
        for turn, _, speaker in diar.itertracks(yield_label=True):
            turns.append((float(turn.start), float(turn.end), str(speaker)))
        return turns or None
    except Exception:
        return None

def _assign_speakers_to_segments(
    segments: List[Segment],
    diar_turns: List[Tuple[float, float, str]]
) -> List[Segment]:
    """
    Assign speaker by segment midpoint overlapping diarization turns.
    """
    if not diar_turns:
        return segments

    # For speed, keep turns in order
    j = 0
    for seg in segments:
        mid = (seg.start + seg.end) / 2.0
        while j < len(diar_turns) and diar_turns[j][1] < mid:
            j += 1
        # Check current and previous turn for overlap
        cand = []
        if 0 <= j < len(diar_turns):
            cand.append(diar_turns[j])
        if j - 1 >= 0:
            cand.append(diar_turns[j - 1])

        best = None
        best_ov = 0.0
        for (a, b, spk) in cand:
            ov = max(0.0, min(seg.end, b) - max(seg.start, a))
            if ov > best_ov:
                best_ov = ov
                best = spk
        seg.speaker = best if best_ov > 0 else seg.speaker
    return segments

def _render_with_speakers(paras: List[List[Segment]], include_timestamps: bool = True) -> str:
    """
    If speakers exist, each paragraph is prefixed with the dominant speaker label.
    """
    out = []
    for para in paras:
        speaker = None
        # dominant speaker by total overlap length
        counts: Dict[str, float] = {}
        for s in para:
            if s.speaker:
                counts[s.speaker] = counts.get(s.speaker, 0.0) + (s.end - s.start)
        if counts:
            speaker = max(counts.items(), key=lambda x: x[1])[0]

        start = para[0].start
        end = para[-1].end
        text = " ".join(s.text.strip() for s in para).strip()

        prefix = ""
        if speaker:
            prefix += f"{speaker}: "
        if include_timestamps:
            prefix = f"[{_format_timestamp(start)}–{_format_timestamp(end)}] " + prefix

        out.append(prefix + text)
    return "\n\n".join(out).strip()


# =========================
# 추임새/정리 (기존 로직 개선)
# =========================

FILLER_PATTERNS = [
    # 한국어는 \b 경계가 약하므로 "문장 시작/공백/줄바꿈" 중심으로 제거
    r'(^|\s)(아+)(?=\s)',
    r'(^|\s)(어+)(?=\s)',
    r'(^|\s)(음+)(?=\s)',
    r'(^|\s)(으+)(?=\s)',
    r'(^|\s)(그+)(?=\s)',
    r'(^|\s)(저+)(?=\s)',
    r'(^|\s)(뭐+)(?=\s)',
    r'(^|\s)(이제)(?=\s)',
    r'(^|\s)(그니까|그러니까)(?=\s)',
    r'(^|\s)(그게|저기)(?=\s)',
    r'(^|\s)(좀|막|약간)(?=\s)',
]

def _clean_text_basic(text: str) -> str:
    t = text
    for pat in FILLER_PATTERNS:
        t = re.sub(pat, r'\1', t, flags=re.IGNORECASE)
    # 공백/줄바꿈 정리
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    t = t.strip()
    return t


# =========================
# (4) GPT 후처리: 요약/정리/코딩용 변환 등
# =========================

def _gpt_postprocess(
    raw_text: str,
    mode: str = "clean",  # clean | summary | atlas_codebook
    model: str = "gpt-4o-mini",
    api_key: str = None,
    api_type: str = "openai"  # openai | gemini
) -> str:
    """
    mode:
      - clean: 맞춤법/띄어쓰기/문장부호 최소 정리 + 의미 유지
      - summary: 핵심 요약(불릿) + 결정사항/액션아이템
      - atlas_codebook: 질적코딩용(주제/코드 후보) 형태로 정리

    api_type:
      - openai: OpenAI GPT 모델 사용
      - gemini: Google Gemini 모델 사용
    """
    if mode == "clean":
        instruction = (
            "다음 한국어 전사 텍스트를 의미를 바꾸지 말고, "
            "띄어쓰기/문장부호를 자연스럽게 다듬고, 중복 표현을 최소화해 주세요. "
            "새로운 사실을 추가하지 마세요."
        )
    elif mode == "summary":
        instruction = (
            "다음 한국어 전사 텍스트를 바탕으로 "
            "1) 핵심 요약(불릿 5~10개) "
            "2) 결정사항(있으면) "
            "3) 액션아이템(담당/기한이 언급되면 포함) "
            "형태로 정리해 주세요. 없는 항목은 '없음'으로 표시하세요. "
            "새로운 사실을 추가하지 마세요."
        )
    elif mode == "atlas_codebook":
        instruction = (
            "다음 한국어 전사 텍스트를 질적 연구 코딩에 바로 쓰기 좋게 정리해 주세요. "
            "출력 형식:\n"
            "- 코드 후보 목록(10~25개): 코드명 / 정의 / 예시 인용(짧게)\n"
            "- 잠정 상위범주(3~7개): 범주명 / 포함 코드\n"
            "텍스트에 없는 사실을 만들지 말고, 인용은 원문 표현을 최대한 유지하세요."
        )
    elif mode == "meeting_summary":
        instruction = (
            "다음은 회의 녹음의 전사 텍스트입니다. (타임스탬프 포함)\n"
            "이 내용을 바탕으로 다음 형식의 회의록을 작성해주세요.\n\n"
            "1. 📌 3줄 핵심 요약\n"
            "   - 전체 회의의 가장 중요한 결론이나 내용을 3가지로 요약 (개조식)\n\n"
            "2. 📝 상세 요약\n"
            "   - 주요 주제가 바뀌는 구간을 나누어 정리\n"
            "   - 각 구간의 시작과 끝 시간을 [mm:ss ~ mm:ss] 형식으로 헤더에 표시 (예: [00:00 ~ 05:30] 주제)\n"
            "   - 내용은 Q&A 형식(Q: 질문, A: 답변) 또는 핵심 내용 서술형으로 상세히 정리\n"
            "   - 전사된 내용의 팩트를 기반으로 작성하되, 문장은 깔끔하게 다듬을 것"
        )
    else:
        instruction = "다음 텍스트를 의미를 바꾸지 말고 정리해 주세요."

    # Gemini 모델 사용
    if api_type == "gemini":
        if not GEMINI_AVAILABLE:
            raise RuntimeError("google-generativeai 패키지가 설치되지 않았습니다.")

        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=instruction
        )
        response = gemini_model.generate_content(raw_text)
        return response.text.strip()

    # OpenAI 모델 사용 (기본)
    else:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": raw_text},
            ],
        )
        # SDK 반환 안전 처리
        try:
            return resp.choices[0].message.content.strip()
        except Exception:
            return str(resp).strip()


# =========================
# Main API for Streamlit
# =========================

def transcribe_audio(
    uploaded_file,
    api_key: Optional[str] = None,
    language: str = "ko",
    chunk_seconds: int = 600,        # (3) 긴 파일 자동 분할: 10분 단위 기본
    do_diarization: bool = False,    # (2) 화자 분리 시도 (기본 False - HF_TOKEN 필요)
    include_timestamps: bool = True, # (1) 문단에 타임스탬프 표시
    remove_fillers: bool = True,     # 추임새 제거
    gpt_mode: Optional[str] = None,  # (4) "clean"|"summary"|"atlas_codebook"|None
    gpt_model: str = "gpt-5.2",
    engine: str = "whisper",         # 전사 엔진: "whisper" | "gemini"
    gemini_model: str = "gemini-3-flash-preview",  # Gemini 모델
) -> Iterator[str]:
    """
    1) 문단 정리: 세그먼트 기반 문단화(타임스탬프 포함 옵션)
    2) 화자 분리: pyannote 가능 시 자동 라벨링(불가 시 미표기)
    3) 긴 파일 분할: ffmpeg 있으면 chunk_seconds로 자동 분할 후 합치기
    4) GPT 후처리: clean/summary/atlas_codebook 모드 제공
    5) 엔진 선택: Whisper (OpenAI) 또는 Gemini (Google)
    """
    if uploaded_file is None:
        return

    if not api_key:
        yield "[오류: API 키가 필요합니다]"
        return

    original_filename = getattr(uploaded_file, "name", "audio")
    file_ext = _ext(original_filename)

    if file_ext not in SUPPORTED_FORMATS:
        yield f"[오류: 지원되지 않는 파일 형식입니다. 지원 형식: {', '.join(SUPPORTED_FORMATS)}]"
        return

    temp_in = None
    temp_wav = None
    chunk_paths: List[str] = []
    chunk_dirs: set = set()

    try:
        # 0) 업로드 파일을 먼저 임시 파일로 저장 (파일 핸들 즉시 해제)
        temp_in = _write_uploaded_to_temp(uploaded_file, suffix=f".{file_ext}")
        # 업로드 파일 포인터를 바로 리셋 (더 이상 사용하지 않음)
        _safe_seek(uploaded_file)

        # (안정화) 16k mono wav로 변환 (ffmpeg 없으면 원본 사용)
        # Gemini, Whisper 모두 WAV가 안정적이며, 분할(Chunking)을 위해 필요함
        temp_wav = _convert_to_wav_16k_mono(temp_in)
        total_duration_sec = _get_duration_seconds(temp_wav)

        # (3) 긴 파일 분할 (Whisper, Gemini 공통 적용)
        chunk_paths = _split_wav_by_duration(temp_wav, chunk_seconds=chunk_seconds)

        # Gemini 엔진 사용
        if engine == "gemini":
            for i, cp in enumerate(chunk_paths):
                offset_sec = i * chunk_seconds
                # _transcribe_gemini is now a generator
                for part_text in _transcribe_gemini(
                    file_path=cp,
                    api_key=api_key,
                    model=gemini_model,
                    language=language,
                    include_timestamps=include_timestamps,
                    start_offset_sec=offset_sec,
                    total_duration_sec=total_duration_sec
                ):
                    yield _clean_text_basic(part_text) if remove_fillers else part_text

        # Whisper 엔진 사용 (기본)
        else:
            client = OpenAI(api_key=api_key)

            # (2) 화자 분리 시도 (전체 파일에 대해 먼저 수행)
            diar_turns = None
            if do_diarization:
                diar_turns = _try_diarize_with_pyannote(temp_wav)

            offset = 0.0

            # duration 기반 오프셋(가능하면 정확)
            # ffprobe가 없으면 offset은 chunk_seconds로 근사
            for idx, cp in enumerate(chunk_paths):
                # 1) 청크 전사
                verbose = _transcribe_whisper_verbose(
                    client=client,
                    file_path=cp,
                original_filename=os.path.basename(cp),  # 실제 파일(청크)의 확장자에 맞게 전달 (오류 해결)
                    language=language
                )
                
                # 2) 세그먼트 수집 및 오프셋 적용
                chunk_segments = _collect_segments(verbose, time_offset=offset)
                
                # 3) 화자 할당 (해당 구간에 맞는 diarization 결과 매핑)
                if diar_turns:
                    chunk_segments = _assign_speakers_to_segments(chunk_segments, diar_turns)

                # 4) 문단 정리 및 렌더링
                paras = _paragraphize(chunk_segments, gap_threshold=1.2, max_chars=160)
                
                if any(s.speaker for s in chunk_segments):
                    chunk_body = _render_with_speakers(paras, include_timestamps=include_timestamps)
                else:
                    chunk_body = _render_paragraphs(paras, include_timestamps=include_timestamps)

                # 5) 결과 Yield
                if remove_fillers:
                    yield _clean_text_basic(chunk_body)
                else:
                    yield chunk_body

                dur = _get_duration_seconds(cp)
                if dur is not None:
                    offset += dur
                else:
                    offset += float(chunk_seconds)

        # End of generator

    except Exception as e:
        yield f"[오디오 전사 오류: {original_filename} - {str(e)}]"

    finally:
        # 0. 가비지 컬렉션을 먼저 실행하여 파일 핸들 해제 확인
        import time
        gc.collect()
        time.sleep(0.05)  # 짧은 대기로 OS가 핸들을 정리할 시간 제공

        # 1. 임시 파일 삭제 (메인 임시 파일들)
        for p in [temp_in, temp_wav]:
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except PermissionError:
                    # Windows에서 파일이 아직 사용 중일 수 있음 - 짧은 대기 후 재시도
                    time.sleep(0.1)
                    try:
                        os.unlink(p)
                    except Exception:
                        pass
                except Exception:
                    pass

        # 2. 청크 파일들 삭제 및 디렉토리 수집
        for cp in chunk_paths:
            if cp and os.path.exists(cp):
                # 디렉토리 경로 기억
                parent_dir = os.path.dirname(cp)
                if parent_dir:
                    chunk_dirs.add(parent_dir)
                # 청크 파일 삭제
                try:
                    os.unlink(cp)
                except PermissionError:
                    time.sleep(0.1)
                    try:
                        os.unlink(cp)
                    except Exception:
                        pass
                except Exception:
                    pass

        # 3. 청크 디렉토리 삭제
        for d in chunk_dirs:
            if d and os.path.exists(d) and os.path.isdir(d):
                try:
                    # 디렉토리가 비어있는지 확인
                    if not os.listdir(d):
                        os.rmdir(d)
                except Exception:
                    pass

        # 4. 마지막 가비지 컬렉션 실행
        gc.collect()


def is_audio_file(filename: str) -> bool:
    return _ext(filename) in SUPPORTED_FORMATS

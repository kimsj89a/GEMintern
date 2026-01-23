import os
import re
import io
import gc
import math
import json
import shutil
import tempfile
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

from openai import OpenAI


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

def _format_timestamp(t: float) -> str:
    # mm:ss
    m = int(t // 60)
    s = int(t % 60)
    return f"{m:02d}:{s:02d}"

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
    client: OpenAI,
    raw_text: str,
    mode: str = "clean",  # clean | summary | atlas_codebook
    model: str = "gpt-4o-mini",
) -> str:
    """
    mode:
      - clean: 맞춤법/띄어쓰기/문장부호 최소 정리 + 의미 유지
      - summary: 핵심 요약(불릿) + 결정사항/액션아이템
      - atlas_codebook: 질적코딩용(주제/코드 후보) 형태로 정리
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
    else:
        instruction = "다음 텍스트를 의미를 바꾸지 말고 정리해 주세요."

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
    gpt_model: str = "gpt-4o-mini",
) -> str:
    """
    1) 문단 정리: 세그먼트 기반 문단화(타임스탬프 포함 옵션)
    2) 화자 분리: pyannote 가능 시 자동 라벨링(불가 시 미표기)
    3) 긴 파일 분할: ffmpeg 있으면 chunk_seconds로 자동 분할 후 합치기
    4) GPT 후처리: clean/summary/atlas_codebook 모드 제공
    """
    if uploaded_file is None:
        return ""

    if not api_key:
        return "[오류: OpenAI API 키가 필요합니다]"

    original_filename = getattr(uploaded_file, "name", "audio")
    file_ext = _ext(original_filename)

    if file_ext not in SUPPORTED_FORMATS:
        return f"[오류: 지원되지 않는 파일 형식입니다. 지원 형식: {', '.join(SUPPORTED_FORMATS)}]"

    client = OpenAI(api_key=api_key)

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
        temp_wav = _convert_to_wav_16k_mono(temp_in)

        # (3) 긴 파일 분할
        chunk_paths = _split_wav_by_duration(temp_wav, chunk_seconds=chunk_seconds)

        # 1) 각 청크 전사 + 세그먼트 수집(시간 오프셋 누적)
        all_segments: List[Segment] = []
        offset = 0.0

        # duration 기반 오프셋(가능하면 정확)
        # ffprobe가 없으면 offset은 chunk_seconds로 근사
        for idx, cp in enumerate(chunk_paths):
            verbose = _transcribe_whisper_verbose(
                client=client,
                file_path=cp,
                original_filename=original_filename,  # 원래 파일명 전달
                language=language
            )
            segs = _collect_segments(verbose, time_offset=offset)
            all_segments.extend(segs)

            dur = _get_duration_seconds(cp)
            if dur is not None:
                offset += dur
            else:
                offset += float(chunk_seconds)

        # (2) 화자 분리 시도
        if do_diarization:
            diar_turns = _try_diarize_with_pyannote(temp_wav)
            if diar_turns:
                all_segments = _assign_speakers_to_segments(all_segments, diar_turns)

        # (1) 문단 단위 정리
        paras = _paragraphize(all_segments, gap_threshold=1.2, max_chars=160)

        if any(s.speaker for s in all_segments):
            body = _render_with_speakers(paras, include_timestamps=include_timestamps)
        else:
            body = _render_paragraphs(paras, include_timestamps=include_timestamps)

        # 기본 텍스트 클린(추임새 제거 + 공백 정리)
        if remove_fillers:
            body_cleaned = _clean_text_basic(body)
        else:
            body_cleaned = body

        # (4) GPT 후처리 옵션
        if gpt_mode:
            body_final = _gpt_postprocess(
                client=client,
                raw_text=body_cleaned,
                mode=gpt_mode,
                model=gpt_model
            )
        else:
            body_final = body_cleaned

        return f"### [오디오 전사 결과: {original_filename}]\n\n{body_final}\n"

    except Exception as e:
        return f"[오디오 전사 오류: {original_filename} - {str(e)}]"

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

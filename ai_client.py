"""
AI Client Adapter — Gemini / Anthropic 통합 어댑터.
모델명이 'claude-'로 시작하면 Anthropic API, 아니면 Gemini API로 라우팅.
기존 코드의 `genai.Client` 인터페이스(client.models.generate_content / generate_content_stream)를 유지.
"""
import os
import re
import time
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _parse_retry_delay(error_msg: str) -> float:
    """429 에러 메시지에서 retryDelay 추출. 없으면 기본 15초."""
    m = re.search(r'retry\s*(?:in|Delay[\'"]?\s*:\s*[\'"]?)\s*([\d.]+)', str(error_msg), re.IGNORECASE)
    if m:
        return min(float(m.group(1)) + 1, 60)
    return 15.0


def _get_anthropic_key() -> str:
    """Anthropic API key: env var → settings.json fallback."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        import json
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f).get("anthropic_api_key", "")
    except Exception:
        pass
    return ""


def _is_claude(model: str) -> bool:
    return model.startswith("claude-")


# ── Anthropic 응답 → Gemini 호환 래퍼 ──

class _AnthropicTextResponse:
    """Anthropic 응답을 genai 응답처럼 .text 로 접근 가능하게 래핑."""
    def __init__(self, text: str):
        self.text = text


class _AnthropicStreamChunk:
    """Anthropic 스트리밍 청크를 .text 로 접근 가능하게 래핑."""
    def __init__(self, text: str):
        self.text = text


# ── Gemini GenerateContentConfig → Anthropic 파라미터 변환 ──

def _translate_config(config, prompt_text: str):
    """GenerateContentConfig 객체를 Anthropic API 파라미터로 변환."""
    params = {}

    if config is None:
        return {"max_tokens": 8192}, None, prompt_text

    system_msg = None

    # system_instruction
    if hasattr(config, "system_instruction") and config.system_instruction:
        si = config.system_instruction
        if isinstance(si, list):
            system_msg = "\n".join(str(s) for s in si)
        else:
            system_msg = str(si)

    # temperature
    if hasattr(config, "temperature") and config.temperature is not None:
        params["temperature"] = config.temperature

    # max_output_tokens
    if hasattr(config, "max_output_tokens") and config.max_output_tokens:
        params["max_tokens"] = config.max_output_tokens
    else:
        params["max_tokens"] = 8192

    # response_mime_type="application/json" → 시스템 프롬프트에 JSON 지시 추가
    if hasattr(config, "response_mime_type") and config.response_mime_type == "application/json":
        json_instruction = (
            "\n\n[CRITICAL FORMAT INSTRUCTION] "
            "You MUST respond ONLY with valid JSON. No markdown fences, no explanation. "
            "Output raw JSON object directly."
        )
        if system_msg:
            system_msg += json_instruction
        else:
            system_msg = json_instruction

    # tools (google_search 등) → Claude에서는 무시
    # thinking_config → Claude에서는 무시

    return params, system_msg, prompt_text


# ── Models 네임스페이스 ──

class _ModelsNamespace:
    """client.models.generate_content() / generate_content_stream() 인터페이스 제공."""

    def __init__(self, gemini_client, anthropic_key: str):
        self._gemini = gemini_client
        self._anthropic_key = anthropic_key
        self._anthropic_client = None

    def _get_anthropic(self):
        if self._anthropic_client is None:
            import anthropic
            self._anthropic_client = anthropic.Anthropic(api_key=self._anthropic_key)
        return self._anthropic_client

    def generate_content(self, model: str, contents, config=None):
        if _is_claude(model):
            return self._claude_generate(model, contents, config)
        for attempt in range(MAX_RETRIES):
            try:
                return self._gemini.models.generate_content(model=model, contents=contents, config=config)
            except Exception as e:
                if '429' in str(e) and attempt < MAX_RETRIES - 1:
                    delay = _parse_retry_delay(str(e))
                    logger.warning(f"Rate limited (429), retrying in {delay:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                else:
                    raise

    def generate_content_stream(self, model: str, contents, config=None):
        if _is_claude(model):
            return self._claude_stream(model, contents, config)
        for attempt in range(MAX_RETRIES):
            try:
                return self._gemini.models.generate_content_stream(model=model, contents=contents, config=config)
            except Exception as e:
                if '429' in str(e) and attempt < MAX_RETRIES - 1:
                    delay = _parse_retry_delay(str(e))
                    logger.warning(f"Rate limited (429), retrying in {delay:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                else:
                    raise

    # ── Anthropic 구현 ──

    def _claude_generate(self, model: str, contents, config=None):
        """비스트리밍 호출 — 내부적으로 스트리밍으로 수집 (Anthropic 10분 제한 회피)."""
        client = self._get_anthropic()
        prompt_text = contents if isinstance(contents, str) else str(contents)
        params, system_msg, prompt_text = _translate_config(config, prompt_text)

        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            **params,
        }
        if system_msg:
            kwargs["system"] = system_msg

        full_text = ""
        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                full_text += text
        return _AnthropicTextResponse(full_text)

    def _claude_stream(self, model: str, contents, config=None):
        client = self._get_anthropic()
        prompt_text = contents if isinstance(contents, str) else str(contents)
        params, system_msg, prompt_text = _translate_config(config, prompt_text)

        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt_text}],
            **params,
        }
        if system_msg:
            kwargs["system"] = system_msg

        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield _AnthropicStreamChunk(text)


# ── 메인 AIClient ──

class AIClient:
    """genai.Client 드롭인 대체. 모델명에 따라 Gemini/Anthropic 라우팅."""

    def __init__(self, api_key: str):
        """
        Args:
            api_key: Gemini API key. Anthropic key는 env/settings에서 자동 로드.
        """
        self._gemini_client = genai.Client(api_key=api_key)
        anthropic_key = _get_anthropic_key()
        self.models = _ModelsNamespace(self._gemini_client, anthropic_key)


# ── 헬퍼: 상태 메시지 청크 생성 ──

def make_status_chunk(text: str):
    """진행 상황 알림용 청크 생성. Gemini types가 있으면 사용, 없으면 래퍼 반환."""
    try:
        return types.GenerateContentResponse(
            candidates=[types.Candidate(
                content=types.Content(parts=[types.Part(text=text)])
            )]
        )
    except Exception:
        return _AnthropicStreamChunk(text)

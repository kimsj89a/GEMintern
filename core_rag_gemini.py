"""
Gemini File Search API 연동 모듈.
Google 관리형 RAG — 청킹/임베딩/검색을 서버사이드에서 자동 처리.
ChromaDB 불필요, Railway에서도 동작.
"""
import json
import logging
import os
import time
from typing import Dict, List, Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

RAG_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_storage")


def _files_meta_path(project_name: str) -> str:
    return os.path.join(RAG_ROOT, project_name, "_gemini_files.json")


def _load_meta(project_name: str) -> Dict[str, dict]:
    """저장된 Gemini 파일 메타데이터 로드.
    Returns: {doc_name: {"uri": ..., "name": ..., "uploaded_at": ...}}
    """
    path = _files_meta_path(project_name)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_meta(project_name: str, meta: Dict[str, dict]):
    path = _files_meta_path(project_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def upload_doc(api_key: str, project_name: str,
               doc_name: str, content: str) -> Optional[str]:
    """문서를 Gemini Files API에 업로드.

    Returns: file URI 또는 None (실패 시)
    """
    client = genai.Client(api_key=api_key)
    meta = _load_meta(project_name)

    # 임시 파일로 저장 후 업로드
    import tempfile
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        result = client.files.upload(file=tmp_path, config={
            "display_name": f"{project_name}/{doc_name}",
        })

        meta[doc_name] = {
            "uri": result.uri,
            "name": result.name,
            "uploaded_at": time.time(),
        }
        _save_meta(project_name, meta)
        logger.info(f"Gemini Files: Uploaded '{doc_name}' → {result.uri}")
        return result.uri

    except Exception as e:
        logger.warning(f"Gemini Files: Upload failed for '{doc_name}': {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def upload_project_docs(api_key: str, project_name: str,
                        docs_dict: Dict[str, str]) -> dict:
    """프로젝트의 전체 문서를 Gemini Files에 업로드.

    Returns: {"uploaded": int, "failed": int, "skipped": int}
    """
    meta = _load_meta(project_name)
    uploaded, failed, skipped = 0, 0, 0

    for doc_name, content in docs_dict.items():
        if not content or not content.strip():
            skipped += 1
            continue

        # 이미 업로드됨 + 48시간 미만이면 스킵
        if doc_name in meta:
            age = time.time() - meta[doc_name].get("uploaded_at", 0)
            if age < 40 * 3600:  # 40시간 (만료 전 여유)
                skipped += 1
                continue

        uri = upload_doc(api_key, project_name, doc_name, content)
        if uri:
            uploaded += 1
        else:
            failed += 1

        # Rate limit 방지
        time.sleep(0.5)

    logger.info(
        f"Gemini Files: project '{project_name}' — "
        f"uploaded={uploaded}, skipped={skipped}, failed={failed}"
    )
    return {"uploaded": uploaded, "failed": failed, "skipped": skipped}


def get_file_parts(api_key: str, project_name: str,
                   selected_docs: Optional[List[str]] = None) -> List:
    """Gemini generate_content에 전달할 파일 파트 리스트 반환.

    만료된 파일은 자동 제외.
    Returns: [types.Part] 리스트 또는 빈 리스트
    """
    meta = _load_meta(project_name)
    if not meta:
        return []

    parts = []
    now = time.time()

    for doc_name, info in meta.items():
        if selected_docs and doc_name not in selected_docs:
            continue

        # 48시간 만료 체크
        age = now - info.get("uploaded_at", 0)
        if age > 47 * 3600:
            logger.debug(f"Gemini Files: '{doc_name}' expired, skipping")
            continue

        try:
            part = types.Part.from_uri(
                file_uri=info["uri"],
                mime_type="text/markdown",
            )
            parts.append(part)
        except Exception as e:
            logger.warning(f"Gemini Files: Failed to create part for '{doc_name}': {e}")

    return parts


def is_available(project_name: str) -> bool:
    """프로젝트에 유효한 Gemini Files가 있는지 확인."""
    meta = _load_meta(project_name)
    if not meta:
        return False
    now = time.time()
    return any(
        now - info.get("uploaded_at", 0) < 47 * 3600
        for info in meta.values()
    )


def refresh_expired(api_key: str, project_name: str,
                    docs_dict: Dict[str, str]) -> int:
    """만료된 파일을 재업로드. Returns: 재업로드 수."""
    meta = _load_meta(project_name)
    now = time.time()
    refreshed = 0

    for doc_name, info in list(meta.items()):
        age = now - info.get("uploaded_at", 0)
        if age > 40 * 3600 and doc_name in docs_dict:
            uri = upload_doc(api_key, project_name, doc_name, docs_dict[doc_name])
            if uri:
                refreshed += 1
            time.sleep(0.5)

    return refreshed


def delete_project_files(api_key: str, project_name: str):
    """프로젝트의 Gemini Files 메타데이터 삭제 (실제 파일은 48h 후 자동 만료)."""
    path = _files_meta_path(project_name)
    if os.path.exists(path):
        os.remove(path)

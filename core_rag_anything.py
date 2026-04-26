"""
RAG-Anything 어댑터 (Phase 2).

활성 조건: USE_RAG_ANYTHING=true 환경변수.
- ingest_file(): 업로드된 파일을 LightRAG working_dir 에 인덱싱 (MinerU/Docling 파싱)
- query(): hybrid 쿼리로 컨텍스트 추출
- enrich_context(): core_rag.enrich_context_with_rag 와 동일 시그니처 (drop-in)

Note:
- raganything / lightrag-hku 는 lazy import. 미설치 환경에서도 모듈 자체는 import 가능.
- 프로젝트별 working_dir: rag_storage/{storage_name}/lightrag/
- LLM: OpenAI gpt-5.5-2026-04-23, 임베딩: text-embedding-3-large (ai_client 상수 참조)
- 동기 wrapper: FastAPI 라우트가 동기/비동기 혼재라 sync 인터페이스 노출
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from ai_client import OPENAI_RAG_MODEL, OPENAI_EMBEDDING_MODEL, get_openai_client
from core_rag import RAG_STORAGE_DIR, _get_storage_name

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return os.environ.get("USE_RAG_ANYTHING", "").lower() in ("1", "true", "yes")


def _working_dir(project_name: str, owner_id: int | None = None) -> str:
    storage = _get_storage_name(project_name, owner_id=owner_id)
    return os.path.join(RAG_STORAGE_DIR, storage, "lightrag")


# ── LLM / 임베딩 콜백 (RAG-Anything 시그니처 준수) ──

def _llm_func(prompt: str, system_prompt: str | None = None,
              history_messages: list | None = None, **kwargs) -> str:
    """OpenAI Chat completions wrapper — RAG-Anything llm_model_func 시그니처."""
    client = get_openai_client()
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    for h in (history_messages or []):
        msgs.append(h)
    msgs.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=OPENAI_RAG_MODEL,
        messages=msgs,
        temperature=kwargs.get("temperature", 0.2),
    )
    return resp.choices[0].message.content or ""


async def _embedding_func(texts: list[str]):
    """OpenAI text-embedding-3-large — async wrapper. 반환: List[List[float]]."""
    client = get_openai_client()
    # OpenAI SDK는 sync — to_thread 로 우회
    def _sync():
        resp = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=texts)
        return [d.embedding for d in resp.data]
    return await asyncio.to_thread(_sync)


# ── 인스턴스 캐시 (프로젝트별) ──
_INSTANCES: dict[str, object] = {}


def _get_instance(project_name: str, owner_id: int | None = None):
    """프로젝트별 RAGAnything 싱글톤 반환. lazy import 로 의존성 부재 시 명확히 에러."""
    key = f"{owner_id}::{project_name}"
    if key in _INSTANCES:
        return _INSTANCES[key]

    try:
        from raganything import RAGAnything, RAGAnythingConfig  # type: ignore
        from lightrag.utils import EmbeddingFunc  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "raganything / lightrag-hku 가 설치되지 않았습니다. "
            "USE_RAG_ANYTHING=true 사용 전 `pip install raganything lightrag-hku` 실행."
        ) from e

    wd = _working_dir(project_name, owner_id)
    os.makedirs(wd, exist_ok=True)

    config = RAGAnythingConfig(
        working_dir=wd,
        parser=os.environ.get("RAG_ANYTHING_PARSER", "mineru"),
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )
    embedding_func = EmbeddingFunc(
        embedding_dim=3072,  # text-embedding-3-large
        max_token_size=8192,
        func=_embedding_func,
    )
    rag = RAGAnything(
        config=config,
        llm_model_func=_llm_func,
        embedding_func=embedding_func,
    )
    _INSTANCES[key] = rag
    return rag


# ── Public API (동기 wrapper) ──

def ingest_file(project_name: str, owner_id: int, file_path: str,
                output_dir: Optional[str] = None) -> dict:
    """단일 파일을 LightRAG working_dir 에 인덱싱. 동기."""
    rag = _get_instance(project_name, owner_id)
    out = output_dir or os.path.join(_working_dir(project_name, owner_id), "_parsed")
    os.makedirs(out, exist_ok=True)
    try:
        asyncio.run(rag.process_document_complete(
            file_path=file_path, output_dir=out, parse_method="auto",
        ))
        return {"success": True, "file": os.path.basename(file_path)}
    except Exception as e:
        logger.exception(f"[rag_anything] ingest 실패: {file_path}")
        return {"success": False, "file": os.path.basename(file_path), "error": str(e)}


def query(project_name: str, owner_id: int, question: str,
          mode: str = "hybrid") -> str:
    """LightRAG hybrid 쿼리. 동기. mode: hybrid/local/global/naive."""
    rag = _get_instance(project_name, owner_id)
    try:
        result = asyncio.run(rag.aquery(question, mode=mode))
        return str(result) if result else ""
    except Exception as e:
        logger.exception(f"[rag_anything] query 실패")
        return f"(쿼리 실패: {e})"


def enrich_context(api_key: str, structure_text: str, context_text: str,
                   project_name: str, template_option: str = "",
                   owner_id: int | None = None) -> str:
    """core_rag.enrich_context_with_rag 의 drop-in 대체.
    USE_RAG_ANYTHING 활성 시 query() 결과를 컨텍스트로 반환.
    """
    if not is_enabled():
        # 폴백 — 기존 core_rag 경로
        import core_rag
        return core_rag.enrich_context_with_rag(
            api_key=api_key, structure_text=structure_text,
            context_text=context_text, project_name=project_name,
            template_option=template_option,
        )
    if owner_id is None:
        # owner_id 없으면 안전하게 기존 경로
        import core_rag
        return core_rag.enrich_context_with_rag(
            api_key=api_key, structure_text=structure_text,
            context_text=context_text, project_name=project_name,
            template_option=template_option,
        )
    q = (context_text or "").strip() or (structure_text or "").strip()
    if not q:
        return ""
    try:
        ctx = query(project_name, owner_id, q, mode="hybrid")
        if ctx and len(ctx.strip()) > 20:
            return f"\n\n--- [RAG-Anything KG/벡터: {project_name}] ---\n{ctx}"
    except Exception as e:
        logger.warning(f"[rag_anything] enrich 폴백: {e}")
    # 마지막 폴백
    import core_rag
    return core_rag.enrich_context_with_rag(
        api_key=api_key, structure_text=structure_text,
        context_text=context_text, project_name=project_name,
        template_option=template_option,
    )


def reindex_project(project_name: str, owner_id: int) -> dict:
    """프로젝트 docs 폴더의 모든 파일을 LightRAG 에 재인덱싱.
    Phase 4 에서 UI 노출 예정. Phase 2 에서는 API 만 우선 제공.
    """
    if not is_enabled():
        return {"success": False, "error": "USE_RAG_ANYTHING=false (env 활성 필요)"}
    from core_rag import _get_storage_name as _gs, _get_project_docs_dir
    storage = _gs(project_name, owner_id=owner_id)
    docs_dir = _get_project_docs_dir(storage)
    if not os.path.isdir(docs_dir):
        return {"success": False, "error": f"docs 디렉토리 없음: {docs_dir}"}
    indexed: list[str] = []
    errors: list[dict] = []
    for fname in sorted(os.listdir(docs_dir)):
        path = os.path.join(docs_dir, fname)
        if not os.path.isfile(path):
            continue
        r = ingest_file(project_name, owner_id, path)
        if r.get("success"):
            indexed.append(fname)
        else:
            errors.append({"file": fname, "error": r.get("error")})
    return {"success": len(errors) == 0, "indexed": indexed, "errors": errors,
            "count": len(indexed)}

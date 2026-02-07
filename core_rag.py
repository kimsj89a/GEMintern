"""
RAG integration module for GEM Intern.
Uses lightrag-hku directly with Gemini's OpenAI-compatible endpoint.
"""

import asyncio
import json
import os
import threading
from functools import partial
from typing import List, Dict, Any

# --- RAG availability check ---
RAG_AVAILABLE = False
try:
    from lightrag import LightRAG, QueryParam
    from lightrag.llm.openai import openai_complete_if_cache, openai_embed
    from lightrag.utils import EmbeddingFunc
    RAG_AVAILABLE = True
except ImportError:
    pass

# --- Constants ---
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_RAG_LLM_MODEL = "gemini-2.0-flash"
DEFAULT_EMBEDDING_MODEL = "text-embedding-004"
DEFAULT_EMBEDDING_DIM = 768

RAG_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_storage")
INDEXED_DOCS_FILE = os.path.join(RAG_STORAGE_DIR, "_indexed_docs.json")


# ========================================
# Utility functions
# ========================================

def _run_async(coro):
    """Run async coroutine from sync context (Streamlit-safe)."""
    result = [None]
    exception = [None]

    def _target():
        try:
            result[0] = asyncio.run(coro)
        except Exception as e:
            exception[0] = e

    t = threading.Thread(target=_target)
    t.start()
    t.join()

    if exception[0]:
        raise exception[0]
    return result[0]


def _create_lightrag(api_key: str) -> "LightRAG":
    """Create a LightRAG instance using Gemini's OpenAI-compatible API."""
    os.makedirs(RAG_STORAGE_DIR, exist_ok=True)

    embedding_func = EmbeddingFunc(
        embedding_dim=DEFAULT_EMBEDDING_DIM,
        func=partial(
            openai_embed,
            model=DEFAULT_EMBEDDING_MODEL,
            base_url=GEMINI_OPENAI_BASE_URL,
            api_key=api_key,
        ),
        max_token_size=8192,
    )

    return LightRAG(
        working_dir=RAG_STORAGE_DIR,
        llm_model_func=openai_complete_if_cache,
        llm_model_name=DEFAULT_RAG_LLM_MODEL,
        embedding_func=embedding_func,
        llm_model_kwargs={
            "base_url": GEMINI_OPENAI_BASE_URL,
            "api_key": api_key,
        },
    )


# ========================================
# Index tracking (avoid duplicate indexing)
# ========================================

def _get_indexed_docs() -> List[str]:
    """Get list of already-indexed document names."""
    if os.path.exists(INDEXED_DOCS_FILE):
        try:
            with open(INDEXED_DOCS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_indexed_docs(docs: List[str]):
    """Save indexed document names."""
    os.makedirs(RAG_STORAGE_DIR, exist_ok=True)
    with open(INDEXED_DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False)


# ========================================
# Public API - Status checks
# ========================================

def is_rag_available() -> bool:
    """Check if lightrag-hku is installed."""
    return RAG_AVAILABLE


def is_indexed() -> bool:
    """Check if any documents have been indexed."""
    return len(_get_indexed_docs()) > 0


def get_indexed_count() -> int:
    """Get number of indexed documents."""
    return len(_get_indexed_docs())


def get_indexed_doc_names() -> List[str]:
    """Get names of indexed documents."""
    return _get_indexed_docs()


# ========================================
# Core async functions
# ========================================

async def _index_texts_async(api_key: str, texts: Dict[str, str]) -> Dict[str, Any]:
    """Index multiple text documents into RAG."""
    already_indexed = set(_get_indexed_docs())

    new_texts = {k: v for k, v in texts.items() if k not in already_indexed}
    if not new_texts:
        return {
            "success": True,
            "indexed": [],
            "skipped": list(texts.keys()),
            "errors": [],
            "message": "All documents already indexed",
        }

    rag = _create_lightrag(api_key)
    await rag.initialize_storages()

    indexed = []
    errors = []
    try:
        for name, text in new_texts.items():
            try:
                if text and len(text.strip()) > 50:
                    await rag.ainsert(text)
                    indexed.append(name)
            except Exception as e:
                errors.append({"name": name, "error": str(e)})
    finally:
        await rag.finalize_storages()

    all_indexed = list(already_indexed | set(indexed))
    _save_indexed_docs(all_indexed)

    return {
        "success": len(errors) == 0,
        "indexed": indexed,
        "skipped": list(already_indexed & set(texts.keys())),
        "errors": errors,
        "total": len(texts),
    }


async def _query_async(api_key: str, question: str, mode: str = "mix") -> str:
    """Query indexed documents."""
    rag = _create_lightrag(api_key)
    await rag.initialize_storages()
    try:
        return await rag.aquery(question, param=QueryParam(mode=mode))
    finally:
        await rag.finalize_storages()


async def _batch_query_async(
    api_key: str, questions: List[str], mode: str = "mix"
) -> List[Dict[str, Any]]:
    """Batch query indexed documents."""
    rag = _create_lightrag(api_key)
    await rag.initialize_storages()
    results = []
    try:
        for q in questions:
            try:
                answer = await rag.aquery(q, param=QueryParam(mode=mode))
                results.append({"query": q, "answer": answer, "success": True})
            except Exception as e:
                results.append({"query": q, "answer": "", "success": False, "error": str(e)})
    finally:
        await rag.finalize_storages()
    return results


# ========================================
# Public API - Sync wrappers
# ========================================

def index_texts(api_key: str, texts: Dict[str, str]) -> Dict[str, Any]:
    """Index text documents into RAG (sync wrapper)."""
    if not RAG_AVAILABLE:
        return {"success": False, "error": "lightrag-hku not installed"}
    return _run_async(_index_texts_async(api_key, texts))


def query_rag(api_key: str, question: str, mode: str = "mix") -> str:
    """Query indexed documents (sync wrapper)."""
    if not RAG_AVAILABLE:
        return ""
    return _run_async(_query_async(api_key, question, mode))


def batch_query_rag(
    api_key: str, questions: List[str], mode: str = "mix"
) -> List[Dict[str, Any]]:
    """Batch query indexed documents (sync wrapper)."""
    if not RAG_AVAILABLE:
        return []
    return _run_async(_batch_query_async(api_key, questions, mode))


def index_saved_documents(api_key: str) -> Dict[str, Any]:
    """Index all documents in saved_documents/ directory."""
    import utils

    docs = {}
    for fname in utils.list_saved_docs():
        content = utils.load_saved_doc(fname)
        if content:
            docs[fname] = content

    if not docs:
        return {"success": False, "error": "No saved documents to index", "indexed": []}

    return index_texts(api_key, docs)


def index_single_document(api_key: str, filename: str, content: str) -> Dict[str, Any]:
    """Index a single document by name and content."""
    if not content or len(content.strip()) < 50:
        return {"success": True, "indexed": [], "message": "Content too short to index"}
    return index_texts(api_key, {filename: content})


# ========================================
# Context enrichment via RAG queries
# ========================================

def enrich_context_with_rag(
    api_key: str,
    structure_text: str,
    context_text: str,
    template_option: str = "",
) -> str:
    """
    Query RAG to retrieve relevant context for report generation.
    Returns enriched context string to append to file_context.
    """
    if not RAG_AVAILABLE or not is_indexed():
        return ""

    queries = _build_queries_from_structure(structure_text, context_text, template_option)
    if not queries:
        return ""

    try:
        results = batch_query_rag(api_key, queries[:6], mode="mix")
    except Exception:
        return ""

    if not results:
        return ""

    parts = ["\n\n--- [RAG 검색 결과 (Knowledge Graph + Vector Search)] ---"]
    for r in results:
        if r.get("success") and r.get("answer"):
            answer = r["answer"].strip()
            if answer and len(answer) > 30:
                parts.append(f"\n**Q: {r['query']}**\n{answer}")

    if len(parts) <= 1:
        return ""

    return "\n".join(parts)


def _build_queries_from_structure(
    structure_text: str, context_text: str, template_option: str
) -> List[str]:
    """Generate RAG queries based on report structure and context."""
    queries = []

    if context_text.strip():
        queries.append(f"다음 맥락과 관련된 핵심 정보를 찾아주세요: {context_text[:300]}")

    for line in structure_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("-"):
            section = line.lstrip("#- ").strip()
            if section and len(section) > 3 and len(section) < 100:
                queries.append(f"{section}에 대한 관련 정보와 데이터를 찾아주세요.")

    template_queries = {
        "investment": [
            "회사의 주요 재무 지표와 실적 데이터를 요약해주세요.",
            "투자 리스크 요인과 주의사항을 정리해주세요.",
            "사업 모델과 경쟁력 분석 내용을 찾아주세요.",
        ],
        "simple_review": [
            "핵심 투자 포인트와 요약 정보를 찾아주세요.",
            "주요 재무 데이터와 수치를 정리해주세요.",
        ],
        "im": [
            "투자 하이라이트와 핵심 매력 포인트를 정리해주세요.",
            "시장 분석 및 성장 전망 관련 데이터를 찾아주세요.",
        ],
        "management": [
            "경영 성과 및 KPI 달성 현황을 찾아주세요.",
            "향후 계획 및 이슈사항을 정리해주세요.",
        ],
        "presentation": [
            "발표자료에 포함할 핵심 데이터와 차트 정보를 찾아주세요.",
        ],
        "paper_review": [
            "논문의 핵심 기여와 방법론을 요약해주세요.",
            "실험 결과와 성능 비교 데이터를 찾아주세요.",
        ],
    }
    queries.extend(template_queries.get(template_option, []))

    return queries[:8]


# ========================================
# Index management
# ========================================

def clear_rag_index():
    """Clear the entire RAG index and storage."""
    import shutil
    if os.path.exists(RAG_STORAGE_DIR):
        shutil.rmtree(RAG_STORAGE_DIR, ignore_errors=True)

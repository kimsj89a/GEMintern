"""
RAG integration module for GEM Intern.
Project-based RAG: each project has its own isolated LightRAG index.
Uses lightrag-hku directly with Gemini's OpenAI-compatible endpoint.
"""

import asyncio
import datetime
import json
import os
import re
import shutil
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
PROJECTS_FILE = os.path.join(RAG_STORAGE_DIR, "_projects.json")


# ========================================
# Persistent event loop + LightRAG instance cache
# ========================================
# Root cause of "bound to a different event loop":
#   LightRAG creates asyncio.Lock objects internally. These locks bind to
#   the event loop on which they are first awaited.  If we create a new
#   LightRAG (and thus new locks) on a different loop, or re-create loops,
#   locks from earlier become invalid.
#
# Solution:
#   1. ONE persistent background event loop (never destroyed).
#   2. ONE cached LightRAG instance per project, created AND initialized
#      on that loop. Reused across calls so locks stay on the same loop.
#   3. No finalize_storages() between calls — only on explicit cleanup.

_bg_loop: asyncio.AbstractEventLoop | None = None
_bg_thread: threading.Thread | None = None
_bg_lock = threading.Lock()

# Cache: project_name -> LightRAG (already initialized)
_rag_instances: Dict[str, "LightRAG"] = {}
_rag_instances_lock = threading.Lock()


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    """Return the persistent background event loop, creating it if needed."""
    global _bg_loop, _bg_thread
    with _bg_lock:
        if _bg_loop is not None and _bg_loop.is_running():
            return _bg_loop

        loop = asyncio.new_event_loop()

        def _run_loop():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        t = threading.Thread(target=_run_loop, daemon=True)
        t.start()
        _bg_loop = loop
        _bg_thread = t
        return _bg_loop


def _run_async(coro):
    """Run async coroutine on the persistent background loop (Streamlit-safe)."""
    loop = _get_or_create_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=600)  # 10 min max


def _get_project_dir(project_name: str) -> str:
    """Return the storage directory for a specific project."""
    return os.path.join(RAG_STORAGE_DIR, project_name)


def _get_indexed_docs_file(project_name: str) -> str:
    """Return the _indexed_docs.json path for a specific project."""
    return os.path.join(_get_project_dir(project_name), "_indexed_docs.json")


def _create_lightrag_instance(api_key: str, project_name: str) -> "LightRAG":
    """Create a raw LightRAG instance (not yet initialized)."""
    project_dir = _get_project_dir(project_name)
    os.makedirs(project_dir, exist_ok=True)

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
        working_dir=project_dir,
        llm_model_func=openai_complete_if_cache,
        llm_model_name=DEFAULT_RAG_LLM_MODEL,
        embedding_func=embedding_func,
        llm_model_kwargs={
            "base_url": GEMINI_OPENAI_BASE_URL,
            "api_key": api_key,
        },
    )


async def _get_rag(api_key: str, project_name: str) -> "LightRAG":
    """Get or create a cached, initialized LightRAG for a project.
    MUST be called from the persistent background loop.
    """
    with _rag_instances_lock:
        if project_name in _rag_instances:
            return _rag_instances[project_name]

    # Create and initialize outside the lock (may do I/O)
    rag = _create_lightrag_instance(api_key, project_name)
    await rag.initialize_storages()

    with _rag_instances_lock:
        # Double-check (another coroutine might have created it)
        if project_name not in _rag_instances:
            _rag_instances[project_name] = rag
        else:
            # Someone else got here first; finalize ours and use theirs
            try:
                await rag.finalize_storages()
            except Exception:
                pass
            rag = _rag_instances[project_name]
    return rag


def _evict_rag_cache(project_name: str):
    """Remove a project's cached LightRAG instance (e.g. on clear/delete)."""
    with _rag_instances_lock:
        rag = _rag_instances.pop(project_name, None)
    if rag is not None:
        try:
            _run_async(rag.finalize_storages())
        except Exception:
            pass


# ========================================
# Project management
# ========================================

def _load_projects() -> List[Dict[str, Any]]:
    """Load project registry from _projects.json."""
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("projects", [])
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_projects(projects: List[Dict[str, Any]]):
    """Save project registry."""
    os.makedirs(RAG_STORAGE_DIR, exist_ok=True)
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"projects": projects}, f, ensure_ascii=False, indent=2)


def list_projects() -> List[Dict[str, Any]]:
    """List all projects with metadata."""
    projects = _load_projects()
    for p in projects:
        p["doc_count"] = len(_get_indexed_docs(p["name"]))
    return projects


def create_project(project_name: str) -> Dict[str, Any]:
    """Create a new project."""
    project_name = project_name.strip()
    if not project_name:
        return {"success": False, "error": "프로젝트명을 입력해주세요."}

    safe_name = re.sub(r'[\\/*?:"<>|]', "", project_name).strip()
    if not safe_name:
        return {"success": False, "error": "유효하지 않은 프로젝트명입니다."}

    projects = _load_projects()
    if any(p["name"] == safe_name for p in projects):
        return {"success": False, "error": f"'{safe_name}' 프로젝트가 이미 존재합니다."}

    project_dir = _get_project_dir(safe_name)
    os.makedirs(project_dir, exist_ok=True)

    new_project = {
        "name": safe_name,
        "created": datetime.datetime.now().isoformat(),
        "doc_count": 0,
    }
    projects.append(new_project)
    _save_projects(projects)

    return {"success": True, "project": new_project}


def get_project_info(project_name: str) -> Dict[str, Any]:
    """Get info for a specific project."""
    projects = _load_projects()
    for p in projects:
        if p["name"] == project_name:
            p["doc_count"] = len(_get_indexed_docs(project_name))
            p["indexed_docs"] = _get_indexed_docs(project_name)
            return p
    return {}


def delete_project(project_name: str) -> Dict[str, Any]:
    """Delete a project and all its RAG data."""
    _evict_rag_cache(project_name)

    projects = _load_projects()
    projects = [p for p in projects if p["name"] != project_name]
    _save_projects(projects)

    project_dir = _get_project_dir(project_name)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir, ignore_errors=True)

    return {"success": True}


# ========================================
# Index tracking (per-project)
# ========================================

def _get_indexed_docs(project_name: str) -> List[str]:
    """Get list of already-indexed document names for a project."""
    docs_file = _get_indexed_docs_file(project_name)
    if os.path.exists(docs_file):
        try:
            with open(docs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_indexed_docs(project_name: str, docs: List[str]):
    """Save indexed document names for a project."""
    project_dir = _get_project_dir(project_name)
    os.makedirs(project_dir, exist_ok=True)
    docs_file = _get_indexed_docs_file(project_name)
    with open(docs_file, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False)


# ========================================
# Public API - Status checks
# ========================================

def is_rag_available() -> bool:
    """Check if lightrag-hku is installed."""
    return RAG_AVAILABLE


def is_indexed(project_name: str) -> bool:
    """Check if a project has any indexed documents."""
    return len(_get_indexed_docs(project_name)) > 0


def get_indexed_count(project_name: str) -> int:
    """Get number of indexed documents in a project."""
    return len(_get_indexed_docs(project_name))


def get_indexed_doc_names(project_name: str) -> List[str]:
    """Get names of indexed documents in a project."""
    return _get_indexed_docs(project_name)


# ========================================
# Core async functions (use cached instances)
# ========================================

async def _index_texts_async(api_key: str, texts: Dict[str, str], project_name: str) -> Dict[str, Any]:
    """Index multiple text documents into a project's RAG."""
    already_indexed = set(_get_indexed_docs(project_name))

    new_texts = {k: v for k, v in texts.items() if k not in already_indexed}
    if not new_texts:
        return {
            "success": True,
            "indexed": [],
            "skipped": list(texts.keys()),
            "errors": [],
            "message": "All documents already indexed",
        }

    rag = await _get_rag(api_key, project_name)

    indexed = []
    errors = []
    for name, text in new_texts.items():
        try:
            if text and len(text.strip()) > 50:
                await rag.ainsert(text)
                indexed.append(name)
        except Exception as e:
            errors.append({"name": name, "error": str(e)})

    all_indexed = list(already_indexed | set(indexed))
    _save_indexed_docs(project_name, all_indexed)

    return {
        "success": len(errors) == 0,
        "indexed": indexed,
        "skipped": list(already_indexed & set(texts.keys())),
        "errors": errors,
        "total": len(texts),
    }


async def _query_async(api_key: str, question: str, project_name: str, mode: str = "mix") -> str:
    """Query a project's indexed documents."""
    rag = await _get_rag(api_key, project_name)
    return await rag.aquery(question, param=QueryParam(mode=mode))


async def _batch_query_async(
    api_key: str, questions: List[str], project_name: str, mode: str = "mix"
) -> List[Dict[str, Any]]:
    """Batch query a project's indexed documents."""
    rag = await _get_rag(api_key, project_name)
    results = []
    for q in questions:
        try:
            answer = await rag.aquery(q, param=QueryParam(mode=mode))
            results.append({"query": q, "answer": answer, "success": True})
        except Exception as e:
            results.append({"query": q, "answer": "", "success": False, "error": str(e)})
    return results


# ========================================
# Public API - Sync wrappers
# ========================================

def index_texts(api_key: str, texts: Dict[str, str], project_name: str) -> Dict[str, Any]:
    """Index text documents into a project's RAG (sync wrapper)."""
    if not RAG_AVAILABLE:
        return {"success": False, "error": "lightrag-hku not installed"}
    return _run_async(_index_texts_async(api_key, texts, project_name))


def query_rag(api_key: str, question: str, project_name: str, mode: str = "mix") -> str:
    """Query a project's indexed documents (sync wrapper)."""
    if not RAG_AVAILABLE:
        return ""
    return _run_async(_query_async(api_key, question, project_name, mode))


def batch_query_rag(
    api_key: str, questions: List[str], project_name: str, mode: str = "mix"
) -> List[Dict[str, Any]]:
    """Batch query a project's indexed documents (sync wrapper)."""
    if not RAG_AVAILABLE:
        return []
    return _run_async(_batch_query_async(api_key, questions, project_name, mode))


def index_saved_documents(api_key: str, project_name: str) -> Dict[str, Any]:
    """Index all documents in saved_documents/ into a project."""
    import utils

    docs = {}
    for fname in utils.list_saved_docs():
        content = utils.load_saved_doc(fname)
        if content:
            docs[fname] = content

    if not docs:
        return {"success": False, "error": "No saved documents to index", "indexed": []}

    return index_texts(api_key, docs, project_name)


def index_single_document(api_key: str, filename: str, content: str, project_name: str) -> Dict[str, Any]:
    """Index a single document into a project."""
    if not content or len(content.strip()) < 50:
        return {"success": True, "indexed": [], "message": "Content too short to index"}
    return index_texts(api_key, {filename: content}, project_name)


# ========================================
# Context enrichment via RAG queries
# ========================================

def enrich_context_with_rag(
    api_key: str,
    structure_text: str,
    context_text: str,
    project_name: str,
    template_option: str = "",
) -> str:
    """
    Query a project's RAG to retrieve relevant context for report generation.
    Returns enriched context string to append to file_context.
    """
    if not RAG_AVAILABLE or not is_indexed(project_name):
        return ""

    queries = _build_queries_from_structure(structure_text, context_text, template_option)
    if not queries:
        return ""

    try:
        results = batch_query_rag(api_key, queries[:6], project_name, mode="mix")
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
# Index management (per-project)
# ========================================

def clear_rag_index(project_name: str):
    """Clear a project's RAG index (keeps the project entry)."""
    _evict_rag_cache(project_name)
    project_dir = _get_project_dir(project_name)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir, ignore_errors=True)
        os.makedirs(project_dir, exist_ok=True)
    _save_indexed_docs(project_name, [])

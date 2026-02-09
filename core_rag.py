"""
Project-based document storage for GEM Intern.
Each project stores parsed documents as markdown files.
Documents are loaded as context for report generation and analysis.

Replaces the previous LightRAG-based approach with simple file-based storage.
"""

import datetime
import json
import os
import re
import shutil
from typing import List, Dict, Any


# --- Constants ---
RAG_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_storage")
PROJECTS_FILE = os.path.join(RAG_STORAGE_DIR, "_projects.json")
DOCS_SUBDIR = "docs"  # 프로젝트 내 문서 저장 하위 폴더


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


def _get_project_dir(project_name: str) -> str:
    """Return the storage directory for a specific project."""
    return os.path.join(RAG_STORAGE_DIR, project_name)


def _get_project_docs_dir(project_name: str) -> str:
    """Return the docs directory for a specific project."""
    return os.path.join(_get_project_dir(project_name), DOCS_SUBDIR)


def _get_indexed_docs_file(project_name: str) -> str:
    """Return the _indexed_docs.json path for a specific project."""
    return os.path.join(_get_project_dir(project_name), "_indexed_docs.json")


# ========================================
# Index tracking (per-project)
# ========================================

def _get_indexed_docs(project_name: str) -> List[str]:
    """Get list of indexed document names for a project."""
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
# Public API - Project management
# ========================================

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
    os.makedirs(_get_project_docs_dir(safe_name), exist_ok=True)

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
    """Delete a project and all its stored documents."""
    projects = _load_projects()
    projects = [p for p in projects if p["name"] != project_name]
    _save_projects(projects)

    project_dir = _get_project_dir(project_name)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir, ignore_errors=True)

    return {"success": True}


# ========================================
# Public API - Status checks
# ========================================

def is_rag_available() -> bool:
    """문서 저장소 사용 가능 여부 (항상 True)."""
    return True


def is_indexed(project_name: str) -> bool:
    """Check if a project has any stored documents."""
    return len(_get_indexed_docs(project_name)) > 0


def get_indexed_count(project_name: str) -> int:
    """Get number of stored documents in a project."""
    return len(_get_indexed_docs(project_name))


def get_indexed_doc_names(project_name: str) -> List[str]:
    """Get names of stored documents in a project."""
    return _get_indexed_docs(project_name)


# ========================================
# Core: Document storage (file-based)
# ========================================

def _save_doc_file(project_name: str, filename: str, content: str):
    """Save a single document as markdown file in the project docs dir."""
    docs_dir = _get_project_docs_dir(project_name)
    os.makedirs(docs_dir, exist_ok=True)
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", os.path.splitext(filename)[0]).strip()
    if not safe_name:
        safe_name = "unnamed"
    save_path = os.path.join(docs_dir, f"{safe_name}.md")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(content)
    return save_path


def _load_doc_file(project_name: str, filename: str) -> str:
    """Load a single document from the project docs dir."""
    docs_dir = _get_project_docs_dir(project_name)
    # Try exact match first, then .md extension
    for candidate in [filename, f"{os.path.splitext(filename)[0]}.md"]:
        path = os.path.join(docs_dir, candidate)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return ""


def load_all_project_docs(project_name: str) -> str:
    """Load all documents from a project as concatenated text.
    Returns a single string with all document contents.
    """
    docs_dir = _get_project_docs_dir(project_name)
    if not os.path.exists(docs_dir):
        return ""

    parts = []
    for fname in sorted(os.listdir(docs_dir)):
        if fname.endswith(".md"):
            fpath = os.path.join(docs_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    parts.append(content)
            except Exception:
                pass

    return "\n\n".join(parts)


def load_project_docs_dict(project_name: str) -> Dict[str, str]:
    """Load all documents from a project as a dict {filename: content}."""
    docs_dir = _get_project_docs_dir(project_name)
    if not os.path.exists(docs_dir):
        return {}

    result = {}
    for fname in sorted(os.listdir(docs_dir)):
        if fname.endswith(".md"):
            fpath = os.path.join(docs_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    result[fname] = content
            except Exception:
                pass

    return result


# ========================================
# Public API - Indexing (saves documents)
# ========================================

def index_texts(api_key: str, texts: Dict[str, str], project_name: str) -> Dict[str, Any]:
    """Save text documents into a project's document store.
    api_key is kept in the signature for backward compatibility but not used.
    """
    already_indexed = set(_get_indexed_docs(project_name))

    new_texts = {k: v for k, v in texts.items() if k not in already_indexed}
    if not new_texts:
        return {
            "success": True,
            "indexed": [],
            "skipped": list(texts.keys()),
            "errors": [],
            "message": "모든 문서가 이미 저장됨",
        }

    indexed = []
    errors = []
    for name, text in new_texts.items():
        try:
            if text and len(text.strip()) > 50:
                _save_doc_file(project_name, name, text)
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


def index_saved_documents(api_key: str, project_name: str) -> Dict[str, Any]:
    """Import all documents from saved_documents/ into a project."""
    import utils

    docs = {}
    for fname in utils.list_saved_docs():
        content = utils.load_saved_doc(fname)
        if content:
            docs[fname] = content

    if not docs:
        return {"success": False, "error": "저장된 문서가 없습니다.", "indexed": []}

    return index_texts(api_key, docs, project_name)


def index_single_document(api_key: str, filename: str, content: str, project_name: str) -> Dict[str, Any]:
    """Save a single document into a project."""
    if not content or len(content.strip()) < 50:
        return {"success": True, "indexed": [], "message": "내용이 너무 짧아 저장하지 않음"}
    return index_texts(api_key, {filename: content}, project_name)


# ========================================
# Context enrichment (load project docs)
# ========================================

def enrich_context_with_rag(
    api_key: str,
    structure_text: str,
    context_text: str,
    project_name: str,
    template_option: str = "",
) -> str:
    """
    Load a project's stored documents and return as enriched context.
    Replaces the previous LightRAG query-based approach.
    """
    if not is_indexed(project_name):
        return ""

    all_docs = load_all_project_docs(project_name)
    if not all_docs or len(all_docs.strip()) < 50:
        return ""

    return f"\n\n--- [프로젝트 문서 컨텍스트: {project_name}] ---\n{all_docs}"


# ========================================
# Index management (per-project)
# ========================================

def clear_rag_index(project_name: str):
    """Clear a project's stored documents (keeps the project entry)."""
    project_dir = _get_project_dir(project_name)
    docs_dir = _get_project_docs_dir(project_name)
    if os.path.exists(docs_dir):
        shutil.rmtree(docs_dir, ignore_errors=True)
    os.makedirs(docs_dir, exist_ok=True)
    _save_indexed_docs(project_name, [])

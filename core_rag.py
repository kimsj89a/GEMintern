"""
Project-based document storage for GEM Intern.
Each project stores parsed documents as markdown files.
Documents are loaded as context for report generation and analysis.

Replaces the previous LightRAG-based approach with simple file-based storage.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
from typing import List, Dict, Any, Optional


# --- Cloud sync hook ---
_sync_manager = None


def set_sync_manager(manager):
    """Set the CloudSyncManager instance for automatic cloud sync."""
    global _sync_manager
    _sync_manager = manager


def get_sync_manager():
    """Get the current CloudSyncManager instance (or None)."""
    return _sync_manager


# --- Constants ---
RAG_STORAGE_DIR = os.environ.get(
    "RAG_STORAGE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_storage"),
)
PROJECTS_FILE = os.path.join(RAG_STORAGE_DIR, "_projects.json")
DOCS_SUBDIR = "docs"  # 프로젝트 내 문서 저장 하위 폴더
TRASH_SUBDIR = "_trash"  # 프로젝트 내 휴지통 하위 폴더
ROOT_FOLDER = "__root__"  # 최상위(미분류) 폴더 키


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




def _get_storage_name(project_name: str, owner_id: int | None = None) -> str:
    """Resolve display name to storage directory name.
    Checks _projects.json first, then falls back to SQLite DB.
    """
    projects = _load_projects()
    for p in projects:
        if p["name"] == project_name:
            if owner_id is not None and p.get("owner_id") is not None and p.get("owner_id") != owner_id:
                continue
            return p.get("storage_name", p["name"])
    # Fallback: check SQLite DB for projects created after auth migration
    try:
        from backend.database import get_db
        with get_db() as conn:
            if owner_id is not None:
                row = conn.execute(
                    "SELECT storage_name FROM projects WHERE name = ? AND owner_id = ?",
                    (project_name, owner_id)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT storage_name FROM projects WHERE name = ? ORDER BY id LIMIT 1",
                    (project_name,)
                ).fetchone()
            if row:
                return row["storage_name"] if row["storage_name"] else project_name
    except Exception:
        pass
    return project_name

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
# Folder management (per-project, metadata-only)
# ========================================

def _get_folders_file(project_name: str) -> str:
    """Return the _folders.json path for a specific project."""
    return os.path.join(_get_project_dir(project_name), "_folders.json")


def _load_folders(project_name: str) -> Dict[str, List[str]]:
    """Load folder structure. Returns {folder_name: [doc_stems], ROOT_FOLDER: [doc_stems]}.
    Auto-migrates from flat _indexed_docs.json if _folders.json doesn't exist.
    """
    folders_file = _get_folders_file(project_name)
    if os.path.exists(folders_file):
        try:
            with open(folders_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Ensure root key exists
                    if ROOT_FOLDER not in data:
                        data[ROOT_FOLDER] = []
                    return data
        except (json.JSONDecodeError, IOError):
            pass

    # Auto-migrate: put all existing indexed docs into root folder
    existing_docs = _get_indexed_docs(project_name)
    return {ROOT_FOLDER: existing_docs}


def _save_folders(project_name: str, folders: Dict[str, List[str]]):
    """Save folder structure."""
    project_dir = _get_project_dir(project_name)
    os.makedirs(project_dir, exist_ok=True)
    folders_file = _get_folders_file(project_name)
    with open(folders_file, "w", encoding="utf-8") as f:
        json.dump(folders, f, ensure_ascii=False, indent=2)

    # Keep _indexed_docs.json in sync (flat list of all docs)
    all_docs = []
    for doc_list in folders.values():
        all_docs.extend(doc_list)
    _save_indexed_docs(project_name, all_docs)


def get_folder_tree(project_name: str, owner_id: int | None = None) -> Dict[str, List[str]]:
    """Get the folder tree structure for a project.
    Returns dict with folder names as keys and lists of doc names as values.
    ROOT_FOLDER key contains unfiled documents.
    """
    storage = _get_storage_name(project_name, owner_id=owner_id)
    return _load_folders(storage)


def list_folders(project_name: str, owner_id: int | None = None) -> List[str]:
    """List all folder names (excluding root) for a project."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    folders = _load_folders(storage)
    return [k for k in sorted(folders.keys()) if k != ROOT_FOLDER]


def create_folder(project_name: str, folder_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Create a new folder in the project."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    folder_name = folder_name.strip()
    if not folder_name:
        return {"success": False, "error": "폴더명을 입력해주세요."}
    if folder_name == ROOT_FOLDER:
        return {"success": False, "error": "예약된 이름입니다."}

    safe_name = re.sub(r'[\\/*?:"<>|]', "", folder_name).strip()
    if not safe_name:
        return {"success": False, "error": "유효하지 않은 폴더명입니다."}

    folders = _load_folders(storage)
    if safe_name in folders:
        return {"success": False, "error": f"'{safe_name}' 폴더가 이미 존재합니다."}

    folders[safe_name] = []
    _save_folders(storage, folders)
    return {"success": True, "folder": safe_name}


def rename_folder(project_name: str, old_name: str, new_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Rename a folder."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    new_name = new_name.strip()
    if not new_name or new_name == ROOT_FOLDER:
        return {"success": False, "error": "유효하지 않은 폴더명입니다."}

    safe_name = re.sub(r'[\\/*?:"<>|]', "", new_name).strip()
    if not safe_name:
        return {"success": False, "error": "유효하지 않은 폴더명입니다."}

    folders = _load_folders(storage)
    if old_name not in folders or old_name == ROOT_FOLDER:
        return {"success": False, "error": f"'{old_name}' 폴더를 찾을 수 없습니다."}
    if safe_name in folders:
        return {"success": False, "error": f"'{safe_name}' 폴더가 이미 존재합니다."}

    folders[safe_name] = folders.pop(old_name)
    _save_folders(storage, folders)
    return {"success": True}


def delete_folder(project_name: str, folder_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Delete a folder and move its documents to root."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    if folder_name == ROOT_FOLDER:
        return {"success": False, "error": "루트 폴더는 삭제할 수 없습니다."}

    folders = _load_folders(storage)
    if folder_name not in folders:
        return {"success": False, "error": f"'{folder_name}' 폴더를 찾을 수 없습니다."}

    # Move docs to root
    docs_to_move = folders.pop(folder_name)
    folders.setdefault(ROOT_FOLDER, []).extend(docs_to_move)
    _save_folders(storage, folders)
    return {"success": True}


def move_doc_to_folder(project_name: str, doc_name: str, target_folder: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Move a document to a different folder (or ROOT_FOLDER for unfiled)."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    folders = _load_folders(storage)

    if target_folder != ROOT_FOLDER and target_folder not in folders:
        return {"success": False, "error": f"'{target_folder}' 폴더를 찾을 수 없습니다."}

    # Remove from current folder
    for folder_key, doc_list in folders.items():
        if doc_name in doc_list:
            doc_list.remove(doc_name)
            break

    # Add to target folder
    folders.setdefault(target_folder, []).append(doc_name)
    _save_folders(storage, folders)
    return {"success": True}


def get_doc_folder(project_name: str, doc_name: str, owner_id: int | None = None) -> str:
    """Get the folder that contains a document. Returns ROOT_FOLDER if unfiled."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    folders = _load_folders(storage)
    for folder_key, doc_list in folders.items():
        if doc_name in doc_list:
            return folder_key
    return ROOT_FOLDER


def index_texts_to_folder(
    api_key: str, texts: Dict[str, str], project_name: str, folder: str = ROOT_FOLDER, owner_id: int | None = None
) -> Dict[str, Any]:
    """Save text documents into a specific folder in the project.
    Wrapper around index_texts that places new docs into the specified folder.
    """
    storage = _get_storage_name(project_name, owner_id=owner_id)
    result = index_texts(api_key, texts, project_name, owner_id=owner_id)

    # Move newly indexed docs to the target folder
    if result.get("indexed") and folder != ROOT_FOLDER:
        folders = _load_folders(storage)
        if folder not in folders:
            folders[folder] = []
        for doc_stem in result["indexed"]:
            # Remove from root if it was placed there by index_texts
            root_docs = folders.get(ROOT_FOLDER, [])
            if doc_stem in root_docs:
                root_docs.remove(doc_stem)
            # Add to target folder
            if doc_stem not in folders[folder]:
                folders[folder].append(doc_stem)
        _save_folders(storage, folders)

    return result


# ========================================
# Public API - Project management
# ========================================

def list_projects(owner_id: int | None = None) -> List[Dict[str, Any]]:
    """List projects. If owner_id given, only return that user's + legacy projects."""
    projects = _load_projects()
    if owner_id is not None:
        projects = [
            p for p in projects
            if p.get("owner_id") is None or p.get("owner_id") == owner_id
        ]
    for p in projects:
        storage = p.get("storage_name", p["name"])
        p["doc_count"] = len(_get_indexed_docs(storage))
    return projects


def create_project(project_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Create a new project."""
    project_name = project_name.strip()
    if not project_name:
        return {"success": False, "error": "프로젝트명을 입력해주세요."}

    safe_name = re.sub(r'[\\/*?:"<>|]', "", project_name).strip()
    if not safe_name:
        return {"success": False, "error": "유효하지 않은 프로젝트명입니다."}

    projects = _load_projects()
    if owner_id is not None:
        if any(p["name"] == safe_name and p.get("owner_id") == owner_id for p in projects):
            return {"success": False, "error": f"'{safe_name}' 프로젝트가 이미 존재합니다."}
    else:
        if any(p["name"] == safe_name for p in projects):
            return {"success": False, "error": f"'{safe_name}' 프로젝트가 이미 존재합니다."}

    # Storage dir namespaced by owner_id
    if owner_id is not None:
        storage_name = f"u{owner_id}_{safe_name}"
    else:
        storage_name = safe_name

    project_dir = _get_project_dir(storage_name)
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(os.path.join(project_dir, DOCS_SUBDIR), exist_ok=True)

    # [기능 추가] 기본 템플릿 문서 자동 생성
    templates = {
        "README.md": f"# {safe_name}\n\n생성일: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n## 프로젝트 개요\n이 프로젝트는 GEM Intern을 통해 생성되었습니다.\n\n## 주요 목표\n- \n",
        "Memo.md": "# 메모\n\n아이디어 및 주요 사항을 기록하세요.\n"
    }
    for fname, content in templates.items():
        _save_doc_file(storage_name, fname, content)
    template_stems = [os.path.splitext(f)[0] for f in templates.keys()]
    _save_indexed_docs(storage_name, template_stems)
    _save_folders(storage_name, {ROOT_FOLDER: template_stems})

    new_project = {
        "name": safe_name,
        "storage_name": storage_name,
        "owner_id": owner_id,
        "created": datetime.datetime.now().isoformat(),
        "last_accessed": datetime.datetime.now().isoformat(),
        "doc_count": len(templates),
    }
    projects.append(new_project)
    _save_projects(projects)

    if _sync_manager:
        try:
            _sync_manager.on_project_created(storage_name)
        except Exception:
            pass

    return {"success": True, "project": new_project}


def get_project_info(project_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Get info for a specific project."""
    projects = _load_projects()
    for p in projects:
        if p["name"] == project_name:
            if owner_id is not None and p.get("owner_id") is not None and p.get("owner_id") != owner_id:
                continue
            storage = p.get("storage_name", p["name"])
            p["doc_count"] = len(_get_indexed_docs(storage))
            p["indexed_docs"] = _get_indexed_docs(storage)
            return p
    return {}


def update_project_access_time(project_name: str):
    """Update the last_accessed timestamp for a project."""
    projects = _load_projects()
    updated = False
    for p in projects:
        if p["name"] == project_name:
            p["last_accessed"] = datetime.datetime.now().isoformat()
            updated = True
            break
    if updated:
        _save_projects(projects)


def delete_project(project_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Delete a project and all its stored documents."""
    projects = _load_projects()
    target_p = None
    for p in projects:
        if p["name"] == project_name:
            if owner_id is not None and p.get("owner_id") is not None and p.get("owner_id") != owner_id:
                return {"success": False, "error": "접근 권한이 없습니다."}
            target_p = p
            break
    if target_p is None:
        return {"success": False, "error": "프로젝트를 찾을 수 없습니다."}

    storage = target_p.get("storage_name", target_p["name"])
    projects = [pp for pp in projects if not (pp["name"] == project_name and pp.get("storage_name", pp["name"]) == storage)]
    _save_projects(projects)

    project_dir = _get_project_dir(storage)
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir, ignore_errors=True)

    return {"success": True}


# ========================================
# Public API - Status checks
# ========================================

def is_rag_available() -> bool:
    """문서 저장소 사용 가능 여부 (항상 True)."""
    return True


def is_indexed(project_name: str, owner_id: int | None = None) -> bool:
    """Check if a project has any stored documents."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    return len(_get_indexed_docs(storage)) > 0


def get_indexed_count(project_name: str, owner_id: int | None = None) -> int:
    """Get number of stored documents in a project."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    return len(_get_indexed_docs(storage))


def get_indexed_doc_names(project_name: str, owner_id: int | None = None) -> List[str]:
    """Get names of stored documents in a project.
    Always syncs with actual .md files on disk to prevent ghost/orphan docs.
    """
    storage = _get_storage_name(project_name, owner_id=owner_id)
    indexed = set(_get_indexed_docs(storage))
    docs_dir = _get_project_docs_dir(storage)
    if not os.path.exists(docs_dir):
        return list(indexed)

    disk_stems = {os.path.splitext(f)[0] for f in os.listdir(docs_dir) if f.endswith(".md")}

    # Auto-fix: if there's any mismatch, sync index to disk
    if indexed != disk_stems:
        _save_indexed_docs(storage, sorted(disk_stems))
        # Also fix folder structure: remove ghosts, add orphans to root
        folders = _load_folders(storage)
        for folder_key in list(folders.keys()):
            folders[folder_key] = [d for d in folders[folder_key] if d in disk_stems]
        root = folders.setdefault(ROOT_FOLDER, [])
        all_in_folders = set()
        for doc_list in folders.values():
            all_in_folders.update(doc_list)
        for stem in sorted(disk_stems - all_in_folders):
            root.append(stem)
        _save_folders(storage, folders)
        return sorted(disk_stems)

    return sorted(indexed)


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


def load_all_project_docs(project_name: str, owner_id: int | None = None) -> str:
    """Load all documents from a project as concatenated text.
    Returns a single string with all document contents.
    """
    storage = _get_storage_name(project_name, owner_id=owner_id)
    docs_dir = _get_project_docs_dir(storage)
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


def load_selected_project_docs(project_name: str, selected_doc_names: List[str], owner_id: int | None = None) -> str:
    """Load only selected documents from a project as concatenated text.

    Args:
        project_name: Name of the project
        selected_doc_names: List of document names to load (without .md extension)

    Returns:
        Concatenated text of selected documents
    """
    if not selected_doc_names:
        return ""

    storage = _get_storage_name(project_name, owner_id=owner_id)
    docs_dir = _get_project_docs_dir(storage)
    if not os.path.exists(docs_dir):
        return ""

    parts = []
    # Normalize selected names: remove ANY extension to get base name
    # This handles .xlsx, .pdf, .md etc. stored in _indexed_docs.json
    normalized_names = set()
    for name in selected_doc_names:
        normalized_names.add(os.path.splitext(name)[0])

    for fname in sorted(os.listdir(docs_dir)):
        if fname.endswith(".md"):
            doc_name = fname[:-3]  # Remove .md extension
            if doc_name in normalized_names or fname in selected_doc_names:
                fpath = os.path.join(docs_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content:
                        parts.append(content)
                except Exception:
                    pass

    return "\n\n".join(parts)


def load_project_docs_dict(project_name: str, owner_id: int | None = None) -> Dict[str, str]:
    """Load all documents from a project as a dict {filename: content}.
    Falls back to SQLite documents table when filesystem is empty (Railway).
    """
    storage = _get_storage_name(project_name, owner_id=owner_id)
    docs_dir = _get_project_docs_dir(storage)

    result = {}
    if os.path.exists(docs_dir):
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

    # Fallback: load from SQLite documents table (Railway ephemeral FS)
    if not result:
        try:
            from backend.database import get_db
            with get_db() as conn:
                query = "SELECT d.filename, d.parsed_text FROM documents d JOIN projects p ON p.id = d.project_id WHERE p.name = ?"
                params: list = [project_name]
                if owner_id is not None:
                    query += " AND p.owner_id = ?"
                    params.append(owner_id)
                rows = conn.execute(query, params).fetchall()
                for r in rows:
                    if r["parsed_text"] and r["parsed_text"].strip():
                        fname = r["filename"] if r["filename"].endswith(".md") else r["filename"] + ".md"
                        result[fname] = r["parsed_text"].strip()
        except Exception:
            pass

    return result


# ========================================
# Public API - Indexing (saves documents)
# ========================================

def index_texts(api_key: str, texts: Dict[str, str], project_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Save text documents into a project's document store.
    api_key is kept in the signature for backward compatibility but not used.
    """
    storage = _get_storage_name(project_name, owner_id=owner_id)
    already_indexed = set(_get_indexed_docs(storage))
    # Compare using base names (without extension) to avoid duplicates
    already_indexed_stems = {os.path.splitext(d)[0] for d in already_indexed}

    new_texts = {k: v for k, v in texts.items()
                 if os.path.splitext(k)[0] not in already_indexed_stems}
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
                saved_path = _save_doc_file(storage, name, text)
                # Store the stem of the actual saved .md file
                saved_stem = os.path.splitext(os.path.basename(saved_path))[0]
                indexed.append(saved_stem)
        except Exception as e:
            errors.append({"name": name, "error": str(e)})

    # Merge with existing, normalizing all to stems
    all_stems = already_indexed_stems | set(indexed)

    # Update folder structure — ensure ALL stems are in some folder
    # (_save_folders internally syncs _indexed_docs.json, so no separate save needed)
    folders = _load_folders(storage)
    root_docs = folders.setdefault(ROOT_FOLDER, [])
    all_in_folders = set()
    for doc_list in folders.values():
        all_in_folders.update(doc_list)
    for stem in all_stems:
        if stem not in all_in_folders:
            root_docs.append(stem)
    _save_folders(storage, folders)

    if _sync_manager and indexed:
        try:
            for name in indexed:
                content = _load_doc_file(storage, name)
                if content:
                    _sync_manager.on_document_saved(storage, name, content)
        except Exception:
            pass

    # Vector DB 인덱싱은 별도 /reindex 엔드포인트에서 수행
    # (ChromaDB가 uvicorn 프로세스에서 segfault를 유발할 수 있어 업로드 시 자동 인덱싱 제거)

    return {
        "success": len(errors) == 0,
        "indexed": indexed,
        "skipped": [k for k in texts.keys() if k not in new_texts],
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

def clear_rag_index(project_name: str, owner_id: int | None = None):
    """Clear a project's stored documents (keeps the project entry)."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    docs_dir = _get_project_docs_dir(storage)
    if os.path.exists(docs_dir):
        shutil.rmtree(docs_dir, ignore_errors=True)
    os.makedirs(docs_dir, exist_ok=True)
    _save_indexed_docs(storage, [])
    _save_folders(storage, {ROOT_FOLDER: []})


# ========================================
# Trash management (per-project)
# ========================================

def _get_trash_dir(project_name: str) -> str:
    """Return the trash directory for a specific project."""
    return os.path.join(_get_project_dir(project_name), TRASH_SUBDIR)


def trash_document(project_name: str, doc_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Move a document to the trash folder (soft delete)."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    docs_dir = _get_project_docs_dir(storage)
    trash_dir = _get_trash_dir(storage)
    os.makedirs(trash_dir, exist_ok=True)

    # doc_name은 보통 확장자 없는 stem (예: "1.2.1.3 Cardinal_FAQ_202505")
    # os.path.splitext를 쓰면 이름 내 점(.)을 확장자로 잘못 인식하므로
    # stem 그대로 사용하고, 파일 존재 여부로 판단
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", doc_name).strip()
    md_name = f"{sanitized}.md"
    src_path = os.path.join(docs_dir, md_name)

    # Fallback: 확장자가 포함된 이름이 전달된 경우 (예: "report.pdf")
    if not os.path.exists(src_path):
        sanitized_stem = re.sub(r'[\\/*?:"<>|]', "_", os.path.splitext(doc_name)[0]).strip()
        alt_md = f"{sanitized_stem}.md"
        alt_path = os.path.join(docs_dir, alt_md)
        if os.path.exists(alt_path):
            md_name = alt_md
            src_path = alt_path

    if not os.path.exists(src_path):
        return {"success": False, "error": f"파일을 찾을 수 없습니다: {doc_name}"}

    dst_path = os.path.join(trash_dir, md_name)
    shutil.move(src_path, dst_path)

    # Remove from folder structure (_save_folders가 _indexed_docs.json도 동기화)
    folders = _load_folders(storage)
    stem_fallback = os.path.splitext(doc_name)[0]
    for folder_key, doc_list in folders.items():
        # 가능한 모든 형태의 이름으로 제거
        for name_variant in {doc_name, sanitized, stem_fallback}:
            while name_variant in doc_list:
                doc_list.remove(name_variant)
    _save_folders(storage, folders)

    if _sync_manager:
        try:
            _sync_manager.on_document_deleted(storage, doc_name)
        except Exception:
            pass

    return {"success": True}


def list_trash(project_name: str, owner_id: int | None = None) -> List[str]:
    """List documents in the trash folder."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    trash_dir = _get_trash_dir(storage)
    if not os.path.exists(trash_dir):
        return []
    return sorted([f for f in os.listdir(trash_dir) if f.endswith(".md")])


def restore_from_trash(project_name: str, trash_filename: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Restore a document from trash back to docs folder."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    trash_dir = _get_trash_dir(storage)
    docs_dir = _get_project_docs_dir(storage)
    os.makedirs(docs_dir, exist_ok=True)

    src_path = os.path.join(trash_dir, trash_filename)
    if not os.path.exists(src_path):
        return {"success": False, "error": "휴지통에서 파일을 찾을 수 없습니다."}

    dst_path = os.path.join(docs_dir, trash_filename)
    shutil.move(src_path, dst_path)

    # Re-add to indexed docs (use the .md filename as doc_name)
    doc_name = os.path.splitext(trash_filename)[0]
    indexed = _get_indexed_docs(storage)
    if doc_name not in indexed and trash_filename not in indexed:
        indexed.append(doc_name)
    _save_indexed_docs(storage, indexed)

    # Add back to root folder
    folders = _load_folders(storage)
    root_docs = folders.setdefault(ROOT_FOLDER, [])
    if doc_name not in root_docs:
        root_docs.append(doc_name)
    _save_folders(storage, folders)

    return {"success": True}


def permanently_delete_from_trash(project_name: str, trash_filename: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Permanently delete a document from trash."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    trash_dir = _get_trash_dir(storage)
    fpath = os.path.join(trash_dir, trash_filename)
    if os.path.exists(fpath):
        os.remove(fpath)
        return {"success": True}
    return {"success": False, "error": "파일을 찾을 수 없습니다."}


def empty_trash(project_name: str, owner_id: int | None = None) -> Dict[str, Any]:
    """Permanently delete all documents in trash."""
    storage = _get_storage_name(project_name, owner_id=owner_id)
    trash_dir = _get_trash_dir(storage)
    if os.path.exists(trash_dir):
        shutil.rmtree(trash_dir, ignore_errors=True)
    os.makedirs(trash_dir, exist_ok=True)
    return {"success": True}

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
RAG_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_storage")
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


def get_folder_tree(project_name: str) -> Dict[str, List[str]]:
    """Get the folder tree structure for a project.
    Returns dict with folder names as keys and lists of doc names as values.
    ROOT_FOLDER key contains unfiled documents.
    """
    return _load_folders(project_name)


def list_folders(project_name: str) -> List[str]:
    """List all folder names (excluding root) for a project."""
    folders = _load_folders(project_name)
    return [k for k in sorted(folders.keys()) if k != ROOT_FOLDER]


def create_folder(project_name: str, folder_name: str) -> Dict[str, Any]:
    """Create a new folder in the project."""
    folder_name = folder_name.strip()
    if not folder_name:
        return {"success": False, "error": "폴더명을 입력해주세요."}
    if folder_name == ROOT_FOLDER:
        return {"success": False, "error": "예약된 이름입니다."}

    safe_name = re.sub(r'[\\/*?:"<>|]', "", folder_name).strip()
    if not safe_name:
        return {"success": False, "error": "유효하지 않은 폴더명입니다."}

    folders = _load_folders(project_name)
    if safe_name in folders:
        return {"success": False, "error": f"'{safe_name}' 폴더가 이미 존재합니다."}

    folders[safe_name] = []
    _save_folders(project_name, folders)
    return {"success": True, "folder": safe_name}


def rename_folder(project_name: str, old_name: str, new_name: str) -> Dict[str, Any]:
    """Rename a folder."""
    new_name = new_name.strip()
    if not new_name or new_name == ROOT_FOLDER:
        return {"success": False, "error": "유효하지 않은 폴더명입니다."}

    safe_name = re.sub(r'[\\/*?:"<>|]', "", new_name).strip()
    if not safe_name:
        return {"success": False, "error": "유효하지 않은 폴더명입니다."}

    folders = _load_folders(project_name)
    if old_name not in folders or old_name == ROOT_FOLDER:
        return {"success": False, "error": f"'{old_name}' 폴더를 찾을 수 없습니다."}
    if safe_name in folders:
        return {"success": False, "error": f"'{safe_name}' 폴더가 이미 존재합니다."}

    folders[safe_name] = folders.pop(old_name)
    _save_folders(project_name, folders)
    return {"success": True}


def delete_folder(project_name: str, folder_name: str) -> Dict[str, Any]:
    """Delete a folder and move its documents to root."""
    if folder_name == ROOT_FOLDER:
        return {"success": False, "error": "루트 폴더는 삭제할 수 없습니다."}

    folders = _load_folders(project_name)
    if folder_name not in folders:
        return {"success": False, "error": f"'{folder_name}' 폴더를 찾을 수 없습니다."}

    # Move docs to root
    docs_to_move = folders.pop(folder_name)
    folders.setdefault(ROOT_FOLDER, []).extend(docs_to_move)
    _save_folders(project_name, folders)
    return {"success": True}


def move_doc_to_folder(project_name: str, doc_name: str, target_folder: str) -> Dict[str, Any]:
    """Move a document to a different folder (or ROOT_FOLDER for unfiled)."""
    folders = _load_folders(project_name)

    if target_folder != ROOT_FOLDER and target_folder not in folders:
        return {"success": False, "error": f"'{target_folder}' 폴더를 찾을 수 없습니다."}

    # Remove from current folder
    for folder_key, doc_list in folders.items():
        if doc_name in doc_list:
            doc_list.remove(doc_name)
            break

    # Add to target folder
    folders.setdefault(target_folder, []).append(doc_name)
    _save_folders(project_name, folders)
    return {"success": True}


def get_doc_folder(project_name: str, doc_name: str) -> str:
    """Get the folder that contains a document. Returns ROOT_FOLDER if unfiled."""
    folders = _load_folders(project_name)
    for folder_key, doc_list in folders.items():
        if doc_name in doc_list:
            return folder_key
    return ROOT_FOLDER


def index_texts_to_folder(
    api_key: str, texts: Dict[str, str], project_name: str, folder: str = ROOT_FOLDER
) -> Dict[str, Any]:
    """Save text documents into a specific folder in the project.
    Wrapper around index_texts that places new docs into the specified folder.
    """
    result = index_texts(api_key, texts, project_name)

    # Move newly indexed docs to the target folder
    if result.get("indexed") and folder != ROOT_FOLDER:
        folders = _load_folders(project_name)
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
        _save_folders(project_name, folders)

    return result


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

    # [기능 추가] 기본 템플릿 문서 자동 생성
    templates = {
        "README.md": f"# {safe_name}\n\n생성일: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n## 프로젝트 개요\n이 프로젝트는 GEM Intern을 통해 생성되었습니다.\n\n## 주요 목표\n- \n",
        "Memo.md": "# 메모\n\n아이디어 및 주요 사항을 기록하세요.\n"
    }
    for fname, content in templates.items():
        _save_doc_file(safe_name, fname, content)
    template_stems = [os.path.splitext(f)[0] for f in templates.keys()]
    _save_indexed_docs(safe_name, template_stems)
    _save_folders(safe_name, {ROOT_FOLDER: template_stems})

    new_project = {
        "name": safe_name,
        "created": datetime.datetime.now().isoformat(),
        "last_accessed": datetime.datetime.now().isoformat(),
        "doc_count": len(templates),
    }
    projects.append(new_project)
    _save_projects(projects)

    if _sync_manager:
        try:
            _sync_manager.on_project_created(safe_name)
        except Exception:
            pass

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
    """Get names of stored documents in a project.
    Falls back to reading actual .md files from disk if index is empty/missing.
    """
    names = _get_indexed_docs(project_name)
    if names:
        return names
    # Fallback: read actual .md files from disk
    docs_dir = _get_project_docs_dir(project_name)
    if os.path.exists(docs_dir):
        return [os.path.splitext(f)[0] for f in sorted(os.listdir(docs_dir)) if f.endswith(".md")]
    return []


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


def load_selected_project_docs(project_name: str, selected_doc_names: List[str]) -> str:
    """Load only selected documents from a project as concatenated text.

    Args:
        project_name: Name of the project
        selected_doc_names: List of document names to load (without .md extension)

    Returns:
        Concatenated text of selected documents
    """
    if not selected_doc_names:
        return ""

    docs_dir = _get_project_docs_dir(project_name)
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
                saved_path = _save_doc_file(project_name, name, text)
                # Store the stem of the actual saved .md file
                saved_stem = os.path.splitext(os.path.basename(saved_path))[0]
                indexed.append(saved_stem)
        except Exception as e:
            errors.append({"name": name, "error": str(e)})

    # Merge with existing, normalizing all to stems
    all_stems = already_indexed_stems | set(indexed)
    _save_indexed_docs(project_name, list(all_stems))

    # Add new docs to root folder in folder structure
    if indexed:
        folders = _load_folders(project_name)
        root_docs = folders.setdefault(ROOT_FOLDER, [])
        for doc_stem in indexed:
            if not any(doc_stem in doc_list for doc_list in folders.values()):
                root_docs.append(doc_stem)
        _save_folders(project_name, folders)

    if _sync_manager and indexed:
        try:
            for name in indexed:
                content = _load_doc_file(project_name, name)
                if content:
                    _sync_manager.on_document_saved(project_name, name, content)
        except Exception:
            pass

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

def clear_rag_index(project_name: str):
    """Clear a project's stored documents (keeps the project entry)."""
    docs_dir = _get_project_docs_dir(project_name)
    if os.path.exists(docs_dir):
        shutil.rmtree(docs_dir, ignore_errors=True)
    os.makedirs(docs_dir, exist_ok=True)
    _save_indexed_docs(project_name, [])
    _save_folders(project_name, {ROOT_FOLDER: []})


# ========================================
# Trash management (per-project)
# ========================================

def _get_trash_dir(project_name: str) -> str:
    """Return the trash directory for a specific project."""
    return os.path.join(_get_project_dir(project_name), TRASH_SUBDIR)


def trash_document(project_name: str, doc_name: str) -> Dict[str, Any]:
    """Move a document to the trash folder (soft delete)."""
    docs_dir = _get_project_docs_dir(project_name)
    trash_dir = _get_trash_dir(project_name)
    os.makedirs(trash_dir, exist_ok=True)

    # Find the actual file (original name or .md version)
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", os.path.splitext(doc_name)[0]).strip()
    md_name = f"{safe_name}.md"
    src_path = os.path.join(docs_dir, md_name)

    if not os.path.exists(src_path):
        return {"success": False, "error": f"파일을 찾을 수 없습니다: {doc_name}"}

    dst_path = os.path.join(trash_dir, md_name)
    shutil.move(src_path, dst_path)

    # Remove from indexed docs list and folder structure
    indexed = _get_indexed_docs(project_name)
    indexed = [d for d in indexed if d != doc_name]
    _save_indexed_docs(project_name, indexed)

    # Remove from folder structure
    folders = _load_folders(project_name)
    stem = os.path.splitext(doc_name)[0]
    for folder_key, doc_list in folders.items():
        if doc_name in doc_list:
            doc_list.remove(doc_name)
        if stem in doc_list:
            doc_list.remove(stem)
    _save_folders(project_name, folders)

    if _sync_manager:
        try:
            _sync_manager.on_document_deleted(project_name, doc_name)
        except Exception:
            pass

    return {"success": True}


def list_trash(project_name: str) -> List[str]:
    """List documents in the trash folder."""
    trash_dir = _get_trash_dir(project_name)
    if not os.path.exists(trash_dir):
        return []
    return sorted([f for f in os.listdir(trash_dir) if f.endswith(".md")])


def restore_from_trash(project_name: str, trash_filename: str) -> Dict[str, Any]:
    """Restore a document from trash back to docs folder."""
    trash_dir = _get_trash_dir(project_name)
    docs_dir = _get_project_docs_dir(project_name)
    os.makedirs(docs_dir, exist_ok=True)

    src_path = os.path.join(trash_dir, trash_filename)
    if not os.path.exists(src_path):
        return {"success": False, "error": "휴지통에서 파일을 찾을 수 없습니다."}

    dst_path = os.path.join(docs_dir, trash_filename)
    shutil.move(src_path, dst_path)

    # Re-add to indexed docs (use the .md filename as doc_name)
    doc_name = os.path.splitext(trash_filename)[0]
    indexed = _get_indexed_docs(project_name)
    if doc_name not in indexed and trash_filename not in indexed:
        indexed.append(doc_name)
    _save_indexed_docs(project_name, indexed)

    # Add back to root folder
    folders = _load_folders(project_name)
    root_docs = folders.setdefault(ROOT_FOLDER, [])
    if doc_name not in root_docs:
        root_docs.append(doc_name)
    _save_folders(project_name, folders)

    return {"success": True}


def permanently_delete_from_trash(project_name: str, trash_filename: str) -> Dict[str, Any]:
    """Permanently delete a document from trash."""
    trash_dir = _get_trash_dir(project_name)
    fpath = os.path.join(trash_dir, trash_filename)
    if os.path.exists(fpath):
        os.remove(fpath)
        return {"success": True}
    return {"success": False, "error": "파일을 찾을 수 없습니다."}


def empty_trash(project_name: str) -> Dict[str, Any]:
    """Permanently delete all documents in trash."""
    trash_dir = _get_trash_dir(project_name)
    if os.path.exists(trash_dir):
        shutil.rmtree(trash_dir, ignore_errors=True)
    os.makedirs(trash_dir, exist_ok=True)
    return {"success": True}

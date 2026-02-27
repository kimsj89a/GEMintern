"""FastAPI REST API routes for GEMintern."""
import io
import json
import os
import uuid
import tempfile
from typing import List, Dict

from fastapi import APIRouter, UploadFile, File

from pydantic import BaseModel
from backend.api_models import (
    ProjectCreate, FolderCreate, DocMoveRequest,
    GenerateRequest, QaRequest, SyncRequest, AnalysisRequest,
)
from backend.api_ws import create_task, run_generate_task, run_analysis_task, get_task

router = APIRouter()

# Max context size (~200K tokens for Gemini)
MAX_CONTEXT_CHARS = 800_000


def _load_context_with_budget(project_name: str, selected_docs: list = None,
                               max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Load project docs with per-document truncation and clear headers."""
    import core_rag
    docs_dict = core_rag.load_project_docs_dict(project_name)

    if selected_docs:
        docs_dict = {k: v for k, v in docs_dict.items() if k.replace('.md', '') in selected_docs or k in selected_docs}

    if not docs_dict:
        return ""

    n = len(docs_dict)
    per_doc = max_chars // n
    parts = []
    for name, content in sorted(docs_dict.items()):
        doc_name = name.replace('.md', '')
        if len(content) > per_doc:
            content = content[:per_doc] + f"\n\n[... '{doc_name}' 문서 일부 생략 ({len(content):,}자 중 {per_doc:,}자)]"
        parts.append(f"===== 문서: {doc_name} =====\n{content}")

    return '\n\n'.join(parts)


def _truncate_context(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Simple truncation fallback for pre-loaded text."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... 컨텍스트 길이 제한으로 잘림]"


def _get_vector_context(api_key: str, project_name: str, query: str,
                        selected_docs: list = None) -> str:
    """Vector 검색으로 관련 청크 추출. ChromaDB segfault 방지를 위해 서브프로세스에서 실행."""
    import subprocess, sys, json as _json
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vdb_dir = os.path.join(base, "rag_storage", "_vectordb")
        if not os.path.isdir(vdb_dir):
            raise FileNotFoundError("no vectordb")

        # 서브프로세스에서 ChromaDB 검색 실행 (segfault 격리)
        script = f"""
import sys, json
sys.path.insert(0, {repr(base)})
import core_rag_vector
result = core_rag_vector.build_context_from_search(
    {repr(api_key)}, {repr(project_name)}, {repr(query)},
    selected_docs={repr(selected_docs)})
if result:
    print("__VECTOR_OK__")
    print(result)
else:
    print("__VECTOR_EMPTY__")
"""
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=30, cwd=base,
        )
        if proc.returncode == 0 and "__VECTOR_OK__" in proc.stdout:
            context = proc.stdout.split("__VECTOR_OK__\n", 1)[1]
            if context.strip():
                return context
    except Exception:
        pass
    # Fallback: 전체 문서 로드 + 예산 분배
    return _load_context_with_budget(project_name, selected_docs)

# Settings file path
SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "settings.json"
)


def _load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ========================================
# Health
# ========================================

@router.get("/health")
def health_check():
    return {"status": "ok", "version": "7.0"}


# ========================================
# Settings
# ========================================

@router.get("/settings")
def get_settings():
    data = _load_settings()
    masked = {**data}
    if masked.get("api_key"):
        key = masked["api_key"]
        masked["api_key_masked"] = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    return masked


@router.put("/settings")
def update_settings(settings: dict):
    current = _load_settings()
    current.update(settings)
    _save_settings(current)
    return {"success": True}


@router.post("/settings/apply")
def apply_settings():
    data = _load_settings()
    if not data.get("api_key"):
        return {"success": False, "error": "API Key가 설정되지 않았습니다."}
    try:
        import core_logic
        core_logic.get_client(data["api_key"])
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========================================
# Projects
# ========================================

@router.get("/projects")
def list_projects():
    import core_rag
    return core_rag.list_projects()


@router.post("/projects")
def create_project(req: ProjectCreate):
    import core_rag
    return core_rag.create_project(req.name)


@router.delete("/projects/{name}")
def delete_project(name: str):
    import core_rag
    return core_rag.delete_project(name)


# ========================================
# Documents & Folders
# ========================================

@router.get("/projects/{name}/docs")
def get_project_docs(name: str):
    import core_rag
    tree = core_rag.get_folder_tree(name)
    doc_names = core_rag.get_indexed_doc_names(name) or []
    return {"folder_tree": tree, "doc_names": doc_names, "count": len(doc_names)}


@router.post("/projects/{name}/folders")
def create_folder(name: str, req: FolderCreate):
    import core_rag
    return core_rag.create_folder(name, req.name)


@router.delete("/projects/{name}/folders/{folder}")
def delete_folder(name: str, folder: str):
    import core_rag
    return core_rag.delete_folder(name, folder)


@router.post("/projects/{name}/docs/{doc}/move")
def move_doc(name: str, doc: str, req: DocMoveRequest):
    import core_rag
    return core_rag.move_doc_to_folder(name, doc, req.target_folder)


@router.delete("/projects/{name}/docs/{doc}")
def trash_doc(name: str, doc: str):
    import core_rag
    return core_rag.trash_document(name, doc)


@router.post("/projects/{name}/upload")
async def upload_files(name: str, files: List[UploadFile] = File(...)):
    import core_rag
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    texts = {}
    parse_errors = []
    for f in files:
        content_bytes = await f.read()
        parsed = _parse_file_bytes(f.filename, content_bytes, api_key)
        if parsed:
            texts[f.filename] = parsed
        else:
            parse_errors.append(f.filename)
    result = core_rag.index_texts(api_key, texts, name)
    if parse_errors:
        result["parse_errors"] = parse_errors
    return result


def _parse_file_bytes(filename: str, data: bytes, api_key: str = "") -> str:
    """파일 바이트를 텍스트로 변환. PDF/DOCX/PPTX/XLSX 파서 지원."""
    import tempfile
    ext = os.path.splitext(filename)[1].lower()

    # 텍스트 파일은 직접 디코드
    if ext in ('.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm'):
        return data.decode("utf-8", errors="replace")

    # MarkItDown 우선 시도 (PDF, DOCX, PPTX, XLSX 등 다양한 포맷 지원)
    try:
        from markitdown import MarkItDown
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            import concurrent.futures
            def _convert(path):
                md = MarkItDown()
                return md.convert(path)
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_convert, tmp_path)
                result = future.result(timeout=120)
            if result and result.text_content and len(result.text_content.strip()) > 50:
                return f"### [파일명: {filename}]\n{result.text_content}"
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
    except Exception:
        pass

    # PDF fallback: PyMuPDF
    if ext == '.pdf':
        try:
            import fitz
            with fitz.open(stream=data, filetype="pdf") as doc:
                pages = []
                for page in doc:
                    pages.append(page.get_text())
                text = "\n\n".join(pages)
                if text.strip():
                    return f"### [파일명: {filename}]\n{text}"
        except Exception:
            pass

    # DOCX fallback: python-docx
    if ext in ('.docx', '.doc'):
        try:
            from docx import Document
            doc = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in doc.paragraphs)
            if text.strip():
                return f"### [파일명: {filename}]\n{text}"
        except Exception:
            pass

    # PPTX fallback: python-pptx
    if ext in ('.pptx', '.ppt'):
        try:
            from pptx import Presentation
            prs = Presentation(io.BytesIO(data))
            text_parts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        text_parts.append(shape.text)
            text = "\n".join(text_parts)
            if text.strip():
                return f"### [파일명: {filename}]\n{text}"
        except Exception:
            pass

    # XLSX fallback: openpyxl
    if ext in ('.xlsx', '.xls'):
        try:
            import pandas as pd
            df = pd.read_excel(io.BytesIO(data), sheet_name=None)
            parts = []
            for sheet_name, sheet_df in df.items():
                parts.append(f"## 시트: {sheet_name}\n{sheet_df.to_markdown()}")
            text = "\n\n".join(parts)
            if text.strip():
                return f"### [파일명: {filename}]\n{text}"
        except Exception:
            pass

    # 최종 fallback: UTF-8 디코드
    return data.decode("utf-8", errors="replace")


# ========================================
# AI Generation
# ========================================

@router.post("/generate")
def start_generate(req: GenerateRequest):
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    model = settings.get("model_name", "gemini-3.1-pro-preview")

    user_context = req.file_context.strip()  # 유저가 입력한 추가 컨텍스트
    selected_docs = req.inputs.get("selected_docs", [])
    print(f"[generate] project={req.project_name}, template={req.template_option}, "
          f"user_context_len={len(user_context)}, selected_docs={selected_docs}")

    # 항상 프로젝트 문서를 로드 (유저 컨텍스트 유무와 무관)
    file_context = ""
    if req.project_name:
        file_context = _load_context_with_budget(
            req.project_name, selected_docs if selected_docs else None
        )
        print(f"[generate] loaded docs: {len(file_context)} chars")

    # Pass template_option and user context into inputs for core_logic
    inputs = dict(req.inputs)
    inputs.setdefault("template_option", req.template_option)
    inputs["context_text"] = user_context  # 유저 컨텍스트를 프롬프트에 전달

    task_id = create_task()
    run_generate_task(
        task_id, api_key, model,
        inputs, req.thinking_level, file_context,
        mode=req.mode
    )
    return {"task_id": task_id}


@router.post("/qa")
def start_qa(req: QaRequest):
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    model = settings.get("model_name", "gemini-3.1-pro-preview")

    # Vector 검색으로 관련 청크만 추출 (fallback: 전체 로드)
    context = _get_vector_context(
        api_key, req.project_name, req.question, req.selected_docs
    )
    task_id = create_task()
    run_analysis_task(
        task_id, "qa_answer", api_key, model,
        file_context=context, question=req.question
    )
    return {"task_id": task_id}


@router.post("/analyze")
def start_analysis(req: AnalysisRequest):
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    model = settings.get("model_name", "gemini-3.1-pro-preview")

    # If project_name is in kwargs, use vector search for context
    kwargs = dict(req.kwargs)
    if "project_name" in kwargs:
        pname = kwargs.pop("project_name")
        sel_docs = kwargs.pop("selected_docs", [])
        # analysis의 경우 task_type을 query로 사용
        query = kwargs.get("question", req.task_type)
        kwargs["file_context"] = _get_vector_context(
            api_key, pname, query, sel_docs
        )

    task_id = create_task()
    run_analysis_task(task_id, req.task_type, api_key, model, **kwargs)
    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        return {"error": "Task not found"}
    return {
        "task_id": task_id,
        "status": task["status"],
        "result": task["result"],
        "error": task["error"],
    }


# ========================================
# Vector RAG
# ========================================

@router.post("/projects/{name}/reindex")
def reindex_project(name: str, force: bool = False):
    """프로젝트 문서를 벡터 DB에 증분 인덱싱 (서브프로세스에서 실행, segfault 격리).

    force=True면 전체 재인덱싱, 기본은 변경분만 처리.
    """
    import subprocess, sys, json as _json
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    if not api_key:
        return {"success": False, "error": "API Key가 설정되지 않았습니다."}
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script = f"""
import sys, json
sys.path.insert(0, {repr(base)})
import core_rag_vector
result = core_rag_vector.index_project_all({repr(api_key)}, {repr(name)}, force={repr(force)})
print(json.dumps(result, ensure_ascii=False))
"""
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=300, cwd=base,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return _json.loads(proc.stdout.strip().split("\n")[-1])
        error_msg = proc.stderr.strip() if proc.stderr else f"exit code {proc.returncode}"
        return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/projects/{name}/vector-stats")
def vector_stats(name: str):
    """프로젝트 벡터 인덱스 통계 (파일시스템 기반, ChromaDB 직접 열지 않음)."""
    try:
        local_data = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "GEMintern")
        vdb_dir = os.path.join(local_data, "vectordb")
        # ChromaDB 디렉토리 존재 여부로 인덱싱 상태 판단
        if os.path.isdir(vdb_dir) and any(
            f for f in os.listdir(vdb_dir) if not f.startswith(".")
        ):
            return {"total_chunks": -1, "documents": -1, "indexed": True,
                    "note": "벡터 DB 존재 (상세 통계는 재인덱싱 시 확인)"}
        return {"total_chunks": 0, "documents": 0, "indexed": False}
    except Exception as e:
        return {"total_chunks": 0, "documents": 0, "indexed": False, "error": str(e)}


@router.get("/projects/{name}/sync-status")
def doc_sync_status(name: str):
    """파일 목록과 RAG DB 동기화 상태 비교."""
    import core_rag
    try:
        # RAG storage에 저장된 문서 목록 (indexed .md files)
        indexed_names = set(core_rag.get_indexed_doc_names(name))

        # 실제 docs 디렉토리의 .md 파일
        docs_dir = core_rag._get_project_docs_dir(name)
        disk_files = {}
        if os.path.isdir(docs_dir):
            for f in sorted(os.listdir(docs_dir)):
                if f.endswith(".md"):
                    fpath = os.path.join(docs_dir, f)
                    stat = os.stat(fpath)
                    doc_name = f[:-3]  # remove .md
                    disk_files[doc_name] = {
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    }

        disk_names = set(disk_files.keys())

        docs = []
        for doc_name in sorted(disk_names | indexed_names):
            on_disk = doc_name in disk_names
            in_index = doc_name in indexed_names
            info = disk_files.get(doc_name, {})
            status = "synced" if on_disk and in_index else "disk_only" if on_disk else "index_only"
            docs.append({
                "name": doc_name,
                "status": status,
                "size": info.get("size", 0),
                "modified": info.get("modified", 0),
            })

        return {
            "total_disk": len(disk_names),
            "total_indexed": len(indexed_names),
            "synced": len(disk_names & indexed_names),
            "disk_only": len(disk_names - indexed_names),
            "index_only": len(indexed_names - disk_names),
            "docs": docs,
        }
    except Exception as e:
        return {"error": str(e), "docs": []}


class SyncDocsRequest(BaseModel):
    add: List[str] = []       # disk_only 파일을 인덱스에 추가
    remove: List[str] = []    # index_only 항목을 인덱스에서 제거


@router.post("/projects/{name}/sync-docs")
def sync_selected_docs(name: str, req: SyncDocsRequest):
    """선택한 파일들의 동기화 상태를 변경."""
    import core_rag
    try:
        indexed = set(core_rag.get_indexed_doc_names(name))
        folders = core_rag._load_folders(name)

        # disk_only → 인덱스에 추가
        for doc_name in req.add:
            indexed.add(doc_name)
            # 폴더 구조에도 추가 (어디에도 없으면 root에)
            in_any = any(doc_name in docs for docs in folders.values())
            if not in_any:
                root = folders.setdefault(core_rag.ROOT_FOLDER, [])
                root.append(doc_name)

        # index_only → 인덱스에서 제거
        for doc_name in req.remove:
            indexed.discard(doc_name)
            # 폴더 구조에서도 제거
            for folder_docs in folders.values():
                if doc_name in folder_docs:
                    folder_docs.remove(doc_name)

        core_rag._save_indexed_docs(name, list(indexed))
        core_rag._save_folders(name, folders)

        return {
            "success": True,
            "added": len(req.add),
            "removed": len(req.remove),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========================================
# Cloud Sync
# ========================================

@router.get("/sync/status")
def sync_status():
    settings = _load_settings()
    cs = settings.get("cloud_sync", {})
    services = []
    if cs.get("onedrive_enabled"):
        services.append("OneDrive")
    if cs.get("gsheets_enabled"):
        services.append("GSheets")
    if cs.get("gdrive_enabled"):
        services.append("GDrive")
    return {"connected": len(services) > 0, "services": services}


@router.post("/sync/push")
def sync_push(req: SyncRequest):
    from cloud_sync import CloudSyncManager
    mgr = _get_sync_manager()
    if not mgr:
        return {"success": False, "error": "클라우드 미연결"}
    return mgr.push_project(req.project_name)


@router.post("/sync/pull")
def sync_pull(req: SyncRequest):
    mgr = _get_sync_manager()
    if not mgr:
        return {"success": False, "error": "클라우드 미연결"}
    return mgr.pull_project(req.project_name)


@router.post("/sync/full")
def sync_full(req: SyncRequest):
    mgr = _get_sync_manager()
    if not mgr:
        return {"success": False, "error": "클라우드 미연결"}
    return mgr.full_sync(req.project_name)


def _get_sync_manager():
    """Create a CloudSyncManager from current settings."""
    settings = _load_settings()
    cs = settings.get("cloud_sync", {})

    gdrive_client = None
    if cs.get("gdrive_enabled") and cs.get("gdrive_client_id"):
        try:
            from utils_gdrive import GoogleDriveClient
            gdrive_client = GoogleDriveClient(
                cs["gdrive_client_id"],
                cs.get("gdrive_client_secret", ""),
            )
            gdrive_client.load_saved_token()
        except Exception:
            pass

    gsheets_client = None
    if cs.get("gsheets_enabled") and cs.get("gsheets_credentials_path"):
        try:
            from utils_gsheets import GSheetsClient
            cred_path = cs["gsheets_credentials_path"]
            if os.path.exists(cred_path):
                gsheets_client = GSheetsClient(cred_path)
        except Exception:
            pass

    if gdrive_client or gsheets_client:
        from cloud_sync import CloudSyncManager
        return CloudSyncManager(gdrive_client=gdrive_client, gsheets_client=gsheets_client)
    return None


# ========================================
# OCR
# ========================================

@router.post("/ocr")
async def ocr_files(files: List[UploadFile] = File(...), engine: str = "gemini"):
    """이미지/PDF에서 텍스트 추출 (Gemini Vision 또는 Document AI)."""
    import fitz
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    results = []

    for f in files:
        data = await f.read()
        ext = os.path.splitext(f.filename)[1].lower()
        text = ""

        try:
            if ext == '.pdf':
                doc = fitz.open(stream=data, filetype="pdf")
                if engine == "gemini" and api_key:
                    import ocr as ocr_module
                    text = ocr_module.extract_pdf_with_gemini_ocr(doc, api_key)
                elif engine == "docai":
                    try:
                        import utils_docai
                        text = utils_docai.process_document(data)
                    except Exception:
                        text = ocr_module.extract_pdf_with_ocr(doc) if 'ocr_module' in dir() else ""
                else:
                    import ocr as ocr_module
                    text = ocr_module.extract_pdf_with_ocr(doc)
                doc.close()
            elif ext in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp'):
                if engine == "gemini" and api_key:
                    from google import genai
                    from google.genai import types
                    client = genai.Client(api_key=api_key)
                    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg',
                                '.jpeg': 'image/jpeg', '.tiff': 'image/tiff', '.bmp': 'image/bmp'}
                    mime = mime_map.get(ext, 'image/png')
                    response = client.models.generate_content(
                        model="gemini-3-pro-preview",
                        contents=[
                            types.Part.from_bytes(data=data, mime_type=mime),
                            "이 이미지의 내용을 텍스트로 추출해줘. 표는 Markdown 표 문법으로 변환해줘. 서론 없이 결과만 출력해."
                        ],
                        config=types.GenerateContentConfig(temperature=0.0)
                    )
                    text = response.text.strip() if response.text else ""
                elif engine == "docai":
                    try:
                        import utils_docai
                        text = utils_docai.process_document(data)
                    except Exception as e:
                        text = f"Document AI 오류: {e}"
                else:
                    text = "API 키가 필요합니다."
            else:
                text = f"지원하지 않는 형식: {ext}"
        except Exception as e:
            text = f"처리 오류: {e}"

        results.append({"filename": f.filename, "text": text})

    return {"results": results}


# ========================================
# Markdown to Word
# ========================================

class FreeDocRequest(BaseModel):
    instruction: str
    file_text: str = ""
    paste_text: str = ""


class MarkdownToDocxRequest(BaseModel):
    markdown: str
    filename: str = "output.docx"


# ========================================
# Free-form Document Writing
# ========================================

@router.post("/freedoc/upload")
async def freedoc_upload(files: List[UploadFile] = File(...)):
    """자유양식 문서작성: 파일 업로드 → 파싱된 텍스트 반환."""
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    parsed_parts = []
    for f in files:
        content_bytes = await f.read()
        parsed = _parse_file_bytes(f.filename, content_bytes, api_key)
        if parsed:
            parsed_parts.append(f"--- [{f.filename}] ---\n{parsed}")
    return {"file_text": "\n\n".join(parsed_parts), "count": len(parsed_parts)}


@router.post("/freedoc/generate")
def freedoc_generate(req: FreeDocRequest):
    """자유양식 문서작성: 파싱된 텍스트 + 지시사항 → AI 문서 생성 (task)."""
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    model = settings.get("model_name", "gemini-3.1-pro-preview")

    combined = req.file_text
    if req.paste_text.strip():
        combined += f"\n\n--- [직접 입력 텍스트] ---\n{req.paste_text.strip()}"

    if not combined.strip():
        return {"error": "자료가 비어있습니다."}

    task_id = create_task()

    def _run():
        task = get_task(task_id)
        task["status"] = "generating"
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)

            system_prompt = (
                "당신은 전문 문서 작성 AI입니다.\n"
                "제공된 자료를 분석하여 사용자의 지시에 맞는 문서를 작성합니다.\n\n"
                "[핵심 규칙]\n"
                "1. 제공된 자료의 내용을 충실히 반영하세요. 자료에 없는 내용을 임의로 추가하지 마세요.\n"
                "2. 서문, 인트로, 설명 문장 없이 바로 마크다운 본문(# 헤딩)으로 시작하세요.\n"
                "3. 수치, 고유명사, 날짜 등 구체적 데이터는 절대 변경하지 마세요.\n"
                "4. 논리적이고 체계적인 구조로 작성하세요.\n"
                "5. 마크다운 형식으로 출력하세요.\n"
                "6. 한국어로 작성하세요.\n"
            )

            prompt = (
                f"[사용자 지시사항]\n{req.instruction}\n\n"
                f"[제공된 자료]\n{_truncate_context(combined)}"
            )

            config = types.GenerateContentConfig(
                max_output_tokens=65536,
                temperature=0.4,
                system_instruction=system_prompt,
            )

            stream = client.models.generate_content_stream(
                model=model, contents=prompt, config=config
            )
            full_text = ""
            for chunk in stream:
                text = chunk.text or "" if hasattr(chunk, "text") else ""
                if text:
                    full_text += text
                    task["chunks"].append(text)
            task["result"] = full_text
            task["status"] = "complete"
        except Exception as e:
            task["error"] = str(e)
            task["status"] = "error"

    import threading
    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id}


@router.post("/markdown-to-docx")
def markdown_to_docx(req: MarkdownToDocxRequest):
    """마크다운 텍스트를 Word 문서로 변환."""
    from fastapi.responses import Response
    import utils
    docx_bytes = utils.create_docx(req.markdown)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{req.filename}"'},
    )


# ========================================
# Document Updater
# ========================================

_doc_updater_sessions: Dict[str, str] = {}  # session_id -> temp_dir


class DocUpdaterRunRequest(BaseModel):
    session_id: str
    supplementary_text: str = ""
    instruction: str
    mode: str = "full"


@router.post("/doc-updater/upload-original")
async def doc_updater_upload_original(file: UploadFile = File(...)):
    """원본 문서 업로드 → 인덱싱 프리뷰 반환."""
    import core_doc_updater

    session_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.mkdtemp(prefix="gemintern_docupd_")
    _doc_updater_sessions[session_id] = temp_dir

    file_path = os.path.join(temp_dir, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        doc_type, indexed = core_doc_updater.index_document(file_path)
        preview = core_doc_updater.format_document_map(indexed)
    except Exception as e:
        return {"error": f"문서 인덱싱 오류: {e}"}

    return {
        "session_id": session_id,
        "filename": file.filename,
        "doc_type": doc_type,
        "paragraph_count": len(indexed),
        "preview": preview[:5000],
    }


@router.post("/doc-updater/{session_id}/supplementary")
async def doc_updater_upload_supplementary(
    session_id: str, files: List[UploadFile] = File(...)
):
    """추가 자료 파일 업로드."""
    temp_dir = _doc_updater_sessions.get(session_id)
    if not temp_dir:
        return {"error": "세션이 없습니다. 원본 문서를 먼저 업로드해주세요."}

    sup_dir = os.path.join(temp_dir, "supplementary")
    os.makedirs(sup_dir, exist_ok=True)

    filenames = []
    for f in files:
        path = os.path.join(sup_dir, f.filename)
        content = await f.read()
        with open(path, "wb") as out:
            out.write(content)
        filenames.append(f.filename)

    return {"filenames": filenames, "count": len(filenames)}


@router.post("/doc-updater/run")
def doc_updater_run(req: DocUpdaterRunRequest):
    """문서 업데이트 실행 (백그라운드)."""
    temp_dir = _doc_updater_sessions.get(req.session_id)
    if not temp_dir:
        return {"error": "세션이 없습니다."}

    settings = _load_settings()
    api_key = settings.get("api_key", "")
    model = settings.get("model_name", "gemini-3.1-pro-preview")

    # Find original file
    original_files = [
        f for f in os.listdir(temp_dir)
        if os.path.isfile(os.path.join(temp_dir, f))
    ]
    if not original_files:
        return {"error": "원본 문서가 없습니다."}
    original_path = os.path.join(temp_dir, original_files[0])

    # Find supplementary files
    sup_dir = os.path.join(temp_dir, "supplementary")
    sup_paths = []
    if os.path.isdir(sup_dir):
        sup_paths = [
            os.path.join(sup_dir, f) for f in os.listdir(sup_dir)
            if os.path.isfile(os.path.join(sup_dir, f))
        ]

    task_id = create_task()

    def _run():
        task = get_task(task_id)
        task["status"] = "generating"
        try:
            import core_doc_updater
            output_path, summary, preview = core_doc_updater.update_document(
                original_path, sup_paths, req.supplementary_text,
                req.instruction, req.mode, api_key, model,
            )
            task["result"] = json.dumps({
                "output_path": output_path,
                "output_filename": os.path.basename(output_path),
                "summary": summary,
                "preview": preview,
            }, ensure_ascii=False)
            task["status"] = "complete"
        except Exception as e:
            task["error"] = str(e)
            task["status"] = "error"

    import threading
    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id}


@router.get("/doc-updater/download")
def doc_updater_download(path: str):
    """업데이트된 문서 다운로드."""
    from fastapi.responses import FileResponse
    if not os.path.exists(path):
        return {"error": "파일을 찾을 수 없습니다."}
    return FileResponse(
        path,
        filename=os.path.basename(path),
        media_type="application/octet-stream",
    )

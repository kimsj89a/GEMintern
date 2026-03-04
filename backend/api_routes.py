"""FastAPI REST API routes for GEMintern."""
import io
import json
import os
import uuid
import tempfile
from typing import List, Dict

from fastapi import APIRouter, UploadFile, File, Depends

from pydantic import BaseModel
from backend.api_models import (
    ProjectCreate, FolderCreate, DocMoveRequest,
    GenerateRequest, QaRequest, AnalysisRequest,
)
from backend.api_ws import create_task, run_generate_task, run_analysis_task, get_task
from backend.auth import get_current_user
from backend.database import log_usage

router = APIRouter()


def _get_api_key() -> str:
    """Return Gemini API key: env var first, then settings.json fallback."""
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key:
        return env_key
    return _load_settings().get("api_key", "")


def _get_model_name() -> str:
    """Return model name: env var first, then settings.json fallback."""
    env_model = os.environ.get("MODEL_NAME", "")
    if env_model:
        return env_model
    return _load_settings().get("model_name", "gemini-2.5-flash")


def _get_anthropic_api_key() -> str:
    """Return Anthropic API key: env var first, then settings.json fallback."""
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        return env_key
    return _load_settings().get("anthropic_api_key", "")

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
    return {"status": "ok", "version": "7.1"}


# ========================================
# Settings
# ========================================

@router.get("/settings")
def get_settings(user: dict = Depends(get_current_user)):
    data = _load_settings()
    masked = {**data}
    # Never expose full API keys — only show whether they're configured
    masked.pop("api_key", None)
    masked.pop("anthropic_api_key", None)
    masked["api_key_configured"] = bool(_get_api_key())
    masked["anthropic_api_key_configured"] = bool(_get_anthropic_api_key())
    return masked


@router.put("/settings")
def update_settings(settings: dict, user: dict = Depends(get_current_user)):
    current = _load_settings()
    settings.pop("api_key", None)  # API key managed via env var
    settings.pop("anthropic_api_key", None)  # Anthropic key managed via env var
    current.update(settings)
    _save_settings(current)
    return {"success": True}


@router.post("/settings/apply")
def apply_settings(user: dict = Depends(get_current_user)):
    settings = _load_settings()
    model = settings.get("model_name", "")

    # Claude 모델 선택 시 Anthropic key 검증
    if model.startswith("claude-"):
        anthropic_key = _get_anthropic_api_key()
        if not anthropic_key:
            return {"success": False, "error": "Anthropic API Key가 설정되지 않았습니다. (.env 파일의 ANTHROPIC_API_KEY 확인)"}
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            # 간단한 검증 호출
            client.messages.create(
                model=model, max_tokens=10,
                messages=[{"role": "user", "content": "hi"}],
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Anthropic API 검증 실패: {str(e)}"}

    # Gemini 모델
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "API Key가 설정되지 않았습니다. (GEMINI_API_KEY 환경변수 확인)"}
    try:
        import core_logic
        core_logic.get_client(api_key)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========================================
# Projects
# ========================================

@router.get("/projects")
def list_projects(user: dict = Depends(get_current_user)):
    import core_rag
    return core_rag.list_projects()


@router.post("/projects")
def create_project(req: ProjectCreate, user: dict = Depends(get_current_user)):
    import core_rag
    return core_rag.create_project(req.name)


@router.delete("/projects/{name}")
def delete_project(name: str, user: dict = Depends(get_current_user)):
    import core_rag
    return core_rag.delete_project(name)


# ========================================
# Documents & Folders
# ========================================

@router.get("/projects/{name}/docs")
def get_project_docs(name: str, user: dict = Depends(get_current_user)):
    import core_rag
    tree = core_rag.get_folder_tree(name)
    doc_names = core_rag.get_indexed_doc_names(name) or []
    return {"folder_tree": tree, "doc_names": doc_names, "count": len(doc_names)}


@router.post("/projects/{name}/folders")
def create_folder(name: str, req: FolderCreate, user: dict = Depends(get_current_user)):
    import core_rag
    return core_rag.create_folder(name, req.name)


@router.delete("/projects/{name}/folders/{folder}")
def delete_folder(name: str, folder: str, user: dict = Depends(get_current_user)):
    import core_rag
    return core_rag.delete_folder(name, folder)


@router.post("/projects/{name}/docs/{doc}/move")
def move_doc(name: str, doc: str, req: DocMoveRequest, user: dict = Depends(get_current_user)):
    import core_rag
    return core_rag.move_doc_to_folder(name, doc, req.target_folder)


@router.delete("/projects/{name}/docs/{doc}")
def trash_doc(name: str, doc: str, user: dict = Depends(get_current_user)):
    import core_rag
    return core_rag.trash_document(name, doc)


@router.post("/projects/{name}/upload")
async def upload_files(name: str, files: List[UploadFile] = File(...), user: dict = Depends(get_current_user)):
    import core_rag
    api_key = _get_api_key()
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
def start_generate(req: GenerateRequest, user: dict = Depends(get_current_user)):
    api_key = _get_api_key()
    model = _load_settings().get("model_name", "gemini-3.1-pro-preview")

    user_context = req.file_context.strip()
    selected_docs = req.inputs.get("selected_docs", [])
    print(f"[generate] project={req.project_name}, template={req.template_option}, "
          f"user_context_len={len(user_context)}, selected_docs={selected_docs}")

    file_context = ""
    if req.project_name:
        file_context = _load_context_with_budget(
            req.project_name, selected_docs if selected_docs else None
        )
        print(f"[generate] loaded docs: {len(file_context)} chars")

    inputs = dict(req.inputs)
    inputs.setdefault("template_option", req.template_option)
    inputs["context_text"] = user_context

    task_id = create_task()
    run_generate_task(
        task_id, api_key, model,
        inputs, req.thinking_level, file_context,
        mode=req.mode
    )
    log_usage(user["id"], "/generate", model)
    return {"task_id": task_id}


@router.post("/qa")
def start_qa(req: QaRequest, user: dict = Depends(get_current_user)):
    api_key = _get_api_key()
    model = _load_settings().get("model_name", "gemini-3.1-pro-preview")

    context = _get_vector_context(
        api_key, req.project_name, req.question, req.selected_docs
    )
    task_id = create_task()
    run_analysis_task(
        task_id, "qa_answer", api_key, model,
        file_context=context, question=req.question
    )
    log_usage(user["id"], "/qa", model)
    return {"task_id": task_id}


@router.post("/analyze")
def start_analysis(req: AnalysisRequest, user: dict = Depends(get_current_user)):
    api_key = _get_api_key()
    model = _load_settings().get("model_name", "gemini-3.1-pro-preview")

    kwargs = dict(req.kwargs)
    if "project_name" in kwargs:
        pname = kwargs.pop("project_name")
        sel_docs = kwargs.pop("selected_docs", [])
        query = kwargs.get("question", req.task_type)
        kwargs["file_context"] = _get_vector_context(
            api_key, pname, query, sel_docs
        )

    task_id = create_task()
    run_analysis_task(task_id, req.task_type, api_key, model, **kwargs)
    log_usage(user["id"], f"/analyze/{req.task_type}", model)
    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, user: dict = Depends(get_current_user)):
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
def reindex_project(name: str, force: bool = False, user: dict = Depends(get_current_user)):
    """프로젝트 문서를 벡터 DB에 증분 인덱싱 (서브프로세스에서 실행, segfault 격리).

    force=True면 전체 재인덱싱, 기본은 변경분만 처리.
    """
    import subprocess, sys, json as _json
    api_key = _get_api_key()
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
def vector_stats(name: str, user: dict = Depends(get_current_user)):
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
def doc_sync_status(name: str, user: dict = Depends(get_current_user)):
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
def sync_selected_docs(name: str, req: SyncDocsRequest, user: dict = Depends(get_current_user)):
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
# OCR
# ========================================

@router.post("/ocr")
async def ocr_files(files: List[UploadFile] = File(...), engine: str = "gemini", user: dict = Depends(get_current_user)):
    """이미지/PDF에서 텍스트 추출 (Gemini Vision 또는 Document AI)."""
    import fitz
    api_key = _get_api_key()
    log_usage(user["id"], "/ocr")
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
async def freedoc_upload(files: List[UploadFile] = File(...), user: dict = Depends(get_current_user)):
    """자유양식 문서작성: 파일 업로드 → 파싱된 텍스트 반환."""
    api_key = _get_api_key()
    parsed_parts = []
    for f in files:
        content_bytes = await f.read()
        parsed = _parse_file_bytes(f.filename, content_bytes, api_key)
        if parsed:
            parsed_parts.append(f"--- [{f.filename}] ---\n{parsed}")
    return {"file_text": "\n\n".join(parsed_parts), "count": len(parsed_parts)}


@router.post("/freedoc/generate")
def freedoc_generate(req: FreeDocRequest, user: dict = Depends(get_current_user)):
    """자유양식 문서작성: 파싱된 텍스트 + 지시사항 → AI 문서 생성 (task)."""
    api_key = _get_api_key()
    model = _load_settings().get("model_name", "gemini-3.1-pro-preview")
    log_usage(user["id"], "/freedoc/generate", model)

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
            from google.genai import types
            from ai_client import AIClient
            client = AIClient(api_key=api_key)

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
def markdown_to_docx(req: MarkdownToDocxRequest, user: dict = Depends(get_current_user)):
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
async def doc_updater_upload_original(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
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
    session_id: str, files: List[UploadFile] = File(...), user: dict = Depends(get_current_user)
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
def doc_updater_run(req: DocUpdaterRunRequest, user: dict = Depends(get_current_user)):
    """문서 업데이트 실행 (백그라운드)."""
    temp_dir = _doc_updater_sessions.get(req.session_id)
    if not temp_dir:
        return {"error": "세션이 없습니다."}

    api_key = _get_api_key()
    model = _load_settings().get("model_name", "gemini-3.1-pro-preview")
    log_usage(user["id"], "/doc-updater/run", model)

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
def doc_updater_download(path: str, user: dict = Depends(get_current_user)):
    """업데이트된 문서 다운로드."""
    from fastapi.responses import FileResponse
    if not os.path.exists(path):
        return {"error": "파일을 찾을 수 없습니다."}
    return FileResponse(
        path,
        filename=os.path.basename(path),
        media_type="application/octet-stream",
    )


# ──────────────────────────────────────────
# NPS (국민연금 가입 사업장 조회)
# ──────────────────────────────────────────

import sys as _sys
_nps_path = os.path.join(os.path.expanduser("~"), "nps_query")
if _nps_path not in _sys.path:
    _sys.path.insert(0, _nps_path)

try:
    from nps_query import NpsQuery, ENDPOINTS as NPS_ENDPOINTS
    _NPS_KEY = "SEtf7JkRv42rZno75HZqEZwMESrUT5LGXWyqJulYgDT3soMupX4WBEf3FayvqhHJqHKz0KO36R63obsB6xlHqg=="
    _nps = NpsQuery(_NPS_KEY)
    _NPS_AVAILABLE = True
except ImportError:
    _NPS_AVAILABLE = False
    _nps = None

# 캐시
import time as _time
from threading import Lock as _Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

_nps_cache: dict = {}
_nps_cache_lock = _Lock()
_NPS_CACHE_TTL = 300


def _nps_cache_get(key: str):
    with _nps_cache_lock:
        entry = _nps_cache.get(key)
        if entry and _time.time() - entry["t"] < _NPS_CACHE_TTL:
            return entry["v"]
        _nps_cache.pop(key, None)
        return None


def _nps_cache_set(key: str, value):
    with _nps_cache_lock:
        _nps_cache[key] = {"v": value, "t": _time.time()}
        if len(_nps_cache) > 500:
            oldest = min(_nps_cache, key=lambda k: _nps_cache[k]["t"])
            del _nps_cache[oldest]


def _nps_fetch_one(uddi: str, name, page: int, per_page: int):
    cache_key = f"{uddi}|{name}|{page}|{per_page}"
    cached = _nps_cache_get(cache_key)
    if cached is not None:
        return cached
    resp = _nps._call_api(uddi, name=name, page=page, per_page=per_page)
    _nps_cache_set(cache_key, resp)
    return resp


@router.get("/nps/periods")
def nps_periods(user: dict = Depends(get_current_user)):
    if not _NPS_AVAILABLE:
        return {"periods": [], "error": "NPS module not available"}
    return {"periods": NpsQuery.available_periods()}


@router.get("/nps/search")
def nps_search(name: str = "", year: int = None, month: int = None,
               page: int = 1, perPage: int = 50, user: dict = Depends(get_current_user)):
    if not _NPS_AVAILABLE:
        return {"error": "NPS module not available", "data": [], "total": 0}
    if not name and year is None:
        return {"error": "사업장명 또는 연도를 입력하세요", "data": [], "total": 0}

    endpoints = _nps._get_endpoints(year, month)
    if not endpoints:
        return {"data": [], "total": 0, "page": page, "perPage": perPage}

    name_param = name if name else None

    if len(endpoints) == 1:
        ym, uddi = endpoints[0]
        try:
            resp = _nps_fetch_one(uddi, name_param, page, perPage)
            return {
                "data": resp.get("data", []),
                "total": resp.get("matchCount", 0),
                "page": page,
                "perPage": perPage,
            }
        except Exception as e:
            return {"error": str(e), "data": [], "total": 0}
    else:
        all_data = []
        total = 0
        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = {
                pool.submit(_nps_fetch_one, uddi, name_param, 1, perPage): ym
                for ym, uddi in endpoints
            }
            for fut in as_completed(futures):
                try:
                    resp = fut.result()
                    all_data.extend(resp.get("data", []))
                    total += resp.get("matchCount", 0)
                except:
                    pass
        all_data.sort(key=lambda r: r.get("자료생성년월", ""))
        return {
            "data": all_data,
            "total": total,
            "page": 1,
            "perPage": len(all_data),
        }


# ──────────────────────────────────────────
# QuickMail (AI 이메일 작성)
# ──────────────────────────────────────────

class QuickMailRequest(BaseModel):
    prompt: str
    context: str = ""
    tone: str = "professional"
    language: str = "한국어"

_TONE_MAP = {
    "formal": "격식체 (합쇼체)",
    "casual": "비격식 (해요체)",
    "professional": "비즈니스 (합니다체)",
}

@router.post("/quickmail/generate")
def quickmail_generate(req: QuickMailRequest, user: dict = Depends(get_current_user)):
    """AI 이메일 생성 (task 기반 스트리밍)."""
    api_key = _get_api_key()
    if not api_key:
        return {"error": "API key not configured"}
    model = _get_model_name()
    is_reply = bool(req.context.strip())
    tone_label = _TONE_MAP.get(req.tone, "비즈니스 (합니다체)")

    system_prompt = (
        "당신은 비즈니스 이메일 작성 전문가입니다.\n"
        f"{'주어진 원본 메일에 대한 답장을 작성하세요.' if is_reply else '사용자의 요청에 맞는 이메일 본문을 작성하세요.'}\n\n"
        "[필수 규칙 - 반드시 지킬 것]\n"
        f"- {tone_label} 어조로 {req.language}(으)로 작성\n"
        "- 제목(Subject)은 포함하지 말 것 (별도 요청 시에만 포함)\n"
        "- 절대로 마크다운 서식(**, *, #, - 등)을 사용하지 말 것. 순수 텍스트만 사용\n"
        "- 절대로 [이름], [회의 장소], [Your Name], [안건] 등 대괄호 플레이스홀더를 사용하지 말 것\n"
        "- 구체적 정보가 없으면 일반적이고 자연스러운 표현으로 대체하여 바로 보낼 수 있게 작성\n"
        "- 불릿 포인트 대신 자연스러운 문장으로 서술\n"
        f"{'- 답장 본문만 작성하고 원본 인용은 포함하지 말 것' if is_reply else ''}\n\n"
        "[톤 & 매너 - 공손하고 정중하게]\n"
        "- 바쁜 상대방에 대한 배려를 반드시 표현하세요\n"
        "  예: '바쁘신 와중에 죄송합니다만', '업무에 바쁘신 줄 알지만'\n"
        "- 협조/참석/회신에 대한 감사를 자연스럽게 포함하세요\n"
        "  예: '바쁘신 가운데 참석해 주셔서 감사합니다', '협조해 주셔서 대단히 감사드립니다'\n"
        "- 부탁이나 요청 시 공손한 완곡 표현을 사용하세요\n"
        "  예: '번거로우시겠지만', '혹시 가능하시다면', '양해 부탁드립니다'\n"
        "- 마무리에 안부 인사를 포함하세요\n"
        "  예: '좋은 하루 보내시기 바랍니다', '항상 건강하시길 바랍니다'\n"
        "- 전체적으로 따뜻하고 정중한 느낌을 유지하되, 과도하게 장황하지 않게 작성하세요\n"
    )

    user_message = (
        f"원본 메일:\n---\n{req.context}\n---\n\n요청: {req.prompt}"
        if is_reply else req.prompt
    )

    task_id = create_task()
    task = get_task(task_id)
    task["status"] = "generating"

    def _run():
        try:
            from ai_client import AIClient
            from google.genai import types
            client = AIClient(api_key=api_key)
            config = types.GenerateContentConfig(
                max_output_tokens=2048,
                temperature=0.7,
                system_instruction=system_prompt,
            )
            stream = client.models.generate_content_stream(
                model=model, contents=user_message, config=config,
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
    log_usage(user.get("user_id", 0), "quickmail", model)
    return {"task_id": task_id}


# ──────────────────────────────────────────
# DartWings (DART 전자공시 기업분석)
# ──────────────────────────────────────────

try:
    import importlib.util as _ilu
    import types as _types
    _dw_base = os.path.join(os.path.expanduser("~"), "dartwings", "backend")

    def _dw_import(name, filepath, extra_globals=None):
        spec = _ilu.spec_from_file_location(name, filepath)
        mod = _ilu.module_from_spec(spec)
        if extra_globals:
            for k, v in extra_globals.items():
                setattr(mod, k, v)
        spec.loader.exec_module(mod)
        return mod

    # Load config first
    _dw_config = _dw_import("dw_config", os.path.join(_dw_base, "config.py"))
    # Temporarily register fake 'backend.config' so dart_service can import it
    _fake_pkg = _types.ModuleType("backend")
    _fake_pkg.config = _dw_config
    _saved_backend = _sys.modules.get("backend")
    _sys.modules["backend"] = _fake_pkg
    _sys.modules["backend.config"] = _dw_config
    try:
        _dw_dart = _dw_import("dw_dart_service", os.path.join(_dw_base, "services", "dart_service.py"))
    finally:
        # Restore real backend module
        if _saved_backend:
            _sys.modules["backend"] = _saved_backend
        else:
            _sys.modules.pop("backend", None)
        _sys.modules.pop("backend.config", None)
    _dw_stock = _dw_import("dw_stock_service", os.path.join(_dw_base, "services", "stock_service.py"))
    _dw_analysis = _dw_import("dw_analysis_service", os.path.join(_dw_base, "services", "analysis_service.py"))
    _DW_AVAILABLE = True
except Exception as _e:
    print(f"[DartWings] Failed to load: {_e}")
    _DW_AVAILABLE = False

from fastapi import Query as _Query
from datetime import datetime as _dt, timedelta as _td
from collections import Counter as _Counter


@router.get("/dartwings/search")
def dw_search(q: str = _Query(..., min_length=1), limit: int = _Query(20, le=50),
              user: dict = Depends(get_current_user)):
    if not _DW_AVAILABLE:
        return {"error": "DartWings module not available"}
    return _dw_dart.search_corps(q, limit=limit)


@router.get("/dartwings/popular")
def dw_popular(user: dict = Depends(get_current_user)):
    return [
        {"corpName": "삼성전자", "stockCode": "005930"},
        {"corpName": "SK하이닉스", "stockCode": "000660"},
        {"corpName": "현대차", "stockCode": "005380"},
        {"corpName": "NAVER", "stockCode": "035420"},
        {"corpName": "카카오", "stockCode": "035720"},
    ]


@router.get("/dartwings/analyze")
def dw_analyze(stockCode: str = _Query(...), user: dict = Depends(get_current_user)):
    if not _DW_AVAILABLE:
        return {"error": "DartWings module not available"}
    from fastapi import HTTPException
    corp_code = _dw_dart.stock_code_to_corp_code(stockCode)
    if not corp_code:
        raise HTTPException(404, "종목코드를 찾을 수 없습니다")

    company = _dw_dart.get_company_info(corp_code)
    current_year = _dt.today().year
    month = _dt.today().month
    start_offset = 2 if month <= 3 else 1
    years = [str(current_year - i) for i in range(start_offset, start_offset + 3)]

    financials_by_year = []
    for yr in years:
        fs = _dw_dart.get_financial_statements(corp_code, yr)
        extracted = _dw_analysis.extract_key_financials(fs)
        extracted["year"] = yr
        financials_by_year.append(extracted)
    financials_by_year.reverse()

    financials = {
        "years": [f["year"] for f in financials_by_year],
        "revenue": [f.get("revenue", 0) for f in financials_by_year],
        "operatingProfit": [f.get("operatingProfit", 0) for f in financials_by_year],
        "netIncome": [f.get("netIncome", 0) for f in financials_by_year],
        "totalAssets": [f.get("totalAssets", 0) for f in financials_by_year],
        "totalEquity": [f.get("totalEquity", 0) for f in financials_by_year],
        "totalDebt": [f.get("totalDebt", 0) for f in financials_by_year],
    }

    price = _dw_stock.get_current_price(stockCode)
    price_history = _dw_stock.get_price_history(stockCode)
    market_cap = _dw_stock.get_market_cap(stockCode)

    dividend_list = _dw_dart.get_dividend_info(corp_code, years[0])
    dps = 0
    for item in dividend_list:
        se = item.get("se", "")
        if "주당" in se and "현금" in se:
            dps = _dw_analysis.parse_amount(item.get("thstrm", "0"))
            break
    dividend_yield = round(dps / price["current"] * 100, 2) if price["current"] else 0

    return {
        "company": company,
        "financials": financials,
        "stockPrice": {
            "current": price["current"],
            "change": price["change"],
            "volume": price["volume"],
            "marketCap": market_cap,
        },
        "dividend": {"dps": dps, "dividendYield": dividend_yield},
        "priceHistory": price_history,
    }


@router.get("/dartwings/disclosure-chart")
def dw_disclosure_chart(stockCode: str = _Query(...), user: dict = Depends(get_current_user)):
    if not _DW_AVAILABLE:
        return {"error": "DartWings module not available"}
    from fastapi import HTTPException
    corp_code = _dw_dart.stock_code_to_corp_code(stockCode)
    if not corp_code:
        raise HTTPException(404, "종목코드를 찾을 수 없습니다")

    end = _dt.today().strftime("%Y%m%d")
    bgn = (_dt.today() - _td(days=365 * 3)).strftime("%Y%m%d")
    disclosures = _dw_dart.get_disclosures(corp_code, bgn, end)

    monthly_counter: _Counter = _Counter()
    type_counter: _Counter = _Counter()
    recent = []

    for d in disclosures:
        date_str = d.get("rcept_dt", "")
        report_nm = d.get("report_nm", "")
        if len(date_str) == 8:
            monthly_counter[f"{date_str[:4]}-{date_str[4:6]}"] += 1
        if any(k in report_nm for k in ("사업보고서", "분기보고서", "반기보고서")):
            dtype = "정기보고서"
        elif "주요사항" in report_nm:
            dtype = "주요사항보고"
        elif any(k in report_nm for k in ("임원", "주식등", "지분")):
            dtype = "지분공시"
        else:
            dtype = "기타공시"
        type_counter[dtype] += 1
        if len(recent) < 20:
            recent.append({
                "date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str,
                "title": report_nm, "type": dtype,
                "link": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={d.get('rcept_no', '')}",
            })

    sorted_months = sorted(monthly_counter.keys())
    return {
        "monthly": {"labels": sorted_months, "counts": [monthly_counter[m] for m in sorted_months]},
        "byType": {"labels": list(type_counter.keys()), "counts": list(type_counter.values())},
        "recentDisclosures": recent,
    }


@router.get("/dartwings/valuation-models")
def dw_valuation_models(stockCode: str = _Query(...), user: dict = Depends(get_current_user)):
    if not _DW_AVAILABLE:
        return {"error": "DartWings module not available"}
    from fastapi import HTTPException
    corp_code = _dw_dart.stock_code_to_corp_code(stockCode)
    if not corp_code:
        raise HTTPException(404, "종목코드를 찾을 수 없습니다")

    current_year = _dt.today().year
    month = _dt.today().month
    start_offset = 2 if month <= 3 else 1
    years = [str(current_year - i) for i in range(start_offset, start_offset + 3)]

    financials_by_year = []
    for yr in years:
        fs = _dw_dart.get_financial_statements(corp_code, yr)
        extracted = _dw_analysis.extract_key_financials(fs)
        extracted["year"] = yr
        financials_by_year.append(extracted)
    financials_by_year.reverse()

    latest = financials_by_year[-1] if financials_by_year else {}
    fundamentals = _dw_stock.get_fundamentals(stockCode)
    market_cap = _dw_stock.get_market_cap(stockCode)
    price = _dw_stock.get_current_price(stockCode)

    multiples = _dw_analysis.calc_valuation_multiples(latest, market_cap)
    multiples["per"] = fundamentals["per"]
    multiples["pbr"] = fundamentals["pbr"]

    multiples_history = {"years": [f["year"] for f in financials_by_year], "roe": []}
    for f in financials_by_year:
        ni, eq = f.get("netIncome", 0), f.get("totalEquity", 0)
        multiples_history["roe"].append(round(ni / eq * 100, 2) if eq else 0)

    shares = int(market_cap / price["current"]) if price["current"] else 0
    dcf = _dw_analysis.calc_dcf(financials_by_year, market_cap, shares)
    dcf["currentPrice"] = price["current"]
    if dcf["fairValue"] and price["current"]:
        dcf["upside"] = round((dcf["fairValue"] - price["current"]) / price["current"] * 100, 1)

    srim = _dw_analysis.calc_srim(fundamentals["bps"], multiples["roe"])
    srim["currentPrice"] = price["current"]
    if srim["fairValue"] and price["current"]:
        srim["upside"] = round((srim["fairValue"] - price["current"]) / price["current"] * 100, 1)

    avg_upside, count = 0, 0
    if dcf.get("fairValue"):
        avg_upside += dcf.get("upside", 0); count += 1
    if srim.get("fairValue"):
        avg_upside += srim.get("upside", 0); count += 1
    avg_upside = avg_upside / count if count else 0
    grade = "저평가" if avg_upside > 15 else ("고평가" if avg_upside < -15 else "적정")

    return {"multiples": multiples, "multiplesHistory": multiples_history, "dcf": dcf, "srim": srim, "grade": grade}

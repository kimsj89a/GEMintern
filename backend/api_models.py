"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel
from typing import Optional, Dict, List, Any


class ProjectCreate(BaseModel):
    name: str


class ProjectRename(BaseModel):
    new_name: str


class FolderCreate(BaseModel):
    name: str


class DocMoveRequest(BaseModel):
    target_folder: str


class GenerateRequest(BaseModel):
    project_name: str
    template_option: str = "free_summary"
    thinking_level: str = "MEDIUM"
    file_context: str = ""
    inputs: Dict[str, Any] = {}
    mode: str = "single"


class QaRequest(BaseModel):
    project_name: str = ""
    question: str
    selected_docs: List[str] = []
    file_context: str = ""


class SyncRequest(BaseModel):
    project_name: str = ""


class AnalysisRequest(BaseModel):
    task_type: str
    project_name: str = ""
    file_context: str = ""
    kwargs: Dict[str, Any] = {}


class CreatePptxRequest(BaseModel):
    slide_json: Any  # JSON string or dict
    template_path: Optional[str] = None  # optional .pptx template file path


class SlideRegenerateRequest(BaseModel):
    current_slide: Any
    prev_slide: Any = None
    next_slide: Any = None
    instruction: str


class SlidesFromOutlineRequest(BaseModel):
    outline: Any  # edited outline JSON
    project_name: str = ""
    selected_docs: Optional[List[str]] = None
    context_text: str = ""


class SaveResearchRequest(BaseModel):
    project_name: str
    doc_name: str
    content: str


class FolderScanRequest(BaseModel):
    folder_path: str
    recursive: bool = True
    file_extensions: list[str] = []


class FolderScanFileInfo(BaseModel):
    path: str
    name: str
    size: int
    ext: str
    relative_path: str


class FolderScanPreviewResponse(BaseModel):
    files: list[FolderScanFileInfo]
    total_size: int
    file_count: int


class FolderIngestRequest(BaseModel):
    folder_path: str
    selected_files: list[str]
    preserve_structure: bool = True

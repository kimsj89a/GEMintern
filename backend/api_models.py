"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel
from typing import Optional, Dict, List, Any


class ProjectCreate(BaseModel):
    name: str


class ProjectRename(BaseModel):
    new_name: str


class FolderCreate(BaseModel):
    name: str


class FolderRename(BaseModel):
    old_name: str
    new_name: str  # leaf name only (parent path is preserved by backend)


class DocMoveRequest(BaseModel):
    target_folder: str


class NoteCreate(BaseModel):
    title: str
    content: str = ""
    tags: list[str] = []


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None


class PptPlanRequest(BaseModel):
    project_name: str = ""
    selected_docs: list[str] = []
    user_goal: str = ""
    prior_plan: Optional[Dict[str, Any]] = None
    user_feedback: str = ""
    mode: str = "im"  # 'teaser' | 'im'
    target_pages: int = 30


class QuickCaptureRequest(BaseModel):
    content: str = ""


class PromoteInboxRequest(BaseModel):
    title: Optional[str] = None
    tags: Optional[list[str]] = None


class NoteTemplateUpsert(BaseModel):
    name: str
    body: str


class NoteFromTemplateRequest(BaseModel):
    template_name: str
    title: Optional[str] = None  # 사용자가 입력. 없으면 template name 사용


class TimelineEventCreate(BaseModel):
    title: str
    content: str = ""
    event_date: str  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    color: str = "#6366f1"


class TimelineEventUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    event_date: Optional[str] = None
    end_date: Optional[str] = None
    color: Optional[str] = None


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
    use_mckinsey: bool = False  # True → vendored mckinsey-pptx PresentationBuilder


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


# ── Wiki ──

class WikiSectionUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None


class WikiSectionCreate(BaseModel):
    id: str
    title: str
    content: str = ""


# ── Deal Structure ──

class DealStructureNode(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    data: Dict
    width: Optional[float] = None
    height: Optional[float] = None
    parentId: Optional[str] = None
    style: Optional[Dict] = None


class DealStructureEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None
    label: Optional[str] = None
    type: Optional[str] = None
    animated: Optional[bool] = False
    style: Optional[Dict] = None
    data: Optional[Dict] = None


class DealStructurePayload(BaseModel):
    nodes: List[DealStructureNode] = []
    edges: List[DealStructureEdge] = []
    viewport: Optional[Dict] = None
    version: int = 1

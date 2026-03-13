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

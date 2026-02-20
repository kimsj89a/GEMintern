# PyWebView Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert GEMintern from PyQt6 to React + FastAPI + pywebview, supporting both desktop and browser modes.

**Architecture:** FastAPI serves REST + WebSocket APIs backed by existing Python modules. React frontend (Vite + Tailwind) renders all UI. pywebview wraps the app in a native window; `--web` flag opens in browser instead.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS, Zustand, FastAPI, uvicorn, pywebview, Pydantic

---

## Phase 1: Scaffolding

### Task 1: Initialize Frontend (Vite + React + TypeScript + Tailwind)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`

**Step 1: Scaffold Vite React-TS project**

```bash
cd C:/Users/kimsj/GEMintern/GEMintern
npm create vite@latest frontend -- --template react-ts
```

**Step 2: Install Tailwind CSS and dependencies**

```bash
cd frontend
npm install -D tailwindcss @tailwindcss/vite
npm install zustand react-markdown react-router-dom
npm install -D @types/react @types/react-dom
```

**Step 3: Configure Tailwind in `frontend/src/index.css`**

```css
@import "tailwindcss";
```

**Step 4: Configure Vite proxy for API (`frontend/vite.config.ts`)**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8741',
      '/ws': { target: 'ws://localhost:8741', ws: true },
    },
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
})
```

**Step 5: Create minimal App.tsx**

```tsx
// frontend/src/App.tsx
export default function App() {
  return (
    <div className="flex h-screen bg-white">
      <aside className="w-64 bg-[#F7F6F3] border-r border-[#E9E9E7]">
        <h1 className="text-lg font-bold p-5 text-[#37352F]">GEM Intern v7.0</h1>
      </aside>
      <main className="flex-1 p-8">
        <p className="text-[#787774]">React frontend loaded.</p>
      </main>
    </div>
  )
}
```

**Step 6: Verify frontend starts**

```bash
cd frontend && npm run dev
```
Expected: Browser opens at localhost:5173 showing sidebar + main area.

**Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React + Vite + Tailwind frontend"
```

---

### Task 2: Initialize FastAPI Backend

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/main.py`
- Create: `backend/api_routes.py`
- Create: `backend/api_models.py`

**Step 1: Install Python dependencies**

```bash
pip install fastapi uvicorn[standard] python-multipart websockets pydantic
```

**Step 2: Create FastAPI app (`backend/main.py`)**

```python
"""
GEMintern Web Backend - FastAPI + pywebview dual mode.
"""
import sys
import os
import argparse
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add parent dir to path so core_*.py modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api_routes import router as api_router

app = FastAPI(title="GEMintern API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Serve built frontend (production)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


PORT = 8741


def start_server():
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web", action="store_true", help="Open in browser instead of pywebview")
    parser.add_argument("--dev", action="store_true", help="API-only mode for frontend dev")
    args = parser.parse_args()

    if args.dev:
        # Dev mode: just run API server, frontend uses Vite dev server
        uvicorn.run(app, host="127.0.0.1", port=PORT, reload=False)
    elif args.web:
        # Web mode: start server + open browser
        import webbrowser
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        webbrowser.open(f"http://localhost:{PORT}")
        input("Press Enter to stop server...")
    else:
        # Desktop mode: pywebview
        try:
            import webview
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            webview.create_window(
                "GEM Intern v7.0",
                f"http://localhost:{PORT}",
                width=1400, height=900,
                min_size=(1000, 700),
            )
            webview.start()
        except ImportError:
            print("pywebview not installed. Install with: pip install pywebview")
            print("Falling back to browser mode...")
            import webbrowser
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            webbrowser.open(f"http://localhost:{PORT}")
            input("Press Enter to stop server...")


if __name__ == "__main__":
    main()
```

**Step 3: Create initial API routes (`backend/api_routes.py`)**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "version": "7.0"}
```

**Step 4: Create empty models file (`backend/api_models.py`)**

```python
"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel
from typing import Optional, Dict, List, Any


class SettingsResponse(BaseModel):
    api_key: str = ""
    model_name: str = "gemini-3.1-pro-preview"
    thinking_level: str = "MEDIUM"
    cloud_sync: Dict[str, Any] = {}


class ProjectCreate(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    name: str
    doc_count: int = 0
    created: str = ""


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


class QaRequest(BaseModel):
    project_name: str
    question: str
    selected_docs: List[str] = []


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
```

**Step 5: Create `backend/__init__.py`**

```python
```

**Step 6: Install pywebview**

```bash
pip install pywebview
```

**Step 7: Verify backend starts**

```bash
cd C:/Users/kimsj/GEMintern/GEMintern
python -m backend.main --dev
```
Expected: FastAPI running on port 8741. `curl http://localhost:8741/api/health` returns `{"status":"ok","version":"7.0"}`

**Step 8: Commit**

```bash
git add backend/ requirements_pyqt.txt
git commit -m "feat: scaffold FastAPI backend with dual-mode launcher"
```

---

## Phase 2: Core Infrastructure

### Task 3: Settings API

**Files:**
- Modify: `backend/api_routes.py`
- Reference: `settings.json` (existing)

**Step 1: Add settings endpoints to `backend/api_routes.py`**

```python
import json, os

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


@router.get("/settings")
def get_settings():
    data = _load_settings()
    # Mask API key for security
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
    # Validate API key
    if not data.get("api_key"):
        return {"success": False, "error": "API Key가 설정되지 않았습니다."}
    try:
        import core_logic
        client = core_logic.get_client(data["api_key"])
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Step 2: Commit**

```bash
git add backend/api_routes.py
git commit -m "feat: add settings REST API endpoints"
```

---

### Task 4: Projects API

**Files:**
- Modify: `backend/api_routes.py`

**Step 1: Add project endpoints**

```python
import core_rag


@router.get("/projects")
def list_projects():
    return core_rag.list_projects()


@router.post("/projects")
def create_project(req: ProjectCreate):
    from backend.api_models import ProjectCreate
    return core_rag.create_project(req.name)


@router.delete("/projects/{name}")
def delete_project(name: str):
    return core_rag.delete_project(name)


@router.get("/projects/{name}/docs")
def get_project_docs(name: str):
    tree = core_rag.get_folder_tree(name)
    doc_names = core_rag.get_indexed_doc_names(name)
    return {"folder_tree": tree, "doc_names": doc_names, "count": len(doc_names)}


@router.post("/projects/{name}/folders")
def create_folder(name: str, req: FolderCreate):
    from backend.api_models import FolderCreate
    return core_rag.create_folder(name, req.name)


@router.delete("/projects/{name}/folders/{folder}")
def delete_folder(name: str, folder: str):
    return core_rag.delete_folder(name, folder)


@router.post("/projects/{name}/docs/{doc}/move")
def move_doc(name: str, doc: str, req: DocMoveRequest):
    from backend.api_models import DocMoveRequest
    return core_rag.move_doc_to_folder(name, doc, req.target_folder)


@router.delete("/projects/{name}/docs/{doc}")
def trash_doc(name: str, doc: str):
    return core_rag.trash_document(name, doc)


@router.post("/projects/{name}/upload")
async def upload_files(name: str, files: list[UploadFile]):
    from fastapi import UploadFile
    texts = {}
    for f in files:
        content = await f.read()
        texts[f.filename] = content.decode("utf-8", errors="replace")
    result = core_rag.index_texts("", texts, name)
    return result
```

**Step 2: Commit**

```bash
git add backend/api_routes.py
git commit -m "feat: add projects & documents REST API"
```

---

### Task 5: AI Generation API + WebSocket

**Files:**
- Create: `backend/api_ws.py`
- Modify: `backend/main.py`
- Modify: `backend/api_routes.py`

**Step 1: Create WebSocket handler (`backend/api_ws.py`)**

```python
"""WebSocket handler for streaming AI generation."""
import asyncio
import uuid
import threading
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict

# Active tasks: task_id -> { "status": ..., "chunks": [...], "result": ..., "error": ... }
_tasks: Dict[str, dict] = {}


def get_task(task_id: str) -> dict:
    return _tasks.get(task_id, {})


def create_task() -> str:
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {"status": "pending", "chunks": [], "result": None, "error": None}
    return task_id


def run_generate_task(task_id: str, api_key: str, model_name: str,
                      inputs: dict, thinking_level: str, file_context: str,
                      mode: str = "single"):
    """Run AI generation in a background thread, storing chunks."""
    import core_logic

    task = _tasks[task_id]
    task["status"] = "generating"

    def _run():
        try:
            if mode == "chained":
                stream = core_logic.generate_report_stream_chained(
                    api_key, model_name, inputs, thinking_level, file_context
                )
            else:
                stream = core_logic.generate_report_stream(
                    api_key, model_name, inputs, thinking_level, file_context
                )
            full_text = ""
            for chunk in stream:
                text = ""
                if hasattr(chunk, "text"):
                    text = chunk.text or ""
                elif isinstance(chunk, str):
                    text = chunk
                if text:
                    full_text += text
                    task["chunks"].append(text)
            task["result"] = full_text
            task["status"] = "complete"
        except Exception as e:
            task["error"] = str(e)
            task["status"] = "error"

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def run_analysis_task(task_id: str, task_type: str, api_key: str,
                      model_name: str, **kwargs):
    """Run analysis in background thread."""
    import core_logic

    task = _tasks[task_id]
    task["status"] = "generating"

    def _run():
        try:
            fn_map = {
                "material_summary": core_logic.generate_material_summary,
                "qa_answer": core_logic.generate_qa_answer,
                "followup_questions": core_logic.generate_followup_questions,
                "additional_questions": core_logic.generate_additional_questions,
                "followup_analysis": core_logic.generate_followup_analysis,
                "checklist_eval": core_logic.evaluate_checklist_item,
                "dd_issues": core_logic.analyze_dd_issues,
                "slide_json": core_logic.generate_slide_json,
                "refine": core_logic.refine_report_with_context,
            }
            fn = fn_map.get(task_type)
            if not fn:
                raise ValueError(f"Unknown task type: {task_type}")
            result = fn(api_key, model_name, **kwargs)
            task["result"] = result
            task["status"] = "complete"
        except Exception as e:
            task["error"] = str(e)
            task["status"] = "error"

    t = threading.Thread(target=_run, daemon=True)
    t.start()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming task results."""
    await websocket.accept()
    subscribed_tasks = set()

    try:
        while True:
            # Check for client messages (non-blocking with timeout)
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                msg_type = data.get("type")
                if msg_type == "subscribe":
                    subscribed_tasks.add(data["task_id"])
                elif msg_type == "unsubscribe":
                    subscribed_tasks.discard(data["task_id"])
            except asyncio.TimeoutError:
                pass

            # Push updates for subscribed tasks
            for task_id in list(subscribed_tasks):
                task = _tasks.get(task_id)
                if not task:
                    continue

                # Send any pending chunks
                while task["chunks"]:
                    chunk = task["chunks"].pop(0)
                    await websocket.send_json({
                        "type": "chunk", "task_id": task_id, "data": chunk
                    })

                # Send completion/error
                if task["status"] == "complete":
                    await websocket.send_json({
                        "type": "complete", "task_id": task_id,
                        "result": task["result"]
                    })
                    subscribed_tasks.discard(task_id)
                elif task["status"] == "error":
                    await websocket.send_json({
                        "type": "error", "task_id": task_id,
                        "error": task["error"]
                    })
                    subscribed_tasks.discard(task_id)

            await asyncio.sleep(0.05)

    except WebSocketDisconnect:
        pass
```

**Step 2: Register WebSocket in `backend/main.py`**

Add before the static mount:
```python
from backend.api_ws import websocket_endpoint

@app.websocket("/ws/stream")
async def ws_stream(websocket):
    await websocket_endpoint(websocket)
```

**Step 3: Add generation endpoints to `backend/api_routes.py`**

```python
from backend.api_ws import create_task, run_generate_task, run_analysis_task, get_task
from backend.api_models import GenerateRequest, QaRequest


@router.post("/generate")
def start_generate(req: GenerateRequest):
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    model = settings.get("model_name", req.inputs.get("model_name", "gemini-3.1-pro-preview"))
    task_id = create_task()
    run_generate_task(
        task_id, api_key, model,
        req.inputs, req.thinking_level, req.file_context,
        mode=req.inputs.get("mode", "single")
    )
    return {"task_id": task_id}


@router.post("/qa")
def start_qa(req: QaRequest):
    settings = _load_settings()
    api_key = settings.get("api_key", "")
    model = settings.get("model_name", "gemini-3.1-pro-preview")
    import core_rag
    context = core_rag.load_selected_project_docs(req.project_name, req.selected_docs)
    task_id = create_task()
    run_analysis_task(
        task_id, "qa_answer", api_key, model,
        file_context=context, question=req.question
    )
    return {"task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        return {"error": "Task not found"}
    return {"task_id": task_id, "status": task["status"],
            "result": task["result"], "error": task["error"]}
```

**Step 4: Commit**

```bash
git add backend/
git commit -m "feat: add AI generation API with WebSocket streaming"
```

---

### Task 6: Frontend API Client + WebSocket Hook

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/ws.ts`

**Step 1: Create REST API client (`frontend/src/api/client.ts`)**

```ts
const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  // Settings
  getSettings: () => request<any>('/settings'),
  updateSettings: (data: any) => request<any>('/settings', { method: 'PUT', body: JSON.stringify(data) }),
  applySettings: () => request<any>('/settings/apply', { method: 'POST' }),

  // Projects
  listProjects: () => request<any[]>('/projects'),
  createProject: (name: string) => request<any>('/projects', { method: 'POST', body: JSON.stringify({ name }) }),
  deleteProject: (name: string) => request<any>(`/projects/${name}`, { method: 'DELETE' }),

  // Documents
  getProjectDocs: (name: string) => request<any>(`/projects/${name}/docs`),
  createFolder: (project: string, folderName: string) =>
    request<any>(`/projects/${project}/folders`, { method: 'POST', body: JSON.stringify({ name: folderName }) }),
  deleteFolder: (project: string, folder: string) =>
    request<any>(`/projects/${project}/folders/${folder}`, { method: 'DELETE' }),
  moveDoc: (project: string, doc: string, targetFolder: string) =>
    request<any>(`/projects/${project}/docs/${doc}/move`, { method: 'POST', body: JSON.stringify({ target_folder: targetFolder }) }),
  trashDoc: (project: string, doc: string) =>
    request<any>(`/projects/${project}/docs/${doc}`, { method: 'DELETE' }),
  uploadFiles: async (project: string, files: File[]) => {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    const res = await fetch(`${BASE}/projects/${project}/upload`, { method: 'POST', body: formData });
    return res.json();
  },

  // AI
  startGenerate: (data: any) => request<{ task_id: string }>('/generate', { method: 'POST', body: JSON.stringify(data) }),
  startQa: (data: any) => request<{ task_id: string }>('/qa', { method: 'POST', body: JSON.stringify(data) }),
  getTaskStatus: (taskId: string) => request<any>(`/tasks/${taskId}`),

  // Sync
  syncPush: (project: string) => request<any>('/sync/push', { method: 'POST', body: JSON.stringify({ project_name: project }) }),
  syncPull: (project: string) => request<any>('/sync/pull', { method: 'POST', body: JSON.stringify({ project_name: project }) }),
};
```

**Step 2: Create WebSocket hook (`frontend/src/api/ws.ts`)**

```ts
type WsCallback = (msg: { type: string; task_id: string; data?: string; result?: string; error?: string }) => void;

let ws: WebSocket | null = null;
const listeners = new Map<string, WsCallback>();

function getWs(): WebSocket {
  if (ws && ws.readyState === WebSocket.OPEN) return ws;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/stream`);

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    const cb = listeners.get(msg.task_id);
    if (cb) cb(msg);
  };

  ws.onclose = () => { ws = null; };
  return ws;
}

export function subscribeTask(taskId: string, callback: WsCallback) {
  listeners.set(taskId, callback);
  const socket = getWs();
  const send = () => socket.send(JSON.stringify({ type: 'subscribe', task_id: taskId }));
  if (socket.readyState === WebSocket.OPEN) {
    send();
  } else {
    socket.addEventListener('open', send, { once: true });
  }
}

export function unsubscribeTask(taskId: string) {
  listeners.delete(taskId);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'unsubscribe', task_id: taskId }));
  }
}
```

**Step 3: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: add REST client and WebSocket streaming hook"
```

---

### Task 7: Zustand Stores

**Files:**
- Create: `frontend/src/stores/appStore.ts`

**Step 1: Create unified app store**

```ts
import { create } from 'zustand';

interface AppState {
  // App
  currentProject: string;
  setCurrentProject: (p: string) => void;
  activePage: string;
  setActivePage: (p: string) => void;
  openTabs: string[];
  openTab: (page: string) => void;
  closeTab: (page: string) => void;

  // Settings
  settings: Record<string, any>;
  setSettings: (s: Record<string, any>) => void;
  appStarted: boolean;
  setAppStarted: (v: boolean) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  currentProject: '',
  setCurrentProject: (p) => set({ currentProject: p }),
  activePage: 'home',
  setActivePage: (p) => {
    const { openTabs } = get();
    if (!openTabs.includes(p)) {
      set({ activePage: p, openTabs: [...openTabs, p] });
    } else {
      set({ activePage: p });
    }
  },
  openTabs: ['home'],
  openTab: (page) => {
    const { openTabs } = get();
    if (!openTabs.includes(page)) {
      set({ openTabs: [...openTabs, page], activePage: page });
    } else {
      set({ activePage: page });
    }
  },
  closeTab: (page) => {
    const { openTabs, activePage } = get();
    if (openTabs.length <= 1) return;
    const next = openTabs.filter(t => t !== page);
    set({
      openTabs: next,
      activePage: activePage === page ? next[next.length - 1] : activePage,
    });
  },

  settings: {},
  setSettings: (s) => set({ settings: s }),
  appStarted: false,
  setAppStarted: (v) => set({ appStarted: v }),
}));
```

**Step 2: Commit**

```bash
git add frontend/src/stores/
git commit -m "feat: add Zustand app store"
```

---

### Task 8: App Shell (Sidebar + TabContainer + Page Router)

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/components/TabContainer.tsx`
- Create: `frontend/src/pages/index.ts` (page registry)

**Step 1: Create Sidebar (`frontend/src/components/Sidebar.tsx`)**

Notion-style sidebar with:
- Title "GEM Intern v7.0"
- Project combo select
- Navigation sections (Main, Phase Workflow, Independent Tools, Utilities)
- Bottom: sync status, settings button
- Active page highlighted

**Step 2: Create TabContainer (`frontend/src/components/TabContainer.tsx`)**

Tab bar showing open tabs with close buttons. Active tab content rendered below.

**Step 3: Create page registry (`frontend/src/pages/index.ts`)**

```ts
import { lazy } from 'react';

export const PAGE_REGISTRY: Record<string, { label: string; component: React.LazyExoticComponent<any> }> = {
  home: { label: '🏠 홈', component: lazy(() => import('./HomePage')) },
  settings: { label: '⚙️ 설정', component: lazy(() => import('./SettingsPage')) },
  project: { label: '📂 프로젝트', component: lazy(() => import('./ProjectPage')) },
  phase1: { label: '📥 사전 정보 수집', component: lazy(() => import('./WorkflowPage')) },
  phase2: { label: '📝 투심보고서 작성', component: lazy(() => import('./WorkflowPage')) },
  im: { label: '📑 IM 작성', component: lazy(() => import('./WorkflowPage')) },
  ppt_tools: { label: '📢 발표자료', component: lazy(() => import('./PptToolsPage')) },
  lp_qa: { label: '🙋‍♂️ LP Q&A', component: lazy(() => import('./LpQaPage')) },
  qa_session: { label: '💬 자료기반 Q&A', component: lazy(() => import('./QaSessionPage')) },
  audio: { label: '🎤 오디오 전사', component: lazy(() => import('./AudioPage')) },
  crawler: { label: '🌐 웹 크롤러', component: lazy(() => import('./CrawlerPage')) },
  ocr: { label: '👁️ 문서 OCR', component: lazy(() => import('./OcrPage')) },
  markdown: { label: '📝 MD to Word', component: lazy(() => import('./MarkdownPage')) },
  doctemplate: { label: '📋 문서양식', component: lazy(() => import('./DocTemplatePage')) },
  text_organizer: { label: '✏️ 문장 정리기', component: lazy(() => import('./TextOrganizerPage')) },
};
```

**Step 4: Wire up App.tsx**

Compose: `<Sidebar />` + `<TabContainer />` with store-driven routing.

**Step 5: Create placeholder pages** (each exports a simple div with page name)

Create stub files for all 14 pages in `frontend/src/pages/`.

**Step 6: Verify full shell works**

```bash
cd frontend && npm run dev
```
Expected: Sidebar navigation opens tabs, tabs closable, pages switch correctly.

**Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: add app shell with sidebar, tabs, and page routing"
```

---

## Phase 3: Pages (Settings → Project → Home)

### Task 9: SettingsPage

**Files:**
- Create: `frontend/src/pages/SettingsPage.tsx`

Full settings form with:
- API Key input (password mode)
- Model select dropdown (gemini-3.1-pro-preview, gemini-3-pro-preview, etc.)
- Thinking level select
- Cloud sync section: OneDrive, Google Sheets, Google Drive (JSON upload + login button)
- "설정 적용 및 업무 시작" button

Calls: `api.getSettings()`, `api.updateSettings()`, `api.applySettings()`

**Commit after implementation.**

---

### Task 10: ProjectPage

**Files:**
- Create: `frontend/src/pages/ProjectPage.tsx`
- Create: `frontend/src/components/FolderTree.tsx`
- Create: `frontend/src/components/FilePicker.tsx`

Features:
- Folder tree view with 📁/📄 icons
- Context menu: create folder, rename, delete, move doc
- File upload area with drag-drop (HTML5 drop zone)
- Document preview panel

Calls: `api.getProjectDocs()`, `api.createFolder()`, `api.uploadFiles()`, etc.

**Commit after implementation.**

---

### Task 11: HomePage

**Files:**
- Create: `frontend/src/pages/HomePage.tsx`

Dashboard with cards:
- Phase 1, Phase 2 workflow cards
- Independent tools buttons
- Project management button
- Stats from API

**Commit after implementation.**

---

## Phase 4: Workflow + Chat Pages

### Task 12: WorkflowPage (High Complexity)

**Files:**
- Create: `frontend/src/pages/WorkflowPage.tsx`
- Modify: `backend/api_routes.py` (add file parse endpoint)

Largest page. Features:
- Tab-based (phase1) or step-based (phase2, im) workflow
- File upload + parsing step
- AI generation with streaming (WebSocket)
- Refinement chat
- Final result with export (MD/Word)
- Template selection

Must handle workflow configs (phase1 tabs, phase2 steps, im steps).

**Commit after implementation.**

---

### Task 13: QaSessionPage + LpQaPage

**Files:**
- Create: `frontend/src/pages/QaSessionPage.tsx`
- Create: `frontend/src/pages/LpQaPage.tsx`
- Create: `frontend/src/components/ChatWidget.tsx`

ChatWidget: message list (user/assistant), input field, markdown rendering.
QaSessionPage: left=FolderTree selector, right=ChatWidget.
LpQaPage: auto-generated questions, follow-up Q&A.

**Commit after implementation.**

---

## Phase 5: Utility Pages

### Task 14: AudioPage + CrawlerPage + OcrPage

**Files:**
- Create: `frontend/src/pages/AudioPage.tsx`
- Create: `frontend/src/pages/CrawlerPage.tsx`
- Create: `frontend/src/pages/OcrPage.tsx`
- Modify: `backend/api_routes.py` (add utility endpoints)

Simple form → API call → result display pages.

**Commit after implementation.**

---

### Task 15: MarkdownPage + DocTemplatePage + TextOrganizerPage + PptToolsPage

**Files:**
- Create: `frontend/src/pages/MarkdownPage.tsx`
- Create: `frontend/src/pages/DocTemplatePage.tsx`
- Create: `frontend/src/pages/TextOrganizerPage.tsx`
- Create: `frontend/src/pages/PptToolsPage.tsx`
- Modify: `backend/api_routes.py` (add remaining endpoints)

**Commit after implementation.**

---

## Phase 6: Cloud Sync + Polish

### Task 16: Cloud Sync API

**Files:**
- Modify: `backend/api_routes.py`

Endpoints for:
- `POST /api/sync/push`, `POST /api/sync/pull`, `POST /api/sync/full`
- `GET /api/sync/status`
- `POST /api/gdrive/login`, `POST /api/gdrive/logout`, `POST /api/gdrive/upload-json`

Wire up existing `cloud_sync.py` and `utils_gdrive.py`.

**Commit after implementation.**

---

### Task 17: Production Build + Entry Point

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `backend/main.py`
- Create: `run_web.bat` (launcher script)

**Step 1: Build frontend for production**

```bash
cd frontend && npm run build
```
This outputs to `backend/static/`.

**Step 2: Create launcher script (`run_web.bat`)**

```bat
@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
python -m backend.main %*
```

**Step 3: Verify both modes work**

```bash
python -m backend.main          # Desktop (pywebview)
python -m backend.main --web    # Browser
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: production build and dual-mode launcher"
```

---

## Summary

| Phase | Tasks | Estimated Complexity |
|-------|-------|---------------------|
| 1. Scaffolding | Tasks 1-2 | Low |
| 2. Core Infrastructure | Tasks 3-8 | Medium |
| 3. Settings/Project/Home | Tasks 9-11 | Medium |
| 4. Workflow + Chat | Tasks 12-13 | **High** |
| 5. Utility Pages | Tasks 14-15 | Low-Medium |
| 6. Sync + Polish | Tasks 16-17 | Medium |

**Total: 17 tasks across 6 phases.**

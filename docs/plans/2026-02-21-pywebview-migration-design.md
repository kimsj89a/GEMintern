# GEMintern PyWebView Migration Design

**Date:** 2026-02-21
**Goal:** PyQt6 데스크톱 앱을 React + FastAPI + pywebview 기반으로 전환

## Architecture

```
Frontend (React + Vite + Tailwind CSS)
    ↕ HTTP REST + WebSocket
Backend (FastAPI + uvicorn)
    ↕
Existing Python modules (core_rag, core_logic, utils_*, cloud_sync)
    ↕
Runner: pywebview (desktop) / uvicorn only (--web mode)
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 + TypeScript | UI components |
| Styling | Tailwind CSS | Notion-inspired design |
| Build | Vite | Fast dev/build |
| State | Zustand | Client-side state management |
| API | FastAPI | REST + WebSocket server |
| Streaming | WebSocket | AI generation streaming |
| Desktop | pywebview | Native window wrapper |
| Schemas | Pydantic | API request/response validation |

## Directory Structure

```
GEMintern/
├── backend/
│   ├── main.py            # Entry point (pywebview + --web mode)
│   ├── api_routes.py      # REST API routers
│   ├── api_ws.py          # WebSocket handlers
│   └── api_models.py      # Pydantic schemas
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       ├── api/           # API client (fetch + WebSocket)
│       │   ├── client.ts
│       │   └── ws.ts
│       ├── stores/        # Zustand stores
│       │   ├── appStore.ts
│       │   ├── projectStore.ts
│       │   └── settingsStore.ts
│       ├── components/    # Shared UI components
│       │   ├── Sidebar.tsx
│       │   ├── TabContainer.tsx
│       │   ├── ChatWidget.tsx
│       │   ├── FolderTree.tsx
│       │   ├── FilePicker.tsx
│       │   ├── StatusBox.tsx
│       │   ├── StepIndicator.tsx
│       │   ├── MarkdownViewer.tsx
│       │   └── CollapsibleBox.tsx
│       └── pages/         # 14 page components
│           ├── HomePage.tsx
│           ├── SettingsPage.tsx
│           ├── ProjectPage.tsx
│           ├── WorkflowPage.tsx
│           ├── QaSessionPage.tsx
│           ├── LpQaPage.tsx
│           ├── AudioPage.tsx
│           ├── CrawlerPage.tsx
│           ├── OcrPage.tsx
│           ├── MarkdownPage.tsx
│           ├── DocTemplatePage.tsx
│           ├── TextOrganizerPage.tsx
│           └── PptToolsPage.tsx
├── core_rag.py            # Unchanged
├── core_logic.py          # Unchanged
├── core_rfi.py            # Unchanged
├── core_chained.py        # Unchanged
├── cloud_sync.py          # Unchanged
├── utils_gdrive.py        # Unchanged
├── utils_gsheets.py       # Unchanged
├── utils_onedrive.py      # Unchanged
├── utils_audio.py         # Unchanged
├── prompts.py             # Unchanged
└── app_state.py           # Unchanged (used by backend)
```

## API Design

### REST Endpoints

```
# Settings
GET    /api/settings              → current settings
PUT    /api/settings              → update settings
POST   /api/settings/apply        → apply and start

# Projects
GET    /api/projects              → list all projects
POST   /api/projects              → create project
DELETE /api/projects/{name}       → delete project

# Documents
GET    /api/projects/{name}/docs         → folder tree with docs
POST   /api/projects/{name}/docs         → upload files
DELETE /api/projects/{name}/docs/{doc}   → trash document
POST   /api/projects/{name}/folders      → create folder
PUT    /api/projects/{name}/docs/{doc}/move → move doc to folder

# AI Operations
POST   /api/generate              → start AI generation (returns task_id)
POST   /api/qa                    → Q&A question (returns task_id)
POST   /api/refine                → refine existing text
POST   /api/analyze               → run analysis task

# Cloud Sync
POST   /api/sync/push             → push to cloud
POST   /api/sync/pull             → pull from cloud
POST   /api/sync/full             → bidirectional sync
GET    /api/sync/status           → sync connection status

# Google Drive
POST   /api/gdrive/login          → start OAuth flow
POST   /api/gdrive/logout         → clear token
GET    /api/gdrive/status         → connection status

# Utilities
POST   /api/audio/transcribe      → audio transcription
POST   /api/crawler/crawl         → web crawling
POST   /api/ocr/process           → OCR processing
POST   /api/markdown/convert      → MD to Word
POST   /api/ppt/generate          → PPT generation
```

### WebSocket

```
ws://localhost:PORT/ws/stream

Client → Server:
  { "type": "subscribe", "task_id": "xxx" }

Server → Client:
  { "type": "chunk", "task_id": "xxx", "data": "..." }
  { "type": "status", "task_id": "xxx", "status": "generating" }
  { "type": "complete", "task_id": "xxx", "result": "..." }
  { "type": "error", "task_id": "xxx", "error": "..." }
```

## Page Complexity Map

| Page | Complexity | Key Features |
|------|-----------|--------------|
| HomePage | Low | Dashboard, stats |
| SettingsPage | Medium | Forms, OAuth flow, file browser |
| ProjectPage | Medium | Tree view, context menu, file upload |
| WorkflowPage | **High** | Multi-tab, multi-step, streaming, file context |
| QaSessionPage | Medium | Chat, tree selector, streaming |
| LpQaPage | Medium | Chat, auto-questions, streaming |
| AudioPage | Low | File upload, model selection |
| CrawlerPage | Low | URL input, results display |
| OcrPage | Low | File upload, engine selection |
| MarkdownPage | Low | Text input, file download |
| DocTemplatePage | Low | Template selection, generation |
| TextOrganizerPage | Low | Text input/output |
| PptToolsPage | Medium | Context input, slide generation |

## Run Modes

```bash
# Desktop mode (default) - pywebview window
python backend/main.py

# Web mode - opens in browser
python backend/main.py --web

# Dev mode - frontend hot reload
cd frontend && npm run dev    # Vite dev server (port 5173)
python backend/main.py --dev  # API server only (port 8000)
```

## Migration Strategy

Existing PyQt6 code is preserved. New code lives in `backend/` and `frontend/`.
Both can coexist during transition. Old `main.py` remains as legacy launcher.

## Design Decisions

1. **FastAPI over pywebview.api**: User chose WebSocket for streaming support
2. **React over Svelte**: Larger ecosystem, user preference
3. **Zustand over Redux**: Simpler, less boilerplate for this scale
4. **Dual mode**: pywebview desktop + browser --web flag
5. **Tailwind CSS**: Rapid styling, Notion-inspired design tokens
6. **TypeScript**: Type safety for 14-page frontend

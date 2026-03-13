# Server-First Data Sync Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the server the single source of truth for all project data, enabling cross-PC access by logging into the same account.

**Architecture:** Replace IndexedDB-first approach with server-first. All CRUD operations go through server API first, IDB becomes a read cache. Add Q&A session persistence to SQLite. Migrate existing rag_storage/_projects.json data to SQLite on startup.

**Tech Stack:** SQLite (backend), FastAPI endpoints, React + Zustand (frontend), existing rag_storage for file-based document storage.

---

## Chunk 1: Backend — Database Schema & Migration

### Task 1: Add project/document/Q&A tables to SQLite

**Files:**
- Modify: `backend/database.py:51-82` (init_db function)

- [ ] **Step 1: Add new tables to init_db()**

Add after the existing `CREATE TABLE IF NOT EXISTS user_settings` block:

```python
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                storage_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id),
                UNIQUE(owner_id, name)
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                folder TEXT DEFAULT '__root__',
                filename TEXT NOT NULL,
                parsed_text TEXT,
                size INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(project_id, folder, filename)
            );

            CREATE TABLE IF NOT EXISTS qa_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT DEFAULT '새 대화',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS qa_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES qa_sessions(id) ON DELETE CASCADE
            );
```

- [ ] **Step 2: Add migration function for existing rag_storage data**

Add `migrate_rag_projects_to_db()` function to `database.py` that reads `rag_storage/_projects.json` and inserts into SQLite projects table. Called from `init_db()`.

```python
def migrate_rag_projects_to_db():
    """One-time migration: rag_storage/_projects.json → SQLite projects table."""
    import json
    rag_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag_storage")
    projects_file = os.path.join(rag_root, "_projects.json")
    if not os.path.exists(projects_file):
        return

    with open(projects_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    with get_db() as conn:
        for p in data.get("projects", []):
            owner_id = p.get("owner_id")
            if owner_id is None:
                owner_id = 1  # assign legacy projects to admin
            existing = conn.execute(
                "SELECT id FROM projects WHERE name = ? AND owner_id = ?",
                (p["name"], owner_id)
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO projects (name, owner_id, storage_name, created_at) VALUES (?, ?, ?, ?)",
                    (p["name"], owner_id, p.get("storage_name", p["name"]),
                     p.get("created", datetime.datetime.now().isoformat()))
                )
    print("[DB] Migrated rag_storage projects to SQLite.")
```

- [ ] **Step 3: Call migration from init_db()**

Add at the end of `init_db()`:
```python
    migrate_rag_projects_to_db()
```

- [ ] **Step 4: Commit**

```bash
git add backend/database.py
git commit -m "feat: add projects/documents/qa tables to SQLite with rag_storage migration"
```

---

### Task 2: Add server-side project CRUD via SQLite

**Files:**
- Modify: `backend/api_routes.py:338-416` (project endpoints)

- [ ] **Step 1: Update list_projects to query SQLite**

```python
@router.get("/projects")
def list_projects(user: dict = Depends(get_current_user)):
    from backend.database import get_db
    import core_rag
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, storage_name, created_at FROM projects WHERE owner_id = ? ORDER BY created_at DESC",
            (user["id"],)
        ).fetchall()
    result = []
    for r in rows:
        doc_count = 0
        try:
            doc_count = len(core_rag.get_indexed_doc_names(r["name"]))
        except:
            pass
        result.append({
            "id": r["id"], "name": r["name"], "storage_name": r["storage_name"],
            "created_at": r["created_at"], "doc_count": doc_count,
        })
    return result
```

- [ ] **Step 2: Update create_project to insert into SQLite + rag_storage**

Keep existing `core_rag.create_project()` for file storage, but also insert into SQLite.

- [ ] **Step 3: Update delete_project similarly**

- [ ] **Step 4: Add GET /projects/{name}/documents endpoint**

Returns all documents for a project from SQLite (with folder structure).

```python
@router.get("/projects/{name}/documents")
def list_documents(name: str, user: dict = Depends(get_current_user)):
    _verify_project_ownership(name, user["id"])
    from backend.database import get_db
    with get_db() as conn:
        project = conn.execute(
            "SELECT id FROM projects WHERE name = ? AND owner_id = ?",
            (name, user["id"])
        ).fetchone()
        if not project:
            raise HTTPException(404, "프로젝트를 찾을 수 없습니다.")
        docs = conn.execute(
            "SELECT id, folder, filename, size, uploaded_at FROM documents WHERE project_id = ? ORDER BY folder, filename",
            (project["id"],)
        ).fetchall()
    return [dict(d) for d in docs]
```

- [ ] **Step 5: Update upload/sync-texts to store parsed_text in SQLite**

After saving .md to rag_storage, also INSERT into documents table with parsed_text.

- [ ] **Step 6: Commit**

```bash
git add backend/api_routes.py
git commit -m "feat: server-first project and document CRUD via SQLite"
```

---

### Task 3: Add Q&A session persistence API

**Files:**
- Modify: `backend/api_routes.py` (add new section)

- [ ] **Step 1: Add Q&A session CRUD endpoints**

```python
# ── Q&A Sessions ──

@router.get("/qa/sessions")
def list_qa_sessions(project: str, user: dict = Depends(get_current_user)):
    """List Q&A sessions for a project."""
    _verify_project_ownership(project, user["id"])
    from backend.database import get_db
    with get_db() as conn:
        proj = conn.execute(
            "SELECT id FROM projects WHERE name = ? AND owner_id = ?",
            (project, user["id"])
        ).fetchone()
        if not proj:
            return []
        sessions = conn.execute(
            "SELECT id, title, created_at, updated_at FROM qa_sessions WHERE project_id = ? ORDER BY updated_at DESC",
            (proj["id"],)
        ).fetchall()
    return [dict(s) for s in sessions]


@router.post("/qa/sessions")
def create_qa_session(data: dict, user: dict = Depends(get_current_user)):
    project_name = data.get("project")
    _verify_project_ownership(project_name, user["id"])
    from backend.database import get_db
    with get_db() as conn:
        proj = conn.execute(
            "SELECT id FROM projects WHERE name = ? AND owner_id = ?",
            (project_name, user["id"])
        ).fetchone()
        if not proj:
            raise HTTPException(404)
        cur = conn.execute(
            "INSERT INTO qa_sessions (project_id, title) VALUES (?, ?)",
            (proj["id"], data.get("title", "새 대화"))
        )
        session_id = cur.lastrowid
    return {"id": session_id}


@router.get("/qa/sessions/{session_id}/messages")
def get_session_messages(session_id: int, user: dict = Depends(get_current_user)):
    from backend.database import get_db
    with get_db() as conn:
        msgs = conn.execute(
            "SELECT id, role, content, created_at FROM qa_messages WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
    return [dict(m) for m in msgs]


@router.post("/qa/sessions/{session_id}/messages")
def add_session_message(session_id: int, data: dict, user: dict = Depends(get_current_user)):
    from backend.database import get_db
    with get_db() as conn:
        conn.execute(
            "INSERT INTO qa_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, data["role"], data["content"])
        )
        conn.execute(
            "UPDATE qa_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
    return {"ok": True}
```

- [ ] **Step 2: Commit**

```bash
git add backend/api_routes.py
git commit -m "feat: Q&A session persistence API"
```

---

## Chunk 2: Frontend — Server-First Data Flow

### Task 4: Update API client with new endpoints

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add new API methods**

```typescript
  // Server-first project/document APIs
  listDocuments: (project: string) =>
    request<any[]>(`/projects/${encodeURIComponent(project)}/documents`),

  // Q&A Sessions
  listQaSessions: (project: string) =>
    request<any[]>(`/qa/sessions?project=${encodeURIComponent(project)}`),
  createQaSession: (project: string, title?: string) =>
    request<{ id: number }>('/qa/sessions', {
      method: 'POST', body: JSON.stringify({ project, title }),
    }),
  getSessionMessages: (sessionId: number) =>
    request<any[]>(`/qa/sessions/${sessionId}/messages`),
  addSessionMessage: (sessionId: number, role: string, content: string) =>
    request<any>(`/qa/sessions/${sessionId}/messages`, {
      method: 'POST', body: JSON.stringify({ role, content }),
    }),
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add server-first API methods for documents and Q&A sessions"
```

---

### Task 5: Convert ProjectPage to server-first

**Files:**
- Modify: `frontend/src/pages/ProjectPage.tsx`

Key changes:
- `loadProjects()` → `api.listProjects()` instead of `listLocalProjects()`
- `handleCreateProject()` → `api.createProject()` instead of `createLocalProject()`
- `handleDeleteProject()` → `api.deleteProject()` instead of `deleteLocalProject()`
- `loadDocs()` → `api.getProjectDocs()` instead of `getLocalFolderTree()`
- `handleUpload()` → `api.uploadFiles()` directly (already exists), remove IDB save
- Remove "로컬 저장: X개 문서" indicator, replace with "서버 저장: X개 문서"
- Remove manual "서버 동기화" button (no longer needed)
- Remove all imports from `projectDB.ts`

- [ ] **Step 1: Rewrite loadProjects and loadDocs to use server API**
- [ ] **Step 2: Rewrite CRUD handlers to use server API**
- [ ] **Step 3: Remove IDB imports and sync UI elements**
- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ProjectPage.tsx
git commit -m "feat: ProjectPage uses server as source of truth"
```

---

### Task 6: Convert QaSessionPage to use sessions

**Files:**
- Modify: `frontend/src/pages/QaSessionPage.tsx`

Key changes:
- Add session sidebar (list of past sessions)
- Auto-create session on first message
- Save each message to server via `api.addSessionMessage()`
- Load history on session switch via `api.getSessionMessages()`
- Remove `useAutoSync` import
- Use `api.getProjectDocs()` for folder tree instead of `getLocalFolderTree()`

- [ ] **Step 1: Add session state and sidebar**
- [ ] **Step 2: Modify handleSend to persist messages**
- [ ] **Step 3: Add session switching**
- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/QaSessionPage.tsx
git commit -m "feat: Q&A with persistent sessions and server-side history"
```

---

### Task 7: Update remaining pages that use projectDB

**Files:**
- Modify: `frontend/src/pages/WorkflowPage.tsx` — use `api.getProjectDocs()` for tree
- Modify: `frontend/src/utils/autoSync.ts` — can be deleted or gutted
- Modify: `frontend/src/utils/projectDB.ts` — keep as cache-only utility, remove as source of truth

- [ ] **Step 1: Update WorkflowPage imports**
- [ ] **Step 2: Remove or simplify autoSync.ts**
- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/WorkflowPage.tsx frontend/src/utils/autoSync.ts
git commit -m "refactor: remove IDB as source of truth from all pages"
```

---

## Chunk 3: Build, Test, Deploy

### Task 8: End-to-end test and deploy

- [ ] **Step 1: Build frontend**

```bash
cd frontend && npx vite build --outDir ../backend/static
```

- [ ] **Step 2: Start server and test**

Test: create project, upload docs, verify docs persist across browser refresh (not IDB).
Test: Q&A session creates, messages persist, visible after page reload.
Test: login from incognito → same projects visible.

- [ ] **Step 3: Commit final build and push**

```bash
git add -f backend/static/
git commit -m "build: server-first sync complete"
git push
```

- [ ] **Step 4: Deploy to Railway**

```bash
railway up --detach --service gemintern
```

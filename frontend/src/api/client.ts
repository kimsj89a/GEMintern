import { useAuthStore } from '../stores/authStore';
import type { GenerateRequest, QaRequest, AnalysisRequest, SettingsData, SlideData } from '../types/api';

const BASE = '/api';

function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  if (token) return { Authorization: `Bearer ${token}` };
  return {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(),
  };
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { ...headers, ...(options?.headers as Record<string, string>) },
  });
  if (res.status === 401) {
    // Refresh failure should not cascade to logout — only real API calls should
    if (!path.includes('/auth/refresh')) {
      useAuthStore.getState().logout();
    }
    throw new Error('Unauthorized');
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function fetchWithAuth(url: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(url, {
    ...init,
    headers: { ...getAuthHeaders(), ...(init?.headers as Record<string, string>) },
  });
  if (res.status === 401) {
    useAuthStore.getState().logout();
    throw new Error('Unauthorized');
  }
  return res;
}

export const api = {
  // Health
  health: () => request<{ status: string; version?: string }>('/health'),

  // Settings
  getSettings: () => request<SettingsData>('/settings'),
  updateSettings: (data: SettingsData) =>
    request<SettingsData>('/settings', { method: 'PUT', body: JSON.stringify(data) }),
  applySettings: () =>
    request<{ ok?: boolean; success?: boolean; error?: string }>('/settings/apply', { method: 'POST' }),

  // Projects
  listProjects: () => request<any[]>('/projects'),
  createProject: (name: string) =>
    request<any>('/projects', { method: 'POST', body: JSON.stringify({ name }) }),
  renameProject: (name: string, newName: string) =>
    request<any>(`/projects/${encodeURIComponent(name)}`, {
      method: 'PATCH',
      body: JSON.stringify({ new_name: newName }),
    }),
  deleteProject: (name: string) =>
    request<any>(`/projects/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  // Documents
  getProjectDocs: (name: string) =>
    request<any>(`/projects/${encodeURIComponent(name)}/docs`),
  createFolder: (project: string, folderName: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/folders`, {
      method: 'POST',
      body: JSON.stringify({ name: folderName }),
    }),
  deleteFolder: (project: string, folder: string) =>
    request<any>(
      `/projects/${encodeURIComponent(project)}/folders/${encodeURIComponent(folder)}`,
      { method: 'DELETE' }
    ),
  renameFolder: (project: string, oldName: string, newLeaf: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/folders/rename`, {
      method: 'POST',
      body: JSON.stringify({ old_name: oldName, new_name: newLeaf }),
    }),
  moveDoc: (project: string, doc: string, targetFolder: string) =>
    request<any>(
      `/projects/${encodeURIComponent(project)}/docs/${encodeURIComponent(doc)}/move`,
      { method: 'POST', body: JSON.stringify({ target_folder: targetFolder }) }
    ),
  trashDoc: (project: string, doc: string) =>
    request<any>(
      `/projects/${encodeURIComponent(project)}/docs/${encodeURIComponent(doc)}`,
      { method: 'DELETE' }
    ),
  uploadFiles: async (project: string, files: File[], folder?: string) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    if (folder) formData.append('folder', folder);
    const res = await fetchWithAuth(`${BASE}/projects/${encodeURIComponent(project)}/upload`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },
  syncTextsToServer: (project: string, docs: { filename: string; parsedText: string }[]) =>
    request<any>(`/projects/${encodeURIComponent(project)}/sync-texts`, {
      method: 'POST',
      body: JSON.stringify({ docs }),
    }),

  // Wiki
  getWiki: (project: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki`),
  generateWiki: (project: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki/generate`, { method: 'POST' }),
  updateWiki: (project: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki/update`, { method: 'POST' }),
  suggestWikiSections: (project: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki/suggest-sections`, { method: 'POST' }),
  patchWikiSection: (project: string, sectionId: string, body: any) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki/sections/${encodeURIComponent(sectionId)}`, {
      method: 'PATCH', body: JSON.stringify(body),
    }),
  reviseWikiSection: (project: string, sectionId: string, instruction: string, selectedDocs?: string[]) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki/sections/${encodeURIComponent(sectionId)}/revise`, {
      method: 'POST', body: JSON.stringify({ instruction, selected_docs: selectedDocs }),
    }),
  addWikiSection: (project: string, body: { id: string; title: string; content?: string }) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki/sections`, {
      method: 'POST', body: JSON.stringify(body),
    }),
  deleteWikiSection: (project: string, sectionId: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki/sections/${encodeURIComponent(sectionId)}`, {
      method: 'DELETE',
    }),
  getCitationContext: (project: string, source_doc: string, excerpt: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/wiki/citation-context`, {
      method: 'POST', body: JSON.stringify({ source_doc, excerpt }),
    }),

  // Review Workflow
  extractRfi: (project: string) =>
    request<{ task_id: string }>(`/projects/${encodeURIComponent(project)}/review/extract-rfi`, {
      method: 'POST',
    }),
  crosscheckRfi: (project: string, items: any[]) =>
    request<{ task_id: string }>(`/projects/${encodeURIComponent(project)}/review/crosscheck`, {
      method: 'POST', body: JSON.stringify({ items }),
    }),
  generateExternalRfi: (project: string, gapItems: any[]) =>
    request<{ task_id: string }>(`/projects/${encodeURIComponent(project)}/review/generate-external-rfi`, {
      method: 'POST', body: JSON.stringify({ gap_items: gapItems }),
    }),

  // Excel Model
  generateExcelModel: (project: string) =>
    request<{ task_id: string }>(`/projects/${encodeURIComponent(project)}/excel-model`, {
      method: 'POST',
    }),
  // Contract Comparison
  contractCompare: (project: string, selectedDocs?: string[]) =>
    request<{ task_id: string }>(`/projects/${encodeURIComponent(project)}/contract-compare`, {
      method: 'POST',
      body: JSON.stringify({ selected_docs: selectedDocs }),
    }),

  downloadExcelModel: async (project: string, excelB64: string, filename: string) => {
    const res = await fetchWithAuth(`${BASE}/projects/${encodeURIComponent(project)}/excel-model/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ excel_b64: excelB64, filename }),
    });
    if (!res.ok) throw new Error(`다운로드 실패: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  extractExcelCells: async (files: File[]) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await fetchWithAuth(`${BASE}/extract-excel-cells`, {
      method: 'POST',
      body: formData,
    });
    return res.json() as Promise<{ cells: string[]; count: number }>;
  },

  parseFiles: async (files: File[]) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await fetchWithAuth(`${BASE}/parse-files`, {
      method: 'POST',
      body: formData,
    });
    return res.json() as Promise<{ parsed_texts: Record<string, string>; errors: string[]; count: number }>;
  },

  // AI
  startGenerate: (data: GenerateRequest) =>
    request<{ task_id: string }>('/generate', { method: 'POST', body: JSON.stringify(data) }),
  startQa: (data: QaRequest) =>
    request<{ task_id: string }>('/qa', { method: 'POST', body: JSON.stringify(data) }),
  startAnalysis: (data: AnalysisRequest) =>
    request<{ task_id: string }>('/analyze', { method: 'POST', body: JSON.stringify(data) }),
  getTaskStatus: (taskId: string) => request<any>(`/tasks/${taskId}`),
  saveResearch: (data: { project_name: string; doc_name: string; content: string }) =>
    request<any>('/save-research', { method: 'POST', body: JSON.stringify(data) }),
  downloadDoc: async (project: string, docName: string) => {
    const res = await fetchWithAuth(
      `${BASE}/projects/${encodeURIComponent(project)}/docs/${encodeURIComponent(docName)}/download`
    );
    if (!res.ok) throw new Error(`다운로드 실패: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${docName}.md`;
    a.click();
    URL.revokeObjectURL(url);
  },

  // PPT
  createPptx: async (slideJson: SlideData[]) => {
    const res = await fetchWithAuth(`${BASE}/create-pptx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slide_json: slideJson }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'PPTX 생성 실패' }));
      throw new Error(err.detail || `API error: ${res.status}`);
    }
    return res.blob();
  },
  createIbPptx: async (slideJson: any) => {
    const res = await fetchWithAuth(`${BASE}/create-ib-pptx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slide_json: slideJson }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'IB PPTX 생성 실패' }));
      throw new Error(err.detail || `API error: ${res.status}`);
    }
    return res.blob();
  },
  slideRegenerate: (data: { current_slide: SlideData; prev_slide?: SlideData; next_slide?: SlideData; instruction: string }) =>
    request<{ task_id: string }>('/slide-regenerate', { method: 'POST', body: JSON.stringify(data) }),
  slideOutline: (data: { task_type: string; kwargs: Record<string, any> }) =>
    request<{ task_id: string }>('/slide-outline', { method: 'POST', body: JSON.stringify(data) }),
  slidesFromOutline: (data: { outline: any; project_name?: string; selected_docs?: string[]; context_text?: string }) =>
    request<{ task_id: string }>('/slides-from-outline', { method: 'POST', body: JSON.stringify(data) }),
  updatePptxHistory: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetchWithAuth(`${BASE}/update-pptx-history`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '업데이트 실패' }));
      throw new Error(err.detail || `API error: ${res.status}`);
    }
    return res.blob();
  },

  // QuickMail
  quickmailGenerate: (data: { prompt: string; context?: string; tone?: string; language?: string }) =>
    request<{ task_id: string }>('/quickmail/generate', { method: 'POST', body: JSON.stringify(data) }),

  // Vector RAG
  reindexProject: (project: string, force = false) =>
    request<any>(`/projects/${encodeURIComponent(project)}/reindex?force=${force}`, { method: 'POST' }),
  vectorStats: (project: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/vector-stats`),
  syncStatus: (project: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/sync-status`),
  syncDocs: (project: string, add: string[], remove: string[]) =>
    request<any>(`/projects/${encodeURIComponent(project)}/sync-docs`, {
      method: 'POST', body: JSON.stringify({ add, remove }),
    }),

  // Free-form Document
  freedocUpload: async (files: File[]) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await fetchWithAuth(`${BASE}/freedoc/upload`, { method: 'POST', body: formData });
    return res.json();
  },
  freedocGenerate: (data: { instruction: string; file_text?: string; paste_text?: string }) =>
    request<{ task_id: string }>('/freedoc/generate', { method: 'POST', body: JSON.stringify(data) }),

  // Draft Document (기안문)
  draftdocGenerate: (data: { file_text?: string; paste_text?: string; instruction?: string }) =>
    request<{ task_id: string }>('/draftdoc/generate', { method: 'POST', body: JSON.stringify(data) }),

  // Document Updater
  docUpdaterUploadOriginal: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetchWithAuth(`${BASE}/doc-updater/upload-original`, {
      method: 'POST', body: formData,
    });
    return res.json();
  },
  docUpdaterUploadSupplementary: async (sessionId: string, files: File[]) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await fetchWithAuth(`${BASE}/doc-updater/${sessionId}/supplementary`, {
      method: 'POST', body: formData,
    });
    return res.json();
  },
  docUpdaterRun: (data: {
    session_id: string; supplementary_text?: string;
    instruction: string; mode?: string;
  }) =>
    request<{ task_id: string }>('/doc-updater/run', {
      method: 'POST', body: JSON.stringify(data),
    }),
  docUpdaterPromoteOutput: (data: { session_id: string; output_path: string }) =>
    request<{ filename: string; doc_type: string; paragraph_count: number; preview: string }>(
      '/doc-updater/promote-output', { method: 'POST', body: JSON.stringify(data) },
    ),
  docUpdaterDownload: async (path: string, filename: string) => {
    const res = await fetchWithAuth(
      `${BASE}/doc-updater/download?path=${encodeURIComponent(path)}`
    );
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },

  // Auth (no auth header — must bypass request() to avoid stale token)
  login: async (username: string, password: string) => {
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json() as Promise<{ token: string; user: any }>;
  },
  register: async (username: string, password: string, invite_code: string) => {
    const res = await fetch(`${BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, invite_code }),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json() as Promise<{ token: string; user: any }>;
  },
  getMe: () => request<any>('/auth/me'),
  refreshToken: () => request<{ token: string; user: any }>('/auth/refresh', { method: 'POST' }),

  // Research Notes
  listNotes: (project: string) =>
    request<any[]>(`/projects/${encodeURIComponent(project)}/notes`),
  createNote: (project: string, data: { title: string; content?: string; tags?: string[] }) =>
    request<any>(`/projects/${encodeURIComponent(project)}/notes`, {
      method: 'POST', body: JSON.stringify(data),
    }),
  getNote: (project: string, slug: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/notes/${encodeURIComponent(slug)}`),
  updateNote: (project: string, slug: string, data: { title?: string; content?: string; tags?: string[] }) =>
    request<any>(`/projects/${encodeURIComponent(project)}/notes/${encodeURIComponent(slug)}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),
  deleteNote: (project: string, slug: string) =>
    request<any>(`/projects/${encodeURIComponent(project)}/notes/${encodeURIComponent(slug)}`, {
      method: 'DELETE',
    }),
  getNoteBacklinks: (project: string, slug: string) =>
    request<any[]>(`/projects/${encodeURIComponent(project)}/notes/${encodeURIComponent(slug)}/backlinks`),
  getNoteTags: (project: string) =>
    request<any[]>(`/projects/${encodeURIComponent(project)}/notes/tags`),

  // NPS
  npsSearch: (params: URLSearchParams) =>
    request<{ data: any[]; total: number; page: number; perPage: number; error?: string }>(
      `/nps/search?${params.toString()}`
    ),

  // Server-first document list
  listDocuments: (project: string) =>
    request<any[]>(`/projects/${encodeURIComponent(project)}/documents`),

  // Q&A Sessions
  listQaSessions: (project: string) =>
    request<any[]>(`/qa/sessions?project=${encodeURIComponent(project)}`),
  createQaSession: (project: string, title?: string) =>
    request<{ id: number }>('/qa/sessions', {
      method: 'POST', body: JSON.stringify({ project, title }),
    }),
  updateQaSession: (sessionId: number, title: string) =>
    request<any>(`/qa/sessions/${sessionId}`, {
      method: 'PATCH', body: JSON.stringify({ title }),
    }),
  deleteQaSession: (sessionId: number) =>
    request<any>(`/qa/sessions/${sessionId}`, { method: 'DELETE' }),
  getSessionMessages: (sessionId: number) =>
    request<any[]>(`/qa/sessions/${sessionId}/messages`),
  addSessionMessage: (sessionId: number, role: string, content: string) =>
    request<any>(`/qa/sessions/${sessionId}/messages`, {
      method: 'POST', body: JSON.stringify({ role, content }),
    }),

  // Generation History
  listHistory: (limit = 50, offset = 0) =>
    request<{ items: any[]; limit: number; offset: number }>(
      `/history?limit=${limit}&offset=${offset}`
    ),
  getHistory: (id: number) => request<any>(`/history/${id}`),
  deleteHistory: (id: number) =>
    request<{ ok: boolean }>(`/history/${id}`, { method: 'DELETE' }),

  // Folder Scan
  scanFolderPreview: (data: { folder_path: string; recursive?: boolean; file_extensions?: string[] }) =>
    request<{ files: { path: string; name: string; size: number; ext: string; relative_path: string }[]; total_size: number; file_count: number }>(
      '/scan-folder/preview', { method: 'POST', body: JSON.stringify(data) },
    ),
  ingestScannedFiles: (project: string, data: { folder_path: string; selected_files: string[]; preserve_structure?: boolean }) =>
    request<{ success: boolean; indexed: string[]; skipped: string[]; errors: any[]; indexed_count: number; skipped_count: number; error_count: number }>(
      `/projects/${encodeURIComponent(project)}/scan-folder/ingest`,
      { method: 'POST', body: JSON.stringify(data) },
    ),

  // PDF Unlock
  unlockPdf: async (file: File, password: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('password', password);
    const res = await fetchWithAuth(`${BASE}/unlock-pdf`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '알 수 없는 오류' }));
      throw new Error(err.detail || `API error: ${res.status}`);
    }
    const blob = await res.blob();
    const disposition = res.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename="?(.+?)"?$/);
    const filename = match ? match[1] : `unlocked_${file.name}`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    return { filename };
  },

  // Admin
  createInviteCodes: (count: number) =>
    request<{ codes: string[] }>('/auth/invite-codes', {
      method: 'POST',
      body: JSON.stringify({ count }),
    }),
  listInviteCodes: () => request<any[]>('/auth/invite-codes'),
  getUsageStats: () => request<any[]>('/auth/usage'),
};

import { useAuthStore } from '../stores/authStore';

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
    useAuthStore.getState().logout();
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
  health: () => request<{ status: string }>('/health'),

  // Settings
  getSettings: () => request<any>('/settings'),
  updateSettings: (data: any) =>
    request<any>('/settings', { method: 'PUT', body: JSON.stringify(data) }),
  applySettings: () =>
    request<any>('/settings/apply', { method: 'POST' }),

  // Projects
  listProjects: () => request<any[]>('/projects'),
  createProject: (name: string) =>
    request<any>('/projects', { method: 'POST', body: JSON.stringify({ name }) }),
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
  uploadFiles: async (project: string, files: File[]) => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
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
  startGenerate: (data: any) =>
    request<{ task_id: string }>('/generate', { method: 'POST', body: JSON.stringify(data) }),
  startQa: (data: any) =>
    request<{ task_id: string }>('/qa', { method: 'POST', body: JSON.stringify(data) }),
  startAnalysis: (data: any) =>
    request<{ task_id: string }>('/analyze', { method: 'POST', body: JSON.stringify(data) }),
  getTaskStatus: (taskId: string) => request<any>(`/tasks/${taskId}`),

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

  // Admin
  createInviteCodes: (count: number) =>
    request<{ codes: string[] }>('/auth/invite-codes', {
      method: 'POST',
      body: JSON.stringify({ count }),
    }),
  listInviteCodes: () => request<any[]>('/auth/invite-codes'),
  getUsageStats: () => request<any[]>('/auth/usage'),
};

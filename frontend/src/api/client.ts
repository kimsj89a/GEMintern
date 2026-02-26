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
    const res = await fetch(`${BASE}/projects/${encodeURIComponent(project)}/upload`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  // AI
  startGenerate: (data: any) =>
    request<{ task_id: string }>('/generate', { method: 'POST', body: JSON.stringify(data) }),
  startQa: (data: any) =>
    request<{ task_id: string }>('/qa', { method: 'POST', body: JSON.stringify(data) }),
  startAnalysis: (data: any) =>
    request<{ task_id: string }>('/analyze', { method: 'POST', body: JSON.stringify(data) }),
  getTaskStatus: (taskId: string) => request<any>(`/tasks/${taskId}`),

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
    const res = await fetch(`${BASE}/freedoc/upload`, { method: 'POST', body: formData });
    return res.json();
  },
  freedocGenerate: (data: { instruction: string; file_text?: string; paste_text?: string }) =>
    request<{ task_id: string }>('/freedoc/generate', { method: 'POST', body: JSON.stringify(data) }),

  // Sync
  syncPush: (project: string) =>
    request<any>('/sync/push', { method: 'POST', body: JSON.stringify({ project_name: project }) }),
  syncPull: (project: string) =>
    request<any>('/sync/pull', { method: 'POST', body: JSON.stringify({ project_name: project }) }),
  cloudSyncStatus: () => request<any>('/sync/status'),
};

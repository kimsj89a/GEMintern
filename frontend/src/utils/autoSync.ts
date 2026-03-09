/**
 * Auto-sync: when a project is selected, ensure server has documents
 * by syncing from IndexedDB if needed.
 */
import { useEffect, useRef } from 'react';
import { api } from '../api/client';
import { getProjectDocuments } from './projectDB';

const syncedProjects = new Set<string>();

export async function ensureServerSync(project: string): Promise<void> {
  if (!project || syncedProjects.has(project)) return;

  try {
    // Check if server already has documents
    const serverDocs = await api.getProjectDocs(project).catch(() => null) as any;
    const serverHasDocs = serverDocs && serverDocs.count > 0;

    if (serverHasDocs) {
      syncedProjects.add(project);
      return;
    }

    // Server empty — sync from IndexedDB
    const localDocs = await getProjectDocuments(project);
    const realDocs = localDocs.filter(d => d.filename !== '__folder_placeholder__' && d.parsedText);

    if (realDocs.length === 0) {
      syncedProjects.add(project);
      return;
    }

    const payload = realDocs.map(d => ({
      filename: d.filename,
      parsedText: d.parsedText,
      folder: d.folder,
    }));

    await api.syncTextsToServer(project, payload);
    syncedProjects.add(project);
    console.log(`[autoSync] Synced ${realDocs.length} docs for "${project}" to server`);
  } catch (err) {
    console.warn('[autoSync] Failed:', err);
  }
}

/** React hook: auto-sync on project change */
export function useAutoSync(project: string) {
  const ran = useRef('');
  useEffect(() => {
    if (!project || ran.current === project) return;
    ran.current = project;
    ensureServerSync(project);
  }, [project]);
}

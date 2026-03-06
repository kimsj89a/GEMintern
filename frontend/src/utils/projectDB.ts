/**
 * IndexedDB-based local project storage.
 * Projects and parsed documents are stored in the browser,
 * so data persists across server deploys (Railway etc.).
 */

const DB_NAME = 'gemintern_projects';
const DB_VERSION = 1;

export interface LocalProject {
  name: string;
  createdAt: number;
}

export interface LocalDocument {
  id: string;
  project: string;
  folder: string;
  filename: string;
  parsedText: string;
  size: number;
  uploadedAt: number;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('projects')) {
        db.createObjectStore('projects', { keyPath: 'name' });
      }
      if (!db.objectStoreNames.contains('documents')) {
        const store = db.createObjectStore('documents', { keyPath: 'id' });
        store.createIndex('by_project', 'project', { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function listLocalProjects(): Promise<LocalProject[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('projects', 'readonly');
    const store = tx.objectStore('projects');
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function createLocalProject(name: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('projects', 'readwrite');
    const store = tx.objectStore('projects');
    store.put({ name, createdAt: Date.now() });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteLocalProject(name: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction(['projects', 'documents'], 'readwrite');
  tx.objectStore('projects').delete(name);
  const docStore = tx.objectStore('documents');
  const idx = docStore.index('by_project');
  const cursor = idx.openCursor(IDBKeyRange.only(name));
  return new Promise((resolve, reject) => {
    cursor.onsuccess = () => {
      const c = (cursor as IDBRequest<IDBCursorWithValue>).result;
      if (c) { c.delete(); c.continue(); }
    };
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

function docId(project: string, folder: string, filename: string) {
  return project + '::' + folder + '::' + filename;
}

export async function addLocalDocuments(
  project: string,
  docs: { filename: string; parsedText: string; folder?: string }[]
): Promise<void> {
  const db = await openDB();
  const tx = db.transaction('documents', 'readwrite');
  const store = tx.objectStore('documents');
  for (const d of docs) {
    const folder = d.folder || '__root__';
    const doc: LocalDocument = {
      id: docId(project, folder, d.filename),
      project,
      folder,
      filename: d.filename,
      parsedText: d.parsedText,
      size: new Blob([d.parsedText]).size,
      uploadedAt: Date.now(),
    };
    store.put(doc);
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getProjectDocuments(project: string): Promise<LocalDocument[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('documents', 'readonly');
    const store = tx.objectStore('documents');
    const idx = store.index('by_project');
    const req = idx.getAll(IDBKeyRange.only(project));
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function deleteLocalDocument(project: string, folder: string, filename: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction('documents', 'readwrite');
  tx.objectStore('documents').delete(docId(project, folder, filename));
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteLocalFolder(project: string, folder: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction('documents', 'readwrite');
  const store = tx.objectStore('documents');
  const idx = store.index('by_project');
  const cursor = idx.openCursor(IDBKeyRange.only(project));
  return new Promise((resolve, reject) => {
    cursor.onsuccess = () => {
      const c = (cursor as IDBRequest<IDBCursorWithValue>).result;
      if (c) {
        if ((c.value as LocalDocument).folder === folder) { c.delete(); }
        c.continue();
      }
    };
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function moveLocalDocument(
  project: string, filename: string, fromFolder: string, toFolder: string
): Promise<void> {
  const db = await openDB();
  const tx = db.transaction('documents', 'readwrite');
  const store = tx.objectStore('documents');
  const oldId = docId(project, fromFolder, filename);
  const getReq = store.get(oldId);
  return new Promise((resolve, reject) => {
    getReq.onsuccess = () => {
      const doc = getReq.result as LocalDocument | undefined;
      if (!doc) { resolve(); return; }
      store.delete(oldId);
      doc.id = docId(project, toFolder, filename);
      doc.folder = toFolder;
      store.put(doc);
    };
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function createLocalFolder(project: string, folderName: string): Promise<void> {
  const db = await openDB();
  const tx = db.transaction('documents', 'readwrite');
  const store = tx.objectStore('documents');
  const id = docId(project, folderName, '__folder_placeholder__');
  store.put({
    id,
    project,
    folder: folderName,
    filename: '__folder_placeholder__',
    parsedText: '',
    size: 0,
    uploadedAt: Date.now(),
  } as LocalDocument);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getLocalFolderTree(project: string): Promise<Record<string, string[]>> {
  const docs = await getProjectDocuments(project);
  const tree: Record<string, string[]> = {};
  for (const d of docs) {
    if (d.filename === '__folder_placeholder__') {
      if (!tree[d.folder]) tree[d.folder] = [];
      continue;
    }
    if (!tree[d.folder]) tree[d.folder] = [];
    tree[d.folder].push(d.filename);
  }
  return tree;
}

export async function buildFileContext(
  project: string,
  selectedDocs?: string[]
): Promise<string> {
  const docs = await getProjectDocuments(project);
  const filtered = docs.filter(d => {
    if (d.filename === '__folder_placeholder__') return false;
    if (selectedDocs && selectedDocs.length > 0) {
      return selectedDocs.includes(d.filename);
    }
    return true;
  });
  return filtered.map(d => d.parsedText).join('\n\n');
}

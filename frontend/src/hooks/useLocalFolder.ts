/**
 * useLocalFolder — File System Access API를 사용한 로컬 폴더 연결 훅.
 * Chrome/Edge에서만 동작. 연결된 폴더에서 파일 읽기/쓰기 가능.
 */
import { useState, useCallback, useRef } from 'react';

const SUPPORTED_EXTENSIONS = new Set([
  '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
  '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm',
  '.png', '.jpg', '.jpeg',
]);

export interface LocalFile {
  name: string;
  path: string;
  size: number;
  ext: string;
  file: File;
}

// Check if File System Access API is supported
export function isFileSystemAccessSupported(): boolean {
  return 'showDirectoryPicker' in window;
}

export function useLocalFolder() {
  const [connected, setConnected] = useState(false);
  const [folderName, setFolderName] = useState('');
  const [scanning, setScanning] = useState(false);
  const [files, setFiles] = useState<LocalFile[]>([]);
  const handleRef = useRef<FileSystemDirectoryHandle | null>(null);

  // Connect to a local folder
  const connect = useCallback(async (): Promise<LocalFile[]> => {
    if (!isFileSystemAccessSupported()) {
      throw new Error('이 브라우저는 폴더 연결을 지원하지 않습니다. Chrome 또는 Edge를 사용하세요.');
    }

    try {
      const dirHandle = await (window as any).showDirectoryPicker({
        mode: 'readwrite',
      });
      handleRef.current = dirHandle;
      setFolderName(dirHandle.name);
      setConnected(true);

      // Scan files
      const scanned = await scanFolder(dirHandle);
      setFiles(scanned);
      return scanned;
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // User cancelled picker
        return [];
      }
      throw err;
    }
  }, []);

  // Rescan connected folder
  const rescan = useCallback(async (): Promise<LocalFile[]> => {
    if (!handleRef.current) return [];
    setScanning(true);
    try {
      // Verify permission is still granted
      const perm = await (handleRef.current as any).queryPermission({ mode: 'readwrite' });
      if (perm !== 'granted') {
        const requested = await (handleRef.current as any).requestPermission({ mode: 'readwrite' });
        if (requested !== 'granted') {
          disconnect();
          throw new Error('폴더 접근 권한이 거부되었습니다.');
        }
      }
      const scanned = await scanFolder(handleRef.current);
      setFiles(scanned);
      return scanned;
    } finally {
      setScanning(false);
    }
  }, []);

  // Save a file to the connected folder
  const saveFile = useCallback(async (filename: string, content: Blob | string): Promise<void> => {
    if (!handleRef.current) throw new Error('연결된 폴더가 없습니다.');

    const fileHandle = await handleRef.current.getFileHandle(filename, { create: true });
    const writable = await (fileHandle as any).createWritable();
    await writable.write(content);
    await writable.close();
  }, []);

  // Save to a subfolder
  const saveFileToSubfolder = useCallback(async (subfolder: string, filename: string, content: Blob | string): Promise<void> => {
    if (!handleRef.current) throw new Error('연결된 폴더가 없습니다.');

    const subHandle = await handleRef.current.getDirectoryHandle(subfolder, { create: true });
    const fileHandle = await subHandle.getFileHandle(filename, { create: true });
    const writable = await (fileHandle as any).createWritable();
    await writable.write(content);
    await writable.close();
  }, []);

  // Disconnect
  const disconnect = useCallback(() => {
    handleRef.current = null;
    setConnected(false);
    setFolderName('');
    setFiles([]);
  }, []);

  return {
    connected,
    folderName,
    scanning,
    files,
    connect,
    rescan,
    saveFile,
    saveFileToSubfolder,
    disconnect,
    isSupported: isFileSystemAccessSupported(),
  };
}


// ── Internal helpers ──

async function scanFolder(
  dirHandle: FileSystemDirectoryHandle,
  basePath = '',
): Promise<LocalFile[]> {
  const results: LocalFile[] = [];

  for await (const entry of (dirHandle as any).values()) {
    const entryPath = basePath ? `${basePath}/${entry.name}` : entry.name;

    if (entry.kind === 'file') {
      const ext = entry.name.includes('.') ? '.' + entry.name.split('.').pop()!.toLowerCase() : '';
      if (!SUPPORTED_EXTENSIONS.has(ext)) continue;
      if (entry.name.startsWith('~$') || entry.name.startsWith('.')) continue;

      try {
        const file: File = await entry.getFile();
        results.push({
          name: entry.name,
          path: entryPath,
          size: file.size,
          ext,
          file,
        });
      } catch {
        // Skip files that can't be read
      }
    } else if (entry.kind === 'directory') {
      // Skip hidden/system directories
      if (entry.name.startsWith('.') || entry.name === 'node_modules' || entry.name === '__pycache__') continue;
      const subResults = await scanFolder(entry, entryPath);
      results.push(...subResults);
    }
  }

  return results;
}

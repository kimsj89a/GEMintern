import { useRef, useState } from 'react';
import { isFileSystemAccessSupported } from '../hooks/useLocalFolder';

const SUPPORTED_EXTENSIONS = new Set([
  '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.txt', '.md', '.csv',
]);

interface FilePickerProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  loading?: boolean;
  // Local folder connection
  localFolderConnected?: boolean;
  localFolderName?: string;
  onConnectFolder?: () => void;
  onRescanFolder?: () => void;
  onDisconnectFolder?: () => void;
  localScanning?: boolean;
}

export default function FilePicker({
  onFilesSelected, accept, multiple = true, loading,
  localFolderConnected, localFolderName, onConnectFolder, onRescanFolder, onDisconnectFolder, localScanning,
}: FilePickerProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);

  const filterSupported = (files: File[]) =>
    files.filter(f => {
      const ext = f.name.includes('.') ? '.' + f.name.split('.').pop()!.toLowerCase() : '';
      return SUPPORTED_EXTENSIONS.has(ext) && !f.name.startsWith('~$');
    });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) onFilesSelected(files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) onFilesSelected(files);
    e.target.value = '';
  };

  const handleFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const allFiles = Array.from(e.target.files || []);
    const supported = filterSupported(allFiles);
    if (supported.length > 0) onFilesSelected(supported);
    e.target.value = '';
  };

  const fsaSupported = isFileSystemAccessSupported();

  return (
    <div className="space-y-2">
      <div
        className={`relative border-2 border-dashed rounded-xl p-5 text-center transition-all duration-200 cursor-pointer ${
          dragOver
            ? 'border-blue-400 bg-blue-50/50 scale-[1.01]'
            : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50/50'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleChange}
          className="hidden"
        />
        <input
          ref={folderRef}
          type="file"
          // @ts-expect-error webkitdirectory is non-standard
          webkitdirectory=""
          multiple
          onChange={handleFolderChange}
          className="hidden"
        />
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-1">
            <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-slate-500">업로드 중...</span>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-3">
            <svg className="w-8 h-8 text-slate-300" viewBox="0 0 24 24" fill="none">
              <path d="M12 16V4m0 0L8 8m4-4l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <div className="text-left">
              <div className="text-sm text-slate-600 font-medium">파일을 드래그하거나 클릭</div>
              <div className="text-xs text-slate-400 mt-0.5">PDF, Word, Excel, TXT, MD</div>
            </div>
          </div>
        )}
      </div>
      {!loading && (
        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); folderRef.current?.click(); }}
            className="flex-1 px-2 py-1.5 text-[11px] text-violet-600 bg-violet-50 border border-violet-200 rounded-lg hover:bg-violet-100 transition-colors"
          >
            📁 폴더 업로드
          </button>
          {fsaSupported && onConnectFolder && (
            localFolderConnected ? (
              <div className="flex-1 flex items-center gap-1">
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onRescanFolder?.(); }}
                  disabled={localScanning}
                  className="flex-1 px-2 py-1.5 text-[11px] text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors disabled:opacity-50 truncate"
                  title={localFolderName}
                >
                  {localScanning ? '⏳ 스캔 중...' : `🔗 ${localFolderName}`}
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onDisconnectFolder?.(); }}
                  className="px-1.5 py-1.5 text-[11px] text-slate-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition-colors"
                  title="연결 해제"
                >
                  ✕
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); onConnectFolder(); }}
                className="flex-1 px-2 py-1.5 text-[11px] text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors"
              >
                🔗 폴더 연결
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
}

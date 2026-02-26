import { useRef, useState } from 'react';

interface FilePickerProps {
  onFilesSelected: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  loading?: boolean;
}

export default function FilePicker({ onFilesSelected, accept, multiple = true, loading }: FilePickerProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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

  return (
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
      {loading ? (
        <div className="flex items-center justify-center gap-2 py-1">
          <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-slate-500">업로드 중...</span>
        </div>
      ) : (
        <>
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
        </>
      )}
    </div>
  );
}

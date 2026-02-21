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
      className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
        dragOver
          ? 'border-[#2383E2] bg-blue-50'
          : 'border-[#E9E9E7] hover:border-[#2383E2] hover:bg-[#FAFAF9]'
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
        <div className="text-sm text-[#787774]">업로드 중...</div>
      ) : (
        <>
          <div className="text-3xl mb-2">📎</div>
          <div className="text-sm text-[#37352F] font-medium">파일을 드래그하거나 클릭하여 업로드</div>
          <div className="text-xs text-[#9B9A97] mt-1">PDF, Word, Excel, TXT, MD 지원</div>
        </>
      )}
    </div>
  );
}

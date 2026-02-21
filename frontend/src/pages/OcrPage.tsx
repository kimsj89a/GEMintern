import { useRef, useState } from 'react';

interface OcrResult {
  filename: string;
  text: string;
}

export default function OcrPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [engine, setEngine] = useState<'gemini' | 'docai'>('gemini');
  const [results, setResults] = useState<OcrResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setFiles(selected);
  };

  const handleOcr = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setResults([]);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const formData = new FormData();
      files.forEach((f) => formData.append('files', f));
      formData.append('engine', engine);

      const res = await fetch('/api/ocr', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });
      const data = await res.json();
      setResults(data.results || []);
      setActiveTab(0);
    } catch (err: any) {
      if (err.name !== 'AbortError') setResults([{ filename: 'Error', text: err.message }]);
    }
    setLoading(false);
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const downloadAll = () => {
    const text = results.map((r) => `=== ${r.filename} ===\n\n${r.text}\n`).join('\n---\n\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'ocr_results.txt'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">👁️ 문서 OCR</h1>
      <p className="text-sm text-[#787774] mb-6">이미지/PDF에서 텍스트를 추출합니다.</p>

      {/* File picker */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <label className="block text-sm font-medium text-[#37352F] mb-2">파일 선택</label>
        <div
          className="border-2 border-dashed border-[#E9E9E7] rounded-xl p-6 text-center cursor-pointer hover:border-[#2383E2] hover:bg-[#FAFAF9] transition-colors"
          onClick={() => inputRef.current?.click()}
        >
          <input ref={inputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp" multiple onChange={handleFiles} className="hidden" />
          <div className="text-3xl mb-2">📎</div>
          <div className="text-sm text-[#37352F]">
            {files.length > 0 ? `${files.length}개 파일 선택됨` : 'PDF, 이미지 파일을 선택하세요'}
          </div>
        </div>
      </div>

      {/* Engine */}
      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <label className="block text-sm font-medium text-[#37352F] mb-2">OCR 엔진</label>
        <div className="flex gap-3">
          <label className="flex items-center gap-1.5 text-sm cursor-pointer">
            <input type="radio" checked={engine === 'gemini'} onChange={() => setEngine('gemini')} />
            Gemini Vision (빠름)
          </label>
          <label className="flex items-center gap-1.5 text-sm cursor-pointer">
            <input type="radio" checked={engine === 'docai'} onChange={() => setEngine('docai')} />
            Document AI (고품질)
          </label>
        </div>
      </div>

      {loading ? (
        <div className="flex gap-2 mb-4">
          <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
            OCR 변환 중...
          </div>
          <button onClick={handleStop}
            className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
            중지
          </button>
        </div>
      ) : (
        <button onClick={handleOcr} disabled={files.length === 0}
          className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
          🔍 OCR 변환 시작
        </button>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-[#E9E9E7]">
            <div className="flex gap-1 overflow-x-auto">
              {results.map((r, i) => (
                <button key={i} onClick={() => setActiveTab(i)}
                  className={`px-3 py-1 text-xs rounded-lg whitespace-nowrap ${activeTab === i ? 'bg-[#2383E2] text-white' : 'hover:bg-[#F7F6F3]'}`}>
                  {r.filename}
                </button>
              ))}
            </div>
            <button onClick={downloadAll} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3] shrink-0 ml-2">
              📄 전체 TXT 저장
            </button>
          </div>
          <div className="p-4 max-h-96 overflow-y-auto">
            <pre className="text-sm text-[#37352F] whitespace-pre-wrap">{results[activeTab]?.text}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

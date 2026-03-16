import { useCallback, useRef, useState } from 'react';
import { generateFilename } from '../utils/clipboard';
import { useAppStore } from '../stores/appStore';
import { useAuthStore } from '../stores/authStore';
import MarkdownViewer from '../components/MarkdownViewer';

interface OcrResult {
  filename: string;
  text: string;
}

type Engine = 'gemini' | 'claude' | 'docai';

export default function OcrPage() {
  const { currentProject } = useAppStore();
  const [files, setFiles] = useState<File[]>([]);
  const [engine, setEngine] = useState<Engine>('gemini');
  const [results, setResults] = useState<OcrResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const addFiles = useCallback((newFiles: File[]) => {
    const accepted = newFiles.filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase() || '';
      return ['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp'].includes(ext);
    });
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name));
      return [...prev, ...accepted.filter(f => !existing.has(f.name))];
    });
  }, []);

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(e.target.files || []));
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    addFiles(Array.from(e.dataTransfer.files));
  }, [addFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const removeFile = (idx: number) => {
    setFiles(prev => prev.filter((_, i) => i !== idx));
  };

  const handleOcr = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setResults([]);
    setProgress({ done: 0, total: files.length });
    const controller = new AbortController();
    abortRef.current = controller;

    const token = useAuthStore.getState().token;
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    // Process files one by one for progress tracking
    const allResults: OcrResult[] = [];
    for (let i = 0; i < files.length; i++) {
      if (controller.signal.aborted) break;
      setProgress({ done: i, total: files.length });

      try {
        const formData = new FormData();
        formData.append('files', files[i]);
        formData.append('engine', engine);

        const res = await fetch('/api/ocr', {
          method: 'POST',
          body: formData,
          signal: controller.signal,
          headers,
        });
        const data = await res.json();
        const fileResults = data.results || [];
        allResults.push(...fileResults);
        setResults([...allResults]);
        if (allResults.length === 1) setActiveTab(0);
      } catch (err: any) {
        if (err.name === 'AbortError') break;
        allResults.push({ filename: files[i].name, text: `오류: ${err.message}` });
        setResults([...allResults]);
      }
    }
    setProgress(null);
    setLoading(false);
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
    setProgress(null);
  };

  const downloadAll = () => {
    const text = results.map((r) => `=== ${r.filename} ===\n\n${r.text}\n`).join('\n---\n\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = generateFilename('OCR', 'txt', currentProject); a.click();
    URL.revokeObjectURL(url);
  };

  const downloadSingle = (r: OcrResult) => {
    const blob = new Blob([r.text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${r.filename.replace(/\.[^.]+$/, '')}_OCR.md`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-slate-800 mb-1">문서 OCR</h1>
      <p className="text-sm text-slate-500 mb-6">이미지/PDF에서 텍스트를 추출합니다.</p>

      <div className="flex gap-4">
        {/* Left panel: files + engine */}
        <div className="w-80 shrink-0 space-y-3">
          {/* Drop zone */}
          <div className="glass-card p-4">
            <label className="block text-sm font-semibold text-slate-700 mb-2">파일 선택</label>
            <div
              className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                dragging
                  ? 'border-blue-400 bg-blue-50/50'
                  : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50/50'
              }`}
              onClick={() => inputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={() => setDragging(false)}
            >
              <input ref={inputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.webp" multiple onChange={handleFiles} className="hidden" />
              <div className="text-2xl mb-1">{dragging ? '📥' : '📎'}</div>
              <div className="text-sm text-slate-600">
                {dragging ? '여기에 놓으세요' : '클릭 또는 드래그 앤 드롭'}
              </div>
              <div className="text-[10px] text-slate-400 mt-1">PDF, PNG, JPG, TIFF, BMP, WebP</div>
            </div>

            {/* File list */}
            {files.length > 0 && (
              <div className="mt-3 space-y-1 max-h-48 overflow-y-auto">
                {files.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-slate-50 group">
                    <span className="text-xs text-slate-400">📄</span>
                    <span className="text-xs text-slate-700 truncate flex-1">{f.name}</span>
                    <span className="text-[10px] text-slate-400">{(f.size / 1024).toFixed(0)}KB</span>
                    <button onClick={() => removeFile(i)}
                      className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 text-xs transition-opacity">✕</button>
                  </div>
                ))}
                <div className="flex items-center justify-between pt-1 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">{files.length}개 파일</span>
                  <button onClick={() => setFiles([])} className="text-[10px] text-red-400 hover:text-red-600">전체 삭제</button>
                </div>
              </div>
            )}
          </div>

          {/* Engine selector */}
          <div className="glass-card p-4">
            <label className="block text-sm font-semibold text-slate-700 mb-2">OCR 엔진</label>
            <div className="space-y-1.5">
              {([
                { id: 'gemini' as Engine, label: 'Gemini Vision', desc: '빠르고 정확 (기본)' },
                { id: 'claude' as Engine, label: 'Claude Vision', desc: '고품질 문서 인식' },
                { id: 'docai' as Engine, label: 'Document AI', desc: 'Google Cloud OCR' },
              ]).map(opt => (
                <label key={opt.id}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-all ${
                    engine === opt.id ? 'bg-blue-50/80 border border-blue-200' : 'hover:bg-slate-50 border border-transparent'
                  }`}>
                  <input type="radio" checked={engine === opt.id} onChange={() => setEngine(opt.id)}
                    className="w-3.5 h-3.5 text-blue-600" />
                  <div>
                    <div className={`text-sm ${engine === opt.id ? 'font-semibold text-blue-700' : 'text-slate-600'}`}>{opt.label}</div>
                    <div className="text-[10px] text-slate-400">{opt.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Action button */}
          {loading ? (
            <div className="space-y-2">
              <div className="flex gap-2">
                <div className="flex-1 py-2.5 bg-slate-300 text-white text-sm font-semibold rounded-xl text-center">
                  {progress ? `변환 중... (${progress.done + 1}/${progress.total})` : '변환 중...'}
                </div>
                <button onClick={handleStop}
                  className="px-4 py-2.5 bg-red-500 text-white text-sm font-semibold rounded-xl hover:bg-red-600 transition-colors">
                  중지
                </button>
              </div>
              {progress && (
                <div className="w-full bg-slate-100 rounded-full h-1.5">
                  <div className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${((progress.done + 0.5) / progress.total) * 100}%` }} />
                </div>
              )}
            </div>
          ) : (
            <button onClick={handleOcr} disabled={files.length === 0}
              className={`w-full py-3 text-sm font-semibold rounded-xl transition-all ${
                files.length > 0 ? 'btn-primary' : 'bg-slate-100 text-slate-400 cursor-not-allowed'
              }`}>
              OCR 변환 시작 ({files.length}개)
            </button>
          )}
        </div>

        {/* Right panel: results */}
        <div className="flex-1 min-w-0">
          {results.length > 0 ? (
            <div className="glass-card-elevated overflow-hidden" style={{ height: 'calc(100vh - 200px)' }}>
              {/* Tabs */}
              <div className="flex items-center gap-1 px-3 py-2 border-b border-slate-100 overflow-x-auto">
                {results.map((r, i) => (
                  <button key={i} onClick={() => setActiveTab(i)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-all ${
                      activeTab === i ? 'btn-primary shadow-sm' : 'text-slate-500 hover:bg-slate-50'
                    }`}>
                    {r.filename}
                  </button>
                ))}
              </div>
              {/* Content */}
              <div className="flex-1 overflow-y-auto p-4" style={{ height: 'calc(100% - 85px)' }}>
                <MarkdownViewer content={results[activeTab]?.text || ''} />
              </div>
              {/* Actions */}
              <div className="flex gap-2 px-3 py-2 border-t border-slate-100">
                <button onClick={() => results[activeTab] && downloadSingle(results[activeTab])}
                  className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
                  이 파일 저장
                </button>
                <button onClick={downloadAll}
                  className="px-3 py-1.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors">
                  전체 TXT 저장
                </button>
                <button onClick={() => { navigator.clipboard.writeText(results[activeTab]?.text || ''); }}
                  className="px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition-colors">
                  복사
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-400 py-20">
              <svg className="w-12 h-12 mb-3 opacity-20" viewBox="0 0 24 24" fill="none"><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke="currentColor" strokeWidth="1.5"/><path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" stroke="currentColor" strokeWidth="1.5"/></svg>
              <span className="text-sm">파일을 선택하고 OCR을 시작하세요</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

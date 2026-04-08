/**
 * DocxMarkupPage — DOCX Tracked Changes tool.
 * Extract, compare, generate clean/redline versions.
 */
import { useRef, useState } from 'react';
import { useAuthStore } from '../stores/authStore';

type TabId = 'extract' | 'compare' | 'output';

export default function DocxMarkupPage() {
  const [tab, setTab] = useState<TabId>('extract');
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = async (endpoint: string) => {
    if (!files.length) return;
    setLoading(true); setResult(null);
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    try {
      const res = await fetch(`/api${endpoint}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${useAuthStore.getState().token}` },
        body: formData,
      });
      if (res.ok) {
        setResult(await res.json());
      } else {
        const text = await res.text();
        try { setResult(JSON.parse(text)); } catch { setResult({ error: `서버 오류 (${res.status}): ${text.slice(0, 200)}` }); }
      }
    } catch (e: any) { setResult({ error: `요청 실패: ${e.message}` }); }
    setLoading(false);
  };

  const downloadB64 = (b64: string, filename: string) => {
    const bytes = atob(b64);
    const arr = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
    const blob = new Blob([arr], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename; a.click();
  };

  return (
    <div className="max-w-4xl mx-auto p-6" style={{ fontFamily: "'Noto Sans KR', sans-serif" }}>
      <h1 className="text-xl font-bold text-[#2A2A2A] mb-1">📝 DOCX Markup Tool</h1>
      <p className="text-sm text-[#9B9B9B] mb-5">Tracked Changes 추출 · 비교 · Clean/Redline 생성</p>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 bg-white rounded-xl border border-slate-100 p-1 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        {([['extract', '변경사항 추출'], ['compare', '문서 비교'], ['output', 'Clean/Redline']] as [TabId, string][]).map(([id, label]) => (
          <button key={id} onClick={() => { setTab(id); setResult(null); }}
            className={`flex-1 px-4 py-2 text-sm rounded-lg transition-colors ${tab === id ? 'bg-indigo-500 text-white font-medium' : 'text-[#6A6A6A] hover:bg-slate-50'}`}>
            {label}
          </button>
        ))}
      </div>

      {/* File upload */}
      <div className="bg-white rounded-2xl border border-slate-100 p-5 mb-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <div
          className="border-2 border-dashed border-slate-200 rounded-xl p-6 text-center cursor-pointer hover:border-indigo-300 transition-colors"
          onClick={() => fileRef.current?.click()}
          onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('border-indigo-400', 'bg-indigo-50/30'); }}
          onDragLeave={e => { e.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50/30'); }}
          onDrop={e => { e.preventDefault(); e.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50/30'); setFiles(Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.docx'))); }}
        >
          <input ref={fileRef} type="file" multiple accept=".docx" className="hidden"
            onChange={e => { if (e.target.files) setFiles(Array.from(e.target.files)); e.target.value = ''; }} />
          <div className="text-3xl mb-2">📄</div>
          <div className="text-sm text-[#6A6A6A]">{files.length > 0 ? `${files.length}개 파일 선택됨` : 'DOCX 파일을 드래그하거나 클릭'}</div>
          {files.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3 justify-center">
              {files.map((f, i) => (
                <span key={i} className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded-lg text-xs">{f.name}</span>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={() => upload(tab === 'extract' ? '/docx-markup/extract' : tab === 'compare' ? '/docx-markup/compare' : '/docx-markup/clean-redline')}
          disabled={!files.length || loading}
          className="w-full mt-4 px-5 py-2.5 bg-indigo-500 text-white rounded-xl font-medium hover:bg-indigo-600 disabled:opacity-30 transition-colors">
          {loading ? '처리 중...' : tab === 'extract' ? '변경사항 추출' : tab === 'compare' ? '문서 비교' : 'Clean/Redline 생성'}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
          {result.error && <div className="text-red-500 text-sm">{result.error}</div>}

          {/* Extract results */}
          {tab === 'extract' && result.results && Object.entries(result.results).map(([fname, changes]: any) => (
            <div key={fname} className="mb-4">
              <div className="text-sm font-bold text-[#2A2A2A] mb-2">📄 {fname}</div>
              {Array.isArray(changes) ? (
                <div className="space-y-1.5">
                  {changes.map((c: any, i: number) => (
                    <div key={i} className="flex gap-2 text-xs px-3 py-2 bg-[#FAFAFA] rounded-lg">
                      <span className={`shrink-0 px-1.5 py-0.5 rounded font-medium ${c.type === 'insertion' ? 'bg-green-100 text-green-700' : c.type === 'deletion' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                        {c.type}
                      </span>
                      <span className="text-[#6A6A6A]">{c.author}</span>
                      <span className="text-[#2A2A2A] flex-1">{c.text}</span>
                    </div>
                  ))}
                  <div className="text-[10px] text-[#9B9B9B] mt-2">총 {changes.length}건</div>
                </div>
              ) : (
                <div className="text-red-500 text-xs">{changes.error}</div>
              )}
            </div>
          ))}

          {/* Compare results */}
          {tab === 'compare' && result.report && (
            <pre className="text-sm text-[#2A2A2A] whitespace-pre-wrap leading-relaxed">{result.report}</pre>
          )}

          {/* Clean/Redline download */}
          {tab === 'output' && result.files && (
            <div className="flex gap-3">
              {result.files.clean && (
                <button onClick={() => downloadB64(result.files.clean, `${result.stem}_CLEAN.docx`)}
                  className="flex-1 px-4 py-3 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700 font-medium hover:bg-green-100">
                  ✅ Clean 버전 다운로드
                </button>
              )}
              {result.files.redline && (
                <button onClick={() => downloadB64(result.files.redline, `${result.stem}_REDLINE.docx`)}
                  className="flex-1 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 font-medium hover:bg-red-100">
                  📝 Redline 버전 다운로드
                </button>
              )}
            </div>
          )}
          {tab === 'output' && result.error && (
            <div className="text-sm text-red-500">{result.error}</div>
          )}
        </div>
      )}
    </div>
  );
}

import { useRef, useState } from 'react';
import { generateFilename } from '../utils/clipboard';
import { useAppStore } from '../stores/appStore';

interface CrawlResult {
  url: string;
  title: string;
  preview: string;
  text: string;
}

export default function CrawlerPage() {
  const { currentProject } = useAppStore();
  const [urls, setUrls] = useState('');
  const [depth, setDepth] = useState(1);
  const [maxPages, setMaxPages] = useState(10);
  const [results, setResults] = useState<CrawlResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  const handleCrawl = async () => {
    const urlList = urls.split('\n').map((u) => u.trim()).filter(Boolean);
    if (urlList.length === 0) return;
    setLoading(true);
    setResults([]);
    setProgress('크롤링 시작...');
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch('/api/crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: urlList, depth, max_pages: maxPages }),
        signal: controller.signal,
      });
      const data = await res.json();
      setResults(data.results || []);
      setProgress(`${data.results?.length || 0}개 페이지 수집 완료`);
    } catch (err: any) {
      if (err.name !== 'AbortError') setProgress(`오류: ${err.message}`);
      else setProgress('크롤링 중지됨');
    }
    setLoading(false);
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const exportCsv = () => {
    const header = 'URL,제목,미리보기\n';
    const rows = results.map((r) =>
      `"${r.url}","${r.title?.replace(/"/g, '""') || ''}","${r.preview?.replace(/"/g, '""') || ''}"`
    ).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = generateFilename('크롤링', 'csv', currentProject); a.click();
    URL.revokeObjectURL(url);
  };

  const exportTxt = () => {
    const text = results.map((r) => `=== ${r.url} ===\n${r.title}\n\n${r.text}\n`).join('\n---\n\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = generateFilename('크롤링', 'txt', currentProject); a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">🌐 웹 크롤러</h1>
      <p className="text-sm text-[#787774] mb-6">웹 페이지에서 텍스트를 추출합니다.</p>

      <div className="bg-white border border-[#E9E9E7] rounded-xl p-4 mb-4">
        <label className="block text-sm font-medium text-[#37352F] mb-2">URL 입력 (줄 단위)</label>
        <textarea
          value={urls}
          onChange={(e) => setUrls(e.target.value)}
          placeholder="https://example.com&#10;https://example.com/page2"
          rows={4}
          className="w-full px-3 py-2 border border-[#E9E9E7] rounded-lg text-sm focus:outline-none focus:border-[#2383E2] resize-none mb-3"
        />
        <div className="flex gap-4">
          <div>
            <label className="block text-xs text-[#787774] mb-1">깊이</label>
            <input type="number" min={1} max={5} value={depth} onChange={(e) => setDepth(+e.target.value)}
              className="w-20 px-2 py-1 border border-[#E9E9E7] rounded text-sm" />
          </div>
          <div>
            <label className="block text-xs text-[#787774] mb-1">최대 페이지</label>
            <input type="number" min={1} max={50} value={maxPages} onChange={(e) => setMaxPages(+e.target.value)}
              className="w-20 px-2 py-1 border border-[#E9E9E7] rounded text-sm" />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex gap-2 mb-4">
          <div className="flex-1 py-2.5 bg-[#b0b0b0] text-white text-sm font-semibold rounded-xl text-center">
            크롤링 중...
          </div>
          <button onClick={handleStop}
            className="px-6 py-2.5 bg-[#EB5757] text-white text-sm font-semibold rounded-xl hover:bg-[#d94848] transition-colors">
            중지
          </button>
        </div>
      ) : (
        <button onClick={handleCrawl} disabled={!urls.trim()}
          className="w-full py-2.5 bg-[#2383E2] text-white text-sm font-semibold rounded-xl hover:bg-[#1b6ec2] disabled:bg-[#b0b0b0] transition-colors mb-4">
          🕷️ 크롤링 시작
        </button>
      )}

      {progress && <div className="text-sm text-[#787774] mb-4">{progress}</div>}

      {results.length > 0 && (
        <div className="bg-white border border-[#E9E9E7] rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-[#E9E9E7]">
            <div className="text-sm font-semibold text-[#37352F]">{results.length}개 결과</div>
            <div className="flex gap-2">
              <button onClick={exportCsv} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">CSV</button>
              <button onClick={exportTxt} className="px-2 py-1 text-xs border border-[#E9E9E7] rounded hover:bg-[#F7F6F3]">TXT</button>
            </div>
          </div>
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#F7F6F3] sticky top-0">
                <tr>
                  <th className="text-left px-4 py-2 text-[#787774] font-medium">URL</th>
                  <th className="text-left px-4 py-2 text-[#787774] font-medium">제목</th>
                  <th className="text-left px-4 py-2 text-[#787774] font-medium">미리보기</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className="border-t border-[#E9E9E7] hover:bg-[#FAFAF9]">
                    <td className="px-4 py-2 text-[#2383E2] truncate max-w-[200px]">{r.url}</td>
                    <td className="px-4 py-2 text-[#37352F] truncate max-w-[200px]">{r.title}</td>
                    <td className="px-4 py-2 text-[#787774] truncate max-w-[300px]">{r.preview}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

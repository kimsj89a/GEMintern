import { useEffect, useState } from 'react';
import { api } from '../api/client';

interface HistoryItem {
  id: number;
  endpoint: string;
  title: string;
  model: string;
  status: string;
  created_at: string;
}

interface HistoryDetail extends HistoryItem {
  inputs: Record<string, any> | null;
  result_text: string;
}

const ENDPOINT_LABELS: Record<string, string> = {
  '/generate': '문서 생성',
  '/qa': 'Q&A',
  '/freedoc/generate': '자유양식 문서',
  '/draftdoc/generate': '기안문 작성',
  '/quickmail/generate': 'QuickMail',
};

function endpointLabel(ep: string): string {
  if (ep.startsWith('/analyze/')) return ep.replace('/analyze/', '분석: ');
  return ENDPOINT_LABELS[ep] || ep;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60_000) return '방금 전';
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)}분 전`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}시간 전`;
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<HistoryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadItems = async () => {
    setLoading(true);
    try {
      const res = await api.listHistory(100);
      setItems(res.items);
    } catch {
      /* ignore */
    }
    setLoading(false);
  };

  useEffect(() => { loadItems(); }, []);

  const openDetail = async (id: number) => {
    setDetailLoading(true);
    try {
      const detail = await api.getHistory(id);
      setSelected(detail);
    } catch {
      /* ignore */
    }
    setDetailLoading(false);
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteHistory(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      if (selected?.id === id) setSelected(null);
    } catch {
      /* ignore */
    }
  };

  const handleCopy = () => {
    if (selected?.result_text) {
      navigator.clipboard.writeText(selected.result_text);
    }
  };

  if (selected) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <button
          onClick={() => setSelected(null)}
          className="text-sm text-[#2383E2] hover:underline mb-4 inline-block"
        >
          &larr; 목록으로
        </button>

        <div className="bg-white border border-[#E9E9E7] rounded-xl p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-600 border border-blue-200 mr-2">
                {endpointLabel(selected.endpoint)}
              </span>
              <span className="text-xs text-[#787774]">{selected.model}</span>
              <h2 className="text-lg font-bold text-[#37352F] mt-1">
                {selected.title || '(제목 없음)'}
              </h2>
              <p className="text-xs text-[#787774]">{formatDate(selected.created_at)}</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCopy}
                className="px-3 py-1.5 text-xs border border-[#E9E9E7] rounded-lg hover:bg-[#F7F6F3] transition-colors"
              >
                복사
              </button>
              <button
                onClick={() => handleDelete(selected.id)}
                className="px-3 py-1.5 text-xs border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
              >
                삭제
              </button>
            </div>
          </div>

          {selected.inputs && Object.keys(selected.inputs).length > 0 && (
            <div className="mb-4 p-3 bg-[#FAFAF9] rounded-lg">
              <div className="text-xs font-medium text-[#787774] mb-1">입력 파라미터</div>
              <div className="text-xs text-[#37352F] font-mono">
                {Object.entries(selected.inputs).map(([k, v]) => (
                  <div key={k}><span className="text-[#787774]">{k}:</span> {String(v)}</div>
                ))}
              </div>
            </div>
          )}

          <div className="max-h-[60vh] overflow-y-auto">
            <pre className="text-sm text-[#37352F] whitespace-pre-wrap leading-relaxed">
              {selected.result_text}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-[#37352F] mb-1">생성 이력</h1>
      <p className="text-sm text-[#787774] mb-6">AI로 생성한 작업 결과를 확인합니다.</p>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-[#787774]">
          <div className="text-4xl mb-3">📭</div>
          <div className="text-sm">아직 생성 이력이 없습니다.</div>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-white border border-[#E9E9E7] rounded-xl p-4 hover:border-[#2383E2] cursor-pointer transition-colors group"
              onClick={() => openDetail(item.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-600 border border-blue-200">
                      {endpointLabel(item.endpoint)}
                    </span>
                    <span className="text-xs text-[#787774]">{item.model}</span>
                  </div>
                  <div className="text-sm font-medium text-[#37352F] truncate">
                    {item.title || '(제목 없음)'}
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-4 shrink-0">
                  <span className="text-xs text-[#787774]">{formatDate(item.created_at)}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(item.id); }}
                    className="w-7 h-7 flex items-center justify-center rounded-lg text-[#787774] hover:bg-red-50 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all"
                    title="삭제"
                  >
                    &times;
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {detailLoading && (
        <div className="fixed inset-0 bg-black/10 flex items-center justify-center z-50">
          <div className="w-8 h-8 border-3 border-blue-400 border-t-transparent rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}
